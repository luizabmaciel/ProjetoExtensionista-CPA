from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
from matplotlib.path import Path as MplPath

from comum import (ARQ_BAIRROS, ARQ_CNEFE, ARQ_SETORES, COD_POA, REFERENCIA,
                   SAIDA, chave, corrige_apostrofo, le_ibge, num_br)

VARIAVEIS = {
    "v0001": "pessoas",
    "v0002": "domicilios",
    "v0003": "dom_particulares",
    "v0004": "dom_coletivos",
    "v0005": "media_moradores_dppo",
    "v0006": "var_moradores_dppo",
    "v0007": "dom_part_ocupados",
    "v0008": "dom_part_uso_ocasional",   # inferido, ver docstring
    "v0009": "dom_part_vagos",           # inferido, ver docstring
}
CONTAGENS = [v for k, v in VARIAVEIS.items() if k not in ("v0005", "v0006")]

ESPECIE = {
    "1": "domicilio_particular",
    "2": "domicilio_coletivo",
    "3": "estab_agropecuario",
    "4": "estab_ensino",
    "5": "estab_saude",
    "6": "estab_outras_finalidades",
    "7": "edificacao_em_construcao",
    "8": "estab_religioso",
}
TIPO_ESPECIE = {"101": "casa", "102": "casa_de_vila_ou_condominio",
                "103": "apartamento", "104": "outros"}
NIVEL_GEO = {
    "1": "endereco_coordenada_original",
    "2": "endereco_coordenada_modificada",
    "3": "endereco_coordenada_estimada",
    "4": "face_de_quadra",
    "5": "localidade",
    "6": "setor_censitario",
}


# ---------------------------------------------------------------- Censo ----

def limpa_agregado(df: pd.DataFrame) -> pd.DataFrame:
    df = df.mask(df == ".")  # o IBGE marca "não se aplica" com um ponto
    for c in df.columns:
        if c.startswith("NM_"):
            df[c] = corrige_apostrofo(df[c].str.strip())
    df["AREA_KM2"] = num_br(df["AREA_KM2"])
    for v in VARIAVEIS:
        df[v] = num_br(df[v])
    df = df.rename(columns=VARIAVEIS)
    for c in CONTAGENS:
        df[c] = df[c].astype("Int64")
    # Colunas que são todas vazias em POA (núcleo urbano, aglomerado etc.) saem.
    df = df.drop(columns=[c for c in df.columns if df[c].isna().all()])
    df.columns = [c.lower() for c in df.columns]
    return df


def censo() -> tuple[pd.DataFrame, pd.DataFrame]:
    setores = limpa_agregado(le_ibge(ARQ_SETORES).query("CD_MUN == @COD_POA"))
    bairros = limpa_agregado(le_ibge(ARQ_BAIRROS).query("CD_MUN == @COD_POA"))

    de_para = pd.read_csv(REFERENCIA / "de_para_bairros.csv", dtype=str)
    bairros = bairros.merge(
        de_para[["cod_ibge", "nome_inct", "nome_prefeitura"]],
        left_on="cd_bairro", right_on="cod_ibge", how="left",
        validate="1:1").drop(columns="cod_ibge")
    bairros["chave"] = bairros["nome_inct"].map(chave)
    sem_par = bairros["nome_inct"].isna().sum()
    assert sem_par == 0, f"{sem_par} bairros do Censo sem par no de-para"

    # Os setores agregados têm de reproduzir a tabela de bairros.
    soma = setores.groupby("cd_bairro")[CONTAGENS].sum()
    ref = bairros.set_index("cd_bairro")[CONTAGENS]
    assert (soma.sort_index() == ref.sort_index()).all().all(), \
        "soma dos setores não fecha com a tabela de bairros"
    assert (setores["dom_part_ocupados"] + setores["dom_part_uso_ocasional"]
            + setores["dom_part_vagos"] == setores["dom_particulares"]).all()

    setores = setores.merge(bairros[["cd_bairro", "nome_inct", "chave"]],
                            on="cd_bairro", how="left")
    return setores, bairros


