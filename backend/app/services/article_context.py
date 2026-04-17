"""Shared article preprocessing context — computed ONCE, passed to both modules.

This module solves the redundant preprocessing problem: previously both
unBIAS (analyze_bias) and ClaimBuster (analyze_claims) independently ran:
  - full_text = f"{title}. {synopsis}"      ← duplicated
  - sentence splitting (re.split)            ← duplicated in claimbuster.py:100
  - text cleaning (clean_text)               ← not called at all by either
  - NLP features (extract_nlp_features)      ← not called at all by either
  - language detection (detect_language)     ← not called at all by either

ArticleContext is computed once by the caller (e.g. the analysis task/worker)
and injected into both analyze_bias() and analyze_claims(), eliminating all
redundant work.

Usage (in your task/worker layer):
    from app.services.article_context import build_article_context
    from app.services.unbias import analyze_bias
    from app.services.claimbuster import analyze_claims

    ctx = build_article_context(title, synopsis)
    bias_result    = analyze_bias(ctx, source_name=article.source_name)
    factcheck_result = await analyze_claims(ctx, source_name=article.source_name)
    aggregated     = aggregate_analysis(bias_result, factcheck_result)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.logging import logger
from app.services.preprocessor import clean_text, detect_language, extract_nlp_features


@dataclass
class ArticleContext:
    """Preprocessed metadata shared between unBIAS and ClaimBuster.

    Computed once per article by build_article_context(), then passed
    into analyze_bias() and analyze_claims() as a single argument.

    Attributes:
        title:          Original (raw) headline.
        synopsis:       Original (raw) body/synopsis.
        clean_title:    HTML-stripped, Unicode-normalised title.
        clean_synopsis: HTML-stripped, Unicode-normalised synopsis.
        full_text:      "{clean_title}. {clean_synopsis}" — the canonical
                        combined text string used by both modules.
        sentences:      Sentence-split list from spaCy (used by ClaimBuster
                        check-worthiness pass instead of inline re.split).
        entities:       spaCy NER dict keyed by label (PERSON, ORG, GPE…).
        noun_phrases:   Top-20 noun chunks from spaCy.
        language:       ISO 639-1 language code (e.g. "en", "hi").
        word_count:     Precomputed len(full_text.split()) — used by unBIAS
                        token_bias_density to avoid re-splitting.
        nlp_extras:     Any additional NLP fields returned by
                        extract_nlp_features() that are not promoted to
                        top-level attributes (forward-compatible).
    """

    title: str
    synopsis: str
    clean_title: str
    clean_synopsis: str
    full_text: str
    sentences: list[str]
    entities: dict[str, list[str]]
    noun_phrases: list[str]
    language: str
    word_count: int
    nlp_extras: dict[str, Any] = field(default_factory=dict)


def build_article_context(title: str, synopsis: str) -> ArticleContext:
    """Preprocess an article and return a shared ArticleContext.

    This is the single entry-point that replaces the duplicated
    preprocessing scattered across unbias.analyze_bias() and
    claimbuster.analyze_claims().

    Steps (mirrors preprocessor.preprocess_article but promotes fields):
      1. clean_text() on title and synopsis
      2. Combine → full_text
      3. extract_nlp_features() — spaCy NER, noun phrases, sentences
      4. detect_language()
      5. Compute word_count once

    Args:
        title:    Raw article headline.
        synopsis: Raw article body / synopsis.

    Returns:
        ArticleContext ready for injection into both analysis modules.
    """
    clean_title = clean_text(title)
    clean_synopsis = clean_text(synopsis)
    full_text = f"{clean_title}. {clean_synopsis}"

    nlp_features = extract_nlp_features(full_text)
    language = detect_language(full_text)
    word_count = max(len(full_text.split()), 1)

    # Promote known fields; keep the rest in nlp_extras for forward compat
    sentences: list[str] = nlp_features.pop("sentences", [])
    entities: dict[str, list[str]] = nlp_features.pop("entities", {})
    noun_phrases: list[str] = nlp_features.pop("noun_phrases", [])

    logger.debug(
        f"ArticleContext built — lang={language}, sentences={len(sentences)}, words={word_count}"
    )

    return ArticleContext(
        title=title,
        synopsis=synopsis,
        clean_title=clean_title,
        clean_synopsis=clean_synopsis,
        full_text=full_text,
        sentences=sentences,
        entities=entities,
        noun_phrases=noun_phrases,
        language=language,
        word_count=word_count,
        nlp_extras=nlp_features,  # key_verbs etc.
    )
