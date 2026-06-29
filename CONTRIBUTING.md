# Contribuindo

Obrigado pelo interesse no **Foot Game Theory**! Contribuições são bem-vindas —
correções, novos modelos, novas visualizações ou melhorias de texto.

## Setup

```bash
git clone https://github.com/ArvorCo/footgametheory.git
cd footgametheory
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Rodar o pipeline

```bash
python3 scripts/build_report.py
```

Isso regenera o banco (`build/`), os CSVs (`analysis/`) e todo o site (`docs/`).

## Padrão de qualidade

Política **zero-lint**. Antes de abrir um PR:

```bash
ruff check scripts/
black --check scripts/
isort --check scripts/
```

Para corrigir automaticamente: `black scripts/ && isort scripts/`.
A configuração vive em `pyproject.toml` (perfil `black` para o isort).

## Estilo

- Arquivos de código com menos de ~1000 linhas; se passar, dividir por responsabilidade.
- Funções puras sempre que possível: recebem DataFrames, devolvem DataFrames/strings.
- `data/` é fonte imutável; material derivado vai para `build/`, `analysis/` ou `docs/`.

## Pull Requests

1. Crie um branch a partir de `main`.
2. Rode o pipeline e os linters.
3. Descreva o que mudou e por quê. Screenshots ajudam para mudanças visuais.

## Dados

Veja a nota de dados no [LICENSE](LICENSE) e no README. Não adicione dados de
terceiros sem garantir o direito de redistribuição.
