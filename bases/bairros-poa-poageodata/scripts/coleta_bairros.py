"""
  3. Malha oficial dos bairros de Porto Alegre — Prefeitura (ArcGIS REST)
  4. POAGEODATA — dados geoespaciais por bairro (Zenodo, DOI 10.5281/zenodo.14807279)

Grava o dado bruto em dados/originais/ e nunca é chamado pelo dashboard: uma
coleta, muitas execuções da análise. Rodando de novo, usa o cache do disco a
menos que --forcar seja passado.

Uso:
    python scripts/coleta_bairros.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ORIGINAIS = RAIZ / "dados" / "originais"
UA = "projeto-extensionista-inct-simai/1.0 (+uso academico; coleta pontual)"
TEMPO_LIMITE = 180

BAIRROS_URL = (
    "https://gis-smamus.portoalegre.rs.gov.br/server/rest/services"
    "/01_PUBLICACOES/bairros_2016/MapServer/0/query"
    "?where=1%3D1&outFields=*&outSR=4674&f=geojson"
)

POAGEODATA_DOI = "10.5281/zenodo.14807279"
POAGEODATA_BASE = "https://zenodo.org/records/14807279/files/"
POAGEODATA_ARQUIVOS = {
    "basico": "POA_bairros_basico_SIRGAS2000_22S.gpkg",
    "demografia_simplificada": "POA_bairros_demografia_simplificada_SIRGAS2000_22S.gpkg",
    "demografia_expandida": "POA_bairros_demografia_expandida_SIRGAS2000_22S.gpkg",
    "mortalidade": "POA_bairros_mortalidade_SIRGAS2000_22S.gpkg",
}
# MD5 publicados na página do Zenodo em 07/11/2026. Servem de conferência de
# integridade: se o arquivo baixado não bater, a versão mudou ou veio corrompido.
POAGEODATA_MD5 = {
    "POA_bairros_basico_SIRGAS2000_22S.gpkg": "68766507a4deeef0e4d1255ad5997b80",
    "POA_bairros_demografia_expandida_SIRGAS2000_22S.gpkg": "3da8f4adfdc176c9392d83e01b449d0a",
    "POA_bairros_demografia_simplificada_SIRGAS2000_22S.gpkg": "bb72a8e59c23da14bfba3feb7a73b9b4",
    "POA_bairros_mortalidade_SIRGAS2000_22S.gpkg": "821038b8f06ae1a9fb28625b7111f465",
}



def agora():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def robots_permite(url: str) -> tuple[bool, str]:
    """Lê o robots.txt do domínio antes da primeira requisição a ele.

    Domínio que não publica robots.txt é tratado como permitido, que é o
    comportamento padrão do protocolo.
    """
    partes = urllib.parse.urlsplit(url)
    robots = f"{partes.scheme}://{partes.netloc}/robots.txt"
    leitor = urllib.robotparser.RobotFileParser()
    leitor.set_url(robots)
    try:
        leitor.read()
    except Exception as erro:
        return True, f"robots.txt não lido ({type(erro).__name__}); tratado como permitido"
    return leitor.can_fetch(UA, url), f"robots.txt lido em {robots}"


def baixar(url: str, destino: Path, forcar: bool = False) -> dict:
    """Baixa com cache em disco. Devolve o envelope de coleta."""
    registro = {
        "url": url,
        "arquivo": str(destino.relative_to(RAIZ)),
        "datahora_utc": agora(),
        "origem_cache": False,
        "status": None,
        "bytes": None,
        "md5": None,
        "mensagem": None,
    }

    if destino.exists() and not forcar:
        bruto = destino.read_bytes()
        registro.update(origem_cache=True, status="cache", bytes=len(bruto),
                        md5=hashlib.md5(bruto).hexdigest(),
                        mensagem="arquivo já existia; use --forcar para rebaixar")
        return registro

    permitido, nota = robots_permite(url)
    registro["robots"] = nota
    if not permitido:
        registro.update(status="bloqueado",
                        mensagem="robots.txt do domínio proíbe esta requisição")
        return registro

    destino.parent.mkdir(parents=True, exist_ok=True)
    pedido = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(pedido, timeout=TEMPO_LIMITE) as resposta:
            bruto = resposta.read()
            registro["status"] = resposta.status
    except urllib.error.HTTPError as erro:
        registro.update(status=erro.code, mensagem=f"HTTPError: {erro.reason}")
        return registro
    except Exception as erro:
        registro.update(status="erro", mensagem=f"{type(erro).__name__}: {erro}")
        return registro

    destino.write_bytes(bruto)
    registro.update(bytes=len(bruto), md5=hashlib.md5(bruto).hexdigest(),
                    mensagem="baixado")
    return registro


#bases
def coletar_bairros(forcar=False) -> dict:
    destino = ORIGINAIS / "bairros_poa_2016.geojson"
    registro = baixar(BAIRROS_URL, destino, forcar)

    resumo = {}
    if destino.exists():
        try:
            dados = json.loads(destino.read_text(encoding="utf-8"))
        except json.JSONDecodeError as erro:
            resumo["erro_leitura"] = str(erro)
        else:
            feicoes = dados.get("features", [])
            resumo["n_feicoes"] = len(feicoes)
            resumo["crs"] = dados.get("crs")
            # O ArcGIS avisa quando cortou o resultado. Sem esse aviso, vieram
            # todas as feições em uma chamada só.
            resumo["excedeu_limite"] = dados.get("exceededTransferLimit", False)
            if feicoes:
                props = feicoes[0].get("properties", {})
                resumo["campos"] = sorted(props.keys())
                resumo["tipos_geometria"] = sorted(
                    {f.get("geometry", {}).get("type") for f in feicoes})

    return {
        "base": "bairros_poa_2016",
        "titulo": "Malha oficial dos bairros de Porto Alegre",
        "fonte": {
            "instituicao": "Prefeitura Municipal de Porto Alegre",
            "servico": "01_PUBLICACOES/bairros_2016/MapServer/0",
            "url": BAIRROS_URL,
            "licenca": "dado público municipal; exige citação da Prefeitura",
            "observacao": "mesma malha divulgada pelo ObservaPOA; divisão de 2016",
        },
        "coleta": registro,
        "resumo": resumo,
    }


def coletar_poageodata(forcar=False) -> dict:
    registros, resumo = {}, {}
    for apelido, nome in POAGEODATA_ARQUIVOS.items():
        destino = ORIGINAIS / "poageodata" / nome
        reg = baixar(POAGEODATA_BASE + nome + "?download=1", destino, forcar)

        esperado = POAGEODATA_MD5.get(nome)
        if reg.get("md5") and esperado:
            reg["md5_confere"] = (reg["md5"] == esperado)
            if not reg["md5_confere"]:
                reg["mensagem"] = (f"{reg['mensagem']} — MD5 diferente do "
                                   f"publicado; a versão pode ter mudado")
        registros[apelido] = reg
        resumo[apelido] = reg.get("bytes")

    return {
        "base": "poageodata",
        "titulo": "POAGEODATA — dados geoespaciais por bairro de Porto Alegre",
        "fonte": {
            "instituicao": "Giovani Longo Rosa (UFRGS/PROPUR), via Zenodo",
            "doi": POAGEODATA_DOI,
            "url": "https://zenodo.org/records/14807279",
            "licenca": "CC BY 4.0",
            "observacao": ("v1.0 de 07/02/2025; quatro GeoPackages separados, "
                           "SIRGAS 2000 UTM 22S; base Censo 2022 e mortalidade 2022"),
        },
        "coleta": registros,
        "resumo": resumo,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--forcar", action="store_true",
                    help="rebaixa mesmo se o arquivo já existir em disco")
    args = ap.parse_args()

    ORIGINAIS.mkdir(parents=True, exist_ok=True)
    inicio = time.time()

    saida = {
        "projeto": "Projeto Extensionista INCT SiMAI — Fase 2",
        "responsavel": "Gabriel Erich Franco",
        "datahora_utc": agora(),
        "bases": [coletar_bairros(args.forcar), coletar_poageodata(args.forcar)],
    }

    manifesto = ORIGINAIS / "coleta_bairros_manifesto.json"
    manifesto.write_text(json.dumps(saida, ensure_ascii=False, indent=2),
                         encoding="utf-8")

    print(f"Coleta em {time.time() - inicio:.1f}s. Manifesto: "
          f"{manifesto.relative_to(RAIZ)}\n")

    falhou = False
    for base in saida["bases"]:
        print(f"[{base['base']}]")
        coleta = base["coleta"]
        itens = coleta.items() if isinstance(coleta, dict) and "url" not in coleta \
            else [(base["base"], coleta)]
        for apelido, reg in itens:
            marca = "ok " if reg["status"] in (200, "cache") else "FALHA"
            tam = f"{reg['bytes']/1_048_576:.1f} MB" if reg.get("bytes") else "—"
            cache = " (cache)" if reg.get("origem_cache") else ""
            print(f"  {marca} {apelido:<26} {tam:>9}{cache}  {reg['mensagem']}")
            if reg["status"] not in (200, "cache"):
                falhou = True
            if reg.get("md5_confere") is False:
                print(f"       ATENÇÃO: MD5 não confere com o publicado no Zenodo")
        if base.get("resumo"):
            print(f"  resumo: {base['resumo']}")
        print()

    return 1 if falhou else 0


if __name__ == "__main__":
    sys.exit(main())
