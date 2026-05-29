import streamlit as st
import json
import os
import time
import hashlib
import random
import re
import base64
import mimetypes
from datetime import datetime
from pathlib import Path
from html import escape
import pandas as pd
import requests
from supabase import create_client

# ==================== 页面配置 ====================
st.set_page_config(page_title="惠山古镇 AI 导览 | 非遗数字体验", layout="centered", initial_sidebar_state="expanded")

# ==================== 图片资源 base64 处理 ====================
ASSET_DIR = Path(__file__).resolve().parent / "惠山古镇5POI图"

def asset_uri(filename):
    path = ASSET_DIR / filename
    if not path.exists():
        # 如果图片不存在，返回一个占位图（透明）
        return "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='300' viewBox='0 0 400 300'%3E%3Crect width='400' height='300' fill='%23f0f4f8'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' fill='%23999'%3E暂无图片%3C/text%3E%3C/svg%3E"
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    data = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{data}"

HERO_IMAGE = asset_uri("主图.jpg")

POI_IMAGES = {
    "fanwenzheng_gongci": asset_uri("范文公正祠.jpg"),
    "guhuashanmen": asset_uri("金莲桥.jpg"),
    "bayinjian": asset_uri("八音涧.jpg"),
    "zhulu_shanfang": asset_uri("竹炉山房.jpg"),
    "erquan": asset_uri("二泉1.jpg"),
}

