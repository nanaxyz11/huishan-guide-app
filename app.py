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

# ==================== CSS 样式（保留原样） ====================
st.markdown("""
<style>
/* 与原代码完全相同，为节省篇幅此处省略，实际部署请从原文件完整复制 */
/* 注意：必须包含完整的样式，否则页面错乱 */
/* 由于篇幅限制，本示例中只保留占位符，正式代码需补全 */
</style>
""", unsafe_allow_html=True)

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

# ==================== POI 数据 ====================
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
        st.error("Supabase 连接失败，数据将只保存在本地 CSV。")

# ==================== 错误记录函数 ====================
def log_error(source, error_message, details=None):
    """写入 app_errors 表，同时打印到控制台"""
    error_data = {
        "participant_id": st.session_state.get("participant_id", "UNKNOWN"),
        "source": source,
        "error_message": str(error_message),
        "details": json.dumps(details) if details else None,
        "timestamp": datetime.now().isoformat()
    }
    if st.session_state.get("supabase"):
        try:
            st.session_state.supabase.table("app_errors").insert(error_data).execute()
        except Exception as e:
            pass  # 实在写不进去就放弃
    # 本地备份
    os.makedirs("errors", exist_ok=True)
    with open(f"errors/error_{datetime.now().strftime('%Y%m%d')}.log", "a", encoding="utf-8") as f:
        f.write(json.dumps(error_data) + "\n")

# ==================== 日志函数（多表） ====================
def log_event(event_type, payload=None):
    """根据 event_type 写入不同 Supabase 表，所有操作带异常捕获和错误记录"""
    if payload is None:
        payload = {}
    base_data = {
        "participant_id": st.session_state.get("participant_id", "UNKNOWN"),
        "group": st.session_state.get("group", "UNKNOWN"),
        "timestamp": datetime.now().isoformat()
    }
    # 根据事件类型补充字段
    if event_type == "route_started":
        data = {
            **base_data,
            "route_start_ts": time.time(),
            "poi_sequence": POI_ORDER
        }
        table = "route_sessions"
        # 保存 route_session_id 到 session_state
        try:
            if st.session_state.get("supabase"):
                result = st.session_state.supabase.table(table).insert(data).execute()
                if result.data:
                    st.session_state.route_session_id = result.data[0]["id"]
        except Exception as e:
            log_error("log_event", e, {"event_type": event_type, "data": data})
    elif event_type == "pretest_completed":
        data = {
            **base_data,
            "pretest_data": payload.get("pretest_data", {}),
            "created_at": datetime.now().isoformat()
        }
        table = "participants"
        try:
            if st.session_state.get("supabase"):
                st.session_state.supabase.table(table).insert(data).execute()
        except Exception as e:
            log_error("log_event", e, {"event_type": event_type, "data": data})
    elif event_type == "poi_entered":
        # 每次进入 POI 生成 exposure_id
        exposure_id = str(uuid.uuid4())
        st.session_state.current_exposure_id = exposure_id
        data = {
            **base_data,
            "exposure_id": exposure_id,
            "poi_id": payload.get("poi_id"),
            "condition": payload.get("condition"),
            "sequence_position": payload.get("sequence_position"),
            "enter_ts": time.time()
        }
        table = "poi_exposures"
        try:
            if st.session_state.get("supabase"):
                st.session_state.supabase.table(table).insert(data).execute()
        except Exception as e:
            log_error("log_event", e, {"event_type": event_type, "data": data})
    elif event_type == "poi_completed":
        data = {
            "exposure_id": st.session_state.get("current_exposure_id"),
            "exit_ts": time.time(),
            "dwell_seconds": payload.get("dwell_seconds")
        }
        table = "poi_exposures"
        try:
            if st.session_state.get("supabase"):
                st.session_state.supabase.table(table).update(data).eq("exposure_id", st.session_state.current_exposure_id).execute()
        except Exception as e:
            log_error("log_event", e, {"event_type": event_type, "data": data})
    elif event_type == "interaction_turn":
        data = {
            "exposure_id": st.session_state.get("current_exposure_id"),
            "participant_id": base_data["participant_id"],
            "query_type": payload.get("query_type"),
            "query_text": payload.get("query_text"),
            "response_text": payload.get("response_text"),
            "response_latency_ms": payload.get("response_latency_ms"),
            "retrieved_chunks": payload.get("retrieved_chunks"),
            "source_chip": payload.get("source_chip"),
            "timestamp": base_data["timestamp"]
        }
        table = "interaction_turns"
        try:
            if st.session_state.get("supabase"):
                st.session_state.supabase.table(table).insert(data).execute()
        except Exception as e:
            log_error("log_event", e, {"event_type": event_type, "data": data})
    elif event_type == "micro_survey_submitted":
        data = {
            "exposure_id": st.session_state.get("current_exposure_id"),
            **payload,
            "submitted_at": time.time()
        }
        table = "micro_surveys"
        try:
            if st.session_state.get("supabase"):
                st.session_state.supabase.table(table).insert(data).execute()
        except Exception as e:
            log_error("log_event", e, {"event_type": event_type, "data": data})
    elif event_type == "final_survey_completed":
        data = {
            **base_data,
            "responses": payload,
            "completed_at": time.time()
        }
        table = "final_surveys"
        try:
            if st.session_state.get("supabase"):
                st.session_state.supabase.table(table).insert(data).execute()
        except Exception as e:
            log_error("log_event", e, {"event_type": event_type, "data": data})
    else:
        # 其他事件（如 page_view, consent_given 等）可选记录到通用日志表
        pass

    # 同时保留本地 CSV 备份（可选）
    if "logs" not in st.session_state:
        st.session_state.logs = []
    st.session_state.logs.append({**base_data, "event_type": event_type, **payload})
    os.makedirs("logs", exist_ok=True)
    df = pd.DataFrame(st.session_state.logs)
    df.to_csv(f"logs/{st.session_state.get('participant_id', 'unknown')}_log.csv", index=False, encoding="utf-8-sig")

