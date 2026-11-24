"""Tela 1 — Simulação do INCT: se o rio chegar a X metros, quais bairros e quantas pessoas são afetados?"""
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import dados
from comum import AZUL, CINZA, LINK_INCT, linhas_do_nivel, mapa_bairros, numero, slider_nivel

st.title("Se o Guaíba chegar a X metros, quem é afetado?")
st.caption("Simulação do INCT SiMAI: prédios atingidos pela água em cada bairro de Porto Alegre, "
           "para níveis do Guaíba de 3,0 m a 10,0 m.")

st.info(
    "**Estes números são estimativas de uma simulação, não previsões nem contagens oficiais.** "
    "A população afetada supõe que as pessoas se distribuem igualmente entre todos os prédios do bairro, "
    "inclusive os não residenciais. O total de prédios vem do OpenStreetMap, que pode estar incompleto. "
    "Os dados originais tinham inconsistências, corrigidas pela equipe antes de entrar neste painel. "
    "Detalhes em *Sobre os dados*, no fim da página.",
    icon="ℹ️",
)

niveis = dados.niveis_inct()
nivel = slider_nivel("nivel_tela1")
atual = linhas_do_nivel(niveis, nivel)
atingidos = atual[atual.affected_buildings > 0]

# ---------------------------------------------------------------- indicadores
c1, c2, c3 = st.columns(3)
c1.metric("Pessoas afetadas (estimativa)", numero(atual.pop_afetada_est.sum()),
          help=f"De {numero(atual.population.sum())} habitantes (Censo 2022).")
c2.metric("Prédios afetados", numero(atual.affected_buildings.sum()),
          help=f"De {numero(atual.total_buildings.sum())} prédios mapeados na cidade.")
c3.metric("Bairros atingidos", f"{len(atingidos)} de {len(atual)}",
          help="Bairros com pelo menos um prédio atingido pela água.")

# ---------------------------------------------------------------- mapa + ranking
col_mapa, col_rank = st.columns([3, 2], gap="large")

with col_mapa:
    st.subheader(f"Prédios afetados por bairro a {numero(nivel, 1)} m")
    st.plotly_chart(mapa_bairros(atual, altura=560, zoom=9.7), width="stretch", config={"scrollZoom": False})
    st.caption("Cinza: nenhum prédio atingido. Azul: quanto mais escuro, maior a % de prédios atingidos.")

with col_rank:
    st.subheader("Bairros mais afetados")
    st.caption("Os 10 bairros com mais pessoas afetadas no nível escolhido.")
    ranking = (atingidos.sort_values("pop_afetada_est", ascending=False).head(10)
               [["bairro", "pop_afetada_est", "affected_buildings", "pct_predios"]])
    st.dataframe(
        ranking, hide_index=True, width="stretch",
        column_config={
            "bairro": "Bairro",
            "pop_afetada_est": st.column_config.NumberColumn("Pessoas (est.)", format="localized"),
            "affected_buildings": st.column_config.NumberColumn("Prédios", format="localized"),
            "pct_predios": st.column_config.ProgressColumn("% prédios", min_value=0, max_value=100, format="%.1f%%"),
        },
    )
    if atingidos.empty:
        st.write("Nenhum bairro atingido neste nível.")

# ---------------------------------------------------------------- curva + barras
col_curva, col_barras = st.columns(2, gap="large")

