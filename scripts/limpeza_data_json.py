"""Limpeza do data.json do INCT — simulação de alagamento por nível de água.

O arquivo chega aninhado em três camadas: nível de água, depois bairro, depois
as métricas. Para analisar, isso tem que virar tabela: uma linha por par
nível-bairro. É o que este script faz, e no caminho ele conserta duas coisas
que atrapalham quem usar o dado sem olhar:

  1. O campo `percentage` foi arredondado para cima (ceil) em todas as 6.674
     linhas. Qualquer bairro com um prédio afetado aparece com 1%, mesmo quando
     a conta dá 0,006%. Recalculo a proporção e guardo o original ao lado.

  2. Quatro células estão com zero onde devia haver valor — a série do bairro
     está subindo, zera em um nível e volta no seguinte. Marco como faltante e
     interpolo entre os vizinhos, com bandeira para quem quiser descartar.

O que o script NÃO faz é inventar valor para o Espírito Santo. Aquele bairro
tem um problema de outra natureza (ver o relatório de qualidade no final) e
corrigir no chute seria pior que deixar marcado.

Saída: dados/processados/inct_niveis_bairro.csv
       dados/processados/inct_qualidade.csv

Uso:
    python scripts/limpeza_data_json.py
"""

from __future__ import annotations

import json
import math
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
ENTRADA = RAIZ / "dados" / "originais" / "data.json"
SAIDA = RAIZ / "dados" / "processados"

METRICAS = ["total_buildings", "affected_buildings", "population",
            "affected_population"]

# Dois nomes não fecham por normalização nenhuma, porque a diferença não é de
# grafia e sim de palavra. Mapeados à mão, com o nome do IBGE como destino —
# que é a convenção do data.json e do POAGEODATA.
APELIDOS = {
    "CORONEL APARICIO BORGES": "CEL APARICIO BORGES",
    "PASSO D AREIA": "PASSO DA AREIA",
    "PASSO DAREIA": "PASSO DA AREIA",
}

ASPAS = dict.fromkeys(map(ord, "'`´’‘ʼʼ"), None)


def normaliza(nome) -> str | None:
    """Caixa alta, sem acento e sem pontuação, com espaços simples.

    A remoção dos apóstrofos vem antes do NFKD de propósito: no NFKD o `´`
    (U+00B4) se decompõe em espaço mais acento combinante, e `Passo d´Areia`
    acabaria virando `PASSO D AREIA` em vez de `PASSO DAREIA`.
    """
    if nome is None or (isinstance(nome, float) and pd.isna(nome)):
        return None
    s = str(nome).replace(" ", " ").translate(ASPAS)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^A-Z0-9 ]", " ", s.upper())
    return re.sub(r"\s+", " ", s).strip()


def chave(nome) -> str | None:
    """Chave de junção: normaliza, resolve os apelidos e tira os espaços.

    Sem espaço nenhum porque é isso que faz `VILA NOVA` casar com `VILANOVA`.
    """
    k = normaliza(nome)
    if k is None:
        return None
    k = APELIDOS.get(k, k)
    return k.replace(" ", "")


def nivel_para_metro(texto: str) -> float:
    """`3_0m` -> 3.0, `10_0m` -> 10.0. O underscore é a vírgula decimal."""
    return float(texto.rstrip("m").replace("_", "."))


def para_tabela(bruto: dict) -> pd.DataFrame:
    """Desaninha as três camadas em uma linha por par nível-bairro."""
    linhas = []
    for nivel, bairros in bruto.items():
        metro = nivel_para_metro(nivel)
        for nome, m in bairros.items():
            faltando = [c for c in METRICAS + ["percentage"] if c not in m]
            if faltando:
                raise KeyError(f"{nivel}/{nome} sem os campos {faltando}")
            linhas.append({
                "nivel_m": metro,
                "nivel_origem": nivel,
                "bairro": nome,
                "chave": chave(nome),
                **{c: m[c] for c in METRICAS},
                "percentage_origem": m["percentage"],
            })
    return pd.DataFrame(linhas).sort_values(["bairro", "nivel_m"], ignore_index=True)


