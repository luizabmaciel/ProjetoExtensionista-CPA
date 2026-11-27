"""Carregamento dos dados do dashboard.

Todas as funções usam @st.cache_data: o arquivo é lido uma vez só, e não a cada
movimento do slider.
"""
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parent.parent
EXT = RAIZ / "dados" / "externos"
PROC = RAIZ / "dados" / "processados"
ORIG = RAIZ / "dados" / "originais"

NIVEL_MAIO_2024 = 5.35   # maior marca, estação 87444000 (Usina do Gasômetro).
PISO =  3.0 # menor nível simulado pelo INCT

@st.cache_data
def niveis_inct():
    """Simulação do INCT limpa pelo Gabriel: 1 linha por nível x bairro (71 x 94)."""
    df = pd.read_csv(EXT / "inct_niveis_bairro.csv")
    return df[["nivel_m", "bairro", "chave", "total_buildings", "affected_buildings",
               "pct_predios", "population", "pop_afetada_est", "percentage_origem", "qualidade"]]


@st.cache_data
def malha_bairros_geojson():
    """Malha oficial dos bairros (Prefeitura), 1 polígono por bairro.

    A geometria é simplificada (~11 m) só para o mapa ficar leve no navegador;
    a forma dos bairros não muda de forma perceptível nessa escala.
    """
    malha = gpd.read_file(EXT / "bairros_poa_2016.geojson").dissolve(by="nome", as_index=False)
    de_para = pd.read_csv(EXT / "de_para_bairros.csv")
    malha = malha.merge(de_para[["nome_prefeitura", "chave_tres_bases"]],
                        left_on="nome", right_on="nome_prefeitura")
    malha["geometry"] = malha.geometry.simplify(0.0001, preserve_topology=True)
    malha = malha.rename(columns={"chave_tres_bases": "chave"})[["chave", "geometry"]].to_crs(4326)
    return json.loads(malha.to_json())


@st.cache_data
def bairros_integrado():
    return pd.read_csv(PROC / "integracao" / "bairros_integrado.csv")

def perfil_vulnerabilidade(bairros, niveis):
    """Classifica cada bairro pela cota em que começa a alagar.

    Três situações distintas, que NÃO podem virar o mesmo número:
      - 'censurado'  : já alagado no piso da simulação (3,0 m). A cota real é
                       desconhecida: só sabemos que é <= 3,0 m.
      - 'medido'     : começa a alagar em algum nível acima do piso.
      - 'nunca alaga': nenhum prédio atingido até 10,0 m.
    """
    base = bairros[["chave", "bairro", "pessoas", "escolas",
                    "inct_nivel_primeiro_alagamento_m"]].copy()
    base = base.rename(columns={"inct_nivel_primeiro_alagamento_m": "cota_inicio"})

    piso = niveis[niveis.nivel_m.round(1) == PISO].set_index("chave")
    base["pct_no_piso"] = base.chave.map(piso.pct_predios)

    base["situacao"] = "medido"
    base.loc[base.cota_inicio.isna(), "situacao"] = "nunca alaga"
    base.loc[base.cota_inicio.eq(PISO), "situacao"] = "censurado"

    teto = niveis[niveis.nivel_m.round(1) == 10.0].set_index("chave")
    base["pct_em_10m"] = base.chave.map(teto.pct_predios)
    return base.sort_values(["cota_inicio", "pct_no_piso"],
                            ascending=[True, False], na_position="last")


@st.cache_data
def equipamentos_por_nivel():
    return pd.read_csv(PROC / "integracao" / "equipamentos_por_nivel.csv")


@st.cache_data
def pontos_osm():
    return pd.read_csv(PROC / "osm_pontos_interesse_limpo.csv")


ARQ_SERIE_NIVEL = PROC / "nivel_guaiba_horario.csv"


@st.cache_data
def serie_nivel_horaria():
    """Leituras do nível do Guaíba (ANA Hidro-Telemetria; colunas data_hora, nivel_m, estacao;
    horário de Brasília). Gerado por scripts/serie_nivel_guaiba.py.

    Devolve None enquanto o arquivo não existir: a Tela 3 funciona sem ele, com menos precisão.
    """
    if not ARQ_SERIE_NIVEL.exists():
        return None
    serie = pd.read_csv(ARQ_SERIE_NIVEL, parse_dates=["data_hora"])
    return serie.dropna(subset=["nivel_m"]).sort_values("data_hora").reset_index(drop=True)


@st.cache_data
def eta_bairro():
    return pd.read_csv(PROC / "integracao" / "eta_bairro.csv")


@st.cache_data
def etas():
    with open(ORIG / "etas_poa_enchente_2024.json", encoding="utf-8") as f:
        return json.load(f)
