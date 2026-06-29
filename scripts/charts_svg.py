#!/usr/bin/env python3
"""Inline SVG chart helpers for the Brazil x Japan dossier and thread.

Each function returns a self-contained, responsive ``<svg>`` string (viewBox +
no fixed width) so the same markup scales inside a full-width report section or
a 16:9 social card. Colours follow the project palette; fonts reference the same
families loaded by the host HTML.
"""

from __future__ import annotations

import html
import math

# Palette -------------------------------------------------------------------- #
BRA = "#13a05c"
BRA_D = "#0c6f3f"
GOLD = "#e8b923"
JPN = "#2a5fb0"
JPN_D = "#173a72"
JPN_RED = "#c0392b"
INK = "#13161c"
MUTED = "#5f5d57"
LINE = "#d7cdbd"
GRID = "#e7e0d4"

SANS = "'Source Sans 3', system-ui, sans-serif"
MONO = "'Spline Sans Mono', ui-monospace, monospace"
DISPLAY = "'Archivo Black', Impact, sans-serif"


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def _txt(
    x: float,
    y: float,
    text: str,
    *,
    size: float = 12,
    fill: str = INK,
    weight: str = "700",
    anchor: str = "middle",
    font: str = SANS,
) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="{font}" font-size="{size:.1f}" '
        f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{_esc(text)}</text>'
    )


# --------------------------------------------------------------------------- #
# Radar / pizza chart
# --------------------------------------------------------------------------- #
def radar(
    labels: list[str],
    values: list[float],
    *,
    color: str = BRA,
    maxv: float = 100.0,
    size: float = 320.0,
) -> str:
    """Polygon radar across N axes (values 0..maxv)."""
    cx = cy = size / 2
    r = size / 2 - 46
    n = len(labels)
    rings = []
    for frac in (0.25, 0.5, 0.75, 1.0):
        pts = []
        for i in range(n):
            ang = -math.pi / 2 + 2 * math.pi * i / n
            pts.append(
                f"{cx + r * frac * math.cos(ang):.1f},{cy + r * frac * math.sin(ang):.1f}"
            )
        rings.append(
            f'<polygon points="{" ".join(pts)}" fill="none" stroke="{GRID}" stroke-width="1"/>'
        )
    spokes, label_tags, value_pts = [], [], []
    for i, (label, value) in enumerate(zip(labels, values)):
        ang = -math.pi / 2 + 2 * math.pi * i / n
        ex, ey = cx + r * math.cos(ang), cy + r * math.sin(ang)
        spokes.append(
            f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{ex:.1f}" y2="{ey:.1f}" stroke="{GRID}" stroke-width="1"/>'
        )
        frac = max(0.0, min(1.0, value / maxv))
        value_pts.append(
            f"{cx + r * frac * math.cos(ang):.1f},{cy + r * frac * math.sin(ang):.1f}"
        )
        lx, ly = cx + (r + 22) * math.cos(ang), cy + (r + 22) * math.sin(ang)
        anchor = (
            "middle"
            if abs(math.cos(ang)) < 0.3
            else ("start" if math.cos(ang) > 0 else "end")
        )
        label_tags.append(_txt(lx, ly + 4, label, size=11.5, fill=MUTED, anchor=anchor))
        label_tags.append(
            _txt(
                cx + (r + 22) * math.cos(ang),
                cy + (r + 22) * math.sin(ang) + 16,
                f"{value:.0f}",
                size=11,
                fill=color,
                anchor=anchor,
                font=MONO,
            )
        )
    return (
        f'<svg viewBox="0 0 {size:.0f} {size:.0f}" role="img" aria-label="Radar">'
        f'{"".join(rings)}{"".join(spokes)}'
        f'<polygon points="{" ".join(value_pts)}" fill="{color}" fill-opacity="0.28" '
        f'stroke="{color}" stroke-width="2.5"/>'
        f'{"".join(label_tags)}</svg>'
    )


