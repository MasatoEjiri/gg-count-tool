import streamlit as st
from PIL import Image
import numpy as np
import cv2
import io
import requests # Google Driveからのダウンロードに必要
import re       # Google DriveのリンクからファイルIDを抽出するために必要

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
1. 画像を左にアップロードしてください。（またはGoogle Driveのリンクを指定）
2. 左サイドバーの「1. 二値化」の閾値を動かして、「1. 二値化処理後」の画像が、輝点と背景が適切に分離された状態（実物に近い見え方）になるように調整してください。
3. （それでもカウント値がおかしい場合は、サイドバーの「2. 形態学的処理」や「3. 輝点フィルタリング」の各パラメータも調整してみてください。）
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

# 画像入力方法の選択
input_method = st.sidebar.radio(
    "画像の入力方法を選択:",
    ('ローカルファイルからアップロード', 'Google Drive の共有リンクを使用'),
    key="input_method_radio"
)

pil_image_original = None # 読み込まれたPillowイメージオブジェクトを格納

if input_method == 'ローカルファイルからアップロード':
    UPLOAD_ICON = "📤" 
    uploaded_file_local = st.sidebar.file_uploader(
        f"{UPLOAD_ICON} 画像をアップロード", 
        type=['tif', 'tiff', 'png', 'jpg', 'jpeg'], 
        help="対応形式: TIF, TIFF, PNG, JPG, JPEG。"
    )
    if uploaded_file_local is not None:
        try:
            uploaded_file_bytes = uploaded_file_local.getvalue()
            pil_image_original = Image.open(io.BytesIO(uploaded_file_bytes))
        except Exception as e:
            st.sidebar.error(f"ローカル画像の読み込みに失敗: {e}")
            pil_image_original = None
            st.session_state.counted_spots_value = "エラー" # エラー時はカウントもエラーに

elif input_method == 'Google Drive の共有リンクを使用':
    gdrive_url = st.sidebar.text_input("Google Drive の共有可能な画像リンク:", help="「リンクを知っている全員」に共有設定してください。")
    if gdrive_url:
        file_id = None
        # 様々なGoogle Driveリンク形式からファイルIDを抽出
        patterns = [
            r'/file/d/([a-zA-Z0-9_-]+)/view',
            r'/file/d/([a_zA-Z0-9_-]+)/edit',
            r'id=([a-zA-Z0-9_-]+)',
            r'/d/([a-zA-Z0-9_-]{25,})' # Direct link often has longer ID like this
        ]
        for pattern in patterns:
            match = re.search(pattern, gdrive_url)
            if match:
                file_id = match.group(1)
                break
        
        if file_id:
            st.sidebar.info(f"ファイルID: {file_id} を検出しました。ダウンロードを試みます...")
            download_url = f'https://drive.google.com/uc?export=download&id={file_id}'
            try:
                response = requests.get(download_url, stream=True, timeout=15) # タイムアウトを設定
                response.raise_for_status()
                pil_image_original = Image.open(io.BytesIO(response.content))
                st.sidebar.success("Google Driveから画像を読み込みました！")
            except requests.exceptions.Timeout:
                st.sidebar.error("Google Driveからのダウンロードがタイムアウトしました。ファイルサイズが大きいか、ネットワークが不安定かもしれません。")
                pil_image_original = None
                st.session_state.counted_spots_value = "エラー"
            except requests.exceptions.RequestException as e:
                st.sidebar.error(f"Google Driveからのダウンロードに失敗: {e}")
                st.sidebar.caption("ファイルの共有設定（「リンクを知っている全員が閲覧可」）、リンクの正しさを確認してください。")
                pil_image_original = None
                st.session_state.counted_spots_value = "エラー"
            except Exception as e_pil:
                st.sidebar.error(f"ダウンロードした画像をPillowで開けませんでした: {e_pil}")
                pil_image_original = None
                st.session_state.counted_spots_value = "エラー"
        elif gdrive_url: # URLは入力されたがIDが見つからない場合
            st.sidebar.warning("有効なGoogle DriveリンクからファイルIDを抽出できませんでした。")
            pil_image_original = None
            st.session_state.counted_spots_value = "---"


# サイドバー上部のプレースホルダーに初期/更新後のカウント数を表示
display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value)

