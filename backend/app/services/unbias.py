"""unBIAS module — media bias detection pipeline.

Hybrid approach:
  1. VADER for headline sentiment
  2. Transformer-based sentiment (cardiffnlp/twitter-roberta-base-sentiment-latest)
  3. Bias type classification (multi-label)
  4. Dbias for token-level bias detection
  5. Combined bias scoring
"""

from __future__ import annotations

from typing import Any

from app.core import get_settings
from app.core.logging import logger

# Lazy-loaded models
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
    """Lazy-load HuggingFace sentiment analysis pipeline."""
    global _sentiment_pipeline
    if _sentiment_pipeline is None:
        try:
            from transformers import pipeline

            settings = get_settings()
            device_str = settings.resolved_device
            # Map device string to pipeline device arg
            device = -1  # CPU
            if device_str == "cuda":
                device = 0
            elif device_str == "mps":
                device = -1  # MPS handled via torch default

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
    """Lazy-load zero-shot bias classifier for multi-label classification."""
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
    """VADER sentiment — good for short text / headlines.

    Returns:
        {"score": float (-1 to 1), "label": str, "compound": float}
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
    """Transformer-based sentiment analysis.

    Returns:
        {"score": float (-1 to 1), "label": str, "raw": dict}
    """
    pipe = _get_sentiment_pipeline()
    if pipe is None:
        return analyze_sentiment_vader(text)  # Fallback to VADER

    try:
        result = pipe(text[:512])  # Truncate to model max
        if result:
            r = result[0]
            label = r["label"].lower()
            score = r["score"]

            # Normalize to -1 to 1 scale
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
# Bias Type Classification (Multi-Label)
# ═══════════════════════════════════════════════════

BIAS_TYPES = [
    "political bias",
    "sensationalism",
    "loaded language",
    "framing bias",
    "omission bias",
]


def classify_bias_types(text: str) -> list[dict[str, float]]:
    """Multi-label bias classification using zero-shot NLI.

    Returns:
        List of detected bias types with confidence scores.
    """
    classifier = _get_bias_classifier()
    if classifier is None:
        return []

    try:
        result = classifier(
            text[:1024],
            candidate_labels=BIAS_TYPES,
            multi_label=True,
        )
        detected = []
        for label, score in zip(result["labels"], result["scores"], strict=False):
            if score > 0.3:  # Threshold for detection
                detected.append({"type": label, "confidence": round(score, 3)})
        return detected
    except Exception as e:
        logger.warning(f"Bias classification failed: {e}")
        return []


# ═══════════════════════════════════════════════════
# Dbias — Token-Level Bias Detection
# ═══════════════════════════════════════════════════


def detect_biased_tokens(text: str) -> list[dict[str, str]]:
    """Use Dbias to find biased words and suggest replacements.

    Returns:
        List of {"word": str, "suggestion": str} dicts.
    """
    try:
        from Dbias.text_debiasing import debias_text

        result = debias_text(text)
        if isinstance(result, dict) and "debiased_text" in result:
            # Compare original vs debiased to find changed tokens
            original_words = text.split()
            debiased_words = result["debiased_text"].split()

            flagged = []
            for orig, deb in zip(original_words, debiased_words, strict=False):
                if orig.lower() != deb.lower():
                    flagged.append({"word": orig, "suggestion": deb})

            return flagged
    except ImportError:
        logger.warning("Dbias not installed — skipping token-level bias detection")
    except Exception as e:
        logger.warning(f"Dbias failed: {e}")

    return []


# ═══════════════════════════════════════════════════
# Combined Bias Analysis
# ═══════════════════════════════════════════════════


def analyze_bias(title: str, synopsis: str) -> dict[str, Any]:
    """Run full unBIAS analysis pipeline on an article.

    Args:
        title: Article headline.
        synopsis: Article body text.

    Returns:
        Full bias analysis dict matching the output schema.
    """
    full_text = f"{title}. {synopsis}"

    # Sentiment: use VADER for headline, transformer for body
    headline_sentiment = analyze_sentiment_vader(title)
    body_sentiment = analyze_sentiment_transformer(synopsis)

    # Combined sentiment (weighted: 40% headline, 60% body)
    combined_score = headline_sentiment["score"] * 0.4 + body_sentiment["score"] * 0.6
    if combined_score >= 0.05:
        combined_label = "positive"
    elif combined_score <= -0.05:
        combined_label = "negative"
    else:
        combined_label = "neutral"

    # Bias type classification
    bias_types_raw = classify_bias_types(full_text)
    bias_types = [b["type"] for b in bias_types_raw]

    # Token-level bias (Dbias)
    flagged_tokens = detect_biased_tokens(full_text)

    # Compute overall bias score (0-1, higher = more biased)
    bias_signals = []

    # Signal 1: Sentiment extremity (far from neutral = potentially biased)
    sentiment_bias = abs(combined_score)
    bias_signals.append(sentiment_bias)

    # Signal 2: Number of bias types detected
    type_bias = min(len(bias_types) / len(BIAS_TYPES), 1.0)
    bias_signals.append(type_bias)

    # Signal 3: Flagged tokens ratio
    word_count = len(full_text.split())
    token_bias = min(len(flagged_tokens) / max(word_count, 1) * 10, 1.0)
    bias_signals.append(token_bias)

    # Signal 4: Bias type confidence average
    if bias_types_raw:
        avg_conf = sum(b["confidence"] for b in bias_types_raw) / len(bias_types_raw)
        bias_signals.append(avg_conf)

    bias_score = sum(bias_signals) / len(bias_signals) if bias_signals else 0.0
    bias_score = round(min(max(bias_score, 0.0), 1.0), 3)

    # Determine bias label based on political bias detection
    # This is simplified — a production system would use a trained classifier
    bias_label = "unclassified"
    if "political bias" in bias_types:
        # Heuristic based on sentiment + known patterns
        if combined_score > 0.2:
            bias_label = "right"
        elif combined_score < -0.2:
            bias_label = "left"
        else:
            bias_label = "center"
    elif bias_score < 0.2:
        bias_label = "center"

    # Model confidence — average of all component confidences
    confidences = [1.0 - abs(0.5 - abs(combined_score))]  # Sentiment confidence
    if bias_types_raw:
        confidences.extend([b["confidence"] for b in bias_types_raw])
    model_confidence = round(sum(confidences) / len(confidences), 3)

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
        "flagged_tokens": flagged_tokens,
        "model_confidence": model_confidence,
    }
