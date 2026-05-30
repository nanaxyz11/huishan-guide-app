import streamlit as st
import json
import os
import time
import hashlib
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

# ==================== GitHub 图片直链（中文路径自动编码） ====================
def get_github_raw_url(filename: str) -> str:
    """根据文件名生成 GitHub raw 链接，自动处理中文编码"""
    base = "https://raw.githubusercontent.com/nanaxyz11/huishan-guide-app/main/%E6%83%A0%E5%B1%B1%E5%8F%A45POI%E5%9B%BE/"
    encoded_filename = quote(filename)
    return base + encoded_filename

# 主图背景 URL
MAIN_IMG_URL = get_github_raw_url("主图.jpg")
# 推荐卡片图片 URL
RECOMMEND_IMG_URLS = {
    "天下第二泉": get_github_raw_url("二泉.jpg"),
    "古华山门": get_github_raw_url("金莲桥.jpg"),
    "知鱼栏": get_github_raw_url("知鱼栏.jpg"),
    "竹炉山房": get_github_raw_url("竹炉山房.jpg"),
    "范文正公祠": get_github_raw_url("范文公正祠.jpg")
}

# 本地路径备用（仅用于开发环境，云端无效）
LOCAL_IMG_BASE = "/Users/clisl/Documents/huishan_3a_exp/惠山古镇5POI图"

def get_img_url_or_local(filename: str, github_url: str) -> str:
    """优先使用 GitHub raw，若本地存在（开发环境）则使用本地路径，否则返回 GitHub URL"""
    if os.path.exists(os.path.join(LOCAL_IMG_BASE, filename)):
        return os.path.join(LOCAL_IMG_BASE, filename)
    return github_url

# ==================== 实时天气、舒适度、人流量 ====================
def get_weather_and_comfort():
    """获取无锡实时天气、温度，并计算舒适度，人流量写固定值"""
    try:
        url = "https://wttr.in/Wuxi?format=%C+%t&lang=zh"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            weather_text = response.text.strip()
            parts = weather_text.split()
            if len(parts) >= 2:
                condition = parts[0]
                temp_str = parts[1]
                temp_num = re.search(r'[-+]?\d+', temp_str)
                temp_c = int(temp_num.group()) if temp_num else 18
                if temp_c < 5:
                    comfort = "寒冷"
                elif temp_c < 15:
                    comfort = "偏冷"
                elif temp_c < 25:
                    comfort = "舒适"
                elif temp_c < 32:
                    comfort = "偏热"
                else:
                    comfort = "炎热"
                crowd = "舒适"
                return f"{condition} {temp_str} · 体感{comfort} · 街区人流{crowd}"
            else:
                return "多云 18°C · 体感舒适 · 街区人流舒适"
        else:
            return "多云 18°C · 体感舒适 · 街区人流舒适"
    except Exception:
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
POIS = [
    {"id": "fanwenzheng_gongci", "name": "范文正公祠"},
    {"id": "guhuashanmen", "name": "古华山门 / 金莲桥"},
    {"id": "bayinjian", "name": "八音涧 / 知鱼槛"},
    {"id": "zhulu_shanfang", "name": "竹炉山房"},
    {"id": "erquan", "name": "天下第二泉"}
]
POI_ORDER = [p["id"] for p in POIS]

# ==================== 6 组全排列条件映射 ====================
# 条件代码: "baseline", "free_text", "recchatbox"
GROUP_CONDITION_MAP = {
    "G1": ["baseline", "free_text", "recchatbox", "baseline", "free_text"],
    "G2": ["baseline", "recchatbox", "free_text", "baseline", "recchatbox"],
    "G3": ["free_text", "baseline", "recchatbox", "free_text", "baseline"],
    "G4": ["free_text", "recchatbox", "baseline", "free_text", "recchatbox"],
    "G5": ["recchatbox", "baseline", "free_text", "recchatbox", "baseline"],
    "G6": ["recchatbox", "free_text", "baseline", "recchatbox", "free_text"]
}
VALID_GROUPS = list(GROUP_CONDITION_MAP.keys())


