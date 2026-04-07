"""Sanity checks for pure scoring functions (no ML models).

Runs in CI and `python -m evaluation.run_all` without GPU or HuggingFace downloads.
Validates invariants and stable numeric outputs for paper-reproducible formulas.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.scoring import (  # noqa: E402
    SCORING_METHODOLOGY,
    compute_bias_score,
    compute_consensus_score,
    compute_political_lean,
    compute_reliability_score,
    compute_source_diversity_score,
    compute_trust_score,
)


def run_scoring_sanity() -> dict:
    """Execute fixed-input checks; returns a report dict."""
    checks: list[dict] = []

    b = compute_bias_score(0.5, 0.5, 0.5, 0.5)
    checks.append({"name": "bias_midpoint", "value": b, "ok": abs(b - 0.5) < 1e-6})

    t = compute_trust_score(0.8, 0.9, 1.0)
    checks.append({"name": "trust_high", "value": t, "ok": t > 0.85})

    r = compute_reliability_score(0.0, 1.0, 0.0, 0.0)
    checks.append({"name": "reliability_perfect_inputs", "value": r, "ok": r == 100.0})

    r2 = compute_reliability_score(1.0, 0.0, 0.7, 1.0)
    checks.append({"name": "reliability_worst_inputs", "value": r2, "ok": r2 < 15.0})

    pl = compute_political_lean(0.5, 0.2)
    checks.append({"name": "political_lean_range", "value": pl, "ok": -1.0 <= pl <= 1.0})

    div = compute_source_diversity_score(5)
    checks.append({"name": "diversity_half", "value": div, "ok": abs(div - 0.5) < 1e-6})

    cons = compute_consensus_score(["SUPPORTS", "SUPPORTS", "REFUTES"])
    expected_cons = round(2 / 3, 3)
    checks.append(
        {"name": "consensus_majority", "value": cons, "ok": abs(cons - expected_cons) < 1e-9}
    )

    meta_ok = isinstance(SCORING_METHODOLOGY, dict) and "version" in SCORING_METHODOLOGY
    checks.append(
        {"name": "methodology_metadata", "value": SCORING_METHODOLOGY.get("version"), "ok": meta_ok}
    )

    cw = (
        SCORING_METHODOLOGY.get("checkworthiness")
        if isinstance(SCORING_METHODOLOGY, dict)
        else None
    )
    cw_ok = isinstance(cw, dict) and cw.get("model") and "pass1" in cw and "pass2" in cw
    checks.append({"name": "methodology_checkworthiness_spec", "value": bool(cw_ok), "ok": cw_ok})

    all_ok = all(c["ok"] for c in checks)
    return {
        "suite": "scoring_sanity",
        "all_passed": all_ok,
        "checks": checks,
    }


if __name__ == "__main__":
    report = run_scoring_sanity()
    print(json.dumps(report, indent=2))
    sys.exit(0 if report["all_passed"] else 1)
