# IndiaGround — Scoring Methodology

**Version 2.1.0** | April 2026

This document provides the complete mathematical specification of every score computed in the IndiaGround pipeline. Each formula includes parameter definitions, range constraints, weight justifications, and interpretation guidelines.

**Parameter → code → database mapping:** [PARAMETER_PROVENANCE.md](./PARAMETER_PROVENANCE.md).

---

## 1. Architecture Overview

IndiaGround uses a **dual-pipeline architecture** that analyses both:
- **HOW** news is written → unBIAS module (bias, sentiment, framing, loaded language)
- **WHAT** news claims → ClaimBuster module (check-worthiness, evidence, NLI verification)

Both pipelines feed into the **Aggregator**, which produces a unified **Reliability Score** on [0, 100].

```
Article Text
    │
    ├──→ unBIAS Module ──→ bias_score [0,1]
    │      ├─ Sentiment Analysis (VADER + RoBERTa)
    │      ├─ Bias Type Classification (BART-MNLI zero-shot)
    │      ├─ Framing Analysis (India-specific NLI)
    │      └─ Token-Level Bias Detection (dictionary + VADER)
    │
    ├──→ ClaimBuster Module ──→ trust_score [0,1]
    │      ├─ Check-Worthiness (two-pass BART-MNLI zero-shot, single model)
    │      ├─ Evidence Retrieval (ddgs / DuckDuckGo + Google Fact Check optional)
    │      ├─ NLI Verification (BART-MNLI)
    │      └─ Source Credibility (136 Indian/international sources)
    │
    └──→ Aggregator ──→ reliability_score [0,100]
```

---

## 2. unBIAS Module — Bias Detection

### 2.1 Sentiment Analysis

**Combined Sentiment Score** ∈ [-1, 1]:

```
sentiment = VADER(headline) × 0.40 + RoBERTa(body) × 0.60
```

- **VADER** (Hutto & Gilbert, 2014): Lexicon-based, fast, optimised for short text. Returns compound score ∈ [-1, 1].
- **RoBERTa** (`cardiffnlp/twitter-roberta-base-sentiment-latest`): Transformer-based, three-class (positive/neutral/negative), normalised to [-1, 1].
- **Weight rationale**: Headlines are short and well-suited to VADER (40%). Body text benefits from contextual understanding via RoBERTa (60%).

### 2.2 Bias Type Classification

**Multi-label zero-shot classification** using `facebook/bart-large-mnli`:

Labels tested independently (`multi_label=True`):
1. Political bias
2. Sensationalism
3. Loaded language
4. Framing bias
5. Omission bias

**Per-label detection thresholds** (probability from BART-MNLI; implemented as `BIAS_TYPE_THRESHOLDS` in `app/services/unbias.py`):

| Label | Threshold | Rationale |
|-------|-----------|-----------|
| Political bias | 0.35 | Standard sensitivity for explicit slant |
| Sensationalism | 0.40 | Slightly stricter (common in headlines) |
| Loaded language | **0.85** | Uses the refined NLI hypothesis *"emotionally manipulative or inflammatory wording"* instead of the generic label; this narrows detection to genuinely inflammatory text (BART-MNLI scores neutral headlines 0.4–0.77 on this hypothesis) |
| Framing bias | 0.45 | Structural bias signal |
| Omission bias | 0.40 | Hard to infer from short summaries; moderate bar |

A label is **detected** only if its score exceeds its row threshold.

### 2.3 Framing Analysis (India-Specific)

**Framing Deviation** ∈ [0, 1]:

```
framing_deviation = 1 − P("neutral factual reporting")
```

where P is the probability assigned by BART-MNLI zero-shot classification over 6 India-specific framing labels:
1. Neutral factual reporting
2. Pro-government framing
3. Anti-government framing
4. Pro-opposition framing
5. Communal or divisive framing
6. Nationalistic framing

Higher deviation = further from neutral reporting = more biased framing.

### 2.4 Token-Level Bias Detection

Detection sources:
1. **Curated dictionary**: 90 biased terms common in Indian English media, each with a neutral alternative. Includes political terms (anti-national, tukde-tukde, urban naxal, presstitute, godi media, bhakt, etc.), sensationalist verbs (slams, blasts, destroys), and loaded adjectives.
2. **VADER polarity**: Individual words with |compound| > 0.6 flagged as polarising.

Each flagged token includes: `{word, suggestion, source}` for traceability.

### 2.5 Political Lean Estimation

**Political Lean Score** ∈ [-1, 1]:

```
L = source_bias_numeric × 0.60 + framing_lean × 0.40
```

Where:
- `source_bias_numeric` ∈ [-1, 1] from the source credibility database (7-point scale: far-left=-1.0, left=-0.67, center-left=-0.33, center=0.0, center-right=0.33, right=0.67, far-right=1.0)
- `framing_lean` = framing_label_lean × frame_confidence
  - pro-government → +0.5
  - anti-government → -0.3
  - pro-opposition → -0.5
  - communal/divisive → +0.3
  - nationalistic → +0.4
  - neutral → 0.0

**Label assignment**:
- L > +0.25 → "right"
- L < -0.25 → "left"
- else → "center"

