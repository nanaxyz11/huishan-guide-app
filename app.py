import streamlit as st
import json
import os
import time
import hashlib
import random
from datetime import datetime
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from supabase import create_client

st.set_page_config(page_title="惠山古镇 AI 导览 | 非遗数字体验", layout="centered", initial_sidebar_state="collapsed")

# 非遗风格 CSS（略，与之前相同，可复用）
st.markdown("""
<style>
    .stApp { background-color: #fef7e8; font-family: 'Georgia', '宋体', serif; }
    .main > div { background-color: #fffaf2; border-radius: 24px; padding: 1.5rem; box-shadow: 0 8px 20px rgba(0,0,0,0.05); border: 1px solid #e4d5c0; }
    .poi-card { background: #fef3e4; border-left: 6px solid #b76e3e; padding: 1rem; border-radius: 16px; margin: 1rem 0; font-size: 1.05rem; line-height: 1.5; color: #3e2a1f; }
    .source-chip { display: inline-block; background-color: #e8e0d5; color: #7a5b3e; padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 500; margin-top: 8px; }
    .stButton button { background-color: #b76e3e; color: white; border-radius: 32px; padding: 0.5rem 1.2rem; }
    .stButton button:hover { background-color: #965a32; }
    .stChatInput input { border-radius: 32px; border: 1px solid #ddd0c0; background-color: #fffcf5; }
    [data-testid="stSidebar"] { background-color: #fcf5ea; border-right: 1px solid #eeddcc; }
</style>
""", unsafe_allow_html=True)

# ==================== 加载 POI 知识库（带错误处理） ====================
@st.cache_data
def load_poi_data():
    json_path = "data/poi_content.json"
    if not os.path.exists(json_path):
        st.error(f"❌ 找不到文件：{json_path}。请确保文件存在。")
        st.stop()
    with open(json_path, "r", encoding="utf-8") as f:
        content = f.read()
        # 尝试修复尾部多余逗号（常见错误）
        import re
        content = re.sub(r',\s*}', '}', content)  # 移除对象最后一个逗号
        content = re.sub(r',\s*]', ']', content)  # 移除数组最后一个逗号
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            st.error(f"JSON 解析错误：{e}\n请用 JSON 验证器检查文件格式。")
            st.stop()
    return data

poi_database = load_poi_data()
expected_pois = ["fanwenzheng_gongci", "guhuashanmen", "bayinjian", "zhulu_shanfang", "erquan"]
missing = [p for p in expected_pois if p not in poi_database]
if missing:
    st.error(f"❌ POI 数据库中缺少以下键：{missing}\n请检查 JSON 文件中的键名是否正确。")
    st.stop()

POI_ORDER = expected_pois
POI_NAMES = {pid: poi_database[pid]["name"] for pid in POI_ORDER}

# ==================== URL 参数 ====================
query_params = st.query_params
participant_id = query_params.get("pid", "P_TEST_USER")
current_poi_key = query_params.get("poi", POI_ORDER[0])
if current_poi_key not in POI_ORDER:
    st.error(f"无效的 POI：{current_poi_key}。自动重置为第一个。")
    current_poi_key = POI_ORDER[0]
current_poi = poi_database[current_poi_key]

# ==================== 被试内条件分配 ====================
def assign_conditions_for_user(pid):
    seed = int(hashlib.md5(pid.encode()).hexdigest()[:8], 16)
    r = random.Random(seed)
    base = ["baseline", "free_text", "recchatbox"]
    remaining = r.choices(base, k=2)
    full = base + remaining
    r.shuffle(full)
    return {poi: cond for poi, cond in zip(POI_ORDER, full)}

if "condition_assignment" not in st.session_state:
    st.session_state.condition_assignment = assign_conditions_for_user(participant_id)

current_condition = st.session_state.condition_assignment[current_poi_key]
if current_condition == "baseline":
    actual_render = "baseline"
    display_condition_name = "传统静态网页"
elif current_condition == "free_text":
    actual_render = "free_text"
    display_condition_name = "自由提问 RAG"
else:
    actual_render = "recchatbox"
    display_condition_name = "智能推荐对话"

# ==================== Session 初始化 ====================
if "logs" not in st.session_state:
    st.session_state.logs = []
if "page_load_time" not in st.session_state:
    st.session_state.page_load_time = time.time()
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "followup_questions" not in st.session_state:
    st.session_state.followup_questions = []
if actual_render != "baseline" and not st.session_state.chat_messages:
    st.session_state.chat_messages = [
        {"role": "assistant", "content": f"您好！欢迎来到【{current_poi['name']}】。您可以问我任何关于这个古迹的问题。"}
    ]

