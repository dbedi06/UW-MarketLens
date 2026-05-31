"""
S6 — Citation Generator
=======================
Pure function. No network calls, no dependencies beyond the standard library.
Takes market metadata and produces APA, MLA, and BibTeX citation strings with
an embedded reliability flag.

Public entry points
-------------------
  make_citation(url, question, as_of, permalink, score)  ->  CitationOutput
      Generate formatted citation strings for a market snapshot.

Design notes
------------
  - This is intentionally a pure function with no side effects.
  - The reliability flag is embedded in the citation text so anyone
    reading a paper that cites a MarketLens snapshot sees the caveat
    without having to look it up.
  - BibTeX key is deterministic from the snapshot permalink so two
    citations of the same snapshot produce the same key.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass


# ── Output dataclass ──────────────────────────────────────────────────────────

@dataclass
class CitationOutput:
    apa:              str
    mla:              str
    bibtex:           str
    ris:              str
    reliability_flag: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _reliability_flag(score: int) -> str:
    if score >= 70:
        return "RELIABLE (score >= 70)"
    elif score >= 40:
        return "USE WITH CAUTION (score 40-69): reliability below recommended threshold"
    else:
        return "NOT RECOMMENDED FOR CITATION (score < 40): low reliability"


def _bibtex_key(permalink: str) -> str:
    """
    Deterministic BibTeX key from the snapshot permalink.
    Format: marketlens_<first 8 chars of permalink hash>
    """
    h = hashlib.sha256(permalink.encode()).hexdigest()[:8]
    return f"marketlens_{h}"


def _clean_question(question: str) -> str:
    """Ensure the question ends with a question mark and has no double spaces."""
    q = re.sub(r"\s+", " ", question.strip())
    if q and not q.endswith("?"):
        q += "?"
    return q


def _apa(question: str, url: str, as_of: str, permalink: str, flag: str) -> str:
    """
    APA 7th edition format for a web document / dataset.

    Pattern:
    Author. (n.d.). Title [Type]. Publisher. Retrieved from URL (snapshot: permalink).
    [Reliability: FLAG]
    """
    return (
        f"Polymarket. (n.d.). {question} [Prediction market]. "
        f"UW MarketLens reliability snapshot {as_of}. "
        f"Retrieved from {url} (snapshot: {permalink}). "
        f"[Reliability: {flag}]"
    )


def _mla(question: str, url: str, as_of: str, permalink: str, flag: str) -> str:
    """
    MLA 9th edition format.

    Pattern:
    "Title." Publisher, URL. Accessed/snapshot DATE, permalink. [Reliability: FLAG]
    """
    return (
        f'"{question}" Polymarket, {url}. '
        f"UW MarketLens reliability snapshot, {as_of}, {permalink}. "
        f"[Reliability: {flag}]"
    )


def _ris(
    question: str,
    url: str,
    as_of: str,
    permalink: str,
    flag: str,
) -> str:
    """RIS-formatted citation for Zotero / Mendeley / EndNote import.

    Uses TY=GEN (generic) because no RIS tag describes a prediction
    market exactly. Reliability flag goes in N1 (notes) so importers
    surface it on the record.
    """
    year = as_of[:4] if len(as_of) >= 4 else ""
    return "\n".join([
        "TY  - GEN",
        f"T1  - {question}",
        "AU  - Polymarket",
        f"PY  - {year}",
        f"DA  - {as_of}",
        f"UR  - {url}",
        f"L2  - {permalink}",
        "M3  - Prediction market",
        f"N1  - UW MarketLens reliability snapshot {as_of}. Reliability: {flag}",
        "ER  - ",
        "",
    ])


def _bibtex(
    question: str,
    url: str,
    as_of: str,
    permalink: str,
    flag: str,
    key: str,
) -> str:
    """BibTeX @misc entry."""
    # Escape braces in question for BibTeX
    title = question.replace("{", r"\{").replace("}", r"\}")
    return (
        f"@misc{{{key},\n"
        f"  title  = {{{title}}},\n"
        f"  author = {{Polymarket}},\n"
        f"  note   = {{UW MarketLens reliability snapshot {as_of}. "
        f"Reliability: {flag}}},\n"
        f"  url    = {{{permalink}}}\n"
        f"}}"
    )


# ── Public API ────────────────────────────────────────────────────────────────

def make_citation(
    url: str,
    question: str,
    as_of: str,
    permalink: str,
    score: int,
) -> CitationOutput:
    """
    Generate APA, MLA, and BibTeX citations for a market snapshot.

    Parameters
    ----------
    url         Full Polymarket market URL
    question    Market question text (e.g. "Will the Fed cut rates in 2025?")
    as_of       Snapshot date as ISO string (YYYY-MM-DD)
    permalink   Snapshot permalink (e.g. /snapshot/abc123)
    score       Reliability score 0-100 — determines the reliability flag

    Returns
    -------
    CitationOutput with apa, mla, bibtex, and reliability_flag fields
    """
    q    = _clean_question(question)
    flag = _reliability_flag(score)
    key  = _bibtex_key(permalink)

    return CitationOutput(
        apa=_apa(q, url, as_of, permalink, flag),
        mla=_mla(q, url, as_of, permalink, flag),
        bibtex=_bibtex(q, url, as_of, permalink, flag, key),
        ris=_ris(q, url, as_of, permalink, flag),
        reliability_flag=flag,
    )
