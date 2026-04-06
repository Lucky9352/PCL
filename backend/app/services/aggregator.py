"""Aggregator service — combines unBIAS + ClaimBuster into unified reliability score."""

from __future__ import annotations

from typing import Any

from app.core.logging import logger


def compute_reliability_score(
    bias_score: float,
    trust_score: float,
    bias_types: list[str] | None = None,
) -> float:
    """Compute the final reliability score (0-100).

    Formula:
        reliability = (
            (1 - bias_score) * 0.40
          + trust_score * 0.40
          + (1 - sensationalism_score) * 0.20
        ) * 100

    Args:
        bias_score: Overall bias score (0-1, higher = more biased).
        trust_score: Trust score from ClaimBuster (0-1, higher = more trustworthy).
        bias_types: List of detected bias types.

    Returns:
        Reliability score (0-100).
    """
    # Sensationalism component
    sensationalism_score = 0.0
    if bias_types:
        if "sensationalism" in bias_types:
            sensationalism_score = 0.7
        if "loaded language" in bias_types:
            sensationalism_score = max(sensationalism_score, 0.5)

    reliability = (1 - bias_score) * 0.40 + trust_score * 0.40 + (1 - sensationalism_score) * 0.20

    # Scale to 0-100
    score = round(reliability * 100, 1)
    return min(max(score, 0.0), 100.0)


def aggregate_analysis(
    bias_result: dict[str, Any],
    factcheck_result: dict[str, Any],
) -> dict[str, Any]:
    """Combine bias and fact-check results into final analysis.

    Args:
        bias_result: Output from unbias.analyze_bias().
        factcheck_result: Output from claimbuster.analyze_claims().

    Returns:
        Unified analysis dict ready for DB storage.
    """
    bias_score = bias_result.get("bias_score", 0.0)
    bias_label = bias_result.get("bias_label", "unclassified")
    sentiment = bias_result.get("sentiment", {})
    bias_types = bias_result.get("bias_types", [])
    flagged_tokens = bias_result.get("flagged_tokens", [])

    trust_score = factcheck_result.get("trust_score", 0.5)
    claims = factcheck_result.get("claims", [])
    credibility_tier = factcheck_result.get("source_credibility_tier", "unknown")

    reliability_score = compute_reliability_score(
        bias_score=bias_score,
        trust_score=trust_score,
        bias_types=bias_types,
    )

    logger.info(
        f"Aggregated: bias={bias_score:.3f} trust={trust_score:.3f} "
        f"reliability={reliability_score:.1f}"
    )

    return {
        "bias_score": bias_score,
        "bias_label": bias_label,
        "sentiment_score": sentiment.get("score", 0.0),
        "sentiment_label": sentiment.get("label", "neutral"),
        "bias_types": bias_types,
        "flagged_tokens": flagged_tokens,
        "trust_score": trust_score,
        "source_credibility_tier": credibility_tier,
        "top_claims": claims,
        "reliability_score": reliability_score,
        "analysis_status": "complete",
    }
