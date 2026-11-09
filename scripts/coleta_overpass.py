"""Coleta de pontos de interesse de Porto Alegre no OpenStreetMap (Overpass API).

Fonte: OpenStreetMap contributors, licença ODbL
       https://www.openstreetmap.org/copyright
API:   https://overpass-api.de/api/interpreter

Saídas:
  dados/originais/overpass_<categoria>.json   resposta bruta + metadados (data de coleta)
  dados/processados/osm_pontos_interesse.csv  tabela única: categoria, tipo, id, nome, lat, lon

Uso:
  python scripts/coleta_overpass.py          # usa o cache se o bruto já existir
  python scripts/coleta_overpass.py --force  # refaz as requisições
"""
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

URL = "https://overpass-api.de/api/interpreter"
# Sem User-Agent identificado o servidor responde 406.
HEADERS = {"User-Agent": "projeto-academico-pucrs/1.0 (luiggipn@gmail.com)"}

RAIZ = Path(__file__).resolve().parent.parent
ORIGINAIS = RAIZ / "dados" / "originais"
PROCESSADOS = RAIZ / "dados" / "processados"

AREA = 'area["name"="Porto Alegre"]["boundary"="administrative"]["admin_level"="8"]->.a;'

# categoria -> filtros OSM (cada filtro vira uma linha da consulta)
CATEGORIAS = {
    "escolas": ['nwr["amenity"="school"](area.a);'],
    "saude": ['nwr["amenity"~"^(hospital|clinic)$"](area.a);',
              'nwr["healthcare"="hospital"](area.a);'],
    # Abrigos PERMANENTES de assistência social (albergues, casas de acolhimento).
    # NÃO são os abrigos temporários da enchente de 2024, que quase não existem no OSM.
    "abrigos_sociais": ['nwr["social_facility"="shelter"](area.a);'],
}


def consulta(filtros):
    corpo = "\n".join(filtros)
    return f"[out:json][timeout:120];\n{AREA}\n(\n{corpo}\n);\nout center tags;"


def baixar(categoria, filtros, tentativas=4):
    q = consulta(filtros)
    for i in range(1, tentativas + 1):
        r = requests.post(URL, data={"data": q}, headers=HEADERS, timeout=180)
        if r.status_code == 200:
            return {
                "fonte": URL,
                "licenca": "ODbL - © OpenStreetMap contributors",
                "coletado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "categoria": categoria,
                "consulta": q,
                "resposta": r.json(),
            }
        if r.status_code in (429, 504):
            espera = 15 * i
            print(f"  {categoria}: HTTP {r.status_code}, aguardando {espera}s")
            time.sleep(espera)
            continue
        r.raise_for_status()
    raise RuntimeError(f"Overpass não respondeu para '{categoria}'")


def coletar(force=False):
    ORIGINAIS.mkdir(parents=True, exist_ok=True)
    brutos = {}
    for cat, filtros in CATEGORIAS.items():
        arq = ORIGINAIS / f"overpass_{cat}.json"
        if arq.exists() and not force:
            print(f"{cat}: usando cache ({arq.name})")
            brutos[cat] = json.loads(arq.read_text(encoding="utf-8"))
            continue
        print(f"{cat}: consultando Overpass...")
        brutos[cat] = baixar(cat, filtros)
        arq.write_text(json.dumps(brutos[cat], ensure_ascii=False, indent=1), encoding="utf-8")
        time.sleep(5)  # cortesia com o servidor público
    return brutos


def para_tabela(brutos):
    linhas = []
    for cat, dados in brutos.items():
        for el in dados["resposta"]["elements"]:
            # node tem lat/lon; way/relation trazem o centro em "center"
            c = el if "lat" in el else el.get("center", {})
            tags = el.get("tags", {})
            linhas.append({
                "categoria": cat,
                "osm_tipo": el["type"],
                "osm_id": el["id"],
                "nome": tags.get("name"),
                "amenity": tags.get("amenity"),
                "rua": tags.get("addr:street"),
                "numero": tags.get("addr:housenumber"),
                "lat": c.get("lat"),
                "lon": c.get("lon"),
                "coletado_em": dados["coletado_em"],
            })
    df = pd.DataFrame(linhas)
    antes = len(df)
    # o mesmo objeto pode casar em mais de um filtro da mesma categoria
    df = df.drop_duplicates(subset=["categoria", "osm_tipo", "osm_id"])
    sem_coord = df[["lat", "lon"]].isna().any(axis=1).sum()
    print(f"\n{antes} registros, {antes - len(df)} duplicados removidos, {sem_coord} sem coordenada")
    return df.dropna(subset=["lat", "lon"]).reset_index(drop=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="refaz as requisições")
    df = para_tabela(coletar(ap.parse_args().force))
    PROCESSADOS.mkdir(parents=True, exist_ok=True)
    saida = PROCESSADOS / "osm_pontos_interesse.csv"
    df.to_csv(saida, index=False, encoding="utf-8")
    print(df.groupby("categoria").size().to_string())
    print(f"Salvo em {saida}")
