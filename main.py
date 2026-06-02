#!/usr/bin/env python3
# Telegram OSINT Bot - Flask Webhook Version for Render

import os
import json
import re
import time
import requests
import hashlib
import threading
from datetime import datetime
from typing import Dict, Any, Optional
import logging
from flask import Flask, request, jsonify

# ==================== CONFIGURATION ====================
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8862514002:AAH73OEOZzyC5DPcMlzm1c6xu-1fWmHCwpc')
API_URL = f'https://api.telegram.org/bot{BOT_TOKEN}/'
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', '')  # Set this in Render env vars
PORT = int(os.environ.get('PORT', 10000))

# API Endpoints
NUMBER_API_ENDPOINT = 'https://exploitsindia.site/demo/number.php?exploits={term}'
AADHAAR_API_ENDPOINT = 'https://exploitsindia.site/demo/aadhar.php?exploits={term}'
FAMILY_API_ENDPOINT = 'https://exploitsindia.site/demo/family.php?exploits={term}'
PINCODE_API_ENDPOINT = 'https://exploitsindia.site/demo/pincode.php?exploits={term}'
IFSC_API_ENDPOINT = 'https://exploitsindia.site/demo/ifsc.php?exploits={term}'
TELEGRAM_API_ENDPOINT = 'https://exploitsindia.site/demo/telegram.php?exploits={term}'
INSTAGRAM_API_ENDPOINT = 'https://exploitsindia.site/demo/instagram.php?exploits={term}'
VEHICLE_API_ENDPOINT = 'https://exploitsindia.site/demo/vehicle.php?exploits={term}'

STATE_DIR = './bot_states'
CACHE_DIR = './cache'

os.makedirs(STATE_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ==================== HELPER FUNCTIONS ====================
def http_get(url: str, use_cache: bool = False) -> str:
    cache_key = hashlib.md5(url.encode()).hexdigest()
    cache_file = os.path.join(CACHE_DIR, f'{cache_key}.json')

    if use_cache and os.path.exists(cache_file):
        cache_age = time.time() - os.path.getmtime(cache_file)
        if cache_age < 300:
            with open(cache_file, 'r') as f:
                return f.read()

    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            if use_cache:
                with open(cache_file, 'w') as f:
                    f.write(response.text)
            return response.text
        return f"Error: Request failed (HTTP {response.status_code})"
    except Exception as e:
        logger.error(f"HTTP request failed: {e}")
        return f"Error: {str(e)}"

def clean_response(response: str) -> str:
    patterns = [
        r'BUY API :.*?\nSUPPORT :.*?\nCredit:.*?$',
        r'BUY API :.*?\nSUPPORT :.*?$',
        r'BUY API:.*?\nSUPPORT:.*?$',
        r'Credit :.*?\nApi By :.*?$',
        r'Credit:.*?$',
    ]
    for pattern in patterns:
        response = re.sub(pattern, '', response, flags=re.DOTALL)
    response = re.sub(r'\n{3,}', '\n\n', response)
    return response.strip()

def load_state(chat_id: str) -> Dict:
    state_file = os.path.join(STATE_DIR, f'state_{chat_id}.json')
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_state(chat_id: str, state: Dict) -> None:
    clean_state = {}
    for key, value in state.items():
        if callable(value):
            continue
        clean_state[key] = value

    state_file = os.path.join(STATE_DIR, f'state_{chat_id}.json')
    try:
        with open(state_file, 'w') as f:
            json.dump(clean_state, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save state: {e}")

# ==================== TELEGRAM API FUNCTIONS ====================
def send_message(chat_id: str, text: str, reply_markup: Dict = None) -> Optional[Dict]:
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)

    try:
        response = requests.post(API_URL + 'sendMessage', data=payload, timeout=10)
        return response.json()
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        return None

def send_photo(chat_id: str, photo_url: str, caption: str = '', reply_markup: Dict = None) -> Optional[Dict]:
    payload = {
        'chat_id': chat_id,
        'photo': photo_url,
        'caption': caption,
        'parse_mode': 'HTML'
    }
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)

    try:
        response = requests.post(API_URL + 'sendPhoto', data=payload, timeout=10)
        return response.json()
    except Exception as e:
        logger.error(f"Failed to send photo: {e}")
        return None

