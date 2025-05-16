import streamlit as st
from PIL import Image
import numpy as np
import cv2
import io

# ページ設定 (一番最初に呼び出す)
st.set_page_config(page_title="輝点解析ツール", layout="wide")

# ★★★ キャッシュする画像読み込み関数を定義 ★★★
@st.cache_data # 同じバイトデータに対してはキャッシュされた結果を返す
def load_and_prepare_image_data(uploaded_file_bytes, uploaded_file_name_for_caption):
    pil_image_original = Image.open(io.BytesIO(uploaded_file_bytes))
    pil_image_rgb = pil_image_original.convert("RGB")
    
    temp_np_array = np.array(pil_image_rgb)
    original_img_to_display_np_uint8 = None
    if temp_np_array.dtype != np.uint8:
        if np.issubdtype(temp_np_array.dtype, np.floating):
            if temp_np_array.min() >= 0.0 and temp_np_array.max() <= 1.0:
                original_img_to_display_np_uint8 = (temp_np_array * 255).astype(np.uint8)
            else: 
                original_img_to_display_np_uint8 = np.clip(temp_np_array, 0, 255).astype(np.uint8)
        elif np.issubdtype(temp_np_array.dtype, np.integer): 
            original_img_to_display_np_uint8 = np.clip(temp_np_array, 0, 255).astype(np.uint8)
        else: 
            original_img_to_display_np_uint8 = temp_np_array.astype(np.uint8)
    else: 
        original_img_to_display_np_uint8 = temp_np_array
    
    img_gray = cv2.cvtColor(original_img_to_display_np_uint8, cv2.COLOR_RGB2GRAY)
    if img_gray.dtype != np.uint8: 
        img_gray = img_gray.astype(np.uint8)
    
    # キャプションもここで生成して返す（st.session_stateに依存しないように）
    image_caption = f"アップロード: {uploaded_file_name_for_caption}"
    return original_img_to_display_np_uint8, img_gray, image_caption


# --- サイドバーの上部に結果表示用のプレースホルダーを定義 ---
result_placeholder_sidebar = st.sidebar.empty() 

# --- カスタマイズされた結果表示関数 (サイドバー表示用) ---
def display_count_in_sidebar(placeholder, count_value):
    label_text = "【解析結果】輝点数"; value_text = str(count_value) 
    bg="#495057"; lf="white"; vf="white"
    html=f"""<div style="border-radius:8px; padding:15px; text-align:center; background-color:{bg}; margin-bottom:15px; color:{lf};"><p style="font-size:16px; margin-bottom:5px; font-weight:bold;">{label_text}</p><p style="font-size:48px; font-weight:bold; margin-top:0px; color:{vf}; line-height:1.1;">{value_text}</p></div>"""
    placeholder.markdown(html, unsafe_allow_html=True)

# アプリのタイトル (メインエリア)
st.markdown("<h1>Gra&Green<br>輝点カウントツール</h1>", unsafe_allow_html=True)

# 「使用方法」(メインエリア)
st.markdown("""
### 使用方法
1. 画像を左にアップロードしてください。
2. 左サイドバーのパラメータを調整し、メインエリアの「4. 輝点検出とマーキング」で輝点が正しく検出されるようにしてください。
3. 特に「1. ノイズ除去」と「2. 二値化」の設定が重要です。各ステップの画像を下の折りたたみセクションで確認しながら調整します。
""") # 使用方法を少し調整
st.markdown("---") 

# --- セッションステートの初期化 ---
if 'counted_spots_value' not in st.session_state: st.session_state.counted_spots_value = "---" 
if "binary_threshold_value" not in st.session_state: st.session_state.binary_threshold_value = 58
if "threshold_slider_for_binary" not in st.session_state: st.session_state.threshold_slider_for_binary = st.session_state.binary_threshold_value
if "threshold_number_for_binary" not in st.session_state: st.session_state.threshold_number_for_binary = st.session_state.binary_threshold_value
# pil_image_to_process と image_source_caption はキャッシュ関数から返されるのでセッションステートは不要に

