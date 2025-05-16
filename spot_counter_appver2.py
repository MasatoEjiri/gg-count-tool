import streamlit as st
from PIL import Image
import numpy as np
import cv2
import io
# import requests # ★★★ requestsライブラリのインポートを削除 ★★★

# ページ設定 (一番最初に呼び出す)
st.set_page_config(page_title="輝点解析ツール", layout="wide")

# --- サイドバーの上部に結果表示用のプレースホルダーを定義 ---
result_placeholder_sidebar = st.sidebar.empty() 

# --- カスタマイズされた結果表示関数 (サイドバー表示用) ---
def display_count_in_sidebar(placeholder, count_value):
    label_text = "【解析結果】輝点数" 
    value_text = str(count_value) 
    background_color = "#495057"; label_font_color = "white"; value_font_color = "white"
    html_content = f"""
    <div style="border-radius:8px; padding:15px; text-align:center; background-color:{background_color}; margin-bottom:15px; color:{label_font_color};">
        <p style="font-size:16px; margin-bottom:5px; font-weight:bold;">{label_text}</p>
        <p style="font-size:48px; font-weight:bold; margin-top:0px; color:{value_font_color}; line-height:1.1;">{value_text}</p>
    </div>"""
    placeholder.markdown(html_content, unsafe_allow_html=True)

# アプリのタイトル (メインエリア)
st.markdown("<h1>Gra&Green<br>輝点カウントツール</h1>", unsafe_allow_html=True)

# 「使用方法」(メインエリア) - URL入力に関する記述を削除
st.markdown("""
### 使用方法
1. 画像を左にアップロードしてください。
2. 左サイドバーの「1. 二値化」の閾値を動かして、「1. 二値化処理後」の画像が、輝点と背景が適切に分離された状態（実物に近い見え方）になるように調整してください。
3. （それでもカウント値がおかしい場合は、サイドバーの「2. 形態学的処理」や「3. 輝点フィルタリング」の各パラメータも調整してみてください。）
""")
st.markdown("---") 

# --- セッションステートの初期化 ---
if 'counted_spots_value' not in st.session_state: st.session_state.counted_spots_value = "---" 
if "binary_threshold_value" not in st.session_state: st.session_state.binary_threshold_value = 58
if "threshold_slider_for_binary" not in st.session_state: st.session_state.threshold_slider_for_binary = st.session_state.binary_threshold_value
if "threshold_number_for_binary" not in st.session_state: st.session_state.threshold_number_for_binary = st.session_state.binary_threshold_value
if 'pil_image_to_process' not in st.session_state: st.session_state.pil_image_to_process = None
if 'image_source_caption' not in st.session_state: st.session_state.image_source_caption = "アップロードされた画像"


# --- コールバック関数の定義 ---
def sync_threshold_from_slider():
    st.session_state.binary_threshold_value = st.session_state.threshold_slider_for_binary
    st.session_state.threshold_number_for_binary = st.session_state.threshold_slider_for_binary
def sync_threshold_from_number_input():
    st.session_state.binary_threshold_value = st.session_state.threshold_number_for_binary
    st.session_state.threshold_slider_for_binary = st.session_state.threshold_number_for_binary

# --- サイドバー ---
st.sidebar.header("解析パラメータ設定")
UPLOAD_ICON = "📤" 
uploaded_file_widget = st.sidebar.file_uploader(f"{UPLOAD_ICON} 画像をアップロード", type=['tif', 'tiff', 'png', 'jpg', 'jpeg'], help="対応形式: TIF, TIFF, PNG, JPG, JPEG。")

# ★★★ URL入力欄と読み込みボタンを削除 ★★★
# st.sidebar.markdown("---") 
# image_url_input = st.sidebar.text_input("または、画像URLから読み込む:", placeholder="https://example.com/image.jpg", key="image_url_text_input")
# load_url_button = st.sidebar.button("URLから画像を読み込む", key="load_url_button_key")
# st.sidebar.markdown("---") 

display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value)

# --- 画像読み込みロジック (ファイルアップロードのみに) ---
# URL読み込みボタンのチェックを削除
if uploaded_file_widget is not None:
    try:
        uploaded_file_bytes = uploaded_file_widget.getvalue()
        pil_img = Image.open(io.BytesIO(uploaded_file_bytes))
        st.session_state.pil_image_to_process = pil_img
        st.session_state.image_source_caption = f"アップロード: {uploaded_file_widget.name}"
    except Exception as e:
        st.sidebar.error(f"アップロード画像の読み込みに失敗: {e}")
        st.session_state.pil_image_to_process = None
else: # ファイルがアップロードされていない場合、処理対象画像をNoneにリセット
    st.session_state.pil_image_to_process = None


