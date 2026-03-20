# oraculo.py — Entrypoint Streamlit do MavAI
import os
import streamlit as st
from dotenv import load_dotenv

# Carrega variáveis de ambiente antes de importar módulos que leem DB_URL/GROQ.
load_dotenv()

from mavai_core import criar_recursos
from modules import ia, painel, estoque


def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)


# --- Config da página (deve ser o primeiro comando st.) ---
st.set_page_config(
    page_title="MavAI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

load_css("style.css")

# --- Variáveis de ambiente ---
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API", "")

# --- Recursos cacheados (LLM + DB instanciados 1x) ---
@st.cache_resource
def iniciar_oraculo():
    return criar_recursos()   # usa DB_URL e GROQ_API do .env

db, chain, llm_conversa, llm_intent = iniciar_oraculo()


# --- Sidebar + Navegação ---
with st.sidebar:
    st.image("image/image.png", width=160)

    def render_ia():
        ia.render(db, chain, llm_conversa, llm_intent)

    def render_painel():
        painel.render(db)

    def render_estoque():
        estoque.render(db)

    pg = st.navigation([
        st.Page(render_ia,      title="Assistente IA",   icon="💬"),
        st.Page(render_painel,  title="Painel Executivo", icon="📊"),
        st.Page(render_estoque, title="Estoque",          icon="📦"),
    ])

    st.markdown(
        '<div class="sidebar-footer">'
        'MavAI v1.0 · MAVA Distribuidora · Powered by Llama 3.3 · Groq</div>',
        unsafe_allow_html=True
    )

pg.run()
