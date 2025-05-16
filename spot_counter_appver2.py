import streamlit as st
from PIL import Image
import numpy as np
import cv2
import io

# ページ設定
st.set_page_config(page_title="輝点解析ツール", layout="wide")

# サイドバー上部結果表示
result_placeholder_sidebar = st.sidebar.empty() 
def display_count_in_sidebar(placeholder, count_value):
    label_text = "【解析結果】輝点数"; value_text = str(count_value) 
    bg="#495057"; lf="white"; vf="white"
    html=f"""<div style="border-radius:8px;padding:15px;text-align:center;background-color:{bg};margin-bottom:15px;color:{lf};"><p style="font-size:16px;margin-bottom:5px;font-weight:bold;">{label_text}</p><p style="font-size:48px;font-weight:bold;margin-top:0px;color:{vf};line-height:1.1;">{value_text}</p></div>"""
    placeholder.markdown(html, unsafe_allow_html=True)

# アプリタイトルと使用方法
st.markdown("<h1>Gra&Green<br>輝点カウントツール</h1>", unsafe_allow_html=True)
st.markdown("""### 使用方法
1. 画像を左にアップロードしてください。
2. 左サイドバーのパラメータを調整し、メインエリアの「3. 輝点検出とマーキング」で輝点が正しく検出されるようにしてください。
3. 特に「1. ノイズ除去」と「2. 二値化」の設定が重要です。「2. 二値化処理後」の画像で輝点と背景が綺麗に分かれるように調整します。
4. 「3. 形態学的処理」や「4. 輝点フィルタリング」は、検出結果をさらに調整するために使用します。""")
st.markdown("---") 

# セッションステート初期化
if 'counted_spots_value' not in st.session_state: st.session_state.counted_spots_value = "---" 
# (二値化のセッションステートは適応的閾値処理用に変更するため、一旦コメントアウトまたは削除も検討)
# if "binary_threshold_value" not in st.session_state: st.session_state.binary_threshold_value = 58
# if "threshold_slider_for_binary" not in st.session_state: st.session_state.threshold_slider_for_binary = st.session_state.binary_threshold_value
# if "threshold_number_for_binary" not in st.session_state: st.session_state.threshold_number_for_binary = st.session_state.binary_threshold_value

# コールバック関数 (適応的閾値処理では直接は使わないが、もしグローバルと切り替えるなら必要)
# def sync_threshold_from_slider(): ...
# def sync_threshold_from_number_input(): ...

# --- サイドバー ---
st.sidebar.header("解析パラメータ設定")
UPLOAD_ICON = "📤" 
uploaded_file = st.sidebar.file_uploader(f"{UPLOAD_ICON} 画像をアップロード", type=['tif', 'tiff', 'png', 'jpg', 'jpeg'], help="対応形式: TIF, TIFF, PNG, JPG, JPEG。")
display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value)

