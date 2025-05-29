import streamlit as st
from PIL import Image, ImageDraw 
import numpy as np
import cv2
from streamlit_drawable_canvas import st_canvas
import io
# import time # timeモジュールは今回のキー戦略では一旦不要とします

# ページ設定
st.set_page_config(page_title="輝点解析ツール", layout="wide")

# ファイルアップローダーのカスタムCSS (変更なし)
file_uploader_css = """<style>
section[data-testid="stFileUploaderDropzone"]{border:3px dashed white !important;border-radius:0.5rem !important;background-color:#495057 !important;padding:25px !important;}
section[data-testid="stFileUploaderDropzone"] > div[data-testid="stFileUploadDropzoneInstructions"]{display:flex;flex-direction:column;align-items:center;justify-content:center;}
section[data-testid="stFileUploaderDropzone"] p{color:#f8f9fa !important;font-size:0.9rem;margin-bottom:0.75rem !important;}
section[data-testid="stFileUploaderDropzone"] span{color:#ced4da !important;font-size:0.8rem;}
section[data-testid="stFileUploaderDropzone"] button{color:#fff !important;background-color:#007bff !important;border:1px solid #007bff !important;padding:0.5em 1em !important;border-radius:0.375rem !important;font-weight:500 !important;margin-top:0.5rem !important;}
</style>"""
st.markdown(file_uploader_css, unsafe_allow_html=True)

result_placeholder_sidebar = st.sidebar.empty()
def display_count_in_sidebar(placeholder, count_value):
    label_text = "【解析結果】輝点数"; value_text = str(count_value) 
    bg="#495057"; lf="white"; vf="white"
    html=f"""<div style="border-radius:8px;padding:15px;text-align:center;background-color:{bg};margin-bottom:15px;color:{lf};"><p style="font-size:16px;margin-bottom:5px;font-weight:bold;">{label_text}</p><p style="font-size:48px;font-weight:bold;margin-top:0px;color:{vf};line-height:1.1;">{value_text}</p></div>"""
    with placeholder.container(): placeholder.markdown(html, unsafe_allow_html=True)

