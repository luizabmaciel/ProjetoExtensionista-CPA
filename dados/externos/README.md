# Bases de outras pessoas da equipe

Cópias, sem nenhuma alteração, dos arquivos processados que outras pessoas publicaram nas suas branches.
São usadas pelo notebook `notebooks/integracao_bairros.ipynb`. Quando as bases forem unificadas no `main`,
estes arquivos podem ser apagados e o notebook passa a ler do caminho oficial.

Copiados em 17/11/2026 com `git show <branch>:<caminho>`.

| Arquivo | Responsável | Branch | Caminho na branch | Commit |
|---|---|---|---|---|
| `de_para_bairros.csv` | Gabriel | `Franco/bases-v2` | `dados/processados/de_para_bairros.csv` | `52fb67ef` (10/11/2026) |
| `inct_niveis_bairro.csv` | Gabriel | `Franco/bases-v2` | `dados/processados/inct_niveis_bairro.csv` | `52fb67ef` (10/11/2026) |
| `inct_qualidade.csv` | Gabriel | `Franco/bases-v2` | `dados/processados/inct_qualidade.csv` | `52fb67ef` (10/11/2026) |
| `censo_bairros_poa.csv` | Luiza | `Luiza/bases` | `dados/processados/censo_bairros_poa.csv` | `e66e4516` (09/11/2026) |
| `cnefe_resumo_bairro.csv` | Luiza | `Luiza/bases` | `dados/processados/cnefe_resumo_bairro.csv` | `e66e4516` (09/11/2026) |
| `bairros_poa_2016.geojson` | Luiza (malha oficial da Prefeitura) | `Luiza/bases` | `dados/referencia/bairros_poa_2016.geojson` | `795aa5eb` (09/11/2026) |

Para atualizar um arquivo depois que o colega mudar a base:

```bash
git fetch origin
git show origin/Luiza/bases:dados/processados/censo_bairros_poa.csv > dados/externos/censo_bairros_poa.csv
```

e atualizar a data e o commit nesta tabela (`git log -1 --format=%h origin/Luiza/bases`).