def valida_inct(bairros: pd.DataFrame) -> pd.DataFrame:
    """population do data.json (é igual em todos os níveis) × pessoas do Censo."""
    bruto = json.loads((REFERENCIA / "data.json").read_text(encoding="utf-8"))
    nivel = next(iter(bruto.values()))
    inct = pd.DataFrame([
        {"nome_inct": nome, "population_inct": m["population"],
         "total_buildings_inct": m["total_buildings"]}
        for nome, m in nivel.items()])
    inct["chave"] = inct["nome_inct"].map(chave)
    v = bairros[["cd_bairro", "nm_bairro", "chave", "pessoas"]].merge(
        inct.drop(columns="nome_inct"), on="chave", how="outer", indicator=True)
    v["dif_pessoas"] = v["population_inct"] - v["pessoas"]
    return v


# ---------------------------------------------------------------- CNEFE ----

def poligonos_bairros() -> list[tuple[str, MplPath]]:
    g = json.loads((REFERENCIA / "bairros_poa_2016.geojson").read_text(encoding="utf-8"))
    saida = []
    for f in g["features"]:
        anel = np.asarray(f["geometry"]["coordinates"][0])  # sem buracos na malha
        saida.append((f["properties"]["nome"], MplPath(anel)))
    return saida


def bairro_por_coordenada(lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    """Ponto-no-polígono. A malha (EPSG:4674) e o CNEFE são ambos SIRGAS 2000
    em graus, então não há reprojeção."""
    pts = np.column_stack([lon, lat])
    resultado = np.full(len(pts), None, dtype=object)
    for nome, poly in poligonos_bairros():
        x0, y0 = poly.vertices.min(axis=0)
        x1, y1 = poly.vertices.max(axis=0)
        cand = np.flatnonzero((resultado == None) & (lon >= x0) & (lon <= x1)  # noqa: E711
                              & (lat >= y0) & (lat <= y1))
        if len(cand):
            dentro = poly.contains_points(pts[cand])
            resultado[cand[dentro]] = nome
    return resultado


def cnefe(setores: pd.DataFrame) -> pd.DataFrame:
    c = pd.read_csv(ARQ_CNEFE, sep=";", dtype=str)
    n0 = len(c)
    for col in c.columns:
        c[col] = c[col].str.strip()

    out = pd.DataFrame({
        "cod_endereco": c["COD_UNICO_ENDERECO"],
        "cod_setor_preliminar": c["COD_SETOR"],
        "num_quadra": c["NUM_QUADRA"].astype("Int64"),
        "num_face": c["NUM_FACE"].astype("Int64"),
        "cep": c["CEP"],
        "localidade": c["DSC_LOCALIDADE"],
        "logradouro": c[["NOM_TIPO_SEGLOGR", "NOM_TITULO_SEGLOGR", "NOM_SEGLOGR"]]
                      .fillna("").agg(" ".join, axis=1).str.split().str.join(" "),
        "numero": c["NUM_ENDERECO"],
        "modificador": c["DSC_MODIFICADOR"],
    })
    comp = [f"{p}_COMP_ELEM{i}" for i in range(1, 6) for p in ("NOM", "VAL")]
    out["complemento"] = (c[comp].fillna("").agg(" ".join, axis=1)
                          .str.split().str.join(" ").replace("", None))
    out["lat"] = pd.to_numeric(c["LATITUDE"])
    out["lon"] = pd.to_numeric(c["LONGITUDE"])
    out["nivel_geo"] = c["NV_GEO_COORD"].astype(int)
    out["nivel_geo_desc"] = c["NV_GEO_COORD"].map(NIVEL_GEO)
    out["coord_no_endereco"] = out["nivel_geo"] <= 3
    out["cod_especie"] = c["COD_ESPECIE"].astype(int)
    out["especie"] = c["COD_ESPECIE"].map(ESPECIE)
    out["tipo_domicilio"] = c["COD_TIPO_ESPECI"].map(TIPO_ESPECIE)
    out["estabelecimento"] = c["DSC_ESTABELECIMENTO"]
    out["residencial"] = out["cod_especie"].isin([1, 2])
    out["n_especies_endereco"] = out.groupby("cod_endereco")["cod_endereco"].transform("size")

    # Bairro pelo setor (só onde o setor preliminar sobreviveu na malha final).
    s15 = c["COD_SETOR"].str[:15]
    final = setores.set_index("cd_setor")
    out["cod_setor_final"] = s15.where(s15.isin(final.index))
    out["bairro_pelo_setor"] = out["cod_setor_final"].map(final["nome_inct"])

    # Bairro pela coordenada (o que vale).
    nome_pmpa = bairro_por_coordenada(out["lon"].to_numpy(), out["lat"].to_numpy())
    de_para = pd.read_csv(REFERENCIA / "de_para_bairros.csv", dtype=str)
    pmpa_inct = dict(zip(de_para["nome_prefeitura"], de_para["nome_inct"]))
    out["bairro_pela_coord"] = pd.Series(nome_pmpa, index=out.index).map(pmpa_inct)

    out["bairro"] = out["bairro_pela_coord"].fillna(out["bairro_pelo_setor"])
    out["bairro_origem"] = np.select(
        [out["bairro_pela_coord"].notna(), out["bairro_pelo_setor"].notna()],
        ["coordenada", "setor"], default="sem_bairro")
    out["chave"] = out["bairro"].map(chave)

    assert len(out) == n0
    return out


def resumo_cnefe(cn: pd.DataFrame, bairros: pd.DataFrame,
                 val: pd.DataFrame) -> pd.DataFrame:
    g = cn.groupby("bairro")
    r = pd.DataFrame({
        "enderecos_unicos": g["cod_endereco"].nunique(),
        "linhas_cnefe": g.size(),
        "dom_particulares_cnefe": g["cod_especie"].apply(lambda s: (s == 1).sum()),
        "dom_coletivos_cnefe": g["cod_especie"].apply(lambda s: (s == 2).sum()),
        "estabelecimentos_cnefe": g["cod_especie"].apply(lambda s: s.isin([3, 4, 5, 6, 8]).sum()),
        "em_construcao_cnefe": g["cod_especie"].apply(lambda s: (s == 7).sum()),
        "apartamentos_cnefe": g["tipo_domicilio"].apply(lambda s: (s == "apartamento").sum()),
        "pontos_distintos": g.apply(lambda d: d[["lat", "lon"]].drop_duplicates().shape[0],
                                    include_groups=False),
    }).reset_index().rename(columns={"bairro": "nome_inct"})
    r["pct_residencial"] = (100 * (r["dom_particulares_cnefe"] + r["dom_coletivos_cnefe"])
                            / r["linhas_cnefe"]).round(2)
    r = r.merge(bairros[["nome_inct", "cd_bairro", "pessoas", "dom_particulares"]],
                on="nome_inct", how="outer")
    r = r.merge(val[["cd_bairro", "total_buildings_inct"]], on="cd_bairro", how="left")
    r["dif_dom_part_cnefe_censo"] = r["dom_particulares_cnefe"] - r["dom_particulares"]
    return r


def main() -> int:
    SAIDA.mkdir(parents=True, exist_ok=True)

    print("Censo: setores e bairros de POA…")
    setores, bairros = censo()
    setores.to_csv(SAIDA / "censo_setores_poa.csv", index=False)
    bairros.to_csv(SAIDA / "censo_bairros_poa.csv", index=False)
    print(f"  {len(setores)} setores, {len(bairros)} bairros, "
          f"{bairros['pessoas'].sum():,} pessoas")

    val = valida_inct(bairros)
    val.to_csv(SAIDA / "validacao_censo_inct.csv", index=False)
    casou = (val["_merge"] == "both").sum()
    print(f"  INCT × Censo: {casou}/94 bairros casam; "
          f"total INCT {val['population_inct'].sum():,.0f}, "
          f"bairros com população diferente: {(val['dif_pessoas'] != 0).sum()}")

    print("CNEFE: limpeza e bairro por coordenada…")
    cn = cnefe(setores)
    cn.to_csv(SAIDA / "cnefe_poa_limpo.csv.gz", index=False, compression="gzip")
    concorda = (cn["bairro_pela_coord"].map(chave) == cn["bairro_pelo_setor"].map(chave))
    ambos = cn["bairro_pela_coord"].notna() & cn["bairro_pelo_setor"].notna()
    print(f"  {len(cn):,} linhas, {cn['cod_endereco'].nunique():,} endereços únicos")
    print(f"  setor preliminar sem par na malha final: "
          f"{cn['cod_setor_final'].isna().sum():,} linhas")
    print(f"  bairro: {cn['bairro_origem'].value_counts().to_dict()}")
    print(f"  coordenada × setor concordam em {concorda[ambos].mean():.2%} dos casos comparáveis")

    r = resumo_cnefe(cn, bairros, val)
    r.to_csv(SAIDA / "cnefe_resumo_bairro.csv", index=False)
    print(f"  domicílios particulares: CNEFE {(cn['cod_especie'] == 1).sum():,} × "
          f"Censo {bairros['dom_particulares'].sum():,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
