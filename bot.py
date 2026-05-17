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
import glob

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

user_links = {}

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    chat_id = update.message.chat.id
    user_links[chat_id] = url

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
    chat_id = query.message.chat.id
    url = user_links.get(chat_id)

    if not url:
        await query.message.reply_text("❌ Link expired. Send again.")
        return

    await query.message.reply_text("⏳ Downloading...")

    cookie_opts = {}
    if os.path.exists('cookies.txt'):
        cookie_opts['cookiefile'] = 'cookies.txt'
        print("✅ cookies.txt FOUND")
    else:
        print("❌ cookies.txt NOT FOUND")

    try:
        common = {
            'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['web'],
                    'skip': ['hls', 'dash'],
                }
            },
            **cookie_opts,
        }
        if quality == "mp3":
            ydl_opts = {
                **common,
                'format': 'bestaudio/best',
            }
        elif quality == "360":
            ydl_opts = {
                **common,
                'format': 'best[height<=360]/best',
            }
        elif quality == "720":
            ydl_opts = {
                **common,
                'format': 'best[height<=720]/best',
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            base_path = ydl.prepare_filename(info)
            base_no_ext = os.path.splitext(base_path)[0]

        if quality == "mp3":
            file_path = base_no_ext + ".mp3"
        else:
            mp4_path = base_no_ext + ".mp4"
            if os.path.exists(mp4_path):
                file_path = mp4_path
            else:
                matches = glob.glob(base_no_ext + ".*")
                if matches:
                    file_path = matches[0]
                else:
                    file_path = base_path

        if not os.path.exists(file_path):
            await query.message.reply_text("❌ File download nahi hui. Dobara try karo.")
            return

        if quality == "mp3":
            with open(file_path, "rb") as audio:
                await query.message.reply_audio(audio=audio)
        else:
            with open(file_path, "rb") as video:
                await query.message.reply_video(video=video)

        user_links.pop(chat_id, None)
        if os.path.exists(file_path):
            os.remove(file_path)

    except Exception as e:
        await query.message.reply_text(f"❌ Error: {e}")

print("BOT TOKEN:", BOT_TOKEN)
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
app.add_handler(CallbackQueryHandler(button_click))
print("🚀 Bot Running...")
app.run_polling()
