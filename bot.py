"""
Sleep Tracker Bot — v1.1.0
---------------------------
Features:
- /start command to initialize the bot
- Start, Stop, and Cancel buttons for tracking sleep
- Automatically calculates sleep duration
- Detects and labels sleep type (🌞 Day / 🌙 Night)
- Sends all messages inside a specific topic/thread (set via TOPIC_ID)
"""

import os
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# --- Setup ---
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
TOPIC_ID = 4  # your topic/thread ID inside the group

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
    if 12 <= hour < 18:
        return "day"
    else:
        return "night"


# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command — sends the initial message with the start button."""
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        message_thread_id=TOPIC_ID,
        text="Welcome to Sleep Tracker 😴\nPress start when you go to sleep:",
        reply_markup=main_menu()
    )


async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles all button callbacks."""
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    # --- Start sleep ---
    if query.data == "start_sleep":
        user_sleep_data[user_id] = datetime.now()
        start_time = user_sleep_data[user_id].strftime("%H:%M")
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
            return

        start_time = user_sleep_data.pop(user_id)
        end_time = datetime.now()

        duration = end_time - start_time
        hours, remainder = divmod(duration.seconds, 3600)
        minutes, _ = divmod(remainder, 60)

        start_str = start_time.strftime("%H:%M")
        end_str = end_time.strftime("%H:%M")
        duration_str = f"{hours}h {minutes}m"

        # 🕓 Detect sleep type
        sleep_type = get_sleep_type(start_time)
        emoji = "🌞" if sleep_type == "day" else "🌙"

        # 1️⃣ Keep summary message in chat
        await query.edit_message_text(
            text=f"{emoji} {sleep_type.capitalize()} sleep\n{start_str}–{end_str} ({duration_str})"
        )

        # 2️⃣ Send new "Start" message in the same topic
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            message_thread_id=TOPIC_ID,
            text="Ready for next nap? 😴",
            reply_markup=main_menu()
        )

    # --- Cancel sleep ---
    elif query.data == "cancel_sleep":
        user_sleep_data.pop(user_id, None)
        await query.edit_message_text(
            text="Sleep tracking canceled. Ready when you are 💤",
            reply_markup=main_menu()
        )


# --- App setup ---
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(handle_buttons))

print("😴 Sleep Tracker Bot v1.1.0 is running (thread mode)...")
app.run_polling()