# --------------------------------------------------------------------------- #
# Brazil vs Japan comparison bars (paired)
# --------------------------------------------------------------------------- #
def compare_bars(
    rows: list[tuple[str, float, float, str]], *, width: float = 520.0
) -> str:
    """rows = [(label, brasil_value, japao_value, display_fmt)] with a shared scale per row."""
    rh, gap, top = 30.0, 16.0, 10.0
    height = top + len(rows) * (rh + gap)
    bar_x, bar_w = 150.0, width - 150.0 - 70.0
    out = [
        f'<svg viewBox="0 0 {width:.0f} {height:.0f}" role="img" aria-label="Brasil vs Japão">'
    ]
    for i, (label, bv, jv, fmt) in enumerate(rows):
        y = top + i * (rh + gap)
        maxv = max(bv, jv) or 1.0
        bw = bar_w * (bv / maxv)
        jw = bar_w * (jv / maxv)
        winner_b = bv >= jv
        out.append(
            _txt(bar_x - 10, y + rh / 2 + 1, label, size=12.5, fill=INK, anchor="end")
        )
        out.append(
            f'<rect x="{bar_x}" y="{y}" width="{bw:.1f}" height="{rh / 2 - 2:.1f}" rx="2" fill="{BRA if winner_b else BRA + "99"}"/>'
        )
        out.append(
            f'<rect x="{bar_x}" y="{y + rh / 2 + 2:.1f}" width="{jw:.1f}" height="{rh / 2 - 2:.1f}" rx="2" fill="{JPN if not winner_b else JPN + "99"}"/>'
        )
        out.append(
            _txt(
                bar_x + max(bw, jw) + 8,
                y + rh / 2 + 1,
                fmt,
                size=11.5,
                fill=MUTED,
                anchor="start",
                font=MONO,
            )
        )
    out.append("</svg>")
    return "".join(out)


# --------------------------------------------------------------------------- #
# Poisson probability bar (win / draw / loss)
# --------------------------------------------------------------------------- #
def poisson_bar(
    p_win: float, p_draw: float, p_loss: float, *, width: float = 520.0
) -> str:
    h = 54.0
    segs = [
        (p_win, BRA, "Brasil"),
        (p_draw, "#8a8577", "Empate"),
        (p_loss, JPN, "Japão"),
    ]
    out = [
        f'<svg viewBox="0 0 {width:.0f} {h + 34:.0f}" role="img" aria-label="Probabilidade de resultado">'
    ]
    x = 0.0
    for prob, color, name in segs:
        w = width * prob
        out.append(
            f'<rect x="{x:.1f}" y="0" width="{w:.1f}" height="{h}" fill="{color}"/>'
        )
        if w > 56:
            out.append(
                _txt(
                    x + w / 2,
                    h / 2 - 4,
                    f"{prob * 100:.0f}%",
                    size=22,
                    fill="#fff",
                    weight="900",
                    font=DISPLAY,
                )
            )
            out.append(_txt(x + w / 2, h / 2 + 16, name, size=11.5, fill="#fff"))
        x += w
    out.append("</svg>")
    return "".join(out)


def scoreline_bars(scorelines: list[dict], *, width: float = 520.0) -> str:
    """Likely scorelines as a horizontal bar list."""
    rows = scorelines[:5]
    rh, gap, top = 26.0, 12.0, 6.0
    height = top + len(rows) * (rh + gap)
    bar_x, bar_w = 84.0, width - 84.0 - 56.0
    maxp = max((s["prob"] for s in rows), default=1.0) or 1.0
    out = [
        f'<svg viewBox="0 0 {width:.0f} {height:.0f}" role="img" aria-label="Placares prováveis">'
    ]
    for i, s in enumerate(rows):
        y = top + i * (rh + gap)
        w = bar_w * (s["prob"] / maxp)
        diff = s["brasil"] - s["japao"]
        color = BRA if diff > 0 else (JPN if diff < 0 else "#8a8577")
        out.append(
            _txt(
                bar_x - 12,
                y + rh / 2 + 4,
                f'{s["brasil"]}–{s["japao"]}',
                size=15,
                fill=INK,
                anchor="end",
                font=MONO,
            )
        )
        out.append(
            f'<rect x="{bar_x}" y="{y}" width="{w:.1f}" height="{rh}" rx="3" fill="{color}"/>'
        )
        out.append(
            _txt(
                bar_x + w + 8,
                y + rh / 2 + 4,
                f'{s["prob"] * 100:.1f}%',
                size=11.5,
                fill=MUTED,
                anchor="start",
                font=MONO,
            )
        )
    out.append("</svg>")
    return "".join(out)


