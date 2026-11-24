# Integração das bases da equipe

Como as bases que cada pessoa coletou se ligam entre si e com a simulação do INCT (Tela 1).
O código está em `notebooks/integracao_bairros.ipynb`, com uma célula por passo.

## A ideia: três eixos de ligação

Toda base da equipe se conecta à simulação do INCT por pelo menos um destes eixos:

| Eixo | Coluna de ligação | Bases |
|---|---|---|
| **Bairro** | `chave` (nome sem acento e sem espaço, ex.: `ABERTADOSMORROS`) | INCT, malha de bairros (Gabriel); Censo, CNEFE (Luiza); OSM, ETAs (Luiggi); mancha de 2024 (Lucas, a integrar) |
| **Nível / tempo** | `nivel_m` e data/hora | INCT; nível horário do Guaíba (Luiggi); chuva e cotas (João); paradas das ETAs (Luiggi); S2iD (Luiza) |
| **Município** | `cod_ibge` | S2iD (Luiza); Atlas de risco (Lucas) |

**Até agora está implementado o eixo bairro.** Os outros dois dependem de bases que ainda estão sendo processadas.

## Como rodar

Abrir `notebooks/integracao_bairros.ipynb` e executar todas as células. As bases dos colegas estão copiadas em
`dados/externos/`; o `README.md` dessa pasta diz de qual branch e commit veio cada arquivo.

## Passos do notebook

1. **Ler as bases:** de-para de bairros, INCT limpo (Gabriel), Censo e CNEFE (Luiza), pontos do OSM e ETAs (Luiggi)
   e a malha de bairros da Prefeitura.
2. **Bairro de cada ponto do OSM:** junção espacial (`geopandas.sjoin`). Os 128 polígonos da malha são agrupados
   em 94 bairros (o Arquipélago tem 34 ilhas) e os pontos são convertidos do sistema do GPS (WGS 84) para o da malha
   (SIRGAS 2000). Os 585 pontos encontraram um bairro.
3. **Contagem por bairro:** escolas e unidades de saúde.
4. **ETAs → bairro:** cada nome das listas do Dmae vira uma `chave` e é comparado com os 94 bairros oficiais.
   - 92 nomes casam exatamente.
   - 8 foram ligados por um de-para manual decidido pela equipe e marcado **a confirmar com o Dmae** (ex.: "Centro"
     → Centro Histórico, "Vila Farrapos" → Farrapos). Três têm confiança baixa: Alto Teresópolis, São Pedro e
     Vila Floresta.
   - 19 entradas (18 nomes) são vilas e loteamentos e ficam sem bairro (ex.: Vila Safira, Praça Moema).
5. **Tabela por bairro:** `merge` pela `chave`, com `validate="1:1"` para impedir bairros repetidos.
6. **Equipamentos por nível:** combina a contagem de cada bairro com a % de prédios afetados do INCT em cada nível.
7. **Conferências e gravação.**

## Saídas (`dados/processados/integracao/`)

| Arquivo | Conteúdo |
|---|---|
| `bairros_integrado.csv` | 94 bairros × 12 colunas: população e domicílios, % residencial, prédios, nível do primeiro alagamento e % de população afetada a 5 m, escolas, unidades de saúde, ETAs |
| `equipamentos_por_nivel.csv` | de 3,0 a 10,0 m: equipamentos em bairros atingidos e estimativa proporcional |
| `eta_bairro.csv` | os 119 pares ETA × nome de bairro do Dmae, com o método da correspondência |

## Conferências feitas

- Os pontos contados por bairro somam os 581 da base limpa (433 escolas e 148 unidades de saúde).
- A população dos 94 bairros soma 1.332.845, o total do Censo 2022, e é igual à usada pelo INCT.
- Nenhum bairro aparece repetido em nenhuma junção.

## Cuidados na leitura

- **Equipamentos por nível:** `em_bairros_atingidos` é um teto (um bairro com 1% de prédios afetados conta todas
  as suas escolas); `estimativa_proporcional` supõe que os equipamentos se distribuem como os prédios. Nenhuma das
  duas diz que uma escola específica alagou.
- **`eta_parou_por_agua_2024`:** `sim` se alguma ETA que abastece o bairro parou por água; `não confirmado` para a
  São João, cujas fontes divergem; `não`; ou `sem ETA na lista`. 16 bairros são atendidos por duas ETAs, então `sim`
  não quer dizer que o bairro inteiro ficou sem água.
- **10 bairros não aparecem em nenhuma lista do Dmae:** Bom Jesus, Glória, Lami, Pitinga, Ponta Grossa, Santa Maria
  Goretti, Santa Rosa de Lima, São Caetano, Sétimo Céu e Vila Jardim. Isso não significa que não tenham abastecimento.
- **OpenStreetMap não é cadastro oficial.**
- **Os números do INCT são estimativas de uma simulação,** não previsões nem contagens oficiais.

## Pendências

1. Confirmar com o Dmae as 8 correspondências manuais e as vilas sem bairro.
2. Incluir o % de área alagada por bairro na mancha de maio de 2024 (Lucas), para comparar com a simulação a 5,3 m.
3. Eixo nível/tempo: depende da série horária do nível do Guaíba e das cotas da ANA (João). Antes, confirmar que as
   fontes de nível usam a mesma régua (Cais Mauá) e o mesmo zero.
4. Eixo município: S2iD (Luiza) com o Atlas de risco (Lucas), pela coluna `cod_ibge`.

## Uso de IA

O notebook e este documento foram feitos com auxílio do Claude Code, conforme exigido no enunciado.
As correspondências manuais das ETAs foram decididas pela equipe.
