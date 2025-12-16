import os
import redis
import json
import time
import requests
import smtplib, ssl
from email.message import EmailMessage

REDIS_HOST = os.getenv("REDIS_HOST", "redis-service")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
CHANNEL = "auction:ended"

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

def send_discord_webhook_message(webhook_url, message_content):
    """
    Sends a message to a Discord channel using a webhook.
    """
    data = {
        "content": message_content
    }
    
    response = requests.post(webhook_url, json=data)
    
    if response.status_code == 204:
        print("Message sent successfully via webhook.")
    else:
        print(f"Failed to send message. Status code: {response.status_code}, Response: {response.text}")

def anunciar_vencedor_discord(nome, produto, preco):
    msg = f"Parabéns, {nome}, por adquirir o produto {produto} por R${preco}"
    send_discord_webhook_message(DISCORD_WEBHOOK_URL, msg)

def anunciar_vencedor_email(receiver_email, produto, preco):
    msg = EmailMessage()
    msg["From"] = SMTP_EMAIL
    msg["To"] = receiver_email
    msg["Subject"] = "🎉 Você venceu o leilão!"
    
    msg.set_content(
        f"""
Parabéns!

Você adquiriu o produto {produto} por R$ {preco}.

Acesse o link para pagamento:
https://algum-link.com
"""
    )

    context = ssl._create_unverified_context()
    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
            print("Email enviado com sucesso!")
    except Exception as e:
        print("Erro ao enviar email:", e)

def main():
    # Conecta no redis
    r = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        decode_responses=True
    )

    # Se inscreve no canal (de leiloes finalizados)
    pubsub = r.pubsub()
    pubsub.subscribe(CHANNEL)

    print("Agente aguardando leilões encerrados...")

    for message in pubsub.listen():
        if message["type"] != "message":
            continue

        data = json.loads(message["data"])

        print("Evento recebido:", data)

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

        print("Notificações enviadas")

if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            print("Erro:", e)
            time.sleep(5)
