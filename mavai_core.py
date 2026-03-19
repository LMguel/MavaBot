# mavai_core.py — MavAI Core v2 com LangChain SQL Agent
# Melhorias: NLU via LLM, tabelas adaptativas, prompts por perfil, histórico persistente

import os
import shelve
import re
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

# ─────────────────────────────────────────────
# Config via .env — todas as variáveis lidas aqui
# ─────────────────────────────────────────────
DB_URL          = os.getenv("DB_URL", "sqlite:///winthor_fake.db")
GROQ_MODEL      = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
DEBUG_SQL       = os.getenv("DEBUG_SQL", "0") == "1"
HISTORY_DB      = os.getenv("HISTORY_DB", "mavai_historico")
MAX_REPLY_CHARS = int(os.getenv("MAX_REPLY_CHARS", "2000"))  # limite de chars na resposta final

USUARIOS_ACESSO = {
    "5524992585255": "admin",
    "5524XXXXXXXXX": "vendedor",
    "5524YYYYYYYYY": "estoquista",
    "5524ZZZZZZZZZ": "cliente",
}

def get_nivel_acesso(numero: str) -> str:
    return USUARIOS_ACESSO.get(numero, "vendedor")

# ─────────────────────────────────────────────
# Histórico Persistente (shelve — sobrevive restart)
# ─────────────────────────────────────────────
def _adicionar_historico(user_id: str, role: str, content: str):
    with shelve.open(HISTORY_DB) as db:
        historico = db.get(user_id, [])
        historico.append({"role": role, "content": content})
        db[user_id] = historico[-20:]  # mantém as últimas 20 mensagens

def _historico_texto(user_id: str, limit: int = 6) -> str:
    with shelve.open(HISTORY_DB) as db:
        msgs = db.get(user_id, [])[-limit:]
    return "\n".join(
        f"{m['role'].upper()}: {m['content']}"
        for m in msgs if m.get("content")
    )

def limpar_historico(user_id: str):
    with shelve.open(HISTORY_DB) as db:
        db.pop(user_id, None)

# ─────────────────────────────────────────────
# Detecção de Intenção via LLM (NLU semântico)
# Substitui regex por compreensão real de linguagem natural
# ─────────────────────────────────────────────
INTENCOES_VALIDAS = {
    "saudacao":    "Cumprimento, oi, olá, tudo bem, bom dia — sem pedido de dado.",
    "consulta_sql":"Perguntas sobre preços, estoque, pedidos, produtos — precisa de SQL.",
    "analise":     "Análise de desempenho, faturamento, ranking, comparativo, metas.",
    "conversa":    "Dúvidas gerais, instruções, como usar, pedidos não relacionados a dados.",
}

def detectar_intencao_llm(pergunta: str, llm) -> str:
    """
    Usa o LLM para classificar a intenção com compreensão semântica real.
    Retorna uma das chaves de INTENCOES_VALIDAS.
    """
    opcoes = "\n".join(f"- {k}: {v}" for k, v in INTENCOES_VALIDAS.items())
    prompt = f"""Classifique a mensagem abaixo em exatamente UMA das intenções listadas.
Responda SOMENTE com a chave, sem explicação.

Intenções:
{opcoes}

Mensagem: "{pergunta}"

Intenção:"""
    try:
        resultado = llm.invoke([HumanMessage(content=prompt)])
        intencao = resultado.content.strip().lower().split()[0]
        return intencao if intencao in INTENCOES_VALIDAS else "conversa"
    except Exception:
        return "conversa"

