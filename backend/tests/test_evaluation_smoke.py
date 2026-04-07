"""Smoke tests for evaluation entrypoints (no external datasets)."""

from evaluation.evaluate_scoring import run_scoring_sanity
from evaluation.evaluate_tokens import run_synthetic_token_check


def test_scoring_sanity_passes():
    report = run_scoring_sanity()
    assert report["all_passed"] is True
    assert len(report["checks"]) >= 5


def test_token_synthetic_passes():
    out = run_synthetic_token_check()
    assert out["ok"] is True
