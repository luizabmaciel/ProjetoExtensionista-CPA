# Enchentes em Porto Alegre: análise dos dados do INCT SiMAI

Projeto Extensionista da disciplina Coleta, Preparação e Análise de Dados, curso de Ciência de Dados da PUCRS.

O ponto de partida é a simulação do INCT SiMAI, que estima os prédios e as pessoas atingidos em cada bairro de Porto Alegre para níveis do Guaíba de 3,0 a 10,0 m, em passos de 0,1 m. A essa simulação a equipe somou bases externas:

- equipamentos públicos (escolas e unidades de saúde);
- população e domicílios (Censo 2022 e CNEFE);
- abastecimento de água (as estações de tratamento do Dmae);
- manchas de inundação observadas e simuladas (IPH/UFRGS);
- vulnerabilidade a inundações por trecho de rio (ANA/SGB);
- o nível do Guaíba em maio de 2024.

O resultado é um dashboard em Streamlit com cinco telas.

> Aviso: os números são estimativas de uma simulação e do que aconteceu em maio de 2024. Não são previsões nem contagens oficiais.

## Como rodar

### Pré-requisitos

- Python 3.13 (testado com 3.13.12)
- `git`

### Instalar

Na raiz do repositório:

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

No Windows, troque `.venv/bin/` por `.venv\Scripts\`.

> No Debian ou Ubuntu, o `python3` do sistema pode criar o `.venv` sem o `pip`. Se isso acontecer, use o Python do miniconda ou do Anaconda (`~/miniconda3/bin/python -m venv .venv`) ou instale o pacote `python3-venv`.

O `requirements.txt` inclui o que os notebooks precisam. Para só abrir o dashboard, este conjunto menor basta e ocupa cerca de metade do espaço:

```bash
.venv/bin/pip install streamlit plotly pandas geopandas pyogrio shapely pyproj numpy matplotlib
```

### Abrir o dashboard

```bash
.venv/bin/streamlit run app/app.py
```

O navegador abre em <http://localhost:8501>. Para parar, use `Ctrl+C` no terminal.

O comando precisa ser executado na raiz do repositório, não dentro de `app/`. Os arquivos de dados já estão versionados, então o dashboard funciona sem refazer a coleta.

### Refazer o processamento (opcional)

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

Conferências esperadas:

- a limpeza do OSM deixa 581 registros: 433 escolas e 148 unidades de saúde;
- a série do nível marca 5,09 m às 12h de 04/05/2024 e tem máximo de 5,35 m na régua do Gasômetro. O script falha se esses valores não baterem.

As outras frentes têm scripts e notebooks próprios, em `scripts/coleta/` e nas subpastas de `notebooks/`. Cada um documenta a sua própria ordem de execução.

### Publicar no Streamlit Community Cloud

Em <https://share.streamlit.io>, crie um app apontando para este repositório e branch, com Main file path `app/app.py`. As dependências vêm do `requirements.txt` na raiz, e o tema, de `.streamlit/config.toml`.

## O dashboard

O nível escolhido no slider (de 3,0 a 10,0 m, em passos de 0,1) vale para as telas que o usam.

| Tela | O que mostra | Dados |
|---|---|---|
| 1. Simulação do INCT | Aviso de limitações; pessoas, prédios e bairros atingidos; mapa por bairro; ranking dos bairros; curva da população afetada com o pico de 2024 marcado; % de prédios atingidos por bairro | Só o JSON do INCT, limpo |
| 2. Equipamentos e abastecimento | Filtro por categoria; escolas e unidades de saúde em bairros atingidos por nível; mapa dos pontos; linha do tempo das ETAs em 2024 e situação de cada uma no nível escolhido; tabela de fontes com link e data de coleta | OSM, ETAs, Censo 2022, malha de bairros |
| 3. Abastecimento de água | ETAs que estariam paradas no nível escolhido, conforme o que aconteceu em 2024, e bairros sem abastecimento ou com abastecimento parcial | ETAs, nível do Guaíba (ANA), Censo 2022 |
| 4. Educação | Mapa das escolas por faixa de exposição; ranking de bairros; escolas por 10 mil habitantes; curva de exposição por nível; recorte de maio de 2024; exportação em CSV | OSM, INCT, Censo 2022, malha de bairros |
| 5. Vulnerabilidade por bairro | Em que cota cada bairro começa a alagar; os bairros com cota censurada; ritmo em que a cidade cede; o que a cota não diz; o que o modelo não enxerga; teste de consistência física da simulação | INCT, Censo 2022, malha de bairros |

A tela 5 separa os 94 bairros em três grupos: 40 não alagam em nenhum dos 71 níveis simulados, 30 têm cota de início medida e 24 já aparecem alagados no primeiro nível da simulação, o que deixa a cota deles desconhecida.

## Estrutura do repositório

```
app/                      dashboard (Streamlit)
  app.py                  ponto de entrada: navegação entre as telas
  tela1_simulacao.py      Tela 1
  tela2_bases.py          Tela 2
  tela3_abastecimento.py  Tela 3
  tela4_educacao.py       Tela 4
  tela5_vulnerabilidade.py  Tela 5
  etas_limiar.py          lógica da Tela 3 (em que nível cada ETA parou)
  dados.py                leitura dos arquivos (com cache)
  comum.py                cores, formatação pt-BR, slider e mapa compartilhados