# --- メイン処理 (画像が正常に読み込めた場合のみ実行) ---
if pil_image_original is not None:
    # 表示用にRGBのPillowイメージを準備
    try:
        pil_image_rgb_for_display = pil_image_original.convert("RGB")
    except Exception as e:
        st.error(f"画像のRGB変換に失敗しました: {e}")
        st.stop()

    # OpenCV処理用にNumPy配列を準備
    img_array_rgb_for_opencv = np.array(pil_image_rgb_for_display) 
    img_gray = cv2.cvtColor(img_array_rgb_for_opencv, cv2.COLOR_RGB2GRAY)
    
    # グレースケール画像のデータ型調整 (8bit uintに)
    if img_gray.dtype != np.uint8:
        if img_gray.ndim == 2 and (img_gray.max() > 255 or img_gray.min() < 0 or img_gray.dtype != np.uint8):
            img_gray = cv2.normalize(img_gray, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        elif img_gray.ndim == 3:
            img_gray = cv2.cvtColor(img_gray, cv2.COLOR_BGR2GRAY).astype(np.uint8)
        else:
            try:
                img_gray_temp = img_gray.astype(np.uint8)
                if img_gray_temp.max() > 255 or img_gray_temp.min() < 0:
                    img_gray = np.clip(img_gray, 0, 255).astype(np.uint8)
                else: img_gray = img_gray_temp
            except Exception as e_gray_conv:
                st.error(f"グレースケール画像のデータ型変換に失敗: {e_gray_conv}"); st.stop()
    
    # --- サイドバーの残りのパラメータ設定UI ---
    # (これらのUIは画像が読み込まれた後に表示されるか、値が使われる)
    st.sidebar.subheader("1. 二値化") 
    st.sidebar.markdown("_この値を色々と変更して、「1. 二値化処理後」画像を実物に近づけてください。_")
    st.sidebar.slider('閾値 (スライダーで調整)', min_value=0,max_value=255,step=1,value=st.session_state.binary_threshold_value,key="threshold_slider_for_binary",on_change=sync_threshold_from_slider)
    st.sidebar.number_input('閾値 (直接入力)', min_value=0,max_value=255,step=1,value=st.session_state.binary_threshold_value,key="threshold_number_for_binary",on_change=sync_threshold_from_number_input)
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

    # --- メインエリアでの画像表示と処理 ---
    st.header("処理ステップごとの画像")
    
    kernel_size_blur = 1 
    if img_gray is None or img_gray.size == 0 : 
        st.error("グレースケール画像の準備に失敗。処理を続行できません。")
        st.stop()
        
    blurred_img = cv2.GaussianBlur(img_gray, (kernel_size_blur,kernel_size_blur),0)

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
    output_image_contours_display_bgr = cv2.cvtColor(img_gray, cv2.COLOR_GRAY2BGR) # ベースは全体のグレースケールから

    if binary_img_for_contours_processed is not None:
        contours, hierarchy = cv2.findContours(binary_img_for_contours_processed,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        if 'contours' in locals() and contours: 
            for contour in contours:
                area = cv2.contourArea(contour)
                if min_area <= area <= max_area:
                    current_counted_spots += 1
                    cv2.drawContours(output_image_contours_display_bgr, [contour], -1, (0,255,0), 2) 
        st.session_state.counted_spots_value = current_counted_spots 
    else:
        st.warning("輪郭検出の元画像準備できず。"); st.session_state.counted_spots_value="エラー"
    
    st.subheader("元の画像")
    st.image(pil_image_rgb_for_display, caption='アップロードされた画像', use_container_width=True) # 表示はPillow RGB
    st.markdown("---")

    st.subheader("1. 二値化処理後")
    if binary_img_processed is not None: st.image(binary_img_processed,caption=f'閾値:{threshold_value}',use_container_width=True)
    else: st.info("二値化未実施/失敗")
    st.markdown("---")

    st.subheader("2. 形態学的処理後")
    if opened_img_processed is not None: st.image(opened_img_processed,caption=f'カーネル:{selected_shape_name} {kernel_size_morph}x{kernel_size_morph}',use_container_width=True)
    else: st.info("形態学的処理未実施/失敗")
    st.markdown("---")

    st.subheader("3. 輝点検出とマーキング")
    try:
        display_final_marked_image_rgb = cv2.cvtColor(output_image_contours_display_bgr, cv2.COLOR_BGR2RGB)
        if 'contours' in locals() and contours and binary_img_for_contours_processed is not None and current_counted_spots > 0 :
             st.image(display_final_marked_image_rgb,caption=f'検出輝点(緑輪郭,面積:{min_area}-{max_area})',use_container_width=True)
        elif binary_img_for_contours_processed is not None: 
            st.image(display_final_marked_image_rgb,caption='輝点見つからず',use_container_width=True)
        else: st.info("輝点検出未実施")
    except Exception as e_mark_disp:
        st.error(f"マーキング画像の表示に失敗: {e_mark_disp}")

    # サイドバー上部のプレースホルダーを最新のカウント数で更新 (処理の最後に再度呼び出し)
    display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value)

else: # 画像がアップロードもリンク指定もされていない場合
    st.info("まず、サイドバーから画像入力方法を選択し、画像を準備してください。")
    st.session_state.counted_spots_value = "---"
    display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value)
