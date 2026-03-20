# cria_banco.py — Banco fake espelhando schema real do Winthor
# Tabelas derivadas do script pcmov/PBI: pcmov, pcprodut, pcdepto, pcclient,
# pcregiao, pcpraca, pcusuari, pcsuperv, pcpedc, pcest, pcnfsaid
# Marcas: Vigor, Danone, DuCoco, Regina Festas, Xandô, Piracanjuba

import sqlite3
from datetime import datetime, timedelta
import random

DB_NAME = "winthor_fake.db"
random.seed(42)

# ── Datas de referência ───────────────────────────────────────────────────────
hoje   = datetime.now().date()
d      = lambda n: str(hoje - timedelta(days=n))
fev    = lambda dia: f"2026-02-{dia:02d}"
jan    = lambda dia: f"2026-01-{dia:02d}"

def criar_banco():
    conn = sqlite3.connect(DB_NAME)
    cur  = conn.cursor()

    # Limpa tudo
    for t in [
        "PCMOV","PCNFSAID","PCPEDC","PCPEDI","PCEST",
        "PCPRODUT","PCDEPTO","PCCLIENT","PCREGIAO","PCPRACA",
        "PCUSUARI","PCSUPERV","PCTABPR",
    ]:
        cur.execute(f"DROP TABLE IF EXISTS {t}")

    # =========================================================================
    # PCDEPTO — departamentos (marcas/categorias)
    # =========================================================================
    cur.execute("""
        CREATE TABLE PCDEPTO (
            CODEPTO   INTEGER PRIMARY KEY,
            DESCRICAO TEXT NOT NULL
        )
    """)
    deptos = [
        (8,  "DUCOCO"),
        (9,  "VIGOR"),
        (10, "DANONE"),
        (11, "REGINA FESTAS"),
        (12, "XANDO"),
        (13, "PIRACANJUBA"),
        (14, "OUTROS LATICINIOS"),
    ]
    cur.executemany("INSERT INTO PCDEPTO VALUES (?,?)", deptos)

    # =========================================================================
    # PCREGIAO — regiões de venda
    # =========================================================================
    cur.execute("""
        CREATE TABLE PCREGIAO (
            NUMREGIAO   INTEGER PRIMARY KEY,
            DESCREGIAO  TEXT NOT NULL
        )
    """)
    cur.executemany("INSERT INTO PCREGIAO VALUES (?,?)", [
        (1, "Capital / Grande Rio"),
        (2, "Litoral Norte / Costa Verde"),
        (3, "Interior Sul / Serrana"),
    ])

    # =========================================================================
    # PCPRACA — praças (zonas de entrega)
    # =========================================================================
    cur.execute("""
        CREATE TABLE PCPRACA (
            CODPRACA  INTEGER PRIMARY KEY,
            DESCPRACA TEXT NOT NULL,
            ROTA      TEXT,
            NUMREGIAO INTEGER,
            FOREIGN KEY (NUMREGIAO) REFERENCES PCREGIAO(NUMREGIAO)
        )
    """)
    cur.executemany("INSERT INTO PCPRACA VALUES (?,?,?,?)", [
        (1, "Rio de Janeiro Centro",   "R01", 1),
        (2, "Niteroi / Sao Goncalo",   "R02", 1),
        (3, "Baixada Fluminense",      "R03", 1),
        (4, "Angra / Paraty",          "R04", 2),
        (5, "Buzios / Cabo Frio",      "R05", 2),
        (6, "Macae / Norte Fluminense","R06", 2),
        (7, "Petropolis / Teresopolis","R07", 3),
        (8, "Volta Redonda / Sul",     "R08", 3),
        (9, "Nova Friburgo / Serrana", "R09", 3),
    ])

    # =========================================================================
    # PCSUPERV — supervisores
    # =========================================================================
    cur.execute("""
        CREATE TABLE PCSUPERV (
            CODSUPERVISOR INTEGER PRIMARY KEY,
            NOME          TEXT NOT NULL
        )
    """)
    cur.executemany("INSERT INTO PCSUPERV VALUES (?,?)", [
        (1, "Carlos Mendes"),
        (2, "Fernanda Lima"),
        (3, "Roberto Souza"),
    ])

    # =========================================================================
    # PCUSUARI — representantes/RCAs (vendedores)
    # =========================================================================
    cur.execute("""
        CREATE TABLE PCUSUARI (
            CODUSUR       INTEGER PRIMARY KEY,
            NOME          TEXT NOT NULL,
            CODSUPERVISOR INTEGER,
            DTTERMINO     DATE,           -- NULL = ativo
            CODPRACA      INTEGER,
            FOREIGN KEY (CODSUPERVISOR) REFERENCES PCSUPERV(CODSUPERVISOR),
            FOREIGN KEY (CODPRACA)      REFERENCES PCPRACA(CODPRACA)
        )
    """)
    cur.executemany("INSERT INTO PCUSUARI VALUES (?,?,?,?,?)", [
        (10, "Andre Figueiredo",   1, None, 1),
        (11, "Beatriz Cardoso",    1, None, 2),
        (12, "Diego Almeida",      1, None, 3),
        (20, "Juliana Ferreira",   2, None, 4),
        (21, "Lucas Prado",        2, None, 5),
        (22, "Marina Costa",       2, None, 6),
        (30, "Paulo Henrique",     3, None, 7),
        (31, "Rafaela Nunes",      3, None, 8),
        (32, "Thiago Barbosa",     3, None, 9),
        (78, "SISTEMA/AJUSTE",     None, "2020-01-01", 1),  # excluído nas queries
    ])

    # =========================================================================
    # PCCLIENT — clientes
    # =========================================================================
    cur.execute("""
        CREATE TABLE PCCLIENT (
            CODCLI       INTEGER PRIMARY KEY,
            CLIENTE      TEXT    NOT NULL,
            CNPJ         TEXT,
            CIDADE       TEXT,
            ESTADO       TEXT    DEFAULT 'RJ',
            LIMITE_CRED  REAL,
            DTULTCOMP    DATE,
            NUMREGIAOCLI INTEGER,
            CODPRACA     INTEGER,
            FOREIGN KEY (NUMREGIAOCLI) REFERENCES PCREGIAO(NUMREGIAO),
            FOREIGN KEY (CODPRACA)     REFERENCES PCPRACA(CODPRACA)
        )
    """)
    clientes = [
        # (CODCLI, CLIENTE, CNPJ, CIDADE, ESTADO, LIMITE, DTULTCOMP, REGIAO, PRACA)
        (1,  "Supermercado Angra",         "12.345.678/0001-90", "Angra dos Reis",   "RJ", 60000, d(0),  2, 4),
        (2,  "Padaria do Ze",              "98.765.432/0001-10", "Paraty",            "RJ", 15000, d(0),  2, 4),
        (3,  "Lanchonete Central",         "11.222.333/0001-44", "Rio de Janeiro",    "RJ",  5000, d(3),  1, 1),
        (4,  "Mercadinho do Bairro",       "55.666.777/0001-88", "Niteroi",           "RJ", 25000, d(0),  1, 2),
        (5,  "Hotel Maravilha",            "88.999.000/0001-22", "Buzios",            "RJ",100000, d(1),  2, 5),
        (6,  "Restaurante Sabor da Casa",  "22.333.444/0001-55", "Cabo Frio",         "RJ", 35000, d(2),  2, 5),
        (7,  "Doceria Mel e Canela",       "33.444.555/0001-66", "Petropolis",        "RJ", 12000, d(5),  3, 7),
        (8,  "Atacado Boa Compra",         "44.555.666/0001-77", "Rio de Janeiro",    "RJ",200000, d(0),  1, 1),
        (9,  "Cafe Expresso Ltda",         "66.777.888/0001-99", "Volta Redonda",     "RJ",  8000, d(7),  3, 8),
        (10, "Sorveteria Tropical",        "77.888.999/0001-11", "Macae",             "RJ", 18000, d(1),  2, 6),
        (11, "Emporio Natural",            "99.000.111/0001-33", "Nova Friburgo",     "RJ", 22000, fev(28),3, 9),
        (12, "Cantina do Italiano",        "10.111.222/0001-44", "Teresopolis",       "RJ", 16000, fev(25),3, 7),
        (13, "Supermercado Rede Facil",    "13.246.579/0001-01", "Rio de Janeiro",    "RJ",150000, d(0),  1, 1),
        (14, "Distribuidora Norte RJ",     "14.357.680/0001-02", "Campos dos G.",     "RJ", 80000, d(2),  2, 6),
        (15, "Mini Mercado Sao Jorge",     "15.468.791/0001-03", "Sao Goncalo",       "RJ", 10000, d(0),  1, 2),
    ]
    cur.executemany("INSERT INTO PCCLIENT VALUES (?,?,?,?,?,?,?,?,?)", clientes)

    # =========================================================================
    # PCPRODUT — produtos (Vigor, Danone, DuCoco, Regina, Xandô, Piracanjuba)
    # =========================================================================
    cur.execute("""
        CREATE TABLE PCPRODUT (
            CODPROD   INTEGER PRIMARY KEY,
            DESCRICAO TEXT    NOT NULL,
            EMBALAGEM TEXT,
            PRECO     REAL,
            CODEPTO   INTEGER,
            PESOLIQ   REAL,
            PESOBRUTO REAL,
            FOREIGN KEY (CODEPTO) REFERENCES PCDEPTO(CODEPTO)
        )
    """)
    produtos = [
        # ── DUCOCO (8) ────────────────────────────────────────────────────────
        (801, "Agua de Coco DuCoco 200ml Tp",    "FD/27",  3.20,  8, 0.20, 0.22),
        (802, "Agua de Coco DuCoco 1L TP",       "CX/12",  7.90,  8, 1.00, 1.10),
        (803, "Agua de Coco DuCoco 330ml Lata",  "FD/12",  4.50,  8, 0.33, 0.36),
        (804, "Creme de Coco DuCoco 200ml",      "CX/24",  4.80,  8, 0.20, 0.22),
        (805, "Leite de Coco DuCoco 200ml",      "CX/24",  3.90,  8, 0.20, 0.22),
        (806, "Leite de Coco DuCoco 1L",         "CX/12",  9.50,  8, 1.00, 1.10),
        # ── VIGOR (9) ─────────────────────────────────────────────────────────
        (901, "Iogurte Vigor Morango 1kg",        "UN",    14.90,  9, 1.00, 1.05),
        (902, "Iogurte Vigor Natural Integral 1kg","UN",   13.50,  9, 1.00, 1.05),
        (903, "Bebida Lactea Vigor Choc 200ml",   "FD/12",  3.80,  9, 0.20, 0.22),
        (904, "Bebida Lactea Vigor Morango 1L",   "CX/6",   6.50,  9, 1.00, 1.10),
        (905, "Petit Suisse Vigor Morango 360g",  "UN",     7.20,  9, 0.36, 0.40),
        (906, "Vigor Grego Natural 500g",         "UN",    11.90,  9, 0.50, 0.54),
        (907, "Vigor Grego Mel e Noz 500g",       "UN",    13.20,  9, 0.50, 0.54),
        (908, "Coalhada Vigor 900g",              "UN",    12.80,  9, 0.90, 0.95),
        (909, "Leite Fermentado Vigor 80g Pc6",   "FD/4",   8.90,  9, 0.48, 0.52),
        # ── DANONE (10) ───────────────────────────────────────────────────────
        (1001,"Activia Ameixa 170g",              "UN",     4.90, 10, 0.17, 0.19),
        (1002,"Activia Natural 170g",             "UN",     4.50, 10, 0.17, 0.19),
        (1003,"Danette Chocolate 90g",            "UN",     2.80, 10, 0.09, 0.10),
        (1004,"Danette Baunilha 90g",             "UN",     2.80, 10, 0.09, 0.10),
        (1005,"Danoninho 100g",                   "UN",     2.50, 10, 0.10, 0.11),
        (1006,"Danoninho Pack 4x100g",            "UN",     9.20, 10, 0.40, 0.44),
        (1007,"Danio Morango 160g",               "UN",     5.90, 10, 0.16, 0.18),
        (1008,"Danio Blueberry 160g",             "UN",     5.90, 10, 0.16, 0.18),
        (1009,"Oikos Grego Natural 400g",         "UN",    15.90, 10, 0.40, 0.44),
        (1010,"Oikos Grego Coco 400g",            "UN",    16.50, 10, 0.40, 0.44),
        # ── REGINA FESTAS (11) ────────────────────────────────────────────────
        (1101,"Creme Chantilly Regina 250ml",     "UN",     8.90, 11, 0.25, 0.27),
        (1102,"Creme Chantilly Regina 1L",        "UN",    22.00, 11, 1.00, 1.08),
        (1103,"Creme de Leite Regina 200g TP",    "CX/24",  3.20, 11, 0.20, 0.22),
        (1104,"Creme de Leite Regina 300g",       "UN",     5.40, 11, 0.30, 0.33),
        (1105,"Doce de Leite Regina 400g",        "UN",     7.80, 11, 0.40, 0.44),
        (1106,"Doce de Leite Regina 1kg",         "UN",    16.90, 11, 1.00, 1.08),
        # ── XANDÔ (12) ────────────────────────────────────────────────────────
        (1201,"Creme Vegetal Xando Coco 200g",    "UN",    12.50, 12, 0.20, 0.22),
        (1202,"Bebida Vegetal Xando Aveia 1L",    "CX/6",  10.90, 12, 1.00, 1.10),
        (1203,"Bebida Vegetal Xando Amendoas 1L", "CX/6",  14.90, 12, 1.00, 1.10),
        (1204,"Iogurte Vegetal Xando Baunilha",   "UN",    11.90, 12, 0.50, 0.54),
        # ── PIRACANJUBA (13) ──────────────────────────────────────────────────
        (1301,"Leite Piracanjuba Integral 1L TP", "CX/12",  4.20, 13, 1.00, 1.10),
        (1302,"Leite Piracanjuba Desnatado 1L",   "CX/12",  4.20, 13, 1.00, 1.10),
        (1303,"Leite Piracanjuba Zero Lact 1L",   "CX/12",  5.90, 13, 1.00, 1.10),
        (1304,"Butter Piracanjuba 200g",          "UN",     8.90, 13, 0.20, 0.22),
        (1305,"Creme de Leite Piracanjuba 200g",  "CX/24",  3.10, 13, 0.20, 0.22),
        (1306,"Manteiga Piracanjuba com Sal 500g","UN",    19.90, 13, 0.50, 0.54),
    ]
    cur.executemany("INSERT INTO PCPRODUT VALUES (?,?,?,?,?,?,?)", produtos)

    # =========================================================================
    # PCEST — estoque por produto/filial
    # =========================================================================
    cur.execute("""
        CREATE TABLE PCEST (
            CODPROD   INTEGER,
            CODFILIAL INTEGER,
            ESTOQUE   REAL,
            ESTOQMIN  REAL,
            CUSTOFIN  REAL,
            PRIMARY KEY (CODPROD, CODFILIAL),
            FOREIGN KEY (CODPROD) REFERENCES PCPRODUT(CODPROD)
        )
    """)
    estoques = []
    for codprod, _, _, preco, _, _, _ in produtos:
        custo = round(preco * 0.65, 2)
        qtd   = random.randint(20, 500)
        minimo= random.randint(10, 50)
        estoques.append((codprod, 1, qtd, minimo, custo))
    cur.executemany("INSERT INTO PCEST VALUES (?,?,?,?,?)", estoques)

    # =========================================================================
    # PCTABPR — tabela de preços por região
    # =========================================================================
    cur.execute("""
        CREATE TABLE PCTABPR (
            NUMREGIAO INTEGER NOT NULL,
            CODPROD   INTEGER NOT NULL,
            PVENDA    REAL    NOT NULL,
            PTABELA   INTEGER NOT NULL DEFAULT 1,
            PRIMARY KEY (NUMREGIAO, PTABELA, CODPROD),
            FOREIGN KEY (CODPROD) REFERENCES PCPRODUT(CODPROD)
        )
    """)
    fatores = {1: 1.00, 2: 1.05, 3: 1.08}
    tabpr   = []
    for codprod, _, _, preco, _, _, _ in produtos:
        for regiao, fator in fatores.items():
            tabpr.append((regiao, codprod, round(preco * fator, 2), 1))
    cur.executemany(
        "INSERT OR REPLACE INTO PCTABPR (NUMREGIAO,CODPROD,PVENDA,PTABELA) VALUES (?,?,?,?)",
        tabpr,
    )

    # =========================================================================
    # PCPEDC — cabeçalho do pedido
    # =========================================================================
    cur.execute("""
        CREATE TABLE PCPEDC (
            NUMPED    INTEGER PRIMARY KEY,
            CODCLI    INTEGER,
            CODUSUR   INTEGER,
            DATA      DATE,
            VLTOTAL   REAL,
            POSICAO   TEXT,     -- F=Faturado, L=Liberado, M=Montagem
            CODFILIAL INTEGER   DEFAULT 1,
            ORIGEMPED TEXT      DEFAULT 'V',  -- V=Vendedor, W=Web, A=Auto
            FOREIGN KEY (CODCLI)  REFERENCES PCCLIENT(CODCLI),
            FOREIGN KEY (CODUSUR) REFERENCES PCUSUARI(CODUSUR)
        )
    """)

    # =========================================================================
    # PCNFSAID — nota fiscal de saída (cabeçalho)
    # =========================================================================
    cur.execute("""
        CREATE TABLE PCNFSAID (
            NUMTRANSVENDA INTEGER PRIMARY KEY,
            NUMPED        INTEGER,
            NUMNOTA       INTEGER,
            CODSUPERVISOR INTEGER,
            CODFILIALNF   INTEGER DEFAULT 1,
            CONDVENDA     INTEGER DEFAULT 1,
            FOREIGN KEY (NUMPED)        REFERENCES PCPEDC(NUMPED),
            FOREIGN KEY (CODSUPERVISOR) REFERENCES PCSUPERV(CODSUPERVISOR)
        )
    """)

    # =========================================================================
    # PCMOV — movimentação (espelho de pcmov real do Winthor)
    # Colunas do script PBI: numtransitem, numtransvenda, numnota, numcar,
    # codcli, codprod, codoper, dtmov, qt, punit, punitcont, custocont,
    # st, basestsaida, percbasered, numped, coddevol, codfilial, codst,
    # vlipi, vlfrete, vloutrasdesp, vlfrete_rateio, vloutros, vlrepasse,
    # codusur, dtcancel
    # =========================================================================
    cur.execute("""
        CREATE TABLE PCMOV (
            NUMTRANSITEM  INTEGER PRIMARY KEY,
            NUMTRANSVENDA INTEGER,
            NUMNOTA       INTEGER,
            NUMCAR        INTEGER,
            CODCLI        INTEGER,
            CODPROD       INTEGER,
            CODOPER       TEXT,    -- S=Saída, SB=Bonificação, ED=Devolução
            DTMOV         DATE,
            QT            REAL,
            PUNIT         REAL,
            PUNITCONT     REAL,
            CUSTOCONT     REAL,
            ST            REAL    DEFAULT 0,
            BASESTSAIDA   REAL    DEFAULT 0,
            PERCBASERED   REAL    DEFAULT 0,
            NUMPED        INTEGER,
            CODDEVOL      INTEGER,
            CODFILIAL     INTEGER DEFAULT 1,
            CODST         TEXT,
            VLIPI         REAL    DEFAULT 0,
            VLFRETE       REAL    DEFAULT 0,
            VLOUTRASDESP  REAL    DEFAULT 0,
            VLFRETE_RATEIO REAL   DEFAULT 0,
            VLOUTROS      REAL    DEFAULT 0,
            VLREPASSE     REAL    DEFAULT 0,
            CODUSUR       INTEGER,
            DTCANCEL      DATE,
            FOREIGN KEY (CODCLI)   REFERENCES PCCLIENT(CODCLI),
            FOREIGN KEY (CODPROD)  REFERENCES PCPRODUT(CODPROD),
            FOREIGN KEY (NUMPED)   REFERENCES PCPEDC(NUMPED),
            FOREIGN KEY (CODUSUR)  REFERENCES PCUSUARI(CODUSUR)
        )
    """)

    # =========================================================================
    # PCPEDI — itens do pedido (JOIN com PCPEDC)
    # =========================================================================
    cur.execute("""
        CREATE TABLE PCPEDI (
            NUMPED  INTEGER,
            CODPROD INTEGER,
            QTBAIXA REAL,
            PVENDA  REAL,
            FOREIGN KEY (NUMPED)  REFERENCES PCPEDC(NUMPED),
            FOREIGN KEY (CODPROD) REFERENCES PCPRODUT(CODPROD)
        )
    """)

    # =========================================================================
    # Geração de pedidos + itens + movimentos
    # =========================================================================

    # Mapeamento vendedor → clientes (quem atende quem)
    vendedor_clientes = {
        10: [3, 8, 13],   # Andre — Rio capital
        11: [4, 15],       # Beatriz — Niteroi
        12: [3, 8],        # Diego — Baixada
        20: [1, 2],        # Juliana — Angra/Paraty
        21: [5, 6],        # Lucas — Buzios/Cabo Frio
        22: [10, 14],      # Marina — Macae
        30: [7, 12],       # Paulo — Petropolis/Teres
        31: [9],           # Rafaela — Volta Redonda
        32: [11],          # Thiago — Nova Friburgo
    }

    # Produtos mais vendidos por categoria (para dar realismo)
    produtos_frequentes = [801,802,901,903,909,1001,1005,1006,1101,1103,1301,1303]
    produtos_todos      = [p[0] for p in produtos]

    pedidos      = []
    itens_pedido = []
    movimentos   = []
    pcnfsaid_rows= []

    numped        = 20000
    numtransitem  = 1
    numtransvenda = 1
    numnota       = 5000

    def gerar_pedido(codcli, codusur, data_str, posicao="F", filial=1, origem="V"):
        nonlocal numped, numtransitem, numtransvenda, numnota

        # Seleciona 3-7 produtos (com viés para os frequentes)
        pool  = random.choices(produtos_frequentes, k=4) + random.choices(produtos_todos, k=2)
        selecionados = list(set(pool))[:random.randint(3, 6)]

        vltotal   = 0.0
        itens_ped = []
        movs      = []

        # Busca preço e custo
        preco_map = {p[0]: p[3] for p in produtos}
        for codprod in selecionados:
            qt     = round(random.uniform(5, 80), 0)
            punit  = preco_map.get(codprod, 5.00)
            custo  = round(punit * 0.65, 2)
            total  = round(qt * punit, 2)
            vltotal += total

            itens_ped.append((numped, codprod, qt, punit))

            movs.append((
                numtransitem, numtransvenda, numnota,
                numped,                        # numcar = numped (simplificado)
                codcli, codprod, "S",          # codoper S = Saída
                data_str,
                qt, punit, punit, custo,
                0, 0, 0,                       # st, basestsaida, percbasered
                numped, None, filial,
                None, 0, 0, 0, 0, 0, 0,
                codusur, None,                 # dtcancel NULL = não cancelado
            ))
            numtransitem += 1

        vltotal = round(vltotal, 2)
        pedidos.append((numped, codcli, codusur, data_str, vltotal, posicao, filial, origem))
        itens_pedido.extend(itens_ped)
        movimentos.extend(movs)

        # Supervisor do vendedor
        sup_map = {10:1,11:1,12:1, 20:2,21:2,22:2, 30:3,31:3,32:3}
        pcnfsaid_rows.append((numtransvenda, numped, numnota, sup_map.get(codusur,1), filial, 1))

        numped        += 1
        numtransvenda += 1
        numnota       += 1

    # ── Pedidos dos últimos 7 dias ─────────────────────────────────────────────
    for dias_atras in range(0, 8):
        data = d(dias_atras)
        for codusur, clientes_list in vendedor_clientes.items():
            # Cada vendedor faz 1-2 pedidos por dia
            for codcli in random.sample(clientes_list, k=min(len(clientes_list), random.randint(1,2))):
                posicao = random.choices(["F","F","F","L","M"], k=1)[0]
                gerar_pedido(codcli, codusur, data, posicao=posicao)

    # ── Pedidos de fevereiro/2026 ─────────────────────────────────────────────
    for dia in [3,5,7,10,12,14,17,19,21,24,26,28]:
        data = fev(dia)
        for codusur, clientes_list in vendedor_clientes.items():
            codcli = random.choice(clientes_list)
            gerar_pedido(codcli, codusur, data, posicao="F")

    # ── Pedidos de janeiro/2026 ───────────────────────────────────────────────
    for dia in [5,10,15,20,25,31]:
        data = jan(dia)
        for codusur, clientes_list in vendedor_clientes.items():
            codcli = random.choice(clientes_list)
            gerar_pedido(codcli, codusur, data, posicao="F")

    # ── Insere tudo ───────────────────────────────────────────────────────────
    cur.executemany("INSERT INTO PCPEDC VALUES (?,?,?,?,?,?,?,?)", pedidos)
    cur.executemany("INSERT INTO PCPEDI VALUES (?,?,?,?)",          itens_pedido)
    cur.executemany(
        "INSERT INTO PCMOV VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        movimentos,
    )
    cur.executemany("INSERT INTO PCNFSAID VALUES (?,?,?,?,?,?)", pcnfsaid_rows)

    conn.commit()
    conn.close()

    print(f"\n✅ Banco '{DB_NAME}' criado com sucesso!")
    print(f"   → {len(deptos)} departamentos (marcas)")
    print(f"   → {len(produtos)} produtos")
    print(f"   → {len(clientes)} clientes  (3 regiões, 9 praças)")
    print(f"   → {len([u for u in [(10,'Andre'),(11,'Beatriz'),(12,'Diego'),(20,'Juliana'),(21,'Lucas'),(22,'Marina'),(30,'Paulo'),(31,'Rafaela'),(32,'Thiago')]])} vendedores  (3 supervisores)")
    print(f"   → {len(pedidos)} pedidos")
    print(f"   → {len(itens_pedido)} itens de pedido")
    print(f"   → {len(movimentos)} movimentos (PCMOV)")
    print(f"\n   Query de teste — top produtos fev/2026:")
    print( "   SELECT p.DESCRICAO, SUM(m.QT) AS qtd")
    print( "   FROM PCMOV m JOIN PCPRODUT p ON p.CODPROD=m.CODPROD")
    print( "   WHERE m.DTMOV BETWEEN '2026-02-01' AND '2026-02-28'")
    print( "     AND m.CODOPER='S' AND m.DTCANCEL IS NULL")
    print( "   GROUP BY p.DESCRICAO ORDER BY qtd DESC LIMIT 10;\n")

if __name__ == "__main__":
    criar_banco()