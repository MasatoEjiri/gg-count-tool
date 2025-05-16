import streamlit as st
from PIL import Image
import numpy as np
import cv2
import io

# ページ設定 (一番最初に呼び出す)
st.set_page_config(page_title="輝点解析ツール", layout="wide")

# --- サイドバーの上部に結果表示用のプレースホルダーを定義 ---
result_placeholder_sidebar = st.sidebar.empty() 

# --- カスタマイズされた結果表示関数 (サイドバー表示用、スティッキー対応) ---
def display_count_in_sidebar(placeholder, count_value):
    label_text = "【解析結果】輝点数" 
    value_text = str(count_value) 
    background_color = "#495057"; label_font_color = "white"; value_font_color = "white"
    # border_color = "#343a40"; 

    html_content = f"""
    <div style="
        position: -webkit-sticky; /* Safari 向け */
        position: sticky;         /* 標準 */
        top: 0px;                 /* サイドバーの上端に固定 */
        z-index: 100;             /* 他のサイドバー要素より手前に表示 */
        background-color: {background_color}; /* 背景色で下のコンテンツを隠す */
        border-radius: 8px; 
        padding: 15px; 
        text-align: center; 
        margin-bottom: 15px; /* この要素の下の要素との間隔 */
        color: {label_font_color}; 
    ">
        <p style="font-size:16px; margin-bottom:5px; font-weight:bold;">{label_text}</p>
        <p style="font-size:48px; font-weight:bold; margin-top:0px; color:{value_font_color}; line-height:1.1;">{value_text}</p>
    </div>"""
    placeholder.markdown(html_content, unsafe_allow_html=True)


# --- セッションステートの初期化 ---
if 'counted_spots_value' not in st.session_state: st.session_state.counted_spots_value = "---" 
if "binary_threshold_value" not in st.session_state: st.session_state.binary_threshold_value = 58
if "threshold_slider_for_binary" not in st.session_state: st.session_state.threshold_slider_for_binary = st.session_state.binary_threshold_value
if "threshold_number_for_binary" not in st.session_state: st.session_state.threshold_number_for_binary = st.session_state.binary_threshold_value
if "morph_shape_sb_key" not in st.session_state:
    morph_kernel_shape_options_init = {"楕円":cv2.MORPH_ELLIPSE,"矩形":cv2.MORPH_RECT,"十字":cv2.MORPH_CROSS}
    st.session_state.morph_shape_sb_key = list(morph_kernel_shape_options_init.keys())[0] 
if "morph_size_sb_key" not in st.session_state:
    st.session_state.morph_size_sb_key = 3
if "min_area_sb_key" not in st.session_state:
    st.session_state.min_area_sb_key = 1 
if "max_area_sb_key" not in st.session_state:
    st.session_state.max_area_sb_key = 1000
if 'pil_image_to_process' not in st.session_state: st.session_state.pil_image_to_process = None
if 'image_source_caption' not in st.session_state: st.session_state.image_source_caption = "アップロードされた画像"


# --- コールバック関数の定義 ---
def sync_threshold_from_slider():
    st.session_state.binary_threshold_value = st.session_state.threshold_slider_for_binary
    st.session_state.threshold_number_for_binary = st.session_state.threshold_slider_for_binary
def sync_threshold_from_number_input():
    st.session_state.binary_threshold_value = st.session_state.threshold_number_for_binary
    st.session_state.threshold_slider_for_binary = st.session_state.threshold_number_for_binary

# --- サイドバーの定義開始 ---
display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value) 

st.sidebar.header("解析パラメータ設定")
UPLOAD_ICON = "📤" 
uploaded_file_widget = st.sidebar.file_uploader(f"{UPLOAD_ICON} 画像をアップロード", type=['tif', 'tiff', 'png', 'jpg', 'jpeg'], help="対応形式: TIF, TIFF, PNG, JPG, JPEG。")

