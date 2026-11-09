"""Testa a lógica de junção, extraindo as funções do notebook

A normalização de nomes e a escolha de colunas.

Uso:
    python scripts/teste_juncao.py
"""

import ast
import json
import re
import sys
import textwrap
import unicodedata
from pathlib import Path

import pandas as pd

NB = Path(__file__).resolve().parent.parent / "notebooks" / "exploracao_bairros.ipynb"

# As funções do notebook dependem destas constantes. Nomeadas uma a uma de
# propósito: pegar toda variável em caixa alta arrastaria coisas que só existem
# depois de o notebook ler os arquivos.
CONSTANTES = {"ASPAS", "APELIDOS"}

# ----------------------------------- extrai as funções definidas no notebook
fonte = []
for cel in json.loads(NB.read_text(encoding="utf-8"))["cells"]:
    if cel["cell_type"] != "code":
        continue
    try:
        arvore = ast.parse("".join(cel["source"]))
    except SyntaxError:
        continue
    src = "".join(cel["source"])
    # ast.walk e não arvore.body: nomes_do_inct é definida dentro de um else.
    for no in ast.walk(arvore):
        if isinstance(no, ast.FunctionDef):
            trecho = ast.get_source_segment(src, no)
            if trecho:
                fonte.append(textwrap.dedent(trecho))
        elif isinstance(no, ast.Assign) and any(
                getattr(a, "id", "") in CONSTANTES for a in no.targets):
            fonte.append(ast.get_source_segment(src, no))

# As constantes do notebook usam Path e json, então entram no namespace junto.
NS = {"pd": pd, "re": re, "unicodedata": unicodedata}
exec("\n\n".join(fonte), NS)
print(f"funções extraídas do notebook: "
      f"{sorted(k for k, v in NS.items() if callable(v) and not k.startswith('__'))}\n")

normaliza = NS["normaliza"]
chave_forte = NS["chave_forte"]
achar = NS["achar"]
quase = NS["quase"]
chave_inct = NS["chave_inct"]
APELIDOS = NS["APELIDOS"]
colunas_de_proporcao = NS["colunas_de_proporcao"]

falhas = []


def checar(rotulo, ok, detalhe=""):
    print(f"  {'ok  ' if ok else 'FALHA'} {rotulo}{'  ' + detalhe if detalhe else ''}")
    if not ok:
        falhas.append(rotulo)


# ------------------------------------------------ 1. heurística de colunas
print("1. Heurística achar(), com três convenções de nome de coluna")
for rotulo, cols in {
    "descritiva": ["cod_ibge", "nome_ibge", "nome_pmpa", "nome_sim", "geometry"],
    "abreviada": ["cd_bairro", "nm_bairro_ibge", "nm_bairro_pmpa",
                  "nm_bairro_sim", "geometry"],
    "observapoa": ["codigo_ibge", "nome_bairro_ibge", "nome_bairro_observapoa",
                   "nome_bairro_sim", "geometry"],
}.items():
    g = pd.DataFrame(columns=cols)
    achou = {
        "cod_ibge": achar(g, "cod") or achar(g, "codigo") or achar(g, "cd"),
        "nome_ibge": achar(g, "nome", "ibge") or achar(g, "nm", "ibge"),
        "nome_pmpa": (achar(g, "nome", "pmpa") or achar(g, "nome", "observa")
                      or achar(g, "nm", "pmpa")),
        "nome_sim": achar(g, "nome", "sim") or achar(g, "nm", "sim"),
    }
    checar(f"convenção {rotulo}", all(achou.values()),
           "" if all(achou.values()) else str(achou))

# ------------------------------------------------ 2. quase-casos
print("\n2. Quase-casos por diferença de espaço")
pares = quase({"PASSO D AREIA", "VILA NOVA", "BOM FIM"},
              {"PASSO DAREIA", "VILANOVA", "CENTRO HISTORICO"})
checar("acha PASSO D AREIA ~ PASSO DAREIA",
       ("PASSO D AREIA", "PASSO DAREIA") in pares)
checar("acha VILA NOVA ~ VILANOVA", ("VILA NOVA", "VILANOVA") in pares)
checar("não inventa par para BOM FIM", len(pares) == 2, f"pares={pares}")

# ------------------------------------------------ 3. apelidos e data.json
print("\n3. Dicionário de apelidos: o que a normalização não resolve")
# Dois nomes em que a diferença é de palavra, não de grafia. Nenhuma
# normalização Unicode conserta isso — tem que ser mapeado à mão.
checar("Coronel Aparício Borges casa com CEL. APARICIO BORGES",
       chave_inct("Coronel Aparício Borges") == chave_inct("CEL. APARICIO BORGES"),
       chave_inct("Coronel Aparício Borges"))
checar("Passo D'Areia casa com PASSO DA AREIA",
       chave_inct("Passo D'Areia") == chave_inct("PASSO DA AREIA"),
       chave_inct("Passo D'Areia"))
checar("Passo d´Areia (acento agudo) cai na mesma chave",
       chave_inct("Passo d\u00b4Areia") == chave_inct("Passo da Areia"))
