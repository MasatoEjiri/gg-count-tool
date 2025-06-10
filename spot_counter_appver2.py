import streamlit as st
from PIL import Image
import numpy as np
import cv2
import io

# ページ設定 (一番最初に呼び出す)
st.set_page_config(page_title="輝点解析ツール", layout="wide")

# ★★★ メイン画面上部の余白を調整するためのCSS ★★★
# Streamlitのデフォルトの余白を小さくします。
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
if "binary_threshold_value" not in st.session_state: st.session_state.binary_threshold_value = 15
if "threshold_slider_for_binary" not in st.session_state: st.session_state.threshold_slider_for_binary = st.session_state.binary_threshold_value
if "threshold_number_for_binary" not in st.session_state: st.session_state.threshold_number_for_binary = st.session_state.binary_threshold_value
if 'pil_image_to_process' not in st.session_state: st.session_state.pil_image_to_process = None
if 'image_source_caption' not in st.session_state: st.session_state.image_source_caption = "アップロードされた画像"
if 'contour_color_name' not in st.session_state: st.session_state.contour_color_name = "緑" # ★★★ 色選択のデフォルトを追加 ★★★


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
3. まず「1. 二値化」の閾値を動かし、「元の画像」と「輝点検出とマーキング」の画像を比較しながら、実物に近い見え方になるよう調整してください。
4. 必要に応じて「2. 形態学的処理」、「3. 輝点フィルタリング」、「4. 表示設定」の各パラメータも調整します。
""")
st.markdown("---") 

# --- 画像読み込みと処理のロジック ---
if uploaded_file_widget is not None:
    try:
        uploaded_file_bytes = uploaded_file_widget.getvalue()
        pil_img = Image.open(io.BytesIO(uploaded_file_bytes))
        st.session_state.pil_image_to_process = pil_img
        st.session_state.image_source_caption = f"アップロード: {uploaded_file_widget.name}"
    except Exception as e:
        st.sidebar.error(f"アップロード画像の読み込みに失敗: {e}"); st.session_state.pil_image_to_process = None; st.session_state.counted_spots_value = "読込エラー"; st.stop()
else: 
    if st.session_state.pil_image_to_process is not None: 
        st.session_state.pil_image_to_process = None
        st.session_state.counted_spots_value = "---" 

if st.session_state.pil_image_to_process is not None:
    # --- サイドバーのパラメータ設定UI ---
    st.sidebar.subheader("1. 二値化") 
    st.sidebar.markdown("_この値を調整して、輝点と背景を分離します。_")
    st.sidebar.slider('閾値 (スライダーで調整)',min_value=0,max_value=255,step=1,value=st.session_state.binary_threshold_value,key="threshold_slider_for_binary",on_change=sync_threshold_from_slider)
    st.sidebar.number_input('閾値 (直接入力)',min_value=0,max_value=255,step=1,value=st.session_state.binary_threshold_value,key="threshold_number_for_binary",on_change=sync_threshold_from_number_input)
    threshold_value_to_use = st.session_state.binary_threshold_value 
    st.sidebar.caption("この値より明るいピクセルは白に、暗いピクセルは黒になります。")
    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    
    st.sidebar.subheader("2. 形態学的処理 (オープニング)") 
    morph_kernel_shape_to_use = cv2.MORPH_ELLIPSE 
    kernel_options_morph = [1,3,5,7,9]
    kernel_size_morph_to_use =st.sidebar.select_slider('カーネルサイズ',options=kernel_options_morph,value=1) 
    st.sidebar.caption("""オープニング処理で、小さなノイズ除去や輝点同士の分離を行います。\n- **大きくすると:** 効果が強まり、大きめのノイズも除去できますが、輝点自体が削られて消える可能性もあります。\n- **小さくすると:** 効果は弱く、輝点への影響は少ないですが、ノイズが残りやすくなります。""")
    
    st.sidebar.subheader("3. 輝点フィルタリング (面積)") 
    min_area_to_use = st.sidebar.number_input('最小面積',min_value=1,max_value=10000,step=1,value=1) 
    st.sidebar.caption("このピクセル数より小さい輝点（またはノイズ）はカウントから除外されます。") 
    max_area_to_use = st.sidebar.number_input('最大面積',min_value=1,max_value=100000,step=1,value=10000) 
    st.sidebar.caption("このピクセル数より大きい輝点（または塊）はカウントから除外されます。") 

    # ★★★ 色選択UIをサイドバーに再追加 ★★★
    st.sidebar.subheader("4. 表示設定")
    CONTOUR_COLORS = {"緑":"#28a745","青":"#007bff","赤":"#dc3545","黄":"#ffc107","シアン":"#17a2b8","ピンク":"#e83e8c"}
    st.sidebar.radio("輝点マーキング色を選択",options=list(CONTOUR_COLORS.keys()),key="contour_color_name",horizontal=True)
    selected_name = st.session_state.contour_color_name
    selected_hex = CONTOUR_COLORS[selected_name]
    st.sidebar.markdown(f"""<div style="padding-top: 5px;"><span style="font-size: 0.9em;">選択中の色: <b>{selected_name}</b></span><div style="width: 100%; height: 25px; background-color: {selected_hex}; border: 1px solid rgba(0,0,0,0.2); border-radius: 5px; margin-top: 5px;"></div></div>""", unsafe_allow_html=True)
    contour_color_bgr = hex_to_bgr(selected_hex)

    # --- メインエリアの画像処理と表示ロジック ---
    original_img_to_display_np_uint8 = None; img_gray = None                         
    try:
        pil_image_rgb = st.session_state.pil_image_to_process.convert("RGB")
        temp_np_array = np.array(pil_image_rgb)
        if temp_np_array.dtype != np.uint8: 
            if np.issubdtype(temp_np_array.dtype, np.floating):
                if temp_np_array.min() >= 0.0 and temp_np_array.max() <= 1.0: original_img_to_display_np_uint8 = (temp_np_array * 255).astype(np.uint8)
                else: original_img_to_display_np_uint8 = np.clip(temp_np_array, 0, 255).astype(np.uint8)
            elif np.issubdtype(temp_np_array.dtype, np.integer): original_img_to_display_np_uint8 = np.clip(temp_np_array, 0, 255).astype(np.uint8)
            else: original_img_to_display_np_uint8 = temp_np_array.astype(np.uint8)
        else: original_img_to_display_np_uint8 = temp_np_array
        img_gray = cv2.cvtColor(original_img_to_display_np_uint8, cv2.COLOR_RGB2GRAY)
        if img_gray.dtype != np.uint8: img_gray = img_gray.astype(np.uint8)
    except Exception as e: st.error(f"画像の基本変換に失敗: {e}"); st.session_state.counted_spots_value="変換エラー"; st.stop() 
    
    st.header("解析結果の比較")
    kernel_size_blur=1 
    if img_gray is None or img_gray.size == 0 : st.error("グレースケール画像準備失敗。"); st.stop()
    blurred_img = cv2.GaussianBlur(img_gray, (kernel_size_blur,kernel_size_blur),0)
    ret_thresh, binary_img_processed = cv2.threshold(blurred_img,threshold_value_to_use,255,cv2.THRESH_BINARY)
    if not ret_thresh: st.error("二値化失敗。"); binary_img_for_morph=None
    else: binary_img_for_morph=binary_img_processed.copy()
    opened_img_processed = None 
    if binary_img_for_morph is not None:
        kernel_morph_obj=cv2.getStructuringElement(morph_kernel_shape_to_use,(kernel_size_morph_to_use,kernel_size_morph_to_use))
        opened_img_processed=cv2.morphologyEx(binary_img_for_morph,cv2.MORPH_OPEN,kernel_morph_obj)
        binary_img_for_contours = opened_img_processed.copy()
    else: binary_img_for_contours = None
    current_counted_spots = 0 
    output_image_contours = cv2.cvtColor(original_img_to_display_np_uint8, cv2.COLOR_RGB2BGR) 
    if binary_img_for_contours is not None:
        contours, hierarchy = cv2.findContours(binary_img_for_contours,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        if 'contours' in locals() and contours: 
            for contour in contours:
                area = cv2.contourArea(contour)
                if min_area_to_use <= area <= max_area_to_use: 
                    current_counted_spots += 1
                    cv2.drawContours(output_image_contours, [contour], -1, contour_color_bgr, 2) 
        st.session_state.counted_spots_value = current_counted_spots 
    else:
        st.warning("輪郭検出元画像準備できず。"); st.session_state.counted_spots_value="エラー"
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("元の画像")
        if original_img_to_display_np_uint8 is not None:
            st.image(original_img_to_display_np_uint8, caption=st.session_state.image_source_caption, use_container_width=True)
            
    with col2:
        st.subheader("輝点検出とマーキング")
        display_final_marked_image_rgb = cv2.cvtColor(output_image_contours, cv2.COLOR_BGR2RGB)
        caption_text = f'検出輝点({current_counted_spots}個, 選択色, 面積:{min_area_to_use}-{max_area_to_use})'
        if current_counted_spots == 0:
            caption_text = '輝点見つからず'
        st.image(display_final_marked_image_rgb, caption=caption_text, use_container_width=True)

    st.markdown("---")
    
    with st.expander("▼ 中間処理の画像を見る"):
        st.subheader("1. 二値化処理後")
        if binary_img_processed is not None: 
            st.image(binary_img_processed,caption=f'閾値:{threshold_value_to_use}')
        else: st.info("二値化未実施/失敗")
        
        st.subheader("2. 形態学的処理後")
        if opened_img_processed is not None: 
            st.image(opened_img_processed,caption=f'カーネル: 楕円 {kernel_size_morph_to_use}x{kernel_size_morph_to_use}')
        else: st.info("形態学的処理未実施/失敗")
else: 
    st.info("まず、サイドバーから画像ファイルをアップロードしてください。")

display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value)
