#!/usr/bin/env python3
"""Player ranking page for the Foot Game Theory dossier.

Ranks every regular (>= 45 min) by the FGT Index, filterable by team and
sortable by column. Same light "paper" aesthetic as the report, with Arvor
branding. Entry point: ``render_ranking(players)``.
"""

from __future__ import annotations

import html

import pandas as pd
import seo

SEO_TITLE = "Ranking dos Jogadores · Foot Game Theory · Arvor Intelligence"
SEO_DESC = (
    "Ranking dos jogadores de Brasil e Japão pelo FGT Index — o score Moneyball "
    "0–100 da Arvor Intelligence. Filtrável por seleção e ordenável por métrica."
)
MEDALS = {0: "🥇", 1: "🥈", 2: "🥉"}
COLS = [
    ("overall_index", "FGT", True),
    ("attack_index", "Ataque", True),
    ("creation_index", "Criação", True),
    ("defense_index", "Defesa", True),
    ("progression_index", "Progressão", True),
    ("xgi90", "xGI/90", False),
    ("pass_accuracy", "Passe%", False),
]


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def _bar(value: float) -> str:
    w = max(2.0, min(100.0, value))
    return f'<span class="rbar"><span style="width:{w:.0f}%"></span></span>'


def _rows(players: pd.DataFrame) -> str:
    pool = players[players["minutes_played"] >= 45].copy()
    pool = pool.sort_values("overall_index", ascending=False).reset_index(drop=True)
    out = []
    for i, (_, p) in enumerate(pool.iterrows()):
        team = str(p["team"])
        rank = MEDALS.get(i, f"{i + 1}")
        cells = [
            f'<td class="rk">{rank}</td>',
            f'<td class="pl"><span class="tdot {team}"></span>'
            f'<b>{esc(str(p["player_label"]).split("(")[0].strip())}</b>'
            f'<span class="sh">{esc(str(p["player_label"]).split("(")[-1].rstrip(")")) if "(" in str(p["player_label"]) else ""}</span></td>',
            f'<td>{esc(p["team_label"])}</td>',
            f'<td>{esc(p["role"])}</td>',
        ]
        for key, _, is_idx in COLS:
            val = float(p[key])
            if key == "pass_accuracy":
                cells.append(f"<td data-v='{val:.4f}'>{val * 100:.0f}%</td>")
            elif is_idx:
                cells.append(
                    f"<td data-v='{val:.2f}'><span class='num'>{val:.0f}</span>{_bar(val)}</td>"
                )
            else:
                cells.append(f"<td data-v='{val:.4f}'>{val:.2f}</td>")
        out.append(f'<tr data-team="{esc(team)}">' + "".join(cells) + "</tr>")
    return "".join(out)


def _podium(players: pd.DataFrame) -> str:
    top = (
        players[players["minutes_played"] >= 45]
        .sort_values("overall_index", ascending=False)
        .head(3)
        .reset_index(drop=True)
    )
    order = [1, 0, 2]  # silver, gold, bronze for visual podium
    cards = []
    for slot in order:
        if slot >= len(top):
            continue
        p = top.iloc[slot]
        team = str(p["team"])
        cards.append(
            f'<div class="pod pod{slot}">'
            f'<div class="medal">{MEDALS[slot]}</div>'
            f'<div class="pfgt {team}">{float(p["overall_index"]):.0f}</div>'
            f'<div class="pname">{esc(str(p["player_label"]).split("(")[0].strip())}</div>'
            f'<div class="pmeta">{esc(p["team_label"])} · {esc(p["role"])}</div>'
            "</div>"
        )
    return f'<div class="podium">{"".join(cards)}</div>'


