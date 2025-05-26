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

# サイドバー結果表示
result_placeholder_sidebar = st.sidebar.empty() 
def display_count_in_sidebar(placeholder, count_value):
    label_text = "【解析結果】輝点数"; value_text = str(count_value) 
    bg="#495057"; lf="white"; vf="white"
    html=f"""<div style="border-radius:8px;padding:15px;text-align:center;background-color:{bg};margin-bottom:15px;color:{lf};"><p style="font-size:16px;margin-bottom:5px;font-weight:bold;">{label_text}</p><p style="font-size:48px;font-weight:bold;margin-top:0px;color:{vf};line-height:1.1;">{value_text}</p></div>"""
    with placeholder.container(): placeholder.markdown(html, unsafe_allow_html=True)

# セッションステート初期化
default_session_values = {
    'counted_spots_value': "---",
    "binary_threshold_value": 58, "threshold_slider_for_binary": 58, "threshold_number_for_binary": 58,
    'pil_image_to_process': None, 'image_source_caption': "アップロードされた画像",
    "crop_x": 0, "crop_y": 0, "crop_w": 0, "crop_h": 0, # 初期値は画像ロード後に設定
    "last_uploaded_filename_for_crop": None # 新しい画像か判定用
}
for key, value in default_session_values.items():
    if key not in st.session_state: st.session_state[key] = value

# 形態学的処理と面積フィルタのデフォルト値 (キーを使わないウィジェット用、これらはUI定義時にvalueで指定)
DEFAULT_MORPH_SHAPE = "楕円"
DEFAULT_MORPH_SIZE = 3
DEFAULT_MIN_AREA = 1
DEFAULT_MAX_AREA = 1000


# コールバック関数
def sync_threshold_from_slider():
    st.session_state.binary_threshold_value = st.session_state.threshold_slider_for_binary
    st.session_state.threshold_number_for_binary = st.session_state.threshold_slider_for_binary
def sync_threshold_from_number_input():
    st.session_state.binary_threshold_value = st.session_state.threshold_number_for_binary
    st.session_state.threshold_slider_for_binary = st.session_state.threshold_number_for_binary

# --- サイドバー基本UI ---
display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value) 
st.sidebar.header("解析パラメータ設定")
UPLOAD_ICON = "📤" 
uploaded_file_widget = st.sidebar.file_uploader(f"{UPLOAD_ICON} 画像をアップロード", type=['tif', 'tiff', 'png', 'jpg', 'jpeg'], help="対応形式: TIF, TIFF, PNG, JPG, JPEG。")

# --- メインエリア ---
st.markdown("<h1>Gra&Green<br>輝点カウントツール</h1>", unsafe_allow_html=True)
st.markdown("""### 使用方法
1. 画像を左にアップロードしてください。
2. (オプション)「1. 元の画像とトリミング設定」で解析したいエリアを数値で指定し、プレビューで確認します。指定しない場合は画像全体が対象です。
3. 画像（またはトリミング後の画像）を元に、左サイドバーの「1. 二値化」以降のパラメータを調整してください。
4. メインエリアの各処理ステップ画像と、最終的な「3. 輝点検出とマーキング」で結果を確認します。""")
st.markdown("---") 

# 画像読み込みと初期処理対象画像の設定
if uploaded_file_widget is not None:
    try:
        uploaded_file_bytes = uploaded_file_widget.getvalue()
        pil_img = Image.open(io.BytesIO(uploaded_file_bytes))
        st.session_state.pil_image_to_process = pil_img
        st.session_state.image_source_caption = f"アップロード: {uploaded_file_widget.name}"
        
        # ★★★ 新しい画像がアップロードされた場合、トリミングパラメータを画像全体にリセット ★★★
        if st.session_state.get("last_uploaded_filename_for_crop") != uploaded_file_widget.name:
            pil_rgb_for_dims = st.session_state.pil_image_to_process.convert("RGB")
            np_for_dims = np.array(pil_rgb_for_dims)
            h_orig, w_orig = np_for_dims.shape[:2]
            
            st.session_state.crop_x = 0
            st.session_state.crop_y = 0
            st.session_state.crop_w = w_orig
            st.session_state.crop_h = h_orig
            st.session_state.last_uploaded_filename_for_crop = uploaded_file_widget.name
            # st.experimental_rerun() # 必要ならリランしてウィジェットに即時反映

    except Exception as e:
        st.sidebar.error(f"アップロード画像の読み込みに失敗: {e}")
        st.session_state.pil_image_to_process = None 
        st.session_state.counted_spots_value = "読込エラー"; st.stop()
else: 
    if st.session_state.pil_image_to_process is not None: 
        st.session_state.pil_image_to_process = None
        st.session_state.counted_spots_value = "---" 
        st.session_state.last_uploaded_filename_for_crop = None # 画像がクリアされたらファイル名もリセット


