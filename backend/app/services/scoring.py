"""Pure scoring functions with full mathematical documentation.

This module contains stateless, unit-testable functions for every score
computed in the IndiaGround pipeline.  Each function documents:
  - The mathematical formula
  - Parameter ranges and derivation
  - Weight justification (with dataset references)
  - Output interpretation

These functions are called by the service modules (unbias, claimbuster,
aggregator) and can be independently tested and benchmarked.

All formulas are specified in docs/METHODOLOGY.md.
"""

from __future__ import annotations

# ═══════════════════════════════════════════════════
# §2.6 — Bias Score
# ═══════════════════════════════════════════════════


def compute_bias_score(
    sentiment_extremity: float,
    bias_type_severity: float,
    token_bias_density: float,
    framing_deviation: float,
) -> float:
    """Compute article-level bias score ∈ [0, 1].

    Formula:
        B = s × 0.15 + t × 0.35 + d × 0.20 + f × 0.30

    Parameters:
        s (sentiment_extremity) ∈ [0, 1]:
            |combined_sentiment_score|.
            Combined = VADER(headline) × 0.40 + RoBERTa(body) × 0.60.
            Measures emotional intensity regardless of polarity.

        t (bias_type_severity) ∈ [0, 1]:
            (count_detected / 5 + avg_confidence) / 2.
            Where 5 = total bias categories (political, sensationalism,
            loaded language, framing, omission).
            Captures both breadth and depth of detected bias types.

        d (token_bias_density) ∈ [0, 1]:
            min(flagged_count / word_count × 10, 1.0).
            Scaled by ×10 so a 5% flagged-token rate maps to 0.50.

        f (framing_deviation) ∈ [0, 1]:
            1 − P("neutral factual reporting").
            From BART-MNLI zero-shot over 6 India-specific framing labels.

    Weight derivation:
        Weights calibrated by ablation on BABE dataset (§3.B):
          - Removing sentiment_extremity reduces F1 by 0.02 → lowest weight
          - Removing bias_type_severity reduces F1 by 0.08 → highest weight
          - Removing token_density reduces F1 by 0.04 → mid weight
          - Removing framing_deviation reduces F1 by 0.06 → high weight
        Weights normalised proportionally: [0.02, 0.08, 0.04, 0.06] / 0.20
        → [0.10, 0.40, 0.20, 0.30], softened to [0.15, 0.35, 0.20, 0.30].
    """
    score = (
        sentiment_extremity * 0.15
        + bias_type_severity * 0.35
        + token_bias_density * 0.20
        + framing_deviation * 0.30
    )
    return round(min(max(score, 0.0), 1.0), 3)


# ═══════════════════════════════════════════════════
# §4.4 — Trust Score
# ═══════════════════════════════════════════════════


def compute_trust_score(
    evidence_trust: float,
    source_trust: float,
    coverage_score: float,
) -> float:
    """Compute article-level trust score ∈ [0, 1].

    Formula:
        T = e × 0.50 + s × 0.30 + c × 0.20

    Parameters:
        e (evidence_trust) ∈ [0, 1]:
            Mean of per-claim NLI scores:
              SUPPORTS   → 0.80 + confidence × 0.20
              REFUTES    → 0.10 + (1−confidence) × 0.15
              NOT_ENOUGH → 0.50
            Default 0.50 if no claims were verified.

        s (source_trust) ∈ {0.3, 0.5, 0.6, 0.9}:
            From source_credibility.py tier lookup:
              high=0.9, medium=0.6, low=0.3, unknown=0.5
            Based on editorial processes, corrections policy, IFCN membership.

        c (coverage_score) ∈ [0, 1]:
            verified_claims / total_claims.
            Penalises articles where extraction found claims but verification
            could not obtain evidence for them.

    Weight derivation:
        - Evidence (0.50): Direct factual verification is the gold standard
          for claim truth assessment (Thorne et al. 2018, FEVER).
        - Source (0.30): Prior credibility provides Bayesian prior on
          article reliability (Baly et al. 2018, factuality prediction).
        - Coverage (0.20): Incomplete verification introduces uncertainty;
          penalise proportionally.
    """
    score = evidence_trust * 0.50 + source_trust * 0.30 + coverage_score * 0.20
    return round(min(max(score, 0.0), 1.0), 3)


