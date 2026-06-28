from __future__ import annotations

import html
import math

import pandas as pd


LANE_LABEL = {"left": "corredor esquerdo", "center": "corredor central", "right": "corredor direito"}
THIRD_LABEL = {"low": "terço baixo", "mid": "terço médio", "high": "terço alto"}
POSITION_COL = "position"
RATE_FIELDS = {
    "pass_accuracy",
    "pass_error_rate",
    "progressive_pass_rate",
    "shot_accuracy_rate",
    "dribble_success_rate",
    "cross_accuracy",
    "long_ball_accuracy",
    "ground_duel_win_rate",
    "aerial_duel_win_rate",
    "duel_win_rate",
    "retention_risk",
    "shot_on_target_rate",
}


def pct(value: float, digits: int = 1) -> str:
    return f"{100 * value:.{digits}f}%"


def fmt(value: object, digits: int = 2) -> str:
    if value is None:
        return "-"
    try:
        val = float(value)
    except (TypeError, ValueError):
        return str(value)
    if math.isnan(val):
        return "-"
    if abs(val - round(val)) < 1e-9:
        return f"{int(round(val))}"
    return f"{val:.{digits}f}"


def signed_fmt(value: float, digits: int = 2) -> str:
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.{digits}f}"


def html_escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def bar(value: float, max_value: float, label: str = "") -> str:
    width = 0 if max_value <= 0 else max(2, min(100, value / max_value * 100))
    return f'<div class="bar" title="{html_escape(label)}"><span style="width:{width:.1f}%"></span></div>'


def index_text(value: object) -> str:
    return f"{fmt(value, 1)}%"


