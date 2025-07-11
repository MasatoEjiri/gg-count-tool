import streamlit as st
from PIL import Image
import numpy as np
import cv2
import io
from streamlit_cropper import st_cropper

# ページ設定 (一番最初に呼び出す)
st.set_page_config(page_title="GG輝点解析ツール", layout="wide", initial_sidebar_state="expanded")

# メイン画面上部の余白を調整するためのCSS
st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem !important;
    }
</style>
""", unsafe_allow_html=True)

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
if "binary_threshold_value" not in st.session_state: st.session_state.binary_threshold_value = 15
if "threshold_slider" not in st.session_state: st.session_state.threshold_slider = st.session_state.binary_threshold_value
if "threshold_number" not in st.session_state: st.session_state.threshold_number = st.session_state.binary_threshold_value
if "saturation_value" not in st.session_state: st.session_state.saturation_value = 120
if "saturation_slider" not in st.session_state: st.session_state.saturation_slider = st.session_state.saturation_value
if "saturation_number" not in st.session_state: st.session_state.saturation_number = st.session_state.saturation_value
if "brightness_value" not in st.session_state: st.session_state.brightness_value = 60
if "brightness_slider" not in st.session_state: st.session_state.brightness_slider = st.session_state.brightness_value
if "brightness_number" not in st.session_state: st.session_state.brightness_number = st.session_state.brightness_value
if "hue_range_value" not in st.session_state: st.session_state.hue_range_value = (0, 20)
if "hue_range_slider" not in st.session_state: st.session_state
