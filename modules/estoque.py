# estoque.py — Gestão de Estoque com filtros por departamento, região e status
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
from utils import _limpar_valor, _formatar_brl

_STATUS_CONFIG = {
    "Crítico": {"cor": "#EF4444", "fundo": "#2D1515"},
    "Atenção": {"cor": "#F59E0B", "fundo": "#2D2010"},
    "Normal":  {"cor": "#10B981", "fundo": "#0F2520"},
}

def _badge(status: str) -> str:
    cfg = _STATUS_CONFIG.get(status, _STATUS_CONFIG["Normal"])
    dot = "&#9679;"
    return (
        f'<span style="background:{cfg["fundo"]};color:{cfg["cor"]};'
        f'padding:3px 10px;border-radius:20px;font-size:0.71rem;font-weight:600;'
        f'border:1px solid {cfg["cor"]}33;letter-spacing:0.03em;">'
        f'{dot} {status}</span>'
    )

def _status_label(estoque: float, estoque_min: float) -> str:
    """
    Classifica com base na relação estoque × mínimo:
      - Crítico  : estoque < mínimo  (abaixo do piso)
      - Atenção  : estoque < mínimo × 1.5  (margem curta, menos de 50% de folga)
      - Normal   : estoque >= mínimo × 1.5
    """
    if estoque_min <= 0:
        return "Normal"
    if estoque < estoque_min:
        return "Crítico"
    if estoque < estoque_min * 1.5:
        return "Atenção"
    return "Normal"

