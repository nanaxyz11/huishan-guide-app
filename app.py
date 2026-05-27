import streamlit as st
import json
import os
import time
import re
from datetime import datetime
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from supabase import create_client

# ==================== 页面配置 ====================
st.set_page_config(page_title="惠山古镇 AI 导览实验平台", layout="centered", initial_sidebar_state="collapsed")

# ==================== DeepSeek 风格 CSS ====================
st.markdown("""
    <style>
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .main .block-container {
        padding: 1rem 1rem 6rem 1rem;
        max-width: 800px;
    }
    .stApp {
        background-color: #f7f7f8;
        font-family: 'Segoe UI', 'Roboto', sans-serif;
    }
    [data-testid="stChatMessage"][data-testid*="user"] {
        background-color: #ffffff;
        border: 1px solid #e5e5e5;
        border-radius: 18px;
        padding: 8px 16px;
        margin: 10px 0;
        box-shadow: 0 1px 1px rgba(0,0,0,0.05);
    }
    [data-testid="stChatMessage"][data-testid*="assistant"] {
        background-color: #f0f0f0;
        border-radius: 18px;
        padding: 8px 16px;
        margin: 10px 0;
    }
    .source-chip {
        display: inline-flex;
        align-items: center;
        background-color: #e8f0fe;
        color: #1a73e8;
        padding: 4px 10px;
        border-radius: 16px;
        font-size: 12px;
        font-weight: 500;
        margin-top: 8px;
        border: 1px solid #d2e3fc;
    }
    .stChatInput {
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        width: 90%;
        max-width: 760px;
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 32px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        z-index: 99;
    }
    </style>
""", unsafe_allow_html=True)

# ==================== 加载本地知识库 ====================
@st.cache_data
def load_poi_data():
    with open("data/poi_content.json", "r", encoding="utf-8") as f:
        return json.load(f)

poi_database = load_poi_data()

# ==================== URL 参数解析与自动跳转（安全版本） ====================
query_params = st.query_params

# 1. 先获取原始参数（可能为空）
raw_pid = query_params.get("pid", "P_TEST_USER")
raw_condition = query_params.get("condition", "")
raw_poi_id = query_params.get("poi", "erquan").lower()

# 2. 自动跳转逻辑：如果 condition 参数不存在，则自动补全为 free_text
if not raw_condition:
    # 防止无限循环，使用 session_state 标记
    if "redirect_done" not in st.session_state:
        # 构造新参数：保留原有 pid 和 poi，添加 condition=free_text
        new_params = dict(query_params)
        new_params["condition"] = "free_text"
        st.query_params.update(new_params)
        st.session_state.redirect_done = True
        st.rerun()
    else:
        # 如果已经跳转过但 condition 仍为空，强行设置
        raw_condition = "free_text"
else:
    raw_condition = raw_condition.lower()

# 3. 最终使用的参数
participant_id = raw_pid
condition = raw_condition if raw_condition else "free_text"
poi_id = raw_poi_id

# 4. 验证 POI 并获取 current_poi（确保总是存在）
if poi_id not in poi_database:
    st.error(f"POI ID '{poi_id}' 不存在，将使用默认景点 'erquan'。")
    poi_id = "erquan"
current_poi = poi_database[poi_id]

# ==================== Session 状态初始化 ====================
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []
if "page_load_time" not in st.session_state:
    st.session_state.page_load_time = time.time()
if "logs" not in st.session_state:
    st.session_state.logs = []
if "followup_questions" not in st.session_state:
    st.session_state.followup_questions = []
if "ai_response" not in st.session_state:
    st.session_state.ai_response = None
if "supabase" not in st.session_state:
    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_KEY"]
    st.session_state.supabase = create_client(supabase_url, supabase_key)

