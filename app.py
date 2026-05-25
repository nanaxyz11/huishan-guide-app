import streamlit as st
import json
import os
import time
from datetime import datetime
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 1. 基础页面声明（采用移动端优先的紧凑布局）
st.set_page_config(page_title="惠山古镇 AI 导览实验平台", layout="centered", initial_sidebar_state="collapsed")

# 强制注入 CSS 样式：美化卡片和来源 chip，使其具备国际顶会高保真原型的质感
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

# 3. 解析 URL 参数（严格捕获外部问卷平台传来的实验控制变量）
query_params = st.query_params
participant_id = query_params.get("pid", "P_TEST_USER") # 参与者ID
condition = query_params.get("condition", "recchatbox").lower() # baseline, free_text, recchatbox
poi_id = query_params.get("poi", "erquan").lower() # erquan, citang

if poi_id not in poi_database:
    st.error("POI ID 错误，请检查 URL 参数。")
    st.stop()

current_poi = poi_database[poi_id]

# 4. 初始化 Session State 变量与会话追踪基础设施
if "logs" not in st.session_state:
    st.session_state.logs = []
if "page_load_time" not in st.session_state:
    st.session_state.page_load_time = time.time()
if "ai_response" not in st.session_state:
    st.session_state.ai_response = None

# 5. 高级日志记录函数：精确捕获设计学投稿所需的各项指标
def log_experimental_event(action_type, query_text="", response_time=0.0, retrieved_chunks=""):
    # 计算当前页面停留时间（Time on Page）
    time_on_page = time.time() - st.session_state.page_load_time
    query_length = len(query_text) if query_text else 0
    
    event_data = {
        "timestamp": datetime.now().isoformat(),
        "participant_id": participant_id,
        "experimental_condition": condition,
        "poi_id": poi_id,
        "action_type": action_type,              # page_loaded, question_submitted, rec_clicked, completed
        "time_on_page_seconds": round(time_on_page, 2), # 替代原先的总体会话时长
        "user_query_text": query_text,
        "user_query_word_count": query_length,    # 替代原先的 word count
        "rag_response_time_ms": round(response_time * 1000, 1), # 记录每次 RAG 响应时间
        "retrieved_chunks_saved": retrieved_chunks # 保存检索片段，用于事后幻觉审查
    }
    
    st.session_state.logs.append(event_data)
    
    # 实时持久化写入 CSV，防止现场设备断电、断网丢失数据
    df = pd.DataFrame(st.session_state.logs)
    log_file = "logs/interaction_log.csv"
    os.makedirs("logs", exist_ok=True)
    if not os.path.isfile(log_file):
        df.to_csv(log_file, index=False, encoding="utf-8-sig")
    else:
        df.to_csv(log_file, mode='a', header=False, index=False, encoding="utf-8-sig")

# 触发首次加载日志
if f"loaded_{poi_id}" not in st.session_state:
    st.session_state[f"loaded_{poi_id}"] = True
    log_experimental_event(action_type="page_loaded")

# ==================== 强化后的 Dify RAG 函数（支持自动重试） ====================
def simulate_rag_engine(user_query):
    """
    真正的云端 Dify RAG 接口：向公网大模型发送请求，并精确捕获回答、真实来源以及 RAG 的检索延迟（用于日志审计）
    内置自动重试机制和更详细的错误提示。
    """
    start_time = time.time()
    
    # 👇 请将下面的 "你的_Dify_API_Key" 替换成你在 Dify 后台获取的真实密钥
    DIFY_API_URL = "https://api.dify.ai/v1/chat-messages"
    DIFY_API_KEY = "Bearer app-rzITs8smrzMUhhdraDriLuRp"   # 示例：Bearer app-xxxxxxxxxx
    
    # 构造符合 Dify 规范的 Payload
    payload = {
        "inputs": {
            "current_poi": current_poi["name"]  # 隐式提示词工程：动态同步用户当前所处的空间位点
        },
        "query": user_query,
        "response_mode": "blocking",            # 阻塞式返回，方便精确计时
        "user": participant_id                  # 传入被试ID，方便在 Dify 后台进行多被试行为对照
    }
    headers = {
        "Authorization": DIFY_API_KEY,
        "Content-Type": "application/json"
    }
    
    # 配置重试策略（应对网络波动）
    session = requests.Session()
    retry_strategy = Retry(
        total=3,                       # 最多重试3次
        backoff_factor=1,              # 重试间隔：1秒、2秒、4秒
        status_forcelist=[500, 502, 503, 504],  # 只在服务器错误时重试
        allowed_methods=["POST"]       # 允许对POST请求重试
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    
    try:
        # 发起真实联网请求（超时时间设为15秒，比原来宽松一些）
        response = session.post(DIFY_API_URL, json=payload, headers=headers, timeout=15)
        response.raise_for_status()  # 如果状态码不是2xx，会抛出异常
        res_json = response.json()
        
        # 1. 提取大模型基于知识库生成的严谨回答
        answer = res_json.get("answer", "系统响应异常，请重试。")
        
        # 2. 提取 RAG 检索的原始 Chunks 片段，作为论文事后审查模型幻觉的硬证据
        retriever_resources = res_json.get("metadata", {}).get("retriever_resources", [])
        
        # 3. 动态合成前端 Cultural Trust Cue (来源芯片文字)
        if retriever_resources:
            # 提取被命中的第一篇知识库文档的名称作为展示来源
            first_source = retriever_resources[0].get("dataset_name", "无锡史志馆保护档案")
            source_display = f"官方数字认证：{first_source}"
            chunks_saved = str(retriever_resources)  # 完整保留
        else:
            # 走兜底提示
            source_display = "惠山古镇历史街区联合文献库"
            chunks_saved = "[模型泛化生成 - 未直接命中本地硬分块]"
            
        elapsed_time = time.time() - start_time
        return answer, source_display, chunks_saved, elapsed_time
        
    except requests.exceptions.Timeout:
        elapsed_time = time.time() - start_time
        return "【网络超时】AI导览员思考时间过长，请重试。", "系统网络延迟警告", "[Timeout]", elapsed_time
    except requests.exceptions.ConnectionError as e:
        elapsed_time = time.time() - start_time
        # 输出具体错误码到控制台（方便你排查），但前端只显示友好提示
        print(f"[DEBUG] 连接错误详情: {e}")
        return "【网络连接失败】请检查网络是否正常（可能需要代理），稍后重试。", "网络连接错误", "[ConnectionError]", elapsed_time
    except requests.exceptions.HTTPError as e:
        elapsed_time = time.time() - start_time
        if response.status_code == 401:
            return "【认证失败】API Key 无效或已过期，请联系管理员。", "API认证错误", "[401]", elapsed_time
        else:
            return f"【服务器错误】HTTP {response.status_code}，请稍后重试。", "服务端异常", f"[HTTP{response.status_code}]", elapsed_time
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"[DEBUG] 未知错误: {e}")  # 打印到终端便于调试
        return f"【系统故障】请向研究员报告。错误类型: {type(e).__name__}", "技术故障降级保护", "[Error]", elapsed_time

