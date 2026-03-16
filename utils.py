import base64
import streamlit as st
from langchain_core.messages import HumanMessage

GLOSSARIO_MAVA = """
Você é a MavAI, assistente de dados da MAVA Distribuidora.

Glossário da empresa:
- "volume de vendas", "quanto vendemos", "faturamento" = valor total dos pedidos (VLTOTAL em PCPEDC)
- "clientes", "compradores", "estabelecimentos" = tabela PCCLIENT
- "pedido", "compra", "nota", "venda" = tabela PCPEDC
- "produto", "item", "mercadoria" = tabela PCPRODUT
- "itens do pedido", "o que foi vendido", "produtos vendidos", "produto mais vendeu" = tabela PCPEDI
- "em aberto", "pendente", "não faturado" = POSICAO = 'L' em PCPEDC
- "faturado", "concluído", "fechado" = POSICAO = 'F' em PCPEDC
- "esse mês" = mês atual
- "semana passada" = últimos 7 dias
- "período" = sempre pergunte qual período se não especificado

Estrutura do banco:
- PCPEDC: pedidos (NUMPED, CODCLI, DATA, VLTOTAL, POSICAO, CODFILIAL)
- PCCLIENT: clientes (CODCLI, CLIENTE, CIDADE, ESTADO, LIMITE_CRED)
- PCPRODUT: produtos (CODPROD, DESCRICAO, EMBALAGEM, PRECO, ESTOQUE)
- PCPEDI: itens dos pedidos (NUMPED, CODPROD, QTBAIXA, PVENDA)

Para saber qual produto mais vendeu: JOIN entre PCPEDI e PCPRODUT, SUM(QTBAIXA) agrupado por CODPROD.
Para saber faturamento por produto: SUM(QTBAIXA * PVENDA) em PCPEDI.
Para filtrar por data: JOIN com PCPEDC usando NUMPED e filtrar pelo campo DATA.
"""

def _limpar_valor(raw):
    try:
        limpo = str(raw).strip("[](),' \n")
        if not limpo or limpo.lower() == 'none':
            return 0.0
        return float(limpo)
    except (ValueError, TypeError):
        return 0.0

