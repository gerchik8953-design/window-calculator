import os
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)
TOKEN = os.environ.get('TELEGRAM_TOKEN')

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({'status': 'ok'}), 200

    chat_id = data['message']['chat']['id']
    text = data['message'].get('text', '').lower()
    
    if 'телефон' in text:
        reply = "Телефон: +7 (953) 816-06-98"
    elif 'вк' in text or 'вконтакте' in text:
        reply = "ВК: https://vk.com/teplye_okna57"
    else:
        reply = f"Вы написали: {text}"
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={'chat_id': chat_id, 'text': reply})
    
    return jsonify({'status': 'ok'}), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'}), 200

# ВАЖНО: Render ожидает порт из переменной PORT
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
