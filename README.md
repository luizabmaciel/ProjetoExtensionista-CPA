# Enchentes em Porto Alegre: análise dos dados do INCT SiMAI

Projeto Extensionista da disciplina **Coleta, Preparação e Análise de Dados**, curso de Ciência de Dados da PUCRS.

O projeto parte da simulação do INCT SiMAI, que estima os prédios e as pessoas atingidos em cada bairro de Porto Alegre para níveis do Guaíba de 3,0 a 10,0 m. A essa simulação somamos bases externas:
- equipamentos públicos (escolas e unidades de saúde);
- população (Censo 2022);
- abastecimento de água (as estações de tratamento do Dmae);
- o nível do Guaíba em maio de 2024.

O resultado é apresentado num dashboard em Streamlit.

> **Aviso:** os números são **estimativas** de uma simulação e do que aconteceu em maio de 2024. Não são previsões nem contagens oficiais.

---

## Como rodar

### 1. Pré-requisitos

- Python **3.13** (testado com 3.13.12)
- `git`

### 2. Instalar

Na raiz do repositório:

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

No Windows, troque `.venv/bin/` por `.venv\Scripts\`.

> No Debian ou Ubuntu, o `python3` do sistema pode criar o `.venv` sem o `pip`. Se isso acontecer, use o Python do miniconda ou do Anaconda (`~/miniconda3/bin/python -m venv .venv`) ou instale o pacote `python3-venv`.

### 3. Abrir o dashboard

```bash
.venv/bin/streamlit run app/app.py
```

O navegador abre em <http://localhost:8501>. Para parar, use `Ctrl+C` no terminal.

O comando precisa ser executado **na raiz do repositório**, não dentro de `app/`. Os arquivos de dados já estão versionados, então o dashboard funciona sem refazer a coleta.

### 4. Refazer o processamento (opcional)

Cada etapa lê o resultado da anterior. Rode na ordem abaixo, sempre a partir da raiz:

```bash
# 1. Coleta do OpenStreetMap (usa o cache em dados/originais/; --force coleta de novo)
.venv/bin/python scripts/coleta_overpass.py

# 2. Limpeza do OSM (os notebooks rodam de dentro da pasta notebooks/)
cd notebooks
../.venv/bin/jupyter execute --inplace limpeza_overpass.ipynb

# 3. Integração das bases por bairro
../.venv/bin/jupyter execute --inplace integracao_bairros.ipynb
cd ..

# 4. Série do nível do Guaíba (ANA)
.venv/bin/python scripts/serie_nivel_guaiba.py
```

Os notebooks também podem ser abertos no VS Code ou no Jupyter. Escolha o `.venv` como kernel e use "Run All".

**Conferências esperadas:**
- a limpeza do OSM deixa **581** registros: 433 escolas e 148 unidades de saúde;
- a série do nível marca **5,09 m às 12h de 04/05/2024** e tem máximo de **5,35 m**. O script falha se esses valores não baterem.

### 5. Publicar no Streamlit Community Cloud

Em <https://share.streamlit.io>, crie um app apontando para este repositório e branch, com **Main file path** `app/app.py`. As dependências são lidas do `requirements.txt` na raiz, e o tema, de `.streamlit/config.toml`.

---

## O dashboard

O nível escolhido no slider (de 3,0 a 10,0 m, em passos de 0,1) vale para as três telas.

| Tela | O que mostra | Dados |
|---|---|---|
| **1. Simulação do INCT** | Aviso de limitações; pessoas, prédios e bairros atingidos; mapa por bairro; ranking dos bairros; curva da população afetada com 5,35 m (maio de 2024) marcado; % de prédios atingidos por bairro | Só o JSON do INCT, limpo |
| **2. Equipamentos e bases externas** | Filtro por categoria; escolas e unidades de saúde em bairros atingidos por nível; mapa dos pontos; linha do tempo das ETAs em 2024 e situação de cada uma no nível escolhido; tabela de fontes com link e data de coleta | OSM, ETAs, Censo 2022, malha de bairros |
| **3. Abastecimento de água** | ETAs que estariam paradas no nível escolhido, conforme o que aconteceu em 2024, e bairros sem abastecimento ou com abastecimento parcial | ETAs, nível do Guaíba (ANA), Censo 2022 |

---

## Estrutura do repositório

```
app/                    dashboard (Streamlit)
  app.py                ponto de entrada: navegação entre as telas
  tela1_simulacao.py    Tela 1
  tela2_bases.py        Tela 2
  tela3_abastecimento.py Tela 3
  etas_limiar.py        lógica da Tela 3 (em que nível cada ETA parou)
  dados.py              leitura dos arquivos (com cache)
  comum.py              cores, formatação pt-BR, slider e mapa compartilhados
