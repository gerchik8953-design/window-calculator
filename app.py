import os
import re
import logging
from flask import Flask, request, jsonify
import requests
from openai import OpenAI

# ================= НАСТРОЙКИ =================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Telegram и DeepSeek
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')

# Контакты компании
COMPANY_NAME = "Теплые Окна"
COMPANY_PHONE = "+7 (953) 816-06-98"
COMPANY_ADDRESS = "г. Орел, ул. Приборостроительная, д. 13, этаж 2, офис 20"
COMPANY_WEBSITE = "https://teplydom-orel.ru"
COMPANY_VK = "https://vk.com/teplye_okna57"

# ========== НОВАЯ НАСТРОЙКА: ВАШ ID ==========
# ВСТАВЬТЕ СВОЙ ID, КОТОРЫЙ ПОЛУЧИЛИ ОТ @userinfobot
MY_USER_ID = 628935507  # <-- ЗАМЕНИТЕ НА ВАШ ID
# ============================================

# === ИНИЦИАЛИЗАЦИЯ DEEPSEEK ===
deepseek_client = None
if DEEPSEEK_API_KEY:
    deepseek_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    logger.info("DeepSeek клиент инициализирован")
else:
    logger.error("DEEPSEEK_API_KEY не задан")

# === ФУНКЦИИ БОТА ===
def send_message(chat_id, text):
    """Отправка сообщения"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={'chat_id': chat_id, 'text': text}, timeout=10)
    except Exception as e:
        logger.error(f"Ошибка отправки: {e}")

def send_action(chat_id):
    """Индикатор «печатает»"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendChatAction"
    try:
        requests.post(url, json={'chat_id': chat_id, 'action': 'typing'}, timeout=5)
    except Exception:
        pass

def send_keyboard(chat_id):
    """Отправляет клавиатуру с двумя кнопками"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    keyboard = {
        "keyboard": [
            [{"text": "📞 Контакты"}, {"text": "📐 Записаться на замер"}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }
    payload = {
        'chat_id': chat_id,
        'text': "👋 Добро пожаловать! С вами общается ИИ-консультант «Теплые Окна» 🤖\nЯ помогаю подобрать окна, рассчитать стоимость и записаться на замер.\n\nЕсли нужен живой менеджер — позвоните по телефону +7 (953) 816-06-98\n\nВыберите действие:",
        'reply_markup': keyboard
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"Ошибка отправки клавиатуры: {e}")

def get_contact_info():
    """Формирует сообщение с контактами"""
    return f"""📞 *Контакты {COMPANY_NAME}:*

Телефон: {COMPANY_PHONE}
Адрес: {COMPANY_ADDRESS}
Сайт: {COMPANY_WEBSITE}
ВКонтакте: {COMPANY_VK}

*График работы:*
Пн–Пт: 9:30 – 18:00
Сб: 10:00 – 15:00
Вс: выходной
"""

# === ОСНОВНАЯ ЛОГИКА БОТА ===
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({'status': 'ok'}), 200

    chat_id = data['message']['chat']['id']
    user_text = data['message'].get('text', '')

    logger.info(f"Получено сообщение от пользователя {chat_id}, длина: {len(user_text)} символов")

    # === ОБРАБОТКА КОМАНДЫ /start ===
    if user_text.startswith('/start'):
        send_keyboard(chat_id)
        return jsonify({'status': 'ok'}), 200

    if user_text.startswith('/'):
        return jsonify({'status': 'ok'}), 200

    send_action(chat_id)

    # === ОБРАБОТКА КНОПОК И ТЕКСТА ===
    if user_text == "📞 Контакты":
        reply = get_contact_info()
    elif user_text == "📐 Записаться на замер":
        reply = "📐 Для вызова замерщика оставьте, пожалуйста, ваш номер телефона.\n\n⚠️ Отправляя номер, вы соглашаетесь на обработку персональных данных для связи с вами."
    elif any(word in user_text.lower() for word in ['телефон', 'позвонить', 'связаться', 'контакт', 'адрес', 'сайт', 'вк', 'вконтакте', 'график']):
        reply = get_contact_info()
    elif 'замер' in user_text.lower() or 'заявк' in user_text.lower():
        reply = "📐 Для вызова замерщика оставьте, пожалуйста, ваш номер телефона.\n\n⚠️ Отправляя номер, вы соглашаетесь на обработку персональных данных для связи с вами."
    
    # === ОТПРАВКА НОМЕРА ТЕЛЕФОНА (и пересылка менеджеру) ===
    elif any(char.isdigit() for char in user_text) and len(user_text) > 9:
        logger.info(f"Пользователь {chat_id} отправил номер телефона (данные не сохранены)")
        
        # --- ОТПРАВЛЯЕМ ЗАЯВКУ ВАМ В ЛИЧКУ ---
        manager_message = f"🔔 *НОВАЯ ЗАЯВКА НА ЗАМЕР!*\n\n📞 Номер клиента: `{user_text}`\n\nДля связи, нажмите на это сообщение и выберите 'Ответить'."
        send_message(MY_USER_ID, manager_message)
        # -------------------------------------
        
        reply = "✅ Спасибо! Ваш номер получен. Наш менеджер свяжется с вами в ближайшее время для согласования даты замера.\n\n📌 Ваши данные не хранятся на сервере и будут использованы только для связи."
    
    # === ОСТАЛЬНЫЕ ВОПРОСЫ — DEEPSEEK ===
    else:
        if not deepseek_client:
            reply = "⚠️ Сервис временно недоступен"
        else:
            try:
                response = deepseek_client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": f"Ты — консультант по пластиковым окнам в компании '{COMPANY_NAME}'. Отвечай кратко, по делу, на русском языке. НИКОГДА не спрашивай телефон клиента."},
                        {"role": "user", "content": user_text}
                    ],
                    temperature=0.7,
                    max_tokens=800
                )
                reply = response.choices[0].message.content
            except Exception as e:
                logger.error(f"DeepSeek ошибка: {e}")
                reply = "⚠️ Извините, произошла ошибка. Попробуйте позже."

    send_message(chat_id, reply)
    return jsonify({'status': 'ok'}), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
