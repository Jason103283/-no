import streamlit as st
import pandas as pd
import json
import os
import random
import time
from datetime import datetime, timedelta

# --- 1. 初始化 Session State ---
if 'all_words' not in st.session_state:
    st.session_state.all_words = []
    st.session_state.review_queue = []
    st.session_state.current_item = None
    st.session_state.is_showing_answer = False
    st.session_state.last_result = None
    st.session_state.current_lib_name = ""

# --- 2. 核心邏輯函式 ---
def load_data_source(file_path_or_buffer, is_json=False, label=""):
    """載入資料源：支援路徑(預設)或上傳對象"""
    try:
        if is_json:
            data = json.load(file_path_or_buffer)
        else:
            df = pd.read_excel(file_path_or_buffer, header=None, names=['日文', '假名'])
            data = [{'日文': str(row['日文']).strip(), '假名': str(row['假名']).strip(), 
                     'level': 0, 'wrong_count': 0, 'next_review': datetime.now().isoformat()} 
                    for _, row in df.dropna().iterrows()]
        
        st.session_state.all_words = data
        st.session_state.current_lib_name = label
        start_session()
    except Exception as e:
        st.error(f"讀取失敗：{e}")

def start_session():
    now = datetime.now()
    # 篩選出到期的單字
    queue = [w for w in st.session_state.all_words if datetime.fromisoformat(w['next_review']) <= now]
    random.shuffle(queue)
    st.session_state.review_queue = queue
    next_question()

def next_question():
    if st.session_state.review_queue:
        st.session_state.current_item = st.session_state.review_queue.pop(0)
        st.session_state.is_showing_answer = False
        st.session_state.last_result = None
    else:
        st.session_state.current_item = None

def update_level(item, new_lv):
    intervals = [0, 1, 2, 4, 7, 15, 30]
    lv = max(0, min(new_lv, len(intervals)-1))
    item['level'] = lv
    item['next_review'] = (datetime.now() + timedelta(days=intervals[lv])).isoformat()

# --- 3. 介面樣式 (CSS) ---
st.markdown("""
    <style>
    .kanji-text { font-size: 72px !important; font-weight: bold; text-align: center; color: #2f3640; padding: 10px; margin-top: -20px; }
    .correct-box { background-color: #27ae60; color: white; padding: 20px; border-radius: 10px; text-align: center; font-size: 24px; }
    .wrong-box { background-color: #e17055; color: white; padding: 20px; border-radius: 10px; text-align: center; font-size: 24px; }
    </style>
""", unsafe_allow_html=True)

# --- 4. 側邊欄：圖書館管理 ---
with st.sidebar:
    st.title("📚 Andy's Library")
    
    # 自動偵測目錄下的 Excel
    local_excels = [f for f in os.listdir('.') if f.endswith('.xlsx')]
    
    if local_excels:
        st.subheader("選擇內建題庫")
        selected = st.selectbox("切換清單：", local_excels)
        if st.button("📖 載入選定題庫"):
            load_data_source(selected, label=selected)
            st.rerun()
    
    st.divider()
    
    st.subheader("匯入進度或新書")
    up_file = st.file_uploader("上傳 .xlsx 或 .json", type=["xlsx", "json"])
    if up_file:
        if st.button("📥 確認匯入上傳檔案"):
            if up_file.name.endswith('.json'):
                load_data_source(up_file, is_json=True, label=up_file.name)
            else:
                load_data_source(up_file, label=up_file.name)
            st.rerun()

    if st.session_state.all_words:
        st.divider()
        st.subheader("💾 數據導出")
        json_str = json.dumps(st.session_state.all_words, ensure_ascii=False, indent=4)
        st.download_button(
            label="下載目前進度 JSON",
            data=json_str,
            file_name=f"andy_progress_{datetime.now().strftime('%m%d_%H%M')}.json",
            mime="application/json"
        )

# --- 5. 主畫面：分頁設計 ---
if st.session_state.all_words:
    st.caption(f"目前正在練習：{st.session_state.current_lib_name}")
    tab_quiz, tab_browse = st.tabs(["✍️ 測驗模式", "📖 瀏覽題庫"])

    with tab_quiz:
        if st.session_state.current_item:
            item = st.session_state.current_item
            st.markdown(f'<div class="kanji-text">{item["日文"]}</div>', unsafe_allow_html=True)

            # 作答區 (使用 Form 確保 Enter 清空)
            if not st.session_state.is_showing_answer:
                with st.form(key='input_form', clear_on_submit=True):
                    u_input = st.text_input("輸入假名 (認輸按 0):", key="main_input").strip()
                    btn_submit = st.form_submit_button("提交判斷")
                    
                    if btn_submit and u_input:
                        ans = item['假名'].strip()
                        st.session_state.is_showing_answer = True
                        
                        if u_input == "0":
                            item['wrong_count'] += 1
                            item['level'] = 0
                            st.session_state.review_queue.insert(min(3, len(st.session_state.review_queue)), item)
                            st.session_state.last_result = ("wrong", f"認輸自首！正確答案是：{ans}")
                            st.rerun()
                        elif u_input == ans:
                            update_level(item, item['level'] + 1)
                            st.session_state.last_result = ("correct", f"✨ 正確！答案是：{ans}")
                            st.rerun()
                        else:
                            item['wrong_count'] += 1
                            item['level'] = 0
                            st.session_state.review_queue.append(item)
                            st.session_state.last_result = ("wrong", f"可惜錯了！正確答案是：{ans}")
                            st.rerun()

            # 回饋與手動改級數區
            if st.session_state.is_showing_answer:
                res_type, res_msg = st.session_state.last_result
                box_style = "correct-box" if res_type == "correct" else "wrong-box"
                st.markdown(f'<div class="{box_style}">{res_msg}</div>', unsafe_allow_html=True)
                
                st.write("---")
                st.write("🔧 手動調整級數 (若不調整則 0.8秒後自動下一題)")
                cols = st.columns(6)
                for i, col in enumerate(cols, 1):
                    if col.button(f"Lv.{i}"):
                        update_level(item, i)
                        next_question()
                        st.rerun()
                
                if st.button("下一題 ➡️ (手動)"):
                    next_question()
                    st.rerun()

                # 自動跳題邏輯 (僅限答對時)
                if res_type == "correct":
                    time.sleep(0.8)
                    next_question()
                    st.rerun()

            st.info(f"今日待複習：{len(st.session_state.review_queue) + 1} 題")
        else:
            st.balloons()
            st.success("今日目標達成！請下載 JSON 儲存進度。")

    with tab_browse:
        st.subheader("📚 題庫內容瀏覽")
        df_all = pd.DataFrame(st.session_state.all_words)
        search = st.text_input("🔍 關鍵字搜尋 (漢字/假名):")
        if search:
            df_all = df_all[df_all['日文'].str.contains(search) | df_all['假名'].str.contains(search)]
        
        st.dataframe(
            df_all[['日文', '假名', 'wrong_count', 'level']].sort_values(by="wrong_count", ascending=False),
            use_container_width=True
        )

else:
    st.info("👈 請從側邊欄選擇題庫開始學習！")