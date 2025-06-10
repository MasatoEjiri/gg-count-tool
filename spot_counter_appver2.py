import streamlit as st
from PIL import Image
import numpy as np
import cv2
from streamlit_cropper import st_cropper
import matplotlib.pyplot as plt

# st.set_option('deprecation.showfileUploaderEncoding', False) # この行を削除しました

st.title("画像範囲選択と解析アプリ")
st.write("画像をアップロードし、ドラッグして解析したい範囲を選択してください。")

# --- 1. 画像のアップロード ---
uploaded_file = st.file_uploader("画像ファイルを選択してください", type=['png', 'jpg', 'jpeg'])

if uploaded_file is not None:
    # Pillowを使って画像を読み込む
    img = Image.open(uploaded_file)
    
    # --- 2. streamlit-cropperで範囲選択 ---
    st.write("元画像")
    # st_cropperコンポーネントを呼び出し
    # realtime_update=Trueにすると、ドラッグ中にリアルタイムで情報が更新される
    # box_colorで選択範囲の枠線の色を変更可能
    cropped_img = st_cropper(img, realtime_update=True, box_color='blue', aspect_ratio=None)
    
    # --- 3. 選択範囲の表示と解析 ---
    st.write("プレビュー (選択範囲)")
    # use_column_width=True で画像の幅を列に合わせる
    st.image(cropped_img, use_column_width=True)
    
    # 解析実行ボタン
    if st.button("この範囲で解析を実行"):
        st.write("---")
        st.header("解析結果")

        # Pillow ImageをOpenCVで扱えるNumpy配列(BGR)に変換
        # Pillow(RGB) -> Numpy(RGB)
        cropped_array_rgb = np.array(cropped_img)
        # Numpy(RGB) -> Numpy(BGR) for OpenCV
        cropped_array_bgr = cv2.cvtColor(cropped_array_rgb, cv2.COLOR_RGB2BGR)

        # --- ここから画像解析処理 ---
        # 例1：グレースケール化して表示
        st.subheader("グレースケール画像")
        gray_cropped = cv2.cvtColor(cropped_array_bgr, cv2.COLOR_BGR2GRAY)
        st.image(gray_cropped, caption="解析結果 (グレースケール)")

        # 例2：選択範囲の平均輝度値を計算
        st.subheader("平均輝度値")
        # グレースケール画像の全ピクセルの平均値を計算
        avg_intensity = np.mean(gray_cropped)
        st.write(f"選択範囲の平均輝度値は **{avg_intensity:.2f}** です。")
        
        # 例3: カラーヒストグラムの表示
        st.subheader("カラーヒストグラム")
        fig, ax = plt.subplots() # st.pyplot()を使うためにmatplotlibのオブジェクトを生成
        color = ('b','g','r')
        for i, col in enumerate(color):
            histr = cv2.calcHist([cropped_array_bgr],[i],None,[256],[0,256])
            ax.plot(histr,color = col)
            ax.set_xlim([0,256])
        ax.set_title('Color Histogram')
        ax.set_xlabel('Pixel Value')
        ax.set_ylabel('Frequency')
        st.pyplot(fig) # Streamlitでmatplotlibのグラフを表示
        
        # --- ここまで画像解析処理 ---
        st.info("💡 上記の解析処理の部分を、目的のコード（物体検出、OCRなど）に置き換えてください。")
