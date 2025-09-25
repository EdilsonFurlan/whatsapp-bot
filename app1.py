from flask import Flask, request
import requests

app = Flask(__name__)

# 📌 Configurações
PHONE_NUMBER_ID = "775519838983089"  # seu Phone Number ID
WHATSAPP_TOKEN = "EAASlWDvlPEoBPm56Di8rOkRR0oJLu5KNUFXfzJfOoUo4xtB1woZCTHwpTTSAZCmKf50TJh8u8XBCLwKrRo4su5WSUebM9Ke3ZBc0fwNlQuu6N5ZByKrpvXJEqzAYQns9YVmpQLZAgXcROd7XBV3ERZB08MB7OgVun8ZCHSRdxSle0ZCfg9ubOJRdABnpFHi7MpzDUAYHbOCsZByiZCZCrp4tPTXqmoYyj3bnFPh71BYMYrg5g2PmAZDZD"
VERIFY_TOKEN = "minha_senha_webhook"  # tem que bater com o painel

# 📌 Função para enviar mensagem
def send_text(to, body):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }
    r = requests.post(url, headers=headers, json=payload, timeout=15)
    print("send_text:", r.status_code, r.text)

# 📌 Webhook
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if mode == "subscribe" and token == VERIFY_TOKEN and challenge:
            return challenge, 200, {"Content-Type": "text/plain"}
        return "forbidden", 403

    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        print("Webhook recebido:", data)

        try:
            change = data["entry"][0]["changes"][0]["value"]
            msg = (change.get("messages") or [None])[0]
            if msg:
                from_wa = msg.get("from")  # número do cliente
                text_body = msg.get("text", {}).get("body", "")
                resposta = f"Oi, recebi sua mensagem: {text_body}"
                send_text(from_wa, resposta)
        except Exception as e:
            import traceback
            traceback.print_exc()

        return "ok", 200

if __name__ == "__main__":
    app.run(port=3000, debug=True)
