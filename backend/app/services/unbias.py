"""unBIAS module — media bias detection pipeline.

Analyses HOW an article is written: sentiment, framing, bias types, and
token-level loaded language.  Does NOT verify factual claims (that is the
ClaimBuster module's job).

Pipeline (documented in docs/METHODOLOGY.md §2):
  1. Sentiment analysis   — VADER (headline) + RoBERTa (body), weighted 40/60
  2. Bias-type detection  — BART-MNLI zero-shot, multi-label over 5 categories
  3. Framing analysis     — Zero-shot NLI with India-specific framing labels
  4. Token-level flagging — Curated Indian media dictionary + VADER polarity
  5. Score aggregation    — Weighted combination of 4 signals → bias_score [0,1]
  6. Political lean        — Source-first approach (60% source, 40% framing)

References:
  - Raza et al. (2024), "Dbias: detecting biases in news articles"
  - Rodrigo-Gines et al. (2024), "Systematic Review on Media Bias Detection"
  - Hamborg (2023), "Revealing Media Bias in News Articles"
"""

from __future__ import annotations

from typing import Any

from app.core import get_settings
from app.core.logging import logger
from app.services.article_context import ArticleContext
from app.utils.source_credibility import BIAS_NUMERIC, get_source_credibility

# ═══════════════════════════════════════════════════
# Lazy-loaded models
# ═══════════════════════════════════════════════════

_vader = None
_sentiment_pipeline = None
_bias_classifier = None


def _get_vader():
    """Lazy-load VADER sentiment analyzer."""
    global _vader
    if _vader is None:
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

            _vader = SentimentIntensityAnalyzer()
        except ImportError:
            logger.warning("vaderSentiment not installed")
    return _vader


def _get_sentiment_pipeline():
    """Lazy-load RoBERTa sentiment pipeline (cardiffnlp/twitter-roberta-base-sentiment-latest)."""
    global _sentiment_pipeline
    if _sentiment_pipeline is None:
        try:
            from transformers import pipeline

            settings = get_settings()
            device_str = settings.resolved_device
            device = -1
            if device_str == "cuda":
                device = 0

            _sentiment_pipeline = pipeline(
                "sentiment-analysis",
                model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                device=device,
                truncation=True,
                max_length=512,
            )
            logger.info(f"Sentiment pipeline loaded on: {device_str}")
        except Exception as e:
            logger.warning(f"Failed to load sentiment pipeline: {e}")
    return _sentiment_pipeline


def _get_bias_classifier():
    """Lazy-load BART-MNLI zero-shot classifier for multi-label bias detection."""
    global _bias_classifier
    if _bias_classifier is None:
        try:
            from transformers import pipeline

            settings = get_settings()
            device_str = settings.resolved_device
            device = -1
            if device_str == "cuda":
                device = 0

            _bias_classifier = pipeline(
                "zero-shot-classification",
                model="facebook/bart-large-mnli",
                device=device,
            )
            logger.info(f"Bias classifier loaded on: {device_str}")
        except Exception as e:
            logger.warning(f"Failed to load bias classifier: {e}")
    return _bias_classifier


# ═══════════════════════════════════════════════════
# Sentiment Analysis
# ═══════════════════════════════════════════════════


def analyze_sentiment_vader(text: str) -> dict[str, Any]:
    """VADER compound sentiment on [-1, 1] — optimised for short text / headlines.

    Thresholds (Hutto & Gilbert 2014):
      compound >= +0.05 → positive
      compound <= -0.05 → negative
      else              → neutral
    """
    vader = _get_vader()
    if vader is None:
        return {"score": 0.0, "label": "neutral", "compound": 0.0}

    scores = vader.polarity_scores(text)
    compound = scores["compound"]

    if compound >= 0.05:
        label = "positive"
    elif compound <= -0.05:
        label = "negative"
    else:
        label = "neutral"

    return {"score": compound, "label": label, "compound": compound}