# --- メイン処理 (処理対象のPillowイメージがあれば実行) ---
if st.session_state.pil_image_to_process is not None:
    # --- 1. 元の画像表示とトリミング設定 ---
    st.header("1. 元の画像 と トリミング設定")
    try:
        pil_image_rgb_full = st.session_state.pil_image_to_process.convert("RGB")
        full_img_np_rgb_uint8 = np.array(pil_image_rgb_full).astype(np.uint8) # uint8に変換
        full_img_h, full_img_w = full_img_np_rgb_uint8.shape[:2]
    except Exception as e:
        st.error(f"画像変換中にエラー (フル): {e}"); st.stop()

    # トリミングパラメータ入力UI
    with st.expander("トリミング範囲を設定する (オプション)", expanded=True): # 最初から開いておく
        st.write(f"元画像サイズ: 幅={full_img_w}px, 高さ={full_img_h}px")
        col_crop1, col_crop2 = st.columns(2)
        
        with col_crop1:
            # X入力。変更時にWを調整するコールバックは複雑なので、今回はmax_valueで制御し、
            # W入力時に session_state.crop_w をさらに調整する
            new_crop_x = st.number_input("切り抜き開始 X座標", 0, full_img_w - 1, st.session_state.crop_x, key="crop_x_ui")
            if new_crop_x != st.session_state.crop_x: # ユーザーがXを変更した場合
                st.session_state.crop_x = new_crop_x
                # Xが変わったらWの最大値も変わるので、Wを再評価・調整する必要がある
                max_w_possible = full_img_w - st.session_state.crop_x
                if st.session_state.crop_w > max_w_possible:
                    st.session_state.crop_w = max_w_possible
                if st.session_state.crop_w < 1: st.session_state.crop_w = 1
                # st.experimental_rerun() # 即時反映のため

            max_w_for_widget = full_img_w - st.session_state.crop_x
            # W入力の前に、現在のセッションステートのWが新しいmax_wを超えていないか確認・調整
            if st.session_state.crop_w > max_w_for_widget:
                st.session_state.crop_w = max_w_for_widget
            if st.session_state.crop_w < 1 and max_w_for_widget >=1 : st.session_state.crop_w = 1
            elif max_w_for_widget < 1: st.session_state.crop_w = max_w_for_widget # 幅が0になることもありうる

            st.number_input("切り抜き幅", 1, max_w_for_widget if max_w_for_widget >=1 else 1, key="crop_w") # valueはセッションステートから

        with col_crop2:
            new_crop_y = st.number_input("切り抜き開始 Y座標", 0, full_img_h - 1, st.session_state.crop_y, key="crop_y_ui")
            if new_crop_y != st.session_state.crop_y:
                st.session_state.crop_y = new_crop_y
                max_h_possible = full_img_h - st.session_state.crop_y
                if st.session_state.crop_h > max_h_possible:
                    st.session_state.crop_h = max_h_possible
                if st.session_state.crop_h < 1: st.session_state.crop_h = 1
                # st.experimental_rerun()

            max_h_for_widget = full_img_h - st.session_state.crop_y
            if st.session_state.crop_h > max_h_for_widget:
                st.session_state.crop_h = max_h_for_widget
            if st.session_state.crop_h < 1 and max_h_for_widget >=1: st.session_state.crop_h = 1
            elif max_h_for_widget < 1: st.session_state.crop_h = max_h_for_widget

            st.number_input("切り抜き高さ", 1, max_h_for_widget if max_h_for_widget >=1 else 1, key="crop_h") # valueはセッションステートから

    # プレビューと処理対象画像の決定
    cx, cy = st.session_state.crop_x, st.session_state.crop_y
    # cw, ch は、X,Yの変更によって調整された後の値をセッションステートから読む
    cw = st.session_state.crop_w 
    ch = st.session_state.crop_h

    preview_img_with_rect = full_img_np_rgb_uint8.copy()
    cv2.rectangle(preview_img_with_rect, (cx, cy), (min(cx + cw, full_img_w), min(cy + ch, full_img_h)), (255,0,0), 3) # 枠線太く
    st.image(preview_img_with_rect, caption=f"トリミング範囲プレビュー (赤枠)", use_container_width=True)
    st.markdown("---")

    if not (cx == 0 and cy == 0 and cw == full_img_w and ch == full_img_h) and (cw > 0 and ch > 0) :
        img_for_analysis_rgb_np_uint8 = full_img_np_rgb_uint8[cy:min(cy+ch, full_img_h), cx:min(cx+cw, full_img_w)].copy()
        analysis_caption_suffix = f"(トリミング領域: {img_for_analysis_rgb_np_uint8.shape[1]}x{img_for_analysis_rgb_np_uint8.shape[0]}px)"
    else:
        img_for_analysis_rgb_np_uint8 = full_img_np_rgb_uint8.copy()
        analysis_caption_suffix = "(画像全体)"
    
    img_gray = cv2.cvtColor(img_for_analysis_rgb_np_uint8, cv2.COLOR_RGB2GRAY)
    if img_gray.dtype != np.uint8: img_gray = img_gray.astype(np.uint8)


    # --- サイドバーのパラメータ設定UI (画像ロード後に表示) ---
    st.sidebar.subheader("1. 二値化") 
    st.sidebar.markdown("_この値を色々と変更して、「1. 二値化処理後」画像を実物に近づけてください。_")
    st.sidebar.slider('閾値 (スライダーで調整)',min_value=0,max_value=255,step=1,value=st.session_state.binary_threshold_value,key="threshold_slider_for_binary",on_change=sync_threshold_from_slider)
    st.sidebar.number_input('閾値 (直接入力)',min_value=0,max_value=255,step=1,value=st.session_state.binary_threshold_value,key="threshold_number_for_binary",on_change=sync_threshold_from_number_input)
    threshold_value_to_use = st.session_state.binary_threshold_value 
    st.sidebar.caption("""- **大きくすると:** 明るい部分のみ白に。\n- **小さくすると:** 暗い部分も白に。""")
    st.sidebar.markdown("<br>", unsafe_allow_html=True); st.sidebar.markdown("_二値化だけでうまくいかない場合は下記も調整を_")
    st.sidebar.subheader("2. 形態学的処理 (オープニング)") 
    morph_kernel_shape_options_display = {"楕円":cv2.MORPH_ELLIPSE,"矩形":cv2.MORPH_RECT,"十字":cv2.MORPH_CROSS}
    selected_shape_name_sb = st.sidebar.selectbox("カーネル形状",options=list(morph_kernel_shape_options_display.keys()),index=0) 
    morph_kernel_shape_to_use = morph_kernel_shape_options_display[selected_shape_name_sb]
    st.sidebar.caption("輝点の形状に合わせて。") 
    kernel_options_morph = [1,3,5,7,9]; kernel_size_morph_to_use =st.sidebar.select_slider('カーネルサイズ',options=kernel_options_morph,value=3)
    st.sidebar.caption("""- **大きくすると:** 効果強、輝点も影響あり。\n- **小さくすると:** 効果弱。""") 
    st.sidebar.subheader("3. 輝点フィルタリング (面積)") 
    min_area_to_use = st.sidebar.number_input('最小面積',min_value=1,max_value=10000,value=1,step=1) 
    st.sidebar.caption("""- **大きくすると:** 小さな輝点を除外。\n- **小さくすると:** ノイズを拾う可能性。""") 
    max_area_to_use = st.sidebar.number_input('最大面積',min_value=1,max_value=100000,value=1000,step=1) 
    st.sidebar.caption("""- **大きくすると:** 大きな塊もカウント。\n- **小さくすると:** 大きな塊を除外。""") 

    # --- メインエリアの画像処理と表示ロジック ---
    st.header(f"処理ステップごとの画像 {analysis_caption_suffix}")
    kernel_size_blur = 1 
    if img_gray.size == 0 : st.error("処理対象のグレースケール画像が空です。トリミング範囲を確認してください。"); st.stop()
    blurred_img = cv2.GaussianBlur(img_gray, (kernel_size_blur,kernel_size_blur),0)
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
    output_image_contours_display = cv2.cvtColor(img_for_analysis_rgb_np_uint8, cv2.COLOR_RGB2BGR) # トリミング後または全体のカラー(BGR)

    if binary_img_for_contours_processed is not None:
        contours, hierarchy = cv2.findContours(binary_img_for_contours_processed,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        if 'contours' in locals() and contours: 
            for contour in contours:
                area = cv2.contourArea(contour)
                if min_area_to_use <= area <= max_area_to_use: 
                    current_counted_spots += 1
                    cv2.drawContours(output_image_contours_display, [contour], -1, (255,0,0), 2) 
        st.session_state.counted_spots_value = current_counted_spots 
    else:
        st.warning("輪郭検出元画像準備できず。"); st.session_state.counted_spots_value="エラー"
    
    st.subheader(f"1. 二値化処理後 {analysis_caption_suffix}")
    if binary_img_processed is not None: st.image(binary_img_processed,caption=f'閾値:{threshold_value_to_use}',use_container_width=True)
    else: st.info("二値化未実施/失敗")
    st.markdown("---")
    with st.expander(f"▼ 2. 形態学的処理後を見る {analysis_caption_suffix}", expanded=False): 
        if opened_img_processed is not None: 
            st.image(opened_img_processed,caption=f'カーネル:{selected_shape_name} {kernel_size_morph_to_use}x{kernel_size_morph_to_use}',use_container_width=True)
        else: st.info("形態学的処理未実施/失敗")
    st.markdown("---") 
    st.subheader(f"3. 輝点検出とマーキング {analysis_caption_suffix}")
    display_final_marked_image_rgb = cv2.cvtColor(output_image_contours_display, cv2.COLOR_BGR2RGB)
    if 'contours' in locals() and contours and binary_img_for_contours_processed is not None and current_counted_spots > 0 :
         st.image(display_final_marked_image_rgb,caption=f'検出輝点(青い輪郭,面積:{min_area_to_use}-{max_area_to_use})',use_container_width=True)
    elif binary_img_for_contours_processed is not None: 
        st.image(display_final_marked_image_rgb,caption='輝点見つからず',use_container_width=True)
    else: st.info("輝点検出未実施")
else: 
    st.info("まず、サイドバーから画像ファイルをアップロードしてください。")

display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value)
