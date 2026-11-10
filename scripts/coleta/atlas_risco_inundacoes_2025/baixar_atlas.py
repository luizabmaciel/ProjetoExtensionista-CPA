from pathlib import Path
import requests

# Encontrando a raiz do projeto
RAIZ = Path(__file__).resolve().parents[3]

# Diretório onde o arquivo será salvo
DESTINO = RAIZ / 'dados' / 'brutos'

# Cria o diretório se ele não existir
DESTINO.mkdir(parents=True, exist_ok=True)

URL = (
    'https://sema.rs.gov.br/upload/arquivos/202511/27165358-atlas.pdf'
)

ARQUIVO_DESTINO = DESTINO / 'atlas_risco_inundacoes_2025.pdf'

if ARQUIVO_DESTINO.exists():
    print(f'O arquivo {ARQUIVO_DESTINO} já existe. Nenhum download será realizado.')
else:
    try:
        print(f'Baixando o arquivo do Atlas de Risco de Inundações 2025...')

        with requests.get(URL, stream=True, timeout=60) as resposta:
            resposta.raise_for_status()  # Levanta um erro se a requisição falhar
            
            with open(ARQUIVO_DESTINO, 'wb') as arquivo:
                for bloco in resposta.iter_content(chunk_size= 1024 ** 2): # 1 MB
                    if bloco:  # Filtra blocos vazios
                        arquivo.write(bloco)
            print(f'Arquivo baixado com sucesso e salvo em: {ARQUIVO_DESTINO}')

    except (requests.exceptions.RequestException, OSError) as e:
        print(f'Erro ao baixar o arquivo: {e}')
        if ARQUIVO_DESTINO.exists():
            ARQUIVO_DESTINO.unlink()
    
    except Exception as e:
        print(f'Ocorreu um erro inesperado: {e}')
        if ARQUIVO_DESTINO.exists():
            ARQUIVO_DESTINO.unlink()

# POSSIVEIS MELHORIAS:
# -> se o arquivo não for baixado completamente, apagar o arquivo incompleto