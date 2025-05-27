import streamlit as st
from PIL import Image
import numpy as np
import cv2
import io

# ページ設定
st.set_page_config(page_title="輝点解析ツール", layout="wide")

# ファイルアップローダーのカスタムCSS (変更なし)
file_uploader_css = """<style>
section[data-testid="stFileUploaderDropzone"]{border:3px dashed white !important;border-radius:0.5rem !important;background-color:#495057 !important;padding:25px !important;}
section[data-testid="stFileUploaderDropzone"] > div[data-testid="stFileUploadDropzoneInstructions"]{display:flex;flex-direction:column;align-items:center;justify-content:center;}
section[data-testid="stFileUploaderDropzone"] p{color:#f8f9fa !important;font-size:0.9rem;margin-bottom:0.75rem !important;}
section[data-testid="stFileUploaderDropzone"] span{color:#ced4da !important;font-size:0.8rem;}
section[data-testid="stFileUploaderDropzone"] button{color:#fff !important;background-color:#007bff !important;border:1px solid #007bff !important;padding:0.5em 1em !important;border-radius:0.375rem !important;font-weight:500 !important;margin-top:0.5rem !important;}
</style>"""
st.markdown(file_uploader_css, unsafe_allow_html=True)

result_placeholder_sidebar = st.sidebar.empty()
def display_count_in_sidebar(placeholder, count_value):
    label_text = "【解析結果】輝点数"; value_text = str(count_value) 
    bg="#495057"; lf="white"; vf="white"
    html=f"""<div style="border-radius:8px;padding:15px;text-align:center;background-color:{bg};margin-bottom:15px;color:{lf};"><p style="font-size:16px;margin-bottom:5px;font-weight:bold;">{label_text}</p><p style="font-size:48px;font-weight:bold;margin-top:0px;color:{vf};line-height:1.1;">{value_text}</p></div>"""
    with placeholder.container(): placeholder.markdown(html, unsafe_allow_html=True)

# セッションステート初期化
default_ss = {
    'counted_spots_value':"---",
    "binary_threshold_value":58, 
    "threshold_slider_for_binary":58, 
    "threshold_number_for_binary":58,
    'pil_image_to_process':None, 
    'image_source_caption':"アップロードされた画像",
    'roi_x': 0, 'roi_y': 0, 'roi_w': 0, 'roi_h': 0, # ROIパラメータ
    'image_for_roi_w': 100, 'image_for_roi_h': 100, # ROI設定用画像の寸法
    'last_uploaded_filename_for_roi_reset':None
}
for k,v in default_ss.items():
    if k not in st.session_state: st.session_state[k]=v

# コールバック
def sync_threshold_from_slider(): st.session_state.binary_threshold_value=st.session_state.threshold_slider_for_binary; st.session_state.threshold_number_for_binary=st.session_state.threshold_slider_for_binary
def sync_threshold_from_number_input(): st.session_state.binary_threshold_value=st.session_state.threshold_number_for_binary; st.session_state.threshold_slider_for_binary=st.session_state.threshold_number_for_binary

# --- サイドバー基本UI ---
display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value) 
st.sidebar.header("解析パラメータ設定")
UPLOAD_ICON="📤"; uploaded_file_widget=st.sidebar.file_uploader(f"{UPLOAD_ICON} 画像をアップロード",type=['tif','tiff','png','jpg','jpeg'],help="対応形式: TIF,TIFF,PNG,JPG,JPEG。")

# --- メインエリア ---
st.markdown("<h1>Gra&Green<br>輝点カウントツール</h1>",unsafe_allow_html=True)
st.markdown("""### 使用方法
1. 画像を左にアップロードしてください。
2. 「1. 解析エリア選択（ROI）」で、表示された画像の下のスライダーを操作し、解析したい四角いエリアを調整します。画像上の赤い枠が選択範囲です。
3. 設定した解析エリア（または画像全体）を元に、左サイドバーの「1. 二値化」以降のパラメータを調整してください。
4. メインエリアの各処理ステップ画像と、最終的な「3. 輝点検出とマーキング」で結果を確認します。
""")
st.markdown("---") 

