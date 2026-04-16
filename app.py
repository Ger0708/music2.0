import streamlit as st
import pandas as pd
import os
import uuid
import subprocess
from googleapiclient.discovery import build
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# --- 1. 頁面設定與初始化 ---
st.set_page_config(page_title="AI 音樂擴充系統", page_icon="🎵", layout="centered")

# 讀取 Secrets (部署後在 Streamlit Cloud 後台設定)
YOUTUBE_API_KEY = st.secrets.get("YOUTUBE_API_KEY")
DATA_FILE = "music.csv"

# 初始化 CSV 檔案
if not os.path.exists(DATA_FILE) or os.stat(DATA_FILE).st_size == 0:
    df = pd.DataFrame(columns=["song", "artist", "genre"])
    df.to_csv(DATA_FILE, index=False)

# --- 2. 核心功能函式 ---

def get_youtube_info(query):
    """使用 API 搜尋影片"""
    try:
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        request = youtube.search().list(q=f"{query} official audio", part="snippet", maxResults=1, type="video")
        response = request.execute()
        if response["items"]:
            item = response["items"][0]
            return {
                "title": item["snippet"]["title"],
                "channel": item["snippet"]["channelTitle"],
                "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}"
            }
    except Exception as e:
        st.error(f"API 錯誤: {e}")
    return None

def download_and_play(video_url):
    """下載音訊並回傳檔案路徑"""
    file_id = f"temp_{uuid.uuid4().hex}.mp3"
    try:
        # 雲端部署會自動找系統安裝的 ffmpeg，不需指定 .exe
        subprocess.run([
            "yt-dlp", "-x", "--audio-format", "mp3", 
            "--no-check-certificates", "-o", file_id, video_url
        ], check=True)
        return file_id
    except Exception as e:
        st.error(f"下載失敗: {e}")
        return None

def update_library(song, artist):
    """自動擴充音樂庫"""
    df = pd.read_csv(DATA_FILE)
    # 檢查是否已存在 (不分大小寫)
    if not ((df['song'].str.lower() == song.lower()) & (df['artist'].str.lower() == artist.lower())).any():
        new_row = pd.DataFrame([[song, artist, "Pop"]], columns=["song", "artist", "genre"])
        pd.concat([df, new_row], ignore_index=True).to_csv(DATA_FILE, index=False)
        return True
    return False

# --- 3. UI 介面設計 ---
st.title("🎶 AI 自動擴充音樂推薦系統")
st.markdown("輸入歌名，系統將自動從 YouTube 抓取並學習新歌。")

search_query = st.text_input("想聽什麼歌？", placeholder="例如: 周杰倫 告白氣球")

if st.button("搜尋並播放", use_container_width=True):
    if not YOUTUBE_API_KEY:
        st.warning("請在 Secrets 中設定 YOUTUBE_API_KEY")
    elif search_query:
        with st.spinner("🔍 正在搜尋 YouTube 並進行轉碼..."):
            info = get_youtube_info(search_query)
            if info:
                st.success(f"找到歌曲: {info['title']}")
                audio_path = download_and_play(info['url'])
                
                if audio_path:
                    st.audio(audio_path)
                    # 自動擴充庫
                    if update_library(info['title'], info['channel']):
                        st.info("✨ 已將此歌曲自動存入您的音樂庫！")
                    
                    # 播放後刪除暫存，避免撐爆雲端硬碟
                    # os.remove(audio_path) 
            else:
                st.error("找不到相關影片，請換個關鍵字。")

# --- 4. 側邊欄：音樂庫與推薦 ---
st.sidebar.header("📂 我的音樂庫")
lib_df = pd.read_csv(DATA_FILE)

if not lib_df.empty:
    st.sidebar.dataframe(lib_df[["song", "artist"]], hide_index=True)
    
    if st.sidebar.button("🎲 隨機推薦一首"):
        random_song = lib_df.sample(n=1).iloc[0]
        st.sidebar.write(f"推薦聽: **{random_song['song']}**")
else:
    st.sidebar.write("目前庫中尚無音樂。")