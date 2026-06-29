#!/usr/bin/env python3
"""Marketing hero homepage for Foot Game Theory by Arvor Intelligence.

A landing page that sells the project and routes to the three deliverables
(report, ranking, thread), with Arvor branding and an open-source band.
Entry point: ``render_home(models, composites, players, heatmaps)``.
"""

from __future__ import annotations

import html
from typing import Any

import pandas as pd
import seo

REPO_URL = "https://github.com/ArvorCo/footgametheory"
SEO_TITLE = "Foot Game Theory · Brasil × Japão · Moneyball da Copa 2026"
SEO_DESC = (
    "O dossiê Moneyball de Brasil × Japão na Copa 2026: probabilidade de placar, "
    "heatmaps de território, ranking de jogadores e veredito tático. Por Arvor Intelligence."
)


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def render_home(
    models: dict[str, Any],
    composites: dict[str, str],
    players: pd.DataFrame,
    heatmaps: pd.DataFrame,
) -> str:
    sim = models["simulation"]
    p_win = f'{sim["p_win"] * 100:.0f}%'
    n_players = int((players["minutes_played"] >= 45).sum())
    n_heat = int(len(heatmaps))
    bg = composites.get("confrontation", "")
    bg_style = (
        f"style=\"background-image:linear-gradient(180deg,rgba(8,12,10,.72),rgba(8,12,10,.93)),url('{esc(bg)}')\""
        if bg
        else ""
    )

    stats = [
        (p_win, "vitória do Brasil", "modelo de Poisson"),
        ("6", "jogos analisados", "fase de grupos"),
        (str(n_players), "jogadores rankeados", "FGT Index"),
        (str(n_heat), "heatmaps", "processados"),
    ]
    stats_html = "".join(
        f'<div class="stat"><div class="sv">{esc(v)}</div>'
        f'<div class="sl">{esc(label)}</div><div class="sx">{esc(x)}</div></div>'
        for v, label, x in stats
    )

    cards = [
        (
            "brasil-japao-moneyball.html",
            "O Laudo",
            "O relatório completo: probabilidade de placar, heatmaps de território, radares, os 11 mapa a mapa, o plano de jogo e o veredito. Denso, visual e direto.",
            "Ler o laudo",
            "report",
            False,
        ),
        (
            "ranking.html",
            "O Ranking",
            "Todos os jogadores de Brasil e Japão ordenados pelo FGT Index, o score Moneyball 0–100. Filtrável por seleção e ordenável por métrica.",
            "Ver o ranking",
            "rank",
            False,
        ),
        (
            "https://arvor.co",
            "Próximos dossiês",
            "Se o Brasil avançar, o próximo relatório sai aqui — com o adversário definido e a mesma profundidade. Acompanhe a Arvor para não perder.",
            "Seguir a Arvor",
            "soon",
            True,
        ),
    ]
    cards_html = "".join(
        f'<a class="card" href="{esc(href)}">'
        f'<div class="ctag {tag}">{"EM BREVE" if soon else esc(tag.upper())}</div>'
        f"<h3>{esc(title)}</h3><p>{esc(desc)}</p>"
        f'<span class="go">{esc(cta)} →</span></a>'
        for href, title, desc, cta, tag, soon in cards
    )

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(SEO_TITLE)}</title>
<meta name="description" content="{esc(SEO_DESC)}">
{seo.head_seo(SEO_TITLE, SEO_DESC, "/")}
{seo.jsonld_site(SEO_TITLE, SEO_DESC)}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=Fraunces:opsz,wght@9..144,600;9..144,900&family=Source+Sans+3:wght@400;600;700;800;900&family=Spline+Sans+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
:root{{
  --ink:#0b0f0d; --paper:#faf8f3; --bra:#13a05c; --bra-d:#0c6f3f; --gold:#e8b923;
  --jpn:#2a5fb0; --cream:#e9e3d6; --muted:#9aa39c;
  --serif:"Fraunces",Georgia,serif; --sans:"Source Sans 3",system-ui,sans-serif;
  --display:"Archivo Black",Impact,sans-serif; --mono:"Spline Sans Mono",ui-monospace,monospace;
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--paper);color:#14171d;font-family:var(--sans);font-size:16px;line-height:1.6}}
a{{color:inherit}}
.wrap{{width:min(1120px,calc(100% - 40px));margin:auto}}

/* HERO */
.hero{{position:relative;color:var(--cream);background:#0b0f0d center/cover no-repeat;background-blend-mode:normal}}
.hero::after{{content:"";position:absolute;inset:0;background:radial-gradient(900px 500px at 80% -10%,rgba(19,160,92,.30),transparent)}}
.hero-in{{position:relative;z-index:2;padding:30px 0 70px}}
.topbar{{display:flex;align-items:center;gap:12px;padding:8px 0 40px}}
.topbar .logo{{width:44px;height:44px;border-radius:11px;background:#fff;object-fit:contain;padding:5px}}
.topbar b{{font-family:var(--display);font-size:.92rem;letter-spacing:.02em}}
.topbar .slug{{font-family:var(--mono);font-size:.72rem;letter-spacing:.14em;text-transform:uppercase;color:#9fc6ad}}
.topbar .gh{{margin-left:auto;font-family:var(--mono);font-size:.78rem;color:#cfe7da;text-decoration:none;border:1px solid #2c4a3b;border-radius:999px;padding:8px 14px}}
.eyebrow{{font-family:var(--mono);font-size:.8rem;letter-spacing:.16em;text-transform:uppercase;color:var(--gold)}}
.hero h1{{font-family:var(--serif);font-weight:900;font-size:clamp(2.8rem,8vw,6rem);line-height:.95;margin:14px 0 8px;color:#fff}}
.hero h1 .g{{color:var(--bra)}}
.hero .sub{{font-size:clamp(1.1rem,2.2vw,1.5rem);max-width:760px;color:#d8d2c4}}
.hero .by{{margin-top:18px;font-family:var(--mono);font-size:.82rem;color:#9fc6ad}}
.hero .by a{{color:#bfe3cf;font-weight:700}}
.statstrip{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:40px}}
.stat{{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.12);border-radius:14px;padding:18px;backdrop-filter:blur(4px)}}
.stat .sv{{font-family:var(--display);font-size:clamp(1.8rem,4vw,2.6rem);color:#fff;line-height:1}}
.stat .sl{{font-weight:800;margin-top:6px;color:#e9e3d6}}
.stat .sx{{font-family:var(--mono);font-size:.72rem;color:#9fc6ad}}

/* CARDS */
section.band{{padding:64px 0}}
.band h2{{font-family:var(--serif);font-weight:900;font-size:clamp(1.8rem,4vw,2.8rem);margin:0 0 6px}}
.band .lead{{color:#3a4750;max-width:720px;margin:0 0 28px}}
.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}}
.card{{display:flex;flex-direction:column;text-decoration:none;background:#fff;border:1px solid #e2e0d6;border-radius:16px;padding:26px;box-shadow:0 10px 30px rgba(18,24,33,.06);transition:.16s}}
.card:hover{{transform:translateY(-4px);border-color:var(--bra);box-shadow:0 16px 40px rgba(18,24,33,.10)}}
.ctag{{font-family:var(--mono);font-size:.64rem;font-weight:700;letter-spacing:.1em;padding:4px 10px;border-radius:999px;align-self:flex-start;margin-bottom:14px}}
.ctag.report{{background:#eafbf2;color:var(--bra-d)}} .ctag.rank{{background:#fbf1d8;color:#8b630f}} .ctag.soon{{background:#ece9e2;color:#6b6f67}}
.card h3{{font-family:var(--serif);font-weight:900;font-size:1.6rem;margin:0 0 8px}}
.card p{{color:#4a555d;font-size:.96rem;margin:0 0 18px;flex:1}}
.card .go{{font-weight:800;color:var(--bra-d)}}

/* ARVOR BAND */
.arvor{{background:#0b0f0d;color:var(--cream)}}
.arvor .wrap{{padding:64px 0}}
.arvor .eyebrow{{color:var(--gold)}}
.arvor h2{{font-family:var(--serif);font-weight:900;font-size:clamp(1.8rem,4vw,2.8rem);color:#fff;margin:10px 0 12px}}
.arvor p{{max-width:680px;color:#cfd6cf}}
.arvor .cta{{display:inline-block;margin-top:20px;background:var(--bra);color:#fff;font-weight:800;text-decoration:none;padding:13px 24px;border-radius:10px}}
.arvor .cta:hover{{background:var(--bra-d)}}

/* OPEN SOURCE */
.os .wrap{{padding:54px 0}}
.os h2{{font-family:var(--serif);font-weight:900;font-size:clamp(1.6rem,3.5vw,2.4rem);margin:0 0 8px}}
.os p{{color:#4a555d;max-width:720px}}
.os .pills{{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}}
.os .pill{{border:1px solid #cdc3b3;background:#fff;border-radius:999px;padding:7px 14px;font-size:.82rem;font-weight:700;color:#3a3f47}}
.os .ghbtn{{display:inline-block;margin-top:20px;border:1px solid var(--ink);border-radius:10px;padding:12px 20px;font-weight:800;text-decoration:none;color:var(--ink)}}

footer{{background:#0b0f0d;color:#9fc6ad;font-family:var(--mono);font-size:.8rem}}
footer .wrap{{padding:30px 0;display:flex;flex-wrap:wrap;gap:14px;align-items:center}}
footer img{{width:26px;height:26px;object-fit:contain}}
footer a{{color:#bfe3cf}}
@media (max-width:820px){{.statstrip{{grid-template-columns:repeat(2,1fr)}}.cards{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<header class="hero" {bg_style}>
  <div class="wrap hero-in">
    <div class="topbar">
      <img class="logo" src="assets/arvor_logo.png" alt="Arvor">
      <div><b>Arvor Intelligence</b><div class="slug">Foot Game Theory</div></div>
      <a class="gh" href="{REPO_URL}">★ GitHub</a>
    </div>
    <div class="eyebrow">Moneyball da Copa 2026 · Oitavas</div>
    <h1>Brasil <span class="g">×</span> Japão,<br>decidido nos dados.</h1>
    <p class="sub">Um dossiê tático-estatístico que junta modelo de probabilidade, mapas de calor de território e a alma da crônica. O craque encontra o cronista.</p>
    <p class="by">por <a href="https://arvor.co">Arvor Intelligence · arvor.co</a></p>
    <div class="statstrip">{stats_html}</div>
  </div>
</header>

<section class="band"><div class="wrap">
  <h2>Três formas de ler o jogo</h2>
  <p class="lead">Do laudo profundo à carta de um tweet. Tudo gerado a partir dos dados da fase de grupos, com método aberto.</p>
  <div class="cards">{cards_html}</div>
</div></section>

<section class="arvor"><div class="wrap">
  <div class="eyebrow">Quem faz</div>
  <h2>Inteligência que vira decisão</h2>
  <p>A <b>Arvor</b> transforma dados em vantagem — de futebol a finanças, de IA a estratégia. O Foot Game Theory é uma amostra do que fazemos: pegar o caos dos números e devolver clareza, narrativa e ação.</p>
  <a class="cta" href="https://arvor.co">Conheça a Arvor →</a>
</div></section>

<section class="os"><div class="wrap">
  <h2>Construído no aberto</h2>
  <p>Para quem é técnico: <b>código, dados e metodologia são públicos</b> no GitHub. O pipeline extrai os dados, calcula o FGT Index, simula o placar por Poisson, compõe os heatmaps e gera o site — tudo reprodutível com um comando.</p>
  <div class="pills">
    <span class="pill">Python · pandas · numpy</span><span class="pill">Poisson / Monte Carlo</span>
    <span class="pill">FGT Index</span><span class="pill">Heatmaps compostos</span>
    <span class="pill">Pillow · scikit-learn</span><span class="pill">Zero-lint</span>
  </div>
  <a class="ghbtn" href="{REPO_URL}">Ver o código no GitHub →</a>
</div></section>

<footer><div class="wrap">
  <img src="assets/arvor_logo.png" alt="Arvor">
  <span><b style="color:#e9e3d6">Arvor Intelligence</b> · <a href="https://arvor.co">arvor.co</a></span>
  <span style="margin-left:auto"><a href="{REPO_URL}">GitHub</a> · Foot Game Theory · Copa 2026</span>
</div></footer>
</body>
</html>
"""
