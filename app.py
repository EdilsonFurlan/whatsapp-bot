from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# coloque seus dados
PHONE_NUMBER_ID = "775519838983089"  # seu Phone Number ID
WHATSAPP_TOKEN  = "EAASlWDvlPEoBPnFc9hKwctRKzxugHHUDzpKni5R41jpR1ZBFzpYSvp3dRHygHw249xf1kJLc0l6fQOHSaKWGhrPWm4VEp0Y2rUDAH9VFuxIdt97clZAnDRzZCVR7WKC1eHmXW1zbWlpboz09sWPkNlhPaqhXZBkGGekzEHSmEQcKe3G2MslvuZAdsUZCVDPGOWYoGu4MxTfZCaQK7gai4nu38WHttrZBX5u85slBzVM66sjDdQZDZD"
VERIFY_TOKEN    = "minha_senha_webhook"

# verificação do webhook (GET)
@app.get("/webhook")
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "forbidden", 403

# recebimento de mensagens (POST)
@app.post("/webhook")
def webhook():
    data = request.get_json()
    print("Webhook recebido:", data)

    # se veio mensagem, responde
    try:
        msg = data["entry"][0]["changes"][0]["value"]["messages"][0]
        from_number = msg["from"]  # número de quem mandou
        send_text(from_number, "Oi! Recebi sua mensagem ✅")
    except Exception as e:
        print("sem mensagem de texto:", e)

    return "ok", 200

def send_text(to, body):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body}
    }
    r = requests.post(url, headers=headers, json=payload)
    print("resposta:", r.status_code, r.text)

if __name__ == "__main__":
    app.run(port=3000, debug=True)
