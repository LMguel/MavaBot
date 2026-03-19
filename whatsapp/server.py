# whatsapp/server.py
"""
Webhook FastAPI para integração MavAI ↔ WhatsApp Cloud API (Meta).

Garante que:
- load_dotenv() é chamado ANTES de qualquer import de config.py
- O endpoint POST /webhook NUNCA retorna 500 (erros são logados e absorvidos)
- Mensagens duplicadas são ignoradas via deque de IDs processados
"""

import os
import sys
from collections import deque

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# ── load_dotenv DEVE vir antes de qualquer import do config ──────────────────
from dotenv import load_dotenv

load_dotenv()  # Carrega o .env da raiz do projeto

# ── Imports do projeto (após load_dotenv) ────────────────────────────────────
from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse

from whatsapp.config import (
    VERIFY_TOKEN,
    MAX_REPLY_CHARS,
)
from whatsapp.evolution_client import send_text
from mavai_core import criar_recursos, responder

# ── App e estado ─────────────────────────────────────────────────────────────
app = FastAPI(title="MavAI WhatsApp Webhook")

_db, _chain, _llm_conversa, _llm_intent = criar_recursos()
_ids_processados: deque[str] = deque(maxlen=500)


# ── GET /webhook — verificação do webhook pela Meta ───────────────────────────
@app.get("/webhook")
async def verificar_webhook(request: Request):
    params = request.query_params
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if token == VERIFY_TOKEN and challenge:
        return PlainTextResponse(challenge, status_code=200)
    return Response(status_code=403)


# ── POST /webhook — recebimento e resposta de mensagens ───────────────────────
@app.post("/webhook")
async def receber_mensagem(request: Request):
    """
    Processa eventos enviados pela Meta.
    NUNCA retorna 500 — erros são logados e absorvidos.
    Retornar 200 evita retentativas infinitas da Meta.
    """

    # ── Leitura do payload ────────────────────────────────────────────────────
    try:
        data = await request.json()
    except Exception as exc:
        print(f"❌ [webhook] Erro ao ler JSON do request: {exc}")
        return Response(status_code=200)  # Retorna 200 mesmo assim

    print("📨 [webhook] Payload recebido:", data)

    # ── Iteração sobre eventos ────────────────────────────────────────────────
    try:
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value") or {}

                for message in value.get("messages", []):
                    await _processar_mensagem(message)

    except Exception as exc:
        # Captura qualquer erro inesperado no loop, loga e retorna 200
        print(f"❌ [webhook] Erro inesperado no loop de eventos: {type(exc).__name__}: {exc}")

    return Response(status_code=200)


# ── Lógica de processamento de uma mensagem individual ────────────────────────
async def _processar_mensagem(message: dict) -> None:
    """
    Processa uma única mensagem recebida.
    Absorve todos os erros internamente — não propaga exceções.
    """

    # Deduplicação
    msg_id = message.get("id")
    if msg_id:
        if msg_id in _ids_processados:
            print(f"⚠️ [webhook] Mensagem duplicada ignorada: {msg_id}")
            return
        _ids_processados.append(msg_id)

    # Remetente
    from_wa = (message.get("from") or "").strip()
    if not from_wa:
        print("⚠️ [webhook] Mensagem sem campo 'from', ignorando.")
        return

    # Tipo de mensagem
    msg_type = message.get("type")
    if msg_type != "text":
        print(f"⚠️ [webhook] Tipo de mensagem não suportado: '{msg_type}'. Avisando remetente.")
        await send_text(from_wa, "No momento só entendo mensagens de texto 😊")
        return

    # Conteúdo do texto
    texto = ((message.get("text") or {}).get("body") or "").strip()
    if not texto:
        print("⚠️ [webhook] Mensagem de texto vazia, ignorando.")
        return

    print(f"📝 [webhook] [{from_wa}]: {texto}")

    # Contexto regional por número
    regioes = {
        "101": "Capital",
        "102": "Capital",
        "103": "Litoral N",
        "104": "Litoral N",
    }
    numero_wa = from_wa[-10:]
    contexto_extra = (
        f"Sou da região {regioes[numero_wa]}. " if numero_wa in regioes else ""
    )

    # ── Gera resposta via LLM ─────────────────────────────────────────────────
    try:
        print("🤖 [webhook] Chamando responder()...")
        resposta = responder(
            user_id=from_wa,
            pergunta=texto,
            db=_db,
            chain=_chain,
            llm_conversa=_llm_conversa,
            llm_intent=_llm_intent,
            contexto_extra=contexto_extra,
        )
        print(f"✅ [webhook] Resposta gerada: {resposta[:120]}")
    except Exception as exc:
        print(f"❌ [webhook] Erro em responder(): {type(exc).__name__}: {exc}")
        await send_text(from_wa, "Desculpe, ocorreu um erro ao processar sua mensagem. Tente novamente.")
        return

    # Trunca se necessário
    if len(resposta) > MAX_REPLY_CHARS:
        resposta = resposta[:MAX_REPLY_CHARS].rstrip() + "…"

    # ── Envia resposta ────────────────────────────────────────────────────────
    resultado = await send_text(from_wa, resposta)
    if resultado.get("error"):
        print(f"❌ [webhook] Falha ao enviar mensagem (absorvida): {resultado}")
    else:
        print(f"📤 [webhook] Mensagem enviada com sucesso! ID: {resultado.get('messages', [{}])[0].get('id', '?')}")