def marca_faltantes(df: pd.DataFrame) -> pd.DataFrame:
    """Acha os zeros que são buraco, não ausência de alagamento.

    O critério é o que a física exige: água subindo não desafeta ninguém. Então
    um zero cercado por valores positivos, em uma série que já tinha começado a
    alagar, é dado que faltou. Zero antes do primeiro nível com alagamento é
    zero de verdade e fica como está.
    """
    df = df.copy()
    df["qualidade"] = "ok"

    for bairro, bloco in df.groupby("bairro", sort=False):
        bloco = bloco.sort_values("nivel_m")
        serie = bloco["affected_buildings"].to_numpy()
        comecou = next((i for i, v in enumerate(serie) if v > 0), None)
        if comecou is None:
            continue  # bairro nunca alaga em nenhum dos 71 níveis
        # Só interessa o que vem depois do primeiro alagamento, e só se houver
        # valor positivo adiante — zero no fim da série seria outra conversa.
        for i in range(comecou + 1, len(serie)):
            if serie[i] == 0 and serie[i + 1:].max(initial=0) > 0:
                df.loc[bloco.index[i], "qualidade"] = "faltante"
    return df


def marca_suspeitos(df: pd.DataFrame) -> pd.DataFrame:
    """Marca pico isolado e platô que colapsa — sem mexer no valor.

    Pico: valor mais de cinco vezes a média dos dois vizinhos. Platô que
    colapsa: a série começa alta, cai para menos da metade e nunca mais volta
    ao patamar inicial. Os dois são incompatíveis com uma simulação de água
    subindo, mas não dá para adivinhar o número certo, então ficam marcados.
    """
    df = df.copy()
    for bairro, bloco in df.groupby("bairro", sort=False):
        bloco = bloco.sort_values("nivel_m")
        s = bloco["affected_buildings"].to_numpy()

        for i in range(1, len(s) - 1):
            vizinhos = (s[i - 1] + s[i + 1]) / 2
            if vizinhos > 0 and s[i] > 5 * vizinhos:
                df.loc[bloco.index[i], "qualidade"] = "suspeito_pico"

        if s[0] > 0 and len(s) > 6 and s[5:].min() < s[0] * 0.5 and s[-1] < s[0]:
            # O platô inicial é o trecho que fica no patamar do primeiro valor
            # antes da queda. Marca ele inteiro.
            for i in range(len(s)):
                if s[i] < s[0] * 0.5:
                    break
                if df.loc[bloco.index[i], "qualidade"] == "ok":
                    df.loc[bloco.index[i], "qualidade"] = "suspeito_plato"
    return df


def marca_ruido(df: pd.DataFrame, tolerancia=0.01) -> pd.DataFrame:
    """Marca as quedas pequenas demais para serem defeito.

    O Arquipélago já está 99,7% alagado no primeiro nível, e daí para cima a
    série oscila entre 4.674 e 4.688 prédios. São 14 prédios de diferença em
    4.688 — ruído de quem está contando pixels na borda de um polígono, não
    informação. A tolerância é 1% do total de prédios do bairro: abaixo disso a
    queda é ruído, acima é defeito e merece olhar.
    """
    df = df.copy()
    for bairro, bloco in df.groupby("bairro", sort=False):
        bloco = bloco.sort_values("nivel_m")
        s = bloco["affected_buildings"].to_numpy()
        limite = bloco["total_buildings"].iloc[0] * tolerancia
        for i in range(1, len(s)):
            if 0 < s[i - 1] - s[i] <= limite \
                    and df.loc[bloco.index[i], "qualidade"] == "ok":
                df.loc[bloco.index[i], "qualidade"] = "ruido_borda"
    return df


def conserta_faltantes(df: pd.DataFrame) -> pd.DataFrame:
    """Interpola linearmente os faltantes ao longo do nível de água.

    Interpolação linear porque entre dois níveis vizinhos (10 cm de diferença)
    a curva é praticamente reta — não é o caso de ajustar nada mais elaborado.
    Arredondo para inteiro porque prédio e pessoa não são fracionários.
    """
    df = df.copy()
    for c in ("affected_buildings", "affected_population"):
        df[c] = df[c].astype(float)
        df.loc[df["qualidade"] == "faltante", c] = pd.NA

    df = df.sort_values(["bairro", "nivel_m"])
    for c in ("affected_buildings", "affected_population"):
        df[c] = (df.groupby("bairro")[c]
                   .transform(lambda s: s.interpolate(method="linear",
                                                      limit_direction="both"))
                   .round().astype("Int64"))
    return df.sort_values(["bairro", "nivel_m"], ignore_index=True)