# ==================== 随机分组函数 ====================
def assign_group():
    """随机分配 G1-G6"""
    return random.choice(VALID_GROUPS)


# ==================== Supabase 客户端 ====================
if "supabase" not in st.session_state:
    try:
        supabase_url = st.secrets["SUPABASE_URL"]
        supabase_key = st.secrets["SUPABASE_KEY"]
        st.session_state.supabase = create_client(supabase_url, supabase_key)
    except Exception as e:
        st.session_state.supabase = None
        st.warning(f"Supabase 连接失败，日志将仅保存在本地: {e}")


# ==================== 日志函数 ====================
def log_event(event_type, payload=None):
    """统一日志记录函数"""
    if payload is None:
        payload = {}
    
    log_data = {
        "participant_id": st.session_state.get("participant_id", "UNKNOWN"),
        "group": st.session_state.get("group", "UNKNOWN"),
        "poi_id": st.session_state.get("current_poi_id", "UNKNOWN"),
        "condition": st.session_state.get("current_condition", "UNKNOWN"),
        "event_type": event_type,
        "timestamp": datetime.now().isoformat(),
        **payload
    }
    
    if "logs" not in st.session_state:
        st.session_state.logs = []
    st.session_state.logs.append(log_data)
    
    # 保存到本地 CSV
    os.makedirs("logs", exist_ok=True)
    df = pd.DataFrame(st.session_state.logs)
    df.to_csv(f"logs/{st.session_state.get('participant_id', 'unknown')}_log.csv", index=False, encoding="utf-8-sig")
    
    # 写入 Supabase
    if st.session_state.get("supabase"):
        try:
            st.session_state.supabase.table("interaction_logs").insert(log_data).execute()
        except Exception as e:
            pass  # 静默失败，不影响用户体验


