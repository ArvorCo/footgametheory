#!/usr/bin/env python3
"""Build the Brazil x Japan Moneyball report from local FotMob-style data."""

from __future__ import annotations

import csv
import math
import re
import shutil
import sqlite3
import struct
import unicodedata
import zipfile
import zlib
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from heatmap_compose import (
    build_composites,
    build_duel_composites,
    build_player_composites,
)
from home_html import render_home
from models import build_models
from ranking_html import render_ranking
from report_html import pick_starting_xi, render_report
from social_card import build_social_card
from thread_html import render_thread

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "16avos"
BUILD_DIR = ROOT / "build"
EXTRACTED_DIR = BUILD_DIR / "extracted"
DB_PATH = BUILD_DIR / "footgametheory.sqlite"
DOCS_DIR = ROOT / "docs"
ASSET_DIR = DOCS_DIR / "assets" / "heatmaps"
REPORT_PATH = DOCS_DIR / "brasil-japao-moneyball.html"
THREAD_PATH = DOCS_DIR / "brasil-japao-thread.html"
RANKING_PATH = DOCS_DIR / "ranking.html"
INDEX_PATH = DOCS_DIR / "index.html"

TEAM_LABEL = {"brasil": "Brasil", "japao": "Japão"}
ROLE_LABEL = {0: "Goleiro", 1: "Defesa", 2: "Meio", 3: "Ataque"}
LANE_LABEL = {
    "left": "corredor esquerdo",
    "center": "corredor central",
    "right": "corredor direito",
}
THIRD_LABEL = {"low": "terço baixo", "mid": "terço médio", "high": "terço alto"}

NUMERIC_COLUMNS = [
    "Shirt",
    "Position",
    "FotMob rating",
    "Minutes played",
    "Goals",
    "Assists",
    "Expected goals (xG)",
    "Expected goals on target (xGOT)",
    "Expected assists (xA)",
    "xG + xA",
    "Total shots",
    "Accurate passes",
    "Accurate passes (total)",
    "Accurate passes (%)",
    "Chances created",
    "Shots on target",
    "Shots off target",
    "Blocked shots",
    "Shot accuracy",
    "Shot accuracy (total)",
    "Shot accuracy (%)",
    "Shotmap",
    "Defensive actions",
    "Touches",
    "Touches in opposition box",
    "Successful dribbles",
    "Successful dribbles (total)",
    "Successful dribbles (%)",
    "Passes into final third",
    "Accurate crosses",
    "Accurate crosses (total)",
    "Accurate crosses (%)",
    "Accurate long balls",
    "Accurate long balls (total)",
    "Accurate long balls (%)",
    "Corners",
    "Dispossessed",
    "xG Non-penalty",
    "Tackles",
    "Blocks",
    "Clearances",
    "Headed clearance",
    "Interceptions",
    "Recoveries",
    "Dribbled past",
    "Ground duels won",
    "Ground duels won (total)",
    "Ground duels won (%)",
    "Aerial duels won",
    "Aerial duels won (total)",
    "Aerial duels won (%)",
    "Was fouled",
    "Fouls committed",
    "Duels won",
    "Duels lost",
    "Big chances created",
    "Big chances missed",
    "Offsides",
    "Saves",
    "Goals conceded",
    "xGOT faced",
    "Goals prevented",
    "Diving save",
    "Saves inside box",
    "Acted as sweeper",
    "Punches",
    "Throws",
    "High claim",
    "Last man tackle",
]

TEXT_COLUMNS = ["Player", "Goalkeeper"]


