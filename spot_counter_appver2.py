import streamlit as st
from PIL import Image
import numpy as np
import cv2
import io
from streamlit_cropper import st_cropper

# ページ設定 (一番最初に呼び出す)
st.set_page_config(page_title="GG輝点解析ツール", layout="wide", initial_sidebar_state="expanded")

# --- シンプルなCSSのみ ---
st.markdown("""
<style>
    .main .block-container {
        padding-top: 1rem !important;
    }
</style>
""", unsafe_allow_html=True)

# --- サイドバーの上部に結果表示用のプレースホルダーを定義 ---
result_placeholder_sidebar = st.sidebar.empty()

# --- 結果表示関数 ---
def display_count_in_sidebar(placeholder, count_value):
    label_text = "【解析結果】輝点数"
    value_text = str(count_value)
    bg="#495057"; lf="white"; vf="white"
    html_code = f"""
    <div style="border-radius:8px; padding:15px; text-align:center; background-color:{bg}; margin-bottom:15px; color:{lf};">
        <p style="font-size:16px; margin-bottom:5px; font-weight:bold;">{label_text}</p>
        <p style="font-size:48px; font-weight:bold; margin-top:0px; color:{vf}; line-height:1.1;">{value_text}</p>
    </div>
    """
    placeholder.markdown(html_code, unsafe_allow_html=True)

# --- 永続化セッションステートを最小限に ---
if 'pil_image_original' not in st.session_state:
    st.session_state.pil_image_original = None
if 'counted_spots_value' not in st.session_state:
    st.session_state.counted_spots_value = "---"

