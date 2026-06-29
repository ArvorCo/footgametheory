#!/usr/bin/env python3
"""Shared SEO + social-card meta helpers for the published pages.

Produces canonical, Open Graph, Twitter Card and JSON-LD markup so links render
as rich news-style cards on social media and rank well in search.
"""

from __future__ import annotations

import html
import json

SITE = "https://footgametheory.arvor.co"
OG_IMAGE = f"{SITE}/assets/og-cover.png"
TWITTER = "@leonardodias"


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def head_seo(
    title: str,
    description: str,
    path: str,
    *,
    image: str = OG_IMAGE,
    og_type: str = "website",
    image_alt: str = "Foot Game Theory — Brasil × Japão, Moneyball da Copa por Arvor Intelligence",
) -> str:
    """A full block of canonical + Open Graph + Twitter meta tags."""
    url = SITE + path
    return (
        f'<link rel="canonical" href="{_esc(url)}">\n'
        '<meta name="robots" content="index,follow,max-image-preview:large">\n'
        '<meta name="author" content="Arvor Intelligence">\n'
        '<meta name="theme-color" content="#0b0f0d">\n'
        '<meta property="og:site_name" content="Foot Game Theory · Arvor Intelligence">\n'
        '<meta property="og:locale" content="pt_BR">\n'
        f'<meta property="og:type" content="{_esc(og_type)}">\n'
        f'<meta property="og:title" content="{_esc(title)}">\n'
        f'<meta property="og:description" content="{_esc(description)}">\n'
        f'<meta property="og:url" content="{_esc(url)}">\n'
        f'<meta property="og:image" content="{_esc(image)}">\n'
        '<meta property="og:image:type" content="image/png">\n'
        '<meta property="og:image:width" content="1200">\n'
        '<meta property="og:image:height" content="630">\n'
        f'<meta property="og:image:alt" content="{_esc(image_alt)}">\n'
        '<meta name="twitter:card" content="summary_large_image">\n'
        f'<meta name="twitter:site" content="{TWITTER}">\n'
        f'<meta name="twitter:creator" content="{TWITTER}">\n'
        f'<meta name="twitter:title" content="{_esc(title)}">\n'
        f'<meta name="twitter:description" content="{_esc(description)}">\n'
        f'<meta name="twitter:image" content="{_esc(image)}">\n'
        f'<meta name="twitter:image:alt" content="{_esc(image_alt)}">'
    )


def jsonld_site(title: str, description: str) -> str:
    """WebSite + Organization structured data for the homepage."""
    data = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Organization",
                "name": "Arvor Intelligence",
                "url": "https://arvor.co",
                "logo": f"{SITE}/assets/arvor_logo.png",
            },
            {
                "@type": "WebSite",
                "name": title,
                "description": description,
                "url": f"{SITE}/",
                "publisher": {"@type": "Organization", "name": "Arvor Intelligence"},
            },
        ],
    }
    return f'<script type="application/ld+json">{json.dumps(data, ensure_ascii=False)}</script>'


def jsonld_article(title: str, description: str, path: str) -> str:
    """Article structured data for the report page."""
    data = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": description,
        "image": OG_IMAGE,
        "url": SITE + path,
        "inLanguage": "pt-BR",
        "author": {
            "@type": "Organization",
            "name": "Arvor Intelligence",
            "url": "https://arvor.co",
        },
        "publisher": {
            "@type": "Organization",
            "name": "Arvor Intelligence",
            "logo": {"@type": "ImageObject", "url": f"{SITE}/assets/arvor_logo.png"},
        },
    }
    return f'<script type="application/ld+json">{json.dumps(data, ensure_ascii=False)}</script>'
