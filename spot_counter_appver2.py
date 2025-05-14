import streamlit as st
from PIL import Image
import numpy as np
import cv2

# ★★★ ロゴ表示部分を削除 ★★★
# try:
#     logo_image = Image.open("GG_logo.tiff") 
#     st.image(logo_image, width=180) 
# except FileNotFoundError:
#     st.error("ロゴ画像 (GG_logo.tiff) が見つかりません。アプリのメインファイルと同じフォルダに配置してください。")
# except Exception as e: 
#     st.error(f"ロゴ画像 (GG_logo.tiff) の読み込み中にエラーが発生しました: {e}")

# アプリのタイトルを設定
st.markdown("<h1>Gra&Green<br>輝点カウントツール</h1>", unsafe_allow_html=True)

# 「使用方法」
st.markdown("""
### 使用方法
1. 画像を左にアップロードしてください。
2. 左サイドバーの「1. 二値化」の閾値を動かして、「1. 二値化処理後」の画像が、輝点と背景が適切に分離された状態（実物に近い見え方）になるように調整してください。
3. （それでもカウント値がおかしい場合は、サイドバーの「2. 形態学的処理」や「3. 輝点フィルタリング」の各パラメータも調整してみてください。）
""")
st.markdown("---") # 区切り線

# --- 結果表示用のプレースホルダーをページ上部に定義 ---
result_placeholder = st.empty()

# --- カスタマイズされた結果表示関数 ---
def display_count_prominently(placeholder, count_value):
    label_text = "【解析結果】検出された輝点の数"
    value_text = str(count_value) 

    background_color = "#495057"
    label_font_color = "white"
    value_font_color = "white"
    border_color = "#343a40"

    html_content = f"""
    <div style="
        border: 1px solid {border_color}; 
        border-radius: 12px;
        padding: 25px;
        text-align: center;
        background-color: {background_color};
        margin-top: 10px;
        margin-bottom: 25px;
        box-shadow: 0 6px 15px rgba(0,0,0,0.2); 
        color: {label_font_color}; 
        max-width: 600px;
        margin-left: auto;
        margin-right: auto;
    ">
        <p style="font-size: 18px; margin-bottom: 8px;">{label_text}</p>
        <p style="font-size: 56px; font-weight: bold; margin-top: 0px; color: {value_font_color};">{value_text}</p>
    </div>
    """
    placeholder.markdown(html_content, unsafe_allow_html=True)

# --- セッションステートの初期化 ---
if 'counted_spots_value' not in st.session_state:
    st.session_state.counted_spots_value = "---" 
if "binary_threshold_value" not in st.session_state: 
    st.session_state.binary_threshold_value = 58
if "threshold_slider_for_binary" not in st.session_state: 
    st.session_state.threshold_slider_for_binary = st.session_state.binary_threshold_value
if "threshold_number_for_binary" not in st.session_state: 
    st.session_state.threshold_number_for_binary = st.session_state.binary_threshold_value

# --- コールバック関数の定義 ---
def sync_threshold_from_slider():
    st.session_state.binary_threshold_value = st.session_state.threshold_slider_for_binary
    st.session_state.threshold_number_for_binary = st.session_state.threshold_slider_for_binary

def sync_threshold_from_number_input():
    st.session_state.binary_threshold_value = st.session_state.threshold_number_for_binary
    st.session_state.threshold_slider_for_binary = st.session_state.threshold_number_for_binary

# --- サイドバーでパラメータを一元管理 ---
st.sidebar.header("解析パラメータ設定")

UPLOAD_ICON = "📤" 
uploaded_file = st.sidebar.file_uploader(
    f"{UPLOAD_ICON} 画像をアップロード",
    type=['tif', 'tiff', 'png', 'jpg', 'jpeg'],
    help="対応形式: TIF, TIFF, PNG, JPG, JPEG。ここにドラッグ＆ドロップするか、クリックしてファイルを選択してください。"
)

display_count_prominently(result_placeholder, st.session_state.counted_spots_value)

