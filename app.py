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
import base64
from PIL import Image

# ==================== 页面配置 ====================
st.set_page_config(page_title="惠山古镇 AI 导览 | 非遗数字体验", layout="centered", initial_sidebar_state="expanded")

# ==================== 辅助函数：图片转 Base64（用于背景） ====================
def get_img_base64(img_path):
    """读取本地图片并转为 Base64 字符串"""
    try:
        if os.path.exists(img_path):
            with open(img_path, "rb") as f:
                data = f.read()
            return base64.b64encode(data).decode()
        else:
            return ""
    except Exception:
        return ""

# ==================== 实时天气获取函数 ====================
def get_weather():
    """获取无锡实时天气和温度 (使用 wttr.in 免费 API)"""
    try:
        # 使用 wttr.in 获取无锡当前天气 (简洁格式: 天气图标+温度)
        url = "https://wttr.in/Wuxi?format=%C+%t&lang=zh"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            weather_text = response.text.strip()
            # 示例输出: "多云 +18°C"
            # 美化显示
            return f"🌤️ {weather_text}"
        else:
            return "🌡️ 惠山古镇 18°C"
    except Exception:
        # 降级显示模拟天气（实际可保留为静态，不影响体验）
        return "🌤️ 惠山古镇 16°C · 适宜游览"

