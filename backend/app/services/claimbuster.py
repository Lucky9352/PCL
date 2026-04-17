"""Claim extraction and verification module (ClaimBuster).

Analyses WHAT an article claims and whether those claims are factually
supported by external evidence.

Pipeline (documented in docs/METHODOLOGY.md §4):
  1. Check-worthiness — Two-pass BART-MNLI zero-shot (single model load)
  2. Evidence retrieval — ddgs (DuckDuckGo) + optional Google Fact Check Tools API
  3. NLI verification — BART-MNLI entailment/contradiction/neutral
  4. Source credibility lookup — Pre-built Indian source tier database
  5. Trust score computation — Decomposed: evidence + source + coverage

References:
  - Hassan et al. (2017), "ClaimBuster: End-to-end Fact-Checking" (KDD)
  - Thorne et al. (2018), "FEVER: Fact Extraction and Verification" (NAACL)
  - Guo et al. (2022), "Survey on Automated Fact-Checking" (TACL)
  - Eldifrawi et al. (2024), "Automated Justification for Claim Veracity" (ACL)
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core import get_settings
from app.core.logging import logger
from app.services.article_context import ArticleContext
from app.utils.source_credibility import get_source_credibility

# ═══════════════════════════════════════════════════
# Lazy-loaded models
# ═══════════════════════════════════════════════════

_nli_pipeline = None
_checkworthiness_pipeline = None


def _get_nli_pipeline():
    """Lazy-load BART-MNLI for zero-shot NLI verification."""
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


def _get_checkworthiness_pipeline():
    """Return the NLI pipeline for zero-shot check-worthiness scoring.

    The original cognotron/distilbert-base-cased-check-worthiness model is
    private/gated on HuggingFace.  Instead we reuse the already-loaded
    BART-MNLI pipeline for zero-shot check-worthiness via hypothesis
    "This sentence contains a verifiable factual claim."
    This avoids an extra model download and gives comparable quality.
    """
    return _get_nli_pipeline()


# ═══════════════════════════════════════════════════
# Check-worthiness: two-pass BART-MNLI (see get_checkworthy_claims docstring)
# ═══════════════════════════════════════════════════


async def get_checkworthy_claims(
    sentences: list[str],
) -> list[dict[str, Any]]:
    """Identify check-worthy claims using BART-MNLI zero-shot classification.

    Accepts pre-split sentences from ArticleContext (ctx.sentences) so the
    inline re.split that previously duplicated the preprocessor's work is
    removed entirely.

    Two-pass approach using a single model (facebook/bart-large-mnli):

    Pass 1 — Broad filter (high recall):
      Hypothesis: "This sentence contains a verifiable factual claim."
      Labels: ["verifiable factual claim", "opinion or commentary"]
      Threshold: 0.45  (keeps most genuine claims)

    Pass 2 — Precision refinement:
      Hypothesis: "This sentence contains a factual claim that should be
                   fact-checked."
      Labels: ["factual claim", "opinion/other"]
      Combined score: 0.35 × S1 + 0.65 × S2  (§4.1)
      Final threshold: 0.50

    Returns top 5 claims sorted by combined score.
    """
    # Filter short sentences (same rule as the old inline re.split)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 30]
    if not sentences:
        return []

    nli = _get_nli_pipeline()
    if nli is None:
        return [{"text": s, "score": 0.5} for s in sentences[:5]]

    # Pass 1: Broad zero-shot filter
    candidates = []
    for sentence in sentences:
        try:
            res = nli(
                sentence,
                candidate_labels=["verifiable factual claim", "opinion or commentary"],
            )
            score = (
                res["scores"][0]
                if res["labels"][0] == "verifiable factual claim"
                else res["scores"][1]
            )
            if score > 0.45:
                candidates.append({"text": sentence, "s1_score": round(score, 3)})
        except Exception as e:
            logger.warning(f"Pass 1 check-worthiness failed: {e}")
            candidates.append({"text": sentence, "s1_score": 0.5})

    if not candidates:
        return []

    candidates.sort(key=lambda x: x["s1_score"], reverse=True)
    top_candidates = candidates[:8]

    # Pass 2: Precision refinement
    final_claims = []
    for cand in top_candidates:
        try:
            res = nli(
                cand["text"],
                candidate_labels=["factual claim", "opinion/other"],
            )
            s2_score = res["scores"][0] if res["labels"][0] == "factual claim" else res["scores"][1]
            combined_score = (cand["s1_score"] * 0.35) + (s2_score * 0.65)

            if combined_score > 0.50:
                final_claims.append({"text": cand["text"], "score": round(combined_score, 3)})
        except Exception as e:
            logger.warning(f"Pass 2 refinement failed for claim: {e}")
            final_claims.append({"text": cand["text"], "score": cand["s1_score"]})

    final_claims.sort(key=lambda x: x["score"], reverse=True)
    return final_claims[:5]


# ═══════════════════════════════════════════════════
# Evidence Retrieval
# ═══════════════════════════════════════════════════


async def retrieve_evidence(claim_text: str) -> list[dict[str, str]]:
    """Retrieve evidence snippets for a claim via DuckDuckGo (region: India).

    Appends "fact check" to the query to bias results toward verification
    content from fact-checking organisations (§4.2).
    """
    try:
        try:
            from ddgs import DDGS
        except ImportError:
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
    """Query Google Fact Check Tools API for existing professional fact-checks.

    Free tier: 10,000 requests/day.  Returns empty list if no API key
    is configured (graceful degradation).
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
    """Verify a claim against evidence using NLI (Natural Language Inference).

    For each (evidence, claim) pair, BART-MNLI assigns probabilities to:
      SUPPORTS, REFUTES, NOT_ENOUGH_INFO

    Aggregation: Confidence-weighted majority vote (§4.3):
      For each verdict v ∈ {S, R, N}:
        vote(v) = Σ confidence_i  for all snippets where verdict_i = v
      Final verdict = argmax_v vote(v)
      Final confidence = vote(winner) / Σ vote(all)
    """
    nli = _get_nli_pipeline()
    if nli is None or not evidence_snippets:
        return {"verdict": "NOT_ENOUGH_INFO", "confidence": 0.0, "details": []}

    verdicts = []
    labels = ["SUPPORTS", "REFUTES", "NOT_ENOUGH_INFO"]

    for snippet in evidence_snippets[:3]:
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

    votes: dict[str, float] = {"SUPPORTS": 0.0, "REFUTES": 0.0, "NOT_ENOUGH_INFO": 0.0}
    for v in verdicts:
        votes[v["verdict"]] += v["confidence"]

    best_verdict = max(votes, key=votes.get)  # type: ignore[arg-type]
    total = sum(votes.values())
    confidence = votes[best_verdict] / total if total > 0 else 0.0

    return {
        "verdict": best_verdict,
        "confidence": round(confidence, 3),
        "details": verdicts,
    }