# ================================================================

# 7. 根据三条件进行差异化前端高保真 UI 渲染

st.title(f"🏛️ 惠山古镇智慧导览：{current_poi['name']}")

# ==================== 条件 1：BASELINE WEBSITE ====================
if condition == "baseline":
    st.markdown(f"### 景区官方概览\n{current_poi['info']}")
    st.image("https://images.unsplash.com/photo-1629814479361-9f268b8b809a?q=80&w=600&auto=format&fit=crop", caption="惠山历史街区情境示意图") # 稳健的公共可用占位图
    st.caption("数据来源：无锡惠山古镇官方遗产保护名录与街区静态档案")

# ==================== 条件 2：FREE-TEXT INTERACTION ====================
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
        # 创新变量表征：渲染 Cultural Trust Cue (来源 chip)
        st.markdown(f"<div class='source-chip'>🔍 权威数字证源：{st.session_state.ai_response['src']}</div>", unsafe_allow_html=True)

# ==================== 条件 3：RECCHATBOX (你的核心改良组) ====================
elif condition == "recchatbox":
    st.markdown(f"### 景区官方概览\n{current_poi['info']}")
    st.write("---")
    st.markdown("#### 💡 上下文智能化启发提问 (RecChatbox)")
    
    # 渲染推荐问题脚手架
    st.caption("根据您当前所处的历史空间情境，AI 为您推荐以下深入探究方向：")
    
    # 采用紧凑的按钮行，适应手机端点击，防止产生过大视觉疲劳
    for rec_q in current_poi["recs"]:
        if st.button(f"✨ {rec_q}"):
            ans, src, chk, r_time = simulate_rag_engine(rec_q)
            st.session_state.ai_response = {"ans": ans, "src": src, "chk": chk, "clicked_q": rec_q}
            log_experimental_event(action_type="rec_clicked", query_text=rec_q, response_time=r_time, retrieved_chunks=chk)
            
    # 同时也保留自由文本输入输入框，保证交互完整度
    user_q = st.text_input("或者，您也可以在此输入其他自由问题：", key="rec_q")
    if st.button("提交自由问题", key="btn_rec"):
        if user_q:
            ans, src, chk, r_time = simulate_rag_engine(user_q)
            st.session_state.ai_response = {"ans": ans, "src": src, "chk": chk, "clicked_q": user_q}
            log_experimental_event(action_type="question_submitted", query_text=user_q, response_time=r_time, retrieved_chunks=chk)

    if st.session_state.ai_response:
        st.markdown(f"<div class='qa-box'><b>AI 智能导览解答：</b><br>{st.session_state.ai_response['ans']}</div>", unsafe_allow_html=True)
        # 严格执行要求：RecChatbox 不仅要流利，而且必须带有权威可信的来源 Chip 基础设施
        st.markdown(f"<div class='source-chip'>🔍 权威数字证源：{st.session_state.ai_response['src']}</div>", unsafe_allow_html=True)


# 8. 实验结束重定向与数据清算闭环
st.write("---")
if st.button("✅ 我已完成当前 POI 的阅读与交互"):
    log_experimental_event(action_type="completed")
    st.success("当前位点交互日志已安全写入后台。")
    # 提示跳转回 Qualtrics 完成本站的即时回忆理解题和心理学量表
    st.markdown(f"**[请点击此处返回 Qualtrics 线上问卷，进行当前 POI 的即时文化理解题测试](https://survey.qualtrics.com/jfe/form/your_survey_id?pid={participant_id}&poi={poi_id}&cond={condition})**")

# 研究者专用的隐藏后台控制面板（位于侧边栏，用于导出日志）
st.sidebar.markdown("### 🛠️ 实验控制后台")
if st.sidebar.button("导出全样本最新交互日志 CSV"):
    if os.path.exists("logs/interaction_log.csv"):
        st.sidebar.download_button("点击下载 CSV", data=open("logs/interaction_log.csv", "rb"), file_name=f"experiment_master_log.csv")
    else:
        st.sidebar.warning("暂无日志产生")
