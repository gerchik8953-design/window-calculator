import os
import re
import logging
from flask import Flask, request, jsonify
import requests
from openai import OpenAI

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# === НАСТРОЙКИ ===
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')

# ID администратора и менеджера (твой Telegram ID)
ADMIN_CHAT_ID = 628935507
MANAGER_CHAT_ID = 628935507

# Контакты компании
COMPANY_NAME = "Теплые Окна"
COMPANY_PHONE = "+7 (953) 816-06-98"
COMPANY_ADDRESS = "г. Орел, ул. Приборостроительная, д. 13, этаж 2, офис 20"
COMPANY_WEBSITE = "https://teplydom-orel.ru"
COMPANY_VK = "https://vk.com/teplye_okna57"

# Ссылка на портфолио
PORTFOLIO_URL = "https://teplydom-orel.ru/nashi-raboty"

# Хранилище состояний пользователей
user_states = {}

# === ИНИЦИАЛИЗАЦИЯ DEEPSEEK ===
deepseek_client = None
if DEEPSEEK_API_KEY:
    deepseek_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    logger.info("DeepSeek клиент инициализирован")
else:
    logger.error("DEEPSEEK_API_KEY не задан")

# === ФУНКЦИИ ===
def extract_phone_number(text):
    digits = re.sub(r'\D', '', text)
    return digits if len(digits) >= 10 else None

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={'chat_id': chat_id, 'text': text}, timeout=10)
    except Exception as e:
        logger.error(f"Ошибка отправки: {e}")

def send_action(chat_id):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendChatAction"
    try:
        requests.post(url, json={'chat_id': chat_id, 'action': 'typing'}, timeout=5)
    except Exception:
        pass

def send_keyboard(chat_id):
    """Отправляет клавиатуру с кнопками"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    keyboard = {
        "keyboard": [
            [{"text": "📞 Контакты"}, {"text": "📐 Записаться на замер"}],
            [{"text": "💰 Цены"}, {"text": "📸 Наши работы"}],
            [{"text": "❓ Помощь"}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }
    payload = {
        'chat_id': chat_id,
        'text': "👋 Добро пожаловать!\n\n"
                "С вами общается ИИ-консультант «Теплые Окна» 🤖\n"
                "Я помогаю подобрать окна, рассчитать стоимость и записаться на замер.\n\n"
                "Если нужен живой менеджер — позвоните по телефону +7 (953) 816-06-98\n\n"
                "Выберите действие:",
        'reply_markup': keyboard
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"Ошибка отправки клавиатуры: {e}")

def get_contact_info():
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

def notify_admin(chat_id, user_question, bot_answer):
    """Отправляет копию диалога администратору"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        answer_preview = bot_answer[:400] + "..." if len(bot_answer) > 400 else bot_answer
        text = f"📋 *Новый диалог*\n\n👤 Пользователь ID: `{chat_id}`\n\n❓ Вопрос: {user_question[:200]}\n\n🤖 Ответ: {answer_preview}"
        requests.post(url, json={'chat_id': ADMIN_CHAT_ID, 'text': text, 'parse_mode': 'Markdown'}, timeout=10)
    except Exception as e:
        logger.error(f"Ошибка уведомления админа: {e}")

