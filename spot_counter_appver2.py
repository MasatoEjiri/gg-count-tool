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
# 新しい画像がアップロードされたことを検知するためのID
if 'current_file_id' not in st.session_state: st.session_state.current_file_id = None

# 各種パラメータの初期化
if 'counted_spots_value' not in st.session_state: st.session_state.counted_spots_value = "---"
if "binary_threshold_value" not in st.session_state: st.session_state.binary_threshold_value = 15
if "saturation_value" not in st.session_state: st.session_state.saturation_value = 200
if "brightness_value" not in st.session_state: st.session_state.brightness_value = 60
if "hue_range_value" not in st.session_state: st.session_state.hue_range_value = (0, 25)
if 'pil_image_original' not in st.session_state: st.session_state.pil_image_original = None
if 'pil_image_to_process' not in st.session_state: st.session_state.pil_image_to_process = None
if 'contour_color_name' not in st.session_state: st.session_state.contour_color_name = "青"
if 'cropper_box_color_name' not in st.session_state: st.session_state.cropper_box_color_name = '白'
if 'detection_method' not in st.session_state: st.session_state.detection_method = "色で検出"
if 'max_area_to_use' not in st.session_state: st.session_state.max_area_to_use = 100
if 'kernel_size_morph' not in st.session_state: st.session_state.kernel_size_morph = 1
if 'min_area_to_use' not in st.session_state: st.session_state.min_area_to_use = 1


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
st.markdown("""
### 使用方法
1.  画像を左にアップロードしてください。
2.  メイン画面で解析したいエリアをトリミングします。
3.  サイドバーの各パラメータを調整します。
4.  すべての操作は解析結果に即時反映されます。
""")
st.markdown("---")

# --- 画像読み込みロジック ---
if uploaded_file_widget is not None:
    # 以前と違うファイルがアップロードされた場合のみ画像を読み込む
    if st.session_state.current_file_id != uploaded_file_widget.id:
        st.session_state.current_file_id = uploaded_file_widget.id
        try:
            uploaded_file_bytes = uploaded_file_widget.getvalue()
            st.session_state.pil_image_original = Image.open(io.BytesIO(uploaded_file_bytes))
        except Exception as e:
            st.sidebar.error(f"画像の読み込みに失敗: {e}")
            st.session_state.pil_image_original = None
else:
    st.session_state.pil_image_original = None
    st.session_state.current_file_id = None


