import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import date, datetime, timedelta
import time

# --- 1. Supabase 클라우드 데이터베이스 연결 ---
@st.cache_resource
def init_connection():
    # Streamlit Cloud의 Secrets(보안 키)에서 URL과 KEY를 가져옵니다.
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

# --- 2. 화면 구성 ---
st.set_page_config(page_title="(주)호성 통합시스템", layout="wide")

# --- 폰트 및 글씨 크기 변경 ---
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
# 🌟 새롭게 추가되는 왼쪽 메뉴바 (사이드바) 🌟
# ==========================================
with st.sidebar:
    st.title("🏢 (주)호성 통합메뉴")
    menu = st.radio("메뉴를 선택하세요", 
                    ["⚙️ 기계설비 관리", "📝 전자결재 (기안)", "📦 물류 및 재고 (ERP)"])


# ==========================================
# [메뉴 2] 전자결재 시스템 화면
# ==========================================
if menu == "📝 전자결재 (기안)":
    st.title("📝 사내 전자결재 시스템")
    
    # 🌟 탭을 3개로 확장: 기안, 결재함, 그리고 완료함(보관/출력)
    tab_draft, tab_approve, tab_archive = st.tabs(["📝 기안 작성", "✅ 결재함 (관리자용)", "🗄️ 결재 완료 문서함"])
    
    admin_list = ["김공장장", "이이사", "박대표", "최팀장"]
    
    # --- [탭 1] 직원이 기안하는 화면 ---
    with tab_draft:
        st.write("부품 구매나 수리 비용 결재를 상신하는 공간입니다.")
        
        doc_title = st.text_input("기안 제목 (예: 파쇄기 모터 교체 비용 청구)")
        doc_content = st.text_area("상세 요청 내용")
        
        selected_approvers = st.multiselect(
            "결재권자 지정 (최대 3명 선택 가능)", 
            options=admin_list, 
            max_selections=3
        )
        
        if st.button("결재 상신하기"):
            if doc_title == "" or len(selected_approvers) == 0:
                st.warning("⚠️ 기안 제목을 입력하고, 결재권자를 최소 1명 이상 지정해 주세요.")
            else:
                approvers_str = ",".join(selected_approvers)
                data = {
                    "title": doc_title,
                    "content": doc_content,
                    "status": "대기중",
                    "approvers": approvers_str,
                    "approved_by": ""
                }
                supabase.table("approvals").insert(data).execute()
                st.success("✅ 결재가 성공적으로 상신되었습니다!")
                
    # --- [탭 2] 사장님이 결재하는 화면 ---
    with tab_approve:
        current_admin = st.selectbox("👤 현재 접속자 (테스트용 가상 로그인)", ["접속자 선택"] + admin_list)
        
        if current_admin != "접속자 선택":
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
                        st.write(f"**상세 내용:** {doc['content']}")
                        st.write(f"**지정된 전체 결재자:** {doc['approvers']}")
                        current_approved = doc.get('approved_by') if doc.get('approved_by') else "없음"
                        st.write(f"**현재까지 승인 완료한 사람:** {current_approved}")
                        
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
            st.info("결재 문서를 보려면 위에서 접속자 이름을 선택해 주세요.")

    # --- [탭 3] 결재 완료 문서 보관 및 출력 화면 🌟 ---
    with tab_archive:
        st.write("결재가 끝난(승인/반려) 문서를 열람하고 다운로드(출력)합니다.")
        
        # '대기중'이 아닌 문서들(결재가 끝난 문서들)을 최신순(id 역순)으로 불러오기
        res = supabase.table("approvals").select("*").neq("status", "대기중").order("id", desc=True).execute()
        completed_docs = res.data
        
        if not completed_docs:
            st.info("📭 아직 결재가 완료된 문서가 없습니다.")
        else:
            for doc in completed_docs:
                # 상태에 따라 아이콘을 다르게 표시
                icon = "🟢" if "승인됨" in doc['status'] else "🔴"
                with st.expander(f"{icon} {doc['title']} ({doc['status']}) - {doc['created_at'][:10]}"):
                    
                    # 1. 화면 열람용 표시
                    st.markdown(f"### 📋 {doc['title']}")
                    st.write(f"- **결재 상태:** {doc['status']}")
                    st.write(f"- **기안 일자:** {doc['created_at'][:10]}")
                    st.write(f"- **지정된 결재자:** {doc['approvers']}")
                    st.write(f"- **최종 승인자:** {doc.get('approved_by', '없음')}")
                    st.markdown("---")
                    st.write(f"**[상세 요청 내용]**")
                    st.info(doc['content'])
                    
                    # 2. 문서 다운로드/출력용 서식 만들기
                    doc_text = f"""
======================================
         결 재 완 료 문 서
======================================
■ 기안 제목: {doc['title']}
■ 기안 일자: {doc['created_at'][:10]}
■ 결재 상태: {doc['status']}
■ 지정 결재자: {doc['approvers']}
■ 승인 완료자: {doc.get('approved_by', '없음')}
--------------------------------------
■ 상세 요청 내용:
{doc['content']}
======================================
"""
                    # 3. 텍스트 파일로 저장하는 버튼
                    st.download_button(
                        label="💾 문서 다운로드 (인쇄/보관용)",
                        data=doc_text,
                        file_name=f"결재문서_{doc['title']}.txt",
                        mime="text/plain",
                        key=f"dl_{doc['id']}"
                    )
                    st.caption("💡 팁: 다운로드한 파일을 열어서 **인쇄(Ctrl+P)**를 누르시면 **PDF로 저장**하여 보관하시거나 종이로 깔끔하게 출력하실 수 있으며, 모바일 기기의 **Samsung Notes** 등에도 쉽게 불러와서 기록하실 수 있습니다.")

    st.stop() # 👈 다른 메뉴를 선택했을 때는 여기서 화면 그리기를 멈춥니다!

