"""Aggregator service — combines unBIAS + ClaimBuster into unified reliability score.

The aggregator is the final stage of the analysis pipeline.  It receives
outputs from the bias module (HOW the article is written) and the
fact-check module (WHAT the article claims), and produces a single
reliability score on [0, 100].

Full mathematical specification in docs/METHODOLOGY.md §5.
"""

from __future__ import annotations

from typing import Any

from app.core.logging import logger


def compute_reliability_score(
    bias_score: float,
    trust_score: float,
    bias_types: list[str] | None = None,
    framing_deviation: float = 0.0,
) -> dict[str, Any]:
    """Compute the final reliability score on [0, 100].

    Formula (§5.1):
        raw = (1 − bias_score)       × W_bias   (0.35)
            + trust_score             × W_trust  (0.35)
            + (1 − sensationalism)    × W_sens   (0.15)
            + (1 − framing_deviation) × W_frame  (0.15)

        reliability = raw × 100, clamped to [0, 100]

    Component breakdown:
      1. Bias inversion (1 − bias_score):
         Lower bias → higher reliability.  bias_score ∈ [0,1] from unbias module.

      2. Trust score:
         Direct pass-through from ClaimBuster.  trust_score ∈ [0,1].

      3. Sensationalism penalty:
         Binary signals from bias_types:
           "sensationalism" detected  → sensationalism = 0.70
           "loaded language" detected → sensationalism = max(current, 0.50)
           Neither                    → sensationalism = 0.00
         Inverted: (1 − sensationalism) rewards non-sensational writing.

      4. Framing neutrality:
         (1 − framing_deviation) rewards articles with neutral framing.
         framing_deviation ∈ [0,1] from the unbias framing analysis.

    Weight justification:
      - W_bias=0.35, W_trust=0.35: Bias and factual trust contribute
        equally as the two core pillars (HOW vs WHAT).
      - W_sens=0.15: Sensationalism is a sub-component of bias but
        important enough for separate penalisation.
      - W_frame=0.15: Framing neutrality captures structural editorial
        choices beyond word-level bias.
      Total = 1.00.

    Returns:
        Dict with score and component breakdown for transparency.
    """
    W_BIAS, W_TRUST, W_SENS, W_FRAME = 0.35, 0.35, 0.15, 0.15

    # Sensationalism from bias types
    sensationalism = 0.0
    if bias_types:
        if "sensationalism" in bias_types:
            sensationalism = 0.70
        if "loaded language" in bias_types:
            sensationalism = max(sensationalism, 0.50)

    # Component scores (each ∈ [0, 1])
    bias_component = 1.0 - bias_score
    trust_component = trust_score
    sens_component = 1.0 - sensationalism
    frame_component = 1.0 - framing_deviation

    raw = (
        bias_component * W_BIAS
        + trust_component * W_TRUST
        + sens_component * W_SENS
        + frame_component * W_FRAME
    )

    score = round(raw * 100, 1)
    score = min(max(score, 0.0), 100.0)

    return {
        "score": score,
        "components": {
            "bias_inversion": round(bias_component, 3),
            "trust": round(trust_component, 3),
            "sensationalism_penalty": round(sens_component, 3),
            "framing_neutrality": round(frame_component, 3),
        },
        "weights": {
            "bias": W_BIAS,
            "trust": W_TRUST,
            "sensationalism": W_SENS,
            "framing": W_FRAME,
        },
        "raw_inputs": {
            "bias_score": bias_score,
            "trust_score": trust_score,
            "sensationalism": sensationalism,
            "framing_deviation": framing_deviation,
        },
    }


def aggregate_analysis(
    bias_result: dict[str, Any],
    factcheck_result: dict[str, Any],
) -> dict[str, Any]:
    """Combine bias and fact-check results into final unified analysis.

    Args:
        bias_result: Output from unbias.analyze_bias().
        factcheck_result: Output from claimbuster.analyze_claims().

    Returns:
        Unified analysis dict ready for DB storage, including full
        component breakdown for frontend transparency.
    """
    bias_score = bias_result.get("bias_score", 0.0)
    bias_label = bias_result.get("bias_label", "unclassified")
    sentiment = bias_result.get("sentiment", {})
    bias_types = bias_result.get("bias_types", [])
    flagged_tokens = bias_result.get("flagged_tokens", [])
    framing = bias_result.get("framing", {})
    political_lean = bias_result.get("political_lean", {})
    score_components = bias_result.get("score_components", {})

    trust_score = factcheck_result.get("trust_score", 0.5)
    claims = factcheck_result.get("claims", [])
    credibility_tier = factcheck_result.get("source_credibility_tier", "unknown")
    trust_components = factcheck_result.get("trust_components", {})

    framing_deviation = framing.get("framing_deviation", 0.0)

    reliability_result = compute_reliability_score(
        bias_score=bias_score,
        trust_score=trust_score,
        bias_types=bias_types,
        framing_deviation=framing_deviation,
    )

    reliability_score = reliability_result["score"]

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
        # Extended analysis data for transparency
        "framing": framing,
        "political_lean": political_lean,
        "bias_score_components": score_components,
        "trust_score_components": trust_components,
        "reliability_components": reliability_result["components"],
        "reliability_weights": reliability_result["weights"],
        "model_confidence": bias_result.get("model_confidence", 0.5),
    }
