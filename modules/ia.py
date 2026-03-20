# modules/ia.py — Interface de chat do Streamlit
# Roteamento 100% via mavai_core.responder() — sem lógica duplicada aqui

import html
import traceback

import streamlit as st
from mavai_core import responder

USER_ID = "streamlit_web"  # ID fixo para a sessão Streamlit

_MENSAGEM_BOAS_VINDAS = (
    "Olá! Sou o **MavAI**, assistente da MAVA Distribuidora 🤖\n\n"
    "Posso te ajudar com:\n"
    "- 📦 Consulta de preços e estoque\n"
    "- 📊 Análise de vendas e faturamento\n"
    "- 🏆 Ranking de vendedores e clientes\n"
    "- 🗂️ Situação de pedidos\n\n"
    "O que você precisa?"
)

# ── CSS das bolhas de chat ─────────────────────────────────────────────────────
_CSS_CHAT = """
<style>
.mav-chat-row        { display:flex; margin:6px 0; }
.mav-chat-row.user   { justify-content:flex-end; }
.mav-chat-row.assistant { justify-content:flex-start; }

.mav-chat-bubble {
    max-width: 78%;
    padding: 10px 14px;
    border-radius: 16px;
    font-size: 0.88rem;
    line-height: 1.55;
    white-space: pre-wrap;
    word-break: break-word;
}
.mav-chat-bubble.user {
    background: #1D4ED8;
    color: #fff;
    border-bottom-right-radius: 4px;
}
.mav-chat-bubble.assistant {
    background: #1E2235;
    color: #E8EAF0;
    border-bottom-left-radius: 4px;
    border: 1px solid #2E3554;
}
/* Tabelas Markdown dentro das bolhas */
.mav-chat-bubble table {
    border-collapse: collapse;
    width: 100%;
    margin-top: 8px;
    font-size: 0.82rem;
}
.mav-chat-bubble th {
    background: #12141F;
    color: #8B92A8;
    padding: 5px 10px;
    text-align: left;
    font-weight: 600;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.mav-chat-bubble td {
    padding: 5px 10px;
    border-bottom: 1px solid #2E3554;
    color: #D1D5E8;
}
</style>
"""


def _render_message(role: str, content: str) -> None:
    """Renderiza uma bolha de chat com suporte a Markdown/tabelas."""
    css_role = "user" if role == "user" else "assistant"
    # Não escapa o conteúdo — mantém Markdown para tabelas renderizarem
    safe = content.replace("<", "&lt;").replace(">", "&gt;") if role == "user" else content
    # Para o assistente renderizamos via st.markdown dentro de um container
    if role == "user":
        st.markdown(
            f'<div class="mav-chat-row user">'
            f'<div class="mav-chat-bubble user">{safe}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        # Bolha do assistente: usa st.chat_message para renderizar Markdown correto
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(content)


def render(db, chain, llm_conversa, llm_intent):
    # Injeta CSS
    st.markdown(_CSS_CHAT, unsafe_allow_html=True)

    st.markdown(
        '<h3 style="font-family:\'IBM Plex Mono\',monospace;font-weight:700;'
        'color:#E8EAF0;margin:0 0 4px 0;">MavAI</h3>'
        '<p style="color:#4B5563;font-size:0.82rem;margin:0 0 1rem 0;">'
        'Assistente inteligente · MAVA Distribuidora</p>',
        unsafe_allow_html=True,
    )

    # ── Inicializa histórico de exibição ──────────────────────────────────────
    if "mensagens" not in st.session_state:
        st.session_state.mensagens = [
            {"role": "assistant", "content": _MENSAGEM_BOAS_VINDAS}
        ]

    # ── Renderiza histórico de mensagens ──────────────────────────────────────
    for msg in st.session_state.mensagens:
        _render_message(msg["role"], msg["content"])

    # ── Input do usuário ──────────────────────────────────────────────────────
    pergunta = st.chat_input("Pergunte sobre preços, vendas, estoque...")

    if pergunta:
        # Exibe mensagem do usuário imediatamente
        st.session_state.mensagens.append({"role": "user", "content": pergunta})
        _render_message("user", pergunta)

        # ── Chama mavai_core.responder() — único ponto de roteamento ──────────
        # Toda a lógica de intenção, SQL, perfil e histórico está no core.
        # O ia.py apenas exibe — não decide nada.
        with st.spinner("Consultando..."):
            try:
                resposta_final = responder(
                    user_id=USER_ID,
                    pergunta=pergunta,
                    db=db,
                    chain=chain,
                    llm_conversa=llm_conversa,
                    llm_intent=llm_intent,
                    canal="streamlit",   # mantém Markdown, não converte tabelas
                )
            except Exception as e:
                traceback.print_exc()
                resposta_final = (
                    f"⚠️ Erro ao processar: `{type(e).__name__}: {e}`\n\n"
                    "Verifique a conexão com o banco ou a chave da API."
                )

        st.session_state.mensagens.append(
            {"role": "assistant", "content": resposta_final}
        )
        st.rerun()