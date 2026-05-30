import streamlit as st
import json
import os
import time
import random
import re
import uuid
from datetime import datetime
import pandas as pd
import requests
from supabase import create_client
from urllib.parse import quote

# ==================== 页面配置 ====================
st.set_page_config(page_title="惠山古镇 AI 导览 | 非遗数字体验", layout="centered", initial_sidebar_state="collapsed")

# ==================== GitHub 图片直链 ====================
def get_github_raw_url(filename: str) -> str:
    base = "https://raw.githubusercontent.com/nanaxyz11/huishan-guide-app/main/%E6%83%A0%E5%B1%B1%E5%8F%A45POI%E5%9B%BE/"
    return base + quote(filename)

MAIN_IMG_URL = get_github_raw_url("主图.jpg")

LOCAL_IMG_BASE = "/Users/clisl/Documents/huishan_3a_exp/惠山古镇5POI图"
def get_img_url_or_local(filename: str, github_url: str) -> str:
    if os.path.exists(os.path.join(LOCAL_IMG_BASE, filename)):
        return os.path.join(LOCAL_IMG_BASE, filename)
    return github_url

# ==================== 实时天气 ====================
def get_weather_and_comfort():
    try:
        url = "https://wttr.in/Wuxi?format=%C+%t&lang=zh"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            parts = resp.text.strip().split()
            if len(parts) >= 2:
                cond, tmp = parts[0], parts[1]
                tmp_num = int(re.search(r'[-+]?\d+', tmp).group())
                if tmp_num < 5: comf = "寒冷"
                elif tmp_num < 15: comf = "偏冷"
                elif tmp_num < 25: comf = "舒适"
                elif tmp_num < 32: comf = "偏热"
                else: comf = "炎热"
                return f"{cond} {tmp} · 体感{comf} · 街区人流舒适"
        return "多云 18°C · 体感舒适 · 街区人流舒适"
    except:
        return "晴 20°C · 体感舒适 · 街区人流舒适"

# ==================== CSS ====================
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

