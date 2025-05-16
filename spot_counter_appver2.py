import streamlit as st
from PIL import Image
import numpy as np
import cv2
from streamlit_drawable_canvas import st_canvas # ROI選択機能を元に戻す場合は必要
import io

# ページ設定 (一番最初に呼び出す)
st.set_page_config(page_title="輝点解析ツール", layout="wide")

# --- サイドバーの上部に結果表示用のプレースホルダーを定義 ---
result_placeholder_sidebar = st.sidebar.empty() 

# --- カスタマイズされた結果表示関数 (サイドバー表示用) ---
def display_count_in_sidebar(placeholder, count_value):
    label_text = "【解析結果】輝点数" 
    value_text = str(count_value) 
    background_color = "#495057"; label_font_color = "white"; value_font_color = "white"
    html_content = f"""
    <div style="border-radius:8px; padding:15px; text-align:center; background-color:{background_color}; margin-bottom:15px; color:{label_font_color};">
        <p style="font-size:16px; margin-bottom:5px; font-weight:bold;">{label_text}</p>
        <p style="font-size:48px; font-weight:bold; margin-top:0px; color:{value_font_color}; line-height:1.1;">{value_text}</p>
    </div>"""
    placeholder.markdown(html_content, unsafe_allow_html=True)

# アプリのタイトル (メインエリア)
st.markdown("<h1>Gra&Green<br>輝点カウントツール</h1>", unsafe_allow_html=True)

# 「使用方法」(メインエリア)
st.markdown("""
### 使用方法
1. 画像を左にアップロードしてください。
2. **(オプション)** 「1. 元の画像 と ROI選択」の下に表示される画像上で、解析したいエリアをマウスでドラッグして四角で囲ってください。最後に描画した四角形がROIとなります。囲まない場合は画像全体が対象になります。
3. 左サイドバーの「1. 二値化」の閾値を動かして、「1. 二値化処理後」の画像（選択エリアがある場合はその部分）が、輝点と背景が適切に分離された状態になるように調整してください。
4. （それでもカウント値がおかしい場合は、サイドバーの「2. 形態学的処理」や「3. 輝点フィルタリング」の各パラメータも調整してみてください。）
""")
st.markdown("---") 

# --- セッションステートの初期化 ---
if 'counted_spots_value' not in st.session_state: st.session_state.counted_spots_value = "---" 
if "binary_threshold_value" not in st.session_state: st.session_state.binary_threshold_value = 58
if "threshold_slider_for_binary" not in st.session_state: st.session_state.threshold_slider_for_binary = st.session_state.binary_threshold_value
if "threshold_number_for_binary" not in st.session_state: st.session_state.threshold_number_for_binary = st.session_state.binary_threshold_value

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
uploaded_file = st.sidebar.file_uploader(f"{UPLOAD_ICON} 画像をアップロード", type=['tif', 'tiff', 'png', 'jpg', 'jpeg'], help="対応形式: TIF, TIFF, PNG, JPG, JPEG。")
display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value)