# ==================== 日志记录 ====================
def log_experimental_event(action_type, query_text="", response_time=0.0, retrieved_chunks="", displayed_source_cue=""):
    time_on_page = time.time() - st.session_state.page_load_time
    query_length = len(query_text) if query_text else 0

    event_data = {
        "participant_id": str(participant_id),
        "experimental_condition": str(condition),
        "poi_id": str(poi_id),
        "action_type": str(action_type),
        "time_on_page_seconds": round(time_on_page, 2),
        "user_query_text": str(query_text),
        "user_query_word_count": query_length,
        "rag_response_time_ms": round(response_time * 1000, 1),
        "retrieved_chunks_saved": str(retrieved_chunks),
        "displayed_source_cue": str(displayed_source_cue),
        "timestamp": datetime.now().isoformat()
    }

    # 本地 CSV 备份
    st.session_state.logs.append(event_data)
    df = pd.DataFrame(st.session_state.logs)
    log_file = "logs/interaction_log.csv"
    os.makedirs("logs", exist_ok=True)
    if not os.path.isfile(log_file):
        df.to_csv(log_file, index=False, encoding="utf-8-sig")
    else:
        df.to_csv(log_file, mode='a', header=False, index=False, encoding="utf-8-sig")

    # 写入 Supabase（错误仅打印，不影响前端）
    try:
        st.session_state.supabase.table("interaction_logs").insert(event_data).execute()
    except Exception as e:
        print(f"[Supabase Error] {e}")
        # 不向用户显示错误，避免干扰体验

# 页面加载埋点
if f"loaded_{poi_id}" not in st.session_state:
    st.session_state[f"loaded_{poi_id}"] = True
    log_experimental_event(action_type="page_loaded")