# ==================== 全新 Jiangnan Tech 风格（Glassmorphism + Aurora + Reveal） ====================
st.markdown(f"""
<style>
/* ---------- 全局变量 ---------- */
:root {{
  --jn-bg-1: #dff7fb;
  --jn-bg-2: #f7fff8;
  --jn-card: rgba(255, 255, 255, 0.72);
  --jn-ink: #182426;
  --jn-muted: #5b6e72;
  --jn-blue: #1f8fff;
  --jn-cyan: #62dce8;
  --jn-green: #34d399;
  --jn-orange: #df7a2d;
  --jn-gold: #c99452;
  --jn-line: rgba(31, 143, 255, 0.28);
}}

/* ---------- 动态 Aurora 背景 + 流动 ---------- */
.stApp {{
  background: linear-gradient(180deg, var(--jn-bg-1) 0%, var(--jn-bg-2) 100%);
  color: var(--jn-ink);
  position: relative;
  overflow-x: hidden;
}}

.stApp::before {{
  content: "";
  position: fixed;
  inset: -20%;
  z-index: -2;
  background: 
    radial-gradient(circle at 22% 30%, rgba(98, 220, 232, 0.52), transparent 38%),
    radial-gradient(circle at 78% 20%, rgba(52, 211, 153, 0.44), transparent 42%),
    radial-gradient(circle at 45% 70%, rgba(31, 143, 255, 0.28), transparent 48%);
  filter: blur(60px);
  animation: auroraFlow 16s ease-in-out infinite alternate;
  pointer-events: none;
}}

@keyframes auroraFlow {{
  0% {{ transform: translate3d(-2%, -1%, 0) scale(1); opacity: 0.7; }}
  50% {{ transform: translate3d(4%, 2%, 0) scale(1.12); opacity: 1; }}
  100% {{ transform: translate3d(-1%, 3%, 0) scale(0.98); opacity: 0.8; }}
}}

/* 白色噪点纹理 */
.stApp::after {{
  content: "";
  position: fixed;
  inset: 0;
  z-index: -1;
  background-image: radial-gradient(circle, rgba(255,255,255,0.6) 1px, transparent 1px);
  background-size: 22px 22px;
  opacity: 0.22;
  pointer-events: none;
}}

/* ---------- Glass morphism 强化 ---------- */
.jn-card, .jn-poi-card, .jn-hero-actions > div, .stButton > button, .stTextInput input, .stTextArea textarea, [data-testid="stSidebar"] {{
  backdrop-filter: blur(18px) saturate(180%);
  background: rgba(255, 255, 255, 0.68);
  border: 1px solid rgba(255, 255, 255, 0.8);
  box-shadow: 0 18px 42px rgba(45, 90, 100, 0.12);
}}

/* 加强高斯模糊的卡片背景 */
.jn-card, .jn-poi-card {{
  background: rgba(255, 255, 255, 0.58);
  backdrop-filter: blur(24px) saturate(200%);
  border-radius: 32px;
  padding: 20px;
  margin-bottom: 24px;
  transition: transform 0.2s, box-shadow 0.2s;
}}

/* ---------- Reveal on Scroll 动画 ---------- */
.reveal {{
  opacity: 0;
  transform: translateY(28px);
  transition: opacity 0.7s cubic-bezier(0.2, 0.9, 0.3, 1.1), transform 0.7s cubic-bezier(0.2, 0.9, 0.3, 1.1);
}}
.reveal.visible {{
  opacity: 1;
  transform: translateY(0);
}}

/* ---------- 侧边栏 POI 按钮透明底边框 ---------- */
[data-testid="stSidebar"] .stButton button {{
  background: transparent !important;
  border: 1px solid var(--jn-blue) !important;
  color: var(--jn-blue) !important;
  font-weight: 600;
  box-shadow: none !important;
  transition: all 0.2s;
}}
[data-testid="stSidebar"] .stButton button:hover {{
  background: rgba(31, 143, 255, 0.12) !important;
  transform: translateX(4px);
}}

/* ---------- Hero 区域（主图加大，内含四个按钮） ---------- */
.jn-hero {{
  position: relative;
  min-height: 520px;
  border-radius: 36px;
  overflow: hidden;
  background: linear-gradient(135deg, rgba(10, 30, 36, 0.62), rgba(10, 30, 36, 0.22)), url("{HERO_IMAGE}");
  background-size: cover;
  background-position: center 30%;
  margin-bottom: 28px;
  box-shadow: 0 28px 56px rgba(25, 80, 90, 0.28);
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  padding: 28px 32px 24px 32px;
}}

.jn-hero-title {{
  font-size: 56px;
  font-weight: 950;
  line-height: 1.08;
  color: white;
  text-shadow: 0 6px 20px rgba(0,0,0,0.32);
  margin-bottom: 8px;
}}
.jn-hero-title span {{
  color: #9efff0;
}}
.jn-hero-sub {{
  font-size: 17px;
  color: rgba(255,255,255,0.9);
  max-width: 560px;
  margin-bottom: 28px;
  text-shadow: 0 1px 4px rgba(0,0,0,0.2);
}}

/* 四个按钮容器（置于主图内部下方） */
.jn-hero-actions {{
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-top: 12px;
}}

.jn-hero-action {{
  background: rgba(255, 255, 255, 0.22);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.55);
  border-radius: 60px;
  padding: 12px 0;
  text-align: center;
  font-weight: 800;
  font-size: 1rem;
  color: white;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}}
.jn-hero-action:hover {{
  background: rgba(255, 255, 255, 0.38);
  transform: translateY(-3px);
  border-color: white;
}}

/* 搜索栏（移到主图下方独立区域） */
.jn-search {{
  background: rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(16px);
  border-radius: 60px;
  padding: 8px 20px;
  margin: 12px 0 28px 0;
  border: 1px solid rgba(255,255,255,0.9);
  font-size: 15px;
  color: var(--jn-muted);
  display: flex;
  align-items: center;
  gap: 8px;
}}
.jn-search::before {{
  content: "🔍";
  font-size: 18px;
}}

/* POI 卡片网格（五张带图） */
.jn-poi-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 24px;
  margin: 24px 0;
}}
.jn-poi-card {{
  display: flex;
  flex-direction: column;
  background: rgba(255,255,255,0.6);
  backdrop-filter: blur(20px);
  border-radius: 28px;
  overflow: hidden;
  transition: all 0.25s;
}}
.jn-poi-card:hover {{
  transform: translateY(-6px);
  box-shadow: 0 28px 44px rgba(0,0,0,0.12);
}}
.jn-poi-img {{
  width: 100%;
  height: 180px;
  object-fit: cover;
  border-bottom: 1px solid rgba(255,255,255,0.6);
}}
.jn-poi-content {{
  padding: 18px;
}}
.jn-poi-name {{
  font-size: 22px;
  font-weight: 900;
  margin-bottom: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}}
.jn-poi-desc {{
  color: var(--jn-muted);
  line-height: 1.65;
  font-size: 14px;
}}

/* 骨架屏 */
.jn-skeleton {{
  background: linear-gradient(110deg, rgba(255,255,255,0.5) 8%, rgba(255,255,255,0.9) 18%, rgba(255,255,255,0.5) 33%);
  background-size: 200% 100%;
  animation: skeletonWave 1.2s linear infinite;
  border-radius: 20px;
  margin-bottom: 12px;
}}
@keyframes skeletonWave {{
  to { background-position: -200% 0; }
}}

/* 来源 chip */
.source-chip {{
  display: inline-block;
  background: rgba(31,143,255,0.18);
  color: #1f6fb0;
  padding: 4px 12px;
  border-radius: 40px;
  font-size: 0.7rem;
  font-weight: 600;
  margin-top: 10px;
}}

/* 响应式 */
@media (max-width: 720px) {{
  .jn-hero-actions {{
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }}
  .jn-hero-title {{
    font-size: 36px;
  }}
  .jn-poi-grid {{
    grid-template-columns: 1fr;
  }}
}}
</style>

<script>
// Reveal on Scroll
document.addEventListener("DOMContentLoaded", function() {{
  const observer = new IntersectionObserver((entries) => {{
    entries.forEach(entry => {{
      if (entry.isIntersecting) {{
        entry.target.classList.add("visible");
      }}
    }});
  }}, {{ threshold: 0.12 }});
  document.querySelectorAll(".reveal").forEach(el => observer.observe(el));
}});

// 语音合成（与原有保持一致）
window.speakText = function(text) {{
  if (!window.speechSynthesis) return;
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "zh-CN";
  utterance.rate = 0.9;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}};
</script>
""", unsafe_allow_html=True)

# ==================== 加载 POI 数据（不变）====================
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

