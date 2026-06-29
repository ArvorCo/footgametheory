#!/usr/bin/env python3
"""Premium HTML report for the Brazil x Japan Moneyball dossier.

Light "paper" editorial layout (PNAD style) built around inline-SVG
infographics, composite heatmaps and cronista prose instead of raw tables.
The single entry point ``render_report`` is called by ``build_report.py``.
"""

from __future__ import annotations

import html
from typing import Any, cast

import cronista
import pandas as pd
import seo
from charts_svg import (
    BRA,
    JPN,
    compare_bars,
    finishing_dumbbell,
    formation_433,
    poisson_bar,
    poisson_curve,
    radar,
    scoreline_bars,
    shrinkage_curve,
    xg_concept,
    xg_race,
    zone_grid_3x3,
)
from models import RADAR_AXES

LANE_LABEL = {
    "left": "corredor esquerdo",
    "center": "corredor central",
    "right": "corredor direito",
}
THIRD_LABEL = {
    "low": "terço defensivo",
    "mid": "terço médio",
    "high": "terço de ataque",
}
ROLE_ORDER = {"Goleiro": 0, "Defesa": 1, "Meio": 2, "Ataque": 3}


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def pct(value: float, digits: int = 1) -> str:
    return f"{100 * value:.{digits}f}%"


def fmt(value: Any, digits: int = 2) -> str:
    try:
        val = float(value)
    except (TypeError, ValueError):
        return esc(value)
    if val != val:  # NaN
        return "-"
    if abs(val - round(val)) < 1e-9:
        return f"{int(round(val))}"
    return f"{val:.{digits}f}"


def paras(section: dict) -> str:
    """Render a copy section's paragraphs (already trusted, only <em>/<b> inline)."""
    return "".join(f"<p>{p}</p>" for p in section.get("paragraphs", []))


def lead_para(section: dict) -> str:
    items = section.get("paragraphs", [])
    if not items:
        return ""
    body = "".join(f"<p>{p}</p>" for p in items[1:])
    return f'<p class="lead">{items[0]}</p>{body}'


# --------------------------------------------------------------------------- #
# Data helpers
# --------------------------------------------------------------------------- #
def _row(df: pd.DataFrame, team: str) -> pd.Series:
    return df[df["team"] == team].iloc[0]


def compare_rows(team: pd.DataFrame) -> list[tuple[str, float, float, str]]:
    b, j = _row(team, "brasil"), _row(team, "japao")
    return [
        (
            "xG criado",
            float(b["expected_goals_xg"]),
            float(j["expected_goals_xg"]),
            f'{fmt(b["expected_goals_xg"])} × {fmt(j["expected_goals_xg"])}',
        ),
        (
            "Finalizações",
            float(b["total_shots"]),
            float(j["total_shots"]),
            f'{fmt(b["total_shots"])} × {fmt(j["total_shots"])}',
        ),
        (
            "Chutes no alvo",
            float(b["shots_on_target"]),
            float(j["shots_on_target"]),
            f'{fmt(b["shots_on_target"])} × {fmt(j["shots_on_target"])}',
        ),
        (
            "Passe certo %",
            float(b["pass_accuracy"]),
            float(j["pass_accuracy"]),
            f'{pct(float(b["pass_accuracy"]))} × {pct(float(j["pass_accuracy"]))}',
        ),
        (
            "Progressão %",
            float(b["progressive_pass_rate"]),
            float(j["progressive_pass_rate"]),
            f'{pct(float(b["progressive_pass_rate"]))} × {pct(float(j["progressive_pass_rate"]))}',
        ),
        (
            "Duelos vencidos %",
            float(b["duel_win_rate"]),
            float(j["duel_win_rate"]),
            f'{pct(float(b["duel_win_rate"]))} × {pct(float(j["duel_win_rate"]))}',
        ),
    ]


def xg_series(team_match: pd.DataFrame) -> tuple[list[str], list[float], list[float]]:
    bra = team_match[team_match["team"] == "brasil"].sort_values("match_id")
    jpn = team_match[team_match["team"] == "japao"].sort_values("match_id")
    labels = [str(o) for o in bra["opponent_label"]]
    jpn_labels = [str(o) for o in jpn["opponent_label"]]
    merged = [f"{a}/{b}" for a, b in zip(labels, jpn_labels)]
    return merged, list(bra["expected_goals_xg"]), list(jpn["expected_goals_xg"])


