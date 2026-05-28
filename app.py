import streamlit as st
import json
import os
import time
import hashlib
import random
import re
from datetime import datetime, timezone, timedelta
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from supabase import create_client
from streamlit_TTS import st_tts  # 新增：导入语音模块

# ==================== 页面配置 ====================
st.set_page_config(page_title="惠山古镇 AI 导览 | 非遗数字体验", layout="centered", initial_sidebar_state="expanded")

# ==================== 更新后的 CSS ====================
# （这里放你新整合的新国潮CSS代码）
st.markdown("""
<style>
    /* 新国潮电商风CSS */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Noto+Serif+SC:wght@400;700&display=swap');
    .stApp {
        background: #F8F9F8;
        font-family: 'Noto Serif SC', serif;
    }
    /* 主容器 - 调整卡片样式为0.5px细边框 */
    .main > div {
        background-color: #ffffff;
        border-radius: 8px;
        padding: 1rem 1.5rem 1.5rem 1.5rem;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
        border: 0.5px solid #e2e2e2;
    }
    /* POI 信息卡片 - 玉色背景，珊瑚红左框 */
    .poi-card {
        background: #EAECE9;
        border-left: 4px solid #E63946;
        padding: 1rem 1.2rem;
        border-radius: 4px;
        margin: 1rem 0 1.5rem 0;
        font-size: 0.95rem;
        line-height: 1.5;
        color: #4A4E51;
        box-shadow: none;
    }
    /* 来源标识 - 融入新配色 */
    .source-chip {
        display: inline-block;
        background-color: #f0f0f0;
        color: #4A4E51;
        padding: 2px 12px;
        border-radius: 4px;
        font-size: 0.7rem;
        font-weight: 400;
        margin-top: 8px;
        font-family: 'Inter', sans-serif;
    }
    /* 按钮电商风 - 珊瑚红 */
    div.stButton > button {
        background-color: #ffffff;
        color: #E63946;
        border: 1px solid #e2e2e2;
        border-radius: 4px;
        padding: 0.5rem 1.2rem;
        font-weight: 400;
        transition: 0.2s;
        font-family: 'Inter', sans-serif;
    }
    div.stButton > button:hover {
        background-color: #E63946;
        color: white;
        border-color: #E63946;
    }
    /* 聊天输入框 */
    .stChatInput input {
        border-radius: 4px;
        border: 1px solid #e2e2e2;
        background-color: #ffffff;
    }
    /* 侧边栏 */
    [data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 0.5px solid #e2e2e2;
        font-family: 'Inter', sans-serif;
    }
</style>
""", unsafe_allow_html=True)

# ==================== 加载 POI 数据 ====================
# 新增：展示路线进度函数
def display_route_progress(current_index):
    total = len(POI_ORDER)
    progress_percentage = (current_index + 1) / total
    # 使用 st.progress 展示进度条
    st.sidebar.progress(progress_percentage)
    # 用文字展现点位列表，高亮当前点位
    for idx, pid in enumerate(POI_ORDER):
        icon = "✅" if idx < current_index else "🟩" if idx == current_index else "▪️"
        st.sidebar.markdown(f"{icon} {POI_NAMES.get(pid, pid)}")

# ... （其余代码与之前完全一致，直到"# ==================== 日志函数"部分） ...

# ==================== 日志函数（修复数据写入） ====================
def log_experimental_event(action_type, query_text="", response_time=0.0, retrieved_chunks="", displayed_source_cue=""):
    time_on_page = time.time() - st.session_state.page_load_time
    utc_time = datetime.now(timezone.utc)
    beijing_time = utc_time + timedelta(hours=8)
    event_data = {
        "participant_id": str(st.session_state.participant_id),
        "experimental_condition": current_condition,
        "poi_id": str(current_poi_key),
        "action_type": str(action_type),
        "time_on_page_seconds": round(time_on_page, 2),
        "user_query_text": str(query_text),
        "user_query_word_count": len(query_text),
        "rag_response_time_ms": round(response_time * 1000, 1),
        "retrieved_chunks_saved": str(retrieved_chunks),
        "displayed_source_cue": str(displayed_source_cue),
        "timestamp": beijing_time.isoformat()
    }
    # ... （本地CSV备份代码保持不变） ...
    try:
        # ✅【修复点】加 returning='minimal' 避免隐式 SELECT 触发 RLS 报错
        st.session_state.supabase.table("interaction_logs").insert(event_data, returning='minimal').execute()
    except Exception as e:
        st.toast(f"⚠️ 数据同步失败，本地已备份: {str(e)[:100]}", icon="⚠️")

# ... （中间函数部分均保持不变） ...

# ==================== 主界面渲染 ====================
# 在页面最上方调用语音朗读
if actual_render != "baseline" and not st.session_state.get("has_read_intro", False):
    st_tts(current_poi["info"], lang="zh")
    st.session_state.has_read_intro = True

# 调用路线显示函数
display_route_progress(st.session_state.current_poi_index)

# ... （其余界面渲染代码保持不变） ...
