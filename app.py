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
    
    # 설비별 사진 딕셔너리 매핑 생성 (이름 일치 보장용)
    equip_photo_map = {row['name']: row.get('photo', '사진 없음') for row in equip_data} if equip_data else {}
    
    # --- [탭 1] 설비 등록 및 현황 ---
    with tab_equip:
        st.write("신규 설비를 등록하고 현재 상태를 확인합니다.")
        with st.expander("➕ 신규 설비 등록하기", expanded=False):
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
                        "install_date": str(install_date)
                    }).execute()
                    st.success(f"✅ [{equip_name}] 등록 완료!")
                    st.rerun()
                else:
                    st.warning("설비명과 위치를 모두 입력해 주세요.")
                
        st.markdown("---")
        st.write("📋 **등록된 기계 설비 목록 (첨부 사진 포함)**")
        if equip_data:
            df_equip = pd.DataFrame(equip_data)
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
            # 🌟 딕셔너리 매핑을 사용하여 확실하게 사진 이름 가져오기
            df_ins['photo'] = df_ins['equipment_name'].map(equip_photo_map).fillna('사진 없음')
            
            df_ins_display = df_ins[['created_at', 'equipment_name', 'detail', 'photo']].sort_values(by='created_at', ascending=False)
            df_ins_display.columns = ['점검일자', '설비명', '점검내역', '설비사진명']
            df_ins_display['점검일자'] = df_ins_display['점검일자'].apply(lambda x: x[:10])
            st.dataframe(df_ins_display, use_container_width=True, hide_index=True)

    # --- [탭 3] 부품 교체 관리 ---
    with tab_parts:
        st.write("부품 교체 및 수리 내역을 등록합니다.")
        res_parts = supabase.table("parts").select("*").execute()
        parts_data = res_parts.data if res_parts.data else []
        existing_parts = sorted(list(set([row['part_name'] for row in parts_data if row.get('part_name')]))) if parts_data else []
        
        target_equip_part = st.selectbox("부품을 교체한 설비 선택", equip_names, key="part_eq_select")
        part_choice = st.selectbox("교체 부품명 선택", ["직접 새 부품명 입력하기"] + existing_parts)
        if part_choice == "직접 새 부품명 입력하기":
            final_part_name = st.text_input("새로운 부품명 입력")
        else:
            final_part_name = part_choice
            
        col_q, col_p, col_t = st.columns(3)
        with col_q: part_qty = st.number_input("교체 수량", min_value=1, step=1, value=1, key="p_qty")
        with col_p: part_price = st.number_input("부품 단가 (원)", min_value=0, step=1000, key="p_price")
            
        total_price = part_qty * part_price
        with col_t: st.info(f"**자동 합계 금액:** {total_price:,} 원")
            
        part_detail = st.text_input("기타 특이사항 (선택)", key="p_detail")
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
            # 🌟 딕셔너리 매핑을 사용하여 확실하게 사진 이름 가져오기
            df_pts['photo'] = df_pts['equipment_name'].map(equip_photo_map).fillna('사진 없음')
            
            df_pts_display = df_pts[['created_at', 'equipment_name', 'part_name', 'quantity', 'total_cost', 'photo']].sort_values(by='created_at', ascending=False)
            df_pts_display.columns = ['교체일자', '설비명', '교체부품명', '수량', '합계금액(원)', '설비사진명']
            df_pts_display['교체일자'] = df_pts_display['교체일자'].apply(lambda x: x[:10])
            st.dataframe(df_pts_display, use_container_width=True, hide_index=True)

    # --- [탭 4] 이력 조회 및 데이터 관리 ---
    with tab_data:
        st.write("특정 설비의 이력을 날짜별로 조회하거나 데이터를 관리(수정/삭제/CSV)합니다.")
        st.subheader("🔎 특정 설비 이력 조회 (사진 및 상세 내역)")
        search_target = st.selectbox("이력을 조회할 설비를 선택하세요", equip_names, key="search_eq")
        
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
            delete_id = st.number_input("삭제할 데이터의 고유 ID 번호", min_value=0, step=1, key="del_id_input")
            if st.button("해당 ID 데이터 완전히 삭제", key="del_btn_action"):
                if delete_id > 0:
                    supabase.table("parts").delete().eq("id", delete_id).execute()
                    st.success(f"ID {delete_id}번 데이터가 삭제되었습니다.")
                    st.rerun()