# サイドバーのパラメータ設定UI
st.sidebar.subheader("1. 二値化") 
st.sidebar.markdown("_この値を色々と変更して、「1. 二値化処理後」画像を実物に近づけてください。_")
st.sidebar.slider('閾値 (スライダーで調整)', min_value=0,max_value=255,step=1,key="threshold_slider_for_binary",on_change=sync_threshold_from_slider)
st.sidebar.number_input('閾値 (直接入力)', min_value=0,max_value=255,step=1,key="threshold_number_for_binary",on_change=sync_threshold_from_number_input)
threshold_value_sb = st.session_state.binary_threshold_value 
st.sidebar.caption("""- **大きくすると:** 明るい部分のみ白に。\n- **小さくすると:** 暗い部分も白に。""")
st.sidebar.markdown("<br>", unsafe_allow_html=True) 
st.sidebar.markdown("_二値化操作だけでうまくいかない場合は下記設定も変更してみてください。_") 
st.sidebar.subheader("2. 形態学的処理 (オープニング)") 
morph_kernel_shape_options_display = {"楕円":cv2.MORPH_ELLIPSE,"矩形":cv2.MORPH_RECT,"十字":cv2.MORPH_CROSS}
selected_shape_name_sb = st.sidebar.selectbox("カーネル形状",options=list(morph_kernel_shape_options_display.keys()), key="morph_shape_sb_key") 
morph_kernel_shape_sb = morph_kernel_shape_options_display[selected_shape_name_sb]
st.sidebar.caption("輝点の形状に合わせて。") 
kernel_options_morph = [1,3,5,7,9]; kernel_size_morph_sb =st.sidebar.select_slider('カーネルサイズ',options=kernel_options_morph, key="morph_size_sb_key")
st.sidebar.caption("""- **大きくすると:** 効果強、輝点も影響あり。\n- **小さくすると:** 効果弱。""") 
st.sidebar.subheader("3. 輝点フィルタリング (面積)") 
min_area_sb = st.sidebar.number_input('最小面積',min_value=1,max_value=10000,step=1, key="min_area_sb_key") 
st.sidebar.caption("""- **大きくすると:** 小さな輝点を除外。\n- **小さくすると:** ノイズを拾う可能性。(画像リサイズ時注意)""") 
max_area_sb = st.sidebar.number_input('最大面積',min_value=1,max_value=100000,step=1, key="max_area_sb_key") 
st.sidebar.caption("""- **大きくすると:** 大きな塊もカウント。\n- **小さくすると:** 大きな塊を除外。(画像リサイズ時注意)""") 


# --- アプリのメインタイトルと使用方法 (メインエリア) ---
st.markdown("<h1>Gra&Green<br>輝点カウントツール</h1>", unsafe_allow_html=True)
st.markdown("""
### 使用方法
1. 画像を左にアップロードしてください。
2. 左サイドバーの「1. 二値化」の閾値を動かして、「1. 二値化処理後」の画像が、輝点と背景が適切に分離された状態（実物に近い見え方）になるように調整してください。
3. （それでもカウント値がおかしい場合は、サイドバーの「2. 形態学的処理」や「3. 輝点フィルタリング」の各パラメータも調整してみてください。）
""")
st.markdown("---") 


# --- 画像読み込みロジック (ファイルアップロードのみ) ---
if uploaded_file_widget is not None:
    try:
        uploaded_file_bytes = uploaded_file_widget.getvalue()
        pil_img = Image.open(io.BytesIO(uploaded_file_bytes))
        st.session_state.pil_image_to_process = pil_img
        st.session_state.image_source_caption = f"アップロード: {uploaded_file_widget.name}"
    except Exception as e:
        st.sidebar.error(f"アップロード画像の読み込みに失敗: {e}")
        st.session_state.pil_image_to_process = None 
        st.stop()


