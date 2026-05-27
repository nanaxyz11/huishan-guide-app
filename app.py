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

# ==================== 页面配置（非遗文化风格） ====================
st.set_page_config(page_title="惠山古镇 AI 导览 | 非遗数字体验", layout="centered", initial_sidebar_state="collapsed")

# 自定义 CSS：仿古书卷风格
st.markdown("""
<style>
    /* 全局背景与字体 */
    .stApp {
        background-color: #fef7e8;
        font-family: 'Georgia', '宋体', 'Microsoft YaHei', serif;
    }
    /* 主容器圆角与阴影 */
    .main > div {
        background-color: #fffaf2;
        border-radius: 24px;
        padding: 1.5rem;
        box-shadow: 0 8px 20px rgba(0,0,0,0.05);
        border: 1px solid #e4d5c0;
    }
    /* 景点概览卡片 */
    .poi-card {
        background: #fef3e4;
        border-left: 6px solid #b76e3e;
        padding: 1rem;
        border-radius: 16px;
        margin: 1rem 0;
        font-size: 1.05rem;
        line-height: 1.5;
        color: #3e2a1f;
    }
    /* 来源 chip */
    .source-chip {
        display: inline-block;
        background-color: #e8e0d5;
        color: #7a5b3e;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 500;
        margin-top: 8px;
        font-family: monospace;
    }
    /* 按钮美化 */
    .stButton button {
        background-color: #b76e3e;
        color: white;
        border: none;
        border-radius: 32px;
        padding: 0.5rem 1.2rem;
        transition: 0.2s;
    }
    .stButton button:hover {
        background-color: #965a32;
        color: #fff;
    }
    /* 聊天输入框圆润 */
    .stChatInput input {
        border-radius: 32px;
        border: 1px solid #ddd0c0;
        background-color: #fffcf5;
    }
    /* 侧边栏 */
    [data-testid="stSidebar"] {
        background-color: #fcf5ea;
        border-right: 1px solid #eeddcc;
    }
</style>
""", unsafe_allow_html=True)

# ==================== 加载POI知识库 ====================
@st.cache_data
def load_poi_data():
    with open("data/poi_content.json", "r", encoding="utf-8") as f:
        return json.load(f)

poi_database = load_poi_data()

# 固定的POI游览顺序（共5个，键名必须与JSON中的键一致）
POI_ORDER = ["fanwenzheng_gongci", "guhuashanmen", "bayinjian", "zhulu_shanfang", "erquan"]
POI_NAMES = {pid: poi_database[pid]["name"] for pid in POI_ORDER if pid in poi_database}

# ==================== URL 参数解析 ====================
query_params = st.query_params
participant_id = query_params.get("pid", "P_TEST_USER")
# condition 不再从URL传入，而是由下面的分配函数决定
# 但是需要读取当前的 poi 参数，如果不存在则默认第一个
current_poi_key = query_params.get("poi", POI_ORDER[0])
if current_poi_key not in POI_ORDER:
    st.error("POI不存在，请重试。")
    st.stop()
current_poi = poi_database[current_poi_key]

# ==================== 被试内条件分配（基于participant_id确定性随机） ====================
def assign_conditions_for_user(pid):
    """为5个POI分配条件 (baseline/free_text/recchatbox)，确保每个条件至少1次，最多2次"""
    # 使用哈希保证同一用户每次分配一致
    seed = int(hashlib.md5(pid.encode()).hexdigest()[:8], 16)
    r = random.Random(seed)
    # 创建5个位置的条件列表，保证三个条件各至少1次，剩余2个位置补全（使得总数为5）
    base_conditions = ["baseline", "free_text", "recchatbox"]
    # 剩余两个位置从三个条件中随机选（可能重复）
    remaining = r.choices(base_conditions, k=2)
    full_conditions = base_conditions + remaining
    r.shuffle(full_conditions)  # 随机打乱顺序
    # 将条件与POI_ORDER对应
    assignment = {poi_id: cond for poi_id, cond in zip(POI_ORDER, full_conditions)}
    return assignment