def radar_for(
    radars: pd.DataFrame, player_key: str, fallback_sort: str, team: str, color: str
) -> tuple[str, str]:
    pool = radars[radars["player_key"] == player_key]
    if pool.empty:
        pool = radars[radars["team"] == team].sort_values(
            fallback_sort, ascending=False
        )
    if pool.empty:
        return "—", ""
    row = pool.iloc[0]
    labels = [label for _, label in RADAR_AXES]
    values = [float(row[axis]) for axis, _ in RADAR_AXES]
    return str(row["player_label"]), radar(labels, values, color=color)


def figure(svg_or_img: str, caption: str) -> str:
    return (
        f'<figure class="fig">{svg_or_img}<figcaption>{caption}</figcaption></figure>'
    )


def composite_fig(composites: dict, key: str, caption: str) -> str:
    path = composites.get(key)
    if not path:
        return ""
    return figure(
        f'<img src="{esc(path)}" alt="{esc(caption)}" loading="lazy">', caption
    )


def pick_starting_xi(players: pd.DataFrame) -> pd.DataFrame:
    brazil = players[players["team"] == "brasil"].copy()
    gk = (
        brazil[brazil["position"] == 0]
        .sort_values("overall_index", ascending=False)
        .head(1)
    )
    df = (
        brazil[brazil["position"] == 1]
        .sort_values("overall_index", ascending=False)
        .head(4)
    )
    mid = (
        brazil[brazil["position"] == 2]
        .sort_values("overall_index", ascending=False)
        .head(3)
    )
    fwd = (
        brazil[brazil["position"] == 3]
        .sort_values("overall_index", ascending=False)
        .head(3)
    )
    return pd.concat([gk, df, mid, fwd]).drop_duplicates("player_key")


def xi_dicts(xi: pd.DataFrame) -> list[dict]:
    return [
        {
            "name": row["player_label"],
            "role": row["role"],
            "position": int(row["position"]),
        }
        for _, row in xi.sort_values("position").iterrows()
    ]


def substitutes_cards(models: dict[str, Any]) -> str:
    subs = models.get("substitutes")
    if not isinstance(subs, pd.DataFrame) or subs.empty:
        return ""
    cards = []
    for _, row in subs.iterrows():
        cards.append(
            '<div class="sub-card">'
            f'<div class="arche">{esc(row["trait"])}</div>'
            f'<div class="sub-line"><span class="bench">{esc(row["substitute"])}</span>'
            f'<span class="arrow">entra por</span><span class="starter">{esc(row["starter"])}</span></div>'
            f'<div class="sub-role">{esc(row["role"])} · {esc(row["reason"])}</div>'
            "</div>"
        )
    return f'<div class="sub-grid">{"".join(cards)}</div>'


def dossier_cards(models: dict[str, Any], composites: dict[str, str]) -> str:
    """Player-by-player scouting cards: heatmap + opponent + weakness + chips."""
    dossiers = models.get("dossiers")
    if not isinstance(dossiers, pd.DataFrame) or dossiers.empty:
        return ""
    cards = []
    for _, d in dossiers.sort_values("order").iterrows():
        key = str(d["player_key"])
        path = composites.get(f"duel_{key}") or composites.get(key, "")
        is_duel = bool(composites.get(f"duel_{key}"))
        legend = (
            '<div class="dlegend"><span><i class="dl warm"></i>'
            f'{esc(d["name"])}</span><span><i class="dl cool"></i>{esc(d["opponent"])}</span></div>'
            if is_duel
            else ""
        )
        img = (
            f'<img src="{esc(path)}" alt="Duelo {esc(d["name"])}" loading="lazy">'
            if path
            else ""
        )
        weak_cls = "good" if str(d["weakness_label"]).startswith("Sólido") else "warn"
        chip_row = (
            '<div class="dchips">'
            f'<span class="dchip"><i>FGT</i>{int(d["fgt"])}</span>'
            f'<span class="dchip"><i>Nota</i>{fmt(d["rating"], 1)}</span>'
            f'<span class="dchip"><i>Passe</i>{pct(float(d["pass_accuracy"]), 0)}</span>'
            f'<span class="dchip"><i>Duelos</i>{pct(float(d["duel_win_rate"]), 0)}</span>'
            "</div>"
        )
        cards.append(
            '<article class="dcard">'
            f'<div class="dmap">{img}</div>'
            '<div class="dbody">'
            f"{legend}"
            f'<div class="drole">{esc(str(d["role"]).upper())} · #{int(d["shirt"])}</div>'
            f'<h4>{esc(d["name"])}</h4>'
            f"{chip_row}"
            f'<div class="dbadge opp"><b>Pega {esc(d["opponent"])}</b><span>{esc(d["opponent_threat"])}</span></div>'
            f'<div class="dbadge {weak_cls}"><b>{esc(d["weakness_label"])}</b><span>{esc(d["weakness_value"])}</span></div>'
            "</div></article>"
        )
    return f'<div class="dgrid">{"".join(cards)}</div>'


