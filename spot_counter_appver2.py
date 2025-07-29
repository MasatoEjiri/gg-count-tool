import streamlit as st
from PIL import Image
import numpy as np
import cv2
import io
from streamlit_cropper import st_cropper

# ページ設定 (一番最初に呼び出す)
st.set_page_config(page_title="GG輝点解析ツール", layout="wide", initial_sidebar_state="expanded")

# メイン画面上部の余白を調整するためのCSS
st.markdown("""
<style>
    .main .block-container {
        padding-top: 1rem !important;
    }
    /* 「枠の色」のラジオボタンのラベルを非表示にするためのCSS */
    div[data-testid="stRadio"] > label[data-baseweb="radio"] > div:first-of-type {
        display: none;
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] {
        align-items: center;
    }
</style>
""", unsafe_allow_html=True)

# ファイルアップローダーのカスタムCSS
file_uploader_css = """
<style>
    section[data-testid="stFileUploaderDropzone"] {
        border: 3px dashed white !important;
        border-radius: 0.5rem !important;
        background-color: #495057 !important;
        padding: 25px !important;
    }
    section[data-testid="stFileUploaderDropzone"] > div[data-testid="stFileUploadDropzoneInstructions"] {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }
    section[data-testid="stFileUploaderDropzone"] p {
        color: #f8f9fa !important;
        font-size: 0.9rem;
        margin-bottom: 0.75rem !important;
    }
    section[data-testid="stFileUploaderDropzone"] span {
        color: #ced4da !important;
        font-size: 0.8rem;
    }
    section[data-testid="stFileUploaderDropzone"] button {
        color: #ffffff !important;
        background-color: #007bff !important;
        border: 1px solid #007bff !important;      
        padding: 0.5em 1em !important;
        border-radius: 0.375rem !important;
        font-weight: 500 !important;
        margin-top: 0.5rem !important; 
    }
</style>
"""
st.markdown(file_uploader_css, unsafe_allow_html=True)

# --- サイドバーの上部に結果表示用のプレースホルダーを定義 ---
result_placeholder_sidebar = st.sidebar.empty()

# --- カスタマイズされた結果表示関数 (サイドバー表示用) ---
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
    with placeholder.container():
        placeholder.markdown(html_code, unsafe_allow_html=True)

# --- セッションステートの初期化 ---
if 'counted_spots_value' not in st.session_state: st.session_state.counted_spots_value = "---"
if "binary_threshold_value" not in st.session_state: st.session_state.binary_threshold_value = 15
if "threshold_slider" not in st.session_state: st.session_state.threshold_slider = st.session_state.binary_threshold_value
if "threshold_number" not in st.session_state: st.session_state.threshold_number = st.session_state.binary_threshold_value
if "saturation_value" not in st.session_state: st.session_state.saturation_value = 200
if "saturation_slider" not in st.session_state: st.session_state.saturation_slider = st.session_state.saturation_value
if "saturation_number" not in st.session_state: st.session_state.saturation_number = st.session_state.saturation_value
if "brightness_value" not in st.session_state: st.session_state.brightness_value = 60
if "brightness_slider" not in st.session_state: st.session_state.brightness_slider = st.session_state.brightness_value
if "brightness_number" not in st.session_state: st.session_state.brightness_number = st.session_state.brightness_value
if "hue_range_value" not in st.session_state: st.session_state.hue_range_value = (0, 25)
if "hue_range_slider" not in st.session_state: st.session_state.hue_range_slider = st.session_state.hue_range_value
if "hue_min_number" not in st.session_state: st.session_state.hue_min_number = st.session_state.hue_range_value[0]
if "hue_max_number" not in st.session_state: st.session_state.hue_max_number = st.session_state.hue_range_value[1]
if 'pil_image_original' not in st.session_state: st.session_state.pil_image_original = None
if 'pil_image_to_process' not in st.session_state: st.session_state.pil_image_to_process = None
if 'image_source_caption' not in st.session_state: st.session_state.image_source_caption = "アップロードされた画像"
if 'contour_color_name' not in st.session_state: st.session_state.contour_color_name = "青"
if 'cropper_box_color_name' not in st.session_state: st.session_state.cropper_box_color_name = '白'
if 'detection_method' not in st.session_state: st.session_state.detection_method = "色で検出"
if 'max_area_to_use' not in st.session_state: st.session_state.max_area_to_use = 100

