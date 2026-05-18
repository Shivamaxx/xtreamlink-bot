import asyncio
asyncio.set_event_loop(asyncio.new_event_loop())

from flask import Flask
from threading import Thread

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

import yt_dlp
import os

# Flask server for Render
app_web = Flask('')

@app_web.route('/')
def home():
    return "Bot is running!"

def run():
    app_web.run(host='0.0.0.0', port=10000)

Thread(target=run).start()

BOT_TOKEN = os.getenv("BOT_TOKEN")

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Store user links
user_links = {}

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    user_links[update.message.chat_id] = url

    keyboard = [
        [
            InlineKeyboardButton("🎥 360p", callback_data="360"),
            InlineKeyboardButton("🎥 720p", callback_data="720"),
        ],
        [
            InlineKeyboardButton("🎵 MP3", callback_data="mp3"),
        ],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Choose download format:",
        reply_markup=reply_markup
    )

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    quality = query.data
    chat_id = query.message.chat_id

    url = user_links.get(chat_id)

    if not url:
        await query.message.reply_text("❌ Link expired. Send again.")
        return

    await query.message.reply_text("⏳ Downloading...")

    try:

        # MP3 Download
        if quality == "mp3":

            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
                'quiet': True,
                'cookiefile': 'cookies.txt',

                'http_headers': {
                    'User-Agent': 'Mozilla/5.0',
                    'Referer': 'https://www.terabox.com/',
                },

                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            }

        # Video Download
        else:

            ydl_opts = {
                'format': 'best',
                'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
                'quiet': True,
                'cookiefile': 'cookies.txt',

                'http_headers': {
                    'User-Agent': 'Mozilla/5.0',
                    'Referer': 'https://www.terabox.com/',
                },

                'extractor_args': {
                    'youtube': {
                        'player_client': ['android']
                    }
                },
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

            if quality == "mp3":
                file_path = os.path.splitext(file_path)[0] + ".mp3"

        # Send Audio
        if quality == "mp3":

            with open(file_path, "rb") as audio:
                await query.message.reply_audio(audio=audio)

        # Send Video
        else:

            with open(file_path, "rb") as video:
                await query.message.reply_video(video=video)

        os.remove(file_path)
        user_links.pop(chat_id, None)

    except Exception as e:
        await query.message.reply_text(f"❌ Error: {e}")

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
app.add_handler(CallbackQueryHandler(button_click))

print("🚀 Bot Running...")
app.run_polling()
