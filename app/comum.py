"""Itens usados pelas duas telas: cores, formatação de números, o slider de nível e o mapa."""
import numpy as np
import plotly.graph_objects as go
import streamlit as st

import dados

# Paleta: azul como cor principal (calmo, sem conotação de alerta).
AZUL = "#2a78d6"
LARANJA = "#eb6834"
CINZA = "#898781"
# escala sequencial de um só tom (azul claro = pouco, azul escuro = muito)
ESCALA_AZUL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#2a78d6", "#1c5cab", "#104281", "#0d366b"]

# Link da ferramenta atual do INCT (Flood - INCT SiMAI). Preencher com o endereço oficial.
LINK_INCT = None


def numero(x, casas=0):
    """Formata no padrão brasileiro: 12.345 ou 12.345,6."""
    s = f"{x:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def slider_nivel(chave_widget):
    """Slider do nível do Guaíba. O valor escolhido vale para as duas telas."""
    if "nivel" not in st.session_state:
        st.session_state.nivel = 5.3

    def guardar():
        st.session_state.nivel = st.session_state[chave_widget]

    nivel = st.slider("Nível do Guaíba (m)", min_value=3.0, max_value=10.0,
                      value=st.session_state.nivel, step=0.1, format="%.1f m",
                      key=chave_widget, on_change=guardar,
                      help="Nível medido na régua do Cais Mauá. A simulação começa em 3,0 m porque, "
                           "abaixo disso, a cidade não era afetada.")
    return round(nivel, 1)


def linhas_do_nivel(df, nivel):
    """Filtra as linhas de um nível. Usa isclose porque 5.3 em ponto flutuante pode virar 5.2999..."""
    return df[np.isclose(df.nivel_m, nivel)]


CINZA_CLARO = "#d9d8d2"


def mapa_bairros(atual, altura, zoom, opacidade=0.85):
    """Mapa dos bairros: cinza = nenhum prédio atingido; azul = % de prédios atingidos (mais escuro, mais)."""
    geo = dados.malha_bairros_geojson()
    nao = atual[atual.affected_buildings == 0]
    sim = atual[atual.affected_buildings > 0]
    fig = go.Figure()
    fig.add_trace(go.Choroplethmap(
        geojson=geo, featureidkey="properties.chave", locations=nao.chave, z=[0] * len(nao),
        colorscale=[[0, CINZA_CLARO], [1, CINZA_CLARO]], showscale=False, marker_opacity=opacidade,
        marker_line_width=0.4, marker_line_color="#ffffff", text=nao.bairro, name="Não atingido",
        hovertemplate="<b>%{text}</b><br>nenhum prédio atingido<extra></extra>"))
    fig.add_trace(go.Choroplethmap(
        geojson=geo, featureidkey="properties.chave", locations=sim.chave, z=sim.pct_predios,
        zmin=0, zmax=100, colorscale=ESCALA_AZUL, marker_opacity=opacidade,
        marker_line_width=0.4, marker_line_color="#ffffff", text=sim.bairro, name="Atingido",
        customdata=sim[["affected_buildings", "pop_afetada_est"]],
        colorbar=dict(title="% prédios<br>atingidos", ticksuffix="%", thickness=12),
        hovertemplate="<b>%{text}</b><br>%{z:.1f}% dos prédios atingidos<br>"
                      "%{customdata[0]:,} prédios · %{customdata[1]:,} pessoas (est.)<extra></extra>"))
    fig.update_layout(map=dict(style="carto-positron", center={"lat": -30.12, "lon": -51.17}, zoom=zoom),
                      height=altura, margin=dict(l=0, r=0, t=0, b=0), separators=",.")
    return fig