# ═══════════════════════════════════════════════════
# Trust Score Computation (Decomposed)
# ═══════════════════════════════════════════════════


def compute_trust_score(
    verified_claims: list[dict[str, Any]],
    raw_claims: list[dict[str, Any]],
    credibility_tier: str,
) -> dict[str, Any]:
    """Compute trust score decomposed into three sub-components.

    Formula (§4.4):
      trust_score = evidence_trust × 0.50
                  + source_trust   × 0.30
                  + coverage_score × 0.20

    Sub-components:

    1. Evidence Trust (from NLI verdicts):
       For each verified claim:
         SUPPORTS   → base=0.80, bonus=confidence×0.20  → [0.80, 1.00]
         REFUTES    → base=0.10, bonus=(1-confidence)×0.15 → [0.10, 0.25]
         NOT_ENOUGH → 0.50 (neutral)
       evidence_trust = mean(per_claim_scores) ∈ [0, 1]

    2. Source Trust (from credibility tier):
       high=0.90, medium=0.60, low=0.30, unknown=0.50
       Directly from source_credibility.py tier mapping.

    3. Coverage Score (verification completeness):
       coverage = verified_claims / total_claims
       Penalises articles where many claims could not be verified.

    Weight justification:
      - Evidence (0.50): Direct factual verification is the strongest signal
      - Source (0.30): Source reputation provides prior probability
      - Coverage (0.20): Completeness of verification matters
    """
    W_EVIDENCE, W_SOURCE, W_COVERAGE = 0.50, 0.30, 0.20

    # Sub-component 1: Evidence trust from NLI verdicts
    claim_scores = []
    for claim in verified_claims:
        verdict = claim.get("verdict", "NOT_ENOUGH_INFO")
        confidence = claim.get("confidence", 0.0)

        if verdict == "SUPPORTS":
            claim_scores.append(0.80 + confidence * 0.20)
        elif verdict == "REFUTES":
            claim_scores.append(0.10 + (1 - confidence) * 0.15)
        else:
            claim_scores.append(0.50)

    evidence_trust = sum(claim_scores) / len(claim_scores) if claim_scores else 0.5

    # Sub-component 2: Source credibility
    tier_scores = {"high": 0.9, "medium": 0.6, "low": 0.3, "unknown": 0.5}
    source_trust = tier_scores.get(credibility_tier, 0.5)

    # Sub-component 3: Verification coverage
    total_claims = len(raw_claims) if raw_claims else 1
    verified_count = len(verified_claims)
    coverage_score = min(verified_count / total_claims, 1.0) if total_claims > 0 else 0.5

    # Weighted combination
    trust_score = (
        evidence_trust * W_EVIDENCE + source_trust * W_SOURCE + coverage_score * W_COVERAGE
    )
    trust_score = round(min(max(trust_score, 0.0), 1.0), 3)

    return {
        "trust_score": trust_score,
        "components": {
            "evidence_trust": round(evidence_trust, 3),
            "source_trust": round(source_trust, 3),
            "coverage_score": round(coverage_score, 3),
            "weights": {
                "evidence": W_EVIDENCE,
                "source": W_SOURCE,
                "coverage": W_COVERAGE,
            },
        },
    }


