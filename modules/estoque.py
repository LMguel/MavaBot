import streamlit as st
import pandas as pd
import plotly.express as px
from utils import _limpar_valor, _formatar_brl

def render(db):
    st.markdown("""
        <h2 style="font-family:'Inter',sans-serif;font-weight:700;color:#E8EAF0;margin:0 0 4px 0;">
            📦 Gestão de Estoque
        </h2>
        <p style="color:#6B7280;font-size:0.95rem;margin:0 0 1rem 0;">
            Monitoramento em tempo real
        </p>
    """, unsafe_allow_html=True)
    st.divider()

    todos = db.run("SELECT CODPROD, DESCRICAO, EMBALAGEM, PRECO, ESTOQUE FROM PCPRODUT ORDER BY ESTOQUE ASC")
    try:
        lista_todos = eval(todos) if todos and todos != '[]' else []
        if lista_todos:
            df_all = pd.DataFrame(lista_todos, columns=["Código", "Produto", "Embalagem", "Preço", "Estoque"])

            # Métricas de Estoque
            c1, c2, c3 = st.columns(3)
            criticos = len(df_all[df_all["Estoque"] < 20])
            normais = len(df_all[df_all["Estoque"] > 50])
            
            c1.metric("📦 Total de SKUs", f"{len(df_all)} itens")
            c2.metric("⚠️ Produtos Críticos", f"{criticos} itens", delta="- crítico" if criticos > 0 else "OK")
            c3.metric("✅ Estoque Saudável", f"{normais} itens")

            st.markdown(
                '<p style="font-size:0.7rem;font-weight:700;color:#4B5563;text-transform:uppercase;'
                'letter-spacing:0.1em;margin:1.25rem 0 0.5rem;">INVENTÁRIO DETALHADO</p>',
                unsafe_allow_html=True
            )

            # Preparar dados para visualização
            df_view = df_all.copy()
            df_view["Status"] = df_view["Estoque"].apply(
                lambda e: "🔴 Crítico" if e < 20 else ("🟡 Atenção" if e <= 50 else "🟢 Normal")
            )
            df_view["Preço"] = df_view["Preço"].apply(_formatar_brl)

            # ── HTML table with inline status badges ────────────────
            def _make_badge(status_text):
                if "Cítico" in status_text or "Crítico" in status_text:
                    return ('<span style="background:#EF4444;color:#fff;padding:2px 12px;'
                            'border-radius:20px;font-size:0.72rem;font-weight:600;'
                            'letter-spacing:0.03em;">&#9679; Crítico</span>')
                elif "Atenção" in status_text:
                    return ('<span style="background:#F59E0B;color:#111;padding:2px 12px;'
                            'border-radius:20px;font-size:0.72rem;font-weight:600;'
                            'letter-spacing:0.03em;">&#9679; Atenção</span>')
                else:
                    return ('<span style="background:#10B981;color:#fff;padding:2px 12px;'
                            'border-radius:20px;font-size:0.72rem;font-weight:600;'
                            'letter-spacing:0.03em;">&#9679; Normal</span>')

            rows_html = ""
            for _, row in df_view.iterrows():
                rows_html += (
                    f'<tr style="border-bottom:1px solid #1E2235;">'
                    f'<td style="padding:12px 16px;color:#E8EAF0;">{row["Produto"]}</td>'
                    f'<td style="padding:12px 16px;color:#8B92A8;">{row["Embalagem"]}</td>'
                    f'<td style="padding:12px 16px;text-align:right;color:#E8EAF0;">{int(row["Estoque"])} un</td>'
                    f'<td style="padding:12px 16px;text-align:right;color:#E8EAF0;">{row["Preço"]}</td>'
                    f'<td style="padding:12px 16px;text-align:center;">{_make_badge(row["Status"])}</td>'
                    f'</tr>'
                )

            th_style = 'padding:12px 16px;text-align:left;color:#6B7280;font-size:0.72rem;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;'
            html_table = f"""
<div style="overflow-x:auto;border-radius:12px;border:1px solid #1E2235;">
  <table style="width:100%;border-collapse:collapse;font-family:Inter,sans-serif;font-size:0.875rem;">
    <thead>
      <tr style="background:#1E2235;">
        <th style="{th_style}">Produto</th>
        <th style="{th_style}">Embalagem</th>
        <th style="{th_style}text-align:right;">Estoque</th>
        <th style="{th_style}text-align:right;">Preço</th>
        <th style="{th_style}text-align:center;">Status</th>
      </tr>
    </thead>
    <tbody style="background:#13151F;">
      {rows_html}
    </tbody>
  </table>
</div>
"""
            st.markdown(html_table, unsafe_allow_html=True)

            st.markdown(
                '<p style="font-size:0.7rem;font-weight:700;color:#4B5563;text-transform:uppercase;'
                'letter-spacing:0.1em;margin:2rem 0 0.75rem 0;">ESTOQUE POR PRODUTO</p>',
                unsafe_allow_html=True
            )
            
            # Gráfico de barras com cores baseadas no nível
            df_all["Cor"] = df_all["Estoque"].apply(
                lambda e: "#EF4444" if e < 20 else ("#F59E0B" if e <= 50 else "#10B981")
            )
            
            fig = px.bar(
                df_all.sort_values("Estoque", ascending=True),
                x="Estoque", y="Produto", orientation='h',
                color="Cor", color_discrete_map="identity",
                labels={"Produto": "", "Estoque": "Unidades em Estoque"}
            )
            
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(family="Inter", color="#8B92A8", size=12),
                title="",
                margin=dict(l=20, r=80, t=20, b=20),
                showlegend=False,
                xaxis=dict(gridcolor='#1E2235', linecolor='#1E2235', zeroline=False, automargin=True),
                yaxis=dict(gridcolor='rgba(0,0,0,0)', linecolor='rgba(0,0,0,0)'),
                height=max(300, len(df_all) * 36)
            )
            fig.update_traces(marker_line_width=0, opacity=0.9)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum produto cadastrado no banco de dados.")
    except Exception as e:
        st.error(f"Erro ao carregar dados de inventário: {str(e)}")
