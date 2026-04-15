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

# КОНТАКТЫ КОМПАНИИ (ЗАМЕНИ НА СВОИ!)
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

# Системный промпт с контактами
SYSTEM_PROMPT = f"""
Ты — профессиональный консультант по пластиковым окнам в компании "{COMPANY_NAME}".

КОНТАКТЫ КОМПАНИИ:
- Телефон: {COMPANY_PHONE}
- Адрес: {COMPANY_ADDRESS}
- Сайт: {COMPANY_WEBSITE}
- ВКонтакте: {COMPANY_VK}

Твоя задача:
- Отвечать на вопросы клиентов о ценах, профилях (REHAU, KBE, VEKA, HAGEL, KÖMMERLING), стеклопакетах.
- Если клиент хочет заказать замер — передай контакты компании и скажи, что менеджер свяжется.
- Если клиент спрашивает контакты, адрес, телефон, сайт, ВК — дай точную информацию из списка выше.
- Будь вежливым, но не навязчивым.
- Отвечай на русском языке.
- НИКОГДА не спрашивай номер телефона, адрес, email или другие личные данные.
- Если клиент сам пишет контакты — не сохраняй их, просто поблагодари и скажи, что информация передана менеджеру.
"""

def send_chat_action(chat_id, action):
    """Отправляет сигнал «бот печатает»"""
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

def handle_contact_request(user_text):
    """Проверяет, хочет ли клиент получить контакты"""
    text_lower = user_text.lower()
    keywords = [
        'контакт', 'телефон', 'номер', 'позвонить', 'созвонить',
        'адрес', 'где находитесь', 'находитесь', 'офис', 'приехать',
        'сайт', 'вк', 'связаться', 'связь', 'написать',
        'как с вами', 'как с вами связаться'
    ]
    return any(keyword in text_lower for keyword in keywords)

def get_contact_info():
    return f"""📞 *Контакты {COMPANY_NAME}:*

Телефон: {COMPANY_PHONE}
Адрес: {COMPANY_ADDRESS}
Сайт: {COMPANY_WEBSITE}
ВКонтакте: {COMPANY_VK}

Режим работы: по будням с 9:30 до 18:00 выходной: воскресенье
"""

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
        
        # Отправляем сигнал «печатает...»
        send_chat_action(chat_id, "typing")
        
        # Проверяем, запрашивает ли клиент контакты
        if handle_contact_request(user_text):
            ai_reply = get_contact_info()
        else:
            # Получаем ответ от ИИ
            ai_reply = get_ai_response(user_text)
        
        # Отправляем готовый ответ
        send_message(chat_id, ai_reply)
    
    return jsonify({'status': 'ok'}), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
