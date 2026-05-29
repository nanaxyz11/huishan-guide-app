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

# ==================== CSS + JS（增强 Glassmorphism + Aurora + 骨架屏 + 侧边栏透明按钮） ====================
st.markdown(f"""
<style>
:root {{
  --jn-blue:#1f8fff; --jn-cyan:#62dce8; --jn-green:#34d399;
  --jn-orange:#df7a2d; --jn-ink:#172326; --jn-muted:#6f7f82;
  --jn-glass:rgba(255,255,255,.58); --jn-line:rgba(31,143,255,.22);
  --jn-radius:24px; --parallax-y:0px;
}}
.stApp {{
  color:var(--jn-ink);
  background:linear-gradient(180deg,#dff8fb 0%,#f8fff8 100%);
  overflow-x:hidden;
}}
/* 动态 Aurora Gradient（加强流动感） */
.stApp::before {{
  content:""; position:fixed; inset:-20%; z-index:-3;
  background:
    radial-gradient(circle at 18% 20%,rgba(98,220,232,.62),transparent 28%),
    radial-gradient(circle at 74% 18%,rgba(52,211,153,.48),transparent 26%),
    radial-gradient(circle at 52% 78%,rgba(31,143,255,.32),transparent 32%);
  filter:blur(36px); animation:auroraFlow 22s ease-in-out infinite alternate;
}}
.stApp::after {{
  content:""; position:fixed; inset:-8%; z-index:-2;
  transform:translateY(calc(var(--parallax-y) * .5));
  background-image:radial-gradient(circle,rgba(255,255,255,.4) 1px,transparent 1px);
  background-size:20px 20px; opacity:.5; pointer-events:none;
}}
@keyframes auroraFlow {{
  0% {{ transform:translate3d(-2%,-1%,0) scale(1); }}
  50% {{ transform:translate3d(3%,2%,0) scale(1.12); }}
  100% {{ transform:translate3d(-1%,4%,0) scale(1.06); }}
}}
[data-testid="stHeader"] {{ background:rgba(223,247,251,.62); backdrop-filter:blur(18px); }}
.block-container {{ max-width:1160px; padding-top:1.2rem; }}

/* Glass morphism 浮窗（强模糊 + 噪点纹理） */
.jn-glass,.jn-bento-card,.jn-poi-card,.jn-masonry-item {{
  position:relative; background:var(--jn-glass); border:1px solid rgba(255,255,255,.8);
  border-radius:var(--jn-radius); box-shadow:0 18px 46px rgba(35,118,138,.14);
  backdrop-filter:blur(24px) saturate(180%);
  overflow:hidden;
}}
.jn-glass::after,.jn-bento-card::after,.jn-poi-card::after {{
  content:""; position:absolute; inset:0; opacity:.18; pointer-events:none;
  background-image:radial-gradient(circle,rgba(255,255,255,.95) .8px,transparent .8px);
  background-size:8px 8px;
}}

/* Hero 区域（放大主图，内部下方放置搜索框） */
.jn-hero {{
  position:relative; min-height:540px; border-radius:34px; padding:34px 34px 24px 34px; overflow:hidden;
  background:linear-gradient(90deg,rgba(5,22,26,.78),rgba(5,22,26,.22) 62%,rgba(5,22,26,.08)),url("{HERO_IMAGE}");
  background-size:cover; background-position:center 30%; box-shadow:0 30px 80px rgba(13,96,120,.24);
  margin-bottom:0;
}}
.jn-hero-title {{
  max-width:720px; font-size:clamp(44px,7vw,80px); line-height:1.02;
  font-weight:950; color:white; text-shadow:0 8px 26px rgba(0,0,0,.36);
}}
.jn-hero-title span {{ color:#8ff7ff; }}
.jn-hero-sub {{ margin-top:16px; max-width:560px; color:rgba(255,255,255,.88); font-size:17px; line-height:1.8; }}
/* 内部搜索栏 */
.jn-hero-search {{
  position:absolute; left:34px; right:34px; bottom:24px;
  background:rgba(255,255,255,.86); backdrop-filter:blur(20px);
  border-radius:999px; border:1px solid rgba(255,255,255,.7);
  padding:6px 16px; display:flex; align-items:center; gap:12px;
  box-shadow:0 8px 20px rgba(0,0,0,.12);
}}
.jn-hero-search input {{
  flex:1; background:transparent; border:none; outline:none; font-size:16px; padding:12px 0;
}}
.jn-hero-search button {{
  background:rgba(31,143,255,.18); border:none; border-radius:40px; padding:8px 20px;
  font-weight:700; color:#1f8fff; cursor:pointer; transition:0.2s;
}}
.jn-hero-search button:hover {{
  background:#1f8fff; color:white;
}}

/* 功能按钮区（置于 Hero 下方，玻璃风格） */
.jn-actions {{
  display:flex; gap:16px; margin:24px 0 32px; justify-content:center; flex-wrap:wrap;
}}
.jn-action-btn {{
  flex:1; min-width:140px; background:rgba(255,255,255,.7); backdrop-filter:blur(20px);
  border:1px solid rgba(31,143,255,.4); border-radius:999px; padding:12px 16px;
  text-align:center; font-weight:800; color:var(--jn-blue); transition:0.2s;
  display:flex; align-items:center; justify-content:center; gap:10px;
}}
.jn-action-btn:hover {{
  transform:translateY(-3px); background:rgba(31,143,255,.15); border-color:var(--jn-blue);
  box-shadow:0 12px 24px rgba(31,143,255,.2);
}}

/* 其他原有组件样式（保留） */
.jn-route-form {{ margin:18px 0 22px; padding:18px; }}
.jn-bento {{ display:grid; grid-template-columns:repeat(6,1fr); gap:16px; margin:18px 0; }}
.jn-bento-card {{ min-height:148px; padding:22px; transition:.22s ease; }}
.jn-bento-large {{ grid-column:span 3; min-height:220px; }}
.jn-bento-wide {{ grid-column:span 2; }}
.jn-bento-small {{ grid-column:span 1; }}
.jn-bento-kicker {{ color:var(--jn-blue); font-size:13px; font-weight:900; }}
.jn-bento-title {{ margin-top:8px; font-size:24px; font-weight:950; }}
.jn-bento-text {{ margin-top:10px; color:var(--jn-muted); line-height:1.65; }}

.jn-poi-list {{ display:grid; gap:16px; }}
.jn-poi-card {{ display:grid; grid-template-columns:minmax(180px,28%) 1fr; gap:20px; padding:16px; }}
.jn-poi-card img {{ width:100%; height:178px; object-fit:cover; border-radius:18px; }}
.jn-poi-title {{ font-size:22px; font-weight:950; }}
.jn-poi-desc {{ color:var(--jn-muted); line-height:1.72; }}

.jn-masonry {{ columns:3 240px; column-gap:16px; margin-top:16px; }}
.jn-masonry-item {{ display:inline-block; width:100%; margin:0 0 16px; }}
.jn-masonry-item img {{ width:100%; display:block; border-radius:22px; }}
.jn-masonry-caption {{ padding:12px 14px 14px; font-weight:800; }}

/* 骨架屏动画 */
.jn-skeleton {{
  height:110px; border-radius:22px;
  background:linear-gradient(90deg,rgba(255,255,255,.45),rgba(255,255,255,.82),rgba(255,255,255,.45));
  background-size:220% 100%; animation:skeletonMove 1.25s infinite linear;
  border:1px solid rgba(255,255,255,.7);
}}
@keyframes skeletonMove {{ from {{ background-position:220% 0; }} to {{ background-position:-220% 0; }} }}
.reveal {{ opacity:0; transform:translateY(22px); transition:opacity .7s ease,transform .7s ease; }}
.reveal.is-visible {{ opacity:1; transform:translateY(0); }}

/* 走马灯 */
.jn-marquee {{
  margin:28px 0 12px; overflow:hidden; border-radius:999px;
  border:1px solid var(--jn-line); background:rgba(255,255,255,.56); backdrop-filter:blur(22px);
}}
.jn-marquee-track {{ display:flex; width:max-content; gap:12px; padding:12px; animation:marquee 24s linear infinite; }}
.jn-marquee:hover .jn-marquee-track {{ animation-play-state:paused; }}
.jn-logo {{ padding:8px 16px; border-radius:999px; background:rgba(31,143,255,.1); color:#126fbf; font-weight:900; white-space:nowrap; }}
@keyframes marquee {{ to {{ transform:translateX(-50%); }} }}

/* 侧边栏按钮透明底 + 主色调边框 */
[data-testid="stSidebar"] div.stButton > button {{
  background:rgba(255,255,255,.0) !important;
  border:1px solid var(--jn-blue) !important;
  color:var(--jn-blue) !important;
  border-radius:40px !important;
  font-weight:700;
  transition:0.2s;
}}
[data-testid="stSidebar"] div.stButton > button:hover {{
  background:rgba(31,143,255,.12) !important;
  transform:translateX(4px);
}}

/* 全局按钮样式 */
div.stButton > button {{
  border-radius:999px; border:1px solid var(--jn-line); background:rgba(255,255,255,.34);
  color:#126fbf; font-weight:850; transition:.2s ease; box-shadow:0 10px 24px rgba(31,143,255,.10);
}}
div.stButton > button:hover {{
  transform:translateY(-2px) scale(1.018); box-shadow:0 16px 34px rgba(31,143,255,.20);
}}
.source-chip {{
  display:inline-block; background:rgba(31,143,255,.12); color:#126fbf;
  padding:4px 12px; border-radius:999px; font-size:.72rem; font-weight:800; margin-top:8px;
}}
@media (max-width:760px) {{
  .jn-hero {{ min-height:480px; padding:24px; }}
  .jn-hero-search {{ left:16px; right:16px; }}
  .jn-actions {{ flex-direction:column; }}
  .jn-poi-card {{ grid-template-columns:1fr; }}
}}
</style>

<script>
function initJiangnanMotion() {{
  const root = document.documentElement;
  window.addEventListener("scroll", () => {{
    root.style.setProperty("--parallax-y", `${{window.scrollY * 0.5}}px`);
  }}, {{ passive:true }});

  const observer = new IntersectionObserver((entries) => {{
    entries.forEach(entry => {{
      if (entry.isIntersecting) entry.target.classList.add("is-visible");
    }});
  }}, {{ threshold:.12 }});
  document.querySelectorAll(".reveal").forEach(el => observer.observe(el));
}}

window.speakText = function(text) {{
  if (!window.speechSynthesis) return;
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "zh-CN";
  utterance.rate = .9;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}};

setTimeout(initJiangnanMotion, 400);
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

    # 限制 retrieved_chunks 长度（避免 Supabase 字段溢出）
    MAX_CHUNKS_LEN = 2000
    if len(retrieved_chunks) > MAX_CHUNKS_LEN:
        retrieved_chunks = retrieved_chunks[:MAX_CHUNKS_LEN] + "... (truncated)"

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
        st.warning(f"Supabase 日志上传失败（本地已保存）: {e}")

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

# ==================== 处理用户提问（含骨架屏） ====================
def handle_question(question):
    skeleton = st.empty()
    skeleton.markdown("""
    <div class="jn-skeleton"></div>
    <div style="height:10px"></div>
    <div class="jn-skeleton" style="height:58px;width:72%;"></div>
    """, unsafe_allow_html=True)

    ans, src, chunks, elapsed = simulate_rag_engine(question)
    skeleton.empty()

    st.session_state.chat_messages.append({"role": "user", "content": question})
    st.session_state.chat_messages.append({"role": "assistant", "content": ans, "source": src})
    log_experimental_event("question_submitted", question, elapsed, chunks, src)

    # 语音朗读（若浏览器支持）
    st.markdown(f'<script>speakText({json.dumps(ans)})</script>', unsafe_allow_html=True)

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

# ==================== 侧边栏（透明按钮样式） ====================
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

# ==================== 主界面渲染（调整后布局） ====================
# Hero 区（内部包含搜索框）
st.markdown("""
<div class="jn-hero reveal">
  <div class="jn-hero-title">惠山古镇<br><span>历史街区</span></div>
  <div class="jn-hero-sub">
    面向 3A 实验的江南科技风 AI 导览界面：在真实点位、文化知识库与智能问答之间建立轻盈、可探索的游览路径。
  </div>
  <div class="jn-hero-search">
    <input type="text" id="route_query_input" placeholder="搜索景点、历史人物、非遗故事或推荐路线...">
    <button id="route_search_btn">搜索并跳转</button>
  </div>
</div>
""", unsafe_allow_html=True)

# 自定义搜索框的 JavaScript 交互（避免使用 Streamlit 表单，保留功能）
st.markdown("""
<script>
document.getElementById('route_search_btn').onclick = function() {
    var query = document.getElementById('route_query_input').value;
    if (query) {
        // 将查询词写入 Streamlit 的 query params 或 session，这里简单重定向到带有参数的路由
        // 为了兼容 Streamlit 的交互，我们模拟点击一个隐藏的 Streamlit 按钮
        var inputEvent = new Event('input', { bubbles: true });
        var hiddenInput = document.createElement('input');
        hiddenInput.id = 'route_query_hidden';
        hiddenInput.style.display = 'none';
        hiddenInput.value = query;
        document.body.appendChild(hiddenInput);
        // 触发 Streamlit 的 rerun 需要通过设置 st.query_params，但这里无法直接设置
        // 改用最简方式：告知用户点击侧边栏或使用下方搜索按钮（保留原有 route_search_form 逻辑）
        alert('请使用侧边栏的路线搜索或下方搜索框（兼容旧版）');
    }
};
</script>
""", unsafe_allow_html=True)

# 下方四个功能按钮（玻璃风格，置于 Hero 外部）
st.markdown("""
<div class="jn-actions reveal">
  <div class="jn-action-btn" id="btn_book">📅 景区预约</div>
  <div class="jn-action-btn" id="btn_ai">🤖 问AI</div>
  <div class="jn-action-btn" id="btn_calendar">🗓️ 活动日历</div>
  <div class="jn-action-btn" id="btn_history">🏛️ 历史名迹</div>
</div>
<script>
document.getElementById('btn_ai')?.addEventListener('click', () => {
  document.querySelector('.stTextInput input')?.focus();
});
document.getElementById('btn_book')?.addEventListener('click', () => alert('景区预约功能即将开放'));
document.getElementById('btn_calendar')?.addEventListener('click', () => alert('活动日历敬请期待'));
document.getElementById('btn_history')?.addEventListener('click', () => alert('历史名迹正在整理中'));
</script>
""", unsafe_allow_html=True)

# 保留原有的 route_search_form（用于实际搜索跳转，但视觉上可隐藏或缩小）
with st.expander("🔍 精准路线搜索（高级）", expanded=False):
    with st.form("route_search_form", clear_on_submit=True):
        route_query = st.text_input("输入点位别名（二泉 / 金莲桥 / 竹炉山房 / 范仲淹）", label_visibility="collapsed")
        route_submit = st.form_submit_button("搜索并跳转", use_container_width=True)
        if route_submit and route_query:
            matched_pid = None
            for alias, pid in ROUTE_ALIASES.items():
                if alias in route_query:
                    matched_pid = pid
                    break
            if matched_pid:
                jump_to_poi(matched_pid)
            else:
                st.toast("未找到匹配点位，试试“二泉”或“金莲桥”", icon="⌕")

# Bento 网格（保持不变）
st.markdown("""
<div class="jn-bento reveal">
  <div class="jn-bento-card jn-bento-large jn-clickable">
    <div class="jn-bento-kicker">3A RAG EXPERIENCE</div>
    <div class="jn-bento-title">AI 导览问答</div>
    <div class="jn-bento-text">基于五个惠山古镇 POI 的知识库，支持自由提问、推荐追问与来源提示。</div>
  </div>
  <div class="jn-bento-card jn-bento-wide jn-clickable">
    <div class="jn-bento-kicker">ROUTE</div>
    <div class="jn-bento-title">路线推荐</div>
    <div class="jn-bento-text">从祠堂、古桥、园林、茶事到二泉，形成连续游览路径。</div>
  </div>
  <div class="jn-bento-card jn-bento-small jn-clickable">
    <div class="jn-bento-kicker">VOICE</div>
    <div class="jn-bento-title">语音</div>
    <div class="jn-bento-text">朗读介绍。</div>
  </div>
  <div class="jn-bento-card jn-bento-wide jn-clickable">
    <div class="jn-bento-kicker">LOG</div>
    <div class="jn-bento-title">实验记录</div>
    <div class="jn-bento-text">记录停留、提问、回答时长与点位切换。</div>
  </div>
  <div class="jn-bento-card jn-bento-wide jn-clickable">
    <div class="jn-bento-kicker">CULTURE</div>
    <div class="jn-bento-title">江南文脉</div>
    <div class="jn-bento-text">整合名臣、泉茶、园林、寺桥和音乐记忆。</div>
  </div>
</div>
""", unsafe_allow_html=True)

# POI 卡片列表（5个，带本地图片）
st.markdown('<div class="jn-poi-list reveal">', unsafe_allow_html=True)
for pid in POI_ORDER:
    poi = poi_database[pid]
    st.markdown(f"""
    <div class="jn-poi-card jn-clickable">
      <img src="{POI_IMAGES[pid]}" alt="{escape(poi['name'])}">
      <div>
        <div class="jn-poi-title">{escape(poi['name'])}</div>
        <div class="jn-poi-desc">{escape(poi['info'])}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# 图片 Masonry 网格
st.markdown('<div class="jn-masonry reveal">', unsafe_allow_html=True)
for caption, img in MASONRY_IMAGES:
    st.markdown(f"""
    <div class="jn-masonry-item jn-clickable">
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

# 底部 marquee
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