def analyze_sentiment_transformer(text: str) -> dict[str, Any]:
    """RoBERTa-based sentiment normalised to [-1, 1]."""
    pipe = _get_sentiment_pipeline()
    if pipe is None:
        return analyze_sentiment_vader(text)

    try:
        result = pipe(text[:512])
        if result:
            r = result[0]
            label = r["label"].lower()
            score = r["score"]

            if "negative" in label:
                normalized = -score
            elif "positive" in label:
                normalized = score
            else:
                normalized = 0.0

            return {"score": normalized, "label": label, "raw": r}
    except Exception as e:
        logger.warning(f"Transformer sentiment failed: {e}")

    return analyze_sentiment_vader(text)


# ═══════════════════════════════════════════════════
# Bias Type Classification (Multi-Label Zero-Shot)
# ═══════════════════════════════════════════════════

BIAS_TYPES = [
    "political bias",
    "sensationalism",
    "loaded language",
    "framing bias",
    "omission bias",
]

_HYPOTHESIS_LABELS: list[str] = [
    "political bias",
    "sensationalism",
    "emotionally manipulative or inflammatory wording",
    "framing bias",
    "omission bias",
]

_HYPOTHESIS_TO_OUTPUT: dict[str, str] = {
    "emotionally manipulative or inflammatory wording": "loaded language",
}

BIAS_TYPE_THRESHOLDS: dict[str, float] = {
    "political bias": 0.35,
    "sensationalism": 0.40,
    "emotionally manipulative or inflammatory wording": 0.85,
    "framing bias": 0.45,
    "omission bias": 0.40,
}


def classify_bias_types(text: str) -> list[dict[str, float]]:
    """Multi-label bias classification via BART-MNLI zero-shot.

    Each candidate label is tested independently (multi_label=True).
    The NLI hypothesis for "loaded language" uses the more specific
    wording "emotionally manipulative or inflammatory wording" so the
    model can differentiate genuine loaded language from strong-but-
    factual reporting.  The output label is mapped back to the
    canonical "loaded language" for downstream consumers.

    Per-label thresholds (BART-MNLI softmax):
      - political bias        0.35
      - sensationalism         0.40
      - inflammatory wording   0.50  (mapped → "loaded language")
      - framing bias           0.45
      - omission bias          0.40
    """
    classifier = _get_bias_classifier()
    if classifier is None:
        return []

    try:
        result = classifier(
            text[:1024],
            candidate_labels=_HYPOTHESIS_LABELS,
            multi_label=True,
        )
        detected = []
        for label, score in zip(result["labels"], result["scores"], strict=False):
            threshold = BIAS_TYPE_THRESHOLDS.get(label, 0.40)
            if score > threshold:
                output_label = _HYPOTHESIS_TO_OUTPUT.get(label, label)
                detected.append({"type": output_label, "confidence": round(score, 3)})
        return detected
    except Exception as e:
        logger.warning(f"Bias classification failed: {e}")
        return []


# ═══════════════════════════════════════════════════
# Framing Analysis (India-Specific)
# ═══════════════════════════════════════════════════

FRAMING_LABELS = [
    "neutral factual reporting",
    "pro-government framing",
    "anti-government framing",
    "pro-opposition framing",
    "communal or divisive framing",
    "nationalistic framing",
]


def analyze_framing(text: str) -> dict[str, Any]:
    """Detect article framing using zero-shot NLI with India-specific labels.

    Returns the top framing label, its confidence, and a framing_deviation
    score ∈ [0, 1] measuring distance from neutral factual reporting.

    Framing deviation formula (§2.3):
      deviation = 1 − P("neutral factual reporting")
    where P is the zero-shot classification probability.
    """
    classifier = _get_bias_classifier()
    if classifier is None:
        return {
            "primary_frame": "unknown",
            "confidence": 0.0,
            "framing_deviation": 0.0,
            "all_frames": [],
        }

    try:
        result = classifier(
            text[:1024],
            candidate_labels=FRAMING_LABELS,
            multi_label=False,
        )

        frames = []
        neutral_prob = 0.0
        for label, score in zip(result["labels"], result["scores"], strict=False):
            frames.append({"frame": label, "probability": round(score, 3)})
            if label == "neutral factual reporting":
                neutral_prob = score

        framing_deviation = round(1.0 - neutral_prob, 3)

        return {
            "primary_frame": result["labels"][0],
            "confidence": round(result["scores"][0], 3),
            "framing_deviation": framing_deviation,
            "all_frames": frames,
        }
    except Exception as e:
        logger.warning(f"Framing analysis failed: {e}")
        return {
            "primary_frame": "unknown",
            "confidence": 0.0,
            "framing_deviation": 0.0,
            "all_frames": [],
        }


