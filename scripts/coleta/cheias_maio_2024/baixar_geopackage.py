from pathlib import Path
import requests

RAIZ = Path(__file__).resolve().parents[3]

DESTINO = RAIZ / 'dados' / 'brutos'
DESTINO.mkdir(parents=True, exist_ok=True)

URL = (
    'https://zenodo.org/records/11185049/files/cheias_rhguaiba_2024_db_v5.gpkg?download=1'
)

ARQUIVO = DESTINO / 'cheias_rhguaiba_2024_db_v5.gpkg'

if ARQUIVO.exists():
    print(f'O arquivo {ARQUIVO.name} já existe. Nenhum download será realizado.')
else:
    try:
        print(f'Baixando o arquivo {ARQUIVO.name}...')

        with requests.get(
            URL, stream=True, timeout=(10, 120) 
        ) as resposta:
            resposta.raise_for_status()
            with open(ARQUIVO, 'wb') as arquivo:
                for chunk in resposta.iter_content(chunk_size= 1024 ** 2):
                    if chunk:
                        arquivo.write(chunk)
        print(f'Arquivo {ARQUIVO.name} baixado com sucesso.')
    
    except (requests.exceptions.RequestException, OSError) as e:
        print(f'Erro ao baixar o arquivo: {e}')
        if ARQUIVO.exists():
            ARQUIVO.unlink()

    except Exception as e:
        print(f'Ocorreu um erro inesperado: {e}')
        if ARQUIVO.exists():
            ARQUIVO.unlink()