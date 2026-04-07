# IndiaGround — Benchmark Datasets

This document describes each dataset used for evaluating the IndiaGround pipeline, including their annotation methodology, label schemas, and how we map them to our scoring system.

For **how to run evaluations** (CI, scoring sanity, full benchmarks), see [EVALUATION.md](./EVALUATION.md).

---

## 1. BABE (Bias Annotations By Experts)

| | |
|---|---|
| **Citation** | Spinde et al. (2021). "An Interdisciplinary Dataset for News Media Bias Detection Using Distant Supervision." AAAI-ICWSM Workshop. |
| **Size** | 3,700 sentences from 1,700 news articles |
| **Task** | Sentence-level binary bias detection |
| **Labels** | biased (1) / non-biased (0) |
| **Inter-annotator agreement** | Krippendorff's α = 0.49 (moderate) |
| **Download** | https://github.com/Media-Bias-Group/Neural-Media-Bias-Detection-Using-Distant-Supervision-With-BABE |

### Annotation Methodology
- 8 trained annotators (media science students)
- Each sentence annotated by at least 2 annotators
- Disagreements resolved by majority vote
- Annotation guidelines based on bias taxonomy from Recasens et al. (2013)

### Our Mapping
```
BABE "biased" (1)     → our bias_score > 0.5
BABE "non-biased" (0) → our bias_score ≤ 0.5
```

### Metrics Reported
- Accuracy, Precision, Recall, F1 (macro and per-class)
- Component ablation (which bias signal contributes most)

---

## 2. LIAR

| | |
|---|---|
| **Citation** | Wang (2017). "Liar, Liar Pants on Fire: A New Benchmark Dataset for Fake News Detection in Political Statement." ACL. |
| **Size** | 12,836 statements from PolitiFact.com |
| **Task** | 6-class veracity classification |
| **Labels** | pants-fire, false, barely-true, half-true, mostly-true, true |
| **Split** | Train: 10,269 / Val: 1,284 / Test: 1,283 |
| **Download** | https://www.cs.ucsb.edu/~william/data/liar_dataset.zip |

### Annotation Methodology
- Labels from PolitiFact professional fact-checkers
- Each statement rated by experienced journalists
- Includes metadata: speaker, context, party, job title
- 6-point truthfulness scale

### Our Mapping (6-class → 3-class)
```
{pants-fire, false}      → REFUTES
{barely-true, half-true} → NOT_ENOUGH_INFO
{mostly-true, true}      → SUPPORTS
```

**Rationale**: Our NLI pipeline produces 3 verdicts. The mapping groups clearly false statements as REFUTES, clearly true as SUPPORTS, and ambiguous middle categories as NOT_ENOUGH_INFO.

### Metrics Reported
- 3-class Accuracy, Macro-F1
- Per-class Precision, Recall, F1

---

## 3. CLEF CheckThat! Lab

| | |
|---|---|
| **Citation** | Barron-Cedeño et al. (2020). "CheckThat! at CLEF 2020." ECIR. |
| **Size** | 50,000+ sentences (accumulated across 2019-2022 editions) |
| **Task** | Binary check-worthiness estimation |
| **Labels** | check-worthy (1) / not check-worthy (0) |
| **Download** | https://sites.google.com/view/clef2022-checkthat/ |

### Annotation Methodology
- Annotators: trained NLP researchers + journalism students
- Source: Political speeches, debates, tweets, news articles
- Agreement measured via Cohen's κ (varies by year, typically 0.55-0.70)

### Our Mapping
```
CLEF "check-worthy" (1)     → our checkworthiness_score > 0.5
CLEF "not check-worthy" (0) → our checkworthiness_score ≤ 0.5
```

### Metrics Reported
- Average Precision @ 5 (MAP@5)
- Precision @ 5
- Binary F1

---

## 4. NELA-GT (News Landscape)

| | |
|---|---|
| **Citation** | Nørregaard et al. (2019). "NELA-GT-2018: A Large Multi-Labelled News Dataset." ICWSM. |
| **Size** | 1.8M articles from 400+ sources (2018-2022 editions) |
| **Task** | Source-level reliability and factuality |
| **Labels** | Source reliability labels from NewsGuard, MBFC, OpenSources |
| **Download** | https://doi.org/10.7910/DVN/ULHLCB |

