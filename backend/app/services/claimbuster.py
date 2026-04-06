"""ClaimBuster module — factual claim detection and verification.

Hybrid approach:
  1. ClaimBuster API for check-worthiness scoring (with graceful fallback)
  2. DuckDuckGo for evidence retrieval
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


# ═══════════════════════════════════════════════════
# ClaimBuster API Integration
# ═══════════════════════════════════════════════════


async def get_checkworthy_claims_api(text: str) -> list[dict[str, Any]]:
    """Query ClaimBuster API for check-worthiness scores.

    Falls back to heuristic-based extraction if API key is not set.

    Returns:
        List of {"text": str, "score": float} sorted by score desc.
    """
    settings = get_settings()

    if not settings.CLAIMBUSTER_API_KEY:
        logger.info("ClaimBuster API key not set — using heuristic fallback")
        return _heuristic_claim_extraction(text)

    try:
        url = "https://idir.uta.edu/claimbuster/api/v2/score/text/"
        headers = {"x-api-key": settings.CLAIMBUSTER_API_KEY}
        payload = {"input_text": text}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()

        data = response.json()
        results = data.get("results", [])

        claims = [
            {"text": r["text"], "score": r["score"]}
            for r in sorted(results, key=lambda x: x["score"], reverse=True)
            if r["score"] > 0.3  # Only check-worthy claims
        ]

        return claims[:5]  # Top 5 most check-worthy

    except Exception as e:
        logger.warning(f"ClaimBuster API failed: {e} — using heuristic fallback")
        return _heuristic_claim_extraction(text)


def _heuristic_claim_extraction(text: str) -> list[dict[str, Any]]:
    """Heuristic fallback when ClaimBuster API is unavailable.

    Uses NLP patterns to identify claim-like sentences.
    """
    import re

    sentences = re.split(r"(?<=[.!?])\s+", text)
    claims = []

    # Patterns that indicate factual claims
    claim_patterns = [
        r"\b\d+\s*%",  # Percentages
        r"\b\d+\s*(million|billion|crore|lakh)",  # Large numbers
        r"\b(according to|reported|said|stated|claimed|announced)\b",  # Attribution
        r"\b(first|largest|smallest|most|least|highest|lowest)\b",  # Superlatives
        r"\b(is|are|was|were|has|have|had)\s+(not\s+)?(been\s+)?(a|the|an)\b",  # Definitional
        r"\b(increased|decreased|grew|fell|rose|dropped)\b",  # Trends
    ]

    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 20:
            continue

        score = 0.0
        for pattern in claim_patterns:
            if re.search(pattern, sentence, re.IGNORECASE):
                score += 0.15

        # Boost for sentences with named entities (proper nouns)
        proper_nouns = len(re.findall(r"\b[A-Z][a-z]+\b", sentence))
        score += min(proper_nouns * 0.05, 0.2)

        # Cap at 1.0
        score = min(score, 1.0)

        if score > 0.25:
            claims.append({"text": sentence, "score": round(score, 3)})

    claims.sort(key=lambda x: x["score"], reverse=True)
    return claims[:5]


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
    raw_claims = await get_checkworthy_claims_api(full_text)

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