/* Hero 区域 */
.jn-hero {
  position: relative;
  min-height: 260px;
  border-radius: 28px;
  overflow: hidden;
  padding: 28px;
  background-size: cover;
  background-position: center 30%;
  box-shadow: 0 24px 60px rgba(25, 110, 130, .22);
  margin-bottom: 28px;
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

/* 实时天气栏 */
.jn-weather-bar {
  margin-top: 0px;
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
  font-size: 1.05rem;
}

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

/* 横向滚动推荐卡片 */
div[data-testid="column"],
div.row-widget.stHorizontalBlock {
    flex-wrap: nowrap !important;
    overflow-x: auto !important;
    overflow-y: hidden !important;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: thin;
    gap: 16px;
}
div[data-testid="column"] > div {
    min-width: 130px !important;
    width: 130px !important;
    flex: 0 0 auto !important;
}
.recommend-name {
    font-weight: 800;
    font-size: 0.85rem;
    margin: 8px 0 4px;
    text-align: center;
    white-space: normal;
    word-break: keep-all;
}

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
.stTextInput input, .stTextArea textarea {
  background: rgba(255,255,255,.86);
  border: 1px solid rgba(31,143,255,.18);
  border-radius: 16px;
}
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
@media (max-width: 640px) {
    div[data-testid="column"] > div {
        min-width: 110px !important;
        width: 110px !important;
    }
    .recommend-name {
        font-size: 0.75rem;
    }
    div.stButton > button {
        padding: 0.5rem 0.8rem;
        font-size: 0.8rem;
    }
}
</style>
""", unsafe_allow_html=True)

# ==================== 语音 JS ====================
st.markdown("""
<script>
window.speakText = function(text) {
    var utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'zh-CN';
    utterance.rate = 0.9;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
};
</script>
""", unsafe_allow_html=True)

# ==================== POI 数据加载 ====================
@st.cache_data
def load_poi_data():
    with open("data/poi_content.json", "r", encoding="utf-8") as f:
        content = f.read()
        content = re.sub(r',\s*}', '}', content)
        content = re.sub(r',\s*]', ']', content)
        return json.loads(content)

poi_database = load_poi_data()
POIS = [
    {"id": "fanwenzheng_gongci", "name": "范文正公祠"},
    {"id": "guhuashanmen", "name": "古华山门 / 金莲桥"},
    {"id": "bayinjian", "name": "八音涧 / 知鱼槛"},
    {"id": "zhulu_shanfang", "name": "竹炉山房"},
    {"id": "erquan", "name": "天下第二泉"}
]
POI_ORDER = [p["id"] for p in POIS]

# ==================== 6 组全排列条件映射 ====================
GROUP_CONDITION_MAP = {
    "G1": ["baseline", "free_text", "recchatbox", "baseline", "free_text"],
    "G2": ["baseline", "recchatbox", "free_text", "baseline", "recchatbox"],
    "G3": ["free_text", "baseline", "recchatbox", "free_text", "baseline"],
    "G4": ["free_text", "recchatbox", "baseline", "free_text", "recchatbox"],
    "G5": ["recchatbox", "baseline", "free_text", "recchatbox", "baseline"],
    "G6": ["recchatbox", "free_text", "baseline", "recchatbox", "free_text"]
}
VALID_GROUPS = list(GROUP_CONDITION_MAP.keys())

# ==================== 均衡分组 ====================
def assign_group_balanced():
    supabase = st.session_state.get("supabase")
    if supabase:
        try:
            res = supabase.table("participants").select("group").execute()
            if res.data:
                cnt = {g:0 for g in VALID_GROUPS}
                for row in res.data:
                    if row.get("group") in cnt:
                        cnt[row["group"]] += 1
                return min(cnt, key=cnt.get)
        except Exception as e:
            log_app_error("assign_group_balanced", str(e))
    return random.choice(VALID_GROUPS)

# ==================== Supabase 客户端 ====================
if "supabase" not in st.session_state:
    try:
        st.session_state.supabase = create_client(
            st.secrets["SUPABASE_URL"],
            st.secrets["SUPABASE_KEY"]
        )
    except Exception as e:
        st.session_state.supabase = None
        st.warning("Supabase 连接失败，日志将仅保存在本地")
        # 错误记录到本地文件
        with open("app_errors_local.log", "a") as f:
            f.write(f"{datetime.now().isoformat()} | Supabase init failed: {e}\n")

# ==================== 错误日志函数（写入 app_errors 表）====================
def log_app_error(context: str, error_message: str, extra: dict = None):
    """记录应用错误到 Supabase app_errors 表"""
    error_record = {
        "participant_id": st.session_state.get("participant_id", "UNKNOWN"),
        "context": context,
        "error_message": str(error_message),
        "extra": json.dumps(extra) if extra else None,
        "timestamp": datetime.now().isoformat()
    }
    # 本地备份
    os.makedirs("logs", exist_ok=True)
    with open("logs/app_errors.csv", "a", encoding="utf-8") as f:
        f.write(f"{error_record['timestamp']},{error_record['participant_id']},{context},{error_message}\n")
    # 尝试写入 Supabase
    if st.session_state.get("supabase"):
        try:
            st.session_state.supabase.table("app_errors").insert(error_record).execute()
        except Exception as e:
            # 不能再无限递归，直接忽略
            pass

# ==================== 数据写入函数（分别写入各表）====================
def write_participant(participant_id, group, pretest_data):
    try:
        st.session_state.supabase.table("participants").insert({
            "participant_id": participant_id,
            "group": group,
            "pretest_data": pretest_data,
            "created_at": datetime.now().isoformat()
        }).execute()
    except Exception as e:
        log_app_error("write_participant", str(e), {"participant_id": participant_id, "group": group})

def write_route_session(participant_id, group, route_start_ts):
    try:
        res = st.session_state.supabase.table("route_sessions").insert({
            "participant_id": participant_id,
            "group": group,
            "route_start_ts": route_start_ts,
            "created_at": datetime.now().isoformat()
        }).execute()
        if res.data:
            return res.data[0]["id"]  # 返回 session_id
    except Exception as e:
        log_app_error("write_route_session", str(e), {"participant_id": participant_id})
    return None

def write_poi_exposure(session_id, participant_id, group, poi_id, condition, exposure_start_ts):
    try:
        res = st.session_state.supabase.table("poi_exposures").insert({
            "session_id": session_id,
            "participant_id": participant_id,
            "group": group,
            "poi_id": poi_id,
            "condition": condition,
            "exposure_start_ts": exposure_start_ts,
            "created_at": datetime.now().isoformat()
        }).execute()
        if res.data:
            return res.data[0]["id"]  # 返回 exposure_id
    except Exception as e:
        log_app_error("write_poi_exposure", str(e), {"poi_id": poi_id})
    return None

def update_poi_exposure(exposure_id, dwell_seconds, next_click_ts):
    try:
        st.session_state.supabase.table("poi_exposures").update({
            "dwell_seconds": dwell_seconds,
            "next_click_ts": next_click_ts
        }).eq("id", exposure_id).execute()
    except Exception as e:
        log_app_error("update_poi_exposure", str(e), {"exposure_id": exposure_id})

def write_interaction_turn(exposure_id, participant_id, condition, query_type, query_text, response_text, latency_ms, retrieved_chunks, source_chip, error_flag=False):
    try:
        st.session_state.supabase.table("interaction_turns").insert({
            "exposure_id": exposure_id,
            "participant_id": participant_id,
            "condition": condition,
            "query_type": query_type,
            "query_text": query_text,
            "response_text": response_text,
            "response_latency_ms": latency_ms,
            "retrieved_chunks": retrieved_chunks,
            "source_chip": source_chip,
            "error_flag": error_flag,
            "created_at": datetime.now().isoformat()
        }).execute()
    except Exception as e:
        log_app_error("write_interaction_turn", str(e), {"exposure_id": exposure_id})

def write_micro_survey(exposure_id, participant_id, poi_id, condition, data_dict):
    try:
        record = {
            "exposure_id": exposure_id,
            "participant_id": participant_id,
            "poi_id": poi_id,
            "condition": condition,
            **data_dict,
            "created_at": datetime.now().isoformat()
        }
        st.session_state.supabase.table("micro_surveys").insert(record).execute()
    except Exception as e:
        log_app_error("write_micro_survey", str(e), {"exposure_id": exposure_id})

def write_final_survey(participant_id, group, final_data):
    try:
        st.session_state.supabase.table("final_surveys").insert({
            "participant_id": participant_id,
            "group": group,
            "final_data": final_data,
            "created_at": datetime.now().isoformat()
        }).execute()
    except Exception as e:
        log_app_error("write_final_survey", str(e), {"participant_id": participant_id})

# ==================== Dify RAG 函数 ====================
def simulate_rag_engine(user_query, poi):
    start = time.time()
    key = st.secrets.get("DIFY_API_KEY_MAIN", "Bearer app-rzITs8smrzMUhhdraDriLuRp")
    try:
        resp = requests.post("https://api.dify.ai/v1/chat-messages",
            headers={"Authorization": key, "Content-Type": "application/json"},
            json={"inputs": {"current_poi": poi["name"]}, "query": user_query,
                  "response_mode": "blocking", "user": st.session_state.get("participant_id")},
            timeout=15)
        data = resp.json()
        ans = data.get("answer", "抱歉，无法回答。")
        resources = data.get("metadata", {}).get("retriever_resources", [])
        src = f"官方数字认证：{resources[0].get('dataset_name', '无锡史志库')}" if resources else "惠山古镇文献库"
        return ans, src, str(resources), time.time()-start, False
    except Exception as e:
        error_msg = f"Dify API error: {str(e)}"
        log_app_error("simulate_rag_engine", error_msg, {"query": user_query, "poi": poi["name"]})
        return "【网络或服务异常】请稍后重试。", "故障降级", "[Error]", time.time()-start, True

def generate_followup_questions(user_question, ai_answer, pid):
    key = st.secrets.get("DIFY_API_KEY_FOLLOWUP", "Bearer app-CCck7NxI8NLZIxf24Q247Hti")
    try:
        resp = requests.post("https://api.dify.ai/v1/chat-messages",
            headers={"Authorization": key, "Content-Type": "application/json"},
            json={"inputs": {}, "query": f"用户问题：{user_question}\nAI回答：{ai_answer}\n请输出3个后续问题，JSON格式",
                  "response_mode": "blocking", "user": pid}, timeout=10)
        match = re.search(r'\[.*\]', resp.json().get("answer", "[]"))
        questions = json.loads(match.group(0)) if match else []
        if len(questions) != 3:
            questions = [f"关于{st.session_state.current_poi_name}还有哪些历史细节？",
                         "这里与无锡本地文化有什么关联？",
                         "有什么值得关注的参观细节？"]
        return questions, False
    except Exception as e:
        log_app_error("generate_followup_questions", str(e), {"user_question": user_question})
        return [f"关于{st.session_state.current_poi_name}还有哪些历史细节？",
                "这里与无锡本地文化有什么关联？",
                "有什么值得关注的参观细节？"], True

# ==================== 三个渲染函数（完整） ====================
def render_baseline(poi):
    st.markdown(f"""
    <div class="jn-card">
      <div style="display:flex; align-items:center; gap:8px;">
        <span style="font-size:28px;">📍</span>
        <b style="font-size:22px;">{poi['name']}</b>
      </div>
      <div style="margin-top:12px; line-height:1.65;">{poi['info']}</div>
    </div>
    """, unsafe_allow_html=True)
    if "kb" in poi and len(poi["kb"]) > 0:
        keywords = set()
        for kb_item in poi["kb"]:
            for kw in kb_item.get("keywords", [])[:2]:
                keywords.add(kw)
        st.markdown("**🏷️ 关键词**")
        st.markdown(" ".join([f'<span class="source-chip">#{kw}</span>' for kw in list(keywords)[:6]]), unsafe_allow_html=True)
    st.markdown(f'<span class="source-chip">🔍 {poi.get("source", "惠山古镇文献库")}</span>', unsafe_allow_html=True)
    voice_col, _ = st.columns([1, 5])
    with voice_col:
        if st.button("🔊 朗读介绍", key="speak_intro"):
            st.markdown(f'<script>speakText("{poi["info"]}")</script>', unsafe_allow_html=True)
    st.caption("✨ 静态展示模式 · 无 AI 对话")

def render_free_text_rag(poi):
    st.markdown(f"""
    <div class="jn-card">
      <div style="display:flex; align-items:center; gap:8px;">
        <span style="font-size:28px;">📍</span>
        <b style="font-size:22px;">{poi['name']}</b>
      </div>
      <div style="margin-top:12px; line-height:1.65;">{poi['info']}</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f'<span class="source-chip">🔍 {poi.get("source", "惠山古镇文献库")}</span>', unsafe_allow_html=True)
    voice_col, _ = st.columns([1, 5])
    with voice_col:
        if st.button("🔊 朗读介绍", key="speak_intro"):
            st.markdown(f'<script>speakText("{poi["info"]}")</script>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("#### 💬 向 AI 提问")
    
    exposure_id = st.session_state.get("current_exposure_id")
    if exposure_id and "chat_messages" in st.session_state and exposure_id in st.session_state.chat_messages:
        for msg in st.session_state.chat_messages[exposure_id]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg["role"] == "assistant" and "source" in msg:
                    st.markdown(f'<span class="source-chip">🔍 {msg["source"]}</span>', unsafe_allow_html=True)
    
    if prompt := st.chat_input("输入您的问题..."):
        handle_question(prompt, poi, "free_text")

def render_recchatbox(poi):
    st.markdown(f"""
    <div class="jn-card">
      <div style="display:flex; align-items:center; gap:8px;">
        <span style="font-size:28px;">📍</span>
        <b style="font-size:22px;">{poi['name']}</b>
      </div>
      <div style="margin-top:12px; line-height:1.65;">{poi['info']}</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f'<span class="source-chip">🔍 {poi.get("source", "惠山古镇文献库")}</span>', unsafe_allow_html=True)
    voice_col, _ = st.columns([1, 5])
    with voice_col:
        if st.button("🔊 朗读介绍", key="speak_intro"):
            st.markdown(f'<script>speakText("{poi["info"]}")</script>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("#### 💬 向 AI 提问")
    
    exposure_id = st.session_state.get("current_exposure_id")
    if exposure_id and "chat_messages" in st.session_state and exposure_id in st.session_state.chat_messages:
        for msg in st.session_state.chat_messages[exposure_id]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg["role"] == "assistant" and "source" in msg:
                    st.markdown(f'<span class="source-chip">🔍 {msg["source"]}</span>', unsafe_allow_html=True)
    
    # 显示推荐问题（若存在）
    if exposure_id and "followup_questions" in st.session_state and exposure_id in st.session_state.followup_questions:
        st.markdown("#### 💡 推荐问题")
        for i, q in enumerate(st.session_state.followup_questions[exposure_id]):
            if st.button(f"❓ {q}", key=f"rec_q_{exposure_id}_{i}"):
                handle_question(q, poi, "recchatbox")
    
    if prompt := st.chat_input("输入您的问题..."):
        handle_question(prompt, poi, "recchatbox")

def handle_question(question, poi, cond):
    with st.spinner("AI 导览员正在查阅史料..."):
        ans, src, chunks, elap, error = simulate_rag_engine(question, poi)
        exposure_id = st.session_state.get("current_exposure_id")
        if exposure_id:
            if "chat_messages" not in st.session_state:
                st.session_state.chat_messages = {}
            if exposure_id not in st.session_state.chat_messages:
                st.session_state.chat_messages[exposure_id] = []
            st.session_state.chat_messages[exposure_id].append({"role": "user", "content": question})
            st.session_state.chat_messages[exposure_id].append({"role": "assistant", "content": ans, "source": src})
            
            # 记录交互回合
            write_interaction_turn(
                exposure_id=exposure_id,
                participant_id=st.session_state.participant_id,
                condition=cond,
                query_type="free" if cond != "recchatbox" else "suggested",
                query_text=question,
                response_text=ans,
                latency_ms=round(elap*1000),
                retrieved_chunks=chunks,
                source_chip=src,
                error_flag=error
            )
            
            # 如果是 recchatbox，生成后续推荐问题
            if cond == "recchatbox":
                new_qs, _ = generate_followup_questions(question, ans, st.session_state.participant_id)
                if "followup_questions" not in st.session_state:
                    st.session_state.followup_questions = {}
                st.session_state.followup_questions[exposure_id] = new_qs
        
        st.markdown(f'<script>speakText("{ans.replace('"', '\\"')}")</script>', unsafe_allow_html=True)
        st.rerun()

# ==================== 页面渲染函数 ====================
def show_intro():
    st.markdown(f"""
    <div class="jn-hero" style="background-image: linear-gradient(90deg, rgba(10,30,36,.68), rgba(10,30,36,.28)), url('{MAIN_IMG_URL}');">
      <div class="jn-hero-title">惠山古镇 <span>AI 导览员</span></div>
      <div class="jn-hero-sub">融合 3A 智能问答、文化知识库与语音导览，呈现江南文脉的轻量化数字体验。</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f'<div class="jn-weather-bar">🌸 惠山古镇 · {get_weather_and_comfort()}</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="jn-card">
      <div class="jn-section-title">📋 实验说明</div>
      <p>感谢您参与本次惠山古镇文化遗产数字导览实验！</p>
      <ul>
        <li>您将沿着固定路线依次参观 <strong>5 个历史文化点位</strong></li>
        <li>路线步行约 <strong>10 分钟</strong>，总实验（含问卷）约 <strong>20-25 分钟</strong></li>
        <li>每个点位停留约 <strong>60-90 秒</strong></li>
        <li>请勿点击浏览器后退按钮</li>
        <li>所有数据将匿名处理，仅用于学术研究</li>
      </ul>
    </div>
    """, unsafe_allow_html=True)
    if st.button("🚀 开始实验", use_container_width=True):
        st.session_state.stage = "consent"
        st.rerun()

def show_consent():
    st.title("📄 知情同意书")
    st.markdown("---")
    st.markdown("""
    **研究题目：** 惠山古镇 AI 导览员实验研究
    **研究目的：** 比较三种文化遗产数字导览界面（原始网页、自由提问 AI、推荐式交互）对游客参观体验的影响。
    **实验流程：** 路线约10分钟 + 问卷约10-15分钟，总计20-25分钟。
    **数据使用声明：** 所有数据严格匿名处理，仅用于学术研究，您有权随时退出。
    **联系方式：** research@example.edu.cn
    """)
    st.markdown("---")
    consent = st.checkbox("我已阅读并同意以上条款，自愿参加本次实验")
    if st.button("✅ 同意并继续", use_container_width=True, disabled=not consent):
        st.session_state.stage = "pretest"
        st.session_state.consent_ts = time.time()
        st.rerun()

def show_pretest():
    st.title("📝 基本信息调查")
    with st.form("pretest_form"):
        age = st.text_input("1. 您的年龄", placeholder="例如：25")
        gender = st.selectbox("2. 您的性别", ["请选择", "男", "女", "不愿透露"])
        education = st.selectbox("3. 您的最高学历", ["请选择", "高中/中专", "大专", "本科", "硕士", "博士及以上"])
        discipline = st.selectbox("4. 您的专业背景", ["请选择", "设计/艺术", "人文/历史", "计算机/信息技术", "旅游/管理", "其他"])
        heritage_visit_freq = st.slider("5. 过去一年参观博物馆/历史街区的频率", 1, 7, 4, help="1=从不，7=非常频繁")
        huishan_familiarity = st.slider("6. 我熟悉惠山古镇或曾经到访", 1, 7, 4)
        genai_familiarity = st.slider("7. 我熟悉生成式 AI 的使用", 1, 7, 4)
        mobile_guide_exp = st.slider("8. 我有使用手机导览的经验", 1, 7, 4)
        st.markdown("#### 探索倾向（1=非常不同意，5=非常同意）")
        cei = [st.slider(f"{i+1}. {txt}", 1, 5, 3) for i, txt in enumerate([
            "我通常会主动寻找新的知识、地点或体验。",
            "当一个问题没有标准答案时，我仍愿意继续探索。",
            "遇到不确定的信息时，我会想进一步查证。",
            "我喜欢发现自己原本不知道的历史或文化细节。",
            "面对陌生场景时，我愿意尝试不同方式理解它。",
            "我会因为一个有趣线索继续追问下去。",
            "当一个系统给出推荐问题时，我愿意点开看看。",
            "我愿意花一点额外时间弄清楚文化信息的来源。"
        ])]
        if st.form_submit_button("提交并继续"):
            if not age or gender=="请选择" or education=="请选择":
                st.error("请完成所有必填项")
                st.stop()
            group = assign_group_balanced()
            st.session_state.group = group
            pretest = {"age":age, "gender":gender, "education":education, "discipline":discipline,
                       "heritage_visit_freq":heritage_visit_freq, "huishan_familiarity":huishan_familiarity,
                       "genai_familiarity":genai_familiarity, "mobile_guide_exp":mobile_guide_exp,
                       **{f"cei_{i+1}":cei[i] for i in range(8)}, "group":group, "pretest_ts":time.time()}
            st.session_state.pretest_data = pretest
            # 写入 participants 表
            write_participant(st.session_state.participant_id, group, pretest)
            # 创建路线会话
            session_id = write_route_session(st.session_state.participant_id, group, time.time())
            st.session_state.route_session_id = session_id
            st.session_state.poi_index = 0
            st.session_state.stage = "route_intro"
            st.rerun()

def show_route_intro():
    st.title("🗺️ 路线说明")
    st.markdown("""
    **您将按以下顺序参观 5 个历史文化点位：**
    1. 范文正公祠
    2. 古华山门 / 金莲桥
    3. 八音涧 / 知鱼槛
    4. 竹炉山房
    5. 天下第二泉
    **注意事项：** 请按照顺序参观，每个点位停留约60-90秒，参观完点击“前往下一站”。路线步行约10分钟，总实验约20-25分钟。
    """)
    if st.button("🚶 开始参观", use_container_width=True):
        st.session_state.stage = "poi"
        st.session_state.route_start_ts = time.time()
        st.rerun()

def show_poi_page():
    poi_idx = st.session_state.poi_index
    if poi_idx >= len(POIS):
        st.session_state.stage = "final_survey"
        st.rerun()
        return
    poi = POIS[poi_idx]
    poi_data = poi_database.get(poi["id"], {"name": poi["name"], "info": "暂无详细介绍。"})
    condition = GROUP_CONDITION_MAP[st.session_state.group][poi_idx]
    st.session_state.current_poi_id = poi["id"]
    st.session_state.current_poi_name = poi["name"]
    st.session_state.current_condition = condition
    if "poi_page_load_ts" not in st.session_state:
        st.session_state.poi_page_load_ts = time.time()
    
    # 创建 POI exposure 记录
    exposure_id = write_poi_exposure(
        session_id=st.session_state.route_session_id,
        participant_id=st.session_state.participant_id,
        group=st.session_state.group,
        poi_id=poi["id"],
        condition=condition,
        exposure_start_ts=st.session_state.poi_page_load_ts
    )
    st.session_state.current_exposure_id = exposure_id
    # 初始化该 exposure 的聊天记录和推荐问题容器
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = {}
    st.session_state.chat_messages[exposure_id] = []
    if "followup_questions" not in st.session_state:
        st.session_state.followup_questions = {}
    st.session_state.followup_questions[exposure_id] = []
    
    # Hero + 天气
    st.markdown(f"""
    <div class="jn-hero" style="background-image: linear-gradient(90deg, rgba(10,30,36,.68), rgba(10,30,36,.28)), url('{get_img_url_or_local("主图.jpg", MAIN_IMG_URL)}');">
      <div class="jn-hero-title">惠山古镇 <span>AI 导览员</span></div>
      <div class="jn-hero-sub">点位 {poi_idx+1}/5</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f'<div class="jn-weather-bar">🌸 惠山古镇 · {get_weather_and_comfort()}</div>', unsafe_allow_html=True)
    
    # 条件渲染
    if condition == "baseline":
        render_baseline(poi_data)
        st.caption("✨ 静态展示模式 · 无 AI 对话")
    elif condition == "free_text":
        render_free_text_rag(poi_data)
    else:
        render_recchatbox(poi_data)
    
    # 下一站 → 微问卷
    if st.button("✅ 我已游览完当前点位，前往下一站", use_container_width=True):
        dwell = time.time() - st.session_state.poi_page_load_ts
        update_poi_exposure(exposure_id, dwell, time.time())
        st.session_state.pending_poi_index = poi_idx
        st.session_state.stage = "micro_survey"
        st.rerun()

def show_micro_survey():
    poi_idx = st.session_state.pending_poi_index
    poi = POIS[poi_idx]
    poi_id = poi["id"]
    st.title(f"📋 点位 {poi_idx+1} 体验问卷")
    st.markdown(f"**{poi['name']}**")
    with st.form("micro_form"):
        mental = st.slider("理解信息需要较多脑力", 1,7,4)
        time_p = st.slider("感到时间紧迫", 1,7,4)
        effort = st.slider("需要付出较多努力", 1,7,4)
        frust = st.slider("感到烦躁或受挫", 1,7,4)
        control = st.slider("能自主决定看什么、问什么", 1,7,4)
        interrupt = st.slider("界面打断了我观察真实环境", 1,7,4)
        engage = st.slider("信息帮助我把手机内容和眼前点位联系起来", 1,7,4)
        satisfy = st.slider("信息满足了我的好奇", 1,7,4)
        trust = st.slider("信息在历史文化上是可信的", 1,7,4)
        source_use = st.slider("来源标注让我更愿意相信信息", 1,7,4)
        learn_conf = st.slider("我能向别人说明该点位的核心文化意义", 1,7,4)
        # 知识题
        q_map = {
            "fanwenzheng_gongci": ("范文正公祠主要祭祀哪位历史人物？",["范仲淹","苏轼","陆羽","阿炳"],"范仲淹"),
            "guhuashanmen": ("金莲桥最适合作为哪类体验节点？",["空间过渡","商业消费","现代交通","纯自然景观"],"空间过渡"),
            "bayinjian": ("八音涧的“八音”更接近哪种含义？",["水声类比传统乐音","八件实物乐器","八位诗人","八座亭子"],"水声类比传统乐音"),
            "zhulu_shanfang": ("竹炉山房最适合连接哪种文化主题？",["文人茶事","战争防御","商业票号","近代工业"],"文人茶事"),
            "erquan": ("关于“天下第二泉”的严谨说法？",["《茶经》和《煎茶水记》需区分","完全由苏轼排名","由阿炳命名","现代营销命名"],"《茶经》和《煎茶水记》需区分")
        }
        q_text, opts, correct = q_map[poi_id]
        answer = st.radio(q_text, opts)
        if st.form_submit_button("提交并继续"):
            is_correct = (answer == correct)
            micro_data = {
                "mental_demand": mental, "temporal_pressure": time_p, "effort": effort,
                "frustration": frust, "perceived_control": control, "interruption": interrupt,
                "situated_engagement": engage, "info_satisfaction": satisfy,
                "cultural_trust": trust, "source_usefulness": source_use,
                "learning_confidence": learn_conf, "knowledge_correct": is_correct,
                "knowledge_answer": answer
            }
            write_micro_survey(
                exposure_id=st.session_state.current_exposure_id,
                participant_id=st.session_state.participant_id,
                poi_id=poi_id,
                condition=st.session_state.current_condition,
                data_dict=micro_data
            )
            st.session_state.poi_index = poi_idx + 1
            if st.session_state.poi_index >= len(POIS):
                st.session_state.stage = "final_survey"
            else:
                st.session_state.stage = "poi"
                # 重置 POI 页面时间戳，不清空 exposure 相关 state（新 POI 会重新创建）
                st.session_state.poi_page_load_ts = time.time()
            st.rerun()

def show_final_survey():
    st.title("📝 整体体验评价")
    st.markdown("请分别评价您体验过的三种界面。")
    conditions = ["baseline", "free_text", "recchatbox"]
    names = {"baseline":"A: 原始网页", "free_text":"B: 自由提问 AI", "recchatbox":"C: 推荐式交互"}
    
    # Tell me more C1-C5 存储
    tm_ratings = {}
    
    with st.form("final_form"):
        for cond in conditions:
            st.markdown(f"#### {names[cond]}")
            for i, sus_item in enumerate([
                "我愿意继续使用该界面。","该界面显得不必要地复杂。","该界面容易上手。",
                "我需要他人帮助才能顺利使用。","功能整合得很好。","在不同点位表现不一致。",
                "多数游客能很快学会。","使用起来很累赘。","使用时有信心。","使用前需要学习很多东西。"]):
                st.slider(f"SUS {i+1}: {sus_item}", 1,5,3, key=f"sus_{cond}_{i}")
            for i, toast_item in enumerate([
                "帮助我完成文化信息探索目标。","表现稳定一致。","反应符合我的预期。",
                "信息很少让我意外或困惑。","我愿意依赖该界面提供的信息。"]):
                st.slider(f"TOAST {i+1}: {toast_item}", 1,7,4, key=f"toast_{cond}_{i}")
        
        # Tell me more C1-C5
        st.markdown("---")
        st.markdown("#### 交互体验评价（Tell me more C1-C5）")
        for cond in ["free_text", "recchatbox"]:
            st.markdown(f"**{names[cond]}**")
            tm_ratings[f"q_easy_{cond}"] = st.slider("提出问题是容易的。", 1,5,3, key=f"q_easy_{cond}")
            tm_ratings[f"ans_understand_{cond}"] = st.slider("我理解系统给出的回答。", 1,5,3, key=f"ans_understand_{cond}")
            tm_ratings[f"ans_interest_{cond}"] = st.slider("系统回答让我觉得内容更有趣。", 1,5,3, key=f"ans_interest_{cond}")
        st.markdown(f"**{names['recchatbox']}**")
        tm_ratings["recq_understand_C"] = st.slider("系统推荐的问题是清楚易懂的。", 1,5,3, key="recq_understand_C")
        tm_ratings["recq_interest_C"] = st.slider("系统推荐的问题能激发我继续探索。", 1,5,3, key="recq_interest_C")
        
        st.markdown("#### 偏好与开放题")
        pref = st.radio("最愿意使用哪一种？", ["原始网页","自由提问 AI","推荐式交互"], key="pref")
        pref_reason = st.text_area("请说明原因")
        trust_break = st.text_area("有没有哪一刻你开始相信或不相信系统？")
        interrupt_moment = st.text_area("有没有哪一刻手机信息干扰了你看真实场景？")
        comments = st.text_area("其他意见或建议")
        
        if st.form_submit_button("提交评价"):
            final = {
                "preference": pref, "preference_reason": pref_reason,
                "trust_breakpoint": trust_break, "interruption_moment": interrupt_moment,
                "open_comments": comments,
                "sus": {f"{cond}_{i}": st.session_state.get(f"sus_{cond}_{i}") for cond in conditions for i in range(10)},
                "toast": {f"{cond}_{i}": st.session_state.get(f"toast_{cond}_{i}") for cond in conditions for i in range(5)},
                "tellmemore": tm_ratings
            }
            write_final_survey(st.session_state.participant_id, st.session_state.group, final)
            st.session_state.stage = "done"
            st.rerun()

def show_done():
    st.success("🎉 实验完成！感谢您的参与！")
    st.markdown("补偿码：`HS-3A-2024`。您可以关闭此页面了。")
    st.caption("惠山古镇 AI 导览员实验研究 | 江南大学")

# ==================== 主入口 ====================
def main():
    if "participant_id" not in st.session_state:
        st.session_state.participant_id = st.query_params.get("pid", f"P_{uuid.uuid4().hex[:8]}")
    if "group" not in st.session_state and st.query_params.get("group") in VALID_GROUPS:
        st.session_state.group = st.query_params.get("group")
    if "stage" not in st.session_state:
        st.session_state.stage = "intro"
    stage = st.session_state.stage
    if stage == "intro": show_intro()
    elif stage == "consent": show_consent()
    elif stage == "pretest": show_pretest()
    elif stage == "route_intro": show_route_intro()
    elif stage == "poi": show_poi_page()
    elif stage == "micro_survey": show_micro_survey()
    elif stage == "final_survey": show_final_survey()
    elif stage == "done": show_done()
    else: st.session_state.stage = "intro"; st.rerun()

if __name__ == "__main__":
    main()