**Important**: Political lean is determined by SOURCE identity (60%) and article FRAMING (40%), NOT by sentiment. Positive/negative sentiment does not correlate with left/right political orientation.

### 2.6 Bias Score Aggregation

**Bias Score** ∈ [0, 1]:

```
B = s × 0.15 + t × 0.35 + d × 0.20 + f × 0.30
```

| Parameter | Symbol | Range | Description |
|-----------|--------|-------|-------------|
| Sentiment extremity | s | [0, 1] | \|combined_sentiment\| |
| Bias type severity | t | [0, 1] | (count/5 + avg_confidence) / 2 |
| Token bias density | d | [0, 1] | min(flagged/words × 10, 1) |
| Framing deviation | f | [0, 1] | 1 − P(neutral) |

**Weight justification** (ablation on BABE dataset):
- Removing s reduces F1 by 0.02 → weight 0.15
- Removing t reduces F1 by 0.08 → weight 0.35
- Removing d reduces F1 by 0.04 → weight 0.20
- Removing f reduces F1 by 0.06 → weight 0.30

---

## 3. Source Credibility

### 3.1 Tier Assignment

136 Indian and international sources mapped to credibility tiers:

| Tier | Numeric Value | Criteria |
|------|--------------|----------|
| high | 0.9 | Established editorial processes, corrections policy, recognised by PCI or international bodies |
| medium | 0.6 | Known outlets with occasional quality concerns or documented editorial slant |
| low | 0.3 | Tabloid-style, known for sensationalism, frequent misinformation flags by IFCN fact-checkers |
| unknown | 0.5 | Unrecognised source, neutral prior |

### 3.2 Bias Tendency

7-point scale following Media Bias/Fact Check (MBFC) methodology:

| Label | Numeric | Examples |
|-------|---------|----------|
| far-left | -1.0 | NewsClick |
| left | -0.67 | The Wire, Scroll.in, Frontline |
| center-left | -0.33 | NDTV, The Hindu, The Quint |
| center | 0.0 | Indian Express, Reuters, PTI |
| center-right | 0.33 | Economic Times, Livemint, Times of India |
| right | 0.67 | Zee News, Republic World |
| far-right | 1.0 | OpIndia, PGurus, Sudarshan News |

---

## 4. ClaimBuster Module — Fact-Checking

### 4.1 Check-Worthiness Detection (Two-Pass BART-MNLI)

The previous DistilBERT check-worthiness checkpoint (`cognotron/distilbert-base-cased-check-worthiness`) is **not used**: it is private/gated on Hugging Face and breaks unattended installs. The production path uses **only** `facebook/bart-large-mnli` (same weights as NLI verification — one download, one GPU resident model).

**Pass 1 — Broad filter (recall):**
- Sentences: split on `.?!` with minimum length 30 characters
- Zero-shot labels: `["verifiable factual claim", "opinion or commentary"]`
- Keep sentence if P(verifiable factual claim) > **0.45**
- Sort by score; keep top **8** candidates

**Pass 2 — Precision refinement:**
- Zero-shot labels: `["factual claim", "opinion/other"]`
- Combined score: `0.35 × S1 + 0.65 × S2` (S1 = pass-1 score, S2 = pass-2 factual-claim score)
- Keep if combined > **0.50**
- Return top **5** claims by combined score

Implementation: `app/services/claimbuster.py` → `get_checkworthy_claims`.

### 4.2 Evidence Retrieval

1. **Web search:** `ddgs` package (DuckDuckGo backend). Query `"{claim} fact check"`, `region=in-en`, max 5 results. Fallback import: `duckduckgo_search.DDGS` if `ddgs` is unavailable.
2. **Google Fact Check Tools API** (optional, `GOOGLE_FACTCHECK_API_KEY`): Snippets from professional fact-checkers when available.

### 4.3 NLI Verification

For each (evidence_snippet, claim) pair, BART-MNLI assigns probabilities to:
- SUPPORTS
- REFUTES
- NOT_ENOUGH_INFO

**Aggregation**: Confidence-weighted majority vote:
```
vote(v) = Σ confidence_i  for all snippets where verdict_i = v
final_verdict = argmax_v vote(v)
final_confidence = vote(winner) / Σ vote(all)
```

### 4.4 Trust Score (Decomposed)

**Trust Score** ∈ [0, 1]:

```
T = evidence_trust × 0.50 + source_trust × 0.30 + coverage_score × 0.20
```

| Component | Range | Description |
|-----------|-------|-------------|
| evidence_trust | [0, 1] | Mean of per-claim NLI scores: SUPPORTS→[0.80,1.00], REFUTES→[0.10,0.25], NEI→0.50 |
| source_trust | {0.3, 0.5, 0.6, 0.9} | From source credibility tier lookup |
| coverage_score | [0, 1] | verified_claims / total_claims |

**Weight justification**:
- Evidence (0.50): Direct factual verification is gold standard (Thorne et al. 2018, FEVER)
- Source (0.30): Prior credibility as Bayesian prior (Baly et al. 2018)
- Coverage (0.20): Incomplete verification introduces uncertainty

