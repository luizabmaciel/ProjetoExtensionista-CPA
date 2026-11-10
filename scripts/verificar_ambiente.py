"""Confere se o ambiente geoespacial está de pé antes de abrir o notebook.

A instalação do geopandas pode dar certo e ainda assim faltar o driver que lê
GeoPackage, ou a projeção sair errada. Em vez de descobrir isso no meio da
análise, este script faz um teste pequeno e verificável: desenha um quadrado
de 1 km de lado perto de Porto Alegre, reprojeta para UTM e confere se a área
calculada dá 1 km². Se der, o pacote inteiro está funcionando.

Uso:
    python scripts/verificar_ambiente.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

LADO_M = 1000.0
TOLERANCIA = 0.01  # 1% de folga; a reprojeção não é exata, mas erra pouco


def main() -> int:
    print("Verificando o ambiente geoespacial\n")

    try:
        import geopandas as gpd
        import pandas as pd
        from shapely.geometry import box
    except ImportError as erro:
        print(f"  FALHA  import: {erro}")
        print("\n  Instale com:  pip install -r requirements.txt")
        return 1

    print(f"  ok   geopandas {gpd.__version__}")
    print(f"  ok   pandas    {pd.__version__}")

    try:
        import pyogrio
        print(f"  ok   pyogrio   {pyogrio.__version__}")
        drivers = set(pyogrio.list_drivers())
    except ImportError:
        print("  aviso  pyogrio não instalado; o geopandas vai cair no fiona")
        drivers = set()

    for driver in ("GPKG", "GeoJSON"):
        if not drivers or driver in drivers:
            print(f"  ok   driver {driver} disponível")
        else:
            print(f"  FALHA  driver {driver} ausente — não dá para ler as bases")
            return 1

    # Quadrado de 1 km de lado em UTM 22S, na altura de Porto Alegre. Começo
    # pela projeção métrica justamente para saber qual é a resposta certa.
    print("\n  Teste de reprojeção e cálculo de área")
    x0, y0 = 480000.0, 6670000.0
    quadrado = gpd.GeoDataFrame(
        {"nome": ["quadrado de teste"]},
        geometry=[box(x0, y0, x0 + LADO_M, y0 + LADO_M)],
        crs="EPSG:31982",
    )

    area_utm = quadrado.area.iloc[0]
    print(f"       área em EPSG:31982 .... {area_utm/1e6:.6f} km²")

    # Ida e volta: para coordenadas geográficas e de volta para métricas. Se a
    # área sobreviver ao percurso, a cadeia de projeção está correta.
    geografico = quadrado.to_crs("EPSG:4674")
    print(f"       área em EPSG:4674 ..... {geografico.area.iloc[0]:.8f} "
          "(graus quadrados — número sem significado físico)")

    volta = geografico.to_crs("EPSG:31982")
    area_volta = volta.area.iloc[0]
    erro_rel = abs(area_volta - LADO_M**2) / LADO_M**2
    print(f"       de volta em EPSG:31982  {area_volta/1e6:.6f} km²  "
          f"(erro de {erro_rel*100:.4f}%)")

    if erro_rel > TOLERANCIA:
        print(f"\n  FALHA  a área não voltou para 1 km². A reprojeção está errada.")
        return 1
    print("  ok   reprojeção preserva a área")

    # Escrever e ler de volta um GeoPackage, que é o formato do POAGEODATA.
    print("\n  Teste de escrita e leitura de GeoPackage")
    with tempfile.TemporaryDirectory() as pasta:
        caminho = Path(pasta) / "teste.gpkg"
        try:
            quadrado.to_file(caminho, driver="GPKG")
            lido = gpd.read_file(caminho)
        except Exception as erro:
            print(f"  FALHA  {type(erro).__name__}: {erro}")
            return 1

    if len(lido) != 1 or lido.crs.to_epsg() != 31982:
        print(f"  FALHA  o arquivo voltou diferente: {len(lido)} feição(ões), "
              f"CRS {lido.crs}")
        return 1
    print("  ok   GeoPackage escrito e lido com o CRS preservado")

    print("\nAmbiente pronto. Pode rodar a coleta e abrir o notebook.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
