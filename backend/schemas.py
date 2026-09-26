"""THE contract. Mirror of frontend/src/types.ts — change both together."""
from typing import Any, Literal, Optional
from pydantic import BaseModel

Band = Literal["clean", "inconclusive", "strong"]
SignalId = Literal["classifier", "ela", "fft", "noise", "metadata"]
Region = Literal["left_eye", "right_eye", "mouth", "nose", "jaw_boundary", "skin", "background"]
Decision = Literal["agree", "disagree", "needs_more"]


class Signal(BaseModel):
    id: SignalId
    name: str
    score: float
    weight: float = 0.0
    contribution: float = 0.0
    reason: str
    heatmap: Optional[str] = None
    panel: Optional[str] = None
    details: Optional[dict[str, Any]] = None
    ok: bool = True
    error: Optional[str] = None


class RegionScore(BaseModel):
    region: Region
    suspicion: float


class Review(BaseModel):
    decision: Decision
    note: str = ""
    at: str = ""


class ReviewIn(BaseModel):
    decision: Decision
    note: str = ""


class Robustness(BaseModel):
    jpeg50: float
    resize50: float


class AnalysisResult(BaseModel):
    case_id: str
    sha256: str
    filename: str
    media_type: Literal["image"] = "image"
    created_at: str
    original: str
    overlay: str
    fused_score: float
    band: Band
    headline: str
    signals: list[Signal]
    regions: list[RegionScore]
    robustness: Robustness
    explanation: str
    limitations: list[str]
    disclaimer: str
    timings_ms: dict[str, float]
    review: Optional[Review] = None


class CaseSummary(BaseModel):
    case_id: str
    filename: str
    media_type: str
    fused_score: float
    band: Band
    created_at: str
    review: Optional[Review] = None