# --- コールバック関数の定義 ---
def sync_threshold_from_slider():
    st.session_state.binary_threshold_value = st.session_state.threshold_slider_for_binary
    st.session_state.threshold_number_for_binary = st.session_state.threshold_slider_for_binary
def sync_threshold_from_number_input():
    st.session_state.binary_threshold_value = st.session_state.threshold_number_for_binary
    st.session_state.threshold_slider_for_binary = st.session_state.threshold_number_for_binary

# --- サイドバー ---
st.sidebar.header("解析パラメータ設定")
UPLOAD_ICON = "📤" 
uploaded_file_widget = st.sidebar.file_uploader(f"{UPLOAD_ICON} 画像をアップロード", type=['tif', 'tiff', 'png', 'jpg', 'jpeg'], help="対応形式: TIF, TIFF, PNG, JPG, JPEG。")

display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value) # 初期表示

# サイドバーのパラメータ設定UI (画像がアップロードされていなくても表示する)
st.sidebar.subheader("1. ノイズ除去 (ガウシアンブラー)") # ★★★ ヘッダー番号修正 ★★★
kernel_options_blur = [1, 3, 5, 7, 9, 11, 13, 15]
kernel_size_blur_sb = st.sidebar.select_slider( # 変数名変更 _sb
    'カーネルサイズ (奇数を選択)', options=kernel_options_blur, value=3, key="blur_kernel_size_slider"
)
st.sidebar.caption("""- **大きくすると:** ぼかしが強くなりノイズが減りますが、輝点もぼやけます。\n- **小さくすると:** ぼかしが弱く、輪郭はシャープですがノイズが残りやすいです。(1はほぼ効果なし)""")

st.sidebar.subheader("2. 二値化") # ★★★ ヘッダー番号修正 ★★★
st.sidebar.markdown("_この値を色々変更して、「二値化処理後」画像を実物に近づけてください。_")
st.sidebar.slider('閾値 (スライダーで調整)', min_value=0,max_value=255,step=1,value=st.session_state.binary_threshold_value,key="threshold_slider_for_binary",on_change=sync_threshold_from_slider)
st.sidebar.number_input('閾値 (直接入力)', min_value=0,max_value=255,step=1,value=st.session_state.binary_threshold_value,key="threshold_number_for_binary",on_change=sync_threshold_from_number_input)
threshold_value_sb = st.session_state.binary_threshold_value # 変数名変更 _sb
st.sidebar.caption("""- **大きくすると:** 明るい部分のみ白に。\n- **小さくすると:** 暗い部分も白に。""")

st.sidebar.markdown("<br>", unsafe_allow_html=True); st.sidebar.markdown("_二値化だけでうまくいかない場合は下記も調整を_")

st.sidebar.subheader("3. 形態学的処理 (オープニング)") # ★★★ ヘッダー番号修正 ★★★
morph_kernel_shape_options = {"楕円":cv2.MORPH_ELLIPSE,"矩形":cv2.MORPH_RECT,"十字":cv2.MORPH_CROSS}
selected_shape_name_sb = st.sidebar.selectbox("カーネル形状",options=list(morph_kernel_shape_options.keys()),index=0, key="morph_shape_sb") 
morph_kernel_shape_sb = morph_kernel_shape_options[selected_shape_name_sb]
st.sidebar.caption("輝点の形状に合わせて。")
kernel_options_morph = [1,3,5,7,9]
kernel_size_morph_sb =st.sidebar.select_slider('カーネルサイズ',options=kernel_options_morph,value=3, key="morph_size_sb")
st.sidebar.caption("""- **大きくすると:** 効果強、輝点も影響あり。\n- **小さくすると:** 効果弱。""")

