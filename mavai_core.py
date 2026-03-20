# mavai_core.py — MavAI Core v2 · MAVA Distribuidora
# Roteamento por intenção via LLM, prompts ricos por perfil,
# histórico persistente, formatação adaptativa por canal

import os
import shelve
import re
import time
from typing import Any
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

# ─────────────────────────────────────────────
# Config via .env
# ─────────────────────────────────────────────
DB_URL          = os.getenv("DB_URL", "sqlite:///winthor_fake.db")
GROQ_MODEL      = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
DEBUG_SQL       = os.getenv("DEBUG_SQL", "0") == "1"
HISTORY_DB      = os.getenv("HISTORY_DB", "mavai_historico")
MAX_REPLY_CHARS = int(os.getenv("MAX_REPLY_CHARS", "4000"))

# ─────────────────────────────────────────────
# Cascata de modelos — Groq primeiro, Gemini como fallback final
#
# .env necessário:
#   GROQ_API_KEY=gsk_...
#   GROQ_MODEL=llama-3.3-70b-versatile
#   GROQ_FALLBACK_1=llama-3.1-8b-instant        (opcional)
#   GROQ_FALLBACK_2=llama3-groq-8b-8192-tool-use-preview (opcional)
#   GOOGLE_API_KEY=AIza...                       (gratuito em aistudio.google.com)
#   GEMINI_MODEL=gemini-2.0-flash                (opcional, esse é o padrão)
# ─────────────────────────────────────────────
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# Cada entrada: (nome_do_modelo, provedor)
# provedor: "groq" | "gemini"
_MODELOS_FALLBACK: list[tuple[str, str]] = [e for e in [
    (GROQ_MODEL,                                              "groq"),
    (os.getenv("GROQ_FALLBACK_1", "llama-3.1-8b-instant"),   "groq"),
    (os.getenv("GROQ_FALLBACK_2", ""),                        "groq"),
    (GEMINI_MODEL,                                            "gemini"),  # fallback final gratuito
] if e[0]]  # remove entradas com modelo vazio

# Estado global: índice do modelo ativo na cascata
_modelo_idx: int = 0
_modelo_bloqueado_ate: dict[int, float] = {}  # idx → timestamp de liberação

def _proximo_modelo_disponivel() -> int:
    """Retorna o índice do primeiro modelo não bloqueado."""
    agora = time.time()
    for idx in range(len(_MODELOS_FALLBACK)):
        if agora >= _modelo_bloqueado_ate.get(idx, 0):
            return idx
    return min(_modelo_bloqueado_ate.keys(), key=lambda i: _modelo_bloqueado_ate[i])

def _marcar_rate_limit(idx: int, segundos: float = 900.0):
    """Bloqueia o modelo idx por `segundos`."""
    _modelo_bloqueado_ate[idx] = time.time() + segundos
    nome, prov = _MODELOS_FALLBACK[idx]
    print(f"🚫 [fallback] '{nome}' ({prov}) bloqueado por {int(segundos)}s")

def _llm_com_fallback(invoke_fn):
    """
    Tenta cada entrada da cascata em ordem.
    Rate limit (429) → bloqueia o modelo atual → tenta o próximo.
    Groq esgotado → cai automaticamente para Gemini.
    """
    global _modelo_idx

    tentativas = len(_MODELOS_FALLBACK)
    ultimo_erro = None

    for _ in range(tentativas):
        _modelo_idx       = _proximo_modelo_disponivel()
        modelo, provedor  = _MODELOS_FALLBACK[_modelo_idx]

        try:
            resultado = invoke_fn(modelo, provedor)
            if _modelo_idx != 0:
                print(f"✅ [fallback] Respondido por '{modelo}' ({provedor})")
            return resultado

        except Exception as e:
            msg = str(e).lower()
            eh_rate_limit = (
                "rate_limit_exceeded" in msg
                or "429"              in msg
                or "tokens per"       in msg
                or "quota"            in msg        # erro quota do Gemini
                or "resource_exhausted" in msg      # gRPC do Gemini
            )
            if eh_rate_limit:
                import re as _re
                match = _re.search(r"try again in ([\d.]+)([smh])", str(e))
                if match:
                    valor, unidade = float(match.group(1)), match.group(2)
                    segundos = valor * {"s": 1, "m": 60, "h": 3600}.get(unidade, 60)
                else:
                    segundos = 900.0
                _marcar_rate_limit(_modelo_idx, segundos + 30)
                ultimo_erro = e
                print(f"⚠️ [fallback] Rate limit em '{modelo}' ({provedor}), tentando próximo...")
            else:
                raise

    raise ultimo_erro or RuntimeError("Todos os modelos da cascata atingiram o rate limit.")

