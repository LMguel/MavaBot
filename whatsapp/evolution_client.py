"""
evolution_client.py — Cliente para envio de mensagens via WhatsApp Cloud API (Meta).

Correções aplicadas:
- Sanitização do número 'to': remove +, espaços, hifens, parênteses
- Extração clara do campo error.message da resposta 400 da Meta
- Validação do PHONE_NUMBER_ID e ACCESS_TOKEN antes do envio
- Logs detalhados e organizados para debug com ngrok
- preview_url explicitamente como bool Python (httpx serializa corretamente)
"""

import re
import httpx

from .config import (
    WHATSAPP_ACCESS_TOKEN,
    WHATSAPP_API_VERSION,
    WHATSAPP_PHONE_NUMBER_ID,
)


def _sanitizar_numero(numero: str) -> str:
    """
    Remove qualquer caractere não numérico do número de telefone.
    Ex: '+55 (11) 99999-9999' → '5511999999999'
    A Meta exige apenas dígitos no formato internacional (sem +).
    """
    return re.sub(r"\D", "", numero)


def _extrair_erro_meta(resp_json: dict) -> str:
    """
    Extrai a mensagem de erro estruturada da resposta da API da Meta.
    Formato comum: { "error": { "message": "...", "type": "...", "code": 190 } }
    """
    erro = resp_json.get("error", {})
    if not erro:
        return str(resp_json)

    partes = []
    if erro.get("code"):
        partes.append(f"code={erro['code']}")
    if erro.get("type"):
        partes.append(f"type={erro['type']}")
    if erro.get("message"):
        partes.append(f"message={erro['message']!r}")
    if erro.get("error_subcode"):
        partes.append(f"subcode={erro['error_subcode']}")
    if erro.get("fbtrace_id"):
        partes.append(f"fbtrace_id={erro['fbtrace_id']}")

    return " | ".join(partes) if partes else str(resp_json)


async def send_text(to: str, text: str) -> dict:
    """
    Envia mensagem de texto pela WhatsApp Cloud API (Meta).

    - Sanitiza o número 'to' para garantir formato E.164 sem '+'.
    - Extrai e loga erros da Meta de forma legível.
    - NUNCA propaga exceções — o webhook permanece estável.

    Retorna um dict com a resposta da API, ou com a chave 'error' em caso de falha.
    """

    # ── Sanitização e validação do número ────────────────────────────────────
    to_limpo = _sanitizar_numero(to)
    if len(to_limpo) < 10:
        print(f"❌ [send_text] Número inválido após sanitização: '{to}' → '{to_limpo}'")
        return {"error": True, "detail": f"Número inválido: {to}"}

    # ── Validação das variáveis de ambiente ──────────────────────────────────
    phone_id = WHATSAPP_PHONE_NUMBER_ID.strip()
    token    = WHATSAPP_ACCESS_TOKEN.strip()
    version  = WHATSAPP_API_VERSION.strip()

    if not phone_id or not phone_id.isdigit():
        print(f"❌ [send_text] WHATSAPP_PHONE_NUMBER_ID inválido: '{phone_id}'")
        return {"error": True, "detail": "PHONE_NUMBER_ID inválido"}

    if not token or len(token) < 20:
        print(f"❌ [send_text] WHATSAPP_ACCESS_TOKEN parece inválido (muito curto)")
        return {"error": True, "detail": "ACCESS_TOKEN inválido"}

    # ── Montagem da URL e payload ─────────────────────────────────────────────
    url = f"https://graph.facebook.com/{version}/{phone_id}/messages"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_limpo,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": text,
        },
    }

    # ── Logs de debug pré-envio ───────────────────────────────────────────────
    token_preview = token[:16] + "..." if len(token) > 16 else "????"
    print("─" * 60)
    print(f"📡 [send_text] PHONE_NUMBER_ID : {phone_id}")
    print(f"📡 [send_text] API_VERSION     : {version}")
    print(f"📡 [send_text] URL             : {url}")
    print(f"📡 [send_text] Token (parcial) : {token_preview}")
    print(f"📡 [send_text] Para (original) : {to}")
    print(f"📡 [send_text] Para (limpo)    : {to_limpo}")
    print(f"📡 [send_text] Texto (preview) : {text[:80]}{'...' if len(text) > 80 else ''}")
    print("─" * 60)

    # ── Envio ─────────────────────────────────────────────────────────────────
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(url, headers=headers, json=payload)

        print(f"📡 [send_text] HTTP Status: {r.status_code}")

        # Tenta parsear JSON da resposta
        try:
            resp_json = r.json()
        except ValueError:
            resp_json = {"raw": r.text}

        # Loga a resposta completa
        print(f"📡 [send_text] Resposta completa: {resp_json}")

        # Se for erro, extrai mensagem clara da Meta
        if not r.is_success:
            erro_legivel = _extrair_erro_meta(resp_json)
            print(
                f"❌ [send_text] Erro {r.status_code} da Meta API:\n"
                f"   {erro_legivel}\n"
                f"\n💡 Dicas para erro 400:\n"
                f"   • Verifique se WHATSAPP_ACCESS_TOKEN não está expirado (tokens temporários duram 24h)\n"
                f"   • Verifique se WHATSAPP_PHONE_NUMBER_ID é o ID numérico (não o número)\n"
                f"   • O número destino deve estar no formato E.164 sem '+': {to_limpo}\n"
                f"   • O número destino deve ter aceito mensagens de teste no painel Meta"
            )
            return {
                "error": True,
                "status_code": r.status_code,
                "meta_error": resp_json.get("error", {}),
                "detail": erro_legivel,
            }

        return resp_json

    except httpx.HTTPStatusError as exc:
        # Fallback: raise_for_status foi chamado (não deveria acontecer com a lógica acima)
        print(f"❌ [send_text] HTTPStatusError {exc.response.status_code}: {exc.response.text}")
        return {"error": True, "status_code": exc.response.status_code, "detail": exc.response.text}

    except httpx.RequestError as exc:
        print(f"❌ [send_text] Erro de conexão: {type(exc).__name__}: {exc}")
        return {"error": True, "detail": str(exc)}

    except Exception as exc:
        print(f"❌ [send_text] Erro inesperado: {type(exc).__name__}: {exc}")
        return {"error": True, "detail": str(exc)}