def slugify(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return text or "unknown"


def metric_name(column: str) -> str:
    if column.endswith(" (%)"):
        return slugify(column.replace(" (%)", " pct"))
    if column.endswith(" (total)"):
        return slugify(column.replace(" (total)", " total"))
    return slugify(column)


COL = {name: metric_name(name) for name in NUMERIC_COLUMNS + TEXT_COLUMNS}


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


def extract_archives() -> None:
    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
    for archive in sorted(DATA_DIR.glob("*.zip")):
        target = EXTRACTED_DIR / archive.stem
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(target)


def parse_match(path: Path) -> tuple[str, str, str]:
    match = re.match(r"(brasil|japao)_x_(.+)_estatisticas", path.stem)
    if not match:
        raise ValueError(f"Cannot infer match metadata from {path}")
    team, opponent = match.group(1), match.group(2)
    return path.stem, team, opponent


def canonical_player_key(player: object, shirt: object) -> str:
    shirt_text = ""
    if pd.notna(shirt):
        try:
            shirt_text = str(int(float(shirt)))
        except (TypeError, ValueError):
            shirt_text = str(shirt)
    return f"{slugify(player)}_{shirt_text}" if shirt_text else slugify(player)


def player_label(player: object, shirt: object) -> str:
    try:
        shirt_int = int(float(shirt))
    except (TypeError, ValueError):
        return str(player)
    return f"{player} ({shirt_int})"


def load_stats() -> pd.DataFrame:
    frames = []
    csv_paths = sorted(EXTRACTED_DIR.glob("*/*_estatisticas.csv"))
    if not csv_paths:
        raise RuntimeError("No extracted CSV files found. Check data/16avos.")

    for sequence, path in enumerate(csv_paths, start=1):
        match_id, team, opponent = parse_match(path)
        df = pd.read_csv(path, encoding="utf-8-sig")
        for col in TEXT_COLUMNS:
            if col not in df:
                df[col] = ""
        for col in NUMERIC_COLUMNS:
            if col not in df:
                df[col] = 0
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        df = df[TEXT_COLUMNS + NUMERIC_COLUMNS].copy()
        df = df.rename(columns=COL)
        df["match_id"] = match_id
        df["match_sequence"] = sequence
        df["team"] = team
        df["team_label"] = TEAM_LABEL[team]
        df["opponent"] = opponent
        df["opponent_label"] = opponent.replace("_", " ").title()
        df["source_csv"] = str(path.relative_to(ROOT))
        df["player_slug"] = df[COL["Player"]].map(slugify)
        df["player_key"] = [
            canonical_player_key(player, shirt)
            for player, shirt in zip(df[COL["Player"]], df[COL["Shirt"]])
        ]
        df["player_label"] = [
            player_label(player, shirt)
            for player, shirt in zip(df[COL["Player"]], df[COL["Shirt"]])
        ]
        df["role"] = df[COL["Position"]].map(
            lambda pos: ROLE_LABEL.get(int(pos), "Indefinido")
        )
        df["played"] = df[COL["Minutes played"]] > 0
        frames.append(df)

    return pd.concat(frames, ignore_index=True)


def read_png_rgba(path: Path) -> np.ndarray:
    raw_bytes = path.read_bytes()
    if raw_bytes[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"Not a PNG: {path}")

    pos = 8
    idat = b""
    width = height = bit_depth = color_type = None
    while pos < len(raw_bytes):
        length = struct.unpack(">I", raw_bytes[pos : pos + 4])[0]
        chunk_type = raw_bytes[pos + 4 : pos + 8]
        payload = raw_bytes[pos + 8 : pos + 8 + length]
        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, _, _, _ = struct.unpack(
                ">IIBBBBB", payload
            )
        elif chunk_type == b"IDAT":
            idat += payload
        elif chunk_type == b"IEND":
            break
        pos += 12 + length

    if bit_depth != 8 or color_type != 6:
        raise ValueError(
            f"Unsupported PNG format in {path}: bit_depth={bit_depth}, color_type={color_type}"
        )

    decompressed = zlib.decompress(idat)
    bpp = 4
    stride = int(width) * bpp
    rows = np.zeros((int(height), stride), dtype=np.uint8)
    prev = np.zeros(stride, dtype=np.uint8)
    cursor = 0
    for y in range(int(height)):
        filter_type = decompressed[cursor]
        cursor += 1
        recon = np.frombuffer(
            decompressed[cursor : cursor + stride], dtype=np.uint8
        ).copy()
        cursor += stride

        if filter_type == 1:
            for x in range(bpp, stride):
                recon[x] = (int(recon[x]) + int(recon[x - bpp])) & 255
        elif filter_type == 2:
            recon = (recon.astype(np.uint16) + prev.astype(np.uint16)).astype(np.uint8)
        elif filter_type == 3:
            for x in range(stride):
                left = int(recon[x - bpp]) if x >= bpp else 0
                up = int(prev[x])
                recon[x] = (int(recon[x]) + ((left + up) // 2)) & 255
        elif filter_type == 4:
            for x in range(stride):
                left = int(recon[x - bpp]) if x >= bpp else 0
                up = int(prev[x])
                upper_left = int(prev[x - bpp]) if x >= bpp else 0
                p = left + up - upper_left
                pa, pb, pc = abs(p - left), abs(p - up), abs(p - upper_left)
                predictor = (
                    left if pa <= pb and pa <= pc else up if pb <= pc else upper_left
                )
                recon[x] = (int(recon[x]) + predictor) & 255
        elif filter_type != 0:
            raise ValueError(f"Unsupported PNG filter {filter_type} in {path}")

        rows[y] = recon
        prev = recon.copy()

    return rows.reshape((int(height), int(width), 4))


def heat_weight(path: Path) -> np.ndarray:
    arr = read_png_rgba(path)[..., :3].astype(np.float32)
    maxc = arr.max(axis=2)
    minc = arr.min(axis=2)
    saturation = (maxc - minc) / (maxc + 1.0)
    brightness = 0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]
    warm_bias = np.maximum(0.0, arr[..., 0] - 0.55 * arr[..., 2]) / 255.0
    return (
        np.maximum(0.0, brightness - 45.0)
        * np.maximum(0.0, saturation - 0.08)
        * (0.7 + 0.6 * warm_bias)
    )


def analyze_heatmap(path: Path) -> dict[str, float]:
    weight = heat_weight(path)
    mask = weight > 3.0
    total = float(weight[mask].sum())
    h, w = weight.shape
    if total <= 0:
        return {
            "centroid_x": 0.5,
            "centroid_y": 0.5,
            "active_area": 0.0,
            "left_lane_share": 0.0,
            "center_lane_share": 0.0,
            "right_lane_share": 0.0,
            "low_third_share": 0.0,
            "mid_third_share": 0.0,
            "high_third_share": 0.0,
            "high_intensity_share": 0.0,
            "length_spread": 0.0,
            "width_spread": 0.0,
            "heat_intensity": 0.0,
        }

    yy, xx = np.indices((h, w))
    cx = float((xx[mask] * weight[mask]).sum() / total / (w - 1))
    cy = float((yy[mask] * weight[mask]).sum() / total / (h - 1))
    x_var = float((((xx[mask] / (w - 1)) - cx) ** 2 * weight[mask]).sum() / total)
    y_var = float((((yy[mask] / (h - 1)) - cy) ** 2 * weight[mask]).sum() / total)
    hot_cut = np.quantile(weight[mask], 0.85)
    return {
        "centroid_x": cx,
        "centroid_y": cy,
        "active_area": float(mask.mean()),
        "left_lane_share": float(weight[(yy < h / 3) & mask].sum() / total),
        "center_lane_share": float(
            weight[(yy >= h / 3) & (yy < 2 * h / 3) & mask].sum() / total
        ),
        "right_lane_share": float(weight[(yy >= 2 * h / 3) & mask].sum() / total),
        "low_third_share": float(weight[(xx < w / 3) & mask].sum() / total),
        "mid_third_share": float(
            weight[(xx >= w / 3) & (xx < 2 * w / 3) & mask].sum() / total
        ),
        "high_third_share": float(weight[(xx >= 2 * w / 3) & mask].sum() / total),
        "high_intensity_share": float(weight[(weight >= hot_cut) & mask].sum() / total),
        "length_spread": math.sqrt(x_var),
        "width_spread": math.sqrt(y_var),
        "heat_intensity": total / (w * h),
    }


def match_heatmap_to_player(
    stats: pd.DataFrame, match_id: str, filename: str
) -> pd.Series | None:
    base = slugify(filename.replace("_heatmap.png", ""))
    active = stats[(stats["match_id"] == match_id) & (stats["played"])].copy()
    shirt_match = re.match(r"(.+)_([0-9]+)$", base)
    if shirt_match:
        name_slug, shirt = shirt_match.group(1), int(shirt_match.group(2))
        rows = active[
            (active["player_slug"] == name_slug) & (active[COL["Shirt"]] == shirt)
        ]
        if len(rows) == 1:
            return rows.iloc[0]

    rows = active[active["player_slug"] == base]
    if len(rows) == 1:
        return rows.iloc[0]
    if len(rows) > 1:
        return rows.sort_values(COL["Minutes played"], ascending=False).iloc[0]
    return None


def collect_heatmaps(stats: pd.DataFrame) -> pd.DataFrame:
    if ASSET_DIR.exists():
        shutil.rmtree(ASSET_DIR)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    records = []
    for heatmap in sorted(EXTRACTED_DIR.glob("*/heatmaps/*_heatmap.png")):
        csv_path = next(heatmap.parents[1].glob("*_estatisticas.csv"))
        match_id, team, opponent = parse_match(csv_path)
        player_row = match_heatmap_to_player(stats, match_id, heatmap.name)
        if player_row is None:
            continue
        asset_name = f"{match_id}_{player_row['player_key']}.png"
        asset_path = ASSET_DIR / asset_name
        shutil.copyfile(heatmap, asset_path)
        features = analyze_heatmap(heatmap)
        record = {
            "match_id": match_id,
            "team": team,
            "team_label": TEAM_LABEL[team],
            "opponent": opponent,
            "player": player_row[COL["Player"]],
            "player_key": player_row["player_key"],
            "player_label": player_row["player_label"],
            "role": player_row["role"],
            "shirt": int(player_row[COL["Shirt"]]),
            "minutes_played": float(player_row[COL["Minutes played"]]),
            "source_heatmap": str(heatmap.relative_to(ROOT)),
            "asset_path": str(asset_path.relative_to(DOCS_DIR)),
        }
        record.update(features)
        records.append(record)
    return pd.DataFrame(records)


def weighted_average(group: pd.DataFrame, value: str, weight: str) -> float:
    valid = group[(group[value] > 0) & (group[weight] > 0)]
    if valid.empty:
        return 0.0
    return float((valid[value] * valid[weight]).sum() / valid[weight].sum())


def add_per90(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    out = df.copy()
    minutes = out["minutes_played"].replace(0, np.nan)
    for col in columns:
        if col in out:
            out[f"{col}90"] = (out[col] / minutes * 90).fillna(0.0)
    return out


def percentile(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
    ranked = series.astype(float).rank(method="average", pct=True) * 100
    return ranked if higher_is_better else 100 - ranked


def safe_rate(
    numerator: pd.Series, denominator: pd.Series, default: float = 0.0
) -> pd.Series:
    rate = numerator / denominator.replace(0, np.nan)
    return rate.replace([np.inf, -np.inf], np.nan).fillna(default)


def build_player_aggregates(
    stats: pd.DataFrame, heatmaps: pd.DataFrame
) -> pd.DataFrame:
    active = stats[stats["played"]].copy()
    numeric = [COL[c] for c in NUMERIC_COLUMNS if COL[c] in active.columns]
    sum_cols = [
        col
        for col in numeric
        if col not in {COL["FotMob rating"], COL["Shirt"], COL["Position"]}
        and not col.endswith("_pct")
    ]
    grouped = active.groupby(
        [
            "team",
            "team_label",
            "player_key",
            "player_label",
            COL["Player"],
            COL["Shirt"],
            COL["Position"],
            "role",
        ],
        as_index=False,
    )
    agg = grouped[sum_cols].sum()
    agg = agg.rename(columns={COL["Minutes played"]: "minutes_played"})

    ratings = (
        active.groupby("player_key")
        .apply(
            lambda g: weighted_average(g, COL["FotMob rating"], COL["Minutes played"]),
            include_groups=False,
        )
        .rename("weighted_rating")
        .reset_index()
    )
    apps = active.groupby("player_key").size().rename("appearances").reset_index()
    agg = agg.merge(ratings, on="player_key", how="left").merge(
        apps, on="player_key", how="left"
    )

    rename_map = {
        COL[c]: metric_name(c) for c in NUMERIC_COLUMNS if COL[c] in agg.columns
    }
    agg = agg.rename(columns=rename_map)
    if "minutes_played" not in agg:
        agg["minutes_played"] = agg[metric_name("Minutes played")]

    base_metrics = [
        "goals",
        "assists",
        "expected_goals_xg",
        "expected_goals_on_target_xgot",
        "expected_assists_xa",
        "xg_xa",
        "total_shots",
        "accurate_passes",
        "accurate_passes_total",
        "chances_created",
        "shots_on_target",
        "touches",
        "touches_in_opposition_box",
        "successful_dribbles",
        "successful_dribbles_total",
        "passes_into_final_third",
        "accurate_crosses",
        "accurate_crosses_total",
        "accurate_long_balls",
        "accurate_long_balls_total",
        "dispossessed",
        "defensive_actions",
        "tackles",
        "blocks",
        "clearances",
        "interceptions",
        "recoveries",
        "dribbled_past",
        "ground_duels_won",
        "ground_duels_won_total",
        "aerial_duels_won",
        "aerial_duels_won_total",
        "fouls_committed",
        "duels_won",
        "duels_lost",
        "big_chances_created",
        "big_chances_missed",
        "saves",
        "goals_conceded",
        "xgot_faced",
        "goals_prevented",
        "shot_accuracy",
        "shot_accuracy_total",
    ]
    for col in base_metrics:
        if col not in agg:
            agg[col] = 0.0

    agg["xgi"] = agg["expected_goals_xg"] + agg["expected_assists_xa"]
    agg["total_passes"] = agg["accurate_passes_total"]
    agg["inaccurate_passes"] = (agg["total_passes"] - agg["accurate_passes"]).clip(
        lower=0
    )
    agg["pass_accuracy"] = safe_rate(agg["accurate_passes"], agg["total_passes"])
    agg["pass_error_rate"] = safe_rate(agg["inaccurate_passes"], agg["total_passes"])
    agg["progressive_pass_rate"] = safe_rate(
        agg["passes_into_final_third"], agg["total_passes"]
    )
    agg["dribble_success_rate"] = safe_rate(
        agg["successful_dribbles"], agg["successful_dribbles_total"]
    )
    agg["cross_accuracy"] = safe_rate(
        agg["accurate_crosses"], agg["accurate_crosses_total"]
    )
    agg["long_ball_accuracy"] = safe_rate(
        agg["accurate_long_balls"], agg["accurate_long_balls_total"]
    )
    agg["shot_accuracy_rate"] = safe_rate(
        agg["shot_accuracy"], agg["shot_accuracy_total"]
    )
    missing_shot = agg["shot_accuracy_rate"] == 0
    agg.loc[missing_shot, "shot_accuracy_rate"] = safe_rate(
        agg.loc[missing_shot, "shots_on_target"],
        agg.loc[missing_shot, "total_shots"],
    )
    agg["ground_duel_win_rate"] = safe_rate(
        agg["ground_duels_won"], agg["ground_duels_won_total"], 0.5
    )
    agg["aerial_duel_win_rate"] = safe_rate(
        agg["aerial_duels_won"], agg["aerial_duels_won_total"], 0.5
    )
    agg["duel_win_rate"] = safe_rate(
        agg["duels_won"], agg["duels_won"] + agg["duels_lost"], 0.5
    )
    agg["retention_risk"] = safe_rate(
        agg["dispossessed"] + agg["duels_lost"], agg["touches"]
    )
    agg["pass_security_proxy"] = agg["pass_accuracy"]
    agg["shot_quality"] = safe_rate(agg["expected_goals_xg"], agg["total_shots"])
    agg = add_per90(agg, base_metrics + ["xgi", "total_passes", "inaccurate_passes"])

    if not heatmaps.empty:
        hm = heatmaps.groupby(["team", "player_key"], as_index=False).apply(
            aggregate_heatmap, include_groups=False
        )
        agg = agg.merge(hm, on=["team", "player_key"], how="left")
    for col in [
        "centroid_x",
        "centroid_y",
        "active_area",
        "left_lane_share",
        "center_lane_share",
        "right_lane_share",
        "low_third_share",
        "mid_third_share",
        "high_third_share",
        "high_intensity_share",
        "length_spread",
        "width_spread",
        "heat_intensity",
    ]:
        if col not in agg:
            agg[col] = 0.0
        agg[col] = agg[col].fillna(0.0)

    scored = score_players(agg)
    return scored.sort_values(
        ["team", "overall_index"], ascending=[True, False]
    ).reset_index(drop=True)


def aggregate_heatmap(group: pd.DataFrame) -> pd.Series:
    weights = (
        group["minutes_played"]
        .replace(0, np.nan)
        .fillna(group["heat_intensity"].clip(lower=0.001))
    )
    cols = [
        "centroid_x",
        "centroid_y",
        "active_area",
        "left_lane_share",
        "center_lane_share",
        "right_lane_share",
        "low_third_share",
        "mid_third_share",
        "high_third_share",
        "high_intensity_share",
        "length_spread",
        "width_spread",
        "heat_intensity",
    ]
    values = {col: float(np.average(group[col], weights=weights)) for col in cols}
    values["primary_lane"] = max(
        ("left", values["left_lane_share"]),
        ("center", values["center_lane_share"]),
        ("right", values["right_lane_share"]),
        key=lambda item: item[1],
    )[0]
    values["primary_third"] = max(
        ("low", values["low_third_share"]),
        ("mid", values["mid_third_share"]),
        ("high", values["high_third_share"]),
        key=lambda item: item[1],
    )[0]
    return pd.Series(values)


def weighted_index(parts: list[tuple[pd.Series, float]]) -> pd.Series:
    total_weight = sum(weight for _, weight in parts)
    result = sum(series * weight for series, weight in parts) / total_weight
    return result.clip(0, 100)


def score_players(agg: pd.DataFrame) -> pd.DataFrame:
    out = agg.copy()
    universe = out[out["minutes_played"] >= 45].copy()
    if universe.empty:
        universe = out.copy()

    def p(col: str, good: bool = True) -> pd.Series:
        if col not in universe:
            return pd.Series(50.0, index=out.index)
        values = percentile(universe[col], good)
        return (
            out["player_key"].map(dict(zip(universe["player_key"], values))).fillna(50)
        )

    out["attack_index"] = weighted_index(
        [
            (p("xgi90"), 0.25),
            (p("expected_goals_on_target_xgot90"), 0.13),
            (p("shots_on_target90"), 0.09),
            (p("shot_accuracy_rate"), 0.07),
            (p("touches_in_opposition_box90"), 0.14),
            (p("successful_dribbles90"), 0.08),
            (p("dribble_success_rate"), 0.07),
            (p("goals90"), 0.13),
            (p("assists90"), 0.07),
            (p("dispossessed90", False), 0.07),
        ]
    )
    out["creation_index"] = weighted_index(
        [
            (p("expected_assists_xa90"), 0.23),
            (p("chances_created90"), 0.22),
            (p("passes_into_final_third90"), 0.18),
            (p("progressive_pass_rate"), 0.10),
            (p("accurate_crosses90"), 0.08),
            (p("cross_accuracy"), 0.05),
            (p("accurate_long_balls90"), 0.06),
            (p("long_ball_accuracy"), 0.04),
            (p("big_chances_created90"), 0.12),
            (p("pass_accuracy"), 0.12),
        ]
    )
    out["defense_index"] = weighted_index(
        [
            (p("defensive_actions90"), 0.16),
            (p("tackles90"), 0.13),
            (p("interceptions90"), 0.13),
            (p("recoveries90"), 0.12),
            (p("blocks90"), 0.09),
            (p("clearances90"), 0.09),
            (p("ground_duels_won90"), 0.08),
            (p("aerial_duels_won90"), 0.06),
            (p("ground_duel_win_rate"), 0.06),
            (p("aerial_duel_win_rate"), 0.04),
            (p("duel_win_rate"), 0.08),
            (p("dribbled_past90", False), 0.05),
            (p("fouls_committed90", False), 0.02),
        ]
    )
    out["security_index"] = weighted_index(
        [
            (p("duel_win_rate"), 0.22),
            (p("pass_accuracy"), 0.25),
            (p("pass_error_rate", False), 0.18),
            (p("retention_risk", False), 0.18),
            (p("dispossessed90", False), 0.12),
            (p("duels_lost90", False), 0.12),
            (p("dribbled_past90", False), 0.07),
        ]
    )
    out["progression_index"] = weighted_index(
        [
            (p("passes_into_final_third90"), 0.28),
            (p("accurate_long_balls90"), 0.16),
            (p("long_ball_accuracy"), 0.08),
            (p("accurate_passes90"), 0.14),
            (p("total_passes90"), 0.10),
            (p("pass_accuracy"), 0.09),
            (p("touches90"), 0.10),
            (p("mid_third_share"), 0.09),
            (p("high_third_share"), 0.16),
        ]
    )
    out["goalkeeper_index"] = weighted_index(
        [
            (p("weighted_rating"), 0.28),
            (p("saves90"), 0.20),
            (p("goals_prevented"), 0.24),
            (p("goals_conceded90", False), 0.18),
            (p("pass_accuracy"), 0.10),
        ]
    )
    out["rating_index"] = p("weighted_rating")

    role_score = []
    for _, row in out.iterrows():
        position = int(row[COL["Position"]])
        if position == 0:
            score = (
                0.58 * row["goalkeeper_index"]
                + 0.18 * row["security_index"]
                + 0.14 * row["progression_index"]
                + 0.10 * row["rating_index"]
            )
        elif position == 1:
            score = (
                0.36 * row["defense_index"]
                + 0.24 * row["security_index"]
                + 0.20 * row["progression_index"]
                + 0.10 * row["attack_index"]
                + 0.10 * row["rating_index"]
            )
        elif position == 2:
            score = (
                0.27 * row["creation_index"]
                + 0.24 * row["defense_index"]
                + 0.19 * row["security_index"]
                + 0.15 * row["progression_index"]
                + 0.10 * row["attack_index"]
                + 0.05 * row["rating_index"]
            )
        else:
            score = (
                0.38 * row["attack_index"]
                + 0.22 * row["creation_index"]
                + 0.14 * row["defense_index"]
                + 0.12 * row["security_index"]
                + 0.14 * row["rating_index"]
            )
        reliability = float(row["minutes_played"] / (row["minutes_played"] + 90))
        role_score.append(score * reliability + 50 * (1 - reliability))

    out["overall_index"] = np.clip(role_score, 0, 100)
    return out


def build_team_tables(stats: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    active = stats[stats["played"]].copy()
    metrics = [
        COL["Minutes played"],
        COL["Goals"],
        COL["Assists"],
        COL["Expected goals (xG)"],
        COL["Expected goals on target (xGOT)"],
        COL["Expected assists (xA)"],
        COL["xG + xA"],
        COL["Total shots"],
        COL["Shots on target"],
        COL["Chances created"],
        COL["Touches"],
        COL["Touches in opposition box"],
        COL["Passes into final third"],
        COL["Accurate passes"],
        COL["Accurate passes (total)"],
        COL["Shot accuracy"],
        COL["Shot accuracy (total)"],
        COL["Successful dribbles"],
        COL["Successful dribbles (total)"],
        COL["Accurate crosses"],
        COL["Accurate crosses (total)"],
        COL["Accurate long balls"],
        COL["Accurate long balls (total)"],
        COL["Dispossessed"],
        COL["Defensive actions"],
        COL["Recoveries"],
        COL["Dribbled past"],
        COL["Ground duels won"],
        COL["Ground duels won (total)"],
        COL["Aerial duels won"],
        COL["Aerial duels won (total)"],
        COL["Duels won"],
        COL["Duels lost"],
        COL["Fouls committed"],
    ]
    team_match = active.groupby(
        ["team", "team_label", "match_id", "opponent_label"], as_index=False
    )[metrics].sum()
    team_match = team_match.rename(columns={col: metric_name(col) for col in metrics})
    team = team_match.groupby(["team", "team_label"], as_index=False).sum(
        numeric_only=True
    )
    for frame in (team_match, team):
        frame["total_passes"] = frame["accurate_passes_total"]
        frame["inaccurate_passes"] = (
            frame["total_passes"] - frame["accurate_passes"]
        ).clip(lower=0)
        frame["pass_accuracy"] = safe_rate(
            frame["accurate_passes"], frame["total_passes"]
        )
        frame["pass_error_rate"] = safe_rate(
            frame["inaccurate_passes"], frame["total_passes"]
        )
        frame["progressive_pass_rate"] = safe_rate(
            frame["passes_into_final_third"], frame["total_passes"]
        )
        frame["shot_accuracy_rate"] = safe_rate(
            frame["shot_accuracy"], frame["shot_accuracy_total"]
        )
        fallback = frame["shot_accuracy_rate"] == 0
        frame.loc[fallback, "shot_accuracy_rate"] = safe_rate(
            frame.loc[fallback, "shots_on_target"],
            frame.loc[fallback, "total_shots"],
        )
        frame["dribble_success_rate"] = safe_rate(
            frame["successful_dribbles"], frame["successful_dribbles_total"]
        )
        frame["cross_accuracy"] = safe_rate(
            frame["accurate_crosses"], frame["accurate_crosses_total"]
        )
        frame["long_ball_accuracy"] = safe_rate(
            frame["accurate_long_balls"], frame["accurate_long_balls_total"]
        )
        frame["ground_duel_win_rate"] = safe_rate(
            frame["ground_duels_won"], frame["ground_duels_won_total"], 0.5
        )
        frame["aerial_duel_win_rate"] = safe_rate(
            frame["aerial_duels_won"], frame["aerial_duels_won_total"], 0.5
        )
        frame["duel_win_rate"] = safe_rate(
            frame["duels_won"], frame["duels_won"] + frame["duels_lost"], 0.5
        )
        frame["retention_risk"] = safe_rate(
            frame["dispossessed"] + frame["duels_lost"], frame["touches"]
        )
        frame["shot_on_target_rate"] = safe_rate(
            frame["shots_on_target"], frame["total_shots"]
        )
    team = team.fillna(0)
    return team_match, team


def save_sqlite(
    stats: pd.DataFrame,
    heatmaps: pd.DataFrame,
    players: pd.DataFrame,
    team_match: pd.DataFrame,
    team: pd.DataFrame,
) -> None:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        stats.to_sql("player_match_stats", conn, if_exists="replace", index=False)
        heatmaps.to_sql("heatmap_features", conn, if_exists="replace", index=False)
        players.to_sql("player_aggregate", conn, if_exists="replace", index=False)
        team_match.to_sql("team_match_stats", conn, if_exists="replace", index=False)
        team.to_sql("team_aggregate", conn, if_exists="replace", index=False)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_stats_team_player ON player_match_stats(team, player_key)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_heatmaps_team_player ON heatmap_features(team, player_key)"
        )


def write_metric_exports(
    stats: pd.DataFrame,
    players: pd.DataFrame,
    team_match: pd.DataFrame,
    team: pd.DataFrame,
) -> None:
    analysis_dir = ROOT / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    stats.to_csv(
        analysis_dir / "player_match_stats.csv", index=False, quoting=csv.QUOTE_MINIMAL
    )
    players.to_csv(
        analysis_dir / "player_aggregate.csv", index=False, quoting=csv.QUOTE_MINIMAL
    )
    team_match.to_csv(
        analysis_dir / "team_match_stats.csv", index=False, quoting=csv.QUOTE_MINIMAL
    )
    team.to_csv(
        analysis_dir / "team_aggregate.csv", index=False, quoting=csv.QUOTE_MINIMAL
    )


def main() -> None:
    extract_archives()
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    stats = load_stats()
    heatmaps = collect_heatmaps(stats)
    players = build_player_aggregates(stats, heatmaps)
    team_match, team = build_team_tables(stats)
    save_sqlite(stats, heatmaps, players, team_match, team)
    write_metric_exports(stats, players, team_match, team)

    starters = list(pick_starting_xi(players)["player_key"])
    models = build_models(stats, players, team_match, starters)
    composites = build_composites(heatmaps)
    dossiers = models["dossiers"]
    composites.update(build_player_composites(heatmaps, list(dossiers["player_key"])))
    duel_pairs = list(zip(dossiers["player_key"], dossiers["opponent_key"]))
    composites.update(build_duel_composites(heatmaps, duel_pairs))
    build_social_card(composites)

    REPORT_PATH.write_text(
        render_report(stats, heatmaps, players, team_match, team, models, composites),
        encoding="utf-8",
    )
    THREAD_PATH.write_text(
        render_thread(players, team, models, composites),
        encoding="utf-8",
    )
    RANKING_PATH.write_text(render_ranking(players), encoding="utf-8")
    INDEX_PATH.write_text(
        render_home(models, composites, players, heatmaps), encoding="utf-8"
    )

    print(f"Wrote {REPORT_PATH.relative_to(ROOT)}")
    print(f"Wrote {THREAD_PATH.relative_to(ROOT)}")
    print(f"Wrote {RANKING_PATH.relative_to(ROOT)}")
    print(f"Wrote {INDEX_PATH.relative_to(ROOT)}")
    print(f"Wrote {DB_PATH.relative_to(ROOT)}")
    print(f"Rows: stats={len(stats)} heatmaps={len(heatmaps)} players={len(players)}")
    sim = models["simulation"]
    print(
        f"Poisson: BR {sim['p_win'] * 100:.0f}% / empate {sim['p_draw'] * 100:.0f}% / JP {sim['p_loss'] * 100:.0f}%"
    )


if __name__ == "__main__":
    main()
