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
st.set_page_config(page_title="기계설비 관리 (Cloud)", layout="wide")
st.title("☁️ (주)호성")

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
