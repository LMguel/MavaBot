import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from utils import _limpar_valor, _formatar_brl

def render(db):
    hoje = datetime.now().strftime("%d de %B de %Y")
    st.markdown(f"""
        <h2 style="font-family:'Inter',sans-serif;font-weight:700;color:#E8EAF0;margin:0 0 4px 0;">
            📊 Painel Executivo
        </h2>
        <p style="color:#6B7280;font-size:0.95rem;margin:0 0 1rem 0;">
            {hoje}
        </p>
    """, unsafe_allow_html=True)
    st.divider()

    # Métricas Principais
    c1, c2, c3, c4 = st.columns(4)
    
    total_fat = _limpar_valor(db.run("SELECT COALESCE(SUM(VLTOTAL), 0) FROM PCPEDC"))
    total_clientes = int(_limpar_valor(db.run("SELECT COUNT(*) FROM PCCLIENT")))
    ticket_medio = _limpar_valor(db.run("SELECT COALESCE(AVG(VLTOTAL), 0) FROM PCPEDC"))
    total_pedidos = int(_limpar_valor(db.run("SELECT COUNT(*) FROM PCPEDC")))

    c1.metric("💰 Faturamento Hoje", _formatar_brl(total_fat), delta="Acumulado geral", delta_color="off")
    c2.metric("🛒 Pedidos Hoje", f"{total_pedidos}", delta="Total registrado", delta_color="off")
    c3.metric("🎫 Ticket Médio", _formatar_brl(ticket_medio), delta="Média por pedido", delta_color="off")
    c4.metric("📦 Pedidos em Aberto", f"{total_clientes}", delta="Clientes ativos", delta_color="off")

    _PLOTLY_BASE = dict(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Inter", color="#8B92A8", size=12),
        title_font=dict(family="Inter", color="#E8EAF0", size=14),
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis=dict(gridcolor='#1E2235', linecolor='#1E2235', zeroline=False),
        yaxis=dict(gridcolor='#1E2235', linecolor='#1E2235', zeroline=False),
    )

    # ── Row 2: Gráficos (60/40) ──────────────────────────────────
    col_chart, col_pie = st.columns([3, 2])

    with col_chart:
        st.markdown(
            '<p style="font-size:0.7rem;font-weight:700;color:#4B5563;text-transform:uppercase;'
            'letter-spacing:0.1em;margin-bottom:0.5rem;">FATURAMENTO POR DIA</p>',
            unsafe_allow_html=True
        )
        dados_graf = db.run("SELECT DATA, SUM(VLTOTAL) FROM PCPEDC GROUP BY DATA ORDER BY DATA")
        try:
            lista_graf = eval(dados_graf) if dados_graf and dados_graf != '[]' else []
            if lista_graf:
                df_graf = pd.DataFrame(lista_graf, columns=["Data", "Total"])
                df_graf["Data"] = pd.to_datetime(df_graf["Data"]).dt.strftime("%d/%m")
                fig = px.bar(df_graf, x="Data", y="Total",
                             color_discrete_sequence=["#4F8EF7"],
                             labels={"Data": "", "Total": "Faturamento (R$)"})
                fig.update_layout(
                    **_PLOTLY_BASE,
                    title="",
                    showlegend=False,
                    height=300
                )
                fig.update_traces(marker_line_width=0)
                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.info(f"Aguardando mais dados históricos para gerar o gráfico. ({e})")

    with col_pie:
        st.markdown(
            '<p style="font-size:0.7rem;font-weight:700;color:#4B5563;text-transform:uppercase;'
            'letter-spacing:0.1em;margin-bottom:0.5rem;">STATUS DOS PEDIDOS</p>',
            unsafe_allow_html=True
        )
        dados_status = db.run("SELECT POSICAO, COUNT(*) FROM PCPEDC GROUP BY POSICAO")
        try:
            lista_status = eval(dados_status) if dados_status and dados_status != '[]' else []
            if lista_status:
                mapa = {'F': 'Faturado', 'L': 'Em Aberto', 'M': 'Manutenção'}
                df_status = pd.DataFrame(lista_status, columns=["Status", "Qtd"])
                df_status["Status"] = df_status["Status"].map(lambda x: mapa.get(x, x))
                fig2 = px.pie(df_status, names="Status", values="Qtd",
                              color="Status",
                              color_discrete_map={
                                  'Faturado':    '#4F8EF7',
                                  'Em Aberto':   '#F59E0B',
                                  'Manutenção': '#EF4444',
                              },
                              hole=0.6)
                pie_layout = {k: v for k, v in _PLOTLY_BASE.items()
                               if k not in ('xaxis', 'yaxis')}
                fig2.update_layout(
                    **pie_layout,
                    title="",
                    showlegend=True,
                    height=300,
                    legend=dict(
                        bgcolor='rgba(0,0,0,0)',
                        font=dict(color="#8B92A8"),
                        orientation="h",
                        yanchor="bottom", y=-0.25,
                        xanchor="center", x=0.5,
                    )
                )
                fig2.update_traces(textposition='inside', textinfo='percent')
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("Sem dados de status.")
        except Exception as e:
            st.error(f"Erro ao carregar status dos pedidos: {e}")

    # ── Row 3: Ranking (largura total) ───────────────────────────
    st.markdown(
        '<h4 style="font-family:\'Inter\',sans-serif;font-weight:600;color:#E8EAF0;'
        'margin:1.5rem 0 0.75rem 0;">🏆 Top Clientes do Mês</h4>',
        unsafe_allow_html=True
    )
    dados_rank = db.run("""
        SELECT C.CLIENTE, C.CIDADE, SUM(P.VLTOTAL) as TOTAL, COUNT(P.NUMPED) as PEDIDOS
        FROM PCPEDC P JOIN PCCLIENT C ON P.CODCLI = C.CODCLI
        GROUP BY C.CLIENTE, C.CIDADE ORDER BY TOTAL DESC LIMIT 10
    """)
    try:
        lista_rank = eval(dados_rank) if dados_rank and dados_rank != '[]' else []
        if lista_rank:
            df_rank = pd.DataFrame(lista_rank, columns=["Cliente", "Cidade", "Volume (R$)", "Pedidos"])
            df_rank.insert(0, "Posição", [f"{i+1}º" for i in range(len(df_rank))])
            df_rank["Volume (R$)"] = df_rank["Volume (R$)"].apply(_formatar_brl)
            st.dataframe(df_rank, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum dado de ranking disponível.")
    except Exception:
        st.error("Erro ao carregar ranking de clientes.")
