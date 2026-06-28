# ── Report form ──
    with st.container():
        # THIS IS THE MISSING LINE! We have to create the columns first.
        col_left, col_right = st.columns([1.1, 1], gap="large")

        with col_left:
            st.markdown("**Upload Photo or Video**")
            uploaded = st.file_uploader(
                "Drag & drop or click to browse",
                type=["jpg", "jpeg", "png", "webp", "mp4", "mov"],
                key="report_upload",
                label_visibility="collapsed",
            )
            if uploaded:
                try:
                    # Extract bytes safely
                    file_bytes = uploaded.getvalue()
                    mime_type = uploaded.type or "image/jpeg"
                    
                    if mime_type.startswith("image"):
                        st.image(file_bytes, use_container_width=True)
                    else:
                        st.video(file_bytes)
                except Exception:
                    # If Streamlit panics on the file format, catch it!
                    st.warning("⚠️ Preview unavailable for this specific file, but you can still submit it!")

        with col_right:
            st.markdown("**Citizen Details**")
            citizen_id = st.text_input("Citizen ID", placeholder="e.g. CIT-00123", key="citizen_id")
            locality = st.text_input("Locality / Ward Name", placeholder="e.g. Sector 62, Noida", key="locality")

            st.markdown("**GPS Coordinates**")
            coord_col1, coord_col2, coord_col3 = st.columns([2, 2, 1])
            with coord_col1:
                lat = st.number_input("Latitude", value=28.6139, format="%.6f", key="lat")
            with coord_col2:
                lon = st.number_input("Longitude", value=77.2090, format="%.6f", key="lon")
            with coord_col3:
                st.markdown("<div style='margin-top:1.75rem'></div>", unsafe_allow_html=True)
                def randomize_coords():
                    st.session_state["lat"] = round(28.4 + random.random() * 0.5, 6)
                    st.session_state["lon"] = round(76.9 + random.random() * 0.6, 6)
                st.button("🎲", help="Randomise coordinates near Delhi NCR", on_click=randomize_coords)

            st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)
            submit_btn = st.button("🚀 Submit Report", use_container_width=True, key="submit_report")