import os
import re
import logging
from flask import Flask, request, jsonify
import requests
from openai import OpenAI

# Настройка логирования — теперь без хранения сообщений
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# === НАСТРОЙКИ ===
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')

# Контакты компании
COMPANY_NAME = "Теплые Окна"
COMPANY_PHONE = "+7 (953) 816-06-98"
COMPANY_ADDRESS = "г. Орел, ул. Приборостроительная, д. 13, этаж 2, офис 20"
COMPANY_WEBSITE = "https://teplydom-orel.ru"
COMPANY_VK = "https://vk.com/teplye_okna57"

# === ИНИЦИАЛИЗАЦИЯ DEEPSEEK ===
deepseek_client = None
if DEEPSEEK_API_KEY:
    deepseek_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    logger.info("DeepSeek клиент успешно инициализирован")
else:
    logger.error("DEEPSEEK_API_KEY не задан! Бот будет работать только в режиме контактов.")

# === ФУНКЦИИ ОТПРАВКИ ===
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

# === ФУНКЦИЯ ДЛЯ УДАЛЕНИЯ НОМЕРА ИЗ ЛОГА ===
def mask_phone_number(text):
    """Заменяет номер телефона в тексте на [НОМЕР УДАЛЁН] для логов"""
    phone_pattern = r'(\+7|8)?[\s\-]?\(?[0-9]{3}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}'
    return re.sub(phone_pattern, '[НОМЕР УДАЛЁН]', text)

# === ВЕБХУК ===
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({'status': 'ok'}), 200

    chat_id = data['message']['chat']['id']
    user_text = data['message'].get('text', '')
    
    # Логируем только ID пользователя и факт сообщения (без текста и номера)
    logger.info(f"Получено сообщение от пользователя {chat_id}, длина: {len(user_text)} символов")

    if user_text.startswith('/'):
        return jsonify({'status': 'ok'}), 200

    send_action(chat_id)

    low = user_text.lower()
    
    # === ЯВНЫЕ ЗАПРОСЫ КОНТАКТОВ ===
    contact_keywords = ['телефон', 'позвонить', 'связаться', 'контакт', 'адрес', 'сайт', 'вк', 'вконтакте', 'график', 'режим работы']
    
    if any(word in low for word in contact_keywords):
        reply = get_contact_info()
    
    # === ЗАЯВКА НА ЗАМЕР ===
    elif 'замер' in low or 'заявк' in low:
        reply = "📐 Для вызова замерщика оставьте, пожалуйста, ваш номер телефона.\n\n⚠️ Отправляя номер, вы соглашаетесь на обработку персональных данных для связи с вами."
    
    # === ОТПРАВКА НОМЕРА ТЕЛЕФОНА ===
    elif any(char.isdigit() for char in user_text) and len(user_text) > 9:
        # Логируем факт получения номера, но сам номер не сохраняем
        logger.info(f"Пользователь {chat_id} отправил номер телефона (данные не сохранены)")
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
                        {"role": "system", "content": f"""
Ты — консультант по пластиковым окнам в компании "{COMPANY_NAME}".

Вот наши цены (за 1 м²):

=== ТОЛЬКО ПРОФИЛЬ (без установки) ===
- РЕХАУ BLITZ: 10 000 ₽/м²
- REHAU Delight: 11 500 ₽/м²
- KBE Engine: 10 000 ₽/м²
- KBE Expert 70: 11 200 ₽/м²
- Veka Euroline 58: 10 300 ₽/м²
- VEKA Softline 70: 11 500 ₽/м²
- HAGEL 58: 9 100 ₽/м²
- HAGEL 70: 10 000 ₽/м²
- KÖMMERLING 76: 12 000 ₽/м²

=== ОКНО ПОД КЛЮЧ (доставка + демонтаж + установка + подоконник + отлив + откосы) ===
Цена за окно размером 1.3м x 1.4м (примерно):

- РЕХАУ BLITZ: 26 000 ₽
- REHAU Delight: 30 000 ₽
- KBE Engine: 25 500 ₽
- KBE Expert 70: 30 000 ₽
- Veka Euroline 58: 27 000 ₽
- VEKA Softline 70: 34 000 ₽
- HAGEL 58: 24 500 ₽
- HAGEL 70: 26 000 ₽
- KÖMMERLING 76: 34 000 ₽

*Для других размеров цена пересчитывается индивидуально. Нужен замер.

Правила:
- Отвечай кратко, по делу, на русском языке.
- НИКОГДА не спрашивай телефон клиента.
- Контакты компании не давай — их обрабатывает отдельный блок.
- Если клиент спрашивает цену — называй конкретные цифры из списка выше.
- Если клиент спрашивает «под ключ» — называй цену из раздела «Окно под ключ».
- Если клиент спрашивает про балконы, установку, характеристики — отвечай как эксперт.
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

    send_message(chat_id, reply)
    return jsonify({'status': 'ok'}), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
