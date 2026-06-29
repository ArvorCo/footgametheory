#!/usr/bin/env python3
"""Viral 25-card thread for the Brazil x Japan dossier (PNAD thread style).

Dark page, 16:9 screenshot-ready cards. Three kinds of card carry the argument:
math explainers (with a formula block + a visual), findings (a chart), and
**player cards** — one per Brazilian starter, GK to striker, with his territory
heatmap as the hero plus opponent/weakness badges and stat chips. Words come
from ``analysis/copy_thread.json``; data/visuals are attached here so prose and
numbers always match.
"""

from __future__ import annotations

import html
from typing import Any, cast

import cronista
import pandas as pd
from charts_svg import (
    compare_bars,
    finishing_dumbbell,
    formation_433,
    poisson_curve,
    scoreline_bars,
    shrinkage_curve,
    xg_concept,
)

# Posts 9..19 map to these starters, goalkeeper to right winger.
PLAYER_KEYS = [
    "alisson_becker_1",
    "gabriel_3",
    "marquinhos_4",
    "douglas_santos_16",
    "danilo_13",
    "casemiro_5",
    "bruno_guimaraes_8",
    "lucas_paqueta_20",
    "matheus_cunha_9",
    "vinicius_junior_7",
    "rayan_26",
]
ROLE_TAG = {
    "Goleiro": "GOLEIRO",
    "Defesa": "DEFESA",
    "Meio": "MEIO",
    "Ataque": "ATAQUE",
}


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def pct(value: float, digits: int = 0) -> str:
    return f"{100 * value:.{digits}f}%"


def fnum(value: Any, digits: int = 2) -> str:
    try:
        val = float(value)
    except (TypeError, ValueError):
        return esc(value)
    if abs(val - round(val)) < 1e-9:
        return f"{int(round(val))}"
    return f"{val:.{digits}f}".replace(".", ",")


def bignum(value: str, sub: str = "", color: str = "bra") -> str:
    sub_html = f'<p class="sub">{sub}</p>' if sub else ""
    return f'<div class="vcenter"><div class="bignum {color}">{esc(value)}</div>{sub_html}</div>'


def chips(items: list[tuple[str, str]]) -> str:
    cells = "".join(
        f'<div class="chip"><span class="cl">{esc(label)}</span>'
        f'<span class="cv">{esc(value)}</span></div>'
        for label, value in items
    )
    return f'<div class="chips">{cells}</div>'


def badge(kind: str, label: str, value: str) -> str:
    return (
        f'<div class="badge {kind}"><span class="bl">{esc(label)}</span>'
        f'<span class="bv">{esc(value)}</span></div>'
    )


def _row(df: pd.DataFrame, team: str) -> pd.Series:
    return df[df["team"] == team].iloc[0]


