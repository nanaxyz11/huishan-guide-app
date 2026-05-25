import streamlit as st
import json
import os
import time
import requests
from datetime import datetime
import pandas as pd
from supabase import create_client

# ------------------------------
# 1. 页面配置
# ------------------------------
st.set_page_config(page_title="惠山古镇 AI 导览实验平台", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .source-chip {
        display: inline-flex;
        align-items: center;
        background-color: #e8f0fe;
        color: #1a73e8;
        padding: 6px 12px;
        border-radius: 16px;
        font-size: 12px;
        font-weight: 600;
        margin-top: 10px;
        border: 1px solid #d2e3fc;
    }
    .qa-box {
        background-color: #f8f9fa;
        padding: 16px;
        border-radius: 8px;
        border-left: 4px solid #1a73e8;
        margin-top: 12px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)

# ------------------------------
# 2. 加载本地知识库（兜底）
# ------------------------------
@st.cache_data
def load_poi_data():
    with open("data/poi_content.json", "r", encoding="utf-8") as f:
        return json.load(f)

poi_database = load_poi_data()

# ------------------------------
# 3. 获取URL参数
# ------------------------------
query_params = st.query_params
participant_id = query_params.get("pid", "P_DEBUG_USER")
condition = query_params.get("condition", "recchatbox").lower()
poi_id = query_params.get("poi", "erquan").lower()

if poi_id not in poi_database:
    st.error("POI ID 错误，请检查 URL 参数。")
    st.stop()

current_poi = poi_database[poi_id]

# ------------------------------
# 4. 初始化 Session State
# ------------------------------
if "logs" not in st.session_state:
    st.session_state.logs = []
if "page_load_time" not in st.session_state:
    st.session_state.page_load_time = time.time()
if "ai_response" not in st.session_state:
    st.session_state.ai_response = None
if "rag_cache" not in st.session_state:
    st.session_state.rag_cache = {}

# 初始化 Supabase 客户端（使用 secrets 中的配置）
if "supabase" not in st.session_state:
    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_KEY"]
    st.session_state.supabase = create_client(supabase_url, supabase_key)

# ------------------------------
# 5. 日志记录函数（写入 Supabase）
# ------------------------------
def log_experimental_event(action_type, query_text="", response_time=0.0, retrieved_chunks="", source_cue=""):
    # 计算页面停留时间（相对页面加载时刻）
    time_on_page = time.time() - st.session_state.page_load_time
    query_length = len(query_text) if query_text else 0
    
    # 构造一条记录，完全匹配 Supabase 表中的列名
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
        "displayed_source_cue": source_cue,
        "timestamp": datetime.now().isoformat()  # 确保有时间戳
    }
    
    # 本地也保留一份（可选，用于调试）
    st.session_state.logs.append(event_data)
    
    # 写入 Supabase
    try:
        result = st.session_state.supabase.table("interaction_logs").insert(event_data).execute()
        # 可选：打印成功信息（调试用）
        # print("插入成功:", result)
    except Exception as e:
        # 发生错误时在终端打印，不影响用户体验
        print(f"Supabase 写入错误: {e}")

# 页面加载时记录一条日志
if f"loaded_{poi_id}" not in st.session_state:
    st.session_state[f"loaded_{poi_id}"] = True
    log_experimental_event(action_type="page_loaded")

# ------------------------------
# 6. 云端 RAG 函数（带缓存）
# ------------------------------
def call_live_llm_rag(user_query):
    start_time = time.time()
    
    # 缓存检查
    cache_key = (poi_id, user_query)
    if cache_key in st.session_state.rag_cache:
        cached = st.session_state.rag_cache[cache_key]
        if time.time() - cached["timestamp"] < 600:  # 10分钟有效
            return cached["answer"], cached["source"], cached["chunks"], 0.01, cached["source"]
    
    # Dify API 配置
    DIFY_API_URL = "https://api.dify.ai/v1/chat-messages"
    DIFY_API_KEY = "Bearer app-rzITs8smrzMUhhdraDriLuRp"   # ⚠️ 替换成你的真实密钥
    
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
    
    proxies = {"http": None, "https": None}  # 禁用代理
    
    try:
        response = requests.post(DIFY_API_URL, json=payload, headers=headers, timeout=3.0, proxies=proxies)
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
        
        elapsed = time.time() - start_time
        
        # 存入缓存
        st.session_state.rag_cache[cache_key] = {
            "answer": answer,
            "source": source_display,
            "chunks": chunks_saved,
            "timestamp": time.time()
        }
        return answer, source_display, chunks_saved, elapsed, source_display
        
    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        return "【网络较慢】请再点一次", "网络临时降级", "[Timeout]", elapsed, "网络临时降级"
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"Dify API 错误: {e}")
        return f"【服务异常】请稍后重试", "系统降级", "[Error]", elapsed, "系统降级"