# ==========================================
# [메뉴 3] 재고/물류 관리 (ERP) 화면
# ==========================================
elif menu == "📦 물류 및 재고 (ERP)":
    st.title("📦 실시간 재고/물류 관리")
    st.write("주요 취급 품목의 일일 입고량과 출고량을 기록합니다.")
    
    col1, col2 = st.columns(2)
    with col1:
        item_type = st.selectbox("품목 선택", ["고철", "폐목재", "기타"])
        in_out = st.radio("물류 구분", ["입고", "출고"])
    with col2:
        weight = st.number_input("수량 (단위: 톤)", min_value=0.0, step=0.1)
        st.write("") 
        st.write("")
        st.button("물류 내역 저장")
        
    st.stop() # 👈 중요


# ==========================================
# [메뉴 1] 기존 기계설비 관리 화면 
# (위에서 st.stop()이 걸리지 않았다면 자동으로 이 화면이 나옵니다)
# ==========================================

st.title("☁️ (주)호성 - 기계설비 관리")

tab1, tab2, tab3 = st.tabs(["📋 설비 등록 및 관리", "🔍 점검 내역 관리", "🔧 부품 교체 관리"])

# 유틸리티 함수: 데이터 불러오기
def get_equipment_list():
    res = supabase.table("equipment").select("name").order("name").execute()
    return [row['name'] for row in res.data]

def get_location_list():
    res = supabase.table("equipment").select("location").execute()
    locs = list(set([row['location'] for row in res.data if row['location']]))
    locs.sort()
    return locs

def get_part_name_list():
    res = supabase.table("parts").select("part_name").execute()
    parts = list(set([row['part_name'] for row in res.data if row['part_name']]))
    parts.sort()
    return parts

