from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import google_search
from google.genai import types
import asyncio
import requests
import json
import smtplib, ssl

# Tem que pegar o webhook de algum canal do discord, esse daqui é de um servidor privado meu
# Replace "YOUR_WEBHOOK_URL" with the URL you copied from Discord
WEBHOOK_URL = "https://discord.com/api/webhooks/1449803067145846996/K-BBorAKZDgKuJ60OIjOGDWaKtQgAEUZTeXrtdE8e175BHj887cP9DD1x0DnTHMgbQ83"

# mandar e-mails
port = 465  # For starttls
smtp_server = "smtp.gmail.com"

#Coloque algum e-mail e senha aqui
sender_email = "<e-mail>"
password = "<senha>"

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

# CONFIGURATION
APP_NAME = "simple_search_agent"
USER_ID = "user_default"
SESSION_ID = "session_01"

# AGENT DEFINITION
root_agent = Agent(
    name="search_agent",
    model="gemini-3-pro-preview",
    description="A helpful assistant that can search Google.",
    instruction="""
    You are a helpful assistant with access to Google Search.
    
    If the user asks a question that requires current information or facts, use the 'google_search' tool.
    Always cite your sources implicitly by providing the answer clearly based on the search results.
    """,
    # This is the only tool enabled
    tools=[anunciar_vencedor_discord, anunciar_vencedor_email]
)

# Session and Runner
async def setup_session_and_runner():
    session_service = InMemorySessionService()
    session = await session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
    runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)
    return session, runner

# Agent Interaction
async def call_agent_async(query):
    content = types.Content(role='user', parts=[types.Part(text=query)])
    session, runner = await setup_session_and_runner()
    events = runner.run_async(user_id=USER_ID, session_id=SESSION_ID, new_message=content)

    async for event in events:
        if event.is_final_response():
            final_response = event.content.parts[0].text
            print("Agent Response: ", final_response)

def run_agent(prompt):
    asyncio.run(call_agent_async(prompt))