# --------------------------------------------------------------------------- #
# xG race (cumulative xG per match)
# --------------------------------------------------------------------------- #
def xg_race(
    labels: list[str],
    bra: list[float],
    jpn: list[float],
    *,
    width: float = 520.0,
    height: float = 260.0,
) -> str:
    pad_l, pad_r, pad_t, pad_b = 38.0, 14.0, 18.0, 34.0
    plot_w, plot_h = width - pad_l - pad_r, height - pad_t - pad_b
    bra_c = [sum(bra[: i + 1]) for i in range(len(bra))]
    jpn_c = [sum(jpn[: i + 1]) for i in range(len(jpn))]
    maxv = max(bra_c + jpn_c + [1.0])

    def pt(i: int, v: float, n: int) -> tuple[float, float]:
        x = pad_l + (plot_w * i / max(1, n - 1))
        y = pad_t + plot_h * (1 - v / maxv)
        return x, y

    out = [
        f'<svg viewBox="0 0 {width:.0f} {height:.0f}" role="img" aria-label="Corrida de xG">'
    ]
    for frac in (0, 0.5, 1.0):
        y = pad_t + plot_h * (1 - frac)
        out.append(
            f'<line x1="{pad_l}" y1="{y:.1f}" x2="{width - pad_r}" y2="{y:.1f}" stroke="{GRID}" stroke-width="1"/>'
        )
        out.append(
            _txt(
                pad_l - 6,
                y + 4,
                f"{maxv * frac:.0f}",
                size=10,
                fill=MUTED,
                anchor="end",
                font=MONO,
            )
        )
    for i, label in enumerate(labels):
        x, _ = pt(i, 0, len(labels))
        out.append(_txt(x, height - 12, label, size=10.5, fill=MUTED))
    for series, color in ((bra_c, BRA), (jpn_c, JPN)):
        pts = [pt(i, v, len(series)) for i, v in enumerate(series)]
        poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        out.append(
            f'<polyline points="{poly}" fill="none" stroke="{color}" stroke-width="3"/>'
        )
        for x, y in pts:
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{color}"/>')
    out.append("</svg>")
    return "".join(out)


# --------------------------------------------------------------------------- #
# Zone grid (3x3 pitch heat)
# --------------------------------------------------------------------------- #
def zone_grid_3x3(
    cells: dict[tuple[str, str], float],
    *,
    color: str = BRA,
    width: float = 360.0,
    attacking_up: bool = True,
) -> str:
    """cells keyed by (third, lane); third in low/mid/high, lane in left/center/right."""
    thirds = ["high", "mid", "low"] if attacking_up else ["low", "mid", "high"]
    lanes = ["left", "center", "right"]
    height = width * 1.35
    cw, ch = width / 3, height / 3
    maxv = max(cells.values()) or 1.0
    out = [
        f'<svg viewBox="0 0 {width:.0f} {height:.0f}" role="img" aria-label="Mapa de zonas">'
    ]
    out.append(
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#0c6f3f" fill-opacity="0.05" stroke="{LINE}"/>'
    )
    for ti, third in enumerate(thirds):
        for li, lane in enumerate(lanes):
            v = cells.get((third, lane), 0.0)
            op = 0.12 + 0.78 * (v / maxv)
            x, y = li * cw, ti * ch
            out.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{cw:.1f}" height="{ch:.1f}" fill="{color}" fill-opacity="{op:.2f}" stroke="#fff" stroke-width="1"/>'
            )
            out.append(
                _txt(
                    x + cw / 2,
                    y + ch / 2 + 4,
                    f"{v * 100:.0f}",
                    size=13,
                    fill="#fff" if op > 0.5 else INK,
                    weight="800",
                    font=MONO,
                )
            )
    # pitch midline + circle
    out.append(
        f'<line x1="0" y1="{height / 2:.1f}" x2="{width}" y2="{height / 2:.1f}" stroke="#fff" stroke-opacity="0.5" stroke-width="1.5"/>'
    )
    out.append(
        f'<circle cx="{width / 2:.1f}" cy="{height / 2:.1f}" r="{width * 0.14:.1f}" fill="none" stroke="#fff" stroke-opacity="0.5" stroke-width="1.5"/>'
    )
    out.append(_txt(width / 2, 14, "ATAQUE ↑", size=10, fill="#fff", font=MONO))
    out.append("</svg>")
    return "".join(out)


