# (if st.session_state.pil_image_to_process is not None: ブロック内)
    # ... (面積フィルタリングのUIの後) ...
    
    # ★★★ サイドバーに輪郭色選択UIを追加 (color_pickerをradioに変更) ★★★
    st.sidebar.subheader("4. 表示設定")
    st.sidebar.write("輝点マーキング色を選択:")

    # 代表的な6色を定義 (少し落ち着いた見やすい色に変更)
    CONTOUR_COLORS = {
        "緑": "#28a745",
        "青": "#007bff",
        "赤": "#dc3545",
        "黄": "#ffc107",
        "ｼｱﾝ": "#17a2b8", # シアン
        "ﾋﾟﾝｸ": "#e83e8c" # ピンク
    }
    
    # セッションステートに選択中の色名がなければ、デフォルト（緑）を設定
    if 'contour_color_name' not in st.session_state:
        st.session_state.contour_color_name = "緑"

    # 6つの列を作成して、それぞれの色を配置
    cols = st.sidebar.columns(len(CONTOUR_COLORS))

    for i, (name, hex_code) in enumerate(CONTOUR_COLORS.items()):
        with cols[i]:
            # カラーパッチを表示
            st.markdown(
                f'<div style="width:100%; height:25px; background-color:{hex_code}; border: 1px solid #ccc; border-radius: 4px; margin-bottom: 5px;"></div>',
                unsafe_allow_html=True
            )
            # 色選択ボタン
            # 選択中の色のボタンは type="primary" でハイライト
            button_type = "primary" if name == st.session_state.contour_color_name else "secondary"
            if st.button(name, key=f"color_btn_{name}", use_container_width=True, type=button_type):
                st.session_state.contour_color_name = name
                st.rerun() # UIを即時更新してハイライトを反映

    # 選択された色を取得してBGRに変換
    selected_color_hex = CONTOUR_COLORS[st.session_state.contour_color_name]
    contour_color_bgr = hex_to_bgr(selected_color_hex)
    
    # (以降の画像処理ロジックは変更なし)
    # ...
