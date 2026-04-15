import os
import logging
from flask import Flask, request, jsonify
import requests
from openai import OpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')

COMPANY_NAME = "Теплые Окна"
COMPANY_PHONE = "+7 (953) 816-06-98"
COMPANY_ADDRESS = "г. Орел, ул. Приборостроительная, д. 13, этаж 2, офис 20"
COMPANY_WEBSITE = "https://teplydom-orel.ru"
COMPANY_VK = "https://vk.com/teplye_okna57"

deepseek_client = None
if DEEPSEEK_API_KEY:
    deepseek_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

def send_message(chat_id, text):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    try:
        requests.post(url, json={'chat_id': chat_id, 'text': text}, timeout=10)
    except Exception as e:
        logger.error(f"Ошибка отправки: {e}")

def send_action(chat_id):
    url = f"{TELEGRAM_API_URL}/sendChatAction"
    try:
        requests.post(url, json={'chat_id': chat_id, 'action': 'typing'}, timeout=5)
    except Exception:
        pass

def get_contact_info():
    return f"""📞 Контакты {COMPANY_NAME}:

Телефон: {COMPANY_PHONE}
Адрес: {COMPANY_ADDRESS}
Сайт: {COMPANY_WEBSITE}
ВКонтакте: {COMPANY_VK}

График работы:
Пн–Пт: 9:30 – 18:00
Сб: 10:00 – 15:00
Вс: выходной
"""

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    if not update or 'message' not in update:
        return jsonify({'status': 'ok'}), 200

    chat_id = update['message']['chat']['id']
    text = update['message'].get('text', '')

    if text.startswith('/'):
        return jsonify({'status': 'ok'}), 200

    send_action(chat_id)

    low = text.lower()
    # Жёсткая проверка на запрос контактов
    if any(word in low for word in ['телефон', 'номер', 'позвонить', 'вк', 'вконтакте', 'контакт', 'связаться', 'адрес', 'сайт', 'график', 'работаете']):
        reply = get_contact_info()
    else:
        if not deepseek_client:
            reply = "⚠️ Сервис временно недоступен"
        else:
            try:
                resp = deepseek_client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": f"Ты консультант по окнам в {COMPANY_NAME}. Отвечай кратко, по делу, на русском. НИКОГДА не спрашивай телефон клиента."},
                        {"role": "user", "content": text}
                    ],
                    temperature=0.7,
                    max_tokens=500
                )
                reply = resp.choices[0].message.content
            except Exception as e:
                logger.error(f"DeepSeek error: {e}")
                reply = "⚠️ Ошибка, попробуйте позже"

    send_message(chat_id, reply)
    return jsonify({'status': 'ok'}), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
