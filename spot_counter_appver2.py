import streamlit as st
from PIL import Image
import numpy as np
import cv2
from streamlit_drawable_canvas import st_canvas
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
if "binary_threshold_value" not in st.session_state: st.session_state.binary_threshold_value = 58
if "threshold_slider_for_binary" not in st.session_state: st.session_state.threshold_slider_for_binary = st.session_state.binary_threshold_value
if "threshold_number_for_binary" not in st.session_state: st.session_state.threshold_number_for_binary = st.session_state.binary_threshold_value
if "morph_shape_sb_key" not in st.session_state: st.session_state.morph_shape_sb_key = "楕円" 
if "morph_size_sb_key" not in st.session_state: st.session_state.morph_size_sb_key = 3
if "min_area_sb_key_v3" not in st.session_state: st.session_state.min_area_sb_key_v3 = 1 
if "max_area_sb_key_v3" not in st.session_state: st.session_state.max_area_sb_key_v3 = 1000 
if 'pil_image_to_process' not in st.session_state: st.session_state.pil_image_to_process = None
if 'image_source_caption' not in st.session_state: st.session_state.image_source_caption = "アップロードされた画像"
if 'roi_coords' not in st.session_state: st.session_state.roi_coords = None
if 'last_uploaded_filename_for_roi_reset' not in st.session_state: st.session_state.last_uploaded_filename_for_roi_reset = None


# --- コールバック関数の定義 ---
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
st.markdown("""
### 使用方法
1. 画像を左にアップロードしてください。
2. **(オプション)** 「1. 元の画像 と 解析エリア選択」で、表示された画像（キャンバス）上でマウスをドラッグし、解析したい四角いエリアを描画します。最後に描画した四角形がROIとなります。何も描画しない場合は画像全体が対象です。
3. 画像（または選択エリア）を元に、左サイドバーの「1. 二値化」以降のパラメータを調整してください。
4. メインエリアの各処理ステップ画像と、最終的な「3. 輝点検出とマーキング」で結果を確認します。
""")
st.markdown("---") 

# 画像読み込みロジック
if uploaded_file_widget is not None:
    if st.session_state.get('last_uploaded_filename_for_roi_reset') != uploaded_file_widget.name:
        st.session_state.roi_coords = None 
        st.session_state.last_uploaded_filename_for_roi_reset = uploaded_file_widget.name
    try:
        uploaded_file_bytes = uploaded_file_widget.getvalue()
        pil_img_original_full_res = Image.open(io.BytesIO(uploaded_file_bytes))
        st.session_state.pil_image_to_process = pil_img_original_full_res
        st.session_state.image_source_caption = f"アップロード: {uploaded_file_widget.name}"
    except Exception as e:
        st.sidebar.error(f"アップロード画像の読み込みに失敗: {e}")
        st.session_state.pil_image_to_process = None 
        st.session_state.counted_spots_value = "読込エラー"; st.stop()
else: 
    if st.session_state.pil_image_to_process is not None: 
        st.session_state.pil_image_to_process = None
        st.session_state.counted_spots_value = "---" 
        st.session_state.roi_coords = None