# 画像読み込みとROIパラメータ初期化
if uploaded_file_widget is not None:
    if st.session_state.get('last_uploaded_filename_for_roi_reset') != uploaded_file_widget.name:
        st.session_state.last_uploaded_filename_for_roi_reset = uploaded_file_widget.name
        # 新しい画像がアップロードされたらROIパラメータをリセット
        try:
            temp_bytes = uploaded_file_widget.getvalue() # 一時的にバイトデータを取得
            temp_pil = Image.open(io.BytesIO(temp_bytes)).convert("RGB")
            temp_np = np.array(temp_pil).astype(np.uint8)
            h_orig, w_orig = temp_np.shape[:2]
            st.session_state.roi_x = 0
            st.session_state.roi_y = 0
            st.session_state.roi_w = w_orig
            st.session_state.roi_h = h_orig
            st.session_state.image_for_roi_w = w_orig
            st.session_state.image_for_roi_h = h_orig
            uploaded_file_widget.seek(0) # ポインタを戻す (getvalue()の後必要)
        except Exception: # 画像が開けない場合は何もしない（次のブロックでエラー処理）
            pass


    try:
        uploaded_file_bytes = uploaded_file_widget.getvalue() # 再度取得（またはキャッシュされたものを使う）
        pil_img_original_full_res = Image.open(io.BytesIO(uploaded_file_bytes))
        st.session_state.pil_image_to_process = pil_img_original_full_res # フル解像度を保持
        st.session_state.image_source_caption = f"アップロード: {uploaded_file_widget.name}"
    except Exception as e: 
        st.sidebar.error(f"アップロード画像の読み込みに失敗: {e}"); 
        st.session_state.pil_image_to_process=None; st.session_state.counted_spots_value="読込エラー"; st.stop()
else: 
    if st.session_state.pil_image_to_process is not None: 
        st.session_state.pil_image_to_process=None; st.session_state.counted_spots_value="---"

