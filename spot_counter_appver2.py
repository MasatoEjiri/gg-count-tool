import streamlit as st
from PIL import Image
import numpy as np
import cv2
from streamlit_drawable_canvas import st_canvas # ★★★ インポート追加 ★★★

# ★★★ ページ設定: ブラウザタブのタイトルを変更 ★★★
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

# アプリのタイトルを設定 (メインエリア)
st.markdown("<h1>Gra&Green<br>輝点カウントツール</h1>", unsafe_allow_html=True)

# 「使用方法」(メインエリア)
st.markdown("""
### 使用方法
1. 画像を左にアップロードしてください。
2. **(オプション)** 元の画像の下に表示されるキャンバス上で、解析したいエリアをマウスでドラッグして四角で囲ってください。囲まない場合は画像全体が対象になります。
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
    pil_image = Image.open(uploaded_file)
    # オリジナル画像をカラーで保持 (表示用と、ROI選択後のカラーでのマーキング用)
    original_color_for_marking = np.array(pil_image.convert("RGB"))
    
    # グレースケール画像を作成 (これは常に画像全体から作る)
    img_gray_full = cv2.cvtColor(original_color_for_marking, cv2.COLOR_RGB2GRAY)
    # (より詳細なグレースケール変換ロジックは、必要に応じて前回のものをここに組み込んでください)
    if img_gray_full.dtype != np.uint8: # 基本的な8bit化
        img_gray_full = cv2.normalize(img_gray_full, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)


    st.header("1. 元の画像 と ROI選択")
    st.image(original_color_for_marking, caption='アップロードされた画像 (ROI選択用)', use_container_width=True)
    
    st.info("↑上の画像上で、解析したいエリアをマウスでドラッグして四角で囲ってください。最後に描画した四角形がROIとなります。")

    drawing_mode = "rect"
    stroke_color = "red"
    # Pillow Imageを背景にする場合、st_canvasはPillow Imageを直接受け付ける
    canvas_result = st_canvas(
        fill_color="rgba(255, 0, 0, 0.1)",
        stroke_width=2,
        stroke_color=stroke_color,
        background_image=pil_image, # 元のPillow Imageを背景に
        update_streamlit=True, # 描画のたびに再実行
        height=pil_image.height, # キャンバスの高さを画像に合わせる
        width=pil_image.width,   # キャンバスの幅を画像に合わせる
        drawing_mode=drawing_mode,
        key="roi_canvas"
    )

    img_to_process = img_gray_full # デフォルトは画像全体
    roi_display_img = None       # ROI部分の切り出し画像表示用
    roi_coords = None            # (x, y, w, h) を格納

    if canvas_result.json_data is not None and canvas_result.json_data["objects"]:
        # 最後に描画された四角形を取得 (objectsが空でないことを確認)
        if canvas_result.json_data["objects"][-1]["type"] == "rect":
            rect_data = canvas_result.json_data["objects"][-1]
            x, y, w, h = int(rect_data["left"]), int(rect_data["top"]), int(rect_data["width"]), int(rect_data["height"])
            
            if w > 0 and h > 0: # 有効な四角形か
                # 元のグレースケール画像からROIを切り出す
                img_h_full, img_w_full = img_gray_full.shape[:2]
                x1_roi, y1_roi = max(0, x), max(0, y)
                x2_roi, y2_roi = min(img_w_full, x + w), min(img_h_full, y + h)

                if (x2_roi - x1_roi > 0) and (y2_roi - y1_roi > 0):
                    img_to_process = img_gray_full[y1_roi:y2_roi, x1_roi:x2_roi].copy()
                    roi_display_img = img_to_process # 表示用に保持
                    roi_coords = (x1_roi, y1_roi, x2_roi - x1_roi, y2_roi - y1_roi) # (x, y, w, h)形式で保存
                    st.subheader("選択されたROI（グレースケール）")
                    st.image(roi_display_img, caption=f"処理対象ROI: x={x1_roi}, y={y1_roi}, w={x2_roi-x1_roi}, h={y2_roi-y1_roi}", use_container_width=True)
                else:
                    st.warning("描画されたROIのサイズが無効です。画像全体を処理します。")
                    img_to_process = img_gray_full # ROIが無効なら全体を処理
            # else: # wかhが0以下なら、有効なROIではない
                # st.info("四角形を描画してROIを選択してください。ない場合は画像全体を処理します。")
    # else: # json_dataがないか、objectsが空の場合
        # st.info("四角形を描画してROIを選択してください。ない場合は画像全体を処理します。")

    # --- サイドバーのパラメータ設定 ---
    # (この部分は変更なし、ただし処理対象が img_to_process になることを意識)
    st.sidebar.subheader("1. 二値化") 
    st.sidebar.markdown("_この値を色々と変更して、「1. 二値化処理後」画像を実物に近づけてください。_")
    st.sidebar.slider('閾値 (スライダーで調整)', min_value=0, max_value=255, step=1, value=st.session_state.binary_threshold_value, key="threshold_slider_for_binary", on_change=sync_threshold_from_slider)
    st.sidebar.number_input('閾値 (直接入力)', min_value=0, max_value=255, step=1, value=st.session_state.binary_threshold_value, key="threshold_number_for_binary", on_change=sync_threshold_from_number_input)
    threshold_value = st.session_state.binary_threshold_value 
    st.sidebar.caption("...") # キャプション省略

    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    st.sidebar.markdown("_二値化操作だけでうまくいかない場合は下記設定も変更してみてください。_")

    st.sidebar.subheader("2. 形態学的処理 (オープニング)") 
    morph_kernel_shape_options = { "楕円 (Ellipse)": cv2.MORPH_ELLIPSE, "矩形 (Rectangle)": cv2.MORPH_RECT, "十字 (Cross)": cv2.MORPH_CROSS }
    selected_shape_name = st.sidebar.selectbox( "カーネル形状", options=list(morph_kernel_shape_options.keys()), index=0) 
    morph_kernel_shape = morph_kernel_shape_options[selected_shape_name]
    st.sidebar.caption("...") # キャプション省略
    kernel_options_morph = [1, 3, 5, 7, 9]
    kernel_size_morph = st.sidebar.select_slider( 'カーネルサイズ', options=kernel_options_morph, value=3)
    st.sidebar.caption("...") # キャプション省略

    st.sidebar.subheader("3. 輝点フィルタリング (面積)") 
    min_area = st.sidebar.number_input('輝点の最小面積 (ピクセル)', min_value=1, max_value=10000, value=15, step=1) 
    st.sidebar.caption("...") # キャプション省略
    max_area = st.sidebar.number_input('輝点の最大面積 (ピクセル)', min_value=1, max_value=100000, value=1000, step=1) 
    st.sidebar.caption("...") # キャプション省略


    # --- メインエリアでの画像表示と処理 (img_to_process を使用) ---
    st.header("処理ステップごとの画像 (選択エリア内)")
    
    kernel_size_blur = 1 # 固定
    if kernel_size_blur > 0 and img_to_process is not None and img_to_process.size > 0 : # ROIが有効か確認
        blurred_img = cv2.GaussianBlur(img_to_process, (kernel_size_blur, kernel_size_blur), 0)
    elif img_to_process is not None and img_to_process.size > 0:
        blurred_img = img_to_process.copy()
    else: # img_to_process がない (ROI選択に失敗など)
        st.error("処理対象の画像領域がありません。")
        st.stop() # アプリの実行をここで止める

    ret_thresh, binary_img_processed = cv2.threshold(blurred_img, threshold_value, 255, cv2.THRESH_BINARY)
    if not ret_thresh:
        st.error("二値化処理に失敗しました。")
        binary_img_for_morph_processed = None
    else:
        binary_img_for_morph_processed = binary_img_processed.copy()
    
    opened_img_processed = None 
    if binary_img_for_morph_processed is not None:
        kernel_morph_obj = cv2.getStructuringElement(morph_kernel_shape, (kernel_size_morph, kernel_size_morph))
        opened_img_processed = cv2.morphologyEx(binary_img_for_morph_processed, cv2.MORPH_OPEN, kernel_morph_obj)
        binary_img_for_contours_processed = opened_img_processed.copy()
    else: 
        binary_img_for_contours_processed = None

    current_counted_spots = 0
    
    # 結果描画用のベース画像 (ROIが選択されていればROI部分のカラー画像、なければ画像全体のカラー画像)
    if roi_coords:
        x, y, w, h = roi_coords
        # オリジナルのカラー画像からROI部分を切り出して、それにマーキングする
        base_for_marking = original_color_for_marking[y:y+h, x:x+w].copy()
        # もし original_color_for_marking が BGR 順でない場合は注意 (PillowはRGB、OpenCVはBGR)
        # ここでは original_color_for_marking は np.array(pil_image.convert("RGB")) なのでRGBのはず。
        # cv2.drawContours はBGRを期待するので、必要なら変換する。
        if base_for_marking.shape[2] == 3: # カラー画像であることの確認
             base_for_marking_bgr = cv2.cvtColor(base_for_marking, cv2.COLOR_RGB2BGR)
        else: # グレースケールだった場合 (ありえないはずだが念のため)
             base_for_marking_bgr = cv2.cvtColor(base_for_marking, cv2.COLOR_GRAY2BGR)

        output_image_contours = base_for_marking_bgr
    else: # ROIが選択されていない場合は、画像全体のグレースケールをカラー変換して使う
        output_image_contours = cv2.cvtColor(img_gray_full, cv2.COLOR_GRAY2BGR)


    if binary_img_for_contours_processed is not None:
        contours, hierarchy = cv2.findContours(binary_img_for_contours_processed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if 'contours' in locals() and contours: 
            for contour in contours:
                area = cv2.contourArea(contour)
                if min_area <= area <= max_area:
                    current_counted_spots += 1
                    # 輪郭は output_image_contours (ROI部分または全体) に描画
                    cv2.drawContours(output_image_contours, [contour], -1, (0, 255, 0), 2) # 緑色
        st.session_state.counted_spots_value = current_counted_spots 
    else:
        st.warning("輪郭検出の元となる画像が準備できませんでした。")
        st.session_state.counted_spots_value = "エラー"

    # --- メインエリアの画像表示を1カラムに変更 ---
    st.subheader("1. 二値化処理後 (選択エリア内)")
    if binary_img_for_morph_processed is not None: 
        st.image(binary_img_processed, caption=f'閾値: {threshold_value}', use_container_width=True)
    else:
        st.info("二値化未実施または失敗")
    st.markdown("---")

    st.subheader("2. 形態学的処理後 (選択エリア内)")
    if opened_img_processed is not None: 
        st.image(opened_img_processed, caption=f'カーネル: {selected_shape_name} {kernel_size_morph}x{kernel_size_morph}', use_container_width=True)
    else:
        st.info("形態学的処理未実施または失敗")
    st.markdown("---")

    st.subheader("3. 輝点検出とマーキング (選択エリア内)")
    # output_image_contours は常に定義されているはず (ROI部分または全体)
    # cv2.cvtColor(output_image_contours, cv2.COLOR_BGR2RGB) で表示した方が色が正しいかも
    # (ただし original_color_for_marking がRGBなら、base_for_marking_bgr を表示するときにRGBに戻す)
    if roi_coords and base_for_marking.shape[2] == 3: # ROIがありカラーの場合
        display_marked_image = cv2.cvtColor(output_image_contours, cv2.COLOR_BGR2RGB)
    else: # ROIがないか、元がグレースケールだった場合 (output_image_contoursはBGRになっている)
        display_marked_image = cv2.cvtColor(output_image_contours, cv2.COLOR_BGR2RGB)

    if 'contours' in locals() and contours and binary_img_for_contours_processed is not None:
         st.image(display_marked_image, caption=f'検出された輝点 (緑の輪郭、面積範囲: {min_area}-{max_area})', use_container_width=True)
    elif binary_img_for_contours_processed is not None: 
        st.image(display_marked_image, caption='輝点は見つかりませんでした', use_container_width=True)
    else:
        st.info("輝点検出未実施")

    # サイドバー上部のプレースホルダーを最新のカウント数で更新
    display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value)

else: 
    st.info("まず、サイドバーから画像ファイルをアップロードしてください。")
    st.session_state.counted_spots_value = "---"
    display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value)