# --- メイン処理 ---
if uploaded_file is not None:
    # --- 画像の読み込みと初期表示の堅牢化 ---
    st.sidebar.markdown("---") # アップロード情報の前に区切り
    st.sidebar.write(f"**アップロードファイル情報:**")
    st.sidebar.caption(f"名前: `{uploaded_file.name}`")
    st.sidebar.caption(f"タイプ: `{uploaded_file.type}`")
    st.sidebar.caption(f"サイズ: `{uploaded_file.size}` bytes")
    st.sidebar.markdown("---")


    pil_image_original = None
    pil_image_rgb_for_display_and_canvas = None # 表示とキャンバス背景、OpenCVの元になるPillow RGB

    try:
        uploaded_file_bytes = uploaded_file.getvalue()
        if not uploaded_file_bytes:
            st.error("アップロードされたファイルが空、または読み込めませんでした。")
            st.stop()
        
        # st.sidebar.write(f"読み込んだバイト数: {len(uploaded_file_bytes)}") # デバッグ用

        try:
            # Pillowで画像を開く試み
            pil_image_original = Image.open(io.BytesIO(uploaded_file_bytes))
            # st.sidebar.caption(f"Pillowで開いたモード: {pil_image_original.mode}") # デバッグ用
        except Exception as e_pillow:
            st.warning(f"Pillowでの画像読み込みに失敗: {e_pillow}")
            st.info("OpenCVでの読み込みを試みます...")
            try:
                np_array_from_bytes = np.frombuffer(uploaded_file_bytes, np.uint8)
                img_decoded_cv = cv2.imdecode(np_array_from_bytes, cv2.IMREAD_UNCHANGED) 
                
                if img_decoded_cv is None:
                    raise ValueError("cv2.imdecodeが画像のデコードに失敗しました。")

                if len(img_decoded_cv.shape) == 3 and img_decoded_cv.shape[2] == 4: # BGRA
                    pil_image_original = Image.fromarray(cv2.cvtColor(img_decoded_cv, cv2.COLOR_BGRA2RGBA))
                elif len(img_decoded_cv.shape) == 3 and img_decoded_cv.shape[2] == 3: # BGR
                    pil_image_original = Image.fromarray(cv2.cvtColor(img_decoded_cv, cv2.COLOR_BGR2RGB))
                elif len(img_decoded_cv.shape) == 2: # Grayscale
                    pil_image_original = Image.fromarray(img_decoded_cv)
                else:
                    raise ValueError(f"OpenCVでデコードされた画像のチャンネル数({img_decoded_cv.shape})が予期しません。")
                # st.sidebar.caption(f"OpenCV経由 Pillowモード: {pil_image_original.mode}") # デバッグ用
            except Exception as e_cv2:
                st.error(f"PillowおよびOpenCVでの画像読み込みに最終的に失敗しました: {e_cv2}")
                st.stop()
        
        if pil_image_original is None: # ここには来ないはずだが念のため
             st.error("画像オブジェクトの準備に失敗しました。")
             st.stop()

        pil_image_rgb_for_display_and_canvas = pil_image_original.convert("RGB")
        
        # 表示用にNumPy配列(RGB, uint8)を準備
        np_array_rgb_uint8_for_display = np.array(pil_image_rgb_for_display_and_canvas)
        if np_array_rgb_uint8_for_display.dtype != np.uint8:
            if np.issubdtype(np_array_rgb_uint8_for_display.dtype, np.floating):
                if np_array_rgb_uint8_for_display.min() >= 0.0 and np_array_rgb_uint8_for_display.max() <= 1.0:
                    np_array_rgb_uint8_for_display = (np_array_rgb_uint8_for_display * 255).astype(np.uint8)
                else: 
                    np_array_rgb_uint8_for_display = np.clip(np_array_rgb_uint8_for_display, 0, 255).astype(np.uint8)
            elif np.issubdtype(np_array_rgb_uint8_for_display.dtype, np.integer): 
                np_array_rgb_uint8_for_display = np.clip(np_array_rgb_uint8_for_display, 0, 255).astype(np.uint8)
            else: 
                np_array_rgb_uint8_for_display = np_array_rgb_uint8_for_display.astype(np.uint8)
        
        st.header("1. 元の画像 と ROI選択")
        st.image(np_array_rgb_uint8_for_display, caption='アップロードされた画像 (ROI選択用)', use_container_width=True)
        
    except Exception as e_outer:
        st.error(f"画像処理の初期段階で予期せぬエラー: {e_outer}")
        st.stop() 

    img_array_rgb_for_opencv = np.array(pil_image_rgb_for_display_and_canvas) 
    img_gray_full = cv2.cvtColor(img_array_rgb_for_opencv, cv2.COLOR_RGB2GRAY)
    
    if img_gray_full.dtype != np.uint8:
        # (グレースケール画像の8bit化処理 - 前回のものを流用)
        if img_gray_full.ndim == 2 and (img_gray_full.max() > 255 or img_gray_full.min() < 0 or img_gray_full.dtype != np.uint8):
            img_gray_full = cv2.normalize(img_gray_full, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        elif img_gray_full.ndim == 3:
            img_gray_full = cv2.cvtColor(img_gray_full, cv2.COLOR_BGR2GRAY).astype(np.uint8)
        else:
            try:
                img_gray_full_temp = img_gray_full.astype(np.uint8)
                if img_gray_full_temp.max() > 255 or img_gray_full_temp.min() < 0:
                    img_gray_full = np.clip(img_gray_full, 0, 255).astype(np.uint8)
                else: img_gray_full = img_gray_full_temp
            except Exception as e_gray_conv:
                st.error(f"グレースケール画像のデータ型変換に失敗: {e_gray_conv}"); st.stop()

    st.info("↑上の画像上で、解析したいエリアをマウスでドラッグして四角で囲ってください。最後に描画した四角形がROIとなります。")

    drawing_mode = "rect"; stroke_color = "red"
    canvas_result = st_canvas(
        fill_color="rgba(255,0,0,0.1)", stroke_width=2, stroke_color=stroke_color,
        background_image=pil_image_rgb_for_display_and_canvas, 
        update_streamlit=True, height=pil_image_rgb_for_display_and_canvas.height, width=pil_image_rgb_for_display_and_canvas.width,
        drawing_mode=drawing_mode, key="roi_canvas"
    )

    img_to_process = img_gray_full 
    roi_coords = None 
    base_for_marking_bgr = cv2.cvtColor(img_array_rgb_for_opencv, cv2.COLOR_RGB2BGR) 

    if canvas_result.json_data is not None and canvas_result.json_data.get("objects", []):
        if canvas_result.json_data["objects"][-1]["type"] == "rect":
            rect = canvas_result.json_data["objects"][-1]
            x,y,w,h = int(rect["left"]),int(rect["top"]),int(rect["width"]),int(rect["height"])
            if w > 0 and h > 0:
                img_h_full, img_w_full = img_gray_full.shape[:2]
                x1_roi,y1_roi = max(0,x),max(0,y)
                x2_roi,y2_roi = min(img_w_full,x+w),min(img_h_full,y+h)
                if (x2_roi-x1_roi > 0) and (y2_roi-y1_roi > 0):
                    roi_coords = (x1_roi,y1_roi,x2_roi-x1_roi,y2_roi-y1_roi)
                    img_to_process = img_gray_full[y1_roi:y2_roi, x1_roi:x2_roi].copy()
                    base_for_marking_bgr = cv2.cvtColor(img_array_rgb_for_opencv[y1_roi:y2_roi, x1_roi:x2_roi], cv2.COLOR_RGB2BGR)
                    st.subheader("選択されたROI（グレースケールでの処理対象）")
                    st.image(img_to_process, caption=f"処理対象ROI: x={x1_roi},y={y1_roi},w={x2_roi-x1_roi},h={y2_roi-y1_roi}", use_container_width=True)
                else:
                    st.warning("描画されたROIのサイズが無効。画像全体を処理します。"); img_to_process = img_gray_full 
    
    st.sidebar.subheader("1. 二値化") 
    st.sidebar.markdown("_この値を色々と変更して、「1. 二値化処理後」画像を実物に近づけてください。_")
    st.sidebar.slider('閾値 (スライダーで調整)',min_value=0,max_value=255,step=1,value=st.session_state.binary_threshold_value,key="threshold_slider_for_binary",on_change=sync_threshold_from_slider)
    st.sidebar.number_input('閾値 (直接入力)',min_value=0,max_value=255,step=1,value=st.session_state.binary_threshold_value,key="threshold_number_for_binary",on_change=sync_threshold_from_number_input)
    threshold_value = st.session_state.binary_threshold_value 
    st.sidebar.caption("""- **大きくすると:** 明るい部分のみ白に。\n- **小さくすると:** 暗い部分も白に。""")
    st.sidebar.markdown("<br>", unsafe_allow_html=True); st.sidebar.markdown("_二値化だけでうまくいかない場合は下記も調整を_")
    st.sidebar.subheader("2. 形態学的処理 (オープニング)") 
    morph_kernel_shape_options = {"楕円":cv2.MORPH_ELLIPSE,"矩形":cv2.MORPH_RECT,"十字":cv2.MORPH_CROSS}
    selected_shape_name = st.sidebar.selectbox("カーネル形状",options=list(morph_kernel_shape_options.keys()),index=0) 
    morph_kernel_shape = morph_kernel_shape_options[selected_shape_name]
    st.sidebar.caption("輝点の形状に合わせて。")
    kernel_options_morph = [1,3,5,7,9]; kernel_size_morph=st.sidebar.select_slider('カーネルサイズ',options=kernel_options_morph,value=3)
    st.sidebar.caption("""- **大きくすると:** 効果強、輝点も影響あり。\n- **小さくすると:** 効果弱。""")
    st.sidebar.subheader("3. 輝点フィルタリング (面積)") 
    min_area = st.sidebar.number_input('最小面積',min_value=1,max_value=10000,value=15,step=1) 
    st.sidebar.caption("""- **大きくすると:** 小さな輝点を除外。\n- **小さくすると:** ノイズを拾う可能性。""")
    max_area = st.sidebar.number_input('最大面積',min_value=1,max_value=100000,value=1000,step=1) 
    st.sidebar.caption("""- **大きくすると:** 大きな塊もカウント。\n- **小さくすると:** 大きな塊を除外。""")

    st.header("処理ステップごとの画像 (選択エリア内)")
    kernel_size_blur = 1
    if img_to_process.size==0: st.error("処理対象の画像領域が空です。"); st.stop()
    blurred_img = cv2.GaussianBlur(img_to_process, (kernel_size_blur,kernel_size_blur),0)
    ret_thresh, binary_img_processed = cv2.threshold(blurred_img,threshold_value,255,cv2.THRESH_BINARY)
    if not ret_thresh: st.error("二値化失敗。"); binary_img_for_morph_processed=None
    else: binary_img_for_morph_processed=binary_img_processed.copy()
    opened_img_processed = None 
    if binary_img_for_morph_processed is not None:
        kernel_morph_obj=cv2.getStructuringElement(morph_kernel_shape,(kernel_size_morph,kernel_size_morph))
        opened_img_processed=cv2.morphologyEx(binary_img_for_morph_processed,cv2.MORPH_OPEN,kernel_morph_obj)
        binary_img_for_contours_processed = opened_img_processed.copy()
    else: binary_img_for_contours_processed = None
    current_counted_spots = 0 
    output_image_contours_display = base_for_marking_bgr.copy()
    if binary_img_for_contours_processed is not None:
        contours, hierarchy = cv2.findContours(binary_img_for_contours_processed,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        if 'contours' in locals() and contours: 
            for contour in contours:
                area = cv2.contourArea(contour)
                if min_area <= area <= max_area:
                    current_counted_spots += 1
                    cv2.drawContours(output_image_contours_display, [contour], -1, (0,255,0), 2) 
        st.session_state.counted_spots_value = current_counted_spots 
    else:
        st.warning("輪郭検出の元画像準備できず。"); st.session_state.counted_spots_value="エラー"
    
    st.subheader("1. 二値化処理後 (選択エリア内)")
    if binary_img_processed is not None: st.image(binary_img_processed,caption=f'閾値:{threshold_value}',use_container_width=True)
    else: st.info("二値化未実施/失敗")
    st.markdown("---")
    st.subheader("2. 形態学的処理後 (選択エリア内)")
    if opened_img_processed is not None: st.image(opened_img_processed,caption=f'カーネル:{selected_shape_name} {kernel_size_morph}x{kernel_size_morph}',use_container_width=True)
    else: st.info("形態学的処理未実施/失敗")
    st.markdown("---")
    st.subheader("3. 輝点検出とマーキング (選択エリア内または全体)")
    display_final_marked_image = cv2.cvtColor(output_image_contours_display, cv2.COLOR_BGR2RGB)
    if 'contours' in locals() and contours and binary_img_for_contours_processed is not None and current_counted_spots > 0 :
         st.image(display_final_marked_image,caption=f'検出輝点(緑輪郭,面積:{min_area}-{max_area})',use_container_width=True)
    elif binary_img_for_contours_processed is not None: 
        st.image(display_final_marked_image,caption='輝点見つからず',use_container_width=True)
    else: st.info("輝点検出未実施")

    display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value)
else: 
    st.info("まず、サイドバーから画像ファイルをアップロードしてください。")
    st.session_state.counted_spots_value = "---"
    display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value)