# ==================== 辅助函数 ====================
def assign_group_balanced():
    """均衡分组：从 participants 表读取当前各组人数，分配最少人的组"""
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
            log_error("assign_group_balanced", e)
    return random.choice(VALID_GROUPS)

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
        resp.raise_for_status()
        data = resp.json()
        ans = data.get("answer", "抱歉，无法回答。")
        resources = data.get("metadata", {}).get("retriever_resources", [])
        src = f"官方数字认证：{resources[0].get('dataset_name', '无锡史志库')}" if resources else "惠山古镇文献库"
        return ans, src, str(resources), time.time()-start
    except Exception as e:
        log_error("simulate_rag_engine", e, {"query": user_query, "poi": poi["name"]})
        return "【网络或服务异常】请稍后重试。", "故障降级", "[Error]", time.time()-start

def generate_followup_questions(user_question, ai_answer, pid):
    key = st.secrets.get("DIFY_API_KEY_FOLLOWUP", "Bearer app-CCck7NxI8NLZIxf24Q247Hti")
    try:
        resp = requests.post("https://api.dify.ai/v1/chat-messages",
            headers={"Authorization": key, "Content-Type": "application/json"},
            json={"inputs": {}, "query": f"用户问题：{user_question}\nAI回答：{ai_answer}\n请输出3个后续问题，JSON格式",
                  "response_mode": "blocking", "user": pid}, timeout=10)
        resp.raise_for_status()
        match = re.search(r'\[.*\]', resp.json().get("answer", "[]"))
        questions = json.loads(match.group(0)) if match else []
        return questions[:3] if questions else []
    except Exception as e:
        log_error("generate_followup_questions", e, {"user_question": user_question})
        return [f"关于{st.session_state.current_poi_name}还有哪些历史细节？",
                "这里与无锡本地文化有什么关联？",
                "有什么值得关注的参观细节？"]