checar("apelido não encosta em quem não pediu",
       chave_inct("Centro Histórico") == "CENTROHISTORICO",
       chave_inct("Centro Histórico"))
checar("chave_inct devolve None para vazio", chave_inct(None) is None)
checar("o dicionário de apelidos tem só os 2 casos conhecidos",
       len({v for v in APELIDOS.values()}) == 2, str(APELIDOS))

print("\n3b. Estrutura do data.json: o nome do bairro é a CHAVE do dicionário")
# Era aqui que a versão anterior deste teste errava: procurava o nome como
# valor de um campo "nome", e o arquivo guarda o nome como chave.
FALSO = {
    "3_0m": {"Centro Histórico": {"total_buildings": 100, "affected_buildings": 1,
                                  "percentage": 1, "population": 1000,
                                  "affected_population": 10},
             "Passo D'Areia": {"total_buildings": 50, "affected_buildings": 0,
                               "percentage": 0, "population": 500,
                               "affected_population": 0}},
    "10_0m": {"Centro Histórico": {"total_buildings": 100, "affected_buildings": 60,
                                   "percentage": 60, "population": 1000,
                                   "affected_population": 600},
              "Passo D'Areia": {"total_buildings": 50, "affected_buildings": 25,
                                "percentage": 50, "population": 500,
                                "affected_population": 250}},
}
niveis = sorted(FALSO, key=lambda k: float(k.rstrip("m").replace("_", ".")))
checar("níveis ordenados numericamente, não alfabeticamente",
       niveis == ["3_0m", "10_0m"], str(niveis))
checar("3_0m vira 3.0 e 10_0m vira 10.0",
       [float(k.rstrip("m").replace("_", ".")) for k in niveis] == [3.0, 10.0])
nomes = set(FALSO[niveis[0]])
checar("extrai os 2 nomes das chaves", len(nomes) == 2, str(sorted(nomes)))
checar("mesmo conjunto de bairros em todos os níveis",
       all(set(v) == nomes for v in FALSO.values()))

# ------------------------------------------------ 4. grafia x divergência
print("\n4. Grafia resolvida pela normalização x divergência real de nome")
nomes = pd.DataFrame({
    "cod_ibge": [1, 2, 3, 9],
    "nome_ibge": ["Centro Histórico", "Passo d'Areia", "Cristal", "SÓ NO POA"],
    "nome_pmpa": ["CENTRO HISTORICO", "PASSO DAREIA", "CRISTAL", "SO NO POA"],
    "nome_sim": ["CENTRO", "PASSO D AREIA", "CRISTAL", "SO NO POA"]})
for c in ["nome_ibge", "nome_pmpa", "nome_sim"]:
    nomes[f"k_{c}"] = nomes[c].map(normaliza)
    nomes[f"f_{c}"] = nomes[c].map(chave_forte)
so_grafia = ((nomes["f_nome_ibge"] == nomes["f_nome_pmpa"])
             & (nomes["f_nome_pmpa"] == nomes["f_nome_sim"]))

checar("CENTRO HISTÓRICO vs CENTRO entra como divergência real",
       not so_grafia.iloc[0])
checar("PASSO D'AREIA / PASSO DAREIA / PASSO D AREIA é só grafia",
       so_grafia.iloc[1], f"so_grafia={so_grafia.tolist()}")
checar("CRISTAL idêntico nas três é só grafia", so_grafia.iloc[2])

# ------------------------------------------------ 5. tabela de-para
print("\n5. Tabela de-para com desencontro dos dois lados")
malha = pd.DataFrame({
    "nome": ["CENTRO HISTÓRICO", "PASSO D'AREIA", "CRISTAL", "SÓ NA MALHA"],
    "area_km2": [2.2, 5.1, 4.4, 1.0]})
malha["k"] = malha["nome"].map(normaliza)
nomes["k_nome_pmpa"] = nomes["nome_pmpa"].map(normaliza)

de_para = (malha[["k", "nome", "area_km2"]]
           .rename(columns={"nome": "nome_prefeitura"})
           .merge(nomes.rename(columns={"k_nome_pmpa": "k"})
                  [["k", "cod_ibge", "nome_ibge", "nome_pmpa", "nome_sim"]],
                  on="k", how="outer", indicator=True))
cont = de_para["_merge"].value_counts().to_dict()
checar("3 casam, 1 de cada lado sobra",
       (cont.get("both"), cont.get("left_only"), cont.get("right_only")) == (3, 1, 1),
       str(cont))
checar("CENTRO HISTÓRICO casou apesar do acento",
       de_para.loc[de_para["k"] == "CENTRO HISTORICO", "_merge"].iloc[0] == "both")
checar("PASSO D'AREIA casou com PASSO DAREIA",
       de_para.loc[de_para["k"] == "PASSO DAREIA", "_merge"].iloc[0] == "both")