def build_visuals(
    players: pd.DataFrame,
    team: pd.DataFrame,
    models: dict[str, Any],
    composites: dict[str, str] | None = None,
) -> dict[int, str]:
    """Visuals for the non-player cards, keyed by post number."""
    composites = composites or {}
    sim = models["simulation"]
    mism = cast(pd.DataFrame, models["mismatches"])
    eff = cast(pd.DataFrame, models["efficiency"])
    b, j = _row(team, "brasil"), _row(team, "japao")

    confronto = composites.get("confrontation", "")
    confronto_html = (
        f'<img class="hmap" src="{esc(confronto)}" alt="Confronto Brasil x Japão">'
        '<div class="duel-legend"><span><i class="dl warm"></i>Brasil</span>'
        '<span><i class="dl cool"></i>Japão</span></div>'
        if confronto
        else ""
    )

    eff_rows = [
        (
            str(r["player_label"]).split("(")[0].strip(),
            float(r["goals"]),
            float(r["expected_goals_xg"]),
        )
        for _, r in pd.concat(
            [eff[eff["team"] == "brasil"].head(3), eff[eff["team"] == "japao"].head(2)]
        ).iterrows()
    ]

    return {
        1: bignum(
            f'{sim["p_win"] * 100:.0f}%', "vitória do Brasil · mas 48% é o resto", "bra"
        ),
        2: xg_concept(),
        3: poisson_curve(float(sim["lambda_brasil"]), float(sim["lambda_japao"])),
        4: scoreline_bars(sim["top_scorelines"]),
        5: shrinkage_curve(),
        6: finishing_dumbbell(eff_rows),
        7: compare_bars(
            [
                (
                    "Progressão %",
                    float(b["progressive_pass_rate"]) * 100,
                    float(j["progressive_pass_rate"]) * 100,
                    f'{pct(float(b["progressive_pass_rate"]))} × {pct(float(j["progressive_pass_rate"]))}',
                ),
                (
                    "Passe certo %",
                    float(b["pass_accuracy"]) * 100,
                    float(j["pass_accuracy"]) * 100,
                    f'{pct(float(b["pass_accuracy"]))} × {pct(float(j["pass_accuracy"]))}',
                ),
            ],
            width=440,
        ),
        8: compare_bars(
            [
                (
                    "Duelos %",
                    float(b["duel_win_rate"]) * 100,
                    float(j["duel_win_rate"]) * 100,
                    f'{pct(float(b["duel_win_rate"]))} × {pct(float(j["duel_win_rate"]))}',
                ),
                (
                    "Driblado (n)",
                    float(b["dribbled_past"]),
                    float(j["dribbled_past"]),
                    f'{int(b["dribbled_past"])} × {int(j["dribbled_past"])}',
                ),
            ],
            width=440,
        ),
        20: confronto_html
        or compare_bars(
            [
                (
                    str(r["lane_label"]),
                    float(r["brasil_attack_share"]) * 100,
                    float(r["japao_defense_share"]) * 100,
                    f'{pct(float(r["brasil_attack_share"]))} × {pct(float(r["japao_defense_share"]))}',
                )
                for _, r in mism.iterrows()
            ],
            width=440,
        ),
        21: compare_bars(
            [
                (
                    "Duelo aéreo %",
                    float(b["aerial_duel_win_rate"]) * 100,
                    float(j["aerial_duel_win_rate"]) * 100,
                    f'{pct(float(b["aerial_duel_win_rate"]))} × {pct(float(j["aerial_duel_win_rate"]))}',
                )
            ],
            width=440,
        ),
        22: formation_433(_xi_dicts(players), overload_lane="left"),
        23: _dont_block(),
        24: _subs_block(models.get("substitutes")),
        25: bignum(
            f'{sim["p_win"] * 100:.0f}%', "o método manda o Brasil avançar", "bra"
        ),
    }


def _xi_dicts(players: pd.DataFrame) -> list[dict]:
    brazil = players[players["team"] == "brasil"].copy()

    def line(pos: int, n: int) -> pd.DataFrame:
        return (
            brazil[brazil["position"] == pos]
            .sort_values("overall_index", ascending=False)
            .head(n)
        )

    xi = pd.concat([line(0, 1), line(1, 4), line(2, 3), line(3, 3)]).drop_duplicates(
        "player_key"
    )
    return [
        {"name": r["player_label"], "role": r["role"], "position": int(r["position"])}
        for _, r in xi.sort_values("position").iterrows()
    ]


def _subs_block(subs: object) -> str:
    if not isinstance(subs, pd.DataFrame) or subs.empty:
        return ""
    items = []
    for _, row in subs.head(4).iterrows():
        items.append(
            f'<li><span class="ar">{esc(row["trait"])}</span>'
            f'<b>{esc(row["substitute"])}</b> entra por {esc(row["starter"])} '
            f'<span class="ar">{esc(row["reason"])}</span></li>'
        )
    return f'<ul class="subs">{"".join(items)}</ul>'


def _dont_block() -> str:
    sins = [
        "Laterais altos ao mesmo tempo",
        "Casemiro caçando Kamada",
        "Vertical forçado por dentro",
        "Cruzar sem ocupação",
    ]
    return '<ul class="dont">' + "".join(f"<li>✕ {esc(s)}</li>" for s in sins) + "</ul>"


# --------------------------------------------------------------------------- #
# Card renderers
# --------------------------------------------------------------------------- #
def _shell(
    n: int, label: str, body_inner: str, copy_text: str, single: bool = False
) -> str:
    chars = len(copy_text)
    cls = " single" if single else ""
    return f"""<section class="post">
  <div class="post-label">Post {n}/25 · {esc(label)}</div>
  <div class="card">
    <div class="card-head"><div class="brand"><img class="logo" src="assets/arvor_logo.png" alt="Arvor"><div><b>Arvor Intelligence</b><span>arvor.co · Foot Game Theory</span></div></div><div class="pno">{n}/25</div></div>
    <div class="card-body{cls}">{body_inner}</div>
    <div class="card-foot"><span>Arvor Intelligence · arvor.co</span><span>Poisson + FGT Index · dados da fase de grupos</span></div>
  </div>
  <div class="copy"><span class="cc">~{chars} chars</span>{esc(copy_text)}</div>
  <button class="copy-btn" onclick="cp(this)">Copiar texto</button>
</section>"""


