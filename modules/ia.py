# modules/ia.py
import html
import traceback

import streamlit as st
from langchain_core.messages import HumanMessage, SystemMessage

from mavai_core import responder
from modules.intent import detectar_intencao

USER_ID = "streamlit"  # id fixo para sessão do Streamlit


def _render_message(role: str, content: str) -> None:
    css_role = "user" if role == "user" else "assistant"
    safe_content = html.escape(content).replace("\n", "<br>")
    st.markdown(
        (
            f'<div class="mav-chat-row {css_role}">'
            f'<div class="mav-chat-bubble {css_role}">{safe_content}</div>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render(db, chain, llm_conversa, llm_intent):
    st.title("Assistente IA")
    st.caption("Faça perguntas sobre vendas, clientes e estoque da MAVA.")
    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    bem_vindo = (
        "Oi! Eu sou o MavBot da Mava Distribuidora.\n\n"
        "Posso te ajudar com preços, estoque e pedidos."
    )

    if "mensagens" not in st.session_state:
        st.session_state.mensagens = [{"role": "assistant", "content": bem_vindo}]

    for msg in st.session_state.mensagens:
        _render_message(msg["role"], msg["content"])

    if pergunta := st.chat_input("Digite sua pergunta sobre a MAVA..."):
        st.session_state.mensagens.append({"role": "user", "content": pergunta})

        with st.spinner("MavBot esta pensando..."):
            try:
                intencao = detectar_intencao(pergunta)

                if intencao == "saudacao":
                    resposta_final = (
                        "Oi! Eu sou o MavBot da Mava Distribuidora. "
                        "Posso consultar precos, estoque e pedidos pra voce. Em que posso ajudar?"
                    )
                elif intencao == "consulta":
                    resposta_final = responder(
                        user_id=USER_ID,
                        pergunta=pergunta,
                        db=db,
                        chain=chain,
                        llm_conversa=llm_conversa,
                        llm_intent=llm_intent,
                    )
                else:
                    resposta_llm = llm_conversa.invoke([
                        SystemMessage(
                            content="Voce e um assistente de vendas simpatico e direto da Mava Distribuidora."
                        ),
                        HumanMessage(content=pergunta),
                    ])
                    resposta_final = resposta_llm.content

                st.session_state.mensagens.append(
                    {"role": "assistant", "content": resposta_final}
                )

            except Exception as e:
                traceback.print_exc()
                st.session_state.mensagens.append(
                    {
                        "role": "assistant",
                        "content": f"Erro na analise: {str(e)}\n\nDica: Verifique sua conexao ou a chave da API.",
                    }
                )

        st.rerun()
