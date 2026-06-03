"""
GET /api/og/{sid} — dynamic Open Graph share card (SVG, 1200x630).

Rendered from the snapshot's real deterministic data: an arc score gauge,
the actual trade-window price sparkline (with the flagged span shaded), the
three subscores as bars, the question and headline. Hand-built SVG, no image
deps. Unknown ids fall back to a generic branded card (not 404).
"""

import logging
import math
from fastapi import APIRouter, Response
from .. import composite, mock
from ..ingestion import IngestionUnavailable

router = APIRouter(prefix="/api", tags=["og"])
logger = logging.getLogger(__name__)

_BAND = {"HIGH": "#3FBF7F", "MEDIUM": "#E0A23A", "LOW": "#E0584F"}
_SUBS = [
    ("LIQUIDITY", "liquidity_health"),
    ("ANOMALY", "anomaly"),
    ("RESOLUTION", "resolution_quality"),
]


def _esc(s: str) -> str:
    return (
        s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _wrap(text: str, width: int, max_lines: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= width:
            cur = f"{cur} {w}".strip()
        else:
            lines.append(cur)
            cur = w
            if len(lines) == max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    if len(lines) == max_lines and len(" ".join(lines)) < len(text):
        lines[-1] = lines[-1].rstrip(".,") + "…"
    return lines


def _sub_color(v: int) -> str:
    return "#3FBF7F" if v >= 70 else "#E0A23A" if v >= 40 else "#E0584F"


def _gauge(score: int, color: str) -> str:
    cx, cy, r, w = 200, 270, 118, 20
    c = 2 * math.pi * r
    off = c * (1 - max(0, min(100, score)) / 100)
    return f"""
  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#ffffff"
          stroke-opacity="0.12" stroke-width="{w}"/>
  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}"
          stroke-width="{w}" stroke-linecap="round"
          stroke-dasharray="{c:.1f}" stroke-dashoffset="{off:.1f}"
          transform="rotate(-90 {cx} {cy})"/>
  <text x="{cx}" y="{cy+18}" text-anchor="middle"
        font-family="Archivo, Arial, sans-serif" font-size="120"
        font-weight="800" fill="{color}">{score}</text>
  <text x="{cx}" y="{cy+58}" text-anchor="middle" font-family="monospace"
        font-size="22" fill="#F6F4EF" opacity="0.55">/ 100</text>"""


def _sparkline(series) -> str:
    if not series:
        return ""
    x0, x1, ytop, ybot = 470, 1130, 470, 560
    n = len(series)
    
    # Normalize prices to 0-1 range based on min/max in series for better visualization
    prices = [float(p.price) for p in series]
    min_price = min(prices) if prices else 0
    max_price = max(prices) if prices else 1
    price_range = max_price - min_price if max_price > min_price else 1
    
    pts = []
    for i, p in enumerate(series):
        x = x0 + (x1 - x0) * (i / max(1, n - 1))
        # Normalize price to 0-1 range based on min/max, then scale to Y coordinates
        normalized_price = (float(p.price) - min_price) / price_range if price_range > 0 else 0.5
        normalized_price = max(0.0, min(1.0, normalized_price))
        y = ybot - (ybot - ytop) * normalized_price
        pts.append(f"{x:.1f},{y:.1f}")
    poly = " ".join(pts)
    flagged = [i for i, p in enumerate(series) if p.flagged]
    shade = ""
    if flagged:
        fx0 = x0 + (x1 - x0) * (flagged[0] / max(1, n - 1))
        fx1 = x0 + (x1 - x0) * (flagged[-1] / max(1, n - 1))
        shade = (
            f'<rect x="{fx0:.1f}" y="{ytop}" width="{max(3, fx1 - fx0):.1f}" '
            f'height="{ybot - ytop}" fill="#E0584F" fill-opacity="0.18"/>'
        )
    return f"""
  <text x="470" y="455" font-family="monospace" font-size="16"
        fill="#F6F4EF" opacity="0.4">TRADE-WINDOW PRICE PATH</text>
  {shade}
  <polyline points="{poly}" fill="none" stroke="#B7A57A"
            stroke-width="3" stroke-linejoin="round"/>"""


def _subbars(subs) -> str:
    out = []
    for i, (label, key) in enumerate(_SUBS):
        v = int(getattr(subs, key)) if subs else 0
        y = 590 + i * 16
        col = _sub_color(v)
        out.append(
            f'<text x="80" y="{y+4}" font-family="monospace" font-size="13" '
            f'fill="#F6F4EF" opacity="0.55">{label}</text>'
            f'<rect x="200" y="{y-9}" width="200" height="9" rx="2" '
            f'fill="#ffffff" fill-opacity="0.12"/>'
            f'<rect x="200" y="{y-9}" width="{v*2}" height="9" rx="2" '
            f'fill="{col}"/>'
            f'<text x="412" y="{y+1}" font-family="monospace" font-size="13" '
            f'fill="{col}">{v}</text>'
        )
    return "".join(out)


def _card(question, headline, score, band, as_of, subs=None,
          series=None, resolution_applicable: bool = True) -> str:
    color = _BAND.get(band, "#B7A57A")
    q_svg = "".join(
        f'<text x="470" y="{170 + i*62}" font-family="Archivo, Arial, '
        f'sans-serif" font-size="52" font-weight="800" fill="#F6F4EF">'
        f"{_esc(ln)}</text>"
        for i, ln in enumerate(_wrap(question, 28, 3))
    )
    q_n = len(_wrap(question, 28, 3))
    h_y = 170 + q_n * 62 + 6
    h_svg = "".join(
        f'<text x="470" y="{h_y + i*34}" font-family="Archivo, Arial, '
        f'sans-serif" font-size="26" fill="#F6F4EF" opacity="0.7">'
        f"{_esc(ln)}</text>"
        for i, ln in enumerate(_wrap(headline, 52, 2))
    )
    resolution_note = ""
    if not resolution_applicable:
        resolution_note = (
            f'<text x="470" y="{h_y + 74}" font-family="monospace" '
            f'font-size="18" fill="#F6F4EF" opacity="0.55">'
            "Resolution not yet applicable for this open market."
            "</text>"
        )
    gauge = _gauge(score, color) if isinstance(score, int) else f"""
  <text x="200" y="288" text-anchor="middle"
        font-family="Archivo, Arial, sans-serif" font-size="120"
        font-weight="800" fill="#B7A57A">{_esc(str(score))}</text>"""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#2c1a4c"/>
      <stop offset="55%" stop-color="#4B2E83"/>
      <stop offset="100%" stop-color="#3d2569"/>
    </linearGradient>
    <radialGradient id="glow" cx="16%" cy="10%" r="75%">
      <stop offset="0%" stop-color="#8a6abd" stop-opacity="0.55"/>
      <stop offset="100%" stop-color="#4B2E83" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="gold" cx="92%" cy="4%" r="55%">
      <stop offset="0%" stop-color="#B7A57A" stop-opacity="0.35"/>
      <stop offset="100%" stop-color="#B7A57A" stop-opacity="0"/>
    </radialGradient>
    <pattern id="grid" width="44" height="44" patternUnits="userSpaceOnUse">
      <path d="M44 0H0V44" fill="none" stroke="#ffffff"
            stroke-opacity="0.06"/>
    </pattern>
  </defs>
  <rect width="1200" height="630" fill="url(#bg)"/>
  <rect width="1200" height="630" fill="url(#grid)"/>
  <rect width="1200" height="630" fill="url(#glow)"/>
  <rect width="1200" height="630" fill="url(#gold)"/>
  <rect x="0" y="0" width="10" height="630" fill="{color}"/>

  <text x="70" y="86" font-family="Archivo, Arial, sans-serif"
        font-size="26" font-weight="800" letter-spacing="2"
        fill="#F6F4EF">UW MARKETLENS</text>
  <text x="1130" y="86" text-anchor="end" font-family="monospace"
        font-size="20" fill="#B7A57A">prediction-market reliability</text>
  <line x1="70" y1="108" x2="1130" y2="108" stroke="#ffffff"
        stroke-opacity="0.12"/>
{gauge}
  <text x="200" y="430" text-anchor="middle"
        font-family="Archivo, Arial, sans-serif" font-size="30"
        font-weight="800" fill="{color}">{_esc(band) or "LIVE"}</text>

  {q_svg}
  {h_svg}
  {resolution_note}
  {_sparkline(series or [])}
  {_subbars(subs)}

  <text x="1130" y="600" text-anchor="end" font-family="monospace"
        font-size="22" fill="#F6F4EF" opacity="0.7">Reliability snapshot · {_esc(as_of)}</text>
</svg>"""


@router.get("/og/{sid}")
def og_card(sid: str) -> Response:
    full = mock.resolve_snapshot_full(sid)
    if full is None:
        svg = _card(
            "Is this prediction market citable?",
            "Open a market to generate its reliability snapshot.",
            "?", "", "live",
        )
    else:
        url, as_of, source = full
        if source == "live":
            # Dispatch live-source snapshots through composite so the
            # OG card matches the report instead of showing stale mock
            # values. Any failure (cold cache, env flags unset,
            # upstream API misbehaving) falls back to mock — the OG
            # endpoint should never 5xx, an image is always better
            # than no image when a link gets shared.
            try:
                m = composite.make_market_score(url, as_of)
            except (IngestionUnavailable, ValueError) as exc:
                logger.warning(
                    "og: live render failed for %s (%s); falling back "
                    "to mock card.", sid, exc,
                )
                m = mock.make_market_score(url, as_of)
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "og: unexpected live-render error for %s (%s); "
                    "falling back to mock card.", sid, exc,
                )
                m = mock.make_market_score(url, as_of)
        else:
            m = mock.make_market_score(url, as_of)
        svg = _card(
            m.market_question, m.headline, m.reliability_score, m.band,
            m.as_of, m.subscores, m.anomaly_series,
            m.subscores.resolution_applicable,
        )
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=300"},
    )