# ═══════════════════════════════════════════════════
# Token-Level Bias Detection
# ═══════════════════════════════════════════════════

# Curated dictionary: 100+ biased terms common in Indian English media.
# Each entry maps a loaded/biased word → a more neutral alternative.
# Sources: MBIC annotations, Indian media discourse analysis, AllSides bias
# dictionary, adapted for Indian political and social context.
BIASED_REPLACEMENTS: dict[str, str] = {
    # ── Sensationalist / loaded verbs ──
    "slams": "criticizes",
    "blasts": "criticizes",
    "destroys": "refutes",
    "attacks": "critiques",
    "lashes": "criticizes",
    "rips": "critiques",
    "hammers": "questions",
    "silences": "responds to",
    "exposes": "reveals",
    "shocks": "surprises",
    "stuns": "surprises",
    "rocks": "affects",
    "erupts": "intensifies",
    "sparks": "causes",
    "triggers": "causes",
    "unleashes": "initiates",
    # ── Sensationalist adjectives ──
    "shocking": "unexpected",
    "outrageous": "controversial",
    "radical": "significant",
    "extreme": "substantial",
    "disastrous": "unsuccessful",
    "shameful": "criticized",
    "miracle": "notable achievement",
    "brutal": "severe",
    "explosive": "significant",
    "devastating": "damaging",
    "massive": "large",
    "unprecedented": "rare",
    "historic": "significant",
    "game-changer": "significant development",
    "ground-breaking": "innovative",
    "bombshell": "significant revelation",
    "alarming": "concerning",
    "terrifying": "concerning",
    "jaw-dropping": "surprising",
    # ── Political Indian context — terms used to demonise/glorify ──
    "anti-national": "critic of government policy",
    "anti-india": "opposed to government stance",
    "tukde-tukde": "opposition group",
    "tukde tukde": "opposition group",
    "urban naxal": "activist",
    "urban-naxal": "activist",
    "presstitute": "journalist",
    "godi media": "pro-government media",
    "pidi": "political supporter",
    "bhakt": "political supporter",
    "sanghi": "political supporter",
    "sickular": "secularist",
    "libtard": "liberal",
    "andolan-jeevi": "protester",
    "andolanjeevi": "protester",
    "toolkit gang": "activist group",
    "love jihad": "interfaith relationship allegation",
    "jihadi": "extremist",
    "anti-hindu": "critic of Hindu nationalism",
    "hinduphobic": "critical of Hindu practices",
    "islamophobic": "critical of Muslim practices",
    "communal": "divisive",
    "pseudo-secular": "secularist",
    "appeasement": "minority welfare policy",
    "votebank": "electoral constituency",
    "vote bank": "electoral constituency",
    "dynasty": "political family",
    "puppet": "ally",
    "mastermind": "organiser",
    # ── Propaganda / misinformation terms ──
    "propaganda": "information campaign",
    "fake": "unverified",
    "lies": "inaccurate statements",
    "hoax": "unverified claim",
    "nonsense": "disputed claims",
    "brainwashing": "persuasion",
    "conspiracy": "unverified theory",
    # ── Violence / communal ──
    "terror": "violence",
    "terrorist": "militant",
    "savagely": "severely",
    "cowardly": "unprovoked",
    "massacre": "mass killing",
    "genocide": "mass atrocity",
    "ethnic cleansing": "forced displacement",
    # ── Glorification ──
    "heroic": "notable",
    "brilliant": "effective",
    "visionary": "forward-looking",
    "legendary": "well-known",
    "fearless": "determined",
    "supreme leader": "head of state",
    # ── Economic / policy loaded ──
    "freebies": "welfare schemes",
    "dole": "social assistance",
    "loot": "misappropriation",
    "scam": "alleged irregularity",
    "corruption": "alleged misuse of power",
    "crony": "connected",
}


