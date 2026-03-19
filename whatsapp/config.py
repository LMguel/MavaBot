"""
config.py — Carrega variáveis de ambiente para a integração WhatsApp Cloud API.

IMPORTANTE: este módulo NÃO deve ser importado antes de load_dotenv() ser chamado.
O server.py garante isso chamando load_dotenv() antes de qualquer import deste módulo.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Garante que o .env seja lido mesmo se config.py for importado diretamente.
# load_dotenv() é idempotente: chamar múltiplas vezes não causa problema.
load_dotenv()


def _get(name: str, default: Optional[str] = None) -> str:
    val = os.getenv(name, default)
    if val is None or str(val).strip() == "":
        raise RuntimeError(
            f"❌ Variável de ambiente ausente ou vazia: '{name}'. "
            f"Verifique o arquivo .env na raiz do projeto."
        )
    return str(val).strip()


# ── WhatsApp Cloud API ────────────────────────────────────────────────────────
VERIFY_TOKEN              = _get("WHATSAPP_VERIFY_TOKEN")
WHATSAPP_ACCESS_TOKEN     = _get("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_NUMBER_ID  = _get("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_API_VERSION      = os.getenv("WHATSAPP_API_VERSION", "v21.0").strip()

# ── Groq ──────────────────────────────────────────────────────────────────────
GROQ_API_KEY  = _get("GROQ_API_KEY")
GROQ_MODEL    = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()

# ── Banco ─────────────────────────────────────────────────────────────────────
DB_URL = os.getenv("DB_URL", "sqlite:///winthor_fake.db")

# ── Misc ──────────────────────────────────────────────────────────────────────
MAX_REPLY_CHARS = int(os.getenv("MAX_REPLY_CHARS", "1200"))
DEBUG_SQL       = os.getenv("DEBUG_SQL", "0") == "1"
