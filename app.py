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
from urllib.parse import quote

create_client = None

# ==================== 页面配置 ====================
st.set_page_config(page_title="惠山古镇 AI 导览 | 非遗数字体验", layout="centered", initial_sidebar_state="collapsed")

# ==================== GitHub 图片直链 ====================
def get_github_raw_url(filename: str) -> str:
    base = "https://raw.githubusercontent.com/nanaxyz11/huishan-guide-app/main/%E6%83%A0%E5%B1%B1%E5%8F%A45POI%E5%9B%BE/"
    return base + quote(filename)

MAIN_IMG_URL = get_github_raw_url("主图.jpg")
RECOMMEND_IMG_URLS = {
    "天下第二泉": get_github_raw_url("二泉.jpg"),
    "古华山门": get_github_raw_url("金莲桥.jpg"),
    "知鱼槛": get_github_raw_url("知鱼栏.jpg"),
    "竹炉山房": get_github_raw_url("竹炉山房.jpg"),
    "范文正公祠": get_github_raw_url("范文公正祠.jpg")
}

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

# ==================== 完整 CSS（与 app_副本2.py 完全相同） ====================
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
CONDITION_CODE_MAP = {"baseline": "A", "free_text": "B", "recchatbox": "C"}
VALID_CONDITIONS = set(CONDITION_CODE_MAP.keys())
FIELD_MODE_VALUES = {"1", "true", "yes", "field", "formal"}
LEGACY_MODE_VALUES = {"1", "true", "yes", "legacy", "all_in_one"}


def is_field_mode():
    return str(st.query_params.get("field", "")).strip().lower() in FIELD_MODE_VALUES


def is_legacy_mode():
    return str(st.query_params.get("legacy", "")).strip().lower() in LEGACY_MODE_VALUES


def field_query_value(name, default=""):
    value = st.query_params.get(name, default)
    if isinstance(value, list):
        return value[0] if value else default
    return value or default


def safe_secret(name, default=""):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


def group_sequence_code(group):
    return "".join(CONDITION_CODE_MAP.get(c, "?") for c in GROUP_CONDITION_MAP.get(group, []))


def safe_int(value):
    try:
        return int(value)
    except Exception:
        return None


def remember_supabase_error(context, error_detail, payload=None):
    st.session_state.setdefault("supabase_write_errors", []).append({
        "context": context,
        "error_detail": str(error_detail),
        "payload": payload or {},
        "timestamp": datetime.now().isoformat()
    })


def get_supabase_config():
    url = (safe_secret("SUPABASE_URL") or "").rstrip("/")
    key = safe_secret("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL or SUPABASE_KEY is not configured")
    token = key.replace("Bearer ", "")
    return url, token


def supabase_rest_headers(token):
    return {
        "apikey": token,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }


def supabase_rest_insert(table_name, payload):
    url, token = get_supabase_config()
    resp = requests.post(
        f"{url}/rest/v1/{table_name}",
        headers=supabase_rest_headers(token),
        json=payload,
        timeout=10
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"Supabase insert {table_name} failed: {resp.status_code} {resp.text[:500]}")
    return True


def supabase_rest_upsert_ignore(table_name, payload, conflict_col):
    url, token = get_supabase_config()
    headers = supabase_rest_headers(token)
    headers["Prefer"] = "resolution=ignore-duplicates,return=minimal"
    resp = requests.post(
        f"{url}/rest/v1/{table_name}?on_conflict={quote(str(conflict_col), safe='')}",
        headers=headers,
        json=payload,
        timeout=10
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"Supabase upsert {table_name} failed: {resp.status_code} {resp.text[:500]}")
    return True


def supabase_rest_update(table_name, payload, eq_col, eq_value):
    url, token = get_supabase_config()
    resp = requests.patch(
        f"{url}/rest/v1/{table_name}?{quote(str(eq_col))}=eq.{quote(str(eq_value), safe='')}",
        headers=supabase_rest_headers(token),
        json=payload,
        timeout=10
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"Supabase update {table_name} failed: {resp.status_code} {resp.text[:500]}")
    return True


def supabase_rest_select(table_name, columns="*", limit=1000):
    url, token = get_supabase_config()
    resp = requests.get(
        f"{url}/rest/v1/{table_name}?select={quote(columns, safe=',')}&limit={int(limit)}",
        headers=supabase_rest_headers(token),
        timeout=10
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"Supabase select {table_name} failed: {resp.status_code} {resp.text[:500]}")
    return resp.json()


def try_supabase_insert(table_name, payload_variants, context, pid="UNKNOWN", grp="UNKNOWN", exp_id="UNKNOWN"):
    supabase = st.session_state.get("supabase")
    if not supabase:
        remember_supabase_error(context, "supabase client is None")
        return False

    last_error = None
    for payload in payload_variants:
        try:
            supabase_rest_insert(table_name, payload)
            return True
        except Exception as e:
            last_error = e

    remember_supabase_error(context, last_error, payload_variants[-1] if payload_variants else {})
    log_app_error(context, str(last_error), pid, grp, exp_id)
    return False


def try_supabase_update(table_name, update_payload_variants, eq_col, eq_value, context, exp_id="UNKNOWN"):
    supabase = st.session_state.get("supabase")
    if not supabase:
        remember_supabase_error(context, "supabase client is None")
        return False

    last_error = None
    for payload in update_payload_variants:
        try:
            supabase_rest_update(table_name, payload, eq_col, eq_value)
            return True
        except Exception as e:
            last_error = e

    remember_supabase_error(context, last_error, update_payload_variants[-1] if update_payload_variants else {})
    log_app_error(context, str(last_error), exp_id=exp_id)
    return False


def write_legacy_event(event_type, payload=None):
    payload = payload or {}
    query_text = payload.get("query_text") or payload.get("user_query_text") or ""
    legacy_payload = {
        "participant_id": st.session_state.get("participant_id", "UNKNOWN"),
        "experimental_condition": st.session_state.get("current_condition", "UNKNOWN"),
        "poi_id": st.session_state.get("current_poi_id", "UNKNOWN"),
        "action_type": event_type,
        "time_on_page_seconds": payload.get("dwell_seconds") or payload.get("time_on_page_seconds"),
        "user_query_text": query_text,
        "user_query_word_count": len(str(query_text).split()) if query_text else 0,
        "rag_response_time_ms": payload.get("response_latency_ms") or payload.get("rag_response_time_ms"),
        "retrieved_chunks_saved": str(payload.get("retrieved_chunks") or payload.get("retrieved_chunks_saved") or ""),
        "displayed_source_cue": payload.get("source_chip") or payload.get("displayed_source_cue"),
        "timestamp": datetime.now().isoformat()
    }
    base = {
        "participant_id": st.session_state.get("participant_id", "UNKNOWN"),
        "group": st.session_state.get("group", "UNKNOWN"),
        "group_name": st.session_state.get("group", "UNKNOWN"),
        "poi_id": st.session_state.get("current_poi_id", "UNKNOWN"),
        "condition": st.session_state.get("current_condition", "UNKNOWN"),
        "event_type": event_type,
        "timestamp": datetime.now().isoformat(),
        **payload
    }
    return try_supabase_insert("interaction_logs", [
        legacy_payload,
        base,
        {k: v for k, v in base.items() if k != "group_name"},
        {k: v for k, v in base.items() if k != "group"},
    ], f"legacy_{event_type}",
        pid=base["participant_id"], grp=st.session_state.get("group", "UNKNOWN"),
        exp_id=payload.get("exposure_id", "UNKNOWN"))