scripts/
  coleta_overpass.py    coleta do OpenStreetMap pela Overpass API
  serie_nivel_guaiba.py série do nível do Guaíba a partir dos arquivos da ANA
notebooks/
  limpeza_overpass.ipynb   limpeza do OSM, passo a passo, com log de decisões
  integracao_bairros.ipynb integração das bases pela chave de bairro
dados/
  originais/            dados como foram obtidos (respostas da Overpass, JSON das ETAs, arquivos da ANA)
  externos/             bases de outros membros da equipe (origem em dados/externos/README.md)
  processados/          resultados das etapas de limpeza e integração
relatorios/             relatório de andamento (PDF) e documentação da integração
.streamlit/config.toml  tema do dashboard
```

---

## Bases de dados

| Base | Fonte | Como foi obtida | Coleta |
|---|---|---|---|
| Simulação de enchente por bairro | INCT SiMAI, arquivo `data.json` fornecido à disciplina | Limpeza pela equipe (Gabriel) | 10/11/2026 |
| Escolas e unidades de saúde | [OpenStreetMap](https://www.openstreetmap.org/copyright) via [Overpass API](https://overpass-api.de/api/interpreter), licença ODbL | Por código (`scripts/coleta_overpass.py`) | 08/11/2026 |
| Estações de tratamento de água (ETAs) em maio de 2024 | 15 notas do Dmae e da Prefeitura de Porto Alegre e reportagens (lista em `dados/originais/etas_poa_enchente_2024_fontes.md`) | Compilação manual, com cada campo ligado à sua fonte e revisão automática (402 checagens) | 13/11/2026 |
| Nível do Guaíba, maio de 2024 | ANA: estação 87444000 (Usina do Gasômetro) pelo [HidroWeb](https://www.snirh.gov.br/hidroweb/serieshistoricas); estação 87450004 (Cais Mauá C6) pelo [Hidro-Telemetria](https://www.snirh.gov.br/hidrotelemetria/) | Download manual do arquivo oficial. As leituras do Cais Mauá foram copiadas da tabela do site, porque o download dessa estação veio vazio (detalhes em `dados/originais/nivel_guaiba_fontes.md`) | 17/11/2026 |
| População por bairro | IBGE, [Censo 2022, agregados por bairro](https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/Agregados_por_Bairro_csv/) | Luiza | 09/11/2026 |
| Limites dos bairros | Prefeitura de Porto Alegre, [malha oficial de bairros (2016)](https://gis-smamus.portoalegre.rs.gov.br/server/rest/services/01_PUBLICACOES/bairros_2016/MapServer/0) | Luiza | 09/11/2026 |

As bases são ligadas por uma **chave de bairro**: o nome sem acento, em maiúsculas e só com letras. A equivalência entre os nomes de cada fonte está em `dados/externos/de_para_bairros.csv`, que cobre os 94 bairros oficiais.

---

## Limitações

- **Simulação do INCT.** Os resultados dependem dos prédios mapeados no OpenStreetMap, e a população atingida é estimada.
- **ETAs (Tela 3).**
  - As fontes informam só o dia e o período de cada parada, e não a hora. Por isso, o nível em que cada ETA parou é uma **faixa estimada**.
  - Entre 02/05 às 23h15 e 03/05 às 15h não há leituras do nível. Por isso, a estimativa de Moinhos de Vento tem **confiança baixa**.
  - Acima de 5,35 m (o recorde de 2024) não há observação.
- **OSM.** A cobertura é colaborativa e pode estar incompleta.
- **Bairros.** 19 nomes das listas do Dmae são vilas ou loteamentos que não correspondem a bairros oficiais.

Os detalhes do método estão no relatório `relatorios/relatorio_andamento_luiggi.pdf` e nos expanders "Sobre os dados" e "Como a estimativa é feita" do dashboard.

---

## Equipe

| Pessoa | Responsabilidade |
|---|---|
| Gabriel | Malha de bairros, POAGEODATA e limpeza do JSON do INCT |
| João | Cotas da ANA e Open-Meteo |
| Lucas | Mancha da UFRGS de 2024 e Atlas de Risco |
| Luiggi | OpenStreetMap (Overpass), nível do Guaíba, ETAs, integração e dashboard |
| Luiza | Censo 2022, CNEFE e S2iD |

## Uso de IA

O assistente **Claude Code** (Anthropic) foi usado para escrever e revisar código (coleta, notebooks e dashboard), buscar e conferir fontes, e redigir documentação. Todos os números foram gerados ou conferidos por scripts sobre os dados. As decisões de análise foram da equipe, por exemplo: o critério de duplicatas do OSM, o uso do horário médio do turno para as ETAs e a criação da Tela 3.
