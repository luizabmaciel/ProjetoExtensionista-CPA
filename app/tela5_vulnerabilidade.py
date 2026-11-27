"""Tela 5 — Vulnerabilidade por bairro: em que cota cada um começa a alagar."""
import plotly.graph_objects as go
import streamlit as st

import dados
from comum import AZUL, CINZA, LARANJA, numero, linhas_do_nivel

TETO = 10.0          # maior nível simulado pelo INCT
NIVEL_LEITURA = 5.3  # nível usado no bloco de leitura crítica


def violacoes_monotonia(niveis):
    """A água não recua: se o nível sobe, o % de prédios atingidos não pode cair.

    Devolve só os passos que violam essa regra. A tolerância de 0,001 pp evita
    acusar arredondamento como se fosse defeito.
    """
    d = niveis.sort_values(["chave", "nivel_m"]).copy()
    d["variacao"] = d.groupby("chave").pct_predios.diff()
    return d[d.variacao < -0.001]


def curva_bairros(niveis):
    """Quantos bairros têm ao menos um prédio atingido em cada nível simulado."""
    d = niveis.assign(atingido=niveis.affected_buildings > 0)
    return d.groupby("nivel_m", as_index=False).atingido.sum()


st.title("Vulnerabilidade por bairro")
st.caption("Cota do Guaíba em que cada bairro começa a alagar · Simulação do INCT SiMAI, "
           "71 níveis de 3,0 a 10,0 m em passos de 0,1 m, sobre a malha de 94 bairros da Prefeitura")

bairros = dados.bairros_integrado()
niveis = dados.niveis_inct()
perfil = dados.perfil_vulnerabilidade(bairros, niveis)

st.markdown(
    "A **cota de início de alagamento** é o menor nível simulado do Guaíba em que o bairro passa a ter "
    "pelo menos um prédio atingido. Ela não vem pronta na base: foi obtida varrendo os 71 níveis de cada "
    "bairro e tomando o primeiro em que o número de prédios atingidos deixa de ser zero.\n\n"
    "As telas 1 a 4 mostram **quanto** é atingido em cada nível. Esta mostra **quem** cede primeiro — "
    "e o que a simulação não consegue dizer."
)

st.divider()
st.subheader("1. Os três grupos de bairros")

c1, c2, c3 = st.columns(3)
c1.metric("Nunca alagam", numero((perfil.situacao == "nunca alaga").sum()),
          help="Nenhum prédio atingido em nenhum dos 71 níveis simulados, até 10,0 m.")
c2.metric("Cota medida", numero((perfil.situacao == "medido").sum()),
          help="O bairro começa a alagar em algum nível acima do piso, então a cota é medida de fato.")
c3.metric("Cota censurada", numero((perfil.situacao == "censurado").sum()),
          help="O bairro já aparece alagado no primeiro nível simulado (3,0 m); a cota real é "
               "desconhecida, só se sabe que é menor ou igual a 3,0 m.")


resumo = (perfil.groupby("situacao")
          .agg(Bairros=("bairro", "size"), Pessoas=("pessoas", "sum"), Escolas=("escolas", "sum"))
          .reindex(["nunca alaga", "medido", "censurado"]))
resumo["% da cidade"] = (100 * resumo.Pessoas / perfil.pessoas.sum()).round(1)
resumo.index = ["Nunca alagam", "Cota medida", "Cota censurada"]
st.dataframe(resumo.reset_index().rename(columns={"index": "Situação"}),
             hide_index=True, width="stretch")

expostos = perfil.loc[perfil.situacao != "nunca alaga", "pessoas"].sum()
censurados_pop = perfil.loc[perfil.situacao == "censurado", "pessoas"].sum()
st.info(
    f"**{numero(100 * expostos / perfil.pessoas.sum(), 1)}% da cidade** mora em bairro que alaga em algum "
    f"cenário simulado. E **{numero(100 * censurados_pop / perfil.pessoas.sum(), 1)}%** mora em bairro cuja "
    "cota de início a base não consegue medir — eles já aparecem alagados no primeiro nível da simulação."
)

st.divider()
st.subheader("2. Os bairros com cota medida")
st.caption("Os bairros que começam a alagar acima do piso da simulação, ordenados pela cota. "
           "Os demais aparecem nos blocos 3 e 4.")

