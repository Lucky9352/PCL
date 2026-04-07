"""Test configuration and fixtures."""

import pytest


@pytest.fixture
def sample_article_data():
    """Sample article data for testing."""
    return {
        "title": "India launches new space mission to study the Sun",
        "synopsis": (
            "ISRO successfully launched Aditya-L1, India's first space-based "
            "solar observatory. The spacecraft will study the solar corona and "
            "its impact on space weather. According to ISRO chief, the mission "
            "cost approximately 400 crore rupees."
        ),
        "author": "Test Author",
        "category": "science",
        "source_name": "The Hindu",
    }


@pytest.fixture
def sample_bias_result():
    """Sample bias analysis result."""
    return {
        "bias_score": 0.35,
        "bias_label": "center",
        "sentiment": {"score": 0.15, "label": "positive"},
        "bias_types": ["sensationalism"],
        "flagged_tokens": [{"word": "successfully", "suggestion": ""}],
        "framing": {"primary_frame": "neutral factual reporting", "framing_deviation": 0.2},
        "political_lean": {"lean_label": "center", "lean_score": 0.0},
        "model_confidence": 0.7,
    }


@pytest.fixture
def sample_factcheck_result():
    """Sample fact-check analysis result."""
    return {
        "claims": [
            {
                "text": "The mission cost approximately 400 crore rupees",
                "checkworthiness": 0.85,
                "verdict": "SUPPORTS",
                "evidence_urls": ["https://isro.gov.in"],
                "confidence": 0.72,
            }
        ],
        "trust_score": 0.78,
        "trust_components": {
            "evidence_trust": 0.9,
            "source_trust": 0.9,
            "coverage_score": 1.0,
            "weights": {"evidence": 0.5, "source": 0.3, "coverage": 0.2},
        },
        "source_credibility_tier": "high",
    }
