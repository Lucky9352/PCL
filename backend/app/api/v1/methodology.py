"""Methodology API endpoint — serves scoring formulas and documentation."""

from __future__ import annotations

from fastapi import APIRouter

from app.services.scoring import SCORING_METHODOLOGY

router = APIRouter()


@router.get("/methodology", response_model=dict)
async def get_methodology():
    """Return the complete scoring methodology for frontend display.

    This powers the "How It Works" / Methodology page, providing
    formulas, weights, component descriptions, and interpretation
    guidelines so users understand exactly how scores are computed.
    """
    return {
        "success": True,
        "data": {
            "methodology": SCORING_METHODOLOGY,
            "pipeline": {
                "overview": "IndiaGround uses a dual-pipeline architecture that analyses "
                "both HOW news is written (bias detection) and WHAT it claims "
                "(fact-checking), then combines both into a unified reliability score.",
                "stages": [
                    {
                        "name": "Scraping & Ingestion",
                        "description": "Articles are collected from multiple sources: "
                        "Inshorts API, Google News RSS, direct outlet RSS feeds, "
                        "and optionally NewsAPI.org.",
                        "models": [],
                    },
                    {
                        "name": "Preprocessing",
                        "description": "Text cleaning, NER extraction (spaCy), "
                        "language detection, and semantic deduplication using "
                        "sentence-transformer embeddings (cosine > 0.92).",
                        "models": ["en_core_web_sm (spaCy)", "all-MiniLM-L6-v2"],
                    },
                    {
                        "name": "unBIAS Module (HOW)",
                        "description": "Analyses writing style: sentiment (VADER + RoBERTa), "
                        "bias types (BART-MNLI zero-shot), framing (India-specific NLI), "
                        "and token-level loaded language detection.",
                        "models": [
                            "VADER",
                            "cardiffnlp/twitter-roberta-base-sentiment-latest",
                            "facebook/bart-large-mnli",
                        ],
                    },
                    {
                        "name": "ClaimBuster Module (WHAT)",
                        "description": "Extracts check-worthy claims with a two-pass "
                        "BART-MNLI zero-shot filter (no private HF models), retrieves "
                        "evidence via ddgs (DuckDuckGo) in India region plus optional "
                        "Google Fact Check Tools API, then verifies claims with the "
                        "same BART-MNLI NLI head.",
                        "models": [
                            "facebook/bart-large-mnli (check-worthiness + NLI)",
                            "ddgs (DuckDuckGo search)",
                            "Google Fact Check Tools API (optional)",
                        ],
                    },
                    {
                        "name": "Aggregator",
                        "description": "Combines bias score, trust score, sensationalism "
                        "penalty, and framing neutrality into a final reliability "
                        "score on [0, 100].",
                        "models": [],
                    },
                ],
                "source_credibility": {
                    "description": "100+ Indian and international news sources mapped to "
                    "credibility tiers (high/medium/low) and political bias "
                    "tendency on a 7-point scale.",
                    "tier_mapping": {
                        "high": "0.9 — Established editorial processes, corrections policy",
                        "medium": "0.6 — Known outlets with occasional quality concerns",
                        "low": "0.3 — Tabloid-style, known sensationalism",
                        "unknown": "0.5 — Unrecognised source, neutral prior",
                    },
                },
            },
            "datasets_used_for_evaluation": [
                {
                    "name": "BABE",
                    "full_name": "Bias Annotations By Experts",
                    "size": "3,700 sentences",
                    "task": "Binary bias detection",
                    "citation": "Spinde et al. (2021), AAAI-ICWSM",
                },
                {
                    "name": "LIAR",
                    "full_name": "LIAR: A Benchmark Dataset for Fake News Detection",
                    "size": "12,836 statements",
                    "task": "Claim veracity (6-class → 3-class)",
                    "citation": "Wang (2017), ACL",
                },
                {
                    "name": "CLEF CheckThat!",
                    "full_name": "CLEF CheckThat! Lab",
                    "size": "50,000+ sentences",
                    "task": "Check-worthiness estimation",
                    "citation": "Barron-Cedeño et al. (2020)",
                },
                {
                    "name": "NELA-GT",
                    "full_name": "NELA-GT: A Large Multi-Labelled News Dataset",
                    "size": "1.8M articles, 400+ sources",
                    "task": "Source-level reliability",
                    "citation": "Nørregaard et al. (2019)",
                },
            ],
        },
    }