if "supabase" not in st.session_state:
    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_KEY"]
    st.session_state.supabase = create_client(supabase_url, supabase_key)

# ==================== 日志函数 ====================
def log_experimental_event(action_type, query_text="", response_time=0.0, retrieved_chunks="", displayed_source_cue=""):
    time_on_page = time.time() - st.session_state.page_load_time
    event_data = {
        "participant_id": str(participant_id),
        "experimental_condition": current_condition,
        "poi_id": str(current_poi_key),
        "action_type": str(action_type),
        "time_on_page_seconds": round(time_on_page, 2),
        "user_query_text": str(query_text),
        "user_query_word_count": len(query_text),
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
        st.toast(f"⚠️ 数据同步失败，本地已备份: {str(e)[:100]}", icon="⚠️")

if f"loaded_{current_poi_key}" not in st.session_state:
    st.session_state[f"loaded_{current_poi_key}"] = True
    log_experimental_event("page_loaded")

# ==================== Dify RAG 函数 ====================
def simulate_rag_engine(user_query):
    start = time.time()
    url = "https://api.dify.ai/v1/chat-messages"
    key = "Bearer app-rzITs8smrzMUhhdraDriLuRp"
    payload = {"inputs": {"current_poi": current_poi["name"]}, "query": user_query, "response_mode": "blocking", "user": participant_id}
    headers = {"Authorization": key, "Content-Type": "application/json"}
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500,502,503,504])
    session.mount("https://", HTTPAdapter(max_retries=retries))
    try:
        resp = session.post(url, json=payload, headers=headers, timeout=15)
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
    except:
        elapsed = time.time() - start
        return "【网络或服务异常】请稍后重试。", "故障降级", "[Error]", elapsed

def generate_followups(question, answer):
    url = "https://api.dify.ai/v1/chat-messages"
    key = "Bearer app-CCck7NxI8NLZIxf24Q247Hti"
    prompt = f"用户问题：{question}\nAI回答：{answer}\n生成3个文化遗产相关的后续问题，每行一个。"
    try:
        resp = requests.post(url, json={"inputs":{},"query":prompt,"response_mode":"blocking","user":participant_id},
                             headers={"Authorization":key,"Content-Type":"application/json"}, timeout=10)
        lines = resp.json().get("answer","").strip().split("\n")[:3]
        while len(lines) < 3:
            lines.append("您还想了解更多吗？")
        return [l.strip() for l in lines]
    except:
        return ["这个景点还有什么故事？", "这里发生过什么重大事件？", "建筑风格有什么特别之处？"]

def handle_question(question):
    with st.spinner("AI 导览员正在查阅史料..."):
        ans, src, chunks, elapsed = simulate_rag_engine(question)
        st.session_state.chat_messages.append({"role": "user", "content": question})
        st.session_state.chat_messages.append({"role": "assistant", "content": ans, "source": src})
        log_experimental_event("question_submitted", question, elapsed, chunks, src)
        if actual_render == "recchatbox":
            st.session_state.followup_questions = generate_followups(question, ans)
        else:
            st.session_state.followup_questions = []
        st.rerun()

# ==================== UI 渲染 ====================
st.sidebar.markdown(f"**参与者 ID**：`{participant_id}`")
st.sidebar.markdown(f"**当前体验**：{display_condition_name}")
st.sidebar.markdown(f"**进度**：{POI_ORDER.index(current_poi_key)+1}/{len(POI_ORDER)}")
st.sidebar.markdown("**游览路线**")
for idx, pid in enumerate(POI_ORDER):
    icon = "📍" if pid == current_poi_key else "🔲"
    st.sidebar.markdown(f"{icon} {POI_NAMES[pid]}")

st.title(f"🏯 {current_poi['name']}")
st.markdown(f'<div class="poi-card">{current_poi["info"]}</div>', unsafe_allow_html=True)

if actual_render == "baseline":
    st.caption("静态展示模式 · 无 AI 对话")
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
current_idx = POI_ORDER.index(current_poi_key)
if current_idx + 1 < len(POI_ORDER):
    next_poi = POI_ORDER[current_idx + 1]
    if st.button("✅ 我已游览完当前点位，前往下一站", use_container_width=True):
        log_experimental_event("completed")
        st.query_params["poi"] = next_poi
        st.query_params["pid"] = participant_id
        st.rerun()
else:
    st.success("🎉 恭喜您完成全部点位！")
    if st.button("📤 完成实验，提交数据"):
        log_experimental_event("all_completed")
        st.markdown("请关闭页面并返回问卷。")