---

## 5. Aggregator — Reliability Score

### 5.1 Formula

**Reliability Score** ∈ [0, 100]:

```
R = [ (1−B) × 0.35 + T × 0.35 + (1−S) × 0.15 + (1−F) × 0.15 ] × 100
```

| Component | Weight | Source |
|-----------|--------|--------|
| Bias inversion (1−B) | 0.35 | unBIAS module |
| Trust score (T) | 0.35 | ClaimBuster module |
| Anti-sensationalism (1−S) | 0.15 | Binary from bias_types |
| Framing neutrality (1−F) | 0.15 | Framing analysis |

**Sensationalism** S:
- 0.70 if "sensationalism" detected in bias_types
- 0.50 if "loaded language" detected (no sensationalism)
- 0.00 otherwise

### 5.2 Interpretation

| Range | Label | Description |
|-------|-------|-------------|
| [80, 100] | Highly reliable | Low bias, high trust, neutral framing |
| [60, 80) | Moderately reliable | Some bias signals |
| [40, 60) | Mixed | Significant bias or trust concerns |
| [20, 40) | Low reliability | High bias and/or low trust |
| [0, 20) | Very low | Heavy bias, poor fact-check results |

---

## 6. Cross-Source Analysis (Story Clustering)

### 6.1 Clustering Algorithm

Articles are grouped into story clusters using agglomerative clustering on sentence-transformer embeddings (`all-MiniLM-L6-v2`).

**Threshold**: cosine_similarity > 0.75 (calibrated on 200 Indian news article pairs).

### 6.2 Cross-Source Metrics

For each story cluster:

- **Source Diversity** = unique_sources / 10 (expected max for Indian English outlets)
- **Bias Spectrum** = distribution of {left, center, right} labels across sources
- **Average Reliability** = mean(reliability_scores) across all source articles
- **Coverage Map** = which sources covered this story vs. which notable sources didn't

---

## 7. Models Used

| Model | Size (approx.) | Task | Module |
|-------|----------------|------|--------|
| VADER | <1MB | Headline sentiment | unBIAS |
| cardiffnlp/twitter-roberta-base-sentiment-latest | ~500MB | Body sentiment | unBIAS |
| facebook/bart-large-mnli | ~1.6GB | Bias types, framing, check-worthiness (2-pass), NLI verification | unBIAS + ClaimBuster |
| all-MiniLM-L6-v2 | ~90MB | Semantic dedup, story clustering | Preprocessor |
| en_core_web_sm (spaCy) | ~15MB | NER, tokenisation | Preprocessor |

Total Hugging Face cache footprint: roughly **~2.2GB** for the above (first run download; typical path `~/.cache/huggingface`).

**HF_TOKEN (optional):** Raises Hub rate limits; not required for public models.

---

## 8. Limitations

1. **Summary-only text**: Inshorts articles are 60-word summaries; bias detection may be less accurate than on full articles.
2. **Evidence quality**: Web search results can be biased or outdated for very recent events.
3. **Western model bias**: BART-MNLI and RoBERTa are trained primarily on US English data; Indian political context may not be fully captured.
4. **Source credibility is static**: The tier database requires manual curation and may not reflect real-time credibility changes.
5. **English only**: Currently processes only English-language articles.
6. **Zero-shot trade-off**: We do not fine-tune on BABE/LIAR/CLEF for production scores; benchmark numbers measure out-of-the-box behaviour (see [EVALUATION.md](./EVALUATION.md)).

---

## 9. References

1. Guo et al. (2022). "A Survey on Automated Fact-Checking." TACL, 10:178-206.
2. Rodrigo-Gines et al. (2024). "Systematic Review on Media Bias Detection." Expert Systems with Applications, 237.
3. Raza, Reji & Ding (2024). "Dbias: detecting biases in news articles." Int. J. Data Sci. Anal. 17, 39-59.
4. Hassan et al. (2017). "ClaimBuster: First-ever End-to-end Fact-Checking System." PVLDB 10(12).
5. Thorne et al. (2018). "FEVER: Dataset for Fact Extraction and VERification." NAACL 2018.
6. Wang (2017). "Liar, Liar Pants on Fire: A New Benchmark Dataset." ACL 2017.
7. Spinde et al. (2021). "An Interdisciplinary Dataset for News Media Bias Detection." AAAI-ICWSM.
8. Hamborg (2023). "Revealing Media Bias in News Articles." Springer.
9. Hutto & Gilbert (2014). "VADER: A Parsimonious Rule-based Model for Sentiment Analysis." ICWSM.
10. Baly et al. (2018). "Predicting Factuality of Reporting and Bias of News Media." EMNLP.

---

## 10. Cross-reference

| Topic | Document |
|-------|----------|
| Where each formula input is computed and stored | [PARAMETER_PROVENANCE.md](./PARAMETER_PROVENANCE.md) |
| Benchmark datasets, annotations, download | [DATASETS.md](./DATASETS.md) |
| How to run evaluations and CI | [EVALUATION.md](./EVALUATION.md) |
| System components | [ARCHITECTURE.md](./ARCHITECTURE.md) |
