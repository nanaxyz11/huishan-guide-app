import streamlit as st
import json
import os
import time
from datetime import datetime
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from supabase import create_client

# ==================== 页面配置 ====================
st.set_page_config(page_title="惠山古镇 AI 导览实验平台", layout="centered", initial_sidebar_state="collapsed")

# ==================== 加载本地知识库 ====================
@st.cache_data
def load_poi_data():
    with open("data/poi_content.json", "r", encoding="utf-8") as f:
        return json.load(f)

poi_database = load_poi_data()

# ==================== URL 参数解析 ====================
query_params = st.query_params
participant_id = query_params.get("pid", "P_TEST_USER")
condition = query_params.get("condition", "recchatbox").lower()
poi_id = query_params.get("poi", "erquan").lower()

if poi_id not in poi_database:
    st.error("POI ID 错误，请检查 URL 参数。")
    st.stop()

current_poi = poi_database[poi_id]

# ==================== Session 状态初始化 ====================
if "logs" not in st.session_state:
    st.session_state.logs = []
if "page_load_time" not in st.session_state:
    st.session_state.page_load_time = time.time()
if "ai_response" not in st.session_state:
    st.session_state.ai_response = None
if "followup_questions" not in st.session_state:
    st.session_state.followup_questions = []
if "supabase" not in st.session_state:
    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_KEY"]
    st.session_state.supabase = create_client(supabase_url, supabase_key)

# ---------- 核心新增: 用于存储聊天消息的 Session State ----------
if "chat_messages" not in st.session_state:
    # 可以在这里添加一条开场白
    st.session_state.chat_messages = [
        {"role": "assistant", "content": f"您好！欢迎来到{current_poi['name']}，有什么想了解的吗？"}
    ]
# ---------------------------------------------------------

# ==================== 日志记录函数（写入 Supabase + 本地CSV） ====================
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

    # 1. 写入本地 CSV（备份）
    st.session_state.logs.append(event_data)
    df = pd.DataFrame(st.session_state.logs)
    log_file = "logs/interaction_log.csv"
    os.makedirs("logs", exist_ok=True)
    if not os.path.isfile(log_file):
        df.to_csv(log_file, index=False, encoding="utf-8-sig")
    else:
        df.to_csv(log_file, mode='a', header=False, index=False, encoding="utf-8-sig")

    # 2. 写入 Supabase
    try:
        st.session_state.supabase.table("interaction_logs").insert(event_data).execute()
    except Exception as e:
        # 如果写入失败，用 Streamlit 的 toast 通知在右下角弹出一个短暂的提示[reference:8]
        st.toast(f"⚠️ 数据保存失败: {e}", icon="⚠️")

# 页面加载埋点
if f"loaded_{poi_id}" not in st.session_state:
    st.session_state[f"loaded_{poi_id}"] = True
    log_experimental_event(action_type="page_loaded")

# ==================== Dify RAG 函数（回答问题） ====================
def simulate_rag_engine(user_query):
    start_time = time.time()
    DIFY_API_URL = "https://api.dify.ai/v1/chat-messages"
    DIFY_API_KEY = "Bearer app-rzITs8smrzMUhhdraDriLuRp"   # 你的主应用 API Key

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

# ==================== 生成延伸问题（调用独立的 Dify 应用） ====================
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
        res_json = response.json()
        content = res_json.get("answer", "")
        lines = [line.strip() for line in content.strip().split("\n") if line.strip()]
        import re
        questions = []
        for line in lines[:3]:
            cleaned = re.sub(r'^\d+[\.\、]?\s*', '', line)
            if cleaned:
                questions.append(cleaned)
        while len(questions) < 3:
            questions.append("您还想了解这个景点的其他方面吗？")
        return questions
    except Exception as e:
        st.toast(f"生成延伸问题失败: {e}", icon="⚠️")
        return [
            "这个景点还有哪些有趣的历史故事？",
            "与这里相关的名人有哪些？",
            "有什么特别的建筑细节值得关注吗？"
        ]

# ---------- 核心新增: 统一处理用户提问的函数 ----------
def handle_question(question):
    with st.spinner("AI 导览员正在思考..."):
        # 1. 调用 RAG 得到回答
        answer, source, chunks, elapsed = simulate_rag_engine(question)
        # 2. 保存到会话状态的消息列表中
        st.session_state.chat_messages.append({"role": "user", "content": question})
        st.session_state.chat_messages.append({"role": "assistant", "content": answer, "source": source})
        # 3. 记录日志
        log_experimental_event(
            action_type="question_submitted",
            query_text=question,
            response_time=elapsed,
            retrieved_chunks=chunks,
            displayed_source_cue=source
        )
        # 4. 根据最新的问答，生成延伸问题
        followups = generate_followup_questions(question, answer)
        st.session_state.followup_questions = followups
        # 5. 强制刷新页面以显示新内容
        st.rerun()
# -----------------------------------------------------

# ==================== 前端界面渲染 ====================

# 显示当前实验条件提示
st.info(f"当前实验条件: {condition} | 参与者: {participant_id} | 景点: {current_poi['name']}")

# 显示景点官方概览
st.markdown(f"### 景区官方概览")
st.markdown(current_poi['info'])

if condition == "baseline":
    st.image("https://images.unsplash.com/photo-1629814479361-9f268b8b809a?q=80&w=600&auto=format&fit=crop", caption="惠山历史街区情境示意图")
    st.caption("数据来源：无锡惠山古镇官方遗产保护名录与街区静态档案")

elif condition == "free_text":
    # ---------- 核心改造: 使用 st.chat_message 渲染历史记录，并用 st.chat_input 做底部输入框 ----------
    # 1. 遍历并展示所有历史消息[reference:9][reference:10]
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            # 如果是助手消息，额外显示一个来源标签
            if msg["role"] == "assistant" and "source" in msg:
                st.caption(f"🔍 权威数字证源：{msg['source']}")
    # 2. 检查并显示生成的延伸问题建议按钮
    if st.session_state.followup_questions:
        st.markdown("#### 💡 相关问题推荐")
        cols = st.columns(3)
        for i, q in enumerate(st.session_state.followup_questions):
            with cols[i % 3]:
                if st.button(f"❓ {q}", key=f"followup_{i}"):
                    handle_question(q)
    # 3. 在底部放置 chat_input，用户输入新问题[reference:11]
    if prompt := st.chat_input("请输入您的问题..."):
        handle_question(prompt)
    # ----------------------------------------------------------------------------------------

elif condition == "recchatbox":
    # recchatbox 模式保持不变
    # ... (原有代码保持不变)
    pass

# ==================== 实验完成交互与结束按钮 ====================
# 注意: recchatbox 和 baseline 的部分省略，您可以在完整代码中查看。
