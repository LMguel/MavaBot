# whatsapp/server.py
import os
import sys
from collections import deque

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv

load_dotenv()

from whatsapp.config import (
    VERIFY_TOKEN,
    ACCESS_TOKEN,
    PHONE_NUMBER_ID,
    GRAPH_API_VERSION,
    MAX_REPLY_CHARS,
)
from whatsapp.meta_client import send_text
from mavai_core import criar_recursos, responder

app = FastAPI(title="MavAI WhatsApp Webhook")

_db, _chain, _llm_conversa = criar_recursos()
_ids_processados: deque[str] = deque(maxlen=500)


@app.get("/webhook")
async def verificar_webhook(request: Request):
    params = request.query_params
    mode      = params.get("hub.mode")
    token     = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN and challenge:
        return PlainTextResponse(challenge, status_code=200)
    return Response(status_code=403)


@app.post("/webhook")
async def receber_mensagem(request: Request):
    data = await request.json()
    print("📨 PAYLOAD:", data)

    for entry in data.get("entry", []):
        for ch in entry.get("changes", []):
            value = ch.get("value") or {}

            for msg in value.get("messages") or []:
                msg_id = msg.get("id")
                if msg_id in _ids_processados:
                    print("⚠️ Duplicado, pulando")
                    continue
                _ids_processados.append(msg_id)

                from_wa = msg.get("from")
                if not from_wa:
                    continue

                if msg.get("type") != "text":
                    send_text(from_wa, "No momento só entendo mensagens de texto. 😊")
                    continue

                texto = (msg.get("text") or {}).get("body", "").strip()
                if not texto:
                    continue

                print(f"📝 [{from_wa}]: {texto}")
                print("🤖 Chamando responder()...")

                try:
                    resposta = responder(
                        user_id=from_wa,
                        pergunta=texto,
                        db=_db,
                        chain=_chain,
                        llm_conversa=_llm_conversa,
                    )
                    print(f"✅ Resposta: {resposta[:120]}")
                except Exception as e:
                    print(f"❌ ERRO responder(): {type(e).__name__}: {e}")
                    raise

                if len(resposta) > MAX_REPLY_CHARS:
                    resposta = resposta[:MAX_REPLY_CHARS].rstrip() + "…"

                try:
                    send_text(from_wa, resposta)
                    print("📤 Enviado!")
                except Exception as e:
                    print(f"❌ ERRO send_text(): {type(e).__name__}: {e}")
                    raise

    return Response(status_code=200)
