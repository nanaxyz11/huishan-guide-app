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

st.markdown("""
    <style>
    .source-chip {
        display: inline-flex;
        align-items: center;
        background-color: #f0f2f6;
        color: #31333f;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 500;
        margin-top: 8px;
        border: 1px solid #e0e2e6;
    }
    .qa-box {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #ff4b4b;
        margin-top: 10px;
    }
    .followup-button {
        margin-top: 10px;
        margin-right: 8px;
    }
    </style>
""", unsafe_allow_html=True)

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
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []   # 存储 [{"question": str, "answer": str, "source": str}, ...]
if "page_load_time" not in st.session_state:
    st.session_state.page_load_time = time.time()
if "ai_response" not in st.session_state:
    st.session_state.ai_response = None
if "followup_questions" not in st.session_state:
    st.session_state.followup_questions = []      # 当前显示的建议问题列表
if "supabase" not in st.session_state:
    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_KEY"]
    st.session_state.supabase = create_client(supabase_url, supabase_key)

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

    # 2. 写入 Supabase（如果失败，显示错误但不中断）
    try:
        st.session_state.supabase.table("interaction_logs").insert(event_data).execute()
    except Exception as e:
        # 显示错误提示（方便调试，但用户可忽略）
        st.error(f"Supabase 写入失败: {e}")
        print(f"[Supabase Error] {e}")

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
    """基于用户问题和 AI 回答生成 3 个后续问题，失败时返回默认问题"""
    FOLLOWUP_API_URL = "https://api.dify.ai/v1/chat-messages"
    FOLLOWUP_API_KEY = "Bearer app-xxxxxxxxxxxxxxxxxxxx"   # ⚠️ 替换为你新建的“生成问题”应用的 API Key

    # 构建提示词
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
        # 提取每行一个问题
        lines = [line.strip() for line in content.strip().split("\n") if line.strip()]
        # 只取前3个，并去除序号（如 "1. " 或 "1、"）
        import re
        questions = []
        for line in lines[:3]:
            cleaned = re.sub(r'^\d+[\.\、]?\s*', '', line)
            if cleaned:
                questions.append(cleaned)
        # 如果不足3个，补一些默认问题
        while len(questions) < 3:
            questions.append("您还想了解这个景点的其他方面吗？")
        return questions
    except Exception as e:
        st.error(f"生成延伸问题失败: {e}")  # 显示错误便于调试
        # 返回默认问题
        return [
            "这个景点还有哪些有趣的历史故事？",
            "与这里相关的名人有哪些？",
            "有什么特别的建筑细节值得关注吗？"
        ]

# ==================== 处理用户提问（核心流程） ====================
def handle_question(question):
    with st.spinner("AI 导览员正在思考..."):
        # 1. 调用 RAG 得到回答
        answer, source, chunks, elapsed = simulate_rag_engine(question)
        # 2. 保存到会话历史
        st.session_state.conversation_history.append({
            "question": question,
            "answer": answer,
            "source": source
        })
        # 3. 记录日志
        log_experimental_event(
            action_type="question_submitted",
            query_text=question,
            response_time=elapsed,
            retrieved_chunks=chunks,
            displayed_source_cue=source
        )
        # 4. 生成延伸问题（基于当前问题和回答）
        followups = generate_followup_questions(question, answer)
        st.session_state.followup_questions = followups
        # 5. 强制刷新页面以显示新内容
        st.rerun()

# ==================== 前端界面渲染 ====================
st.title(f"🏛️ 惠山古镇智慧导览：{current_poi['name']}")

# 显示当前实验条件提示
st.info(f"当前实验条件: {condition} | 参与者: {participant_id} | 景点: {current_poi['name']}")

if condition == "baseline":
    st.markdown(f"### 景区官方概览\n{current_poi['info']}")
    st.image("https://images.unsplash.com/photo-1629814479361-9f268b8b809a?q=80&w=600&auto=format&fit=crop", caption="惠山历史街区情境示意图")
    st.caption("数据来源：无锡惠山古镇官方遗产保护名录与街区静态档案")

elif condition == "free_text":
    st.markdown(f"### 景区官方概览\n{current_poi['info']}")
    st.write("---")
    st.markdown("#### 💬 自由提问（每次回答后会生成3个后续问题）")

    # 显示历史对话
    if st.session_state.conversation_history:
        for idx, item in enumerate(st.session_state.conversation_history):
            st.markdown(f"**您**：{item['question']}")
            st.markdown(f"<div class='qa-box'><b>AI 解答：</b><br>{item['answer']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='source-chip'>🔍 {item['source']}</div>", unsafe_allow_html=True)
            st.write("---")
    else:
        st.markdown("*暂无对话，请在下方输入您的问题开始。*")

    # 当前输入框
    user_q = st.text_input("请输入您的问题：", key="free_text_input")
    if st.button("发送", key="send_btn"):
        if user_q.strip():
            handle_question(user_q.strip())

    # 显示生成的延伸问题按钮（如果存在）
    if st.session_state.followup_questions:
        st.markdown("#### 💡 相关问题推荐（点击继续提问）")
        cols = st.columns(3)
        for i, q in enumerate(st.session_state.followup_questions):
            with cols[i % 3]:
                if st.button(f"❓ {q}", key=f"followup_{i}_{len(st.session_state.conversation_history)}"):
                    handle_question(q)

elif condition == "recchatbox":
    st.markdown(f"### 景区官方概览\n{current_poi['info']}")
    st.write("---")
    st.markdown("#### 💡 上下文智能化启发提问 (RecChatbox)")
    st.caption("根据您当前所处的历史空间情境，AI 为您推荐以下深度探究方向：")
    # 原有推荐按钮（不生成延伸问题，保持原样）
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

# 底部按钮
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