if uploaded_file is not None:
    # (画像読み込みとグレースケール変換、8bit化処理は前回と同様)
    # ... (省略) ...
    pil_image_original = Image.open(io.BytesIO(uploaded_file.getvalue()))
    pil_image_rgb_for_display = pil_image_original.convert("RGB")
    np_array_rgb_uint8_for_display = np.array(pil_image_rgb_for_display).astype(np.uint8) # uint8に変換
    img_gray = cv2.cvtColor(np_array_rgb_uint8_for_display, cv2.COLOR_RGB2GRAY)
    if img_gray.dtype != np.uint8: img_gray = img_gray.astype(np.uint8)


    # --- サイドバーのパラメータ設定 ---
    # ★★★ 1. ガウシアンブラーを調整可能に戻す ★★★
    st.sidebar.subheader("1. ノイズ除去 (ガウシアンブラー)")
    kernel_options_blur = [1, 3, 5, 7, 9, 11, 13, 15]
    kernel_size_blur = st.sidebar.select_slider(
        'カーネルサイズ (奇数を選択)', 
        options=kernel_options_blur, 
        value=3 # デフォルトを少しぼかす3に
    )
    st.sidebar.caption("""
    - **大きくすると:** ぼかしが強くなりノイズが減りますが、輝点もぼやけます。
    - **小さくすると:** ぼかしが弱く、輪郭はシャープですがノイズが残りやすいです。(1はほぼ効果なし)
    """)

    # ★★★ 2. 二値化を適応的閾値処理に変更 ★★★
    st.sidebar.subheader("2. 二値化 (適応的閾値処理)")
    st.sidebar.markdown("画像の局所的な特徴に応じて閾値を変化させます。照明ムラに強いです。")
    
    adaptive_method_options = {
        "平均値 (Mean)": cv2.ADAPTIVE_THRESH_MEAN_C,
        "ガウシアン重み付き平均 (Gaussian)": cv2.ADAPTIVE_THRESH_GAUSSIAN_C
    }
    selected_adaptive_method_name = st.sidebar.selectbox(
        "適応的閾値処理の方法",
        options=list(adaptive_method_options.keys()),
        index=1 # デフォルトはガウシアン
    )
    adaptive_method_cv = adaptive_method_options[selected_adaptive_method_name]

    block_size = st.sidebar.slider(
        "ブロックサイズ (奇数、閾値計算の近傍領域)",
        min_value=3, max_value=51, value=11, step=2 # 奇数のみ
    )
    c_value = st.sidebar.slider(
        "C値 (計算された閾値から引く定数)",
        min_value=-10, max_value=10, value=2, step=1
    )
    st.sidebar.caption("""
    - **ブロックサイズ:** 小さすぎるとノイズに敏感、大きすぎると局所性が失われます。
    - **C値:** 正の値にすると閾値が下がり白くなりやすく、負の値にすると閾値が上がり黒くなりやすくなります。
    """)

    # (以前のグローバル閾値のスライダーと数値入力は削除またはコメントアウト)
    # st.sidebar.slider('二値化 閾値 (スライダーで調整)', ...)
    # st.sidebar.number_input('二値化 閾値 (直接入力)', ...)
    
    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    st.sidebar.markdown("_上記「二値化」でうまくいかない場合は下記設定も変更してみてください。_")

    # (形態学的処理と輝点フィルタリングのUIは変更なし、ヘッダー番号のみ変更)
    st.sidebar.subheader("3. 形態学的処理 (オープニング)") 
    # ... (内容は前回と同じ)
    morph_kernel_shape_options = {"楕円":cv2.MORPH_ELLIPSE,"矩形":cv2.MORPH_RECT,"十字":cv2.MORPH_CROSS}
    selected_shape_name_sb = st.sidebar.selectbox("カーネル形状 ",options=list(morph_kernel_shape_options.keys()),index=0, key="morph_shape_sb_key_adapt") 
    morph_kernel_shape = morph_kernel_shape_options[selected_shape_name_sb]
    st.sidebar.caption("輝点の形状に合わせて。")
    kernel_options_morph = [1,3,5,7,9]; kernel_size_morph=st.sidebar.select_slider('カーネルサイズ ',options=kernel_options_morph,value=3, key="morph_size_sb_key_adapt") # キー名を少し変更
    st.sidebar.caption("""- **大きくすると:** 効果強、輝点も影響あり。\n- **小さくすると:** 効果弱。""")

    st.sidebar.subheader("4. 輝点フィルタリング (面積)") 
    # ... (内容は前回と同じ)
    min_area = st.sidebar.number_input('最小面積 ',min_value=1,max_value=10000,value=15,step=1, key="min_area_sb_key_adapt") 
    st.sidebar.caption("""- **大きくすると:** 小さな輝点を除外。\n- **小さくすると:** ノイズを拾う可能性。""")
    max_area = st.sidebar.number_input('最大面積 ',min_value=1,max_value=100000,value=1000,step=1, key="max_area_sb_key_adapt") 
    st.sidebar.caption("""- **大きくすると:** 大きな塊もカウント。\n- **小さくすると:** 大きな塊を除外。""")


    # --- メインエリアでの画像表示と処理 ---
    st.header("処理ステップごとの画像")
    
    # 1. ノイズ除去 (ガウシアンブラー)
    # (この処理は画像がロードされた直後、かつimg_grayが確定した後に行うのが適切)
    if img_gray is None or img_gray.size == 0 : 
        st.error("グレースケール画像の準備に失敗しました。")
        st.stop()
    
    blurred_img = cv2.GaussianBlur(img_gray, (kernel_size_blur, kernel_size_blur), 0)

    # 2. 二値化処理 (適応的閾値処理を使用)
    try:
        # ★★★ 適応的閾値処理 ★★★
        binary_img_processed = cv2.adaptiveThreshold(
            blurred_img, 
            255, # 最大値
            adaptive_method_cv, # 適応方法
            cv2.THRESH_BINARY, # 閾値の種類 (通常の二値化)
            block_size, # ブロックサイズ
            c_value # C値
        )
        binary_img_for_morph_processed = binary_img_processed.copy()
    except Exception as e_thresh:
        st.error(f"適応的二値化処理に失敗: {e_thresh}")
        binary_img_for_morph_processed = None # エラー時はNone
    
    # (形態学的処理、輪郭検出、カウント、結果表示は前回とほぼ同じだが、入力画像名に注意)
    # (opened_img_processed, binary_img_for_contours_processed, current_counted_spots, output_image_contours_display の計算)
    # ... (省略) ...

    # (メインエリアの画像表示部分、ヘッダー番号変更)
    st.subheader("元の画像")
    st.image(np_array_rgb_uint8_for_display, caption='アップロードされた画像', use_container_width=True)
    st.markdown("---")

    st.subheader("1. ノイズ除去後 (ガウシアンブラー)") # ★★★ 表示追加 ★★★
    st.image(blurred_img, caption=f'カーネル: {kernel_size_blur}x{kernel_size_blur}', use_container_width=True)
    st.markdown("---")
    
    st.subheader("2. 二値化処理後 (適応的閾値)") # ★★★ ヘッダー変更 ★★★
    if binary_img_processed is not None: 
        st.image(binary_img_processed,caption=f'適応的閾値: {selected_adaptive_method_name}, Block:{block_size}, C:{c_value}',use_container_width=True)
    else: st.info("二値化未実施/失敗")
    st.markdown("---")

    # (形態学的処理後と輝点検出とマーキングの表示、ヘッダー番号変更)
    # ... (省略) ...
    opened_img_processed = None 
    if binary_img_for_morph_processed is not None:
        kernel_morph_obj=cv2.getStructuringElement(morph_kernel_shape,(kernel_size_morph,kernel_size_morph))
        opened_img_processed=cv2.morphologyEx(binary_img_for_morph_processed,cv2.MORPH_OPEN,kernel_morph_obj)
        binary_img_for_contours_processed = opened_img_processed.copy()
    else: binary_img_for_contours_processed = None
    
    current_counted_spots = 0 
    output_image_contours_display = cv2.cvtColor(np_array_rgb_uint8_for_display, cv2.COLOR_RGB2BGR) # 元のカラー画像(BGR)をベースに
    if binary_img_for_contours_processed is not None:
        contours, hierarchy = cv2.findContours(binary_img_for_contours_processed,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        if 'contours' in locals() and contours: 
            for contour in contours:
                area = cv2.contourArea(contour)
                if min_area <= area <= max_area: # min_area, max_area はサイドバーから取得
                    current_counted_spots += 1
                    cv2.drawContours(output_image_contours_display, [contour], -1, (0,255,0), 2) 
        st.session_state.counted_spots_value = current_counted_spots 
    else:
        st.warning("輪郭検出の元画像準備できず。"); st.session_state.counted_spots_value="エラー"

    st.subheader("3. 形態学的処理後") # ★★★ ヘッダー番号変更 ★★★
    if opened_img_processed is not None: st.image(opened_img_processed,caption=f'カーネル:{selected_shape_name_sb} {kernel_size_morph}x{kernel_size_morph}',use_container_width=True)
    else: st.info("形態学的処理未実施/失敗")
    st.markdown("---")

    st.subheader("4. 輝点検出とマーキング") # ★★★ ヘッダー番号変更 ★★★
    display_final_marked_image_rgb = cv2.cvtColor(output_image_contours_display, cv2.COLOR_BGR2RGB)
    if 'contours' in locals() and contours and binary_img_for_contours_processed is not None and current_counted_spots > 0 :
         st.image(display_final_marked_image_rgb,caption=f'検出輝点(緑輪郭,面積:{min_area}-{max_area})',use_container_width=True)
    elif binary_img_for_contours_processed is not None: 
        st.image(display_final_marked_image_rgb,caption='輝点見つからず',use_container_width=True)
    else: st.info("輝点検出未実施")

    display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value)

else: 
    st.info("まず、サイドバーから画像ファイルをアップロードしてください。")
    st.session_state.counted_spots_value = "---"
    display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value)