# ==================== 全新 Hue SkillC 风格（美化版） ====================
st.markdown("""
<style>
/* ===== Hue SkillC: Jiangnan Tech 3A Streamlit ===== */
:root {
  --jn-bg-1: #dff7fb;
  --jn-bg-2: #f7fff8;
  --jn-card: rgba(255, 255, 255, 0.85);
  --jn-ink: #182426;
  --jn-muted: #6f7f82;
  --jn-blue: #1f8fff;
  --jn-cyan: #62dce8;
  --jn-green: #34d399;
  --jn-orange: #df7a2d;
  --jn-gold: #c99452;
  --jn-line: rgba(31, 143, 255, 0.16);
}

.stApp {
  background:
    radial-gradient(circle at 12% 8%, rgba(98, 220, 232, .42), transparent 28%),
    radial-gradient(circle at 85% 18%, rgba(52, 211, 153, .28), transparent 24%),
    linear-gradient(180deg, var(--jn-bg-1) 0%, var(--jn-bg-2) 100%);
  color: var(--jn-ink);
}

[data-testid="stHeader"] {
  background: rgba(223, 247, 251, .72);
  backdrop-filter: blur(14px);
}

.block-container {
  max-width: 1080px;
  padding-top: 1.4rem;
}

/* Hero 区域 (背景图片已通过内联样式替换) */
.jn-hero {
  position: relative;
  min-height: 260px;
  border-radius: 28px;
  overflow: hidden;
  padding: 28px;
  background-size: cover;
  background-position: center 30%;
  box-shadow: 0 24px 60px rgba(25, 110, 130, .22);
  margin-bottom: 20px;
}
.jn-hero::after {
  content: "";
  position: absolute;
  inset: 0;
  background-image: radial-gradient(circle, rgba(98,220,232,.45) 1px, transparent 1px);
  background-size: 18px 18px;
  opacity: .18;
  pointer-events: none;
}
.jn-hero-title {
  position: relative;
  z-index: 1;
  max-width: 620px;
  font-size: 44px;
  line-height: 1.08;
  font-weight: 900;
  color: white;
  text-shadow: 0 4px 18px rgba(0,0,0,.32);
}
.jn-hero-title span { color: #8ff7ff; }
.jn-hero-sub {
  position: relative;
  z-index: 1;
  margin-top: 14px;
  max-width: 520px;
  font-size: 16px;
  line-height: 1.7;
  color: rgba(255,255,255,.86);
}

/* 实时天气栏 (替换搜索框) */
.jn-weather-bar {
  margin-top: -28px;
  position: relative;
  z-index: 3;
  background: rgba(255,255,255,.86);
  border: 1px solid var(--jn-line);
  border-radius: 999px;
  padding: 14px 24px;
  box-shadow: 0 16px 38px rgba(43, 140, 160, .16);
  margin-bottom: 24px;
  color: var(--jn-ink);
  font-weight: 600;
  backdrop-filter: blur(8px);
  text-align: center;
  font-size: 1.1rem;
}
.jn-weather-bar i {
  font-style: normal;
  margin-right: 6px;
}

/* 功能宫格 */
.jn-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-bottom: 24px;
}
.jn-feature {
  background: var(--jn-card);
  border: 1px solid rgba(255,255,255,.72);
  border-radius: 22px;
  padding: 18px 12px;
  text-align: center;
  box-shadow: 0 14px 32px rgba(50, 120, 130, .12);
  backdrop-filter: blur(18px);
}
.jn-icon {
  width: 44px;
  height: 44px;
  margin: 0 auto 10px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, rgba(31,143,255,.16), rgba(52,211,153,.18));
  color: var(--jn-blue);
  font-weight: 800;
}
.jn-feature-title { font-size: 14px; font-weight: 700; }

/* 内容卡片 */
.jn-card {
  background: var(--jn-card);
  border: 1px solid rgba(255,255,255,.76);
  border-radius: 24px;
  padding: 20px;
  box-shadow: 0 16px 40px rgba(45, 120, 138, .13);
  backdrop-filter: blur(18px);
  margin-bottom: 20px;
}
.jn-section-title {
  font-size: 22px;
  font-weight: 900;
  margin: 6px 0 12px;
}

/* 推荐图片卡片样式 */
.recommend-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 12px;
  justify-content: space-between;
}
.recommend-item {
  flex: 1;
  min-width: 100px;
  background: rgba(255,255,255,0.5);
  border-radius: 24px;
  padding: 12px 8px;
  text-align: center;
  transition: all 0.2s;
  backdrop-filter: blur(4px);
  border: 1px solid rgba(255,255,255,0.6);
}
.recommend-item:hover {
  transform: translateY(-4px);
  background: rgba(255,255,255,0.75);
  box-shadow: 0 12px 24px rgba(0,0,0,0.08);
}
.recommend-img {
  width: 100%;
  aspect-ratio: 1 / 1;
  object-fit: cover;
  border-radius: 18px;
  margin-bottom: 10px;
  box-shadow: 0 6px 14px rgba(0,0,0,0.1);
}
.recommend-name {
  font-weight: 800;
  font-size: 0.9rem;
  margin: 8px 0 4px;
}
.recommend-btn button {
  background: rgba(31,143,255,0.12);
  border: none;
  border-radius: 40px;
  padding: 5px 12px;
  font-size: 0.75rem;
  font-weight: 600;
  color: #126fbf;
}

/* POI 卡片 */
.jn-poi-desc { margin-top: 6px; color: var(--jn-muted); line-height: 1.65; }

/* 按钮样式 */
div.stButton > button {
  background: linear-gradient(135deg, var(--jn-blue), var(--jn-green));
  color: white;
  border: none;
  border-radius: 999px;
  padding: .75rem 1.35rem;
  font-weight: 800;
  box-shadow: 0 12px 26px rgba(31,143,255,.24);
  transition: all 0.2s;
}
div.stButton > button:hover {
  filter: brightness(1.04);
  transform: translateY(-1px);
}
/* 语音专用按钮 */
.voice-btn {
  background: #ffffffcc;
  backdrop-filter: blur(8px);
  border: 1px solid var(--jn-line);
  border-radius: 999px;
  padding: 10px 20px;
  font-weight: 600;
  cursor: pointer;
  transition: 0.2s;
  font-size: 0.9rem;
}
.voice-btn:hover {
  background: var(--jn-orange);
  color: white;
  border-color: var(--jn-orange);
}

/* 输入框 */
.stTextInput input, .stTextArea textarea {
  background: rgba(255,255,255,.86);
  border: 1px solid rgba(31,143,255,.18);
  border-radius: 16px;
}

/* 侧边栏 */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, rgba(255,255,255,.88), rgba(232,250,252,.86));
  border-right: 1px solid rgba(31,143,255,.12);
}

/* 来源chip */
.source-chip {
  display: inline-block;
  background-color: rgba(31,143,255,0.12);
  color: #1f8fff;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.7rem;
  font-weight: 500;
  margin-top: 8px;
}
</style>
""", unsafe_allow_html=True)