medidos = perfil[perfil.situacao == "medido"][["bairro", "cota_inicio", "pessoas", "escolas"]]
medidos = medidos.rename(columns={
    "bairro": "Bairro",
    "cota_inicio": "Cota de início (m)",
    "pessoas": "População (2022)",
    "escolas": "Escolas mapeadas",
})
st.dataframe(medidos, hide_index=True, width="stretch")

st.divider()
st.subheader("3. Os bairros com cota censurada")
st.markdown(
    f"A simulação começa em **{numero(dados.PISO, 1)} m**, e {numero((perfil.situacao == 'censurado').sum())} "
    "bairros já aparecem alagados nesse primeiro passo. Para eles, a cota registrada não é uma medida: é o "
    "piso da base. Não dá para saber se alagariam a 2,5 ou a 2,0 m, porque a simulação não desce até lá.\n\n"
    "Isso não os deixa sem ordenação. Eles não podem ser comparados pela cota, mas podem pelo **quanto já "
    "está submerso no piso** — que é uma régua diferente, aplicada só a este grupo."
)

censurados = perfil[perfil.situacao == "censurado"][["bairro", "pct_no_piso", "pct_em_10m", "pessoas", "escolas"]]
censurados = censurados.rename(columns={
    "bairro": "Bairro",
    "pct_no_piso": "% prédios já atingidos a 3,0 m",
    "pct_em_10m": "% prédios a 10,0 m",
    "pessoas": "População (2022)",
    "escolas": "Escolas mapeadas",
})
st.dataframe(censurados.round(1), hide_index=True, width="stretch")

st.divider()
st.subheader("4. A que ritmo a cidade cede")

curva = curva_bairros(niveis)
fig = go.Figure()
fig.add_trace(go.Scatter(x=curva.nivel_m, y=curva.atingido, mode="lines",
                         line=dict(color=AZUL, width=3), name="Bairros com algum prédio atingido"))
fig.add_vline(x=dados.NIVEL_MAIO_2024, line_dash="dash", line_color=CINZA,
              annotation_text=f"Pico de 2024: {numero(dados.NIVEL_MAIO_2024, 2)} m",
              annotation_position="top left")
fig.update_layout(height=400, separators=",.", margin=dict(l=5, r=15, t=30, b=10),
                  xaxis_title="Nível do Guaíba (m)", yaxis_title="Bairros atingidos",
                  yaxis=dict(rangemode="tozero"), hovermode="x unified", showlegend=False)
st.plotly_chart(fig, width="stretch")

primeiro = int(curva.atingido.iloc[0])
em_35 = int(curva.loc[curva.nivel_m.between(3.49, 3.51), "atingido"].iloc[0])
em_40 = int(curva.loc[curva.nivel_m.between(3.99, 4.01), "atingido"].iloc[0])
em_50 = int(curva.loc[curva.nivel_m.between(4.99, 5.01), "atingido"].iloc[0])
st.markdown(
    f"A curva é desigual. Já no piso da simulação **{primeiro} bairros** estão atingidos, e só entre 3,0 e "
    f"3,5 m entram mais **{em_35 - primeiro}**. Depois ela arrasta: de 4,0 a 5,0 m — um metro inteiro — "
    f"entram apenas **{em_50 - em_40}**.\n\n"
    "A vulnerabilidade de Porto Alegre está concentrada na cota baixa, não distribuída ao longo da escala."
)

st.divider()
st.subheader("5. O que a cota não quer dizer")
st.markdown(
    "- **Não é o bairro inteiro.** É o primeiro prédio. Arquipélago e Sarandi aparecem ambos a 3,0 m, "
    "mas o primeiro já está 99,9% atingido nesse nível e o segundo, 13,5%.\n"
    "- **Não é data nem previsão.** Cada nível é um cenário independente, não um instante de uma enchente.\n"
    "- **Não considera proteção.** Dique, muro e comporta não existem no modelo — ele só compara terreno "
    "com nível d'água.\n"
    "- **Não diz profundidade nem duração.** Registra apenas se há prédio atingido."
)

