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

# --- 2. 화면 및 폰트 설정 (모바일에 최적화된 14px) ---
st.set_page_config(page_title="(주)호성 통합시스템", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Nanum+Gothic:wght@400;700;800&display=swap');
html, body, [class*="css"]  {
    font-family: 'Nanum Gothic', sans-serif !important;
    font-size: 14px !important; 
}
</style>
""", unsafe_allow_html=True)


# ==========================================
# 🔒 3. 보안 로그인 시스템
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['username'] = None

if not st.session_state['logged_in']:
    st.subheader("🔐 (주)호성 통합시스템 로그인")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        login_name = st.selectbox("👤 접속자 이름", ["직원", "김공장장", "이이사", "박대표", "최팀장"])
        login_pw = st.text_input("🔑 비밀번호", type="password")
        
        if st.button("로그인"):
            if login_pw == "1234":
                st.session_state['logged_in'] = True
                st.session_state['username'] = login_name
                st.rerun()
            else:
                st.error("⚠️ 비밀번호가 틀렸습니다.")
                
    st.stop()


# ==========================================
# 왼쪽 메뉴바
# ==========================================
with st.sidebar:
    st.success(f"👤 **{st.session_state['username']}**님 접속 중")
    if st.button("로그아웃"):
        st.session_state['logged_in'] = False
        st.session_state['username'] = None
        st.rerun()
        
    st.markdown("---")
    st.markdown("### 🏢 (주)호성 통합메뉴")
    menu = st.radio("메뉴를 선택하세요", 
                    ["⚙️ 기계설비 관리", "📝 전자결재 (기안)", "📦 물류 및 재고 (ERP)"])


# ==========================================
# [메뉴 1] 기계설비 및 유지보수 관리 화면
# ==========================================
if menu == "⚙️ 기계설비 관리":
    st.subheader("⚙️ 기계설비 및 유지보수 관리")
    
    tab_equip, tab_inspect, tab_parts, tab_data = st.tabs(["🚜 설비 등록 및 현황", "🔍 점검 내역 관리", "🔩 부품 교체 관리", "📊 이력 조회 및 데이터 관리"])
    
    res_equip = supabase.table("equipment").select("*").execute()
    equip_data = res_equip.data if res_equip.data else []
    
    equip_names = sorted(list(set([row['name'] for row in equip_data]))) if equip_data else ["등록된 설비 없음"]
    existing_locations = sorted(list(set([row['location'] for row in equip_data if row.get('location')]))) if equip_data else []
    
    # --- [탭 1] 설비 등록 및 현황 ---
    with tab_equip:
        st.write("신규 설비를 등록하고 현재 상태를 확인합니다.")
        with st.expander("➕ 신규 설비 등록하기", expanded=False):
            # 🌟 사용자가 직접 등록일(설치일)을 선택할 수 있는 기능 추가
            install_date = st.date_input("설비 등록일 (설치일)", date.today())
            
            loc_choice = st.selectbox("설치 위치 및 공정 선택", ["직접 새 위치 입력하기"] + existing_locations)
            if loc_choice == "직접 새 위치 입력하기":
                final_location = st.text_input("새로운 설치 위치/공정 입력")
            else:
                final_location = loc_choice
                
            equip_name = st.text_input("설비명 (예: 1호기 파쇄기)")
            equip_cost = st.number_input("취득금액 (원)", min_value=0, step=10000)
            status = st.selectbox("현재 상태", ["🟢 정상 가동", "🟡 점검 요망", "🔴 수리 중"])
            equip_photo = st.file_uploader("설비 사진 첨부 (옵션)", type=["jpg", "png", "jpeg"])
            
            if st.button("신규 설비 등록 저장"):
                if equip_name and final_location:
                    photo_name = equip_photo.name if equip_photo else "사진 없음"
                    supabase.table("equipment").insert({
                        "name": equip_name, 
                        "location": final_location, 
                        "status": status,
                        "cost": equip_cost,
                        "photo": photo_name,
                        "install_date": str(install_date) # 🌟 지정한 등록일 저장
                    }).execute()
                    st.success(f"✅ [{equip_name}] 등록 완료!")
                    st.rerun()
                else:
                    st.warning("설비명과 위치를 모두 입력해 주세요.")
                
        st.markdown("---")
        st.write("📋 **등록된 기계 설비 목록 (첨부 사진 포함)**")
        if equip_data:
            df_equip = pd.DataFrame(equip_data)
            # 사용자가 지정한 install_date가 있으면 우선 표시, 없으면 기존 생성일자 사용
            if 'install_date' not in df_equip.columns:
                df_equip['install_date'] = df_equip['created_at'].apply(lambda x: x[:10])
            df_equip['install_date'] = df_equip['install_date'].fillna(df_equip['created_at'].apply(lambda x: x[:10]))
            
            df_equip_display = df_equip[['install_date', 'name', 'location', 'cost', 'status', 'photo']].sort_values(by='install_date', ascending=False)
            df_equip_display.columns = ['등록일', '설비명', '위치/공정', '취득금액(원)', '상태', '첨부사진명']
            st.dataframe(df_equip_display, use_container_width=True, hide_index=True)
            
    # --- [탭 2] 점검 내역 관리 ---
    with tab_inspect:
        st.write("설비의 정기/수시 점검 내역을 기록합니다.")
        with st.form("inspect_form"):
            target_equip_ins = st.selectbox("점검한 설비 선택", equip_names)
            inspect_detail = st.text_area("점검 상세 내역 및 조치사항")
            if st.form_submit_button("점검 내역 저장") and target_equip_ins != "등록된 설비 없음":
                supabase.table("inspections").insert({"equipment_name": target_equip_ins, "detail": inspect_detail}).execute()
                st.success("✅ 점검 내역이 저장되었습니다.")
                st.rerun()
                
        st.write("📋 **최근 점검 기록 목록 (설비 사진 정보 연동)**")
        res_ins = supabase.table("inspections").select("*").execute()
        if res_ins.data:
            df_ins = pd.DataFrame(res_ins.data)
            # 설비별 사진 정보를 매칭하기 위해 equipment 테이블과 병합
            df_eq_info = pd.DataFrame(equip_data)[['name', 'photo']] if equip_data else pd.DataFrame(columns=['name', 'photo'])
            df_ins_merged = pd.merge(df_ins, df_eq_info, left_on='equipment_name', right_on='name', how='left')
            
            df_ins_display = df_ins_merged[['created_at', 'equipment_name', 'detail', 'photo']].sort_values(by='created_at', ascending=False)
            df_ins_display.columns = ['점검일자', '설비명', '점검내역', '설비사진명']
            df_ins_display['점검일자'] = df_ins_display['점검일자'].apply(lambda x: x[:10])
            df_ins_display['설비사진명'] = df_ins_display['설비사진명'].fillna('사진 없음')
            st.dataframe(df_ins_display, use_container_width=True, hide_index=True)

    # --- [탭 3] 부품 교체 관리 ---
    with tab_parts:
        st.write("부품 교체 및 수리 내역을 등록합니다.")
        res_parts = supabase.table("parts").select("*").execute()
        parts_data = res_parts.data if res_parts.data else []
        existing_parts = sorted(list(set([row['part_name'] for row in parts_data if row.get('part_name')]))) if parts_data else []
        
        target_equip_part = st.selectbox("부품을 교체한 설비 선택", equip_names)
        part_choice = st.selectbox("교체 부품명 선택", ["직접 새 부품명 입력하기"] + existing_parts)
        if part_choice == "직접 새 부품명 입력하기":
            final_part_name = st.text_input("새로운 부품명 입력")
        else:
            final_part_name = part_choice
            
        col_q, col_p, col_t = st.columns(3)
        with col_q: part_qty = st.number_input("교체 수량", min_value=1, step=1, value=1)
        with col_p: part_price = st.number_input("부품 단가 (원)", min_value=0, step=1000)
            
        total_price = part_qty * part_price
        with col_t: st.info(f"**자동 합계 금액:** {total_price:,} 원")
            
        part_detail = st.text_input("기타 특이사항 (선택)")
        if st.button("부품 교체 등록 저장"):
            if target_equip_part != "등록된 설비 없음" and final_part_name:
                supabase.table("parts").insert({
                    "equipment_name": target_equip_part, "part_name": final_part_name,
                    "quantity": part_qty, "unit_price": part_price, "total_cost": total_price, "detail": part_detail
                }).execute()
                st.success("✅ 부품 교체 내역이 저장되었습니다.")
                st.rerun()

        st.write("📋 **최근 부품 교체 기록 목록 (설비 사진 정보 연동)**")
        if parts_data:
            df_pts = pd.DataFrame(parts_data)
            df_eq_info = pd.DataFrame(equip_data)[['name', 'photo']] if equip_data else pd.DataFrame(columns=['name', 'photo'])
            df_pts_merged = pd.merge(df_pts, df_eq_info, left_on='equipment_name', right_on='name', how='left')
            
            df_pts_display = df_pts_merged[['created_at', 'equipment_name', 'part_name', 'quantity', 'total_cost', 'photo']].sort_values(by='created_at', ascending=False)
            df_pts_display.columns = ['교체일자', '설비명', '교체부품명', '수량', '합계금액(원)', '설비사진명']
            df_pts_display['교체일자'] = df_pts_display['교체일자'].apply(lambda x: x[:10])
            df_pts_display['설비사진명'] = df_pts_display['설비사진명'].fillna('사진 없음')
            st.dataframe(df_pts_display, use_container_width=True, hide_index=True)

    # --- [탭 4] 이력 조회 및 데이터 관리 ---
    with tab_data:
        st.write("특정 설비의 이력을 날짜별로 조회하거나 데이터를 관리(수정/삭제/CSV)합니다.")
        st.subheader("🔎 특정 설비 이력 조회 (사진 및 상세 내역)")
        search_target = st.selectbox("이력을 조회할 설비를 선택하세요", equip_names, key="search_eq")
        
        # 선택한 설비의 등록 사진 정보 먼저 보여주기
        if equip_data:
            matched_eq = [eq for eq in equip_data if eq['name'] == search_target]
            if matched_eq:
                eq_info = matched_eq[0]
                st.info(f"📌 **[{search_target}]** 기본 정보 | 위치: {eq_info.get('location', '-')} | 상태: {eq_info.get('status', '-')} | 등록 사진명: **{eq_info.get('photo', '사진 없음')}**")
        
        if parts_data:
            df_all_parts = pd.DataFrame(parts_data)
            filtered_df = df_all_parts[df_all_parts['equipment_name'] == search_target]
            if not filtered_df.empty:
                filtered_df = filtered_df.sort_values(by='created_at', ascending=False)
                disp_df = filtered_df[['created_at', 'part_name', 'quantity', 'total_cost', 'detail']]
                disp_df.columns = ['교체일자', '부품명', '수량', '비용(원)', '특이사항']
                disp_df['교체일자'] = disp_df['교체일자'].apply(lambda x: x[:10])
                st.dataframe(disp_df, use_container_width=True, hide_index=True)
            else:
                st.info(f"'{search_target}'의 부품 교체 이력이 없습니다.")
                
        st.markdown("---")
        st.subheader("💾 CSV 내보내기 및 데이터 삭제")
        col_down, col_del = st.columns(2)
        with col_down:
            if parts_data:
                csv = df_all_parts.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 전체 부품 교체 내역 CSV 다운로드", data=csv, file_name='parts_history.csv', mime='text/csv')
        with col_del:
            delete_id = st.number_input("삭제할 데이터의 고유 ID 번호", min_value=0, step=1)
            if st.button("해당 ID 데이터 완전히 삭제"):
                if delete_id > 0:
                    supabase.table("parts").delete().eq("id", delete_id).execute()
                    st.success(f"ID {delete_id}번 데이터가 삭제되었습니다.")
                    st.rerun()


# ==========================================
# [메뉴 2] 전자결재 시스템 화면
# ==========================================
elif menu == "📝 전자결재 (기안)":
    st.subheader("📝 사내 전자결재 시스템")
    
    tab_draft, tab_approve, tab_archive = st.tabs(["📝 기안 작성", "✅ 결재함 (관리자용)", "🗄️ 결재 완료 문서함"])
    admin_list = ["김공장장", "이이사", "박대표", "최팀장"]
    
    with tab_draft:
        st.write("문서 양식을 선택한 후, 빈칸을 채워 결재를 상신해 주세요.")
        doc_type = st.radio("📋 문서 양식 선택", ["📝 공문형 기안문", "💰 지출 품의서", "📊 표준 보고서"], horizontal=True)
        doc_title = st.text_input("문서 제목")
        
        if doc_type == "📝 공문형 기안문":
            template = "(주) 호 성\n\n수신자: [수신 부서 또는 직책]\n(경유): \n제  목: [여기에 제목을 한 번 더 입력하세요]\n--------------------------------------------------\n1. 귀 부서의 노고에 감사드립니다.\n2. [기안의 배경 및 목적을 간략히 기재하세요.]\n3. 위와 관련하여 아래와 같이 업무를 추진하고자 하오니 검토 후 재가하여 주시기 바랍니다.\n\n                        - 아    래 -\n        \n가. 일시/기간: \n나. 대상/장소: \n다. 소요 예산: \n라. 상세 내용: \n        \n붙임  1. [첨부문서 1 이름] 1부.\n      2. [첨부문서 2 이름] 1부.  끝.\n\n                     (주) 호 성 대 표 이 사"
        elif doc_type == "💰 지출 품의서":
            template = "■ 청구 내역 (품목/공사명):\n\n■ 예상 비용 (VAT 포함):\n             원\n■ 결제 수단 (법인카드/계좌이체 등):\n\n■ 거래처 정보 (상호/연락처):\n\n■ 첨부(영수증/견적서) 유무:\n"
        elif doc_type == "📊 표준 보고서":
            template = "[ 📄 주 요 업 무  보 고 서 ]\n\n■ 보고 일자 : 202 년   월   일\n■ 보  고  자 : 소속          성명          (서명)\n--------------------------------------------------\n1. 현황 및 배경\n   - [현재 상황이나 보고를 하게 된 배경을 요약]\n\n2. 주요 추진 내용 (또는 발생한 문제점)\n   - [핵심적인 업무 진행 상황이나 상세 내역 기술]\n   - \n\n3. 향후 계획 (또는 개선 방안)\n   - [앞으로의 일정이나 문제 해결을 위한 구체적 방안 기술]\n   - \n\n4. 건의 및 요청사항\n   - [결재권자의 지원이 필요한 부분이나 참고사항 기술]\n"
            
        doc_content = st.text_area("상세 내용 작성", value=template, height=450)
        selected_approvers = st.multiselect("결재권자 지정 (최대 3명 선택 가능)", options=admin_list, max_selections=3)
        
        if st.button("결재 상신하기"):
            if doc_title == "" or len(selected_approvers) == 0:
                st.warning("⚠️ 문서 제목을 입력하고, 결재권자를 최소 1명 이상 지정해 주세요.")
            else:
                approvers_str = ",".join(selected_approvers)
                type_prefix = doc_type.split(" ")[1] 
                final_title = f"[{type_prefix}] {doc_title}"
                data = {"title": final_title, "content": doc_content, "status": "대기중", "approvers": approvers_str, "approved_by": ""}
                supabase.table("approvals").insert(data).execute()
                st.success("✅ 결재가 성공적으로 상신되었습니다!")
                
    with tab_approve:
        current_admin = st.session_state['username']
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
                        st.write("**상세 내용:**")
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
                                new_status = "최종 통과 (승인됨)" if set(approvers_list).issubset(set(approved_list)) else "대기중"
                                supabase.table("approvals").update({"approved_by": new_approved_by, "status": new_status}).eq("id", doc['id']).execute()
                                st.rerun()
                        with col2:
                            if st.button("❌ 반려하기", key=f"rej_{doc['id']}"):
                                supabase.table("approvals").update({"status": "반려됨"}).eq("id", doc['id']).execute()
                                st.rerun()
        else:
            st.warning("🔒 결재 권한이 없습니다. (관리자 계정으로 로그인해 주세요)")

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
                    st.write("**[상세 요청 내용]**")
                    st.info(doc['content'])
                    doc_text = f"======================================\n         결 재 완 료 문 서\n======================================\n■ 기안 제목: {doc['title']}\n■ 기안 일자: {doc['created_at'][:10]}\n■ 결재 상태: {doc['status']}\n■ 지정 결재자: {doc['approvers']}\n■ 승인 완료자: {doc.get('approved_by', '없음')}\n--------------------------------------\n{doc['content']}\n======================================"
                    st.download_button(label="💾 문서 다운로드 (인쇄/보관용)", data=doc_text, file_name=f"결재문서_{doc['title']}.txt", mime="text/plain", key=f"dl_{doc['id']}")


# ==========================================
# [메뉴 3] 재고/물류 관리 (ERP) 화면
# ==========================================
elif menu == "📦 물류 및 재고 (ERP)":
    st.subheader("📦 실시간 재고/물류 관리")
    
    tab_input, tab_dashboard = st.tabs(["🚛 물류 입출고 등록", "📊 실시간 재고 대시보드"])
    
    with tab_input:
        st.write("입고, 출고, 사용 내역과 단위를 정확히 기록해 주세요.")
        with st.form("inventory_form"):
            col1, col2 = st.columns(2)
            with col1:
                log_date = st.date_input("일시 (날짜 선택)", date.today())
                item_list = [
                    "골재(1등급 25mm)", "골재(25mm)", "골재(1등급 20mm)", 
                    "골재(20mm)", "골재(1등급 13mm)", "골재(13mm)", 
                    "골재(잔골재 No4)", "아스팔트(스트레이트)", "아스팔트(개질)"
                ]
                item_type = st.selectbox("품목 선택", item_list)
                in_out = st.radio("물류 구분", ["입고", "출고", "사용"], horizontal=True)
            with col2:
                unit = st.selectbox("단위 선택", ["톤(t)", "m³ (루베)", "L (리터)"])
                quantity = st.number_input("수량", min_value=0.0, step=0.1, format="%.1f")
                
            submitted = st.form_submit_button("저장하기")
            if submitted:
                if quantity <= 0:
                    st.warning("⚠️ 0보다 큰 수량을 입력해 주세요.")
                else:
                    data = {"log_date": str(log_date), "item_type": item_type, "in_out": in_out, "unit": unit, "weight": quantity}
                    supabase.table("inventory").insert(data).execute()
                    st.success(f"✅ {log_date} | [{item_type}] {quantity} {unit} - {in_out} 기록이 저장되었습니다!")
                    
    with tab_dashboard:
        st.write("현재까지 누적된 품목별 재고 현황 및 변화 트렌드입니다.")
        res = supabase.table("inventory").select("*").execute()
        inv_data = res.data
        
        if not inv_data:
            st.info("아직 등록된 물류 내역이 없습니다.")
        else:
            df = pd.DataFrame(inv_data)
            if 'unit' not in df.columns: df['unit'] = '톤(t)'
            df['unit'] = df['unit'].fillna('톤(t)')
            if 'log_date' not in df.columns: df['log_date'] = df['created_at'].apply(lambda x: x[:10])
            df['log_date'] = df['log_date'].fillna(df['created_at'].apply(lambda x: x[:10]))
            
            df['calc_qty'] = df.apply(lambda x: x['weight'] if x['in_out'] == '입고' else -x['weight'], axis=1)
            inventory_summary = df.groupby(['item_type', 'unit'])['calc_qty'].sum().reset_index()
            inventory_summary.columns = ['품목명', '단위', '현재 재고']
            
            cols = st.columns(3)
            for i, row in inventory_summary.iterrows():
                with cols[i % 3]:
                    st.metric(label=f"📦 {row['품목명']}", value=f"{row['현재 재고']:.1f} {row['단위']}")
            
            st.markdown("---")
            st.write("📈 **품목별 누적 재고 트렌드**")
            daily_changes = df.groupby(['log_date', 'item_type'])['calc_qty'].sum().reset_index()
            pivot_df = daily_changes.pivot(index='log_date', columns='item_type', values='calc_qty').fillna(0)
            trend_df = pivot_df.cumsum()
            
            available_items = trend_df.columns.tolist()
            selected_items = st.multiselect("📊 그래프에서 조회할 품목을 선택/해제하세요", options=available_items, default=available_items)
            
            if selected_items:
                st.line_chart(trend_df[selected_items])
            else:
                st.info("👆 위 선택창에서 그래프로 보고 싶은 품목을 선택해 주세요.")
            
            st.markdown("---")
            st.write("📋 **상세 입출고/사용 기록 (최근 순)**")
            df_display = df[['log_date', 'item_type', 'in_out', 'weight', 'unit']].sort_values(by='log_date', ascending=False)
            df_display.columns = ['일시', '품목', '구분', '수량', '단위']
            st.dataframe(df_display, use_container_width=True, hide_index=True)
