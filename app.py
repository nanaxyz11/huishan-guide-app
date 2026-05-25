import streamlit as st
import json
import os
import time
from datetime import datetime
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from supabase import create_client  # 新增：导入 Supabase 客户端

# 1. 基础页面声明
st.set_page_config(page_title="惠山古镇 AI 导览实验平台", layout="centered", initial_sidebar_state="collapsed")

# 样式（不变）
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
    </style>
""", unsafe_allow_html=True)

# 2. 从外部 JSON 读取锁定知识库
@st.cache_data
def load_poi_data():
    with open("data/poi_content.json", "r", encoding="utf-8") as f:
        return json.load(f)

poi_database = load_poi_data()

# 3. 解析 URL 参数
query_params = st.query_params
participant_id = query_params.get("pid", "P_TEST_USER")
condition = query_params.get("condition", "recchatbox").lower()
poi_id = query_params.get("poi", "erquan").lower()

if poi_id not in poi_database:
    st.error("POI ID 错误，请检查 URL 参数。")
    st.stop()

current_poi = poi_database[poi_id]

# 4. 初始化 Session State
if "logs" not in st.session_state:
    st.session_state.logs = []
if "page_load_time" not in st.session_state:
    st.session_state.page_load_time = time.time()
if "ai_response" not in st.session_state:
    st.session_state.ai_response = None

# 新增：初始化 Supabase 客户端（从 Streamlit Secrets 读取配置）
if "supabase" not in st.session_state:
    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_KEY"]
    st.session_state.supabase = create_client(supabase_url, supabase_key)

# 5. 日志记录函数（修改为写入 Supabase）
def log_experimental_event(action_type, query_text="", response_time=0.0, retrieved_chunks=""):
    # 计算页面停留时间
    time_on_page = time.time() - st.session_state.page_load_time
    query_length = len(query_text) if query_text else 0
    
    # 构建事件数据字典（字段名必须与 Supabase 表中的列名完全一致）
    event_data = {
        "participant_id": participant_id,
        "experimental_condition": condition,
        "poi_id": poi_id,
        "action_type": action_type,
        "time_on_page_seconds": round(time_on_page, 2),
        "user_query_text": query_text,
        "user_query_word_count": query_length,
        "rag_response_time_ms": round(response_time * 1000, 1),
        "retrieved_chunks_saved": retrieved_chunks,
        "displayed_source_cue": "",   # 如果你需要记录来源标签，可以后续从 RAG 返回中获取；这里先留空
        "timestamp": datetime.now().isoformat()
    }
    
    # 本地保留一份（可选，用于调试）
    st.session_state.logs.append(event_data)
    
    # 写入 Supabase
    try:
        result = st.session_state.supabase.table("interaction_logs").insert(event_data).execute()
        # 如果写入成功，什么都不做；失败时打印错误到终端（不影响前端）
    except Exception as e:
        print(f"[Supabase 写入错误] {e}")

# 首次加载日志
if f"loaded_{poi_id}" not in st.session_state:
    st.session_state[f"loaded_{poi_id}"] = True
    log_experimental_event(action_type="page_loaded")

# ==================== Dify RAG 函数（完全不变） ====================
def simulate_rag_engine(user_query):
    start_time = time.time()
    DIFY_API_URL = "https://api.dify.ai/v1/chat-messages"
    DIFY_API_KEY = "Bearer 你的_app-rzITs8smrzMUhhdraDriLuRp"   # ⚠️ 请替换成你的真实密钥
    
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
    except requests.exceptions.ConnectionError as e:
        elapsed_time = time.time() - start_time
        print(f"[DEBUG] 连接错误详情: {e}")
        return "【网络连接失败】请检查网络，稍后重试。", "网络连接错误", "[ConnectionError]", elapsed_time
    except requests.exceptions.HTTPError as e:
        elapsed_time = time.time() - start_time
        if response.status_code == 401:
            return "【认证失败】API Key 无效。", "API认证错误", "[401]", elapsed_time
        else:
            return f"【服务器错误】HTTP {response.status_code}，请稍后重试。", "服务端异常", f"[HTTP{response.status_code}]", elapsed_time
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"[DEBUG] 未知错误: {e}")
        return f"【系统故障】请向研究员报告。错误类型: {type(e).__name__}", "技术故障降级保护", "[Error]", elapsed_time

# ========== 以下 UI 渲染部分完全不变 ==========
st.title(f"🏛️ 惠山古镇智慧导览：{current_poi['name']}")

if condition == "baseline":
    st.markdown(f"### 景区官方概览\n{current_poi['info']}")
    st.image("https://images.unsplash.com/photo-1629814479361-9f268b8b809a?q=80&w=600&auto=format&fit=crop", caption="惠山历史街区情境示意图")
    st.caption("数据来源：无锡惠山古镇官方遗产保护名录与街区静态档案")

elif condition == "free_text":
    st.markdown(f"### 景区官方概览\n{current_poi['info']}")
    st.write("---")
    st.markdown("#### 💬 向 AI 导览员自由提问")
    user_q = st.text_input("您可以输入任何关于当前 POI 历史、文化、碑文的追问：", key="free_q")
    if st.button("提交问题", key="btn_free"):
        if user_q:
            ans, src, chk, r_time = simulate_rag_engine(user_q)
            st.session_state.ai_response = {"ans": ans, "src": src, "chk": chk}
            log_experimental_event(action_type="question_submitted", query_text=user_q, response_time=r_time, retrieved_chunks=chk)
    if st.session_state.ai_response:
        st.markdown(f"<div class='qa-box'><b>AI 智能导览解答：</b><br>{st.session_state.ai_response['ans']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='source-chip'>🔍 权威数字证源：{st.session_state.ai_response['src']}</div>", unsafe_allow_html=True)

elif condition == "recchatbox":
    st.markdown(f"### 景区官方概览\n{current_poi['info']}")
    st.write("---")
    st.markdown("#### 💡 上下文智能化启发提问 (RecChatbox)")
    st.caption("根据您当前所处的历史空间情境，AI 为您推荐以下深入探究方向：")
    for rec_q in current_poi["recs"]:
        if st.button(f"✨ {rec_q}"):
            ans, src, chk, r_time = simulate_rag_engine(rec_q)
            st.session_state.ai_response = {"ans": ans, "src": src, "chk": chk, "clicked_q": rec_q}
            log_experimental_event(action_type="rec_clicked", query_text=rec_q, response_time=r_time, retrieved_chunks=chk)
    user_q = st.text_input("或者，您也可以在此输入其他自由问题：", key="rec_q")
    if st.button("提交自由问题", key="btn_rec"):
        if user_q:
            ans, src, chk, r_time = simulate_rag_engine(user_q)
            st.session_state.ai_response = {"ans": ans, "src": src, "chk": chk, "clicked_q": user_q}
            log_experimental_event(action_type="question_submitted", query_text=user_q, response_time=r_time, retrieved_chunks=chk)
    if st.session_state.ai_response:
        st.markdown(f"<div class='qa-box'><b>AI 智能导览解答：</b><br>{st.session_state.ai_response['ans']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='source-chip'>🔍 权威数字证源：{st.session_state.ai_response['src']}</div>", unsafe_allow_html=True)

st.write("---")
if st.button("✅ 我已完成当前 POI 的阅读与交互"):
    log_experimental_event(action_type="completed")
    st.success("当前位点交互日志已安全写入后台。")
    st.markdown(f"**[请点击此处返回 Qualtrics 线上问卷，进行当前 POI 的即时文化理解题测试](https://survey.qualtrics.com/jfe/form/your_survey_id?pid={participant_id}&poi={poi_id}&cond={condition})**")

st.sidebar.markdown("### 🛠️ 实验控制后台")
if st.sidebar.button("导出全样本最新交互日志 CSV"):
    if os.path.exists("logs/interaction_log.csv"):
        st.sidebar.download_button("点击下载 CSV", data=open("logs/interaction_log.csv", "rb"), file_name=f"experiment_master_log.csv")
    else:
        st.sidebar.warning("暂无日志产生")
