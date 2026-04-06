"""Unit tests for the aggregator scoring logic."""

import pytest

from app.services.aggregator import aggregate_analysis, compute_reliability_score


class TestComputeReliabilityScore:
    """Tests for the reliability score formula."""

    def test_perfect_article(self):
        """No bias, fully trustworthy, no sensationalism → 100."""
        score = compute_reliability_score(
            bias_score=0.0,
            trust_score=1.0,
            bias_types=[],
        )
        assert score == 100.0

    def test_worst_article(self):
        """Max bias, no trust, sensationalism + loaded language → ~0."""
        score = compute_reliability_score(
            bias_score=1.0,
            trust_score=0.0,
            bias_types=["sensationalism", "loaded language"],
        )
        assert score == pytest.approx(6.0, abs=1.0)

    def test_balanced_article(self):
        """Moderate bias and trust → middle range."""
        score = compute_reliability_score(
            bias_score=0.3,
            trust_score=0.7,
            bias_types=[],
        )
        # (1-0.3)*0.4 + 0.7*0.4 + (1-0)*0.2 = 0.28 + 0.28 + 0.20 = 0.76 → 76.0
        assert score == pytest.approx(76.0, abs=0.1)

    def test_biased_but_trustworthy(self):
        """High bias but factually accurate."""
        score = compute_reliability_score(
            bias_score=0.8,
            trust_score=0.9,
            bias_types=[],
        )
        # (1-0.8)*0.4 + 0.9*0.4 + 1.0*0.2 = 0.08 + 0.36 + 0.20 = 0.64 → 64.0
        assert score == pytest.approx(64.0, abs=0.1)

    def test_unbiased_but_untrustworthy(self):
        """Low bias but questionable facts."""
        score = compute_reliability_score(
            bias_score=0.1,
            trust_score=0.2,
            bias_types=[],
        )
        # (1-0.1)*0.4 + 0.2*0.4 + 1.0*0.2 = 0.36 + 0.08 + 0.20 = 0.64 → 64.0
        assert score == pytest.approx(64.0, abs=0.1)

    def test_sensationalism_penalty(self):
        """Sensationalism should reduce score."""
        score_no_sens = compute_reliability_score(
            bias_score=0.3,
            trust_score=0.7,
            bias_types=[],
        )
        score_sens = compute_reliability_score(
            bias_score=0.3,
            trust_score=0.7,
            bias_types=["sensationalism"],
        )
        assert score_sens < score_no_sens

    def test_loaded_language_penalty(self):
        """Loaded language should reduce score."""
        score_clean = compute_reliability_score(
            bias_score=0.3,
            trust_score=0.7,
            bias_types=[],
        )
        score_loaded = compute_reliability_score(
            bias_score=0.3,
            trust_score=0.7,
            bias_types=["loaded language"],
        )
        assert score_loaded < score_clean

    def test_score_bounds(self):
        """Score should always be between 0 and 100."""
        for bias in [0.0, 0.5, 1.0]:
            for trust in [0.0, 0.5, 1.0]:
                for types in [[], ["sensationalism"], ["loaded language"]]:
                    score = compute_reliability_score(bias, trust, types)
                    assert 0.0 <= score <= 100.0


class TestAggregateAnalysis:
    """Tests for the aggregate_analysis function."""

    def test_complete_aggregation(self, sample_bias_result, sample_factcheck_result):
        """Full aggregation produces all expected fields."""
        result = aggregate_analysis(sample_bias_result, sample_factcheck_result)

        assert "bias_score" in result
        assert "bias_label" in result
        assert "sentiment_score" in result
        assert "sentiment_label" in result
        assert "bias_types" in result
        assert "flagged_tokens" in result
        assert "trust_score" in result
        assert "source_credibility_tier" in result
        assert "top_claims" in result
        assert "reliability_score" in result
        assert result["analysis_status"] == "complete"

    def test_reliability_score_range(self, sample_bias_result, sample_factcheck_result):
        """Reliability score should be 0-100."""
        result = aggregate_analysis(sample_bias_result, sample_factcheck_result)
        assert 0.0 <= result["reliability_score"] <= 100.0

    def test_passthrough_fields(self, sample_bias_result, sample_factcheck_result):
        """Bias and trust scores should be passed through."""
        result = aggregate_analysis(sample_bias_result, sample_factcheck_result)
        assert result["bias_score"] == sample_bias_result["bias_score"]
        assert result["trust_score"] == sample_factcheck_result["trust_score"]
        assert result["bias_label"] == sample_bias_result["bias_label"]
        assert (
            result["source_credibility_tier"] == sample_factcheck_result["source_credibility_tier"]
        )
