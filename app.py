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

# ==================== 完整 CSS ====================
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
    try {
        var utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'zh-CN';
        utterance.rate = 0.9;
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(utterance);
    } catch(e) {
        console.error("语音合成错误:", e);
    }
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

# ==================== Supabase 客户端 ====================
if "supabase" not in st.session_state:
    try:
        st.session_state.supabase = create_client(
            st.secrets["SUPABASE_URL"],
            st.secrets["SUPABASE_KEY"]
        )
    except Exception as e:
        st.session_state.supabase = None
        st.warning(f"Supabase 连接失败: {e}")

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
            log_app_error("assign_group_balanced", e)
    return random.choice(VALID_GROUPS)

# ==================== 错误记录 ====================
def log_app_error(operation, error, extra=None):
    if extra is None: extra = {}
    error_data = {
        "participant_id": st.session_state.get("participant_id", "UNKNOWN"),
        "operation": operation,
        "error_message": str(error),
        "extra": extra,
        "timestamp": datetime.now().isoformat()
    }
    if "errors_log" not in st.session_state:
        st.session_state.errors_log = []
    st.session_state.errors_log.append(error_data)
    os.makedirs("logs", exist_ok=True)
    df = pd.DataFrame(st.session_state.errors_log)
    df.to_csv(f"logs/{st.session_state.get('participant_id', 'unknown')}_errors.csv", index=False, encoding="utf-8-sig")
    supabase = st.session_state.get("supabase")
    if supabase:
        try:
            supabase.table("app_errors").insert(error_data).execute()
        except:
            pass

# ==================== 统一日志（多表拆分）====================
def log_event(event_type, payload=None):
    if payload is None: payload = {}
    base_fields = {
        "participant_id": st.session_state.get("participant_id", "UNKNOWN"),
        "group": st.session_state.get("group", "UNKNOWN"),
        "timestamp": datetime.now().isoformat(),
        "payload": payload
    }
    supabase = st.session_state.get("supabase")
    os.makedirs("logs", exist_ok=True)
    log_line = {**base_fields, "event_type": event_type}
    with open(f"logs/{st.session_state.get('participant_id', 'unknown')}_all_events.log", "a", encoding="utf-8") as f:
        f.write(json.dumps(log_line, ensure_ascii=False) + "\n")
    
    if not supabase:
        return
    
    try:
        if event_type == "pretest_completed":
            supabase.table("participants").insert({
                "participant_id": st.session_state.participant_id,
                "group": st.session_state.group,
                "pretest_data": payload.get("pretest_data", {}),
                "created_at": datetime.now().isoformat()
            }).execute()
        elif event_type == "route_started":
            supabase.table("route_sessions").insert({
                "participant_id": st.session_state.participant_id,
                "group": st.session_state.group,
                "start_time": datetime.now().isoformat(),
                "payload": payload
            }).execute()
        elif event_type == "poi_entered":
            exposure_id = str(uuid.uuid4())
            st.session_state.current_exposure_id = exposure_id
            supabase.table("poi_exposures").insert({
                "exposure_id": exposure_id,
                "participant_id": st.session_state.participant_id,
                "group": st.session_state.group,
                "poi_id": payload.get("poi_id"),
                "condition": payload.get("condition"),
                "sequence_position": payload.get("sequence_position"),
                "enter_time": datetime.now().isoformat(),
                "payload": payload
            }).execute()
        elif event_type == "poi_completed":
            exposure_id = st.session_state.get("current_exposure_id")
            if exposure_id:
                supabase.table("poi_exposures").update({
                    "exit_time": datetime.now().isoformat(),
                    "dwell_seconds": payload.get("dwell_seconds")
                }).eq("exposure_id", exposure_id).execute()
        elif event_type == "question_submitted":
            supabase.table("interaction_turns").insert({
                "turn_id": str(uuid.uuid4()),
                "exposure_id": st.session_state.get("current_exposure_id"),
                "participant_id": st.session_state.participant_id,
                "query_text": payload.get("query_text"),
                "response_text": payload.get("response_text"),
                "response_latency_ms": payload.get("response_latency_ms"),
                "retrieved_chunks": payload.get("retrieved_chunks"),
                "source_chip": payload.get("source_chip"),
                "timestamp": datetime.now().isoformat()
            }).execute()
        elif event_type == "micro_survey_submitted":
            supabase.table("micro_surveys").insert({
                "exposure_id": st.session_state.get("current_exposure_id"),
                "participant_id": st.session_state.participant_id,
                "poi_id": payload.get("poi_id"),
                "condition": payload.get("condition"),
                "mental_demand": payload.get("mental_demand"),
                "temporal_pressure": payload.get("temporal_pressure"),
                "effort": payload.get("effort"),
                "frustration": payload.get("frustration"),
                "perceived_control": payload.get("perceived_control"),
                "interruption": payload.get("interruption"),
                "situated_engagement": payload.get("situated_engagement"),
                "info_satisfaction": payload.get("info_satisfaction"),
                "cultural_trust": payload.get("cultural_trust"),
                "source_usefulness": payload.get("source_usefulness"),
                "learning_confidence": payload.get("learning_confidence"),
                "knowledge_correct": payload.get("knowledge_correct"),
                "knowledge_answer": payload.get("knowledge_answer"),
                "timestamp": datetime.now().isoformat()
            }).execute()
        elif event_type == "final_survey_completed":
            supabase.table("final_surveys").insert({
                "participant_id": st.session_state.participant_id,
                "group": st.session_state.group,
                "preference": payload.get("preference"),
                "preference_reason": payload.get("preference_reason"),
                "trust_breakpoint": payload.get("trust_breakpoint"),
                "interruption_moment": payload.get("interruption_moment"),
                "open_comments": payload.get("open_comments"),
                "sus_responses": payload.get("sus"),
                "toast_responses": payload.get("toast"),
                "c1_easy_b": payload.get("c1_easy_b"),
                "c2_understand_b": payload.get("c2_understand_b"),
                "c3_interesting_b": payload.get("c3_interesting_b"),
                "c1_easy_c": payload.get("c1_easy_c"),
                "c2_understand_c": payload.get("c2_understand_c"),
                "c3_interesting_c": payload.get("c3_interesting_c"),
                "c4_recq_understand_c": payload.get("c4_recq_understand_c"),
                "c5_recq_interesting_c": payload.get("c5_recq_interesting_c"),
                "timestamp": datetime.now().isoformat()
            }).execute()
        else:
            supabase.table("interaction_logs").insert({
                "participant_id": st.session_state.participant_id,
                "event_type": event_type,
                "payload": payload,
                "timestamp": datetime.now().isoformat()
            }).execute()
    except Exception as e:
        log_app_error(f"log_event_{event_type}", e, extra=payload)