# --------------------------------------------------------------------------- #
# Main render
# --------------------------------------------------------------------------- #
def render_report(
    stats: pd.DataFrame,
    heatmaps: pd.DataFrame,
    players: pd.DataFrame,
    team_match: pd.DataFrame,
    team: pd.DataFrame,
    models: dict[str, Any],
    composites: dict[str, str] | None = None,
    db_relative: str = "build/footgametheory.sqlite",
) -> str:
    composites = composites or {}
    sim = models["simulation"]
    radars = cast(pd.DataFrame, models["radars"])
    mism = cast(pd.DataFrame, models["mismatches"])
    grids = cast(pd.DataFrame, models["zone_grids"])
    eff = cast(pd.DataFrame, models["efficiency"])
    b = _row(team, "brasil")

    h = cronista.hero()
    xi = pick_starting_xi(players)

    # Charts -------------------------------------------------------------- #
    poisson_svg = poisson_bar(sim["p_win"], sim["p_draw"], sim["p_loss"])
    scores_svg = scoreline_bars(sim["top_scorelines"])
    compare_svg = compare_bars(compare_rows(team))
    xg_labels, xg_bra, xg_jpn = xg_series(team_match)
    xg_svg = xg_race(xg_labels, xg_bra, xg_jpn)

    vini_name, vini_radar = radar_for(
        radars, "vinicius_junior_7", "attack_index", "brasil", BRA
    )
    jp_threat = radars[radars["team"] == "japao"].sort_values(
        "attack_index", ascending=False
    )
    jp_key = str(jp_threat.iloc[0]["player_key"]) if not jp_threat.empty else ""
    jp_name, jp_radar = radar_for(radars, jp_key, "attack_index", "japao", JPN)

    eff_bra = eff[eff["team"] == "brasil"].head(4)
    eff_jpn = eff[eff["team"] == "japao"].head(2)
    eff_rows = [
        (
            str(r["player_label"]).split("(")[0].strip(),
            float(r["goals"]),
            float(r["expected_goals_xg"]),
        )
        for _, r in pd.concat([eff_bra, eff_jpn]).iterrows()
    ]
    eff_svg = finishing_dumbbell(eff_rows)

    def grid_cells(t: str) -> dict:
        sub = grids[grids["team"] == t]
        return {
            (row["third"], row["lane"]): float(row["value"])
            for _, row in sub.iterrows()
        }

    grid_bra = zone_grid_3x3(grid_cells("brasil"), color=BRA)
    grid_jpn = zone_grid_3x3(grid_cells("japao"), color=JPN)
    form_svg = formation_433(xi_dicts(xi), overload_lane="left")

    mism_rows = [
        (
            str(r["lane_label"]),
            float(r["brasil_attack_share"]) * 100,
            float(r["japao_defense_share"]) * 100,
            f'{pct(float(r["brasil_attack_share"]))} × {pct(float(r["japao_defense_share"]))}',
        )
        for _, r in mism.iterrows()
    ]
    mism_svg = compare_bars(mism_rows)

    math_xg = xg_concept()
    math_poisson = poisson_curve(
        float(sim["lambda_brasil"]), float(sim["lambda_japao"])
    )
    math_shrink = shrinkage_curve()
    dossier_html = dossier_cards(models, composites)

    # Copy ---------------------------------------------------------------- #
    s_open = cronista.section("abertura", "O confronto")
    s_mat = cronista.section("matematica", "A matemática, sem susto")
    s_onze = cronista.section("os_onze", "Os 11, mapa a mapa")
    s_prob = cronista.section("probabilidade", "A conta antes da bola")
    s_comp = cronista.section("comparativo", "Quem cria mais perigo")
    s_terr = cronista.section("territorio", "O território")
    s_zona = cronista.section("zonas", "Onde bater")
    s_radar = cronista.section("radares", "O alfa e as ameaças")
    s_fin = cronista.section("finalizacao", "Os matadores")
    s_esc = cronista.section("escalacao", "A escalação")
    s_clu = cronista.section("clusters", "O banco inteligente")
    s_ver = cronista.section("veredito", "O veredito")

    most = sim["most_likely"]
    chips = [
        ("Vitória Brasil", f'{sim["p_win"] * 100:.0f}%', "bra"),
        ("xG na fase", fmt(b["expected_goals_xg"]), "ink"),
        ("Placar provável", f'{most["brasil"]}–{most["japao"]}', "ink"),
        ("Escalação", "4-3-3", "ink"),
    ]
    chips_html = "".join(
        f'<div class="chip"><span class="chip-l">{esc(label)}</span>'
        f'<span class="chip-v {cls}">{esc(val)}</span></div>'
        for label, val, cls in chips
    )

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Brasil × Japão · Dossiê Moneyball · Foot Game Theory</title>
<meta name="description" content="{esc(h['lead'])}">
{seo.head_seo("Brasil × Japão · Dossiê Moneyball · Foot Game Theory", h['lead'], "/brasil-japao-moneyball.html", og_type="article")}
{seo.jsonld_article("Brasil × Japão · Dossiê Moneyball", h['lead'], "/brasil-japao-moneyball.html")}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=Fraunces:opsz,wght@9..144,500;9..144,700;9..144,900&family=Source+Sans+3:wght@400;600;700;800;900&family=Spline+Sans+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
:root{{
  --paper:#faf8f3; --panel:#fff; --ink:#14171d; --muted:#5e6675; --line:#dde2ec; --line-2:#cdc3b3;
  --bra:#13a05c; --bra-d:#0c6f3f; --gold:#b07d10; --jpn:#2a5fb0; --jpn-d:#173a72; --red:#c0392b;
  --serif:"Fraunces",Georgia,serif; --sans:"Source Sans 3",system-ui,sans-serif;
  --display:"Archivo Black",Impact,sans-serif; --mono:"Spline Sans Mono",ui-monospace,monospace;
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);font-size:17px;line-height:1.6}}
body::before{{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;opacity:.5;
  background:linear-gradient(90deg,rgba(16,19,26,.035) 1px,transparent 1px) 0 0/60px 60px}}