# ==================== 语音 JS（增强版） ====================
st.markdown("""
<script>
window.speechSynthesisPolyfill = function() {
    if (!window.speechSynthesis) {
        alert("您的浏览器不支持语音合成");
        return false;
    }
    var dummy = new SpeechSynthesisUtterance("");
    window.speechSynthesis.cancel();
    return true;
};

window.speakText = function(text) {
    if (!window.speechSynthesis) {
        alert("您的浏览器不支持语音合成");
        return;
    }
    var utterance = new SpeechSynthesisUtterance(text);
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

# ==================== 日志函数（稳定写入） ====================
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

# ==================== Dify RAG 函数（优化） ====================
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

# ==================== 侧边栏 ====================
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

# ==================== 主界面渲染（美化改造版） ====================
# 1. 主图背景替换为本地 "主图.jpg"
main_img_path = "/Users/clisl/Documents/huishan_3a_exp/惠山古镇5POI图/主图.jpg"
main_img_b64 = get_img_base64(main_img_path)
if main_img_b64:
    hero_bg_style = f"background-image: linear-gradient(90deg, rgba(10, 30, 36, .68), rgba(10, 30, 36, .28)), url('data:image/jpg;base64,{main_img_b64}');"
else:
    # 降级（如果图片不存在，保持原渐变）
    hero_bg_style = "background-image: linear-gradient(90deg, rgba(10,30,36,.78), rgba(10,30,36,.18)), url('https://images.unsplash.com/photo-1528181304800-259b08848526?auto=format&fit=crop&w=1400&q=80');"

st.markdown(f"""
<div class="jn-hero" style="{hero_bg_style}">
  <div class="jn-hero-title">惠山古镇 <span>AI 导览员</span></div>
  <div class="jn-hero-sub">
    融合 3A 智能问答、文化知识库与语音导览，呈现江南文脉的轻量化数字体验。
  </div>
</div>
""", unsafe_allow_html=True)

# 2. 实时天气温度显示 (替换原来的搜索框)
weather_info = get_weather()
st.markdown(f"""
<div class="jn-weather-bar">
  🌸 惠山古镇 · {weather_info}
</div>
""", unsafe_allow_html=True)

# 3. 功能宫格
st.markdown("""
<div class="jn-grid">
  <div class="jn-feature"><div class="jn-icon">AI</div><div class="jn-feature-title">智能问答</div></div>
  <div class="jn-feature"><div class="jn-icon">泉</div><div class="jn-feature-title">二泉导览</div></div>
  <div class="jn-feature"><div class="jn-icon">祠</div><div class="jn-feature-title">名人祠堂</div></div>
  <div class="jn-feature"><div class="jn-icon">游</div><div class="jn-feature-title">路线推荐</div></div>
</div>
""", unsafe_allow_html=True)

# 4. 今日推荐区域：图片化卡片（天下第二泉、古华山门、知鱼栏、竹炉山房、范文正公祠）
# 定义推荐列表: (显示名称, 对应POI ID, 图片路径)
recommend_pois = [
    ("天下第二泉", "erquan", "/Users/clisl/Documents/huishan_3a_exp/惠山古镇5POI图/二泉.jpg"),
    ("古华山门", "guhuashanmen", "/Users/clisl/Documents/huishan_3a_exp/惠山古镇5POI图/金莲桥.jpg"),
    ("知鱼栏", "bayinjian", "/Users/clisl/Documents/huishan_3a_exp/惠山古镇5POI图/知鱼栏.jpg"),
    ("竹炉山房", "zhulu_shanfang", "/Users/clisl/Documents/huishan_3a_exp/惠山古镇5POI图/竹炉山房.jpg"),
    ("范文正公祠", "fanwenzheng_gongci", "/Users/clisl/Documents/huishan_3a_exp/惠山古镇5POI图/范文公正祠.jpg")
]

st.markdown('<div class="jn-card"><div class="jn-section-title">📸 今日推荐 · 寻迹江南</div><div class="recommend-grid">', unsafe_allow_html=True)
cols = st.columns(len(recommend_pois))
for idx, (name, poi_id, img_path) in enumerate(recommend_pois):
    with cols[idx]:
        # 显示图片
        if os.path.exists(img_path):
            st.image(img_path, use_column_width=True, output_format="JPEG")
        else:
            # 占位图
            st.markdown(f'<div class="recommend-img" style="background:#e2e8f0; display:flex; align-items:center; justify-content:center;">📷</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="recommend-name">{name}</div>', unsafe_allow_html=True)
        # 点击跳转按钮
        if st.button("✨ 探寻", key=f"rec_btn_{idx}"):
            # 跳转到对应 POI 点位
            if poi_id in POI_ORDER:
                new_index = POI_ORDER.index(poi_id)
                if new_index != st.session_state.current_poi_index:
                    st.session_state.current_poi_index = new_index
                    st.session_state.chat_messages = []
                    st.session_state.followup_questions = []
                    st.session_state.ai_response = None
                    st.session_state.page_load_time = time.time()
                    st.query_params["poi"] = poi_id
                    st.query_params["pid"] = st.session_state.participant_id
                    st.rerun()
            else:
                st.warning("该点位暂未开放")
st.markdown('</div></div>', unsafe_allow_html=True)

# 5. 当前点位详情卡片（保留原有内容风格）
st.markdown(f"""
<div class="jn-card" style="margin-top:4px;">
  <div style="display:flex; align-items:center; gap:8px;">
    <span style="font-size:28px;">📍</span>
    <b style="font-size:22px;">{current_poi['name']}</b>
  </div>
  <div style="margin-top:12px; line-height:1.65;">{current_poi["info"]}</div>
</div>
""", unsafe_allow_html=True)

# 语音按钮
voice_col, _ = st.columns([1, 5])
with voice_col:
    if st.button("🔊 朗读介绍", key="speak_intro", help="点击聆听景点介绍"):
        st.markdown(f'<script>speakText("{current_poi["info"]}")</script>', unsafe_allow_html=True)

# 聊天界面 (保持原有实验逻辑)
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
