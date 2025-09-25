from django.shortcuts import render



from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json, requests, re, time

# ===================== CONFIG ===================== #
VERIFY_TOKEN     = "minha_senha_webhook"
PHONE_NUMBER_ID  = "775519838983089"
WHATSAPP_TOKEN   = "EAASlWDvlPEoBPrEF4a2ZBnHT3IbdttKYDi9mACo3EvWsz5whvGlg2gW0juLh3uG1DTZBdiFGviWKrCvv9HEdi1vZAeCi7b51gtoObBxZB8qLZCneWEZAl7aZA21mUfhNWcAXXTNdBrwZBfemiGlhMzr8smqiWShY3tMbSEEPokLsArvCbALYAK7dFxxfVu1B1KeVHZBspMOToMTCfkTxb4XhtXkGhqkv2k8AYBoEgvwV4ESO1lwZDZD"  # cole seu token válido
AGENT_NUMBER     = "5515996862293"  # ex: "5512999999999" (onde o "humano" recebe alerta)
BUSINESS_NAME    = "Minha Empresa"
# ================================================== #

# Estado em memória: { wa_id: {"state": "root"|"support"|"human", "updated_at": ts} }
SESSIONS = {}

def _now(): return int(time.time())

def get_state(wa_id):
    s = SESSIONS.get(wa_id, {})
    return s.get("state", "root")

def set_state(wa_id, state):
    SESSIONS[wa_id] = {"state": state, "updated_at": _now()}

def normalize(txt):
    txt = (txt or "").strip().lower()
    # tira acentos simples e espaços extras
    repl = {
        "á":"a","ã":"a","â":"a","à":"a",
        "é":"e","ê":"e",
        "í":"i",
        "ó":"o","ô":"o","õ":"o",
        "ú":"u","ü":"u",
        "ç":"c"
    }
    for k,v in repl.items():
        txt = txt.replace(k,v)
    return re.sub(r"\s+", " ", txt)

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

def send_menu_root(to):
    msg = (
        f"👋 Olá! Você está falando com o *{BUSINESS_NAME}*.\n"
        "Escolha uma opção:\n"
        "1️⃣ Falar com atendente humano\n"
        "2️⃣ Suporte técnico\n"
        "9️⃣ Encerrar/voltar ao início"
    )
    send_text(to, msg)

def send_menu_support(to):
    msg = (
        "🛠️ *Suporte técnico*\n"
        "1️⃣ Status do pedido\n"
        "2️⃣ 2ª via de boleto\n"
        "9️⃣ Voltar ao menu inicial"
    )
    send_text(to, msg)

def _to_e164_digits(num: str) -> str:
    # mantém só dígitos
    return "".join(ch for ch in (num or "") if ch.isdigit())

def transfer_to_human(customer_wa, last_text):
    set_state(customer_wa, "human")
    send_text(customer_wa, "✅ Vou te transferir para um atendente humano. Aguarde, por favor.")

    # alerta para o atendente
    agent = _to_e164_digits(AGENT_NUMBER)
    if not agent:
        print("⚠️ AGENT_NUMBER não configurado. Defina um número E.164, ex: 5512999999999")
        return

    alert = (
        f"📞 *Novo atendimento*\n"
        f"Cliente: {customer_wa}\n"
        f"Mensagem: {last_text or '(vazia)'}\n"
        f"Acesse o painel/rota de atendimento para assumir."
    )
    send_text(agent, alert)

@csrf_exempt
def webhook(request):
    # ======= VERIFICAÇÃO (GET) ======= #
    if request.method == "GET":
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")
        if mode == "subscribe" and token == VERIFY_TOKEN and challenge:
            return HttpResponse(challenge, content_type="text/plain")
        return HttpResponse("forbidden", status=403)

    # ======= EVENTOS (POST) ======= #
    if request.method == "POST":
        data = json.loads(request.body.decode("utf-8") or "{}")
        print("📩 Webhook recebido:", json.dumps(data, indent=2, ensure_ascii=False))

        try:
            value = data["entry"][0]["changes"][0]["value"]
            messages = value.get("messages")
            if not messages:
                return HttpResponse("ok")  # status/delivery etc.

            msg = messages[0]
            wa_id = msg.get("from")  # número do cliente
            text = msg.get("text", {}).get("body", "")
            text_norm = normalize(text)

            # Recupera estado do cliente
            state = get_state(wa_id)

            # Se sessão está em 'human', não responde automático
            if state == "human":
                # opcional: se cliente mandar "menu" volta para bot
                if text_norm in ("menu", "0", "reiniciar", "voltar"):
                    set_state(wa_id, "root")
                    send_text(wa_id, "🔁 Voltando ao menu inicial.")
                    send_menu_root(wa_id)
                # senão, silencia para não competir com o humano
                return HttpResponse("ok")

            # ===== LÓGICA DO MENU ===== #
            if state == "root":
                if text_norm in ("1", "humano", "atendente", "falar com humano"):
                    transfer_to_human(wa_id, text)
                elif text_norm in ("2", "suporte", "suporte tecnico"):
                    set_state(wa_id, "support")
                    send_menu_support(wa_id)
                elif text_norm in ("9", "sair", "encerrar", "voltar"):
                    send_text(wa_id, "👋 Atendimento encerrado. Quando precisar, mande *menu* para recomeçar.")
                else:
                    # qualquer outra coisa → mostra o menu
                    send_menu_root(wa_id)

            elif state == "support":
                if text_norm in ("1", "status", "status do pedido"):
                    send_text(wa_id, "🧾 Seu pedido está *em separação* e será enviado em até 24h.")
                    send_menu_support(wa_id)
                elif text_norm in ("2", "boleto", "2 via", "2a via", "segunda via"):
                    send_text(wa_id, "📄 Enviamos a 2ª via do boleto para seu e-mail cadastrado.")
                    send_menu_support(wa_id)
                elif text_norm in ("9", "voltar", "menu"):
                    set_state(wa_id, "root")
                    send_menu_root(wa_id)
                elif text_norm in ("1️⃣","2️⃣","9️⃣"):
                    # emojis de teclado numérico viram 1/2/9
                    mapping = {"1️⃣":"1","2️⃣":"2","9️⃣":"9"}
                    mapped = mapping.get(text_norm)
                    request.POST = request.POST  # no-op só pra manter estrutura
                    # reprocessa como se tivesse digitado numérico
                    if mapped == "1":
                        send_text(wa_id, "🧾 Seu pedido está *em separação* e será enviado em até 24h.")
                        send_menu_support(wa_id)
                    elif mapped == "2":
                        send_text(wa_id, "📄 Enviamos a 2ª via do boleto para seu e-mail cadastrado.")
                        send_menu_support(wa_id)
                    else:
                        set_state(wa_id, "root")
                        send_menu_root(wa_id)
                else:
                    send_text(wa_id, "❓ Não entendi. Responda *1*, *2* ou *9*.")
                    send_menu_support(wa_id)

        except Exception as e:
            # loga mas nunca quebra a entrega
            print("Erro:", e)

        return HttpResponse("ok")

    return HttpResponse("method not allowed", status=405)