# ==================== KEYBOARDS ====================
def get_main_keyboard() -> Dict:
    return {
        'keyboard': [
            [{'text': 'NUMBER LOOKUP'}, {'text': 'AADHAAR LOOKUP'}],
            [{'text': 'FAMILY LOOKUP'}, {'text': 'PINCODE LOOKUP'}],
            [{'text': 'IFSC LOOKUP'}, {'text': 'INSTAGRAM LOOKUP'}],
            [{'text': 'TELEGRAM LOOKUP'}, {'text': 'VEHICLE LOOKUP'}]
        ],
        'resize_keyboard': True
    }

def get_cancel_keyboard() -> Dict:
    return {
        'keyboard': [[{'text': 'CANCEL'}]],
        'resize_keyboard': True
    }

# ==================== FORMAT FUNCTIONS ====================
def format_number_response(response: str, term: str, retry: bool = True) -> str:
    if "Error" in response or not response:
        if retry:
            time.sleep(1)
            url = NUMBER_API_ENDPOINT.replace('{term}', term)
            retry_response = http_get(url)
            return format_number_response(retry_response, term, False)
        return "Error: No data found for this number."

    response = clean_response(response)
    return f"<b>NUMBER LOOKUP RESULT</b>\n\n{'='*30}\n\n{response}\n\n{'='*30}"

def format_aadhaar_response(response: str, term: str, retry: bool = True) -> str:
    if "Error" in response or not response:
        if retry:
            time.sleep(1)
            url = AADHAAR_API_ENDPOINT.replace('{term}', term)
            retry_response = http_get(url)
            return format_aadhaar_response(retry_response, term, False)
        return "Error: No data found for this Aadhaar number."

    response = clean_response(response)
    return f"<b>AADHAAR LOOKUP RESULT</b>\n\n{'='*30}\n\n{response}\n\n{'='*30}"

def format_pincode_response(response: str, term: str, retry: bool = True) -> str:
    if "Error" in response or not response:
        if retry:
            time.sleep(1)
            url = PINCODE_API_ENDPOINT.replace('{term}', term)
            retry_response = http_get(url)
            return format_pincode_response(retry_response, term, False)
        return "Error: No data found for this pincode."

    response = clean_response(response)
    return f"<b>PINCODE LOOKUP RESULT</b>\n\n{'='*30}\n\n{response}\n\n{'='*30}"

def format_family_response(response: str, term: str, retry: bool = True) -> str:
    if "Error" in response or not response or len(response) < 20:
        if retry:
            time.sleep(1)
            url = FAMILY_API_ENDPOINT.replace('{term}', term)
            retry_response = http_get(url)
            return format_family_response(retry_response, term, False)
        return f"No family records found for: {term}"

    if "<!DOCTYPE" in response or "<html" in response:
        return "API temporarily unavailable. Please try again later."

    response = clean_response(response)

    if len(response) < 15:
        return "No family data found for this Aadhaar number."

    return f"<b>FAMILY LOOKUP RESULT</b>\n\n{'='*30}\n\n{response}\n\n{'='*30}"

def format_ifsc_response(response: str, term: str, retry: bool = True) -> str:
    if "Error" in response or not response:
        if retry:
            time.sleep(1)
            url = IFSC_API_ENDPOINT.replace('{term}', term)
            retry_response = http_get(url)
            return format_ifsc_response(retry_response, term, False)
        return f"Error: No IFSC data found for: {term}"

    response = clean_response(response)
    return f"<b>IFSC LOOKUP RESULT</b>\n\n{'='*30}\n\n{response}\n\n{'='*30}"

