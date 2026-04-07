"""IndiaGround evaluation framework.

Scripts:
  - evaluate_scoring.py  — Pure scoring invariants (no ML; CI default)
  - evaluate_tokens.py   — Token flagging synthetic + optional MBIC-style TSV
  - evaluate_bias.py     — BABE sentence-level bias (requires dataset + models)
  - evaluate_claims.py   — LIAR / CLEF (requires dataset + models)
  - run_all.py           — Scoring + tokens always; benchmarks if data exists

See docs/EVALUATION.md.
"""
