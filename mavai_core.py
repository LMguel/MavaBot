# mavai_core.py — MavAI Core com LangChain SQL Agent
# Sem glossário manual: o agente lê o schema do banco sozinho e se corrige
import os
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

# ─────────────────────────────────────────────
# Config via .env
# ─────────────────────────────────────────────
DB_URL      = os.getenv("DB_URL", "sqlite:///winthor_fake.db")
GROQ_API    = os.getenv("GROQ_API", "")
GROQ_MODEL  = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
DEBUG_SQL   = os.getenv("DEBUG_SQL", "0") == "1"

# ─────────────────────────────────────────────
# Histórico de conversa por user_id
# ─────────────────────────────────────────────
_historico: dict[str, list[dict]] = {}

def _adicionar_historico(user_id: str, role: str, content: str):
    _historico.setdefault(user_id, [])
    _historico[user_id].append({"role": role, "content": content})

def _historico_texto(user_id: str, limit: int = 6) -> str:
    msgs = _historico.get(user_id, [])[-limit:]
    return "\n".join(
        f"{m['role'].upper()}: {m['content']}"
        for m in msgs if m.get("content")
    )

def limpar_historico(user_id: str):
    _historico.pop(user_id, None)

# ─────────────────────────────────────────────
# Prompt do agente SQL
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """Você é o MavAI, assistente de dados da MAVA Distribuidora.
Você responde perguntas consultando um banco de dados SQL.

REGRAS OBRIGATÓRIAS:
- Responda SEMPRE em português brasileiro
- NUNCA execute INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE ou qualquer DDL/DML
- Sempre use LIMIT 200 no máximo
- Sempre verifique o SQL com sql_db_query_checker antes de executar
- Se encontrar erro, corrija e tente novamente (até 3 tentativas)
- Ao responder, formate valores monetários como R$ X.XXX,XX
- Seja direto e profissional, máximo 10 linhas na resposta final

CONTEXTO DO NEGÓCIO (use isso para entender os dados):
- Departamentos estão em PCPRODUT.CODEPTO (8=DUCOCO, 9=VIGOR, 10=DANONE)
- Regiões estão em PCTABPR.NUMREGIAO e PCCLIENT.NUMREGIAO
  (1=Capital, 2=Litoral Norte, 3=Interior Sul)
- Preço por região: tabela PCTABPR, JOIN com PCPRODUT pelo CODPROD
- Pedidos: POSICAO = F (faturado), L (em aberto), M (em montagem)
- Faturamento = VLTOTAL em PCPEDC

Histórico da conversa:
{historico}"""

# ─────────────────────────────────────────────
# Inicialização dos recursos
# ─────────────────────────────────────────────
def criar_recursos(
    db_url:  str = DB_URL,
    api_key: str = GROQ_API,
    model:   str = GROQ_MODEL,
):
    """
    Retorna (db, agent_executor, llm_conversa).
    Mesma assinatura anterior — nada muda no oraculo.py nem no ia.py.
    """
    db = SQLDatabase.from_uri(db_url)

    llm_sql = ChatGroq(
        model_name=model,
        temperature=0,
        groq_api_key=api_key,
    )

    llm_conversa = ChatGroq(
        model_name=model,
        temperature=0.3,
        groq_api_key=api_key,
    )

    # Toolkit: dá ao agente 4 ferramentas automáticas:
    # sql_db_list_tables, sql_db_schema, sql_db_query_checker, sql_db_query
    toolkit = SQLDatabaseToolkit(db=db, llm=llm_sql)
    tools   = toolkit.get_tools()

    # LangGraph create_react_agent (substitui AgentExecutor removido no LangChain 1.x)
    # O system prompt dinâmico é injetado a cada chamada em responder()
    agent_executor = create_react_agent(model=llm_sql, tools=tools)

    # Retorna db como 1o item para compatibilidade com oraculo.py
    # (db, "agent_executor no lugar do chain", llm_conversa)
    return db, agent_executor, llm_conversa

# ─────────────────────────────────────────────
# Função principal — mesma assinatura de antes
# Usada por modules/ia.py e whatsapp/server.py
# ─────────────────────────────────────────────
def responder(
    user_id: str,
    pergunta: str,
    db,
    chain,
    llm_conversa,
) -> str:
    """Retorna a resposta em português."""
    _adicionar_historico(user_id, "user", pergunta)

    historico = _historico_texto(user_id)

    try:
        system_content = SYSTEM_PROMPT.format(historico=historico)
        resultado = chain.invoke(
            {"messages": [SystemMessage(content=system_content), HumanMessage(content=pergunta)]},
            config={"recursion_limit": 16},  # ~8 iterações
        )

        mensagens = resultado.get("messages", [])
        resposta = ""
        for msg in reversed(mensagens):
            if hasattr(msg, "content") and not isinstance(msg, (HumanMessage, SystemMessage, ToolMessage)):
                resposta = (msg.content or "").strip()
                if resposta:
                    break
        if not resposta:
            resposta = "Não consegui processar essa pergunta. Pode reformular?"

    except Exception as e:
        resposta = "Erro ao processar sua pergunta. Tente reformular com mais detalhes."
        if DEBUG_SQL:
            resposta += f"\n\nDetalhe: {type(e).__name__}: {e}"

    _adicionar_historico(user_id, "assistant", resposta)
    return resposta


