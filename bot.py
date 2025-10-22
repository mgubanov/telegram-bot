"""
Sleep Tracker Bot — v1.2.1
---------------------------
Features:
- /start command to initialize the bot
- Start, Stop, and Cancel buttons for tracking sleep
- Calculates sleep duration
- Detects and labels sleep type (🌞 Day / 🌙 Night)
- Sends all messages inside a specific topic/thread (set via TOPIC_ID)
- Uses webhook mode for deployment (Render-friendly)
- Logs all user interactions
- Adjusted sleep classification: 06:00–18:00 → day; otherwise → night
"""

import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
import pytz

# --- Setup ---
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
TOPIC_ID = 4  # your topic/thread ID inside the group
BERLIN_TZ = pytz.timezone("Europe/Berlin")

# --- Logging ---
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# --- State storage ---
user_sleep_data = {}  # {user_id: datetime_start}


# --- Buttons ---
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("😴 Start sleep", callback_data="start_sleep")]
    ])


def sleep_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛑 Stop sleep", callback_data="stop_sleep")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_sleep")]
    ])


# --- Helpers ---
def get_sleep_type(start_time: datetime) -> str:
    """Return 'day' or 'night' based on start time hour."""
    hour = start_time.hour
    if 6 <= hour < 18:
        return "day"
    else:
        return "night"


# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"{user.first_name} ({user.id}) used /start")
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        message_thread_id=TOPIC_ID,
        text="Welcome to Sleep Tracker 😴\nPress start when you go to sleep:",
        reply_markup=main_menu()
    )


async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    user_id = user.id
    await query.answer()

    # --- Start sleep ---
    if query.data == "start_sleep":
        user_sleep_data[user_id] = datetime.now(BERLIN_TZ)
        start_time = user_sleep_data[user_id].strftime("%H:%M")
        logger.info(f"{user.first_name} started sleeping at {start_time}")
        await query.edit_message_text(
            text=f"Sleep started at {start_time} 💤",
            reply_markup=sleep_menu()
        )

    # --- Stop sleep ---
    elif query.data == "stop_sleep":
        if user_id not in user_sleep_data:
            await query.edit_message_text(
                "You haven’t started sleeping yet 😅",
                reply_markup=main_menu()
            )
            logger.warning(f"{user.first_name} tried to stop sleep without starting")
            return

        start_time = user_sleep_data.pop(user_id)
        end_time = datetime.now(BERLIN_TZ)

        duration = end_time - start_time
        hours, remainder = divmod(duration.seconds, 3600)
        minutes, _ = divmod(remainder, 60)

        start_str = start_time.strftime("%H:%M")
        end_str = end_time.strftime("%H:%M")
        duration_str = f"{hours}h {minutes}m"

        sleep_type = get_sleep_type(start_time)
        emoji = "🌞" if sleep_type == "day" else "🌙"

        logger.info(
            f"{user.first_name} stopped sleeping at {end_str} ({duration_str}, {sleep_type})"
        )

        await query.edit_message_text(
            text=f"{emoji} {sleep_type.capitalize()} sleep\n{start_str}–{end_str} ({duration_str})"
        )

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            message_thread_id=TOPIC_ID,
            text="Ready for next nap? 😴",
            reply_markup=main_menu()
        )

    # --- Cancel sleep ---
    elif query.data == "cancel_sleep":
        user_sleep_data.pop(user_id, None)
        logger.info(f"{user.first_name} canceled sleep tracking")
        await query.edit_message_text(
            text="Sleep tracking canceled. Ready when you are 💤",
            reply_markup=main_menu()
        )


# --- Flask Webhook ---
flask_app = Flask(__name__)

@flask_app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.create_task(application.process_update(update))
    return "OK", 200


# --- Telegram Bot Setup ---
application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(handle_buttons))

# --- Run Webhook ---
if __name__ == "__main__":
    logger.info("😴 Sleep Tracker Bot v1.2.1 starting via Webhook...")

    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        url_path="webhook",
        webhook_url=f"{WEBHOOK_URL}/webhook"
    )