# --------------------------------------------------------------------------- #
# Formation diagram (4-3-3)
# --------------------------------------------------------------------------- #
def formation_433(
    xi: list[dict], *, width: float = 420.0, overload_lane: str = "left"
) -> str:
    """xi = list of {name, role, position} ordered GK, DEF(4), MID(3), FWD(3)."""
    height = width * 1.45
    out = [
        f'<svg viewBox="0 0 {width:.0f} {height:.0f}" role="img" aria-label="Escalação 4-3-3">'
    ]
    out.append(
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#0c6f3f" fill-opacity="0.08" stroke="{LINE}"/>'
    )
    out.append(
        f'<line x1="0" y1="{height / 2:.1f}" x2="{width}" y2="{height / 2:.1f}" stroke="{LINE}" stroke-width="1"/>'
    )
    out.append(
        f'<circle cx="{width / 2:.1f}" cy="{height / 2:.1f}" r="{width * 0.13:.1f}" fill="none" stroke="{LINE}"/>'
    )

    lines = {0: [], 1: [], 2: [], 3: []}
    for p in xi:
        lines.setdefault(int(p["position"]), []).append(p)
    rows_y = {0: height * 0.92, 1: height * 0.72, 2: height * 0.48, 3: height * 0.22}

    if overload_lane == "left":
        out.append(
            f'<path d="M {width * 0.2:.0f} {height * 0.6:.0f} Q {width * 0.12:.0f} {height * 0.4:.0f} {width * 0.22:.0f} {height * 0.24:.0f}" fill="none" stroke="{GOLD}" stroke-width="3" stroke-dasharray="6 5" marker-end="url(#arr)"/>'
        )
    out.append(
        f'<defs><marker id="arr" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="{GOLD}"/></marker></defs>'
    )

    for pos, players in lines.items():
        y = rows_y[pos]
        n = len(players)
        for i, p in enumerate(players):
            x = width * (i + 1) / (n + 1)
            out.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="15" fill="{BRA}" stroke="#fff" stroke-width="2"/>'
            )
            short = _esc(str(p["name"]).split("(")[0].strip().split()[-1])
            out.append(_txt(x, y + 30, short, size=10.5, fill=INK, weight="700"))
    out.append("</svg>")
    return "".join(out)


# --------------------------------------------------------------------------- #
# Finishing dumbbell (goals vs xG)
# --------------------------------------------------------------------------- #
def finishing_dumbbell(
    rows: list[tuple[str, float, float]], *, width: float = 520.0
) -> str:
    """rows = [(label, goals, xg)]."""
    rh, gap, top = 28.0, 12.0, 8.0
    height = top + len(rows) * (rh + gap)
    bar_x, bar_w = 140.0, width - 140.0 - 40.0
    maxv = max((max(g, x) for _, g, x in rows), default=1.0) or 1.0
    out = [
        f'<svg viewBox="0 0 {width:.0f} {height:.0f}" role="img" aria-label="Gols vs xG">'
    ]
    for i, (label, goals, xg) in enumerate(rows):
        y = top + i * (rh + gap) + rh / 2
        gx = bar_x + bar_w * (goals / maxv)
        xx = bar_x + bar_w * (xg / maxv)
        out.append(_txt(bar_x - 10, y + 4, label, size=12, fill=INK, anchor="end"))
        out.append(
            f'<line x1="{min(gx, xx):.1f}" y1="{y:.1f}" x2="{max(gx, xx):.1f}" y2="{y:.1f}" stroke="{LINE}" stroke-width="3"/>'
        )
        out.append(f'<circle cx="{xx:.1f}" cy="{y:.1f}" r="6" fill="{MUTED}"/>')
        out.append(
            f'<circle cx="{gx:.1f}" cy="{y:.1f}" r="6" fill="{BRA if goals >= xg else JPN_RED}"/>'
        )
        out.append(
            _txt(
                max(gx, xx) + 10,
                y + 4,
                f"{goals:.0f}G · {xg:.1f}xG",
                size=10.5,
                fill=MUTED,
                anchor="start",
                font=MONO,
            )
        )
    out.append("</svg>")
    return "".join(out)


# --------------------------------------------------------------------------- #
# Math explainers (visual)
# --------------------------------------------------------------------------- #
def poisson_curve(
    lam_bra: float, lam_jpn: float, *, width: float = 480.0, height: float = 240.0
) -> str:
    """Side-by-side Poisson PMFs for both lambdas (goals 0..5)."""
    pad_l, pad_b, pad_t = 30.0, 30.0, 14.0
    plot_w, plot_h = width - pad_l - 10, height - pad_b - pad_t
    ks = list(range(6))

    def pmf(lam: float, k: int) -> float:
        return math.exp(-lam) * lam**k / math.factorial(k)

    series = [(lam_bra, BRA), (lam_jpn, JPN)]
    maxp = max(pmf(lam, k) for lam, _ in series for k in ks) or 1.0
    group_w = plot_w / len(ks)
    bar_w = group_w / 3
    out = [
        f'<svg viewBox="0 0 {width:.0f} {height:.0f}" role="img" aria-label="Distribuição de Poisson">'
    ]
    for k in ks:
        gx = pad_l + k * group_w + group_w * 0.2
        for i, (lam, color) in enumerate(series):
            p = pmf(lam, k)
            bh = plot_h * (p / maxp)
            x = gx + i * bar_w
            y = pad_t + plot_h - bh
            out.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w - 2:.1f}" height="{bh:.1f}" rx="2" fill="{color}"/>'
            )
        out.append(
            _txt(
                gx + bar_w, pad_t + plot_h + 16, f"{k}", size=11, fill=MUTED, font=MONO
            )
        )
    out.append(
        _txt(pad_l, height - 6, "gols", size=10, fill=MUTED, anchor="start", font=MONO)
    )
    out.append("</svg>")
    return "".join(out)


