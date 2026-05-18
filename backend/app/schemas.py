"""
PLACEHOLDER SCHEMAS — replace in S0.

These Pydantic models define the *shape* of every API request and response.
They are intentionally temporary: just enough structure to make the backend
return something the frontend can render. The whole team finalizes the real
schemas in Section S0 — do not treat field names here as final.

Why Pydantic: FastAPI validates incoming requests against these models, and
auto-generates the interactive API docs at /docs from them for free.
"""

from typing import List, Literal
from pydantic import BaseModel, Field


# ---- Request models -------------------------------------------------------

class ScoreRequest(BaseModel):
    # PLACEHOLDER — replace in S0
    url: str = Field(..., description="A Polymarket market URL")


class CitationRequest(BaseModel):
    # PLACEHOLDER — replace in S0
    url: str = Field(..., description="A Polymarket market URL")
    style: Literal["APA", "MLA"] = "APA"


# ---- Response sub-models --------------------------------------------------

class Subscores(BaseModel):
    # PLACEHOLDER — replace in S0
    liquidity_health: int = Field(..., ge=0, le=100)
    anomaly: int = Field(..., ge=0, le=100)
    resolution_quality: int = Field(..., ge=0, le=100)


class AnomalyResult(BaseModel):
    # PLACEHOLDER — replace in S0 (real version comes from S3 Isolation Forest)
    score: float = Field(..., description="Aggregate anomaly score, higher = more anomalous")
    flagged_windows: int = Field(..., description="Count of suspicious time windows")
    top_features: List[str] = Field(default_factory=list)


class ResolutionVerdict(BaseModel):
    # PLACEHOLDER — replace in S0 (real version comes from S4 LLM-as-judge)
    verdict: Literal["HIGH", "MEDIUM", "LOW", "UNVERIFIABLE"]
    reasoning: str
    supporting_sources: List[str] = Field(default_factory=list)


class Tags(BaseModel):
    # PLACEHOLDER — replace in S0 (real version comes from S5 LLM tagger)
    departments: List[str] = Field(default_factory=list)
    course_applicability: int = Field(..., ge=0, le=100)


class Citation(BaseModel):
    # PLACEHOLDER — replace in S0 (real version comes from S6 citation generator)
    apa: str
    mla: str
    reliability_flag: str


class MarketScore(BaseModel):
    # PLACEHOLDER — replace in S0
    market_url: str
    market_question: str
    reliability_score: int = Field(..., ge=0, le=100)
    band: Literal["HIGH", "MEDIUM", "LOW"]
    subscores: Subscores
    anomaly: AnomalyResult
    resolution: ResolutionVerdict
    tags: Tags
    citation: Citation


class LibraryEntry(BaseModel):
    # PLACEHOLDER — replace in S0
    market_url: str
    market_question: str
    reliability_score: int
    band: Literal["HIGH", "MEDIUM", "LOW"]
    departments: List[str]
    verified: bool
