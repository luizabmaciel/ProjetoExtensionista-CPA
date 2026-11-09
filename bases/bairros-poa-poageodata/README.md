# Bases 3 e 4 — Malha dos bairros de Porto Alegre e POAGEODATA


| # | Base | Fonte | Formato |
|---|---|---|---|
| 3 | Malha oficial dos bairros de Porto Alegre (divisão de 2016) | Prefeitura de POA — serviço ArcGIS REST | GeoJSON, EPSG:4674 |
| 4 | POAGEODATA — dados por bairro (Censo 2022 e mortalidade 2022) | Zenodo, DOI [10.5281/zenodo.14807279](https://doi.org/10.5281/zenodo.14807279) | 4 GeoPackages, EPSG:31982 |

Entrou depois o `data.json` do próprio INCT — a simulação de alagamento por
nível de água, de 3,0 m a 10,0 m de 10 em 10 cm, com prédios e população
atingidos em cada um dos 94 bairros. Ele não é uma das dez bases da divisão,
mas é o arquivo que a tela do mapa vai consumir, então vale tratá-lo aqui:
94 × 71 = 6.674 linhas, e o cruzamento com as duas bases de cima é o que dá
sentido a ele.

A pergunta que guia a exploração: **essas duas bases conversam?** A malha da
Prefeitura tem o desenho dos bairros; o POAGEODATA tem a demografia. Só servem
juntas se der para casar bairro com bairro 

```

**Linux ou macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Depois, em qualquer sistema:

```bash
python scripts/verificar_ambiente.py   # confere se o geopandas reprojeta e lê GPKG
python scripts/coleta_bairros.py       # baixa as duas bases para dados/originais/
python scripts/limpeza_data_json.py    # desaninha e limpa o data.json do INCT
python scripts/teste_juncao.py         # roda os 31 testes da lógica
jupyter notebook                        # abre o navegador em localhost:8888
```

---

## O que tem em cada arquivo

```
scripts/
  coleta_bairros.py       coleta das duas bases, com cache em disco e manifesto
  verificar_ambiente.py   checagem de que o ambiente geoespacial está de pé
  limpeza_data_json.py    desaninha e limpa a simulação de alagamento do INCT
  teste_juncao.py         testes da normalização, da junção e da limpeza
notebooks/
  exploracao_bairros.ipynb  a exploração em si
dados/
  originais/              dado bruto (fora do git) + manifesto da coleta
  processados/            de_para_bairros.csv     — correspondência entre as bases
                          inct_niveis_bairro.csv  — a simulação em formato tabela
                          inct_qualidade.csv       — um resumo por bairro
```

---

## O que a exploração encontrou

Os números completos estão nas saídas do notebook. Os três achados que mudam
como o grupo deve usar essas bases:

**Uma feição não é um bairro.** O serviço da Prefeitura devolve **128
polígonos** para **94 bairros**. A diferença é física: o Arquipélago são 34
ilhas, cada uma um polígono.

**O nome é a única chave, e ele diverge entre as bases.** Não há código de
bairro comum às duas. Então a junção é por texto, e texto quebra: acento,
caixa, espaço duplo, `Passo d'Areia` com apóstrofo tipográfico. A normalização
que usei está testada no `teste_juncao.py`.

**Área só faz sentido depois de reprojetar.** A malha da Prefeitura vem em
EPSG:4674, que é um sistema de coordenadas geográficas: `area` ali sai em graus
quadrados, um número que não significa nada. Reprojetado para EPSG:31982
(SIRGAS 2000 / UTM 22S), o total dá **471,9 km²**, contra 495,4 km² do IBGE. A
diferença são as áreas de água que a malha municipal não inclui — vale saber
antes de usar essa área como denominador de densidade.

---

### E sobre o `data.json` do INCT

**Os nomes casam, e isso diz de onde eles vieram.** 93 dos 94 nomes do
`data.json` são idênticos *caractere por caractere* ao `nome_ibge` do
POAGEODATA — a nomenclatura é a do IBGE, não a da Prefeitura. Contra a malha
municipal são **zero** nomes idênticos, porque lá é tudo maiúscula. Com a
normalização, 92 fecham; os dois que sobram não são diferença de grafia e sim
de palavra (`Coronel` abreviado como `Cel.`, e `Passo D'Areia` contra `Passo da
Areia`), e vão num dicionário de apelidos. Com ele, **as três bases fecham em
94/94**.

**`affected_population` não é contagem de pessoas.** Todas as 6.674 linhas, sem
uma exceção, são `percentage / 100 * population`. E o `percentage` vem
arredondado para cima. Duas consequências: o campo nunca subestima, inflando o
total da cidade em 4,8% no cenário de 3,0 m — justo o mais provável — e ele só
se move em degraus de 1% da população do bairro. Santa Tereza tem 50 valores
distintos de prédios atingidos ao longo dos 71 níveis e **três** de população
atingida. Quem usar esse campo como número de pessoas vai desenhar uma escada
achando que é uma curva. A limpeza estima pela razão de prédios, que tem a
granularidade real, e guarda o original ao lado.

**Quatro células são buraco, não zero.** Centro Histórico em 9,7 e 9,8 m,
Lageado em 8,1 m, Rubem Berta em 8,8 m: a série sobe, zera num nível e volta ao
normal no seguinte. Água subindo não desafeta ninguém, então é dado que faltou.
Interpolado linearmente entre os vizinhos — a 10 cm de distância a curva é
praticamente reta — e marcado na coluna `qualidade`.

**Espírito Santo é outro problema, e não mexi nele.** Um platô de 637 prédios
nos cinco primeiros níveis, queda para 25, subida lenta até 133 em 10,0 m, e um
pico isolado de 2.101 em 4,7 m. Não é buraco nem ruído, e não dá para adivinhar
o número certo. Fica o valor original com bandeira de suspeito e uma pergunta
para o INCT. Dos 94 bairros, é o único com esse padrão.

**O Arquipélago oscila, e isso é normal.** Entre 4.674 e 4.688 prédios ao longo
dos níveis — 14 prédios de amplitude num bairro que já está 99,7% alagado em
3,0 m. É imprecisão de contagem na borda do polígono. Marcado como
`ruido_borda` e mantido.

---

## Decisões de método

**Coleta separada da análise.** Uma coleta, muitas execuções da análise. O
script grava em `dados/originais/`

O `teste_juncao.py` extrai as
funções do próprio notebook e roda 19 asserções contra casos construídos de
propósito: nome com acento, nome com apóstrofo, espaço duplo, bairro que existe
em uma base e não na outra, e a soma das proporções demográficas, que tem que
fechar em 1 (se uma coluna de contagem entrar na soma por engano, o total
estoura e o teste pega).

---