def player_table(df: pd.DataFrame, team: str, limit: int = 12) -> str:
    cols = [
        ("player_label", "Jogador"),
        ("role", "Função"),
        ("minutes_played", "Min"),
        ("overall_index", "FGT %"),
        ("attack_index", "Ataque %"),
        ("creation_index", "Criação %"),
        ("defense_index", "Defesa %"),
        ("security_index", "Segurança %"),
        ("xgi90", "xGI/90"),
        ("pass_accuracy", "Passe %"),
        ("total_passes90", "Passes/90"),
        ("inaccurate_passes90", "Erros/90"),
        ("dribble_success_rate", "Drible %"),
        ("duel_win_rate", "Duelos %"),
    ]
    rows = []
    for _, row in df[df["team"] == team].head(limit).iterrows():
        cells = []
        for key, label in cols:
            val = row[key]
            if key.endswith("_index") or key == "overall_index":
                cells.append(f"<td><strong>{index_text(val)}</strong>{bar(float(val), 100, label)}</td>")
            elif key in RATE_FIELDS:
                cells.append(f"<td>{pct(float(val), 1)}</td>")
            elif key == "player_label":
                cells.append(f"<td><strong>{html_escape(val)}</strong></td>")
            else:
                cells.append(f"<td>{html_escape(fmt(val, 2))}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    header = "".join(f"<th>{html_escape(label)}</th>" for _, label in cols)
    return f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def team_comparison(team: pd.DataFrame) -> str:
    metrics = [
        ("goals", "Gols"),
        ("expected_goals_xg", "xG"),
        ("expected_assists_xa", "xA"),
        ("total_shots", "Finalizações"),
        ("shots_on_target", "No alvo"),
        ("shot_accuracy_rate", "Chute no alvo %"),
        ("chances_created", "Chances criadas"),
        ("touches_in_opposition_box", "Toques na área"),
        ("total_passes", "Passes totais"),
        ("pass_accuracy", "Passe certo %"),
        ("inaccurate_passes", "Passes errados"),
        ("pass_error_rate", "Erro de passe %"),
        ("passes_into_final_third", "Passes ao terço final"),
        ("progressive_pass_rate", "Terço final/pass %"),
        ("successful_dribbles", "Dribles certos"),
        ("dribble_success_rate", "Drible %"),
        ("accurate_crosses", "Cruzamentos certos"),
        ("cross_accuracy", "Cruzamento %"),
        ("accurate_long_balls", "Bolas longas certas"),
        ("long_ball_accuracy", "Bola longa %"),
        ("dispossessed", "Desarmes sofridos"),
        ("defensive_actions", "Ações defensivas"),
        ("dribbled_past", "Driblado"),
        ("ground_duel_win_rate", "Duelos chão %"),
        ("aerial_duel_win_rate", "Duelos aéreos %"),
        ("duel_win_rate", "% duelos vencidos"),
    ]
    b = team[team["team"] == "brasil"].iloc[0]
    j = team[team["team"] == "japao"].iloc[0]
    rows = []
    for key, label in metrics:
        bv, jv = float(b[key]), float(j[key])
        maxv = max(bv, jv)
        if key in RATE_FIELDS:
            btext, jtext = pct(bv), pct(jv)
            edge_text = signed_fmt((bv - jv) * 100, 1) + " p.p."
        else:
            btext, jtext = fmt(bv), fmt(jv)
            edge_text = signed_fmt(bv - jv, 2)
        rows.append(
            "<tr>"
            f"<td>{html_escape(label)}</td>"
            f"<td><strong>{btext}</strong>{bar(bv, maxv, 'Brasil')}</td>"
            f"<td><strong>{jtext}</strong>{bar(jv, maxv, 'Japão')}</td>"
            f"<td>{html_escape(edge_text)}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>Métrica</th><th>Brasil</th><th>Japão</th><th>Edge BR</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def pick_starting_xi(players: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    brazil = players[players["team"] == "brasil"].copy()
    gk = brazil[brazil[POSITION_COL] == 0].sort_values("overall_index", ascending=False).head(1)
    defenders = brazil[brazil[POSITION_COL] == 1].sort_values("overall_index", ascending=False).head(4)
    midfield = brazil[brazil[POSITION_COL] == 2].sort_values("overall_index", ascending=False).head(3)
    forwards = brazil[brazil[POSITION_COL] == 3].sort_values("overall_index", ascending=False).head(3)
    xi = pd.concat([gk, defenders, midfield, forwards]).drop_duplicates("player_key")
    return "4-3-3 assimétrico", xi


def selected_table(xi: pd.DataFrame) -> str:
    rows = []
    for _, row in xi.sort_values([POSITION_COL, "overall_index"], ascending=[True, False]).iterrows():
        rows.append(
            "<tr>"
            f"<td><strong>{html_escape(row['player_label'])}</strong></td>"
            f"<td>{html_escape(row['role'])}</td>"
            f"<td>{fmt(row['minutes_played'])}</td>"
            f"<td>{fmt(row['weighted_rating'], 2)}</td>"
            f"<td><strong>{index_text(row['overall_index'])}</strong>{bar(float(row['overall_index']), 100)}</td>"
            f"<td>{pct(float(row['pass_accuracy']), 1)}</td>"
            f"<td>{pct(float(row['duel_win_rate']), 1)}</td>"
            f"<td>{html_escape(LANE_LABEL.get(row.get('primary_lane', ''), '-'))}</td>"
            f"<td>{html_escape(THIRD_LABEL.get(row.get('primary_third', ''), '-'))}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>Titular</th><th>Função</th><th>Min</th><th>Rating</th><th>FGT</th><th>Passe</th><th>Duelos</th><th>Mapa</th><th>Altura</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def heatmap_cards(heatmaps: pd.DataFrame, players: pd.DataFrame, team: str, keys: list[str]) -> str:
    cards = []
    for key in keys:
        maps = heatmaps[(heatmaps["team"] == team) & (heatmaps["player_key"] == key)].copy()
        if maps.empty:
            continue
        player = players[players["player_key"] == key].iloc[0]
        best = maps.sort_values("minutes_played", ascending=False).iloc[0]
        cards.append(
            '<article class="heat-card">'
            f'<img src="{html_escape(best["asset_path"])}" alt="Heatmap {html_escape(best["player_label"])}">'
            f'<h4>{html_escape(best["player_label"])}</h4>'
            f'<p>{html_escape(best["match_id"].replace("_", " "))}: {fmt(best["minutes_played"])} min. '
            f'{html_escape(LANE_LABEL.get(player.get("primary_lane", ""), "zona indefinida"))}, '
            f'{html_escape(THIRD_LABEL.get(player.get("primary_third", ""), "altura indefinida"))}.</p>'
            "</article>"
        )
    return '<div class="heat-grid">' + "".join(cards) + "</div>"


def all_heatmap_details(heatmaps: pd.DataFrame, team: str) -> str:
    cards = []
    maps = heatmaps[heatmaps["team"] == team].sort_values(["player_label", "match_id"])
    for _, row in maps.iterrows():
        cards.append(
            '<article class="mini-heat">'
            f'<img src="{html_escape(row["asset_path"])}" alt="Heatmap {html_escape(row["player_label"])}">'
            f'<span>{html_escape(row["player_label"])}</span>'
            f'<small>{html_escape(row["opponent"].replace("_", " ").title())}</small>'
            "</article>"
        )
    return '<div class="mini-grid">' + "".join(cards) + "</div>"


def insight_list(players: pd.DataFrame, team: pd.DataFrame) -> dict[str, object]:
    brazil = players[players["team"] == "brasil"].sort_values("overall_index", ascending=False)
    japan = players[players["team"] == "japao"].sort_values("overall_index", ascending=False)
    br_team = team[team["team"] == "brasil"].iloc[0]
    jp_team = team[team["team"] == "japao"].iloc[0]
    return {
        "br_best": brazil.head(5),
        "jp_threats": japan.head(5),
        "br_top_attack": brazil.sort_values("attack_index", ascending=False).head(4),
        "jp_top_attack": japan.sort_values("attack_index", ascending=False).head(4),
        "br_def_risk": brazil[(brazil[POSITION_COL] != 0)].sort_values(["security_index", "dribbled_past90"], ascending=[True, False]).head(4),
        "br_team": br_team,
        "jp_team": jp_team,
    }


def narrative(players: pd.DataFrame, team: pd.DataFrame) -> dict[str, str]:
    info = insight_list(players, team)
    br = info["br_team"]
    jp = info["jp_team"]
    best = info["br_best"].iloc[0]
    threat = info["jp_threats"].iloc[0]
    attack = info["br_top_attack"].iloc[0]
    japan_attack = info["jp_top_attack"].iloc[0]
    dribbled_delta = float(br["dribbled_past"] - jp["dribbled_past"])
    duel_delta = float(br["duel_win_rate"] - jp["duel_win_rate"])
    pass_delta = float(br["pass_accuracy"] - jp["pass_accuracy"])
    prog_delta = float(br["progressive_pass_rate"] - jp["progressive_pass_rate"])

    return {
        "headline": (
            f"O Brasil tem o melhor jogador da amostra em {html_escape(best['player_label'])}, "
            f"mas o Japão tem ameaça real em {html_escape(threat['player_label'])}. "
            "Com os campos novos, o recado ficou mais claro: Brasil controla melhor a bola; Japão progride mais direto."
        ),
        "moneyball": (
            f"O Brasil tentou {fmt(br['total_passes'])} passes e acertou {pct(float(br['pass_accuracy']))}; "
            f"o Japão tentou {fmt(jp['total_passes'])} e acertou {pct(float(jp['pass_accuracy']))} "
            f"({signed_fmt(pass_delta * 100, 1)} p.p. para o Brasil). "
            f"Só que o Japão leva {pct(float(jp['progressive_pass_rate']))} dos passes ao terço final contra "
            f"{pct(float(br['progressive_pass_rate']))} do Brasil ({signed_fmt(prog_delta * 100, 1)} p.p. BR). "
            "Moral: controlar posse não basta; tem que matar a transição japonesa na origem."
        ),
        "risk": (
            f"No contato, Brasil ainda tem edge: {pct(float(br['duel_win_rate']))} dos duelos contra "
            f"{pct(float(jp['duel_win_rate']))} do Japão ({signed_fmt(duel_delta * 100, 1)} p.p.). "
            f"O ponto ruim é ter sido driblado {fmt(br['dribbled_past'])} vezes contra "
            f"{fmt(jp['dribbled_past'])} do Japão ({signed_fmt(dribbled_delta, 0)}). "
            f"O Japão também dribla com {pct(float(jp['dribble_success_rate']))} de sucesso contra "
            f"{pct(float(br['dribble_success_rate']))} do Brasil. Essa porra é o alerta defensivo."
        ),
        "attack": (
            f"O plano ofensivo deve começar por {html_escape(attack['player_label'])}: "
            f"{fmt(attack['xgi90'], 2)} xGI/90, {fmt(attack['touches_in_opposition_box90'], 2)} toques na área/90 "
            f"e índice ofensivo {fmt(attack['attack_index'], 1)}. "
            "A ideia é acelerar o primeiro passe vertical, atrair o lateral japonês e atacar o intervalo lateral-zagueiro."
        ),
        "defense": (
            f"O Japão mais perigoso aparece em {html_escape(japan_attack['player_label'])}, "
            f"com {fmt(japan_attack['xgi90'], 2)} xGI/90 e mapa de calor agressivo. "
            "Casemiro não pode ser arrastado para longe da zona 14; o encaixe certo é volante protegendo e zagueiro antecipando, não perseguição burra."
        ),
    }


def render_report(stats: pd.DataFrame, heatmaps: pd.DataFrame, players: pd.DataFrame, team_match: pd.DataFrame, team: pd.DataFrame, db_relative: str = "build/footgametheory.sqlite") -> str:
    formation, xi = pick_starting_xi(players)
    texts = narrative(players, team)
    brazil = players[players["team"] == "brasil"].sort_values("overall_index", ascending=False)
    japan = players[players["team"] == "japao"].sort_values("overall_index", ascending=False)
    br = team[team["team"] == "brasil"].iloc[0]
    jp = team[team["team"] == "japao"].iloc[0]
    vini_pool = brazil[brazil["player_key"] == "vinicius_junior_7"]
    vini = vini_pool.iloc[0] if not vini_pool.empty else brazil.sort_values("attack_index", ascending=False).iloc[0]

    br_keys = list(brazil.head(6)["player_key"])
    jp_keys = list(japan.head(6)["player_key"])
    sub_candidates = brazil[~brazil["player_key"].isin(xi["player_key"])].head(7)
    weak_brazil = brazil[(brazil[POSITION_COL] != 0)].sort_values(["security_index", "weighted_rating"]).head(5)

    sub_rows = "".join(
        "<tr>"
        f"<td><strong>{html_escape(row['player_label'])}</strong></td>"
        f"<td>{html_escape(row['role'])}</td>"
        f"<td>{index_text(row['overall_index'])}</td>"
        f"<td>{index_text(row['attack_index'])}</td>"
        f"<td>{index_text(row['creation_index'])}</td>"
        f"<td>{index_text(row['defense_index'])}</td>"
        f"<td>{pct(float(row['pass_accuracy']), 1)}</td>"
        f"<td>{pct(float(row['dribble_success_rate']), 1)}</td>"
        f"<td>{fmt(row['xgi90'], 2)}</td>"
        "</tr>"
        for _, row in sub_candidates.iterrows()
    )

    weak_rows = "".join(
        "<tr>"
        f"<td><strong>{html_escape(row['player_label'])}</strong></td>"
        f"<td>{html_escape(row['role'])}</td>"
        f"<td>{fmt(row['weighted_rating'], 2)}</td>"
        f"<td>{index_text(row['security_index'])}</td>"
        f"<td>{pct(float(row['pass_error_rate']), 1)}</td>"
        f"<td>{fmt(row['inaccurate_passes90'], 2)}</td>"
        f"<td>{fmt(row['retention_risk'], 3)}</td>"
        f"<td>{fmt(row['dribbled_past90'], 2)}</td>"
        f"<td>{fmt(row['duels_lost90'], 2)}</td>"
        "</tr>"
        for _, row in weak_brazil.iterrows()
    )

    pass_brazil = brazil[brazil["minutes_played"] >= 45].sort_values("total_passes", ascending=False).head(8)
    pass_rows = "".join(
        "<tr>"
        f"<td><strong>{html_escape(row['player_label'])}</strong></td>"
        f"<td>{fmt(row['total_passes'])}</td>"
        f"<td>{pct(float(row['pass_accuracy']), 1)}</td>"
        f"<td>{fmt(row['inaccurate_passes'])}</td>"
        f"<td>{fmt(row['passes_into_final_third'])}</td>"
        f"<td>{pct(float(row['progressive_pass_rate']), 1)}</td>"
        f"<td>{pct(float(row['long_ball_accuracy']), 1)}</td>"
        "</tr>"
        for _, row in pass_brazil.iterrows()
    )

    japan_progress = japan[japan["minutes_played"] >= 45].sort_values(
        ["passes_into_final_third90", "xgi90"], ascending=False
    ).head(8)
    japan_progress_rows = "".join(
        "<tr>"
        f"<td><strong>{html_escape(row['player_label'])}</strong></td>"
        f"<td>{html_escape(row['role'])}</td>"
        f"<td>{fmt(row['passes_into_final_third90'], 2)}</td>"
        f"<td>{pct(float(row['progressive_pass_rate']), 1)}</td>"
        f"<td>{fmt(row['xgi90'], 2)}</td>"
        f"<td>{pct(float(row['dribble_success_rate']), 1)}</td>"
        f"<td>{pct(float(row['pass_accuracy']), 1)}</td>"
        "</tr>"
        for _, row in japan_progress.iterrows()
    )

    match_rows = "".join(
        "<tr>"
        f"<td>{html_escape(row['team_label'])}</td>"
        f"<td>{html_escape(row['opponent_label'])}</td>"
        f"<td>{fmt(row['goals'])}</td>"
        f"<td>{fmt(row['expected_goals_xg'])}</td>"
        f"<td>{fmt(row['expected_assists_xa'])}</td>"
        f"<td>{fmt(row['total_shots'])}</td>"
        f"<td>{fmt(row['total_passes'])}</td>"
        f"<td>{pct(float(row['pass_accuracy']), 1)}</td>"
        f"<td>{pct(float(row['progressive_pass_rate']), 1)}</td>"
        f"<td>{fmt(row['chances_created'])}</td>"
        f"<td>{fmt(row['defensive_actions'])}</td>"
        "</tr>"
        for _, row in team_match.sort_values(["team", "match_id"]).iterrows()
    )

    generated = "28 de junho de 2026"
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Brasil x Japão | Laudo Moneyball</title>
  <style>
    :root {{
      --ink: #f6f0df;
      --muted: #c6c0ad;
      --paper: #11130f;
      --panel: #191c15;
      --panel-2: #20251d;
      --line: #3a4032;
      --canary: #f2c94c;
      --green: #30d158;
      --blue: #63d2ff;
      --red: #ff6b57;
      --white: #fffaf0;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font-family: Avenir Next, Optima, Candara, Segoe UI, sans-serif;
      line-height: 1.55;
    }}
    body::before {{
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      opacity: .24;
      background:
        linear-gradient(90deg, transparent 0 8.1%, rgba(255,255,255,.045) 8.2% 8.35%, transparent 8.45%),
        linear-gradient(0deg, transparent 0 49.8%, rgba(255,255,255,.05) 49.9% 50.1%, transparent 50.2%);
      background-size: 160px 160px, 100% 100%;
    }}
    header {{
      min-height: 76vh;
      display: grid;
      align-items: end;
      padding: 48px clamp(18px, 5vw, 72px);
      border-bottom: 1px solid var(--line);
      background:
        linear-gradient(rgba(17,19,15,.30), rgba(17,19,15,.92)),
        url("assets/heatmaps/brasil_x_escocia_estatisticas_vinicius_junior_7.png") center / cover no-repeat;
    }}
    .hero {{ max-width: 1120px; }}
    .kicker {{ color: var(--canary); text-transform: uppercase; letter-spacing: .16em; font-size: 12px; font-weight: 800; }}
    h1 {{
      font-family: Georgia, Cambria, serif;
      font-size: clamp(42px, 7vw, 104px);
      line-height: .9;
      margin: 14px 0 22px;
      letter-spacing: 0;
      max-width: 1040px;
    }}
    .lead {{ font-size: clamp(18px, 2vw, 26px); max-width: 900px; color: var(--white); }}
    main {{ padding: 34px clamp(16px, 4vw, 64px) 72px; }}
    section {{ max-width: 1260px; margin: 0 auto 54px; overflow-x: auto; }}
    h2 {{ font-family: Georgia, Cambria, serif; font-size: clamp(30px, 4vw, 56px); margin: 0 0 18px; letter-spacing: 0; }}
    h3 {{ margin: 0 0 12px; font-size: 20px; color: var(--canary); }}
    h4 {{ margin: 12px 0 4px; }}
    p {{ color: var(--muted); max-width: 980px; }}
    .grid {{ display: grid; gap: 16px; grid-template-columns: repeat(4, minmax(0, 1fr)); }}
    .card, .note, .recommendation {{
      background: color-mix(in srgb, var(--panel) 94%, black);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
    }}
    .metric {{ font-size: 34px; font-weight: 900; color: var(--white); }}
    .label {{ color: var(--muted); font-size: 13px; text-transform: uppercase; letter-spacing: .08em; }}
    .two {{ display: grid; grid-template-columns: 1.1fr .9fr; gap: 22px; align-items: start; }}
    .three {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }}
    table {{ width: 100%; min-width: 860px; border-collapse: collapse; overflow: hidden; border: 1px solid var(--line); border-radius: 8px; }}
    th, td {{ padding: 10px 12px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }}
    th {{ color: var(--canary); font-size: 12px; text-transform: uppercase; letter-spacing: .08em; background: var(--panel-2); }}
    td {{ color: var(--ink); font-size: 14px; }}
    tr:last-child td {{ border-bottom: 0; }}
    .bar {{ height: 6px; background: #30362a; border-radius: 99px; overflow: hidden; margin-top: 5px; }}
    .bar span {{ display: block; height: 100%; background: linear-gradient(90deg, var(--green), var(--canary)); }}
    .heat-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }}
    .heat-card, .mini-heat {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }}
    .heat-card img, .mini-heat img {{ display: block; width: 100%; height: auto; background: #0b0d09; }}
    .heat-card h4, .heat-card p {{ padding: 0 14px; }}
    .heat-card p {{ font-size: 13px; margin-top: 0; }}
    details {{ border: 1px solid var(--line); border-radius: 8px; padding: 14px; background: var(--panel); }}
    summary {{ cursor: pointer; color: var(--canary); font-weight: 800; }}
    .mini-grid {{ display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 10px; margin-top: 14px; }}
    .mini-heat span, .mini-heat small {{ display: block; padding: 0 8px; }}
    .mini-heat span {{ font-size: 12px; font-weight: 800; margin-top: 6px; }}
    .mini-heat small {{ color: var(--muted); font-size: 11px; margin-bottom: 7px; }}
    .pill {{ display: inline-block; border: 1px solid var(--line); border-radius: 999px; padding: 4px 9px; margin: 3px 5px 3px 0; color: var(--white); background: #23291f; }}
    .callout {{ border-left: 5px solid var(--canary); padding-left: 18px; font-size: 19px; color: var(--white); }}
    .red {{ color: var(--red); }}
    .green {{ color: var(--green); }}
    .small {{ font-size: 12px; color: var(--muted); }}
    @media (max-width: 980px) {{
      .grid, .three, .two, .heat-grid {{ grid-template-columns: 1fr; }}
      .mini-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      header {{ min-height: 68vh; }}
      td, th {{ font-size: 12px; padding: 8px; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="hero">
      <div class="kicker">Laudo tático-estatístico | Copa do Mundo | Brasil x Japão</div>
      <h1>Moneyball para ganhar a segunda-feira.</h1>
      <p class="lead">{texts["headline"]}</p>
      <p class="small">Gerado em {generated}. Dados: 6 CSVs e {len(heatmaps)} heatmaps extraídos de <code>data/16avos</code>. Partida referenciada no pedido: segunda-feira, 29 de junho de 2026.</p>
    </div>
  </header>

  <main>
    <section>
      <div class="grid">
        <div class="card"><div class="label">xG Brasil</div><div class="metric">{fmt(br["expected_goals_xg"])}</div><p>Contra {fmt(jp["expected_goals_xg"])} do Japão.</p></div>
        <div class="card"><div class="label">Passe certo Brasil</div><div class="metric">{pct(float(br["pass_accuracy"]))}</div><p>{fmt(br["total_passes"])} passes tentados; Japão ficou em {pct(float(jp["pass_accuracy"]))}.</p></div>
        <div class="card"><div class="label">Progressão Japão</div><div class="metric red">{pct(float(jp["progressive_pass_rate"]))}</div><p>Share de passes ao terço final; Brasil teve {pct(float(br["progressive_pass_rate"]))}.</p></div>
        <div class="card"><div class="label">Escalação modelo</div><div class="metric">{formation}</div><p>Pressão seletiva, lado esquerdo agressivo, volante segurando zona 14.</p></div>
      </div>
    </section>

    <section class="two">
      <div>
        <h2>Diagnóstico Cru</h2>
        <p class="callout">{texts["moneyball"]}</p>
        <p>{texts["risk"]}</p>
        <p>{texts["attack"]}</p>
        <p>{texts["defense"]}</p>
      </div>
      <div class="note">
        <h3>Upgrade de dados</h3>
        <p>Agora o CSV traz denominadores e percentuais: passes totais, passe certo %, chute %, drible %, cruzamento %, bola longa %, duelos no chão % e duelos aéreos %. O modelo recalcula os percentuais agregados por numerador/denominador, não soma porcentagens.</p>
        <p>Os heatmaps são imagens, não tracking bruto. O algoritmo mede pixels saturados/brilhantes para estimar centro de atividade, corredor dominante e terço dominante.</p>
      </div>
    </section>

    <section>
      <h2>Brasil x Japão: Tabela De Edge</h2>
      {team_comparison(team)}
    </section>

    <section>
      <h2>Escalação Recomendada</h2>
      <p>Modelo: <strong>{formation}</strong>. A escalação abaixo maximiza índice FGT com confiabilidade por minutos, sem ignorar função. Danilo entra porque a amostra brasileira tem pouca alternativa natural de lateral direito; a compensação é tática, não fé.</p>
      {selected_table(xi)}
    </section>

    <section class="two">
      <div>
        <h2>Circulação Brasileira</h2>
        <p>Quem carrega a estabilidade de passe e onde nasce a progressão. Aqui já estamos usando passe total real e erro real.</p>
        <table><thead><tr><th>Jogador</th><th>Passes</th><th>Passe %</th><th>Errados</th><th>Terço final</th><th>Prog/pass %</th><th>Bola longa %</th></tr></thead><tbody>{pass_rows}</tbody></table>
      </div>
      <div>
        <h2>Progressão Japonesa</h2>
        <p>Esses são os gatilhos para cortar: passe ao terço final, xGI e drible. Se eles recebem limpos, vira jogo de faca.</p>
        <table><thead><tr><th>Jogador</th><th>Função</th><th>Terço/90</th><th>Prog/pass %</th><th>xGI/90</th><th>Drible %</th><th>Passe %</th></tr></thead><tbody>{japan_progress_rows}</tbody></table>
      </div>
    </section>

    <section class="three">
      <div class="recommendation">
        <h3>Plano Ofensivo</h3>
        <p><strong>Overload no lado de Vinícius.</strong> Atrair bloco japonês, acelerar com Bruno/Paquetá e atacar o intervalo entre lateral e zagueiro. Vini é o alfa: {fmt(vini["xgi90"], 2)} xGI/90, {fmt(vini["touches_in_opposition_box90"], 2)} toques na área/90 e {pct(float(vini["pass_accuracy"]), 1)} nos passes.</p>
      </div>
      <div class="recommendation">
        <h3>Plano Defensivo</h3>
        <p><strong>Não abrir a zona 14.</strong> Kamada, Nakamura e Ueda vivem de receber entre linhas e finalizar rápido. Casemiro deve proteger, não caçar. Zagueiro antecipa, lateral fecha diagonal.</p>
      </div>
      <div class="recommendation">
        <h3>Banco Inteligente</h3>
        <p><strong>Rayan/Raphinha/Neymar/Endrick conforme cenário.</strong> Se o Japão baixar, entra 1v1 e chute. Se o Brasil estiver ganhando, entra fôlego para pressionar saída e proteger corredor.</p>
      </div>
    </section>

    <section>
      <h2>Top Brasil: Índice FGT</h2>
      {player_table(players, "brasil", 14)}
    </section>

    <section>
      <h2>Ameaças Do Japão</h2>
      {player_table(players, "japao", 14)}
    </section>

    <section>
      <h2>Melhores Substitutos Do Brasil</h2>
      <table><thead><tr><th>Jogador</th><th>Função</th><th>FGT</th><th>Ataque</th><th>Criação</th><th>Defesa</th><th>Passe %</th><th>Drible %</th><th>xGI/90</th></tr></thead><tbody>{sub_rows}</tbody></table>
    </section>

    <section>
      <h2>Pontos Fracos A Mitigar</h2>
      <p>Não é para queimar jogador; é para não fingir que risco não existe. Estes são os perfis brasileiros com menor segurança contextual na amostra.</p>
      <table><thead><tr><th>Jogador</th><th>Função</th><th>Rating</th><th>Segurança</th><th>Erro passe %</th><th>Erro/90</th><th>Risco posse</th><th>Driblado/90</th><th>Duelos perdidos/90</th></tr></thead><tbody>{weak_rows}</tbody></table>
    </section>

    <section>
      <h2>Heatmaps-Chave: Brasil</h2>
      {heatmap_cards(heatmaps, players, "brasil", br_keys)}
    </section>

    <section>
      <h2>Heatmaps-Chave: Japão</h2>
      {heatmap_cards(heatmaps, players, "japao", jp_keys)}
    </section>

    <section>
      <h2>Resumo Por Jogo</h2>
      <table><thead><tr><th>Time</th><th>Adversário</th><th>Gols</th><th>xG</th><th>xA</th><th>Chutes</th><th>Passes</th><th>Passe %</th><th>Prog/pass %</th><th>Chances</th><th>Ações def.</th></tr></thead><tbody>{match_rows}</tbody></table>
    </section>

    <section class="two">
      <div>
        <h2>Como Jogar</h2>
        <p><span class="pill">Saída 3+2</span><span class="pill">Vini isolado no 1v1</span><span class="pill">Paquetá atacando meia-esquerda</span><span class="pill">Bruno virando corredor</span><span class="pill">Casemiro fixo</span></p>
        <p>Com bola, o Brasil deve formar uma saída 3+2: um lateral mais baixo, Gabriel/Marquinhos abrindo, Casemiro e Bruno dando linha. O alvo é tirar o Japão do centro e gerar 1v1 no corredor forte. Sem bola, bloco médio agressivo: gatilho de pressão quando o Japão tocar para lateral de costas ou volante pressionado.</p>
      </div>
      <div>
        <h2>O Que Não Fazer</h2>
        <p><span class="pill red">Laterais simultaneamente altos</span><span class="pill red">Casemiro perseguindo ponta</span><span class="pill red">Passe vertical forçado por dentro</span><span class="pill red">Cruzamento sem ocupação</span></p>
        <p>O Japão pune bagunça mais do que domina território. O Brasil não pode transformar superioridade técnica em transição defensiva suicida. Perdeu a bola no lado forte? Cinco segundos de contra-pressão ou falta tática longe da área.</p>
      </div>
    </section>

    <section>
      <h2>Todos Os Heatmaps</h2>
      <details>
        <summary>Brasil: abrir galeria completa</summary>
        {all_heatmap_details(heatmaps, "brasil")}
      </details>
      <br>
      <details>
        <summary>Japão: abrir galeria completa</summary>
        {all_heatmap_details(heatmaps, "japao")}
      </details>
    </section>

    <section>
      <h2>Modelo Matemático</h2>
      <p>O FGT Index é um score 0-100 com percentis e shrinkage bayesiano simples por minutos: <code>score_final = score_funcao * min/(min+90) + 50 * 90/(min+90)</code>. Isso evita endeusar jogador de 8 minutos e punir injustamente reserva sem amostra.</p>
      <p>Componentes: ataque (xGI/90, xGOT/90, chutes no alvo, chute %, toques na área, dribles e drible %), criação (xA/90, chances, passes ao terço final, progressão/pass %, cruzamento %, bola longa %), defesa (ações defensivas, tackles, interceptações, recuperações, duelos no chão %, duelos aéreos %), segurança (passe %, erro de passe %, perdas, duelos perdidos, driblado), progressão e goleiro.</p>
      <p class="small">Banco SQLite: <code>{html_escape(str(db_relative))}</code>. Tabelas: <code>player_match_stats</code>, <code>player_aggregate</code>, <code>team_match_stats</code>, <code>team_aggregate</code>, <code>heatmap_features</code>.</p>
    </section>
  </main>
</body>
</html>
"""