# ==========================================
# [탭 1] 설비 등록 및 관리
# ==========================================
with tab1:
    st.subheader("신규 설비 등록")
    # 👇👇 여기서부터 아래에 있는 기존 코드들은 원래대로 쭉 두시면 됩니다! 👇👇
    with st.form("equip_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            e_name = st.text_input("설비명 (필수)")
            loc_options = ["직접 입력"] + get_location_list()
            selected_loc = st.selectbox("설치 위치 및 공정 선택", loc_options)
            e_loc = st.text_input("새로운 위치 직접 입력") if selected_loc == "직접 입력" else selected_loc
            e_price = st.number_input("취득 금액 (원)", min_value=0, value=0, step=10000)
            
        with col2:
            e_date = st.date_input("설치(도입) 일자", value=date.today())
            e_img = st.file_uploader("설비 사진 첨부 (선택)", type=['png', 'jpg', 'jpeg'])
        
        if st.form_submit_button("설비 등록하기"):
            if e_name:
                # 사진이 있다면 Supabase Storage에 업로드 후 URL 받아오기
                img_url = None
                if e_img:
                    file_ext = e_img.name.split('.')[-1]
                    file_name = f"{e_name}_{int(time.time())}.{file_ext}"
                    supabase.storage.from_("equipment").upload(file_name, e_img.read())
                    img_url = supabase.storage.from_("equipment").get_public_url(file_name)
                
                # DB 테이블에 데이터 입력
                try:
                    supabase.table("equipment").insert({
                        "name": e_name, "location": e_loc, 
                        "install_date": str(e_date), "price": e_price, "image_url": img_url
                    }).execute()
                    st.success(f"'{e_name}' 등록 완료!")
                    st.rerun()
                except Exception as e:
                    st.error("이미 등록된 동일한 이름의 설비가 있거나 서버 오류가 발생했습니다.")
            else:
                st.warning("설비명을 입력해 주세요.")
    
    st.subheader("등록된 설비 목록")
    res_eq = supabase.table("equipment").select("*").execute()
    df_equip = pd.DataFrame(res_eq.data)
    if not df_equip.empty:
        df_display = df_equip[['name', 'location', 'install_date', 'price']].rename(
            columns={'name':'설비명', 'location':'설치위치', 'install_date':'도입일자', 'price':'취득금액(원)'})
        st.dataframe(df_display, width='stretch')

    st.divider()
    st.subheader("🛠️ 설비 삭제 관리")
    equip_list = get_equipment_list()
    target_equip = st.selectbox("관리할 설비 선택", equip_list if equip_list else ["등록된 설비 없음"])
    
    if target_equip and target_equip != "등록된 설비 없음":
        target_data = next((item for item in res_eq.data if item["name"] == target_equip), None)
        if target_data and target_data.get('image_url'):
            st.image(target_data['image_url'], width=300)
            
        if st.button("이 설비 기록 영구 삭제 🚨"):
            supabase.table("equipment").delete().eq("name", target_equip).execute()
            st.success("삭제되었습니다.")
            st.rerun()

# ==========================================
# [탭 2] 점검 내역 관리
# ==========================================
with tab2:
    st.subheader("신규 점검 기록")
    with st.form("inspect_form", clear_on_submit=True):
        i_name = st.selectbox("점검한 설비 선택", equip_list if equip_list else ["등록된 설비 없음"])
        i_date = st.date_input("점검 일자", value=date.today())
        i_details = st.text_area("점검 내용 및 특이사항")
        
        if st.form_submit_button("점검 내역 저장"):
            if equip_list:
                supabase.table("inspection").insert({
                    "equip_name": i_name, "inspect_date": str(i_date), "details": i_details
                }).execute()
                st.success("저장 완료!")
                st.rerun()
    
    st.subheader("점검 기록 목록")
    filter_i_equip = st.selectbox("조회할 설비명 선택 (전체보기)", ["전체 보기"] + equip_list, key="i_filter")
    
    query = supabase.table("inspection").select("*").order("inspect_date", desc=True)
    if filter_i_equip != "전체 보기":
        query = query.eq("equip_name", filter_i_equip)
        
    res_insp = query.execute()
    df_inspect = pd.DataFrame(res_insp.data)
    
    if not df_inspect.empty:
        st.dataframe(df_inspect[['equip_name', 'inspect_date', 'details']].rename(
            columns={'equip_name':'설비명', 'inspect_date':'점검일자', 'details':'점검내용'}), width='stretch')

# ==========================================
# [탭 3] 부품 교체 관리
# ==========================================
with tab3:
    st.subheader("신규 부품 교체 등록")
    
    p_name = st.selectbox("부품을 교체한 설비 선택", equip_list if equip_list else ["등록된 설비 없음"])
    p_date = st.date_input("교체 일자", value=date.today())
    
    part_options = ["직접 입력"] + get_part_name_list()
    selected_part = st.selectbox("교체 부품명 선택", part_options)
    p_part = st.text_input("새로운 교체 부품명 직접 입력") if selected_part == "직접 입력" else selected_part
    
    col_q1, col_q2 = st.columns(2)
    with col_q1:
        p_qty = st.number_input("수량 (개)", min_value=1, value=1, step=1)
    with col_q2:
        p_price = st.number_input("단가 (원)", min_value=0, value=0, step=1000)
    
    p_total = p_qty * p_price
    st.info(f"💰 총 합계액: **{p_total:,} 원** (자동 계산)")

    with st.form("parts_form", clear_on_submit=True):
        p_details = st.text_area("교체 사유 및 상세 내용")
        
        if st.form_submit_button("교체 내역 저장"):
            if equip_list and p_part:
                supabase.table("parts").insert({
                    "equip_name": p_name, "replace_date": str(p_date), "part_name": p_part,
                    "quantity": p_qty, "unit_price": p_price, "total_price": p_total, "details": p_details
                }).execute()
                st.success("저장 완료!")
                st.rerun()
            else:
                st.warning("부품명을 올바르게 입력해 주세요.")
    
    st.subheader("부품 교체 기록 조회")
    filter_p_equip = st.selectbox("조회할 설비명 선택 (전체보기)", ["전체 보기"] + equip_list, key="p_filter")
    
    query_p = supabase.table("parts").select("*").order("replace_date", desc=True)
    if filter_p_equip != "전체 보기":
        query_p = query_p.eq("equip_name", filter_p_equip)
        
    res_parts = query_p.execute()
    df_parts = pd.DataFrame(res_parts.data)
    
    if not df_parts.empty:
        st.dataframe(df_parts[['equip_name', 'replace_date', 'part_name', 'quantity', 'unit_price', 'total_price', 'details']].rename(
            columns={'equip_name':'설비명', 'replace_date':'교체일자', 'part_name':'부품명', 'quantity':'수량', 'unit_price':'단가(원)', 'total_price':'합계액(원)', 'details':'교체사유'}), width='stretch')
