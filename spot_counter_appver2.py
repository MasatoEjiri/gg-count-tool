import streamlit as st
from PIL import Image
import numpy as np
import cv2
import io
from streamlit_cropper import st_cropper

# ページ設定 (一番最初に呼び出す)
# ★★★ サイドバーを最初から展開する設定を追加 ★★★
st.set_page_config(
    page_title="輝点解析ツール", 
    layout="wide",
    initial_sidebar_state="expanded" 
)

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
if 'pil_image_original' not in st.session_state: st.session_state.pil_image_original = None
if 'pil_image_to_process' not in st.session_state: st.session_state.pil_image_to_process = None
if 'image_source_caption' not in st.session_state: st.session_state.image_source_caption = "アップロードされた画像"
if 'contour_color_name' not in st.session_state: st.session_state.contour_color_name = "緑"
if 'cropper_box_color_name' not in st.session_state: st.session_state.cropper_box_color_name = '赤'


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
2. メイン画面に表示された画像の上で、四角い枠をドラッグ＆リサイズして解析したいエリアを選択します。枠の色は、画像の右隣のオプションで変更できます。
3. 左サイドバーの各パラメータを調整し、「元の画像（トリミング後）」と「輝点検出とマーキング」を比較しながら最適な設定を見つけてください。
""")
st.markdown("---") 

# --- 画像読み込みロジック ---
if uploaded_file_widget is not None:
    try:
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
    # --- メインエリアのトリミングUI ---
    st.header("1. 解析エリアの選択 (トリミング)")
    col_cropper, col_options = st.columns([3, 1])

    with col_cropper:
        st.info("画像上の四角い枠をドラッグ、または枠の角をドラッグして、解析したいエリアを選択してください。")
        img_for_cropper = st.session_state.pil_image_original.copy()
        CROPPER_MAX_DIM = 700
        if img_for_cropper.width > CROPPER_MAX_DIM or img_for_cropper.height > CROPPER_MAX_DIM:
            img_for_cropper.thumbnail((CROPPER_MAX_DIM, CROPPER_MAX_DIM))
        
        cropper_key = f"cropper_{uploaded_file_widget.name}_{uploaded_file_widget.size}"
        CROP_BOX_COLORS = {"赤":"#FF4500","黄":"#FFD700","シアン":"#00FFFF","白":"#FFFFFF"}
        selected_cropper_color_hex = CROP_BOX_COLORS[st.session_state.cropper_box_color_name]

        cropped_img = st_cropper(
            img_for_cropper, 
            realtime_update=True, 
            box_color=selected_cropper_color_hex, 
            aspect_ratio=None,
            key=cropper_key
        )
        st.session_state.pil_image_to_process = cropped_img
    
    with col_options:
        with st.container(border=True):
            st.subheader("枠のオプション", divider="rainbow")
            st.radio(
                "トリミング枠の色を選択",
                options=list(CROP_BOX_COLORS.keys()),
                key="cropper_box_color_name",
            )
    
    # --- サイドバーのパラメータ設定UI ---
    st.sidebar.subheader("1. 二値化")
    st.sidebar.markdown("_この値を調整して、輝点と背景を分離します。_")
    st.sidebar.slider('閾値 (スライダーで調整)',min_value=0,max_value=255,step=1,value=st.session_state.binary_threshold_value,key="threshold_slider_for_binary",on_change=sync_threshold_from_slider)
    st.sidebar.number_input('閾値 (直接入力)',min_value=0,max_value=255,step=1,value=st.session_state.binary_threshold_value,key="threshold_number_for_binary",on_change=sync_threshold_from_number_input)
    threshold_value_to_use = st.session_state.binary_threshold_value
    st.sidebar.subheader("2. 形態学的処理")
    kernel_size_morph_to_use =st.sidebar.select_slider('カーネルサイズ',options=[1,3,5,7,9],value=1)
    erosion_iterations = 1 
    st.sidebar.caption("""- **小さくすると:** 輝点への影響は少なくなりますが、小さなノイズが残りやすくなります。\n- **大きくすると:** ノイズ除去や輝点の分離効果は高まりますが、輝点自体が削られて消えてしまうことがあります。""")
    st.sidebar.subheader("3. 輝点フィルタリング (面積)")
    min_area_to_use = st.sidebar.number_input('最小面積',min_value=1,max_value=10000,step=1,value=1)
    max_area_to_use = st.sidebar.number_input('最大面積',min_value=1,max_value=100000,step=1,value=10000)
    st.sidebar.subheader("4. 表示設定")
    CONTOUR_COLORS = {"緑":"#28a745","青":"#007bff","赤":"#dc3545","黄":"#ffc107","シアン":"#17a2b8","ピンク":"#e83e8c"}
    st.sidebar.radio("輝点マーキング色を選択",options=list(CONTOUR_COLORS.keys()),key="contour_color_name",horizontal=True)
    selected_name = st.session_state.contour_color_name
    selected_hex = CONTOUR_COLORS[selected_name]
    contour_color_bgr = hex_to_bgr(selected_hex)

    # --- メインエリアの画像処理と表示ロジック ---
    st.markdown("---")
    st.header("解析結果の比較")
    original_img_to_display_np_uint8 = None; img_gray = None                         
    try:
        pil_image_rgb = st.session_state.pil_image_to_process.convert("RGB")
        original_img_to_display_np_uint8 = np.array(pil_image_rgb).astype(np.uint8)
        img_gray = cv2.cvtColor(original_img_to_display_np_uint8, cv2.COLOR_RGB2GRAY)
    except Exception as e:
        st.error(f"トリミング後の画像の基本変換に失敗: {e}"); st.session_state.counted_spots_value="変換エラー"; st.stop() 
    
    morph_kernel_shape_to_use = cv2.MORPH_ELLIPSE
    kernel_size_blur=1; blurred_img = cv2.GaussianBlur(img_gray, (kernel_size_blur,kernel_size_blur),0)
    ret_thresh, binary_img = cv2.threshold(blurred_img,threshold_value_to_use,255,cv2.THRESH_BINARY)
    if not ret_thresh: st.error("二値化失敗。"); st.stop()
    
    kernel_morph_obj=cv2.getStructuringElement(morph_kernel_shape_to_use,(kernel_size_morph_to_use,kernel_size_morph_to_use))
    eroded_img = cv2.erode(binary_img, kernel_morph_obj, iterations=erosion_iterations)
    opened_img = cv2.dilate(eroded_img, kernel_morph_obj, iterations=erosion_iterations)
    binary_img_for_contours = opened_img.copy()
    current_counted_spots = 0 
    output_image_contours_display = cv2.cvtColor(original_img_to_display_np_uint8, cv2.COLOR_RGB2BGR) 
    contours, hierarchy = cv2.findContours(binary_img_for_contours,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    if 'contours' in locals() and contours: 
        for contour in contours:
            area = cv2.contourArea(contour)
            if min_area_to_use <= area <= max_area_to_use: 
                current_counted_spots += 1
                cv2.drawContours(output_image_contours_display, [contour], -1, contour_color_bgr, 2) 
    st.session_state.counted_spots_value = current_counted_spots 
    
    # --- 表示エリア ---
    col1_res, col2_res = st.columns(2)
    with col1_res:
        st.subheader("元の画像 (トリミング後)")
        if original_img_to_display_np_uint8 is not None:
            st.image(original_img_to_display_np_uint8, caption=f"処理対象エリア (サイズ: {original_img_to_display_np_uint8.shape[1]}x{original_img_to_display_np_uint8.shape[0]})", use_container_width=True)
            
    with col2_res:
        st.subheader("輝点検出とマーキング")
        display_final_marked_image_rgb = cv2.cvtColor(output_image_contours_display, cv2.COLOR_BGR2RGB)
        caption_text = f'検出輝点({current_counted_spots}個)'
        st.image(display_final_marked_image_rgb, caption=caption_text, use_container_width=True)

    st.markdown("---")
    with st.expander("▼ 中間処理の画像を見る"):
        st.subheader("1. 二値化処理後")
        st.image(binary_img,caption=f'閾値:{threshold_value_to_use}')
        st.subheader("2. 形態学的処理後")
        st.image(opened_img,caption=f'カーネル: 楕円 {kernel_size_morph_to_use}x{erosion_iterations}回')
else: 
    st.info("まず、サイドバーから画像ファイルをアップロードしてください。")

display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value)