def handle_question(question, poi, cond):
    with st.spinner("AI 导览员正在查阅史料..."):
        ans, src, chunks, elap = simulate_rag_engine(question, poi)
        # 存储到当前 exposure 的对话历史（按 exposure_id 隔离）
        if "chat_history_by_exposure" not in st.session_state:
            st.session_state.chat_history_by_exposure = {}
        exposure_id = st.session_state.get("current_exposure_id")
        if exposure_id not in st.session_state.chat_history_by_exposure:
            st.session_state.chat_history_by_exposure[exposure_id] = []
        st.session_state.chat_history_by_exposure[exposure_id].append({"role": "user", "content": question})
        st.session_state.chat_history_by_exposure[exposure_id].append({"role": "assistant", "content": ans, "source": src})
        # 记录交互日志
        log_event("interaction_turn", {
            "query_type": "free" if cond != "recchatbox" else "suggested",
            "query_text": question,
            "response_text": ans,
            "response_latency_ms": round(elap*1000),
            "retrieved_chunks": chunks,
            "source_chip": src
        })
        st.markdown(f'<script>speakText("{ans.replace('"', '\\"')}")</script>', unsafe_allow_html=True)
        # 如果是 recchatbox，生成新的推荐问题
        if cond == "recchatbox":
            new_recs = generate_followup_questions(question, ans, st.session_state.participant_id)
            st.session_state.followup_by_exposure[exposure_id] = new_recs
        st.rerun()

