import geopandas as gpd
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import dados
from comum import AZUL, LARANJA, CINZA, numero, slider_nivel, linhas_do_nivel, mapa_bairros

CLASSES = ["Sem prédios atingidos", "Baixa (até 25%)", "Moderada (25–50%)", "Alta (acima de 50%)"]
CORES = dict(zip(CLASSES, ["#26965B", "#D6AC19", "#E5822D", "#CB3838"]))
SEM_DADO = "Sem informação"
CORES[SEM_DADO] = CINZA


@st.cache_data
def escolas_com_bairro():
    """Repete a junção espacial do notebook de integração, com a malha não simplificada."""
    pontos = dados.pontos_osm().query("categoria == 'escolas'").copy().reset_index(drop=True)
    malha = gpd.read_file(dados.EXT / "bairros_poa_2016.geojson").dissolve(by="nome", as_index=False)
    de_para = pd.read_csv(dados.EXT / "de_para_bairros.csv")
    malha = malha.merge(de_para[["nome_prefeitura", "chave_tres_bases"]],
                        left_on="nome", right_on="nome_prefeitura", validate="one_to_one")
    malha = malha.rename(columns={"chave_tres_bases": "chave"})
    geo = gpd.GeoDataFrame(pontos, geometry=gpd.points_from_xy(pontos.lon, pontos.lat),
                          crs="EPSG:4326").to_crs(malha.crs)
    join = gpd.sjoin(geo, malha[["chave", "geometry"]], how="left", predicate="within")
    if not join.index.is_unique:
        raise ValueError("Uma escola corresponde a mais de um bairro. Verifique a malha.")
    return pd.DataFrame(join.drop(columns=["geometry", "index_right"]))


def base_no_nivel(bairros, niveis, nivel):
    atual = linhas_do_nivel(niveis, nivel)
    base = bairros[["chave", "bairro", "escolas", "pessoas"]].merge(
        atual[["chave", "affected_buildings", "pct_predios"]], on="chave", how="left", validate="one_to_one")
    if base[["affected_buildings", "pct_predios"]].isna().any().any():
        raise ValueError("Faltam dados da simulação para algum bairro.")
    base["estimativa"] = base.escolas * base.pct_predios / 100
    base["expostas"] = base.escolas.where(base.affected_buildings > 0, 0)
    base["escolas_10mil"] = 10000 * base.escolas / base.pessoas.where(base.pessoas > 0)
    base["classe"] = np.select(
        [base.affected_buildings.eq(0), base.pct_predios.le(25), base.pct_predios.le(50)],
        CLASSES[:3], default=CLASSES[3])
    return base


def taxa(n, d):
    return 100 * n / d if d else 0


def formato(x, casas=1):
    return numero(x, casas) if pd.notna(x) else "—"


def grafico(fig, altura=380):
    fig.update_layout(height=altura, separators=",.", margin=dict(l=5, r=15, t=30, b=10),
                      legend=dict(orientation="h", y=1.02, yanchor="bottom"))
    st.plotly_chart(fig, width="stretch")


st.title("Educação e enchentes em Porto Alegre")
st.caption("Exposição territorial das escolas · OpenStreetMap, INCT SiMAI e Censo 2022")
st.markdown("Onde estão as escolas e quais bairros apresentam maior exposição da infraestrutura escolar "
            "quando o nível do Guaíba aumenta? Os dados ajudam a discutir prioridades de prevenção "
            "e continuidade do ensino, sem identificar danos reais a escolas individuais.")

nivel = slider_nivel("nivel_tela4")
bairros = dados.bairros_integrado()
niveis = dados.niveis_inct()
escolas = escolas_com_bairro()
base = base_no_nivel(bairros, niveis, nivel)
atual = linhas_do_nivel(niveis, nivel)
serie = dados.equipamentos_por_nivel().query("categoria == 'escolas'").sort_values("nivel_m")

# Verifica se a associação espacial reproduz as contagens do projeto.
contagem = escolas.groupby("chave").size().reindex(base.chave, fill_value=0).to_numpy()
if escolas.chave.isna().any() or not np.array_equal(contagem, base.escolas.to_numpy()):
    st.error("A associação das escolas aos bairros diverge da base integrada. Confira os arquivos do projeto.")
    st.stop()

