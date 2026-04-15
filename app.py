import os
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# === КОНФИГУРАЦИЯ ===
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
COMPANY_PHONE = "+7 (953) 816-06-98"
COMPANY_VK = "https://vk.com/teplye_okna57"

# === ФУНКЦИЯ ОТПРАВКИ СООБЩЕНИЙ ===
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={'chat_id': chat_id, 'text': text}, timeout=10)
    except Exception as e:
        print(f"Ошибка отправки: {e}")

# === ВЕБХУК ===
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({'status': 'ok'}), 200

    chat_id = data['message']['chat']['id']
    text = data['message'].get('text', '').lower()

    # Жёсткая проверка на ключевые слова
    if 'телефон' in text or 'номер' in text or 'позвонить' in text:
        reply = f"📞 Наш телефон для связи: {COMPANY_PHONE}"
    elif 'вк' in text or 'вконтакте' in text or 'группа' in text:
        reply = f"🌐 Наша группа ВКонтакте: {COMPANY_VK}"
    else:
        # Ответ по умолчанию, если запрос не про контакты
        reply = f"Вы написали: {text}. Если хотите узнать наши контакты, напишите 'телефон' или 'вк'."

    send_message(chat_id, reply)
    return jsonify({'status': 'ok'}), 200

# === ПРОВЕРКА ЗДОРОВЬЯ ===
@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'}), 200

# === ЗАПУСК С ПРАВИЛЬНЫМ ПОРТОМ ===
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