def format_telegram_response(response: str, term: str, retry: bool = True) -> str:
    if "Error" in response or not response or len(response) < 30:
        if retry:
            time.sleep(1)
            url = TELEGRAM_API_ENDPOINT.replace('{term}', term)
            retry_response = http_get(url)
            return format_telegram_response(retry_response, term, False)
        return "Error: No data found for this Telegram ID/Username."

    response = clean_response(response)
    return f"{response}\n\n{'='*30}"

def format_instagram_response(response: str, term: str, retry: bool = True) -> str:
    if "Error" in response or not response or len(response) < 30:
        if retry:
            time.sleep(1)
            url = INSTAGRAM_API_ENDPOINT.replace('{term}', term)
            retry_response = http_get(url)
            return format_instagram_response(retry_response, term, False)
        return "Error: No data found for this Instagram username."

    try:
        data = json.loads(response)
        if data.get('status') and data.get('data', {}).get('profile'):
            profile = data['data']['profile']
            output = f"{'='*30}\n<b>INSTAGRAM LOOKUP RESULT</b>\n{'='*30}\n\n"
            output += f"Lookup Result for: @{profile.get('username', term)}\n"
            output += f"{'-'*20}\n\n"
            output += f"ID: {profile.get('id', 'N/A')}\n"
            output += f"Username: @{profile.get('username', 'N/A')}\n"
            output += f"Full Name: {profile.get('full_name', 'N/A')}\n"
            output += f"Bio: {profile.get('biography', 'N/A')}\n"
            output += f"Private: {'Yes' if profile.get('is_private') else 'No'}\n"
            output += f"Verified: {'Yes' if profile.get('is_verified') else 'No'}\n"
            output += f"Followers: {profile.get('followers', 0):,}\n"
            output += f"Following: {profile.get('following', 0):,}\n"
            output += f"Posts: {profile.get('posts', 0)}\n"
            output += f"\n{'='*30}"
            return output
    except:
        pass

    response = clean_response(response)
    return f"<b>INSTAGRAM LOOKUP RESULT</b>\n\n{'='*30}\n\n{response}\n\n{'='*30}"

def format_vehicle_response(response: str, term: str, retry: bool = True) -> str:
    if "Error" in response or not response or len(response) < 20:
        if retry:
            time.sleep(1)
            url = VEHICLE_API_ENDPOINT.replace('{term}', term)
            retry_response = http_get(url)
            return format_vehicle_response(retry_response, term, False)
        return "Error: No data found for this vehicle number."

    response = clean_response(response)
    return f"<b>VEHICLE LOOKUP RESULT</b>\n\n{'='*30}\n\n{response}\n\n{'='*30}"