default_ss = {'counted_spots_value':"---","binary_threshold_value":58,"threshold_slider_for_binary":58,"threshold_number_for_binary":58,"morph_shape_sb_key":"楕円","morph_size_sb_key":3,"min_area_sb_key_v3":1,"max_area_sb_key_v3":1000,'pil_image_to_process':None,'image_source_caption':"アップロードされた画像",'roi_coords':None,'last_uploaded_filename_for_roi_reset':None}
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
2. 「1. 解析エリア選択」で、表示された画像の上で直接マウスをドラッグし、解析したい四角いエリアを描画します。最後に描画した四角形がROIとなります。何も描画しない場合は画像全体が対象です。
3. 画像（または選択エリア）を元に、左サイドバーの「1. 二値化」以降のパラメータを調整してください。
4. メインエリアの各処理ステップ画像と、最終的な「3. 輝点検出とマーキング」で結果を確認します。
""")
st.markdown("---") 

if uploaded_file_widget is not None:
    if st.session_state.get('last_uploaded_filename_for_roi_reset') != uploaded_file_widget.name:
        st.session_state.roi_coords = None; st.session_state.last_uploaded_filename_for_roi_reset = uploaded_file_widget.name
    try:
        uploaded_file_bytes = uploaded_file_widget.getvalue()
        pil_img_original_full_res = Image.open(io.BytesIO(uploaded_file_bytes))
        st.session_state.pil_image_to_process = pil_img_original_full_res
        st.session_state.image_source_caption = f"アップロード: {uploaded_file_widget.name}"
    except Exception as e: st.sidebar.error(f"アップロード画像の読み込みに失敗: {e}"); st.session_state.pil_image_to_process=None; st.session_state.counted_spots_value="読込エラー"; st.stop()
else: 
    if st.session_state.pil_image_to_process is not None: st.session_state.pil_image_to_process=None; st.session_state.counted_spots_value="---"; st.session_state.roi_coords=None

if st.session_state.pil_image_to_process is not None:
    pil_image_rgb_full_res = None; img_gray_full_res = None
    np_array_rgb_uint8_full_res = None 
    
    try:
        pil_image_rgb_full_res = st.session_state.pil_image_to_process.convert("RGB")
        np_array_rgb_uint8_full_res = np.array(pil_image_rgb_full_res).astype(np.uint8)
        img_gray_full_res = cv2.cvtColor(np_array_rgb_uint8_full_res, cv2.COLOR_RGB2GRAY)
        if img_gray_full_res.dtype != np.uint8: img_gray_full_res = img_gray_full_res.astype(np.uint8)
    except Exception as e: st.error(f"画像変換(フル解像度)に失敗: {e}"); st.stop()

    st.header("1. 解析エリア選択") 
    
    pil_for_display_and_canvas = pil_image_rgb_full_res.copy()
    DISPLAY_MAX_DIM = 600 
    
    original_width_for_scaling = pil_for_display_and_canvas.width
    original_height_for_scaling = pil_for_display_and_canvas.height

    if pil_for_display_and_canvas.width > DISPLAY_MAX_DIM or pil_for_display_and_canvas.height > DISPLAY_MAX_DIM:
        pil_for_display_and_canvas.thumbnail((DISPLAY_MAX_DIM, DISPLAY_MAX_DIM))
    
    canvas_width = pil_for_display_and_canvas.width
    canvas_height = pil_for_display_and_canvas.height

    scale_x = original_width_for_scaling / canvas_width if canvas_width > 0 else 1.0
    scale_y = original_height_for_scaling / canvas_height if canvas_height > 0 else 1.0

    st.info(f"↓下の画像の上でマウスをドラッグして、解析したい四角いエリアを描画してください。（表示サイズ: {canvas_width}x{canvas_height}）")

    # ★★★ 重ね合わせのためのCSSとHTMLコンテナ ★★★
    # このコンテナのクラス名 (roi-overlay-container-class) をCSSで使います。
    # st.image と st_canvas は、このコンテナの直接の子として配置されることを期待します。
    # Streamlitでは要素は通常divでラップされるため、CSSセレクタの調整が必要になることが多いです。
    
    # CSSを定義 (st.image と st_canvas のラッパーdivを特定し、重ねる試み)
    # このセレクタはStreamlitのバージョンによって変わる可能性が高いです。
    # 正確なセレクタはブラウザの開発者ツールで確認する必要があります。
    # ここでは、st.imageとst_canvasを配置する親要素にクラス名をつけ、
    # その子要素としてst.imageとst_canvasが特定の構造で配置されることを仮定します。
    
    # このキーは、CSSでst_canvasの特定のインスタンスをターゲットにするために使います。
    canvas_unique_key = "unique_roi_canvas_for_css"

    # 非常に実験的なCSSです。
    # Streamlitが生成するHTML構造をブラウザの開発ツールで確認し、
    # '.stImage' や '.stDrawableCanvas' などのクラス名や、より具体的な
    # data-testid を使ったセレクタに調整する必要があるかもしれません。
    overlay_css = f"""
    <style>
        /* このコンテナがst.imageとst_canvasを直接の子として持つとは限らないため、
           より深い階層を狙う必要がある場合が多い */
        .roi-overlay-container {{
            position: relative;
            width: {canvas_width}px;
            height: {canvas_height}px;
            margin: auto; /* 中央寄せ */
            /* border: 1px dashed red; /* デバッグ用にコンテナの範囲を可視化 */
        }}
        /* st.imageが生成するimg要素は通常、div[data-testid="stImage"]の中にあります */
        /* div[data-testid="stImage"] をコンテナ内の最初の要素と仮定 */
        .roi-overlay-container > div:nth-child(1) {{ /* st.imageを包むdivを想定 */
            position: absolute !important;
            top: 0 !important;
            left: 0 !important;
            width: 100% !important;
            height: 100% !important;
            z-index: 1 !important; /* 画像を下に */
        }}
        /* st_canvasを包むdivを、そのキーを使って特定する試み */
        /* data-testid="stVerticalBlock" のネストは環境や要素の追加で変わります */
        .roi-overlay-container div[data-testid="stVerticalBlock"] div[data-testid="stDrawableCanvas"][key="{canvas_unique_key}"] {{
            position: absolute !important;
            top: 0 !important;
            left: 0 !important;
            width: {canvas_width}px !important;
            height: {canvas_height}px !important;
            z-index: 2 !important; /* キャンバスを画像の上に */
            pointer-events: auto !important; /* キャンバス上で描画操作を可能に */
        }}
    </style>
    """
    st.markdown(overlay_css, unsafe_allow_html=True)
    
    # HTMLとst_image, st_canvasを配置 (st.markdownで親divを生成)
    # st.markdown("<div class='roi-overlay-container'>", unsafe_allow_html=True) # この方法はstウィジェットを内部に置けない

    # st.container() を使って、それにクラス名をつけることはできないので、
    # Streamlitが生成する構造に頼るしかありません。
    # ここでは、st.imageとst_canvasを連続して配置し、CSSでst_canvasが
    # 先行するst.imageの上に重なるように調整することを試みます。

    # 1. ベースとなる画像を表示
    st.image(pil_for_display_and_canvas, width=canvas_width, use_column_width=False, 
             caption="この画像に重ねてROIを描画してください。") # keyは削除

    # 2. 透明なst_canvasを重ねる (CSSでの調整を期待)
    # 上のst.imageの高さ分だけネガティブマージンで引き上げることで重ねる試み
    # ただし、この方法はst.imageの実際のレンダリング高さに依存し、非常に不安定です。
    st.markdown(f"""
        <div style="margin-top: -{canvas_height + 8}px; position: relative; z-index: 2;"> 
        """, unsafe_allow_html=True) # +8px はst.imageのキャプションや余白を考慮した微調整値（要調整）

    canvas_result = st_canvas(
        fill_color="rgba(255, 0, 0, 0.2)", 
        stroke_width=2, 
        stroke_color="red",
        background_color="rgba(0,0,0,0)",  # 背景は完全に透明
        update_streamlit=True, 
        height=canvas_height,   
        width=canvas_width,    
        drawing_mode="rect", 
        key=canvas_unique_key 
    )
    st.markdown("</div>", unsafe_allow_html=True)


    # (以降のROI処理、サイドバーUI、メインの画像処理・表示ロジックは変更なし)
    img_to_process_gray = img_gray_full_res 
    img_for_marking_color_np = np_array_rgb_uint8_full_res.copy() 
    analysis_caption_suffix = "(画像全体)"
    
    if canvas_result and canvas_result.json_data is not None and canvas_result.json_data.get("objects", []):
        if canvas_result.json_data["objects"][-1]["type"] == "rect":
            rect = canvas_result.json_data["objects"][-1]
            x_cvs,y_cvs,w_cvs,h_cvs = int(rect["left"]),int(rect["top"]),int(rect["width"]),int(rect["height"])
            if w_cvs > 0 and h_cvs > 0:
                x_orig,y_orig,w_orig,h_orig = int(x_cvs*scale_x),int(y_cvs*scale_y),int(w_cvs*scale_x),int(h_cvs*scale_y)
                x1,y1=max(0,x_orig),max(0,y_orig); x2,y2=min(img_gray_full_res.shape[1],x_orig+w_orig),min(img_gray_full_res.shape[0],y_orig+h_orig)
                if (x2-x1 > 0) and (y2-y1 > 0):
                    st.session_state.roi_coords=(x1,y1,x2-x1,y2-y1)
                    img_to_process_gray = img_gray_full_res[y1:y2, x1:x2].copy()
                    img_for_marking_color_np = np_array_rgb_uint8_full_res[y1:y2, x1:x2].copy()
                    analysis_caption_suffix = f"(選択エリア: {img_to_process_gray.shape[1]}x{img_to_process_gray.shape[0]}px @フル解像度)"
                    with st.expander("選択されたROI（処理対象のグレースケール）", expanded=True):
                        st.image(img_to_process_gray, caption=f"ROI: x={x1},y={y1},w={x2-x1},h={y2-y1} (フル解像度座標)")
                else: st.warning("描画ROI無効。全体処理。"); img_to_process_gray=img_gray_full_res; st.session_state.roi_coords=None
            else: st.session_state.roi_coords = None
    st.markdown("---")

    # --- サイドバーのパラメータ設定UI (変更なし) ---
    st.sidebar.subheader("1. 二値化") 
    st.sidebar.markdown("_この値を色々変更して、「1. 二値化処理後」画像を実物に近づけてください。_")
    st.sidebar.slider('閾値 (スライダーで調整)',min_value=0,max_value=255,step=1,value=st.session_state.binary_threshold_value,key="threshold_slider_for_binary",on_change=sync_threshold_from_slider)
    st.sidebar.number_input('閾値 (直接入力)',min_value=0,max_value=255,step=1,value=st.session_state.binary_threshold_value,key="threshold_number_for_binary",on_change=sync_threshold_from_number_input)
    threshold_value_to_use = st.session_state.binary_threshold_value 
    st.sidebar.caption("""- ..."""); st.sidebar.markdown("<br>", unsafe_allow_html=True); st.sidebar.markdown("_..._") 
    st.sidebar.subheader("2. 形態学的処理 (オープニング)") 
    morph_kernel_shape_to_use = cv2.MORPH_ELLIPSE 
    st.sidebar.markdown("カーネル形状: **楕円 (固定)**")
    kernel_options_morph = [1,3,5,7,9]; kernel_size_morph_to_use =st.sidebar.select_slider('カーネルサイズ',options=kernel_options_morph,value=st.session_state.morph_size_sb_key,key="morph_size_sb_key")
    st.sidebar.markdown("""オープニング処理は...""", unsafe_allow_html=True)
    st.sidebar.subheader("3. 輝点フィルタリング (面積)") 
    min_area_to_use = st.sidebar.number_input('最小面積',min_value=1,max_value=10000,value=st.session_state.min_area_sb_key_v3,key="min_area_sb_key_v3") 
    st.sidebar.caption("""- ...""") 
    max_area_to_use = st.sidebar.number_input('最大面積',min_value=1,max_value=100000,value=st.session_state.max_area_sb_key_v3,key="max_area_sb_key_v3") 
    st.sidebar.caption("""- ...""") 

    st.header(f"処理ステップごとの画像") 
    kernel_size_blur=1;
    if img_to_process_gray.size==0: st.error("処理対象グレースケール画像が空。"); st.stop()
    blurred_img = cv2.GaussianBlur(img_to_process_gray,(kernel_size_blur,kernel_size_blur),0)
    ret_thresh,binary_img_processed = cv2.threshold(blurred_img,threshold_value_to_use,255,cv2.THRESH_BINARY)
    if not ret_thresh: st.error("二値化失敗。"); binary_img_for_morph_processed=None
    else: binary_img_for_morph_processed=binary_img_processed.copy()
    opened_img_processed=None
    if binary_img_for_morph_processed is not None:
        kernel_morph_obj=cv2.getStructuringElement(morph_kernel_shape_to_use,(kernel_size_morph_to_use,kernel_size_morph_to_use))
        opened_img_processed=cv2.morphologyEx(binary_img_for_morph_processed,cv2.MORPH_OPEN,kernel_morph_obj)
        binary_img_for_contours_processed = opened_img_processed.copy()
    else: binary_img_for_contours_processed=None
    current_counted_spots=0
    output_image_contours_display_bgr = cv2.cvtColor(img_for_marking_color_np, cv2.COLOR_RGB2BGR)
    if binary_img_for_contours_processed is not None:
        contours,hierarchy = cv2.findContours(binary_img_for_contours_processed,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        if 'contours' in locals() and contours:
            for contour in contours:
                area=cv2.contourArea(contour)
                if min_area_to_use <= area <= max_area_to_use: current_counted_spots+=1; cv2.drawContours(output_image_contours_display_bgr,[contour],-1,(255,0,0),2)
        st.session_state.counted_spots_value=current_counted_spots
    else: st.warning("輪郭検出元画像準備できず。"); st.session_state.counted_spots_value="エラー"
    
    st.subheader(f"1. 二値化処理後 {analysis_caption_suffix}")
    if binary_img_processed is not None: st.image(binary_img_processed,caption=f'閾値:{threshold_value_to_use}')
    else: st.info("二値化未実施/失敗")
    st.markdown("---")
    with st.expander(f"▼ 2. 形態学的処理後を見る {analysis_caption_suffix}", expanded=False):
        if opened_img_processed is not None: st.image(opened_img_processed,caption=f'カーネル: 楕円 {kernel_size_morph_to_use}x{kernel_size_morph_to_use}')
        else: st.info("形態学的処理未実施/失敗")
    st.markdown("---") 
    st.subheader(f"3. 輝点検出とマーキング {analysis_caption_suffix}")
    display_final_marked_image_rgb = cv2.cvtColor(output_image_contours_display_bgr, cv2.COLOR_BGR2RGB)
    if 'contours' in locals() and contours and binary_img_for_contours_processed is not None and current_counted_spots > 0 :
         st.image(display_final_marked_image_rgb,caption=f'検出輝点(青い輪郭,面積:{min_area_to_use}-{max_area_to_use})')
    elif binary_img_for_contours_processed is not None: st.image(display_final_marked_image_rgb,caption='輝点見つからず')
    else: st.info("輝点検出未実施")
else: 
    st.info("まず、サイドバーから画像ファイルをアップロードしてください。")

display_count_in_sidebar(result_placeholder_sidebar, st.session_state.counted_spots_value)