# ==================== 错误日志辅助函数 ====================
def log_app_error(context, error_detail, pid="UNKNOWN", grp="UNKNOWN", exp_id="UNKNOWN"):
    error_data = {
        "participant_id": pid,
        "group": grp,
        "exposure_id": exp_id,
        "context": context,
        "error_detail": str(error_detail),
        "timestamp": datetime.now().isoformat()
    }
    os.makedirs("logs", exist_ok=True)
    with open("logs/app_errors.csv", "a", encoding="utf-8") as f:
        f.write(f"{error_data}\n")
    if "supabase" in st.session_state and st.session_state.get("supabase"):
        for payload in [
            {
                "participant_id": pid,
                "stage": st.session_state.get("stage", "unknown"),
                "poi_id": st.session_state.get("current_poi_id"),
                "condition": st.session_state.get("current_condition"),
                "error_type": context,
                "error_message": str(error_detail),
                "payload": {
                    "group_code": grp,
                    "exposure_id": exp_id,
                    "local_error_data": error_data
                },
                "created_at": datetime.now().isoformat()
            },
            error_data
        ]:
            try:
                supabase_rest_insert("app_errors", payload)
                break
            except:
                pass

# ==================== Supabase REST 配置 ====================
if "supabase" not in st.session_state:
    try:
        supabase_url = safe_secret("SUPABASE_URL")
        supabase_key = safe_secret("SUPABASE_KEY")
        if not supabase_url or not supabase_key:
            raise RuntimeError("SUPABASE_URL or SUPABASE_KEY is not configured")
        st.session_state.supabase = {"url": supabase_url.rstrip("/"), "key_configured": True}
    except Exception as e:
        st.session_state.supabase = None
        error_data = {
            "participant_id": "UNKNOWN",
            "group": "UNKNOWN",
            "exposure_id": "UNKNOWN",
            "context": "supabase_init",
            "error_detail": str(e),
            "timestamp": datetime.now().isoformat()
        }
        os.makedirs("logs", exist_ok=True)
        with open("logs/app_errors.csv", "a", encoding="utf-8") as f:
            f.write(f"{error_data}\n")
        st.warning("Supabase 连接失败，日志将仅保存在本地")

# ==================== 均衡分组 ====================
def assign_group_balanced():
    supabase = st.session_state.get("supabase")
    if supabase:
        last_error = None
        for group_col in ["group_name", "group_code", "group"]:
            try:
                rows = supabase_rest_select("participants", group_col)
                if rows:
                    cnt = {g: 0 for g in VALID_GROUPS}
                    for row in rows:
                        if row.get(group_col) in cnt:
                            cnt[row[group_col]] += 1
                    return min(cnt, key=cnt.get)
            except Exception as e:
                last_error = e
        if last_error:
            log_app_error("assign_group_balanced", str(last_error),
                          pid=st.session_state.get("participant_id", "UNKNOWN"),
                          grp=st.session_state.get("group", "UNKNOWN"))
    return random.choice(VALID_GROUPS)

