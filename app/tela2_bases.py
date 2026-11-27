"""Tela 2 — O que outras bases acrescentam à simulação: equipamentos públicos e abastecimento de água."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import dados
import etas_limiar as lim
from comum import AZUL, CINZA, LARANJA, LINK_INCT, linhas_do_nivel, mapa_bairros, numero, slider_nivel

st.title("O que outras bases acrescentam à simulação")
st.caption("Escolas e unidades de saúde (OpenStreetMap) e as estações de tratamento de água "
           "na enchente de maio de 2024 (Dmae), cruzados com a simulação do INCT por bairro.")

CATEGORIAS = {"Escolas": "escolas", "Unidades de saúde": "saude"}

# ---------------------------------------------------------------- filtros (valem para os dois primeiros gráficos)
f1, f2 = st.columns([3, 1], gap="large")
with f1:
    nivel = slider_nivel("nivel_tela2")
with f2:
    rotulo = st.selectbox("Equipamento", list(CATEGORIAS))
categoria = CATEGORIAS[rotulo]

niveis = dados.niveis_inct()
atual = linhas_do_nivel(niveis, nivel)
equip = dados.equipamentos_por_nivel()
serie = equip[equip.categoria == categoria]
no_nivel = linhas_do_nivel(serie, nivel).iloc[0]
total_cidade = dados.bairros_integrado()[categoria].sum()

# ---------------------------------------------------------------- 1. equipamentos por nível
st.subheader(f"{rotulo} em bairros atingidos, por nível do Guaíba")
k1, k2, k3 = st.columns(3)
k1.metric("Total mapeado na cidade", numero(total_cidade))
k2.metric(f"Em bairros atingidos a {numero(nivel, 1)} m", numero(no_nivel.em_bairros_atingidos),
          help="Equipamentos em bairros com pelo menos um prédio atingido. É um teto: um bairro com 1% dos "
               "prédios atingidos conta todos os seus equipamentos.")
k3.metric("Estimativa proporcional", numero(no_nivel.estimativa_proporcional, 1),
          help="Soma de (equipamentos do bairro × % de prédios atingidos). Supõe que os equipamentos estão "
               "distribuídos como os prédios do bairro.")

linha = go.Figure()
for col, nome, cor in [("em_bairros_atingidos", "Em bairros atingidos (teto)", AZUL),
                       ("estimativa_proporcional", "Estimativa proporcional", LARANJA)]:
    linha.add_trace(go.Scatter(x=serie.nivel_m, y=serie[col], mode="lines", name=nome,
                               line=dict(color=cor, width=2),
                               hovertemplate="%{x:.1f} m: %{y:,.1f}<extra>" + nome + "</extra>"))
linha.add_vline(x=nivel, line_width=1, line_color=CINZA,
                annotation_text=f"Escolhido: {numero(nivel, 1)} m", annotation_position="top right",
                annotation_font_color=CINZA)
linha.add_vline(x=dados.NIVEL_MAIO_2024, line_width=1, line_dash="dash", line_color=CINZA,
                annotation_text=f"Maio de 2024: {numero(dados.NIVEL_MAIO_2024, 2)} m", annotation_position="bottom right",
                annotation_font_color=CINZA)
linha.update_layout(height=380, margin=dict(l=0, r=10, t=30, b=0), separators=",.", hovermode="x unified",
                    xaxis_title="Nível do Guaíba (m)", yaxis_title=f"{rotulo} (quantidade)",
                    yaxis=dict(rangemode="tozero"),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
st.plotly_chart(linha, width="stretch")
st.caption("Nenhuma das duas medidas diz que um equipamento específico alagou: a simulação informa quantos "
           "prédios de cada bairro são atingidos, não quais.")

# ---------------------------------------------------------------- 2. mapa dos equipamentos
st.subheader(f"Onde ficam: {rotulo.lower()} sobre os bairros atingidos a {numero(nivel, 1)} m")
pontos = dados.pontos_osm()
pontos = pontos[pontos.categoria == categoria]
mapa = mapa_bairros(atual, altura=600, zoom=9.8, opacidade=0.6)
mapa.add_trace(go.Scattermap(
    lat=pontos.lat, lon=pontos.lon, mode="markers", name=f"{rotulo} (OpenStreetMap)",
    marker=dict(size=7, color=LARANJA), text=pontos.nome, customdata=pontos[["subtipo"]],
    hovertemplate="%{text}<br>tipo: %{customdata[0]}<extra></extra>",
))
mapa.update_traces(showlegend=False, selector=dict(type="choroplethmap"))
mapa.update_layout(showlegend=True, legend=dict(orientation="h", yanchor="top", y=0.99, x=0.01,
                                                bgcolor="rgba(255,255,255,0.8)"))
st.plotly_chart(mapa, width="stretch", config={"scrollZoom": False})
st.caption("Pontos laranja: equipamentos mapeados no OpenStreetMap. Bairros em cinza: nenhum prédio atingido; "
           "em azul: quanto mais escuro, maior a % de prédios atingidos no nível escolhido.")

# ---------------------------------------------------------------- 3. ETAs na enchente de 2024
st.subheader("Estações de tratamento de água paradas na enchente de maio de 2024")
st.caption("A linha do tempo mostra o que aconteceu em 2024 e não muda com o nível. A coluna "
           f"\"A {numero(nivel, 1)} m\" da tabela usa o nível escolhido; o cálculo completo está na Tela 3.")
info_etas = dados.etas()
SITUACAO = {True: "Parou por alagamento", None: "Parou; causa diverge entre as fontes", False: "Não parou"}

# situação de cada ETA no nível escolhido (mesma estimativa da Tela 3)
limiares = lim.limiares(info_etas["etas"], dados.serie_nivel_horaria())
no_nivel_escolhido = {r.eta_id: lim.situacao_eta(r, nivel) for r in limiares.itertuples()}

linhas_tl, linhas_tab = [], []
eta_bairro = pd.read_csv(dados.PROC / "integracao" / "eta_bairro.csv")
pop_bairro = dados.bairros_integrado().set_index("chave").pessoas
for e in info_etas["etas"]:
    ev = e["enchente_2024"]
    situacao = SITUACAO[ev["parada_por_agua"]]
    paradas = [x["data"] for x in ev["eventos"] if x["tipo"].startswith("suspensao")]
    retomadas = [x["data"] for x in ev["eventos"] if x["tipo"].startswith("retomada")]
    chaves = eta_bairro[(eta_bairro.eta == e["nome"])].chave.dropna().unique()
    if paradas and retomadas:
        linhas_tl.append({"ETA": e["nome"].replace("ETA ", ""), "Início": paradas[0], "Fim": retomadas[0],
                          "Situação": situacao})
    linhas_tab.append({
        "ETA": e["nome"].replace("ETA ", ""), "Em 2024": situacao,
        f"A {numero(nivel, 1)} m": no_nivel_escolhido[e["id"]],
        "Parada": pd.to_datetime(paradas[0]).strftime("%d/%m/%Y") if paradas else "-",
        "Retomada": pd.to_datetime(retomadas[0]).strftime("%d/%m/%Y") if retomadas else "-",
        "Nomes de bairro na lista do Dmae": len(e["bairros_conforme_fonte"]["lista"]),
        "Bairros oficiais identificados": len(chaves),
        "População desses bairros (Censo 2022)": int(pop_bairro.reindex(chaves).sum()),
    })

tl = pd.DataFrame(linhas_tl)
tl["Fim"] = pd.to_datetime(tl.Fim) + pd.Timedelta(days=1)   # barra cobre o dia da retomada inteiro
linha_tempo = px.timeline(tl, x_start="Início", x_end="Fim", y="ETA", color="Situação",
                          color_discrete_map={SITUACAO[True]: AZUL, SITUACAO[None]: CINZA},
                          category_orders={"ETA": list(tl.sort_values("Início").ETA)})
linha_tempo.update_traces(hovertemplate="%{y}<extra></extra>")
linha_tempo.update_layout(height=300, margin=dict(l=0, r=10, t=10, b=0), xaxis_title="", yaxis_title="",
                          bargap=0.35, legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title=""),
                          xaxis=dict(tickformat="%d/%m", dtick=7 * 24 * 3600 * 1000))
st.plotly_chart(linha_tempo, width="stretch")
st.caption("Cada barra vai do primeiro registro de parada até a retomada, com precisão de dia (as fontes não "
           "informam a hora). Moinhos de Vento: o Dmae registra a suspensão do sistema na madrugada de 03/05 e "
           "a da ETA na manhã de 04/05. A ETA Belém Novo não parou, mas operou com capacidade reduzida.")

st.dataframe(pd.DataFrame(linhas_tab), hide_index=True, width="stretch",
             column_config={"População desses bairros (Censo 2022)":
                            st.column_config.NumberColumn(format="localized")})
st.caption("A população é um teto: algumas ETAs atendem só parte dos bairros listados, bairros atendidos por "
           "duas ETAs entram na conta das duas, e vilas que não são bairros oficiais ficam de fora. Oito nomes "
           "foram ligados a bairros oficiais por correspondência manual, ainda a confirmar com o Dmae.")

# ---------------------------------------------------------------- fontes
st.subheader("Fontes dos dados")
inct = f"[INCT SiMAI]({LINK_INCT})" if LINK_INCT else "INCT SiMAI (PUCRS)"
st.markdown(f"""
| Dado | Fonte | Coleta |
|---|---|---|
| Escolas e unidades de saúde | [OpenStreetMap](https://www.openstreetmap.org/copyright), via [Overpass API](https://overpass-api.de/api/interpreter) (coleta por código). © colaboradores do OpenStreetMap, licença ODbL | 08/11/2026 |
| Estações de tratamento de água na enchente de 2024 | Notas do [Dmae](https://prefeitura.poa.br/dmae/noticias) e da Prefeitura de Porto Alegre e reportagens (15 fontes, lista abaixo) | 13/11/2026 |
| Nível do Guaíba em maio de 2024 (Tela 3) | ANA: estação 87444000 (Usina do Gasômetro) baixada do [HidroWeb](https://www.snirh.gov.br/hidroweb/serieshistoricas); estação 87450004 (Cais Mauá C6) copiada do [Hidro-Telemetria](https://www.snirh.gov.br/hidrotelemetria/), pois o download dela veio vazio | 17/11/2026 |
| População por bairro | IBGE, Censo Demográfico 2022, [agregados por bairro](https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/Agregados_por_Bairro_csv/) (arquivo básico) | 09/11/2026 |
| Limites dos bairros | Prefeitura de Porto Alegre, [malha oficial de bairros](https://gis-smamus.portoalegre.rs.gov.br/server/rest/services/01_PUBLICACOES/bairros_2016/MapServer/0) (divisão de 2016) | 09/11/2026 |
| Prédios atingidos por nível (simulação) | {inct}, arquivo `data.json` fornecido à disciplina; limpeza pela equipe | limpeza em 10/11/2026 |
""")

with st.expander("As 15 fontes sobre as estações de tratamento de água"):
    for f in info_etas["metadados"]["fontes"]:
        data = pd.to_datetime(f["publicado_em"]).strftime("%d/%m/%Y")
        st.markdown(f"- **{f['id']}** · {f['veiculo']} · [{f['titulo']}]({f['url']}) · publicada em {data}")