scripts/
  coleta_overpass.py      coleta do OpenStreetMap pela Overpass API
  coleta_bairros.py       malha oficial de bairros e POAGEODATA
  serie_nivel_guaiba.py   série do nível do Guaíba a partir dos arquivos da ANA
  limpeza_data_json.py    limpeza do JSON do INCT
  limpeza_censo_cnefe.py  Censo 2022 e CNEFE por bairro
  limpeza_s2id.py         registros de desastres do S2iD
  coleta/                 scripts de download do Atlas de Risco e do banco de cheias
notebooks/
  limpeza_overpass.ipynb     limpeza do OSM, passo a passo, com log de decisões
  integracao_bairros.ipynb   integração das bases pela chave de bairro
  analise_exploratoria.ipynb exploração das bases do Censo, CNEFE e S2iD
  exploracao_bairros.ipynb   exploração da malha de bairros e do POAGEODATA
  dados_openmeteo.ipynb      série meteorológica do Open-Meteo
  eda_projeto_extensionista_enchentes_rs_v2_tratado.ipynb  tratamento da base ANA/SGB
  atlas/                     tabelas municipais do Atlas de Risco 2025
  cheias_guaiba/             manchas de inundação do banco do IPH
dados/
  originais/   dados como foram obtidos (respostas da Overpass, JSON das ETAs, arquivos da ANA)
  brutos/      downloads do IBGE e do S2iD
  externos/    bases de outros membros da equipe (origem em dados/externos/README.md)
  referencia/  malha de bairros, JSON do INCT e de-para de nomes
  extraidos/   tabelas extraídas do Atlas de Risco
  tratados/    saídas das etapas de tratamento
  processados/ resultados das etapas de limpeza e integração