# ─────────────────────────────────────────────
# Controle de acesso
# ─────────────────────────────────────────────
USUARIOS_ACESSO = {
    "5524992585255": "admin",
    "5524XXXXXXXXX": "vendedor",
    "5524YYYYYYYYY": "estoquista",
    "5524ZZZZZZZZZ": "cliente",
    "streamlit_web": "admin",   # sessão web sempre como admin
}

def get_nivel_acesso(numero: str) -> str:
    return USUARIOS_ACESSO.get(numero, "vendedor")

# ─────────────────────────────────────────────
# Histórico Persistente (shelve)
# ─────────────────────────────────────────────
def _adicionar_historico(user_id: str, role: str, content: str):
    with shelve.open(HISTORY_DB) as db:
        historico = db.get(user_id, [])
        historico.append({"role": role, "content": content})
        db[user_id] = historico[-20:]

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
# Detecção de Intenção via LLM
# ─────────────────────────────────────────────
INTENCOES_VALIDAS = {
    "saudacao":     "Cumprimento puro — oi, olá, tudo bem, bom dia — sem pedir nenhum dado.",
    "consulta_sql": (
        "Qualquer pergunta que envolva dados do negócio: preços, estoque, produtos, "
        "pedidos, clientes, fornecedores, quantidades, notas fiscais, faturamento de "
        "um período, produtos mais vendidos, ranking. Inclui erros de digitação "
        "('masi vendidos', 'predutos', 'faturamneto') e perguntas vagas como "
        "'quanto vendeu hoje', 'tem no estoque', 'qual o preco'."
    ),
    "analise": (
        "Análise comparativa, desempenho de vendedores, evolução de faturamento entre "
        "períodos, metas, tendências, insights gerenciais. Ex: 'compare jan x fev', "
        "'quem vendeu mais esse mês', 'como foi o desempenho da equipe'."
    ),
    "conversa": (
        "Dúvidas sobre como usar o sistema, perguntas sem relação com dados da empresa."
    ),
}

def detectar_intencao_llm(pergunta: str, llm) -> str:
    opcoes = "\n".join(f"- {k}: {v}" for k, v in INTENCOES_VALIDAS.items())
    prompt = (
        "Você é um classificador de intenções. Classifique a mensagem abaixo em "
        "exatamente UMA das intenções listadas.\n"
        "Responda SOMENTE com a chave, sem explicação, sem pontuação.\n"
        "Em caso de dúvida entre consulta_sql e analise, escolha consulta_sql.\n"
        "Se a mensagem mencionar qualquer dado de negócio (produto, preco, venda, "
        "pedido, cliente, estoque), classifique como consulta_sql.\n\n"
        f"Intenções:\n{opcoes}\n\n"
        f"Mensagem: \"{pergunta}\"\n\n"
        "Intenção:"
    )
    try:
        resultado = llm.invoke([HumanMessage(content=prompt)])
        intencao  = resultado.content.strip().lower().split()[0].rstrip(".,:")
        if intencao not in INTENCOES_VALIDAS:
            print(f"⚠️ [intent] Inesperado: '{intencao}' → consulta_sql")
            return "consulta_sql"
        return intencao
    except Exception as e:
        print(f"⚠️ [intent] Erro: {e} → consulta_sql")
        return "consulta_sql"

