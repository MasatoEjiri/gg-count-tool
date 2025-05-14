import streamlit as st
from PIL import Image
import numpy as np
import cv2

# ★★★ ロゴ画像の表示 (ファイル名を実際のロゴ画像のファイル名に置き換えてください) ★★★
logo_image = Image.open("GG_logo.tiff") # 画像ファイルを読み込む
st.image(logo_image, width=300) # 画像を表示。widthで幅を調整 (お好みで)

# アプリのタイトルを設定
st.markdown("<h1>Gra&Green<br>輝点カウントツール</h1>", unsafe_allow_html=True)

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
    st.session_state.binary_threshold_value = 88

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
    else:
        img_gray = img_array.copy()

    kernel_size_blur = 1 

    st.sidebar.subheader("1. 二値化") 
    st.sidebar.markdown("この値を色々と変更して、「1. 二値化処理後」画像を実物に近づけてください。")
    
    # スライダーと数値入力で二値化閾値を設定 (キーを共有)
    st.sidebar.slider(
        '閾値 (スライダーで調整)', 
        min_value=0, 
        max_value=255, 
        step=1,
        key="binary_threshold_value" # セッションステートのキーを直接指定
    )
    st.sidebar.number_input(
        '閾値 (直接入力)', 
        min_value=0, 
        max_value=255, 
        step=1,
        key="binary_threshold_value" # 同じキーを指定
    )
    threshold_value = st.session_state.binary_threshold_value # 実際に使用する閾値
    
    st.sidebar.caption("""
    - **大きくすると:** より明るいピクセルのみが白（輝点候補）となり、背景ノイズは減りますが、暗めの輝点を見逃す可能性があります。
    - **小さくすると:** より暗いピクセルも白（輝点候補）となり、暗い輝点も拾いやすくなりますが、背景ノイズを拾いやすくなります。
    """)

    st.sidebar.subheader("2. 形態学的処理 (オープニング)") 
    morph_kernel_shape_options = { "楕円 (Ellipse)": cv2.MORPH_ELLIPSE, "矩形 (Rectangle)": cv2.MORPH_RECT, "十字 (Cross)": cv2.MORPH_CROSS }
    selected_shape_name = st.sidebar.selectbox( "カーネル形状", options=list(morph_kernel_shape_options.keys()), index=0) 
    morph_kernel_shape = morph_kernel_shape_options[selected_shape_name]
    st.sidebar.caption("輝点の形状に合わせて選択します。「楕円」は丸い輝点に適しています。")
    
    kernel_options_morph = [1, 3]
