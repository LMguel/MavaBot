# MavAI

Assistente de dados para a MAVA Distribuidora com duas interfaces:
- Web app em Streamlit (chat + painel executivo + gestão de estoque)
- Webhook para WhatsApp (FastAPI + WhatsApp Cloud API)

O projeto usa um agente SQL com LLM para transformar perguntas em linguagem natural em consultas no banco e responder em português.

## Como o projeto funciona

### 1) Entrada da aplicação web
- `app.py` inicializa a página do Streamlit e carrega `style.css`.
- Lê variáveis do `.env` e cria recursos compartilhados com cache:
  - conexão com banco (`SQLDatabase`)
  - agente SQL (`create_react_agent`)
  - LLM de conversa
- Registra 3 páginas no menu lateral:
  - `modules/ia.py` (assistente)
  - `modules/painel.py` (KPIs e gráficos)
  - `modules/estoque.py` (inventário)

### 2) Núcleo de IA e SQL
Arquivo principal: `mavai_core.py`.

Responsabilidades:
- Criar recursos (`criar_recursos`) com LangChain + LangGraph + Groq.
- Manter histórico por `user_id` em memória.
- Responder perguntas (`responder`) usando prompt de sistema com regras de segurança:
  - apenas leitura
  - limite de resultados
  - resposta em português
  - foco em contexto de negócio

Fluxo simplificado de resposta:
1. Recebe pergunta do usuário.
2. Atualiza histórico em memória.
3. Injeta histórico no prompt de sistema.
4. Executa agente SQL com ferramentas do toolkit.
5. Extrai a mensagem final do agente.
6. Retorna resposta para a interface (web ou WhatsApp).

### 3) Módulo de Assistente (chat)
Arquivo: `modules/ia.py`.

- Renderiza histórico com `st.chat_message`.
- Envia pergunta para `mavai_core.responder`.
- Exibe resposta e mantém conversa na sessão do Streamlit.
- Possui botão para limpar histórico da sessão.

### 4) Painel Executivo
Arquivo: `modules/painel.py`.

Consulta o banco e mostra:
- métricas principais (faturamento, pedidos, ticket médio, etc.)
- gráfico de faturamento por dia
- distribuição de status dos pedidos
- ranking de clientes

### 5) Gestão de Estoque
Arquivo: `modules/estoque.py`.

- Lista produtos e níveis de estoque.
- Classifica status (crítico, atenção, normal).
- Mostra tabela detalhada e gráfico horizontal por produto.

### 6) Banco de dados de exemplo
Arquivo: `criar_banco.py`.

Cria e popula `winthor_fake.db` com tabelas:
- `PCCLIENT`
- `PCPRODUT`
- `PCPEDC`
- `PCPEDI`
- `PCTABPR`

Inclui dados fictícios de clientes, pedidos, itens e preço por região.

### 7) Integração WhatsApp
Arquivos: `whatsapp/server.py`, `whatsapp/meta_client.py`, `whatsapp/config.py`.

Fluxo:
1. Meta chama `GET /webhook` para verificação (token).
2. Meta envia mensagens para `POST /webhook`.
3. Serviço lê a mensagem, evita duplicidade por ID e chama `responder`.
4. Resposta é enviada ao usuário via WhatsApp Cloud API.

## Estrutura do projeto

```text
MavAI/
├─ app.py
├─ mavai_core.py
├─ criar_banco.py
├─ utils.py
├─ style.css
├─ fewshot_examples.json
├─ winthor_fake.db
├─ modules/
│  ├─ ia.py
│  ├─ painel.py
│  └─ estoque.py
└─ whatsapp/
   ├─ config.py
   ├─ meta_client.py
   └─ server.py
```

## Pré-requisitos

- Python 3.10+
- Chave de API da Groq
- (Opcional) Conta Meta/WhatsApp Cloud API para webhook

## Instalação

### 1) Criar ambiente virtual

No PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2) Instalar dependências

```powershell
pip install streamlit python-dotenv pandas plotly fastapi uvicorn requests langchain-community langchain-core langchain-groq langgraph
```

### 3) Configurar variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto.

Exemplo:

```env
# Banco
DB_URL=sqlite:///winthor_fake.db

# Groq
GROQ_API=seu_token_groq
GROQ_API_KEY=seu_token_groq
GROQ_MODEL=llama-3.3-70b-versatile
DEBUG_SQL=0

# WhatsApp Cloud API (somente se usar webhook)
WHATSAPP_VERIFY_TOKEN=seu_verify_token
WHATSAPP_ACCESS_TOKEN=seu_access_token
WHATSAPP_PHONE_NUMBER_ID=seu_phone_number_id
WHATSAPP_GRAPH_API_VERSION=v19.0
MAX_REPLY_CHARS=1200
```

Observação:
- A interface Streamlit usa `GROQ_API`.
- O módulo de configuração do WhatsApp valida `GROQ_API_KEY`.
- Na prática, mantenha os dois com o mesmo valor para evitar erro de inicialização.

## Como executar

### 1) (Opcional) Recriar banco de exemplo

```powershell
python criar_banco.py
```

### 2) Iniciar aplicação web (Streamlit)

```powershell
streamlit run app.py
```

### 3) Iniciar webhook WhatsApp (FastAPI)

```powershell
uvicorn whatsapp.server:app --host 0.0.0.0 --port 8000 --reload
```

Endpoints:
- `GET /webhook` (verificação)
- `POST /webhook` (recebimento de mensagens)

## Exemplos de perguntas

- "Quais são os 5 clientes que mais compraram neste mês?"
- "Qual o faturamento por região nos últimos 7 dias?"
- "Quais produtos estão com estoque crítico?"
- "Compare pedidos faturados e em aberto hoje."

## Principais decisões técnicas

- Agente SQL baseado em ferramentas do toolkit (`list_tables`, `schema`, `query_checker`, `query`).
- Histórico por usuário em memória para manter contexto.
- Interface única para web e WhatsApp reutilizando `mavai_core.responder`.
- Banco SQLite local para facilitar testes e demonstrações.

## Limitações atuais

- Histórico em memória (reinicia ao reiniciar o processo).
- Sem autenticação/controle de acesso por perfil na interface web.
- Não há suíte de testes automatizados no repositório neste momento.

## Próximos passos sugeridos

- Criar `requirements.txt` fixando versões.
- Persistir histórico em banco (ex.: SQLite/PostgreSQL).
- Adicionar testes para consultas críticas e fluxos do webhook.
- Incluir observabilidade (logs estruturados e métricas).
