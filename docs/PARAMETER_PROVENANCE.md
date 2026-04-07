# IndiaGround — Parameter Provenance & Data Lineage

**Version 2.1.0** | April 2026

This document answers: *for every quantity that enters a formula, where does it come from in code, where is it persisted, and how does it relate to external benchmark annotations?*

Canonical formulas live in [METHODOLOGY.md](./METHODOLOGY.md). Pure functions are in `backend/app/services/scoring.py`; production values are produced by `unbias.py`, `claimbuster.py`, and `aggregator.py`.

---

## 1. Bias score components → source → database

| Symbol (formula) | Name in API/DB | How it is computed | Primary code | PostgreSQL column |
|------------------|----------------|--------------------|--------------|-------------------|
| **s** | `sentiment_extremity` | `abs(VADER(title)×0.40 + RoBERTa(body)×0.60)` clipped to [0,1] | `unbias.analyze_bias` → internal sentiment dict | `sentiment_score`, `sentiment_label`; component in `bias_score_components.sentiment_extremity` |
| **t** | `bias_type_severity` | `(count_detected/5 + mean(confidences))/2` over labels passing per-label thresholds | `unbias.classify_bias_types` + aggregation in `unbias` | `bias_types` (JSONB list); component in `bias_score_components.bias_type_severity` |
| **d** | `token_bias_density` | `min(flagged_count / word_count × 10, 1)` | Dictionary + VADER word scan in `unbias` | `flagged_tokens`; component in `bias_score_components.token_bias_density` |
| **f** | `framing_deviation` | `1 − P("neutral factual reporting")` from BART-MNLI zero-shot over 6 framing labels | `unbias.analyze_framing` | `framing` JSONB; component in `bias_score_components.framing_deviation` |

**Bias score** `B = 0.15s + 0.35t + 0.20d + 0.30f` → stored as `articles.bias_score` (Float). Decomposition: `articles.bias_score_components` (JSONB).

**Per-label bias-type thresholds** (BART-MNLI softmax, `multi_label=True`): defined in `unbias.BIAS_TYPE_THRESHOLDS` — political 0.35, sensationalism 0.40, loaded language **0.85** (using the more specific NLI hypothesis *"emotionally manipulative or inflammatory wording"* to avoid false positives on neutral headlines), framing 0.45, omission 0.40.

---

## 2. Trust score components → source → database

| Symbol | Name | How it is computed | Primary code | PostgreSQL column |
|--------|------|--------------------|--------------|-------------------|
| **e** | `evidence_trust` | Mean of per-claim scores from NLI verdicts (SUPPORTS / REFUTES / NEI mapping) | `claimbuster.analyze_claims` | `trust_score_components.evidence_trust` |
| **s** | `source_trust` | Tier lookup: high=0.9, medium=0.6, low=0.3, unknown=0.5 | `source_credibility.get_source_credibility` | `source_credibility_tier` + component in `trust_score_components.source_trust` |
| **c** | `coverage_score` | `verified_claims / max(total_claims, 1)` | `claimbuster` | `trust_score_components.coverage_score` |

**Trust score** `T = 0.50e + 0.30s + 0.20c` → `articles.trust_score`.

---

## 3. Reliability score → inputs → database

**Formula:** `R = [(1−B)×0.35 + T×0.35 + (1−S)×0.15 + (1−F)×0.15] × 100`

| Input | Meaning | Derivation |
|-------|---------|------------|
| B | `bias_score` | §1 |
| T | `trust_score` | §2 |
| S | sensationalism scalar | `0.70` if `"sensationalism"` ∈ `bias_types`; else `max(0, 0.50)` if `"loaded language"` ∈ `bias_types`; else `0.0` |
| F | framing deviation | Same **f** as §1 (`framing.framing_deviation`) |

**Code:** `aggregator.compute_reliability_score` (service) mirrors the documented weights; `scoring.compute_reliability_score` (pure) takes scalar `sensationalism` directly for tests.

**Stored:** `articles.reliability_score`, `articles.reliability_components` (bias_inversion, trust, sensationalism_penalty, framing_neutrality).

---

## 4. Check-worthiness (claims pipeline)

Not a scalar in the final reliability formula; it selects which sentences become `top_claims`.

| Stage | Model | Thresholds | Code |
|-------|-------|------------|------|
| Pass 1 | BART-MNLI zero-shot | Labels: verifiable factual claim vs opinion; keep if score > **0.45**; top **8** sentences | `get_checkworthy_claims` |
| Pass 2 | Same pipeline | Combined `0.35×S1 + 0.65×S2`; keep if > **0.50**; return top **5** | `get_checkworthy_claims` |

Also exposed in API metadata: `GET /api/v1/methodology` → `data.methodology.checkworthiness`.

---

## 5. Political lean

`L = 0.60 × source_bias_numeric + 0.40 × framing_lean` → label left/center/right by ±0.25 cutoffs. Stored in `articles.political_lean` (JSONB) and `articles.bias_label` (coarse).

---

## 6. Story clustering

| Field | Provenance |
|-------|------------|
| `story_cluster_id`, `cluster_similarity` | `story_cluster_sync.assign_article_to_cluster` using `all-MiniLM-L6-v2` embedding cosine vs cluster centroid; threshold **0.75** |
| Cluster aggregates | `story_cluster` service: `source_diversity`, `bias_spectrum`, averages |

---

## 7. External benchmark datasets vs operational database

| Data | Role | Stored in our DB? |
|------|------|-------------------|
| **BABE / LIAR / CLEF / MBIC** (see [DATASETS.md](./DATASETS.md)) | Offline evaluation only; human or distant labels | **No** — files under `backend/evaluation/datasets/` when you download them |
| **Scraped articles** | Production input | `articles`, `archived_articles` |
| **Raw model outputs (audit)** | Debugging / reproducibility | `analysis_runs.raw_output` (JSONB per module run) |
| **Source registry** | Prior for trust + lean | `sources` table + `source_credibility.py` constants |

We do **not** copy benchmark annotations into Postgres for live articles. Paper tables come from `evaluation/run_all.py` reports (`evaluation_report.json`).

---

## 8. Single-source-of-truth map (files)

| Concern | File(s) |
|---------|---------|
| Documented formulas | `docs/METHODOLOGY.md`, `docs/PARAMETER_PROVENANCE.md` |
| Testable pure math | `app/services/scoring.py` |
| Live bias pipeline | `app/services/unbias.py` |
| Live claims pipeline | `app/services/claimbuster.py` |
| Reliability assembly | `app/services/aggregator.py` |
| HTTP + embedded spec | `app/api/v1/methodology.py` + `SCORING_METHODOLOGY` in `scoring.py` |
| ORM / persistence | `app/db/models.py` |

When documentation and code disagree, **code wins** until the doc is updated — this file and `METHODOLOGY.md` are maintained to match `scoring.py` / `unbias.py` / `claimbuster.py` / `aggregator.py`.
