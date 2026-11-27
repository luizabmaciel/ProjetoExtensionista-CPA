"""Tela 3 — Se o Guaíba chegar a X metros, quais estações de tratamento de água (ETAs) param e quais bairros
ficam sem abastecimento? Estimativa baseada no que aconteceu em maio de 2024."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import dados
import etas_limiar as lim
from comum import AZUL, CINZA, CINZA_CLARO, linhas_do_nivel, numero, slider_nivel

st.title("Se o Guaíba chegar a X metros, quem fica sem água?")
st.caption("Estações de tratamento de água (ETAs) do Dmae que pararam na enchente de maio de 2024 e os bairros "
           "que elas abastecem, cruzados com o nível do Guaíba.")

serie = dados.serie_nivel_horaria()
info = dados.etas()["etas"]

if serie is None:
    st.warning(
        "**Precisão limitada.** As fontes informam só o dia e o período em que cada ETA parou, e a única medida do "
        "nível com horário é 5,09 m às 12h de 04/05/2024. Por isso, abaixo de 5,1 m não dá para dizer se as ETAs "
        "param. Quando a série horária do nível (Sema) for incluída, cada ETA ganha uma faixa de nível estimada.",
        icon="⚠️")
else:
    st.info(
        "**Estimativa baseada em maio de 2024, não previsão.** O nível em que cada ETA parou foi estimado "
        "cruzando o período da parada informado pelo Dmae com as leituras do nível do Guaíba da ANA. Uma nova "
        "cheia pode ter efeitos diferentes (obras, diques, energia elétrica).", icon="ℹ️")

nivel = slider_nivel("nivel_tela3")

# ---------------------------------------------------------------- cálculo
limiares = lim.limiares(info, serie)
limiares["situacao"] = [lim.situacao_eta(r, nivel) for r in limiares.itertuples()]

nome_para_id = {e["nome"]: e["id"] for e in info}
eb = dados.eta_bairro().assign(eta_id=lambda d: d.eta.map(nome_para_id))
bairros = dados.bairros_integrado()[["chave", "bairro", "pessoas"]]
abast = bairros.merge(lim.situacao_bairros(limiares[["eta_id", "situacao"]], eb), on="chave", how="left")
abast["abastecimento"] = abast.abastecimento.fillna("sem informação")

alagados = linhas_do_nivel(dados.niveis_inct(), nivel)

# ---------------------------------------------------------------- indicadores
pop = abast.groupby("abastecimento").pessoas.sum()
c1, c2, c3, c4 = st.columns(4)
c1.metric("ETAs paradas", f"{(limiares.situacao == 'parada').sum()} de {len(limiares)}",
          help="ETAs que, em 2024, já estavam paradas quando o Guaíba atingiu este nível.")
c2.metric("Pessoas em bairros sem abastecimento", numero(pop.get("sem abastecimento", 0)),
          help="Bairros em que todas as ETAs que os atendem estavam paradas. População do Censo 2022, "
               "cada bairro contado uma vez.")
c3.metric("Pessoas em bairros com abastecimento parcial", numero(pop.get("abastecimento parcial", 0)),
          help="Bairros atendidos por duas ETAs, em que só uma estava parada.")
c4.metric("Para comparar: pessoas em prédios atingidos", numero(alagados.pop_afetada_est.sum()),
          help="Estimativa da simulação do INCT (Tela 1) para o mesmo nível.")

# ---------------------------------------------------------------- mapa
CORES = {"sem abastecimento": "#104281", "abastecimento parcial": "#6da7ec", "incerto": "#ead7b0",
         "abastecido": CINZA_CLARO, "sem informação": "#ffffff"}
col_mapa, col_tab = st.columns([3, 2], gap="large")
with col_mapa:
    st.subheader(f"Abastecimento de água por bairro a {numero(nivel, 1)} m")
    geo = dados.malha_bairros_geojson()
    mapa = go.Figure()
    for situacao, cor in CORES.items():
        parte = abast[abast.abastecimento == situacao]
        if parte.empty:
            continue
        mapa.add_trace(go.Choroplethmap(
            geojson=geo, featureidkey="properties.chave", locations=parte.chave, z=[1] * len(parte),
            colorscale=[[0, cor], [1, cor]], showscale=False, marker_opacity=0.85,
            marker_line_width=0.5, marker_line_color="#9a9893", name=situacao, showlegend=True,
            text=parte.bairro, customdata=parte[["pessoas"]],
            hovertemplate="<b>%{text}</b><br>" + situacao + "<br>%{customdata[0]:,} habitantes<extra></extra>"))
    mapa.update_layout(map=dict(style="carto-positron", center={"lat": -30.12, "lon": -51.17}, zoom=9.7),
                       height=560, margin=dict(l=0, r=0, t=0, b=0), separators=",.",
                       legend=dict(yanchor="top", y=0.99, x=0.01, bgcolor="rgba(255,255,255,0.85)"))
    st.plotly_chart(mapa, width="stretch", config={"scrollZoom": False})
    st.caption("Incerto: alguma ETA do bairro não tem limiar conhecido neste nível. Sem informação: o bairro não "
               "aparece nas listas do Dmae.")

with col_tab:
    st.subheader("Situação de cada ETA")
    tab = limiares.copy()

    def faixa(r):
        if pd.notna(r.nivel_min):
            return f"{numero(r.nivel_min, 2)} a {numero(r.nivel_max, 2)} m"
        if pd.notna(r.nivel_max):
            return f"até {numero(r.nivel_max, 2)} m"
        return "-"

    tab["Parou com o Guaíba em"] = [faixa(r) for r in tab.itertuples()]
    tab["Janela da parada"] = [f"{r.inicio:%d/%m %H:%M} a {r.fim:%H:%M}" if pd.notna(r.inicio) else "-"
                               for r in tab.itertuples()]
    st.dataframe(tab[["eta", "situacao", "Parou com o Guaíba em", "Janela da parada", "confianca"]]
                 .rename(columns={"eta": "ETA", "situacao": f"Situação a {numero(nivel, 1)} m",
                                  "confianca": "Confiança"}),
                 hide_index=True, width="stretch")
    for r in tab.itertuples():
        if isinstance(r.ressalva, str):
            st.caption(f"**{r.eta}:** {r.ressalva}.")

# ---------------------------------------------------------------- série do nível (quando existir)
if serie is not None:
    st.subheader("Nível do Guaíba e janelas de parada das ETAs")
    # linha cheia onde há leituras; tracejado cinza nos intervalos de mais de 3 h sem leitura
    buraco = serie.data_hora.diff() > lim.LACUNA_MAX
    fig = go.Figure()
    for i in serie.index[buraco]:
        fig.add_trace(go.Scatter(x=serie.data_hora[[i - 1, i]], y=serie.nivel_m[[i - 1, i]], mode="lines",
                                 line=dict(color=CINZA, width=1.5, dash="dot"), hoverinfo="skip",
                                 name="sem leitura (ligação)", showlegend=bool(i == serie.index[buraco][0])))
    quebrada = serie.assign(grupo=buraco.cumsum())
    for g, parte in quebrada.groupby("grupo"):
        fig.add_trace(go.Scatter(x=parte.data_hora, y=parte.nivel_m, mode="lines+markers" if len(parte) < 4 else "lines",
                                 line=dict(color=AZUL, width=2), marker=dict(size=6), name="leituras da ANA",
                                 showlegend=bool(g == 0),
                                 hovertemplate="%{x|%d/%m %H:%M}: %{y:.2f} m<extra></extra>"))
    # ETAs com a mesma janela (São João e Tristeza) ganham um rótulo só, para os nomes não se sobreporem
    janelas = limiares.dropna(subset=["inicio"]).groupby(["inicio", "fim"]).eta.agg(" e ".join).reset_index()
    for r in janelas.itertuples():
        fig.add_vrect(x0=r.inicio, x1=r.fim, fillcolor=CINZA, opacity=0.15, line_width=0,
                      annotation_text=r.eta, annotation_position="top left", annotation_font_color=CINZA)
    fig.add_hline(y=nivel, line_width=1, line_color=CINZA, annotation_text=f"nível escolhido: {numero(nivel, 1)} m")
    fig.update_layout(height=380, margin=dict(l=0, r=10, t=30, b=0), yaxis_title="Nível (m)", separators=",.")
    st.plotly_chart(fig, width="stretch")
    st.caption("Leituras da ANA: estação 87450004 Cais Mauá C6 até 02/05 23:15 (Hidro-Telemetria) e estação "
               "87444000 Usina do Gasômetro a partir de 03/05 15:00 (HidroWeb), obtidas em 17/11/2026. "
               "O tracejado só liga as leituras: o nível nesses intervalos não foi medido.")

with st.expander("Como a estimativa é feita"):
    st.markdown("""