# ==================== 页面渲染函数 ====================
def show_intro():
    """入口页"""
    st.markdown(f"""
    <div class="jn-hero" style="background-image: linear-gradient(90deg, rgba(10, 30, 36, .68), rgba(10, 30, 36, .28)), url('{MAIN_IMG_URL}');">
      <div class="jn-hero-title">惠山古镇 <span>AI 导览员</span></div>
      <div class="jn-hero-sub">
        融合 3A 智能问答、文化知识库与语音导览，呈现江南文脉的轻量化数字体验。
      </div>
    </div>
    """, unsafe_allow_html=True)
    
    weather_str = get_weather_and_comfort()
    st.markdown(f'<div class="jn-weather-bar">🌸 惠山古镇 · {weather_str}</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="jn-card">
      <div class="jn-section-title">📋 实验说明</div>
      <p>感谢您参与本次惠山古镇文化遗产数字导览实验！</p>
      <ul>
        <li>您将沿着固定路线依次参观 <strong>5 个历史文化点位</strong></li>
        <li>预计总时长约 <strong>10-15 分钟</strong>（不含问卷）</li>
        <li>每个点位停留约 <strong>60-90 秒</strong></li>
        <li>请勿点击浏览器后退按钮，以免影响实验数据</li>
        <li>所有数据将匿名处理，仅用于学术研究</li>
      </ul>
      <p style="margin-top: 16px; color: var(--jn-muted);">👇 点击下方按钮开始实验</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 开始实验", use_container_width=True):
            st.session_state.stage = "consent"
            log_event("stage_intro_completed")
            st.rerun()


def show_consent():
    """知情同意页"""
    st.title("📄 知情同意书")
    st.markdown("---")
    
    st.markdown("""
    **研究题目：** 惠山古镇 AI 导览员实验研究
    
    **研究目的：** 本研究旨在比较三种文化遗产数字导览界面（原始网页、自由提问 AI、推荐式交互）对游客参观体验的影响。
    
    **实验流程：**
    1. 您将完成约 10-15 分钟的路线参观
    2. 参观完成后，您将回答一份简短的问卷
    3. 整个实验过程约 15-20 分钟
    
    **数据使用声明：**
    - 所有数据将严格匿名处理，仅用于学术研究目的
    - 您的回答不会被追踪到个人身份
    - 您有权随时退出实验，不会产生任何不利影响
    
    **研究者联系方式：**
    - 如有任何问题，请联系：xxxxxxxx@xx.edu.cn
    """)
    
    st.markdown("---")
    consent = st.checkbox("我已阅读并同意以上条款，自愿参加本次实验")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("✅ 同意并继续", use_container_width=True, disabled=not consent):
            st.session_state.stage = "pretest"
            st.session_state.consent_ts = time.time()
            log_event("consent_given")
            st.rerun()


def show_pretest():
    """前测页"""
    st.title("📝 基本信息调查")
    st.markdown("请回答以下问题，所有信息将严格保密。")
    st.markdown("---")
    
    with st.form("pretest_form"):
        age = st.text_input("1. 您的年龄", placeholder="例如：25")
        
        gender = st.selectbox("2. 您的性别", ["请选择", "男", "女", "不愿透露"])
        
        education = st.selectbox("3. 您的最高学历", ["请选择", "高中/中专", "大专", "本科", "硕士", "博士及以上"])
        
        discipline = st.selectbox("4. 您的专业背景", ["请选择", "设计/艺术", "人文/历史", "计算机/信息技术", "旅游/管理", "其他"])
        
        heritage_visit_freq = st.slider("5. 过去一年参观博物馆/历史街区的频率", 1, 7, 4,
                                        help="1=从不，7=非常频繁")
        
        huishan_familiarity = st.slider("6. 我熟悉惠山古镇或曾经到访", 1, 7, 4,
                                        help="1=完全不熟悉，7=非常熟悉")
        
        genai_familiarity = st.slider("7. 我熟悉 ChatGPT/通义/文心等生成式 AI 的使用", 1, 7, 4,
                                      help="1=完全不熟悉，7=非常熟悉")
        
        mobile_guide_exp = st.slider("8. 我有使用手机导览/小程序导览/数字展陈导览的经验", 1, 7, 4,
                                     help="1=完全没有，7=非常丰富")
        
        st.markdown("---")
        st.markdown("#### 探索倾向（1=非常不同意，5=非常同意）")
        
        cei_1 = st.slider("我通常会主动寻找新的知识、地点或体验。", 1, 5, 3)
        cei_2 = st.slider("当一个问题没有标准答案时，我仍愿意继续探索。", 1, 5, 3)
        cei_3 = st.slider("遇到不确定的信息时，我会想进一步查证。", 1, 5, 3)
        cei_4 = st.slider("我喜欢发现自己原本不知道的历史或文化细节。", 1, 5, 3)
        cei_5 = st.slider("面对陌生场景时，我愿意尝试不同方式理解它。", 1, 5, 3)
        cei_6 = st.slider("我会因为一个有趣线索继续追问下去。", 1, 5, 3)
        cei_7 = st.slider("当一个系统给出推荐问题时，我愿意点开看看。", 1, 5, 3)
        cei_8 = st.slider("我愿意花一点额外时间弄清楚文化信息的来源。", 1, 5, 3)
        
        st.markdown("---")
        
        if st.form_submit_button("提交并继续"):
            # 随机分组
            group = assign_group()
            st.session_state.group = group
            
            # 保存前测数据
            pretest_data = {
                "age": age,
                "gender": gender,
                "education": education,
                "discipline": discipline,
                "heritage_visit_freq": heritage_visit_freq,
                "huishan_familiarity": huishan_familiarity,
                "genai_familiarity": genai_familiarity,
                "mobile_guide_exp": mobile_guide_exp,
                "cei_1": cei_1, "cei_2": cei_2, "cei_3": cei_3, "cei_4": cei_4,
                "cei_5": cei_5, "cei_6": cei_6, "cei_7": cei_7, "cei_8": cei_8,
                "group": group,
                "pretest_ts": time.time()
            }
            st.session_state.pretest_data = pretest_data
            
            log_event("pretest_completed", {"group": group})
            
            st.session_state.poi_index = 0
            st.session_state.stage = "route_intro"
            st.rerun()


def show_route_intro():
    """路线说明页"""
    st.title("🗺️ 路线说明")
    st.markdown("---")
    
    st.markdown("""
    **您将按以下顺序参观 5 个历史文化点位：**
    
    | 顺序 | 点位名称 |
    |------|----------|
    | 1 | 范文正公祠 |
    | 2 | 古华山门 / 金莲桥 |
    | 3 | 八音涧 / 知鱼槛 |
    | 4 | 竹炉山房 |
    | 5 | 天下第二泉 |
    
    **注意事项：**
    - 请按照上方顺序依次参观
    - 在每个点位停留约 **60-90 秒**
    - 参观完一个点位后，点击页面下方的 **"我已游览完当前点位，前往下一站"** 按钮
    - 请不要点击浏览器的后退按钮
    
    💡 提示：每个点位可能会看到不同类型的导览界面，请按照界面指引操作即可。
    """)
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚶 开始参观", use_container_width=True):
            st.session_state.stage = "poi"
            st.session_state.route_start_ts = time.time()
            log_event("route_started")
            st.rerun()


# ==================== Dify RAG 函数 ====================
def simulate_rag_engine(user_query, poi):
    start = time.time()
    url = "https://api.dify.ai/v1/chat-messages"
    key = "Bearer app-rzITs8smrzMUhhdraDriLuRp"
    payload = {
        "inputs": {"current_poi": poi["name"]},
        "query": user_query,
        "response_mode": "blocking",
        "user": st.session_state.get("participant_id", "unknown")
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
        return "【网络或服务异常】请稍后重试。", "故障降级", "[Error]", elapsed


def generate_followups_fallback(poi_name):
    return [
        f"关于{poi_name}还有哪些值得一访的历史细节？",
        f"这座建筑与无锡本地文化传统的关联体现在哪些方面？",
        f"在您的日常游览中，最能引发好奇心的遗产元素是什么？"
    ]


def generate_followup_questions(user_question, ai_answer, participant_id):
    url = "https://api.dify.ai/v1/chat-messages"
    key = "Bearer app-CCck7NxI8NLZIxf24Q247Hti"
    prompt = f"""用户问题：{user_question}
AI回答：{ai_answer}
请以 JSON 格式输出 3 个与文化遗产相关的后续问题，格式为 ["问题1", "问题2", "问题3"]，不要有其他解释。"""
    try:
        resp = requests.post(url, json={"inputs": {}, "query": prompt, "response_mode": "blocking", "user": participant_id}, headers={"Authorization": key, "Content-Type": "application/json"}, timeout=10)
        answer = resp.json().get("answer", "[\"\"]")
        match = re.search(r'\[.*\]', answer, re.DOTALL)
        questions = json.loads(match.group(0)) if match else []
        while len(questions) < 3:
            questions.append("您还想了解更多关于这里的历史渊源吗？")
        return questions[:3]
    except Exception:
        return generate_followups_fallback(st.session_state.current_poi_name)


def handle_question(question, poi, condition):
    with st.spinner("AI 导览员正在查阅史料..."):
        ans, src, chunks, elapsed = simulate_rag_engine(question, poi)
        
        if "chat_messages" not in st.session_state:
            st.session_state.chat_messages = []
        st.session_state.chat_messages.append({"role": "user", "content": question})
        st.session_state.chat_messages.append({"role": "assistant", "content": ans, "source": src})
        
        log_event("question_submitted", {
            "query_text": question,
            "response_text": ans,
            "response_latency_ms": round(elapsed * 1000, 1),
            "retrieved_chunks": chunks,
            "source_chip": src
        })
        
        st.markdown(f'<script>speakText("{ans.replace('"', '\\"')}")</script>', unsafe_allow_html=True)
        
        if condition == "recchatbox":
            st.session_state.followup_questions = generate_followup_questions(question, ans, st.session_state.participant_id)
        else:
            st.session_state.followup_questions = []
        
        st.rerun()


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
    
    # 关键词 chip
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
            st.markdown(f'<script>speakText("{poi["info"]}")</script>', unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("#### 💬 向 AI 提问")
    
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and "source" in msg:
                st.markdown(f'<span class="source-chip">🔍 {msg["source"]}</span>', unsafe_allow_html=True)
    
    if prompt := st.chat_input("输入您的问题..."):
        handle_question(prompt, poi, "free_text")


def render_recchatbox(poi):
    """RecChatbox 界面：固定介绍 + 3 个推荐问题按钮 + 输入框 + AI 回答 + 来源 chip"""
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
    st.markdown("#### 💡 推荐问题")
    
    if "followup_questions" not in st.session_state:
        # 从 POI 数据中获取推荐问题
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
    
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and "source" in msg:
                st.markdown(f'<span class="source-chip">🔍 {msg["source"]}</span>', unsafe_allow_html=True)
    
    if prompt := st.chat_input("输入您的问题..."):
        handle_question(prompt, poi, "recchatbox")


def show_poi_page():
    """POI 体验页"""
    poi_index = st.session_state.poi_index
    if poi_index >= len(POIS):
        st.session_state.stage = "final_survey"
        st.rerun()
        return
    
    poi = POIS[poi_index]
    poi_id = poi["id"]
    poi_name = poi["name"]
    
    # 从 poi_database 获取完整内容
    poi_data = poi_database.get(poi_id, {
        "name": poi_name,
        "info": "暂无详细介绍。",
        "recs": ["请问这个点位有什么值得一看的吗？"],
        "source": "惠山古镇文献库"
    })
    
    # 确定条件
    group = st.session_state.group
    condition_code = GROUP_CONDITION_MAP[group][poi_index]
    
    # 保存到 session_state
    st.session_state.current_poi_id = poi_id
    st.session_state.current_poi_name = poi_name
    st.session_state.current_condition = condition_code
    
    # 记录页面加载时间
    if "poi_page_load_ts" not in st.session_state:
        st.session_state.poi_page_load_ts = time.time()
    
    # 显示 Hero 和天气
    main_img_src = get_img_url_or_local("主图.jpg", MAIN_IMG_URL)
    hero_bg_style = f"background-image: linear-gradient(90deg, rgba(10, 30, 36, .68), rgba(10, 30, 36, .28)), url('{main_img_src}');"
    st.markdown(f"""
    <div class="jn-hero" style="{hero_bg_style}">
      <div class="jn-hero-title">惠山古镇 <span>AI 导览员</span></div>
      <div class="jn-hero-sub">点位 {poi_index + 1} / 5</div>
    </div>
    """, unsafe_allow_html=True)
    
    weather_str = get_weather_and_comfort()
    st.markdown(f'<div class="jn-weather-bar">🌸 惠山古镇 · {weather_str}</div>', unsafe_allow_html=True)
    
    # 今日推荐卡片
    st.markdown('<div class="jn-card"><div class="jn-section-title">📸 今日推荐 · 寻迹江南</div>', unsafe_allow_html=True)
    recommend_pois = [
        ("天下第二泉", "erquan", RECOMMEND_IMG_URLS["天下第二泉"]),
        ("古华山门", "guhuashanmen", RECOMMEND_IMG_URLS["古华山门"]),
        ("知鱼栏", "bayinjian", RECOMMEND_IMG_URLS["知鱼栏"]),
        ("竹炉山房", "zhulu_shanfang", RECOMMEND_IMG_URLS["竹炉山房"]),
        ("范文正公祠", "fanwenzheng_gongci", RECOMMEND_IMG_URLS["范文正公祠"])
    ]
    cols = st.columns(len(recommend_pois))
    for idx, (name, rec_poi_id, github_url) in enumerate(recommend_pois):
        img_url = get_img_url_or_local(
            {"天下第二泉": "二泉.jpg", "古华山门": "金莲桥.jpg", "知鱼栏": "知鱼栏.jpg", "竹炉山房": "竹炉山房.jpg", "范文正公祠": "范文公正祠.jpg"}[name],
            github_url
        )
        with cols[idx]:
            st.image(img_url, use_column_width=True, output_format="JPEG")
            st.markdown(f'<div class="recommend-name">{name}</div>', unsafe_allow_html=True)
            if st.button("✨ 探寻", key=f"rec_btn_{idx}"):
                # 跳转到对应 POI 点位
                new_index = POI_ORDER.index(rec_poi_id) if rec_poi_id in POI_ORDER else 0
                if new_index != poi_index:
                    st.session_state.poi_index = new_index
                    st.session_state.chat_messages = []
                    st.session_state.followup_questions = []
                    log_event("poi_jumped", {"from": poi_id, "to": rec_poi_id})
                    st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 根据条件渲染界面
    if condition_code == "baseline":
        render_baseline(poi_data)
        st.caption("✨ 静态展示模式 · 无 AI 对话")
    elif condition_code == "free_text":
        render_free_text_rag(poi_data)
    else:  # recchatbox
        render_recchatbox(poi_data)
    
    # 下一站按钮
    st.markdown("---")
    if st.button("✅ 我已游览完当前点位，前往下一站", use_container_width=True):
        dwell_seconds = time.time() - st.session_state.poi_page_load_ts
        log_event("poi_completed", {
            "poi": poi_id,
            "condition": condition_code,
            "dwell_seconds": round(dwell_seconds, 2)
        })
        
        # 保存微问卷数据（简化版，正式版需要在此处显示问卷表单）
        # 注意：根据实验设计，每个POI后应显示微问卷。这里简化为直接继续。
        # 如需完整微问卷，可在 poi_completed 后设置 stage = "micro_survey"
        
        st.session_state.poi_index += 1
        if st.session_state.poi_index >= len(POIS):
            st.session_state.stage = "final_survey"
        else:
            # 重置聊天消息，为下一个POI做准备
            st.session_state.chat_messages = []
            st.session_state.followup_questions = []
            st.session_state.poi_page_load_ts = time.time()
        
        st.rerun()


def show_final_survey():
    """终测页"""
    st.title("📝 体验评价")
    st.markdown("感谢您完成全部 5 个点位的参观！请回答以下问题。")
    st.markdown("---")
    
    st.info("请根据您在三种界面（原始网页、自由提问 AI、推荐式交互）下的整体体验进行评价。")
    
    with st.form("final_survey_form"):
        st.markdown("#### 界面可用性评价")
        
        sus_items = [
            "我愿意在类似文化遗产参观中继续使用该界面。",
            "该界面显得不必要地复杂。",
            "该界面容易上手。",
            "我需要他人帮助才能顺利使用该界面。",
            "该界面的功能整合得很好。",
            "该界面在不同点位上的表现不一致。",
            "多数游客能够很快学会使用该界面。",
            "该界面使用起来很累赘。",
            "使用该界面时我很有信心。",
            "开始使用前我需要学习很多东西。"
        ]
        
        for i, item in enumerate(sus_items):
            st.slider(f"{i+1}. {item}", 1, 5, 3, key=f"sus_{i}")
        
        st.markdown("---")
        st.markdown("#### 系统表现信任评价")
        
        toast_items = [
            "该界面帮助我完成了文化信息探索目标。",
            "该界面的表现是稳定一致的。",
            "该界面的反应符合我的预期。",
            "该界面的回答/信息很少让我意外或困惑。",
            "我愿意依赖该界面提供的文化信息。"
        ]
        
        for i, item in enumerate(toast_items):
            st.slider(f"{i+1}. {item}", 1, 7, 4, key=f"toast_{i}")
        
        st.markdown("---")
        st.markdown("#### 偏好与开放题")
        
        st.radio("1. 三种界面中，您最愿意在真实惠山古镇使用哪一种？",
                 ["原始网页", "自由提问 AI", "推荐式交互"], key="preference")
        
        st.text_area("2. 请说明您选择上述界面的原因。", key="preference_reason", height=100)
        
        st.text_area("3. 有没有哪一刻您开始相信或不相信系统？请描述具体点位和原因。", key="trust_breakpoint", height=100)
        
        st.text_area("4. 有没有哪一刻手机信息干扰了您观察真实场景？", key="interruption_moment", height=100)
        
        st.text_area("5. 您还有什么想分享的意见或建议？", key="open_comments", height=100)
        
        st.markdown("---")
        
        if st.form_submit_button("提交评价"):
            final_data = {
                "participant_id": st.session_state.participant_id,
                "group": st.session_state.group,
                "sus_responses": {f"sus_{i}": st.session_state.get(f"sus_{i}") for i in range(10)},
                "toast_responses": {f"toast_{i}": st.session_state.get(f"toast_{i}") for i in range(5)},
                "preference": st.session_state.get("preference"),
                "preference_reason": st.session_state.get("preference_reason"),
                "trust_breakpoint": st.session_state.get("trust_breakpoint"),
                "interruption_moment": st.session_state.get("interruption_moment"),
                "open_comments": st.session_state.get("open_comments"),
                "finish_ts": time.time()
            }
            st.session_state.final_data = final_data
            
            log_event("final_survey_completed", final_data)
            
            st.session_state.stage = "done"
            st.rerun()


def show_done():
    """完成页"""
    st.success("🎉 实验完成！感谢您的参与！")
    st.markdown("---")
    st.markdown("""
    **您的参与对我们非常重要！**
    
    - 所有数据将严格匿名处理，仅用于学术研究目的
    - 如对实验有任何疑问，请联系：xxxxxxxx@xx.edu.cn
    
    **补偿码：** `HS-3A-2024`
    
    您可以关闭此页面了。
    """)
    
    st.markdown("---")
    st.caption("惠山古镇 AI 导览员实验研究 | 江南大学")


# ==================== 主入口 ====================
def main():
    # 初始化 participant_id
    if "participant_id" not in st.session_state:
        url_pid = st.query_params.get("pid")
        if url_pid:
            st.session_state.participant_id = url_pid
        else:
            st.session_state.participant_id = f"P_{uuid.uuid4().hex[:8]}"
    
    # 从 URL 参数获取 group（用于 Qualtrics 集成）
    url_group = st.query_params.get("group")
    if url_group and url_group in VALID_GROUPS and "group" not in st.session_state:
        st.session_state.group = url_group
    
    # 初始化 stage
    if "stage" not in st.session_state:
        st.session_state.stage = "intro"
    
    # 根据 stage 渲染对应页面
    if st.session_state.stage == "intro":
        show_intro()
    elif st.session_state.stage == "consent":
        show_consent()
    elif st.session_state.stage == "pretest":
        show_pretest()
    elif st.session_state.stage == "route_intro":
        show_route_intro()
    elif st.session_state.stage == "poi":
        show_poi_page()
    elif st.session_state.stage == "final_survey":
        show_final_survey()
    elif st.session_state.stage == "done":
        show_done()
    else:
        st.session_state.stage = "intro"
        st.rerun()


if __name__ == "__main__":
    main()
