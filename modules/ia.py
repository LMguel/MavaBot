# modules/ia.py
import streamlit as st
import traceback
from mavai_core import responder, limpar_historico

USER_ID = "streamlit"  # id fixo para sessão do Streamlit

def render(db, chain, llm_conversa):

    st.title("💬 Assistente IA")
    st.caption("Faça perguntas sobre vendas, clientes e estoque.")
    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

    # Inicializa histórico da UI
    if "mensagens" not in st.session_state:
        st.session_state.mensagens = [{
            "role": "assistant",
            "content": "Olá! Sou a **MavAI**. Em que posso ajudar hoje? Posso analisar vendas, estoque ou clientes para você."
        }]

    # Renderiza histórico de mensagens
    for msg in st.session_state.mensagens:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input do usuário
    if pergunta := st.chat_input("Digite sua pergunta sobre a MAVA..."):

        st.session_state.mensagens.append({"role": "user", "content": pergunta})

        with st.spinner("MavAI está pensando..."):
            try:
                resposta_final = responder(
                    user_id=USER_ID,
                    pergunta=pergunta,
                    db=db,
                    chain=chain,
                    llm_conversa=llm_conversa,
                )
                st.session_state.mensagens.append({"role": "assistant", "content": resposta_final})

            except Exception as e:
                traceback.print_exc()
                st.session_state.mensagens.append({
                    "role": "assistant",
                    "content": f"⚠️ Erro na análise: {str(e)}\n\n_Dica: Verifique sua conexão ou se a chave da API do Groq é válida._"
                })

        st.rerun()

    # Botão para limpar conversa
    if len(st.session_state.mensagens) > 1:
        if st.button("🗑️ Limpar conversa", key="limpar"):
            limpar_historico(USER_ID)
            st.session_state.mensagens = [{
                "role": "assistant",
                "content": "Olá! Sou a **MavAI**. Em que posso ajudar hoje? Posso analisar vendas, estoque ou clientes para você."
            }]
            st.rerun()
