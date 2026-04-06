"""Pydantic schemas for analysis-specific data structures."""

from __future__ import annotations

from pydantic import BaseModel


class ClaimSchema(BaseModel):
    """A single factual claim with verification results."""

    text: str
    checkworthiness: float
    verdict: str  # SUPPORTS | REFUTES | NOT_ENOUGH_INFO
    evidence_urls: list[str] = []
    confidence: float = 0.0


class BiasAnalysisSchema(BaseModel):
    """Output from the unBIAS module."""

    bias_score: float  # 0–1
    bias_label: str  # left | center | right | unclassified
    sentiment: dict  # {"score": float, "label": str}
    bias_types: list[str] = []
    flagged_tokens: list[dict] = []
    model_confidence: float = 0.0


class FactCheckSchema(BaseModel):
    """Output from the ClaimBuster module."""

    claims: list[ClaimSchema] = []
    trust_score: float  # 0–1
    source_credibility_tier: str  # high | medium | low | unknown
