import os
import logging
from flask import Flask, request, jsonify
import requests
from openai import OpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ========== НАСТРОЙКИ ==========
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')

# КОНТАКТЫ КОМПАНИИ
COMPANY_NAME = "Теплые Окна"
COMPANY_PHONE = "+7 (953) 816-06-98"
COMPANY_ADDRESS = "г. Орел, ул. Приборостроительная, д. 13, этаж 2, офис 20"
COMPANY_WEBSITE = "https://teplydom-orel.ru"
COMPANY_VK = "https://vk.com/teplye_okna57"
# =================================

if not DEEPSEEK_API_KEY:
    logger.error("DEEPSEEK_API_KEY не задан")
if not TELEGRAM_TOKEN:
    logger.error("TELEGRAM_TOKEN не задан")

deepseek_client = None
if DEEPSEEK_API_KEY:
    deepseek_client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com"
    )

def send_chat_action(chat_id, action):
    url = f"{TELEGRAM_API_URL}/sendChatAction"
    payload = {'chat_id': chat_id, 'action': action}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        logger.error(f"Ошибка отправки действия: {e}")

def send_message(chat_id, text):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {'chat_id': chat_id, 'text': text}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"Ошибка отправки в Telegram: {e}")

def is_contact_request(text):
    """Проверяет, хочет ли клиент получить контакты компании"""
    text_lower = text.lower()
    keywords = [
        'телефон', 'номер', 'позвонить', 'созвонить', 'звонок',
        'контакт', 'связаться', 'связь', 'контакты',
        'адрес', 'где находитесь', 'находитесь', 'офис', 'приехать', 'локация',
        'сайт', 'вебсайт', 'интернет сайт', 'страница',
        'вк', 'вконтакте', 'группа вк', 'группа вконтакте',
        'график', 'режим работы', 'работаете', 'открыто'
    ]
    return any(keyword in text_lower for keyword in keywords)

def get_contact_info():
    return f"""📞 *Контакты {COMPANY_NAME}:*

Телефон: {COMPANY_PHONE}
Адрес: {COMPANY_ADDRESS}
Сайт: {COMPANY_WEBSITE}
ВКонтакте: {COMPANY_VK}

*График работы:*
Пн–Пт: 9:00 – 20:00
Сб: 10:00 – 16:00
Вс: выходной

По всем вопросам обращайтесь, будем рады помочь!
"""

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    logger.info(f"Получен update: {update}")
    
    if 'message' in update:
        chat_id = update['message']['chat']['id']
        user_text = update['message'].get('text', '')
        
        if user_text.startswith('/'):
            return jsonify({'status': 'ok'}), 200
        
        send_chat_action(chat_id, "typing")
        
        # Если запрос про контакты или график — отвечаем сразу, без DeepSeek
        if is_contact_request(user_text):
            ai_reply = get_contact_info()
        else:
            if not deepseek_client:
                ai_reply = "⚠️ Сервис временно недоступен"
            else:
                try:
                    response = deepseek_client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[
                            {"role": "system", "content": f"""
Ты — консультант по пластиковым окнам в компании '{COMPANY_NAME}'.

Твоя задача:
- Отвечать на вопросы клиентов о ценах, профилях (REHAU, KBE, VEKA, HAGEL, KÖMMERLING), стеклопакетах.
- Если клиент хочет заказать замер — скажи, что менеджер свяжется с ним по телефону, который он укажет.
- Будь вежливым, но не навязчивым.
- Отвечай на русском языке.
- НИКОГДА не запрашивай у клиента его номер телефона, адрес, email или другие личные данные.
- Если клиент сам пишет свои контакты — не сохраняй их, просто поблагодари и скажи, что менеджер свяжется.
- НЕ давай контакты компании (телефон, адрес, сайт, ВК) — они уже обрабатываются отдельно.
"""},
                            {"role": "user", "content": user_text}
                        ],
                        temperature=0.7,
                        max_tokens=500
                    )
                    ai_reply = response.choices[0].message.content
                except Exception as e:
                    logger.error(f"Ошибка DeepSeek: {e}")
                    ai_reply = "⚠️ Ошибка, попробуйте позже"
        
        send_message(chat_id, ai_reply)
    
    return jsonify({'status': 'ok'}), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
