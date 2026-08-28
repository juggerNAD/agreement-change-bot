"""
Agreement Change Request Bot
-----------------------------
Sales team DMs the bot /request, answers 3 questions one at a time,
the bot logs the submission to a Google Sheet (via an Apps Script
webhook) and posts a clean summary into the Agreement Change
Requests Telegram group.

Runs a tiny background HTTP server alongside the Telegram polling
loop, purely so Render's free Web Service tier has a port to detect
as "alive." The bot itself still works entirely through Telegram
polling, not HTTP.

NOTE: Render's free tier spins the service down after ~15 min of
inactivity. The first /request after it's been idle may take
30-60 seconds to respond while it wakes back up.

Env vars required (see .env.example):
  BOT_TOKEN          - Telegram bot token from @BotFather
  GROUP_CHAT_ID       - chat_id of the "Agreement Change Requests" group
  APPS_SCRIPT_URL     - Web App URL of the deployed Apps Script (AppsScript.gs)
  PORT                - provided automatically by Render, defaults to 10000 locally
"""

import os
import logging
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
GROUP_CHAT_ID = os.environ["GROUP_CHAT_ID"]
APPS_SCRIPT_URL = os.environ["APPS_SCRIPT_URL"]
PORT = int(os.environ.get("PORT", 10000))

# Conversation states
CLIENT_NAME, AGREEMENT_SENT, CHANGES_REQUESTED = range(3)


# ---- tiny health-check HTTP server (for Render's free tier) ----
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Agreement Change Request bot is running.")

    def log_message(self, format, *args):
        pass  # silence default request logging, keep logs clean


def run_health_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
    logger.info(f"Health check server listening on port {PORT}")
    server.serve_forever()


def log_to_sheet(payload: dict) -> bool:
    try:
        resp = requests.post(APPS_SCRIPT_URL, json=payload, timeout=15)
        resp.raise_for_status()
        return resp.json().get("status") == "ok"
    except Exception:
        logger.exception("Failed to log submission to Sheet via Apps Script")
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "📋 *Agreement Change Request*\n\n"
        "I'll ask you 3 quick questions. Send /cancel anytime to stop.\n\n"
        "1️⃣ What's the *client name*?",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    return CLIENT_NAME


async def client_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["client_name"] = update.message.text.strip()
    await update.message.reply_text(
        "2️⃣ *Exact agreement sent* — name/version of the agreement document?",
        parse_mode="Markdown",
    )
    return AGREEMENT_SENT


async def agreement_sent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["agreement_sent"] = update.message.text.strip()
    await update.message.reply_text(
        "3️⃣ *Explain the exact changes* they want — be specific "
        "(what's changing, from what to what):",
        parse_mode="Markdown",
    )
    return CHANGES_REQUESTED


async def changes_requested(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["changes_requested"] = update.message.text.strip()

    user = update.effective_user
    submitted_by = user.full_name
    username = f"@{user.username}" if user.username else "(no username)"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    data = context.user_data

    sheet_ok = log_to_sheet(
        {
            "timestamp": timestamp,
            "submitted_by": submitted_by,
            "username": username,
            "client_name": data["client_name"],
            "agreement_sent": data["agreement_sent"],
            "changes_requested": data["changes_requested"],
        }
    )

    summary = (
        "📋 *New Agreement Change Request*\n\n"
        f"*Client Name:* {data['client_name']}\n"
        f"*Agreement Sent:* {data['agreement_sent']}\n"
        f"*Changes Requested:* {data['changes_requested']}\n\n"
        f"_Submitted by {submitted_by} ({username}) — {timestamp}_"
    )
    try:
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ID, text=summary, parse_mode="Markdown"
        )
        post_ok = True
    except Exception:
        logger.exception("Failed to post summary to group")
        post_ok = False

    if post_ok and sheet_ok:
        await update.message.reply_text("✅ Submitted! Posted to the channel and logged.")
    elif post_ok:
        await update.message.reply_text(
            "✅ Posted to the channel, but logging to the Sheet failed — flagging for admin."
        )
    else:
        await update.message.reply_text(
            "⚠️ Something went wrong submitting this. Please try again or ping an admin."
        )

    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("Cancelled. Send /request to start over.")
    return ConversationHandler.END


def main() -> None:
    # Start the tiny health-check server in the background so Render's
    # free web service tier sees an open port and considers it "live."
    threading.Thread(target=run_health_server, daemon=True).start()

    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("request", start)],
        states={
            CLIENT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, client_name)],
            AGREEMENT_SENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, agreement_sent)],
            CHANGES_REQUESTED: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, changes_requested)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
