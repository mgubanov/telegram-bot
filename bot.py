"""
Sleep Tracker Bot — v1.2.0
---------------------------
Features:
- Webhook-based (no polling)
- /start command to initialize the bot
- Start, Stop, and Cancel buttons for tracking sleep
- Automatically calculates sleep duration
- Detects and labels sleep type (🌞 Day / 🌙 Night)
- Logs user interactions
- Sends all messages inside a specific topic/thread (set via TOPIC_ID)
"""

import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from flask import Flask, request

# --- Setup ---
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # e.g. https://your-app.onrender.com/webhook
TOPIC_ID = 4  # your topic/thread ID inside the group

# --- Logging ---
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# --- Flask app for webhook endpoint ---
flask_app = Flask(__name__)

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
    return "day" if 12 <= hour < 18 else "night"


# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command — sends the initial message with the start button."""
    user = update.effective_user
    logger.info(f"/start called by {user.full_name} (id: {user.id})")

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        message_thread_id=TOPIC_ID,
        text="Welcome to Sleep Tracker 😴\nPress start when you go to sleep:",
        reply_markup=main_menu(),
    )


async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles all button callbacks."""
    query = update.callback_query
    user = query.from_user
    user_id = user.id
    await query.answer()

    logger.info(f"Button pressed by {user.full_name} (id: {user_id}): {query.data}")

    # --- Start sleep ---
    if query.data == "start_sleep":
        user_sleep_data[user_id] = datetime.now()
        start_time = user_sleep_data[user_id].strftime("%H:%M")
        await query.edit_message_text(
            text=f"Sleep started at {start_time} 💤",
            reply_markup=sleep_menu(),
        )

    # --- Stop sleep ---
    elif query.data == "stop_sleep":
        if user_id not in user_sleep_data:
            await query.edit_message_text(
                "You haven’t started sleeping yet 😅",
                reply_markup=main_menu(),
            )
            return

        start_time = user_sleep_data.pop(user_id)
        end_time = datetime.now()

        duration = end_time - start_time
        hours, remainder = divmod(duration.seconds, 3600)
        minutes, _ = divmod(remainder, 60)

        start_str = start_time.strftime("%H:%M")
        end_str = end_time.strftime("%H:%M")
        duration_str = f"{hours}h {minutes}m"

        sleep_type = get_sleep_type(start_time)
        emoji = "🌞" if sleep_type == "day" else "🌙"

        logger.info(f"{user.full_name} ({user_id}) finished {sleep_type} sleep: {start_str}-{end_str} ({duration_str})")

        await query.edit_message_text(
            text=f"{emoji} {sleep_type.capitalize()} sleep\n{start_str}–{end_str} ({duration_str})"
        )

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            message_thread_id=TOPIC_ID,
            text="Ready for next nap? 😴",
            reply_markup=main_menu(),
        )

    # --- Cancel sleep ---
    elif query.data == "cancel_sleep":
        user_sleep_data.pop(user_id, None)
        logger.info(f"{user.full_name} ({user_id}) canceled sleep tracking.")
        await query.edit_message_text(
            text="Sleep tracking canceled. Ready when you are 💤",
            reply_markup=main_menu(),
        )


# --- Telegram App Setup ---
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(handle_buttons))


# --- Webhook routes ---
@flask_app.route("/webhook", methods=["POST"])
def webhook():
    """Main webhook endpoint."""
    update = Update.de_json(request.get_json(force=True), app.bot)
    app.update_queue.put_nowait(update)
    return "OK", 200


@flask_app.route("/")
def home():
    return "Sleep Tracker Bot is running 🚀", 200


# --- Start webhook server ---
if __name__ == "__main__":
    import asyncio

    async def run():
        await app.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
        logger.info(f"😴 Sleep Tracker Bot v1.2.0 started via Webhook at {WEBHOOK_URL}/webhook")
        flask_app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

    asyncio.run(run())
