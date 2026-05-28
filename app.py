import streamlit as st
import json
import os
import time
import hashlib
import random
from datetime import datetime, timezone, timedelta
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from supabase import create_client

# ==================== 页面配置 ====================
st.set_page_config(page_title="惠山古镇 AI 导览 | 非遗数字体验", layout="centered", initial_sidebar_state="expanded")

# ==================== 更新 CSS ====================
st.markdown("""
<style>
    /* 全局江南水墨风 */
    .stApp {
        background: linear-gradient(145deg, #fdfbf7 0%, #f9f5eb 100%);
        font-family: 'Georgia', 'Songti SC', 'Source Serif Pro', serif;
    }
    /* 主容器 */
    .main > div {
        background-color: rgba(255, 250, 240, 0.92);
        border-radius: 0px 16px 16px 0px;
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
        font-family: 'Songti SC', serif;
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
        font-family: 'Songti SC', serif;
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
        font-family: 'Songti SC', serif;
    }
    /* 侧边栏链接样式 */
    .sidebar-poi-link {
        display: block;
        padding: 6px 12px;
        margin: 4px 0;
        border-radius: 20px;
        background: transparent;
        color: #6e5c44;
        text-decoration: none;
        transition: 0.2s;
        cursor: pointer;
        font-size: 0.9rem;
    }
    .sidebar-poi-link:hover, .sidebar-poi-link.active {
        background: #e8dfd0;
        color: #6b8c7c;
    }
</style>
""", unsafe_allow_html=True)

# ==================== 1. 加载POI数据（带错误处理） ====================
@st.cache_data
def load_poi_data():
    json_path = "data/poi_content.json"
    if not os.path.exists(json_path):
        st.error(f"❌ 找不到文件：{json_path}。请确保文件存在。")
        st.stop()
    with open(json_path, "r", encoding="utf-8") as f:
        content = f.read()
        import re
        content = re.sub(r',\s*}', '}', content)
        content = re.sub(r',\s*]', ']', content)
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

# ==================== 2. URL参数与Session初始化 ====================
if "participant_id" not in st.session_state:
    st.session_state.participant_id = st.query_params.get("pid", "P_TEST_USER")
if "group" not in st.session_state:
    # 伪随机分组（A/B/C），结合pid确保稳定
    hash_val = int(hashlib.md5(st.session_state.participant_id.encode()).hexdigest()[:4], 16)
    group_map = ["A", "B", "C"]
    st.session_state.group = group_map[hash_val % 3]

# 根据组别映射对应的条件顺序（5个POI依次使用不同条件）
group_condition_map = {
    "A": ["baseline", "free_text", "recchatbox", "baseline", "free_text"],
    "B": ["free_text", "recchatbox", "baseline", "free_text", "recchatbox"],
    "C": ["recchatbox", "baseline", "free_text", "recchatbox", "baseline"]
}
condition_sequence = group_condition_map[st.session_state.group]

# 当前POI索引
if "current_poi_index" not in st.session_state:
    current_poi_key = st.query_params.get("poi", POI_ORDER[0])
    if current_poi_key in POI_ORDER:
        st.session_state.current_poi_index = POI_ORDER.index(current_poi_key)
    else:
        st.session_state.current_poi_index = 0
else:
    # 确保与URL同步
    url_poi = st.query_params.get("poi")
    if url_poi and url_poi in POI_ORDER and POI_ORDER.index(url_poi) != st.session_state.current_poi_index:
        st.session_state.current_poi_index = POI_ORDER.index(url_poi)

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

# ==================== 3. Session状态初始化 ====================
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
    try:
        supabase_url = st.secrets["SUPABASE_URL"]
        supabase_key = st.secrets["SUPABASE_KEY"]
        st.session_state.supabase = create_client(supabase_url, supabase_key)
    except Exception as e:
        st.error(f"Supabase 连接失败：{e}")
        st.stop()

