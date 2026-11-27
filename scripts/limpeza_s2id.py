from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from comum import (ARQ_S2ID, ARQ_SETORES, COD_POA, SAIDA, UF_SIGLA,
                   corrige_apostrofo, le_ibge, normaliza)

COBRADE_GRUPO = {
    "11": "natural_geologico", "12": "natural_hidrologico",
    "13": "natural_meteorologico", "14": "natural_climatologico",
    "15": "natural_biologico", "21": "tecnologico_radioativo",
    "22": "tecnologico_produtos_perigosos", "23": "tecnologico_incendio_urbano",
    "24": "tecnologico_obras_civis", "25": "tecnologico_transporte",
}
COBRADE_TIPO = {
    "11321": "deslizamento", "12100": "inundacao", "12200": "enxurrada",
    "12300": "alagamento", "13211": "tornado", "13212": "tempestade_de_raios",
    "13213": "granizo", "13214": "chuvas_intensas", "13215": "vendaval",
    "14110": "estiagem", "14120": "seca", "15110": "doenca_infecciosa_viral",
    "24200": "rompimento_de_barragem",
}

RE_PROTO = (r"^(?P<uf_proto>[A-Z]{2})-(?P<tipo_proto>[A-Z])-(?P<cod_proto>\d{7})-"
            r"(?P<cobrade_proto>\d{5})-(?P<data_proto>\d{6}|\d{8})$")

MORTOS_TETO = 500          # acima disso, fora de epidemia, é suspeito
MORTOS_PCT_POP = 0.5       # % da população do município


def k(nome) -> str | None:
    n = normaliza(nome)
    return None if n is None else n.replace(" ", "")


def municipios() -> pd.DataFrame:
    """Lista de municípios do Censo 2022, com população, a partir dos setores."""
    st = le_ibge(ARQ_SETORES, usecols=["CD_UF", "CD_MUN", "NM_MUN", "v0001"])
    st["v0001"] = pd.to_numeric(st["v0001"])
    m = (st.groupby(["CD_MUN", "NM_MUN", "CD_UF"], as_index=False)["v0001"].sum()
           .rename(columns={"CD_MUN": "cod_ibge", "NM_MUN": "nome_ibge",
                            "v0001": "pop_2022"}))
    m["uf_ibge"] = m["CD_UF"].map(UF_SIGLA)
    m["k"] = m["nome_ibge"].map(k)
    assert m["cod_ibge"].is_unique
    return m.drop(columns="CD_UF")


def resolve_municipio(s: pd.DataFrame, mun: pd.DataFrame) -> pd.DataFrame:
    por_cod = mun.set_index("cod_ibge")
    s["k_mun"] = s["mun"].map(k)

    # a) código do protocolo existe e o nome bate
    nome_do_cod = s["cod_proto"].map(por_cod["k"])
    ok_cod = nome_do_cod.notna() & (nome_do_cod == s["k_mun"])

    # b) nome dentro da UF informada, quando é único
    uf_nome = mun.drop_duplicates(["uf_ibge", "k"], keep=False)
    por_uf_nome = uf_nome.set_index(["uf_ibge", "k"])["cod_ibge"]
    via_uf = pd.Series(list(zip(s["uf"], s["k_mun"])), index=s.index).map(por_uf_nome)

    # c) código existe e é da UF informada, mas o nome difere: município que
    #    mudou de nome ou grafia antiga (Moji Mirim, Boa Saúde, Brasópolis…)
    cod_na_uf = s["cod_proto"].map(por_cod["uf_ibge"]) == s["uf"]

    # d) nome único no país
    unico = mun.drop_duplicates("k", keep=False).set_index("k")["cod_ibge"]
    via_pais = s["k_mun"].map(unico)

    s["cod_ibge"] = np.select(
        [ok_cod, via_uf.notna(), cod_na_uf, via_pais.notna()],
        [s["cod_proto"], via_uf, s["cod_proto"], via_pais], default=None)
    s["cod_ibge_origem"] = np.select(
        [ok_cod, via_uf.notna(), cod_na_uf, via_pais.notna()],
        ["protocolo", "nome_na_uf", "protocolo_nome_diferente", "nome_no_pais"],
        default="nao_resolvido")
    s["cod_ibge"] = s["cod_ibge"].where(s["cod_ibge_origem"] != "nao_resolvido")

    s = s.merge(mun[["cod_ibge", "nome_ibge", "uf_ibge", "pop_2022"]],
                on="cod_ibge", how="left")
    s["uf_diverge"] = s["uf_ibge"].notna() & (s["uf_ibge"] != s["uf"])
    return s.drop(columns="k_mun")


def corrige_datas(s: pd.DataFrame) -> pd.DataFrame:
    s["dt_original"] = s["dt"]
    dt = s["dt"].copy()
    status = pd.Series("ok", index=s.index)

    # Sem data: usa o protocolo se ele tiver AAMMDD.
    falta = dt.isna() & (s["data_proto"].str.len() == 6)
    dt[falta] = "20" + s.loc[falta, "data_proto"].str.replace(
        r"(\d{2})(\d{2})(\d{2})", r"\1-\2-\3", regex=True)
    status[falta] = "corrigida_pelo_protocolo"

    # 0013-12-16 ou 1013-10-24 num arquivo de 2013: século digitado errado.
    ano = dt.str[:4]
    seculo = ano.str[:2].isin(["00", "10"]) & (ano.str[2:] == s["ano_arq"].str[2:])
    dt[seculo] = s.loc[seculo, "ano_arq"] + dt[seculo].str[4:]
    status[seculo] = "corrigida_seculo"

    data = pd.to_datetime(dt, format="%Y-%m-%d", errors="coerce")
    invalida = data.isna() | (data.dt.year < 2000)
    data[invalida] = pd.NaT
    status[invalida] = "invalida"
    fora = ~invalida & (data.dt.year.astype("Int64").astype(str) != s["ano_arq"])
    status[fora & (status == "ok")] = "fora_do_ano_do_arquivo"

    s["dt"] = data
    s["dt_status"] = status
    return s


