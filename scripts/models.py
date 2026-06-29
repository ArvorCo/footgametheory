#!/usr/bin/env python3
"""Advanced analytical models for the Brazil x Japan Moneyball dossier.

This module sits on top of the aggregates produced by ``build_report.py`` and
adds the layer that turns a pile of tables into a scouting argument:

* a Poisson scoreline model (win/draw/loss probabilities and likely results);
* finishing efficiency (goals vs. expected goals);
* six-axis player radars (0-100, comparable across the sample);
* corridor mismatches (where Brazil attacks vs. where Japan is thin);
* 3x3 zone-occupation grids per team (territory maps);
* role clusters (statistical archetypes, for like-for-like substitutes).

Every function is pure: it takes DataFrames and returns DataFrames/dicts. The
``build_models`` orchestrator persists the outputs to ``analysis/*.csv`` and to
new SQLite tables so the HTML builders can read a single source of truth.
"""

from __future__ import annotations

import math
import sqlite3
from pathlib import Path
from typing import cast

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_DIR = ROOT / "analysis"
DB_PATH = ROOT / "build" / "footgametheory.sqlite"

LANES = ["left", "center", "right"]
THIRDS = ["low", "mid", "high"]
LANE_LABEL = {"left": "Esquerda", "center": "Centro", "right": "Direita"}
THIRD_LABEL = {"low": "Defesa", "mid": "Meio", "high": "Ataque"}

# Six radar axes reused from the FGT index family (already 0-100 percentiles).
RADAR_AXES = [
    ("attack_index", "Ataque"),
    ("creation_index", "Criação"),
    ("progression_index", "Progressão"),
    ("defense_index", "Defesa"),
    ("security_index", "Segurança"),
    ("rating_index", "Nota"),
]

CLUSTER_FEATURES = [
    "attack_index",
    "creation_index",
    "progression_index",
    "defense_index",
    "security_index",
]