# ==================== Dify RAG 函数（直接使用提供的 API URL 和密钥） ====================
DIFY_API_URL = "https://api.dify.ai/v1/chat-messages"
DIFY_API_KEY_MAIN = "app-rzITs8smrzMUhhdraDriLuRp"        # AI导览员
DIFY_API_KEY_FOLLOWUP = "app-CCck7NxI8NLZIxf24Q247Hti"   # 对话型应用API（引导3问题）

def simulate_rag_engine(user_query, poi):
    start = time.time()
    try:
        resp = requests.post(
            DIFY_API_URL,
            headers={"Authorization": f"Bearer {DIFY_API_KEY_MAIN}", "Content-Type": "application/json"},
            json={
                "inputs": {"current_poi": poi["name"]},
                "query": user_query,
                "response_mode": "blocking",
                "user": st.session_state.get("participant_id", "unknown")
            },
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        ans = data.get("answer", "抱歉，无法回答。")
        resources = data.get("metadata", {}).get("retriever_resources", [])
        src = f"官方数字认证：{resources[0].get('dataset_name', '无锡史志库')}" if resources else "惠山古镇文献库"
        return ans, src, str(resources), time.time()-start
    except requests.exceptions.Timeout:
        err_msg = "AI 服务响应超时，请稍后重试。"
        st.warning(err_msg)
        log_app_error("simulate_rag_engine_timeout", err_msg, {"query": user_query, "poi": poi["name"]})
        return err_msg, "网络超时", "[Timeout]", time.time()-start
    except Exception as e:
        err_msg = f"AI 服务异常：{str(e)}"
        st.error(err_msg)
        log_app_error("simulate_rag_engine", e, {"query": user_query, "poi": poi["name"]})
        return "【网络或服务异常】请稍后重试。", "故障降级", "[Error]", time.time()-start

def generate_followup_questions(user_question, ai_answer, pid):
    try:
        resp = requests.post(
            DIFY_API_URL,
            headers={"Authorization": f"Bearer {DIFY_API_KEY_FOLLOWUP}", "Content-Type": "application/json"},
            json={
                "inputs": {},
                "query": f"用户问题：{user_question}\nAI回答：{ai_answer}\n请输出3个后续问题，JSON格式",
                "response_mode": "blocking",
                "user": pid
            },
            timeout=10
        )
        match = re.search(r'\[.*\]', resp.json().get("answer", "[]"))
        questions = json.loads(match.group(0)) if match else []
        while len(questions) < 3:
            questions.append("您还想了解更多关于这里的历史渊源吗？")
        return questions[:3]
    except Exception as e:
        log_app_error("generate_followup_questions", e, {"user_question": user_question})
        return [f"关于{st.session_state.current_poi_name}还有哪些历史细节？",
                "这里与无锡本地文化有什么关联？",
                "有什么值得关注的参观细节？"]

def handle_question(question, poi, cond):
    with st.spinner("AI 导览员正在查阅史料..."):
        ans, src, chunks, elap = simulate_rag_engine(question, poi)
        exposure_id = st.session_state.get("current_exposure_id")
        if "chat_messages_by_exposure" not in st.session_state:
            st.session_state.chat_messages_by_exposure = {}
        if exposure_id not in st.session_state.chat_messages_by_exposure:
            st.session_state.chat_messages_by_exposure[exposure_id] = []
        st.session_state.chat_messages_by_exposure[exposure_id].append({"role": "user", "content": question})
        st.session_state.chat_messages_by_exposure[exposure_id].append({"role": "assistant", "content": ans, "source": src})
        
        log_event("question_submitted", {
            "query_text": question, "response_text": ans,
            "response_latency_ms": round(elap*1000), "retrieved_chunks": chunks, "source_chip": src
        })
        # 尝试语音播报
        try:
            safe_ans = ans.replace('"', '\\"').replace('\n', ' ')
            st.markdown(f'<script>speakText("{safe_ans}")</script>', unsafe_allow_html=True)
        except Exception as e:
            log_app_error("speakText", e, {"answer": ans[:100]})
        
        if cond == "recchatbox":
            st.session_state.followup_questions = generate_followup_questions(question, ans, st.session_state.participant_id)
        else:
            st.session_state.followup_questions = []
        st.rerun()

# ==================== 三个渲染函数（完整） ====================
def render_baseline(poi):
    """Baseline 界面：固定介绍 + 关键词 chip + 来源 chip"""
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
            safe_info = poi["info"].replace('"', '\\"').replace('\n', ' ')
            st.markdown(f'<script>speakText("{safe_info}")</script>', unsafe_allow_html=True)
    
    st.caption("✨ 静态展示模式 · 无 AI 对话")

def render_free_text_rag(poi):
    """Free-Text RAG 界面：固定介绍 + 输入框 + AI 回答 + 来源 chip"""
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
            safe_info = poi["info"].replace('"', '\\"').replace('\n', ' ')
            st.markdown(f'<script>speakText("{safe_info}")</script>', unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("#### 💬 向 AI 提问")
    
    exposure_id = st.session_state.get("current_exposure_id")
    if exposure_id and exposure_id in st.session_state.get("chat_messages_by_exposure", {}):
        messages = st.session_state.chat_messages_by_exposure[exposure_id]
        for msg in messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg["role"] == "assistant" and "source" in msg:
                    st.markdown(f'<span class="source-chip">🔍 {msg["source"]}</span>', unsafe_allow_html=True)
    
    if prompt := st.chat_input("输入您的问题..."):
        handle_question(prompt, poi, "free_text")

def render_recchatbox(poi):
    """RecChatbox 界面：固定介绍 + 推荐问题 + 输入框 + AI 回答 + 来源 chip"""
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
            safe_info = poi["info"].replace('"', '\\"').replace('\n', ' ')
            st.markdown(f'<script>speakText("{safe_info}")</script>', unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("#### 💡 推荐问题")
    
    if "followup_questions" not in st.session_state:
        st.session_state.followup_questions = poi.get("recs", [
            f"关于{poi['name']}还有哪些历史细节？",
            f"这里与无锡本地文化有什么关联？",
            f"有什么值得关注的参观细节？"
        ])
    
    cols = st.columns(3)
    for i, q in enumerate(st.session_state.followup_questions[:3]):
        with cols[i]:
            if st.button(f"❓ {q[:20]}{'...' if len(q) > 20 else ''}", key=f"rec_q_{i}"):
                handle_question(q, poi, "recchatbox")
    
    st.markdown("#### 💬 向 AI 提问")
    
    exposure_id = st.session_state.get("current_exposure_id")
    if exposure_id and exposure_id in st.session_state.get("chat_messages_by_exposure", {}):
        messages = st.session_state.chat_messages_by_exposure[exposure_id]
        for msg in messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg["role"] == "assistant" and "source" in msg:
                    st.markdown(f'<span class="source-chip">🔍 {msg["source"]}</span>', unsafe_allow_html=True)
    
    if prompt := st.chat_input("输入您的问题..."):
        handle_question(prompt, poi, "recchatbox")

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
        log_event("stage_intro_completed")
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
        log_event("consent_given")
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
            log_event("pretest_completed", {"pretest_data": pretest})
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
        log_event("route_started")
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
    
    log_event("poi_entered", {
        "poi_id": poi["id"],
        "condition": condition,
        "sequence_position": poi_idx + 1
    })
    
    st.markdown(f"""
    <div class="jn-hero" style="background-image: linear-gradient(90deg, rgba(10,30,36,.68), rgba(10,30,36,.28)), url('{get_img_url_or_local("主图.jpg", MAIN_IMG_URL)}');">
      <div class="jn-hero-title">惠山古镇 <span>AI 导览员</span></div>
      <div class="jn-hero-sub">点位 {poi_idx+1}/5</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f'<div class="jn-weather-bar">🌸 惠山古镇 · {get_weather_and_comfort()}</div>', unsafe_allow_html=True)
    
    # 已删除“今日推荐”图片卡片
    
    if condition == "baseline":
        render_baseline(poi_data)
        st.caption("✨ 静态展示模式 · 无 AI 对话")
    elif condition == "free_text":
        render_free_text_rag(poi_data)
    else:
        render_recchatbox(poi_data)
    
    if st.button("✅ 我已游览完当前点位，前往下一站", use_container_width=True):
        dwell = time.time() - st.session_state.poi_page_load_ts
        log_event("poi_completed", {"poi": poi["id"], "condition": condition, "dwell_seconds": round(dwell,2)})
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
                "poi_id": poi_id, "condition": st.session_state.current_condition,
                "mental_demand": mental, "temporal_pressure": time_p, "effort": effort,
                "frustration": frust, "perceived_control": control, "interruption": interrupt,
                "situated_engagement": engage, "info_satisfaction": satisfy,
                "cultural_trust": trust, "source_usefulness": source_use,
                "learning_confidence": learn_conf, "knowledge_correct": is_correct,
                "knowledge_answer": answer
            }
            log_event("micro_survey_submitted", micro_data)
            st.session_state.poi_index = poi_idx + 1
            if st.session_state.poi_index >= len(POIS):
                st.session_state.stage = "final_survey"
            else:
                st.session_state.stage = "poi"
                st.session_state.poi_page_load_ts = time.time()
                st.session_state.followup_questions = []
            st.rerun()

def show_final_survey():
    st.title("📝 整体体验评价")
    st.markdown("请分别评价您体验过的三种界面。")
    conditions = ["baseline", "free_text", "recchatbox"]
    names = {"baseline":"A: 原始网页", "free_text":"B: 自由提问 AI", "recchatbox":"C: 推荐式交互"}
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
        st.markdown("---")
        st.markdown("#### 关于**自由提问 AI (B)** 的体验")
        c1_easy_b = st.slider("提出问题是容易的。", 1,5,3, key="c1_easy_b")
        c2_understand_b = st.slider("我理解系统给出的回答。", 1,5,3, key="c2_understand_b")
        c3_interesting_b = st.slider("系统回答让我觉得内容更有趣。", 1,5,3, key="c3_interesting_b")
        st.markdown("#### 关于**推荐式交互 (C)** 的体验")
        c1_easy_c = st.slider("提出问题是容易的。", 1,5,3, key="c1_easy_c")
        c2_understand_c = st.slider("我理解系统给出的回答。", 1,5,3, key="c2_understand_c")
        c3_interesting_c = st.slider("系统回答让我觉得内容更有趣。", 1,5,3, key="c3_interesting_c")
        c4_recq_understand_c = st.slider("系统推荐的问题是清楚易懂的。", 1,5,3, key="c4_recq_understand_c")
        c5_recq_interesting_c = st.slider("系统推荐的问题能激发我继续探索。", 1,5,3, key="c5_recq_interesting_c")
        st.markdown("#### 偏好与开放题")
        pref = st.radio("最愿意使用哪一种？", ["原始网页","自由提问 AI","推荐式交互"], key="pref")
        pref_reason = st.text_area("请说明原因")
        trust_break = st.text_area("有没有哪一刻你开始相信或不相信系统？")
        interrupt_moment = st.text_area("有没有哪一刻手机信息干扰了你看真实场景？")
        comments = st.text_area("其他意见或建议")
        if st.form_submit_button("提交评价"):
            final = {
                "preference": pref, "preference_reason": pref_reason, "trust_breakpoint": trust_break,
                "interruption_moment": interrupt_moment, "open_comments": comments,
                "sus": {f"{cond}_{i}": st.session_state.get(f"sus_{cond}_{i}") for cond in conditions for i in range(10)},
                "toast": {f"{cond}_{i}": st.session_state.get(f"toast_{cond}_{i}") for cond in conditions for i in range(5)},
                "c1_easy_b": c1_easy_b, "c2_understand_b": c2_understand_b, "c3_interesting_b": c3_interesting_b,
                "c1_easy_c": c1_easy_c, "c2_understand_c": c2_understand_c, "c3_interesting_c": c3_interesting_c,
                "c4_recq_understand_c": c4_recq_understand_c, "c5_recq_interesting_c": c5_recq_interesting_c
            }
            log_event("final_survey_completed", final)
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
    if "chat_messages_by_exposure" not in st.session_state:
        st.session_state.chat_messages_by_exposure = {}
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
