import streamlit as st
from PIL import Image
import numpy as np
import cv2
import io
from streamlit_drawable_canvas import st_canvas # ★★★ ライブラリを変更 ★★★

# ページ設定 (一番最初に呼び出す)
st.set_page_config(page_title="輝点解析ツール", layout="wide", initial_sidebar_state="expanded")

# メイン画面上部の余白を調整するためのCSS
st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem !important;
    }
</style>
""", unsafe_allow_html=True)

# ファイルアップローダーのカスタムCSS
file_uploader_css = """
<style>
    section[data-testid="stFileUploaderDropzone"] {
        border: 3px dashed white !important; border-radius: 0.5rem !important;
        background-color: #495057 !important; padding: 25px !important;
    }
    section[data-testid="stFileUploaderDropzone"] > div[data-testid="stFileUploadDropzoneInstructions"] {
        display: flex; flex-direction: column; align-items: center; justify-content: center;
    }
    section[data-testid="stFileUploaderDropzone"] p { color: #f8f9fa !important; font-size: 0.9rem; margin-bottom: 0.75rem !important; }
    section[data-testid="stFileUploaderDropzone"] span { color: #ced4da !important; font-size: 0.8rem; }
    section[data-testid="stFileUploaderDropzone"] button {
        color: #ffffff !important; background-color: #007bff !important; border: 1px solid #007bff !important;      
        padding: 0.5em 1em !important; border-radius: 0.375rem !important; font-weight: 500 !important;
        margin-top: 0.5rem !important; 
    }
</style>
"""
st.markdown(file_uploader_css, unsafe_allow_html=True)

# --- サイドバーの上部に結果表示用のプレースホルダーを定義 ---
result_placeholder_sidebar = st.sidebar.empty() 

# --- カスタマイズされた結果表示関数 (サイドバー表示用) ---
def display_count_in_sidebar(placeholder, count_value):
    label_text = "【解析結果】輝点数"; value_text = str(count_value) 
    bg="#495057"; lf="white"; vf="white"
    html=f"""<div style="border-radius:8px;padding:15px;text-align:center;background-color:{bg};margin-bottom:15px;color:{lf};"><p style="font-size:16px;margin-bottom:5px;font-weight:bold;">{label_text}</p><p style="font-size:48px;font-weight:bold;margin-top:0px;color:{vf};line-height:1.1;">{value_text}</p></div>"""
    with placeholder.container(): placeholder.markdown(html, unsafe_allow_html=True)

# --- セッションステートの初期化 ---
if 'counted_spots_value' not in st.session_state: st.session_state.counted_spots_value = "---" 
if "binary_threshold" not in st.session_state: st.session_state.binary_threshold = 15
if "saturation" not in st.session_state: st.session_state.saturation = 120
if "brightness" not in st.session_state: st.session_state.brightness = 60
if 'pil_image_original' not in st.session_state: st.session_state.pil_image_original = None
if 'image_source_caption' not in st.session_state: st.session_state.image_source_caption = "アップロードされた画像"
if 'contour_color_name' not in st.session_state: st.session_state.contour_color_name = "緑"
if 'detection_method' not in st.session_state: st.session_state.detection_method = "色で検出（新機能）"
if 'roi_coords' not in st.session_state: st.session_state.roi_coords = None

# --- ヘルパー関数 ---
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
st.markdown("<h1>Gra&Green<br>輝点カウントツール</h1>", unsafe_allow_html=True)
st.markdown("""### 使用方法
1. 画像を左にアップロードしてください。
2. 「1. 解析エリアの選択」で、上に表示される参照用画像を見ながら、下の描画エリアにマウスで解析したい四角い範囲を描画します。
3. サイドバーの各パラメータを調整し、「元の画像（トリミング後）」と「輝点検出とマーキング」を比較しながら最適な設定を見つけます。
""")
st.markdown("---") 

# --- 画像読み込みロジック ---
if uploaded_file_widget is not None:
    try:
        if 'last_uploaded_filename' not in st.session_state or st.session_state.last_uploaded_filename != uploaded_file_widget.name:
            st.session_state.last_uploaded_filename = uploaded_file_widget.name
            # 新しい画像がアップロードされたらROIとパラメータをリセット
            st.session_state.roi_coords = None
            st.session_state.binary_threshold = 15
            st.session_state.saturation = 120
            st.session_state.brightness = 60

        uploaded_file_bytes = uploaded_file_widget.getvalue()
        pil_img = Image.open(io.BytesIO(uploaded_file_bytes))
        st.session_state.pil_image_original = pil_img
        st.session_state.image_source_caption = f"アップロード: {uploaded_file_widget.name}"
    except Exception as e:
        st.sidebar.error(f"アップロード画像の読み込みに失敗: {e}"); st.session_state.pil_image_original = None; st.session_state.counted_spots_value = "読込エラー"; st.stop()
else: 
    if st.session_state.pil_image_original is not None: 
        st.session_state.pil_image_original = None
        st.session_state.counted_spots_value = "---" 

# --- メイン処理 ---
if st.session_state.pil_image_original is not None:
    # --- フル解像度画像の準備 ---
    pil_image_rgb_full_res = st.session_state.pil_image_original.convert("RGB")
    np_array_rgb_uint8_full_res = np.array(pil_image_rgb_full_res).astype(np.uint8)
    img_gray_full_res = cv2.cvtColor(np_array_rgb_uint8_full_res, cv2.COLOR_RGB2GRAY)

    # --- メインエリアのROI選択UI ---
    st.header("1. 解析エリアの選択 (ROI)")
    
    # 参照用画像を準備 (縮小)
    pil_for_reference = pil_image_rgb_full_res.copy()
    DISPLAY_MAX_DIM = 600 
    if pil_for_reference.width > DISPLAY_MAX_DIM or pil_for_reference.height > DISPLAY_MAX_DIM:
        pil_for_reference.thumbnail((DISPLAY_MAX_DIM, DISPLAY_MAX_DIM))
    
    canvas_width = pil_for_reference.width
    canvas_height = pil_for_reference.height

    st.markdown("##### 元の画像（参照用）")
    st.image(pil_for_reference, caption="この画像を参照して、下のキャンバスにROIを描画してください。")
    
    # 描画用キャンバス
    canvas_result = st_canvas(
        fill_color="rgba(255, 0, 0, 0.2)",
        stroke_width=2,
        stroke_color="red",
        background_color="#eee", # 薄いグレーの背景
        height=canvas_height,   
        width=canvas_width,    
        drawing_mode="rect", 
        key="roi_canvas"
    )

    # 処理対象画像を決定
    scale_x = pil_image_rgb_full_res.width / canvas_width if canvas_width > 0 else 1.0
    scale_y = pil_image_rgb_full_res.height / canvas_height if canvas_height > 0 else 1.0

    img_to_process_rgb = np_array_rgb_uint8_full_res # デフォルトは全体
    analysis_caption_suffix = "(画像全体)"

    if canvas_result.json_data is not None and canvas_result.json_data.get("objects", []):
        rect = canvas_result.json_data["objects"][-1]
        x, y, w, h = int(rect["left"]), int(rect["top"]), int(rect["width"]), int(rect["height"])
        if w > 0 and h > 0:
            x1 = int(x * scale_x); y1 = int(y * scale_y)
            x2 = int((x + w) * scale_x); y2 = int((y + h) * scale_y)
            img_to_process_rgb = np_array_rgb_uint8_full_res[y1:y2, x1:x2]
            analysis_caption_suffix = f"(選択エリア: {img_to_process_rgb.shape[1]}x{img_to_process_rgb.shape[0]}px)"

    # --- サイドバーのパラメータ設定UI ---
    st.sidebar.subheader("1. 輝点検出方法")
    detection_options = ("明るさで検出", "色で検出")
    if st.session_state.detection_method not in detection_options:
        st.session_state.detection_method = "色で検出" # 安全策
    detection_method = st.sidebar.radio("検出方法", options=detection_options, key="detection_method", horizontal=True)
    st.sidebar.markdown("---")

    # (以降のサイドバーUIは、最新のものを維持)
    if detection_method == "明るさで検出":
        st.sidebar.subheader("2. 二値化")
        st.sidebar.slider('閾値', min_value=0,max_value=255,key="binary_threshold", help="この値より明るいピクセルは白（検出対象）に、暗いピクセルは黒になります。")
        st.sidebar.number_input('（直接入力）', min_value=0,max_value=255,key="binary_threshold", label_visibility="collapsed")
    else: # 色で検出
        st.sidebar.subheader("2. 色の範囲設定 (HSV)")
        st.sidebar.slider("彩度(S)の下限", min_value=0, max_value=255, key="saturation", help="色の「鮮やかさ」の最低ライン。値を上げると、白やグレーに近いくすんだ色が除外されます。")
        st.sidebar.number_input("（直接入力）", min_value=0, max_value=255, key="saturation", label_visibility="collapsed")
        st.sidebar.slider("明度(V)の下限", min_value=0, max_value=255, key="brightness", help="色の「明るさ」の最低ライン。値を上げると、暗い部分にあるノイズが除外されます。")
        st.sidebar.number_input("（直接入力）", min_value=0, max_value=255, key="brightness", label_visibility="collapsed")
        
    st.sidebar.subheader("3. 形態学的処理"); kernel_size_morph_to_use = st.sidebar.select_slider('カーネルサイズ',options=[1,3,5,7,9],value=1, help="ノイズ除去や輝点分離の効果の強さを調整します。")
    st.sidebar.subheader("4. 輝点フィルタリング (面積)"); min_area_to_use = st.sidebar.number_input('最小面積',min_value=1,max_value=10000,step=1,value=1); max_area_to_use = st.sidebar.number_input('最大面積',min_value=1,max_value=100000,step=1,value=10000)
    st.sidebar.subheader("5. 表示設定"); CONTOUR_COLORS = {"緑":"#28a745","青":"#007bff","赤":"#dc3545","黄":"#ffc107","シアン":"#17a2b8","ピンク":"#e83e8c"}; st.sidebar.radio("輝点マーキング色を選択",options=list(CONTOUR_COLORS.keys()),key="contour_color_name",horizontal=True)
    contour_color_bgr = hex_to_bgr(CONTOUR_COLORS[st.session_state.contour_color_name])
    
    # --- メインエリアの画像処理と表示ロジック ---
    st.markdown("---")
    st.header("解析結果の比較")
    
    if detection_method == "明るさで検出":
        img_gray = cv2.cvtColor(img_to_process_rgb, cv2.COLOR_RGB2GRAY)
        kernel_size_blur=1; blurred_img = cv2.GaussianBlur(img_gray, (kernel_size_blur,kernel_size_blur),0)
        binary_img = cv2.threshold(blurred_img, st.session_state.binary_threshold, 255, cv2.THRESH_BINARY)[1]
    else: # 色で検出
        img_hsv = cv2.cvtColor(img_to_process_rgb, cv2.COLOR_RGB2HSV)
        sat_min = st.session_state.saturation; val_min = st.session_state.brightness
        hue_lower1, hue_upper1 = 0, 20; hue_lower2, hue_upper2 = 160, 179; hue_lower_green, hue_upper_green = 35, 85
        lower_range1 = np.array([hue_lower1, sat_min, val_min]); upper_range1 = np.array([hue_upper1, 255, 255])
        lower_range2 = np.array([hue_lower2, sat_min, val_min]); upper_range2 = np.array([hue_upper2, 255, 255])
        mask_red = cv2.add(cv2.inRange(img_hsv, lower_range1, upper_range1), cv2.inRange(img_hsv, lower_range2, upper_range2))
        lower_range_green = np.array([hue_lower_green, sat_min, val_min]); upper_range_green = np.array([hue_upper_green, 255, 255])
        mask_green = cv2.inRange(img_hsv, lower_range_green, upper_range_green)
        binary_img = cv2.add(mask_red, mask_green)

    morph_kernel_shape_to_use = cv2.MORPH_ELLIPSE; erosion_iterations = 1
    kernel_morph_obj=cv2.getStructuringElement(morph_kernel_shape_to_use,(kernel_size_morph_to_use,kernel_size_morph_to_use))
    opened_img = cv2.morphologyEx(binary_img, cv2.MORPH_OPEN, kernel_morph_obj, iterations=erosion_iterations)
    binary_img_for_contours = opened_img.copy()
    current_counted_spots = 0 
    output_image_contours_display = cv2.cvtColor(img_to_process_rgb, cv2.COLOR_RGB2BGR) 
    contours, hierarchy = cv2.findContours(binary_img_for_contours,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    if 'contours' in locals() and contours: 
        for contour in contours:
            area = cv2.contourArea(contour)
            if min_area_to_use <= area <= max_area_to_use: 
                current_counted_spots += 1
                cv2.drawContours(output_image_contours_display, [contour], -1, contour_color_bgr, 1) 
    st.session_state.counted_spots_value = current_counted_spots 
    
    col1_res, col2_res = st.columns(2)
    with col1_res:
        st.subheader(f"元の画像 {analysis_caption_suffix}")
        st.image(img_to_process_rgb, use_container_width=True)
            
    with col2_res:
        st.subheader("輝点検出とマーキング")
        display_final_marked_image_rgb = cv2.cvtColor(output_image_contours_display, cv2.COLOR_BGR2RGB)
        st.image(display_final_marked_image_rgb, caption=f'検出輝点({current_counted_spots}個)', use_container_width=True)

    with st.expander("▼ 中間処理の画像を見る"):
        st.subheader(f"1. {detection_method}による二値化処理後"); st.image(binary_img)
        st.subheader("2. 形態学的処理後"); st.image(opened_img,caption=f'カーネル: 楕円 {kernel_size_morph_to_use}x{kernel_size_morph_to_use}')
else: 
    st.info("まず、サイドバーから画像ファイルをアップロードしてください。")

display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value)