if uploaded_file is not None:
    pil_image = Image.open(uploaded_file)
    img_array = np.array(pil_image)
    original_img_display = img_array.copy() 

    if len(img_array.shape) == 3 and img_array.shape[2] == 3:
        img_gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    elif len(img_array.shape) == 3 and img_array.shape[2] == 4: 
        img_gray = cv2.cvtColor(img_array, cv2.COLOR_RGBA2GRAY)
    elif pil_image.mode == 'L': 
        img_gray = img_array.copy()
    elif pil_image.mode == 'LA': 
        temp_rgba = pil_image.convert('RGBA') 
        temp_array = np.array(temp_rgba)
        img_gray = cv2.cvtColor(temp_array, cv2.COLOR_RGBA2GRAY)
    elif pil_image.mode in ['I;16', 'I;16B', 'I;16L', 'I']: 
        if img_array.dtype == np.uint16 or img_array.dtype == np.int32 : # Add np.int32 for 'I' mode
            img_array_normalized = cv2.normalize(img_array, None, 0, 255, cv2.NORM_MINMAX)
            img_gray = img_array_normalized.astype(np.uint8)
        elif img_array.dtype == np.float32 or img_array.dtype == np.float64: # Handle float types
            img_array_normalized = cv2.normalize(img_array, None, 0, 255, cv2.NORM_MINMAX)
            img_gray = img_array_normalized.astype(np.uint8)
        else: 
            img_gray = img_array.astype(np.uint8) # Try to convert other types to uint8
            if img_gray.max() > 255 or img_gray.min() < 0: # if conversion is still not in range
                 st.warning(f"画像のモード ({pil_image.mode}, dtype: {img_array.dtype}) の8bit変換が不正確な可能性があります。値を0-255にクリップします。")
                 img_gray = np.clip(img_array, 0, 255).astype(np.uint8) # Fallback to clipping
            else:
                 st.warning(f"画像のモード ({pil_image.mode}, dtype: {img_array.dtype}) の8bit変換を行いました。")

    else: 
        img_gray = img_array.copy()
        st.warning(f"画像のモード ({pil_image.mode}) が予期しない形式です。グレースケール変換に失敗する可能性があります。")

    kernel_size_blur = 1 

    st.sidebar.subheader("1. 二値化") 
    st.sidebar.markdown("_この値を色々と変更して、「1. 二値化処理後」画像を実物に近づけてください。_")
    
    st.sidebar.slider(
        '閾値 (スライダーで調整)', 
        min_value=0, max_value=255, step=1,
        value=st.session_state.binary_threshold_value,
        key="threshold_slider_for_binary",
        on_change=sync_threshold_from_slider
    )
    st.sidebar.number_input(
        '閾値 (直接入力)', 
        min_value=0, max_value=255, step=1,
        value=st.session_state.binary_threshold_value,
        key="threshold_number_for_binary",
        on_change=sync_threshold_from_number_input
    )
    threshold_value = st.session_state.binary_threshold_value 
    
    st.sidebar.caption("""
    - **大きくすると:** より明るいピクセルのみが白（輝点候補）となり、背景ノイズは減りますが、暗めの輝点を見逃す可能性があります。
    - **小さくすると:** より暗いピクセルも白（輝点候補）となり、暗い輝点も拾いやすくなりますが、背景ノイズを拾いやすくなります。
    """)

    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    st.sidebar.markdown("_二値化操作だけでうまくいかない場合は下記設定も変更してみてください。_")

    st.sidebar.subheader("2. 形態学的処理 (オープニング)") 
    morph_kernel_shape_options = { "楕円 (Ellipse)": cv2.MORPH_ELLIPSE, "矩形 (Rectangle)": cv2.MORPH_RECT, "十字 (Cross)": cv2.MORPH_CROSS }
    selected_shape_name = st.sidebar.selectbox( "カーネル形状", options=list(morph_kernel_shape_options.keys()), index=0) 
    morph_kernel_shape = morph_kernel_shape_options[selected_shape_name]
    st.sidebar.caption("輝点の形状に合わせて選択します。「楕円」は丸い輝点に適しています。")
    
    kernel_options_morph = [1, 3, 5, 7, 9]
    kernel_size_morph = st.sidebar.select_slider( 'カーネルサイズ', options=kernel_options_morph, value=3)
    st.sidebar.caption("""
    - **大きくすると:** より大きなノイズや太い連結部分を除去する効果が高まりますが、輝点自体も削られ小さくなるか、消えてしまうことがあります。
    - **小さくすると:** 微細なノイズの除去や細い連結の切断に適しますが、効果が弱くなることがあります。
    """)

    st.sidebar.subheader("3. 輝点フィルタリング (面積)") 
    min_area = st.sidebar.number_input('輝点の最小面積 (ピクセル)', min_value=1, max_value=10000, value=1, step=1) 
    st.sidebar.caption("""
    - **大きくすると:** 小さすぎるノイズや非常に小さな輝点が除外され、カウント数が減ることがあります。
    - **小さくすると:** より小さな対象物も輝点としてカウントしますが、ノイズを誤検出する可能性も上がります。
    """)
    max_area = st.sidebar.number_input('輝点の最大面積 (ピクセル)', min_value=1, max_value=100000, value=1000, step=1) 
    st.sidebar.caption("""
    - **大きくすると:** より大きな塊も輝点としてカウントされるようになります。
    - **小さくすると:** 大きすぎる塊（例: 複数の輝点の結合、大きなゴミやアーティファクト）が除外され、カウント数が減ることがあります。
    """)

    # --- メインエリアでの画像表示と処理 ---
    st.header("処理ステップごとの画像")
    
    # グレースケール画像 img_gray が正しく処理可能な8bit画像であることを確認/変換
    if img_gray.dtype != np.uint8:
        if img_gray.ndim == 2 and (img_gray.max() > 255 or img_gray.min() < 0 or img_gray.dtype != np.uint8) : # 16bitグレースケールやfloatなど
            img_gray_normalized = cv2.normalize(img_gray, None, 0, 255, cv2.NORM_MINMAX)
            img_gray = img_gray_normalized.astype(np.uint8)
        elif img_gray.ndim == 3: # 何らかの理由で3チャンネルのまま来た場合 (通常は上で処理されるはず)
             st.warning(f"グレースケール変換後のはずの画像が3チャンネルです。再度グレースケール変換を試みます。")
             img_gray = cv2.cvtColor(img_gray, cv2.COLOR_BGR2GRAY) # BGRと仮定
        else: # その他の特殊なケースはエラーの可能性あり
            try:
                img_gray = img_gray.astype(np.uint8)
                if img_gray.max() > 255 or img_gray.min() < 0 :
                    img_gray = np.clip(img_gray, 0, 255).astype(np.uint8)
                    st.warning(f"グレースケール画像のデータ型/範囲をuint8に強制変換しました。")
            except Exception as e:
                st.error(f"グレースケール画像のデータ型変換に失敗しました: {e}")
                st.stop() # 処理を中断

    if kernel_size_blur > 0:
        blurred_img = cv2.GaussianBlur(img_gray, (kernel_size_blur, kernel_size_blur), 0)
    else:
        blurred_img = img_gray.copy()

    ret_thresh, binary_img_original = cv2.threshold(blurred_img, threshold_value, 255, cv2.THRESH_BINARY)
    if not ret_thresh:
        st.error("二値化処理に失敗しました。")
        binary_img_for_morph = None
    else:
        binary_img_for_morph = binary_img_original.copy()
    
    opened_img = None 
    if binary_img_for_morph is not None:
        kernel_morph = cv2.getStructuringElement(morph_kernel_shape, (kernel_size_morph, kernel_size_morph))
        opened_img = cv2.morphologyEx(binary_img_for_morph, cv2.MORPH_OPEN, kernel_morph)
        binary_img_for_contours = opened_img.copy()
    else: 
        binary_img_for_contours = None

    current_counted_spots = 0 
    output_image_contours = cv2.cvtColor(img_gray, cv2.COLOR_GRAY2BGR) # ベース画像を事前に準備

    if binary_img_for_contours is not None:
        contours, hierarchy = cv2.findContours(binary_img_for_contours, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if 'contours' in locals() and contours: 
            for contour in contours:
                area = cv2.contourArea(contour)
                if min_area <= area <= max_area:
                    current_counted_spots += 1
                    cv2.drawContours(output_image_contours, [contour], -1, (0, 255, 0), 2)
        st.session_state.counted_spots_value = current_counted_spots 
    else:
        st.warning("輪郭検出の元となる画像が準備できませんでした。前のステップを確認してください。")
        st.session_state.counted_spots_value = "エラー"

    # ★★★ メインエリアの画像表示を1カラムに変更 ★★★
    st.subheader("元の画像")
    st.image(original_img_display, caption='アップロードされた画像', use_container_width=True)
    st.markdown("---")

    st.subheader("1. 二値化処理後")
    if binary_img_for_morph is not None: 
        st.image(binary_img_original, caption=f'閾値: {threshold_value}', use_container_width=True)
    else:
        st.info("二値化未実施または失敗") # st.text から st.info に変更
    st.markdown("---")

    st.subheader("2. 形態学的処理後")
    if opened_img is not None: 
        st.image(opened_img, caption=f'カーネル: {selected_shape_name} {kernel_size_morph}x{kernel_size_morph}', use_container_width=True)
    else:
        st.info("形態学的処理未実施または失敗") # st.text から st.info に変更
    st.markdown("---")

    st.subheader("3. 輝点検出とマーキング")
    if 'contours' in locals() and contours and binary_img_for_contours is not None:
         st.image(output_image_contours, caption=f'検出された輝点 (緑の輪郭、面積範囲: {min_area}-{max_area})', use_container_width=True)
    elif binary_img_for_contours is not None: 
        st.image(output_image_contours, caption='輝点は見つかりませんでした', use_container_width=True)
    else:
        st.info("輝点検出未実施") # st.text から st.info に変更


    display_count_prominently(result_placeholder, st.session_state.counted_spots_value)

else: 
    st.info("まず、サイドバーから画像ファイルをアップロードしてください。")
    st.session_state.counted_spots_value = "---"
    display_count_prominently(result_placeholder, st.session_state.counted_spots_value)