with col_curva:
    st.subheader("População afetada em toda a cidade, por nível")
    cidade = niveis.groupby("nivel_m", as_index=False).pop_afetada_est.sum()
    curva = go.Figure()
    curva.add_trace(go.Scatter(x=cidade.nivel_m, y=cidade.pop_afetada_est, mode="lines",
                               line=dict(color=AZUL, width=2), name="Pessoas afetadas",
                               hovertemplate="%{x:.1f} m: %{y:,.0f} pessoas<extra></extra>"))
    valor_atual = atual.pop_afetada_est.sum()
    curva.add_trace(go.Scatter(x=[nivel], y=[valor_atual], mode="markers",
                               marker=dict(color=AZUL, size=11, line=dict(color="#ffffff", width=2)),
                               name="Nível escolhido",
                               hovertemplate="Nível escolhido, %{x:.1f} m: %{y:,.0f} pessoas<extra></extra>"))
    curva.add_vline(x=dados.NIVEL_MAIO_2024, line_width=1, line_dash="dash", line_color=CINZA,
                    annotation_text="Maio de 2024: 5,35 m", annotation_position="top left",
                    annotation_font_color=CINZA)
    curva.update_layout(height=420, showlegend=False, margin=dict(l=0, r=10, t=30, b=0),
                        xaxis_title="Nível do Guaíba (m)", yaxis_title="Pessoas afetadas (estimativa)",
                        yaxis=dict(tickformat=",.0f", rangemode="tozero"), separators=",.")
    st.plotly_chart(curva, width="stretch")
    st.caption("O ponto marca o nível escolhido no controle acima. A linha tracejada marca a maior cheia "
               "registrada em Porto Alegre, em maio de 2024.")

with col_barras:
    st.subheader("% de prédios afetados em cada bairro atingido")
    if atingidos.empty:
        st.write("Nenhum bairro atingido neste nível.")
    else:
        ordem = atingidos.sort_values("pct_predios")
        barras = px.bar(ordem, x="pct_predios", y="bairro", orientation="h",
                        labels={"pct_predios": "% de prédios afetados", "bairro": ""},
                        hover_data={"affected_buildings": ":,", "total_buildings": ":,", "pct_predios": ":.1f"})
        barras.update_traces(marker_color=AZUL)
        barras.update_layout(height=max(320, 20 * len(ordem) + 80), margin=dict(l=0, r=10, t=10, b=0),
                             xaxis=dict(range=[0, 100], ticksuffix="%"), bargap=0.25, separators=",.")
        st.plotly_chart(barras, width="stretch")

# ---------------------------------------------------------------- sobre os dados
with st.expander("Sobre os dados e tabela completa"):
    fonte_inct = f"[INCT SiMAI]({LINK_INCT})" if LINK_INCT else "INCT SiMAI (PUCRS)"
    ressalvas = niveis[niveis.qualidade != "ok"]
    divergentes = int((niveis.percentage_origem.round(3) != niveis.pct_predios.round(3)).sum())
    st.markdown(f"""
**Fonte:** simulação do {fonte_inct}, arquivo `data.json` fornecido à disciplina, com 94 bairros e 71 níveis
(3,0 a 10,0 m, de 0,1 em 0,1 m). O total de prédios de cada bairro vem do OpenStreetMap e a população, do
Censo IBGE 2022.

**Limpeza (feita pela equipe):** a porcentagem de prédios e a população afetada foram recalculadas a partir dos
prédios atingidos e do total de prédios, porque os valores originais não batiam com esses campos em
{numero(divergentes)} das {numero(len(niveis))} combinações de nível e bairro.
Além disso, {int((ressalvas.qualidade == "faltante").sum())} valores faltantes foram interpolados entre os níveis vizinhos e
{int((ressalvas.qualidade != "faltante").sum())} valores suspeitos foram mantidos e sinalizados
(coluna *Ressalva da limpeza* na tabela abaixo).

**Como ler:** a população afetada é estimada como *população do bairro × % de prédios afetados*.
Ela não diferencia prédios residenciais de comerciais nem considera andares altos.
""")
    st.dataframe(
        atual.sort_values("pct_predios", ascending=False)
        [["bairro", "pct_predios", "affected_buildings", "total_buildings", "pop_afetada_est", "population", "qualidade"]],
        hide_index=True, width="stretch",
        column_config={
            "bairro": "Bairro",
            "pct_predios": st.column_config.NumberColumn("% prédios afetados", format="%.1f"),
            "affected_buildings": st.column_config.NumberColumn("Prédios afetados", format="localized"),
            "total_buildings": st.column_config.NumberColumn("Total de prédios", format="localized"),
            "pop_afetada_est": st.column_config.NumberColumn("Pessoas afetadas (est.)", format="localized"),
            "population": st.column_config.NumberColumn("População", format="localized"),
            "qualidade": "Ressalva da limpeza",
        },
    )