def render(db):
    # ── Cabeçalho ─────────────────────────────────────────────────────────────
    st.markdown("""
        <h2 style="font-family:'IBM Plex Mono',monospace;font-weight:700;
                   color:#E8EAF0;margin:0 0 2px 0;letter-spacing:-0.5px;">
            Gestão de Estoque
        </h2>
        <p style="color:#4B5563;font-size:0.88rem;margin:0 0 1.25rem 0;
                  font-family:'IBM Plex Mono',monospace;">
            Inventário · Níveis · Alertas
        </p>
    """, unsafe_allow_html=True)
    st.divider()

    # ── Carrega dados base ─────────────────────────────────────────────────────
    raw = db.run("""
        SELECT
            p.CODPROD,
            p.DESCRICAO,
            p.EMBALAGEM,
            p.PRECO,
            d.DESCRICAO   AS DEPTO,
            e.ESTOQUE,
            e.ESTOQMIN,
            e.CUSTOFIN
        FROM PCPRODUT p
        JOIN PCDEPTO  d ON d.CODEPTO  = p.CODEPTO
        JOIN PCEST    e ON e.CODPROD   = p.CODPROD
        ORDER BY e.ESTOQUE ASC
    """)

    raw_tabpr = db.run("""
        SELECT t.CODPROD, r.DESCREGIAO, t.PVENDA
        FROM PCTABPR t
        JOIN PCREGIAO r ON r.NUMREGIAO = t.NUMREGIAO
        WHERE t.PTABELA = 1
        ORDER BY t.CODPROD
    """)

    try:
        lista = eval(raw) if raw and raw != "[]" else []
        lista_tabpr = eval(raw_tabpr) if raw_tabpr and raw_tabpr != "[]" else []
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return

    if not lista:
        st.info("Nenhum produto cadastrado.")
        return

    df = pd.DataFrame(lista, columns=["Código", "Produto", "Embalagem", "Preço", "Depto", "Estoque", "Estoque Mín.", "Custo"])
    df["Status"]   = df.apply(lambda r: _status_label(r["Estoque"], r["Estoque Mín."]), axis=1)
    df["Cobertura"]= (df["Estoque"] / df["Estoque Mín."].replace(0, 1)).round(1)

    # Tabela de preços por região (pivot: produto → região → preço)
    df_tabpr = pd.DataFrame(lista_tabpr, columns=["Código", "Região", "Preço Região"])

    # ── KPIs ──────────────────────────────────────────────────────────────────
    total_skus   = len(df)
    criticos     = len(df[df["Status"] == "Crítico"])
    atencao      = len(df[df["Status"] == "Atenção"])
    normais      = len(df[df["Status"] == "Normal"])
    abaixo_min   = len(df[df["Estoque"] < df["Estoque Mín."]])
    valor_estoque = (df["Estoque"] * df["Custo"]).sum()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("SKUs Total",         f"{total_skus}")
    c2.metric("🔴 Críticos",        f"{criticos}",   delta=f"-{criticos} alerta" if criticos else "OK",     delta_color="inverse")
    c3.metric("🟡 Atenção",         f"{atencao}",    delta=f"{atencao} revisar"  if atencao  else "OK",     delta_color="inverse")
    c4.metric("Abaixo do Mínimo",   f"{abaixo_min}", delta_color="inverse")
    c5.metric("Valor em Estoque",   _formatar_brl(valor_estoque))

    st.divider()

    # ── Filtros ────────────────────────────────────────────────────────────────
    st.markdown(
        '<p style="font-size:0.68rem;font-weight:700;color:#4B5563;'
        'text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.4rem;">'
        'FILTROS</p>',
        unsafe_allow_html=True,
    )

    deptos_disponiveis  = ["Todos"] + sorted(df["Depto"].unique().tolist())
    status_disponiveis  = ["Todos", "Crítico", "Atenção", "Normal"]
    regioes_disponiveis = ["Todas"] + sorted(df_tabpr["Região"].unique().tolist()) if not df_tabpr.empty else ["Todas"]

    fc1, fc2, fc3, fc4 = st.columns([2, 2, 2, 2])
    with fc1:
        filtro_depto  = st.selectbox("Departamento / Marca", deptos_disponiveis, key="est_depto")
    with fc2:
        filtro_status = st.selectbox("Status de Estoque",    status_disponiveis, key="est_status")
    with fc3:
        filtro_regiao = st.selectbox("Região de Preço",      regioes_disponiveis, key="est_regiao")
    with fc4:
        busca = st.text_input("Buscar produto", placeholder="Digite parte do nome...", key="est_busca")

    # ── Aplica filtros ─────────────────────────────────────────────────────────
    df_filtrado = df.copy()
    if filtro_depto  != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Depto"] == filtro_depto]
    if filtro_status != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Status"] == filtro_status]
    if busca:
        df_filtrado = df_filtrado[df_filtrado["Produto"].str.contains(busca, case=False, na=False)]

    # Se filtrou por região, enriquece com preço regional
    if filtro_regiao != "Todas" and not df_tabpr.empty:
        df_reg = df_tabpr[df_tabpr["Região"] == filtro_regiao][["Código", "Preço Região"]]
        df_filtrado = df_filtrado.merge(df_reg, on="Código", how="left")
    else:
        df_filtrado["Preço Região"] = None

    st.markdown(
        f'<p style="font-size:0.75rem;color:#4B5563;margin:0.5rem 0 0.75rem;">'
        f'{len(df_filtrado)} produto(s) encontrado(s)</p>',
        unsafe_allow_html=True,
    )

    # ── Tabela de inventário ───────────────────────────────────────────────────
    st.markdown(
        '<p style="font-size:0.68rem;font-weight:700;color:#4B5563;'
        'text-transform:uppercase;letter-spacing:0.1em;margin:0.5rem 0 0.75rem;">INVENTÁRIO DETALHADO</p>',
        unsafe_allow_html=True,
    )

    th = ('padding:10px 14px;text-align:left;color:#4B5563;font-size:0.68rem;'
          'font-weight:700;text-transform:uppercase;letter-spacing:0.08em;white-space:nowrap;')

    mostrar_preco_reg = filtro_regiao != "Todas" and "Preço Região" in df_filtrado.columns

    header_extra = f'<th style="{th}text-align:right;">Preço ({filtro_regiao})</th>' if mostrar_preco_reg else ""

    rows_html = ""
    for _, row in df_filtrado.iterrows():
        cobertura_cor = "#EF4444" if row["Cobertura"] < 1 else ("#F59E0B" if row["Cobertura"] < 2 else "#10B981")
        preco_reg_td = ""
        if mostrar_preco_reg:
            val = row.get("Preço Região")
            preco_reg_td = (
                f'<td style="padding:10px 14px;text-align:right;color:#E8EAF0;">'
                f'{_formatar_brl(val) if pd.notna(val) else "—"}</td>'
            )
        rows_html += (
            f'<tr style="border-bottom:1px solid #1A1D2B;">'
            f'<td style="padding:10px 14px;color:#E8EAF0;font-size:0.85rem;">{row["Produto"]}</td>'
            f'<td style="padding:10px 14px;color:#6B7280;font-size:0.82rem;">{row["Depto"]}</td>'
            f'<td style="padding:10px 14px;color:#6B7280;">{row["Embalagem"]}</td>'
            f'<td style="padding:10px 14px;text-align:right;color:#E8EAF0;font-variant-numeric:tabular-nums;">'
            f'{int(row["Estoque"])} / <span style="color:#4B5563">{int(row["Estoque Mín."])}</span></td>'
            f'<td style="padding:10px 14px;text-align:right;color:{cobertura_cor};font-weight:600;">'
            f'{row["Cobertura"]}×</td>'
            f'<td style="padding:10px 14px;text-align:right;color:#E8EAF0;">{_formatar_brl(row["Preço"])}</td>'
            f'{preco_reg_td}'
            f'<td style="padding:10px 14px;text-align:center;">{_badge(row["Status"])}</td>'
            f'</tr>'
        )

    html_table = f"""
<div style="overflow-x:auto;border-radius:10px;border:1px solid #1A1D2B;margin-bottom:1.5rem;">
  <table style="width:100%;border-collapse:collapse;font-family:'IBM Plex Mono',monospace;font-size:0.84rem;">
    <thead>
      <tr style="background:#12141F;">
        <th style="{th}">Produto</th>
        <th style="{th}">Marca</th>
        <th style="{th}">Embal.</th>
        <th style="{th}text-align:right;">Estoque / Mín.</th>
        <th style="{th}text-align:right;">Cobertura</th>
        <th style="{th}text-align:right;">Preço Base</th>
        {header_extra}
        <th style="{th}text-align:center;">Status</th>
      </tr>
    </thead>
    <tbody style="background:#0D0F1A;">
      {rows_html}
    </tbody>
  </table>
</div>
"""
    altura_tabela = max(300, len(df_filtrado) * 44 + 60)
    components.html(html_table, height=altura_tabela, scrolling=False)

    # ── Gráficos lado a lado ───────────────────────────────────────────────────
    col_bar, col_depto = st.columns([3, 2])

    with col_bar:
        st.markdown(
            '<p style="font-size:0.68rem;font-weight:700;color:#4B5563;'
            'text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.5rem;">NÍVEL DE ESTOQUE POR PRODUTO</p>',
            unsafe_allow_html=True,
        )
        df_grafico = df_filtrado.copy()
        df_grafico["Cor"] = df_grafico["Status"].map(
            {"Crítico": "#EF4444", "Atenção": "#F59E0B", "Normal": "#10B981"}
        )
        fig_bar = px.bar(
            df_grafico.sort_values("Estoque"),
            x="Estoque", y="Produto", orientation="h",
            color="Cor", color_discrete_map="identity",
        )
        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="IBM Plex Mono", color="#6B7280", size=11),
            margin=dict(l=10, r=60, t=10, b=20), showlegend=False,
            xaxis=dict(gridcolor="#1A1D2B", zeroline=False),
            yaxis=dict(gridcolor="rgba(0,0,0,0)"),
            height=max(280, len(df_grafico) * 32),
        )
        fig_bar.update_traces(marker_line_width=0, opacity=0.9)
        # Linha de mínimo como anotação
        for _, row in df_grafico.iterrows():
            fig_bar.add_vline(x=row["Estoque Mín."], line_dash="dot",
                              line_color="#334155", line_width=1)
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_depto:
        st.markdown(
            '<p style="font-size:0.68rem;font-weight:700;color:#4B5563;'
            'text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.5rem;">DISTRIBUIÇÃO POR MARCA</p>',
            unsafe_allow_html=True,
        )
        df_depto_agg = (
            df_filtrado.groupby("Depto")
            .agg(Produtos=("Código", "count"), Estoque_Total=("Estoque", "sum"))
            .reset_index()
        )
        fig_pie = px.pie(
            df_depto_agg, names="Depto", values="Estoque_Total",
            color_discrete_sequence=["#4F8EF7","#10B981","#F59E0B","#EF4444","#8B5CF6","#EC4899","#06B6D4"],
            hole=0.55,
        )
        fig_pie.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="IBM Plex Mono", color="#6B7280", size=11),
            margin=dict(l=10, r=10, t=10, b=10),
            showlegend=True,
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#8B92A8"),
                        orientation="v", x=1.02, y=0.5),
            height=300,
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label",
                               textfont_size=10)
        st.plotly_chart(fig_pie, use_container_width=True)

    # ── Preços por região (se filtro ativo) ───────────────────────────────────
    if not df_tabpr.empty:
        st.markdown(
            '<p style="font-size:0.68rem;font-weight:700;color:#4B5563;'
            'text-transform:uppercase;letter-spacing:0.1em;margin:1rem 0 0.75rem;">TABELA DE PREÇOS POR REGIÃO</p>',
            unsafe_allow_html=True,
        )
        # Pivot: produto nas linhas, regiões nas colunas
        df_pivot_base = df_filtrado[["Produto", "Depto", "Preço"]].copy()
        df_pivot_reg  = df_tabpr.copy()
        if filtro_depto != "Todos":
            codigos_filtrados = df_filtrado["Código"].tolist()
            df_pivot_reg = df_pivot_reg[df_pivot_reg["Código"].isin(codigos_filtrados)]
        if busca:
            df_pivot_reg = df_pivot_reg[df_pivot_reg["Código"].isin(df_filtrado["Código"].tolist())]

        df_pivot = df_pivot_reg.pivot_table(
            index="Código", columns="Região", values="Preço Região", aggfunc="first"
        ).reset_index()
        df_pivot = df_pivot.merge(df[["Código","Produto","Depto"]], on="Código", how="left")

        regioes_cols = [c for c in df_pivot.columns if c not in ["Código","Produto","Depto"]]
        cols_show = ["Produto","Depto"] + regioes_cols

        # Formata valores
        df_show = df_pivot[cols_show].copy()
        for col in regioes_cols:
            df_show[col] = df_show[col].apply(lambda v: _formatar_brl(v) if pd.notna(v) else "—")

        st.dataframe(df_show, use_container_width=True, hide_index=True)