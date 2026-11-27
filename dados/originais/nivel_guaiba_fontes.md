# Nível do Guaíba em maio de 2024 (ANA)

Dois arquivos alimentam a série usada na Tela 3 (`scripts/serie_nivel_guaiba.py` junta os dois e gera
`dados/processados/nivel_guaiba_horario.csv`).

## 1. `hidroweb_telemetrica_87444000.csv` — Usina do Gasômetro (arquivo oficial)

- **Fonte:** ANA, HidroWeb, Séries Históricas, aba "Dados Telemétricos" —
  <https://www.snirh.gov.br/hidroweb/serieshistoricas>
- **Estação:** 87444000 – USINA DO GASOMETRO (CHEIA 2024), criada durante a enchente (responsável SEMA-RS).
- **Download:** 17/11/2026, período 01/05/2024 a 10/05/2024, formato CSV. Arquivo mantido como veio
  (separador `;`, codificação latin-1, nível em cm, registros a cada 15 minutos).
- **Conteúdo:** de 03/05 00:00 a 10/05 00:00; o nível começa às 15:00 de 03/05 (458 cm).
  Pico: 535 cm às 05:30 de 05/05.
- **Conferências:** 509 cm às 12:00 de 04/05 = 5,09 m da nota da Prefeitura (fonte F13 das ETAs);
  pico = recorde de 5,35 m. As 38 leituras desta estação copiadas antes à mão do Hidro-Telemetria
  conferem uma a uma com o arquivo.

## 2. `ana_telemetria_leituras_transcritas.csv` — Cais Mauá C6 (copiado à mão)

- **Fonte:** ANA, Hidro-Telemetria, consulta "Gráfico / Tabela" — <https://www.snirh.gov.br/hidrotelemetria/>
- **Estação:** 87450004 – CAIS MAUÁ C6 (a estação citada na página de nível da Defesa Civil do RS).
- **Consulta:** 17/11/2026. O download desta estação no HidroWeb (telemétrico e convencional) veio
  **vazio**, por isso as leituras foram copiadas da tabela exibida pelo Hidro-Telemetria.
- **Conteúdo:** só as leituras necessárias, de 01/05 00:00 a 02/05 23:15. A estação não tem dados
  depois disso (parou de transmitir na enchente).
- O arquivo também traz as leituras do Gasômetro copiadas à mão; elas ficam só como registro,
  o script usa o arquivo oficial para essa estação.

## Horário

Como exibido pela ANA (horário de Brasília, UTC−3). A leitura das 12:00 de 04/05 confere com a nota
da Prefeitura, publicada no horário local.

## Limitações

- **Lacuna entre 02/05 23:15 e 03/05 15:00:** o Cais Mauá parou de transmitir e o Gasômetro só começou
  às 15:00 de 03/05. O nível nesse intervalo é interpolado entre duas estações e tem **baixa
  confiança**. A parada do sistema Moinhos de Vento (madrugada de 03/05) cai nessa lacuna.
- As duas estações ficam no mesmo trecho da orla do Centro, mas não há garantia de que as réguas
  estejam no mesmo zero.
- Entre 01/05 00:15 e 02/05 00:00 há só os pontos das pontas.