# --- メイン処理 (st.session_state.pil_image_to_process があれば実行) ---
if st.session_state.pil_image_to_process is not None:
    original_img_to_display_np_uint8 = None 
    img_gray = None                         
    try:
        pil_image_rgb = st.session_state.pil_image_to_process.convert("RGB")
        temp_np_array = np.array(pil_image_rgb)
        if temp_np_array.dtype != np.uint8:
            if np.issubdtype(temp_np_array.dtype, np.floating):
                if temp_np_array.min() >= 0.0 and temp_np_array.max() <= 1.0:
                    original_img_to_display_np_uint8 = (temp_np_array * 255).astype(np.uint8)
                else: original_img_to_display_np_uint8 = np.clip(temp_np_array, 0, 255).astype(np.uint8)
            elif np.issubdtype(temp_np_array.dtype, np.integer): 
                original_img_to_display_np_uint8 = np.clip(temp_np_array, 0, 255).astype(np.uint8)
            else: original_img_to_display_np_uint8 = temp_np_array.astype(np.uint8)
        else: original_img_to_display_np_uint8 = temp_np_array
        img_gray = cv2.cvtColor(original_img_to_display_np_uint8, cv2.COLOR_RGB2GRAY)
        if img_gray.dtype != np.uint8: img_gray = img_gray.astype(np.uint8)
    except Exception as e:
        st.error(f"画像の基本変換に失敗しました: {e}"); st.stop() 
    
    st.header("処理ステップごとの画像")
    kernel_size_blur = 1 
    if img_gray is None or img_gray.size == 0 : 
        st.error("グレースケール画像の準備に失敗しました。"); st.stop()
    blurred_img = cv2.GaussianBlur(img_gray, (kernel_size_blur,kernel_size_blur),0)
    ret_thresh, binary_img_processed = cv2.threshold(blurred_img,threshold_value_sb,255,cv2.THRESH_BINARY)
    if not ret_thresh: st.error("二値化失敗。"); binary_img_for_morph_processed=None
    else: binary_img_for_morph_processed=binary_img_processed.copy()
    opened_img_processed = None 
    if binary_img_for_morph_processed is not None:
        kernel_morph_obj=cv2.getStructuringElement(morph_kernel_shape_sb,(kernel_size_morph_sb,kernel_size_morph_sb))
        opened_img_processed=cv2.morphologyEx(binary_img_for_morph_processed,cv2.MORPH_OPEN,kernel_morph_obj)
        binary_img_for_contours_processed = opened_img_processed.copy()
    else: binary_img_for_contours_processed = None
    current_counted_spots = 0 
    output_image_contours_display = cv2.cvtColor(original_img_to_display_np_uint8, cv2.COLOR_RGB2BGR) 
    if binary_img_for_contours_processed is not None:
        contours, hierarchy = cv2.findContours(binary_img_for_contours_processed,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        if 'contours' in locals() and contours: 
            for contour in contours:
                area = cv2.contourArea(contour)
                if st.session_state.min_area_sb_key <= area <= st.session_state.max_area_sb_key: 
                    current_counted_spots += 1
                    cv2.drawContours(output_image_contours_display, [contour], -1, (255,0,0), 2) 
        st.session_state.counted_spots_value = current_counted_spots 
    else:
        st.warning("輪郭検出の元画像準備できず。"); st.session_state.counted_spots_value="エラー"
    
    st.subheader("元の画像")
    if original_img_to_display_np_uint8 is not None:
        st.image(original_img_to_display_np_uint8, caption=st.session_state.image_source_caption, use_container_width=True)
    st.markdown("---")
    st.subheader("1. 二値化処理後")
    if binary_img_processed is not None: st.image(binary_img_processed,caption=f'閾値:{threshold_value_sb}',use_container_width=True)
    else: st.info("二値化未実施/失敗")
    st.markdown("---")
    with st.expander("▼ 2. 形態学的処理後を見る", expanded=False): 
        if opened_img_processed is not None: 
            st.image(opened_img_processed,caption=f'カーネル:{st.session_state.morph_shape_sb_key} {st.session_state.morph_size_sb_key}x{st.session_state.morph_size_sb_key}',use_container_width=True)
        else: st.info("形態学的処理未実施/失敗")
    st.markdown("---") 
    st.subheader("3. 輝点検出とマーキング")
    display_final_marked_image_rgb = cv2.cvtColor(output_image_contours_display, cv2.COLOR_BGR2RGB)
    if 'contours' in locals() and contours and binary_img_for_contours_processed is not None and current_counted_spots > 0 :
         st.image(display_final_marked_image_rgb,caption=f'検出輝点(青い輪郭,面積:{st.session_state.min_area_sb_key}-{st.session_state.max_area_sb_key})',use_container_width=True)
    elif binary_img_for_contours_processed is not None: 
        st.image(display_final_marked_image_rgb,caption='輝点見つからず',use_container_width=True)
    else: st.info("輝点検出未実施")

    display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value) 
else: 
    # display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value) # 初期表示はスクリプト上部で行う
    st.info("まず、サイドバーから画像ファイルをアップロードしてください。")