def xg_concept(*, width: float = 460.0, height: float = 240.0) -> str:
    """A goal mouth with shots sized/coloured by their chance of scoring (xG)."""
    out = [
        f'<svg viewBox="0 0 {width:.0f} {height:.0f}" role="img" aria-label="O que é xG">'
    ]
    gx0, gy = width * 0.2, 40.0
    gw = width * 0.6
    out.append(
        f'<rect x="{gx0:.0f}" y="{gy - 26:.0f}" width="{gw:.0f}" height="26" fill="none" stroke="{INK}" stroke-width="3"/>'
    )
    out.append(
        f'<line x1="20" y1="{gy:.0f}" x2="{width - 20:.0f}" y2="{gy:.0f}" stroke="{GRID}" stroke-width="2"/>'
    )
    shots = [
        (width * 0.5, height - 30, 0.62, "boa"),
        (width * 0.30, height - 70, 0.18, "média"),
        (width * 0.72, height - 60, 0.22, "média"),
        (width * 0.18, height - 110, 0.05, "fraca"),
        (width * 0.84, height - 120, 0.04, "fraca"),
    ]
    for sx, sy, xg, _ in shots:
        r = 6 + xg * 26
        color = BRA if xg >= 0.4 else (GOLD if xg >= 0.15 else MUTED)
        out.append(
            f'<line x1="{sx:.1f}" y1="{sy:.1f}" x2="{(gx0 + gw / 2):.1f}" y2="{gy:.1f}" stroke="{color}" stroke-width="1" stroke-dasharray="3 3" opacity="0.5"/>'
        )
        out.append(
            f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="{r:.1f}" fill="{color}" fill-opacity="0.35" stroke="{color}" stroke-width="2"/>'
        )
        out.append(_txt(sx, sy + 4, f"{xg:.2f}", size=10, fill=INK, font=MONO))
    out.append(
        _txt(
            width / 2,
            height - 6,
            "tamanho do círculo = chance de virar gol",
            size=10,
            fill=MUTED,
            font=MONO,
        )
    )
    return "".join(out) + "</svg>"


def shrinkage_curve(*, width: float = 440.0, height: float = 200.0) -> str:
    """Reliability weight min/(min+90) vs minutes played."""
    pad_l, pad_b, pad_t = 34.0, 28.0, 14.0
    plot_w, plot_h = width - pad_l - 12, height - pad_b - pad_t
    pts = []
    for m in range(0, 301, 10):
        w = m / (m + 90)
        x = pad_l + plot_w * (m / 300)
        y = pad_t + plot_h * (1 - w)
        pts.append(f"{x:.1f},{y:.1f}")
    out = [
        f'<svg viewBox="0 0 {width:.0f} {height:.0f}" role="img" aria-label="Shrinkage por minutos">'
    ]
    for frac in (0, 0.5, 1.0):
        y = pad_t + plot_h * (1 - frac)
        out.append(
            f'<line x1="{pad_l}" y1="{y:.1f}" x2="{width - 12}" y2="{y:.1f}" stroke="{GRID}" stroke-width="1"/>'
        )
        out.append(
            _txt(
                pad_l - 6,
                y + 4,
                f"{frac:.0%}",
                size=9,
                fill=MUTED,
                anchor="end",
                font=MONO,
            )
        )
    out.append(
        f'<polyline points="{" ".join(pts)}" fill="none" stroke="{BRA}" stroke-width="3"/>'
    )
    mx = pad_l + plot_w * (90 / 300)
    out.append(
        f'<line x1="{mx:.1f}" y1="{pad_t}" x2="{mx:.1f}" y2="{pad_t + plot_h:.1f}" stroke="{JPN_RED}" stroke-width="1.5" stroke-dasharray="4 3"/>'
    )
    out.append(
        _txt(mx, pad_t + plot_h + 16, "90 min", size=10, fill=JPN_RED, font=MONO)
    )
    out.append(
        _txt(
            width - 12,
            pad_t + plot_h + 16,
            "minutos →",
            size=10,
            fill=MUTED,
            anchor="end",
            font=MONO,
        )
    )
    out.append("</svg>")
    return "".join(out)
