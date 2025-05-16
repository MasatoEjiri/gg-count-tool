import streamlit as st
from PIL import Image
import numpy as np
import cv2
import io

# ページ設定
st.set_page_config(page_title="輝点解析ツール", layout="wide")

# ★★★ キャッシュする画像読み込み関数を定義 ★★★
@st.cache_data
def load_and_prepare_image_data(uploaded_file_bytes):
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
        
    return original_img_to_display_np_uint8, img_gray

# (これ以降、display_count_in_sidebar関数、タイトル、使用方法、セッションステート初期化、コールバック関数定義は変更なし)
# ...