# === ВЕБХУК ===
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({'status': 'ok'}), 200

    chat_id = data['message']['chat']['id']
    user_text = data['message'].get('text', '')

    logger.info(f"Получено сообщение от пользователя {chat_id}, длина: {len(user_text)} символов")

    if user_text.startswith('/start'):
        send_keyboard(chat_id)
        return jsonify({'status': 'ok'}), 200

    if user_text.startswith('/'):
        return jsonify({'status': 'ok'}), 200

    send_action(chat_id)

    # === ОБРАБОТКА КНОПОК ===
    if user_text == "📞 Контакты":
        reply = get_contact_info()
    elif user_text == "📐 Записаться на замер":
        user_states[chat_id] = 'waiting_for_phone'
        reply = "📐 Для вызова замерщика оставьте, пожалуйста, ваш номер телефона (в формате 8XXXXXXXXXX или +7XXXXXXXXXX).\n\n⚠️ Отправляя номер, вы соглашаетесь на обработку персональных данных для связи с вами."
    elif user_text == "💰 Цены":
        reply = """💰 *Наши цены на профили (за 1 м² без установки):*

• РЕХАУ BLITZ: 10 000 ₽
• REHAU Delight: 11 500 ₽
• KBE Engine: 10 000 ₽
• KBE Expert 70: 11 200 ₽
• VEKA Softline 70: 11 500 ₽
• HAGEL 70: 10 000 ₽
• KÖMMERLING 76: 12 000 ₽

Для уточнения цен на другие профили или расчёта под ваш размер — напишите, я помогу!"""
    elif user_text == "📸 Наши работы":
        reply = f"📸 Посмотрите примеры наших работ на сайте:\n\n🌐 {PORTFOLIO_URL}"
    elif user_text == "❓ Помощь":
        reply = """❓ *Я могу помочь:*

✅ Рассказать о ценах на окна
✅ Помочь выбрать профиль
✅ Ответить на вопросы про установку
✅ Записать вас на бесплатный замер
✅ Отправить ссылку на наши работы

Просто напишите ваш вопрос, или воспользуйтесь кнопками ниже."""
    
    # === ЯВНЫЕ ЗАПРОСЫ КОНТАКТОВ ===
    elif any(word in user_text.lower() for word in ['телефон', 'позвонить', 'связаться', 'контакт', 'адрес', 'сайт', 'вк', 'вконтакте', 'график']):
        reply = get_contact_info()
    
    # === ЗАЯВКА НА ЗАМЕР (текстом) ===
    elif 'замер' in user_text.lower() or 'заявк' in user_text.lower():
        user_states[chat_id] = 'waiting_for_phone'
        reply = "📐 Для вызова замерщика оставьте, пожалуйста, ваш номер телефона (в формате 8XXXXXXXXXX или +7XXXXXXXXXX).\n\n⚠️ Отправляя номер, вы соглашаетесь на обработку персональных данных для связи с вами."
    
    # === ОТПРАВКА НОМЕРА ТЕЛЕФОНА (проверяем состояние) ===
    elif user_states.get(chat_id) == 'waiting_for_phone':
        phone = extract_phone_number(user_text)
        if phone:
            try:
                url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
                requests.post(url, json={
                    'chat_id': MANAGER_CHAT_ID,
                    'text': f"🔔 *НОВАЯ ЗАЯВКА НА ЗАМЕР!*\n\n📞 Номер клиента: `{phone}`\n\nДля связи нажмите на это сообщение и выберите 'Ответить'.",
                    'parse_mode': 'Markdown'
                }, timeout=10)
                logger.info(f"Уведомление менеджеру отправлено для клиента {chat_id}")
            except Exception as e:
                logger.error(f"Ошибка уведомления менеджера: {e}")
            
            user_states[chat_id] = None
            reply = "✅ Спасибо! Ваш номер получен. Наш менеджер свяжется с вами в ближайшее время для согласования даты замера.\n\n📌 Ваши данные не хранятся на сервере и будут использованы только для связи."
        else:
            reply = "❓ Я не распознал номер телефона. Пожалуйста, отправьте номер в формате 8XXXXXXXXXX или +7XXXXXXXXXX (только цифры)."
    
    # === ОБЫЧНЫЙ НОМЕР ТЕЛЕФОНА (без состояния) ===
    elif extract_phone_number(user_text):
        reply = "❓ Если вы хотите записаться на замер, пожалуйста, напишите «Записаться на замер». Я помогу оформить заявку."
    
    # === ОСТАЛЬНЫЕ ВОПРОСЫ — DEEPSEEK ===
    else:
        if not deepseek_client:
            reply = "⚠️ Сервис временно недоступен"
        else:
            try:
                response = deepseek_client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": f"""
Ты — консультант по пластиковым окнам в компании "{COMPANY_NAME}".

=== ПРАВИЛА ОТВЕТОВ ===
1. Если клиент назвал бренд (REHAU, KBE, VEKA, HAGEL, KÖMMERLING) и размер (например, "Века 1350*1420"):
   - Рассчитай площадь (ширина × высота / 1000000)
   - Напиши: "💰 Цена профиля {{бренд}} без установки: {{цена_за_м² × площадь}} ₽"
   - Напиши: "🏠 Цена окна под ключ (доставка + демонтаж + установка + подоконник + отлив + откосы): {{цена_из_списка_под_ключ}} ₽ для стандартного окна 1.3×1.4м. Для вашего размера нужен точный замер."

2. Если клиент спрашивает "сколько стоят окна {{бренд}}" без размера:
   - Напиши цену за 1 м² профиля без установки
   - Напиши цену под ключ для стандартного окна 1.3×1.4м

=== ЦЕНЫ (за 1 м² без установки) ===
- РЕХАУ BLITZ: 10 000 ₽/м²
- REHAU Delight: 11 500 ₽/м²
- KBE Engine: 10 000 ₽/м²
- KBE Expert 70: 11 200 ₽/м²
- VEKA Euroline 58: 10 300 ₽/м²
- VEKA Softline 70: 11 500 ₽/м²
- HAGEL 58: 9 100 ₽/м²
- HAGEL 70: 10 000 ₽/м²
- KÖMMERLING 76: 12 000 ₽/м²

=== ЦЕНЫ ПОД КЛЮЧ (окно 1.3×1.4м) ===
- РЕХАУ BLITZ: 26 000 ₽
- REHAU Delight: 30 000 ₽
- KBE Engine: 25 500 ₽
- KBE Expert 70: 30 000 ₽
- VEKA Euroline 58: 27 000 ₽
- VEKA Softline 70: 34 000 ₽
- HAGEL 58: 24 500 ₽
- HAGEL 70: 26 000 ₽
- KÖMMERLING 76: 34 000 ₽

=== ДОПОЛНИТЕЛЬНЫЕ ПРАВИЛА ===
- Отвечай кратко, по делу, на русском языке.
- НИКОГДА не спрашивай телефон клиента.
- Контакты компании не давай — они уже обрабатываются отдельно.
- Если клиент хочет заказать замер — скажи, что нужно оставить номер телефона.
"""},
                        {"role": "user", "content": user_text}
                    ],
                    temperature=0.7,
                    max_tokens=800
                )
                reply = response.choices[0].message.content
            except Exception as e:
                logger.error(f"DeepSeek ошибка: {e}")
                reply = "⚠️ Извините, произошла ошибка. Попробуйте позже."

    # === ОТПРАВКА КОПИИ АДМИНИСТРАТОРУ ===
    if not user_text.startswith('/') and user_text not in ["📞 Контакты", "📐 Записаться на замер", "💰 Цены", "📸 Наши работы", "❓ Помощь"]:
        notify_admin(chat_id, user_text, reply)

    send_message(chat_id, reply)
    return jsonify({'status': 'ok'}), 200