### Annotation Methodology
- Source-level labels aggregated from 3+ independent assessment organisations
- NewsGuard: Professional journalist evaluation (0-100 trust score)
- MBFC: Volunteer-driven, political bias + factual reporting rating
- OpenSources: Crowdsourced categorisation (reliable/satire/fake/etc.)

### Our Mapping
```
NELA source reliability (aggregated) → compared with our reliability_score distribution per source
Spearman correlation between NELA source labels and our mean reliability_score per source
```

### Metrics Reported
- Spearman rank correlation
- RMSE between normalised scores

---

## 5. MBIC (Media Bias Identification Corpus)

| | |
|---|---|
| **Citation** | Spinde et al. (2021). "MBIC — A Media Bias Annotation Dataset." arXiv:2105.11910. |
| **Size** | 1,700 articles, 17,000+ annotated sentences |
| **Task** | Token-level and sentence-level bias annotation |
| **Labels** | Biased tokens marked with spans, sentence-level bias labels |
| **Download** | https://github.com/Media-Bias-Group/MBIC |

### Annotation Methodology
- Token-level: biased word/phrase spans highlighted by annotators
- Sentence-level: binary biased/not-biased
- 5 annotators per item, majority vote for final label

### Our Mapping
```
MBIC token spans → compared with our flagged_tokens
Token-level F1: exact match and partial overlap scoring
```

### Metrics Reported
- Token-level Precision, Recall, F1
- Sentence-level F1 (using our bias_score > 0.5 threshold)

---

## 6. Production database vs benchmark annotations

| Layer | What it is | Annotation |
|-------|------------|------------|
| **`articles` table** | Every scraped + analyzed news row | **Machine-generated** — our pipeline writes scores, JSONB fields (`bias_types`, `framing`, `top_claims`, component dicts). No human labeler in the loop for live data. |
| **`analysis_runs` table** | Optional audit trail | Raw dict outputs from `unbias` / `claimbuster` per run for debugging and reproducibility. |
| **`story_clusters` table** | Clusters of same-event articles | **Algorithmic** — embedding similarity + agglomerative assignment; aggregates (e.g. `bias_spectrum`) derived from member articles. |
| **`sources` table** | Curated outlet metadata | **Human-curated** priors (credibility tier, bias tendency) aligned with [METHODOLOGY.md](./METHODOLOGY.md) §3; not the same as BABE sentence labels. |
| **Files under `evaluation/datasets/`** | BABE, LIAR, CLEF, etc. | **Third-party annotations** — used only offline by `evaluation/*.py`; never required for the app to run. |

**Paper / compliance narrative:** Live user-facing scores are **not** trained or tuned on BABE/LIAR/CLEF rows inside Postgres. Benchmarks measure how well the frozen pipeline aligns with those external standards when you opt in by downloading data and running `run_all.py`.

Full field-level mapping: [PARAMETER_PROVENANCE.md](./PARAMETER_PROVENANCE.md).

---

## 7. Dataset Download Instructions

Create the evaluation datasets directory:

```bash
mkdir -p backend/evaluation/datasets
cd backend/evaluation/datasets
```

### BABE
```bash
git clone https://github.com/Media-Bias-Group/Neural-Media-Bias-Detection-Using-Distant-Supervision-With-BABE.git babe_repo
cp babe_repo/data/final_labels_SG*.tsv babe.tsv
```

### LIAR
```bash
wget https://www.cs.ucsb.edu/~william/data/liar_dataset.zip
unzip liar_dataset.zip
# Files: train.tsv, valid.tsv, test.tsv
mv test.tsv liar_test.tsv
mv train.tsv liar_train.tsv
```

### CLEF CheckThat!
Download from the official CLEF repository:
https://sites.google.com/view/clef2022-checkthat/tasks/task-1-check-worthiness-estimation

### Running Evaluations
```bash
cd backend
uv run python -m evaluation.run_all --data-dir evaluation/datasets/ --sample 200
```

---

## 8. Notes for Research Paper

When citing dataset results in the paper:
1. Always report the sample size used (full dataset or subsample)
2. Report macro-averaged metrics for multi-class tasks
3. Include confidence intervals where possible (bootstrap with 1000 resamples)
4. Note that our system uses zero-shot / pre-trained models without fine-tuning — comparison with fine-tuned baselines should acknowledge this difference
5. For LIAR dataset, note that we only use statement text (no metadata features like speaker party), making our task harder but evaluation more fair for the NLI-only approach