# --- メイン処理 ---
if st.session_state.pil_image_original is not None:
    # --- サイドバーのパラメータ設定UI (コールバックを使わず、直接セッションステートに書き込む) ---
    st.sidebar.subheader("1. 輝点検出方法")
    st.session_state.detection_method = st.sidebar.radio("検出方法", ("色で検出", "明るさで検出"), key="detection_method_radio", horizontal=True)
    st.sidebar.markdown("---")
    
    if st.session_state.detection_method == "明るさで検出":
        st.sidebar.subheader("2. 二値化")
        st.session_state.binary_threshold_value = st.sidebar.slider('閾値', 0, 255, st.session_state.binary_threshold_value)
    else: # 色で検出
        st.sidebar.subheader("2. 色の範囲設定 (HSV)")
        st.session_state.hue_range_value = st.sidebar.slider("色相(H)の範囲", 0, 179, st.session_state.hue_range_value)
        st.session_state.saturation_value = st.sidebar.slider("彩度(S)の下限", 0, 255, st.session_state.saturation_value)
        st.session_state.brightness_value = st.sidebar.slider("明度(V)の下限", 0, 255, st.session_state.brightness_value)
        
    st.sidebar.subheader("3. 形態学的処理")
    st.session_state.kernel_size_morph = st.sidebar.select_slider('カーネルサイズ', options=[1, 3, 5, 7, 9], value=st.session_state.kernel_size_morph)
    
    st.sidebar.subheader("4. 輝点フィルタリング (面積)")
    st.session_state.min_area_to_use = st.sidebar.number_input('最小面積', 1, 10000, st.session_state.min_area_to_use)
    st.session_state.max_area_to_use = st.sidebar.number_input('最大面積', 1, 100000, st.session_state.max_area_to_use)
    
    st.sidebar.subheader("5. 表示設定")
    CONTOUR_COLORS = {"緑":"#28a745", "青":"#007bff", "赤":"#dc3545", "黄":"#ffc107", "シアン":"#17a2b8", "ピンク":"#e83e8c"}
    st.session_state.contour_color_name = st.sidebar.radio("輝点マーキング色", list(CONTOUR_COLORS.keys()), key="contour_color_radio", horizontal=True)
    contour_color_bgr = hex_to_bgr(CONTOUR_COLORS[st.session_state.contour_color_name])

    # --- メインエリアのトリミングUI ---
    st.header("解析エリアの選択 (トリミング)")
    col_cropper, col_options = st.columns([3, 1])
    
    with col_cropper:
        img_for_cropper = st.session_state.pil_image_original.copy()
        CROPPER_MAX_DIM = 700
        if img_for_cropper.width > CROPPER_MAX_DIM or img_for_cropper.height > CROPPER_MAX_DIM:
            img_for_cropper.thumbnail((CROPPER_MAX_DIM, CROPPER_MAX_DIM))
        
        # ★★★ 修正点: realtime_update=True に戻し、即時反映を実現 ★★★
        st.session_state.pil_image_to_process = st_cropper(
            img_for_cropper, 
            realtime_update=True, 
            box_color='#007BFF', 
            aspect_ratio=None,
            key=f"cropper_{st.session_state.current_file_id}" # ファイルごとにユニークなキー
        )
    
    with col_options:
        with st.container(border=True):
            st.subheader("枠の色", divider="rainbow")
            st.session_state.cropper_box_color_name = st.radio("色を選択", list(CROP_BOX_COLORS.keys()), key="cropper_color_radio", label_visibility="collapsed")
    
    # --- メインエリアの画像処理と表示ロジック ---
    st.markdown("---")
    st.header("解析結果の比較")
    
    try:
        pil_image_rgb = st.session_state.pil_image_to_process.convert("RGB")
        original_img_to_display_np_uint8 = np.array(pil_image_rgb).astype(np.uint8)
    except Exception as e:
        st.error(f"トリミング画像の変換に失敗: {e}")
        st.stop()
    
    binary_img = None
    if st.session_state.detection_method == "明るさで検出":
        img_gray = cv2.cvtColor(original_img_to_display_np_uint8, cv2.COLOR_RGB2GRAY)
        blurred_img = cv2.GaussianBlur(img_gray, (1, 1), 0)
        _, binary_img = cv2.threshold(blurred_img, st.session_state.binary_threshold_value, 255, cv2.THRESH_BINARY)
    else: # 色で検出
        img_hsv = cv2.cvtColor(original_img_to_display_np_uint8, cv2.COLOR_RGB2HSV)
        hue_min, hue_max = st.session_state.hue_range_value
        lower = np.array([hue_min, st.session_state.saturation_value, st.session_state.brightness_value])
        upper = np.array([hue_max, 255, 255])
        binary_img = cv2.inRange(img_hsv, lower, upper)
    
    if binary_img is not None:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (st.session_state.kernel_size_morph, st.session_state.kernel_size_morph))
        opened_img = cv2.morphologyEx(binary_img, cv2.MORPH_OPEN, kernel, iterations=1)
        contours, _ = cv2.findContours(opened_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        current_counted_spots = 0 
        output_image = cv2.cvtColor(original_img_to_display_np_uint8, cv2.COLOR_RGB2BGR) 
        
        if contours: 
            for c in contours:
                area = cv2.contourArea(c)
                if st.session_state.min_area_to_use <= area <= st.session_state.max_area_to_use:
                    current_counted_spots += 1
                    cv2.drawContours(output_image, [c], -1, contour_color_bgr, 2) 
        
        st.session_state.counted_spots_value = current_counted_spots 
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("元の画像 (トリミング後)")
            st.image(original_img_to_display_np_uint8, use_container_width=True)
        with col2:
            st.subheader("輝点検出とマーキング")
            st.image(cv2.cvtColor(output_image, cv2.COLOR_BGR2RGB), caption=f'検出輝点({current_counted_spots}個)', use_container_width=True)
    else:
        st.error("二値化処理に失敗しました。")

else: 
    st.info("まず、サイドバーから画像ファイルをアップロードしてください。")
    st.session_state.counted_spots_value = "---"

display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value)
