"""Claim extraction and verification module.

Hybrid local-first approach:
  1. Local Hybrid AI Pipeline (DistilBERT + BART-MNLI) for check-worthiness
  2. DuckDuckGo & Google Fact Check for evidence retrieval
  3. NLI-based verification (facebook/bart-large-mnli)
  4. Source credibility scoring
  5. Combined trust score
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core import get_settings
from app.core.logging import logger
from app.utils.source_credibility import get_source_credibility

# Lazy-loaded NLI model
_nli_pipeline = None


def _get_nli_pipeline():
    """Lazy-load NLI pipeline for claim verification."""
    global _nli_pipeline
    if _nli_pipeline is None:
        try:
            from transformers import pipeline

            settings = get_settings()
            device_str = settings.resolved_device
            device = -1
            if device_str == "cuda":
                device = 0

            _nli_pipeline = pipeline(
                "zero-shot-classification",
                model="facebook/bart-large-mnli",
                device=device,
            )
            logger.info(f"NLI pipeline loaded on: {device_str}")
        except Exception as e:
            logger.warning(f"Failed to load NLI pipeline: {e}")
    return _nli_pipeline


# Lazy-loaded Check-worthiness model
_checkworthiness_pipeline = None


def _get_checkworthiness_pipeline():
    """Lazy-load specialized DistilBERT model for check-worthiness detection."""
    global _checkworthiness_pipeline
    if _checkworthiness_pipeline is None:
        try:
            from transformers import pipeline

            settings = get_settings()
            device_str = settings.resolved_device
            device = -1
            if device_str == "cuda":
                device = 0

            _checkworthiness_pipeline = pipeline(
                "text-classification",
                model="cognotron/distilbert-base-cased-check-worthiness",
                device=device,
            )
            logger.info(f"Check-worthiness model loaded on: {device_str}")
        except Exception as e:
            logger.warning(f"Failed to load check-worthiness model: {e}")
    return _checkworthiness_pipeline


# ═══════════════════════════════════════════════════
# Local Check-Worthiness Pipeline (Hybrid)
# ═══════════════════════════════════════════════════


async def get_checkworthy_claims(text: str) -> list[dict[str, Any]]:
    """Identify check-worthy claims using a local hybrid pipeline.

    Stage 1: Fast ranking using a specialized transformer (DistilBERT).
    Stage 2: High-precision refinement using zero-shot NLI (BART).

    Returns:
        List of {"text": str, "score": float} sorted by score.
    """
    import re

    # 1. Clean and split into sentences
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 30]
    if not sentences:
        return []

    # Stage 1: Fast Transformer Scorer (DistilBERT)
    pipe = _get_checkworthiness_pipeline()
    candidates = []

    if pipe:
        try:
            # Batch processing candidates for speed
            results = pipe(sentences, truncation=True, max_length=128)
            for sentence, res in zip(sentences, results, strict=False):
                # The model usually returns LABEL_1 for check-worthy
                score = res["score"] if res["label"] == "LABEL_1" else 1.0 - res["score"]
                if score > 0.4:  # Initial threshold
                    candidates.append({"text": sentence, "s1_score": score})
        except Exception as e:
            logger.warning(f"Stage 1 check-worthiness failed: {e}")
            # Fallback to simple keyword density if model fails
            candidates = [{"text": s, "s1_score": 0.5} for s in sentences]
    else:
        candidates = [{"text": s, "s1_score": 0.5} for s in sentences]

    if not candidates:
        return []

    # Sort and take top 8 for Stage 2 (BART-MNLI refinement)
    candidates.sort(key=lambda x: x["s1_score"], reverse=True)
    top_candidates = candidates[:8]

    # Stage 2: Deep Refinement (BART-MNLI Zero-Shot)
    nli = _get_nli_pipeline()
    final_claims = []

    if nli:
        hypothesis = "This sentence contains a factual claim that should be fact-checked."
        for cand in top_candidates:
            try:
                res = nli(
                    cand["text"],
                    candidate_labels=["factual claim", "opinion/other"],
                    hypothesis=hypothesis,
                )
                # Weighted score: 40% Stage 1, 60% Stage 2
                s2_score = (
                    res["scores"][0] if res["labels"][0] == "factual claim" else res["scores"][1]
                )
                combined_score = (cand["s1_score"] * 0.4) + (s2_score * 0.6)

                if combined_score > 0.5:
                    final_claims.append({"text": cand["text"], "score": round(combined_score, 3)})
            except Exception as e:
                logger.warning(f"Stage 2 refinement failed for claim: {e}")
                final_claims.append({"text": cand["text"], "score": cand["s1_score"]})
    else:
        # If NLI is not available, just use Stage 1 results
        final_claims = [
            {"text": c["text"], "score": round(c["s1_score"], 3)} for c in top_candidates
        ]

    # Sort final results and take top 5
    final_claims.sort(key=lambda x: x["score"], reverse=True)
    return final_claims[:5]


# ═══════════════════════════════════════════════════
# Evidence Retrieval
# ═══════════════════════════════════════════════════


async def retrieve_evidence(claim_text: str) -> list[dict[str, str]]:
    """Retrieve evidence for a claim using DuckDuckGo search.

    Returns:
        List of {"title": str, "url": str, "snippet": str}.
    """
    try:
        from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = list(
                ddgs.text(
                    f"{claim_text} fact check",
                    max_results=5,
                    region="in-en",
                )
            )

        evidence = [
            {
                "title": r.get("title", ""),
                "url": r.get("href", r.get("link", "")),
                "snippet": r.get("body", r.get("snippet", "")),
            }
            for r in results
        ]
        return evidence

    except Exception as e:
        logger.warning(f"Evidence retrieval failed: {e}")
        return []


async def check_google_factcheck(claim_text: str) -> list[dict[str, str]]:
    """Query Google Fact Check Tools API.

    Returns:
        List of existing fact-checks for the claim.
    """
    settings = get_settings()
    if not settings.GOOGLE_FACTCHECK_API_KEY:
        return []

    try:
        url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
        params = {
            "query": claim_text,
            "key": settings.GOOGLE_FACTCHECK_API_KEY,
            "languageCode": "en",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()

        data = response.json()
        claims = data.get("claims", [])

        results = []
        for claim in claims[:3]:
            reviews = claim.get("claimReview", [])
            for review in reviews:
                results.append(
                    {
                        "claim": claim.get("text", ""),
                        "rating": review.get("textualRating", ""),
                        "publisher": review.get("publisher", {}).get("name", ""),
                        "url": review.get("url", ""),
                    }
                )

        return results

    except Exception as e:
        logger.warning(f"Google Fact Check API failed: {e}")
        return []


# ═══════════════════════════════════════════════════
# NLI-Based Verification
# ═══════════════════════════════════════════════════


def verify_claim_nli(claim: str, evidence_snippets: list[str]) -> dict[str, Any]:
    """Use NLI to verify a claim against evidence.

    Args:
        claim: The factual claim text.
        evidence_snippets: List of evidence text snippets.

    Returns:
        {"verdict": str, "confidence": float, "details": list}
    """
    nli = _get_nli_pipeline()
    if nli is None or not evidence_snippets:
        return {"verdict": "NOT_ENOUGH_INFO", "confidence": 0.0, "details": []}

    verdicts = []
    labels = ["SUPPORTS", "REFUTES", "NOT_ENOUGH_INFO"]

    for snippet in evidence_snippets[:3]:  # Limit to top 3 for speed
        if not snippet.strip():
            continue
        try:
            premise = snippet[:512]
            result = nli(
                premise,
                candidate_labels=labels,
                hypothesis=claim,
            )
            best_label = result["labels"][0]
            best_score = result["scores"][0]
            verdicts.append(
                {
                    "evidence": premise[:200],
                    "verdict": best_label,
                    "confidence": round(best_score, 3),
                }
            )
        except Exception as e:
            logger.warning(f"NLI verification failed for snippet: {e}")
            continue

    if not verdicts:
        return {"verdict": "NOT_ENOUGH_INFO", "confidence": 0.0, "details": []}

    # Aggregate: majority vote weighted by confidence
    votes = {"SUPPORTS": 0.0, "REFUTES": 0.0, "NOT_ENOUGH_INFO": 0.0}
    for v in verdicts:
        votes[v["verdict"]] += v["confidence"]

    best_verdict = max(votes, key=votes.get)
    total = sum(votes.values())
    confidence = votes[best_verdict] / total if total > 0 else 0.0

    return {
        "verdict": best_verdict,
        "confidence": round(confidence, 3),
        "details": verdicts,
    }


# ═══════════════════════════════════════════════════
# Combined Fact-Check Analysis
# ═══════════════════════════════════════════════════


async def analyze_claims(
    title: str,
    synopsis: str,
    source_name: str | None = None,
) -> dict[str, Any]:
    """Run full ClaimBuster analysis pipeline.

    Args:
        title: Article headline.
        synopsis: Article body text.
        source_name: Publisher name for credibility lookup.

    Returns:
        Full fact-check analysis dict matching output schema.
    """
    full_text = f"{title}. {synopsis}"

    # Step 1: Extract check-worthy claims
    raw_claims = await get_checkworthy_claims(full_text)

    # Step 2: For each claim, retrieve evidence and verify
    verified_claims = []
    for claim_data in raw_claims[:3]:  # Top 3 claims
        claim_text = claim_data["text"]

        # Evidence retrieval
        evidence = await retrieve_evidence(claim_text)
        evidence_snippets = [e["snippet"] for e in evidence if e.get("snippet")]
        evidence_urls = [e["url"] for e in evidence if e.get("url")]

        # Also check Google Fact Check
        factchecks = await check_google_factcheck(claim_text)
        for fc in factchecks:
            if fc.get("url"):
                evidence_urls.append(fc["url"])

        # NLI verification
        nli_result = verify_claim_nli(claim_text, evidence_snippets)

        verified_claims.append(
            {
                "text": claim_text,
                "checkworthiness": claim_data["score"],
                "verdict": nli_result["verdict"],
                "evidence_urls": evidence_urls[:5],
                "confidence": nli_result["confidence"],
            }
        )

    # Step 3: Source credibility
    source_info = get_source_credibility(source_name or "")
    credibility_tier = source_info["tier"]

    # Step 4: Compute trust score
    trust_signals = []

    # Signal from NLI verdicts
    for claim in verified_claims:
        if claim["verdict"] == "SUPPORTS":
            trust_signals.append(0.8 + claim["confidence"] * 0.2)
        elif claim["verdict"] == "REFUTES":
            trust_signals.append(0.1 + (1 - claim["confidence"]) * 0.2)
        else:
            trust_signals.append(0.5)

    # Signal from source credibility
    credibility_scores = {"high": 0.9, "medium": 0.6, "low": 0.3, "unknown": 0.5}
    trust_signals.append(credibility_scores.get(credibility_tier, 0.5))

    # Signal from check-worthiness (many claims = more scrutiny needed)
    if raw_claims:
        avg_checkworth = sum(c["score"] for c in raw_claims) / len(raw_claims)
        # Higher check-worthiness slightly lowers trust (more claims to verify)
        trust_signals.append(1.0 - avg_checkworth * 0.3)

    trust_score = sum(trust_signals) / len(trust_signals) if trust_signals else 0.5
    trust_score = round(min(max(trust_score, 0.0), 1.0), 3)

    return {
        "claims": verified_claims,
        "trust_score": trust_score,
        "source_credibility_tier": credibility_tier,
    }
