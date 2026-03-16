import requests
from .config import ACCESS_TOKEN, PHONE_NUMBER_ID, GRAPH_API_VERSION

GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

def send_text(to_phone_e164_or_waid: str, text: str) -> dict:
    """
    Envia mensagem de texto pelo WhatsApp Cloud API.
    Endpoint: /<PHONE_NUMBER_ID>/messages. [web:120]
    """
    url = f"{GRAPH_BASE}/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone_e164_or_waid,
        "type": "text",
        "text": {"body": text},
    }
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()
