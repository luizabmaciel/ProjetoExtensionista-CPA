"""Gera a série do nível do Guaíba usada na Tela 3 do dashboard.

Entradas (dados/originais/):
  hidroweb_telemetrica_87444000.csv          estação Usina do Gasômetro, baixada do HidroWeb (ANA)
  ana_telemetria_leituras_transcritas.csv    estação Cais Mauá C6, copiada da tabela do Hidro-Telemetria
                                             (o arquivo do HidroWeb dessa estação veio vazio)
Saída:
  dados/processados/nivel_guaiba_horario.csv (data_hora, nivel_m, estacao)

Rodar a partir da raiz do repositório:
    .venv/bin/python scripts/serie_nivel_guaiba.py
"""
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
ORIG = RAIZ / "dados" / "originais"
SAIDA = RAIZ / "dados" / "processados" / "nivel_guaiba_horario.csv"

# 1. Gasômetro (arquivo oficial): separador ";", acentos em latin-1, hora em coluna separada
gaso = pd.read_csv(ORIG / "hidroweb_telemetrica_87444000.csv", sep=";", encoding="latin-1")
gaso = gaso.rename(columns={"Data": "data", "Hora": "hora", "Nível (cm)": "nivel_cm"})
gaso["data_hora"] = pd.to_datetime(gaso.data + " " + gaso.hora, format="%d/%m/%Y %H:%M:%S")
gaso["nivel_cm"] = pd.to_numeric(gaso.nivel_cm.astype(str).str.strip(), errors="coerce")  # vazio -> NaN
gaso["estacao"] = 87444000
print(f"Gasômetro: {len(gaso)} registros, {gaso.nivel_cm.notna().sum()} com nível")

# 2. Cais Mauá (copiado à mão): só as linhas dessa estação
cais = pd.read_csv(ORIG / "ana_telemetria_leituras_transcritas.csv", parse_dates=["data_hora"])
cais = cais[cais.estacao_codigo == 87450004].rename(columns={"estacao_codigo": "estacao"})
print(f"Cais Mauá: {len(cais)} registros, {cais.nivel_cm.notna().sum()} com nível")

# 3. junta, tira registros sem nível, cm -> m, ordena no tempo
serie = pd.concat([cais[["data_hora", "nivel_cm", "estacao"]], gaso[["data_hora", "nivel_cm", "estacao"]]])
serie = serie.dropna(subset=["nivel_cm"])
serie["nivel_m"] = serie.nivel_cm / 100
serie = serie.sort_values("data_hora")[["data_hora", "nivel_m", "estacao"]]

# 4. checagens: um registro por horário, valores plausíveis e as leituras oficiais conhecidas
assert serie.data_hora.is_unique, "horário repetido"
assert serie.nivel_m.between(1, 6).all(), "nível fora da faixa esperada"
leitura = serie.set_index("data_hora").nivel_m
assert leitura["2024-05-04 12:00"] == 5.09, "deveria bater com a nota da Prefeitura (5,09 m às 12h de 04/05)"
assert leitura.max() == 5.35, "deveria bater com o recorde de 5,35 m"

serie.to_csv(SAIDA, index=False)
print(f"{len(serie)} leituras salvas em {SAIDA.relative_to(RAIZ)}")
print(f"de {serie.data_hora.min()} a {serie.data_hora.max()}; máximo {serie.nivel_m.max():.2f} m")
