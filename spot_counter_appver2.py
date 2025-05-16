import streamlit as st
from PIL import Image
import numpy as np
import cv2
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
    # placeholder.container() を使ってクリアしてから書き込むと確実
    with placeholder.container():
        placeholder.markdown(html_content, unsafe_allow_html=True)


# --- セッションステートの初期化 ---
if 'counted_spots_value' not in st.session_state: st.session_state.counted_spots_value = "---" 
if "binary_threshold_value" not in st.session_state: st.session_state.binary_threshold_value = 58
if "threshold_slider_for_binary" not in st.session_state: st.session_state.threshold_slider_for_binary = st.session_state.binary_threshold_value
if "threshold_number_for_binary" not in st.session_state: st.session_state.threshold_number_for_binary = st.session_state.binary_threshold_value
if 'pil_image_to_process' not in st.session_state: st.session_state.pil_image_to_process = None
if 'image_source_caption' not in st.session_state: st.session_state.image_source_caption = "アップロードされた画像"


# --- コールバック関数の定義 ---
def sync_threshold_from_slider():
    st.session_state.binary_threshold_value = st.session_state.threshold_slider_for_binary
    st.session_state.threshold_number_for_binary = st.session_state.threshold_slider_for_binary
def sync_threshold_from_number_input():
    st.session_state.binary_threshold_value = st.session_state.threshold_number_for_binary
    st.session_state.threshold_slider_for_binary = st.session_state.threshold_number_for_binary

# --- サイドバーの定義開始 ---

# ★★★ 解析結果をサイドバーの最上部に表示 ★★★
display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value) 

st.sidebar.header("解析パラメータ設定")
UPLOAD_ICON = "📤" 
uploaded_file_widget = st.sidebar.file_uploader(f"{UPLOAD_ICON} 画像をアップロード", type=['tif', 'tiff', 'png', 'jpg', 'jpeg'], help="対応形式: TIF, TIFF, PNG, JPG, JPEG。")

# (パラメータ設定UIは、結果表示とメインヘッダーの後に配置)
st.sidebar.subheader("1. 二値化") 
st.sidebar.markdown("_この値を色々と変更して、「1. 二値化処理後」画像を実物に近づけてください。_")
st.sidebar.slider('閾値 (スライダーで調整)', min_value=0,max_value=255,step=1,value=st.session_state.binary_threshold_value,key="threshold_slider_for_binary",on_change=sync_threshold_from_slider)
st.sidebar.number_input('閾値 (直接入力)', min_value=0,max_value=255,step=1,value=st.session_state.binary_threshold_value,key="threshold_number_for_binary",on_change=sync_threshold_from_number_input)
threshold_value_sb = st.session_state.binary_threshold_value # サイドバーで設定された値を保持
st.sidebar.caption("""- **大きくすると:** 明るい部分のみ白に。\n- **小さくすると:** 暗い部分も白に。""")

st.sidebar.markdown("<br>", unsafe_allow_html=True) 
st.sidebar.markdown("_二値化操作だけでうまくいかない場合は下記設定も変更してみてください。_") 

st.sidebar.subheader("2. 形態学的処理 (オープニング)") 
morph_kernel_shape_options = {"楕円":cv2.MORPH_ELLIPSE,"矩形":cv2.MORPH_RECT,"十字":cv2.MORPH_CROSS}
selected_shape_name_sb = st.sidebar.selectbox("カーネル形状",options=list(morph_kernel_shape_options.keys()),index=0, key="morph_shape_sb_key") 
morph_kernel_shape_sb = morph_kernel_shape_options[selected_shape_name_sb]
st.sidebar.caption("輝点の形状に合わせて。") 
kernel_options_morph = [1,3,5,7,9]
kernel_size_morph_sb =st.sidebar.select_slider('カーネルサイズ',options=kernel_options_morph,value=3, key="morph_size_sb_key")
st.sidebar.caption("""- **大きくすると:** 効果強、輝点も影響あり。\n- **小さくすると:** 効果弱。""") 

st.sidebar.subheader("3. 輝点フィルタリング (面積)") 
# ★★★ 最小面積のデフォルト値を1に変更 ★★★
min_area_sb = st.sidebar.number_input('最小面積',
