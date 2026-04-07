# IndiaGround — System Architecture

**Version 2.1.0** | Updated April 2026

---

## High-Level Architecture

```
┌─────────────────────────────────────────────┐
│            NEWS SOURCE LAYER                │
│                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐     │
│  │ Inshorts │ │Google RSS│ │ NewsAPI  │     │
│  │ JSON API │ │+ Direct  │ │ (opt.)   │     │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘     │
└───────┼─────────────┼────────────┼──────────┘
        │             │            │
        ▼             ▼            ▼
┌─────────────────────────────────────────────┐
│         UNIFIED INGESTION PIPELINE          │
│                                             │
│  Normalise → SHA-256 dedup → PostgreSQL     │
│  source_type tracking (inshorts/rss/newsapi)│
└────────────────────┬────────────────────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│Preprocess│  │ unBIAS   │  │ClaimBust │
│          │  │ (HOW)    │  │ (WHAT)   │
│spaCy NER │  │          │  │          │
│langdetect│  │Sentiment │  │Checkwrth │
│MiniLM    │  │Bias types│  │Evidence  │
│dedup     │  │Framing   │  │NLI       │
│          │  │Tokens    │  │Trust     │
└────┬─────┘  └────┬─────┘  └────┬─────┘
     │             │              │
     │             ▼              ▼
     │      ┌─────────────────────────┐
     │      │      AGGREGATOR         │
     │      │                         │
     │      │ reliability = f(bias,   │
     │      │   trust, sensationalism,│
     │      │   framing)              │
     │      └───────────┬─────────────┘
     │                  │
     ▼                  ▼
┌─────────────────────────────────────────────┐
│            STORY CLUSTERING                 │
│                                             │
│  MiniLM embeddings → cosine > 0.75 →        │
│  Agglomerative clustering → cross-source    │
│  analysis (diversity, bias spectrum)        │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│              DATA LAYER                     │
│                                             │
│  PostgreSQL 18          Redis 8             │
│  ├─ articles            ├─ Celery broker    │
│  ├─ story_clusters      └─ Cache            │
│  ├─ analysis_runs                           │
│  ├─ archived_articles                       │
│  └─ sources                                 │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│            API + FRONTEND                   │
│                                             │
│  FastAPI (async)         React 19 + Vite    │
│  ├─ /articles            ├─ Feed            │
│  ├─ /stories             ├─ Stories (new)   │
│  ├─ /categories          ├─ Article Detail  │
│  ├─ /stats               ├─ Categories      │
│  ├─ /methodology (new)   ├─ Dashboard       │
│  └─ /scrape/trigger      └─ Methodology     │
└─────────────────────────────────────────────┘
```

---

## Database Schema

### `articles` (hot table — last 7 days)

| Column | Type | Purpose |
|--------|------|---------|
| id | UUID PK | Auto-generated |
| title | TEXT | Article headline |
| synopsis | TEXT | Article body / summary |
| author | TEXT | Writer name |
| published_at | TIMESTAMPTZ | Original publish time |
| category | VARCHAR(100) | national, business, sports, etc. |
| source_name | TEXT | Original publisher |
| source_url | TEXT | Link to original article |
| source_type | VARCHAR(20) | inshorts \| rss \| newsapi |
| image_url | TEXT | Article image |
| content_hash | VARCHAR(64) UNIQUE | SHA-256 dedup key |
| status | VARCHAR(20) | raw → preprocessed → analyzed → failed |
| bias_score | FLOAT | 0–1 (1 = highly biased) |
| bias_label | VARCHAR(20) | left / center / right |
| sentiment_score | FLOAT | -1 to +1 |
| trust_score | FLOAT | 0–1 (1 = trustworthy) |
| reliability_score | FLOAT | 0–100 (final composite) |
| framing | JSONB | Framing analysis output |
| political_lean | JSONB | Political lean breakdown |
| bias_score_components | JSONB | Component-level bias breakdown |
| trust_score_components | JSONB | Component-level trust breakdown |
| reliability_components | JSONB | Component-level reliability breakdown |
| model_confidence | FLOAT | Mean model confidence |
| top_claims | JSONB | Verified claims array |
| flagged_tokens | JSONB | Biased words + replacements |
| story_cluster_id | UUID FK | Link to story_clusters |
| cluster_similarity | FLOAT | Cosine similarity to cluster centroid |

### `story_clusters` (new)

| Column | Type | Purpose |
|--------|------|---------|
| id | UUID PK | Auto-generated |
| representative_title | TEXT | Title of seed article |
| category | VARCHAR(100) | Story category |
| article_count | INTEGER | Number of articles in cluster |
| source_diversity | FLOAT | unique_sources / 10 |
| bias_spectrum | JSONB | {left: n, center: n, right: n} |
| avg_reliability_score | FLOAT | Mean reliability across sources |
| avg_trust_score | FLOAT | Mean trust across sources |
| unique_sources | JSONB | List of source names |
| centroid_embedding | JSONB | Mean MiniLM embedding for incremental cluster assignment |

### `analysis_runs` — Audit trail per model run

### `archived_articles` — Articles older than 7 days

### `sources` — Static source credibility tiers (136 outlets)

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/health | Health check |
| GET | /api/v1/articles | Paginated article list with filters |
| GET | /api/v1/articles/{id} | Full article detail |
| GET | /api/v1/articles/{id}/analysis | Detailed analysis breakdown |
| GET | /api/v1/stories | Story clusters (multi-source) |
| GET | /api/v1/stories/{id} | Single story with all source articles |
| GET | /api/v1/categories | Categories with counts |
| GET | /api/v1/stats | Dashboard aggregates |
| GET | /api/v1/methodology | Scoring formulas + pipeline docs |
| POST | /api/v1/scrape/trigger | Dispatch multi-source scrape |

---

## ML Models

| Model | Size | Pipeline | Task |
|-------|------|----------|------|
| VADER | <1MB | unBIAS | Headline sentiment |
| twitter-roberta-base-sentiment-latest | ~500MB | unBIAS | Body sentiment |
| facebook/bart-large-mnli | ~1.6GB | unBIAS + ClaimBuster | ZS bias, framing, 2-pass check-worthiness, NLI |
| all-MiniLM-L6-v2 | ~90MB | Preprocess | Dedup, clustering |
| en_core_web_sm (spaCy) | ~15MB | Preprocess | NER, tokenisation |

---

## Evaluation Framework

Located in `backend/evaluation/`:

| Script | Dataset | Metrics |
|--------|---------|---------|
| evaluate_bias.py | BABE | Accuracy, F1, P/R |
| evaluate_claims.py | LIAR, CLEF | Macro-F1, AP@5 |
| run_all.py | All | Unified report |

See [DATASETS.md](./DATASETS.md), [EVALUATION.md](./EVALUATION.md), and [PARAMETER_PROVENANCE.md](./PARAMETER_PROVENANCE.md).
