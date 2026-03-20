# whatsapp/server.py
"""
Webhook FastAPI — MavAI ↔ WhatsApp Cloud API (Meta)

Garantias:
- load_dotenv() antes de qualquer import de config
- POST /webhook NUNCA retorna 500
- Deduplicação de mensagens via deque
"""

import os
import sys
from collections import deque

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse

from whatsapp.config import VERIFY_TOKEN, MAX_REPLY_CHARS
from whatsapp.evolution_client import send_text
from mavai_core import criar_recursos, responder

# ── App e recursos ────────────────────────────────────────────────────────────
app = FastAPI(title="MavAI WhatsApp Webhook")

_db, _chain, _llm_conversa, _llm_intent = criar_recursos()
_ids_processados: deque[str] = deque(maxlen=500)

# Mapeamento de prefixos de número → região (personalize conforme sua área)
_REGIOES = {
    "101": "Capital / Grande Rio",
    "102": "Capital / Grande Rio",
    "103": "Litoral Norte",
    "104": "Litoral Norte",
    "108": "Interior Sul / Serrana",
}


# ── GET /webhook — verificação Meta ───────────────────────────────────────────
@app.get("/webhook")
async def verificar_webhook(request: Request):
    params    = request.query_params
    token     = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    if token == VERIFY_TOKEN and challenge:
        return PlainTextResponse(challenge, status_code=200)
    return Response(status_code=403)


# ── POST /webhook — recebimento de mensagens ──────────────────────────────────
@app.post("/webhook")
async def receber_mensagem(request: Request):
    try:
        data = await request.json()
    except Exception as exc:
        print(f"❌ [webhook] Erro ao ler JSON: {exc}")
        return Response(status_code=200)

    print("📨 [webhook] Payload:", data)

    try:
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value") or {}
                for message in value.get("messages", []):
                    await _processar_mensagem(message)
    except Exception as exc:
        print(f"❌ [webhook] Erro no loop de eventos: {type(exc).__name__}: {exc}")

    return Response(status_code=200)


# ── Processamento individual ──────────────────────────────────────────────────
async def _processar_mensagem(message: dict) -> None:
    # Deduplicação
    msg_id = message.get("id")
    if msg_id:
        if msg_id in _ids_processados:
            print(f"⚠️ [webhook] Duplicada ignorada: {msg_id}")
            return
        _ids_processados.append(msg_id)

    # Remetente
    from_wa = (message.get("from") or "").strip()
    if not from_wa:
        print("⚠️ [webhook] Sem campo 'from', ignorando.")
        return

    # Tipo de mensagem
    msg_type = message.get("type")
    if msg_type != "text":
        await send_text(from_wa, "No momento só entendo mensagens de texto 😊")
        return

    # Texto
    texto = ((message.get("text") or {}).get("body") or "").strip()
    if not texto:
        return

    print(f"📝 [{from_wa}]: {texto}")

    # Contexto de região pelo prefixo do número
    prefixo      = from_wa[-10:][:3]
    regiao_nome  = _REGIOES.get(prefixo, "")
    contexto_extra = f"Sou da região {regiao_nome}. " if regiao_nome else ""

    # Gera resposta
    try:
        resposta = responder(
            user_id        = from_wa,
            pergunta       = texto,
            db             = _db,
            chain          = _chain,
            llm_conversa   = _llm_conversa,
            llm_intent     = _llm_intent,
            contexto_extra = contexto_extra,
            canal          = "whatsapp",
        )
    except Exception as exc:
        print(f"❌ [webhook] Erro em responder(): {type(exc).__name__}: {exc}")
        await send_text(from_wa, "Desculpe, ocorreu um erro. Tente novamente em instantes.")
        return

    # Trunca se necessário (segurança extra além do core)
    if len(resposta) > MAX_REPLY_CHARS:
        resposta = resposta[:MAX_REPLY_CHARS].rstrip() + "…"

    # Envia
    resultado = await send_text(from_wa, resposta)
    if resultado.get("error"):
        print(f"❌ [webhook] Falha ao enviar: {resultado}")
    else:
        id_msg = resultado.get("messages", [{}])[0].get("id", "?")
        print(f"📤 [webhook] Enviado com sucesso! ID: {id_msg}")