def render_ranking(players: pd.DataFrame) -> str:
    header_cells = "".join(
        f'<th data-sort="{i + 4}">{esc(label)}</th>'
        for i, (_, label, _) in enumerate(COLS)
    )
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(SEO_TITLE)}</title>
<meta name="description" content="{esc(SEO_DESC)}">
{seo.head_seo(SEO_TITLE, SEO_DESC, "/ranking.html")}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=Fraunces:opsz,wght@9..144,600;9..144,900&family=Source+Sans+3:wght@400;600;700;800;900&family=Spline+Sans+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
:root{{
  --paper:#faf8f3; --panel:#fff; --ink:#14171d; --muted:#5e6675; --line:#dde2ec;
  --bra:#13a05c; --bra-d:#0c6f3f; --gold:#b07d10; --jpn:#2a5fb0; --jpn-d:#173a72;
  --serif:"Fraunces",Georgia,serif; --sans:"Source Sans 3",system-ui,sans-serif;
  --display:"Archivo Black",Impact,sans-serif; --mono:"Spline Sans Mono",ui-monospace,monospace;
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);font-size:16px;line-height:1.55}}
nav{{position:sticky;top:0;z-index:20;background:rgba(250,248,243,.92);backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}}
nav .wrap{{display:flex;gap:16px;align-items:center;height:54px}}
.wrap{{width:min(1100px,calc(100% - 40px));margin:auto}}
.brandlink{{display:flex;align-items:center;gap:8px;text-decoration:none;color:var(--ink);margin-right:auto}}
.brandlink img{{width:26px;height:26px;object-fit:contain}}
.brandlink b{{font-family:var(--display);font-size:.85rem}}
nav a.lnk{{color:var(--muted);text-decoration:none;font-weight:700;font-size:.85rem}}
nav a.lnk:hover{{color:var(--bra)}}
header.hero{{padding:54px 0 18px}}
.kicker{{font-family:var(--mono);font-size:.76rem;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:var(--bra-d)}}
h1{{font-family:var(--serif);font-weight:900;font-size:clamp(2.2rem,6vw,4rem);line-height:1;margin:12px 0 10px}}
.lead{{color:#33414f;font-size:1.12rem;max-width:720px}}
.podium{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;align-items:end;margin:30px 0 10px}}
.pod{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px;text-align:center;box-shadow:0 8px 22px rgba(18,24,33,.06)}}
.pod1{{transform:translateY(0)}} .pod0{{transform:translateY(-14px);border-color:var(--gold)}} .pod2{{transform:translateY(8px)}}
.medal{{font-size:1.6rem}}
.pfgt{{font-family:var(--display);font-size:clamp(2rem,5vw,3rem);line-height:1}}
.pfgt.brasil{{color:var(--bra-d)}} .pfgt.japao{{color:var(--jpn)}}
.pname{{font-family:var(--serif);font-weight:900;font-size:1.15rem;margin-top:4px}}
.pmeta{{font-family:var(--mono);font-size:.72rem;color:var(--muted)}}
.filters{{display:flex;gap:8px;margin:26px 0 12px;flex-wrap:wrap}}
.filters button{{font-family:var(--sans);font-weight:800;font-size:.84rem;border:1px solid var(--line);background:#fff;color:var(--ink);border-radius:999px;padding:8px 16px;cursor:pointer}}
.filters button.active{{background:var(--ink);color:#fff;border-color:var(--ink)}}
.tablewrap{{overflow-x:auto;border:1px solid var(--line);border-radius:14px;background:var(--panel);box-shadow:0 8px 22px rgba(18,24,33,.05)}}
table{{width:100%;border-collapse:collapse;min-width:760px}}
th,td{{padding:11px 12px;text-align:left;border-bottom:1px solid var(--line);font-size:.9rem;white-space:nowrap}}
th{{font-family:var(--mono);font-size:.7rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);cursor:pointer;user-select:none;background:#f3f1ea;position:sticky;top:54px}}
th[data-sort]:hover{{color:var(--bra-d)}}
tr:last-child td{{border-bottom:0}}
tbody tr:hover{{background:#f7f5ef}}
.rk{{font-family:var(--display);font-size:.95rem;color:var(--muted);width:42px}}
.pl b{{font-weight:800}} .pl .sh{{font-family:var(--mono);font-size:.7rem;color:var(--muted);margin-left:6px}}
.tdot{{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:8px;vertical-align:1px}}
.tdot.brasil{{background:var(--bra)}} .tdot.japao{{background:var(--jpn)}}
.num{{font-family:var(--display);font-size:.95rem;margin-right:8px}}
.rbar{{display:inline-block;width:64px;height:6px;background:#e9e6dd;border-radius:99px;overflow:hidden;vertical-align:middle}}
.rbar span{{display:block;height:100%;background:linear-gradient(90deg,var(--bra),var(--gold))}}
footer{{padding:40px 0 70px;color:var(--muted);font-family:var(--mono);font-size:.78rem}}
.foot-cta{{display:flex;align-items:center;gap:8px;margin-bottom:8px}}
.foot-cta img{{width:28px;height:28px;object-fit:contain}}
.foot-cta a{{color:var(--jpn);font-weight:700}}
.note{{font-size:.74rem;color:var(--muted);margin-top:14px;max-width:760px}}
@media (max-width:640px){{th{{position:static}}}}
</style>
</head>
<body>
<nav><div class="wrap">
  <a class="brandlink" href="https://arvor.co"><img src="assets/arvor_logo.png" alt="Arvor"><b>Arvor Intelligence</b></a>
  <a class="lnk" href="index.html">Início</a>
  <a class="lnk" href="brasil-japao-moneyball.html">Laudo</a>
</div></nav>

<header class="hero"><div class="wrap">
  <div class="kicker">Ranking · FGT Index</div>
  <h1>Quem manda no jogo</h1>
  <p class="lead">Todos os jogadores de Brasil e Japão (≥ 45 min) ordenados pelo <b>FGT Index</b> — o score Moneyball 0–100 da Arvor, por percentil e ajustado por minutos. Filtre por seleção, clique nas colunas para ordenar.</p>
  {_podium(players)}
  <div class="filters">
    <button class="active" data-f="all" onclick="flt(this,'all')">Todos</button>
    <button data-f="brasil" onclick="flt(this,'brasil')">Brasil</button>
    <button data-f="japao" onclick="flt(this,'japao')">Japão</button>
  </div>
</div></header>

<main><div class="wrap">
  <div class="tablewrap">
    <table id="rk">
      <thead><tr>
        <th>#</th><th data-sort="1">Jogador</th><th>Time</th><th>Função</th>{header_cells}
      </tr></thead>
      <tbody>{_rows(players)}</tbody>
    </table>
  </div>
  <p class="note">FGT Index: percentil por função com shrinkage por minutos <code>score · min/(min+90) + 50 · 90/(min+90)</code>.
  Dados: fase de grupos da Copa 2026 (3 jogos de cada seleção). Metodologia aberta no laudo completo.</p>
</div></main>

<footer><div class="wrap">
  <div class="foot-cta"><img src="assets/arvor_logo.png" alt="Arvor"><span><b style="color:var(--ink)">Arvor Intelligence</b> · <a href="https://arvor.co">arvor.co</a></span></div>
  Foot Game Theory · Dossiê Moneyball Brasil × Japão · Copa 2026 ·
  <a href="brasil-japao-moneyball.html" style="color:var(--bra-d)">ver o laudo completo →</a>
</div></footer>

<script>
function flt(btn, team){{
  document.querySelectorAll('.filters button').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('#rk tbody tr').forEach(tr=>{{
    tr.style.display = (team==='all'||tr.dataset.team===team) ? '' : 'none';
  }});
  renumber();
}}
function renumber(){{
  let n=1;
  document.querySelectorAll('#rk tbody tr').forEach(tr=>{{
    if(tr.style.display!=='none'){{
      const medals=['🥇','🥈','🥉'];
      tr.querySelector('.rk').textContent = n<=3?medals[n-1]:n; n++;
    }}
  }});
}}
let sortAsc={{}};
document.querySelectorAll('th[data-sort]').forEach(th=>{{
  th.addEventListener('click',()=>{{
    const col=+th.dataset.sort, body=document.querySelector('#rk tbody');
    const rows=[...body.querySelectorAll('tr')];
    const asc=sortAsc[col]=!sortAsc[col];
    rows.sort((a,b)=>{{
      const av=parse(a.children[col]), bv=parse(b.children[col]);
      return asc?av-bv:bv-av;
    }});
    rows.forEach(r=>body.appendChild(r)); renumber();
  }});
}});
function parse(td){{
  if(td.dataset.v!==undefined) return parseFloat(td.dataset.v);
  return td.textContent.trim().toLowerCase().charCodeAt(0)||0;
}}
</script>
</body>
</html>
"""