# --- メイン処理 (st.session_state.pil_image_to_process があれば実行) ---
if st.session_state.pil_image_to_process is not None:
    pil_image_rgb_for_display = st.session_state.pil_image_to_process.convert("RGB")
    
    np_array_rgb_uint8_for_display = np.array(pil_image_rgb_for_display)
    if np_array_rgb_uint8_for_display.dtype != np.uint8:
        if np.issubdtype(np_array_rgb_uint8_for_display.dtype, np.floating):
            if np_array_rgb_uint8_for_display.min() >= 0.0 and np_array_rgb_uint8_for_display.max() <= 1.0:
                np_array_rgb_uint8_for_display = (np_array_rgb_uint8_for_display * 255).astype(np.uint8)
            else: np_array_rgb_uint8_for_display = np.clip(np_array_rgb_uint8_for_display, 0, 255).astype(np.uint8)
        elif np.issubdtype(np_array_rgb_uint8_for_display.dtype, np.integer): 
            np_array_rgb_uint8_for_display = np.clip(np_array_rgb_uint8_for_display, 0, 255).astype(np.uint8)
        else: np_array_rgb_uint8_for_display = np_array_rgb_uint8_for_display.astype(np.uint8)
    
    img_gray = cv2.cvtColor(np_array_rgb_uint8_for_display, cv2.COLOR_RGB2GRAY)
    if img_gray.dtype != np.uint8: img_gray = img_gray.astype(np.uint8)

    # サイドバーのパラメータ取得
    threshold_value = st.session_state.binary_threshold_value 
    morph_kernel_shape_options = {"楕円":cv2.MORPH_ELLIPSE,"矩形":cv2.MORPH_RECT,"十字":cv2.MORPH_CROSS}
    selected_shape_name_sb = st.sidebar.selectbox("カーネル形状",options=list(morph_kernel_shape_options.keys()),index=0, key="morph_shape_sb_key_no_roi") 
    morph_kernel_shape = morph_kernel_shape_options[selected_shape_name_sb]
    kernel_options_morph = [1,3,5,7,9]
    kernel_size_morph =st.sidebar.select_slider('カーネルサイズ',options=kernel_options_morph,value=3, key="morph_size_sb_key_no_roi")
    min_area = st.sidebar.number_input('最小面積',min_value=1,max_value=10000,value=15,step=1, key="min_area_sb_key_no_roi") 
    max_area = st.sidebar.number_input('最大面積',min_value=1,max_value=100000,value=1000,step=1, key="max_area_sb_key_no_roi") 

    # サイドバーのキャプション類 (パラメータウィジェットの後に配置)
    st.sidebar.caption("""- **大きくすると:** 明るい部分のみ白に。\n- **小さくすると:** 暗い部分も白に。""", key="caption_thresh_sb_no_roi")
    st.sidebar.markdown("<br>", unsafe_allow_html=True, key="br_sb1_no_roi")
    st.sidebar.markdown("_二値化だけでうまくいかない場合は下記も調整を_", key="md_sb1_no_roi")
    st.sidebar.subheader("2. 形態学的処理 (オープニング)", key="subheader_morph_sb_no_roi") # selectboxの前にsubheader
    # selected_shape_name_sb と morph_kernel_shape は上で定義済み
    st.sidebar.caption("輝点の形状に合わせて。", key="caption_morph_shape_sb_no_roi")
    # kernel_size_morph は上で定義済み
    st.sidebar.caption("""- **大きくすると:** 効果強、輝点も影響あり。\n- **小さくすると:** 効果弱。""", key="caption_morph_size_sb_no_roi")
    st.sidebar.subheader("3. 輝点フィルタリング (面積)", key="subheader_filter_sb_no_roi")
    # min_area, max_area は上で定義済み
    st.sidebar.caption("""- **大きくすると:** 小さな輝点を除外。\n- **小さくすると:** ノイズを拾う可能性。""", key="caption_min_area_sb_no_roi")
    st.sidebar.caption("""- **大きくすると:** 大きな塊もカウント。\n- **小さくすると:** 大きな塊を除外。""", key="caption_max_area_sb_no_roi")


    # --- メインエリアでの画像表示と処理 ---
    st.header("処理ステップごとの画像")
    kernel_size_blur = 1
    if img_gray.size==0: st.error("グレースケール画像が空です。"); st.stop()
    blurred_img = cv2.GaussianBlur(img_gray, (kernel_size_blur,kernel_size_blur),0)
    ret_thresh, binary_img_processed = cv2.threshold(blurred_img,threshold_value,255,cv2.THRESH_BINARY)
    if not ret_thresh: st.error("二値化失敗。"); binary_img_for_morph_processed=None
    else: binary_img_for_morph_processed=binary_img_processed.copy()
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
                if min_area <= area <= max_area:
                    current_counted_spots += 1
                    cv2.drawContours(output_image_contours_display, [contour], -1, (0,255,0), 2) 
        st.session_state.counted_spots_value = current_counted_spots 
    else:
        st.warning("輪郭検出の元画像準備できず。"); st.session_state.counted_spots_value="エラー"
    
    st.subheader("元の画像")
    st.image(np_array_rgb_uint8_for_display, caption=st.session_state.image_source_caption, use_container_width=True)
    st.markdown("---")
    st.subheader("1. 二値化処理後")
    if binary_img_processed is not None: st.image(binary_img_processed,caption=f'閾値:{threshold_value}',use_container_width=True)
    else: st.info("二値化未実施/失敗")
    st.markdown("---")
    st.subheader("2. 形態学的処理後")
    if opened_img_processed is not None: st.image(opened_img_processed,caption=f'カーネル:{selected_shape_name_sb} {kernel_size_morph}x{kernel_size_morph}',use_container_width=True)
    else: st.info("形態学的処理未実施/失敗")
    st.markdown("---")
    st.subheader("3. 輝点検出とマーキング")
    display_final_marked_image_rgb = cv2.cvtColor(output_image_contours_display, cv2.COLOR_BGR2RGB)
    if 'contours' in locals() and contours and binary_img_for_contours_processed is not None and current_counted_spots > 0 :
         st.image(display_final_marked_image_rgb,caption=f'検出輝点(緑輪郭,面積:{min_area}-{max_area})',use_container_width=True)
    elif binary_img_for_contours_processed is not None: 
        st.image(display_final_marked_image_rgb,caption='輝点見つからず',use_container_width=True)
    else: st.info("輝点検出未実施")

    display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value)
else: 
    # ★★★ 「使用方法」のメッセージをファイル未アップロード時にも表示するように変更 ★★★
    st.info("まず、サイドバーから画像ファイルをアップロードしてください。")
    st.session_state.counted_spots_value = "---"
    display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value)