def _formatar_brl(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def get_image_base64(path):
    try:
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    except Exception:
        return ""

def precisa_de_detalhes(llm_conversa, pergunta):
    prompt = f"""{GLOSSARIO_MAVA}

O usuário perguntou: "{pergunta}"

Analise se essa pergunta tem informações suficientes para ser respondida.

REGRAS IMPORTANTES:
- Se a pergunta já menciona "todos", "geral", "completo", "histórico", "sem filtro", "qualquer", "todos os meses" ou similar, considere COMPLETA.
- Se a pergunta pede uma lista de clientes sem filtro de tempo, considere COMPLETA (basta listar todos).
- Só marque INCOMPLETA se realmente faltar informação crítica e não houver nenhuma forma de responder sem ela.
- Perguntas sobre cadastro (ex: "liste os clientes", "quais produtos temos") NÃO precisam de período, são COMPLETAS.
- Perguntas financeiras (faturamento, valor de pedidos) SEM período podem ser respondidas com o total geral, são COMPLETas.

Responda APENAS com:
- "COMPLETA"
- "INCOMPLETA: [pergunta de esclarecimento ÚNICA e curta]"

Não explique. Não adicione nada."""
    resposta = llm_conversa.invoke([HumanMessage(content=prompt)])
    return resposta.content.strip()

def consolidar_pergunta(llm_conversa, historico, pergunta_atual):
    contexto = ""
    for msg in historico:
        if msg["role"] == "user":
            contexto += f"Usuário: {msg['content']}\n"
        elif msg["role"] == "assistant" and msg.get("sql") is None and msg["content"]:
            contexto += f"Assistente: {msg['content']}\n"

    prompt = f"""{GLOSSARIO_MAVA}

Histórico recente da conversa:
{contexto}
Usuário disse agora: "{pergunta_atual}"

Com base em TODO o histórico acima, reformule uma ÚNICA pergunta completa que capture toda a intenção do usuário, combinando todas as informações fornecidas ao longo da conversa.

Responda APENAS com a pergunta reformulada em português. Sem explicações, sem prefixos."""
    resposta = llm_conversa.invoke([HumanMessage(content=prompt)])
    return resposta.content.strip()

def formatar_resposta_completa(llm_conversa, pergunta, resultado_bruto, query_sql):
    prompt = f"""{GLOSSARIO_MAVA}

O usuário perguntou: "{pergunta}"
A consulta retornou os seguintes dados: {resultado_bruto}
A query SQL executada foi: {query_sql}

Responda seguindo estas regras OBRIGATÓRIAS:
1. Escreva em português, de forma clara e profissional.
2. Nunca mencione SQL, tabelas, banco de dados ou termos técnicos.
3. Sempre formate valores monetários como R$ X.XXX,XX (exemplo: R$ 8.900,00).
4. Se um mesmo cliente aparecer mais de uma vez nos resultados, some os valores e liste-o apenas UMA vez com o valor total consolidado.
5. Se o resultado for uma lista ordenada, use numeração (1º, 2º, 3º...) e inclua o valor de cada item.
6. Sempre mencione o total de itens encontrados antes de listar (ex: "Foram encontrados 3 clientes...").
7. Se o resultado estiver vazio, diga educadamente que não encontrou dados para essa consulta.
8. Seja completo mas objetivo. Não escreva mais de 6 linhas."""
    resposta = llm_conversa.invoke([HumanMessage(content=prompt)])
    return resposta.content

CSS_GLOBAL = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* Reset geral */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Esconder elementos padrão do Streamlit */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header { visibility: hidden; }
[data-testid="stDecoration"] { display: none; }

/* Container principal */
.main .block-container {
    padding: 0.75rem 2rem 1rem 2rem;
    max-width: 1400px;
}

/* Remove espaço excessivo do topo */
.block-container {
    padding-top: 0rem !important;
    padding-bottom: 1rem !important;
}

[data-testid="stAppViewContainer"] > .main {
    padding-top: 0rem;
    margin-left: 240px;
}

div[data-testid="stVerticalBlock"] > div:first-child {
    margin-top: 0;
}

/* ── SIDEBAR LOGO CENTERED ── */
[data-testid="stSidebar"] [data-testid="stImage"] {
    display: flex;
    justify-content: center;
    margin: 0 auto 0.75rem auto;
}
[data-testid="stSidebar"] [data-testid="stImage"] img {
    display: block;
    margin: 0 auto;
}

/* ── SIDEBAR ── */
[data-testid="stSidebar"] {
    background-color: #0D0F18;
    border-right: 1px solid #1E2235;
    padding-top: 1rem;
    transition: all 0.3s ease-in-out;
}
[data-testid="stSidebarNav"] {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    width: 240px;
    background-color: #0D0F18;
    border-right: 1px solid #1E2235;
    padding: 1rem;
}
[data-testid="stSidebar"] > div:first-child {
    padding-top: 0.75rem;
}
[data-testid="stSidebar"] .stButton > button {
    background-color: transparent;
    border-radius: 10px;
    padding: 11px 14px;
    font-size: 0.88rem;
    font-weight: 500;
    color: #8B92A8;
    cursor: pointer;
    transition: all 0.2s ease;
    display: flex;
    align-items: center;
    gap: 10px;
    border: 1px solid transparent;
    width: 100%;
    justify-content: flex-start;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background-color: #1A1D2E;
    color: #E8EAF0;
    border-color: #2A2D3E;
}
[data-testid="stSidebar"] .stButton > button:focus {
    background-color: #1A2744;
    color: #E8EAF0;
    border-color: #4F8EF7;
    box-shadow: none;
}

/* ── CHAT BUBBLES ── */
[data-testid="stChatMessage"] {
    background-color: #13151F;
    border: 1px solid #1E2235;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 8px;
    max-width: 85%;
}
/* User messages — blue tint, right-side */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    background-color: #1A2744;
    border-color: #2A3F6B;
}
/* Assistant messages — default, left-side */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
    background-color: #13151F;
    border-color: #1E2235;
}

/* ── CHAT LAYOUT ── */
.chat-container {
    height: calc(100vh - 200px); /* Ajuste a altura conforme necessário */
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    padding: 1rem 0;
    margin-bottom: 1rem;
}