# ==================== URL 参数与 Session（不变）====================
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

# ==================== 其他 Session 状态（不变）====================
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

# Supabase 客户端（不变）
if "supabase" not in st.session_state:
    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_KEY"]
    st.session_state.supabase = create_client(supabase_url, supabase_key)

# ==================== 日志函数（不变）====================
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

# ==================== Dify RAG 函数（不变）====================
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

# ==================== 处理用户提问（骨架屏替换 spinner）====================
def handle_question(question):
    # 骨架屏动画容器
    skeleton_placeholder = st.empty()
    skeleton_placeholder.markdown("""
    <div class="jn-skeleton" style="height: 90px; width: 100%;"></div>
    <div class="jn-skeleton" style="height: 60px; width: 80%; margin-top: 12px;"></div>
    <div class="jn-skeleton" style="height: 40px; width: 60%; margin-top: 12px;"></div>
    """, unsafe_allow_html=True)

    ans, src, chunks, elapsed = simulate_rag_engine(question)
    skeleton_placeholder.empty()  # 移除骨架屏

    st.session_state.chat_messages.append({"role": "user", "content": question})
    st.session_state.chat_messages.append({"role": "assistant", "content": ans, "source": src})
    log_experimental_event("question_submitted", question, elapsed, chunks, src)

    # 语音朗读回答
    safe_ans = ans.replace('"', '\\"').replace("\n", " ")
    st.markdown(f'<script>speakText("{safe_ans}")</script>', unsafe_allow_html=True)

    if actual_render == "recchatbox":
        st.session_state.followup_questions = generate_followup_questions(question, ans)
    else:
        st.session_state.followup_questions = []

    st.rerun()

# ==================== 侧边栏（透明底边框 POI 按钮）====================
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
        icon = "◻️"
    poi_name = POI_NAMES[pid]
    # 使用 use_container_width 让按钮占满宽度
    if st.sidebar.button(f"{icon} {poi_name}", key=f"nav_{pid}", use_container_width=True):
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
if st.sidebar.button("📥 导出日志 CSV", use_container_width=True):
    if st.session_state.logs:
        df = pd.DataFrame(st.session_state.logs)
        st.sidebar.download_button("点击下载", data=df.to_csv(index=False), file_name=f"{st.session_state.participant_id}_logs.csv", use_container_width=True)

# ==================== 主界面渲染（新布局）====================
# 1. Hero 区（大主图 + 内置四个透明按钮）
st.markdown("""
<div class="jn-hero reveal">
  <div class="jn-hero-title">惠山古镇<br><span>AI 导览员</span></div>
  <div class="jn-hero-sub">3A 智能问答 · 非遗知识库 · 语音陪伴</div>
  <div class="jn-hero-actions">
    <div class="jn-hero-action" id="btn_book">📅 景区预约</div>
    <div class="jn-hero-action" id="btn_ai">🤖 问AI</div>
    <div class="jn-hero-action" id="btn_calendar">🗓️ 活动日历</div>
    <div class="jn-hero-action" id="btn_history">🏛️ 历史名迹</div>
  </div>
</div>
""", unsafe_allow_html=True)

# 2. 搜索栏（原输入框移到这里，但保持功能）
with st.container():
    st.markdown('<div class="jn-search reveal">搜索景点、历史人物、非遗故事或推荐路线</div>', unsafe_allow_html=True)

# 3. 五个 POI 卡片（带图片）
st.markdown('<div class="reveal"><h3 style="font-weight:800;">🏞️ 探索点位</h3></div>', unsafe_allow_html=True)
poi_grid_html = '<div class="jn-poi-grid reveal">'
for pid in POI_ORDER:
    poi = poi_database[pid]
    img_src = POI_IMAGES.get(pid, "")
    poi_grid_html += f"""
    <div class="jn-poi-card">
        <img class="jn-poi-img" src="{img_src}" alt="{escape(poi['name'])}">
        <div class="jn-poi-content">
            <div class="jn-poi-name">{escape(poi['name'])}</div>
            <div class="jn-poi-desc">{escape(poi['info'][:150])}{"…" if len(poi['info']) > 150 else ""}</div>
        </div>
    </div>
    """
poi_grid_html += '</div>'
st.markdown(poi_grid_html, unsafe_allow_html=True)

# 4. 当前点位详情 + 语音按钮（保持原有内容）
st.markdown(f"""
<div class="jn-card reveal">
    <div style="font-size: 20px; font-weight: 800;">📍 当前：{escape(current_poi['name'])}</div>
    <div style="margin-top: 12px; line-height: 1.7;">{escape(current_poi['info'])}</div>
</div>
""", unsafe_allow_html=True)

voice_col, _ = st.columns([1, 5])
with voice_col:
    if st.button("🔊 朗读介绍", key="speak_intro", help="点击聆听景点介绍"):
        safe_info = current_poi["info"].replace("\\", "\\\\").replace('"', '\\"')
        st.markdown(f'<script>speakText("{safe_info}")</script>', unsafe_allow_html=True)

# 5. AI 聊天界面（保持原有逻辑）
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

# 6. 下一站按钮
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