st.sidebar.subheader("4. 輝点フィルタリング (面積)") # ★★★ ヘッダー番号修正 ★★★
min_area_sb = st.sidebar.number_input('最小面積',min_value=1,max_value=10000,value=15,step=1, key="min_area_sb") 
st.sidebar.caption("""- **大きくすると:** 小さな輝点を除外。\n- **小さくすると:** ノイズを拾う可能性。""")
max_area_sb = st.sidebar.number_input('最大面積',min_value=1,max_value=100000,value=1000,step=1, key="max_area_sb") 
st.sidebar.caption("""- **大きくすると:** 大きな塊もカウント。\n- **小さくすると:** 大きな塊を除外。""")


# --- メイン処理 ---
if uploaded_file_widget is not None:
    uploaded_file_bytes = uploaded_file_widget.getvalue()
    try:
        original_img_to_display_np_uint8, img_gray, image_caption_from_load = load_and_prepare_image_data(uploaded_file_bytes, uploaded_file_widget.name)
    except Exception as e:
        st.error(f"画像の読み込みと準備に失敗: {e}")
        st.stop()
    
    st.header("処理ステップごとの画像")
            
    blurred_img = cv2.GaussianBlur(img_gray, (kernel_size_blur_sb, kernel_size_blur_sb),0) # サイドバーの値を使用

    ret_thresh, binary_img_processed = cv2.threshold(blurred_img, threshold_value_sb, 255, cv2.THRESH_BINARY) # サイドバーの値を使用
    if not ret_thresh: st.error("二値化失敗。"); binary_img_for_morph_processed=None
    else: binary_img_for_morph_processed=binary_img_processed.copy()
    
    opened_img_processed = None 
    if binary_img_for_morph_processed is not None:
        kernel_morph_obj=cv2.getStructuringElement(morph_kernel_shape_sb,(kernel_size_morph_sb,kernel_size_morph_sb)) # サイドバーの値を使用
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
                if min_area_sb <= area <= max_area_sb: # サイドバーの値を使用
                    current_counted_spots += 1
                    cv2.drawContours(output_image_contours_display, [contour], -1, (0,255,0), 2) 
        st.session_state.counted_spots_value = current_counted_spots 
    else:
        st.warning("輪郭検出の元画像準備できず。"); st.session_state.counted_spots_value="エラー"
    
    with st.expander("元の画像を見る", expanded=True):
        if original_img_to_display_np_uint8 is not None:
            st.image(original_img_to_display_np_uint8, caption=image_caption_from_load, use_container_width=True)
    
    with st.expander("1. ノイズ除去後 (ガウシアンブラー) を見る", expanded=False):
         st.image(blurred_img, caption=f'カーネル: {kernel_size_blur_sb}x{kernel_size_blur_sb}', use_container_width=True)

    with st.expander("2. 二値化処理後を見る", expanded=False):
        if binary_img_processed is not None: 
            st.image(binary_img_processed,caption=f'閾値:{threshold_value_sb}',use_container_width=True)
        else: st.info("二値化未実施/失敗")

    with st.expander("3. 形態学的処理後を見る", expanded=False):
        if opened_img_processed is not None: 
            st.image(opened_img_processed,caption=f'カーネル:{selected_shape_name_sb} {kernel_size_morph_sb}x{kernel_size_morph_sb}',use_container_width=True)
        else: st.info("形態学的処理未実施/失敗")

    st.subheader("4. 輝点検出とマーキング") # これは常に表示
    display_final_marked_image_rgb = cv2.cvtColor(output_image_contours_display, cv2.COLOR_BGR2RGB)
    if 'contours' in locals() and contours and binary_img_for_contours_processed is not None and current_counted_spots > 0 :
         st.image(display_final_marked_image_rgb,caption=f'検出輝点(緑輪郭,面積:{min_area_sb}-{max_area_sb})',use_container_width=True)
    elif binary_img_for_contours_processed is not None: 
        st.image(display_final_marked_image_rgb,caption='輝点見つからず',use_container_width=True)
    else: st.info("輝点検出未実施")

    display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value)

else: 
    st.info("まず、サイドバーから画像ファイルをアップロードしてください。")
    st.session_state.counted_spots_value = "---"
    display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value)
