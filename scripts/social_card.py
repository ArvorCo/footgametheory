#!/usr/bin/env python3
"""Generate the social-share image (Open Graph card, 1200x630).

A designed cover for when the homepage/report link is posted: dark Arvor
background, the confrontation heatmap blended on the right, the logo, the
headline and the arvor.co lockup. Output: ``docs/assets/og-cover.png``.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
ASSET_DIR = DOCS_DIR / "assets"
W, H = 1200, 630

SERIF_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
    "/System/Library/Fonts/Supplemental/Georgia.ttf",
    "/Library/Fonts/Georgia.ttf",
    "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
]
SANS_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
MONO_CANDIDATES = [
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/Supplemental/Courier New Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
]


def _font(
    candidates: list[str], size: int
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _gradient_bg() -> Image.Image:
    top = np.array([14, 26, 20], dtype=np.float32)
    bot = np.array([6, 14, 10], dtype=np.float32)
    t = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    grad = (top[None, None] * (1 - t) + bot[None, None] * t).astype(np.uint8)
    grad = np.repeat(grad, W, axis=1)
    img = Image.fromarray(grad, "RGB")
    # green radial glow, top-left
    yy, xx = np.indices((H, W))
    d = np.sqrt((xx - 120) ** 2 + (yy + 40) ** 2) / 620.0
    glow = np.clip(1 - d, 0, 1)[..., None] ** 2
    base = np.asarray(img, dtype=np.float32)
    base += glow * np.array([19, 130, 80], dtype=np.float32) * 0.55
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB")


def _blend_heatmap(img: Image.Image, heat_path: Path) -> None:
    if not heat_path.exists():
        return
    panel_w = 560
    heat = Image.open(heat_path).convert("RGB")
    ratio = max(panel_w / heat.width, H / heat.height)
    heat = heat.resize((int(heat.width * ratio), int(heat.height * ratio)))
    left = heat.width - panel_w
    top = max(0, (heat.height - H) // 2)
    heat = heat.crop((left, top, left + panel_w, top + H))
    arr = np.asarray(heat, dtype=np.float32) * 1.18  # lift the heat so colours pop
    heat = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
    # horizontal fade-in mask (transparent at left edge -> fully visible at right)
    ramp = np.clip(np.linspace(-0.05, 1.0, panel_w), 0, 1) ** 0.9
    mask = np.tile((ramp * 255).astype(np.uint8), (H, 1))
    img.paste(heat, (W - panel_w, 0), Image.fromarray(mask, "L"))


def _logo_chip(img: Image.Image) -> None:
    logo_path = ASSET_DIR / "arvor_logo.png"
    if not logo_path.exists():
        return
    chip = Image.new("RGBA", (84, 84), (255, 255, 255, 255))
    logo = Image.open(logo_path).convert("RGBA").resize((66, 66))
    chip.paste(logo, (9, 9), logo)
    rounded = Image.new("L", (84, 84), 0)
    ImageDraw.Draw(rounded).rounded_rectangle([0, 0, 83, 83], radius=18, fill=255)
    img.paste(chip, (72, 60), rounded)


def build_social_card(composites: dict[str, str]) -> str:
    img = _gradient_bg()
    rel = composites.get("confrontation", "")
    _blend_heatmap(img, (DOCS_DIR / rel) if rel else Path("/nonexistent"))
    _logo_chip(img)
    draw = ImageDraw.Draw(img)

    serif = _font(SERIF_CANDIDATES, 92)
    sans = _font(SANS_CANDIDATES, 30)
    sans_sm = _font(SANS_CANDIDATES, 27)
    mono = _font(MONO_CANDIDATES, 24)

    gold, cream, green, muted, white = (
        (232, 185, 35),
        (224, 220, 208),
        (40, 200, 120),
        (150, 165, 150),
        (255, 255, 255),
    )

    draw.text((176, 78), "ARVOR INTELLIGENCE", font=mono, fill=(170, 200, 180))
    draw.text((72, 200), "MONEYBALL DA COPA 2026 · OITAVAS", font=mono, fill=gold)

    # Title with a green "x"
    y = 242
    x = 72
    draw.text((x, y), "Brasil ", font=serif, fill=white)
    x += int(draw.textlength("Brasil ", font=serif))
    draw.text((x, y), "×", font=serif, fill=green)
    x += int(draw.textlength("×", font=serif))
    draw.text((x, y), " Japão", font=serif, fill=white)

    draw.text((72, 362), "Decidido nos dados:", font=sans, fill=cream)
    draw.text((72, 402), "o modelo, os mapas e o veredito.", font=sans, fill=cream)

    draw.text((72, 520), "arvor.co", font=mono, fill=green)
    draw.text(
        (72, 552), "Foot Game Theory · dossiê Moneyball", font=sans_sm, fill=muted
    )

    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    out = ASSET_DIR / "og-cover.png"
    img.save(out, "PNG")
    return str(out.relative_to(DOCS_DIR))
