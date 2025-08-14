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

# --- UI ---
st.sidebar.header("解析パラメータ設定")
uploaded_file = st.sidebar.file_uploader("画像をアップロード", type=['tif', 'tiff', 'png', 'jpg', 'jpeg'])

st.markdown('<h1 style="font-size: 2.5rem; margin-top: 0;">GG輝点解析ツール</h1>', unsafe_allow_html=True)

# --- 画像読み込み ---
if uploaded_file:
    file_id = f"{uploaded_file.name}-{uploaded_file.size}"
    if st.session_state.get('current_file_id') != file_id:
        # 新しいファイルがアップロードされたら、全てのセッションステートをデフォルトに戻す
        for key in st.session_state.keys():
            del st.session_state[key]
        ensure_state_consistency()
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
        st.