def _generic_card(n: int, post: dict, viz: str) -> str:
    tag = esc(post.get("tag", ""))
    headline = post.get("headline", "")
    body = post.get("body", "")
    sub = post.get("sub", "")
    formula = post.get("formula", "")
    tag_html = f'<span class="lead-tag">{tag}</span>' if tag else ""
    formula_html = f'<div class="formula">{esc(formula)}</div>' if formula else ""
    sub_html = f'<p class="csub">{esc(sub)}</p>' if sub else ""
    left = f'<div>{tag_html}<h2>{headline}</h2><p class="t">{body}</p>{formula_html}{sub_html}</div>'
    right = f'<div class="viz">{viz}</div>' if viz.strip() else ""
    single = not viz.strip()
    return _shell(
        n, post.get("label", ""), left + right, post.get("copy", ""), single=single
    )


def _player_card(n: int, post: dict, dossier: pd.Series, heat_path: str) -> str:
    role_tag = ROLE_TAG.get(str(dossier["role"]), "")
    headline = (
        post.get("headline")
        or f'{dossier["name"]} × <em>{esc(dossier["opponent"])}</em>'
    )
    body = post.get("body") or "—"
    weak_kind = (
        "good" if str(dossier["weakness_label"]).startswith("Sólido") else "warn"
    )
    stat_chips = chips(
        [
            ("FGT", f'{int(dossier["fgt"])}'),
            ("Nota", fnum(dossier["rating"], 1)),
            ("Passe", pct(float(dossier["pass_accuracy"]))),
            ("Duelos", pct(float(dossier["duel_win_rate"]))),
        ]
    )
    badges = badge(
        "opp", f'Pega {dossier["opponent"]}', str(dossier["opponent_threat"])
    ) + badge(weak_kind, str(dossier["weakness_label"]), str(dossier["weakness_value"]))
    legend = (
        f'<div class="duel-legend"><span><i class="dl warm"></i>{esc(dossier["name"])}</span>'
        f'<span><i class="dl cool"></i>{esc(dossier["opponent"])}</span></div>'
    )
    img = (
        f'<img class="hmap" src="{esc(heat_path)}" alt="Duelo {esc(dossier["name"])} x {esc(dossier["opponent"])}">{legend}'
        if heat_path
        else ""
    )
    left = (
        f'<div><span class="lead-tag">{esc(role_tag)} · #{int(dossier["shirt"])}</span>'
        f"<h2>{headline}</h2>"
        f'<p class="t">{body}</p>'
        f"{stat_chips}{badges}</div>"
    )
    right = f'<div class="viz hero">{img}</div>'
    return _shell(
        n, post.get("label", dossier["name"]), left + right, post.get("copy", "")
    )


