#!/usr/bin/env python3

import os
import re
import time
import json
import requests
import logging
from flask import Flask, request

# ================= CONFIG =================
BOT_TOKEN = os.environ.get("8862514002:AAH73OEOZzyC5DPcMlzm1c6xu-1fWmHCwpc")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"

PORT = int(os.environ.get("PORT", 10000))

# ================= LOGGING =================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================= APP =================
app = Flask(__name__)

# ================= MEMORY STATE =================
USER_STATES = {}

def load_state(chat_id):
    return USER_STATES.get(chat_id, {})

def save_state(chat_id, state):
    USER_STATES[chat_id] = state

# ================= TELEGRAM =================
def send_message(chat_id, text, keyboard=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if keyboard:
        payload["reply_markup"] = json.dumps(keyboard)

    requests.post(API_URL + "sendMessage", data=payload)

# ================= KEYBOARD =================
def main_keyboard():
    return {
        "keyboard": [
            [{"text": "📱 NUMBER LOOKUP"}],
        ],
        "resize_keyboard": True
    }

def cancel_keyboard():
    return {
        "keyboard": [[{"text": "↩️ CANCEL"}]],
        "resize_keyboard": True
    }

# ================= API =================
def number_lookup(num):
    url = f"https://exploitsindia.site/demo/number.php?exploits={num}"
    try:
        r = requests.get(url, timeout=10)
        return r.text
    except:
        return "❌ API Error"

# ================= HANDLER =================
def handle(update):
    message = update.get("message")
    if not message:
        return

    chat_id = str(message["chat"]["id"])
    text = message.get("text", "").strip()

    state = load_state(chat_id)

    # ===== START =====
    if text == "/start":
        send_message(chat_id, "🔥 Welcome to OSINT Bot", main_keyboard())
        save_state(chat_id, {"stage": "idle"})
        return

    # ===== CANCEL =====
    if text == "↩️ CANCEL":
        send_message(chat_id, "❌ Cancelled", main_keyboard())
        save_state(chat_id, {"stage": "idle"})
        return

    # ===== BUTTON =====
    if text == "📱 NUMBER LOOKUP":
        send_message(chat_id, "Send 10 digit number:", cancel_keyboard())
        save_state(chat_id, {"stage": "awaiting_number"})
        return

    # ===== INPUT =====
    if state.get("stage") == "awaiting_number":

        # clean number
        num = re.sub(r"\D", "", text)[-10:]

        if not re.match(r"^\d{10}$", num):
            send_message(chat_id, "❌ Invalid number", cancel_keyboard())
            return

        send_message(chat_id, "⏳ Fetching...")

        res = number_lookup(num)

        send_message(chat_id, f"📱 RESULT:\n\n{res}", main_keyboard())

        save_state(chat_id, {"stage": "idle"})
        return

    # ===== DEFAULT =====
    send_message(chat_id, "❌ Unknown command", main_keyboard())

# ================= ROUTES =================
@app.route("/")
def home():
    return "Bot Running ✅"

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()
    handle(update)
    return "ok"

# ================= MAIN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