# ─────────────────────────────────────────────
# System Prompts por Perfil
# ─────────────────────────────────────────────
_BASE_COMPORTAMENTO = """
REGRAS DE COMPORTAMENTO:
- Responda em português brasileiro, linguagem natural e direta.
- Seja como um colega experiente que conhece bem os dados da empresa.
- Quando houver dados, SEMPRE mostre em tabela Markdown bem formatada.
- Após a tabela, adicione um parágrafo curto com o destaque mais relevante.
- Se a pergunta for vaga, interprete pelo contexto do histórico da conversa.
- NUNCA invente dados. Se não encontrar, diga claramente.
- NUNCA rode SQL destrutivo (DELETE, DROP, UPDATE, INSERT).
- NUNCA revele que é uma IA ou mencione LLM/modelo/GPT/Groq.

FORMATO DE TABELA OBRIGATÓRIO para 2+ itens:
| Coluna 1 | Coluna 2 | Coluna 3 |
|----------|----------|----------|
| valor    | valor    | valor    |

Formatação de valores: R$ 1.250,00 · percentuais: +12,5% · quantidades: 320 un
"""

PROMPTS_POR_PERFIL = {
    "admin": f"""Você é o MavAI, assistente executivo da MAVA Distribuidora.
PERFIL: GESTOR / ADMINISTRADOR — acesso total a todos os dados.
{_BASE_COMPORTAMENTO}
ANÁLISES DISPONÍVEIS PARA ESTE PERFIL:
- Faturamento com variação % vs período anterior
- Ranking de vendedores com meta, realizado e % atingido
- Produtos mais vendidos com quantidade e receita
- Clientes top com volume e frequência de compra
- Alertas de estoque crítico (abaixo do mínimo)
- Pedidos em aberto ordenados por dias pendentes

EXEMPLO de ranking de vendedores:
| # | Vendedor         | Faturamento   | Meta        | % Meta  |
|---|------------------|---------------|-------------|---------|
| 1 | André Figueiredo | R$ 48.200,00  | R$ 40.000   | 120% ✅ |
| 2 | Beatriz Cardoso  | R$ 35.100,00  | R$ 40.000   |  88% ⚠️ |

> 💡 André superou a meta em 20%. Beatriz está 12% abaixo — vale um acompanhamento.""",

    "vendedor": f"""Você é o MavAI, assistente de vendas da MAVA Distribuidora.
PERFIL: VENDEDOR — acesso a produtos, preços, clientes da sua carteira e seu próprio desempenho.
{_BASE_COMPORTAMENTO}
FOCO PARA ESTE PERFIL:
- Preços e disponibilidade de produtos por região
- Situação dos seus pedidos (faturados, em aberto)
- Seu próprio desempenho — nunca mostre dados de outros vendedores
- Histórico de compras dos seus clientes
- Seja motivador quando o desempenho for positivo""",

    "estoquista": f"""Você é o MavAI, assistente de estoque da MAVA Distribuidora.
PERFIL: ESTOQUISTA — foco em níveis, movimentações e alertas de estoque.
{_BASE_COMPORTAMENTO}
FOCO PARA ESTE PERFIL:
- Estoque atual vs mínimo com cobertura em ×
- Produtos abaixo do mínimo sinalizados com 🔴
- Entradas e saídas por período
- NUNCA mostre preços de custo, margem ou dados financeiros""",

    "cliente": f"""Você é o MavAI, assistente comercial da MAVA Distribuidora.
PERFIL: CLIENTE — acesso a preços de venda e disponibilidade.
{_BASE_COMPORTAMENTO}
RESTRIÇÕES:
- Mostre apenas preço de venda e disponibilidade
- Linguagem cordial e comercial
- Nunca mostre custo, margem ou dados de outros clientes""",
}

def get_system_prompt(nivel: str, historico: str) -> str:
    base = PROMPTS_POR_PERFIL.get(nivel, PROMPTS_POR_PERFIL["vendedor"])
    hist = historico if historico else "(início da conversa)"
    return f"{base}\n\nHISTÓRICO RECENTE:\n{hist}"

