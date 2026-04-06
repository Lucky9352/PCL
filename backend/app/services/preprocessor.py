"""Preprocessing pipeline — text cleaning, NLP, language detection, semantic dedup."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.core import get_settings
from app.core.logging import logger

# Lazy-loaded NLP models
_spacy_nlp = None
_sentence_model = None


def _get_spacy():
    """Lazy-load spaCy model."""
    global _spacy_nlp
    if _spacy_nlp is None:
        import spacy

        try:
            _spacy_nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spaCy model not found. Run: python -m spacy download en_core_web_sm")
            _spacy_nlp = spacy.blank("en")
    return _spacy_nlp


def _get_sentence_model():
    """Lazy-load sentence-transformers model for semantic dedup."""
    global _sentence_model
    if _sentence_model is None:
        try:
            from sentence_transformers import SentenceTransformer

            settings = get_settings()
            device = settings.resolved_device
            _sentence_model = SentenceTransformer("all-MiniLM-L6-v2", device=device)
            logger.info(f"Sentence-transformers loaded on device: {device}")
        except ImportError:
            logger.warning("sentence-transformers not installed")
            _sentence_model = None
    return _sentence_model


# ═══════════════════════════════════════════════════
# Step 1 — Text Cleaning
# ═══════════════════════════════════════════════════


def clean_text(text: str) -> str:
    """Remove HTML tags, normalize Unicode, collapse whitespace."""
    if not text:
        return ""

    # Strip HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Normalize Unicode (NFC form)
    text = unicodedata.normalize("NFC", text)

    # Normalize quotes and dashes
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    text = text.replace("\u00a0", " ")  # non-breaking space

    # Remove zero-width characters
    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)

    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


# ═══════════════════════════════════════════════════
# Step 2 — NLP Preprocessing (spaCy)
# ═══════════════════════════════════════════════════


def extract_nlp_features(text: str) -> dict[str, Any]:
    """Extract NER, noun phrases, key verbs, and sentences using spaCy.

    Returns:
        Dict with entities, noun_phrases, key_verbs, sentences.
    """
    nlp = _get_spacy()
    doc = nlp(text)

    # Named entities grouped by label
    entities: dict[str, list[str]] = {}
    for ent in doc.ents:
        if ent.label_ in ("PERSON", "ORG", "GPE", "LOC", "PER"):
            label = ent.label_
            if label not in entities:
                entities[label] = []
            if ent.text not in entities[label]:
                entities[label].append(ent.text)

    # Noun phrases
    noun_phrases = list({chunk.text for chunk in doc.noun_chunks})

    # Key verbs (lemmatized)
    key_verbs = list({token.lemma_ for token in doc if token.pos_ == "VERB" and not token.is_stop})

    # Sentences
    sentences = [sent.text.strip() for sent in doc.sents]

    return {
        "entities": entities,
        "noun_phrases": noun_phrases[:20],  # Cap to top 20
        "key_verbs": key_verbs[:15],
        "sentences": sentences,
    }


# ═══════════════════════════════════════════════════
# Step 3 — Language Detection
# ═══════════════════════════════════════════════════


def detect_language(text: str) -> str:
    """Detect the language of the text.

    Returns:
        Language code (e.g. 'en', 'hi', 'ta').
    """
    try:
        from langdetect import detect

        return detect(text)
    except Exception:
        return "unknown"


# ═══════════════════════════════════════════════════
# Step 4 — Semantic Deduplication
# ═══════════════════════════════════════════════════


def compute_embedding(text: str):
    """Compute sentence embedding for deduplication."""
    model = _get_sentence_model()
    if model is None:
        return None

    return model.encode(text, convert_to_tensor=True, show_progress_bar=False)


def check_semantic_duplicate(
    new_embedding,
    existing_embeddings: list,
    threshold: float = 0.92,
) -> tuple[bool, float]:
    """Check if new article is semantically similar to existing ones.

    Args:
        new_embedding: Embedding of the new article.
        existing_embeddings: List of embeddings from recent articles.
        threshold: Cosine similarity threshold (> = duplicate).

    Returns:
        Tuple of (is_duplicate, max_similarity_score).
    """
    if new_embedding is None or not existing_embeddings:
        return False, 0.0

    try:
        from sentence_transformers import util

        max_sim = 0.0
        for existing in existing_embeddings:
            sim = util.cos_sim(new_embedding, existing).item()
            if sim > max_sim:
                max_sim = sim

        return max_sim > threshold, max_sim
    except Exception as e:
        logger.warning(f"Semantic dedup check failed: {e}")
        return False, 0.0


# ═══════════════════════════════════════════════════
# Step 5 — Full preprocessing pipeline
# ═══════════════════════════════════════════════════


def preprocess_article(title: str, synopsis: str) -> dict[str, Any]:
    """Run full preprocessing pipeline on an article.

    Args:
        title: Article title.
        synopsis: Article content/synopsis.

    Returns:
        Dict with cleaned text, NLP features, language.
    """
    # Clean
    clean_title = clean_text(title)
    clean_synopsis = clean_text(synopsis)
    full_text = f"{clean_title}. {clean_synopsis}"

    # NLP features
    nlp_features = extract_nlp_features(full_text)

    # Language
    language = detect_language(full_text)

    return {
        "clean_title": clean_title,
        "clean_synopsis": clean_synopsis,
        "entities": nlp_features["entities"],
        "noun_phrases": nlp_features["noun_phrases"],
        "language": language,
        "sentences": nlp_features["sentences"],
    }
