import streamlit as st
from PIL import Image
import numpy as np
import cv2
import io

# ページ設定
st.set_page_config(page_title="輝点解析ツール", layout="wide")

# ファイルアップローダーのカスタムCSS (変更なし)
file_uploader_css = """<style>...</style>""" # CSSは変更なしのため省略
st.markdown(file_uploader_css, unsafe_allow_html=True)

result_placeholder_sidebar = st.sidebar.empty()
def display_count_in_sidebar(placeholder, count_value):
    label_text = "【解析結果】輝点数"; value_text = str(count_value) 
    bg="#495057"; lf="white"; vf="white"
    html=f"""<div style="border-radius:8px;padding:15px;text-align:center;background-color:{bg};margin-bottom:15px;color:{lf};"><p style="font-size:16px;margin-bottom:5px;font-weight:bold;">{label_text}</p><p style="font-size:48px;font-weight:bold;margin-top:0px;color:{vf};line-height:1.1;">{value_text}</p></div>"""
    with placeholder.container(): placeholder.markdown(html, unsafe_allow_html=True)

# セッションステート初期化
default_ss = {'counted_spots_value':"---","binary_threshold_value":58,"threshold_slider_for_binary":58,"threshold_number_for_binary":58,'pil_image_original_full_res':None, 'image_source_caption':"アップロードされた画像"} # pil_image_to_process を pil_image_original_full_res に変更
for k,v in default_ss.items():
    if k not in st.session_state: st.session_state[k]=v

def sync_threshold_from_slider(): st.session_state.binary_threshold_value=st.session_state.threshold_slider_for_binary; st.session_state.threshold_number_for_binary=st.session_state.threshold_slider_for_binary
def sync_threshold_from_number_input(): st.session_state.binary_threshold_value=st.session_state.threshold_number_for_binary; st.session_state.threshold_slider_for_binary=st.session_state.threshold_number_for_binary

display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value) 
st.sidebar.header("解析パラメータ設定")
UPLOAD_ICON="📤"; uploaded_file_widget=st.sidebar.file_uploader(f"{UPLOAD_ICON} 画像をアップロード",type=['tif','tiff','png','jpg','jpeg'],help="対応形式: TIF,TIFF,PNG,JPG,JPEG。")

st.markdown("<h1>Gra&Green<br>輝点カウントツール</h1>",unsafe_allow_html=True)
st.markdown("""### 使用方法
1. 画像を左にアップロードしてください。
2. 画像をアップロードすると、左サイドバーに詳細な解析パラメータが表示されます。
3. まず「1. 二値化」の閾値を動かし、「1. 二値化処理後」の画像（表示は縮小、解析は元サイズ）が実物に近い見え方になるよう調整してください。
4. 必要に応じて「2. 形態学的処理」や「3. 輝点フィルタリング」のパラメータも調整します。
""")
st.markdown("---") 

# 画像読み込みロジック
if uploaded_file_widget is not None:
    try:
        uploaded_file_bytes = uploaded_file_widget.getvalue()
        pil_img_original = Image.open(io.BytesIO(uploaded_file_bytes))
        st.session_state.pil_image_original_full_res = pil_img_original # ★★★ フル解像度で保存 ★★★
        st.session_state.image_source_caption = f"アップロード: {uploaded_file_widget.name} (元サイズ: {pil_img_original.width}x{pil_img_original.height}px)"
    except Exception as e:
        st.sidebar.error(f"アップロード画像の読み込みに失敗: {e}")
        st.session_state.pil_image_original_full_res = None 
        st.session_state.counted_spots_value = "読込エラー"; st.stop()
else: 
    if st.session_state.pil_image_original_full_res is not None: 
        st.session_state.pil_image_original_full_res = None
        st.session_state.counted_spots_value = "---" 

