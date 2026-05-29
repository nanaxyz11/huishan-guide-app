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

# ==================== 本地图片资源 Base64 处理 ====================
ASSET_DIR = Path(__file__).resolve().parent / "惠山古镇5POI图"

def asset_uri(filename):
    """将本地图片转为 base64 内嵌，避免路径问题"""
    path = ASSET_DIR / filename
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    data = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{data}"

# 英雄区背景（主图）
HERO_BG = asset_uri("主图.jpg")

# 5个POI的图片（放在每个POI介绍旁）
POI_IMAGES = {
    "fanwenzheng_gongci": asset_uri("范文公正祠.jpg"),
    "guhuashanmen": asset_uri("金莲桥.jpg"),
    "bayinjian": asset_uri("八音涧.jpg"),
    "zhulu_shanfang": asset_uri("竹炉山房.jpg"),
    "erquan": asset_uri("二泉1.jpg"),
}

# Masonry 网格图片（8张）
MASONRY_IMAGES = [
    ("范文正公祠", asset_uri("范文公正祠.jpg")),
    ("金莲桥", asset_uri("金莲桥.jpg")),
    ("八音涧", asset_uri("八音涧.jpg")),
    ("知鱼槛", asset_uri("知鱼栏.jpg")),
    ("竹炉山房", asset_uri("竹炉山房.jpg")),
    ("天下第二泉", asset_uri("二泉1.jpg")),
    ("二泉水景", asset_uri("二泉2.jpg")),
    ("二泉石刻", asset_uri("二泉3.jpg")),
]

# ==================== 路线别名（原功能保留） ====================
ROUTE_ALIASES = {
    "范文正公祠": "fanwenzheng_gongci",
    "范文公正祠": "fanwenzheng_gongci",
    "范仲淹": "fanwenzheng_gongci",
    "古华山门": "guhuashanmen",
    "金莲桥": "guhuashanmen",
    "八音涧": "bayinjian",
    "知鱼槛": "bayinjian",
    "知鱼栏": "bayinjian",
    "寄畅园": "bayinjian",
    "竹炉山房": "zhulu_shanfang",
    "竹炉": "zhulu_shanfang",
    "天下第二泉": "erquan",
    "二泉": "erquan",
    "惠山泉": "erquan",
}

