import streamlit as st
import os
import docx
import requests
import time
from typing import TypedDict
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END

# ==========================================
# 설정 및 비밀키 로드
# ==========================================
st.set_page_config(page_title="AI 채용공고 이력서 매칭 서비스", page_icon="🐈‍⬛", layout="wide")

if "GOOGLE_API_KEY" in st.secrets:
    os.environ["GOOGLE_API_KEY"] = st.secrets["GOOGLE_API_KEY"]
else:
    st.error("🚨 API 키가 없습니다. 개발자에게 문의 부탁드립니다")
    st.stop()

# 모델 : gemini-2.5-flash
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

# ==========================================
# 디스코드 메세지 (시간 / 별점)
# ==========================================
def send_discord_alert(user_name, duties, result_text, latency_ms):
    webhook_url = st.secrets.get("DISCORD_WEBHOOK_URL", None)
    if not webhook_url: return

    short_duties = duties[:200] + "..." if len(duties) > 200 else duties
    short_result = result_text[:800] + "\n..." if len(result_text) > 800 else result_text

    payload = {
        "username": "AI 매칭 분석 로그",
        "embeds": [{
            "title": "🚀 새로운 이용자 등장!",
            "color": 3447003, # 파란색
            "fields": [
                {"name": "사용자", "value": user_name if user_name else "익명", "inline": True},
                {"name": "처리 시간 (ms)", "value": f"{latency_ms:,} ms", "inline": True},
                {"name": "공고 요약", "value": short_duties, "inline": False},
                {"name": "결과 요약", "value": short_result, "inline": False}
            ]
        }]
    }
    try: requests.post(webhook_url, json=payload)
    except: pass

# 별점
def send_discord_feedback(user_name, score, feedback_text):
    webhook_url = st.secrets.get("DISCORD_WEBHOOK_URL", None)
    if not webhook_url: return
    comments = {1: "😭 최악이에요", 2: "😞 별로예요", 3: "😐 보통이에요", 4: "🙂 좋아요", 5: "😍 최고예요!"}

    payload = {
        "username": "⭐ 만족도 평가 알림",
        "embeds": [{
            "title": f"사용자 만족도 평가: {score}점 {'⭐' * score}",
            "description": f"**평가:** {comments.get(score, '')}",
            "fields": [
                {"name": "사용자", "value": user_name if user_name else "익명", "inline": True},
                {"name": "추가 의견", "value": feedback_text if feedback_text else "없음", "inline": False}
            ]
        }]
    }
    try: requests.post(webhook_url, json=payload)
    except: pass

# ==========================================
# 이력서 읽기 & AI 분석
# ==========================================
def read_resume_file(uploaded_file):
  서 : DOCX 파일")
    uploaded_file = st.file_uploader("Upload .docx", type=["docx"])

    st.markdown("---")
    st.subheader("2. 채용공고")
    duties_input = st.text_area("주요 업무", height=100)
    req_input = st.text_area("자격 요건", height=100)
장 (화면 리셋 방지)
                st.session_state.analysis_result = result['final_result']
                st.session_state.analysis_latency = latency_ms 
                
                # 분석 완료 - 디스코드 알림
                send_discord_alert(user_name, duties_input, result['final_result'], latency_ms)

    # [결과 출력] 저장된 결과가 있으면 보여줌
    if st.session_state.analysis_result:
        # 분석 시간을 UI에 표시
        st.caption(f"분석 시간: **{st.session_state.analysis_latency:,} ms**") 
        st.markdown(st.session_state.analysis_result)
        st.markdown("---")
        
        # ==========================================
        # 만족도 평가
        # ==========================================
        st.subheader("⭐ 분석 결과가 만족스러우신가요? 별점을 매겨주세요. 개발자에게 힘이 됩니다")
        
        # 별점
        sentiment_mapping = ["1점", "2점", "3점", "4점", "5점"]
        selected = st.feedback("stars")
        
        if selected is not None:
            # 점수화
            score = selected + 1
            st.toast(f"소중한 의견 감사합니다! ({score}점)", icon="🐈‍⬛")
            
            # 디스코드로 별점 전송
            # (중복 전송 방지 - 세션 키 확인)
            if 'feedback_sent' not in st.session_state or st.session_state.feedback_sent != score:
                send_discord_feedback(user_name, score, "별점을 남겼어요.")
                st.session_state.feedback_sent = score