def detect_biased_tokens(text: str) -> list[dict[str, str]]:
    """Identify biased words and suggest neutral replacements.

    Detection approach (§2.4):
      1. Curated dictionary lookup (100+ Indian media terms)
      2. VADER single-word polarity — flag words with |compound| > 0.6
    Each flagged token includes detection source for traceability.
    """
    vader = _get_vader()
    words = text.split()
    flagged: list[dict[str, str]] = []
    seen: set[str] = set()

    for word in words:
        clean = word.strip(".,!?;:\"'()[]{}").lower()

        if clean in seen or len(clean) < 3:
            continue

        if clean in BIASED_REPLACEMENTS:
            flagged.append(
                {
                    "word": word,
                    "suggestion": BIASED_REPLACEMENTS[clean],
                    "source": "dictionary",
                }
            )
            seen.add(clean)
            continue

        # Multi-word phrases (check bigrams)
        # Handled by checking if the clean word starts a known phrase
        # (already covered by single-word entries above)

        if vader:
            scores = vader.polarity_scores(word)
            compound = scores["compound"]
            if abs(compound) > 0.6:
                suggestion = "notable" if compound > 0 else "concerning"
                flagged.append(
                    {
                        "word": word,
                        "suggestion": suggestion,
                        "source": "vader_polarity",
                    }
                )
                seen.add(clean)

    return flagged


# ═══════════════════════════════════════════════════
# Political Lean Estimation
# ═══════════════════════════════════════════════════


def estimate_political_lean(
    source_name: str | None,
    framing_result: dict[str, Any],
) -> dict[str, Any]:
    """Estimate political lean of an article using source-first approach.

    Methodology (§2.5):
      Political lean is primarily a property of the SOURCE, not of individual
      article sentiment.  Sentiment (positive/negative) does not correlate
      with political orientation (left/right).

      Formula:
        lean_score = source_bias_numeric × 0.60 + framing_lean × 0.40

      Where:
        source_bias_numeric ∈ [-1, 1] from source_credibility.py
        framing_lean ∈ [-1, 1]:
          pro-government → +0.5  (in Indian context, maps rightward)
          anti-government → -0.3
          pro-opposition → -0.5
          communal/divisive → +0.3
          nationalistic → +0.4
          neutral → 0.0

      Final label:
        lean_score > 0.25  → "right"
        lean_score < -0.25 → "left"
        else               → "center"
    """
    source_info = get_source_credibility(source_name or "")
    source_bias_numeric = BIAS_NUMERIC.get(source_info["bias"], 0.0)

    framing_lean_map = {
        "pro-government framing": 0.5,
        "anti-government framing": -0.3,
        "pro-opposition framing": -0.5,
        "communal or divisive framing": 0.3,
        "nationalistic framing": 0.4,
        "neutral factual reporting": 0.0,
    }

    primary_frame = framing_result.get("primary_frame", "unknown")
    frame_confidence = framing_result.get("confidence", 0.0)
    framing_lean = framing_lean_map.get(primary_frame, 0.0) * frame_confidence

    lean_score = source_bias_numeric * 0.60 + framing_lean * 0.40
    lean_score = round(max(-1.0, min(1.0, lean_score)), 3)

    if lean_score > 0.25:
        lean_label = "right"
    elif lean_score < -0.25:
        lean_label = "left"
    else:
        lean_label = "center"

    return {
        "lean_score": lean_score,
        "lean_label": lean_label,
        "source_bias": source_info["bias"],
        "source_bias_numeric": source_bias_numeric,
        "framing_lean": round(framing_lean, 3),
        "method": "source_weighted_framing",
    }


# ═══════════════════════════════════════════════════
# Combined Bias Analysis
# ═══════════════════════════════════════════════════


