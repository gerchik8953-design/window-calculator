import os
import logging
from flask import Flask, request, jsonify
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

def send_message(chat_id, text, reply_markup=None):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
    if reply_markup:
        payload['reply_markup'] = reply_markup
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"Failed to send: {e}")

# Клавиатура с кнопками
def get_main_keyboard():
    return {
        "keyboard": [
            [{"text": "📋 Цены"}],
            [{"text": "📞 Контакты"}, {"text": "❓ Помощь"}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    logger.info(f"Update: {update}")
    
    if 'message' in update:
        chat_id = update['message']['chat']['id']
        text = update['message'].get('text', '')
        
        # Обработка команд и кнопок
        if text == '/start' or text == '❓ Помощь':
            send_message(chat_id, "👋 Здравствуйте! Я бот компании Теплые Окна.\n\nНажмите на кнопку ниже, чтобы получить информацию.", reply_markup=get_main_keyboard())
        elif text == '/help':
            send_message(chat_id, "📋 Нажмите на кнопки под полем ввода, чтобы узнать цены или связаться с нами.", reply_markup=get_main_keyboard())
        elif text == '/price' or text == '📋 Цены':
            send_message(chat_id, "💰 <b>Цены на окна под ключ:</b>\n\nRehau (5 камер) — от 12 000 ₽/м²\nKBE (5 камер) — от 11 500 ₽/м²\nVEKA (5 камер) — от 13 000 ₽/м²\n\nБесплатный замер. Гарантия 5 лет.\nДля точного расчёта напишите размеры окна.", reply_markup=get_main_keyboard())
        elif text == '📞 Контакты':
            send_message(chat_id, "📞 <b>Свяжитесь с нами:</b>\n\nТелефон: +7 (900) 123-45-67\nEmail: okna@teplye-okna.ru\n\nИли напишите нам сюда — мы ответим!", reply_markup=get_main_keyboard())
        else:
            send_message(chat_id, "❓ Я понимаю только команды. Нажмите на кнопку /start или ❓ Помощь.", reply_markup=get_main_keyboard())
    
    return jsonify({'status': 'ok'}), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