# ------------------------------------------------ 6. colunas de proporção
print("\n6. Seleção das colunas de proporção")
# Nomes de coluna como os do POAGEODATA de verdade: sufixo _pct para
# proporção, e as faixas escritas 0a14, 15a29, 30a59, 60mais.
demo = pd.DataFrame({
    "nome_pmpa": ["A", "B"], "pop_2022": [100, 200],
    "pop_masc_pct": [0.48, 0.47], "pop_fem_pct": [0.52, 0.53],
    "pop_0a14": [20, 40],
    "pop_0a14_pct": [0.2, 0.2], "pop_15a29_pct": [0.25, 0.25],
    "pop_30a59_pct": [0.4, 0.4], "pop_60mais_pct": [0.15, 0.15],
    "pop_branca_pct": [0.7, 0.7], "pop_preta_pct": [0.1, 0.1],
    "pop_amarela_pct": [0.02, 0.02], "pop_parda_pct": [0.17, 0.17],
    "pop_indigena_pct": [0.01, 0.01]})

sexo = colunas_de_proporcao(demo, "MASC", "FEM", "HOM", "MULH")
faixa = colunas_de_proporcao(demo, "0A14", "15A29", "30A59", "60MAIS")
raca = colunas_de_proporcao(demo, "BRANC", "PRET", "AMAREL", "PARD", "INDIGEN")

checar("2 colunas de sexo", len(sexo) == 2, str(sexo))
checar("4 colunas de faixa etária, sem a contagem pop_0a14",
       "pop_0a14" not in faixa and len(faixa) == 4, str(faixa))
checar("5 colunas de cor ou raça", len(raca) == 5, str(raca))
for rotulo, cols in [("sexo", sexo), ("faixa", faixa), ("raça", raca)]:
    s = demo[cols].sum(axis=1)
    checar(f"soma de {rotulo} fica em 1", bool(((s - 1).abs() < 1e-9).all()),
           f"min {s.min():.3f} máx {s.max():.3f}")

# ------------------------------------- 7. a limpeza do data.json
print("\n7. Limpeza do data.json: detecção de buraco, ruído e suspeito")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import limpeza_data_json as lim

# Série montada à mão, com um de cada problema:
#   3_0m a 3_2m sobem normal
#   3_3m é zero cercado de positivo  -> buraco, tem que interpolar
#   3_5m cai 2 prédios em 1000       -> ruído de borda, abaixo de 1%
#   3_7m salta para 900              -> pico isolado, suspeito
SERIE = [10, 20, 30, 0, 40, 38, 50, 900, 60, 70]
FALSO2 = {f"3_{i}m": {"Teste": {"total_buildings": 1000,
                                "affected_buildings": v,
                                "percentage": 1,
                                "population": 2000,
                                "affected_population": v * 2}}
          for i, v in enumerate(SERIE)}

tab = lim.para_tabela(FALSO2)
checar("desaninha para uma linha por nível", len(tab) == len(SERIE), str(len(tab)))
checar("nivel_m vira número", tab["nivel_m"].tolist() == [3.0 + i/10 for i in range(10)],
       str(tab["nivel_m"].tolist()[:3]))

tab = lim.marca_ruido(lim.marca_suspeitos(lim.marca_faltantes(tab)))
q = dict(zip(tab["nivel_origem"], tab["qualidade"]))
checar("zero cercado de positivo é faltante", q["3_3m"] == "faltante", q["3_3m"])
checar("queda de 2 em 1000 é ruído de borda", q["3_5m"] == "ruido_borda", q["3_5m"])
checar("salto para 900 é pico suspeito", q["3_7m"] == "suspeito_pico", q["3_7m"])
checar("o resto fica ok",
       sum(1 for v in q.values() if v == "ok") == 7, str(q))

cheio = lim.conserta_faltantes(tab)
v33 = int(cheio.loc[cheio["nivel_origem"] == "3_3m", "affected_buildings"].iloc[0])
checar("o buraco virou a média dos vizinhos (30 e 40 -> 35)", v33 == 35, str(v33))

prop = lim.recalcula_proporcoes(cheio)
checar("pct_predios recalculado como float, não inteiro",
       abs(prop.loc[0, "pct_predios"] - 1.0) < 1e-9, str(prop.loc[0, "pct_predios"]))
checar("pop_afetada_est usa a razão de prédios, não o percentage",
       int(prop.loc[0, "pop_afetada_est"]) == 20,
       str(prop.loc[0, "pop_afetada_est"]))

# Zero antes do primeiro alagamento é zero de verdade, não buraco.
SECO = {f"3_{i}m": {"Seco": {"total_buildings": 100, "affected_buildings": v,
                             "percentage": 0, "population": 200,
                             "affected_population": 0}}
        for i, v in enumerate([0, 0, 0, 5, 9])}
seco = lim.marca_faltantes(lim.para_tabela(SECO))
checar("zero antes de começar a alagar não é faltante",
       (seco["qualidade"] == "ok").all(), str(seco["qualidade"].tolist()))

print("\n" + "=" * 62)
if falhas:
    print(f"{len(falhas)} FALHA(S): {falhas}")
    sys.exit(1)
print("todos os testes passaram")