# --- コールバック関数とヘルパー関数 ---
def sync_threshold_from_slider():
    st.session_state.binary_threshold_value = st.session_state.threshold_slider
    st.session_state.threshold_number = st.session_state.binary_threshold_value

def sync_threshold_from_number():
    st.session_state.binary_threshold_value = st.session_state.threshold_number
    st.session_state.threshold_slider = st.session_state.binary_threshold_value

def sync_saturation_from_slider():
    st.session_state.saturation_value = st.session_state.saturation_slider
    st.session_state.saturation_number = st.session_state.saturation_value

def sync_saturation_from_number():
    st.session_state.saturation_value = st.session_state.saturation_number
    st.session_state.saturation_slider = st.session_state.saturation_value

def sync_brightness_from_slider():
    st.session_state.brightness_value = st.session_state.brightness_slider
    st.session_state.brightness_number = st.session_state.brightness_value

def sync_brightness_from_number():
    st.session_state.brightness_value = st.session_state.brightness_number
    st.session_state.brightness_slider = st.session_state.brightness_value

def sync_hue_from_slider():
    st.session_state.hue_range_value = st.session_state.hue_range_slider
    st.session_state.hue_min_number, st.session_state.hue_max_number = st.session_state.hue_range_value

def sync_hue_from_number():
    min_val, max_val = st.session_state.hue_min_number, st.session_state.hue_max_number
    if min_val > max_val: min_val = max_val 
    st.session_state.hue_range_value = (min_val, max_val)
    st.session_state.hue_range_slider = st.session_state.hue_range_value