1. As notas do Dmae dizem o **dia e o período** de cada parada (ex.: "manhã de 04/05"). O período vira uma **janela**:
   madrugada 0h–6h, manhã 6h–12h, tarde 12h–18h, fim da tarde 15h–18h, noite 18h–24h.
2. Se a nota foi publicada no mesmo dia, a parada aconteceu **antes da publicação**, e a janela termina ali.
   Ex.: a nota das 07:34 de 04/05 diz que as ETAs pararam "na manhã deste sábado" → janela de 06:00 a 07:34.
3. Com as leituras do nível (ANA), o nível no início e no fim da janela dá a **faixa** em que a ETA parou.
   Quando a janela cai num intervalo de mais de 3 horas sem leitura, ou entre duas estações diferentes,
   a faixa recebe **confiança baixa** (é o caso de Moinhos de Vento, na madrugada de 03/05).
4. **Situação no nível escolhido:** *parada* se, em 2024, ela já estava parada com o rio nesse nível;
   *incerta* se o nível está dentro da faixa; *operou* se, em 2024, ela ainda operava nesse nível.
5. **Bairros:** *sem abastecimento* se todas as ETAs que o atendem estão paradas; *parcial* se só uma de duas.

**Suposições:** o nível subiu continuamente enquanto as ETAs paravam; o que aconteceu em 2024 se repetiria num
nível igual. **Limites:** algumas ETAs atendem só parte dos bairros listados; vilas que não são bairros oficiais
ficam de fora; acima de 5,35 m na régua do Gasômetro não há observação.

Fontes: notas do Dmae e da Prefeitura de Porto Alegre listadas na Tela 2; nível do Guaíba:
ANA, estação Usina do Gasômetro baixada do [HidroWeb](https://www.snirh.gov.br/hidroweb/serieshistoricas) e
estação Cais Mauá copiada do [Hidro-Telemetria](https://www.snirh.gov.br/hidrotelemetria/), em 17/11/2026
(detalhes em `dados/originais/nivel_guaiba_fontes.md`).
""")