# ==================== Dify RAG 函数 ====================
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
    headers = {
        "Authorization": DIFY_API_KEY,
        "Content-Type": "application/json"
    }

    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    try:
        response = session.post(DIFY_API_URL, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        res_json = response.json()
        answer = res_json.get("answer", "系统响应异常，请重试。")
        retriever_resources = res_json.get("metadata", {}).get("retriever_resources", [])
        if retriever_resources:
            first_source = retriever_resources[0].get("dataset_name", "无锡史志馆保护档案")
            source_display = f"官方数字认证：{first_source}"
            chunks_saved = str(retriever_resources)
        else:
            source_display = "惠山古镇历史街区联合文献库"
            chunks_saved = "[模型泛化生成 - 未直接命中本地硬分块]"
        elapsed_time = time.time() - start_time
        return answer, source_display, chunks_saved, elapsed_time
    except requests.exceptions.Timeout:
        elapsed_time = time.time() - start_time
        return "【网络超时】请重试。", "系统网络延迟警告", "[Timeout]", elapsed_time
    except Exception as e:
        elapsed_time = time.time() - start_time
        return f"【系统故障】{str(e)[:50]}", "技术故障降级保护", "[Error]", elapsed_time

# ==================== 生成延伸问题 ====================
def generate_followup_questions(user_question, ai_answer):
    FOLLOWUP_API_URL = "https://api.dify.ai/v1/chat-messages"
    FOLLOWUP_API_KEY = "Bearer app-CCck7NxI8NLZIxf24Q247Hti"

    prompt = f"""用户问题：{user_question}
AI 回答：{ai_answer}
请根据以上内容，生成 3 个与文化遗产相关的、开放式的、引导用户继续深入了解的后续问题。每个问题一行，只输出三个问题，不要序号，不要额外解释。"""

    payload = {
        "inputs": {},
        "query": prompt,
        "response_mode": "blocking",
        "user": participant_id
    }
    headers = {
        "Authorization": FOLLOWUP_API_KEY,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(FOLLOWUP_API_URL, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        content = response.json().get("answer", "")
        lines = [line.strip() for line in content.strip().split("\n") if line.strip()]
        questions = []
        for line in lines[:3]:
            cleaned = re.sub(r'^\d+[\.\、]?\s*', '', line)
            if cleaned:
                questions.append(cleaned)
        while len(questions) < 3:
            questions.append("您还想了解这个景点的其他方面吗？")
        return questions
    except Exception:
        # 静默失败，返回默认问题
        return [
            "这个景点还有哪些有趣的历史故事？",
            "与这里相关的名人有哪些？",
            "有什么特别的建筑细节值得关注吗？"
        ]

# ==================== 处理用户提问 ====================
def handle_question(question):
    with st.spinner("AI 导览员正在思考..."):
        answer, source, chunks, elapsed = simulate_rag_engine(question)
        st.session_state.conversation_history.append({
            "question": question,
            "answer": answer,
            "source": source
        })
        log_experimental_event(
            action_type="question_submitted",
            query_text=question,
            response_time=elapsed,
            retrieved_chunks=chunks,
            displayed_source_cue=source
        )
        followups = generate_followup_questions(question, answer)
        st.session_state.followup_questions = followups
        st.rerun()

# ==================== 前端界面 ====================
st.title(f"🏛️ 惠山古镇智慧导览：{current_poi['name']}")

# 显示当前模式（调试用，可删除）
st.caption(f"模式: {condition} | 参与者: {participant_id} | 景点: {poi_id}")

if condition == "baseline":
    st.markdown(f"### 景区官方概览\n{current_poi['info']}")
    st.image("https://images.unsplash.com/photo-1629814479361-9f268b8b809a?q=80&w=600&auto=format&fit=crop")
    st.caption("数据来源：无锡惠山古镇官方遗产保护名录与街区静态档案")

elif condition == "free_text":
    st.markdown(f"**📍 {current_poi['name']}**  \n{current_poi['info']}")
    st.divider()

    # 显示历史对话
    for turn in st.session_state.conversation_history:
        with st.chat_message("user"):
            st.markdown(turn["question"])
        with st.chat_message("assistant"):
            st.markdown(turn["answer"])
            st.markdown(f"<div class='source-chip'>🔍 {turn['source']}</div>", unsafe_allow_html=True)

    # 显示推荐问题
    if st.session_state.followup_questions:
        st.markdown("**💡 您可能还想了解：**")
        cols = st.columns(3)
        for i, q in enumerate(st.session_state.followup_questions):
            with cols[i % 3]:
                if st.button(f"❓ {q}", key=f"followup_{i}_{len(st.session_state.conversation_history)}"):
                    handle_question(q)

    # 底部输入框
    user_input = st.chat_input("请输入您的问题...", key="free_chat_input")
    if user_input and user_input.strip():
        handle_question(user_input.strip())

elif condition == "recchatbox":
    # 原有 recchatbox 逻辑（保持兼容）
    st.markdown(f"### 景区官方概览\n{current_poi['info']}")
    st.write("---")
    st.markdown("#### 💡 上下文智能化启发提问 (RecChatbox)")
    st.caption("根据您当前所处的历史空间情境，AI 为您推荐以下深度探究方向：")

    for rec_q in current_poi["recs"]:
        if st.button(f"✨ {rec_q}"):
            ans, src, chk, r_time = simulate_rag_engine(rec_q)
            st.session_state.ai_response = {"ans": ans, "src": src, "chk": chk, "clicked_q": rec_q}
            log_experimental_event(action_type="rec_clicked", query_text=rec_q, response_time=r_time, retrieved_chunks=chk, displayed_source_cue=src)

    user_q = st.text_input("或者，您也可以在此输入其他自由提问：", key="rec_txt")
    if st.button("提交自由问题", key="btn_rec"):
        if user_q:
            ans, src, chk, r_time = simulate_rag_engine(user_q)
            st.session_state.ai_response = {"ans": ans, "src": src, "chk": chk, "clicked_q": user_q}
            log_experimental_event(action_type="question_submitted", query_text=user_q, response_time=r_time, retrieved_chunks=chk, displayed_source_cue=src)

    if st.session_state.ai_response:
        st.markdown(f"<div class='qa-box'><b>AI 智能解答：</b><br>{st.session_state.ai_response['ans']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='source-chip'>🔍 权威数字证源：{st.session_state.ai_response['src']}</div>", unsafe_allow_html=True)

# ==================== 底部完成按钮 ====================
st.write("---")
if st.button("✅ 我已完成当前 POI 的阅读与交互"):
    log_experimental_event(action_type="completed")
    st.success("当前位点交互日志已安全写入后台。")
    st.markdown(f"**[请点击此处返回 Qualtrics 线上问卷](https://survey.qualtrics.com/jfe/form/your_survey_id?pid={participant_id}&poi={poi_id}&cond={condition})**")

# 侧边栏日志导出
st.sidebar.markdown("### 🛠️ 实验控制后台")
if st.sidebar.button("导出全样本最新交互日志 CSV"):
    if st.session_state.logs:
        df = pd.DataFrame(st.session_state.logs)
        csv_data = df.to_csv(index=False, encoding="utf-8-sig")
        st.sidebar.download_button("点击下载 CSV", data=csv_data, file_name="experiment_master_log.csv")
    else:
        st.sidebar.warning("暂无日志产生")