# ------------------------------
# 7. 界面渲染
# ------------------------------
st.title(f"🏛️ 惠山智慧导览：{current_poi['name']}")

# 三个条件分支（与之前一模一样，但调用的函数返回5个值，需调整）
if condition == "baseline":
    st.markdown(f"### 📋 官方导览信息\n{current_poi['info']}")
    st.caption("信息来源：惠山古镇官方景区静态导览文本")

elif condition == "free_text":
    st.markdown(f"### 📋 官方导览信息\n{current_poi['info']}")
    st.write("---")
    st.markdown("#### 💬 自由智能化提问 (Free-Text)")
    
    user_q = st.text_input("您可以向 AI 导览员输入任何关于当前位点的历史、文化或传说提问：", key="free_txt")
    if st.button("提交问题", key="btn_free"):
        if user_q:
            with st.spinner("AI 导览员正在查阅地方志..."):
                ans, src, chk, r_time, cue = call_live_llm_rag(user_q)
                st.session_state.ai_response = {"ans": ans, "src": src}
                log_experimental_event(action_type="question_submitted", query_text=user_q, 
                                       response_time=r_time, retrieved_chunks=chk, source_cue=cue)

    if st.session_state.ai_response:
        st.markdown(f"<div class='qa-box'><b>AI 智能解答：</b><br>{st.session_state.ai_response['ans']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='source-chip'>🔍 权威数字证源：{st.session_state.ai_response['src']}</div>", unsafe_allow_html=True)

elif condition == "recchatbox":
    st.markdown(f"### 📋 官方导览信息\n{current_poi['info']}")
    st.write("---")
    st.markdown("#### 💡 上下文启发式推荐对话 (RecChatbox)")
    st.caption("基于您当前所处的历史街区情境，AI 为您推荐以下深度探究方向：")
    
    for rec_q in current_poi["recs"]:
        if st.button(f"✨ {rec_q}"):
            with st.spinner("正在检索历史文献..."):
                ans, src, chk, r_time, cue = call_live_llm_rag(rec_q)
                st.session_state.ai_response = {"ans": ans, "src": src}
                log_experimental_event(action_type="rec_clicked", query_text=rec_q,
                                       response_time=r_time, retrieved_chunks=chk, source_cue=cue)

    user_q = st.text_input("或者，您也可以在此输入其他自由提问：", key="rec_txt")
    if st.button("提交自由问题", key="btn_rec"):
        if user_q:
            with st.spinner("AI 智能分析中..."):
                ans, src, chk, r_time, cue = call_live_llm_rag(user_q)
                st.session_state.ai_response = {"ans": ans, "src": src}
                log_experimental_event(action_type="question_submitted", query_text=user_q,
                                       response_time=r_time, retrieved_chunks=chk, source_cue=cue)

    if st.session_state.ai_response:
        st.markdown(f"<div class='qa-box'><b>AI 智能解答：</b><br>{st.session_state.ai_response['ans']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='source-chip'>🔍 权威数字证源：{st.session_state.ai_response['src']}</div>", unsafe_allow_html=True)

# ------------------------------
# 8. 结束跳转与下载
# ------------------------------
st.write("---")
if st.button("✅ 我已完成当前位点的浏览与交互"):
    log_experimental_event(action_type="completed")
    st.success("数据日志已安全记录。")
    qualtrics_target_url = f"https://survey.qualtrics.com/jfe/form/your_survey_id?pid={participant_id}&poi={poi_id}&cond={condition}"
    st.markdown(f"**[👉 请点击此处进入线上问卷]({qualtrics_target_url})**")

if st.sidebar.button("下载 Master 实验交互日志 (CSV)"):
    if st.session_state.logs:
        df = pd.DataFrame(st.session_state.logs)
        st.sidebar.download_button("确认下载", data=df.to_csv(index=False), file_name="master_interaction_log.csv")
    else:
        st.sidebar.warning("暂无日志，请先交互。")
