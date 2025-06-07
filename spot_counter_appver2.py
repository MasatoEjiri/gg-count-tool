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
if 'pil_image_to_process' not in st.session_state: st.session_state.pil_image_to_process = None
if 'image_source_caption' not in st.session_state: st.session_state.image_source_caption = "アップロードされた画像"


# --- コールバック関数の定義 (二値化閾値同期用) ---
def sync_threshold_from_slider():
    st.session_state.binary_threshold_value = st.session_state.threshold_slider_for_binary
    st.session_state.threshold_number_for_binary = st.session_state.threshold_slider_for_binary
def sync_threshold_from_number_input():
    st.session_state.binary_threshold_value = st.session_state.threshold_number_for_binary
    st.session_state.threshold_slider_for_binary = st.session_state.threshold_number_for_binary

# --- サイドバーの基本部分 (常に表示) ---
display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value) 
st.sidebar.header("解析パラメータ設定")
UPLOAD_ICON = "📤" 
uploaded_file_widget = st.sidebar.file_uploader(f"{UPLOAD_ICON} 画像をアップロード", type=['tif', 'tiff', 'png', 'jpg', 'jpeg'], help="対応形式: TIF, TIFF, PNG, JPG, JPEG。")

# アプリのメインタイトルと使用方法 (メインエリア)
st.markdown("<h1>Gra&Green<br>輝点カウントツール</h1>", unsafe_allow_html=True)
st.markdown("""### 使用方法
1. 画像を左にアップロードしてください。
2. 画像をアップロードすると、左サイドバーに詳細な解析パラメータが表示されます。
3. まず「1. コントラスト強調」や「2. 二値化」の閾値を動かし、処理後の画像が実物に近い見え方になるよう調整してください。
4. 必要に応じて「3. 形態学的処理」や「4. 輝点フィルタリング」のパラメータも調整します。
""")
st.markdown("---") 

# 画像読み込みロジック
if uploaded_file_widget is not None:
    try:
        uploaded_file_bytes = uploaded_file_widget.getvalue()
        pil_img = Image.open(io.BytesIO(uploaded_file_bytes))
        st.session_state.pil_image_to_process = pil_img
        st.session_state.image_source_caption = f"アップロード: {uploaded_file_widget.name}"
    except Exception as e:
        st.sidebar.error(f"アップロード画像の読み込みに失敗: {e}")
        st.session_state.pil_image_to_process = None 
        st.session_state.counted_spots_value = "読込エラー"; st.stop()
else: 
    if st.session_state.pil_image_to_process is not None: 
        st.session_state.pil_image_to_process = None
        st.session_state.counted_spots_value = "---" 