total = int(base.escolas.sum())
expostas = int(base.expostas.sum())
estimativa = base.estimativa.sum()
percentual = taxa(expostas, total)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Escolas mapeadas", numero(total))
c2.metric("Em bairros atingidos", numero(expostas))
c3.metric("% das escolas mapeadas", numero(percentual, 1) + "%")
c4.metric("Estimativa proporcional", numero(estimativa, 1),
          help="Soma de escolas por bairro × proporção de prédios atingidos. Não é uma contagem de escolas alagadas.")
st.info(f"A {numero(nivel, 1)} m, {numero(expostas)} das {numero(total)} escolas mapeadas estão em "
        f"bairros com prédios atingidos na simulação ({numero(percentual, 1)}%). "
        "A exposição do bairro não confirma alagamento da escola.")

st.divider()
st.subheader("1. Mapa das escolas e exposição dos bairros")
st.caption("Escolha os filtros para consultar o mapa, as tabelas e os rankings filtrados. Os indicadores acima "
           "e os gráficos históricos e de cenários permanecem referentes à cidade inteira.")
f1, f2 = st.columns(2)
with f1:
    selecionados = st.multiselect("Bairros (vazio = todos)", sorted(base.bairro.unique()), key="edu_bairros")
with f2:
    classes = st.multiselect("Exposição do bairro (vazio = todas)", CLASSES, key="edu_classes")
apenas_atingidos = st.checkbox("Mostrar somente bairros com prédios atingidos", key="edu_atingidos")
vis = base.copy()
if selecionados:
    vis = vis[vis.bairro.isin(selecionados)]
if classes:
    vis = vis[vis.classe.isin(classes)]
if apenas_atingidos:
    vis = vis[vis.affected_buildings.gt(0)]
pontos = escolas.merge(vis[["chave", "bairro", "pct_predios", "classe"]], on="chave", how="inner", validate="many_to_one")
st.caption(f"Recorte atual: {numero(len(vis))} bairros e {numero(len(pontos))} escolas mapeadas.")
fig = mapa_bairros(atual, altura=570, zoom=9.8, opacidade=0.40)

# Mantém a malha inteira como contexto; apenas os pontos das escolas são filtrados.
for classe in CLASSES:
    p = pontos[pontos.classe.eq(classe)]
    if p.empty:
        continue
    fig.add_trace(go.Scattermap(lat=p.lat, lon=p.lon, mode="markers", name=classe,
        marker=dict(size=9, color=CORES[classe], opacity=0.9), text=p.nome,
        customdata=p[["bairro", "pct_predios", "classe"]],
        hovertemplate="<b>%{text}</b><br>Bairro: %{customdata[0]}<br>Prédios atingidos: "
                      "%{customdata[1]:.1f}%<br>Exposição: %{customdata[2]}<extra></extra>"))
fig.update_traces(showlegend=False, selector=dict(type="choroplethmap"))
fig.update_layout(showlegend=True, legend=dict(orientation="h", x=0, y=-0.02, yanchor="top"),
                  margin=dict(l=0, r=0, t=10, b=65))
st.plotly_chart(fig, width="stretch", config={"scrollZoom": False})
st.caption("Pontos coloridos conforme a exposição do bairro, não da escola. O fundo azul representa a proporção "
           "de prédios atingidos. Os limites de 25% e 50% são faixas descritivas adotadas nesta análise, "
           "não níveis oficiais de risco.")
if vis.empty:
    st.warning("Nenhum bairro corresponde aos filtros selecionados.")

st.subheader("2. Distribuição das escolas por exposição territorial")
dist = vis.groupby("classe", sort=False).agg(bairros=("bairro", "size"), escolas=("escolas", "sum")).reindex(CLASSES, fill_value=0).reset_index()
fig = px.bar(dist, x="classe", y="escolas", color="classe", color_discrete_map=CORES,
             category_orders={"classe": CLASSES}, text="escolas", hover_data=["bairros"],
             labels={"classe": "Exposição do bairro", "escolas": "Escolas mapeadas", "bairros": "Bairros"})
