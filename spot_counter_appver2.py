import streamlit as st
from PIL import Image
import numpy as np
import cv2
import io

# ページ設定 (一番最初に呼び出す)
st.set_page_config(page_title="輝点解析ツール", layout="wide")

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
if "binary_threshold_value" not in st.session_state: st.session_state.binary_threshold_value = 15
if "threshold_slider_for_binary" not in st.session_state: st.session_state.threshold_slider_for_binary = st.session_state.binary_threshold_value
if "threshold_number_for_binary" not in st.session_state: st.session_state.threshold_number_for_binary = st.session_state.binary_threshold_value
if 'pil_image_original_full_res' not in st.session_state: st.session_state.pil_image_original_full_res = None
if 'image_source_caption' not in st.session_state: st.session_state.image_source_caption = "アップロードされた画像"
if 'contour_color_name' not in st.session_state: st.session_state.contour_color_name = "緑" 


# --- コールバック関数とヘルパー関数 ---
def sync_threshold_from_slider():
    st.session_state.binary_threshold_value = st.session_state.threshold_slider_for_binary
    st.session_state.threshold_number_for_binary = st.session_state.threshold_slider_for_binary
def sync_threshold_from_number_input():
    st.session_state.binary_threshold_value = st.session_state.threshold_number_for_binary
    st.session_state.threshold_slider_for_binary = st.session_state.threshold_number_for_binary

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
2. 画像をアップロードすると、左サイドバーに詳細な解析パラメータが表示されます。
3. まず「1. 輝点検出方法の選択」で解析手法を選び、各パラメータを調整してください。
4. 「元の画像」と「輝点検出とマーキング」の画像を比較しながら、最適な設定を見つけます。
""")
st.markdown("---") 

# --- 画像読み込みと処理のロジック ---
if uploaded_file_widget is not None:
    try:
        uploaded_file_bytes = uploaded_file_widget.getvalue()
        pil_img_original = Image.open(io.BytesIO(uploaded_file_bytes))
        st.session_state.pil_image_original_full_res = pil_img_original
        st.session_state.image_source_caption = f"アップロード: {uploaded_file_widget.name} (元サイズ: {pil_img_original.width}x{pil_img_original.height}px)"
    except Exception as e:
        st.sidebar.error(f"アップロード画像の読み込みに失敗: {e}"); st.session_state.pil_image_original_full_res = None; st.session_state.counted_spots_value = "読込エラー"; st.stop()
else: 
    if st.session_state.pil_image_original_full_res is not None: 
        st.session_state.pil_image_original_full_res = None
        st.session_state.counted_spots_value = "---" 

if st.session_state.pil_image_original_full_res is not None:
    # --- サイドバーのパラメータ設定UI ---
    st.sidebar.subheader("1. 輝点検出方法の選択")
    use_hough = st.sidebar.checkbox("Hough Circle Transformで検出", value=False)
    st.sidebar.caption("輝点を円として検出し、接触した輝点を分離します。精度が高いですが、パラメータ調整が必要です。")
    st.sidebar.markdown("---")

    # --- メインの画像処理と表示ロジックのための準備 ---
    pil_rgb_full = st.session_state.pil_image_original_full_res.convert("RGB")
    np_rgb_full_uint8 = np.array(pil_rgb_full).astype(np.uint8)
    img_gray_full_res = cv2.cvtColor(np_rgb_full_uint8, cv2.COLOR_RGB2GRAY)
    if img_gray_full_res.dtype != np.uint8: img_gray_full_res = img_gray_full_res.astype(np.uint8)
    
    current_counted_spots = 0 
    output_image_contours_display = cv2.cvtColor(np_rgb_full_uint8.copy(), cv2.COLOR_RGB2BGR) 
    
    # ★★★ 色選択UIと色情報の準備 ★★★
    CONTOUR_COLORS = {"緑":"#28a745","青":"#007bff","赤":"#dc3545","黄":"#ffc107","シアン":"#17a2b8","ピンク":"#e83e8c"}
    # 最後のセクションとして表示設定UIを配置
    st.sidebar.subheader("表示設定")
    st.sidebar.radio("輝点マーキング色を選択",options=list(CONTOUR_COLORS.keys()),key="contour_color_name",horizontal=True)
    selected_name = st.session_state.contour_color_name
    selected_hex = CONTOUR_COLORS[selected_name] # ★★★ 色名からHEXコードを取得 ★★★
    contour_color_bgr = hex_to_bgr(selected_hex) # ★★★ HEXコードをBGRに変換 ★★★

    if use_hough:
        # --- Hough変換用のパラメータ ---
        st.sidebar.subheader("Hough Circle Transform パラメータ")
        h_min_dist = st.sidebar.slider("輝点間の最小距離", 1, 50, 10)
        h_param1 = st.sidebar.slider("Cannyエッジ検出の閾値", 1, 200, 100)
        h_param2 = st.sidebar.slider("検出の感度", 1, 100, 10)
        st.sidebar.caption("値を小さくすると、より多くの円（偽陽性含む）を検出します。")
        h_min_radius = st.sidebar.slider("輝点の最小半径", 0, 50, 1)
        h_max_radius = st.sidebar.slider("輝点の最大半径", 0, 100, 20)
        
        gray_for_hough = cv2.medianBlur(img_gray_full_res, 5)
        circles = cv2.HoughCircles(gray_for_hough, cv2.HOUGH_GRADIENT, dp=1, minDist=h_min_dist, param1=h_param1, param2=h_param2, minRadius=h_min_radius, maxRadius=h_max_radius)
        
        if circles is not None:
            circles = np.uint16(np.around(circles))
            current_counted_spots = len(circles[0, :])
            for i in circles[0,:]:
                cv2.circle(output_image_contours_display, (i[0], i[1]), i[2], contour_color_bgr, 2)
                cv2.circle(output_image_contours_display, (i[0], i[1]), 2, (0,0,255), 3) 
        else:
            current_counted_spots = 0
    else:
        # --- 従来の閾値ベースの処理 ---
        st.sidebar.subheader("2. 二値化")
        st.sidebar.slider('閾値 (スライダーで調整)',min_value=0,max_value=255,step=1,value=st.session_state.binary_threshold_value,key="threshold_slider_for_binary",on_change=sync_threshold_from_slider)
        st.sidebar.number_input('閾値 (直接入力)',min_value=0,max_value=255,step=1,value=st.session_state.binary_threshold_value,key="threshold_number_for_binary",on_change=sync_threshold_from_number_input)
        threshold_value_to_use = st.session_state.binary_threshold_value 
        st.sidebar.subheader("3. 形態学的処理")
        kernel_size_morph_to_use =st.sidebar.select_slider('カーネルサイズ',options=[1,3,5,7,9],value=1) 
        erosion_iterations = st.sidebar.slider("収縮の強さ（分離度）", 1, 5, 1, 1)
        st.sidebar.subheader("4. 輝点フィルタリング (面積)") 
        min_area_to_use = st.sidebar.number_input('最小面積',min_value=1,max_value=10000,step=1,value=1) 
        max_area_to_use = st.sidebar.number_input('最大面積',min_value=1,max_value=100000,step=1,value=10000) 

        kernel_size_blur=1; blurred_img = cv2.GaussianBlur(img_gray_full_res, (kernel_size_blur,kernel_size_blur),0)
        ret_thresh, binary_img = cv2.threshold(blurred_img,threshold_value_to_use,255,cv2.THRESH_BINARY)
        if not ret_thresh: st.error("二値化失敗。"); st.stop()
        
        kernel_morph_obj=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(kernel_size_morph_to_use,kernel_size_morph_to_use))
        eroded_img = cv2.erode(binary_img, kernel_morph_obj, iterations=erosion_iterations)
        opened_img = cv2.dilate(eroded_img, kernel_morph_obj, iterations=erosion_iterations)
        
        binary_img_for_contours = opened_img.copy()
        
        contours, hierarchy = cv2.findContours(binary_img_for_contours,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        if 'contours' in locals() and contours: 
            for contour in contours:
                area = cv2.contourArea(contour)
                if min_area_to_use <= area <= max_area_to_use: 
                    current_counted_spots += 1
                    cv2.drawContours(output_image_contours_display, [contour], -1, contour_color_bgr, 2) 
    
    st.session_state.counted_spots_value = current_counted_spots
    
    # --- 表示エリア ---
    st.header("解析結果の比較")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("元の画像")
        st.image(np_rgb_full_uint8, caption=st.session_state.image_source_caption, use_container_width=True)
            
    with col2:
        st.subheader("輝点検出とマーキング")
        display_final_marked_image_rgb = cv2.cvtColor(output_image_contours_display, cv2.COLOR_BGR2RGB)
        caption_text = f'検出輝点({current_counted_spots}個)'
        st.image(display_final_marked_image_rgb, caption=caption_text, use_container_width=True)
else: 
    st.info("まず、サイドバーから画像ファイルをアップロードしてください。")

display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value)