# ═══════════════════════════════════════════════════
# Combined Fact-Check Analysis
# ═══════════════════════════════════════════════════


async def analyze_claims(
    ctx: ArticleContext,
    source_name: str | None = None,
) -> dict[str, Any]:
    """Run full ClaimBuster pipeline: extract → retrieve → verify → score.

    Args:
        ctx: Shared ArticleContext produced by build_article_context().
             ctx.sentences replaces the inline re.split that previously
             duplicated the preprocessor's sentence-splitting work.
             ctx.full_text is used for logging only — all text access goes
             through the context so cleaning is never repeated.
        source_name: Publisher name for credibility lookup.

    Returns:
        Complete fact-check analysis dict with decomposed trust score.
    """

    # Step 1: Extract check-worthy claims from pre-split sentences
    raw_claims = await get_checkworthy_claims(ctx.sentences)

    # Step 2: For each claim, retrieve evidence and verify
    verified_claims = []
    for claim_data in raw_claims[:3]:
        claim_text = claim_data["text"]

        evidence = await retrieve_evidence(claim_text)
        evidence_snippets = [e["snippet"] for e in evidence if e.get("snippet")]
        evidence_urls = [e["url"] for e in evidence if e.get("url")]

        factchecks = await check_google_factcheck(claim_text)
        for fc in factchecks:
            if fc.get("url"):
                evidence_urls.append(fc["url"])

        nli_result = verify_claim_nli(claim_text, evidence_snippets)

        verified_claims.append(
            {
                "text": claim_text,
                "checkworthiness": claim_data["score"],
                "verdict": nli_result["verdict"],
                "evidence_urls": evidence_urls[:5],
                "confidence": nli_result["confidence"],
                "nli_details": nli_result.get("details", []),
            }
        )

    # Step 3: Source credibility
    source_info = get_source_credibility(source_name or "")
    credibility_tier = source_info["tier"]

    # Step 4: Compute decomposed trust score
    trust_result = compute_trust_score(verified_claims, raw_claims, credibility_tier)

    return {
        "claims": verified_claims,
        "trust_score": trust_result["trust_score"],
        "trust_components": trust_result["components"],
        "source_credibility_tier": credibility_tier,
        "source_bias_tendency": source_info.get("bias", "unclassified"),
        "total_claims_found": len(raw_claims),
        "claims_verified": len(verified_claims),
    }
