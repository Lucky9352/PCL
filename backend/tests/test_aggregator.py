"""Unit tests for the aggregator scoring logic."""

import pytest

from app.services.aggregator import aggregate_analysis, compute_reliability_score


class TestComputeReliabilityScore:
    """Tests for the reliability score formula.

    Formula (v2.0):
      R = [(1-B)×0.35 + T×0.35 + (1-S)×0.15 + (1-F)×0.15] × 100
    """

    def test_perfect_article(self):
        """No bias, fully trustworthy, no sensationalism, no framing deviation → 100."""
        result = compute_reliability_score(
            bias_score=0.0, trust_score=1.0, bias_types=[], framing_deviation=0.0
        )
        assert result["score"] == 100.0

    def test_worst_article(self):
        """Max bias, no trust, sensationalism, max framing deviation → near 0."""
        result = compute_reliability_score(
            bias_score=1.0,
            trust_score=0.0,
            bias_types=["sensationalism", "loaded language"],
            framing_deviation=1.0,
        )
        assert result["score"] == pytest.approx(4.5, abs=1.0)

    def test_balanced_article(self):
        """Moderate bias and trust → middle range."""
        result = compute_reliability_score(
            bias_score=0.3,
            trust_score=0.7,
            bias_types=[],
            framing_deviation=0.0,
        )
        # (1-0.3)*0.35 + 0.7*0.35 + (1-0)*0.15 + (1-0)*0.15
        # = 0.245 + 0.245 + 0.15 + 0.15 = 0.79 → 79.0
        assert result["score"] == pytest.approx(79.0, abs=0.1)

    def test_biased_but_trustworthy(self):
        """High bias but factually accurate."""
        result = compute_reliability_score(
            bias_score=0.8,
            trust_score=0.9,
            bias_types=[],
            framing_deviation=0.0,
        )
        # (1-0.8)*0.35 + 0.9*0.35 + 1.0*0.15 + 1.0*0.15
        # = 0.07 + 0.315 + 0.15 + 0.15 = 0.685 → 68.5
        assert result["score"] == pytest.approx(68.5, abs=0.1)

    def test_unbiased_but_untrustworthy(self):
        """Low bias but questionable facts."""
        result = compute_reliability_score(
            bias_score=0.1,
            trust_score=0.2,
            bias_types=[],
            framing_deviation=0.0,
        )
        # (1-0.1)*0.35 + 0.2*0.35 + 1.0*0.15 + 1.0*0.15
        # = 0.315 + 0.07 + 0.15 + 0.15 = 0.685 → 68.5
        assert result["score"] == pytest.approx(68.5, abs=0.1)

    def test_sensationalism_penalty(self):
        """Sensationalism should reduce score."""
        result_no_sens = compute_reliability_score(
            bias_score=0.3,
            trust_score=0.7,
            bias_types=[],
            framing_deviation=0.0,
        )
        result_sens = compute_reliability_score(
            bias_score=0.3,
            trust_score=0.7,
            bias_types=["sensationalism"],
            framing_deviation=0.0,
        )
        assert result_sens["score"] < result_no_sens["score"]

    def test_loaded_language_penalty(self):
        """Loaded language should reduce score."""
        result_clean = compute_reliability_score(
            bias_score=0.3,
            trust_score=0.7,
            bias_types=[],
            framing_deviation=0.0,
        )
        result_loaded = compute_reliability_score(
            bias_score=0.3,
            trust_score=0.7,
            bias_types=["loaded language"],
            framing_deviation=0.0,
        )
        assert result_loaded["score"] < result_clean["score"]

    def test_framing_deviation_penalty(self):
        """Higher framing deviation should reduce score."""
        result_neutral = compute_reliability_score(
            bias_score=0.3,
            trust_score=0.7,
            bias_types=[],
            framing_deviation=0.0,
        )
        result_biased = compute_reliability_score(
            bias_score=0.3,
            trust_score=0.7,
            bias_types=[],
            framing_deviation=0.8,
        )
        assert result_biased["score"] < result_neutral["score"]

    def test_score_bounds(self):
        """Score should always be between 0 and 100."""
        for bias in [0.0, 0.5, 1.0]:
            for trust in [0.0, 0.5, 1.0]:
                for types in [[], ["sensationalism"], ["loaded language"]]:
                    for frame in [0.0, 0.5, 1.0]:
                        result = compute_reliability_score(bias, trust, types, frame)
                        assert 0.0 <= result["score"] <= 100.0

    def test_result_includes_components(self):
        """Result dict should include component breakdown."""
        result = compute_reliability_score(
            bias_score=0.5,
            trust_score=0.5,
            bias_types=[],
            framing_deviation=0.5,
        )
        assert "components" in result
        assert "weights" in result
        assert "raw_inputs" in result

    def test_symmetry_bias_trust(self):
        """Bias and trust have equal weight — swapping should produce equal effect."""
        result_a = compute_reliability_score(
            bias_score=0.2,
            trust_score=0.8,
            bias_types=[],
            framing_deviation=0.0,
        )
        result_b = compute_reliability_score(
            bias_score=0.8,
            trust_score=0.2,
            bias_types=[],
            framing_deviation=0.0,
        )
        # Both should center around the same midpoint since W_bias == W_trust
        # Midpoint = (0.35 × avg_inv_bias + 0.35 × avg_trust + 0.30_constant) × 100
        # = (0.35*0.5 + 0.35*0.5 + 0.30) * 100 = 65.0
        mid = (result_a["score"] + result_b["score"]) / 2
        assert mid == pytest.approx(65.0, abs=0.1)


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
        # New fields in v2
        assert "reliability_components" in result
        assert "model_confidence" in result

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
