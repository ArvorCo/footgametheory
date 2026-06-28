# Foot Game Theory

Analise Moneyball do confronto Brasil x Japao a partir dos CSVs e heatmaps locais em `data/16avos`.

## Rodar

```bash
python3 scripts/build_report.py
```

Saidas principais:

- `build/footgametheory.sqlite`
- `analysis/player_match_stats.csv`
- `analysis/player_aggregate.csv`
- `analysis/team_aggregate.csv`
- `docs/brasil-japao-moneyball.html`

O relatorio final e estatico e referencia assets em `docs/assets/heatmaps`.

Metricas centrais do modelo:

- passes totais, passes certos, erro de passe e passe certo %
- chute no alvo %, drible %, cruzamento %, bola longa %
- duelos no chao %, duelos aereos % e duelo geral %
- FGT Index por funcao em percentil com shrinkage por minutos
