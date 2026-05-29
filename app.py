以下是您所需的“惠山古镇 AI 导览员”网页美化后的完整代码。我们保留了所有原有功能（Dify机器人、聊天助手、Supabase数据交互等），仅对界面样式进行了全面升级，采用江南科技风玻璃态设计，使其更加现代、美观且富有沉浸感。
```python
import streamlit as st
import json
import os
import time
import hashlib
import random
import re
from datetime import datetime
import pandas as pd
import requests
from supabase import create_client

# ==================== 页面配置 ====================
st.set_page_config(page_title="惠山古镇 AI 导览 | 非遗数字体验", layout="centered", initial_sidebar_state="expanded")

# ==================== 全新 Hue SkillC 江南科技风样式 ====================
st.markdown("""
<style>
:root {
  --jn-bg-start: #dff8fb;
  --jn-bg-end: #f8fff7;
  --jn-glass: rgba(255, 255, 255, 0.72);
  --jn-ink: #172326;
  --jn-muted: #4e6b70;
  --jn-blue: #128fff;
  --jn-cyan: #6be7f2;
  --jn-green: #38d6aa;
  --jn-orange: #df7a2d;
  --jn-gold: #c99452;
  --jn-line: rgba(18, 143, 255, 0.24);
  --jn-radius-xl: 32px;
  --jn-radius-md: 20px;
  --jn-shadow: 0 20px 48px rgba(35, 118, 138, 0.16);
  --jn-shadow-hover: 0 26px 56px rgba(18, 143, 255, 0.2);
}

/* 主容器背景与极光动效 */
.stApp {
  background: linear-gradient(180deg, var(--jn-bg-start) 0%, var(--jn-bg-end) 100%);
  color: var(--jn-ink);
  overflow-x: hidden;
}

.stApp::before {
  content: "";
  position: fixed;
  inset: -20%;
  z-index: -3;
  background:
    radial-gradient(circle at 18% 18%, rgba(107, 231, 242, 0.58), transparent 38%),
    radial-gradient(circle at 78% 22%, rgba(56, 214, 170, 0.38), transparent 36%),
    radial-gradient(circle at 50% 82%, rgba(18, 143, 255, 0.24), transparent 44%);
  filter: blur(48px);
  animation: auroraFlow 22s ease-in-out infinite alternate;
  pointer-events: none;
}

.stApp::after {
  content: "";
  position: fixed;
  inset: 0;
  z-index: -2;
  opacity: 0.28;
  background-image: radial-gradient(circle, rgba(255, 255, 255, 0.9) 0.7px, transparent 0.7px);
  background-size: 8px 8px;
  pointer-events: none;
}

@keyframes auroraFlow {
  0% { transform: translate3d(-2%, -1%, 0) scale(1); }
  50% { transform: translate3d(3%, 2%, 0) scale(1.05); }
  100% { transform: translate3d(-1%, 4%, 0) scale(1.02); }
}

/* 头部透明模糊 */
[data-testid="stHeader"] {
  background: rgba(223, 248, 251, 0.68);
  backdrop-filter: blur(20px);
}

/* 主容器宽度 */
.block-container {
  max-width: 1180px;
  padding-top: 1.8rem;
}

/* 玻璃卡片基类 */
.glass-card, 
.jn-hero, 
.jn-feature-card,
.jn-poi-card,
.jn-current-card {
  position: relative;
  background: var(--jn-glass);
  border: 1px solid rgba(255, 255, 255, 0.78);
  border-radius: var(--jn-radius-xl);
  backdrop-filter: blur(24px) saturate(1.4);
  -webkit-backdrop-filter: blur(24px) saturate(1.4);
  box-shadow: var(--jn-shadow);
  transition: all 0.3s cubic-bezier(0.2, 0, 0, 1);
}

.glass-card:hover,
.jn-poi-card:hover,
.jn-feature-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--jn-shadow-hover);
  border-color: rgba(255, 255, 255, 0.9);
}

/* Hero 区域 */
.jn-hero {
  min-height: 380px;
  padding: 2.2rem 2.5rem;
  margin-bottom: 1.8rem;
  background: linear-gradient(112deg, rgba(10, 32, 36, 0.78), rgba(10, 32, 36, 0.22)),
              url("https://images.unsplash.com/photo-1587560699334-bea2d8c0a7b1?auto=format&fit=crop&w=1600&q=80");
  background-size: cover;
  background-position: center 30%;
  overflow: hidden;
}

.jn-hero::after {
  content: "";
  position: absolute;
  inset: 0;
  background-image: radial-gradient(circle, rgba(107, 231, 242, 0.35) 0.8px, transparent 0.8px);
  background-size: 18px 18px;
  opacity: 0.26;
  pointer-events: none;
}

.jn-hero-title {
  max-width: 720px;
  font-size: clamp(44px, 8vw, 80px);
  line-height: 1.05;
  font-weight: 900;
  color: white;
  text-shadow: 0 8px 26px rgba(0, 0, 0, 0.36);
  letter-spacing: -0.01em;
}

.jn-hero-title span {
  color: #9ef3ff;
}

.jn-hero-sub {
  margin-top: 1rem;
  max-width: 560px;
  font-size: 1.05rem;
  line-height: 1.7;
  color: rgba(255, 255, 255, 0.92);
  font-weight: 500;
}

/* 快捷操作栏 */
.jn-quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.8rem;
  margin: 1.4rem 0 0.8rem;
}

.jn-quick-chip {
  background: rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.45);
  border-radius: 80px;
  padding: 0.4rem 1.2rem;
  font-size: 0.85rem;
  font-weight: 600;
  color: white;
  transition: 0.2s;
  cursor: default;
}

/* 特色网格 */
.jn-feature-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1.25rem;
  margin: 2rem 0;
}

.jn-feature-card {
  padding: 1.5rem 1rem;
  text-align: center;
}

.jn-feature-icon {
  width: 52px;
  height: 52px;
  margin: 0 auto 0.9rem;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, rgba(18, 143, 255, 0.18), rgba(56, 214, 170, 0.2));
  border-radius: 24px;
  font-size: 1.8rem;
  color: #128fff;
}

.jn-feature-title {
  font-weight: 800;
  font-size: 1.05rem;
  margin-bottom: 0.3rem;
}

.jn-feature-text {
  color: var(--jn-muted);
  font-size: 0.8rem;
  line-height: 1.5;
}

/* POI 列表卡片 */
.jn-poi-list {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  margin: 1.8rem 0;
}

.jn-poi-card {
  display: grid;
  grid-template-columns: 100px 1fr;
  gap: 1.2rem;
  padding: 1.2rem;
  align-items: center;
}

.jn-poi-emoji {
  font-size: 3.2rem;
  text-align: center;
  background: rgba(18, 143, 255, 0.08);
  border-radius: 28px;
  padding: 0.6rem 0;
}

.jn-poi-title {
  font-size: 1.35rem;
  font-weight: 800;
  letter-spacing: -0.3px;
  margin-bottom: 0.3rem;
}

.jn-poi-desc {
  color: var(--jn-muted);
  font-size: 0.88rem;
  line-height: 1.55;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 当前点位卡片 */
.jn-current-card {
  padding: 1.6rem;
  margin: 1.2rem 0;
}

.jn-current-kicker {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--jn-blue);
  font-weight: 800;
}

.jn-current-title {
  font-size: 1.7rem;
  font-weight: 900;
  margin: 0.4rem 0 0.6rem;
}

.jn-current-text {
  color: var(--jn-muted);
  line-height: 1.7;
}

/* 聊天与按钮美化 */
div.stButton > button {
  border-radius: 60px;
  background: linear-gradient(105deg, rgba(18, 143, 255, 0.12), rgba(56, 214, 170, 0.1));
  border: 1px solid var(--jn-line);
  color: #116dbb;
  font-weight: 700;
  transition: all 0.2s;
  box-shadow: 0 6px 14px rgba(18, 143, 255, 0.08);
}

div.stButton > button:hover {
  transform: translateY(-2px);
  background: rgba(18, 143, 255, 0.2);
  border-color: #128fff;
  box-shadow: 0 14px 28px rgba(18, 143, 255, 0.2);
}

[data-testid="stChatMessage"] {
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(12px);
  border-radius: 24px;
  border: 1px solid rgba(255, 255, 255, 0.8);
  padding: 0.8rem 1.2rem;
  margin-bottom: 0.8rem;
}

[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p {
  margin-bottom: 0;
}

.source-chip {
  display: inline-block;
  background: rgba(18, 143, 255, 0.12);
  color: #0f6ba8;
  padding: 0.2rem 0.8rem;
  border-radius: 36px;
  font-size: 0.7rem;
  font-weight: 600;
  margin-top: 0.5rem;
}

/* 侧边栏玻璃化 */
[data-testid="stSidebar"] {
  background: rgba(255, 255, 255, 0.68);
  backdrop-filter: blur(28px);
  border-right: 1px solid var(--jn-line);
}

/* 输入框美化 */
.stTextInput input, .stTextArea textarea {
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid rgba(18, 143, 255, 0.25);
  border-radius: 28px;
  padding: 0.6rem 1rem;
}

/* 进度条圆润 */
[data-testid="stProgress"] > div {
  background-color: rgba(18, 143, 255, 0.2);
  border-radius: 20px;
}

/* 移动端适配 */
@media (max-width: 760px) {
  .jn-feature-grid { grid-template-columns: repeat(2, 1fr); gap: 1rem; }
  .jn-poi-card { grid-template-columns: 1fr; text-align: center; }
  .jn-poi-emoji { font-size: 2.8rem; }
  .jn-hero { padding: 1.6rem; min-height: 280px; }
}
</style>
""", unsafe_allow_html=True)

# ==================== 语音 JS（增强版） ====================
st.markdown("""
<script>
window.speakText = function(text) {
    if (!window.speechSynthesis) return;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'zh-CN';
    utterance.rate = 0.9;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
};
</script>
""", unsafe_allow_html=True)

# ==================== 加载 POI 数据 ====================
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

# ==================== URL 参数与 Session ====================
if "participant_id" not in st.session_state:
    st.session_state.participant_id = st.query_params.get("pid", "P_TEST_USER")

url_group = st.query_params.get("group")
if url_group in ["A", "B", "C"]:
    st.session_state.group = url_group
else:
    if "group" not in st.session_state:
        hash_val = int(hashlib.md5(st.session_state.participant_id.encode()).hexdigest()[:4], 16)
        group_map = ["A", "B", "C"]
        st.session_state.group = group_map[hash_val % 3]

group_condition_map = {
    "A": ["baseline", "free_text", "recchatbox", "baseline", "free_text"],
    "B": ["free_text", "recchatbox", "baseline", "free_text", "recchatbox"],
    "C": ["recchatbox", "baseline", "free_text", "recchatbox", "baseline"]
}
condition_sequence = group_condition_map[st.session_state.group]

if "current_poi_index" not in st.session_state:
    current_poi_key = st.query_params.get("poi", POI_ORDER[0])
    st.session_state.current_poi_index = POI_ORDER.index(current_poi_key) if current_poi_key in POI_ORDER else 0
else:
    url_poi = st.query_params.get("poi")
    if url_poi and url_poi in POI_ORDER and POI_ORDER.index(url_poi) != st.session_state.current_poi_index:
        st.session_state.current_poi_index = POI_ORDER.index(url_poi)
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

# ==================== 其他 Session 状态 ====================
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

# ==================== 日志函数 ====================
def log_experimental_event(action_type, query_text="", response_time=0.0, retrieved_chunks="", displayed_source_cue=""):
    time_on_page = time.time() - st.session_state.page_load_time
    query_length = len(query_text) if query_text else 0

    event_data = {
        "participant_id": str(st.session_state.participant_id),
        "experimental_condition": current_condition,
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
        st.error(f"⚠️ Supabase 写入失败: {e}")

if f"loaded_{current_poi_key}" not in st.session_state:
    st.session_state[f"loaded_{current_poi_key}"] = True
    log_experimental_event("page_loaded")

# ==================== Dify RAG 函数 ====================
def simulate_rag_engine(user_query):
    start = time.time()
    url = "https://api.dify.ai/v1/chat-messages"
    key = "Bearer app-rzITs8smrzMUhhdraDriLuRp"
    payload = {
        "inputs": {"current_poi": current_poi["name"]},
        "query": user_query,
        "response_mode": "blocking",
        "user": st.session_state.participant_id
    }
    headers = {"Authorization": key, "Content-Type": "application/json"}
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
        st.error(f"Dify API 错误: {str(e)}")
        return "【网络或服务异常】请稍后重试。", "故障降级", "[Error]", elapsed

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

def handle_question(question):
    with st.spinner("AI 导览员正在查阅史料..."):
        ans, src, chunks, elapsed = simulate_rag_engine(question)
        st.session_state.chat_messages.append({"role": "user", "content": question})
        st.session_state.chat_messages.append({"role": "assistant", "content": ans, "source": src})
        log_experimental_event("question_submitted", question, elapsed, chunks, src)
        st.markdown(f'<script>speakText("{ans.replace('"', '\\"')}")</script>', unsafe_allow_html=True)
        if actual_render == "recchatbox":
            st.session_state.followup_questions = generate_followup_questions(question, ans)
        else:
            st.session_state.followup_questions = []
        st.rerun()

# ==================== 侧边栏 (保持不变, 仅样式由CSS美化) ====================
st.sidebar.markdown(f"**参与者 ID**：`{st.session_state.participant_id}`")
st.sidebar.markdown(f"**所属组别**：Group {st.session_state.group}")
st.sidebar.markdown(f"**当前体验**：{display_condition_name}")
st.sidebar.markdown(f"**进度**：{st.session_state.current_poi_index+1}/{len(POI_ORDER)}")
st.sidebar.markdown("---")
st.sidebar.markdown("### 🏮 游览路线")

progress = (st.session_state.current_poi_index + 1) / len(POI_ORDER)
st.sidebar.progress(progress)
for idx, pid in enumerate(POI_ORDER):
    if idx < st.session_state.current_poi_index:
        icon = "✅"
    elif idx == st.session_state.current_poi_index:
        icon = "📍"
    else:
        icon = "▪️"
    poi_name = POI_NAMES[pid]
    if st.sidebar.button(f"{icon} {poi_name}", key=f"nav_{pid}"):
        if idx != st.session_state.current_poi_index:
            st.session_state.current_poi_index = idx
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

# ==================== 主界面美化布局 (保留全部后端逻辑) ====================

# Hero 区
st.markdown(f"""
<div class="jn-hero">
  <div class="jn-hero-title">惠山古镇<br><span>AI 导览员</span></div>
  <div class="jn-hero-sub">
    面向 3A 实验的江南科技风导览 · 以真实点位、文化知识库与智能问答构成轻盈、可探索的游览体验。
  </div>
  <div class="jn-quick-actions">
    <div class="jn-quick-chip">🎫 预约入园</div>
    <div class="jn-quick-chip">💬 问AI</div>
    <div class="jn-quick-chip">📅 活动日历</div>
    <div class="jn-quick-chip">🏛️ 历史名迹</div>
  </div>
</div>
""", unsafe_allow_html=True)

# 功能宫格
st.markdown("""
<div class="jn-feature-grid">
  <div class="jn-feature-card">
    <div class="jn-feature-icon">✨</div>
    <div class="jn-feature-title">智能问答</div>
    <div class="jn-feature-text">围绕五个POI进行文化遗产问答</div>
  </div>
  <div class="jn-feature-card">
    <div class="jn-feature-icon">🎤</div>
    <div class="jn-feature-title">语音导览</div>
    <div class="jn-feature-text">支持点位介绍朗读与沉浸式聆听</div>
  </div>
  <div class="jn-feature-card">
    <div class="jn-feature-icon">🗺️</div>
    <div class="jn-feature-title">点位切换</div>
    <div class="jn-feature-text">沿左侧路线探索五处文化节点</div>
  </div>
  <div class="jn-feature-card">
    <div class="jn-feature-icon">📊</div>
    <div class="jn-feature-title">实验记录</div>
    <div class="jn-feature-text">记录停留、提问与回答行为数据</div>
  </div>
</div>
""", unsafe_allow_html=True)

# 所有POI展示卡片（保留原数据库内容）
st.markdown('<div class="jn-poi-list">', unsafe_allow_html=True)
for pid in POI_ORDER:
    poi = poi_database[pid]
    # 为每个点位选择对应emoji
    emoji_map = {
        "fanwenzheng_gongci": "🏛️",
        "guhuashanmen": "⛩️",
        "bayinjian": "🎋",
        "zhulu_shanfang": "🍵",
        "erquan": "💧"
    }
    emoji = emoji_map.get(pid, "🏯")
    st.markdown(f"""
    <div class="jn-poi-card">
        <div class="jn-poi-emoji">{emoji}</div>
        <div>
            <div class="jn-poi-title">{poi['name']}</div>
            <div class="jn-poi-desc">{poi['info'][:140]}…</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# 当前点位详情卡片
st.markdown(f"""
<div class="jn-current-card">
    <div class="jn-current-kicker">📍 当前所在点位</div>
    <div class="jn-current-title">{current_poi['name']}</div>
    <div class="jn-current-text">{current_poi['info']}</div>
</div>
""", unsafe_allow_html=True)

# 语音按钮 (美化)
voice_col, _ = st.columns([1, 5])
with voice_col:
    if st.button("🔊 朗读介绍", key="speak_intro", help="点击聆听景点介绍"):
        safe_info = current_poi["info"].replace('"', '\\"')
        st.markdown(f'<script>speakText("{safe_info}")</script>', unsafe_allow_html=True)

# 聊天界面 (完全保留原有逻辑)
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

# 切换点位按钮
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
