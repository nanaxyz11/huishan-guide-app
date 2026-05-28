import streamlit as st
import json
import os
import time
import hashlib
import random
import re
from datetime import datetime, timezone, timedelta
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from supabase import create_client

# ==================== 页面配置 ====================
st.set_page_config(page_title="惠山古镇 AI 导览 | 非遗数字体验", layout="centered", initial_sidebar_state="expanded")

# ==================== 江南水墨风 CSS（融入江南园林色彩体系） ====================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@300;600;900&display=swap');
    /* 全局江南水墨风 */
    .stApp {
        background: linear-gradient(145deg, #fef7e8 0%, #f9f5eb 100%);
        font-family: 'Noto Serif SC', 'Georgia', 'Songti SC', serif;
    }
    /* 主容器 */
    .main > div {
        background-color: rgba(255, 250, 240, 0.92);
        border-radius: 16px;
        padding: 1rem 1.5rem 1.5rem 1.5rem;
        box-shadow: 0 8px 20px rgba(0,0,0,0.06);
        border-left: 1px solid #e2d9cd;
        border-top: 1px solid #e2d9cd;
    }
    /* POI 信息卡片 */
    .poi-card {
        background: #ffffff;
        border-left: 8px solid #6b8c7c;
        padding: 1rem 1.2rem;
        border-radius: 8px;
        margin: 1rem 0 1.5rem 0;
        font-size: 1rem;
        line-height: 1.6;
        color: #2c3e2f;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
        font-family: 'Noto Serif SC', serif;
    }
    /* 来源标识 */
    .source-chip {
        display: inline-block;
        background-color: #eae3d4;
        color: #6e5c44;
        padding: 2px 12px;
        border-radius: 18px;
        font-size: 0.7rem;
        font-weight: 500;
        margin-top: 8px;
        font-style: italic;
    }
    /* 按钮中国风 */
    div.stButton > button {
        background-color: #ffffff;
        color: #6b8c7c;
        border: 1px solid #cbdcd0;
        border-radius: 32px;
        padding: 0.5rem 1.2rem;
        font-weight: 500;
        transition: 0.2s;
        font-family: 'Noto Serif SC', serif;
    }
    div.stButton > button:hover {
        background-color: #6b8c7c;
        color: white;
        border-color: #6b8c7c;
    }
    /* 聊天输入框 */
    .stChatInput input {
        border-radius: 32px;
        border: 1px solid #dbcebc;
        background-color: #fffcf5;
    }
    /* 侧边栏 */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #fff8ef 0%, #fdf5e6 100%);
        border-right: 1px solid #ede3d5;
        font-family: 'Noto Serif SC', serif;
    }