def hex_to_bgr(hex_color):
    hex_color = hex_color.lstrip('#')
    h_len = len(hex_color)
    return tuple(int(hex_color[i:i + h_len // 3], 16) for i in range(0, h_len, h_len // 3))[::-1]

# --- サイドバーの基本部分 ---
display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value) 
st.sidebar.header("解析パラメータ設定")
UPLOAD_ICON = "📤" 
uploaded_file_widget = st.sidebar.file_uploader(f"{UPLOAD_ICON} 画像をアップロード", type=['tif', 'tiff', 'png', 'jpg', 'jpeg'], help="対応形式: TIF, TIFF, PNG, JPG, JPEG。")

# --- アプリのメインタイトルと使用方法 ---
st.markdown("<h1>GG輝点解析ツール</h1>", unsafe_allow_html=True)
st.markdown("""
### 使用方法
1.  画像を左にアップロードしてください。
2.  メイン画面で解析したいエリアをトリミングします。
3.  サイドバーの「1. 輝点検出方法」で解析手法を選び、続く各パラメータを調整してください。
4.  「元の画像（トリミング後）」と「輝点検出とマーキング」を比較しながら最適な設定を見つけます。
""")
st.markdown("---")

# --- 画像読み込みロジック ---
if uploaded_file_widget is not None:
    try:
        uploaded_file_bytes = uploaded_file_widget.getvalue()
        pil_img = Image.open(io.BytesIO(uploaded_file_bytes))
        st.session_state.pil_image_original = pil_img
        st.session_state.image_source_caption = f"アップロード: {uploaded_file_widget.name}"
    except Exception as e:
        st.sidebar.error(f"アップロード画像の読み込みに失敗: {e}")
        st.session_state.pil_image_original = None
        st.session_state.counted_spots_value = "読込エラー"
        st.stop()
else: 
    if st.session_state.pil_image_original is not None: 
        st.session_state.pil_image_original = None
        st.session_state.counted_spots_value = "---"

# --- メイン処理 ---
if st.session_state.pil_image_original is not None:
    # --- メインエリアのトリミングUI ---
    st.header("1. 解析エリアの選択 (トリミング)")
    col_cropper, col_options = st.columns([3, 1])
    
    with col_cropper:
        img_for_cropper = st.session_state.pil_image_original.copy()
        CROPPER_MAX_DIM = 700
        if img_for_cropper.width > CROPPER_MAX_DIM or img_for_cropper.height > CROPPER_MAX_DIM:
            img_for_cropper.thumbnail((CROPPER_MAX_DIM, CROPPER_MAX_DIM))
        
        cropper_key = f"cropper_{uploaded_file_widget.name}_{uploaded_file_widget.size}"
        CROP_BOX_COLORS = {"白":"#FFFFFF", "赤":"#FF4500", "黄":"#FFD700", "シアン":"#00FFFF"}
        selected_cropper_color_hex = CROP_BOX_COLORS[st.session_state.cropper_box_color_name]
        
        # ★★★修正点: realtime_updateをFalseにして安定性を向上
        cropped_img = st_cropper(
            img_for_cropper, 
            realtime_update=False, 
            box_color=selected_cropper_color_hex, 
            aspect_ratio=None, 
            key=cropper_key
        )
        st.session_state.pil_image_to_process = cropped_img
    
    with col_options:
        with st.container(border=True):
            st.subheader("枠の色", divider="rainbow")
            st.radio(
                "トリミング枠の色を選択", 
                options=list(CROP_BOX_COLORS.keys()), 
                key="cropper_box_color_name", 
                label_visibility="collapsed"
            )
    
    # --- サイドバーのパラメータ設定UI ---
    st.sidebar.subheader("1. 輝点検出方法")
    detection_options = ("色で検出", "明るさで検出")
    detection_method = st.sidebar.radio(
        "検出方法を選択", 
        options=detection_options, 
        key="detection_method", 
        horizontal=True
    )
    st.sidebar.markdown("---")
    
    if detection_method == "明るさで検出":
        st.sidebar.subheader("2. 二値化")
        st.sidebar.slider(
            '閾値 (スライダーで調整)', 
            min_value=0, max_value=255, step=1, 
            key="threshold_slider", 
            on_change=sync_threshold_from_slider
        )
        st.sidebar.number_input(
            '（直接入力）', 
            min_value=0, max_value=255, step=1, 
            key="threshold_number", 
            on_change=sync_threshold_from_number, 
            label_visibility="collapsed"
        )
    else: # 色で検出
        st.sidebar.subheader("2. 色の範囲設定 (HSV)")
        st.sidebar.slider(
            "色相(H)の範囲", 0, 179, 
            key="hue_range_slider", 
            on_change=sync_hue_from_slider, 
            help="検出したい輝点の色のおおまかな範囲を指定します。\n\n**代表的な色の目安 (0-179):**\n- **赤:** 0-15 と 165-179\n- **黄:** 20-35\n- **緑:** 35-85\n- **青:** 100-130"
        )
        col_hue1, col_hue2 = st.sidebar.columns(2)
        col_hue1.number_input("下限", min_value=0, max_value=179, key="hue_min_number", on_change=sync_hue_from_number)
        col_hue2.number_input("上限", min_value=0, max_value=179, key="hue_max_number", on_change=sync_hue_from_number)

        st.sidebar.slider(
            "彩度(S)の下限", 
            min_value=0, max_value=255, 
            key="saturation_slider", 
            on_change=sync_saturation_from_slider
        )
        st.sidebar.number_input(
            "（直接入力）", 
            min_value=0, max_value=255, 
            key="saturation_number", 
            on_change=sync_saturation_from_number, 
            label_visibility="collapsed"
        )

        st.sidebar.slider(
            "明度(V)の下限", 
            min_value=0, max_value=255, 
            key="brightness_slider", 
            on_change=sync_brightness_from_slider
        )
        st.sidebar.number_input(
            "（直接入力）", 
            min_value=0, max_value=255, 
            key="brightness_number", 
            on_change=sync_brightness_from_number, 
            label_visibility="collapsed"
        )
        
    st.sidebar.subheader("3. 形態学的処理")
    kernel_size_morph_to_use = st.sidebar.select_slider(
        'カーネルサイズ',
        options=[1, 3, 5, 7, 9],
        value=1,
        help="ノイズ除去や輝点分離の効果の強さを調整します。"
    )
    st.sidebar.subheader("4. 輝点フィルタリング (面積)")
    min_area_to_use = st.sidebar.number_input('最小面積', min_value=1, max_value=10000, step=1, value=1)
    max_area_to_use = st.sidebar.number_input('最大面積', min_value=1, max_value=100000, step=1, key='max_area_to_use')
    
    st.sidebar.subheader("5. 表示設定")
    CONTOUR_COLORS = {"緑":"#28a745", "青":"#007bff", "赤":"#dc3545", "黄":"#ffc107", "シアン":"#17a2b8", "ピンク":"#e83e8c"}
    st.sidebar.radio(
        "輝点マーキング色を選択",
        options=list(CONTOUR_COLORS.keys()),
        key="contour_color_name",
        horizontal=True
    )
    contour_color_bgr = hex_to_bgr(CONTOUR_COLORS[st.session_state.contour_color_name])

    # --- メインエリアの画像処理と表示ロジック ---
    st.markdown("---")
    st.header("解析結果の比較")
    
    original_img_to_display_np_uint8 = None
    try:
        pil_image_rgb = st.session_state.pil_image_to_process.convert("RGB")
        original_img_to_display_np_uint8 = np.array(pil_image_rgb).astype(np.uint8)
    except Exception as e:
        st.error(f"トリミング後の画像の基本変換に失敗: {e}")
        st.stop()
    
    binary_img = None
    if detection_method == "明るさで検出":
        img_gray = cv2.cvtColor(original_img_to_display_np_uint8, cv2.COLOR_RGB2GRAY)
        blurred_img = cv2.GaussianBlur(img_gray, (1, 1), 0)
        _, binary_img = cv2.threshold(blurred_img, st.session_state.binary_threshold_value, 255, cv2.THRESH_BINARY)
    else: # 色で検出
        img_hsv = cv2.cvtColor(original_img_to_display_np_uint8, cv2.COLOR_RGB2HSV)
        hue_min, hue_max = st.session_state.hue_range_value
        sat_min = st.session_state.saturation_value
        val_min = st.session_state.brightness_value
        lower_range = np.array([hue_min, sat_min, val_min])
        upper_range = np.array([hue_max, 255, 255])
        binary_img = cv2.inRange(img_hsv, lower_range, upper_range)
    
    if binary_img is None:
        st.error("二値化処理に失敗しました。")
        st.stop()
    
    erosion_iterations = 1
    morph_kernel_shape_to_use = cv2.MORPH_ELLIPSE
    kernel_morph_obj = cv2.getStructuringElement(morph_kernel_shape_to_use, (kernel_size_morph_to_use, kernel_size_morph_to_use))
    opened_img = cv2.morphologyEx(binary_img, cv2.MORPH_OPEN, kernel_morph_obj, iterations=erosion_iterations)
    
    binary_img_for_contours = opened_img.copy()
    current_counted_spots = 0 
    output_image_contours_display = cv2.cvtColor(original_img_to_display_np_uint8, cv2.COLOR_RGB2BGR) 
    
    contours, _ = cv2.findContours(binary_img_for_contours, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
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
        display_final_marked_image_rgb = cv2.cvtColor(output_image_contours_display, cv2.COLOR_BGR2RGB)
        st.image(display_final_marked_image_rgb, caption=f'検出輝点({current_counted_spots}個)', use_container_width=True)
    
    with st.expander("▼ 中間処理の画像を見る"):
        st.subheader(f"1. {detection_method}による二値化処理後")
        st.image(binary_img)
        st.subheader("2. 形態学的処理後")
        st.image(opened_img, caption=f'カーネル: 楕円 {kernel_size_morph_to_use}x{kernel_size_morph_to_use} {erosion_iterations}回')

else: 
    st.info("まず、サイドバーから画像ファイルをアップロードしてください。")

display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value)