fig.update_traces(textposition="outside", cliponaxis=False)
fig.update_layout(showlegend=False, yaxis=dict(rangemode="tozero"))
grafico(fig, 340)
st.caption("As categorias são mutuamente exclusivas. Contam todas as escolas mapeadas nos bairros do recorte.")

st.subheader("3. Bairros com maior exposição escolar estimada")
ranking = vis[(vis.escolas > 0) & (vis.affected_buildings > 0)].sort_values(
    ["estimativa", "escolas", "bairro"], ascending=[False, False, True]).head(10)
if ranking.empty:
    st.info("Não há bairros com escolas e prédios atingidos neste recorte.")
else:
    fig = px.bar(ranking.iloc[::-1], x="estimativa", y="bairro", orientation="h", color="classe",
        color_discrete_map=CORES, hover_data={"escolas": True, "pct_predios": ":.1f", "classe": True},
        labels={"estimativa": "Estimativa proporcional de escolas", "bairro": "Bairro", "classe": "Exposição",
                "escolas": "Escolas mapeadas", "pct_predios": "% prédios atingidos"})
    fig.update_yaxes(categoryorder="array", categoryarray=ranking.bairro.iloc[::-1].tolist())
    grafico(fig, 430)
    primeiro = ranking.iloc[0]
    st.markdown(f"No recorte selecionado, **{primeiro.bairro}** lidera a estimativa proporcional "
                f"({numero(primeiro.estimativa, 1)}), com {numero(primeiro.escolas)} escolas mapeadas "
                f"e {numero(primeiro.pct_predios, 1)}% dos prédios atingidos no bairro.")
st.caption("Ranking calculado como número de escolas × percentual de prédios atingidos / 100. "
           "Não é um ranking de danos observados.")

st.subheader("4. Escolas por população e comparação entre bairros")
st.caption("Indicador descritivo: número de escolas mapeadas em 2026 por 10 mil habitantes do Censo 2022. "
           "Não mede vagas, qualidade do ensino ou população em idade escolar.")
if not vis.empty:
    dens = vis.nlargest(10, "escolas_10mil").sort_values("escolas_10mil")
    fig = px.bar(dens, x="escolas_10mil", y="bairro", orientation="h", color_discrete_sequence=[AZUL],
        hover_data={"pessoas": True, "escolas": True}, labels={"escolas_10mil": "Escolas por 10 mil habitantes",
        "bairro": "Bairro", "pessoas": "População (2022)", "escolas": "Escolas mapeadas"})
    grafico(fig, 410)
    fig = px.scatter(vis, x="pct_predios", y="escolas_10mil", size="escolas", color="classe",
        color_discrete_map=CORES, hover_name="bairro", hover_data={"pessoas": True, "escolas": True},
        labels={"pct_predios": "% prédios atingidos", "escolas_10mil": "Escolas por 10 mil habitantes",
                "escolas": "Escolas mapeadas", "pessoas": "População (2022)", "classe": "Exposição"})
    grafico(fig, 390)
    grupos = []
    for rotulo, grupo in [("Bairros com prédios atingidos", vis[vis.affected_buildings.gt(0)]),
                           ("Bairros sem prédios atingidos", vis[vis.affected_buildings.eq(0)])]:
        pop = grupo.pessoas.sum()
        esc = grupo.escolas.sum()
        grupos.append({"Grupo": rotulo, "Bairros": len(grupo), "População (2022)": int(pop),
                       "Escolas mapeadas": int(esc), "Escolas/10 mil habitantes": round(10000 * esc / pop, 2) if pop else None})
    st.dataframe(pd.DataFrame(grupos), hide_index=True, width="stretch")
    st.caption("A comparação usa a razão entre os totais de escolas e habitantes de cada grupo, não a média simples das taxas dos bairros.")

