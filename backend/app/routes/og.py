"""
GET /api/og/{sid} — dynamic Open Graph share card (SVG, 1200x630).

Rendered from the snapshot's real deterministic data so a shared permalink
previews with its actual verdict. Hand-built SVG (no image deps). Unknown ids
fall back to a generic branded card rather than 404, so stale shares still
look intentional.
"""

from fastapi import APIRouter, Response
from .. import mock

router = APIRouter(prefix="/api", tags=["og"])

_BAND_COLOR = {"HIGH": "#3FBF7F", "MEDIUM": "#E0A23A", "LOW": "#E0584F"}


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
    if len(lines) == max_lines and (len(" ".join(lines)) < len(text)):
        lines[-1] = lines[-1].rstrip(".,") + "…"
    return lines


def _card(question: str, headline: str, score: str, band: str,
          as_of: str) -> str:
    color = _BAND_COLOR.get(band, "#B7A57A")
    q_lines = _wrap(question, 30, 3)
    q_svg = "".join(
        f'<text x="470" y="{215 + i * 60}" font-family="Archivo, Arial, '
        f'sans-serif" font-size="50" font-weight="800" fill="#F6F4EF">'
        f"{_esc(ln)}</text>"
        for i, ln in enumerate(q_lines)
    )
    h_lines = _wrap(headline, 46, 2)
    h_y = 215 + len(q_lines) * 60 + 30
    h_svg = "".join(
        f'<text x="470" y="{h_y + i * 38}" font-family="Archivo, Arial, '
        f'sans-serif" font-size="28" fill="#F6F4EF" opacity="0.75">'
        f"{_esc(ln)}</text>"
        for i, ln in enumerate(h_lines)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
  <rect width="1200" height="630" fill="#4B2E83"/>
  <rect width="1200" height="630" fill="url(#g)"/>
  <defs>
    <radialGradient id="g" cx="18%" cy="12%" r="80%">
      <stop offset="0%" stop-color="#6c47a3" stop-opacity="0.55"/>
      <stop offset="100%" stop-color="#4B2E83" stop-opacity="0"/>
    </radialGradient>
    <pattern id="grid" width="48" height="48" patternUnits="userSpaceOnUse">
      <path d="M48 0H0V48" fill="none" stroke="#ffffff" stroke-opacity="0.05"/>
    </pattern>
  </defs>
  <rect width="1200" height="630" fill="url(#grid)"/>
  <text x="80" y="92" font-family="Archivo, Arial, sans-serif" font-size="26"
        font-weight="800" letter-spacing="2" fill="#F6F4EF">UW MARKETLENS</text>
  <text x="1120" y="92" text-anchor="end" font-family="monospace"
        font-size="22" fill="#B7A57A">prediction-market reliability</text>

  <text x="80" y="300" font-family="Archivo, Arial, sans-serif"
        font-size="200" font-weight="800" fill="{color}">{_esc(score)}</text>
  <text x="92" y="350" font-family="monospace" font-size="26"
        fill="#F6F4EF" opacity="0.6">/ 100</text>
  <text x="92" y="392" font-family="Archivo, Arial, sans-serif"
        font-size="30" font-weight="800" fill="{color}">{_esc(band)}</text>

  {q_svg}
  {h_svg}

  <rect x="80" y="540" width="60" height="4" fill="#B7A57A"/>
  <text x="80" y="588" font-family="monospace" font-size="26"
        fill="#F6F4EF" opacity="0.7">Reliability snapshot · {_esc(as_of)}</text>
</svg>"""


@router.get("/og/{sid}")
def og_card(sid: str) -> Response:
    resolved = mock.resolve_snapshot(sid)
    if resolved is None:
        svg = _card(
            "Is this prediction market citable?",
            "Open a market to generate its reliability snapshot.",
            "?", "", "live",
        )
    else:
        url, as_of = resolved
        m = mock.make_market_score(url, as_of)
        svg = _card(
            m.market_question, m.headline, str(m.reliability_score),
            m.band, m.as_of,
        )
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=300"},
    )