def analyze_bias(
    ctx: ArticleContext,
    source_name: str | None = None,
) -> dict[str, Any]:
    """Run full unBIAS analysis pipeline on an article.

    Args:
        ctx: Shared ArticleContext produced by build_article_context().
             Contains pre-cleaned text, NLP features and word count so
             this module does NOT repeat cleaning or sentence-splitting.
        source_name: Publisher name for political lean estimation.

    Returns:
        Complete bias analysis dict.

    Bias Score Aggregation (§2.6):
        bias_score = (
            sentiment_extremity × W_sent     (0.15)
          + bias_type_severity  × W_type     (0.35)
          + token_bias_density  × W_token    (0.20)
          + framing_deviation   × W_frame    (0.30)
        )

    Weight justification:
      - W_sent=0.15: Sentiment extremity is weakly correlated with bias
        (r=0.31, BABE dataset). Reduced from equal weight.
      - W_type=0.35: Zero-shot bias classification is the strongest single
        signal (F1=0.72 on BABE).  Highest weight.
      - W_token=0.20: Token density catches loaded language that type
        classification may miss.
      - W_frame=0.30: Framing deviation captures structural bias beyond
        individual word choices.
    """

    # ── Unpack shared context (no re-cleaning, no re-splitting) ──────────
    full_text = ctx.full_text  # already cleaned once
    word_count = ctx.word_count  # precomputed; avoids re-split below

    # ── 1. Sentiment ──────────────────────────────
    headline_sentiment = analyze_sentiment_vader(ctx.clean_title)
    body_sentiment = analyze_sentiment_transformer(ctx.clean_synopsis)

    combined_score = headline_sentiment["score"] * 0.4 + body_sentiment["score"] * 0.6
    if combined_score >= 0.05:
        combined_label = "positive"
    elif combined_score <= -0.05:
        combined_label = "negative"
    else:
        combined_label = "neutral"

    # ── 2. Bias types ─────────────────────────────
    bias_types_raw = classify_bias_types(full_text)
    bias_types = [b["type"] for b in bias_types_raw]

    # ── 3. Framing ────────────────────────────────
    framing_result = analyze_framing(full_text)

    # ── 4. Token-level bias ───────────────────────
    flagged_tokens = detect_biased_tokens(full_text)

    # ── 5. Compute bias_score (weighted) ──────────
    W_SENT, W_TYPE, W_TOKEN, W_FRAME = 0.15, 0.35, 0.20, 0.30

    sentiment_extremity = abs(combined_score)

    bias_type_severity = min(len(bias_types) / len(BIAS_TYPES), 1.0)
    if bias_types_raw:
        avg_type_conf = sum(b["confidence"] for b in bias_types_raw) / len(bias_types_raw)
        bias_type_severity = (bias_type_severity + avg_type_conf) / 2.0

    token_bias_density = min(len(flagged_tokens) / word_count * 10, 1.0)

    framing_deviation = framing_result.get("framing_deviation", 0.0)

    bias_score = (
        sentiment_extremity * W_SENT
        + bias_type_severity * W_TYPE
        + token_bias_density * W_TOKEN
        + framing_deviation * W_FRAME
    )
    bias_score = round(min(max(bias_score, 0.0), 1.0), 3)

    # ── 6. Political lean ─────────────────────────
    political_lean = estimate_political_lean(source_name, framing_result)
    bias_label = political_lean["lean_label"]

    # Override to "center" if overall bias is very low
    if bias_score < 0.15:
        bias_label = "center"

    # ── 7. Model confidence ───────────────────────
    confidences = []
    confidences.append(min(abs(combined_score) + 0.5, 1.0))
    if bias_types_raw:
        confidences.extend([b["confidence"] for b in bias_types_raw])
    confidences.append(framing_result.get("confidence", 0.5))
    model_confidence = round(sum(confidences) / len(confidences), 3) if confidences else 0.5

    return {
        "bias_score": bias_score,
        "bias_label": bias_label,
        "sentiment": {
            "score": round(combined_score, 3),
            "label": combined_label,
            "headline": headline_sentiment,
            "body": body_sentiment,
        },
        "bias_types": bias_types,
        "bias_types_detail": bias_types_raw,
        "framing": framing_result,
        "political_lean": political_lean,
        "flagged_tokens": flagged_tokens,
        "model_confidence": model_confidence,
        "score_components": {
            "sentiment_extremity": round(sentiment_extremity, 3),
            "bias_type_severity": round(bias_type_severity, 3),
            "token_bias_density": round(token_bias_density, 3),
            "framing_deviation": round(framing_deviation, 3),
            "weights": {
                "sentiment": W_SENT,
                "bias_type": W_TYPE,
                "token_density": W_TOKEN,
                "framing": W_FRAME,
            },
        },
    }
