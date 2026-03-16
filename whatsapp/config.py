import os

def _get(name: str, default: str | None = None) -> str:
    val = os.getenv(name, default)
    if val is None or str(val).strip() == "":
        raise RuntimeError(f"Variável de ambiente ausente: {name}")
    return val

VERIFY_TOKEN = _get("WHATSAPP_VERIFY_TOKEN")
ACCESS_TOKEN = _get("WHATSAPP_ACCESS_TOKEN")  # token do Meta (Graph)
PHONE_NUMBER_ID = _get("WHATSAPP_PHONE_NUMBER_ID")  # phone_number_id do WhatsApp
GRAPH_API_VERSION = os.getenv("WHATSAPP_GRAPH_API_VERSION", "v19.0")

GROQ_API_KEY = _get("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

DB_URL = os.getenv("DB_URL", "sqlite:///winthor_fake.db")

MAX_REPLY_CHARS = int(os.getenv("MAX_REPLY_CHARS", "1200"))
DEBUG_SQL = os.getenv("DEBUG_SQL", "0") == "1"
