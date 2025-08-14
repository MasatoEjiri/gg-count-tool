import streamlit as st
from PIL import Image
import numpy as np
import cv2
import io
from streamlit_cropper import st_cropper

# ページ設定
st.set_page_config(page_title="GG輝点解析ツール", layout="wide", initial_sidebar_state="expanded")

# --- カスタムCSS ---
st.markdown("""
<style>
    .main .block-container { padding-top: 1rem !important; }
    h1 { margin-top: 0px !important; padding-top: 0px !important; }
    section[data-testid="stFileUploaderDropzone"] {
        border: 3px dotted white !important;
        border-radius: 0.5rem !important;
        background-color: #495057 !important;
    }
    div[data-testid="stHorizontalBlock"] > div[style*="flex-direction: row;"] {
        align-items: center;
    }
    
    /* サイドバーを折りたたむボタンを非表示にする */
    button[data-testid="stSidebarCollapseButton"] {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

# --- 定数定義 ---
HUE_PRESETS = {
    "赤": {"range": ((0, 10), (160, 179))},
    "黄": {"range": (20, 35)},
    "緑": {"range": (35, 85)},
    "青": {"range": (100, 130)},
}
CONTOUR_COLORS = {"青":"#007bff", "緑":"#28a745", "赤":"#dc3545", "黄":"#ffc107"}

# --- セッションステート管理 ---
def get_default_params():
    return {
        'binary_threshold': 15, 'saturation': 90, 'brightness': 90,
        'selected_hue_names': ["赤"], 'contour_color': "青",
        'detection_method': "色で検出（オススメ）", 'max_area': 10000, 'min_area': 1,
        'use_image_enhancement': True, 'use_cropper': False,
        'saturation_slider': 90, 'saturation_number': 90,
        'brightness_slider': 90, 'brightness_number': 90,
        'binary_threshold_slider': 15, 'binary_threshold_number': 15,
        'state_initialized': True
    }

def ensure_state_consistency():
    if not st.session_state.get('state_initialized'):
        for key, value in get_default_params().items():
            st.session_state[key] = value

ensure_state_consistency()

# --- 関数定義 ---
def hex_to_bgr(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (4, 2, 0))

def adjust_gamma(image, gamma=1.0):
    invGamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** invGamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
    return cv2.LUT(image, table)

def sync_from_slider(param):
    st.session_state[param] = st.session_state[f"{param}_slider"]
    st.session_state[f"{param}_number"] = st.session_state[f"{param}_slider"]

def sync_from_number(param):
    st.session_state[param] = st.session_state[f"{param}_number"]
    st.session_state[f"{param}_slider"] = st.session_state[f"{param}_number"]

# ▼▼▼【UI改善】色選択のフォーマット関数を定義 ▼▼▼
def format_color_option(option_name):
    """multiselectの選択肢に絵文字を追加する"""
    color_emoji_map = {"赤": "🔴", "黄": "🟡", "緑": "🟢", "青": "🔵"}
    return f"{color_emoji_map.get(option_name, '⚫')} {option_name}"
# ▲▲▲ UI改善ここまで ▲▲▲

# --- UI ---
st.sidebar.header("解析パラメータ設定")
uploaded_file = st.sidebar.file_uploader("画像をアップロード", type=['tif', 'tiff', 'png', 'jpg', 'jpeg'])

st.markdown('<h1 style="font-size: 2.5rem; margin-top: 0;">GG輝点解析ツール</h1>', unsafe_allow_html=True)

# --- 画像読み込み ---
if uploaded_file:
    file_id = f"{uploaded_file.name}-{uploaded_file.size}"
    if st.session_state.get('current_file_id') != file_id:
        for key, value in get_default_params().items():
            st.session_state[key] = value
        st.session_state.pil_image_original = Image.open(io.BytesIO(uploaded_file.getvalue()))
        st.session_state.current_file_id = file_id
else:
    st.session_state.pil_image_original = None

# --- メイン処理 ---
if st.session_state.pil_image_original:
    # --- サイドバーUI ---
    st.sidebar.checkbox("トリミング機能を使用する", key='use_cropper')
    st.sidebar.radio("検出方法", ("色で検出（オススメ）", "明るさで検出"), key='detection_method', horizontal=True)
    st.sidebar.markdown("---")

    if st.session_state.detection_method == "明るさで検出":
        st.sidebar.subheader("二値化")
        st.sidebar.slider('閾値', 0, 255, key='binary_threshold_slider', on_change=sync_from_slider, args=('binary_threshold',))
        st.sidebar.number_input('（値）', 0, 255, key='binary_threshold_number', on_change=sync_from_number, args=('binary_threshold',), label_visibility="collapsed")
    else:
        st.sidebar.subheader("色の範囲設定 (HSV)")
        
        # ▼▼▼【UI改善 & バグ修正】st.multiselectにkeyとformat_funcを追加 ▼▼▼
        st.sidebar.multiselect(
            label="輝点の色 (複数選択可)",
            options=list(HUE_PRESETS.keys()),
            help="解析したい輝点の色をリストから選択します。",
            key='selected_hue_names', # バグ修正：stateを正しく管理するためのキー
            format_func=format_color_option # UI改善：選択肢に絵文字を追加
        )
        # ▲▲▲ 修正ここまで ▲▲▲

        st.sidebar.slider("彩度(S)の下限", 0, 255, key='saturation_slider', on_change=sync_from_slider, args=('saturation',), help="色の鮮やかさの最小値")
        st.sidebar.number_input('（値）', 0, 255, key='saturation_number', on_change=sync_from_number, args=('saturation',), label_visibility="collapsed")
        st.sidebar.slider("明度(V)の下限", 0, 255, key='brightness_slider', on_change=sync_from_slider, args=('brightness',), help="色の明るさの最小値")
        st.sidebar.number_input('（値）', 0, 255, key='brightness_number', on_change=sync_from_number, args=('brightness',), label_visibility="collapsed")

    st.sidebar.subheader("前処理")
    st.sidebar.checkbox("画質を最適化", key='use_image_enhancement', help="ガンマ補正・鮮明化・明るさの向上")
    st.sidebar.subheader("輝点フィルタリング (面積)")
    st.sidebar.number_input('最小面積', 1, 10000, key='min_area')
    st.sidebar.number_input('最大面積', 1, 100000, key='max_area')
    st.sidebar.subheader("表示設定")
    st.sidebar.radio("輝点マーキング色", list(CONTOUR_COLORS.keys()), key='contour_color', horizontal=True)
    contour_color_bgr = hex_to_bgr(CONTOUR_COLORS[st.session_state.contour_color])

    # --- レイアウトと画像の前処理 ---
    pil_image_to_process = None
    if st.session_state.use_cropper:
        col1, col2 = st.columns([2, 3])
        with col1:
            st.subheader("解析エリアの選択")
            img_original_for_cropper = st.session_state.pil_image_original.copy()
            display_width = 400
            scaling_factor = 1.0
            if img_original_for_cropper.width > display_width:
                scaling_factor = img_original_for_cropper.width / display_width
                new_height = int(img_original_for_cropper.height / scaling_factor)
                img_for_display = img_original_for_cropper.resize((display_width, new_height), Image.Resampling.LANCZOS)
            else:
                img_for_display = img_original_for_cropper
            box = st_cropper(img_for_display, realtime_update=True, box_color='#007BFF', return_type='box', key=f"cropper_{st.session_state.current_file_id}")
            left, top = int(box['left'] * scaling_factor), int(box['top'] * scaling_factor)
            right, bottom = int((box['left'] + box['width']) * scaling_factor), int((box['top'] + box['height']) * scaling_factor)
            pil_image_to_process = st.session_state.pil_image_original.crop((left, top, right, bottom))
        result_container = col2
    else:
        pil_image_to_process = st.session_state.pil_image_original
        _, result_container, _ = st.columns([0.5, 3, 0.5])

    # --- 画像処理と結果表示 ---
    with result_container:
        if st.session_state.use_cropper:
            st.subheader("輝点検出とマーキング")
        else:
            st.subheader("輝点検出結果")
            
        img_np = np.array(pil_image_to_process.convert("RGB"))
        img_to_analyze = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        
        if st.session_state.use_image_enhancement:
            img_gamma = adjust_gamma(img_to_analyze, gamma=0.5)
            blurred = cv2.GaussianBlur(img_gamma, (0, 0), 3)
            img_sharpened = cv2.addWeighted(img_gamma, 1.5, blurred, -0.5, 0)
            img_to_analyze = cv2.convertScaleAbs(img_sharpened, alpha=1.0, beta=10)
        
        img_to_analyze_rgb = cv2.cvtColor(img_to_analyze, cv2.COLOR_BGR2RGB)
        
        if st.session_state.detection_method == "明るさで検出":
            img_gray = cv2.cvtColor(img_to_analyze_rgb, cv2.COLOR_RGB2GRAY)
            _, binary_img = cv2.threshold(img_gray, st.session_state.binary_threshold, 255, cv2.THRESH_BINARY)
        else:
            img_hsv = cv2.cvtColor(img_to_analyze_rgb, cv2.COLOR_RGB2HSV)
            sat, val = st.session_state.saturation, st.session_state.brightness
            final_mask = np.zeros(img_hsv.shape[:2], dtype=np.uint8)
            if st.session_state.selected_hue_names:
                for color_name in st.session_state.selected_hue_names:
                    hue_data = HUE_PRESETS[color_name]["range"]
                    if isinstance(hue_data[0], tuple):
                        mask1 = cv2.inRange(img_hsv, np.array([hue_data[0][0], sat, val]), np.array([hue_data[0][1], 255, 255]))
                        mask2 = cv2.inRange(img_hsv, np.array([hue_data[1][0], sat, val]), np.array([hue_data[1][1], 255, 255]))
                        final_mask = cv2.bitwise_or(final_mask, cv2.bitwise_or(mask1, mask2))
                    else:
                        mask = cv2.inRange(img_hsv, np.array([hue_data[0], sat, val]), np.array([hue_data[1], 255, 255]))
                        final_mask = cv2.bitwise_or(final_mask, mask)
            binary_img = final_mask

        # 形態学的処理は内部で固定
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (1, 1))
        opened_img = cv2.morphologyEx(binary_img, cv2.MORPH_OPEN, kernel, iterations=1)
        contours, _ = cv2.findContours(opened_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        count = 0
        output_image = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        for c in contours:
            if st.session_state.min_area <= cv2.contourArea(c) <= st.session_state.max_area:
                count += 1
                cv2.drawContours(output_image, [c], -1, contour_color_bgr, 2)
        st.image(cv2.cvtColor(output_image, cv2.COLOR_BGR2RGB), use_container_width=True)
        st.markdown(f"""<div style="text-align: center; background-image: linear-gradient(45deg, #007bff, #E83E8C); padding: 10px; border-radius: 10px; color: white; font-size: 20px; font-weight: bold; margin-top: 10px;">検出輝点: {count}個</div>""", unsafe_allow_html=True)
    
        st.markdown("---")
        st.subheader("元の画像 " + ("(前処理後)" if st.session_state.use_image_enhancement else "(トリミング後)"))
        st.image(img_to_analyze_rgb if st.session_state.use_image_enhancement else img_np, use_container_width=True)
else:
    st.info("まず、サイドバーから画像ファイルをアップロードしてください。")