[data-testid="stChatInput"] {
    background-color: #0D0F18;
    border-top: 1px solid #1E2235;
    padding: 1rem 0;
    position: fixed;
    bottom: 0;
    left: 240px; /* Largura da sidebar */
    right: 0;
    width: auto;
    z-index: 100;
}

@media (max-width: 768px) {
    [data-testid="stChatInput"] {
        left: 0;
    }
}

/* ── CARDS DE KPI / METRIC ── */
[data-testid="stMetric"] {
    background-color: #13151F;
    border: 1px solid #1E2235;
    border-radius: 14px;
    padding: 20px 24px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.25);
    transition: transform 0.2s ease;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    border-color: #4F8EF7;
}
[data-testid="stMetricLabel"] {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #6B7280;
}
[data-testid="stMetricValue"] {
    font-size: 1.8rem;
    font-weight: 700;
    color: #E8EAF0;
}
[data-testid="stMetricDelta"] {
    font-size: 0.8rem;
    font-weight: 500;
}

/* ── CHAT INPUT TEXT AREA ── */
[data-testid="stChatInput"] textarea {
    border-radius: 12px;
    border: 1px solid #2A2D3E !important;
    background-color: #13151F !important;
    color: #E8EAF0 !important;
}
[data-testid="stChatInput"] textarea::placeholder {
    color: #4B5563;
}

/* ── SQL EXPANDER CODE BLOCK ── */
[data-testid="stExpander"] pre,
[data-testid="stExpander"] code {
    font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace !important;
    font-size: 0.82rem;
    background-color: #0B0D14 !important;
    color: #A5D6FF !important;
    border-radius: 8px;
}
[data-testid="stExpander"] .stCodeBlock {
    background-color: #0B0D14;
    border: 1px solid #1E2235;
    border-radius: 8px;
}

/* ── BOTÕES ── */
.stButton > button {
    background-color: #4F8EF7;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 20px;
    font-size: 0.875rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    transition: all 0.2s ease;
    box-shadow: 0 2px 8px rgba(79,142,247,0.3);
}
.stButton > button:hover {
    background-color: #3B7AE8;
    transform: translateY(-1px);
    box-shadow: 0 4px 16px rgba(79,142,247,0.4);
}

/* ── TABELAS/DATAFRAMES ── */
[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid #1E2235;
}

/* ── EXPANDERS ── */
[data-testid="stExpander"] {
    background-color: #13151F;
    border: 1px solid #1E2235;
    border-radius: 10px;
}

/* ── DIVIDERS ── */
hr {
    border-color: #1E2235;
    margin: 1.5rem 0;
}

/* ── SIDEBAR FOOTER PINNED ── */
.sidebar-footer {
    position: fixed;
    bottom: 1.5rem;
    font-size: 0.72rem;
    color: #4B5563;
    text-align: center;
    width: 220px;
    line-height: 1.6;
}

/* Modern Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0B0D14; }
::-webkit-scrollbar-thumb { background: #1E2235; border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: #2A2D3E; }

/* ── CHAT HEADER ── */
.chat-header {
    padding: 0.5rem 0 0.9rem 0;
    border-bottom: 1px solid #1E2235;
    margin-bottom: 0.9rem;
}

.chat-title {
    margin: 0;
    color: #E8EAF0;
    font-size: 1.35rem;
    font-weight: 700;
}

.chat-subtitle {
    margin: 0.28rem 0 0 0;
    color: #6B7280;
    font-size: 0.92rem;
}

@media (max-width: 980px) {
    [data-testid="stSidebarNav"] {
        width: 210px;
    }
    [data-testid="stAppViewContainer"] > .main {
        margin-left: 210px;
    }
    [data-testid="stChatInput"] {
        left: 210px;
    }
}

@media (max-width: 768px) {
    [data-testid="stAppViewContainer"] > .main {
        margin-left: 0;
    }
    [data-testid="stSidebarNav"] {
        position: relative;
        width: 100%;
        border-right: none;
        border-bottom: 1px solid #1E2235;
        height: auto;
    }
    [data-testid="stChatInput"] {
        left: 0;
        width: 100%;
        padding: 1rem;
    }
}
</style>
"""
