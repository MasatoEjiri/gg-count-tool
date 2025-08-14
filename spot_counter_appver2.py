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
    .color-checkbox-container {
        display: flex; align-items: center; padding: 5px 8px;
        border-radius: 5px; margin-bottom: 8px; border: 1px solid #555;
        background-color: #444;
    }
    .color-label { display: flex; align-items: center; }
    .color-box { width: 18px; height: 18px; margin-right: 8px; border: 1px solid #fff; }
</style>
""", unsafe_allow_html=True)

# --- 定数定義 ---
HUE_PRESETS = {
    "赤": {"range": ((0, 10), (160, 179)), "color": "#FF4B4B"},
    "黄": {"range": (20, 35), "color": "#FFD700"},
    "緑": {"range": (35, 85), "color": "#28a745"},
    "青": {"range": (100, 130), "color": "#007bff"},
}
CONTOUR_COLORS = {"青":"#007bff", "緑":"#28a745", "赤":"#dc3545", "黄":"#ffc107"}

# ★★★★★ 修正点: 堅牢なセッションステート管理 ★★★★★
# 1. 正しいデフォルト値を返す関数
def get_default_params():
    return {
        'binary_threshold': 15, 'saturation': 200, 'brightness': 60,
        'selected_hue_names': ["赤"], 'contour_color': "青",
        'detection_method': "色で検出", 'max_area': 10000, 'min_area': 1, 'kernel_size': 1,
        'use_image_enhancement': False, 'use_cropper': False, # デフォルトはOFF
        'saturation_slider': 200, 'saturation_number': 200,
        'brightness_slider': 60, 'brightness_number': 60,
        'binary_threshold_slider': 15, 'binary_threshold_number': 15,
        'state_initialized': True # 正常な状態の証
    }

# 2. セッションが正常かチェックし、異常なら強制的にリセットする関数
def ensure_state_consistency():
    if not st.session_state.get('state_initialized'):
        # 破損した可能性のあるキーを一度すべてクリア
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        # 正しいデフォルト値で再初期化
        for key, value in get_default_params().items():
            st.session_state[key] = value

# アプリ実行時に必ずチェック
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

# --- UI ---
st.sidebar.header("解析パラメータ設定")
uploaded_file = st.sidebar.file_uploader("画像をアップロード", type=['tif', 'tiff', 'png', 'jpg', 'jpeg'])

st.markdown('<h1 style="font-size: 2.5rem; margin-top: 0;">GG輝点解析ツール</h1>', unsafe_allow_html=True)

# --- 画像読み込み ---
if uploaded_file:
    if st.session_state.get('current_file_id') != uploaded_file.id:
        st.session_state.pil_image_original = Image.open(io.BytesIO(uploaded_file.getvalue()))
        st.session_state.current_file_id = uploaded_file.id
else:
    st.session_state.pil_image_original = None

# --- メイン処理 ---
if st.session_state.pil_image_original:
    # --- サイドバーUI ---
    st.sidebar.checkbox("トリミング機能を使用する", key='use_cropper')
    st.sidebar.radio("検出方法", ("色で検出", "明るさで検出"), key='detection_method', horizontal=True)
    st.sidebar.markdown("---")

    if st.session_state.detection_method == "明るさで検出":
        st.sidebar.subheader("二値化")
        st.sidebar.slider('閾値', 0, 255, key='binary_threshold_slider', on_change=sync_from_slider, args=('binary_threshold',))
        st.sidebar.number_input('（値）', 0, 255, key='binary_threshold_number', on_change=sync_from_number, args=('binary_threshold',), label_visibility="collapsed")
    else:
        st.sidebar.subheader("色の範囲設定 (HSV)")
        st.sidebar.write("**輝点の色** (複数選択可)")
        cols = st.sidebar.columns(2)
        current_selections = []
        for i, (color_name, props) in enumerate(HUE_PRESETS.items()):
            col = cols[i % 2]
            with col.container():
                c1, c2 = st.columns([0.8, 0.2])
                c1.markdown(f'<div class="color-checkbox-container"><div class="color-label"><div class="color-box" style="background-color: {props["color"]};"></div><span>{color_name}</span></div></div>', unsafe_allow_html=True)
                if c2.checkbox("", value=(color_name in st.session_state.selected_hue_names), key=f"cb_{color_name}", label_visibility="collapsed"):
                    current_selections.append(color_name)
        st.session_state.selected_hue_names = current_selections
        st.sidebar.slider("彩度(S)の下限", 0, 255, key='saturation_slider', on_change=sync_from_slider, args=('saturation',), help="色の鮮やかさの最小値")
        st.sidebar.number_input('（値）', 0, 255, key='saturation_number', on_change=sync_from_number, args=('saturation',), label_visibility="collapsed")
        st.sidebar.slider("明度(V)の下限", 0, 255, key='brightness_slider', on_change=sync_from_slider, args=('brightness',), help="色の明るさの最小値")
        st.sidebar.number_input('（値）', 0, 255, key='brightness_number', on_change=sync_from_number, args=('brightness',), label_visibility="collapsed")

    st.sidebar.subheader("前処理")
    st.sidebar.checkbox("画質を最適化", key='use_image_enhancement', help="ガンマ補正・鮮明化・明るさの向上")
    st.sidebar.subheader("形態学的処理")
    st.sidebar.select_slider('カーネルサイズ', options=[1, 3, 5, 7, 9], key='kernel_size', help="ノイズ除去/輝点分離")
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
        result_container = st.container()

    # --- 画像処理と結果表示 ---
    with result_container:
        if st.session_state.use_cropper: # トリミング時のみサブヘッダー表示
            st.subheader("輝点検出とマーキング")
            
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

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (st.session_state.kernel_size, st.session_state.kernel_size))
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
