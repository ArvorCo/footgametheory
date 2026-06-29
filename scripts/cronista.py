#!/usr/bin/env python3
"""Loader for the cronista (Nelson Rodrigues) copy produced by the writer agent.

The human prose lives in ``analysis/copy_report.json`` and
``analysis/copy_thread.json`` so the HTML stays data-driven while gaining a
voice. If a file is missing or malformed the loaders fall back to terse but
functional defaults, so the build never breaks.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_DIR = ROOT / "analysis"


def _load(name: str) -> dict:
    path = ANALYSIS_DIR / name
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


# --------------------------------------------------------------------------- #
# Report copy
# --------------------------------------------------------------------------- #
_REPORT_FALLBACK_HERO = {
    "kicker": "Laudo tático-estatístico · Copa 2026 · Oitavas",
    "title": "Brasil × Japão: a conta que precede a bola.",
    "lead": "O modelo dá o Brasil favorito. Mas favorito não é o mesmo que vencedor — e o número sabe disso.",
}


def report_copy() -> dict:
    return _load("copy_report.json")


def hero() -> dict:
    return {**_REPORT_FALLBACK_HERO, **report_copy().get("hero", {})}


def section(key: str, default_title: str = "") -> dict:
    sec = report_copy().get("sections", {}).get(key, {})
    return {
        "title": sec.get("title", default_title),
        "paragraphs": sec.get("paragraphs", []),
    }


def callout(key: str, default: str = "") -> str:
    return report_copy().get("callouts", {}).get(key, default)


# --------------------------------------------------------------------------- #
# Thread copy
# --------------------------------------------------------------------------- #
_THREAD_FALLBACK_HEADER = {
    "slug": "FOOT GAME THEORY · DOSSIÊ · BRASIL × JAPÃO",
    "title": "Brasil × Japão: o dossiê",
    "subtitle": "25 cartas táticas de uma Copa.",
    "intro": "Cada card é um achado. Cada texto, pronto para colar. Do modelo ao veredito.",
}


def thread_copy() -> dict:
    return _load("copy_thread.json")


def thread_header() -> dict:
    return {**_THREAD_FALLBACK_HEADER, **thread_copy().get("header", {})}


def thread_posts() -> dict[int, dict]:
    """Posts keyed by their number for easy lookup by the thread builder."""
    posts = thread_copy().get("posts", [])
    return {int(p.get("n", i + 1)): p for i, p in enumerate(posts)}


def post(n: int) -> dict:
    return thread_posts().get(n, {})