# ==================== LOOKUP CONFIGURATION ====================
LOOKUPS = {
    'NUMBER LOOKUP': {
        'stage': 'awaiting_number',
        'prompt': "<b>Number Lookup</b>\n\nSend 10 digit mobile number:\n\nExample: <code>1234567890</code>",
        'api_endpoint': NUMBER_API_ENDPOINT,
        'format_func': 'number',
        'pattern': r'^\d{10}$',
        'error_msg': "Invalid mobile number! Send 10 digits only."
    },
    'AADHAAR LOOKUP': {
        'stage': 'awaiting_aadhaar',
        'prompt': "<b>Aadhaar Lookup</b>\n\nSend 12 digit Aadhaar number:\n\nExample: <code>123456789012</code>",
        'api_endpoint': AADHAAR_API_ENDPOINT,
        'format_func': 'aadhaar',
        'pattern': r'^\d{12}$',
        'error_msg': "Invalid Aadhaar number! Send 12 digits only."
    },
    'FAMILY LOOKUP': {
        'stage': 'awaiting_family',
        'prompt': "<b>Family Lookup</b>\n\nSend Aadhaar Number:\n\nExample: <code>123456789012</code>",
        'api_endpoint': FAMILY_API_ENDPOINT,
        'format_func': 'family',
        'pattern': r'^\d{12}$',
        'error_msg': "Invalid Aadhaar number! Send 12 digit number."
    },
    'PINCODE LOOKUP': {
        'stage': 'awaiting_pincode',
        'prompt': "<b>Pincode Lookup</b>\n\nSend 6 digit PINCODE:\n\nExample: <code>123456</code>",
        'api_endpoint': PINCODE_API_ENDPOINT,
        'format_func': 'pincode',
        'pattern': r'^\d{6}$',
        'error_msg': "Invalid pincode! Send 6 digits only."
    },
    'IFSC LOOKUP': {
        'stage': 'awaiting_ifsc',
        'prompt': "<b>IFSC Lookup</b>\n\nSend IFSC Code:\n\nExample: <code>SBIN0001234</code>",
        'api_endpoint': IFSC_API_ENDPOINT,
        'format_func': 'ifsc',
        'pattern': r'^[A-Z]{4}0[A-Z0-9]{6}$',
        'clean': 'upper',
        'error_msg': "Invalid IFSC code! Format: 4 letters + 0 + 6 digits/letters"
    },
    'INSTAGRAM LOOKUP': {
        'stage': 'awaiting_instagram',
        'prompt': "<b>Instagram Lookup</b>\n\nSend Instagram username:\n\nExample: <code>instagramuser</code>",
        'api_endpoint': INSTAGRAM_API_ENDPOINT,
        'format_func': 'instagram',
        'pattern': r'^[a-zA-Z0-9_.]{1,30}$',
        'error_msg': "Invalid Instagram username! Use letters, numbers, underscore, dot."
    },
    'TELEGRAM LOOKUP': {
        'stage': 'awaiting_telegram',
        'prompt': "<b>Telegram Lookup</b>\n\nSend Telegram User ID or Username:\n\nExample: <code>1234567890</code> or <code>@username</code>",
        'api_endpoint': TELEGRAM_API_ENDPOINT,
        'format_func': 'telegram',
        'pattern': r'^(@?[a-zA-Z0-9_]{5,32}|\d+)$',
        'error_msg': "Invalid Telegram ID/Username!"
    },
    'VEHICLE LOOKUP': {
        'stage': 'awaiting_vehicle',
        'prompt': "<b>Vehicle Lookup</b>\n\nSend vehicle registration number:\n\nExample: <code>AB01PB6268</code>",
        'api_endpoint': VEHICLE_API_ENDPOINT,
        'format_func': 'vehicle',
        'pattern': r'^[A-Z]{2}[0-9]{1,2}[A-Z]{1,2}[0-9]{4}$',
        'clean': 'upper',
        'error_msg': "Invalid vehicle number!\n\nValid formats:\n- BR07PB6268\n- UP32AB1234\n- DL09C1234\n- MH12AB1234"
    }
}

def get_format_func(func_name: str):
    funcs = {
        'number': format_number_response,
        'aadhaar': format_aadhaar_response,
        'family': format_family_response,
        'pincode': format_pincode_response,
        'ifsc': format_ifsc_response,
        'telegram': format_telegram_response,
        'instagram': format_instagram_response,
        'vehicle': format_vehicle_response,
    }
    return funcs.get(func_name, format_number_response)