def recalcula_proporcoes(df: pd.DataFrame) -> pd.DataFrame:
    """Proporção como número, e população afetada reestimada.

    Duas correções aqui, e a segunda é a que mais importa.

    A primeira é o `percentage`: ele vem arredondado para cima, então um bairro
    com um prédio afetado em 15.906 aparece com 1% em vez de 0,006%. Recalculo
    a razão e guardo o original como `percentage_origem`.

    A segunda: `affected_population` não é contagem de gente. Testei as 6.674
    linhas e todas, sem exceção, são `percentage / 100 * population` — ou seja,
    a população afetada foi derivada da proporção já arredondada para cima.
    Duas consequências. Ela herda o viés: nunca subestima, e infla o total da
    cidade entre 1,1% e 4,8%, com o pior erro justo nos níveis baixos, que são
    os mais prováveis. E ela só se move em degraus de 1% da população do
    bairro: Santa Tereza tem 50 valores distintos de prédios afetados ao longo
    dos 71 níveis, mas só três de população afetada (0, 314 e 628).

    Então estimo a população afetada pela razão de prédios, que tem a
    granularidade real da simulação, e deixo a de origem ao lado para quem
    quiser comparar.
    """
    df = df.copy()
    df["pct_predios"] = (df["affected_buildings"] / df["total_buildings"] * 100).round(3)

    df["pop_afetada_est"] = (df["affected_buildings"] / df["total_buildings"]
                             * df["population"]).round().astype("Int64")
    df["pct_pop_est"] = (df["pop_afetada_est"] / df["population"] * 100).round(3)

    # O quanto cada campo de origem inflava. Guardo porque é o argumento para
    # não usar nenhum dos dois em análise.
    df["pct_inflado_pp"] = (df["percentage_origem"] - df["pct_predios"]).round(3)
    df["pop_inflada"] = (df["affected_population"] - df["pop_afetada_est"]).astype("Int64")
    return df


def confere(df: pd.DataFrame) -> list[str]:
    """Checagens que têm que passar depois da limpeza."""
    problemas = []
    if len(df) != 71 * 94:
        problemas.append(f"esperava 6674 linhas, veio {len(df)}")
    if df["chave"].isna().any():
        problemas.append("chave nula em alguma linha")
    if (df["affected_buildings"] > df["total_buildings"]).any():
        problemas.append("prédios afetados acima do total")
    if (df["affected_population"] > df["population"]).any():
        problemas.append("população afetada acima do total")

    # total_buildings e population são denominadores: não podem variar com o
    # nível de água dentro do mesmo bairro.
    for c in ("total_buildings", "population"):
        varia = df.groupby("bairro")[c].nunique()
        if (varia > 1).any():
            problemas.append(f"{c} varia por nível em {int((varia > 1).sum())} bairros")

    # Depois do conserto, só o Espírito Santo deveria sobrar com queda.
    quedas = {}
    for bairro, bloco in df.groupby("bairro"):
        s = bloco.sort_values("nivel_m")["affected_buildings"].to_numpy()
        n = sum(1 for i in range(1, len(s)) if s[i] < s[i - 1])
        if n:
            quedas[bairro] = n
    # Queda é esperada só onde há linha marcada: suspeita (Espírito Santo) ou
    # ruído de borda (Arquipélago). Qualquer outra queda é defeito novo.
    explicado = set(df.loc[df["qualidade"].str.startswith(("suspeito", "ruido")),
                           "bairro"])
    inesperadas = {b: n for b, n in quedas.items() if b not in explicado}
    if inesperadas:
        problemas.append(f"quedas não explicadas: {inesperadas}")
    return problemas


