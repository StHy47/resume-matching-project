import streamlit as st
import os
import docx
import requests  # 디스코드 전송용
from typing import TypedDict
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END

# ==========================================
# 1. 설정 및 비밀키 로드
# ==========================================
st.set_page_config(page_title="AI 커리어 코치", page_icon="🎯", layout="wide")

if "GOOGLE_API_KEY" in st.secrets:
    os.environ["GOOGLE_API_KEY"] = st.secrets["GOOGLE_API_KEY"]
else:
    st.error("🚨 API 키가 없습니다.")
    st.stop()

# 모델 설정
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

# ==========================================
# 2. [핵심] 디스코드 알림 함수 (상세 내용 포함)
# ==========================================
def send_discord_alert(user_name, duties, result_text):
    webhook_url = st.secrets.get("DISCORD_WEBHOOK_URL", None)
    
    if not webhook_url:
        return # URL 없으면 그냥 패스 (에러 안 나게)

    # 디스코드는 글자수 제한이 있어서 너무 길면 잘라서 보내야 함
    # (제목+내용 합쳐서 6000자 제한, 필드값 1024자 제한 등)
    short_duties = duties[:200] + "..." if len(duties) > 200 else duties
    short_result = result_text[:800] + "\n...(내용이 길어서 생략됨)" if len(result_text) > 800 else result_text

    # 예쁜 카드 형태(Embed)로 데이터 조립
    payload = {
        "username": "🤖 AI 취업비서 로그",
        "embeds": [
            {
                "title": "🚀 새로운 분석 요청이 들어왔어요!",
                "color": 3447003, # 파란색
                "fields": [
                    {
                        "name": "👤 사용자",
                        "value": user_name if user_name else "익명",
                        "inline": True
                    },
                    {
                        "name": "🏢 분석 공고 (요약)",
                        "value": short_duties,
                        "inline": False
                    },
                    {
                        "name": "📊 AI 분석 결과",
                        "value": short_result,
                        "inline": False
                    }
                ],
                "footer": {
                    "text": "Streamlit Cloud에서 전송됨"
                }
            }
        ]
    }
    
    try:
        requests.post(webhook_url, json=payload)
    except Exception as e:
        print(f"디스코드 전송 실패: {e}")

# ==========================================
# 3. 기존 로직 (이력서 읽기 & AI 분석)
# ==========================================
def read_resume_file(uploaded_file):
    try:
        doc = docx.Document(uploaded_file)
        full_text = []
        for para in doc.paragraphs:
            if para.text.strip():
                full_text.append(para.text)
        for table in doc.tables:
            for row in table.rows:
                row_text = [cell.text for cell in row.cells if cell.text.strip()]
                if row_text:
                    full_text.append(" | ".join(row_text))
        return "\n".join(full_text)
    except Exception as e:
        return f"이력서 읽기 실패: {e}"

class AgentState(TypedDict):
    resume_text: str; duties: str; requirements: str; preferred: str; final_result: str

def match_node(state: AgentState):
    prompt = ChatPromptTemplate.from_template("""
    당신은 IT 채용 담당자입니다. 
    [이력서] {resume}
    [공고] 업무: {duties}, 자격: {requirements}, 우대: {preferred}
    
    분석 결과 리포트:
    1. 📊 적합도 점수 (0~100)
    2. ✅ 합격 포인트
    3. 🚨 보완 필요 사항 (Gap)
    4. 💡 추천 미니 프로젝트
    """)
    chain = prompt | llm
    res = chain.invoke({
        "resume": state['resume_text'], "duties": state['duties'], 
        "requirements": state['requirements'], "preferred": state['preferred']
    })
    return {"final_result": res.content}

workflow = StateGraph(AgentState)
workflow.add_node("matcher", match_node)
workflow.set_entry_point("matcher")
workflow.add_edge("matcher", END)
app = workflow.compile()

# ==========================================
# 4. 화면(UI) 구성
# ==========================================
st.title("🎯 AI 취업 비서: 채용공고 정밀 분석기")

# 사용자 이름 입력받기 (로그용)
with st.sidebar:
    st.header("📝 사용자 정보")
    user_name = st.text_input("이름/닉네임을 입력해주세요", placeholder="예: 김코딩")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1️⃣ 내 이력서")
    uploaded_file = st.file_uploader("Upload .docx", type=["docx"])

    st.markdown("---")
    st.subheader("2️⃣ 채용공고")
    duties_input = st.text_area("📌 주요 업무", height=100)
    req_input = st.text_area("⚠️ 자격 요건", height=100)
    pref_input = st.text_area("🌟 우대 사항", height=100)

    run_btn = st.button("🚀 분석 시작", type="primary", use_container_width=True)

with col2:
    st.subheader("3️⃣ 분석 결과")
    if run_btn:
        if not uploaded_file or (not duties_input and not req_input):
            st.warning("이력서와 공고 내용을 입력해주세요.")
        else:
            with st.spinner("AI가 분석 중입니다..."):
                # 1. 파일 읽기
                resume_text = read_resume_file(uploaded_file)
                
                # 2. AI 분석
                result = app.invoke({
                    "resume_text": resume_text, "duties": duties_input,
                    "requirements": req_input, "preferred": pref_input
                })
                
                # 3. 화면 출력
                st.markdown(result['final_result'])
                st.success("분석 완료!")
                
                # 4. [여기!] 디스코드로 내용 쏘기
                send_discord_alert(user_name, duties_input, result['final_result'])