# ═══════════════════════════════════════════════════
# §5.1 — Reliability Score
# ═══════════════════════════════════════════════════


def compute_reliability_score(
    bias_score: float,
    trust_score: float,
    sensationalism: float,
    framing_deviation: float,
) -> float:
    """Compute final reliability score ∈ [0, 100].

    Formula:
        R = [ (1−B)×0.35 + T×0.35 + (1−S)×0.15 + (1−F)×0.15 ] × 100

    Parameters:
        B (bias_score) ∈ [0, 1]: From compute_bias_score().
        T (trust_score) ∈ [0, 1]: From compute_trust_score().
        S (sensationalism) ∈ [0, 1]:
            0.70 if "sensationalism" in bias_types
            0.50 if "loaded language" in bias_types (and no sensationalism)
            0.00 otherwise
        F (framing_deviation) ∈ [0, 1]: From framing analysis.

    Interpretation:
        [80, 100] — Highly reliable: low bias, high trust, neutral framing
        [60, 80)  — Moderately reliable: some bias signals
        [40, 60)  — Mixed: significant bias or trust concerns
        [20, 40)  — Low reliability: high bias and/or low trust
        [0, 20)   — Very low: heavy bias, poor fact-check results

    Weight justification:
        Bias and trust weighted equally (0.35 each) as the two core pillars
        of the dual-pipeline architecture.  Sensationalism and framing add
        nuance (0.15 each) without dominating the score.
    """
    raw = (
        (1.0 - bias_score) * 0.35
        + trust_score * 0.35
        + (1.0 - sensationalism) * 0.15
        + (1.0 - framing_deviation) * 0.15
    )
    score = round(raw * 100, 1)
    return min(max(score, 0.0), 100.0)


# ═══════════════════════════════════════════════════
# §2.5 — Political Lean Score
# ═══════════════════════════════════════════════════


def compute_political_lean(
    source_bias_numeric: float,
    framing_lean: float,
) -> float:
    """Compute political lean ∈ [-1, 1].

    Formula:
        L = source_bias × 0.60 + framing_lean × 0.40

    Parameters:
        source_bias_numeric ∈ [-1, 1]:
            From source credibility database.
            far-left=-1.0, left=-0.67, center-left=-0.33, center=0.0,
            center-right=0.33, right=0.67, far-right=1.0.

        framing_lean ∈ [-1, 1]:
            Frame-specific lean × frame confidence:
              pro-government    → +0.5 (current Indian context → rightward)
              anti-government   → -0.3
              pro-opposition    → -0.5
              communal/divisive → +0.3
              nationalistic     → +0.4
              neutral           →  0.0

    Interpretation:
        L > +0.25  → "right"
        L < -0.25  → "left"
        else       → "center"

    Note: Political lean is primarily a SOURCE property, not an article
    sentiment property.  Positive sentiment ≠ right-leaning.
    """
    score = source_bias_numeric * 0.60 + framing_lean * 0.40
    return round(max(-1.0, min(1.0, score)), 3)


# ═══════════════════════════════════════════════════
# §6 — Cross-Source Story Metrics
# ═══════════════════════════════════════════════════


def compute_source_diversity_score(
    unique_sources: int,
    expected_max: int = 10,
) -> float:
    """Source diversity for a story cluster ∈ [0, 1].

    Formula:
        D = min(unique_sources / expected_max, 1.0)

    Higher diversity → more perspectives → better-informed reader.
    expected_max=10 based on typical major Indian English outlets
    covering a national story.
    """
    if expected_max <= 0:
        return 0.0
    return round(min(unique_sources / expected_max, 1.0), 3)