folga = TETO - dados.NIVEL_MAIO_2024
st.success(
    f"**\"Nunca alaga\" é uma afirmação forte.** Significa não alagar até {numero(TETO, 1)} m, que está "
    f"{numero(folga, 2)} m acima do pico de maio de 2024. Esses {numero((perfil.situacao == 'nunca alaga').sum())} "
    "bairros estão fora do problema em qualquer cenário plausível, não por acaso da escala."
)

st.divider()
st.subheader("6. O que o modelo não enxerga")

atual = linhas_do_nivel(niveis, NIVEL_LEITURA).sort_values("pct_predios", ascending=False)
destaque = ["Farrapos", "Humaitá", "Navegantes", "Centro Histórico"]
leitura = atual[atual.bairro.isin(destaque)][["bairro", "pct_predios", "population"]]
leitura = leitura.rename(columns={"bairro": "Bairro", "pct_predios": f"% prédios a {NIVEL_LEITURA} m",
                                  "population": "População (2022)"})
st.dataframe(leitura.round(1), hide_index=True, width="stretch")
st.markdown(
    "O Centro Histórico é beira d'água e foi inundado em maio de 2024. A simulação o coloca perto de 10%, "
    "enquanto crava 100% em Farrapos, Humaitá e Navegantes.\n\n"
    "Isso não é erro: é o que o modelo **é**. Ele compara cota de terreno com nível d'água e nada mais. "
    "Onde o terreno é baixo e não há proteção, acerta. Onde existe sistema de proteção, não enxerga nem a "
    "proteção nem a falha dela — e em 2024 foi a falha do sistema que inundou o Centro."
)

with st.expander("Consistência física da simulação"):
    viol = violacoes_monotonia(niveis)
    passos = len(niveis) - niveis.chave.nunique()
    por_bairro = (viol.groupby("bairro")
                  .agg(Passos=("variacao", "size"), **{"Maior queda (pp)": ("variacao", "min")})
                  .sort_values("Passos", ascending=False).round(2))
    st.markdown(
        f"A água não recua: se o nível sobe, o percentual de prédios atingidos não pode cair. "
        f"Testamos essa regra nos {numero(passos)} passos da simulação e **{numero(len(viol))} violam** — "
        f"{numero(100 * (1 - len(viol) / passos), 2)}% da base é fisicamente consistente."
    )
    st.dataframe(por_bairro.reset_index().rename(columns={"bairro": "Bairro"}),
                 hide_index=True, width="stretch")
    st.markdown(
        "São os dois bairros que a nossa coluna `qualidade` já sinalizava na preparação. No Arquipélago a "
        "queda é de fração de ponto percentual: ruído de borda, inofensivo. No Espírito Santo é de mais de "
        "60 pontos, o que é impossível — o bairro aparece com menos prédios atingidos a 10,0 m do que a "
        "4,7 m. Mantivemos as duas linhas na base, sinalizadas, em vez de removê-las."
    )

with st.expander("Fontes, método e limitações"):
    st.markdown("""
**Fontes (arquivos do repositório):**
- INCT SiMAI — `inct_niveis_bairro.csv`: simulação por bairro, 71 níveis de 3,0 a 10,0 m.
- Prefeitura de Porto Alegre — `bairros_poa_2016.geojson` (malha oficial) e `de_para_bairros.csv` (padronização das chaves).
- IBGE — Censo 2022, população por bairro, via `bairros_integrado.csv`.

**Método:** para cada bairro, varredura dos 71 níveis em ordem crescente até o primeiro com prédios
atingidos. Bairros já atingidos no piso (3,0 m) são marcados como censurados e ordenados pelo percentual
atingido nesse nível; bairros sem nenhum prédio atingido até 10,0 m são marcados como "nunca alaga".

**Limitações:** a simulação não representa diques, muros, comportas nem casas de bomba, e não informa
profundidade nem duração do alagamento. O piso de 3,0 m e o teto de 10,0 m são limites da simulação, não
do fenômeno. A cota é um nível do Guaíba conforme a simulação do INCT; a régua de referência não está
confirmada na documentação de que dispomos. A série observada de maio de 2024 foi medida na Usina do
Gasômetro (estação 87444000). Enquanto a equivalência entre as duas réguas não for verificada, a
comparação entre cenário simulado e nível observado tem margem não quantificada.
""")