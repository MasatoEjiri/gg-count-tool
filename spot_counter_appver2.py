# (if st.session_state.pil_image_to_process is not None: ブロック内)
    # ... (pil_image_rgb_full_res, np_array_rgb_uint8_full_res, img_gray_full_res の準備)
    # ... (pil_for_canvas_bg (縮小版Pillowイメージ), canvas_scale_x, canvas_scale_y の準備)
    # ... (np_for_canvas_bg_display (縮小版NumPy uint8配列) の準備) ...
    
    # (デバッグ表示は変更なし)
    with st.expander("キャンバス背景候補の確認（デバッグ用）", expanded=True):
        if np_for_canvas_bg_display is not None:
            st.image(np_for_canvas_bg_display, caption=f"キャンバス背景プレビュー ({np_for_canvas_bg_display.shape[1]}x{np_for_canvas_bg_display.shape[0]})") # キャプションもNumPyの形状から
        else:
            st.warning("キャンバス背景候補 (NumPy uint8 配列) が準備できませんでした。")
    
    st.info("↓下の画像（キャンバス）上でマウスをドラッグして、解析したい四角いエリアを描画してください。...")
    
    drawing_mode = "rect"; stroke_color = "red"
    
    # ★★★ st_canvas の設定を変更 ★★★
    if np_for_canvas_bg_display is not None and np_for_canvas_bg_display.size > 0:
        canvas_height_for_widget = np_for_canvas_bg_display.shape[0]
        canvas_width_for_widget = np_for_canvas_bg_display.shape[1]
        
        canvas_result = st_canvas(
            fill_color="rgba(255,0,0,0.1)", 
            stroke_width=2, 
            stroke_color=stroke_color,
            background_image=np_for_canvas_bg_display, # ★★★ NumPy配列を背景画像として使用 ★★★
            update_streamlit=True, 
            height=canvas_height_for_widget, # NumPy配列の高さ
            width=canvas_width_for_widget,   # NumPy配列の幅
            drawing_mode=drawing_mode, 
            key="roi_canvas_main_v5" # キーを更新して再初期化を促す
        )
    else:
        st.error("キャンバス背景用の画像データがありません。アップロードファイルを確認してください。")
        canvas_result = None # エラー時はNone扱い
        st.stop()

    # (これ以降のROI処理、サイドバーのパラメータ設定、メインエリアの処理ステップ表示は前回と同じ)
    # ただし、scale_x, scale_y の計算は、pil_image_rgb_full_res と pil_for_canvas_bg の寸法を使う必要があります。
    # pil_for_canvas_bg はPillowオブジェクトなので、そのwidth/heightを分母に使います。
    if pil_image_rgb_full_res and pil_for_canvas_bg:
        scale_x = pil_image_rgb_full_res.width / pil_for_canvas_bg.width
        scale_y = pil_image_rgb_full_res.height / pil_for_canvas_bg.height
    else: # 画像オブジェクトがない場合はデフォルトスケール
        scale_x, scale_y = 1.0, 1.0

    # ... (ROI座標取得とスケーリング、後続処理)