# ==================== 4. 日志函数（修正时间戳） ====================
def log_experimental_event(action_type, query_text="", response_time=0.0, retrieved_chunks="", displayed_source_cue=""):
    time_on_page = time.time() - st.session_state.page_load_time
    # 修正时间戳：使用UTC+8（北京时间）
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
        st.session_state.supabase.table("interaction_logs").insert(event_data).execute()
    except Exception as e:
        st.toast(f"⚠️ 数据同步失败，本地已备份: {str(e)[:100]}", icon="⚠️")

if f"loaded_{current_poi_key}" not in st.session_state:
    st.session_state[f"loaded_{current_poi_key}"] = True
    log_experimental_event("page_loaded")

# ==================== 5. Dify RAG 函数（保持不变） ====================
def simulate_rag_engine(user_query):
    start = time.time()
    url = "https://api.dify.ai/v1/chat-messages"
    key = "Bearer app-rzITs8smrzMUhhdraDriLuRp"
    payload = {"inputs": {"current_poi": current_poi["name"]}, "query": user_query, "response_mode": "blocking", "user": st.session_state.participant_id}
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
    except Exception:
        elapsed = time.time() - start
        return "【网络或服务异常】请稍后重试。", "故障降级", "[Error]", elapsed

def generate_followups(question, answer):
    url = "https://api.dify.ai/v1/chat-messages"
    key = "Bearer app-CCck7NxI8NLZIxf24Q247Hti"
    prompt = f"用户问题：{question}\nAI回答：{answer}\n生成3个文化遗产相关的后续问题，每行一个。"
    try:
        resp = requests.post(url, json={"inputs":{},"query":prompt,"response_mode":"blocking","user":st.session_state.participant_id},
                             headers={"Authorization":key,"Content-Type":"application/json"}, timeout=10)
        lines = resp.json().get("answer","").strip().split("\n")[:3]
        while len(lines) < 3:
            lines.append("您还想了解更多吗？")
        return [l.strip() for l in lines]
    except Exception:
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

# ==================== 6. 侧边栏（含手动切换） ====================
st.sidebar.markdown(f"**参与者 ID**：`{st.session_state.participant_id}`")
st.sidebar.markdown(f"**所属组别**：Group {st.session_state.group}")
st.sidebar.markdown(f"**当前体验**：{display_condition_name}")
st.sidebar.markdown(f"**进度**：{st.session_state.current_poi_index+1}/{len(POI_ORDER)}")
st.sidebar.markdown("---")
st.sidebar.markdown("### 🏮 游览路线")

# 手动切换POI
for idx, pid in enumerate(POI_ORDER):
    icon = "📍" if pid == current_poi_key else "▪️"
    poi_name = POI_NAMES[pid]
    if st.sidebar.button(f"{icon} {poi_name}", key=f"nav_{pid}"):
        # 更新索引
        if idx != st.session_state.current_poi_index:
            st.session_state.current_poi_index = idx
            # 更新URL参数（可选）
            st.query_params["poi"] = pid
            st.query_params["pid"] = st.session_state.participant_id
            st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("📥 导出日志 CSV"):
    if st.session_state.logs:
        df = pd.DataFrame(st.session_state.logs)
        st.sidebar.download_button("点击下载", data=df.to_csv(index=False), file_name=f"{st.session_state.participant_id}_logs.csv")

# ==================== 7. 主界面渲染 ====================
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
        # 记录点位完成事件
        log_experimental_event("completed")
        # 记录步行时间：上一站到下一站的间隔（下次计算时会用到）
        st.session_state.last_completed_time = time.time()
        st.session_state.current_poi_index += 1
        st.query_params["poi"] = next_poi
        st.query_params["pid"] = st.session_state.participant_id
        st.rerun()
else:
    st.success("🎉 恭喜您完成全部 5 个点位的文化探索！")
    if st.button("📤 完成实验，提交数据", use_container_width=True):
        log_experimental_event("all_completed")
        st.markdown("请关闭页面并返回问卷。")