# メイン処理
if st.session_state.pil_image_original_full_res is not None:
    # --- サイドバーのパラメータ設定UI (画像ロード後に表示) ---
    # (内容は変更なしのため省略、前回と同じ)
    st.sidebar.subheader("1. 二値化") 
    st.sidebar.markdown("_この値を色々変更して、「1. 二値化処理後」画像を実物に近づけてください。_")
    st.sidebar.slider('閾値 (スライダーで調整)',min_value=0,max_value=255,step=1,value=st.session_state.binary_threshold_value,key="threshold_slider_for_binary",on_change=sync_threshold_from_slider)
    st.sidebar.number_input('閾値 (直接入力)',min_value=0,max_value=255,step=1,value=st.session_state.binary_threshold_value,key="threshold_number_for_binary",on_change=sync_threshold_from_number_input)
    threshold_value_to_use = st.session_state.binary_threshold_value 
    st.sidebar.caption("""- **大きくすると:** 明るい部分のみ白に。\n- **小さくすると:** 暗い部分も白に。""")
    st.sidebar.markdown("<br>", unsafe_allow_html=True); st.sidebar.markdown("_二値化だけでうまくいかない場合は下記も調整を_")
    st.sidebar.subheader("2. 形態学的処理 (オープニング)") 
    morph_kernel_shape_to_use = cv2.MORPH_ELLIPSE 
    kernel_options_morph = [1,3,5,7,9]; kernel_size_morph_to_use =st.sidebar.select_slider('カーネルサイズ',options=kernel_options_morph,value=3) 
    st.sidebar.caption("""オープニング処理（収縮後に膨張）で、小さなノイズ除去や輝点分離を行います。\n- **大きくすると:** 効果が強くなり、より大きなノイズや繋がりも除去できますが、輝点自体も小さくなるか消えることがあります。\n- **小さくすると (例: 1):** 効果は弱く、微細なノイズのみに作用し、輝点への影響は少ないです。\n画像を見ながら調整してください。""")
    st.sidebar.subheader("3. 輝点フィルタリング (面積)") 
    min_area_to_use = st.sidebar.number_input('最小面積',min_value=1,max_value=10000,step=1,value=1) 
    st.sidebar.caption("""- **大きくすると:** 小さな輝点を除外。\n- **小さくすると:** ノイズを拾う可能性。""") 
    max_area_to_use = st.sidebar.number_input('最大面積',min_value=1,max_value=100000,step=1,value=10000) 
    st.sidebar.caption("""- **大きくすると:** 大きな塊もカウント。\n- **小さくすると:** 大きな塊を除外。""") 
    st.sidebar.subheader("4. 表示設定")
    contour_color_hex = st.sidebar.color_picker('輝点マーキング色を選択', "#00FF00") # デフォルト緑
    contour_color_bgr = tuple(int(contour_color_hex.lstrip('#')[i:i+2], 16) for i in (4, 2, 0)) # HEX to BGR


    # --- メインエリアの画像処理と表示ロジック ---
    # ★★★ 解析はフル解像度で行う ★★★
    img_for_processing_pil_rgb = st.session_state.pil_image_original_full_res.convert("RGB")
    img_for_processing_np_uint8 = np.array(img_for_processing_pil_rgb).astype(np.uint8)
    img_gray_full_res = cv2.cvtColor(img_for_processing_np_uint8, cv2.COLOR_RGB2GRAY)
    if img_gray_full_res.dtype != np.uint8: img_gray_full_res = img_gray_full_res.astype(np.uint8)
    
    st.header("処理ステップごとの画像")
    kernel_size_blur = 1 
    if img_gray_full_res is None or img_gray_full_res.size == 0 : 
        st.error("グレースケール画像準備失敗。"); st.session_state.counted_spots_value="処理エラー"; st.stop()
        
    # 解析処理はフル解像度のグレースケール画像で行う
    blurred_img_full_res = cv2.GaussianBlur(img_gray_full_res, (kernel_size_blur,kernel_size_blur),0)
    ret_thresh, binary_img_processed_full_res = cv2.threshold(blurred_img_full_res,threshold_value_to_use,255,cv2.THRESH_BINARY)
    if not ret_thresh: st.error("二値化失敗。"); binary_img_for_morph_full_res=None
    else: binary_img_for_morph_full_res=binary_img_processed_full_res.copy()
    
    opened_img_processed_full_res = None 
    if binary_img_for_morph_full_res is not None:
        kernel_morph_obj=cv2.getStructuringElement(morph_kernel_shape_to_use,(kernel_size_morph_to_use,kernel_size_morph_to_use))
        opened_img_processed_full_res=cv2.morphologyEx(binary_img_for_morph_full_res,cv2.MORPH_OPEN,kernel_morph_obj)
        binary_img_for_contours_full_res = opened_img_processed_full_res.copy()
    else: binary_img_for_contours_full_res = None
    
    current_counted_spots = 0 
    # 輪郭描画はフル解像度のカラー画像に対して行う
    output_image_contours_display_full_res = cv2.cvtColor(img_for_processing_np_uint8.copy(), cv2.COLOR_RGB2BGR) 
    
    if binary_img_for_contours_full_res is not None:
        contours, hierarchy = cv2.findContours(binary_img_for_contours_full_res,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        if 'contours' in locals() and contours: 
            for contour in contours:
                area = cv2.contourArea(contour)
                if min_area_to_use <= area <= max_area_to_use: 
                    current_counted_spots += 1
                    cv2.drawContours(output_image_contours_display_full_res, [contour], -1, contour_color_bgr, 2) 
        st.session_state.counted_spots_value = current_counted_spots 
    else:
        st.warning("輪郭検出元画像準備できず。"); st.session_state.counted_spots_value="エラー"
    
    # --- 表示用の縮小画像準備 ---
    IMAGE_DISPLAY_WIDTH = 600 # 表示用の幅
    
    def create_display_version(pil_image, target_width):
        if pil_image is None: return None
        w, h = pil_image.size
        if w == 0 or h == 0: return None
        aspect_ratio = h / w
        display_h = int(target_width * aspect_ratio)
        # Pillowのresizeはタプル(width, height)を取る
        try:
            resized_pil = pil_image.resize((target_width, display_h), Image.Resampling.LANCZOS)
            return np.array(resized_pil).astype(np.uint8)
        except Exception: # 何らかの理由でリサイズに失敗した場合
            return np.array(pil_image).astype(np.uint8) # 元のPillowからNumPyへ

    original_img_for_display = create_display_version(Image.fromarray(img_for_processing_np_uint8), IMAGE_DISPLAY_WIDTH)
    binary_img_for_display = create_display_version(Image.fromarray(binary_img_processed_full_res, 'L') if binary_img_processed_full_res is not None else None, IMAGE_DISPLAY_WIDTH)
    opened_img_for_display = create_display_version(Image.fromarray(opened_img_processed_full_res, 'L') if opened_img_processed_full_res is not None else None, IMAGE_DISPLAY_WIDTH)
    marked_img_bgr_for_display = create_display_version(Image.fromarray(cv2.cvtColor(output_image_contours_display_full_res, cv2.COLOR_BGR2RGB)), IMAGE_DISPLAY_WIDTH)


    st.subheader("元の画像")
    if original_img_for_display is not None:
        st.image(original_img_for_display, caption=st.session_state.image_source_caption)
    st.markdown("---")
    st.subheader("1. 二値化処理後")
    if binary_img_for_display is not None: 
        st.image(binary_img_for_display,caption=f'閾値:{threshold_value_to_use}')
    else: st.info("二値化未実施/失敗")
    st.markdown("---")
    with st.expander("▼ 2. 形態学的処理後を見る", expanded=False): 
        if opened_img_for_display is not None: 
            st.image(opened_img_for_display,caption=f'カーネル: 楕円 {kernel_size_morph_to_use}x{kernel_size_morph_to_use}')
        else: st.info("形態学的処理未実施/失敗")
    st.markdown("---") 
    st.subheader("3. 輝点検出とマーキング")
    if marked_img_bgr_for_display is not None:
        if current_counted_spots > 0 :
             st.image(marked_img_bgr_for_display,caption=f'検出輝点(選択色,面積:{min_area_to_use}-{max_area_to_use})')
        else: 
             st.image(marked_img_bgr_for_display,caption='輝点見つからず')
    else: st.info("輝点検出未実施")
else: 
    st.info("まず、サイドバーから画像ファイルをアップロードしてください。")

display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value)