def marca_mortos(s: pd.DataFrame) -> pd.DataFrame:
    s["mortos"] = pd.to_numeric(s["mortos"]).astype("Int64")
    epidemia = s["cobrade"].str.startswith("15")
    s["mortos_cumulativo"] = epidemia
    climat = s["cobrade"].str.startswith("14")
    pct = 100 * s["mortos"] / s["pop_2022"]
    s["mortos_suspeito"] = ~epidemia & (
        (s["mortos"] >= MORTOS_TETO)
        | (climat & (s["mortos"] >= 10))
        | (pct > MORTOS_PCT_POP)).fillna(False)
    # Coluna pronta para somar: sem epidemia e sem número suspeito.
    s["mortos_somavel"] = s["mortos"].where(~epidemia & ~s["mortos_suspeito"])
    return s


def marca_repetidos(s: pd.DataFrame) -> pd.DataFrame:
    chave_evento = ["cod_ibge", "cobrade", "dt"]
    s["evento_repetido"] = s.duplicated(chave_evento, keep=False) & s["cod_ibge"].notna() \
        & s["dt"].notna()
    # Principal: protocolo F (o mais comum) primeiro, depois o reconhecido.
    ordem_status = {"Reconhecido": 0, "Registro": 1, "Não reconhecido": 2}
    tmp = s.assign(_f=(s["tipo_proto"] != "F").astype(int),
                   _st=s["status"].map(ordem_status))
    tmp = tmp.sort_values(chave_evento + ["_f", "_st"])
    principal = ~tmp.duplicated(chave_evento, keep="first") | ~tmp["evento_repetido"]
    s["registro_principal"] = principal.reindex(s.index)
    return s


def main() -> int:
    SAIDA.mkdir(parents=True, exist_ok=True)
    s = pd.read_csv(ARQ_S2ID, dtype=str)
    n0 = len(s)
    for c in s.columns:
        s[c] = s[c].str.strip()
    s["mun"] = corrige_apostrofo(s["mun"])

    partes = s["proto"].str.extract(RE_PROTO)
    assert partes.notna().all(axis=1).all(), "protocolo fora do padrão"
    s = pd.concat([s, partes], axis=1)

    print("Municípios do Censo 2022…")
    mun = municipios()
    s = resolve_municipio(s, mun)
    s = corrige_datas(s)

    s["cobrade_diverge_proto"] = s["cobrade"] != s["cobrade_proto"]
    s["cobrade_grupo"] = s["cobrade"].str[:2].map(COBRADE_GRUPO)
    s["cobrade_tipo"] = s["cobrade"].map(COBRADE_TIPO)
    s["grp"] = s["grp"].fillna("outro")
    s["ano_evento"] = s["dt"].dt.year.astype("Int64")

    s = marca_mortos(s)
    s = marca_repetidos(s)
    assert len(s) == n0

    colunas = [
        "proto", "tipo_proto", "ano_arq", "dt", "ano_evento", "dt_status", "dt_original",
        "uf", "mun", "cod_ibge", "nome_ibge", "uf_ibge", "cod_ibge_origem", "uf_diverge",
        "pop_2022", "cobrade", "cobrade_grupo", "cobrade_tipo", "grp",
        "cobrade_diverge_proto", "status", "mortos", "mortos_cumulativo",
        "mortos_suspeito", "mortos_somavel", "evento_repetido", "registro_principal",
    ]
    s = s[colunas].sort_values(["dt", "uf", "mun"], na_position="last")
    s.to_csv(SAIDA / "s2id_limpo.csv", index=False)
    poa = s[s["cod_ibge"] == COD_POA]
    poa.to_csv(SAIDA / "s2id_poa.csv", index=False)

    q = {
        "linhas": n0,
        "cod_ibge_pelo_protocolo": (s["cod_ibge_origem"] == "protocolo").sum(),
        "cod_ibge_protocolo_nome_diferente":
            (s["cod_ibge_origem"] == "protocolo_nome_diferente").sum(),
        "cod_ibge_pelo_nome": s["cod_ibge_origem"].str.startswith("nome").sum(),
        "cod_ibge_nao_resolvido": (s["cod_ibge_origem"] == "nao_resolvido").sum(),
        "uf_diverge": s["uf_diverge"].sum(),
        **{f"dt_{k}": v for k, v in s["dt_status"].value_counts().items()},
        "cobrade_diverge_proto": s["cobrade_diverge_proto"].sum(),
        "mortos_cumulativo_epidemia": s["mortos_cumulativo"].sum(),
        "mortos_suspeito": s["mortos_suspeito"].sum(),
        "evento_repetido": s["evento_repetido"].sum(),
        "registros_nao_principais": (~s["registro_principal"]).sum(),
        "mortos_soma_bruta": int(s["mortos"].sum()),
        "mortos_soma_somavel": int(s["mortos_somavel"].sum()),
        "registros_poa": len(poa),
    }
    qual = pd.DataFrame(q.items(), columns=["indicador", "valor"])
    qual.to_csv(SAIDA / "s2id_qualidade.csv", index=False)
    print(qual.to_string(index=False))
    if (s["cod_ibge_origem"] == "nao_resolvido").any():
        print("\nNão resolvidos:")
        print(s.loc[s["cod_ibge_origem"] == "nao_resolvido",
                    ["proto", "uf", "mun"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