# ==================== MAIN BOT LOGIC ====================
def handle_message(update: Dict) -> None:
    message = update.get('message')
    callback = update.get('callback_query')

    if not message and not callback:
        return

    if callback:
        chat_id = str(callback['message']['chat']['id'])
        text = callback['data']
    else:
        chat_id = str(message['chat']['id'])
        text = message.get('text', '').strip()

    if not text:
        return

    state = load_state(chat_id)
    logger.info(f"Chat {chat_id}: text='{text}', stage={state.get('stage', 'idle')}")

    # Handle /start command
    if text == '/start':
        welcome_caption = """Welcome To - OSINT Information Bot

Free Bot And Unlimited"""

        send_photo(chat_id, 'https://i.postimg.cc/Bv4BqTS0/IMG-2557.jpg', welcome_caption, get_main_keyboard())

        state = {'stage': 'idle'}
        save_state(chat_id, state)
        return

    # Handle cancel button
    if text == 'CANCEL':
        send_message(chat_id, "Cancelled.", get_main_keyboard())
        state = {'stage': 'idle'}
        save_state(chat_id, state)
        return

    # Check if message is a lookup button
    for btn_text, cfg in LOOKUPS.items():
        if text == btn_text:
            send_message(chat_id, cfg['prompt'], get_cancel_keyboard())
            state = {
                'stage': cfg['stage'],
                'api_endpoint': cfg['api_endpoint'],
                'format_func': cfg['format_func']
            }
            if 'pattern' in cfg:
                state['pattern'] = cfg['pattern']
            if 'clean' in cfg:
                state['clean'] = cfg['clean']
            if 'error_msg' in cfg:
                state['error_msg'] = cfg['error_msg']
            save_state(chat_id, state)
            logger.info(f"Chat {chat_id}: Set stage to {cfg['stage']}")
            return

    # Handle input for lookups
    awaiting_stages = [
        'awaiting_number', 'awaiting_aadhaar', 'awaiting_family',
        'awaiting_pincode', 'awaiting_ifsc', 'awaiting_instagram',
        'awaiting_telegram', 'awaiting_vehicle'
    ]

    if state.get('stage') in awaiting_stages:
        query = text

        # Remove +91 prefix for number lookup
        if state['stage'] == 'awaiting_number':
            query = query.replace('+91', '').replace('+', '')

        # Clean if needed
        if state.get('clean') == 'upper':
            query = query.upper()

        # Validate pattern
        if 'pattern' in state:
            if not re.match(state['pattern'], query):
                error_msg = state.get('error_msg', "Invalid input format! Please try again.")
                send_message(chat_id, error_msg, get_cancel_keyboard())
                return

        if query:
            send_message(chat_id, "Fetching details...")
            url = state['api_endpoint'].replace('{term}', query)
            response = http_get(url)

            format_func_name = state.get('format_func', 'number')
            format_func = get_format_func(format_func_name)
            formatted = format_func(response, query)

            send_message(chat_id, formatted, get_main_keyboard())

            state = {'stage': 'idle'}
            save_state(chat_id, state)
            logger.info(f"Chat {chat_id}: Lookup completed, reset to idle")
        else:
            send_message(chat_id, "Invalid input! Please try again.", get_cancel_keyboard())
        return

    # Unknown command
    if text and not text.startswith('/'):
        send_message(chat_id, "Unknown command. Use buttons.", get_main_keyboard())

# ==================== FLASK ROUTES ====================
@app.route('/')
def home():
    return "Bot is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        update = request.get_json()
        if update:
            threading.Thread(target=handle_message, args=(update,)).start()
        return jsonify({'ok': True}), 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/health')
def health():
    return jsonify({'status': 'ok'}), 200

def setup_webhook():
    """Set Telegram webhook on startup"""
    if WEBHOOK_URL:
        webhook_url = f"{WEBHOOK_URL}/webhook"
        try:
            response = requests.post(
                API_URL + 'setWebhook',
                data={'url': webhook_url},
                timeout=10
            )
            result = response.json()
            if result.get('ok'):
                logger.info(f"Webhook set successfully: {webhook_url}")
            else:
                logger.error(f"Failed to set webhook: {result}")
        except Exception as e:
            logger.error(f"Webhook setup error: {e}")

if __name__ == '__main__':
    setup_webhook()
    app.run(host='0.0.0.0', port=PORT)