st.divider()
st.subheader("5. Como a exposição muda com o nível do Guaíba")
fig = go.Figure()
for coluna, rotulo, cor in [("em_bairros_atingidos", "Escolas em bairros atingidos (teto)", AZUL),
                            ("estimativa_proporcional", "Estimativa proporcional", LARANJA)]:
    fig.add_trace(go.Scatter(x=serie.nivel_m, y=serie[coluna], mode="lines", name=rotulo,
                             line=dict(color=cor, width=3)))
fig.add_vline(x=nivel, line_color=AZUL, annotation_text=f"Selecionado: {numero(nivel, 1)} m")
fig.add_vline(x=dados.NIVEL_MAIO_2024, line_dash="dash", line_color=CINZA,
              annotation_text="Pico de 2024: 5,35 m (Usina do Gasômetro)", annotation_position="bottom right")
fig.update_layout(xaxis_title="Nível do Guaíba (m)", yaxis_title="Escolas", hovermode="x unified",
                  yaxis=dict(rangemode="tozero"))
grafico(fig, 410)
st.caption("Cada ponto é um cenário simulado, não uma data. O teto conta todas as escolas dos bairros atingidos; "
           "a estimativa proporcional supõe distribuição semelhante à dos prédios do bairro.")

st.subheader("6. Maio de 2024: referência histórica")
pico = dados.NIVEL_MAIO_2024
inferior, superior = 5.3, 5.4
hist = [base_no_nivel(bairros, niveis, n) for n in [inferior, superior]]
lo, hi = hist
st.markdown(
    f"O pico da série compilada pela equipe foi de **{numero(pico, 2)} m**, "
    "medido na estação 87444000 (Usina do Gasômetro), em 05/05/2024, às 05h30. "
    "Como a simulação possui passos de 0,1 m, apresentamos os cenários de "
    "5,3 e 5,4 m apenas como referências comparativas. "
    "Não há garantia de que a estação e a simulação do INCT utilizem "
    "a mesma referência altimétrica."
)
for col, n, b in zip(st.columns(2), [inferior, superior], hist):
    with col:
        st.markdown(f"**Cenário de {numero(n, 1)} m**")
        st.metric("Escolas em bairros atingidos", numero(b.expostas.sum()), help="Teto territorial")
        st.caption(f"{numero(taxa(b.expostas.sum(), total), 1)}% das escolas mapeadas · "
                   f"Estimativa proporcional: {numero(b.estimativa.sum(), 1)}")
comparacao = []
for n in sorted(set([3.0, inferior, superior, nivel, 6.0, 8.0, 10.0])):
    b = base_no_nivel(bairros, niveis, n)
    comparacao.append({"Cenário (m)": n, "Bairros atingidos": int(b.affected_buildings.gt(0).sum()),
                       "Escolas em bairros atingidos": int(b.expostas.sum()),
                       "% das escolas mapeadas": round(taxa(b.expostas.sum(), total), 1),
                       "Estimativa proporcional": round(b.estimativa.sum(), 1)})
st.dataframe(pd.DataFrame(comparacao), hide_index=True, width="stretch")
st.caption("A localização das escolas foi coletada em 2026. Esta comparação usa a rede mapeada atualmente "
           "como referência; não reconstrói a rede escolar de maio de 2024.")

st.subheader("7. Consulta e exportação de dados")
vis = vis.sort_values(["estimativa", "bairro"], ascending=[False, True])
tabela = vis[["bairro", "pessoas", "escolas", "escolas_10mil", "pct_predios", "classe", "expostas", "estimativa"]].copy()
tabela.columns = ["Bairro", "População (2022)", "Escolas mapeadas", "Escolas/10 mil habitantes",
                  "% prédios atingidos", "Exposição do bairro", "Escolas em bairros atingidos", "Estimativa proporcional"]
for col in ["Escolas/10 mil habitantes", "% prédios atingidos", "Estimativa proporcional"]:
    tabela[col] = tabela[col].round(2)