</style>
""", unsafe_allow_html=True)

# ==================== 加载 POI 数据（同原逻辑） ====================
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

# ==================== URL 参数与 Session 初始化 ====================
if "participant_id" not in st.session_state:
    st.session_state.participant_id = st.query_params.get("pid", "P_TEST_USER")

# 实验组别（A/B/C）分配
if "group" not in st.session_state:
    hash_val = int(hashlib.md5(st.session_state.participant_id.encode()).hexdigest()[:4], 16)
    group_map = ["A", "B", "C"]
    st.session_state.group = group_map[hash_val % 3]

# 条件映射（5 个 POI 依次分配 A/B/C 条件）
group_condition_map = {
    "A": ["baseline", "free_text", "recchatbox", "baseline", "free_text"],
    "B": ["free_text", "recchatbox", "baseline", "free_text", "recchatbox"],
    "C": ["recchatbox", "baseline", "free_text", "recchatbox", "baseline"]
}
condition_sequence = group_condition_map[st.session_state.group]

# 当前 POI 索引
if "current_poi_index" not in st.session_state:
    current_poi_key = st.query_params.get("poi", POI_ORDER[0])
    st.session_state.current_poi_index = POI_ORDER.index(current_poi_key) if current_poi_key in POI_ORDER else 0
else:
    url_poi = st.query_params.get("poi")
    if url_poi and url_poi in POI_ORDER and POI_ORDER.index(url_poi) != st.session_state.current_poi_index:
        st.session_state.current_poi_index = POI_ORDER.index(url_poi)
        # POI 切换时重置聊天状态
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

# 其他 Session 状态
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

# ==================== 日志函数（修复 Supabase 数据写入） ====================
def log_experimental_event(action_type, query_text="", response_time=0.0, retrieved_chunks="", displayed_source_cue=""):
    time_on_page = time.time() - st.session_state.page_load_time
    # 使用 UTC+8（北京时间）修正时间戳偏差
    utc_time = datetime.now(timezone.utc)
    beijing_time = utc_time + timedelta(hours=8)
    event_data = {
        "participant_id": str(st.session_state.participant_id),
        "experimental_condition": current_condition,
        "poi_id": str(current_poi_key),
        "action_type": str(action_type),
        "time_on_page_seconds": round(time_on_page, 2),
        "user_query_text": str(query_text),
        "user_query_word_count": len(query_text),
        "rag_response_time_ms": round(response_time * 1000, 1),
        "retrieved_chunks_saved": str(retrieved_chunks),
        "displayed_source_cue": str(displayed_source_cue),
        "timestamp": beijing_time.isoformat()
    }
    st.session_state.logs.append(event_data)
    df = pd.DataFrame(st.session_state.logs)
    os.makedirs("logs", exist_ok=True)
    df.to_csv("logs/interaction_log.csv", index=False, encoding="utf-8-sig")
    try:
        # 关键修复：加 returning='minimal' 避免隐式 SELECT 触发 RLS 报错
        st.session_state.supabase.table("interaction_logs").insert(event_data, returning='minimal').execute()
    except Exception as e:
        st.toast(f"⚠️ 数据同步失败，本地已备份: {str(e)[:100]}", icon="⚠️")

# 页面首次加载埋点
if f"loaded_{current_poi_key}" not in st.session_state:
    st.session_state[f"loaded_{current_poi_key}"] = True
    log_experimental_event("page_loaded")

# ==================== Dify RAG 函数（优化推理速度） ====================
def simulate_rag_engine(user_query):
    start = time.time()
    url = "https://api.dify.ai/v1/chat-messages"
    # 主应用 API Key
    key = "Bearer app-rzITs8smrzMUhhdraDriLuRp"
    payload = {
        "inputs": {"current_poi": current_poi["name"]},
        "query": user_query,
        "response_mode": "blocking",
        "user": st.session_state.participant_id
    }
    headers = {"Authorization": key, "Content-Type": "application/json"}
    # 移除多次重试，只做单次快速请求
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
        return "【网络或服务异常】请稍后重试。", "故障降级", "[Error]", elapsed

# ==================== 生成推荐问题（修复仅显示两个的问题） ====================
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

# ==================== 处理用户提问 ====================
def handle_question(question):
    with st.spinner("AI 导览员正在查阅史料..."):
        ans, src, chunks, elapsed = simulate_rag_engine(question)
        st.session_state.chat_messages.append({"role": "user", "content": question})
        st.session_state.chat_messages.append({"role": "assistant", "content": ans, "source": src})
        log_experimental_event("question_submitted", question, elapsed, chunks, src)
        if actual_render == "recchatbox":
            st.session_state.followup_questions = generate_followup_questions(question, ans)
        else:
            st.session_state.followup_questions = []
        st.rerun()

# ==================== 侧边栏（支持手动切换点位） ====================
st.sidebar.markdown(f"**参与者 ID**：`{st.session_state.participant_id}`")
st.sidebar.markdown(f"**所属组别**：Group {st.session_state.group}")
st.sidebar.markdown(f"**当前体验**：{display_condition_name}")
st.sidebar.markdown(f"**进度**：{st.session_state.current_poi_index+1}/{len(POI_ORDER)}")
st.sidebar.markdown("---")
st.sidebar.markdown("### 🏮 游览路线")

for idx, pid in enumerate(POI_ORDER):
    icon = "📍" if pid == current_poi_key else "▪️"
    poi_name = POI_NAMES[pid]
    if st.sidebar.button(f"{icon} {poi_name}", key=f"nav_{pid}"):
        if idx != st.session_state.current_poi_index:
            st.session_state.current_poi_index = idx
            # 重置聊天状态，避免上一个点位的问题残留
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
st.title(f"🏯 {current_poi['name']}")
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