# メイン処理と、条件付きでのサイドバーパラメータUI表示
if st.session_state.pil_image_to_process is not None:
    pil_image_rgb_full = None; img_gray_full = None
    np_array_rgb_uint8_full_res = None # この変数がフル解像度のRGB uint8 NumPy配列

    try:
        pil_image_rgb_full = st.session_state.pil_image_to_process.convert("RGB")
        np_array_rgb_uint8_full_res = np.array(pil_image_rgb_full).astype(np.uint8)
        img_gray_full = cv2.cvtColor(np_array_rgb_uint8_full_res, cv2.COLOR_RGB2GRAY)
        if img_gray_full.dtype != np.uint8: img_gray_full = img_gray_full.astype(np.uint8)
    except Exception as e: st.error(f"画像変換(フル)に失敗: {e}"); st.stop()

    st.header("1. 元の画像 と 解析エリア選択")
    
    with st.expander("背景画像候補の確認（デバッグ用、縮小版）", expanded=True):
        if np_array_rgb_uint8_full_res is not None:
            st.write(f"表示用NumPy配列の型: `{type(np_array_rgb_uint8_full_res)}`")
            st.write(f"形状: `{np_array_rgb_uint8_full_res.shape}`")
            st.write(f"データ型: `{np_array_rgb_uint8_full_res.dtype}`")
            if np_array_rgb_uint8_full_res.size > 0:
                st.write(f"最小値: `{np_array_rgb_uint8_full_res.min()}`, 最大値: `{np_array_rgb_uint8_full_res.max()}`")
            else: st.write("表示用NumPy配列が空です。")
            try:
                # ★★★ use_container_width=True を削除 ★★★
                st.image(np_array_rgb_uint8_full_res, caption="この画像がキャンバスの背景になるはずです (NumPy uint8)")
            except Exception as e_img: st.error(f"st.imageでの表示に失敗: {e_img}")
        else: st.warning("背景画像候補 (NumPy uint8 配列) が準備できませんでした。")
    
    st.info("↓下の画像（キャンバス）上でマウスをドラッグして、解析したい四角いエリアを描画してください。最後に描画した四角形がROIとなります。")
    
    pil_for_canvas_bg = pil_image_rgb_full.copy() # キャンバス背景用にPillowイメージを使用
    CANVAS_MAX_DIM = 800 
    if pil_for_canvas_bg.width > CANVAS_MAX_DIM or pil_for_canvas_bg.height > CANVAS_MAX_DIM:
        pil_for_canvas_bg.thumbnail((CANVAS_MAX_DIM, CANVAS_MAX_DIM))
    scale_x = pil_image_rgb_full.width / pil_for_canvas_bg.width
    scale_y = pil_image_rgb_full.height / pil_for_canvas_bg.height

    canvas_result = st_canvas(
        fill_color="rgba(255,0,0,0.1)", stroke_width=2, stroke_color="red",
        background_image=pil_for_canvas_bg, update_streamlit=True, 
        height=pil_for_canvas_bg.height, width=pil_for_canvas_bg.width,
        drawing_mode="rect", key="roi_canvas_main"
    )

    img_to_process_gray = img_gray_full 
    img_for_marking_color_np = np_array_rgb_uint8_full_res.copy() 
    analysis_caption_suffix = "(画像全体)"

    if canvas_result.json_data is not None and canvas_result.json_data.get("objects", []):
        if canvas_result.json_data["objects"][-1]["type"] == "rect":
            rect = canvas_result.json_data["objects"][-1]
            x_cvs, y_cvs, w_cvs, h_cvs = int(rect["left"]), int(rect["top"]), int(rect["width"]), int(rect["height"])
            if w_cvs > 0 and h_cvs > 0:
                x_orig,y_orig,w_orig,h_orig = int(x_cvs*scale_x),int(y_cvs*scale_y),int(w_cvs*scale_x),int(h_cvs*scale_y)
                x1,y1 = max(0,x_orig),max(0,y_orig)
                x2,y2 = min(img_gray_full.shape[1],x_orig+w_orig),min(img_gray_full.shape[0],y_orig+h_orig)
                if (x2-x1 > 0) and (y2-y1 > 0):
                    st.session_state.roi_coords = (x1,y1,x2-x1,y2-y1)
                    img_to_process_gray = img_gray_full[y1:y2, x1:x2].copy()
                    img_for_marking_color_np = np_array_rgb_uint8_full_res[y1:y2, x1:x2].copy()
                    analysis_caption_suffix = f"(選択エリア: {img_to_process_gray.shape[1]}x{img_to_process_gray.shape[0]}px @フル解像度)"
                    # st.subheader("選択されたROI（グレースケール処理対象）") # メイン処理ステップで表示
                    # st.image(img_to_process_gray, caption=f"ROI (グレースケール)", use_container_width=True) # ここでは表示しない
                else: st.warning("描画ROI無効。全体処理。"); img_to_process_gray=img_gray_full; st.session_state.roi_coords=None
            else: st.session_state.roi_coords = None
    st.markdown("---")

    # --- サイドバーのパラメータ設定UI ---
    st.sidebar.subheader("1. 二値化") 
    st.sidebar.markdown("_この値を色々変更して、「1. 二値化処理後」画像を実物に近づけてください。_")
    st.sidebar.slider('閾値 (スライダーで調整)',min_value=0,max_value=255,step=1,value=st.session_state.binary_threshold_value,key="threshold_slider_for_binary",on_change=sync_threshold_from_slider)
    st.sidebar.number_input('閾値 (直接入力)',min_value=0,max_value=255,step=1,value=st.session_state.binary_threshold_value,key="threshold_number_for_binary",on_change=sync_threshold_from_number_input)
    threshold_value_to_use = st.session_state.binary_threshold_value 
    st.sidebar.caption("""- **大きくすると:** 明るい部分のみ白に。\n- **小さくすると:** 暗い部分も白に。""")
    st.sidebar.markdown("<br>", unsafe_allow_html=True); st.sidebar.markdown("_二値化だけでうまくいかない場合は下記も調整を_")
    st.sidebar.subheader("2. 形態学的処理 (オープニング)") 
    morph_kernel_shape_to_use = cv2.MORPH_ELLIPSE 
    st.sidebar.markdown("カーネル形状: **楕円 (固定)**")
    kernel_options_morph = [1,3,5,7,9]
    kernel_size_morph_to_use =st.sidebar.select_slider('カーネルサイズ',options=kernel_options_morph,value=st.session_state.morph_size_sb_key,key="morph_size_sb_key")
    st.sidebar.markdown("""オープニング処理は、画像中の小さな白いノイズ（ゴミなど）を除去したり、輝点同士を繋ぐ細い線や、輝点の細い突起部分を取り除く効果があります。...（中略）...「2. 形態学的処理後を見る」の画像を確認しながら調整してください。""", unsafe_allow_html=True)
    st.sidebar.subheader("3. 輝点フィルタリング (面積)") 
    min_area_to_use = st.sidebar.number_input('最小面積',min_value=1,max_value=10000,value=st.session_state.min_area_sb_key_v3,key="min_area_sb_key_v3") 
    st.sidebar.caption("""- **大きくすると:** 小さな輝点を除外。\n- **小さくすると:** ノイズを拾う可能性。(画像リサイズ時注意)""") 
    max_area_to_use = st.sidebar.number_input('最大面積',min_value=1,max_value=100000,value=st.session_state.max_area_sb_key_v3,key="max_area_sb_key_v3") 
    st.sidebar.caption("""- **大きくすると:** 大きな塊もカウント。\n- **小さくすると:** 大きな塊を除外。(画像リサイズ時注意)""") 

    # --- メインエリアの画像処理と表示ロジック ---
    st.header(f"処理ステップごとの画像") 
    kernel_size_blur = 1 
    if img_to_process_gray.size == 0 : st.error("処理対象のグレースケール画像が空です。"); st.stop()
    blurred_img = cv2.GaussianBlur(img_to_process_gray, (kernel_size_blur,kernel_size_blur),0)
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
    output_image_contours_display_bgr = cv2.cvtColor(img_for_analysis_rgb_np_uint8, cv2.COLOR_RGB2BGR)

    if binary_img_for_contours_processed is not None:
        contours, hierarchy = cv2.findContours(binary_img_for_contours_processed,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        if 'contours' in locals() and contours: 
            for contour in contours:
                area = cv2.contourArea(contour)
                if min_area_to_use <= area <= max_area_to_use: 
                    current_counted_spots += 1
                    cv2.drawContours(output_image_contours_display_bgr, [contour], -1, (255,0,0), 2) 
        st.session_state.counted_spots_value = current_counted_spots 
    else:
        st.warning("輪郭検出元画像準備できず。"); st.session_state.counted_spots_value="エラー"
    
    st.subheader(f"1. 二値化処理後 {analysis_caption_suffix}")
    if binary_img_processed is not None: st.image(binary_img_processed,caption=f'閾値:{threshold_value_to_use}') # ★★★ 削除 ★★★
    else: st.info("二値化未実施/失敗")
    st.markdown("---")
    with st.expander(f"▼ 2. 形態学的処理後を見る {analysis_caption_suffix}", expanded=False): 
        if opened_img_processed is not None: 
            st.image(opened_img_processed,caption=f'カーネル: 楕円 {kernel_size_morph_to_use}x{kernel_size_morph_to_use}') # ★★★ 削除 ★★★
        else: st.info("形態学的処理未実施/失敗")
    st.markdown("---") 
    st.subheader(f"3. 輝点検出とマーキング {analysis_caption_suffix}")
    display_final_marked_image_rgb = cv2.cvtColor(output_image_contours_display_bgr, cv2.COLOR_BGR2RGB)
    if 'contours' in locals() and contours and binary_img_for_contours_processed is not None and current_counted_spots > 0 :
         st.image(display_final_marked_image_rgb,caption=f'検出輝点(青い輪郭,面積:{min_area_to_use}-{max_area_to_use})') # ★★★ 削除 ★★★
    elif binary_img_for_contours_processed is not None: 
        st.image(display_final_marked_image_rgb,caption='輝点見つからず') # ★★★ 削除 ★★★
    else: st.info("輝点検出未実施")
else: 
    st.info("まず、サイドバーから画像ファイルをアップロードしてください。")

display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value)