# ─────────────────────────────────────────────
# Prompts por Perfil de Acesso
# Cada perfil recebe instruções e formato de resposta diferentes
# ─────────────────────────────────────────────
PROMPTS_POR_PERFIL = {
    "admin": """Você é o MavAI, assistente analítico da MAVA Distribuidora.

🎯 PERFIL: GESTOR / ADMIN
- Você tem acesso total a todos os dados.
- Seja analítico, preciso e direto ao ponto.
- Use tabelas Markdown para comparativos, rankings e relatórios.
- Inclua variações percentuais quando relevante (ex: +12% vs mês anterior).
- Para análises de desempenho, sempre mostre: meta, realizado e % atingido.
- Sugira insights quando os dados indicarem algo relevante.

📊 FORMATO DE TABELA (use sempre que houver 2+ itens comparáveis):
| Vendedor | Faturamento | Meta | % Meta |
|----------|------------|------|--------|
| João     | R$ 45.200  | R$ 40.000 | 113% ✅ |

🚫 NUNCA: inventar dados, rodar SQL destrutivo, revelar que é IA.""",

    "vendedor": """Você é o MavAI, assistente de vendas da MAVA Distribuidora.

🎯 PERFIL: VENDEDOR
- Mostre dados relevantes para o trabalho do vendedor.
- Para preços: formato direto — Produto | Preço | Estoque.
- Para desempenho pessoal: mostre apenas os dados do próprio vendedor.
- Seja motivador quando o desempenho for bom.
- Linguagem natural, como um colega experiente.
- Máximo 6 linhas para consultas simples.

📊 FORMATO PARA PRODUTOS:
| Produto | Preço | Estoque |
|---------|-------|---------|
| Frango  | R$ 12,50 | 320 kg |

🚫 NUNCA: mostrar dados de outros vendedores, inventar preços.""",

    "estoquista": """Você é o MavAI, assistente de estoque da MAVA Distribuidora.

🎯 PERFIL: ESTOQUISTA
- Foco em estoque, entradas, saídas e validades.
- Use tabelas para listar produtos com estoque baixo.
- Alerte quando estoque estiver abaixo do mínimo.
- Linguagem técnica e objetiva.

🚫 NUNCA: mostrar preços de custo, dados financeiros, vendedores.""",

    "cliente": """Você é o MavAI, assistente da MAVA Distribuidora.

🎯 PERFIL: CLIENTE
- Mostre apenas preço de venda e disponibilidade.
- Linguagem cordial e comercial.
- Máximo 4 linhas por resposta.

🚫 NUNCA: mostrar custo, margem, dados de outros clientes.""",
}

def get_system_prompt(nivel: str, historico: str) -> str:
    base = PROMPTS_POR_PERFIL.get(nivel, PROMPTS_POR_PERFIL["vendedor"])
    return f"""{base}

📋 HISTÓRICO RECENTE:
{historico if historico else "(sem histórico)"}"""

# ─────────────────────────────────────────────
# Adaptador de Tabela para WhatsApp
# WhatsApp não renderiza Markdown — converte para texto formatado
# ─────────────────────────────────────────────
def _tabela_para_whatsapp(texto: str) -> str:
    """
    Converte tabelas Markdown em listas textuais legíveis no WhatsApp.
    Ex: | João | R$45k | 113% |  →  • João — R$45k — 113%
    """
    linhas = texto.split("\n")
    resultado = []
    dentro_tabela = False

    for linha in linhas:
        if linha.strip().startswith("|") and "|" in linha:
            dentro_tabela = True
            # Pula linha de separação (|---|---|)
            if re.match(r"^\s*\|[\s\-\|]+\|\s*$", linha):
                continue
            colunas = [c.strip() for c in linha.strip("|").split("|")]
            colunas = [c for c in colunas if c]
            resultado.append("• " + " — ".join(colunas))
        else:
            dentro_tabela = False
            resultado.append(linha)

    return "\n".join(resultado)

def formatar_resposta(texto: str, canal: str = "streamlit") -> str:
    """
    canal: 'streamlit' (mantém Markdown) | 'whatsapp' (converte tabelas)
    """
    if canal == "whatsapp":
        return _tabela_para_whatsapp(texto)
    return texto  # Streamlit renderiza Markdown nativamente

# ─────────────────────────────────────────────
# Inicialização dos Recursos — tudo via .env
# ─────────────────────────────────────────────
def criar_recursos():
    """
    Lê DB_URL e GROQ_MODEL do .env. GROQ_API_KEY é lida automaticamente pelo ChatGroq.
    Retorna (db, agent_executor, llm_conversa, llm_intent).
    """
    db = SQLDatabase.from_uri(DB_URL)

    llm_sql      = ChatGroq(model=GROQ_MODEL, temperature=0.0)
    llm_conversa = ChatGroq(model=GROQ_MODEL, temperature=0.4)
    llm_intent   = ChatGroq(model=GROQ_MODEL, temperature=0.0)

    toolkit        = SQLDatabaseToolkit(db=db, llm=llm_sql)
    agent_executor = create_react_agent(model=llm_sql, tools=toolkit.get_tools())

    return db, agent_executor, llm_conversa, llm_intent

