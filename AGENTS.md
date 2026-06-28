# Foot Game Theory

Objetivo: produzir uma analise Moneyball do confronto Brasil x Japao usando os dados locais de `data/16avos`, com foco em recomendacoes praticas para o Brasil.

## Regras Do Projeto

- Tratar `data/16avos/*.zip` como fonte bruta imutavel.
- Material derivado vai para `build/`, `analysis/` ou `docs/`.
- O banco principal e `build/footgametheory.sqlite`.
- O laudo final fica em `docs/brasil-japao-moneyball.html`.
- Evitar arquivos de codigo com mais de 1000 linhas; se passar disso, dividir.
- Nao misturar este repo com o git pai em `/Users/leonardodias/arvor`.

## Pipeline

1. Extrair os ZIPs para `build/extracted`.
2. Normalizar CSVs em SQLite.
3. Calcular metricas por jogador, time e jogo.
4. Extrair sinais dos heatmaps.
5. Gerar HTML com diagnostico, rankings, taticas e recomendacao de escalacao.

## Tom Analitico

Ser direto: apontar quem entrega, quem compromete, onde o Japao machuca e onde o Brasil deve bater.