# ==================== 全新视觉样式（玻璃态 + 动态 Aurora + Masonry + 视差 + Reveal + 跑马灯） ====================
st.markdown(f"""
<style>
/* ---------- 全局变量 ---------- */
:root {{
  --jn-blue:#1f8fff; --jn-cyan:#62dce8; --jn-green:#34d399;
  --jn-orange:#df7a2d; --jn-ink:#172326; --jn-muted:#6f7f82;
  --jn-glass:rgba(255,255,255,.64); --jn-line:rgba(31,143,255,.22);
  --jn-radius:24px; --parallax-y:0px;
}}
.stApp {{
  color:var(--jn-ink);
  background:linear-gradient(180deg,#dff8fb 0%,#f8fff8 100%);
  overflow-x:hidden;
}}
/* 动态 Aurora 背景层 */
.stApp::before {{
  content:""; position:fixed; inset:-20%; z-index:-3;
  background:
    radial-gradient(circle at 18% 20%,rgba(98,220,232,.52),transparent 28%),
    radial-gradient(circle at 74% 18%,rgba(52,211,153,.38),transparent 26%),
    radial-gradient(circle at 52% 78%,rgba(31,143,255,.22),transparent 32%);
  filter:blur(28px); animation:auroraFlow 18s ease-in-out infinite alternate;
}}
@keyframes auroraFlow {{
  0% {{ transform:translate3d(-2%,-1%,0) scale(1); }}
  50% {{ transform:translate3d(3%,2%,0) scale(1.08); }}
  100% {{ transform:translate3d(-1%,4%,0) scale(1.03); }}
}}
/* 噪点纹理 + 视差背景 */
.stApp::after {{
  content:""; position:fixed; inset:-8%; z-index:-2;
  transform:translateY(calc(var(--parallax-y) * .5));
  background-image:radial-gradient(circle,rgba(255,255,255,.34) 1px,transparent 1px);
  background-size:18px 18px; opacity:.45; pointer-events:none;
}}
[data-testid="stHeader"] {{ background:rgba(223,247,251,.62); backdrop-filter:blur(18px); }}
.block-container {{ max-width:1160px; padding-top:1.2rem; }}

/* 玻璃态卡片通用样式（强模糊 + 噪点） */
.jn-glass, .jn-bento-card, .jn-poi-card, .jn-masonry-item {{
  position:relative; background:var(--jn-glass); border:1px solid rgba(255,255,255,.7);
  border-radius:var(--jn-radius); box-shadow:0 18px 46px rgba(35,118,138,.14);
  backdrop-filter:blur(26px) saturate(1.3); overflow:hidden;
}}
/* 噪点叠加 */
.jn-glass::after, .jn-bento-card::after, .jn-poi-card::after {{
  content:""; position:absolute; inset:0; opacity:.16; pointer-events:none;
  background-image:radial-gradient(circle,rgba(255,255,255,.9) .7px,transparent .7px);
  background-size:7px 7px;
}}

/* 英雄区（加大高度，内部放置四个功能按钮） */
.jn-hero {{
  position:relative; min-height:480px; border-radius:34px; padding:34px; overflow:hidden;
  background:linear-gradient(90deg,rgba(5,22,26,.78),rgba(5,22,26,.22) 62%,rgba(5,22,26,.08)), url("{HERO_BG}");
  background-size:cover; background-position:center; box-shadow:0 30px 80px rgba(13,96,120,.24);
}}
.jn-hero-title {{
  max-width:720px; font-size:clamp(40px,7vw,76px); line-height:1.02;
  font-weight:950; color:white; text-shadow:0 8px 26px rgba(0,0,0,.36);
}}
.jn-hero-title span {{ color:#8ff7ff; }}
.jn-hero-sub {{ margin-top:16px; max-width:560px; color:rgba(255,255,255,.88); font-size:17px; line-height:1.8; }}
/* 四个透明按钮置于 Hero 底部 */
.jn-hero-actions {{
  position:absolute; left:26px; right:26px; bottom:24px;
  display:grid; grid-template-columns:repeat(4,1fr); gap:12px;
}}
.jn-hero-action {{
  display:flex; align-items:center; justify-content:center; gap:9px; min-height:58px;
  border:1px solid rgba(255,255,255,.48); border-radius:20px;
  background:rgba(255,255,255,.12); color:white; font-weight:800;
  backdrop-filter:blur(18px); transition:.22s ease; cursor:pointer;
}}
.jn-hero-action:hover {{
  transform:translateY(-3px) scale(1.025); box-shadow:0 20px 44px rgba(20,98,118,.22);
  background:rgba(255,255,255,.24);
}}

/* 搜索表单（放在 Hero 下方） */
.jn-route-form {{ margin:18px 0 22px; padding:18px; }}

/* Bento 网格（保留但微调） */
.jn-bento {{ display:grid; grid-template-columns:repeat(6,1fr); gap:16px; margin:18px 0; }}
.jn-bento-card {{ min-height:148px; padding:22px; transition:.22s ease; }}
.jn-bento-large {{ grid-column:span 3; min-height:220px; }}
.jn-bento-wide {{ grid-column:span 2; }}
.jn-bento-small {{ grid-column:span 1; }}
.jn-bento-kicker {{ color:var(--jn-blue); font-size:13px; font-weight:900; }}
.jn-bento-title {{ margin-top:8px; font-size:24px; font-weight:950; }}
.jn-bento-text {{ margin-top:10px; color:var(--jn-muted); line-height:1.65; }}

/* POI 列表（每个 POI 展示图片 + 文字） */
.jn-poi-list {{ display:grid; gap:16px; }}
.jn-poi-card {{
  display:grid; grid-template-columns:minmax(180px,28%) 1fr; gap:20px; padding:16px;
}}
.jn-poi-card img {{ width:100%; height:178px; object-fit:cover; border-radius:18px; }}
.jn-poi-title {{ font-size:22px; font-weight:950; }}
.jn-poi-desc {{ color:var(--jn-muted); line-height:1.72; }}

/* Masonry 图片网格（自适应列数） */
.jn-masonry {{ columns:3 240px; column-gap:16px; margin-top:16px; }}
.jn-masonry-item {{ display:inline-block; width:100%; margin:0 0 16px; }}
.jn-masonry-item img {{ width:100%; display:block; border-radius:22px; }}
.jn-masonry-caption {{ padding:12px 14px 14px; font-weight:800; }}

/* Skeleton 骨架屏 */
.jn-skeleton {{
  height:110px; border-radius:22px;
  background:linear-gradient(90deg,rgba(255,255,255,.45),rgba(255,255,255,.82),rgba(255,255,255,.45));
  background-size:220% 100%; animation:skeletonMove 1.25s infinite linear;
  border:1px solid rgba(255,255,255,.7);
}}
@keyframes skeletonMove {{ from {{ background-position:220% 0; }} to {{ background-position:-220% 0; }} }}

/* Reveal 动画 */
.reveal {{ opacity:0; transform:translateY(22px); transition:opacity .7s ease,transform .7s ease; }}
.reveal.is-visible {{ opacity:1; transform:translateY(0); }}

/* 跑马灯（无限滚动） */
.jn-marquee {{
  margin:28px 0 12px; overflow:hidden; border-radius:999px;
  border:1px solid var(--jn-line); background:rgba(255,255,255,.56); backdrop-filter:blur(22px);
}}
.jn-marquee-track {{ display:flex; width:max-content; gap:12px; padding:12px; animation:marquee 24s linear infinite; }}
.jn-marquee:hover .jn-marquee-track {{ animation-play-state:paused; }}
.jn-logo {{ padding:8px 16px; border-radius:999px; background:rgba(31,143,255,.1); color:#126fbf; font-weight:900; white-space:nowrap; }}
@keyframes marquee {{ to {{ transform:translateX(-50%); }} }}

/* 按钮通用样式 */
div.stButton > button {{
  border-radius:999px; border:1px solid var(--jn-line); background:rgba(255,255,255,.34);
  color:#126fbf; font-weight:850; transition:.2s ease; box-shadow:0 10px 24px rgba(31,143,255,.10);
}}
div.stButton > button:hover {{
  transform:translateY(-2px) scale(1.018); box-shadow:0 16px 34px rgba(31,143,255,.20);
}}
/* 侧边栏透明按钮（左侧5个POI按钮） */
[data-testid="stSidebar"] .stButton button {{
  background:transparent !important;
  border:1px solid var(--jn-blue) !important;
  color:var(--jn-blue) !important;
  box-shadow:none !important;
}}
[data-testid="stSidebar"] .stButton button:hover {{
  background:rgba(31,143,255,.12) !important;
  transform:translateX(4px);
}}
[data-testid="stSidebar"] {{
  background:rgba(255,255,255,.56); backdrop-filter:blur(28px); border-right:1px solid var(--jn-line);
}}
.source-chip {{
  display:inline-block; background:rgba(31,143,255,.12); color:#126fbf;
  padding:4px 12px; border-radius:999px; font-size:.72rem; font-weight:800; margin-top:8px;
}}
@media (max-width:760px) {{
  .jn-hero {{ min-height:560px; padding:24px; }}
  .jn-hero-actions {{ grid-template-columns:repeat(2,1fr); }}
  .jn-bento {{ grid-template-columns:1fr; }}
  .jn-bento-card,.jn-bento-large,.jn-bento-wide,.jn-bento-small {{ grid-column:span 1; }}
  .jn-poi-card {{ grid-template-columns:1fr; }}
}}
</style>

<script>
// 视差滚动
function initParallax() {{
  const root = document.documentElement;
  window.addEventListener("scroll", () => {{
    root.style.setProperty("--parallax-y", `${{window.scrollY * 0.5}}px`);
  }}, {{ passive:true }});
}}

// Reveal on scroll
function initReveal() {{
  const observer = new IntersectionObserver((entries) => {{
    entries.forEach(entry => {{
      if (entry.isIntersecting) entry.target.classList.add("is-visible");
    }});
  }}, {{ threshold:.12 }});
  document.querySelectorAll(".reveal").forEach(el => observer.observe(el));
}}

// 语音朗读（保持不变）
window.speakText = function(text) {{
  if (!window.speechSynthesis) return;
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "zh-CN";
  utterance.rate = .9;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}};

// 功能按钮交互：问AI滚动到聊天区
function scrollToChat() {{
  const chatInput = document.querySelector('div[data-testid="stChatInput"] textarea');
  if (chatInput) {{
    chatInput.scrollIntoView({{ behavior: "smooth", block: "center" }});
    chatInput.focus();
  }} else {{
    alert("请先开始对话");
  }}
}}
function showComingSoon() {{
  alert("功能开发中，敬请期待");
}}

setTimeout(() => {{
  initParallax();
  initReveal();
}}, 400);
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

# ==================== 处理用户提问（含 Skeleton 动画） ====================
def handle_question(question):
    # 显示骨架屏动画
    skeleton = st.empty()
    skeleton.markdown("""
    <div class="jn-skeleton"></div>
    <div style="height:10px"></div>
    <div class="jn-skeleton" style="height:58px;width:72%;"></div>
    """, unsafe_allow_html=True)

    ans, src, chunks, elapsed = simulate_rag_engine(question)
    skeleton.empty()  # 移除骨架屏

    st.session_state.chat_messages.append({"role": "user", "content": question})
    st.session_state.chat_messages.append({"role": "assistant", "content": ans, "source": src})
    log_experimental_event("question_submitted", question, elapsed, chunks, src)

    # 朗读回答
    safe_ans = ans.replace('"', '\\"')
    st.markdown(f'<script>speakText("{safe_ans}")</script>', unsafe_allow_html=True)

    if actual_render == "recchatbox":
        st.session_state.followup_questions = generate_followup_questions(question, ans)
    else:
        st.session_state.followup_questions = []

    st.toast("AI 导览员已生成回答", icon="✨")
    st.rerun()

# ==================== 辅助函数：跳转 POI ====================
def jump_to_poi(pid):
    st.session_state.current_poi_index = POI_ORDER.index(pid)
    st.session_state.chat_messages = []
    st.session_state.followup_questions = []
    st.session_state.ai_response = None
    st.session_state.page_load_time = time.time()
    st.query_params["poi"] = pid
    st.query_params["pid"] = st.session_state.participant_id
    st.toast(f"已为你定位到：{POI_NAMES[pid]}", icon="⌖")
    st.rerun()

# ==================== 侧边栏（左侧5个POI按钮已变为透明边框） ====================
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
        icon = "◆"
    elif idx == st.session_state.current_poi_index:
        icon = "⌖"
    else:
        icon = "◇"
    poi_name = POI_NAMES[pid]
    if st.sidebar.button(f"{icon} {poi_name}", key=f"nav_{pid}", use_container_width=True):
        if idx != st.session_state.current_poi_index:
            st.session_state.current_poi_index = idx
            st.session_state.chat_messages = []
            st.session_state.followup_questions = []
            st.session_state.ai_response = None
            st.session_state.page_load_time = time.time()
            st.query_params["poi"] = pid
            st.query_params["pid"] = st.session_state.participant_id
            st.toast(f"已切换到：{poi_name}", icon="⌖")
            st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("📥 导出日志 CSV"):
    if st.session_state.logs:
        df = pd.DataFrame(st.session_state.logs)
        st.sidebar.download_button("点击下载", data=df.to_csv(index=False), file_name=f"{st.session_state.participant_id}_logs.csv")

# ==================== 主界面渲染 ====================
# Hero 区（加大，内部包含四个透明功能按钮）
st.markdown(f"""
<div class="jn-hero reveal">
  <div class="jn-hero-title">惠山古镇<br><span>历史街区</span></div>
  <div class="jn-hero-sub">
    面向 3A 实验的江南科技风 AI 导览界面：在真实点位、文化知识库与智能问答之间建立轻盈、可探索的游览路径。
  </div>
  <div class="jn-hero-actions">
    <div class="jn-hero-action" onclick="showComingSoon()">📅 景区预约</div>
    <div class="jn-hero-action" onclick="scrollToChat()">🤖 问AI</div>
    <div class="jn-hero-action" onclick="showComingSoon()">📆 活动日历</div>
    <div class="jn-hero-action" onclick="showComingSoon()">🏛️ 历史名迹</div>
  </div>
</div>
""", unsafe_allow_html=True)

# 搜索表单（移到 Hero 下方）
with st.form("route_search_form", clear_on_submit=True):
    st.markdown('<div class="jn-route-form jn-glass reveal">', unsafe_allow_html=True)
    route_query = st.text_input(
        "路线搜索",
        placeholder="搜索景点、历史人物、非遗故事或推荐路线",
        label_visibility="collapsed",
    )
    route_submit = st.form_submit_button("搜索并跳转", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

if route_submit and route_query:
    matched_pid = None
    for alias, pid in ROUTE_ALIASES.items():
        if alias in route_query:
            matched_pid = pid
            break
    if matched_pid:
        jump_to_poi(matched_pid)
    else:
        st.toast("没有找到对应路线，请试试“二泉 / 金莲桥 / 竹炉山房”。", icon="⌕")

# Bento 网格（保留）
st.markdown("""
<div class="jn-bento reveal">
  <div class="jn-bento-card jn-bento-large">
    <div class="jn-bento-kicker">3A RAG EXPERIENCE</div>
    <div class="jn-bento-title">AI 导览问答</div>
    <div class="jn-bento-text">基于五个惠山古镇 POI 的知识库，支持自由提问、推荐追问与来源提示。</div>
  </div>
  <div class="jn-bento-card jn-bento-wide">
    <div class="jn-bento-kicker">ROUTE</div>
    <div class="jn-bento-title">路线推荐</div>
    <div class="jn-bento-text">从祠堂、古桥、园林、茶事到二泉，形成连续游览路径。</div>
  </div>
  <div class="jn-bento-card jn-bento-small">
    <div class="jn-bento-kicker">VOICE</div>
    <div class="jn-bento-title">语音</div>
    <div class="jn-bento-text">朗读介绍。</div>
  </div>
  <div class="jn-bento-card jn-bento-wide">
    <div class="jn-bento-kicker">LOG</div>
    <div class="jn-bento-title">实验记录</div>
    <div class="jn-bento-text">记录停留、提问、回答时长与点位切换。</div>
  </div>
  <div class="jn-bento-card jn-bento-wide">
    <div class="jn-bento-kicker">CULTURE</div>
    <div class="jn-bento-title">江南文脉</div>
    <div class="jn-bento-text">整合名臣、泉茶、园林、寺桥和音乐记忆。</div>
  </div>
</div>
""", unsafe_allow_html=True)

# POI 卡片列表（5个，每个旁边展示对应图片）
st.markdown('<div class="jn-poi-list reveal">', unsafe_allow_html=True)
for pid in POI_ORDER:
    poi = poi_database[pid]
    img_src = POI_IMAGES[pid]
    st.markdown(f"""
    <div class="jn-poi-card jn-glass">
      <img src="{img_src}" alt="{escape(poi['name'])}">
      <div>
        <div class="jn-poi-title">{escape(poi['name'])}</div>
        <div class="jn-poi-desc">{escape(poi['info'])}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# Masonry 图片网格
st.markdown('<div class="jn-masonry reveal">', unsafe_allow_html=True)
for caption, img in MASONRY_IMAGES:
    st.markdown(f"""
    <div class="jn-masonry-item">
      <img src="{img}" alt="{escape(caption)}">
      <div class="jn-masonry-caption">{escape(caption)}</div>
    </div>
    """, unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# 当前 POI 详情卡片
st.markdown(f"""
<div class="jn-glass reveal" style="padding:22px;margin:20px 0;">
  <div class="jn-bento-kicker">CURRENT POI</div>
  <div class="jn-bento-title">{escape(current_poi['name'])}</div>
  <div class="jn-bento-text">{escape(current_poi['info'])}</div>
</div>
""", unsafe_allow_html=True)

# 语音按钮
voice_col, _ = st.columns([1, 5])
with voice_col:
    if st.button("🔊 朗读介绍", key="speak_intro", help="点击聆听景点介绍"):
        safe_info = current_poi["info"].replace("\\", "\\\\").replace('"', '\\"')
        st.markdown(f'<script>speakText("{safe_info}")</script>', unsafe_allow_html=True)

# 聊天界面
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

# 底部无限跑马灯
st.markdown("""
<div class="jn-marquee reveal">
  <div class="jn-marquee-track">
    <span class="jn-logo">3A Experiment</span><span class="jn-logo">Streamlit</span>
    <span class="jn-logo">Dify RAG</span><span class="jn-logo">Supabase</span>
    <span class="jn-logo">Huishan Ancient Town</span><span class="jn-logo">AI Guide</span>
    <span class="jn-logo">Jiangnan Tech</span><span class="jn-logo">Cultural Heritage</span>
    <span class="jn-logo">3A Experiment</span><span class="jn-logo">Streamlit</span>
    <span class="jn-logo">Dify RAG</span><span class="jn-logo">Supabase</span>
    <span class="jn-logo">Huishan Ancient Town</span><span class="jn-logo">AI Guide</span>
    <span class="jn-logo">Jiangnan Tech</span><span class="jn-logo">Cultural Heritage</span>
  </div>
</div>
""", unsafe_allow_html=True)

# 切换点位 / 完成实验
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