def percentile(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
    ranked = series.astype(float).rank(method="average", pct=True) * 100
    return ranked if higher_is_better else 100 - ranked


# --------------------------------------------------------------------------- #
# Poisson scoreline model
# --------------------------------------------------------------------------- #
def _team_goal_rates(
    stats: pd.DataFrame, team_match: pd.DataFrame
) -> dict[str, dict[str, float]]:
    """Attack (xG for) and defence (xGOT faced) per game, per team.

    Attack uses expected goals scored; defence uses the expected goals on
    target the goalkeepers faced, which is the cleanest concession proxy we
    have without opponent event data.
    """
    rates: dict[str, dict[str, float]] = {}
    keepers = stats[(stats["position"] == 0) & (stats["minutes_played"] > 0)]
    for team in ("brasil", "japao"):
        matches = team_match[team_match["team"] == team]
        n_games = max(1, matches["match_id"].nunique())
        xg_for = float(matches["expected_goals_xg"].sum()) / n_games
        team_keepers = keepers[keepers["team"] == team]
        xgot_against = float(team_keepers["xgot_faced"].sum()) / n_games
        goals_against = float(team_keepers["goals_conceded"].sum()) / n_games
        rates[team] = {
            "n_games": n_games,
            "xg_for_pg": xg_for,
            "xgot_against_pg": xgot_against,
            "goals_against_pg": goals_against,
        }
    return rates


def poisson_simulation(
    stats: pd.DataFrame,
    team_match: pd.DataFrame,
    max_goals: int = 8,
) -> dict[str, object]:
    """Exact Poisson model for Brazil x Japan.

    Each team's expected goals in the tie is the geometric mean of its own
    attacking output and the opponent's concession rate -- this tempers the
    inflation from weak group-stage opponents (Haiti, Tunisia) by folding in
    how leaky each defence actually was. The joint scoreline distribution is
    computed exactly over a goal grid (no sampling) for reproducibility.
    """
    rates = _team_goal_rates(stats, team_match)
    br, jp = rates["brasil"], rates["japao"]

    lam_br = math.sqrt(max(br["xg_for_pg"], 1e-6) * max(jp["xgot_against_pg"], 1e-6))
    lam_jp = math.sqrt(max(jp["xg_for_pg"], 1e-6) * max(br["xgot_against_pg"], 1e-6))

    def pmf(lam: float) -> np.ndarray:
        ks = np.arange(0, max_goals + 1)
        probs = np.exp(-lam) * lam**ks / np.array([math.factorial(k) for k in ks])
        probs[-1] += max(0.0, 1.0 - probs.sum())  # absorb the tail in the last bin
        return probs

    p_br, p_jp = pmf(lam_br), pmf(lam_jp)
    grid = np.outer(p_br, p_jp)  # grid[i, j] = P(Brasil i x j Japao)

    p_win = float(np.tril(grid, -1).sum())  # i > j
    p_draw = float(np.trace(grid))
    p_loss = float(np.triu(grid, 1).sum())  # i < j
    total = p_win + p_draw + p_loss
    p_win, p_draw, p_loss = p_win / total, p_draw / total, p_loss / total

    scorelines = [
        {"brasil": i, "japao": j, "prob": float(grid[i, j])}
        for i in range(max_goals + 1)
        for j in range(max_goals + 1)
    ]
    scorelines.sort(key=lambda s: s["prob"], reverse=True)
    top = scorelines[:6]
    most_likely = top[0]

    return {
        "lambda_brasil": lam_br,
        "lambda_japao": lam_jp,
        "p_win": p_win,
        "p_draw": p_draw,
        "p_loss": p_loss,
        "exp_goals_brasil": lam_br,
        "exp_goals_japao": lam_jp,
        "p_brasil_clean_sheet": float(p_jp[0]),
        "p_japao_clean_sheet": float(p_br[0]),
        "p_over_2_5": float(
            sum(
                grid[i, j]
                for i in range(max_goals + 1)
                for j in range(max_goals + 1)
                if i + j >= 3
            )
        ),
        "top_scorelines": top,
        "most_likely": most_likely,
        "rates": rates,
    }


def poisson_frame(sim: dict[str, object]) -> pd.DataFrame:
    """Flatten the simulation into a tidy one-row-per-metric frame for export."""
    rows = [
        ("lambda_brasil", sim["lambda_brasil"]),
        ("lambda_japao", sim["lambda_japao"]),
        ("p_vitoria_brasil", sim["p_win"]),
        ("p_empate", sim["p_draw"]),
        ("p_vitoria_japao", sim["p_loss"]),
        ("p_brasil_clean_sheet", sim["p_brasil_clean_sheet"]),
        ("p_japao_clean_sheet", sim["p_japao_clean_sheet"]),
        ("p_over_2_5", sim["p_over_2_5"]),
    ]
    for rank, sc in enumerate(cast(list, sim["top_scorelines"]), start=1):
        rows.append(
            (
                f"placar_top{rank}",
                f"{sc['brasil']}-{sc['japao']} ({sc['prob'] * 100:.1f}%)",
            )
        )
    return pd.DataFrame(rows, columns=["metric", "value"])


# --------------------------------------------------------------------------- #
# Finishing efficiency
# --------------------------------------------------------------------------- #
def finishing_efficiency(players: pd.DataFrame) -> pd.DataFrame:
    """Goals minus expected goals, plus shot quality, for outfield scorers."""
    out = players.copy()
    out["goals_minus_xg"] = out["goals"] - out["expected_goals_xg"]
    out["finishing_ratio"] = np.where(
        out["expected_goals_xg"] > 0.2,
        out["goals"] / out["expected_goals_xg"].replace(0, np.nan),
        np.nan,
    )
    cols = [
        "team",
        "team_label",
        "player_key",
        "player_label",
        "role",
        "minutes_played",
        "goals",
        "expected_goals_xg",
        "goals_minus_xg",
        "finishing_ratio",
        "shot_quality",
        "total_shots",
    ]
    cols = [c for c in cols if c in out.columns]
    eff = out[out["total_shots"] >= 2][cols].copy()
    return eff.sort_values("goals_minus_xg", ascending=False).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Player radars
# --------------------------------------------------------------------------- #
def player_radars(players: pd.DataFrame) -> pd.DataFrame:
    """Six-axis 0-100 profile per player (>= 45 minutes)."""
    cols = [
        "team",
        "team_label",
        "player_key",
        "player_label",
        "role",
        "minutes_played",
    ]
    cols += [axis for axis, _ in RADAR_AXES]
    frame = players[players["minutes_played"] >= 45][cols].copy()
    return frame.reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Corridor mismatches and zone grids
# --------------------------------------------------------------------------- #
def _weighted_lane_profile(group: pd.DataFrame) -> dict[str, float]:
    weights = group["minutes_played"].clip(lower=1.0)
    profile = {}
    for lane in LANES:
        col = f"{lane}_lane_share"
        profile[lane] = (
            float(np.average(group[col], weights=weights)) if col in group else 0.0
        )
    total = sum(profile.values()) or 1.0
    return {lane: profile[lane] / total for lane in LANES}


def _weighted_third_profile(group: pd.DataFrame) -> dict[str, float]:
    weights = group["minutes_played"].clip(lower=1.0)
    profile = {}
    for third in THIRDS:
        col = f"{third}_third_share"
        profile[third] = (
            float(np.average(group[col], weights=weights)) if col in group else 0.0
        )
    total = sum(profile.values()) or 1.0
    return {third: profile[third] / total for third in THIRDS}


def corridor_mismatches(players: pd.DataFrame) -> pd.DataFrame:
    """Where Brazil attacks vs. where Japan defends, by corridor.

    Brazil's attacking footprint is the corridor profile of its forwards and
    midfielders; Japan's defensive footprint is the corridor profile of its
    defenders and midfielders weighted toward their own half. The mismatch is
    Brazil's attacking share minus Japan's defensive coverage in that lane:
    positive means a corridor Brazil loads that Japan under-protects.

    Corridors are mirrored: Brazil's left attack meets Japan's defensive right,
    so Japan's lanes are flipped before comparison.
    """
    br = players[(players["team"] == "brasil") & (players["minutes_played"] >= 45)]
    jp = players[(players["team"] == "japao") & (players["minutes_played"] >= 45)]
    br_att = br[br["role"].isin(["Ataque", "Meio"])]
    jp_def = jp[jp["role"].isin(["Defesa", "Meio"])]

    br_lanes = _weighted_lane_profile(br_att)
    jp_lanes_raw = _weighted_lane_profile(jp_def)
    mirror = {"left": "right", "center": "center", "right": "left"}
    jp_lanes = {lane: jp_lanes_raw[mirror[lane]] for lane in LANES}

    rows = []
    for lane in LANES:
        rows.append(
            {
                "lane": lane,
                "lane_label": LANE_LABEL[lane],
                "brasil_attack_share": br_lanes[lane],
                "japao_defense_share": jp_lanes[lane],
                "mismatch": br_lanes[lane] - jp_lanes[lane],
            }
        )
    return (
        pd.DataFrame(rows)
        .sort_values("mismatch", ascending=False)
        .reset_index(drop=True)
    )


def zone_grid(players: pd.DataFrame, team: str) -> pd.DataFrame:
    """3x3 territory grid (lane x third) for a team.

    Only marginal lane/third shares are available, so the joint cell is their
    minutes-weighted outer product -- an approximation of where the team lives
    on the pitch. Cells sum to ~1.
    """
    group = players[(players["team"] == team) & (players["minutes_played"] >= 45)]
    lanes = _weighted_lane_profile(group)
    thirds = _weighted_third_profile(group)
    rows = []
    for third in THIRDS:
        for lane in LANES:
            rows.append(
                {
                    "team": team,
                    "third": third,
                    "lane": lane,
                    "value": thirds[third] * lanes[lane],
                }
            )
    return pd.DataFrame(rows)


def zone_grids(players: pd.DataFrame) -> pd.DataFrame:
    return pd.concat(
        [zone_grid(players, "brasil"), zone_grid(players, "japao")], ignore_index=True
    )


# --------------------------------------------------------------------------- #
# Role clusters
# --------------------------------------------------------------------------- #
def role_clusters(players: pd.DataFrame, k: int = 4, seed: int = 42) -> pd.DataFrame:
    """KMeans archetypes over the index profile; names from the dominant axis."""
    frame = players[players["minutes_played"] >= 45].copy()
    feats = frame[CLUSTER_FEATURES].fillna(50.0).to_numpy()
    if len(frame) < k:
        frame["cluster"] = 0
        frame["archetype"] = "Amostra curta"
        cols = [
            "team",
            "team_label",
            "player_key",
            "player_label",
            "role",
            "cluster",
            "archetype",
        ]
        return frame[cols].reset_index(drop=True)

    scaled = StandardScaler().fit_transform(feats)
    labels = KMeans(n_clusters=k, random_state=seed, n_init="auto").fit_predict(scaled)
    frame["cluster"] = labels

    axis_name = {
        "attack_index": "Finalizador",
        "creation_index": "Criador",
        "progression_index": "Construtor",
        "defense_index": "Destruidor",
        "security_index": "Cofre",
    }
    centers = frame.groupby("cluster")[CLUSTER_FEATURES].mean()
    cluster_archetype = {
        cl: axis_name[centers.loc[cl].idxmax()] for cl in centers.index
    }
    frame["archetype"] = frame["cluster"].map(cluster_archetype)
    cols = [
        "team",
        "team_label",
        "player_key",
        "player_label",
        "role",
        "cluster",
        "archetype",
    ]
    cols += CLUSTER_FEATURES
    return frame[cols].sort_values(["cluster", "team"]).reset_index(drop=True)


# Players unavailable for selection (injuries, suspensions).
UNAVAILABLE = {"raphinha_11"}


def _sub_trait(cand: pd.Series) -> str:
    """A short, position-aware use-case for bringing this player off the bench."""
    pos = int(cand["position"])
    if pos == 1:
        return "Recompõe a defesa"
    if pos == 2:
        return (
            "Equilíbrio e proteção"
            if float(cand["defense_index"]) >= float(cand["creation_index"])
            else "Fôlego na criação"
        )
    if str(cand.get("primary_lane")) == "center" or float(cand["xgi90"]) >= 0.7:
        return "Referência de área"
    if float(cand.get("dribble_success_rate", 0)) >= 0.3:
        return "1v1 e velocidade"
    return "Fôlego no ataque"


def impact_subs(
    players: pd.DataFrame, starters: list[str], max_subs: int = 6
) -> pd.DataFrame:
    """Sensible bench options: same position (and corridor when possible) as the
    starter they relieve. Goalkeepers are never swapped; unavailable players are
    excluded. Each starter is relieved at most once."""
    br = players[
        (players["team"] == "brasil")
        & (players["minutes_played"] >= 45)
        & (~players["player_key"].isin(UNAVAILABLE))
    ].copy()
    starters_df = br[br["player_key"].isin(starters)]
    bench = br[(~br["player_key"].isin(starters)) & (br["position"] != 0)].sort_values(
        "overall_index", ascending=False
    )

    used: set[str] = set()
    rows = []
    for _, cand in bench.iterrows():
        pool = starters_df[
            (starters_df["position"] == cand["position"])
            & (~starters_df["player_key"].isin(used))
        ]
        if pool.empty:
            continue
        same_lane = pool[pool["primary_lane"] == cand["primary_lane"]]
        target = (
            same_lane.sort_values("overall_index").iloc[0]
            if not same_lane.empty
            else pool.sort_values("overall_index").iloc[0]
        )
        used.add(str(target["player_key"]))
        strength = max(STRENGTH_AXES, key=lambda a: float(cand.get(a[0], 0)))
        rows.append(
            {
                "starter": _short(target["player_label"]),
                "substitute": _short(cand["player_label"]),
                "role": cand["role"],
                "trait": _sub_trait(cand),
                "reason": f"{strength[1]} {int(round(float(cand[strength[0]])))} · {float(cand['xgi90']):.2f} xGI/90",
            }
        )
        if len(rows) >= max_subs:
            break
    order = {"Ataque": 0, "Meio": 1, "Defesa": 2}
    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values("role", key=lambda s: s.map(order)).reset_index(drop=True)
    return out


# --------------------------------------------------------------------------- #
# Per-player dossiers: opponent, weakness, strategy
# --------------------------------------------------------------------------- #
WEAKNESS_METRICS = [
    ("inaccurate_passes", "Erra muito passe", True),
    ("dribbled_past90", "É driblado com facilidade", True),
    ("retention_risk", "Perde a posse", True),
    ("duel_win_rate", "Perde duelos", False),
]
STRENGTH_AXES = [
    ("attack_index", "Ataque"),
    ("creation_index", "Criação"),
    ("progression_index", "Progressão"),
    ("defense_index", "Defesa"),
    ("security_index", "Segurança"),
]


def _short(label: object) -> str:
    return str(label).split("(")[0].strip()


def _pick_opponent(brazil_row: pd.Series, jp: pd.DataFrame) -> pd.Series | None:
    """Map a Brazilian player to the Japanese player he most likely faces."""
    pos = int(brazil_row["position"])
    lane = str(brazil_row.get("primary_lane", "center"))

    def top(frame: pd.DataFrame, by: str = "attack_index") -> pd.Series | None:
        return (
            frame.sort_values(by, ascending=False).iloc[0] if not frame.empty else None
        )

    def pick(*cands: pd.Series | None) -> pd.Series | None:
        for c in cands:
            if c is not None:
                return c
        return None

    fwd = jp[jp["position"] == 3]
    mid = jp[jp["position"] == 2]
    dfd = jp[jp["position"] == 1]
    wing_left = fwd[fwd["primary_lane"] == "left"]
    wing_right = fwd[fwd["primary_lane"] == "right"]
    strikers = fwd[fwd["primary_lane"] == "center"]
    fb_left = dfd[dfd["primary_lane"] == "left"]
    fb_right = dfd[dfd["primary_lane"] == "right"]
    cbs = dfd[dfd["primary_lane"] == "center"]

    if pos == 0:  # GK faces the striker who presses
        return pick(top(strikers), top(fwd))
    if pos == 1:  # defender
        if lane == "left":  # left-back vs Japan right winger
            return pick(top(wing_right), top(fwd))
        if lane == "right":  # right-back vs Japan left winger
            return pick(top(wing_left), top(fwd))
        return pick(top(strikers), top(fwd))  # center-back vs striker
    if pos == 2:  # midfielder
        if lane == "center":  # holder vs the creator (#10)
            return pick(top(mid, "xgi90"), top(mid))
        return pick(top(mid), top(fwd))
    # forward: attacks the opposing full-back / center-back
    if lane == "left":
        return pick(top(fb_right), top(dfd))
    if lane == "right":
        return pick(top(fb_left), top(dfd))
    return pick(top(cbs), top(dfd))


def player_dossiers(players: pd.DataFrame) -> pd.DataFrame:
    """One scouting row per Brazilian regular: stats, weakness, opponent, strength."""
    br = players[
        (players["team"] == "brasil") & (players["minutes_played"] >= 45)
    ].copy()
    jp = players[
        (players["team"] == "japao") & (players["minutes_played"] >= 45)
    ].copy()

    # team-relative risk percentiles (higher = worse) stored as columns
    for col, _, higher_bad in WEAKNESS_METRICS:
        if col in br:
            br[f"{col}__rk"] = percentile(br[col], higher_is_better=higher_bad)

    # build the starting XI (4-3-3); rows retain the risk-rank columns
    def line(pos: int, n: int) -> pd.DataFrame:
        return (
            br[br["position"] == pos]
            .sort_values("overall_index", ascending=False)
            .head(n)
        )

    xi = pd.concat([line(0, 1), line(1, 4), line(2, 3), line(3, 3)])

    rows = []
    for order, (_, p) in enumerate(xi.iterrows()):
        # A dimension only counts as a weakness if it crosses an absolute concern
        # threshold (so a high-volume passer with a great rate is not flagged).
        triggered = {
            "inaccurate_passes": float(p["pass_error_rate"]) >= 0.12,
            "dribbled_past90": float(p["dribbled_past90"]) >= 1.0,
            "retention_risk": float(p["retention_risk"]) >= 0.10,
            "duel_win_rate": float(p["duel_win_rate"]) <= 0.50,
        }
        worst_col, worst_pctl = None, -1.0
        for col, _, _ in WEAKNESS_METRICS:
            rk = f"{col}__rk"
            if triggered.get(col) and rk in p and float(p[rk]) > worst_pctl:
                worst_pctl, worst_col = float(p[rk]), col

        if worst_col is None:  # no real brecha — the player is a rock
            wlabel = "Sólido — sem brecha clara"
            wval = f"{p['duel_win_rate'] * 100:.0f}% de duelos · {p['pass_accuracy'] * 100:.0f}% de passe"
        else:
            wlabel = next(lbl for c, lbl, _ in WEAKNESS_METRICS if c == worst_col)
            if worst_col == "inaccurate_passes":
                wval = f"{int(p['inaccurate_passes'])} passes errados ({p['pass_error_rate'] * 100:.0f}%)"
            elif worst_col == "dribbled_past90":
                wval = f"{p['dribbled_past90']:.1f} dribles sofridos/90"
            elif worst_col == "retention_risk":
                wval = f"{p['retention_risk'] * 100:.0f}% de perda por toque"
            else:
                wval = f"só {p['duel_win_rate'] * 100:.0f}% de duelos ganhos"

        strength = max(STRENGTH_AXES, key=lambda a: float(p.get(a[0], 0)))
        opp = _pick_opponent(p, jp)
        opp_label = _short(opp["player_label"]) if opp is not None else "—"
        opp_key = str(opp["player_key"]) if opp is not None else ""
        opp_role = str(opp["role"]) if opp is not None else ""
        opp_threat = (
            f"{opp['xgi90']:.2f} xGI/90 · {opp['dribble_success_rate'] * 100:.0f}% drible"
            if opp is not None
            else ""
        )

        rows.append(
            {
                "order": order,
                "player_key": p["player_key"],
                "player_label": p["player_label"],
                "name": _short(p["player_label"]),
                "shirt": int(p["shirt"]) if pd.notna(p.get("shirt")) else 0,
                "role": p["role"],
                "position": int(p["position"]),
                "minutes": int(p["minutes_played"]),
                "rating": round(float(p["weighted_rating"]), 1),
                "fgt": round(float(p["overall_index"])),
                "pass_accuracy": float(p["pass_accuracy"]),
                "inaccurate_passes": int(p["inaccurate_passes"]),
                "dribbled_past90": float(p["dribbled_past90"]),
                "retention_risk": float(p["retention_risk"]),
                "xgi90": float(p["xgi90"]),
                "duel_win_rate": float(p["duel_win_rate"]),
                "primary_lane": p.get("primary_lane", "center"),
                "primary_third": p.get("primary_third", "mid"),
                "weakness_label": wlabel,
                "weakness_value": wval,
                "strength_label": strength[1],
                "strength_value": round(float(p[strength[0]])),
                "opponent": opp_label,
                "opponent_key": opp_key,
                "opponent_role": opp_role,
                "opponent_threat": opp_threat,
            }
        )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def build_models(
    stats: pd.DataFrame,
    players: pd.DataFrame,
    team_match: pd.DataFrame,
    starters: list[str] | None = None,
) -> dict[str, object]:
    """Compute every model, persist CSV + SQLite tables, return a results dict."""
    sim = poisson_simulation(stats, team_match)
    efficiency = finishing_efficiency(players)
    radars = player_radars(players)
    mismatches = corridor_mismatches(players)
    grids = zone_grids(players)
    clusters = role_clusters(players)
    subs = impact_subs(players, starters or [])
    dossiers = player_dossiers(players)

    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    poisson_frame(sim).to_csv(ANALYSIS_DIR / "match_simulation.csv", index=False)
    efficiency.to_csv(ANALYSIS_DIR / "finishing_efficiency.csv", index=False)
    radars.to_csv(ANALYSIS_DIR / "player_radar.csv", index=False)
    mismatches.to_csv(ANALYSIS_DIR / "matchups.csv", index=False)
    grids.to_csv(ANALYSIS_DIR / "zone_grid.csv", index=False)
    clusters.to_csv(ANALYSIS_DIR / "clusters.csv", index=False)
    dossiers.to_csv(ANALYSIS_DIR / "player_dossiers.csv", index=False)

    if DB_PATH.exists():
        with sqlite3.connect(DB_PATH) as conn:
            poisson_frame(sim).to_sql(
                "match_simulation", conn, if_exists="replace", index=False
            )
            efficiency.to_sql(
                "finishing_efficiency", conn, if_exists="replace", index=False
            )
            radars.to_sql("player_radar", conn, if_exists="replace", index=False)
            mismatches.to_sql("matchups", conn, if_exists="replace", index=False)
            grids.to_sql("zone_grid", conn, if_exists="replace", index=False)
            clusters.to_sql("clusters", conn, if_exists="replace", index=False)
            dossiers.to_sql("player_dossiers", conn, if_exists="replace", index=False)

    return {
        "simulation": sim,
        "efficiency": efficiency,
        "radars": radars,
        "mismatches": mismatches,
        "zone_grids": grids,
        "clusters": clusters,
        "substitutes": subs,
        "dossiers": dossiers,
    }
