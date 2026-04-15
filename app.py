import os
import logging
from flask import Flask, request, jsonify
import requests
from openai import OpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Telegram
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# DeepSeek API
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')

# Проверяем, что ключи заданы
if not DEEPSEEK_API_KEY:
    logger.error("DEEPSEEK_API_KEY не задан в переменных окружения")
if not TELEGRAM_TOKEN:
    logger.error("TELEGRAM_TOKEN не задан в переменных окружения")

# Инициализируем клиент только если ключ есть
deepseek_client = None
if DEEPSEEK_API_KEY:
    deepseek_client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com"
    )

SYSTEM_PROMPT = """
Ты — профессиональный консультант по пластиковым окнам в компании "Теплые Окна".
Твоя задача:
- Отвечать на вопросы клиентов о ценах на окна и балконы, профилях (REHAU, KBE, VEKA, HAGEL, KÖMMERLING), стеклопакетах.
- Если клиент хочет заказать замер — дай контакты или скажи, что передашь заявку менеджеру.
- Будь вежливым, но не навязчивым.
- Не придумывай цены, если их нет в памяти — скажи, что нужно уточнить у менеджера.
- Отвечай на русском языке.
"""

def send_message(chat_id, text):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {'chat_id': chat_id, 'text': text}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"Ошибка отправки в Telegram: {e}")

def get_ai_response(user_message):
    if not deepseek_client:
        return "⚠️ Извините, сервис временно недоступен. Попробуйте позже."
    try:
        response = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Ошибка DeepSeek API: {e}")
        return "⚠️ Извините, сейчас не могу ответить. Попробуйте позже."

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    logger.info(f"Получен update: {update}")
    
    if 'message' in update:
        chat_id = update['message']['chat']['id']
        user_text = update['message'].get('text', '')
        
        if user_text.startswith('/'):
            return jsonify({'status': 'ok'}), 200
        
        ai_reply = get_ai_response(user_text)
        send_message(chat_id, ai_reply)
    
    return jsonify({'status': 'ok'}), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
