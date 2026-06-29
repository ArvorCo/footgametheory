#!/usr/bin/env python3
"""Composite team/player heatmaps from the individual player heatmaps.

The raw dataset ships one positional heatmap per player per match. This module
stacks them -- weighted by minutes played -- into territory maps and renders
each over a drawn pitch. Two clarity rules make the maps legible as a scouting
tool:

* **Colour by team**: Brazil in a warm yellow-orange ramp, Japan in a cool blue
  ramp, so it is obvious whose territory you are looking at.
* **Orientation normalised**: every source map is flipped, if needed, so the
  team always attacks left -> right (detected from the goalkeeper's position).
  A confrontation map mirrors Japan so the two teams face each other on one
  pitch.

Output PNGs land in ``docs/assets/heatmaps/``.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
ASSET_DIR = DOCS_DIR / "assets" / "heatmaps"

PHASES = {
    "team": None,
    "attack": ["Ataque", "Meio"],
    "defense": ["Defesa", "Goleiro"],
}

# Colour ramps (stops + positions). Warm = Brazil, cool = Japan.
PALETTES: dict[str, tuple[list[list[int]], list[float]]] = {
    "warm": (
        [[255, 241, 170], [247, 193, 55], [237, 137, 32], [201, 74, 22]],
        [0.0, 0.40, 0.70, 1.0],
    ),
    "cool": (
        [[201, 224, 247], [96, 160, 224], [42, 95, 182], [18, 42, 104]],
        [0.0, 0.40, 0.70, 1.0],
    ),
}
PALETTE_BY_TEAM = {"brasil": "warm", "japao": "cool"}


def _intensity(img: Image.Image) -> np.ndarray:
    """Warm/saturated heat estimate per pixel, mirroring build_report.heat_weight."""
    arr = np.asarray(img.convert("RGB"), dtype=np.float32)
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


def _colormap(norm: np.ndarray, palette: str = "warm") -> np.ndarray:
    """Map normalized intensity [0,1] -> RGBA using the requested ramp."""
    stop_list, pos_list = PALETTES[palette]
    stops = np.array(stop_list, dtype=np.float32)
    positions = np.array(pos_list, dtype=np.float32)
    h, w = norm.shape
    flat = norm.reshape(-1)
    rgb = np.zeros((flat.size, 3), dtype=np.float32)
    for i in range(len(stops) - 1):
        lo, hi = positions[i], positions[i + 1]
        mask = (flat >= lo) & (flat <= hi)
        t = (flat[mask] - lo) / max(1e-6, hi - lo)
        rgb[mask] = stops[i] * (1 - t)[:, None] + stops[i + 1] * t[:, None]
    alpha = np.clip((flat - 0.10) / 0.90, 0.0, 1.0) ** 0.85 * 225.0
    rgba = np.concatenate([rgb, alpha[:, None]], axis=1)
    return rgba.reshape(h, w, 4).astype(np.uint8)


def _arrow(
    draw: ImageDraw.ImageDraw, y: int, w: int, color: tuple, to_right: bool
) -> None:
    """A thin attack-direction arrow across the top of the pitch."""
    x0, x1 = (
        (int(w * 0.40), int(w * 0.60)) if to_right else (int(w * 0.60), int(w * 0.40))
    )
    draw.line([x0, y, x1, y], fill=color, width=3)
    head = 9 if to_right else -9
    draw.polygon([(x1, y), (x1 - head, y - 6), (x1 - head, y + 6)], fill=color)


def _draw_pitch(size: tuple[int, int], direction: str = "right") -> Image.Image:
    w, h = size
    pitch = Image.new("RGBA", size, (12, 60, 36, 255))
    draw = ImageDraw.Draw(pitch)
    for i in range(0, w, w // 14):  # mowing stripes
        if (i // (w // 14)) % 2 == 0:
            draw.rectangle([i, 0, i + w // 14, h], fill=(14, 68, 41, 255))
    line = (255, 255, 255, 70)
    draw.rectangle([6, 6, w - 6, h - 6], outline=line, width=2)
    draw.line([w // 2, 6, w // 2, h - 6], fill=line, width=2)
    draw.ellipse(
        [w // 2 - 70, h // 2 - 70, w // 2 + 70, h // 2 + 70], outline=line, width=2
    )
    box_h = int(h * 0.55)
    draw.rectangle(
        [6, (h - box_h) // 2, int(w * 0.16), (h + box_h) // 2], outline=line, width=2
    )
    draw.rectangle(
        [int(w * 0.84), (h - box_h) // 2, w - 6, (h + box_h) // 2],
        outline=line,
        width=2,
    )
    if direction == "right":
        _arrow(draw, 22, w, (255, 255, 255, 150), to_right=True)
    elif direction == "confronto":
        _arrow(draw, 20, w, (247, 193, 55, 220), to_right=True)  # Brazil →
        _arrow(draw, h - 20, w, (96, 160, 224, 220), to_right=False)  # Japan ←
    return pitch


def _canonical_flips(heatmaps: pd.DataFrame) -> dict[str, bool]:
    """Per match: True if the source maps must be flipped so the team attacks
    left -> right. Detected from the goalkeeper's horizontal centroid (own goal
    should sit on the left); robust to feeds that mirror the pitch."""
    flips: dict[str, bool] = {}
    for match_id, grp in heatmaps.groupby("match_id"):
        gk = grp[grp["role"] == "Goleiro"]
        ref = gk if not gk.empty else grp
        flips[str(match_id)] = float(ref["centroid_x"].mean()) > 0.5
    return flips


def _stack(
    items: list[tuple[Path, float, bool, bool]], size: tuple[int, int]
) -> np.ndarray | None:
    """Accumulate minutes-weighted intensity. ``lr`` flips left-right (fix attack
    direction); ``ud`` flips up-down. lr+ud together = a 180 turn, used to make
    an opponent face the other way (a real head-to-head)."""
    acc = np.zeros((size[1], size[0]), dtype=np.float32)
    used = 0
    for path, weight, lr, ud in items:
        if not path.exists():
            continue
        img = Image.open(path)
        if img.size != size:
            img = img.resize(size)
        heat = _intensity(img)
        if lr:
            heat = np.fliplr(heat)
        if ud:
            heat = np.flipud(heat)
        acc += heat * weight
        used += 1
    if used == 0 or acc.max() <= 0:
        return None
    return acc


def _norm(acc: np.ndarray, blur: int) -> np.ndarray:
    scaled = (acc / acc.max() * 255.0).astype(np.uint8)
    blurred = np.asarray(
        Image.fromarray(scaled, mode="L").filter(ImageFilter.GaussianBlur(blur)),
        dtype=np.float32,
    )
    return np.clip(blurred / (float(np.quantile(blurred, 0.997)) or 1.0), 0.0, 1.0)


def _render(
    acc: np.ndarray,
    size: tuple[int, int],
    out_path: Path,
    blur: int = 14,
    palette: str = "warm",
    direction: str = "right",
) -> Path:
    """Smooth, colour-ramp and composite one heat layer over a drawn pitch."""
    overlay = Image.fromarray(_colormap(_norm(acc, blur), palette), mode="RGBA")
    out = Image.alpha_composite(_draw_pitch(size, direction), overlay)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    out.convert("RGB").save(out_path, "PNG")
    return out_path


def _items_for(
    subset: pd.DataFrame, flips: dict[str, bool], mirror: bool = False
) -> list:
    """Build stack items. ``mirror`` turns the maps 180 (lr+ud) so the team or
    player faces the opposite way -- for confrontation/duel frames."""
    return [
        (
            ROOT / row["source_heatmap"],
            max(1.0, float(row["minutes_played"])),
            flips.get(str(row["match_id"]), False) ^ mirror,
            mirror,
        )
        for _, row in subset.iterrows()
    ]


def compose_team(
    heatmaps: pd.DataFrame, team: str, phase: str, size: tuple[int, int] = (1050, 680)
) -> Path | None:
    roles = PHASES[phase]
    subset = heatmaps[heatmaps["team"] == team].copy()
    if roles is not None:
        subset = subset[subset["role"].isin(roles)]
    if subset.empty:
        return None
    acc = _stack(_items_for(subset, _canonical_flips(heatmaps)), size)
    if acc is None:
        return None
    return _render(
        acc,
        size,
        ASSET_DIR / f"composite_{team}_{phase}.png",
        blur=14,
        palette=PALETTE_BY_TEAM[team],
    )


def compose_player(
    heatmaps: pd.DataFrame, player_key: str, size: tuple[int, int] = (1050, 680)
) -> Path | None:
    """Clean territory map for one player, stacked across his matches."""
    subset = heatmaps[heatmaps["player_key"] == player_key]
    if subset.empty:
        return None
    team = str(subset.iloc[0]["team"])
    acc = _stack(_items_for(subset, _canonical_flips(heatmaps)), size)
    if acc is None:
        return None
    return _render(
        acc,
        size,
        ASSET_DIR / f"player_{player_key}.png",
        blur=18,
        palette=PALETTE_BY_TEAM.get(team, "warm"),
    )


def _smooth(acc: np.ndarray, blur: int) -> np.ndarray:
    scaled = (acc / acc.max() * 255.0).astype(np.uint8)
    return np.asarray(
        Image.fromarray(scaled, mode="L").filter(ImageFilter.GaussianBlur(blur)),
        dtype=np.float32,
    )


def _control_map(
    acc_warm: np.ndarray,
    acc_cool: np.ndarray,
    out_path: Path,
    size: tuple[int, int],
    blur: int = 16,
) -> Path:
    """Paint each pixel with whichever side (warm vs cool) occupies it more.
    One colour per pixel -> no muddy overlap. Both sides share a scale so the
    comparison is fair."""
    sa, sb = _smooth(acc_warm, blur), _smooth(acc_cool, blur)
    shared = max(float(np.quantile(sa, 0.997)), float(np.quantile(sb, 0.997))) or 1.0
    na, nb = np.clip(sa / shared, 0, 1), np.clip(sb / shared, 0, 1)
    warm = _colormap(na, "warm").astype(np.int16)
    cool = _colormap(nb, "cool").astype(np.int16)
    rgba = np.where((na >= nb)[..., None], warm, cool).astype(np.uint8)
    out = Image.alpha_composite(
        _draw_pitch(size, direction="confronto"), Image.fromarray(rgba, mode="RGBA")
    )
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    out.convert("RGB").save(out_path, "PNG")
    return out_path


def compose_confrontation(
    heatmaps: pd.DataFrame, size: tuple[int, int] = (1050, 680)
) -> Path | None:
    """Team territory-control map: Brazil (warm, attacks right) vs Japan (cool,
    turned 180 to attack left). Shows which side of the pitch each team owns."""
    flips = _canonical_flips(heatmaps)
    acc_br = _stack(_items_for(heatmaps[heatmaps["team"] == "brasil"], flips), size)
    acc_jp = _stack(
        _items_for(heatmaps[heatmaps["team"] == "japao"], flips, mirror=True), size
    )
    if acc_br is None or acc_jp is None:
        return None
    return _control_map(acc_br, acc_jp, ASSET_DIR / "composite_confrontation.png", size)


def compose_duel(
    heatmaps: pd.DataFrame,
    brasil_key: str,
    japao_key: str,
    size: tuple[int, int] = (1050, 680),
) -> Path | None:
    """One pitch for a single matchup: the Brazilian (warm, attacks right) vs his
    Japanese opponent (cool, turned 180 to face him). Their flanks line up."""
    flips = _canonical_flips(heatmaps)
    br = heatmaps[heatmaps["player_key"] == brasil_key]
    jp = heatmaps[heatmaps["player_key"] == japao_key]
    if br.empty or jp.empty:
        return None
    acc_br = _stack(_items_for(br, flips), size)
    acc_jp = _stack(_items_for(jp, flips, mirror=True), size)
    if acc_br is None or acc_jp is None:
        return None
    return _control_map(
        acc_br, acc_jp, ASSET_DIR / f"duel_{brasil_key}.png", size, blur=20
    )


def build_composites(heatmaps: pd.DataFrame) -> dict[str, str]:
    """Render team x phase composites + the confrontation map; return docs paths."""
    produced: dict[str, str] = {}
    for team in ("brasil", "japao"):
        for phase in PHASES:
            path = compose_team(heatmaps, team, phase)
            if path is not None:
                produced[f"{team}_{phase}"] = str(path.relative_to(DOCS_DIR))
    confronto = compose_confrontation(heatmaps)
    if confronto is not None:
        produced["confrontation"] = str(confronto.relative_to(DOCS_DIR))
    return produced


def build_player_composites(
    heatmaps: pd.DataFrame, player_keys: list[str]
) -> dict[str, str]:
    """Render one clean territory map per requested player; {player_key: docs path}."""
    produced: dict[str, str] = {}
    for key in player_keys:
        path = compose_player(heatmaps, key)
        if path is not None:
            produced[key] = str(path.relative_to(DOCS_DIR))
    return produced


def build_duel_composites(
    heatmaps: pd.DataFrame, pairs: list[tuple[str, str]]
) -> dict[str, str]:
    """Render a duel map per (brasil_key, japao_key); keyed ``duel_<brasil_key>``."""
    produced: dict[str, str] = {}
    for br_key, jp_key in pairs:
        if not br_key or not jp_key:
            continue
        path = compose_duel(heatmaps, br_key, jp_key)
        if path is not None:
            produced[f"duel_{br_key}"] = str(path.relative_to(DOCS_DIR))
    return produced
