import streamlit as st
from PIL import Image
import numpy as np
import cv2
import io
from streamlit_cropper import st_cropper

# ページ設定 (一番最初に呼び出す)
st.set_page_config(page_title="GG輝点解析ツール", layout="wide", initial_sidebar_state="expanded")

# --- カスタムCSS ---
st.markdown("""
<style>
    .main .block-container { padding-top: 1rem !important; }
    h1 {
        margin-top: 0px !important;
        padding-top: 0px !important;
    }
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


# --- セッションステートの初期化 ---
def initialize_session_state():
    defaults = {
        'binary_threshold': 15, 'saturation': 200, 'brightness': 60,
        'selected_hue_names': ["赤"], 'contour_color': "青",
        'detection_method': "色で検出", 'max_area': 10000,
        'min_area': 1, 'kernel_size': 1,
        'use_contrast': False # ★コントラスト処理のON/OFF
    }
    for key, value in defaults.items():
        st.session_state[key] = value

    # ウィジェット連携用のキーも初期化
    st.session_state.saturation_slider = st.session_state.saturation
    st.session_state.saturation_number = st.session_state.saturation
    st.session_state.brightness_slider = st.session_state.brightness
    st.session_state.brightness_number = st.session_state.brightness

def hex_to_bgr(hex_color):
    hex_color = hex_color.lstrip('#')
    h_len = len(hex_color)
    return tuple(int(hex_color[i:i + h_len // 3], 16) for i in range(0, h_len, h_len // 3))[::-1]

def sync_saturation_from_slider():
    st.session_state.saturation = st.session_state.saturation_slider
    st.session_state.saturation_number = st.session_state.saturation_slider

def sync_saturation_from_number():
    st.session_state.saturation = st.session_state.saturation_number
    st.session_state.saturation_slider = st.session_state.saturation_number

def sync_brightness_from_slider():
    st.session_state.brightness = st.session_state.brightness_slider
    st.session_state.brightness_number = st.session_state.brightness_slider

def sync_brightness_from_number():
    st.session_state.brightness = st.session_state.brightness_number
    st.session_state.brightness_slider = st.session_state.brightness_number


# --- UI ---
st.sidebar.header("解析パラメータ設定")
uploaded_file = st.sidebar.file_uploader("画像をアップロード", type=['tif', 'tiff', 'png', 'jpg', 'jpeg'])

st.markdown('<h1 style="font-size: 2.5rem; margin-top: 0;">GG輝点解析ツール</h1>', unsafe_allow_html=True)
st.markdown("""
### 使用方法
1.  画像を左にアップロードしてください。（新しい画像をアップするとパラメータは初期化されます）
2.  左の画像上で解析したいエリアをトリミングします。
3.  サイドバーの各パラメータを調整すると、右の結果がリアルタイムで更新されます。
""")
st.markdown("---")

# --- 画像読み込みロジック ---
if uploaded_file:
    file_id = f"{uploaded_file.name}-{uploaded_file.size}"
    if st.session_state.get('current_file_id') != file_id:
        initialize_session_state()
        st.session_state['current_file_id'] = file_id
        try:
            bytes_data = uploaded_file.getvalue()
            st.session_state['pil_image_original'] = Image.open(io.BytesIO(bytes_data))
        except Exception as e:
            st.sidebar.error(f"画像の読み込みに失敗: {e}")
            st.session_state['pil_image_original'] = None
else:
    st.session_state['pil_image_original'] = None
    st.session_state['current_file_id'] = None


# --- メイン処理 ---
if st.session_state.get('pil_image_original'):
    # --- サイドバーUI ---
    st.sidebar.subheader("1. 輝点検出方法")
    st.sidebar.radio("検出方法", ("色で検出", "明るさで検出"), key='detection_method', horizontal=True)
    st.sidebar.markdown("---")

    if st.session_state.detection_method == "明るさで検出":
        st.sidebar.subheader("2. 二値化")
        st.sidebar.slider('閾値', 0, 255, key='binary_threshold')
    else:
        st.sidebar.subheader("2. 色の範囲設定 (HSV)")
        HUE_PRESETS = {
            "赤": {"range": ((0, 10), (160, 179)), "color": "#FF4B4B"},
            "黄": {"range": (20, 35), "color": "#FFD700"},
            "緑": {"range": (35, 85), "color": "#28a745"},
            "青": {"range": (100, 130), "color": "#007bff"},
        }
        st.sidebar.write("**輝点の色** (複数選択可)")
        cols = st.sidebar.columns(2)
        color_items = list(HUE_PRESETS.items())
        current_selections = []

        for i, (color_name, props) in enumerate(color_items):
            col = cols[i % 2]
            container = col.container()
            c1, c2 = container.columns([0.8, 0.2])
            c1.markdown(f'<div class="color-checkbox-container"><div class="color-label"><div class="color-box" style="background-color: {props["color"]};"></div><span>{color_name}</span></div></div>', unsafe_allow_html=True)
            is_selected = c2.checkbox("", value=(color_name in st.session_state.selected_hue_names), key=f"cb_{color_name}", label_visibility="collapsed")
            if is_selected:
                current_selections.append(color_name)
        st.session_state.selected_hue_names = current_selections

        st.sidebar.slider("彩度(S)の下限", 0, 255, key='saturation_slider', on_change=sync_saturation_from_slider, help="色の「鮮やかさ」の最小値を指定します。")
        st.sidebar.number_input('（値）', 0, 255, key='saturation_number', on_change=sync_saturation_from_number, label_visibility="collapsed")

        st.sidebar.slider("明度(V)の下限", 0, 255, key='brightness_slider', on_change=sync_brightness_from_slider, help="色の「明るさ」の最小値を指定します。")
        st.sidebar.number_input('（値）', 0, 255, key='brightness_number', on_change=sync_brightness_from_number, label_visibility="collapsed")

    st.sidebar.subheader("3. 前処理")
    # ★★★ 修正点: チェックボックスのラベルとヘルプテキストを変更 ★★★
    st.sidebar.checkbox("コントラストを向上 (40%)", key='use_contrast', help="輝点と背景の明暗差を強調し、検出精度が向上する場合があります。")
    st.sidebar.subheader("4. 形態学的処理")
    st.sidebar.select_slider('カーネルサイズ', options=[1, 3, 5, 7, 9], key='kernel_size', help="ノイズ除去や輝点分離の効果の強さを調整します。")

    st.sidebar.subheader("5. 輝点フィルタリング (面積)")
    st.sidebar.number_input('最小面積', 1, 10000, key='min_area')
    st.sidebar.number_input('最大面積', 1, 100000, key='max_area')

    st.sidebar.subheader("6. 表示設定")
    CONTOUR_COLORS = {"緑":"#28a745", "青":"#007bff", "赤":"#dc3545", "黄":"#ffc107"}
    st.sidebar.radio("輝点マーキング色", list(CONTOUR_COLORS.keys()), key='contour_color', horizontal=True)
    contour_color_bgr = hex_to_bgr(CONTOUR_COLORS[st.session_state.contour_color])

    col1, col2 = st.columns([2, 3])

    with col1:
        st.subheader("解析エリアの選択")
        img_original = st.session_state.pil_image_original.copy()
        
        display_width = 400
        scaling_factor = 1.0
        img_for_display = img_original
        if img_original.width > display_width:
            scaling_factor = img_original.width / display_width
            new_height = int(img_original.height / scaling_factor)
            img_for_display = img_original.resize((display_width, new_height), Image.Resampling.LANCZOS)
        
        box = st_cropper(
            img_for_display, realtime_update=True, box_color='#007BFF',
            aspect_ratio=None, return_type='box', key=f"cropper_{st.session_state.current_file_id}"
        )

        left = int(box['left'] * scaling_factor)
        top = int(box['top'] * scaling_factor)
        right = int((box['left'] + box['width']) * scaling_factor)
        bottom = int((box['top'] + box['height']) * scaling_factor)
        pil_image_to_process = img_original.crop((left, top, right, bottom))

    with col2:
        st.subheader("輝点検出とマーキング")
        try:
            img_np = np.array(pil_image_to_process.convert("RGB"))
        except Exception as e:
            st.error(f"トリミング画像の変換に失敗: {e}")
            st.stop()

        img_to_analyze = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        # ★★★ 修正点: 鮮明化を削除し、コントラスト向上処理に変更 ★★★
        if st.session_state.use_contrast:
            # コントラストを1.4倍（40%増）に
            img_to_analyze = cv2.addWeighted(img_to_analyze, 1.4, np.zeros(img_to_analyze.shape, img_to_analyze.dtype), 0, 0)
        
        img_to_analyze_rgb = cv2.cvtColor(img_to_analyze, cv2.COLOR_BGR2RGB)

        if st.session_state.detection_method == "明るさで検出":
            img_gray = cv2.cvtColor(img_to_analyze_rgb, cv2.COLOR_RGB2GRAY)
            _, binary_img = cv2.threshold(img_gray, st.session_state.binary_threshold, 255, cv2.THRESH_BINARY)
        else:
            img_hsv = cv2.cvtColor(img_to_analyze_rgb, cv2.COLOR_RGB2HSV)
            sat_min = st.session_state.saturation
            sat_max = 255
            val = st.session_state.brightness
            final_mask = np.zeros(img_hsv.shape[:2], dtype=np.uint8)
            if st.session_state.selected_hue_names:
                for color_name in st.session_state.selected_hue_names:
                    hue_data = HUE_PRESETS[color_name]["range"]
                    if isinstance(hue_data[0], tuple):
                        lower1, upper1 = np.array([hue_data[0][0], sat_min, val]), np.array([hue_data[0][1], sat_max, 255])
                        mask1 = cv2.inRange(img_hsv, lower1, upper1)
                        lower2, upper2 = np.array([hue_data[1][0], sat_min, val]), np.array([hue_data[1][1], sat_max, 255])
                        mask2 = cv2.inRange(img_hsv, lower2, upper2)
                        color_mask = cv2.bitwise_or(mask1, mask2)
                    else:
                        lower, upper = np.array([hue_data[0], sat_min, val]), np.array([hue_data[1], sat_max, 255])
                        color_mask = cv2.inRange(img_hsv, lower, upper)
                    final_mask = cv2.bitwise_or(final_mask, color_mask)
            binary_img = final_mask

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (st.session_state.kernel_size, st.session_state.kernel_size))
        opened_img = cv2.morphologyEx(binary_img, cv2.MORPH_OPEN, kernel, iterations=1)
        
        contours, _ = cv2.findContours(opened_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        count = 0
        output_image = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        for c in contours:
            area = cv2.contourArea(c)
            if st.session_state.min_area <= area <= st.session_state.max_area:
                count += 1
                cv2.drawContours(output_image, [c], -1, contour_color_bgr, 2)
        
        st.image(cv2.cvtColor(output_image, cv2.COLOR_BGR2RGB), use_container_width=True)
        caption_html = f"""
        <div style="text-align: center; background-image: linear-gradient(45deg, #007bff, #E83E8C); padding: 10px;
            border-radius: 10px; color: white; font-size: 20px; font-weight: bold; margin-top: 10px;">
            検出輝点: {count}個
        </div>
        """
        st.markdown(caption_html, unsafe_allow_html=True)
    
    st.markdown("---")
    # ★★★ 修正点: 表示する画像のラベルを変更 ★★★
    if st.session_state.use_contrast:
        st.subheader("元の画像 (コントラスト向上後)")
        st.image(img_to_analyze_rgb, use_container_width=True)
    else:
        st.subheader("元の画像 (トリミング後)")
        st.image(img_np, use_container_width=True)

else:
    st.info("まず、サイドバーから画像ファイルをアップロードしてください。")
