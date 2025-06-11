import streamlit as st
from PIL import Image
import numpy as np
import cv2
import io

# ページ設定
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
if 'pil_image_original_full_res' not in st.session_state: st.session_state.pil_image_original_full_res = None
if 'image_source_caption' not in st.session_state: st.session_state.image_source_caption = "アップロードされた画像"
if 'contour_color_name' not in st.session_state: st.session_state.contour_color_name = "緑"

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
2. 画像をアップロードすると、左サイドバーに検出パラメータが表示されます。
3. 各パラメータを調整し、「元の画像」と「輝点検出とマーキング」の画像を比較しながら、最適な設定を見つけてください。
""")
st.markdown("---") 

# --- 画像読み込みロジック ---
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
    st.sidebar.subheader("1. 輝点検出パラメータ (Hough変換)")
    # Hough変換のパラメータ
    h_min_dist = st.sidebar.slider("輝点間の最小距離", 1, 50, 10, help="このピクセル数より近い中心を持つ輝点は、一つとして扱われます。接触した輝点を分離するのに重要です。")
    h_param2 = st.sidebar.slider("検出感度", 1, 100, 10, help="値を小さくすると、より多くの円（偽の輝点も含む）を検出しやすくなります。")
    h_min_radius = st.sidebar.slider("輝点の最小半径", 0, 50, 1)
    h_max_radius = st.sidebar.slider("輝点の最大半径", 0, 100, 20)
    
    # ★★★ 色選択UI ★★★
    st.sidebar.subheader("2. 表示設定")
    CONTOUR_COLORS = {"緑":"#28a745","青":"#007bff","赤":"#dc3545","黄":"#ffc107","シアン":"#17a2b8","ピンク":"#e83e8c"}
    st.sidebar.radio("輝点マーキング色を選択",options=list(CONTOUR_COLORS.keys()),key="contour_color_name",horizontal=True)
    selected_name = st.session_state.contour_color_name
    selected_hex = CONTOUR_COLORS[selected_name]
    contour_color_bgr = hex_to_bgr(selected_hex)

    # --- メインエリアの画像処理と表示ロジック ---
    pil_rgb_full = st.session_state.pil_image_original_full_res.convert("RGB")
    np_rgb_full_uint8 = np.array(pil_rgb_full).astype(np.uint8)
    img_gray_full_res = cv2.cvtColor(np_rgb_full_uint8, cv2.COLOR_RGB2GRAY)
    if img_gray_full_res.dtype != np.uint8: img_gray_full_res = img_gray_full_res.astype(np.uint8)
    
    st.header("解析結果の比較")
    
    # Hough Circle Transform 実行
    # 画像がノイジーな場合、ブラーをかけると安定することがある
    gray_for_hough = cv2.medianBlur(img_gray_full_res, 5)
    circles = cv2.HoughCircles(
        gray_for_hough, 
        cv2.HOUGH_GRADIENT, 
        dp=1, 
        minDist=h_min_dist, 
        param1=50, # Cannyエッジ検出の上位閾値 (固定値)
        param2=h_param2, 
        minRadius=h_min_radius, 
        maxRadius=h_max_radius
    )
    
    current_counted_spots = 0 
    output_image_marked = cv2.cvtColor(np_rgb_full_uint8.copy(), cv2.COLOR_RGB2BGR) 
    
    if circles is not None:
        circles = np.uint16(np.around(circles))
        current_counted_spots = len(circles[0, :])
        for i in circles[0,:]:
            # 円の輪郭を描画
            cv2.circle(output_image_marked, (i[0], i[1]), i[2], contour_color_bgr, 2)
            # 中心の点は描画しない
            # cv2.circle(output_image_marked, (i[0], i[1]), 2, (0,0,255), 3) 
    else:
        current_counted_spots = 0

    st.session_state.counted_spots_value = current_counted_spots
    
    # --- 表示エリア ---
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("元の画像")
        st.image(np_rgb_full_uint8, caption=st.session_state.image_source_caption, use_container_width=True)
            
    with col2:
        st.subheader("輝点検出とマーキング")
        display_final_marked_image_rgb = cv2.cvtColor(output_image_marked, cv2.COLOR_BGR2RGB)
        caption_text = f'検出輝点({current_counted_spots}個)'
        if current_counted_spots == 0: caption_text = '輝点見つからず'
        st.image(display_final_marked_image_rgb, caption=caption_text, use_container_width=True)

else: 
    st.info("まず、サイドバーから画像ファイルをアップロードしてください。")

display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value)
