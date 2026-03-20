# painel_admin.py — Painel Executivo focado em gestores
# KPIs: faturamento do dia/mês, performance por vendedor/supervisor,
# ranking de clientes, produtos mais vendidos, pedidos em aberto
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
from utils import _limpar_valor, _formatar_brl

_PLOTLY_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="IBM Plex Mono", color="#6B7280", size=11),
    title_font=dict(family="IBM Plex Mono", color="#E8EAF0", size=13),
    margin=dict(l=16, r=16, t=36, b=16),
    xaxis=dict(gridcolor="#1A1D2B", linecolor="#1A1D2B", zeroline=False),
    yaxis=dict(gridcolor="#1A1D2B", linecolor="#1A1D2B", zeroline=False),
)

def _label(txt: str) -> str:
    return (
        f'<p style="font-size:0.68rem;font-weight:700;color:#4B5563;'
        f'text-transform:uppercase;letter-spacing:0.1em;margin:1.25rem 0 0.5rem;">'
        f'{txt}</p>'
    )

def render(db):
    hoje        = date.today()
    hoje_str    = hoje.strftime("%d de %B de %Y")
    inicio_mes  = hoje.replace(day=1).isoformat()
    hoje_iso    = hoje.isoformat()
    ontem_iso   = (hoje - timedelta(days=1)).isoformat()
    inicio_sem  = (hoje - timedelta(days=hoje.weekday())).isoformat()
    mes_ant_ini = (hoje.replace(day=1) - timedelta(days=1)).replace(day=1).isoformat()
    mes_ant_fim = (hoje.replace(day=1) - timedelta(days=1)).isoformat()

    # ── Cabeçalho ─────────────────────────────────────────────────────────────
    st.markdown(f"""
        <h2 style="font-family:'IBM Plex Mono',monospace;font-weight:700;
                   color:#E8EAF0;margin:0 0 2px 0;letter-spacing:-0.5px;">
            Painel Executivo
        </h2>
        <p style="color:#4B5563;font-size:0.88rem;margin:0 0 1.25rem 0;
                  font-family:'IBM Plex Mono',monospace;">
            {hoje_str} · Visão gerencial em tempo real
        </p>
    """, unsafe_allow_html=True)
    st.divider()

    # ── KPIs Principais ───────────────────────────────────────────────────────
    fat_hoje  = _limpar_valor(db.run(
        f"SELECT COALESCE(SUM(VLTOTAL),0) FROM PCPEDC WHERE DATA='{hoje_iso}' AND POSICAO='F'"))
    fat_ontem = _limpar_valor(db.run(
        f"SELECT COALESCE(SUM(VLTOTAL),0) FROM PCPEDC WHERE DATA='{ontem_iso}' AND POSICAO='F'"))
    fat_mes   = _limpar_valor(db.run(
        f"SELECT COALESCE(SUM(VLTOTAL),0) FROM PCPEDC WHERE DATA>='{inicio_mes}' AND POSICAO='F'"))
    fat_mes_ant = _limpar_valor(db.run(
        f"SELECT COALESCE(SUM(VLTOTAL),0) FROM PCPEDC WHERE DATA BETWEEN '{mes_ant_ini}' AND '{mes_ant_fim}' AND POSICAO='F'"))
    ticket_medio = _limpar_valor(db.run(
        f"SELECT COALESCE(AVG(VLTOTAL),0) FROM PCPEDC WHERE DATA>='{inicio_mes}' AND POSICAO='F'"))
    ped_abertos = int(_limpar_valor(db.run(
        "SELECT COUNT(*) FROM PCPEDC WHERE POSICAO IN ('L','M')")))
    ped_hoje    = int(_limpar_valor(db.run(
        f"SELECT COUNT(*) FROM PCPEDC WHERE DATA='{hoje_iso}'")))
    total_clientes_ativos = int(_limpar_valor(db.run(
        f"SELECT COUNT(DISTINCT CODCLI) FROM PCPEDC WHERE DATA>='{inicio_mes}'")))

    # Variação dia a dia
    var_dia = ((fat_hoje - fat_ontem) / fat_ontem * 100) if fat_ontem > 0 else 0
    var_mes = ((fat_mes  - fat_mes_ant) / fat_mes_ant * 100) if fat_mes_ant > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Fat. Hoje",        _formatar_brl(fat_hoje),
              delta=f"{var_dia:+.1f}% vs ontem",
              delta_color="normal" if var_dia >= 0 else "inverse")
    c2.metric("📅 Fat. Mês",         _formatar_brl(fat_mes),
              delta=f"{var_mes:+.1f}% vs mês ant.",
              delta_color="normal" if var_mes >= 0 else "inverse")
    c3.metric("🎫 Ticket Médio",     _formatar_brl(ticket_medio),
              delta=f"{ped_hoje} pedidos hoje", delta_color="off")
    c4.metric("⏳ Pedidos em Aberto", f"{ped_abertos}",
              delta=f"{total_clientes_ativos} clientes ativos no mês", delta_color="off")

    st.divider()

    # ── Filtro de período ──────────────────────────────────────────────────────
    st.markdown(_label("PERÍODO DE ANÁLISE"), unsafe_allow_html=True)
    fp1, fp2 = st.columns([2, 6])
    with fp1:
        periodo = st.selectbox("", ["Hoje", "Esta semana", "Este mês", "Mês anterior", "Últimos 90 dias"],
                               key="adm_periodo", label_visibility="collapsed")

    p_ini, p_fim = {
        "Hoje":           (hoje_iso,    hoje_iso),
        "Esta semana":    (inicio_sem,  hoje_iso),
        "Este mês":       (inicio_mes,  hoje_iso),
        "Mês anterior":   (mes_ant_ini, mes_ant_fim),
        "Últimos 90 dias":((hoje - timedelta(days=90)).isoformat(), hoje_iso),
    }[periodo]

    # ── Row 2: Faturamento diário + Status pedidos ─────────────────────────────
    col_fat, col_status = st.columns([3, 2])

    with col_fat:
        st.markdown(_label("FATURAMENTO DIÁRIO — PEDIDOS FATURADOS"), unsafe_allow_html=True)
        dados_graf = db.run(f"""
            SELECT DATA, SUM(VLTOTAL)
            FROM PCPEDC
            WHERE DATA BETWEEN '{p_ini}' AND '{p_fim}' AND POSICAO='F'
            GROUP BY DATA ORDER BY DATA
        """)
        try:
            lista_graf = eval(dados_graf) if dados_graf and dados_graf != "[]" else []
            if lista_graf:
                df_fat = pd.DataFrame(lista_graf, columns=["Data","Total"])
                df_fat["Data"] = pd.to_datetime(df_fat["Data"]).dt.strftime("%d/%m")
                fig = px.bar(df_fat, x="Data", y="Total",
                             color_discrete_sequence=["#4F8EF7"])
                fig.update_layout(**_PLOTLY_BASE, showlegend=False, height=280,
                                  title="", yaxis_tickprefix="R$")
                fig.update_traces(marker_line_width=0, opacity=0.85)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sem faturamento no período selecionado.")
        except Exception as e:
            st.error(f"Erro: {e}")

    with col_status:
        st.markdown(_label("STATUS DOS PEDIDOS"), unsafe_allow_html=True)
        dados_status = db.run(f"""
            SELECT POSICAO, COUNT(*), COALESCE(SUM(VLTOTAL),0)
            FROM PCPEDC
            WHERE DATA BETWEEN '{p_ini}' AND '{p_fim}'
            GROUP BY POSICAO
        """)
        try:
            lista_status = eval(dados_status) if dados_status and dados_status != "[]" else []
            if lista_status:
                mapa_label = {"F":"Faturado","L":"Em Aberto","M":"Montagem"}
                mapa_cor   = {"Faturado":"#4F8EF7","Em Aberto":"#F59E0B","Montagem":"#EF4444"}
                df_st = pd.DataFrame(lista_status, columns=["Posicao","Qtd","Volume"])
                df_st["Status"] = df_st["Posicao"].map(lambda x: mapa_label.get(x,x))
                fig2 = px.pie(df_st, names="Status", values="Qtd", hole=0.6,
                              color="Status", color_discrete_map=mapa_cor)
                pie_base = {k:v for k,v in _PLOTLY_BASE.items() if k not in ("xaxis","yaxis")}
                fig2.update_layout(**pie_base, height=280, showlegend=True,
                                   legend=dict(bgcolor="rgba(0,0,0,0)",
                                               font=dict(color="#8B92A8"),
                                               orientation="h", yanchor="bottom",
                                               y=-0.2, xanchor="center", x=0.5))
                fig2.update_traces(textposition="inside", textinfo="percent+label",
                                   textfont_size=10)
                st.plotly_chart(fig2, use_container_width=True)
        except Exception as e:
            st.error(f"Erro: {e}")

    # ── Row 3: Ranking vendedores + Supervisores ───────────────────────────────
    col_vend, col_sup = st.columns([3, 2])

    with col_vend:
        st.markdown(_label("RANKING DE VENDEDORES"), unsafe_allow_html=True)
        dados_vend = db.run(f"""
            SELECT
                u.NOME,
                COUNT(DISTINCT p.NUMPED)       AS pedidos,
                COALESCE(SUM(p.VLTOTAL), 0)    AS faturamento,
                COUNT(DISTINCT p.CODCLI)        AS clientes
            FROM PCPEDC p
            JOIN PCUSUARI u ON u.CODUSUR = p.CODUSUR
            WHERE p.DATA BETWEEN '{p_ini}' AND '{p_fim}'
              AND p.POSICAO = 'F'
              AND p.CODUSUR NOT IN (78)
            GROUP BY u.NOME
            ORDER BY faturamento DESC
        """)
        try:
            lista_vend = eval(dados_vend) if dados_vend and dados_vend != "[]" else []
            if lista_vend:
                df_vend = pd.DataFrame(lista_vend, columns=["Vendedor","Pedidos","Faturamento","Clientes"])
                df_vend.insert(0, "#", [f"{i+1}°" for i in range(len(df_vend))])
                df_vend["Faturamento"] = df_vend["Faturamento"].apply(_formatar_brl)
                st.dataframe(df_vend, use_container_width=True, hide_index=True)
            else:
                st.info("Sem dados de vendedores no período.")
        except Exception as e:
            st.error(f"Erro: {e}")

    with col_sup:
        st.markdown(_label("FAT. POR SUPERVISOR"), unsafe_allow_html=True)
        dados_sup = db.run(f"""
            SELECT
                s.NOME,
                COALESCE(SUM(p.VLTOTAL), 0) AS faturamento
            FROM PCPEDC p
            JOIN PCUSUARI u ON u.CODUSUR = p.CODUSUR
            JOIN PCSUPERV s ON s.CODSUPERVISOR = u.CODSUPERVISOR
            WHERE p.DATA BETWEEN '{p_ini}' AND '{p_fim}'
              AND p.POSICAO = 'F'
              AND p.CODUSUR NOT IN (78)
            GROUP BY s.NOME
            ORDER BY faturamento DESC
        """)
        try:
            lista_sup = eval(dados_sup) if dados_sup and dados_sup != "[]" else []
            if lista_sup:
                df_sup = pd.DataFrame(lista_sup, columns=["Supervisor","Faturamento"])
                fig_sup = px.bar(df_sup, x="Faturamento", y="Supervisor",
                                 orientation="h",
                                 color_discrete_sequence=["#8B5CF6"])
                fig_sup.update_layout(**_PLOTLY_BASE, showlegend=False, height=220, title="")
                fig_sup.update_xaxes(tickprefix="R$ ")
                fig_sup.update_yaxes(gridcolor="rgba(0,0,0,0)")
                fig_sup.update_traces(marker_line_width=0, opacity=0.85)
                st.plotly_chart(fig_sup, use_container_width=True)
        except Exception as e:
            st.error(f"Erro: {e}")

    # ── Row 4: Top Clientes + Produtos mais vendidos ───────────────────────────
    col_cli, col_prod = st.columns([1, 1])

    with col_cli:
        st.markdown(_label("TOP 10 CLIENTES"), unsafe_allow_html=True)
        dados_cli = db.run(f"""
            SELECT
                c.CLIENTE, c.CIDADE,
                COUNT(DISTINCT p.NUMPED)    AS pedidos,
                COALESCE(SUM(p.VLTOTAL),0)  AS volume
            FROM PCPEDC p
            JOIN PCCLIENT c ON c.CODCLI = p.CODCLI
            WHERE p.DATA BETWEEN '{p_ini}' AND '{p_fim}'
              AND p.POSICAO = 'F'
            GROUP BY c.CLIENTE, c.CIDADE
            ORDER BY volume DESC LIMIT 10
        """)
        try:
            lista_cli = eval(dados_cli) if dados_cli and dados_cli != "[]" else []
            if lista_cli:
                df_cli = pd.DataFrame(lista_cli, columns=["Cliente","Cidade","Pedidos","Volume (R$)"])
                df_cli.insert(0, "#", [f"{i+1}°" for i in range(len(df_cli))])
                df_cli["Volume (R$)"] = df_cli["Volume (R$)"].apply(_formatar_brl)
                st.dataframe(df_cli, use_container_width=True, hide_index=True)
            else:
                st.info("Sem dados de clientes no período.")
        except Exception as e:
            st.error(f"Erro: {e}")

    with col_prod:
        st.markdown(_label("PRODUTOS MAIS VENDIDOS (QTD)"), unsafe_allow_html=True)
        dados_prod = db.run(f"""
            SELECT
                pr.DESCRICAO,
                d.DESCRICAO AS marca,
                SUM(i.QTBAIXA)                       AS qtd,
                ROUND(SUM(i.QTBAIXA * i.PVENDA), 2)  AS faturamento
            FROM PCPEDI  i
            JOIN PCPEDC  p  ON p.NUMPED  = i.NUMPED
            JOIN PCPRODUT pr ON pr.CODPROD = i.CODPROD
            JOIN PCDEPTO  d  ON d.CODEPTO  = pr.CODEPTO
            WHERE p.DATA BETWEEN '{p_ini}' AND '{p_fim}'
              AND p.POSICAO = 'F'
            GROUP BY pr.DESCRICAO, d.DESCRICAO
            ORDER BY qtd DESC LIMIT 10
        """)
        try:
            lista_prod = eval(dados_prod) if dados_prod and dados_prod != "[]" else []
            if lista_prod:
                df_prod = pd.DataFrame(lista_prod, columns=["Produto","Marca","Qtd","Faturamento"])
                df_prod["Faturamento"] = df_prod["Faturamento"].apply(_formatar_brl)
                df_prod["Qtd"] = df_prod["Qtd"].apply(lambda v: f"{int(v):,}".replace(",","."))
                st.dataframe(df_prod, use_container_width=True, hide_index=True)
            else:
                st.info("Sem dados de produtos no período.")
        except Exception as e:
            st.error(f"Erro: {e}")

    # ── Row 5: Faturamento por marca (depto) ───────────────────────────────────
    st.markdown(_label("FATURAMENTO POR MARCA / DEPARTAMENTO"), unsafe_allow_html=True)
    dados_depto = db.run(f"""
        SELECT
            d.DESCRICAO AS marca,
            ROUND(SUM(i.QTBAIXA * i.PVENDA), 2) AS faturamento,
            SUM(i.QTBAIXA)                        AS qtd_vendida
        FROM PCPEDI  i
        JOIN PCPEDC  p  ON p.NUMPED   = i.NUMPED
        JOIN PCPRODUT pr ON pr.CODPROD  = i.CODPROD
        JOIN PCDEPTO  d  ON d.CODEPTO   = pr.CODEPTO
        WHERE p.DATA BETWEEN '{p_ini}' AND '{p_fim}'
          AND p.POSICAO = 'F'
        GROUP BY d.DESCRICAO
        ORDER BY faturamento DESC
    """)
    try:
        lista_depto = eval(dados_depto) if dados_depto and dados_depto != "[]" else []
        if lista_depto:
            df_depto = pd.DataFrame(lista_depto, columns=["Marca","Faturamento","Qtd Vendida"])
            fig_dep = px.bar(
                df_depto, x="Marca", y="Faturamento",
                color="Marca",
                color_discrete_sequence=["#4F8EF7","#10B981","#F59E0B","#EF4444",
                                          "#8B5CF6","#EC4899","#06B6D4"],
                text="Faturamento",
            )
            fig_dep.update_traces(
                texttemplate="R$ %{text:,.0f}", textposition="outside",
                marker_line_width=0, opacity=0.85,
            )
            fig_dep.update_layout(
                **_PLOTLY_BASE, showlegend=False, height=320,
                title="", yaxis_tickprefix="R$ ", uniformtext_minsize=9,
            )
            st.plotly_chart(fig_dep, use_container_width=True)
        else:
            st.info("Sem dados de departamentos no período.")
    except Exception as e:
        st.error(f"Erro: {e}")

    # ── Row 6: Pedidos em aberto (tabela de ação) ─────────────────────────────
    st.markdown(_label("PEDIDOS EM ABERTO — REQUER ATENÇÃO"), unsafe_allow_html=True)
    dados_abertos = db.run("""
        SELECT
            p.NUMPED, c.CLIENTE, u.NOME AS vendedor,
            p.DATA, p.POSICAO, p.VLTOTAL
        FROM PCPEDC p
        JOIN PCCLIENT c ON c.CODCLI  = p.CODCLI
        JOIN PCUSUARI u ON u.CODUSUR = p.CODUSUR
        WHERE p.POSICAO IN ('L','M')
        ORDER BY p.DATA ASC, p.VLTOTAL DESC
        LIMIT 20
    """)
    try:
        lista_ab = eval(dados_abertos) if dados_abertos and dados_abertos != "[]" else []
        if lista_ab:
            df_ab = pd.DataFrame(lista_ab,
                                  columns=["Pedido","Cliente","Vendedor","Data","Status","Valor"])
            mapa_status = {"L":"⚠️ Em Aberto","M":"🔧 Montagem"}
            df_ab["Status"] = df_ab["Status"].map(lambda x: mapa_status.get(x,x))
            df_ab["Valor"]  = df_ab["Valor"].apply(_formatar_brl)
            # Destaque para pedidos mais antigos (> 2 dias)
            df_ab["Data"]   = pd.to_datetime(df_ab["Data"])
            dias_abertos    = (pd.Timestamp(hoje) - df_ab["Data"]).dt.days
            df_ab["Dias em Aberto"] = dias_abertos
            df_ab["Data"]   = df_ab["Data"].dt.strftime("%d/%m/%Y")
            st.dataframe(
                df_ab.sort_values("Dias em Aberto", ascending=False),
                use_container_width=True, hide_index=True,
            )
        else:
            st.success("✅ Nenhum pedido em aberto no momento.")
    except Exception as e:
        st.error(f"Erro: {e}")