.wrap{{position:relative;z-index:1;width:min(1180px,calc(100% - 40px));margin:auto}}
nav{{position:sticky;top:0;z-index:20;background:rgba(250,248,243,.92);backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}}
nav .wrap{{display:flex;gap:18px;align-items:center;height:52px;overflow-x:auto}}
nav b{{font-family:var(--display);font-size:.85rem;letter-spacing:.02em;white-space:nowrap}}
.brandlink{{display:flex;align-items:center;gap:8px;text-decoration:none;color:var(--ink)!important}}
.navlogo{{width:26px;height:26px;object-fit:contain}}
.footbrand{{display:flex;align-items:center;gap:8px;margin-bottom:8px}}
.footbrand img{{width:30px;height:30px;object-fit:contain}}
.footbrand b{{color:var(--ink)}}
nav a{{color:var(--muted);text-decoration:none;font-size:.82rem;font-weight:700;white-space:nowrap}}
nav a:hover{{color:var(--bra)}}
header.hero{{padding:72px 0 36px}}
.kicker{{font-family:var(--mono);font-size:.78rem;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:var(--bra-d)}}
header.hero h1{{font-family:var(--serif);font-weight:900;font-size:clamp(2.6rem,7vw,5.4rem);line-height:.98;margin:14px 0 18px;letter-spacing:-.01em}}
header.hero .lead{{font-size:clamp(1.1rem,2vw,1.5rem);color:#33414f;max-width:880px;margin:0}}
.scoreboard{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:34px 0 8px}}
.chip{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 18px;box-shadow:0 6px 18px rgba(18,24,33,.05)}}
.chip-l{{display:block;font-family:var(--mono);font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}}
.chip-v{{display:block;font-family:var(--display);font-size:clamp(1.6rem,3vw,2.4rem);line-height:1.1;margin-top:6px}}
.chip-v.bra{{color:var(--bra-d)}} .chip-v.ink{{color:var(--ink)}}
section.band{{padding:46px 0;border-top:1px solid var(--line)}}
section.band h2{{font-family:var(--serif);font-weight:900;font-size:clamp(1.8rem,4vw,3rem);line-height:1.04;margin:6px 0 14px}}
section.band .lead{{font-size:1.16rem;color:#33414f;max-width:820px}}
section.band p{{max-width:820px;color:#2b3340}}
section.band em{{font-style:normal;color:var(--bra-d);font-weight:700}}
section.band b{{color:var(--ink)}}
.split{{display:grid;grid-template-columns:1fr 1fr;gap:34px;align-items:center}}
.split.text-first{{grid-template-columns:1fr 1.05fr}}
.fig{{margin:0;background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px;box-shadow:0 8px 22px rgba(18,24,33,.06)}}
.fig img{{display:block;width:100%;height:auto;border-radius:8px}}
.fig figcaption{{margin-top:10px;font-family:var(--mono);font-size:.76rem;color:var(--muted);line-height:1.45}}
.two-fig{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
.three-fig{{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}}
.dgrid{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-top:18px}}
.dcard{{background:var(--panel);border:1px solid var(--line);border-radius:14px;overflow:hidden;box-shadow:0 8px 22px rgba(18,24,33,.06)}}
.dmap{{aspect-ratio:1050/680;background:#0c3c24;overflow:hidden}}
.dmap img{{display:block;width:100%;height:100%;object-fit:cover}}
.dbody{{padding:14px 16px 16px}}
.drole{{font-family:var(--mono);font-size:.66rem;text-transform:uppercase;letter-spacing:.06em;color:var(--bra-d)}}
.dbody h4{{font-family:var(--serif);font-weight:900;font-size:1.25rem;margin:2px 0 10px}}
.dchips{{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px}}
.dchip{{background:#f3f1ea;border:1px solid var(--line);border-radius:7px;padding:4px 8px;font-family:var(--display);font-size:.95rem;color:var(--ink)}}
.dchip i{{display:block;font-family:var(--mono);font-size:.56rem;font-style:normal;text-transform:uppercase;color:var(--muted)}}
.dbadge{{display:flex;justify-content:space-between;gap:8px;align-items:baseline;border-radius:8px;padding:7px 10px;margin-top:7px;font-size:.82rem}}
.dbadge b{{font-weight:800}} .dbadge span{{font-family:var(--mono);font-size:.72rem;text-align:right}}
.dbadge.opp{{background:#e8f0fb;border:1px solid #c4d8f2;color:var(--jpn-d)}}
.dbadge.warn{{background:#fbeede;border:1px solid #ecd6a8;color:#7a4f06}}
.dbadge.good{{background:#eafbf2;border:1px solid #bfe3cf;color:var(--bra-d)}}
.dlegend{{display:flex;gap:14px;font-family:var(--mono);font-size:.68rem;font-weight:700;color:var(--muted);margin-bottom:6px}}
.dlegend i{{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:5px;vertical-align:-1px}}
.dl.warm{{background:#ed8920}} .dl.cool{{background:#2a5fb0}}
.pull{{border-left:5px solid var(--bra);background:var(--panel);margin:26px 0 0;padding:18px 24px;border-radius:0 12px 12px 0;
  font-family:var(--serif);font-weight:700;font-size:clamp(1.2rem,2.2vw,1.6rem);line-height:1.25;color:var(--ink);box-shadow:0 6px 18px rgba(18,24,33,.05)}}
.legend{{display:flex;gap:18px;flex-wrap:wrap;font-size:.8rem;color:var(--muted);font-weight:700;margin:6px 0 16px}}
.legend i{{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px}}
.dot-bra{{background:var(--bra)}} .dot-jpn{{background:var(--jpn)}}
.dot-warm{{background:#ed8920}} .dot-cool{{background:#2a5fb0}}
.pills{{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0}}
.pill{{border:1px solid var(--line-2);background:#fff;border-radius:999px;padding:7px 14px;font-size:.84rem;font-weight:700;color:#3a3f47}}
.pill.bad{{border-color:#e7c3bd;background:#fbe9e7;color:var(--red)}}
.pill.good{{border-color:#bfe3cf;background:#eafbf2;color:var(--bra-d)}}
.sub-grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;margin-top:18px}}
.sub-card{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px}}
.arche{{font-family:var(--mono);font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;color:var(--bra-d)}}
.sub-line{{display:flex;align-items:center;gap:10px;margin:8px 0 4px;font-weight:800}}
.sub-line .arrow{{color:var(--muted)}} .sub-line .bench{{color:var(--bra-d)}}
.sub-role{{font-size:.82rem;color:var(--muted)}}
details{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 18px;margin-top:10px}}
summary{{cursor:pointer;font-weight:800;color:var(--bra-d)}}
.gallery{{display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin-top:14px}}
.gallery figure{{margin:0}}
.gallery img{{width:100%;height:auto;border-radius:6px;border:1px solid var(--line)}}
.gallery span{{display:block;font-size:.66rem;color:var(--muted);margin-top:3px;font-family:var(--mono)}}
footer{{padding:40px 0 70px;border-top:1px solid var(--line);color:var(--muted);font-family:var(--mono);font-size:.78rem}}
footer a{{color:var(--jpn)}}
.cta{{display:inline-block;margin-top:8px;background:var(--bra);color:#fff;font-weight:800;text-decoration:none;padding:10px 18px;border-radius:8px}}
@media (max-width:860px){{
  .scoreboard{{grid-template-columns:repeat(2,1fr)}}
  .split,.split.text-first,.two-fig,.three-fig,.sub-grid{{grid-template-columns:1fr}}
  .dgrid{{grid-template-columns:1fr}}
  .gallery{{grid-template-columns:repeat(3,1fr)}}
}}
</style>
</head>
<body>
<nav><div class="wrap">
  <a class="brandlink" href="https://arvor.co"><img class="navlogo" src="assets/arvor_logo.png" alt="Arvor"><b>Arvor Intelligence</b></a>
  <a href="#modelo">Modelo</a><a href="#perigo">Perigo</a><a href="#territorio">Território</a>
  <a href="#matematica">Matemática</a><a href="#zonas">Zonas</a><a href="#craques">Craques</a>
  <a href="#onze">Os 11</a><a href="#matadores">Matadores</a>
  <a href="#escalacao">Escalação</a><a href="#veredito">Veredito</a>
  <a href="ranking.html">Ranking →</a><a href="index.html">Início →</a>
</div></nav>

<header class="hero"><div class="wrap">
  <div class="kicker">{esc(h['kicker'])}</div>
  <h1>{h['title']}</h1>
  <p class="lead">{h['lead']}</p>
  <div class="scoreboard">{chips_html}</div>
</div></header>

<main>
  <section class="band" id="abertura"><div class="wrap">
    <div class="kicker">A crônica</div>
    <h2>{esc(s_open['title'])}</h2>
    {lead_para(s_open)}
  </div></section>

  <section class="band" id="modelo"><div class="wrap">
    <div class="kicker">O modelo · Poisson</div>
    <h2>{esc(s_prob['title'])}</h2>
    <div class="split text-first">
      <div>{lead_para(s_prob)}</div>
      <div>
        {figure(poisson_svg, "Probabilidade de resultado em 90 minutos — modelo de Poisson sobre os xG da fase de grupos, ajustado pela defesa adversária.")}
        <div style="height:14px"></div>
        {figure(scores_svg, "Placares mais prováveis. O empate em 1–1 lidera: favoritismo não é salvo-conduto.")}
      </div>
    </div>
    {f'<blockquote class="pull">{cronista.callout("probabilidade")}</blockquote>' if cronista.callout("probabilidade") else ""}
  </div></section>

  <section class="band" id="matematica"><div class="wrap">
    <div class="kicker">A matemática · sem susto</div>
    <h2>{esc(s_mat['title'])}</h2>
    <p class="lead">{(s_mat['paragraphs'][0] if s_mat['paragraphs'] else '')}</p>
    <div class="three-fig">
      {figure(math_xg, "<b>xG</b>: cada chute vale a sua chance de virar gol. O círculo grande no meio da área vale muito mais que o chute de longe.")}
      {figure(math_poisson, "<b>Poisson</b>: P(k gols) = λ^k · e^(−λ) / k!. Com λ Brasil " + fmt(sim["lambda_brasil"]) + " e Japão " + fmt(sim["lambda_japao"]) + ", saem os 52% / 24% / 24%.")}
      {figure(math_shrink, "<b>FGT Index</b>: a nota de quem jogou pouco é puxada para a média. Aos 90 min, vale metade dado, metade prudência.")}
    </div>
    {"".join(f"<p>{p}</p>" for p in s_mat['paragraphs'][1:])}
  </div></section>

  <section class="band" id="perigo"><div class="wrap">
    <div class="kicker">Comparativo · xG</div>
    <h2>{esc(s_comp['title'])}</h2>
    <p class="lead">{(s_comp['paragraphs'][0] if s_comp['paragraphs'] else '')}</p>
    <div class="legend"><span><i class="dot-bra"></i>Brasil</span><span><i class="dot-jpn"></i>Japão</span></div>
    <div class="two-fig">
      {figure(compare_svg, "Brasil × Japão na fase de grupos: o Brasil cria quase o dobro de xG e finaliza mais.")}
      {figure(xg_svg, "Corrida de xG acumulado, jogo a jogo. A linha verde é o Brasil.")}
    </div>
    {"".join(f"<p>{p}</p>" for p in s_comp['paragraphs'][1:])}
  </div></section>

  <section class="band" id="territorio"><div class="wrap">
    <div class="kicker">Mapas de calor compostos</div>
    <h2>{esc(s_terr['title'])}</h2>
    <p class="lead">{(s_terr['paragraphs'][0] if s_terr['paragraphs'] else '')}</p>
    <div class="legend"><span><i class="dot-warm"></i>Brasil (laranja, ataca →)</span><span><i class="dot-cool"></i>Japão (azul, ataca ←)</span></div>
    {composite_fig(composites, "confrontation", "Controle de território: cada zona ganha a cor de quem a ocupa mais. Laranja = Brasil (ataca →); azul = Japão, espelhado para enfrentar o Brasil (ataca ←). Mostra de que lado cada um vive.")}
    <div class="two-fig">
      {composite_fig(composites, "brasil_attack", "Território ofensivo do Brasil (laranja) — atacantes e meias, ponderado por minutos. Ataque para a direita.")}
      {composite_fig(composites, "japao_defense", "Território defensivo do Japão (azul) — onde a defesa se concentra e onde deixa espaço. Ataque para a direita.")}
    </div>
    {"".join(f"<p>{p}</p>" for p in s_terr['paragraphs'][1:])}
    {f'<blockquote class="pull">{cronista.callout("territorio")}</blockquote>' if cronista.callout("territorio") else ""}
  </div></section>

  <section class="band" id="zonas"><div class="wrap">
    <div class="kicker">Zonas e corredores</div>
    <h2>{esc(s_zona['title'])}</h2>
    <div class="split text-first">
      <div>
        {lead_para(s_zona)}
        <div class="legend"><span><i class="dot-bra"></i>Brasil ataca</span><span><i class="dot-jpn"></i>Japão defende</span></div>
        {figure(mism_svg, "Mismatch de corredor: onde o Brasil carrega o ataque contra onde o Japão cobre a defesa (corredores espelhados).")}
      </div>
      <div class="two-fig">
        {figure(grid_bra, "Ocupação do Brasil (3×3). Ataque no topo.")}
        {figure(grid_jpn, "Ocupação do Japão (3×3).")}
      </div>
    </div>
  </div></section>

  <section class="band" id="craques"><div class="wrap">
    <div class="kicker">Radares · perfil 0–100</div>
    <h2>{esc(s_radar['title'])}</h2>
    <p class="lead">{(s_radar['paragraphs'][0] if s_radar['paragraphs'] else '')}</p>
    <div class="two-fig">
      {figure(vini_radar, f"{esc(vini_name)} — o alfa do ataque brasileiro (índices FGT, percentil da amostra).")}
      {figure(jp_radar, f"{esc(jp_name)} — a maior ameaça ofensiva do Japão.")}
    </div>
    {"".join(f"<p>{p}</p>" for p in s_radar['paragraphs'][1:])}
  </div></section>

  <section class="band" id="onze"><div class="wrap">
    <div class="kicker">Os 11 · mapa a mapa</div>
    <h2>{esc(s_onze['title'])}</h2>
    <p class="lead">{(s_onze['paragraphs'][0] if s_onze['paragraphs'] else '')}</p>
    {"".join(f"<p>{p}</p>" for p in s_onze['paragraphs'][1:])}
    {dossier_html}
    {f'<blockquote class="pull">{cronista.callout("os_onze")}</blockquote>' if cronista.callout("os_onze") else ""}
  </div></section>

  <section class="band" id="matadores"><div class="wrap">
    <div class="kicker">Eficiência · gols − xG</div>
    <h2>{esc(s_fin['title'])}</h2>
    <div class="split text-first">
      <div>{lead_para(s_fin)}</div>
      <div>{figure(eff_svg, "Gols (bola cheia) vs. xG (bola vazia). À direita do esperado = finalizador acima da média.")}</div>
    </div>
  </div></section>

  <section class="band" id="escalacao"><div class="wrap">
    <div class="kicker">Escalação recomendada · 4-3-3</div>
    <h2>{esc(s_esc['title'])}</h2>
    <div class="split text-first">
      <div>{lead_para(s_esc)}
        <div class="pills">
          <span class="pill good">Saída 3+2</span><span class="pill good">Overload na esquerda</span>
          <span class="pill good">Casemiro fixo</span><span class="pill good">Bruno virando corredor</span>
        </div>
      </div>
      <div>{figure(form_svg, "4-3-3 assimétrico com sobrecarga no corredor esquerdo de Vinícius (seta dourada).")}</div>
    </div>
  </div></section>

  <section class="band" id="banco"><div class="wrap">
    <div class="kicker">Clusters · arquétipos</div>
    <h2>{esc(s_clu['title'])}</h2>
    {lead_para(s_clu)}
    {substitutes_cards(models)}
  </div></section>

  <section class="band" id="veredito"><div class="wrap">
    <div class="kicker">O veredito</div>
    <h2>{esc(s_ver['title'])}</h2>
    {lead_para(s_ver)}
    <div class="split" style="margin-top:18px">
      <div>
        <h3 style="font-family:var(--serif);font-size:1.3rem;margin:0 0 8px">Como jogar</h3>
        <div class="pills">
          <span class="pill good">Atrair e acelerar</span><span class="pill good">1v1 de Vini</span>
          <span class="pill good">Paquetá na meia-esquerda</span><span class="pill good">Bloco médio agressivo</span>
        </div>
      </div>
      <div>
        <h3 style="font-family:var(--serif);font-size:1.3rem;margin:0 0 8px">O que não fazer</h3>
        <div class="pills">
          <span class="pill bad">Laterais altos juntos</span><span class="pill bad">Casemiro caçando ponta</span>
          <span class="pill bad">Vertical forçado por dentro</span><span class="pill bad">Cruzar sem ocupação</span>
        </div>
      </div>
    </div>
    {f'<blockquote class="pull">{cronista.callout("veredito")}</blockquote>' if cronista.callout("veredito") else ""}
    <a class="cta" href="ranking.html">Ver o ranking dos jogadores →</a>
  </div></section>

  <section class="band"><div class="wrap">
    <div class="kicker">Apêndice</div>
    <h2>Todos os heatmaps</h2>
    <details><summary>Brasil — galeria completa</summary>{_gallery(heatmaps, "brasil")}</details>
    <details><summary>Japão — galeria completa</summary>{_gallery(heatmaps, "japao")}</details>
  </div></section>

  <section class="band" id="metodo"><div class="wrap">
    <div class="kicker">Metodologia</div>
    <h2>Como a conta é feita</h2>
    <p><b>FGT Index</b>: score 0–100 por percentil com shrinkage por minutos
      (<code>score · min/(min+90) + 50 · 90/(min+90)</code>), evitando endeusar amostra curta.</p>
    <p><b>Modelo de placar</b>: Poisson exato sobre um grid de gols. O xG esperado de cada seleção é a média geométrica
      do próprio ataque (xG/jogo) e da fragilidade defensiva do adversário (xGOT sofrido/jogo) — o que tempera a inflação
      dos jogos contra adversários frágeis. Brasil λ={fmt(sim['lambda_brasil'])}, Japão λ={fmt(sim['lambda_japao'])}.</p>
    <p><b>Heatmaps compostos</b>: soma ponderada por minutos dos mapas de calor individuais, suavizada e renderizada
      sobre o gramado. <b>Zonas</b>: produto das distribuições marginais de corredor e terço (aproximação de ocupação conjunta).</p>
    <p style="font-size:.8rem;color:var(--muted)">Banco SQLite: <code>{esc(db_relative)}</code> ·
      Fonte bruta: 6 jogos da fase de grupos (3 Brasil, 3 Japão), {len(stats)} registros jogador-jogo e {len(heatmaps)} heatmaps. Gerado por Foot Game Theory.</p>
  </div></section>
</main>

<footer><div class="wrap">
  <div class="footbrand"><img src="assets/arvor_logo.png" alt="Arvor"><b>Arvor Intelligence</b> · <a href="https://arvor.co">arvor.co</a></div>
  Foot Game Theory · Dossiê Moneyball Brasil × Japão · Copa 2026 · análise data-driven com crônica.
  <a href="ranking.html">Ranking dos jogadores →</a>
</div></footer>
</body>
</html>
"""


def _gallery(heatmaps: pd.DataFrame, team: str) -> str:
    maps = heatmaps[heatmaps["team"] == team].sort_values(["player_label", "match_id"])
    cards = []
    for _, row in maps.iterrows():
        cards.append(
            "<figure>"
            f'<img src="{esc(row["asset_path"])}" alt="Heatmap {esc(row["player_label"])}" loading="lazy">'
            f'<span>{esc(row["player_label"])} · {esc(str(row["opponent"]).replace("_", " ").title())}</span>'
            "</figure>"
        )
    return f'<div class="gallery">{"".join(cards)}</div>'
