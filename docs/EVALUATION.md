# IndiaGround — Evaluation

This document ties together **what we measure**, **which scripts run**, **how results map to code and formulas**, and **how to reproduce** outcomes for a research paper or audit.

## 1. Suites

| Suite | Script | GPU / HF models? | What it proves |
|-------|--------|------------------|----------------|
| **Scoring sanity** | `evaluation/evaluate_scoring.py` | No | Pure formulas in `scoring.py` match documented bounds; metadata includes `checkworthiness` spec |
| **Token flagging** | `evaluation/evaluate_tokens.py` | No (synthetic + optional MBIC path) | Dictionary / structure of flagged-token pipeline |
| **Bias (BABE)** | `evaluation/evaluate_bias.py` | Yes | Sentence-level bias F1 vs expert labels |
| **Claims (LIAR / CLEF)** | `evaluation/evaluate_claims.py` | Yes | NLI verdict mapping + check-worthiness vs CLEF |
| **Orchestrator** | `evaluation/run_all.py` | Partial | Runs scoring + tokens **always**; GPU benchmarks **only if** dataset files exist |

## 2. Formula ↔ code traceability

| Documented quantity | Evaluation touchpoint | Implementation |
|---------------------|----------------------|------------------|
| Bias score B | BABE threshold study | `scoring.compute_bias_score` / `unbias.analyze_bias` |
| Trust score T | LIAR (via NLI verdicts) | `scoring.compute_trust_score` / `claimbuster.analyze_claims` |
| Reliability R | Scoring sanity (extreme inputs) | `scoring.compute_reliability_score` vs `aggregator.compute_reliability_score` |
| Check-worthiness | CLEF | `claimbuster.get_checkworthy_claims` |
| Political lean | (optional future suite) | `scoring.compute_political_lean` / `unbias` |

Full parameter lineage: [PARAMETER_PROVENANCE.md](./PARAMETER_PROVENANCE.md).

## 3. Quick verification (no datasets — CI default)

From the repo root:

```bash
cd backend
uv sync
uv run python -m evaluation.evaluate_scoring
uv run python -m evaluation.evaluate_tokens
```

Expected: exit code `0`, JSON with `all_passed: true` (scoring) and `ok: true` (synthetic tokens).

**Pytest smoke** (also CI-friendly):

```bash
uv run pytest tests/test_evaluation_smoke.py -q
```

## 4. Full benchmark run (optional — requires downloads)

1. Create `backend/evaluation/datasets/` and add files per [DATASETS.md](./DATASETS.md).
2. Run (GPU recommended for BABE/LIAR/CLEF segments):

```bash
cd backend
uv run python -m evaluation.run_all --data-dir evaluation/datasets --sample 200 \
  --output evaluation_report.json --markdown evaluation_report.md
```

**Without dataset files:** the orchestrator still runs **scoring_sanity** and **tokens_synthetic**; other sections report `"status": "dataset_not_found"`. This is **expected** for a clean clone.

## 5. Continuous integration checklist

Run before release:

```bash
cd backend
uv run pytest tests/ -q
uv run python -m evaluation.evaluate_scoring
uv run python -m evaluation.evaluate_tokens
uv run ruff check app/ evaluation/ --select E,F,I --ignore E501
```

Frontend (from repo root):

```bash
cd frontend && pnpm exec tsc --noEmit && pnpm build
```

Monorepo shortcut: `bash scripts/verify_stack.sh` (if present in your tree).

## 6. Story clustering (qualitative)

After migration and scrape + analyze:

- `SELECT COUNT(*) FROM story_clusters;`
- `SELECT COUNT(*) FROM articles WHERE story_cluster_id IS NOT NULL;`
- Multi-source UI: stories with `min_sources=2` in `GET /api/v1/stories`.

## 7. Reporting for the paper

Export `evaluation_report.json` and document:

1. **Sample size** per dataset (and whether subsampled).
2. **Hardware** (GPU model, RAM) and **HF cache revision** (model commit hash from `huggingface_hub` if pinned).
3. **Zero-shot / no fine-tune** — production scores are not trained on BABE/LIAR/CLEF; comparison with fine-tuned baselines belongs in limitations.
4. **Check-worthiness** — CLEF metrics use the same `get_checkworthy_claims` as production (BART-MNLI two-pass).
5. **Operational data** — live `articles` rows are model outputs, not benchmark annotations ([DATASETS.md §6](./DATASETS.md)).

## 8. Related documentation

- [METHODOLOGY.md](./METHODOLOGY.md) — formulas and weights  
- [PARAMETER_PROVENANCE.md](./PARAMETER_PROVENANCE.md) — where each input is computed and stored  
- [DATASETS.md](./DATASETS.md) — annotation schemes and downloads  
- [MANUAL_VERIFICATION.md](./MANUAL_VERIFICATION.md) — end-to-end stack walkthrough  