def main() -> int:
    if not ENTRADA.exists():
        print(f"não achei {ENTRADA.relative_to(RAIZ)}")
        return 1

    bruto = json.loads(ENTRADA.read_text(encoding="utf-8"))
    niveis = sorted(bruto, key=nivel_para_metro)
    print(f"{len(niveis)} níveis, de {niveis[0]} a {niveis[-1]} "
          f"({nivel_para_metro(niveis[0])} m a {nivel_para_metro(niveis[-1])} m)")

    df = para_tabela(bruto)
    print(f"desaninhado: {len(df)} linhas, {df['bairro'].nunique()} bairros\n")

    df = marca_faltantes(df)
    df = marca_suspeitos(df)
    df = marca_ruido(df)
    antes = df["qualidade"].value_counts()
    print("Classificação das linhas:")
    for rotulo, n in antes.items():
        print(f"  {rotulo:<16} {n:>5}")

    faltantes = df[df["qualidade"] == "faltante"][["bairro", "nivel_origem"]]
    if len(faltantes):
        print("\nFaltantes interpolados:")
        for _, r in faltantes.iterrows():
            print(f"  {r['bairro']:<20} {r['nivel_origem']}")

    ruido = df[df["qualidade"] == "ruido_borda"]
    if len(ruido):
        print("\nRuído de borda (queda abaixo de 1% do total, mantida):")
        for bairro, bloco in ruido.groupby("bairro"):
            serie = (df[df["bairro"] == bairro].sort_values("nivel_m")
                     ["affected_buildings"].to_numpy())
            maior = max(serie[i - 1] - serie[i] for i in range(1, len(serie))
                        if serie[i] < serie[i - 1])
            tot = bloco["total_buildings"].iloc[0]
            print(f"  {bairro:<20} {len(bloco)} queda(s), a maior de {maior} "
                  f"prédios em {tot:,} ({maior / tot * 100:.2f}%)")

    suspeitos = df[df["qualidade"].str.startswith("suspeito")]
    if len(suspeitos):
        print("\nSuspeitos deixados como vieram (valor original preservado):")
        for bairro, bloco in suspeitos.groupby("bairro"):
            tipos = bloco["qualidade"].value_counts().to_dict()
            print(f"  {bairro:<20} {len(bloco)} linha(s)  {tipos}")

    df = conserta_faltantes(df)
    df = recalcula_proporcoes(df)

    print(f"\nCampos de origem recalculados")
    print(f"  percentage inflado em média {df['pct_inflado_pp'].mean():+.3f} p.p. "
          f"(máximo {df['pct_inflado_pp'].max():+.3f})")
    pior = df.loc[df[df['affected_buildings'] > 0]
                  .eval("percentage_origem / pct_predios").idxmax()]
    print(f"    pior caso: {pior['bairro']} em {pior['nivel_origem']} — "
          f"{pior['pct_predios']}% virou {pior['percentage_origem']}%")
    print(f"  affected_population inflada em {df['pop_inflada'].sum():+,} pessoas "
          f"somando as 6.674 linhas")
    for nv in (3.0, 5.0, 10.0):
        corte = df[df["nivel_m"] == nv]
        o, e = corte["affected_population"].sum(), corte["pop_afetada_est"].sum()
        print(f"    cidade em {nv:>4.1f} m: origem {o:>9,} | estimado {e:>9,} "
              f"({(o - e) / e * 100:+.1f}%)")

    problemas = confere(df)
    print("\nChecagens finais:", "todas passaram" if not problemas else "")
    for p in problemas:
        print(f"  FALHA  {p}")

    SAIDA.mkdir(parents=True, exist_ok=True)
    colunas = ["nivel_m", "nivel_origem", "bairro", "chave",
               "total_buildings", "affected_buildings", "pct_predios",
               "population", "pop_afetada_est", "pct_pop_est",
               "percentage_origem", "pct_inflado_pp",
               "affected_population", "pop_inflada", "qualidade"]
    df[colunas].to_csv(SAIDA / "inct_niveis_bairro.csv", index=False)

    # Resumo por bairro, que é o formato que serve para juntar com a malha.
    resumo = (df.groupby(["bairro", "chave"], as_index=False)
                .agg(total_buildings=("total_buildings", "first"),
                     population=("population", "first"),
                     nivel_inicio=("nivel_m", "first"),
                     linhas_suspeitas=("qualidade",
                                       lambda s: int(s.str.startswith("suspeito").sum())),
                     linhas_interpoladas=("qualidade",
                                          lambda s: int((s == "faltante").sum())),
                     linhas_ruido=("qualidade",
                                   lambda s: int((s == "ruido_borda").sum()))))
    # Nível em que o bairro começa a alagar: primeiro com afetado > 0.
    comeco = (df[df["affected_buildings"] > 0]
              .groupby("bairro")["nivel_m"].min().rename("nivel_primeiro_alagamento"))
    resumo = resumo.drop(columns="nivel_inicio").merge(
        comeco, left_on="bairro", right_index=True, how="left")
    for nv in (3.0, 5.0, 10.0):
        corte = df[df["nivel_m"] == nv].set_index("bairro")["pct_pop_est"]
        resumo[f"pct_pop_est_{nv:g}m"] = resumo["bairro"].map(corte)
    resumo.to_csv(SAIDA / "inct_qualidade.csv", index=False)

    print(f"\nGravado:")
    print(f"  dados/processados/inct_niveis_bairro.csv  ({len(df)} linhas)")
    print(f"  dados/processados/inct_qualidade.csv      ({len(resumo)} bairros)")
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
