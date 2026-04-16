import streamlit as st
import pandas as pd
import os
import uuid
import subprocess
from googleapiclient.discovery import build

# --- 1. 頁面基礎設定 ---
st.set_page_config(page_title="AI 音樂自動擴充系統", page_icon="🎧", layout="centered")

# 從 Streamlit Cloud Secrets 讀取金鑰 (請至後台設定)
YOUTUBE_API_KEY = st.secrets.get("YOUTUBE_API_KEY")
DATA_FILE = "music.csv"

# 初始化資料庫檔案：如果不存在就建立帶有標題的空白 CSV
if not os.path.exists(DATA_FILE) or os.stat(DATA_FILE).st_size == 0:
    df = pd.DataFrame(columns=["song", "artist", "genre"])
    df.to_csv(DATA_FILE, index=False)

# --- 2. 功能函式庫 ---

def search_youtube(query):
    """利用 YouTube API 取得影片資訊與連結"""
    try:
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        # 搜尋關鍵字：加入 "official audio" 提高搜尋精確度
        request = youtube.search().list(
            q=f"{query} official audio", 
            part="snippet", 
            maxResults=1, 
            type="video"
        )
        response = request.execute()
        
        if response["items"]:
            item = response["items"][0]
            return {
                "title": item["snippet"]["title"],
                "channel": item["snippet"]["channelTitle"],
                "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}"
            }
    except Exception as e:
        st.error(f"YouTube API 呼叫失敗: {e}")
    return None

def process_audio(video_url):
    unique_filename = f"music_{uuid.uuid4().hex}.mp3"
    
    # 嘗試尋找系統中的 ffmpeg 路徑 (解決 "not found" 錯誤)
    import shutil
    ffmpeg_bin = shutil.which("ffmpeg") 
    
    try:
        cmd = [
            "yt-dlp", 
            "-x", 
            "--audio-format", "mp3", 
            "--no-check-certificates", 
            "-o", unique_filename
        ]
        
        # 如果系統有找到 ffmpeg，就明確告訴 yt-dlp 它的位置
        if ffmpeg_bin:
            cmd.extend(["--ffmpeg-location", ffmpeg_bin])
            
        cmd.append(video_url)

        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            st.error("❌ 轉碼失敗，詳細錯誤如下：")
            st.code(result.stderr)
            return None
            
        return unique_filename
    except Exception as e:
        st.error(f"系統執行錯誤: {e}")
        return None
    
def save_to_csv(song_name, artist_name):
    """將新歌曲自動擴充進 music.csv"""
    df = pd.read_csv(DATA_FILE)
    # 檢查是否重複
    is_exist = ((df['song'] == song_name) & (df['artist'] == artist_name)).any()
    
    if not is_exist:
        new_entry = pd.DataFrame([[song_name, artist_name, "Auto-Expanded"]], 
                                 columns=["song", "artist", "genre"])
        pd.concat([df, new_entry], ignore_index=True).to_csv(DATA_FILE, index=False)
        return True
    return False

# --- 3. 前端網頁介面 ---

st.title("🎵 AI 音樂庫自動擴充系統")
st.info("當你搜尋新歌時，系統會自動將其加入您的雲端音樂庫。")

# 搜尋輸入框
user_input = st.text_input("輸入你想聽的歌曲或歌手", placeholder="例如: 周杰倫 青花瓷")

if st.button("開始搜尋並播放", use_container_width=True):
    if not YOUTUBE_API_KEY:
        st.error("⚠️ 偵測不到 API Key！請在 Streamlit Cloud 的 Secrets 設定中加入 YOUTUBE_API_KEY。")
    elif user_input:
        with st.spinner("🚀 正在連結 YouTube 並下載音訊..."):
            song_info = search_youtube(user_input)
            
            if song_info:
                st.write(f"✅ **找到歌曲：** {song_info['title']}")
                audio_file = process_audio(song_info['url'])
                
                if audio_file and os.path.exists(audio_file):
                    # 播放音樂
                    st.audio(audio_file)
                    
                    # 自動擴充資料庫
                    if save_to_csv(song_info['title'], song_info['channel']):
                        st.success("✨ 這首歌已成功擴充進您的 music.csv 資料庫！")
                    
                    # 提示：Streamlit 會在重新整理時自動清理暫存檔，
                    # 或可手動 os.remove(audio_file) 以節省空間。
                else:
                    st.error("❌ 音訊處理失敗，請稍後再試。")
            else:
                st.warning("查無此歌曲，請試試看其他關鍵字。")

# --- 4. 側邊欄：音樂庫狀態 ---
st.sidebar.header("📊 您的雲端音樂庫")
try:
    current_lib = pd.read_csv(DATA_FILE)
    if not current_lib.empty:
        st.sidebar.write(f"目前已有 **{len(current_lib)}** 首歌曲")
        st.sidebar.dataframe(current_lib[["song", "artist"]], hide_index=True)
        
        if st.sidebar.button("🎲 隨機推薦"):
            pick = current_lib.sample(n=1).iloc[0]
            st.sidebar.write(f"推薦嘗試：**{pick['song']}**")
    else:
        st.sidebar.write("音樂庫目前是空的。")
except:
    st.sidebar.write("尚未建立音樂庫。")