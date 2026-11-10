from pathlib import Path
import pdfplumber
import pandas as pd

RAIZ = Path(__file__).resolve().parents[3]

PDF = RAIZ / 'dados' / 'brutos' / 'atlas_risco_inundacoes_2025.pdf'

DESTINO = RAIZ / 'dados' / 'extraidos'
DESTINO.mkdir(parents=True, exist_ok=True)

PAGINAS = [43,44,45]

with pdfplumber.open(PDF) as pdf:
    for numero in PAGINAS:
        pagina = pdf.pages[numero -1]
        tabelas = pagina.extract_tables()

        print(f'Página {numero} - {len(tabelas)} tabelas encontradas')

        for i, tabela in enumerate(tabelas, start=1):
            if not tabela or not any(
                celula is not None and str(celula).strip() for linha in tabela for celula in linha
            ):
                continue

            df = pd.DataFrame(tabela)

            arquivo_saida = DESTINO / f'atlas_{numero}_{i}.csv'
            df.to_csv(arquivo_saida, index=False, header=False, encoding='utf-8-sig')
            print(f'Arquivo salvo: {arquivo_saida.name}')