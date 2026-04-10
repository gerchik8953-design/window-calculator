import os
import logging
from flask import Flask, request, jsonify
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

def send_message(chat_id, text):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"Failed to send: {e}")

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    logger.info(f"Update: {update}")
    
    if 'message' in update:
        chat_id = update['message']['chat']['id']
        text = update['message'].get('text', '')
        
        # Обработка команд
        if text == '/start':
            send_message(chat_id, "👋 Здравствуйте! Я бот компании Теплые Окна.\n\nДоступные команды:\n/help - список команд\n/price - цены на окна")
        elif text == '/help':
            send_message(chat_id, "📋 Доступные команды:\n/start - приветствие\n/help - эта справка\n/price - цены на пластиковые окна")
        elif text == '/price':
            send_message(chat_id, "💰 <b>Цены на окна под ключ:</b>\n\nRehau (5 камер) — от 12 000 ₽/м²\nKBE (5 камер) — от 11 500 ₽/м²\nVEKA (5 камер) — от 13 000 ₽/м²\n\nБесплатный замер. Гарантия 5 лет.\nДля точного расчёта напишите размеры окна.")
        else:
            # Если текст не похож на команду
            if not text.startswith('/'):
                send_message(chat_id, "❓ Я понимаю только команды. Напишите /help для списка команд.")
    
    return jsonify({'status': 'ok'}), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
