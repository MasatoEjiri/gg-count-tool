# (spot_counter_appver2.py の if uploaded_file is not None: ブロック内)

    # ... (pil_image_original = Image.open(...) の後) ...
    pil_image_rgb = pil_image_original.convert("RGB") 

    # ★★★ 表示用にuint8のNumPy配列を確実に準備 ★★★
    np_array_for_display = np.array(pil_image_rgb)
    if np_array_for_display.dtype != np.uint8:
        if np.issubdtype(np_array_for_display.dtype, np.floating):
            if np_array_for_display.min() >= 0.0 and np_array_for_display.max() <= 1.0: # 0-1範囲のfloatと仮定
                np_array_for_display = (np_array_for_display * 255).astype(np.uint8)
            else: # それ以外のfloatはクリップして変換
                np_array_for_display = np.clip(np_array_for_display, 0, 255).astype(np.uint8)
        elif np.issubdtype(np_array_for_display.dtype, np.integer): # 他の整数型(例:uint16)
            np_array_for_display = np.clip(np_array_for_display, 0, 255).astype(np.uint8)
        else: # その他の型はとりあえずキャスト試行
            np_array_for_display = np_array_for_display.astype(np.uint8)
    
    # エラーの出ていた st.image() の呼び出し (メインエリアの「元の画像」表示部分など)
    # pil_image_rgb_for_display の代わりに np_array_for_display を使う
    # 例: st.image(np_array_for_display, caption='アップロードされた画像', use_container_width=True)

    # OpenCV処理用のNumPy配列もこの np_array_for_display (RGB, uint8) から作成できる
    img_array_rgb_for_opencv = np_array_for_display.copy() # (またはpil_image_rgbから再度np.array)
    img_gray = cv2.cvtColor(img_array_rgb_for_opencv, cv2.COLOR_RGB2GRAY)
    # ... (以降の処理)