relatorios/    relatórios de andamento (PDF) e documentação das bases
.streamlit/config.toml   tema do dashboard
```

## Bases de dados

| Base | Fonte | Quem preparou | Coleta |
|---|---|---|---|
| Simulação de enchente por bairro | INCT SiMAI, arquivo `data.json` fornecido à disciplina | Gabriel | 10/11/2026 |
| Limites dos bairros | Prefeitura de Porto Alegre, [malha oficial de bairros (2016)](https://gis-smamus.portoalegre.rs.gov.br/server/rest/services/01_PUBLICACOES/bairros_2016/MapServer/0) | Gabriel e Luiza | 09/11/2026 |
| POAGEODATA (dados por bairro, Censo 2022 e mortalidade) | Zenodo, DOI [10.5281/zenodo.14807279](https://doi.org/10.5281/zenodo.14807279) | Gabriel | 09/11/2026 |
| Escolas e unidades de saúde | [OpenStreetMap](https://www.openstreetmap.org/copyright) via [Overpass API](https://overpass-api.de/api/interpreter), licença ODbL | Luiggi | 08/11/2026 |
| Estações de tratamento de água (ETAs) em maio de 2024 | 15 notas do Dmae e da Prefeitura de Porto Alegre e reportagens (lista em `dados/originais/etas_poa_enchente_2024_fontes.md`) | Luiggi | 13/11/2026 |
| Nível do Guaíba, maio de 2024 | ANA: estação 87444000 (Usina do Gasômetro) pelo [HidroWeb](https://www.snirh.gov.br/hidroweb/serieshistoricas); estação 87450004 (Cais Mauá C6) pelo [Hidro-Telemetria](https://www.snirh.gov.br/hidrotelemetria/) | Luiggi | 17/11/2026 |
| População e domicílios por bairro | IBGE, [Censo 2022, agregados por bairro](https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/Agregados_por_Bairro_csv/) e CNEFE | Luiza | 09/11/2026 |
| Registros de desastres | S2iD, Ministério da Integração e do Desenvolvimento Regional | Luiza | ver `notebooks/analise_exploratoria.ipynb` |
| Manchas de inundação do Guaíba em 2024 | Banco de dados das cheias na Região Hidrográfica do Lago Guaíba, IPH/UFRGS, [Zenodo](https://zenodo.org/records/11359951) | Lucas | ver `notebooks/cheias_guaiba/` |
| Atlas de Risco de Inundações 2025 | Tabelas municipais das páginas 43 a 45 do Atlas | Lucas | ver `notebooks/atlas/` |
| Vulnerabilidade a inundações por trecho de rio | ANA/SGB, shapefile nacional filtrado para o RS (1.377 trechos em 297 municípios) | João | ver `notebooks/eda_projeto_extensionista_enchentes_rs_v2_tratado.ipynb` |
| Séries meteorológicas | [Open-Meteo](https://open-meteo.com/) | João | ver `notebooks/dados_openmeteo.ipynb` |

As bases são ligadas por uma chave de bairro: o nome sem acento, em maiúsculas e só com letras. A equivalência entre os nomes de cada fonte está em `dados/externos/de_para_bairros.csv`, que cobre os 94 bairros oficiais.

## A referência de nível do Guaíba

Os níveis que aparecem no dashboard dependem de qual régua os mediu, e em maio de 2024 foram duas.

A régua histórica de Porto Alegre é a do Cais Mauá (estação 87450004), operada pelo DRHS/SEMA-RS. É nela que estão a cota de inundação de 3,00 m, o recorde de 1941 (4,76 m) e a série histórica da cidade. Ela foi danificada pela cheia e parou de transmitir em 02/05/2024.

O pico foi medido numa régua emergencial instalada pelo SGB na Usina do Gasômetro em 03/05, cuja série está preservada na estação 87444000. As duas réguas não estão no mesmo nível: o governo do RS confirmou o desnível e definiu cotas próprias para o Gasômetro, de 3,60 m para inundação e 3,15 m para alerta. A [nota institucional conjunta da ANA e do SGB](https://www.gov.br/ana/pt-br/assuntos/noticias-e-eventos/noticias/ana-e-servico-geologico-do-brasil-fazem-readequacoes-em-estacao-de-monitoramento-do-rio-guaiba-em-porto-alegre-rs) registra que o zero da régua emergencial equivale a 1,18 m abaixo do nível médio do mar.

O SGB depois reconstruiu o pico na referência do Cais Mauá: 5,37 m, 0,61 m acima do recorde de 1941. Como a simulação do INCT e as manchas do IPH usam essa régua, é esse o valor que o dashboard marca como pico de 2024. A série horária compilada pela equipe continua em uso para a cronologia das paradas das ETAs, onde o valor de 5,35 m é o da régua do Gasômetro.

## Limitações

Simulação do INCT. Os resultados dependem dos prédios mapeados no OpenStreetMap, e a população atingida é estimada. O modelo compara cota de terreno com nível d'água e não representa diques, muros, comportas nem casas de bomba. Por isso o Centro Histórico aparece com cerca de 10% dos prédios atingidos a 5,4 m, enquanto Farrapos, Humaitá e Navegantes aparecem com 100%. Em 2024 foi a falha do sistema de proteção que inundou o Centro, e o modelo não enxerga nem a proteção nem a falha dela.

Piso e teto da simulação. A série começa em 3,0 m e termina em 10,0 m. Para os 24 bairros já atingidos no primeiro nível, a cota de início de alagamento não é uma medida: é o piso da base. Esses bairros somam 279.476 pessoas, 21% da cidade.

Consistência física. A água não recua: se o nível sobe, o percentual de prédios atingidos não pode cair. Em 6.580 passos da simulação, 9 violam essa regra, nos bairros Arquipélago e Espírito Santo. São os mesmos que a coluna `qualidade` já sinalizava na preparação. As linhas continuam na base, marcadas, em vez de removidas.

ETAs (telas 2 e 3). As fontes informam só o dia e o período de cada parada, e não a hora, então o nível em que cada ETA parou é uma faixa estimada. Entre 02/05 às 23h15 e 03/05 às 15h não há leituras, e a estimativa de Moinhos de Vento tem confiança baixa. Os limiares vêm da régua do Gasômetro, enquanto o nível selecionado no slider é o da simulação, referenciado ao Cais Mauá, e a equivalência entre as duas não está estabelecida. Acima de 5,35 m na régua do Gasômetro não há observação.

Modo de falha das ETAs. Em maio de 2024, nenhuma das cinco ETAs que pararam parou porque o prédio alagou. As causas foram estação de bombeamento de água bruta inundada, painel elétrico molhado, risco de choque, corte de energia e estrutura de captação arrastada. Estimar o nível da água não responde sozinho quando uma ETA para.

OSM. A cobertura é colaborativa e pode estar incompleta.

Bairros. 19 nomes das listas do Dmae são vilas ou loteamentos que não correspondem a bairros oficiais.

Os detalhes do método estão nos relatórios em `relatorios/` e nos expanders de fontes e limitações de cada tela.

## Equipe

| Pessoa | Responsabilidade |
|---|---|
| Gabriel | Malha de bairros, POAGEODATA, limpeza do JSON do INCT e Tela 5 |
| João | Base ANA/SGB de vulnerabilidade a inundações e Open-Meteo |
| Lucas | Banco de cheias do IPH/UFRGS e Atlas de Risco 2025 |
| Luiggi | OpenStreetMap, nível do Guaíba, ETAs, integração das bases e dashboard |
| Luiza | Censo 2022, CNEFE, S2iD e Tela 4 |

## Uso de IA

A IA foi utilizada para escrever e revisar código (coleta, notebooks e dashboard), conferir fontes, e apoiar o time na documentação. Todos os números foram gerados ou conferidos por scripts sobre os dados. Todas as decisões de análise foram da equipe.