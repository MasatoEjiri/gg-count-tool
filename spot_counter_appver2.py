import streamlit as st
from PIL import Image
import numpy as np
import cv2

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
        <p style="font-size: 18px; margin
