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
# ★★★ 修正点: シンプルで堅牢な初期化方式に変更 ★★★
defaults = {
    'current_file_id': None,
    'counted_spots_value': "---",
    'binary_threshold': 15,
    'saturation': 200,          # デフォルト値を200に再設定
    'brightness': 60,           # デフォルト値を60に再設定
    'selected_hue_name': "赤",
    'pil_image_original': None,
    'pil_image_to_process': None,
    'contour_color': "青",
    'detection_method': "色で検出",
    'max_area': 1000,           # デフォルト値を1000に再設定
    'min_area': 1,
    'kernel_size': 1,
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

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
    # --- サイドバーUI (コールバックを完全撤廃) ---
    st.sidebar.subheader("1. 輝点検出方法")
    st.sidebar.radio("検出方法", ("色で検出", "明るさで検出"), key='detection_method', horizontal=True)
    st.sidebar.markdown("---")

    if st.session_state.detection_method == "明るさで検出":
        st.sidebar.subheader("2. 二値化")
        st.sidebar.slider('閾値', 0, 255, key='binary_threshold')
    else:
        st.sidebar.subheader("2. 色の範囲設定 (HSV)")
        HUE_PRESETS = {
            "赤": ((0, 10), (160, 179)), "黄": (20, 35), "緑": (35, 85),
            "シアン": (85, 100), "青": (100, 130), "マゼンタ": (130, 160),
        }
        # ★★★ 修正点: 基準色の選択をサイドバーに移動 ★★★
        st.sidebar.selectbox("基準色を選択", HUE_PRESETS.keys(), key='selected_hue_name')
        st.sidebar.slider("彩度(S)の下限", 0, 255, key='saturation', help="色の「鮮やかさ」の最小値を指定します。")
        st.sidebar.slider("明度(V)の下限", 0, 255, key='brightness', help="色の「明るさ」の最小値を指定します。")

    st.sidebar.subheader("3. 形態学的処理")
    st.sidebar.select_slider('カーネルサイズ', options=[1, 3, 5, 7, 9], key='kernel_size', help="ノイズ除去や輝点分離の効果の強さを調整します。")

    st.sidebar.subheader("4. 輝点フィルタリング (面積)")
    st.sidebar.number_input('最小面積', 1, 10000, key='min_area')
    st.sidebar.number_input('最大面積', 1, 100000, key='max_area')

    st.sidebar.subheader("5. 表示設定")
    CONTOUR_COLORS = {"緑":"#28a745", "青":"#007bff", "赤":"#dc3545", "黄":"#ffc107", "シアン":"#17a2b8", "ピンク":"#e83e8c"}
    st.sidebar.radio("輝点マーキング色", list(CONTOUR_COLORS.keys()), key='contour_color', horizontal=True)
    contour_color_bgr = hex_to_bgr(CONTOUR_COLORS[st.session_state.contour_color])

    # --- メインエリアUI ---
    st.header("解析エリアの選択 (トリミング)")
    st.session_state.pil_image_to_process = st_cropper(
        st.session_state.pil_image_original, realtime_update=True, box_color='#007BFF',
        aspect_ratio=None, key=f"cropper_{st.session_state.current_file_id}"
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
        _, binary_img = cv2.threshold(img_gray, st.session_state.binary_threshold, 255, cv2.THRESH_BINARY)
    else:
        img_hsv = cv2.cvtColor(img_np, cv2.COLOR_RGB2HSV)
        sat = st.session_state.saturation
        val = st.session_state.brightness
        hue_range = HUE_PRESETS[st.session_state.selected_hue_name]
        if isinstance(hue_range[0], tuple): # 赤の場合
            lower1 = np.array([hue_range[0][0], sat, val])
            upper1 = np.array([hue_range[0][1], 255, 255])
            mask1 = cv2.inRange(img_hsv, lower1, upper1)
            lower2 = np.array([hue_range[1][0], sat, val])
            upper2 = np.array([hue_range[1][1], 255, 255])
            mask2 = cv2.inRange(img_hsv, lower2, upper2)
            binary_img = cv2.bitwise_or(mask1, mask2)
        else: # その他の色
            lower = np.array([hue_range[0], sat, val])
            upper = np.array([hue_range[1], 255, 255])
            binary_img = cv2.inRange(img_hsv, lower, upper)

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
