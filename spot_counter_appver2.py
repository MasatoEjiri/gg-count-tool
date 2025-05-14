import streamlit as st
from PIL import Image
import numpy as np
import cv2
from streamlit_drawable_canvas import st_canvas
import io # バイトデータから画像を読み込むために必要

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
    st.header("1. 元の画像 と ROI選択")
    pil_image_original = None
    try:
        # アップロードされたファイルオブジェクトのバイトデータを取得
        uploaded_file_bytes = uploaded_file.getvalue()
        # バイトデータからPillowイメージを開く (ファイルポインタ問題を回避)
        pil_image_original = Image.open(io.BytesIO(uploaded_file_bytes))
        
        # 表示用にRGBのPillowイメージを準備
        pil_image_rgb_for_display = pil_image_original.convert("RGB")
        st.image(pil_image_rgb_for_display, caption='アップロードされた画像 (ROI選択用)', use_container_width=True)
        
    except Exception as e:
        st.error(f"画像の読み込みまたは表示に失敗しました: {e}")
        st.stop() # エラーならここで停止

    # PillowイメージをOpenCV処理用にNumPy配列に変換
    img_array_rgb_for_opencv = np.array(pil_image_rgb_for_display)
    img_gray_full = cv2.cvtColor(img_array_rgb_for_opencv, cv2.COLOR_RGB2GRAY)
    
    # グレースケール画像のデータ型調整 (8bit uintに)
    if img_gray_full.dtype != np.uint8:
        if img_gray_full.ndim == 2 and (img_gray_full.max() > 255 or img_gray_full.min() < 0 or img_gray_full.dtype != np.uint8):
            img_gray_full = cv2.normalize(img_gray_full, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        elif img_gray_full.ndim == 3: # 通常はRGB->GRAYで2Dになるはずだが念のため
            img_gray_full = cv2.cvtColor(img_gray_full, cv2.COLOR_BGR2GRAY).astype(np.uint8) # BGRと仮定
        else:
            try:
                img_gray_full_temp = img_gray_full.astype(np.uint8)
                if img_gray_full_temp.max() > 255 or img_gray_full_temp.min() < 0: # astypeで範囲外になった場合
                    img_gray_full = np.clip(img_gray_full, 0, 255).astype(np.uint8)
                    st.warning(f"グレースケール画像のデータ型/範囲をuint8に強制変換(クリップ)しました。")
                else:
                    img_gray_full = img_gray_full_temp
            except Exception as e_gray_conv:
                st.error(f"グレースケール画像のデータ型変換に失敗: {e_gray_conv}")
                st.stop()


    st.info("↑上の画像上で、解析したいエリアをマウスでドラッグして四角で囲ってください。最後に描画した四角形がROIとなります。")

    drawing_mode = "rect"; stroke_color = "red"
    canvas_result = st_canvas(
        fill_color="rgba(255,0,0,0.1)", stroke_width=2, stroke_color=stroke_color,
        background_image=pil_image_rgb_for_display, # 背景もPillowイメージ(RGB)
        update_streamlit=True, height=pil_image_rgb_for_display.height, width=pil_image_rgb_for_display.width,
        drawing_mode=drawing_mode, key="roi_canvas"
    )

    img_to_process = img_gray_full 
    roi_coords = None 
    base_for_marking_bgr = cv2.cvtColor(img_array_rgb_for_opencv, cv2.COLOR_RGB2BGR) 

    if canvas_result.json_data is not None and canvas_result.json_data.get("objects", []):
        if canvas_result.json_data["objects"][-1]["type"] == "rect":
            rect = canvas_result.json_data["objects"][-1]
            x, y, w, h = int(rect["left"]), int(rect["top"]), int(rect["width"]), int(rect["height"])
            if w > 0 and h > 0:
                img_h_full, img_w_full = img_gray_full.shape[:2]
                x1_roi, y1_roi = max(0, x), max(0, y)
                x2_roi, y2_roi = min(img_w_full, x + w), min(img_h_full, y + h)
                if (x2_roi - x1_roi > 0) and (y2_roi - y1_roi > 0):
                    roi_coords = (x1_roi, y1_roi, x2_roi - x1_roi, y2_roi - y1_roi)
                    img_to_process = img_gray_full[y1_roi:y2_roi, x1_roi:x2_roi].copy()
                    base_for_marking_bgr = cv2.cvtColor(img_array_rgb_for_opencv[y1_roi:y2_roi, x1_roi:x2_roi], cv2.COLOR_RGB2BGR)
                    st.subheader("選択されたROI（グレースケールでの処理対象）")
                    st.image(img_to_process, caption=f"処理対象ROI: x={x1_roi},y={y1_roi},w={x2_roi-x1_roi},h={y2_roi-y1_roi}", use_container_width=True)
                else:
                    st.warning("描画されたROIのサイズが無効。画像全体を処理します。")
                    img_to_process = img_gray_full 
    
    # --- サイドバーのパラメータ設定 ---
    st.sidebar.subheader("1. 二値化") 
    st.sidebar.markdown("_この値を色々と変更して、「1. 二値化処理後」画像を実物に近づけてください。_")
    st.sidebar.slider('閾値 (スライダーで調整)', min_value=0,max_value=255,step=1,value=st.session_state.binary_threshold_value,key="threshold_slider_for_binary",on_change=sync_threshold_from_slider)
    st.sidebar.number_input('閾値 (直接入力)', min_value=0,max_value=255,step=1,value=st.session_state.binary_threshold_value,key="threshold_number_for_binary",on_change=sync_threshold_from_number_input)
    threshold_value = st.session_state.binary_threshold_value 
    st.sidebar.caption("""- **大きくすると:** より明るいピクセルのみが白（輝点候補）となり、背景ノイズは減りますが、暗めの輝点を見逃す可能性があります。\n- **小さくすると:** より暗いピクセルも白（輝点候補）となり、暗い輝点も拾いやすくなりますが、背景ノイズを拾いやすくなります。""")
    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    st.sidebar.markdown("_二値化操作だけでうまくいかない場合は下記設定も変更してみてください。_")
    st.sidebar.subheader("2. 形態学的処理 (オープニング)") 
    morph_kernel_shape_options = { "楕円 (Ellipse)": cv2.MORPH_ELLIPSE, "矩形 (Rectangle)": cv2.MORPH_RECT, "十字 (Cross)": cv2.MORPH_CROSS }
    selected_shape_name = st.sidebar.selectbox( "カーネル形状", options=list(morph_kernel_shape_options.keys()), index=0) 
    morph_kernel_shape = morph_kernel_shape_options[selected_shape_name]
    st.sidebar.caption("輝点の形状に合わせて選択します。「楕円」は丸い輝点に適しています。")
    kernel_options_morph = [1, 3, 5, 7, 9]; kernel_size_morph = st.sidebar.select_slider( 'カーネルサイズ', options=kernel_options_morph, value=3)
    st.sidebar.caption("""- **大きくすると:** より大きなノイズや太い連結部分を除去する効果が高まりますが、輝点自体も削られ小さくなるか、消えてしまうことがあります。\n- **小さくすると:** 微細なノイズの除去や細い連結の切断に適しますが、効果が弱くなることがあります。""")
    st.sidebar.subheader("3. 輝点フィルタリング (面積)") 
    min_area = st.sidebar.number_input('輝点の最小面積 (ピクセル)', min_value=1, max_value=10000, value=15, step=1) 
    st.sidebar.caption("""- **大きくすると:** 小さすぎるノイズや非常に小さな輝点が除外され、カウント数が減ることがあります。\n- **小さくすると:** より小さな対象物も輝点としてカウントしますが、ノイズを誤検出する可能性も上がります。""")
    max_area = st.sidebar.number_input('輝点の最大面積 (ピクセル)', min_value=1, max_value=100000, value=1000, step=1) 
    st.sidebar.caption("""- **大きくすると:** より大きな塊も輝点としてカウントされるようになります。\n- **小さくすると:** 大きすぎる塊（例: 複数の輝点の結合、大きなゴミやアーティファクト）が除外され、カウント数が減ることがあります。""")

    # --- メインエリアでの画像表示と処理 (img_to_process を使用) ---
    st.header("処理ステップごとの画像")
    
    kernel_size_blur = 1 # 固定
    if img_to_process.size == 0: 
        st.error("処理対象の画像領域が空です。ROIを正しく描画してください。")
        st.stop()
        
    blurred_img = cv2.GaussianBlur(img_to_process, (kernel_size_blur, kernel_size_blur), 0)

    ret_thresh, binary_img_processed = cv2.threshold(blurred_img, threshold_value, 255, cv2.THRESH_BINARY)
    if not ret_thresh: st.error("二値化処理に失敗。"); binary_img_for_morph_processed = None
    else: binary_img_for_morph_processed = binary_img_processed.copy()
    
    opened_img_processed = None 
    if binary_img_for_morph_processed is not None:
        kernel_morph_obj = cv2.getStructuringElement(morph_kernel_shape, (kernel_size_morph, kernel_size_morph))
        opened_img_processed = cv2.morphologyEx(binary_img_for_morph_processed, cv2.MORPH_OPEN, kernel_morph_obj)
        binary_img_for_contours_processed = opened_img_processed.copy()
    else: binary_img_for_contours_processed = None

    current_counted_spots = 0 
    output_image_contours_display = base_for_marking_bgr.copy()

    if binary_img_for_contours_processed is not None:
        contours, hierarchy = cv2.findContours(binary_img_for_contours_processed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if 'contours' in locals() and contours: 
            for contour in contours:
                area = cv2.contourArea(contour)
                if min_area <= area <= max_area:
                    current_counted_spots += 1
                    cv2.drawContours(output_image_contours_display, [contour], -1, (0, 255, 0), 2) 
        st.session_state.counted_spots_value = current_counted_spots 
    else:
        st.warning("輪郭検出の元となる画像が準備できませんでした。")
        st.session_state.counted_spots_value = "エラー"

    st.subheader("1. 二値化処理後 (選択エリア内)")
    if binary_img_processed is not None: 
        st.image(binary_img_processed, caption=f'閾値: {threshold_value}', use_container_width=True)
    else: st.info("二値化未実施または失敗")
    st.markdown("---")

    st.subheader("2. 形態学的処理後 (選択エリア内)")
    if opened_img_processed is not None: 
        st.image(opened_img_processed, caption=f'カーネル: {selected_shape_name} {kernel_size_morph}x{kernel_size_morph}', use_container_width=True)
    else: st.info("形態学的処理未実施または失敗")
    st.markdown("---")

    st.subheader("3. 輝点検出とマーキング (選択エリア内または全体)")
    display_final_marked_image = cv2.cvtColor(output_image_contours_display, cv2.COLOR_BGR2RGB)
    if 'contours' in locals() and contours and binary_img_for_contours_processed is not None and current_counted_spots > 0 :
         st.image(display_final_marked_image, caption=f'検出された輝点 (緑の輪郭、面積範囲: {min_area}-{max_area})', use_container_width=True)
    elif binary_img_for_contours_processed is not None: 
        st.image(display_final_marked_image, caption='輝点は見つかりませんでした', use_container_width=True)
    else: st.info("輝点検出未実施")

    display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value)

else: 
    st.info("まず、サイドバーから画像ファイルをアップロードしてください。")
    st.session_state.counted_spots_value = "---"
    display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value)