# ─────────────────────────────────────────────
# Função Principal — Roteada por Intenção via LLM
# ─────────────────────────────────────────────
def responder(
    user_id:      str,
    pergunta:     str,
    db,
    chain,
    llm_conversa,
    llm_intent,
    contexto_extra: str = "",
    canal:          str = "streamlit",  # 'streamlit' | 'whatsapp'
) -> str:
    """
    Roteia a pergunta pelo tipo de intenção detectada via LLM.
    canal: define formatação da resposta (Markdown vs texto simples).
    """
    _adicionar_historico(user_id, "user", pergunta)

    nivel    = get_nivel_acesso(user_id)
    historico = _historico_texto(user_id)
    system_content = get_system_prompt(nivel, historico)

    # ── Detecta intenção via LLM (semântico, não regex) ────────────────────
    intencao = detectar_intencao_llm(pergunta, llm_intent)
    print(f"🧠 [intent] '{pergunta[:40]}...' → {intencao} | perfil: {nivel} | canal: {canal}")

    resposta = ""

    try:
        # ── 1. Saudação — resposta direta sem SQL ──────────────────────────
        if intencao == "saudacao":
            resposta = (
                "Oi! Sou o MavAI 🤖 da MAVA Distribuidora.\n"
                "Posso consultar preços, estoque, pedidos e analisar o desempenho da equipe.\n"
                "O que você precisa?"
            )

        # ── 2. Consulta SQL — agente com acesso ao banco ───────────────────
        elif intencao == "consulta_sql":
            resultado = chain.invoke(
                {
                    "messages": [
                        SystemMessage(content=system_content),
                        HumanMessage(content=contexto_extra + pergunta),
                    ]
                },
                config={"recursion_limit": 20},
            )
            mensagens = resultado.get("messages", [])
            for msg in reversed(mensagens):
                if hasattr(msg, "content") and not isinstance(
                    msg, (HumanMessage, SystemMessage, ToolMessage)
                ):
                    resposta = (msg.content or "").strip()
                    if resposta:
                        break

        # ── 3. Análise — agente SQL com prompt analítico explícito ─────────
        elif intencao == "analise":
            prompt_analise = (
                f"{contexto_extra}"
                f"Faça uma análise completa e estruturada com tabela Markdown. "
                f"Inclua totais, variações e um insight no final.\n\n"
                f"Pergunta: {pergunta}"
            )
            resultado = chain.invoke(
                {
                    "messages": [
                        SystemMessage(content=system_content),
                        HumanMessage(content=prompt_analise),
                    ]
                },
                config={"recursion_limit": 24},
            )
            mensagens = resultado.get("messages", [])
            for msg in reversed(mensagens):
                if hasattr(msg, "content") and not isinstance(
                    msg, (HumanMessage, SystemMessage, ToolMessage)
                ):
                    resposta = (msg.content or "").strip()
                    if resposta:
                        break

        # ── 4. Conversa — LLM direto, sem SQL ─────────────────────────────
        else:
            msg_llm = llm_conversa.invoke([
                SystemMessage(content=system_content),
                HumanMessage(content=pergunta),
            ])
            resposta = msg_llm.content

    except Exception as e:
        resposta = "Não consegui processar essa pergunta. Pode reformular com mais detalhes?"
        if DEBUG_SQL:
            resposta += f"\n\n⚠️ Detalhe técnico: {type(e).__name__}: {e}"

    # ── Fallback se resposta vazia ─────────────────────────────────────────
    if not resposta:
        resposta = "Não encontrei dados para essa consulta. Tente reformular."

    # ── Formata para o canal correto ───────────────────────────────────────
    resposta = formatar_resposta(resposta, canal=canal)

    # ── Aplica limite de caracteres do .env (MAX_REPLY_CHARS) ──────────────
    if len(resposta) > MAX_REPLY_CHARS:
        resposta = resposta[:MAX_REPLY_CHARS].rstrip() + "\n\n_(resposta truncada — refine a consulta para mais detalhes)_"

    _adicionar_historico(user_id, "assistant", resposta)
    return resposta