st.dataframe(tabela, hide_index=True, width="stretch")
st.download_button("Baixar dados por bairro (CSV)", tabela.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                   file_name=f"educacao_bairros_{nivel:.1f}m.csv", mime="text/csv")
with st.expander("Consultar escolas individualmente"):
    busca = st.text_input("Buscar pelo nome da escola", key="edu_busca")
    lista = pontos[pontos.nome.str.contains(busca, case=False, regex=False, na=False)] if busca else pontos
    lista = lista[["nome", "bairro", "endereco", "lat", "lon", "pct_predios", "classe"]].sort_values(["bairro", "nome"]).copy()
    lista.columns = ["Nome", "Bairro", "Endereço (quando disponível)", "Latitude", "Longitude", "% prédios atingidos no bairro", "Exposição do bairro"]
    st.dataframe(lista, hide_index=True, width="stretch")
    st.download_button("Baixar lista de escolas (CSV)", lista.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                       file_name=f"educacao_escolas_{nivel:.1f}m.csv", mime="text/csv")

st.divider()
st.subheader("8. O que os resultados significam para a educação?")
altas = int(base.loc[base.classe.eq(CLASSES[3]), "escolas"].sum())
atingidos = int(base.affected_buildings.gt(0).sum())
st.markdown(f"No cenário de **{numero(nivel, 1)} m**, {numero(atingidos)} dos {numero(len(base))} bairros "
            f"apresentam prédios atingidos. **{numero(expostas)} escolas ({numero(percentual, 1)}%)** "
            f"estão nesses bairros, incluindo {numero(altas)} em bairros onde mais de 50% dos prédios "
            f"são atingidos. A estimativa proporcional para a cidade é de {numero(estimativa, 1)} escolas.")
st.markdown("Essa exposição ajuda a identificar locais que merecem avaliação mais detalhada para planejar "
            "rotas de acesso, alternativas de atendimento escolar e recuperação da infraestrutura. "
            "Mesmo uma escola não alagada pode ter problemas de acesso, transporte ou serviços essenciais. "
            "Essas são possibilidades discutidas, não consequências comprovadas pelas bases.")
st.markdown("**Conclusão:** a integração das escolas com a simulação e a população por bairro permite "
            "discutir a distribuição territorial da exposição e apoiar o planejamento preventivo. "
            "Para medir interrupção das aulas, evasão, frequência ou desempenho escolar seriam necessárias "
            "bases educacionais específicas e registros de danos de 2024.")

with st.expander("Fontes, metodologia e limitações"):
    st.markdown("""
**Fontes utilizadas (arquivos do repositório):**
- OpenStreetMap / Overpass API — `osm_pontos_interesse_limpo.csv`: pontos de escolas coletados em novembro de 2026. [Licença ODbL e atribuição](https://www.openstreetmap.org/copyright).
- INCT SiMAI — `inct_niveis_bairro.csv`: cenários de 3,0 a 10,0 m por bairro.
- IBGE — Censo 2022, população dos bairros integrada em `bairros_integrado.csv`.
- Prefeitura de Porto Alegre — `bairros_poa_2016.geojson`: malha oficial de bairros; `de_para_bairros.csv`: padronização das chaves.
- - ANA / Hidro-Telemetria, estação 87444000 — Usina do Gasômetro; pico da série compilada pela equipe.AN.

**Método:** associação espacial das coordenadas às geometrias oficiais (junção `within`, mesma abordagem do notebook da equipe). Integração pela chave de bairro. As categorias de exposição usam o percentual de prédios atingidos. A estimativa proporcional é a soma de escolas × percentual de prédios atingidos / 100. A taxa por 10 mil habitantes usa a população total do bairro.

**Limitações:** cadastro colaborativo e possivelmente incompleto; todos os registros de educação da base têm o subtipo OSM `school`, sem classificação confiável por rede ou etapa de ensino. Os anos das fontes são diferentes. A simulação não identifica prédios escolares individualmente. Não há dados sobre matrículas, aulas suspensas, evasão ou notas. As faixas de exposição não constituem uma classificação oficial de risco.Não há garantia de equivalência entre o zero da régua da estação Usina do Gasômetro e a referência altimétrica utilizada na simulação do INCT. Portanto, a comparação com maio de 2024 é apenas indicativa.
""")

