# cria_banco.py
import sqlite3
from datetime import datetime, timedelta

DB_NAME = 'winthor_fake.db'

def criar_banco():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # Limpar tudo
    cur.execute('DROP TABLE IF EXISTS PCPEDI')
    cur.execute('DROP TABLE IF EXISTS PCPEDC')
    cur.execute('DROP TABLE IF EXISTS PCTABPR')
    cur.execute('DROP TABLE IF EXISTS PCCLIENT')
    cur.execute('DROP TABLE IF EXISTS PCPRODUT')

    # =========================================
    # PCCLIENT
    # =========================================
    cur.execute('''
        CREATE TABLE PCCLIENT (
            CODCLI      INTEGER PRIMARY KEY,
            CLIENTE     TEXT,
            CNPJ        TEXT,
            CIDADE      TEXT,
            ESTADO      TEXT,
            LIMITE_CRED REAL,
            DTULTCOMP   DATE,
            NUMREGIAO   INTEGER
        )
    ''')

    hoje   = datetime.now().date()
    ontem  = hoje - timedelta(days=1)
    d2     = hoje - timedelta(days=2)
    d3     = hoje - timedelta(days=3)
    d4     = hoje - timedelta(days=4)
    d5     = hoje - timedelta(days=5)
    d6     = hoje - timedelta(days=6)
    d7     = hoje - timedelta(days=7)
    fev15  = '2026-02-15'
    fev20  = '2026-02-20'
    fev25  = '2026-02-25'
    fev28  = '2026-02-28'

    # NUMREGIAO: 1=Capital, 2=Litoral Norte, 3=Interior Sul
    clientes = [
        (1,  'Supermercado Angra',        '12.345.678/0001-90', 'Angra dos Reis',  'RJ',  60000.00, str(hoje),  2),
        (2,  'Padaria do Ze',             '98.765.432/0001-10', 'Paraty',           'RJ',  15000.00, str(hoje),  2),
        (3,  'Lanchonete Central',        '11.222.333/0001-44', 'Rio de Janeiro',   'RJ',   5000.00, str(d3),    1),
        (4,  'Mercadinho do Bairro',      '55.666.777/0001-88', 'Niteroi',          'RJ',  25000.00, str(hoje),  1),
        (5,  'Hotel Maravilha',           '88.999.000/0001-22', 'Buzios',           'RJ', 100000.00, str(ontem), 2),
        (6,  'Restaurante Sabor da Casa', '22.333.444/0001-55', 'Cabo Frio',        'RJ',  35000.00, str(d2),    2),
        (7,  'Doceria Mel e Canela',      '33.444.555/0001-66', 'Petropolis',       'RJ',  12000.00, str(d5),    3),
        (8,  'Atacado Boa Compra',        '44.555.666/0001-77', 'Rio de Janeiro',   'RJ', 200000.00, str(hoje),  1),
        (9,  'Cafe Expresso Ltda',        '66.777.888/0001-99', 'Volta Redonda',    'RJ',   8000.00, str(d7),    3),
        (10, 'Sorveteria Tropical',       '77.888.999/0001-11', 'Macae',            'RJ',  18000.00, str(ontem), 2),
        (11, 'Emporio Natural',           '99.000.111/0001-33', 'Nova Friburgo',    'RJ',  22000.00, fev28,      3),
        (12, 'Cantina do Italiano',       '10.111.222/0001-44', 'Teresopolis',      'RJ',  16000.00, fev25,      3),
    ]
    cur.executemany('INSERT INTO PCCLIENT VALUES (?,?,?,?,?,?,?,?)', clientes)

    # =========================================
    # PCPRODUT — renomear CODEPT para CODEPTO
    # =========================================
    cur.execute('''
        CREATE TABLE PCPRODUT (
            CODPROD   INTEGER PRIMARY KEY,
            DESCRICAO TEXT,
            EMBALAGEM TEXT,
            PRECO     REAL,
            ESTOQUE   INTEGER,
            CODEPTO   INTEGER        -- ← era CODEPT
        )
    ''')

    # produtos — mesmos dados, só muda o nome da coluna
    # CODEPTO: 8=DUCOCO, 9=VIGOR, 10=DANONE
    produtos = [
        (101, 'Iogurte Morango 1L',             'CX/6',   8.50, 150, 10),
        (102, 'Iogurte Grego Natural 500g',      'UN',    12.00,  80, 10),
        (103, 'Bebida Lactea Chocolate 200ml',   'FD/12',  4.20, 300,  9),
        (104, 'Iogurte Desnatado 1kg',           'UN',    15.00,  45, 10),
        (105, 'Kefir de Frutas Vermelhas',       'UN',     9.90,  20,  9),
        (106, 'Iogurte Grego Mel 500g',          'UN',    13.50,  65, 10),
        (107, 'Bebida Lactea Morango 1L',        'CX/6',   6.80, 220,  9),
        (108, 'Iogurte Integral Natural 1kg',    'UN',    11.00,  10, 10),
        (109, 'Petit Suisse Morango 360g',       'UN',     7.90,  28,  9),
        (110, 'Coalhada Fresca 500g',            'UN',     8.20,  12,  9),
        (111, 'Iogurte Zero Lactose Morango 1L', 'CX/4',  14.50,  55, 10),
        (112, 'Bebida Lactea Vitamina Banana',   'FD/12',  5.10, 180,  9),
        (113, 'Iogurte Grego Frutas Vermelhas',  'UN',    13.90,   5, 10),
        (114, 'Leite Fermentado 80g (Pack 6)',   'FD/4',   9.20, 400,  8),
        (115, 'Iogurte Protein Baunilha 250g',  'UN',    16.90,   8,  8),
    ]
    cur.executemany('INSERT INTO PCPRODUT VALUES (?,?,?,?,?,?)', produtos)

    # =========================================
    # PCPEDC
    # =========================================
    cur.execute('''
        CREATE TABLE PCPEDC (
            NUMPED    INTEGER PRIMARY KEY,
            CODCLI    INTEGER,
            DATA      DATE,
            VLTOTAL   REAL,
            POSICAO   TEXT,
            CODFILIAL INTEGER,
            FOREIGN KEY (CODCLI) REFERENCES PCCLIENT(CODCLI)
        )
    ''')

    pedidos = [
        # HOJE
        (10001,1, str(hoje),  5200.00,'F',1),
        (10002,2, str(hoje),   850.00,'L',1),
        (10003,4, str(hoje), 12500.00,'F',1),
        (10004,8, str(hoje), 28000.00,'F',2),
        (10005,8, str(hoje), 15300.00,'M',2),
        (10006,1, str(hoje),  3100.00,'L',1),
        (10007,10,str(hoje),  2200.00,'L',1),
        # ONTEM
        (10008,1, str(ontem),  1200.50,'F',1),
        (10009,5, str(ontem),  8900.00,'F',1),
        (10010,5, str(ontem),  4200.00,'F',1),
        (10011,2, str(ontem),   600.00,'F',1),
        (10012,10,str(ontem),  1800.00,'F',1),
        # 2 DIAS
        (10013,6, str(d2),  3500.00,'F',1),
        (10014,6, str(d2),  2100.00,'F',1),
        (10015,8, str(d2), 22000.00,'F',2),
        (10016,1, str(d2),  4800.00,'F',1),
        # 3 DIAS
        (10017,3, str(d3),   950.00,'F',1),
        (10018,4, str(d3),  6700.00,'F',1),
        (10019,7, str(d3),  1100.00,'F',1),
        # 4 DIAS
        (10020,5, str(d4),  5500.00,'F',1),
        (10021,9, str(d4),   780.00,'F',1),
        (10022,1, str(d4),  2900.00,'F',1),
        # 5 DIAS
        (10023,7, str(d5),  1450.00,'F',1),
        (10024,2, str(d5),   520.00,'F',1),
        (10025,8, str(d5), 18500.00,'F',2),
        # 6 DIAS
        (10026,4, str(d6),  3200.00,'F',1),
        (10027,6, str(d6),  4100.00,'F',1),
        (10028,10,str(d6),  1350.00,'F',1),
        # 7 DIAS
        (10029,1, str(d7),  6100.00,'F',1),
        (10030,9, str(d7),   450.00,'F',1),
        (10031,5, str(d7),  7200.00,'F',1),
        # FEVEREIRO
        (10032,1, fev15,  3000.00,'F',1),
        (10033,1, fev20,  4500.00,'F',2),
        (10034,5, fev15,  9800.00,'F',1),
        (10035,5, fev25,  6300.00,'F',1),
        (10036,2, fev20,  1200.00,'F',1),
        (10037,8, fev25, 35000.00,'F',2),
        (10038,6, fev28,  2800.00,'F',1),
        (10039,11,fev28,  3400.00,'F',1),
        (10040,12,fev25,  2100.00,'F',1),
        (10041,3, fev15,   700.00,'F',1),
        (10042,4, fev20,  8200.00,'F',1),
        (10043,7, fev28,  1650.00,'F',1),
        (10044,10,fev15,  2400.00,'F',1),
        (10045,9, fev20,   600.00,'F',1),
    ]
    cur.executemany('INSERT INTO PCPEDC VALUES (?,?,?,?,?,?)', pedidos)

    # =========================================
    # PCPEDI
    # =========================================
    cur.execute('''
        CREATE TABLE PCPEDI (
            NUMPED  INTEGER,
            CODPROD INTEGER,
            QTBAIXA REAL,
            PVENDA  REAL,
            FOREIGN KEY (NUMPED)  REFERENCES PCPEDC(NUMPED),
            FOREIGN KEY (CODPROD) REFERENCES PCPRODUT(CODPROD)
        )
    ''')

    itens = [
        (10001,101,20,8.50),(10001,103,48,4.20),(10001,107,12,6.80),
        (10002,102,3,12.00),(10002,109,5,7.90),
        (10003,101,30,8.50),(10003,104,20,15.00),(10003,106,15,13.50),
        (10004,114,100,9.20),(10004,107,60,6.80),(10004,103,80,4.20),(10004,112,50,5.10),
        (10005,101,40,8.50),(10005,111,20,14.50),(10005,104,30,15.00),
        (10006,102,10,12.00),(10006,105,5,9.90),(10006,106,8,13.50),
        (10007,103,20,4.20),(10007,109,8,7.90),
        (10008,101,10,8.50),(10008,107,8,6.80),
        (10009,103,50,4.20),(10009,114,40,9.20),(10009,112,30,5.10),
        (10010,101,25,8.50),(10010,104,15,15.00),(10010,106,10,13.50),
        (10011,102,3,12.00),(10011,109,4,7.90),
        (10012,107,10,6.80),(10012,111,8,14.50),
        (10013,103,30,4.20),(10013,107,15,6.80),(10013,112,20,5.10),
        (10014,101,15,8.50),(10014,106,8,13.50),
        (10015,114,120,9.20),(10015,107,80,6.80),(10015,103,100,4.20),
        (10016,101,20,8.50),(10016,104,12,15.00),(10016,111,10,14.50),
        (10017,102,5,12.00),(10017,109,3,7.90),
        (10018,101,25,8.50),(10018,103,40,4.20),(10018,107,18,6.80),
        (10019,105,4,9.90),(10019,110,5,8.20),
        (10020,103,35,4.20),(10020,114,25,9.20),(10020,112,20,5.10),
        (10021,102,3,12.00),(10021,109,4,7.90),
        (10022,101,15,8.50),(10022,106,6,13.50),(10022,111,5,14.50),
        (10023,105,6,9.90),(10023,110,4,8.20),(10023,113,3,13.90),
        (10024,102,2,12.00),(10024,109,3,7.90),
        (10025,114,80,9.20),(10025,107,60,6.80),(10025,103,70,4.20),
        (10026,101,18,8.50),(10026,103,25,4.20),(10026,107,12,6.80),
        (10027,112,30,5.10),(10027,103,20,4.20),(10027,107,15,6.80),
        (10028,109,5,7.90),(10028,111,4,14.50),
        (10029,101,30,8.50),(10029,104,15,15.00),(10029,107,20,6.80),
        (10030,102,2,12.00),(10030,109,3,7.90),
        (10031,103,40,4.20),(10031,114,30,9.20),(10031,112,25,5.10),
        (10032,101,20,8.50),(10032,107,15,6.80),
        (10033,101,25,8.50),(10033,104,10,15.00),(10033,106,8,13.50),
        (10034,103,60,4.20),(10034,114,50,9.20),(10034,112,40,5.10),
        (10035,101,30,8.50),(10035,103,35,4.20),(10035,107,20,6.80),
        (10036,102,4,12.00),(10036,109,5,7.90),
        (10037,114,200,9.20),(10037,107,150,6.80),(10037,103,180,4.20),(10037,112,100,5.10),
        (10038,112,20,5.10),(10038,107,12,6.80),(10038,103,15,4.20),
        (10039,101,15,8.50),(10039,106,8,13.50),(10039,111,6,14.50),
        (10040,102,5,12.00),(10040,105,3,9.90),(10040,110,4,8.20),
        (10041,102,3,12.00),(10041,109,2,7.90),
        (10042,101,35,8.50),(10042,103,45,4.20),(10042,107,25,6.80),
        (10043,105,5,9.90),(10043,110,4,8.20),(10043,113,3,13.90),
        (10044,107,10,6.80),(10044,103,15,4.20),(10044,111,5,14.50),
        (10045,102,3,12.00),(10045,109,4,7.90),
    ]
    cur.executemany('INSERT INTO PCPEDI VALUES (?,?,?,?)', itens)

    # =========================================
    # PCTABPR — remover CODEPT, fica só NUMREGIAO/CODPROD/PVENDA/PTABELA
    # =========================================
    cur.execute('''
        CREATE TABLE PCTABPR (
            NUMREGIAO INTEGER NOT NULL,
            CODPROD   INTEGER NOT NULL,
            PVENDA    REAL    NOT NULL,
            PTABELA   INTEGER NOT NULL,
            PRIMARY KEY (NUMREGIAO, PTABELA, CODPROD)
        )
    ''')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_pctabpr ON PCTABPR (NUMREGIAO, CODPROD)')

    # Popular PCTABPR sem CODEPT
    cur.execute("SELECT CODPROD, PRECO FROM PCPRODUT")
    prods = cur.fetchall()
    fatores = {1: 1.00, 2: 1.05, 3: 1.08}
    PTABELA = 1
    tabpr = []
    for regiao, fator in fatores.items():
        for codprod, preco in prods:
            pvenda = round(float(preco) * fator, 2)
            tabpr.append((regiao, codprod, pvenda, PTABELA))

    cur.executemany(
        'INSERT OR REPLACE INTO PCTABPR (NUMREGIAO, CODPROD, PVENDA, PTABELA) VALUES (?,?,?,?)',
        tabpr
    )

    conn.commit()
    conn.close()

    print(f"\n✅ Banco '{DB_NAME}' criado com sucesso!")
    print(f"   → {len(clientes)} clientes  (regiões 1, 2, 3)")
    print(f"   → {len(produtos)} produtos  (CODEPT: 8=DUCOCO, 9=VIGOR, 10=DANONE)")
    print(f"   → {len(pedidos)} pedidos    (F={sum(1 for p in pedidos if p[4]=='F')} | L={sum(1 for p in pedidos if p[4]=='L')} | M={sum(1 for p in pedidos if p[4]=='M')})")
    print(f"   → {len(itens)} itens de pedido")
    print(f"   → {len(tabpr)} linhas em PCTABPR  (3 regiões × {len(produtos)} produtos)")
    print(f"\n   Consulta que o colaborador pediu (DUCOCO / região 3):")
    print( "   SELECT p.DESCRICAO, t.PVENDA FROM PCTABPR t")
    print( "   JOIN PCPRODUT p ON p.CODPROD = t.CODPROD")
    print( "   WHERE t.NUMREGIAO = 3 AND t.CODEPT = 8;\n")

if __name__ == "__main__":
    criar_banco()