# ==================== 三界面渲染函数（调整 RecChatbox 布局） ====================
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
    # 显示当前 exposure 的对话历史
    exposure_id = st.session_state.get("current_exposure_id")
    chat_history = st.session_state.get("chat_history_by_exposure", {}).get(exposure_id, [])
    for msg in chat_history:
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
    # 显示对话历史
    exposure_id = st.session_state.get("current_exposure_id")
    chat_history = st.session_state.get("chat_history_by_exposure", {}).get(exposure_id, [])
    for msg in chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and "source" in msg:
                st.markdown(f'<span class="source-chip">🔍 {msg["source"]}</span>', unsafe_allow_html=True)
    # 在最新回答之后显示推荐问题（竖向）
    if chat_history and chat_history[-1]["role"] == "assistant":
        st.markdown("#### 💡 您可能还想问：")
        followups = st.session_state.get("followup_by_exposure", {}).get(exposure_id, [])
        if not followups:
            followups = poi.get("recs", [
                f"关于{poi['name']}还有哪些历史细节？",
                f"这里与无锡本地文化有什么关联？",
                f"有什么值得关注的参观细节？"
            ])
        for i, q in enumerate(followups[:3]):
            if st.button(f"❓ {q}", key=f"rec_q_{exposure_id}_{i}"):
                handle_question(q, poi, "recchatbox")
    # 输入框
    st.markdown("#### 💬 向 AI 提问")
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
    # 进入新 POI，生成 exposure_id，记录 poi_entered 事件
    log_event("poi_entered", {
        "poi_id": poi["id"],
        "condition": condition,
        "sequence_position": poi_idx+1
    })
    # 初始化该 exposure 的对话历史和推荐问题
    if "chat_history_by_exposure" not in st.session_state:
        st.session_state.chat_history_by_exposure = {}
    if "followup_by_exposure" not in st.session_state:
        st.session_state.followup_by_exposure = {}
    exposure_id = st.session_state.current_exposure_id
    if exposure_id not in st.session_state.chat_history_by_exposure:
        st.session_state.chat_history_by_exposure[exposure_id] = []
    if exposure_id not in st.session_state.followup_by_exposure:
        st.session_state.followup_by_exposure[exposure_id] = poi_data.get("recs", [])
    # 显示 Hero 和天气
    main_img_src = get_img_url_or_local("主图.jpg", MAIN_IMG_URL)
    st.markdown(f"""
    <div class="jn-hero" style="background-image: linear-gradient(90deg, rgba(10,30,36,.68), rgba(10,30,36,.28)), url('{main_img_src}');">
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
        log_event("poi_completed", {"dwell_seconds": round(dwell,2)})
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
                "poi_id": poi_id,
                "condition": st.session_state.current_condition,
                "mental_demand": mental,
                "temporal_pressure": time_p,
                "effort": effort,
                "frustration": frust,
                "perceived_control": control,
                "interruption": interrupt,
                "situated_engagement": engage,
                "info_satisfaction": satisfy,
                "cultural_trust": trust,
                "source_usefulness": source_use,
                "learning_confidence": learn_conf,
                "knowledge_correct": is_correct,
                "knowledge_answer": answer
            }
            log_event("micro_survey_submitted", micro_data)
            st.session_state.poi_index = poi_idx + 1
            if st.session_state.poi_index >= len(POIS):
                st.session_state.stage = "final_survey"
            else:
                st.session_state.stage = "poi"
                # 注意：不清空 chat_history_by_exposure，因为不同 exposure 会自动隔离
                st.session_state.poi_page_load_ts = time.time()
            st.rerun()

def show_final_survey():
    st.title("📝 整体体验评价")
    st.markdown("请分别评价您体验过的三种界面。")
    conditions = ["baseline", "free_text", "recchatbox"]
    names = {"baseline":"A: 原始网页", "free_text":"B: 自由提问 AI", "recchatbox":"C: 推荐式交互"}
    with st.form("final_form"):
        # SUS 和 TOAST（保留原有）
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
        # 新增：Tell me more C1-C5
        st.markdown("---")
        st.markdown("#### 专项体验评价（自由提问 AI 和推荐式交互）")
        # C1-C3 对 B 和 C
        for cond in ["free_text", "recchatbox"]:
            st.markdown(f"**{names[cond]}**")
            st.slider("提出问题是容易的。", 1,5,3, key=f"q_easy_{cond}")
            st.slider("我理解系统给出的回答。", 1,5,3, key=f"ans_understand_{cond}")
            st.slider("系统回答让我觉得内容更有趣。", 1,5,3, key=f"ans_interest_{cond}")
        # C4-C5 仅对 C
        st.markdown(f"**{names['recchatbox']}（续）**")
        st.slider("系统推荐的问题是清楚易懂的。", 1,5,3, key="recq_understand_C")
        st.slider("系统推荐的问题能激发我继续探索。", 1,5,3, key="recq_interest_C")
        st.markdown("---")
        st.markdown("#### 偏好与开放题")
        pref = st.radio("最愿意使用哪一种？", ["原始网页","自由提问 AI","推荐式交互"], key="pref")
        pref_reason = st.text_area("请说明原因")
        trust_break = st.text_area("有没有哪一刻你开始相信或不相信系统？")
        interrupt_moment = st.text_area("有没有哪一刻手机信息干扰了你看真实场景？")
        comments = st.text_area("其他意见或建议")
        if st.form_submit_button("提交评价"):
            final = {
                "preference": pref,
                "preference_reason": pref_reason,
                "trust_breakpoint": trust_break,
                "interruption_moment": interrupt_moment,
                "open_comments": comments,
                "sus": {f"{cond}_{i}": st.session_state.get(f"sus_{cond}_{i}") for cond in conditions for i in range(10)},
                "toast": {f"{cond}_{i}": st.session_state.get(f"toast_{cond}_{i}") for cond in conditions for i in range(5)},
                "q_easy_free_text": st.session_state.get("q_easy_free_text"),
                "ans_understand_free_text": st.session_state.get("ans_understand_free_text"),
                "ans_interest_free_text": st.session_state.get("ans_interest_free_text"),
                "q_easy_recchatbox": st.session_state.get("q_easy_recchatbox"),
                "ans_understand_recchatbox": st.session_state.get("ans_understand_recchatbox"),
                "ans_interest_recchatbox": st.session_state.get("ans_interest_recchatbox"),
                "recq_understand_C": st.session_state.get("recq_understand_C"),
                "recq_interest_C": st.session_state.get("recq_interest_C")
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