# メイン処理
if st.session_state.pil_image_to_process is not None:
    pil_image_rgb_full_res = None; img_gray_full_res = None
    np_array_rgb_uint8_full_res = None
    
    try:
        pil_image_rgb_full_res = st.session_state.pil_image_to_process.convert("RGB")
        np_array_rgb_uint8_full_res = np.array(pil_image_rgb_full_res).astype(np.uint8)
        img_gray_full_res = cv2.cvtColor(np_array_rgb_uint8_full_res, cv2.COLOR_RGB2GRAY)
        if img_gray_full_res.dtype != np.uint8: img_gray_full_res = img_gray_full_res.astype(np.uint8)
    except Exception as e: st.error(f"画像変換(フル解像度)に失敗: {e}"); st.stop()

    st.header("1. 解析エリア選択（ROI）") 
    
    # --- ROI設定用UI ---
    # 表示用の画像を準備 (st.imageはNumPyを期待)
    roi_display_img_base = np_array_rgb_uint8_full_res.copy()
    img_h, img_w = roi_display_img_base.shape[:2]

    # 新しい画像がアップロードされたか、またはROIの幅・高さが画像サイズと異なる場合にリセット
    if st.session_state.image_for_roi_w != img_w or st.session_state.image_for_roi_h != img_h:
        st.session_state.roi_x = 0
        st.session_state.roi_y = 0
        st.session_state.roi_w = img_w
        st.session_state.roi_h = img_h
        st.session_state.image_for_roi_w = img_w
        st.session_state.image_for_roi_h = img_h
        # st.experimental_rerun() # 値の即時反映のため

    st.write(f"元画像サイズ: 幅={img_w}px, 高さ={img_h}px。スライダーで赤い枠（ROI）を調整してください。")
    
    cols_roi1 = st.columns(2)
    st.session_state.roi_x = cols_roi1[0].slider("ROI 左上 X", 0, img_w - 1, st.session_state.roi_x, key="roi_x_slider")
    st.session_state.roi_y = cols_roi1[1].slider("ROI 左上 Y", 0, img_h - 1, st.session_state.roi_y, key="roi_y_slider")
    
    cols_roi2 = st.columns(2)
    max_w = img_w - st.session_state.roi_x
    if st.session_state.roi_w > max_w : st.session_state.roi_w = max_w
    if st.session_state.roi_w < 1 and max_w >=1 : st.session_state.roi_w = 1
    elif max_w < 1: st.session_state.roi_w = max_w
    st.session_state.roi_w = cols_roi2[0].slider("ROI 幅", 1, max_w if max_w >=1 else 1, st.session_state.roi_w, key="roi_w_slider")
    
    max_h = img_h - st.session_state.roi_y
    if st.session_state.roi_h > max_h : st.session_state.roi_h = max_h
    if st.session_state.roi_h < 1 and max_h >=1 : st.session_state.roi_h = 1
    elif max_h < 1: st.session_state.roi_h = max_h
    st.session_state.roi_h = cols_roi2[1].slider("ROI 高さ", 1, max_h if max_h >=1 else 1, st.session_state.roi_h, key="roi_h_slider")

    # ROIプレビュー描画
    preview_img_with_roi = roi_display_img_base.copy()
    rx, ry, rw, rh = st.session_state.roi_x, st.session_state.roi_y, st.session_state.roi_w, st.session_state.roi_h
    if rw > 0 and rh > 0:
        cv2.rectangle(preview_img_with_roi, (rx, ry), (rx + rw, ry + rh), (255, 0, 0), 3) # 赤枠、太さ3
    st.image(preview_img_with_roi, caption=f"ROIプレビュー (X:{rx}, Y:{ry}, 幅:{rw}, 高さ:{rh})")
    st.markdown("---")

    # --- 処理対象画像の決定 ---
    if rw > 0 and rh > 0 and not (rx == 0 and ry == 0 and rw == img_w and rh == img_h):
        img_to_process_gray = img_gray_full_res[ry:ry+rh, rx:rx+rw].copy()
        img_for_marking_color_np = np_array_rgb_uint8_full_res[ry:ry+rh, rx:rx+rw].copy()
        analysis_caption_suffix = f"(選択エリア: {rw}x{rh}px)"
    else:
        img_to_process_gray = img_gray_full_res.copy()
        img_for_marking_color_np = np_array_rgb_uint8_full_res.copy()
        analysis_caption_suffix = "(画像全体)"

    # --- サイドバーのパラメータ設定UI (画像ロード後に表示) ---
    # (内容は変更なし)
    st.sidebar.subheader("1. 二値化") 
    st.sidebar.markdown("_この値を色々変更して、「1. 二値化処理後」画像を実物に近づけてください。_")
    st.sidebar.slider('閾値 (スライダーで調整)',min_value=0,max_value=255,step=1,value=st.session_state.binary_threshold_value,key="threshold_slider_for_binary",on_change=sync_threshold_from_slider)
    st.sidebar.number_input('閾値 (直接入力)',min_value=0,max_value=255,step=1,value=st.session_state.binary_threshold_value,key="threshold_number_for_binary",on_change=sync_threshold_from_number_input)
    threshold_value_to_use = st.session_state.binary_threshold_value 
    st.sidebar.caption("""- ..."""); st.sidebar.markdown("<br>", unsafe_allow_html=True); st.sidebar.markdown("_..._") 
    st.sidebar.subheader("2. 形態学的処理 (オープニング)") 
    morph_kernel_shape_to_use = cv2.MORPH_ELLIPSE 
    st.sidebar.markdown("カーネル形状: **楕円 (固定)**")
    kernel_options_morph = [1,3,5,7,9]; kernel_size_morph_to_use =st.sidebar.select_slider('カーネルサイズ',options=kernel_options_morph,value=3) # Keyなし
    st.sidebar.markdown("""オープニング処理は...""", unsafe_allow_html=True)
    st.sidebar.subheader("3. 輝点フィルタリング (面積)") 
    min_area_to_use = st.sidebar.number_input('最小面積',min_value=1,max_value=10000,value=1,step=1) # Keyなし
    st.sidebar.caption("""- ...""") 
    max_area_to_use = st.sidebar.number_input('最大面積',min_value=1,max_value=100000,value=1000,step=1) # Keyなし
    st.sidebar.caption("""- ...""") 

    # --- メインエリアの画像処理と表示ロジック ---
    st.header(f"処理ステップごとの画像") 
    kernel_size_blur=1;
    if img_to_process_gray.size==0: st.error("処理対象グレースケール画像が空。"); st.stop()
    blurred_img = cv2.GaussianBlur(img_to_process_gray,(kernel_size_blur,kernel_size_blur),0)
    ret_thresh,binary_img_processed = cv2.threshold(blurred_img,threshold_value_to_use,255,cv2.THRESH_BINARY)
    if not ret_thresh: st.error("二値化失敗。"); binary_img_for_morph_processed=None
    else: binary_img_for_morph_processed=binary_img_processed.copy()
    opened_img_processed=None
    if binary_img_for_morph_processed is not None:
        kernel_morph_obj=cv2.getStructuringElement(morph_kernel_shape_to_use,(kernel_size_morph_to_use,kernel_size_morph_to_use))
        opened_img_processed=cv2.morphologyEx(binary_img_for_morph_processed,cv2.MORPH_OPEN,kernel_morph_obj)
        binary_img_for_contours_processed = opened_img_processed.copy()
    else: binary_img_for_contours_processed=None
    current_counted_spots=0
    output_image_contours_display_bgr = cv2.cvtColor(img_for_marking_color_np, cv2.COLOR_RGB2BGR)
    if binary_img_for_contours_processed is not None:
        contours,hierarchy = cv2.findContours(binary_img_for_contours_processed,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        if 'contours' in locals() and contours:
            for contour in contours:
                area=cv2.contourArea(contour)
                if min_area_to_use <= area <= max_area_to_use: current_counted_spots+=1; cv2.drawContours(output_image_contours_display_bgr,[contour],-1,(255,0,0),2)
        st.session_state.counted_spots_value=current_counted_spots
    else: st.warning("輪郭検出元画像準備できず。"); st.session_state.counted_spots_value="エラー"
    
    st.subheader(f"1. 二値化処理後 {analysis_caption_suffix}")
    if binary_img_processed is not None: st.image(binary_img_processed,caption=f'閾値:{threshold_value_to_use}')
    else: st.info("二値化未実施/失敗")
    st.markdown("---")
    with st.expander(f"▼ 2. 形態学的処理後を見る {analysis_caption_suffix}", expanded=False):
        if opened_img_processed is not None: st.image(opened_img_processed,caption=f'カーネル: 楕円 {kernel_size_morph_to_use}x{kernel_size_morph_to_use}')
        else: st.info("形態学的処理未実施/失敗")
    st.markdown("---") 
    st.subheader(f"3. 輝点検出とマーキング {analysis_caption_suffix}")
    display_final_marked_image_rgb = cv2.cvtColor(output_image_contours_display_bgr, cv2.COLOR_BGR2RGB)
    if 'contours' in locals() and contours and binary_img_for_contours_processed is not None and current_counted_spots > 0 :
         st.image(display_final_marked_image_rgb,caption=f'検出輝点(青い輪郭,面積:{min_area_to_use}-{max_area_to_use})')
    elif binary_img_for_contours_processed is not None: st.image(display_final_marked_image_rgb,caption='輝点見つからず')
    else: st.info("輝点検出未実施")
else: 
    st.info("まず、サイドバーから画像ファイルをアップロードしてください。")

display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value)