def hex_to_bgr(hex_color):
    hex_color = hex_color.lstrip('#')
    h_len = len(hex_color)
    return tuple(int(hex_color[i:i + h_len // 3], 16) for i in range(0, h_len, h_len // 3))[::-1]

# --- サイドバーの基本部分 ---
display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value)
st.sidebar.header("解析パラメータ設定")
uploaded_file_widget = st.sidebar.file_uploader("画像をアップロード", type=['tif', 'tiff', 'png', 'jpg', 'jpeg'])

# --- アプリのメインタイトルと使用方法 ---
st.markdown("<h1>GG輝点解析ツール</h1>", unsafe_allow_html=True)
st.markdown("### ★ 現在は動作確認のためのテスト版です ★")
st.markdown("---")

# --- 画像読み込みロジック ---
if uploaded_file_widget is not None:
    try:
        uploaded_file_bytes = uploaded_file_widget.getvalue()
        st.session_state.pil_image_original = Image.open(io.BytesIO(uploaded_file_bytes))
    except Exception as e:
        st.sidebar.error(f"画像の読み込みに失敗: {e}")
        st.session_state.pil_image_original = None
else:
    st.session_state.pil_image_original = None

# --- メイン処理 ---
if st.session_state.pil_image_original is not None:
    # --- サイドバーのパラメータ設定UI (★コールバックやキーを削除し、valueで直接指定) ---
    st.sidebar.subheader("1. 輝点検出方法")
    detection_method = st.sidebar.radio("検出方法を選択", ("色で検出", "明るさで検出"), horizontal=True)
    st.sidebar.markdown("---")

    if detection_method == "明るさで検出":
        st.sidebar.subheader("2. 二値化")
        binary_threshold_value = st.sidebar.slider('閾値', 0, 255, 15)
    else: # 色で検出
        st.sidebar.subheader("2. 色の範囲設定 (HSV)")
        hue_range_value = st.sidebar.slider("色相(H)の範囲", 0, 179, (0, 25))
        saturation_value = st.sidebar.slider("彩度(S)の下限", 0, 255, 200)
        brightness_value = st.sidebar.slider("明度(V)の下限", 0, 255, 60)

    st.sidebar.subheader("3. 形態学的処理")
    kernel_size_morph_to_use = st.sidebar.select_slider('カーネルサイズ', options=[1, 3, 5, 7, 9], value=1)
    
    st.sidebar.subheader("4. 輝点フィルタリング (面積)")
    min_area_to_use = st.sidebar.number_input('最小面積', 1, 10000, 1)
    max_area_to_use = st.sidebar.number_input('最大面積', 1, 100000, 100)
    
    st.sidebar.subheader("5. 表示設定")
    CONTOUR_COLORS = {"緑":"#28a745", "青":"#007bff", "赤":"#dc3545", "黄":"#ffc107", "シアン":"#17a2b8", "ピンク":"#e83e8c"}
    contour_color_name = st.sidebar.radio("輝点マーキング色", list(CONTOUR_COLORS.keys()), index=1, horizontal=True)
    contour_color_bgr = hex_to_bgr(CONTOUR_COLORS[contour_color_name])

    # --- メインエリアのUI ---
    st.header("1. 解析エリアの選択 (トリミング)")
    img_for_cropper = st.session_state.pil_image_original.copy()
    CROPPER_MAX_DIM = 700
    if img_for_cropper.width > CROPPER_MAX_DIM or img_for_cropper.height > CROPPER_MAX_DIM:
        img_for_cropper.thumbnail((CROPPER_MAX_DIM, CROPPER_MAX_DIM))

    cropped_img = st_cropper(img_for_cropper, realtime_update=False, box_color='#007bff')

    st.markdown("---")
    st.header("解析結果の比較")

    # --- 画像処理と表示ロジック ---
    try:
        pil_image_rgb = cropped_img.convert("RGB")
        original_img_to_display_np_uint8 = np.array(pil_image_rgb).astype(np.uint8)
    except Exception as e:
        st.error(f"トリミング後の画像の変換に失敗: {e}")
        st.stop()

    binary_img = None
    if detection_method == "明るさで検出":
        img_gray = cv2.cvtColor(original_img_to_display_np_uint8, cv2.COLOR_RGB2GRAY)
        blurred_img = cv2.GaussianBlur(img_gray, (1, 1), 0)
        _, binary_img = cv2.threshold(blurred_img, binary_threshold_value, 255, cv2.THRESH_BINARY)
    else: # 色で検出
        img_hsv = cv2.cvtColor(original_img_to_display_np_uint8, cv2.COLOR_RGB2HSV)
        hue_min, hue_max = hue_range_value
        lower_range = np.array([hue_min, saturation_value, brightness_value])
        upper_range = np.array([hue_max, 255, 255])
        binary_img = cv2.inRange(img_hsv, lower_range, upper_range)

    if binary_img is not None:
        kernel_morph_obj = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size_morph_to_use, kernel_size_morph_to_use))
        opened_img = cv2.morphologyEx(binary_img, cv2.MORPH_OPEN, kernel_morph_obj, iterations=1)
        
        contours, _ = cv2.findContours(opened_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        current_counted_spots = 0
        output_image_contours_display = cv2.cvtColor(original_img_to_display_np_uint8, cv2.COLOR_RGB2BGR)
        
        if contours:
            for contour in contours:
                area = cv2.contourArea(contour)
                if min_area_to_use <= area <= max_area_to_use:
                    current_counted_spots += 1
                    cv2.drawContours(output_image_contours_display, [contour], -1, contour_color_bgr, 2)
        
        st.session_state.counted_spots_value = current_counted_spots
        
        col1_res, col2_res = st.columns(2)
        with col1_res:
            st.subheader("元の画像 (トリミング後)")
            st.image(original_img_to_display_np_uint8, use_container_width=True)
        with col2_res:
            st.subheader("輝点検出とマーキング")
            st.image(cv2.cvtColor(output_image_contours_display, cv2.COLOR_BGR2RGB), caption=f'検出輝点({current_counted_spots}個)', use_container_width=True)
    else:
        st.error("二値化処理に失敗しました。")

else:
    st.info("まず、サイドバーから画像ファイルをアップロードしてください。")
    st.session_state.counted_spots_value = "---"

# サイドバーの最終結果表示
display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value)
