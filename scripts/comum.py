
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
ORIGINAIS = RAIZ  # os brutos ficam soltos na raiz da pasta, como vieram
REFERENCIA = RAIZ / "dados" / "referencia"
SAIDA = RAIZ / "dados" / "processados"

COD_POA = "4314902"

ARQ_SETORES = ORIGINAIS / "Agregados_por_setores_basico_BR_20260520" / "Agregados_por_setores_basico_BR.csv"
ARQ_BAIRROS = ORIGINAIS / "Agregados_por_bairros_basico_BR_20260520" / "Agregados_por_bairros_basico_BR.csv"
ARQ_CNEFE = ORIGINAIS / "4314902_PORTO_ALEGRE.csv"
ARQ_S2ID = ORIGINAIS / "s2id_master_2013_2025 2.csv"

UF_SIGLA = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO",
    "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL",
    "28": "SE", "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP", "41": "PR",
    "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF",
}

APELIDOS = {
    "CORONEL APARICIO BORGES": "CEL APARICIO BORGES",
    "PASSO D AREIA": "PASSO DA AREIA",
    "PASSO DAREIA": "PASSO DA AREIA",
}

ASPAS = dict.fromkeys(map(ord, "'`´’‘ʼ\x92"), None)


def normaliza(nome) -> str | None:
    """Caixa alta, sem acento, sem pontuação, espaços simples."""
    if nome is None or (isinstance(nome, float) and pd.isna(nome)):
        return None
    s = str(nome).replace(" ", " ").translate(ASPAS)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^A-Z0-9 ]", " ", s.upper())
    return re.sub(r"\s+", " ", s).strip()


def chave(nome) -> str | None:
    """Chave de junção de bairros: normaliza, resolve apelidos, tira espaços."""
    k = normaliza(nome)
    if k is None:
        return None
    return APELIDOS.get(k, k).replace(" ", "")


def corrige_apostrofo(s: pd.Series) -> pd.Series:
    """Crase, acento agudo e aspas tipográficas usados como apóstrofo viram `'`."""
    return s.str.replace(r"[`´’‘\x92]", "'", regex=True)


def num_br(s: pd.Series) -> pd.Series:
    """'0,6282427' -> 0.6282427. O IBGE usa vírgula decimal e '.' para vazio."""
    return pd.to_numeric(s.str.replace(",", ".", regex=False).replace(".", None),
                         errors="coerce")


def le_ibge(caminho: Path, **kw) -> pd.DataFrame:
    """CSV do IBGE: separador ';', codificação Windows-1252 (não latin-1:
    o `’` de Mont’Serrat é o byte 0x92, que só o cp1252 decodifica)."""
    return pd.read_csv(caminho, sep=";", encoding="cp1252", dtype=str, **kw)
