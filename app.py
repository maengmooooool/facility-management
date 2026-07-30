import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import date, datetime, timedelta
import time

# --- 1. Supabase 클라우드 데이터베이스 연결 ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

# --- 2. 화면 및 폰트 설정 ---
st.set_page_config(page_title="(주)호성 통합시스템", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Nanum+Gothic:wght@400;700;800&display=swap');
html, body, [class*="css"]  {
    font-family: 'Nanum Gothic', sans-serif !important;
    font-size: 18px !important; 
}
</style>
""", unsafe_allow_html=True)


# ==========================================
# 🔒 3. 보안 로그인 시스템 추가 🌟
# ==========================================
# 접속 상태를 기억하는 메모리 공간 생성
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['username'] = None

# 로그인하지 않은 상태면 로그인 화면만 보여줌
if not st.session_state['logged_in']:
    st.title("🔐 (주)호성 통합시스템 로그인")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        # 기안을 올리는 '직원'과 결재를 하는 '관리자'들을 모두 포함
        login_name = st.selectbox("👤 접속자 이름", ["직원", "김공장장", "이이사", "박대표", "최팀장"])
        login_pw = st.text_input("🔑 비밀번호", type="password")
        
        if st.button("로그인"):
            # 💡 현재는 테스트를 위해 모든 비밀번호를 '1234'로 통일해 둡니다. (추후 개별 설정 가능)
            if login_pw == "1234":
                st.session_state['logged_in'] = True
                st.session_state['username'] = login_name
                st.rerun() # 화면 새로고침
            else:
                st.error("⚠️ 비밀번호가 틀렸습니다.")
                
    st.stop() # 👈 로그인 안 하면 아래 코드(메인 화면)는 절대 안 보입니다!


# ==========================================
# 🌟 로그인 성공 시 나타나는 왼쪽 메뉴바 🌟
# ==========================================
with st.sidebar:
    st.success(f"👤 **{st.session_state['username']}**님 접속 중")
    if st.button("로그아웃"):
        st.session_state['logged_in'] = False
        st.session_state['username'] = None
        st.rerun()
        
    st.markdown("---")
    st.title("🏢 (주)호성 통합메뉴")
    menu = st.radio("메뉴를 선택하세요", 
                    ["⚙️ 기계설비 관리", "📝 전자결재 (기안)", "📦 물류 및 재고 (ERP)"])


# ==========================================
# [메뉴 2] 전자결재 시스템 화면
# ==========================================
if menu == "📝 전자결재 (기안)":
    st.title("📝 사내 전자결재 시스템")
    
    tab_draft, tab_approve, tab_archive = st.tabs(["📝 기안 작성", "✅ 결재함 (관리자용)", "🗄️ 결재 완료 문서함"])
    
    admin_list = ["김공장장", "이이사", "박대표", "최팀장"]
    
    # --- [탭 1] 직원이 기안하는 화면 ---
    with tab_draft:
        st.write("문서 양식을 선택한 후, 빈칸을 채워 결재를 상신해 주세요.")
        
        doc_type = st.radio(
            "📋 문서 양식 선택", 
            ["📝 공문형 기안문", "💰 지출 품의서", "📊 표준 보고서"], 
            horizontal=True
        )
        
        doc_title = st.text_input("문서 제목")
        
        if doc_type == "📝 공문형 기안문":
            template = "(주) 호 성\n\n수신자: [수신 부서 또는 직책]\n(경유): \n제  목: [여기에 제목을 한 번 더 입력하세요]\n--------------------------------------------------\n1. 귀 부서의 노고에 감사드립니다.\n2. [기안의 배경 및 목적을 간략히 기재하세요.]\n3. 위와 관련하여 아래와 같이 업무를 추진하고자 하오니 검토 후 재가하여 주시기 바랍니다.\n\n                        - 아    래 -\n        \n가. 일시/기간: \n나. 대상/장소: \n다. 소요 예산: \n라. 상세 내용: \n        \n붙임  1. [첨부문서 1 이름] 1부.\n      2. [첨부문서 2 이름] 1부.  끝.\n\n                     (주) 호 성 대 표 이 사"
        elif doc_type == "💰 지출 품의서":
            template = "■ 청구 내역 (품목/공사명):\n\n■ 예상 비용 (VAT 포함):\n             원\n■ 결제 수단 (법인카드/계좌이체 등):\n\n■ 거래처 정보 (상호/연락처):\n\n■ 첨부(영수증/견적서) 유무:\n"
        elif doc_type == "📊 표준 보고서":
            template = "[ 📄 주 요 업 무  보 고 서 ]\n\n■ 보고 일자 : 202 년   월   일\n■ 보  고  자 : 소속          성명          (서명)\n--------------------------------------------------\n1. 현황 및 배경\n   - [현재 상황이나 보고를 하게 된 배경을 요약]\n\n2. 주요 추진 내용 (또는 발생한 문제점)\n   - [핵심적인 업무 진행 상황이나 상세 내역 기술]\n   - \n\n3. 향후 계획 (또는 개선 방안)\n   - [앞으로의 일정이나 문제 해결을 위한 구체적 방안 기술]\n   - \n\n4. 건의 및 요청사항\n   - [결재권자의 지원이 필요한 부분이나 참고사항 기술]\n"
            
        doc_content = st.text_area("상세 내용 작성", value=template, height=450)
        
        selected_approvers = st.multiselect(
            "결재권자 지정 (최대 3명 선택 가능)", 
            options=admin_list, 
            max_selections=3
        )
        
        if st.button("결재 상신하기"):
            if doc_title == "" or len(selected_approvers) == 0:
                st.warning("⚠️ 문서 제목을 입력하고, 결재권자를 최소 1명 이상 지정해 주세요.")
            else:
                approvers_str = ",".join(selected_approvers)
                type_prefix = doc_type.split(" ")[1] 
                final_title = f"[{type_prefix}] {doc_title}"
                
                data = {
                    "title": final_title,
                    "content": doc_content,
                    "status": "대기중",
                    "approvers": approvers_str,
                    "approved_by": ""
                }
                supabase.table("approvals").insert(data).execute()
                st.success("✅ 결재가 성공적으로 상신되었습니다!")
                
    # --- [탭 2] 사장님이 결재하는 화면 ---
    with tab_approve:
        # 🌟 가짜 로그인 창을 없애고, 진짜 로그인한 사람의 이름을 가져옵니다!
        current_admin = st.session_state['username']
        
        # '직원'이 아니라 '관리자' 명단에 있는 사람일 때만 결재함을 보여줌
        if current_admin in admin_list:
            st.write(f"반갑습니다, **{current_admin}**님! 결재 대기 문서를 확인합니다.")
            
            res = supabase.table("approvals").select("*").eq("status", "대기중").execute()
            pending_docs = res.data
            
            my_docs = []
            for doc in pending_docs:
                if doc.get('approvers') and current_admin in doc['approvers']:
                    if not doc.get('approved_by') or current_admin not in doc['approved_by']:
                        my_docs.append(doc)
            
            if not my_docs:
                st.info("🎉 현재 처리하실 결재 문서가 없습니다.")
            else:
                for doc in my_docs:
                    with st.expander(f"📄 {doc['title']}"):
                        st.write(f"**상세 내용:**")
                        st.info(doc['content'])
                        st.write(f"- **지정된 전체 결재자:** {doc['approvers']}")
                        current_approved = doc.get('approved_by') if doc.get('approved_by') else "없음"
                        st.write(f"- **현재까지 승인 완료한 사람:** {current_approved}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✅ 내 순서 승인하기", key=f"app_{doc['id']}"):
                                new_approved_by = doc.get('approved_by', '') + f"{current_admin},"
                                approvers_list = [name.strip() for name in doc['approvers'].split(',') if name.strip()]
                                approved_list = [name.strip() for name in new_approved_by.split(',') if name.strip()]
                                
                                if set(approvers_list).issubset(set(approved_list)):
                                    new_status = "최종 통과 (승인됨)"
                                else:
                                    new_status = "대기중"
                                    
                                supabase.table("approvals").update({
                                    "approved_by": new_approved_by,
                                    "status": new_status
                                }).eq("id", doc['id']).execute()
                                st.rerun()
                        with col2:
                            if st.button("❌ 반려하기", key=f"rej_{doc['id']}"):
                                supabase.table("approvals").update({"status": "반려됨"}).eq("id", doc['id']).execute()
                                st.rerun()
        else:
            st.warning("🔒 결재 권한이 없습니다. (관리자 계정으로 로그인해 주세요)")

    # --- [탭 3] 결재 완료 문서 보관 및 출력 화면 ---
    with tab_archive:
        st.write("결재가 끝난(승인/반려) 문서를 열람하고 다운로드(출력)합니다.")
        
        res = supabase.table("approvals").select("*").neq("status", "대기중").order("id", desc=True).execute()
        completed_docs = res.data
        
        if not completed_docs:
            st.info("📭 아직 결재가 완료된 문서가 없습니다.")
        else:
            for doc in completed_docs:
                icon = "🟢" if "승인됨" in doc['status'] else "🔴"
                with st.expander(f"{icon} {doc['title']} ({doc['status']}) - {doc['created_at'][:10]}"):
                    st.markdown(f"### 📋 {doc['title']}")
                    st.write(f"- **결재 상태:** {doc['status']}")
                    st.write(f"- **기안 일자:** {doc['created_at'][:10]}")
                    st.write(f"- **지정된 결재자:** {doc['approvers']}")
                    st.write(f"- **최종 승인자:** {doc.get('approved_by', '없음')}")
                    st.markdown("---")
                    st.write(f"**[상세 요청 내용]**")
                    st.info(doc['content'])
                    
                    doc_text = f"======================================\n         결 재 완 료 문 서\n======================================\n■ 기안 제목: {doc['title']}\n■ 기안 일자: {doc['created_at'][:10]}\n■ 결재 상태: {doc['status']}\n■ 지정 결재자: {doc['approvers']}\n■ 승인 완료자: {doc.get('approved_by', '없음')}\n--------------------------------------\n{doc['content']}\n======================================"
                    
                    st.download_button(
                        label="💾 문서 다운로드 (인쇄/보관용)",
                        data=doc_text,
                        file_name=f"결재문서_{doc['title']}.txt",
                        mime="text/plain",
                        key=f"dl_{doc['id']}"
                    )
                    st.caption("💡 팁: 다운로드한 텍스트 파일을 열어 인쇄(Ctrl+P)를 통해 PDF로 변환하거나, 기기에 보관하실 수 있습니다.")

    st.stop()
# ==========================================
# [메뉴 3] 재고/물류 관리 (ERP) 화면
# ==========================================
elif menu == "📦 물류 및 재고 (ERP)":
    st.title("📦 실시간 재고/물류 관리")
    
    # 탭을 나누어 입력 화면과 대시보드(통계) 화면을 분리합니다.
    tab_input, tab_dashboard = st.tabs(["🚛 물류 입출고 등록", "📊 실시간 재고 대시보드"])
    
    # --- [탭 1] 입출고 등록 화면 ---
    with tab_input:
        st.write("오늘의 입출고 내역(톤 단위)을 정확히 기록해 주세요.")
        
        with st.form("inventory_form"):
            col1, col2 = st.columns(2)
            with col1:
                # 취급하시는 주요 품목을 리스트에 넣습니다.
                item_type = st.selectbox("품목 선택", ["고철", "폐목재", "비철", "기타"])
                in_out = st.radio("물류 구분", ["입고", "출고"], horizontal=True)
            with col2:
                weight = st.number_input("수량 (단위: 톤)", min_value=0.0, step=0.1, format="%.1f")
                
            submitted = st.form_submit_button("저장하기")
            
            if submitted:
                if weight <= 0:
                    st.warning("⚠️ 0보다 큰 수량을 입력해 주세요.")
                else:
                    data = {
                        "item_type": item_type,
                        "in_out": in_out,
                        "weight": weight
                    }
                    supabase.table("inventory").insert(data).execute()
                    st.success(f"✅ [{item_type}] {weight}톤 {in_out} 기록이 저장되었습니다!")
                    
    # --- [탭 2] 재고 대시보드 화면 ---
    with tab_dashboard:
        st.write("현재까지 누적된 품목별 재고 현황입니다.")
        
        # 데이터베이스에서 모든 입출고 내역 불러오기
        res = supabase.table("inventory").select("*").execute()
        inv_data = res.data
        
        if not inv_data:
            st.info("아직 등록된 물류 내역이 없습니다.")
        else:
            # 불러온 데이터를 엑셀(데이터프레임) 형태로 변환
            df = pd.DataFrame(inv_data)
            
            # 입고는 더하고(+) 출고는 빼서(-) 현재 재고 계산하기
            df['calc_weight'] = df.apply(lambda x: x['weight'] if x['in_out'] == '입고' else -x['weight'], axis=1)
            
            # 품목별로 그룹을 묶어서 총합 계산
            inventory_summary = df.groupby('item_type')['calc_weight'].sum().reset_index()
            inventory_summary.columns = ['품목명', '현재 재고(톤)']
            
            # 🌟 화면에 시각적으로 예쁘게 표시하기
            cols = st.columns(len(inventory_summary))
            for i, row in inventory_summary.iterrows():
                with cols[i]:
                    st.metric(label=f"📦 {row['품목명']}", value=f"{row['현재 재고(톤)']:.1f} t")
            
            st.markdown("---")
            st.write("📋 **상세 입출고 기록 (최근 순)**")
            # 보기 좋게 정렬 및 표시
            df_display = df[['created_at', 'item_type', 'in_out', 'weight']].sort_values(by='created_at', ascending=False)
            df_display.columns = ['일시', '품목', '구분', '수량(톤)']
            # 시간 부분 깔끔하게 자르기 (예: 2026-07-30)
            df_display['일시'] = df_display['일시'].apply(lambda x: x[:10]) 
            
            st.dataframe(df_display, use_container_width=True, hide_index=True)

    st.stop()