# ==================== 数据库写入函数（8 表拆分） ====================
def ensure_field_participant(pid, group):
    """Create a minimal participant row for field mode so poi_exposures FK will not fail.
    WJX still owns Q1 data; this row only preserves participant_id/group linkage in Supabase.
    """
    if not st.session_state.get("supabase") or not pid or group not in VALID_GROUPS:
        return
    base = {
        "participant_id": pid,
        "assigned_sequence": group_sequence_code(group),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    variants = [
        {**base, "group_code": group},
        {**base, "group_name": group},
        {**base, "group": group},
    ]
    last_error = None
    for payload in variants:
        try:
            supabase_rest_upsert_ignore("participants", payload, "participant_id")
            return
        except Exception as e:
            last_error = e
    remember_supabase_error("ensure_field_participant", last_error, variants[-1])
    log_app_error("ensure_field_participant", str(last_error), pid=pid, grp=group)


def write_participant(pid, group, pretest_data):
    if not st.session_state.get("supabase"):
        return
    cei_values = [safe_int(pretest_data.get(f"cei_{i}")) for i in range(1, 9)]
    cei_values = [v for v in cei_values if v is not None]
    detailed_payload = {
        "participant_id": pid,
        "assigned_sequence": group_sequence_code(group),
        "consent_given": True,
        "consent_ts": datetime.fromtimestamp(st.session_state.get("consent_ts", time.time())).isoformat(),
        "age": safe_int(pretest_data.get("age")),
        "gender": pretest_data.get("gender"),
        "education": pretest_data.get("education"),
        "discipline": pretest_data.get("discipline"),
        "heritage_visit_freq": safe_int(pretest_data.get("heritage_visit_freq")),
        "huishan_familiarity": safe_int(pretest_data.get("huishan_familiarity")),
        "genai_familiarity": safe_int(pretest_data.get("genai_familiarity")),
        "mobile_guide_exp": safe_int(pretest_data.get("mobile_guide_exp")),
        **{f"cei_{i}": safe_int(pretest_data.get(f"cei_{i}")) for i in range(1, 9)},
        "cei_mean": round(sum(cei_values) / len(cei_values), 3) if cei_values else None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    ok = try_supabase_insert("participants", [
        {**detailed_payload, "group_name": group},
        {**detailed_payload, "group_code": group},
        {"participant_id": pid, "group_name": group, "pretest_data": pretest_data, "created_at": datetime.now().isoformat()},
        {"participant_id": pid, "group": group, "pretest_data": pretest_data, "created_at": datetime.now().isoformat()},
        {"participant_id": pid, "group_name": group},
        {"participant_id": pid, "group": group},
    ], "write_participant", pid, group)
    write_legacy_event("pretest_completed", {"pretest_data": pretest_data})

def write_poi_exposure(pid, group, exposure_id, poi_id, condition, sequence_position, page_load_ts):
    if not st.session_state.get("supabase"):
        return
    base_payload = {
        "participant_id": pid,
        "exposure_id": exposure_id,
        "poi_id": poi_id,
        "poi_name": st.session_state.get("current_poi_name"),
        "condition": condition,
        "condition_order_base": group_sequence_code(group),
        "sequence_position": sequence_position,
        "page_load_ts": datetime.fromtimestamp(page_load_ts).isoformat(),
        "ui_version": "streamlit-3condition-0530",
        "created_at": datetime.now().isoformat()
    }
    ok = try_supabase_insert("poi_exposures", [
        {**base_payload, "group_name": group},
        {**base_payload, "group_code": group},
        {"participant_id": pid, "exposure_id": exposure_id, "poi_id": poi_id, "condition": condition, "group_name": group, "created_at": datetime.now().isoformat()},
        {"participant_id": pid, "exposure_id": exposure_id, "poi_id": poi_id, "condition": condition},
    ], "write_poi_exposure", pid, group, exposure_id)
    write_legacy_event("poi_exposure_started", {
        "exposure_id": exposure_id,
        "sequence_position": sequence_position,
        "page_load_ts": datetime.fromtimestamp(page_load_ts).isoformat()
    })

def write_interaction_turn(exposure_id, query_text, query_type, response_text, response_latency_ms, retrieved_chunks, source_chip):
    if not st.session_state.get("supabase"):
        return
    try:
        retrieved_payload = retrieved_chunks
        if isinstance(retrieved_chunks, str):
            try:
                retrieved_payload = json.loads(retrieved_chunks)
            except Exception:
                retrieved_payload = {"raw": retrieved_chunks}
        base_payload = {
            "participant_id": st.session_state.get("participant_id"),
            "exposure_id": exposure_id,
            "poi_id": st.session_state.get("current_poi_id"),
            "condition": st.session_state.get("current_condition"),
            "query_text": query_text,
            "query_type": query_type,
            "response_text": response_text,
            "response_latency_ms": response_latency_ms,
            "retrieved_chunks": retrieved_payload,
            "source_chip": source_chip,
            "created_at": datetime.now().isoformat()
        }
        ok = try_supabase_insert("interaction_turns", [
            base_payload,
            {k: v for k, v in base_payload.items() if k not in ["retrieved_chunks", "source_chip"]},
            {**{k: v for k, v in base_payload.items() if k not in ["retrieved_chunks", "source_chip", "created_at"]}, "timestamp": datetime.now().isoformat()},
        ], "write_interaction_turn",
            pid=st.session_state.get("participant_id", "UNKNOWN"),
            grp=st.session_state.get("group", "UNKNOWN"),
            exp_id=exposure_id)
        write_legacy_event("question_submitted", base_payload)
    except Exception as e:
        log_app_error("write_interaction_turn", str(e),
                      pid=st.session_state.get("participant_id", "UNKNOWN"),
                      exp_id=exposure_id)

def write_micro_survey(pid, group, exposure_id, poi_id, condition, micro_data):
    if not st.session_state.get("supabase"):
        return
    payload = {
        "participant_id": pid,
        "exposure_id": exposure_id,
        "sequence_position": st.session_state.get("poi_index", 0) + 1,
        "poi_id": poi_id,
        "condition": condition,
        **micro_data,
        "submitted_at": datetime.now().isoformat()
    }
    ok = try_supabase_insert("micro_surveys", [
        payload,
        {**payload, "group_name": group},
        {**{k: v for k, v in payload.items() if k != "submitted_at"}, "created_at": datetime.now().isoformat()},
    ], "write_micro_survey", pid, group, exposure_id)
    if not ok:
        ok = try_supabase_insert("micro_survey", [
            {**payload, "group": group, "timestamp": datetime.now().isoformat()},
            {**payload, "group_name": group, "timestamp": datetime.now().isoformat()},
        ], "write_micro_survey_legacy", pid, group, exposure_id)
    write_legacy_event("micro_survey_submitted", payload)

def write_final_survey(pid, group, final_data):
    if not st.session_state.get("supabase"):
        return
    payload = {
        "participant_id": pid,
        "preference": final_data.get("preference"),
        "preference_reason": final_data.get("preference_reason"),
        "trust_breakpoint": final_data.get("trust_breakpoint"),
        "interruption_moment": final_data.get("interruption_moment"),
        "open_comments": final_data.get("open_comments"),
        "sus_json": final_data.get("sus"),
        "toast_json": final_data.get("toast"),
        "chat_quality_json": {k: v for k, v in final_data.items() if k.endswith("_c1") or k.endswith("_c2") or k.endswith("_c3") or k in ["recchatbox_c4", "recchatbox_c5"]},
        "submitted_at": datetime.now().isoformat()
    }
    ok = try_supabase_insert("final_surveys", [
        payload,
        {**payload, "group_name": group},
        {"participant_id": pid, "group_name": group, "final_data": final_data, "created_at": datetime.now().isoformat()},
        {"participant_id": pid, "group": group, "final_data": final_data, "created_at": datetime.now().isoformat()},
    ], "write_final_survey", pid, group)
    if not ok:
        ok = try_supabase_insert("final_survey", [
            {"participant_id": pid, "group": group, "final_data": final_data, "timestamp": datetime.now().isoformat()},
            {"participant_id": pid, "group_name": group, "final_data": final_data, "timestamp": datetime.now().isoformat()},
        ], "write_final_survey_legacy", pid, group)
    write_legacy_event("final_survey_completed", {"final_data": final_data})

def write_poi_completed(exposure_id, dwell_seconds):
    if not st.session_state.get("supabase"):
        return
    ok = try_supabase_update("poi_exposures", [
        {"next_click_ts": datetime.now().isoformat(), "dwell_seconds": dwell_seconds},
        {"dwell_seconds": dwell_seconds},
    ], "exposure_id", exposure_id, "write_poi_completed", exp_id=exposure_id)
    write_legacy_event("poi_exposure_completed", {
        "exposure_id": exposure_id,
        "dwell_seconds": dwell_seconds
    })

# ==================== 三个渲染函数（完整，推荐问题循环衍生） ====================
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
    
    if "followup_generation" not in st.session_state:
        st.session_state.followup_generation = 0

    # 仅在当前 POI 尚未产生后续问题时加载初始推荐。
    if "followup_questions" not in st.session_state or not st.session_state.followup_questions:
        st.session_state.followup_questions = poi.get("recs", [
            f"关于{poi['name']}还有哪些历史细节？",
            f"这里与无锡本地文化有什么关联？",
            f"有什么值得关注的参观细节？"
        ])

    st.markdown("#### 💬 向 AI 提问")
    
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and "source" in msg:
                st.markdown(f'<span class="source-chip">🔍 {msg["source"]}</span>', unsafe_allow_html=True)

    st.markdown("#### 💡 推荐继续追问")
    st.caption("点击任一问题后，AI 回答完会继续生成下一轮 3 个推荐问题。")
    for i, q in enumerate(st.session_state.followup_questions[:3]):
        btn_key = f"rec_q_{st.session_state.current_poi_id}_{st.session_state.followup_generation}_{i}"
        if st.button(f"❓ {q}", key=btn_key, use_container_width=True):
            handle_question(q, poi, "recchatbox", query_type="suggested")
    
    if prompt := st.chat_input("输入您的问题..."):
        handle_question(prompt, poi, "recchatbox", query_type="free")

# ==================== Dify RAG 函数 ====================
def simulate_rag_engine(user_query, poi):
    start = time.time()
    key = safe_secret("DIFY_API_KEY_MAIN", "Bearer app-rzITs8smrzMUhhdraDriLuRp")
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
        return ans, src, str(resources), time.time() - start
    except Exception as e:
        log_app_error("simulate_rag_engine", str(e),
                      pid=st.session_state.get("participant_id", "UNKNOWN"),
                      grp=st.session_state.get("group", "UNKNOWN"),
                      exp_id=st.session_state.get("current_exposure_id", "UNKNOWN"))
        return "【网络或服务异常】请稍后重试。", "故障降级", "[Error]", time.time() - start

def fallback_followup_questions(poi_name, user_question=""):
    round_no = st.session_state.get("followup_generation", 0) + 1
    pools = [
        [
            f"{poi_name}最容易被游客误解的历史细节是什么？",
            f"{poi_name}和惠山古镇整体文脉有什么关系？",
            f"如果只记住一个关于{poi_name}的文化重点，应该是什么？"
        ],
        [
            f"关于{poi_name}有没有更具体的史料来源？",
            f"{poi_name}体现了哪些江南文化或地方价值？",
            f"普通游客在现场观察{poi_name}时应注意什么？"
        ],
        [
            f"{poi_name}的故事和今天的旅游体验有什么联系？",
            f"关于{poi_name}，AI 的解释有哪些需要谨慎核查的地方？",
            f"能否用更短的话概括{poi_name}的文化意义？"
        ]
    ]
    selected = pools[(round_no - 1) % len(pools)]
    return [q for q in selected if q != user_question][:3]


def normalize_followup_questions(raw_questions, poi_name, user_question=""):
    fallback = fallback_followup_questions(poi_name, user_question)

    if isinstance(raw_questions, dict):
        raw_questions = (
            raw_questions.get("questions")
            or raw_questions.get("followup_questions")
            or raw_questions.get("data")
            or []
        )
    if isinstance(raw_questions, str):
        raw_questions = [raw_questions]

    cleaned = []
    for item in raw_questions or []:
        if isinstance(item, dict):
            item = item.get("question") or item.get("text") or item.get("title") or ""
        q = re.sub(r"^\s*[\-\*\d\.\、\)\]]+\s*", "", str(item)).strip()
        if q and q != user_question and q not in cleaned:
            cleaned.append(q)

    for q in fallback:
        if len(cleaned) >= 3:
            break
        if q not in cleaned:
            cleaned.append(q)
    return cleaned[:3]


def generate_followup_questions(user_question, ai_answer, pid):
    key = safe_secret("DIFY_API_KEY_FOLLOWUP", "Bearer app-CCck7NxI8NLZIxf24Q247Hti")
    poi_name = st.session_state.get("current_poi_name", "当前点位")
    try:
        resp = requests.post("https://api.dify.ai/v1/chat-messages",
            headers={"Authorization": key, "Content-Type": "application/json"},
            json={"inputs": {"current_poi": poi_name}, "query": (
                    f"当前文化遗产点位：{poi_name}\n"
                    f"用户刚才的问题：{user_question}\n"
                    f"AI刚才的回答：{ai_answer}\n"
                    "请基于用户兴趣和刚才回答，生成下一轮刚好3个可点击的中文追问。"
                    "要求：不要重复用户原问题；不要输出解释；只输出JSON数组，例如[\"问题1？\",\"问题2？\",\"问题3？\"]。"
                ),
                  "response_mode": "blocking", "user": pid}, timeout=10)
        answer = resp.json().get("answer", "[]").strip()
        answer = re.sub(r"^```(?:json)?|```$", "", answer, flags=re.I | re.M).strip()

        parsed = None
        try:
            parsed = json.loads(answer)
        except Exception:
            match = re.search(r"\[[\s\S]*?\]", answer)
            if match:
                parsed = json.loads(match.group(0))
            else:
                parsed = [
                    re.sub(r"^\s*[\-\*\d\.\、\)\]]+\s*", "", line).strip()
                    for line in answer.splitlines()
                    if "?" in line or "？" in line
                ]
        return normalize_followup_questions(parsed, poi_name, user_question)
    except Exception as e:
        log_app_error("generate_followup_questions", str(e), pid=pid)
        return normalize_followup_questions([], poi_name, user_question)

def handle_question(question, poi, cond, query_type=None):
    with st.spinner("AI 导览员正在查阅史料..."):
        ans, src, chunks, elap = simulate_rag_engine(question, poi)
        if "chat_messages" not in st.session_state:
            st.session_state.chat_messages = []
        st.session_state.chat_messages.append({"role": "user", "content": question})
        st.session_state.chat_messages.append({"role": "assistant", "content": ans, "source": src})

        write_interaction_turn(
            exposure_id=st.session_state.get("current_exposure_id", "UNKNOWN"),
            query_text=question,
            query_type=query_type or ("free" if cond == "free_text" else "suggested"),
            response_text=ans,
            response_latency_ms=round(elap * 1000),
            retrieved_chunks=chunks,
            source_chip=src
        )

        st.markdown(f'<script>speakText("{ans.replace('"', '\\"')}")</script>', unsafe_allow_html=True)

        # RecChatbox 每轮回答后都生成下一轮 3 个推荐问题。
        if cond == "recchatbox":
            new_questions = generate_followup_questions(question, ans, st.session_state.participant_id)
            st.session_state.followup_questions = new_questions
            st.session_state.followup_generation = st.session_state.get("followup_generation", 0) + 1
        else:
            st.session_state.followup_questions = []

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
    st.info("请注意量表方向：除特别说明外，1=非常不同意，7=非常同意。探索倾向题为 5 点量表：1=非常不同意，5=非常同意。")
    with st.form("pretest_form"):
        age = st.text_input("1. 您的年龄", placeholder="例如：25")
        gender = st.selectbox("2. 您的性别", ["请选择", "男", "女", "不愿透露"])
        education = st.selectbox("3. 您的最高学历", ["请选择", "高中/中专", "大专", "本科", "硕士", "博士及以上"])
        discipline = st.selectbox("4. 您的专业背景", ["请选择", "设计/艺术", "人文/历史", "计算机/信息技术", "旅游/管理", "其他"])
        heritage_visit_freq = st.slider("5. 过去一年参观博物馆/历史街区的频率（1=从不，7=非常频繁）", 1, 7, 4, help="1=从不，7=非常频繁")
        huishan_familiarity = st.slider("6. 我熟悉惠山古镇或曾经到访（1=非常不同意，7=非常同意）", 1, 7, 4)
        genai_familiarity = st.slider("7. 我熟悉生成式 AI 的使用（1=非常不同意，7=非常同意）", 1, 7, 4)
        mobile_guide_exp = st.slider("8. 我有使用手机导览的经验（1=非常不同意，7=非常同意）", 1, 7, 4)
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
            if not age or gender == "请选择" or education == "请选择":
                st.error("请完成所有必填项")
                st.stop()
            group = assign_group_balanced()
            st.session_state.group = group
            pretest = {"age": age, "gender": gender, "education": education, "discipline": discipline,
                       "heritage_visit_freq": heritage_visit_freq, "huishan_familiarity": huishan_familiarity,
                       "genai_familiarity": genai_familiarity, "mobile_guide_exp": mobile_guide_exp,
                       **{f"cei_{i+1}": cei[i] for i in range(8)}}
            st.session_state.pretest_data = pretest
            write_participant(st.session_state.participant_id, group, pretest)
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

    # 只在真正进入新 POI 时生成 exposure_id。聊天触发 st.rerun() 时不能清空状态。
    if st.session_state.get("active_poi_index") != poi_idx:
        exposure_id = str(uuid.uuid4())
        st.session_state.current_exposure_id = exposure_id
        st.session_state.chat_messages = []
        st.session_state.followup_questions = []
        st.session_state.followup_generation = 0
        st.session_state.poi_page_load_ts = time.time()
        st.session_state.active_poi_index = poi_idx

        write_poi_exposure(
            pid=st.session_state.participant_id,
            group=st.session_state.group,
            exposure_id=exposure_id,
            poi_id=poi["id"],
            condition=condition,
            sequence_position=poi_idx + 1,
            page_load_ts=st.session_state.poi_page_load_ts
        )

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
        write_poi_completed(st.session_state.current_exposure_id, round(dwell, 2))
        st.session_state.pending_poi_index = poi_idx
        st.session_state.stage = "micro_survey"
        st.rerun()

def show_micro_survey():
    poi_idx = st.session_state.pending_poi_index
    poi = POIS[poi_idx]
    poi_id = poi["id"]
    st.title(f"📋 点位 {poi_idx+1} 体验问卷")
    st.markdown(f"**{poi['name']}**")
    st.info("本页所有体验量表均为 7 点量表：1=非常不同意，7=非常同意。")
    with st.form("micro_form"):
        mental = st.slider("理解信息需要较多脑力（1=非常不同意，7=非常同意）", 1, 7, 4)
        time_p = st.slider("感到时间紧迫（1=非常不同意，7=非常同意）", 1, 7, 4)
        effort = st.slider("需要付出较多努力（1=非常不同意，7=非常同意）", 1, 7, 4)
        frust = st.slider("感到烦躁或受挫（1=非常不同意，7=非常同意）", 1, 7, 4)
        control = st.slider("能自主决定看什么、问什么（1=非常不同意，7=非常同意）", 1, 7, 4)
        interrupt = st.slider("界面打断了我观察真实环境（1=非常不同意，7=非常同意）", 1, 7, 4)
        engage = st.slider("信息帮助我把手机内容和眼前点位联系起来（1=非常不同意，7=非常同意）", 1, 7, 4)
        satisfy = st.slider("信息满足了我的好奇（1=非常不同意，7=非常同意）", 1, 7, 4)
        trust = st.slider("信息在历史文化上是可信的（1=非常不同意，7=非常同意）", 1, 7, 4)
        source_use = st.slider("来源标注让我更愿意相信信息（1=非常不同意，7=非常同意）", 1, 7, 4)
        learn_conf = st.slider("我能向别人说明该点位的核心文化意义（1=非常不同意，7=非常同意）", 1, 7, 4)
        q_map = {
            "fanwenzheng_gongci": ("范文正公祠主要祭祀哪位历史人物？", ["范仲淹", "苏轼", "陆羽", "阿炳"], "范仲淹"),
            "guhuashanmen": ("金莲桥最适合作为哪类体验节点？", ["空间过渡", "商业消费", "现代交通", "纯自然景观"], "空间过渡"),
            "bayinjian": ("八音涧的“八音”更接近哪种含义？", ["水声类比传统乐音", "八件实物乐器", "八位诗人", "八座亭子"], "水声类比传统乐音"),
            "zhulu_shanfang": ("竹炉山房最适合连接哪种文化主题？", ["文人茶事", "战争防御", "商业票号", "近代工业"], "文人茶事"),
            "erquan": ("关于“天下第二泉”的严谨说法？", ["《茶经》和《煎茶水记》需区分", "完全由苏轼排名", "由阿炳命名", "现代营销命名"], "《茶经》和《煎茶水记》需区分")
        }
        q_text, opts, correct = q_map[poi_id]
        answer = st.radio(q_text, opts)
        if st.form_submit_button("提交并继续"):
            is_correct = (answer == correct)
            micro_data = {
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
            write_micro_survey(
                pid=st.session_state.participant_id,
                group=st.session_state.group,
                exposure_id=st.session_state.current_exposure_id,
                poi_id=poi_id,
                condition=st.session_state.current_condition,
                micro_data=micro_data
            )
            st.session_state.poi_index = poi_idx + 1
            if st.session_state.poi_index >= len(POIS):
                st.session_state.stage = "final_survey"
            else:
                st.session_state.stage = "poi"
                # 重置聊天和推荐问题，为下一个 POI 做准备
                st.session_state.chat_messages = []
                st.session_state.followup_questions = []
                st.session_state.followup_generation = 0
            st.rerun()

def show_final_survey():
    st.title("📝 整体体验评价")
    st.markdown("请分别评价您体验过的三种界面。")
    st.info("请注意：SUS 与交互体验题为 5 点量表（1=非常不同意，5=非常同意）；TOAST 信任题为 7 点量表（1=非常不同意，7=非常同意）。")
    conditions = ["baseline", "free_text", "recchatbox"]
    names = {"baseline": "A: 原始网页", "free_text": "B: 自由提问 AI", "recchatbox": "C: 推荐式交互"}
    with st.form("final_form"):
        c_answers = {}
        for cond in conditions:
            st.markdown(f"#### {names[cond]}")
            for i, sus_item in enumerate([
                "我愿意继续使用该界面。", "该界面显得不必要地复杂。", "该界面容易上手。",
                "我需要他人帮助才能顺利使用。", "功能整合得很好。", "在不同点位表现不一致。",
                "多数游客能很快学会。", "使用起来很累赘。", "使用时有信心。", "使用前需要学习很多东西。"]):
                st.slider(f"SUS {i+1}: {sus_item}（1=非常不同意，5=非常同意）", 1, 5, 3, key=f"sus_{cond}_{i}")
            for i, toast_item in enumerate([
                "帮助我完成文化信息探索目标。", "表现稳定一致。", "反应符合我的预期。",
                "信息很少让我意外或困惑。", "我愿意依赖该界面提供的信息。"]):
                st.slider(f"TOAST {i+1}: {toast_item}（1=非常不同意，7=非常同意）", 1, 7, 4, key=f"toast_{cond}_{i}")
            if cond != "baseline":
                st.markdown("**交互体验评价**")
                c1 = st.slider("提出问题是容易的。（1=非常不同意，5=非常同意）", 1, 5, 3, key=f"q_easy_{cond}")
                c2 = st.slider("我理解系统给出的回答。（1=非常不同意，5=非常同意）", 1, 5, 3, key=f"ans_understand_{cond}")
                c3 = st.slider("系统回答让我觉得内容更有趣。（1=非常不同意，5=非常同意）", 1, 5, 3, key=f"ans_interest_{cond}")
                c_answers[f"{cond}_c1"] = c1
                c_answers[f"{cond}_c2"] = c2
                c_answers[f"{cond}_c3"] = c3
                if cond == "recchatbox":
                    c4 = st.slider("系统推荐的问题是清楚易懂的。（1=非常不同意，5=非常同意）", 1, 5, 3, key=f"recq_understand")
                    c5 = st.slider("系统推荐的问题能激发我继续探索。（1=非常不同意，5=非常同意）", 1, 5, 3, key=f"recq_interest")
                    c_answers["recchatbox_c4"] = c4
                    c_answers["recchatbox_c5"] = c5
            st.markdown("---")
        st.markdown("#### 偏好与开放题")
        pref = st.radio("最愿意使用哪一种？", ["原始网页", "自由提问 AI", "推荐式交互"], key="pref")
        pref_reason = st.text_area("请说明原因")
        trust_break = st.text_area("有没有哪一刻你开始相信或不相信系统？")
        interrupt_moment = st.text_area("有没有哪一刻手机信息干扰了你看真实场景？")
        comments = st.text_area("其他意见或建议")
        if st.form_submit_button("提交评价"):
            final_data = {
                "preference": pref,
                "preference_reason": pref_reason,
                "trust_breakpoint": trust_break,
                "interruption_moment": interrupt_moment,
                "open_comments": comments,
                "sus": {f"{cond}_{i}": st.session_state.get(f"sus_{cond}_{i}") for cond in conditions for i in range(10)},
                "toast": {f"{cond}_{i}": st.session_state.get(f"toast_{cond}_{i}") for cond in conditions for i in range(5)},
                **c_answers
            }
            write_final_survey(st.session_state.participant_id, st.session_state.group, final_data)
            st.session_state.stage = "done"
            st.rerun()

def show_done():
    st.success("🎉 实验完成！感谢您的参与！")
    st.markdown("补偿码：`HS-3A-2024`。您可以关闭此页面了。")
    st.caption("惠山古镇 AI 导览员实验研究 | 江南大学")


def show_direct_condition_page():
    condition = st.query_params.get("condition", "baseline")
    poi_id = st.query_params.get("poi", POI_ORDER[0])
    if condition not in VALID_CONDITIONS:
        condition = "baseline"
    if poi_id not in POI_ORDER:
        poi_id = POI_ORDER[0]

    poi_idx = POI_ORDER.index(poi_id)
    poi = POIS[poi_idx]
    poi_data = poi_database.get(poi_id, {"name": poi["name"], "info": "暂无详细介绍。"})
    direct_key = f"{condition}:{poi_id}"

    st.session_state.group = st.query_params.get("group", st.session_state.get("group", "G_DIRECT"))
    st.session_state.current_poi_id = poi_id
    st.session_state.current_poi_name = poi["name"]
    st.session_state.current_condition = condition

    if st.session_state.get("active_direct_key") != direct_key:
        st.session_state.current_exposure_id = str(uuid.uuid4())
        st.session_state.chat_messages = []
        st.session_state.followup_questions = []
        st.session_state.followup_generation = 0
        st.session_state.poi_page_load_ts = time.time()
        st.session_state.active_direct_key = direct_key
        write_poi_exposure(
            pid=st.session_state.participant_id,
            group=st.session_state.group,
            exposure_id=st.session_state.current_exposure_id,
            poi_id=poi_id,
            condition=condition,
            sequence_position=poi_idx + 1,
            page_load_ts=st.session_state.poi_page_load_ts
        )

    st.caption(f"直接测试模式：{CONDITION_CODE_MAP[condition]} · {poi['name']}")
    st.markdown(f"""
    <div class="jn-hero" style="background-image: linear-gradient(90deg, rgba(10,30,36,.68), rgba(10,30,36,.28)), url('{get_img_url_or_local("主图.jpg", MAIN_IMG_URL)}');">
      <div class="jn-hero-title">惠山古镇 <span>AI 导览员</span></div>
      <div class="jn-hero-sub">直接测试：{poi['name']}</div>
    </div>
    """, unsafe_allow_html=True)

    if condition == "baseline":
        render_baseline(poi_data)
    elif condition == "free_text":
        render_free_text_rag(poi_data)
    else:
        render_recchatbox(poi_data)


def build_external_survey_url(base_url, params):
    if not base_url:
        return ""
    sep = "&" if "?" in base_url else "?"
    query = "&".join([f"{quote(str(k))}={quote(str(v))}" for k, v in params.items() if v is not None])
    return f"{base_url}{sep}{query}" if query else base_url


def field_survey_url(kind, params):
    secret_key = {
        "pretest": "WJX_PRETEST_URL",
        "micro": "WJX_MICRO_SURVEY_URL",
        "final": "WJX_FINAL_SURVEY_URL"
    }.get(kind)
    if not secret_key:
        return ""
    return build_external_survey_url(safe_secret(secret_key, ""), params)


APP_BASE_URL = "https://huishan-guide-app-d5d45rkqrmgcptdynxx4yj.streamlit.app/"


def field_app_url(pid, group, step=None, pause=False):
    params = {"field": "1", "pid": pid, "group": group}
    if step is not None:
        params["step"] = step
    if pause:
        params["pause"] = "1"
    return build_external_survey_url(safe_secret("APP_BASE_URL", APP_BASE_URL), params)


def field_int_query(name, default=None):
    raw = field_query_value(name, "")
    try:
        return int(raw)
    except Exception:
        return default


def set_field_query_params(step=None, pause=False):
    st.query_params["field"] = "1"
    st.query_params["pid"] = st.session_state.participant_id
    st.query_params["group"] = st.session_state.group
    if step is None:
        try:
            del st.query_params["step"]
        except Exception:
            pass
    else:
        st.query_params["step"] = str(step)
    if pause:
        st.query_params["pause"] = "1"
    else:
        for key in ["pause", "completed_exposure_id", "dwell_seconds"]:
            try:
                del st.query_params[key]
            except Exception:
                pass


def restore_pending_micro_meta_from_url():
    step_from_url = field_int_query("step", None)
    pause_from_url = str(field_query_value("pause", "")).strip().lower() in FIELD_MODE_VALUES
    if not pause_from_url or step_from_url is None:
        return None
    if not st.session_state.get("participant_id") or st.session_state.get("group") not in VALID_GROUPS:
        return None
    if step_from_url < 0 or step_from_url >= len(POIS):
        return None
    meta = field_current_metadata(step_from_url)
    exposure_id = field_query_value("completed_exposure_id", st.session_state.get("current_exposure_id", ""))
    dwell_raw = field_query_value("dwell_seconds", "")
    try:
        dwell_seconds = round(float(dwell_raw), 2)
    except Exception:
        dwell_seconds = None
    if exposure_id:
        meta["exposure_id"] = exposure_id
    if dwell_seconds is not None:
        meta["dwell_seconds"] = dwell_seconds
    if "exposure_id" in meta and "dwell_seconds" in meta:
        st.session_state.pending_field_meta = meta
        return meta
    return None


def field_mode_setup():
    pid = field_query_value("pid", "")
    group = field_query_value("group", "")
    if not pid and group in VALID_GROUPS:
        pid = st.session_state.get("participant_id", "")
    if not group:
        group = st.session_state.get("group", "")

    # 正式现场模式允许一个统一入口链接：?field=1。
    # 若 URL 未带 pid/group，先进入研究助理设置页，不自动生成被试 ID，
    # 避免把随机 P_FIELD_* 误写入问卷星或 Supabase。
    st.session_state.field_needs_subject_setup = not (pid and group in VALID_GROUPS)

    if pid:
        st.session_state.participant_id = pid
    elif "participant_id" not in st.session_state:
        st.session_state.participant_id = ""

    if group in VALID_GROUPS:
        st.session_state.group = group
    elif "group" not in st.session_state or st.session_state.get("group") not in VALID_GROUPS:
        st.session_state.group = None

    subject_key = f"{st.session_state.get('participant_id', '')}:{st.session_state.get('group')}"
    if st.session_state.get("field_subject_key") != subject_key:
        st.session_state.field_subject_key = subject_key
        st.session_state.field_stage = "field_intro"
        st.session_state.field_poi_index = 0
        st.session_state.active_field_key = None
        st.session_state.current_exposure_id = None
        st.session_state.field_route_completed_logged = False
        st.session_state.field_route_started_logged = False
        st.session_state.chat_messages = []
        st.session_state.followup_questions = []
        st.session_state.followup_generation = 0

    step_from_url = field_int_query("step", None)
    pause_from_url = str(field_query_value("pause", "")).strip().lower() in FIELD_MODE_VALUES
    if step_from_url is not None:
        if step_from_url >= len(POIS):
            st.session_state.field_stage = "field_final"
            st.session_state.field_poi_index = len(POIS)
        else:
            st.session_state.field_poi_index = max(0, min(step_from_url, len(POIS) - 1))
            if pause_from_url and (st.session_state.get("pending_field_meta") or restore_pending_micro_meta_from_url()):
                st.session_state.field_stage = "field_micro_pause"
            else:
                st.session_state.field_stage = "field_poi"

    st.session_state.setdefault("field_stage", "field_intro")
    st.session_state.setdefault("field_poi_index", 0)


def show_field_intro():
    st.markdown(f"""
    <div class="jn-hero" style="background-image: linear-gradient(90deg, rgba(10,30,36,.68), rgba(10,30,36,.28)), url('{MAIN_IMG_URL}');">
      <div class="jn-hero-title">惠山古镇 <span>现场实验模式</span></div>
      <div class="jn-hero-sub">Streamlit 只负责 A/B/C 体验刺激与 Supabase 行为日志；问卷由研究者平板在问卷星中采集。</div>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.get("field_needs_subject_setup") or st.session_state.get("group") not in VALID_GROUPS or not st.session_state.get("participant_id"):
        st.markdown("""
        <div class="jn-card">
          <div class="jn-section-title">🧾 研究助理入口设置</div>
          <p>此页用于把统一入口链接转换为某一名被试的固定现场链接。正式实验中，每名被试仍然只对应一个 participant_id 和一个 group。</p>
        </div>
        """, unsafe_allow_html=True)
        with st.form("field_subject_setup_form"):
            default_pid = st.session_state.get("participant_id") or "P001"
            pid_input = st.text_input("participant_id（例如 P001）", value=default_pid)
            group_input = st.selectbox("group（六组完全交叉平衡顺序）", VALID_GROUPS, index=0)
            st.caption("G1=ABCAB｜G2=ACBAC｜G3=BACBA｜G4=BCABC｜G5=CABCA｜G6=CBACB")
            submitted = st.form_submit_button("生成该被试固定链接并进入实验首页", use_container_width=True)
        if submitted:
            pid_clean = re.sub(r"[^A-Za-z0-9_\-]", "", pid_input.strip())
            if not pid_clean:
                st.error("participant_id 不能为空；建议格式为 P001、P002……")
                st.stop()
            st.session_state.participant_id = pid_clean
            st.session_state.group = group_input
            st.session_state.field_needs_subject_setup = False
            set_field_query_params()
            st.rerun()
        st.info("也可以继续使用旧格式直达链接：?field=1&pid=P001&group=G1。")
        st.stop()

    pid = st.session_state.participant_id
    group = st.session_state.group
    sequence = group_sequence_code(group)
    ensure_field_participant(pid, group)
    st.markdown(f"""
    <div class="jn-card">
      <div class="jn-section-title">📋 正式现场实验信息</div>
      <p><strong>participant_id：</strong>{pid}</p>
      <p><strong>group：</strong>{group}｜<strong>5 POI 条件序列：</strong>{sequence}</p>
      <p>请先用研究者平板完成问卷星 Q1「知情同意与前测」。确认提交后，再点击下方按钮进入路线。</p>
    </div>
    """, unsafe_allow_html=True)

    pretest_url = field_survey_url("pretest", {"participant_id": pid, "group": group})
    if pretest_url:
        st.link_button("📝 打开 Q1 前测问卷星", pretest_url, use_container_width=True)
    else:
        st.info("如未在 Streamlit Secrets 配置 WJX_PRETEST_URL，请研究者用平板手动打开 Q1，并填写 participant_id 与 group。")

    if st.button("🚶 Q1 已完成，开始现场路线", use_container_width=True):
        st.session_state.field_stage = "field_poi"
        st.session_state.field_poi_index = 0
        st.session_state.route_start_ts = time.time()
        set_field_query_params(step=0)
        if not st.session_state.get("field_route_started_logged"):
            write_legacy_event("field_route_started", {
                "participant_id": pid,
                "group": group,
                "assigned_sequence": sequence
            })
            st.session_state.field_route_started_logged = True
        st.rerun()
    st.caption("现场稳定版：按钮在当前页内进入路线，同时保留 step 参数，Safari 刷新后仍可回到正确路线。")


def field_current_metadata(poi_idx):
    group = st.session_state.group
    condition = GROUP_CONDITION_MAP[group][poi_idx]
    poi = POIS[poi_idx]
    return {
        "participant_id": st.session_state.participant_id,
        "group": group,
        "sequence_position": poi_idx + 1,
        "poi_id": poi["id"],
        "poi_name": poi["name"],
        "condition": condition,
        "condition_code": CONDITION_CODE_MAP[condition],
        "condition_order": group_sequence_code(group)
    }


def show_field_poi_page():
    poi_idx = st.session_state.get("field_poi_index", 0)
    if poi_idx >= len(POIS):
        st.session_state.field_stage = "field_final"
        st.rerun()
        return

    meta = field_current_metadata(poi_idx)
    poi_data = poi_database.get(meta["poi_id"], {"name": meta["poi_name"], "info": "暂无详细介绍。"})
    st.session_state.current_poi_id = meta["poi_id"]
    st.session_state.current_poi_name = meta["poi_name"]
    st.session_state.current_condition = meta["condition"]

    active_key = f"field:{meta['participant_id']}:{meta['group']}:{poi_idx}:{meta['poi_id']}:{meta['condition']}"
    if st.session_state.get("active_field_key") != active_key:
        if meta["sequence_position"] == 1 and not st.session_state.get("field_route_started_logged"):
            write_legacy_event("field_route_started", {
                "participant_id": meta["participant_id"],
                "group": meta["group"],
                "assigned_sequence": meta["condition_order"]
            })
            st.session_state.field_route_started_logged = True
        exposure_id = str(uuid.uuid4())
        st.session_state.current_exposure_id = exposure_id
        st.session_state.chat_messages = []
        st.session_state.followup_questions = []
        st.session_state.followup_generation = 0
        st.session_state.poi_page_load_ts = time.time()
        st.session_state.active_field_key = active_key

        write_poi_exposure(
            pid=meta["participant_id"],
            group=meta["group"],
            exposure_id=exposure_id,
            poi_id=meta["poi_id"],
            condition=meta["condition"],
            sequence_position=meta["sequence_position"],
            page_load_ts=st.session_state.poi_page_load_ts
        )

    st.caption(
        f"正式现场模式｜{meta['participant_id']}｜{meta['group']}｜"
        f"POI {meta['sequence_position']}/5｜条件 {meta['condition_code']}"
    )
    st.markdown(f"""
    <div class="jn-hero" style="background-image: linear-gradient(90deg, rgba(10,30,36,.68), rgba(10,30,36,.28)), url('{get_img_url_or_local("主图.jpg", MAIN_IMG_URL)}');">
      <div class="jn-hero-title">惠山古镇 <span>AI 导览员</span></div>
      <div class="jn-hero-sub">请先观察真实点位 30 秒，再使用当前界面完成体验。</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f"""
    <div class="jn-card">
      <b>现场口径：</b>请被试先看眼前点位 30 秒。研究者不解释文化内容，只处理操作问题。<br>
      <b>当前元数据：</b>{meta['poi_name']}｜{meta['condition_code']} {meta['condition']}｜
      exposure_id: <code>{st.session_state.current_exposure_id}</code>
    </div>
    """, unsafe_allow_html=True)

    if meta["condition"] == "baseline":
        render_baseline(poi_data)
    elif meta["condition"] == "free_text":
        render_free_text_rag(poi_data)
    else:
        render_recchatbox(poi_data)

    if st.button("✅ 完成当前点位体验，进入平板微问卷环节", use_container_width=True):
        dwell = time.time() - st.session_state.poi_page_load_ts
        write_poi_completed(st.session_state.current_exposure_id, round(dwell, 2))
        st.session_state.pending_field_meta = {
            **meta,
            "exposure_id": st.session_state.current_exposure_id,
            "dwell_seconds": round(dwell, 2)
        }
        st.session_state.field_stage = "field_micro_pause"
        st.query_params["step"] = str(meta["sequence_position"] - 1)
        st.query_params["pause"] = "1"
        st.query_params["completed_exposure_id"] = st.session_state.current_exposure_id
        st.query_params["dwell_seconds"] = str(round(dwell, 2))
        st.rerun()


def show_field_micro_pause():
    meta = st.session_state.get("pending_field_meta") or restore_pending_micro_meta_from_url()
    if not meta:
        st.session_state.field_stage = "field_poi"
        st.rerun()
        return

    st.title("📋 请完成该点位平板微问卷")
    st.markdown(f"""
    <div class="jn-card">
      <div class="jn-section-title">交给问卷星 Q2 的元数据</div>
      <p><strong>participant_id：</strong>{meta['participant_id']}</p>
      <p><strong>group：</strong>{meta['group']}</p>
      <p><strong>sequence_position：</strong>{meta['sequence_position']}</p>
      <p><strong>poi_id：</strong>{meta['poi_id']}</p>
      <p><strong>poi_name：</strong>{meta['poi_name']}</p>
      <p><strong>condition：</strong>{meta['condition']}（{meta['condition_code']}）</p>
      <p><strong>exposure_id：</strong><code>{meta['exposure_id']}</code></p>
      <p><strong>dwell_seconds：</strong>{meta['dwell_seconds']}</p>
    </div>
    """, unsafe_allow_html=True)
    st.code(
        "\n".join([
            f"participant_id={meta['participant_id']}",
            f"group={meta['group']}",
            f"sequence_position={meta['sequence_position']}",
            f"poi_id={meta['poi_id']}",
            f"condition={meta['condition']}",
            f"exposure_id={meta['exposure_id']}",
            f"dwell_seconds={meta['dwell_seconds']}",
        ]),
        language="text"
    )

    micro_url = field_survey_url("micro", meta)
    if micro_url:
        st.link_button("📝 打开 Q2 当前点位微问卷", micro_url, use_container_width=True)
    else:
        st.info("如未配置 WJX_MICRO_SURVEY_URL，请研究者在平板 Q2 第一页手动录入以上元数据。")

    st.warning("确认 Q2 已提交后再进入下一站。不要让被试边走边填问卷。")
    next_step = meta["sequence_position"]
    next_label = "➡️ Q2 已提交，进入下一站" if next_step < len(POIS) else "✅ Q2 已提交，进入终测"
    if st.button(next_label, use_container_width=True):
        st.session_state.field_poi_index = next_step
        st.session_state.chat_messages = []
        st.session_state.followup_questions = []
        st.session_state.followup_generation = 0
        if next_step >= len(POIS):
            st.session_state.field_stage = "field_final"
            set_field_query_params(step=len(POIS))
        else:
            st.session_state.field_stage = "field_poi"
            set_field_query_params(step=next_step)
        st.rerun()
    st.caption("该导航不依赖 Streamlit WebSocket；若现场网络断开，刷新当前链接即可恢复。")


def show_field_final():
    pid = st.session_state.participant_id
    group = st.session_state.group
    if not st.session_state.get("field_route_completed_logged"):
        write_legacy_event("field_route_completed", {
            "participant_id": pid,
            "group": group,
            "assigned_sequence": group_sequence_code(group),
            "completed_poi_count": len(POIS),
            "route_end_ts": datetime.now().isoformat()
        })
        st.session_state.field_route_completed_logged = True
    st.title("🎯 路线体验完成")
    st.success("Streamlit 体验与 Supabase 行为日志采集已完成。")
    st.markdown(f"""
    <div class="jn-card">
      <p><strong>participant_id：</strong>{pid}</p>
      <p><strong>group：</strong>{group}</p>
      <p><strong>条件序列：</strong>{group_sequence_code(group)}</p>
      <p>请在安静位置使用研究者平板完成问卷星 Q3「终测与偏好访谈」。</p>
    </div>
    """, unsafe_allow_html=True)

    final_url = field_survey_url("final", {"participant_id": pid, "group": group})
    if final_url:
        st.link_button("📝 打开 Q3 终测问卷星", final_url, use_container_width=True)
    else:
        st.info("如未配置 WJX_FINAL_SURVEY_URL，请研究者用平板手动打开 Q3，并填写 participant_id 与 group。")

    if st.button("🔄 重置为该被试现场模式首页", use_container_width=True):
        st.session_state.field_stage = "field_intro"
        st.session_state.field_poi_index = 0
        st.session_state.active_field_key = None
        st.session_state.current_exposure_id = None
        st.session_state.field_route_completed_logged = False
        st.session_state.field_route_started_logged = False
        st.session_state.chat_messages = []
        st.session_state.followup_questions = []
        st.session_state.followup_generation = 0
        set_field_query_params()
        st.rerun()


def show_field_mode():
    field_mode_setup()
    stage = st.session_state.get("field_stage", "field_intro")
    if stage == "field_intro":
        show_field_intro()
    elif stage == "field_poi":
        show_field_poi_page()
    elif stage == "field_micro_pause":
        show_field_micro_pause()
    elif stage == "field_final":
        show_field_final()
    else:
        st.session_state.field_stage = "field_intro"
        st.rerun()


# ==================== 主入口 ====================
def main():
    if "participant_id" not in st.session_state:
        if is_field_mode() and not st.query_params.get("pid"):
            st.session_state.participant_id = ""
        else:
            st.session_state.participant_id = st.query_params.get("pid", f"P_{uuid.uuid4().hex[:8]}")
    if "group" not in st.session_state and st.query_params.get("group") in VALID_GROUPS:
        st.session_state.group = st.query_params.get("group")
    if st.query_params.get("condition") in VALID_CONDITIONS:
        show_direct_condition_page()
        return
    if is_field_mode() or not is_legacy_mode():
        show_field_mode()
        return
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
    else:
        st.session_state.stage = "intro"
        st.rerun()

if __name__ == "__main__":
    main()
