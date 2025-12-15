import redis
import json
import time
import requests
import smtplib, ssl

# =====================
# CONFIG
# =====================
REDIS_HOST = "redis-service"
REDIS_PORT = 6379
CHANNEL = "auction:ended"

WEBHOOK_URL = "https://discord.com/api/webhooks/1450235254005698680/CYiOtXuE8la3PMgitGsm_cdVbaPRhwlxklrlpW7Me9V5puo15QqeEqW8nJdSLU6Y7nGj"

smtp_server = "smtp.gmail.com"
port = 465
sender_email = "<email>"
password = "<senha>"

# =====================
# NOTIFICAÇÕES
# =====================
def send_discord_webhook_message(webhook_url, message_content):
    """
    Sends a message to a Discord channel using a webhook.
    """
    data = {
        "content": message_content
    }
    
    # Post the data to the webhook URL
    response = requests.post(webhook_url, json=data)
    
    if response.status_code == 204: # Discord returns 204 No Content on success
        print("Message sent successfully via webhook.")
    else:
        print(f"Failed to send message. Status code: {response.status_code}, Response: {response.text}")

#tool 1
def anunciar_vencedor_discord(nome, produto, preco):
    msg = f"Parabéns, {nome}, por adquirir o produto {produto} por R${preco}"
    send_discord_webhook_message(WEBHOOK_URL, msg)

#tool 2
def anunciar_vencedor_email(receiver_email, produto, preco):

    message = f"""\
    Subject: Leilão

    Parabéns por adquirir o produto {produto} por R$ {preco}.
    Siga o link para entrar no pagamento: <algum-link.com>
    """

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message)


# =====================
# REDIS WORKER
# =====================
def main():
    r = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        decode_responses=True
    )

    pubsub = r.pubsub()
    pubsub.subscribe(CHANNEL)

    print("🟢 Agente aguardando leilões encerrados...")

    for message in pubsub.listen():
        if message["type"] != "message":
            continue

        data = json.loads(message["data"])

        print("📩 Evento recebido:", data)

        anunciar_vencedor_discord(
            data["vencedor"],
            data["produto"],
            data["preco"]
        )

        anunciar_vencedor_email(
            data["email"],
            data["produto"],
            data["preco"]
        )

        print("✅ Notificações enviadas")

if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            print("Erro:", e)
            time.sleep(5)
