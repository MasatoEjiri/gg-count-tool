import streamlit as st
from PIL import Image
import numpy as np
import cv2
import io
from streamlit_cropper import st_cropper

# ページ設定 (一番最初に呼び出す)
st.set_page_config(page_title="GG輝点解析ツール", layout="wide", initial_sidebar_state="expanded")

# メイン画面上部の余白を調整
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


# --- セッションステートの初期化 ---
# 初回起動時にデフォルト値を設定
defaults = {
    'current_file_id': None,
    'counted_spots_value': "---",
    'binary_threshold_value': 15,
    'saturation_value': 200,
    'brightness_value': 60,
    'hue_range_value': (0, 25),
    'pil_image_original': None,
    'pil_image_to_process': None,
    'contour_color_name': "青",
    'cropper_box_color_name': "白",
    'detection_method': "色で検出",
    'max_area_to_use': 100,
    'min_area_to_use': 1,
    'kernel_size_morph': 1,
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# スライダーと数値入力を同期させるためのキーも初期化
if "threshold_slider" not in st.session_state: st.session_state.threshold_slider = st.session_state.binary_threshold_value
if "threshold_number" not in st.session_state: st.session_state.threshold_number = st.session_state.binary_threshold_value
if "saturation_slider" not in st.session_state: st.session_state.saturation_slider = st.session_state.saturation_value
if "saturation_number" not in st.session_state: st.session_state.saturation_number = st.session_state.saturation_value
if "brightness_slider" not in st.session_state: st.session_state.brightness_slider = st.session_state.brightness_value
if "brightness_number" not in st.session_state: st.session_state.brightness_number = st.session_state.brightness_value
if "hue_range_slider" not in st.session_state: st.session_state.hue_range_slider = st.session_state.hue_range_value
if "hue_min_number" not in st.session_state: st.session_state.hue_min_number = st.session_state.hue_range_value[0]
if "hue_max_number" not in st.session_state: st.session_state.hue_max_number = st.session_state.hue_range_value[1]


# --- コールバック関数 (st.rerun()は含めない) ---
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


# --- UI ---
result_placeholder_sidebar = st.sidebar.empty()
st.sidebar.header("解析パラメータ設定")
uploaded_file = st.sidebar.file_uploader("画像をアップロード", type=['tif', 'tiff', 'png', 'jpg', 'jpeg'])

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
if uploaded_file:
    file_id = f"{uploaded_file.name}-{uploaded_file.size}"
    if st.session_state.current_file_id != file_id:
        st.session_state.current_file_id = file_id
        try:
            bytes_data = uploaded_file.getvalue()
            st.session_state.pil_image_original = Image.open(io.BytesIO(bytes_data))
        except Exception as e:
            st.sidebar.error(f"画像の読み込みに失敗: {e}")
            st.session_state.pil_image_original = None
else:
    st.session_state.pil_image_original = None
    st.session_state.current_file_id = None


# --- メイン処理 ---
if st.session_state.pil_image_original:
    # --- サイドバーUI ---
    st.sidebar.subheader("1. 輝点検出方法")
    st.session_state.detection_method = st.sidebar.radio(
        "検出方法", ("色で検出", "明るさで検出"), index=["色で検出", "明るさで検出"].index(st.session_state.detection_method), horizontal=True
    )
    st.sidebar.markdown("---")

    if st.session_state.detection_method == "明るさで検出":
        st.sidebar.subheader("2. 二値化")
        st.sidebar.slider('閾値 (スライダーで調整)', key="threshold_slider", min_value=0, max_value=255, on_change=sync_threshold_from_slider)
        st.sidebar.number_input('（直接入力）', key="threshold_number", min_value=0, max_value=255, on_change=sync_threshold_from_number, label_visibility="collapsed")
    else:
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
            key="saturation_slider",
            min_value=0, max_value=255,
            on_change=sync_saturation_from_slider,
            help="色の鮮やかさの最小値を指定します。値を大きくすると、より鮮やかな色のみが検出されます。"
        )
        st.sidebar.number_input("（直接入力）", key="saturation_number", min_value=0, max_value=255, on_change=sync_saturation_from_number, label_visibility="collapsed")

        st.sidebar.slider(
            "明度(V)の下限",
            key="brightness_slider",
            min_value=0, max_value=255,
            on_change=sync_brightness_from_slider,
            help="色の明るさの最小値を指定します。値を大きくすると、より明るい色のみが検出されます。"
        )
        st.sidebar.number_input("（直接入力）", key="brightness_number", min_value=0, max_value=255, on_change=sync_brightness_from_number, label_visibility="collapsed")

    st.sidebar.subheader("3. 形態学的処理")
    st.session_state.kernel_size_morph = st.sidebar.select_slider('カーネルサイズ', options=[1, 3, 5, 7, 9], value=st.session_state.kernel_size_morph, help="ノイズ除去や輝点分離の効果の強さを調整します。")

    st.sidebar.subheader("4. 輝点フィルタリング (面積)")
    st.session_state.min_area_to_use = st.sidebar.number_input('最小面積', 1, 10000, st.session_state.min_area_to_use)
    st.session_state.max_area_to_use = st.sidebar.number_input('最大面積', 1, 100000, st.session_state.max_area_to_use)

    st.sidebar.subheader("5. 表示設定")
    CONTOUR_COLORS = {"緑":"#28a745", "青":"#007bff", "赤":"#dc3545", "黄":"#ffc107", "シアン":"#17a2b8", "ピンク":"#e83e8c"}
    st.session_state.contour_color_name = st.sidebar.radio(
        "輝点マーキング色", list(CONTOUR_COLORS.keys()), index=list(CONTOUR_COLORS.keys()).index(st.session_state.contour_color_name), horizontal=True
    )
    contour_color_bgr = hex_to_bgr(CONTOUR_COLORS[st.session_state.contour_color_name])

    # --- メインエリアUI ---
    st.header("解析エリアの選択 (トリミング)")
    col_cropper, col_options = st.columns([3, 1])
    with col_cropper:
        img_for_cropper = st.session_state.pil_image_original.copy()
        st.session_state.pil_image_to_process = st_cropper(
            img_for_cropper,
            realtime_update=True,
            box_color='#007BFF',
            aspect_ratio=None,
            key=f"cropper_{st.session_state.current_file_id}"
        )

    with col_options:
        with st.container(border=True):
            st.subheader("枠の色", divider="rainbow")
            CROP_BOX_COLORS = {"白":"#FFFFFF", "赤":"#FF4500", "黄":"#FFD700", "シアン":"#00FFFF"}
            st.session_state.cropper_box_color_name = st.radio(
                "トリミング枠の色を選択",
                options=list(CROP_BOX_COLORS.keys()),
                index=list(CROP_BOX_COLORS.keys()).index(st.session_state.cropper_box_color_name),
                label_visibility="collapsed"
            )

    st.markdown("---")
    st.header("解析結果の比較")

    # --- 画像処理 ---
    try:
        pil_image_rgb = st.session_state.pil_image_to_process.convert("RGB")
        img_np = np.array(pil_image_rgb)
    except Exception as e:
        st.error(f"トリミング画像の変換に失敗: {e}")
        st.stop()

    if st.session_state.detection_method == "明るさで検出":
        img_gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        _, binary_img = cv2.threshold(img_gray, st.session_state.binary_threshold_value, 255, cv2.THRESH_BINARY)
    else:
        img_hsv = cv2.cvtColor(img_np, cv2.COLOR_RGB2HSV)
        lower = np.array([st.session_state.hue_range_value[0], st.session_state.saturation_value, st.session_state.brightness_value])
        upper = np.array([st.session_state.hue_range_value[1], 255, 255])
        binary_img = cv2.inRange(img_hsv, lower, upper)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (st.session_state.kernel_size_morph, st.session_state.kernel_size_morph))
    opened_img = cv2.morphologyEx(binary_img, cv2.MORPH_OPEN, kernel, iterations=1)

    contours, _ = cv2.findContours(opened_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    count = 0
    output_image = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
    for c in contours:
        area = cv2.contourArea(c)
        if st.session_state.min_area_to_use <= area <= st.session_state.max_area_to_use:
            count += 1
            cv2.drawContours(output_image, [c], -1, contour_color_bgr, 2)
    st.session_state.counted_spots_value = count

    # --- 結果表示 ---
    col1, col2 = st.columns(2)
    col1.subheader("元の画像 (トリミング後)")
    col1.image(img_np, use_container_width=True)
    col2.subheader("輝点検出とマーキング")
    col2.image(cv2.cvtColor(output_image, cv2.COLOR_BGR2RGB), caption=f'検出輝点({count}個)', use_container_width=True)

else:
    st.info("まず、サイドバーから画像ファイルをアップロードしてください。")
    st.session_state.counted_spots_value = "---"

display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value)