# メイン処理と、条件付きでのサイドバーパラメータUI表示
if st.session_state.pil_image_to_process is not None:
    # --- サイドバーのパラメータ設定UI (画像ロード後に表示) ---
    # ★★★ 1. コントラスト強調 (CLAHE) ★★★
    st.sidebar.subheader("1. コントラスト強調 (CLAHE)")
    apply_clahe = st.sidebar.checkbox("CLAHEを適用する", value=False)
    clahe_clip_limit = 2.0
    clahe_tile_size = 8
    if apply_clahe:
        clahe_clip_limit = st.sidebar.slider("クリップ制限", 1.0, 10.0, 2.0, 0.5, help="値を大きくするとコントラストが強くなります。")
        clahe_tile_size = st.sidebar.slider("タイルグリッドサイズ", 2, 16, 8, 1, help="値を大きくすると、より局所的な範囲のコントラストを強調します。")

    st.sidebar.subheader("2. 二値化") # 番号を更新
    st.sidebar.markdown("_この値を色々変更して、「2. 二値化処理後」画像を実物に近づけてください。_")
    st.sidebar.slider('閾値 (スライダーで調整)',min_value=0,max_value=255,step=1,
                      value=st.session_state.binary_threshold_value, 
                      key="threshold_slider_for_binary",on_change=sync_threshold_from_slider)
    st.sidebar.number_input('閾値 (直接入力)',min_value=0,max_value=255,step=1,
                            value=st.session_state.binary_threshold_value, 
                            key="threshold_number_for_binary",on_change=sync_threshold_from_number_input)
    threshold_value_to_use = st.session_state.binary_threshold_value 
    st.sidebar.caption("""- **大きくすると:** 明るい部分のみ白に。\n- **小さくすると:** 暗い部分も白に。""")
    st.sidebar.markdown("<br>", unsafe_allow_html=True); st.sidebar.markdown("_二値化だけでうまくいかない場合は下記も調整を_")
    
    st.sidebar.subheader("3. 形態学的処理 (オープニング)") # 番号を更新
    morph_kernel_shape_to_use = cv2.MORPH_ELLIPSE 
    kernel_options_morph = [1,3,5,7,9]
    kernel_size_morph_to_use =st.sidebar.select_slider('カーネルサイズ',options=kernel_options_morph, 
                                                      value=3) 
    st.sidebar.caption("""オープニング処理で小さなノイズ除去や輝点分離を行います。\n- **大きくすると:** 効果が強くなりますが、輝点も消えることがあります。\n- **小さくすると:** 効果は弱く、輝点への影響は少ないです。""")
    
    st.sidebar.subheader("4. 輝点フィルタリング (面積)") # 番号を更新
    min_area_to_use = st.sidebar.number_input('最小面積',min_value=1,max_value=10000,step=1, 
                                          value=1) 
    st.sidebar.caption("""- **大きくすると:** 小さな輝点を除外。\n- **小さくすると:** ノイズを拾う可能性。(画像リサイズ時注意)""") 
    max_area_to_use = st.sidebar.number_input('最大面積',min_value=1,max_value=100000,step=1, 
                                          value=10000) 
    st.sidebar.caption("""- **大きくすると:** 大きな塊もカウント。\n- **小さくすると:** 大きな塊を除外。(画像リサイズ時注意)""") 

    # --- メインエリアの画像処理と表示ロジック ---
    original_img_to_display_np_uint8 = None; img_gray = None                         
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
        st.error(f"画像の基本変換に失敗: {e}"); st.session_state.counted_spots_value="変換エラー"; st.stop() 
    
    st.header("処理ステップごとの画像")
    
    # ★★★ コントラスト強調 (CLAHE) 処理 ★★★
    img_for_binarization = img_gray.copy() # 次のステップに渡す画像
    if apply_clahe:
        clahe = cv2.createCLAHE(clipLimit=clahe_clip_limit, tileGridSize=(clahe_tile_size, clahe_tile_size))
        img_for_binarization = clahe.apply(img_gray)
    
    # 画像処理パイプラインの開始
    kernel_size_blur = 1 
    if img_for_binarization is None or img_for_binarization.size == 0 : 
        st.error("グレースケール画像準備失敗。"); st.session_state.counted_spots_value="処理エラー"; st.stop()
        
    blurred_img = cv2.GaussianBlur(img_for_binarization, (kernel_size_blur,kernel_size_blur),0)
    ret_thresh, binary_img_processed = cv2.threshold(blurred_img,threshold_value_to_use,255,cv2.THRESH_BINARY)
    if not ret_thresh: st.error("二値化失敗。"); binary_img_for_morph_processed=None
    else: binary_img_for_morph_processed=binary_img_processed.copy()
    opened_img_processed = None 
    if binary_img_for_morph_processed is not None:
        kernel_morph_obj=cv2.getStructuringElement(morph_kernel_shape_to_use,(kernel_size_morph_to_use,kernel_size_morph_to_use))
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
                if min_area_to_use <= area <= max_area_to_use: 
                    current_counted_spots += 1
                    cv2.drawContours(output_image_contours_display, [contour], -1, (255,0,0), 2) # マーキング色は現在青固定
        st.session_state.counted_spots_value = current_counted_spots 
    else:
        st.warning("輪郭検出元画像準備できず。"); st.session_state.counted_spots_value="エラー"
    
    st.subheader("元の画像")
    if original_img_to_display_np_uint8 is not None:
        st.image(original_img_to_display_np_uint8, caption=st.session_state.image_source_caption, use_container_width=True)
    st.markdown("---")
    
    # ★★★ コントラスト強調後の画像表示ステップを追加 ★★★
    st.subheader("1. コントラスト強調後 (CLAHE適用時)")
    if apply_clahe:
        st.image(img_for_binarization, caption=f"クリップ制限: {clahe_clip_limit}, タイルサイズ: {clahe_tile_size}", use_container_width=True)
    else:
        st.info("コントラスト強調(CLAHE)は適用されていません。")
    st.markdown("---")

    st.subheader("2. 二値化処理後") # 番号を更新
    if binary_img_processed is not None: st.image(binary_img_processed,caption=f'閾値:{threshold_value_to_use}',use_container_width=True)
    else: st.info("二値化未実施/失敗")
    st.markdown("---")
    with st.expander("▼ 3. 形態学的処理後を見る", expanded=False): # 番号を更新
        if opened_img_processed is not None: 
            st.image(opened_img_processed,caption=f'カーネル: 楕円 {kernel_size_morph_to_use}x{kernel_size_morph_to_use}',use_container_width=True)
        else: st.info("形態学的処理未実施/失敗")
    st.markdown("---") 
    st.subheader("4. 輝点検出とマーキング") # 番号を更新
    display_final_marked_image_rgb = cv2.cvtColor(output_image_contours_display, cv2.COLOR_BGR2RGB)
    if 'contours' in locals() and contours and binary_img_for_contours_processed is not None and current_counted_spots > 0 :
         st.image(display_final_marked_image_rgb,caption=f'検出輝点(青い輪郭,面積:{min_area_to_use}-{max_area_to_use})',use_container_width=True)
    elif binary_img_for_contours_processed is not None: 
        st.image(display_final_marked_image_rgb,caption='輝点見つからず',use_container_width=True)
    else: st.info("輝点検出未実施")
else: 
    st.info("まず、サイドバーから画像ファイルをアップロードしてください。")

display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value)
