import os
import logging
from flask import Flask, request, jsonify
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# ⚠️ ВАЖНО: Укажите ваш личный CHAT_ID (получите у @userinfobot)
ADMIN_CHAT_ID = "628935507"

# Хранилище временных данных пользователей (в реальном проекте лучше использовать базу данных)
user_data = {}

def send_message(chat_id, text, reply_markup=None):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
    if reply_markup:
        payload['reply_markup'] = reply_markup
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"Failed to send: {e}")

def get_main_keyboard():
    return {
        "keyboard": [
            [{"text": "📋 Цены"}],
            [{"text": "📞 Контакты"}, {"text": "📝 Заказать замер"}],
            [{"text": "❓ Помощь"}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }

def get_cancel_keyboard():
    return {
        "keyboard": [[{"text": "❌ Отмена"}]],
        "resize_keyboard": True,
        "one_time_keyboard": True
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
            send_message(chat_id, "📋 Нажмите на кнопки под полем ввода.", reply_markup=get_main_keyboard())
        elif text == '/price' or text == '📋 Цены':
            send_message(chat_id, "💰 <b>Цены на окна под ключ:</b>\n\nRehau (5 камер) — от 12 000 ₽/м²\nKBE (5 камер) — от 11 500 ₽/м²\nVEKA (5 камер) — от 13 000 ₽/м²\n\nБесплатный замер. Гарантия 5 лет.\nДля точного расчёта напишите размеры окна.", reply_markup=get_main_keyboard())
        elif text == '📞 Контакты':
            send_message(chat_id, "📞 <b>Свяжитесь с нами:</b>\n\nТелефон: +7 (900) 123-45-67\nEmail: okna@teplye-okna.ru\n\nИли напишите нам сюда — мы ответим!", reply_markup=get_main_keyboard())
        elif text == '📝 Заказать замер':
            user_data[chat_id] = {'step': 'name'}
            send_message(chat_id, "📝 Давайте оформим заявку на замер.\n\nКак вас зовут?", reply_markup=get_cancel_keyboard())
        elif text == '❌ Отмена':
            if chat_id in user_data:
                del user_data[chat_id]
            send_message(chat_id, "❌ Заявка отменена. Вы можете продолжить пользоваться ботом.", reply_markup=get_main_keyboard())
        else:
            # Обработка ответов на вопросы заявки
            if chat_id in user_data:
                step = user_data[chat_id]['step']
                
                if step == 'name':
                    user_data[chat_id]['name'] = text
                    user_data[chat_id]['step'] = 'phone'
                    send_message(chat_id, "📞 Укажите ваш номер телефона (можно мобильный).")
                elif step == 'phone':
                    user_data[chat_id]['phone'] = text
                    user_data[chat_id]['step'] = 'windows'
                    send_message(chat_id, "🪟 Какой размер окна? (пример: 1500×1200 мм)")
                elif step == 'windows':
                    user_data[chat_id]['windows'] = text
                    user_data[chat_id]['step'] = 'date'
                    send_message(chat_id, "📅 Когда вам удобно приехать на замер? (укажите дату и время)")
                elif step == 'date':
                    user_data[chat_id]['date'] = text
                    
                    # Формируем заявку для отправки админу
                    order = f"🆕 <b>НОВАЯ ЗАЯВКА НА ЗАМЕР</b>\n\n"
                    order += f"👤 Имя: {user_data[chat_id]['name']}\n"
                    order += f"📞 Телефон: {user_data[chat_id]['phone']}\n"
                    order += f"🪟 Размеры окон: {user_data[chat_id]['windows']}\n"
                    order += f"📅 Желаемая дата/время: {user_data[chat_id]['date']}"
                    
                    # Отправляем заявку админу
                    send_message(ADMIN_CHAT_ID, order)
                    
                    # Сообщаем клиенту об успехе
                    send_message(chat_id, "✅ <b>Спасибо за заявку!</b>\n\nМы свяжемся с вами в ближайшее время для подтверждения замера.", reply_markup=get_main_keyboard())
                    
                    # Очищаем данные пользователя
                    del user_data[chat_id]
            else:
                send_message(chat_id, "❓ Я понимаю только команды. Нажмите на кнопку /start или ❓ Помощь.", reply_markup=get_main_keyboard())
    
    return jsonify({'status': 'ok'}), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