# ─────────────────────────────────────────────
# Formatação adaptativa por canal
# ─────────────────────────────────────────────
def _tabela_para_whatsapp(texto: str) -> str:
    """Converte tabelas Markdown em listas legíveis no WhatsApp."""
    linhas    = texto.split("\n")
    resultado = []
    for linha in linhas:
        if linha.strip().startswith("|") and "|" in linha:
            if re.match(r"^\s*\|[\s\-\|:]+\|\s*$", linha):
                continue
            colunas = [c.strip() for c in linha.strip("|").split("|") if c.strip()]
            resultado.append("• " + " — ".join(colunas))
        else:
            resultado.append(linha)
    return "\n".join(resultado)

def formatar_resposta(texto: str, canal: str = "streamlit") -> str:
    if canal == "whatsapp":
        return _tabela_para_whatsapp(texto)
    return texto

# ─────────────────────────────────────────────
# Inicialização dos recursos
# ─────────────────────────────────────────────
# Cache de agentes — um por modelo, criado no startup
# Evita recriar o agente a cada fallback
# ─────────────────────────────────────────────
_agentes_cache: dict[str, Any] = {}  # "modelo|provedor" → agent_executor
_llms_cache:    dict[str, Any] = {}  # "modelo|provedor" → instância LLM


def _criar_llm(modelo: str, provedor: str = "groq") -> Any:
    """Retorna instância cacheada do LLM para o modelo/provedor."""
    chave = f"{modelo}|{provedor}"
    if chave not in _llms_cache:
        if provedor == "gemini":
            _llms_cache[chave] = ChatGoogleGenerativeAI(
                model=modelo,
                temperature=0.0,
                google_api_key=GOOGLE_API_KEY,
            )
        else:  # groq (padrão)
            _llms_cache[chave] = ChatGroq(model=modelo, temperature=0.0)
    return _llms_cache[chave]


def _criar_agente(db, modelo: str, provedor: str = "groq") -> Any:
    """Retorna agente SQL cacheado para o modelo/provedor."""
    chave = f"{modelo}|{provedor}"
    if chave not in _agentes_cache:
        print(f"🔧 [cache] Criando agente: '{modelo}' ({provedor})...")
        llm     = _criar_llm(modelo, provedor)
        toolkit = SQLDatabaseToolkit(db=db, llm=llm)
        _agentes_cache[chave] = create_react_agent(model=llm, tools=toolkit.get_tools())
    return _agentes_cache[chave]


class _LLMProxy:
    """Proxy transparente — roteia .invoke() pela cascata com fallback automático."""
    def invoke(self, messages):
        def _tentar(modelo: str, provedor: str):
            return _criar_llm(modelo, provedor).invoke(messages)
        return _llm_com_fallback(_tentar)


def criar_recursos():
    """
    Pré-cria agentes para todos os modelos da cascata no startup.
    Gemini só é inicializado se GOOGLE_API_KEY estiver definida no .env.
    """
    db = SQLDatabase.from_uri(DB_URL)

    for modelo, provedor in _MODELOS_FALLBACK:
        if provedor == "gemini" and not GOOGLE_API_KEY:
            print(f"⚠️ [startup] GOOGLE_API_KEY não definida — Gemini desabilitado.")
            continue
        try:
            _criar_agente(db, modelo, provedor)
        except Exception as e:
            print(f"⚠️ [startup] Agente '{modelo}' ({provedor}) falhou: {e}")

    proxy = _LLMProxy()
    return db, db, proxy, proxy

# ─────────────────────────────────────────────
# Extração de resposta do agente LangGraph
# ─────────────────────────────────────────────
def _extrair_resposta_agente(resultado: dict) -> str:
    for msg in reversed(resultado.get("messages", [])):
        if isinstance(msg, (HumanMessage, SystemMessage, ToolMessage)):
            continue
        conteudo = (msg.content or "").strip()
        if conteudo:
            return conteudo
    return ""

