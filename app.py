import streamlit as st
import json
import os
import time
import hashlib
import random
import re
from datetime import datetime
import pandas as pd
import requests
from supabase import create_client

# ==================== 页面配置 ====================
st.set_page_config(page_title="惠山古镇 AI 导览 | 非遗数字体验", layout="centered", initial_sidebar_state="expanded")

# ==================== CSS ====================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Noto+Serif+SC:wght@400;700&display=swap');
    .stApp { background: #F8F9F8; font-family: 'Noto Serif SC', serif; }
    .main > div { background-color: #ffffff; border-radius: 8px; padding: 1rem 1.5rem 1.5rem 1.5rem; box-shadow: 0 1px 2px rgba(0,0,0,0.03); border: 0.5px solid #e2e2e2; }
    .poi-card { background: #EAECE9; border-left: 4px solid #E63946; padding: 1rem 1.2rem; border-radius: 4px; margin: 1rem 0 1.5rem 0; font-size: 0.95rem; line-height: 1.5; color: #4A4E51; box-shadow: none; }
    .source-chip { display: inline-block; background-color: #f0f0f0; color: #4A4E51; padding: 2px 12px; border-radius: 4px; font-size: 0.7rem; font-weight: 400; margin-top: 8px; font-family: 'Inter', sans-serif; }
    div.stButton > button { background-color: #ffffff; color: #E63946; border: 1px solid #e2e2e2; border-radius: 4px; padding: 0.5rem 1.2rem; font-weight: 400; transition: 0.2s; font-family: 'Inter', sans-serif; }
    div.stButton > button:hover { background-color: #E63946; color: white; border-color: #E63946; }
    .stChatInput input { border-radius: 4px; border: 1px solid #e2e2e2; background-color: #ffffff; }
    [data-testid="stSidebar"] { background: #ffffff; border-right: 0.5px solid #e2e2e2; font-family: 'Inter', sans-serif; }
</style>
""", unsafe_allow_html=True)

# ==================== 语音 JS ====================
st.markdown("""
<script>
function speakText(text) {
    if (!window.speechSynthesis) {
        console.warn("浏览器不支持语音合成");
        alert("您的浏览器不支持语音合成功能");
        return;
    }
    var utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'zh-CN';
    utterance.rate = 0.9;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
}
</script>
""", unsafe_allow_html=True)

# ==================== 加载 POI 数据 ====================
@st.cache_data
def load_poi_data():
    with open("data/poi_content.json", "r", encoding="utf-8") as f:
        content = f.read()
        content = re.sub(r',\s*}', '}', content)
        content = re.sub(r',\s*]', ']', content)
        return json.loads(content)

poi_database = load_poi_data()
expected_pois = ["fanwenzheng_gongci", "guhuashanmen", "bayinjian", "zhulu_shanfang", "erquan"]
POI_ORDER = [p for p in expected_pois if p in poi_database]
POI_NAMES = {pid: poi_database[pid]["name"] for pid in POI_ORDER}

# ==================== URL 参数与 Session ====================
if "participant_id" not in st.session_state:
    st.session_state.participant_id = st.query_params.get("pid", "P_TEST_USER")

if "group" not in st.session_state:
    hash_val = int(hashlib.md5(st.session_state.participant_id.encode()).hexdigest()[:4], 16)
    group_map = ["A", "B", "C"]
    st.session_state.group = group_map[hash_val % 3]

group_condition_map = {
    "A": ["baseline", "free_text", "recchatbox", "baseline", "free_text"],
    "B": ["free_text", "recchatbox", "baseline", "free_text", "recchatbox"],
    "C": ["recchatbox", "baseline", "free_text", "recchatbox", "baseline"]
}
condition_sequence = group_condition_map[st.session_state.group]

if "current_poi_index" not in st.session_state:
    current_poi_key = st.query_params.get("poi", POI_ORDER[0])
    st.session_state.current_poi_index = POI_ORDER.index(current_poi_key) if current_poi_key in POI_ORDER else 0
else:
    url_poi = st.query_params.get("poi")
    if url_poi and url_poi in POI_ORDER and POI_ORDER.index(url_poi) != st.session_state.current_poi_index:
        st.session_state.current_poi_index = POI_ORDER.index(url_poi)
        st.session_state.chat_messages = []
        st.session_state.followup_questions = []
        st.session_state.ai_response = None
        st.session_state.page_load_time = time.time()

current_poi_key = POI_ORDER[st.session_state.current_poi_index]
current_poi = poi_database[current_poi_key]
current_condition = condition_sequence[st.session_state.current_poi_index]

if current_condition == "baseline":
    actual_render = "baseline"
    display_condition_name = "传统静态网页"
elif current_condition == "free_text":
    actual_render = "free_text"
    display_condition_name = "自由提问 RAG"
else:
    actual_render = "recchatbox"
    display_condition_name = "智能推荐对话"

# ==================== 其他 Session 状态 ====================
if "logs" not in st.session_state:
    st.session_state.logs = []
if "page_load_time" not in st.session_state:
    st.session_state.page_load_time = time.time()
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "followup_questions" not in st.session_state:
    st.session_state.followup_questions = []
if "ai_response" not in st.session_state:
    st.session_state.ai_response = None

if actual_render != "baseline" and not st.session_state.chat_messages:
    st.session_state.chat_messages = [
        {"role": "assistant", "content": f"您好！欢迎来到【{current_poi['name']}】。您可以问我任何关于这个古迹的问题。"}
    ]

# Supabase 客户端
if "supabase" not in st.session_state:
    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_KEY"]
    st.session_state.supabase = create_client(supabase_url, supabase_key)

# ==================== 日志函数（完全沿用旧版稳定写法） ====================
def log_experimental_event(action_type, query_text="", response_time=0.0, retrieved_chunks="", displayed_source_cue=""):
    time_on_page = time.time() - st.session_state.page_load_time
    query_length = len(query_text) if query_text else 0

    event_data = {
        "participant_id": str(st.session_state.participant_id),
        "experimental_condition": current_condition,
        "poi_id": str(current_poi_key),
        "action_type": str(action_type),
        "time_on_page_seconds": round(time_on_page, 2),
        "user_query_text": str(query_text),
        "user_query_word_count": query_length,
        "rag_response_time_ms": round(response_time * 1000, 1),
        "retrieved_chunks_saved": str(retrieved_chunks),
        "displayed_source_cue": str(displayed_source_cue),
        "timestamp": datetime.now().isoformat()
    }
    st.session_state.logs.append(event_data)
    df = pd.DataFrame(st.session_state.logs)
    os.makedirs("logs", exist_ok=True)
    df.to_csv("logs/interaction_log.csv", index=False, encoding="utf-8-sig")
    try:
        st.session_state.supabase.table("interaction_logs").insert(event_data).execute()
    except Exception as e:
        st.error(f"⚠️ Supabase 写入失败: {e}")

# 页面首次加载埋点
if f"loaded_{current_poi_key}" not in st.session_state:
    st.session_state[f"loaded_{current_poi_key}"] = True
    log_experimental_event("page_loaded")

# ==================== Dify RAG 函数 ====================
def simulate_rag_engine(user_query):
    start = time.time()
    url = "https://api.dify.ai/v1/chat-messages"
    key = "Bearer app-rzITs8smrzMUhhdraDriLuRp"
    payload = {
        "inputs": {"current_poi": current_poi["name"]},
        "query": user_query,
        "response_mode": "blocking",
        "user": st.session_state.participant_id
    }
    headers = {"Authorization": key, "Content-Type": "application/json"}
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        ans = data.get("answer", "抱歉，无法回答。")
        resources = data.get("metadata", {}).get("retriever_resources", [])
        if resources:
            src = f"官方数字认证：{resources[0].get('dataset_name', '无锡史志库')}"
            chunks = str(resources)
        else:
            src = "惠山古镇文献库"
            chunks = "[通用生成]"
        elapsed = time.time() - start
        return ans, src, chunks, elapsed
    except Exception as e:
        elapsed = time.time() - start
        st.error(f"Dify API 错误: {str(e)}")
        return "【网络或服务异常】请稍后重试。", "故障降级", "[Error]", elapsed

def generate_followups_fallback():
    return [
        f"关于{current_poi['name']}还有哪些值得一访的历史细节？",
        f"这座建筑与无锡本地文化传统的关联体现在哪些方面？",
        f"在您的日常游览中，最能引发好奇心的遗产元素是什么？"
    ]

def generate_followup_questions(user_question, ai_answer):
    url = "https://api.dify.ai/v1/chat-messages"
    key = "Bearer app-CCck7NxI8NLZIxf24Q247Hti"
    prompt = f"""用户问题：{user_question}
AI回答：{ai_answer}
请以 JSON 格式输出 3 个与文化遗产相关的后续问题，格式为 ["问题1", "问题2", "问题3"]，不要有其他解释。"""
    try:
        resp = requests.post(url, json={"inputs": {}, "query": prompt, "response_mode": "blocking", "user": st.session_state.participant_id}, headers={"Authorization": key, "Content-Type": "application/json"}, timeout=10)
        answer = resp.json().get("answer", "[\"\"]")
        match = re.search(r'\[.*\]', answer, re.DOTALL)
        questions = json.loads(match.group(0)) if match else []
        while len(questions) < 3:
            questions.append("您还想了解更多关于这里的历史渊源吗？")
        return questions[:3]
    except Exception:
        return generate_followups_fallback()

def handle_question(question):
    with st.spinner("AI 导览员正在查阅史料..."):
        ans, src, chunks, elapsed = simulate_rag_engine(question)
        st.session_state.chat_messages.append({"role": "user", "content": question})
        st.session_state.chat_messages.append({"role": "assistant", "content": ans, "source": src})
        log_experimental_event("question_submitted", question, elapsed, chunks, src)
        # 朗读回答
        st.markdown(f'<script>speakText("{ans.replace('"', '\\"')}")</script>', unsafe_allow_html=True)
        if actual_render == "recchatbox":
            st.session_state.followup_questions = generate_followup_questions(question, ans)
        else:
            st.session_state.followup_questions = []

# ==================== 侧边栏 ====================
st.sidebar.markdown(f"**参与者 ID**：`{st.session_state.participant_id}`")
st.sidebar.markdown(f"**所属组别**：Group {st.session_state.group}")
st.sidebar.markdown(f"**当前体验**：{display_condition_name}")
st.sidebar.markdown(f"**进度**：{st.session_state.current_poi_index+1}/{len(POI_ORDER)}")
st.sidebar.markdown("---")
st.sidebar.markdown("### 🏮 游览路线")

progress = (st.session_state.current_poi_index + 1) / len(POI_ORDER)
st.sidebar.progress(progress)
for idx, pid in enumerate(POI_ORDER):
    if idx < st.session_state.current_poi_index:
        icon = "✅"
    elif idx == st.session_state.current_poi_index:
        icon = "📍"
    else:
        icon = "▪️"
    poi_name = POI_NAMES[pid]
    if st.sidebar.button(f"{icon} {poi_name}", key=f"nav_{pid}"):
        if idx != st.session_state.current_poi_index:
            st.session_state.current_poi_index = idx
            st.session_state.chat_messages = []
            st.session_state.followup_questions = []
            st.session_state.ai_response = None
            st.session_state.page_load_time = time.time()
            st.query_params["poi"] = pid
            st.query_params["pid"] = st.session_state.participant_id
            st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("📥 导出日志 CSV"):
    if st.session_state.logs:
        df = pd.DataFrame(st.session_state.logs)
        st.sidebar.download_button("点击下载", data=df.to_csv(index=False), file_name=f"{st.session_state.participant_id}_logs.csv")

# ==================== 主界面渲染 ====================
col1, col2 = st.columns([4, 1])
with col1:
    st.title(f"🏯 {current_poi['name']}")
with col2:
    if st.button("🔊 朗读介绍", key="speak_intro"):
        st.markdown(f'<script>speakText("{current_poi["info"]}")</script>', unsafe_allow_html=True)

st.markdown(f'<div class="poi-card">{current_poi["info"]}</div>', unsafe_allow_html=True)

if actual_render == "baseline":
    st.caption("✨ 静态展示模式 · 无 AI 对话")
else:
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and "source" in msg:
                st.markdown(f'<span class="source-chip">🔍 {msg["source"]}</span>', unsafe_allow_html=True)
    if actual_render == "recchatbox" and st.session_state.followup_questions:
        st.markdown("#### 💬 相关问题推荐")
        cols = st.columns(3)
        for i, q in enumerate(st.session_state.followup_questions):
            with cols[i % 3]:
                if st.button(f"❓ {q}", key=f"followup_{i}"):
                    handle_question(q)
    if prompt := st.chat_input("输入您的问题..."):
        handle_question(prompt)

st.markdown("---")
current_idx = st.session_state.current_poi_index
if current_idx + 1 < len(POI_ORDER):
    next_poi = POI_ORDER[current_idx + 1]
    if st.button("✅ 我已游览完当前点位，前往下一站", use_container_width=True):
        log_experimental_event("completed")
        st.session_state.current_poi_index += 1
        st.session_state.chat_messages = []
        st.session_state.followup_questions = []
        st.session_state.ai_response = None
        st.session_state.page_load_time = time.time()
        st.query_params["poi"] = next_poi
        st.query_params["pid"] = st.session_state.participant_id
        st.rerun()
else:
    st.success("🎉 恭喜您完成全部 5 个点位的文化探索！")
    if st.button("📤 完成实验，提交数据", use_container_width=True):
        log_experimental_event("all_completed")
        st.markdown("请关闭页面并返回问卷。")