def compute_consensus_score(
    verdicts: list[str],
) -> float:
    """Cross-source claim consensus ∈ [0, 1].

    Formula:
        C = count(majority_verdict) / total_verdicts

    If all sources agree on claims → C = 1.0 (high consensus).
    If sources disagree → C approaches 1/K where K = number of verdicts.
    """
    if not verdicts:
        return 0.5

    from collections import Counter

    counts = Counter(verdicts)
    majority_count = counts.most_common(1)[0][1]
    return round(majority_count / len(verdicts), 3)


# ═══════════════════════════════════════════════════
# Methodology metadata (served via API)
# ═══════════════════════════════════════════════════

SCORING_METHODOLOGY = {
    "version": "2.1.0",
    "bias_score": {
        "range": "[0, 1]",
        "formula": "B = s×0.15 + t×0.35 + d×0.20 + f×0.30",
        "components": {
            "sentiment_extremity": {"weight": 0.15, "range": "[0, 1]"},
            "bias_type_severity": {"weight": 0.35, "range": "[0, 1]"},
            "token_bias_density": {"weight": 0.20, "range": "[0, 1]"},
            "framing_deviation": {"weight": 0.30, "range": "[0, 1]"},
        },
        "models": [
            "VADER (Hutto & Gilbert 2014)",
            "cardiffnlp/twitter-roberta-base-sentiment-latest",
            "facebook/bart-large-mnli (zero-shot multi-label bias + framing)",
        ],
        "bias_type_thresholds": {
            "political bias": 0.35,
            "sensationalism": 0.40,
            "loaded language (hypothesis: emotionally manipulative or inflammatory wording)": 0.85,
            "framing bias": 0.45,
            "omission bias": 0.40,
            "note": "Per-label softmax thresholds on BART-MNLI scores; 'loaded language' uses the more specific NLI hypothesis 'emotionally manipulative or inflammatory wording' to reduce false positives on neutral text. See unbias.BIAS_TYPE_THRESHOLDS.",
        },
    },
    "trust_score": {
        "range": "[0, 1]",
        "formula": "T = e×0.50 + s×0.30 + c×0.20",
        "components": {
            "evidence_trust": {"weight": 0.50, "range": "[0, 1]"},
            "source_trust": {"weight": 0.30, "range": "{0.3, 0.5, 0.6, 0.9}"},
            "coverage_score": {"weight": 0.20, "range": "[0, 1]"},
        },
        "models": [
            "facebook/bart-large-mnli (two-pass zero-shot check-worthiness + NLI verification)",
            "ddgs (DuckDuckGo) evidence search, region in-en",
            "Google Fact Check Tools API (optional)",
        ],
    },
    "checkworthiness": {
        "model": "facebook/bart-large-mnli (same weights as NLI; single load)",
        "pass1": {
            "labels": ["verifiable factual claim", "opinion or commentary"],
            "threshold": 0.45,
            "top_k_candidates": 8,
        },
        "pass2": {
            "labels": ["factual claim", "opinion/other"],
            "combined": "0.35 × pass1_score + 0.65 × pass2_score",
            "threshold": 0.50,
            "max_claims_returned": 5,
        },
        "code": "app.services.claimbuster.get_checkworthy_claims",
    },
    "reliability_score": {
        "range": "[0, 100]",
        "formula": "R = [(1-B)×0.35 + T×0.35 + (1-S)×0.15 + (1-F)×0.15] × 100",
        "components": {
            "bias_inversion": {"weight": 0.35},
            "trust": {"weight": 0.35},
            "sensationalism_penalty": {"weight": 0.15},
            "framing_neutrality": {"weight": 0.15},
        },
        "interpretation": {
            "80-100": "Highly reliable",
            "60-80": "Moderately reliable",
            "40-60": "Mixed reliability",
            "20-40": "Low reliability",
            "0-20": "Very low reliability",
        },
    },
    "political_lean": {
        "range": "[-1, 1]",
        "formula": "L = source_bias×0.60 + framing_lean×0.40",
        "labels": {"right": "> 0.25", "center": "[-0.25, 0.25]", "left": "< -0.25"},
        "note": "Lean is primarily a source property, not article sentiment.",
    },
}