# ─────────────────────────────────────────────
# Função Principal — único ponto de entrada
# ─────────────────────────────────────────────
def responder(
    user_id:        str,
    pergunta:       str,
    db,
    chain,
    llm_conversa,
    llm_intent,
    contexto_extra: str = "",
    canal:          str = "streamlit",
) -> str:
    """
    Roteia por intenção, executa a lógica correta e retorna a resposta
    formatada para o canal (streamlit mantém Markdown; whatsapp converte).
    """
    _adicionar_historico(user_id, "user", pergunta)

    nivel          = get_nivel_acesso(user_id)
    historico      = _historico_texto(user_id)
    system_content = get_system_prompt(nivel, historico)
    intencao       = detectar_intencao_llm(pergunta, llm_intent)

    print(f"🧠 [core] '{pergunta[:50]}' → {intencao} | perfil={nivel} | canal={canal}")

    resposta = ""

    try:
        # ── 1. Saudação ───────────────────────────────────────────────────────
        if intencao == "saudacao":
            resposta = (
                "Olá! Sou o MavAI da MAVA Distribuidora 🤖\n\n"
                "Posso consultar preços, estoque, pedidos e analisar vendas. "
                "O que você precisa?"
            )

        # ── 2. Consulta SQL ───────────────────────────────────────────────────
        elif intencao == "consulta_sql":
            prompt_consulta = (
                f"{contexto_extra}"
                "Responda de forma detalhada. Use tabela Markdown quando houver 2 ou "
                "mais itens comparáveis. Após a tabela, destaque o ponto mais relevante "
                "em uma frase direta.\n\n"
                f"Pergunta: {pergunta}"
            )
            msgs_consulta = [
                SystemMessage(content=system_content),
                HumanMessage(content=prompt_consulta),
            ]
            def _invocar_consulta(modelo: str, provedor: str):
                return _criar_agente(db, modelo, provedor).invoke(
                    {"messages": msgs_consulta},
                    config={"recursion_limit": 20},
                )
            resultado = _llm_com_fallback(_invocar_consulta)
            resposta  = _extrair_resposta_agente(resultado)

        # ── 3. Análise gerencial ──────────────────────────────────────────────
        elif intencao == "analise":
            prompt_analise = (
                f"{contexto_extra}"
                "Faça uma análise completa com tabela Markdown contendo todos os dados.\n"
                "Inclua totais, variações percentuais e um insight prático ao final.\n"
                "Use ✅ para destaques positivos, ⚠️ para atenção, 🔴 para crítico.\n\n"
                f"Pergunta: {pergunta}"
            )
            msgs_analise = [
                SystemMessage(content=system_content),
                HumanMessage(content=prompt_analise),
            ]
            def _invocar_analise(modelo: str, provedor: str):
                return _criar_agente(db, modelo, provedor).invoke(
                    {"messages": msgs_analise},
                    config={"recursion_limit": 24},
                )
            resultado = _llm_com_fallback(_invocar_analise)
            resposta  = _extrair_resposta_agente(resultado)

        # ── 4. Conversa geral ─────────────────────────────────────────────────
        else:
            msg = llm_conversa.invoke([
                SystemMessage(content=system_content),
                HumanMessage(content=pergunta),
            ])
            resposta = msg.content

    except Exception as e:
        resposta = "Não consegui processar essa pergunta. Pode reformular com mais detalhes?"
        if DEBUG_SQL:
            resposta += f"\n\n⚠️ Detalhe: `{type(e).__name__}: {e}`"

    if not resposta:
        resposta = "Não encontrei dados para essa consulta. Tente reformular."

    resposta = formatar_resposta(resposta, canal=canal)

    if len(resposta) > MAX_REPLY_CHARS:
        resposta = (
            resposta[:MAX_REPLY_CHARS].rstrip()
            + "\n\n_(resposta truncada — refine a consulta para ver mais detalhes)_"
        )

    _adicionar_historico(user_id, "assistant", resposta)
    return resposta