if "condition_assignment" not in st.session_state:
    st.session_state.condition_assignment = assign_conditions_for_user(participant_id)

# 获取当前POI对应的实验条件
current_condition = st.session_state.condition_assignment[current_poi_key]

# 根据条件确定显示名称和实际渲染类型
if current_condition == "baseline":
    display_condition_name = "传统静态网页 (Baseline)"
    actual_render = "baseline"
elif current_condition == "free_text":
    display_condition_name = "自由提问 RAG (Free-Text)"
    actual_render = "free_text"
else:  # recchatbox
    display_condition_name = "智能推荐对话 (RecChatbox)"
    actual_render = "recchatbox"

# ==================== Session状态初始化 ====================
if "logs" not in st.session_state:
    st.session_state.logs = []
if "page_load_time" not in st.session_state:
    st.session_state.page_load_time = time.time()
if "ai_response" not in st.session_state:
    st.session_state.ai_response = None
if "followup_questions" not in st.session_state:
    st.session_state.followup_questions = []
if "chat_messages" not in st.session_state:
    # 仅当不是 baseline 时才需要聊天历史
    st.session_state.chat_messages = []
    # 如果是条件 free_text 或 recchatbox 且尚无消息，显示欢迎语
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
    query_length = len(query_text) if query_text else 0

    event_data = {
        "participant_id": str(participant_id),
        "experimental_condition": current_condition,   # 记录实际分配的条件
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
        st.toast(f"⚠️ 数据同步失败，但本地已备份: {str(e)[:100]}", icon="⚠️")

# 页面加载日志（仅记录一次）
if f"loaded_{current_poi_key}" not in st.session_state:
    st.session_state[f"loaded_{current_poi_key}"] = True
    log_experimental_event(action_type="page_loaded")

# ==================== Dify RAG 函数（与原来一致） ====================
def simulate_rag_engine(user_query):
    start_time = time.time()
    DIFY_API_URL = "https://api.dify.ai/v1/chat-messages"
    DIFY_API_KEY = "Bearer app-rzITs8smrzMUhhdraDriLuRp"
    payload = {
        "inputs": {"current_poi": current_poi["name"]},
        "query": user_query,
        "response_mode": "blocking",
        "user": participant_id
    }
    headers = {"Authorization": DIFY_API_KEY, "Content-Type": "application/json"}
    session = requests.Session()
    retry_strategy = Retry(total=3, backoff_factor=1, status_forcelist=[500,502,503,504], allowed_methods=["POST"])
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    try:
        resp = session.post(DIFY_API_URL, json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        answer = data.get("answer", "抱歉，暂时无法回答。")
        resources = data.get("metadata", {}).get("retriever_resources", [])
        if resources:
            src = resources[0].get("dataset_name", "无锡史志库")
            source_display = f"官方数字认证：{src}"
            chunks_saved = str(resources)
        else:
            source_display = "惠山古镇文献库"
            chunks_saved = "[通用生成]"
        elapsed = time.time() - start_time
        return answer, source_display, chunks_saved, elapsed
    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        return "【网络超时】请重试", "超时降级", "[Timeout]", elapsed
    except Exception as e:
        elapsed = time.time() - start_time
        return f"【服务异常】{str(e)[:50]}", "故障降级", "[Error]", elapsed

def generate_followup_questions(question, answer):
    FOLLOWUP_API_URL = "https://api.dify.ai/v1/chat-messages"
    FOLLOWUP_API_KEY = "Bearer app-CCck7NxI8NLZIxf24Q247Hti"
    prompt = f"用户问题：{question}\nAI回答：{answer}\n请根据以上内容，生成3个与文化遗产相关的、引导用户继续深入探索的后续问题。每个问题一行，不要序号。"
    try:
        resp = requests.post(FOLLOWUP_API_URL, json={"inputs":{},"query":prompt,"response_mode":"blocking","user":participant_id},
                             headers={"Authorization": FOLLOWUP_API_KEY, "Content-Type":"application/json"}, timeout=10)
        content = resp.json().get("answer","")
        lines = [line.strip() for line in content.split("\n") if line.strip()][:3]
        while len(lines) < 3:
            lines.append("您还想了解更多吗？")
        return lines
    except:
        return ["这个景点还有什么故事？", "这里发生过什么重大事件？", "建筑风格有什么特别之处？"]

def handle_question(question):
    with st.spinner("AI 导览员正在查阅史料..."):
        answer, source, chunks, elapsed = simulate_rag_engine(question)
        st.session_state.chat_messages.append({"role": "user", "content": question})
        st.session_state.chat_messages.append({"role": "assistant", "content": answer, "source": source})
        log_experimental_event("question_submitted", question, elapsed, chunks, source)
        if actual_render == "recchatbox":
            followups = generate_followup_questions(question, answer)
            st.session_state.followup_questions = followups
        else:
            st.session_state.followup_questions = []
        st.rerun()

# ==================== 前端界面 ====================
# 侧边栏显示实验信息
st.sidebar.markdown("## 🏮 实验信息")
st.sidebar.markdown(f"**参与者 ID**：`{participant_id}`")
st.sidebar.markdown(f"**当前体验条件**：{display_condition_name}")
st.sidebar.markdown(f"**进度**：{POI_ORDER.index(current_poi_key)+1} / {len(POI_ORDER)} 个点位")
st.sidebar.markdown("---")
st.sidebar.markdown("### 📜 游览路线")
for idx, pid in enumerate(POI_ORDER):
    icon = "📍" if pid == current_poi_key else "🔲"
    st.sidebar.markdown(f"{icon} {POI_NAMES.get(pid, pid)}")

# 主区显示当前POI概览
st.title(f"🏯 {current_poi['name']}")
st.markdown(f'<div class="poi-card">{current_poi["info"]}</div>', unsafe_allow_html=True)
if "image_url" in current_poi:
    st.image(current_poi["image_url"], use_container_width=True)

if actual_render == "baseline":
    # 无聊天功能，只显示静态内容
    st.markdown("*（静态展示模式）*")
    st.caption("数据来源：无锡市文化遗产局官网")
else:
    # 显示聊天历史
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and "source" in msg:
                st.markdown(f'<span class="source-chip">🔍 {msg["source"]}</span>', unsafe_allow_html=True)
    # 推荐问题（仅当 recchatbox 且存在时显示）
    if actual_render == "recchatbox" and st.session_state.followup_questions:
        st.markdown("#### 💬 相关问题推荐")
        cols = st.columns(3)
        for i, q in enumerate(st.session_state.followup_questions):
            with cols[i % 3]:
                if st.button(f"❓ {q}", key=f"followup_{i}"):
                    handle_question(q)
    # 底部输入框
    if prompt := st.chat_input("输入您的问题..."):
        handle_question(prompt)

st.markdown("---")
# 下一站按钮
current_index = POI_ORDER.index(current_poi_key)
if current_index + 1 < len(POI_ORDER):
    next_poi = POI_ORDER[current_index + 1]
    if st.button("✅ 我已游览完当前点位，前往下一站", use_container_width=True):
        # 记录当前点位完成事件
        log_experimental_event("completed")
        # 更新 URL 参数，只改变 poi，保留 pid
        st.query_params["poi"] = next_poi
        st.query_params["pid"] = participant_id
        st.rerun()
else:
    st.success("🎉 恭喜您完成全部 5 个点位的文化探索！")
    if st.button("📤 完成实验，提交数据"):
        log_experimental_event("all_completed")
        st.markdown("请关闭页面并返回问卷平台。")

st.sidebar.markdown("---")
if st.sidebar.button("导出本次会话日志 (CSV)"):
    if st.session_state.logs:
        df = pd.DataFrame(st.session_state.logs)
        st.sidebar.download_button("下载 CSV", data=df.to_csv(index=False), file_name=f"{participant_id}_logs.csv")