# --------------------------------------------------------------------------- #
def render_thread(
    players: pd.DataFrame,
    team: pd.DataFrame,
    models: dict[str, Any],
    composites: dict[str, str] | None = None,
) -> str:
    composites = composites or {}
    head = cronista.thread_header()
    posts = cronista.thread_posts()
    visuals = build_visuals(players, team, models, composites)
    dossiers = cast(pd.DataFrame, models["dossiers"]).set_index("player_key")

    cards = []
    for n in range(1, 26):
        post = posts.get(n, {})
        if 9 <= n <= 19:
            key = PLAYER_KEYS[n - 9]
            if key in dossiers.index:
                row = cast(pd.Series, dossiers.loc[key])
                heat = composites.get(f"duel_{key}") or composites.get(key, "")
                cards.append(_player_card(n, post, row, heat))
                continue
        cards.append(_generic_card(n, post, visuals.get(n, "")))

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(head['title'])} · Thread · Foot Game Theory</title>
<meta name="description" content="{esc(head.get('subtitle', ''))}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=Fraunces:opsz,wght@9..144,600;9..144,900&family=Source+Sans+3:wght@400;600;700;800;900&family=Spline+Sans+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
:root{{
  --paper:#f6f1e8; --ink:#13161c; --muted:#5f5d57; --line:#cdc3b3;
  --bra:#13a05c; --bra-d:#0c6f3f; --gold:#b07d10; --jpn:#2a5fb0; --jpn-d:#173a72; --red:#c0392b;
  --serif:"Fraunces",Georgia,serif; --sans:"Source Sans 3",system-ui,sans-serif;
  --display:"Archivo Black",Impact,sans-serif; --mono:"Spline Sans Mono",ui-monospace,monospace;
}}
*{{box-sizing:border-box}}
body{{margin:0;background:#14171d;color:#e9e3d6;font-family:var(--sans);font-size:16px;line-height:1.5}}
.wrap{{width:min(1280px,calc(100% - 40px));margin:auto;padding:40px 0 90px}}
header.top{{padding:46px 0 8px}}
.brand-lockup{{display:flex;align-items:center;gap:12px;margin-bottom:14px}}
.brand-lockup .logo{{width:46px;height:46px;border-radius:10px;background:#fff;object-fit:contain;padding:5px}}
.brand-lockup span{{font-weight:700;font-size:.95rem;letter-spacing:.14em;color:#9fc6ad;text-transform:uppercase}}
header.top h1{{font-family:var(--display);font-size:clamp(2.4rem,6vw,4.4rem);line-height:.96;margin:0;color:#f6f1e8}}
header.top h1 span{{display:block;color:var(--bra)}}
header.top p{{max-width:940px;color:#b9b2a3;font-size:1.05rem}}
.howto{{border:1px solid #353a45;border-radius:8px;padding:14px 18px;font-size:.9rem;color:#b9b2a3;margin:18px 0 16px}}
.howto b{{color:#f6f1e8}}
.post{{margin:46px 0}}
.post-label{{font-family:var(--mono);font-size:.8rem;color:#868b9a;text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px}}
.card{{aspect-ratio:16/9;width:100%;max-width:1200px;
  background:linear-gradient(90deg,rgba(16,19,26,.04) 1px,transparent 1px) 0 0/58px 58px,linear-gradient(180deg,#fbf7ef 0,#f6f1e8 52%,#eef2ec 100%);
  color:var(--ink);border-radius:10px;overflow:hidden;display:grid;grid-template-rows:auto 1fr auto;border:1px solid #353a45}}
.card-head{{display:flex;justify-content:space-between;align-items:center;padding:18px 34px 0}}
.brand{{display:flex;align-items:center;gap:11px}}
.brand .logo{{width:36px;height:36px;object-fit:contain}}
.brand b{{font-size:.92rem;color:var(--jpn-d)}}
.brand span{{display:block;color:var(--muted);font-size:.76rem}}
.pno{{font-family:var(--mono);font-size:.95rem;color:var(--muted)}}
.card-body{{padding:6px 34px;display:grid;grid-template-columns:minmax(0,1.05fr) minmax(0,1fr);gap:24px;align-items:center;min-height:0}}
.card-body.single{{grid-template-columns:1fr}}
.card h2{{font-family:var(--serif);font-weight:900;font-size:clamp(1.4rem,2.5vw,2.3rem);line-height:1.05;margin:0 0 10px;letter-spacing:-.01em}}
.card h2 em{{color:var(--bra-d);font-style:normal}}
.card h2 .b{{color:var(--jpn)}}
.card .t{{font-size:clamp(.92rem,1.3vw,1.1rem);line-height:1.4;color:#2b3039;margin:0 0 10px}}
.card .t b{{color:var(--ink)}}
.lead-tag{{display:inline-block;font-family:var(--mono);font-size:.72rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--bra-d);margin-bottom:8px}}
.csub{{font-family:var(--mono);font-size:.8rem;color:var(--muted);margin-top:10px}}
.formula{{font-family:var(--mono);font-size:clamp(.86rem,1.4vw,1.05rem);background:#0f1218;color:#9fe6c0;border-radius:8px;padding:12px 14px;margin:6px 0 8px;letter-spacing:.01em}}
.viz{{min-width:0;display:flex;align-items:center;justify-content:center}}
.viz svg{{display:block;width:100%;height:auto;max-height:300px}}
.viz.hero{{align-self:stretch}}
.hmap{{width:100%;height:auto;max-height:300px;object-fit:cover;border-radius:8px;border:1px solid var(--line)}}
.duel-legend{{display:flex;justify-content:center;gap:18px;margin-top:8px;font-family:var(--mono);font-size:.74rem;color:#3a3f47;font-weight:700}}
.duel-legend i{{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px}}
.dl.warm{{background:#ed8920}} .dl.cool{{background:#2a5fb0}}
.vcenter{{text-align:center;width:100%}}
.bignum{{font-family:var(--display);font-size:clamp(2.8rem,7vw,5.4rem);line-height:.86;color:var(--jpn);letter-spacing:-.02em}}
.bignum.bra{{color:var(--bra-d)}} .bignum.jpn{{color:var(--jpn)}} .bignum.gold{{color:var(--gold)}}
.sub{{font-family:var(--mono);font-size:.8rem;color:var(--muted);margin-top:12px;line-height:1.5}}
.chips{{display:flex;flex-wrap:wrap;gap:7px;margin:4px 0 10px}}
.chip{{background:rgba(255,255,255,.65);border:1px solid var(--line);border-radius:8px;padding:5px 10px;text-align:center;min-width:58px}}
.chip .cl{{display:block;font-family:var(--mono);font-size:.6rem;text-transform:uppercase;color:var(--muted);letter-spacing:.04em}}
.chip .cv{{display:block;font-family:var(--display);font-size:1.05rem;color:var(--ink)}}
.badge{{display:flex;justify-content:space-between;gap:10px;align-items:baseline;border-radius:8px;padding:7px 11px;margin-top:7px;font-size:.84rem}}
.badge .bl{{font-weight:800}} .badge .bv{{font-family:var(--mono);font-size:.78rem;text-align:right}}
.badge.opp{{background:#e8f0fb;border:1px solid #c4d8f2;color:var(--jpn-d)}}
.badge.warn{{background:#fbeede;border:1px solid #ecd6a8;color:#7a4f06}}
.badge.good{{background:#eafbf2;border:1px solid #bfe3cf;color:var(--bra-d)}}
.subs{{list-style:none;margin:0;padding:0;font-size:.92rem}}
.subs li{{padding:8px 0;border-bottom:1px solid var(--line)}}
.subs li:last-child{{border-bottom:0}}
.subs .ar{{display:inline-block;font-family:var(--mono);font-size:.66rem;text-transform:uppercase;color:var(--bra-d);margin-right:8px}}
.dont{{list-style:none;margin:0;padding:0;font-size:1.05rem;font-weight:700;color:var(--red)}}
.dont li{{padding:9px 0;border-bottom:1px solid var(--line)}}
.dont li:last-child{{border-bottom:0}}
.card-foot{{display:flex;justify-content:space-between;padding:0 34px 14px;font-family:var(--mono);font-size:.7rem;color:var(--muted)}}
.copy{{margin-top:14px;background:#0f1218;border:1px solid #353a45;border-radius:8px;padding:16px 18px;font-family:var(--mono);font-size:.92rem;line-height:1.55;color:#dad5c7;white-space:pre-wrap;word-wrap:break-word;position:relative}}
.copy .cc{{position:absolute;top:10px;right:14px;font-size:.72rem;color:#6b7080}}
.copy-btn{{margin-top:8px;background:var(--bra);border:0;color:#fff;font-weight:800;font-size:.8rem;padding:8px 14px;border-radius:6px;cursor:pointer}}
.copy-btn:active{{transform:translateY(1px)}}
.back{{display:inline-block;margin-top:10px;color:#7fc6a0;font-weight:700;text-decoration:none}}
@media (max-width:860px){{.card{{aspect-ratio:auto}}.card-body{{grid-template-columns:1fr}}.viz.hero{{order:-1}}.hmap{{max-height:260px}}}}
</style>
</head>
<body>
<div class="wrap">
<header class="top">
  <div class="brand-lockup"><img class="logo" src="assets/arvor_logo.png" alt="Arvor"><span><b>ARVOR INTELLIGENCE</b> · arvor.co · FOOT GAME THEORY · COPA 2026</span></div>
  <h1>{esc(head['title'])}<span>{esc(head.get('subtitle', ''))}</span></h1>
  <p>{esc(head.get('intro', ''))}</p>
  <div class="howto"><b>Como publicar:</b> screenshot em cada card (16:9), “Copiar texto” para o corpo, publique na ordem. Laudo completo: <span style="font-family:var(--mono)">brasil-japao-moneyball.html</span>.</div>
  <a class="back" href="brasil-japao-moneyball.html">← Laudo completo</a> &nbsp; <a class="back" href="ranking.html">Ranking →</a> &nbsp; <a class="back" href="index.html">Início →</a>
</header>
{"".join(cards)}
</div>
<script>
function cp(btn){{
  const box = btn.previousElementSibling;
  const text = box.childNodes[box.childNodes.length-1].textContent.trim();
  navigator.clipboard.writeText(text).then(()=>{{
    const old = btn.textContent; btn.textContent = "Copiado ✓";
    setTimeout(()=>{{btn.textContent = old;}}, 1600);
  }});
}}
</script>
</body>
</html>
"""
