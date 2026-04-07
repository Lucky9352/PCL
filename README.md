# IndiaGround

**Automated News Bias & Fact-Check Platform for India**

IndiaGround scrapes Indian news from multiple sources (Inshorts, Google News RSS, direct Indian outlet RSS feeds, and optionally NewsAPI), runs each article through a dual-pipeline NLP analysis (bias detection + fact-checking), clusters same-story coverage across outlets, and presents scored reliability results — similar to [Ground News](https://ground.news), built specifically for the Indian English news ecosystem.

---

## Status

| Phase | Module | Status |
|-------|--------|--------|
| 1 | Multi-Source Scraper (Inshorts + RSS + NewsAPI) | Done |
| 2 | Preprocessing (text clean, spaCy NER, langdetect, semantic dedup) | Done |
| 3 | unBIAS Module (VADER + RoBERTa + BART-MNLI + India-specific framing) | Done |
| 4 | Claim Detection (BART-MNLI two-pass check-worthiness + NLI, ddgs evidence) | Done |
| 5 | Aggregator (reliability formula v2 with decomposed components) | Done |
| 6 | Story Clustering (MiniLM embeddings, cross-source comparison) | Done |
| 7 | Backend API (FastAPI, 11 endpoints, async, cursor pagination) | Done |
| 8 | Frontend (React 19, 7 pages, dark theme, Recharts) | Done |
| 9 | Docker Compose (Postgres, Redis, API, Worker, Beat) | Done |
| 10 | Evaluation Framework (BABE, LIAR, CLEF benchmarks) | Done |
| 11 | Tests (27 unit tests passing) | Done |
| 12 | Research Documentation (METHODOLOGY, PARAMETER_PROVENANCE, DATASETS, EVALUATION, ARCHITECTURE, UI_BACKEND_MAP) | Done |

---

## Quick Start

```bash
cd ~/LIMP/PCL
cp .env.example .env
docker compose up -d postgres redis
bash scripts/reset_db.sh

# Terminal 1: API
cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Worker
cd backend && uv run celery -A app.core.celery_app worker -l info -c 2

# Terminal 3: Frontend
cd frontend && pnpm dev

# Trigger scrape
curl -X POST http://localhost:8000/api/v1/scrape/trigger
```

Open [http://localhost:5173](http://localhost:5173) — articles appear after ~2 minutes.

For a complete step-by-step verification guide, see [docs/MANUAL_VERIFICATION.md](docs/MANUAL_VERIFICATION.md).

---

## Verification

```bash
# One-shot checks (pytest, evaluations, ruff, frontend build)
bash scripts/verify_stack.sh

# Database reset + clean setup
bash scripts/reset_db.sh
```

- **Unit tests:** `cd backend && uv run pytest -v` — 27 tests
- **Evaluation sanity:** `cd backend && uv run python -m evaluation.evaluate_scoring`
- **Full eval orchestrator:** `cd backend && uv run python -m evaluation.run_all` (see [docs/EVALUATION.md](docs/EVALUATION.md))

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| **Language** | Python | 3.13 |
| **Backend** | FastAPI, SQLAlchemy (async), Alembic | Latest |
| **Tasks** | Celery + Redis | 5.5 / 8 |
| **Database** | PostgreSQL | 18 |
| **Frontend** | React, Vite, TailwindCSS | 19 / 8 / v4 |
| **Frontend libs** | React Router, React Query, Recharts, Lucide | v7 / v5 / v2 |
| **TypeScript** | TypeScript | 6.0 |
| **NLP/ML** | spaCy, VADER, Transformers, Sentence-Transformers | Latest |
| **ML Models** | BART-MNLI, RoBERTa sentiment, all-MiniLM-L6-v2, spaCy | HuggingFace / spacy.io |
| **Scraping** | httpx, feedparser, trafilatura | Latest |
| **Package Mgmt** | pnpm (frontend), uv (backend) | 10 / 0.11+ |

---

## Architecture

```
┌────────────────────────────────────────────────────┐
│               NEWS SOURCES                         │
│  ┌───────────────┐ ┌───────────┐ ┌──────────────┐  │
│  │  Inshorts     │ │ RSS Feeds │ │ NewsAPI.org  │  │
│  │  (JSON API)   │ │ (Google + │ │ (optional)   │  │
│  │  10 categories│ │ 10 Indian │ │ India top    │  │
│  └──────┬────────┘ │  outlets) │ │ headlines    │  │
│         │          └─────┬─────┘ └──────┬───────┘  │
└─────────┼────────────────┼──────────────┼──────────┘
          └────────────────┼──────────────┘
                           ▼
┌────────────────────────────────────────────────────┐
│  Celery Beat (periodic) + Manual Trigger           │
│  ┌─────────────────────────────┐                   │
│  │  scrape_inshorts task       │  ◀── Redis 8      │
│  │  (multi-source pipeline)    │      (broker)     │
│  └────────────┬────────────────┘                   │
│               │  SHA-256 + semantic dedup          │
│               ▼                                    │
│  ┌──────────────────────────────────────────────┐  │
│  │           ANALYSIS PIPELINE                  │  │
│  │                                              │  │
│  │  1. Preprocessor                             │  │
│  │     └─ spaCy NER → LangDetect → MiniLM dedup │  │
│  │        (cosine > 0.92 = duplicate)           │  │
│  │                                              │  │
│  │  2. unBIAS Module (HOW it's written)         │  │
│  │     ├─ VADER (headline sentiment)            │  │
│  │     ├─ RoBERTa (body sentiment)              │  │
│  │     ├─ BART-MNLI (bias types + framing)      │  │
│  │     └─ Token-level bias (100+ India terms)   │  │
│  │                                              │  │
│  │  3. ClaimBuster Module (WHAT it claims)      │  │
│  │     ├─ Two-pass BART-MNLI check-worthiness   │  │
│  │     ├─ ddgs / DuckDuckGo evidence retrieval  │  │
│  │     ├─ Google Fact Check Tools API (optional)│  │
│  │     └─ BART-MNLI NLI verification            │  │
│  │                                              │  │
│  │  4. Aggregator                               │  │
│  │     R = [(1-B)×0.35 + T×0.35                 │  │
│  │        + (1-S)×0.15 + (1-F)×0.15] × 100      │  │
│  │                                              │  │
│  │  5. Story Clustering                         │  │
│  │     └─ MiniLM embeddings (cosine > 0.75)     │  │
│  │        → cross-source metrics                │  │
│  └──────────────────────────────────────────────┘  │
│               │                                    │
│               ▼                                    │
│  ┌─────────────────────┐                           │
│  │  PostgreSQL 18      │                           │
│  │  • articles (41 col)│◀─── FastAPI (async)       │
│  │  • story_clusters   │     11 REST endpoints     │
│  │  • analysis_runs    │     ┌──────────────┐      │
│  │  • archived_articles│     │  React 19    │      │
│  │  • sources          │     │  7 pages     │      │
│  └─────────────────────┘     │  Vite + TS 6 │      │
│                              └──────────────┘      │
└────────────────────────────────────────────────────┘
```

---

## Project Structure

```
PCL/
├── package.json                 # Monorepo root scripts
├── pnpm-workspace.yaml          # packages: ["frontend"]
├── docker-compose.yml           # Postgres + Redis + API + Worker + Beat
├── .env.example                 # Documented env var template
├── scripts/
│   ├── reset_db.sh              # Drop all tables + migrate + verify + flush Redis
│   └── verify_stack.sh          # One-shot pytest + eval + ruff + frontend build
├── docs/
│   ├── ARCHITECTURE.md          # DB schema + pipeline architecture
│   ├── METHODOLOGY.md           # Full mathematical specification of all scores
│   ├── DATASETS.md              # Benchmark datasets for evaluation
│   ├── EVALUATION.md            # How to run evaluations + CI matrix
│   ├── PARAMETER_PROVENANCE.md  # Formula inputs → code → DB columns
│   ├── UI_BACKEND_MAP.md        # Every UI element ↔ backend field mapping
│   └── MANUAL_VERIFICATION.md   # Step-by-step flow verification guide
│
├── backend/
│   ├── pyproject.toml           # Python deps + ruff + pytest config
│   ├── Dockerfile               # Python 3.13 + uv + spaCy
│   ├── alembic.ini              # DB migration config
│   ├── alembic/
│   │   ├── env.py               # Imports all models for autogenerate
│   │   └── versions/            # 2 migration files (initial + story clusters)
│   ├── app/
│   │   ├── main.py              # FastAPI app factory + CORS + rate limiting
│   │   ├── core/
│   │   │   ├── __init__.py      # Pydantic BaseSettings (all env vars, ML device)
│   │   │   ├── celery_app.py    # Celery + Redis + beat schedule (3 periodic tasks)
│   │   │   └── logging.py       # Loguru structured logging
│   │   ├── db/
│   │   │   ├── base.py          # SQLAlchemy DeclarativeBase
│   │   │   ├── models.py        # Article, StoryCluster, ArchivedArticle, AnalysisRun, Source
│   │   │   ├── session.py       # Async engine + session factory
│   │   │   └── __init__.py      # Clean exports
│   │   ├── schemas/
│   │   │   ├── article.py       # ArticleCard, ArticleDetail, ArticleAnalysis
│   │   │   ├── analysis.py      # ClaimSchema, BiasAnalysisSchema, FactCheckSchema
│   │   │   └── stats.py         # DashboardStats, CategoryStats, SourceStats
│   │   ├── api/v1/
│   │   │   ├── router.py        # Aggregated router (7 sub-routers)
│   │   │   ├── health.py        # GET /health
│   │   │   ├── articles.py      # GET /articles, GET /{id}, GET /{id}/analysis
│   │   │   ├── categories.py    # GET /categories
│   │   │   ├── stats.py         # GET /stats
│   │   │   ├── stories.py       # GET /stories, GET /stories/{id}
│   │   │   ├── methodology.py   # GET /methodology
│   │   │   └── scrape.py        # POST /scrape/trigger, POST /scrape/cluster-backfill
│   │   ├── services/
│   │   │   ├── scraper.py       # Inshorts JSON API scraper
│   │   │   ├── rss_scraper.py   # Google News + Indian outlet RSS feeds
│   │   │   ├── newsapi_scraper.py # NewsAPI.org integration (optional)
│   │   │   ├── preprocessor.py  # Text clean + spaCy + langdetect + dedup
│   │   │   ├── unbias.py        # VADER + RoBERTa + BART-MNLI + token bias
│   │   │   ├── claimbuster.py   # BART-MNLI claims + NLI + ddgs evidence
│   │   │   ├── aggregator.py    # Reliability formula + score aggregation
│   │   │   ├── scoring.py       # Pure scoring functions + SCORING_METHODOLOGY
│   │   │   ├── story_cluster.py # Embedding + clustering logic
│   │   │   └── story_cluster_sync.py # DB persistence for clusters
│   │   ├── tasks/
│   │   │   ├── scrape_task.py   # Multi-source scrape (Inshorts + RSS + NewsAPI)
│   │   │   ├── analyze_task.py  # 5-step analysis pipeline
│   │   │   ├── cleanup_task.py  # 7-day article archival
│   │   │   └── cluster_task.py  # Backfill story clusters
│   │   └── utils/
│   │       ├── hashing.py       # SHA-256 content hash for dedup
│   │       └── source_credibility.py  # 136 Indian/international sources → tiers + bias
│   ├── evaluation/
│   │   ├── evaluate_scoring.py  # Scoring sanity checks (no datasets needed)
│   │   ├── evaluate_tokens.py   # Token-level bias evaluation
│   │   ├── evaluate_bias.py     # BABE dataset evaluation
│   │   ├── evaluate_claims.py   # LIAR + CLEF evaluation
│   │   ├── run_all.py           # Orchestrator for all benchmarks
│   │   └── datasets/README.md   # Where to place benchmark datasets
│   └── tests/
│       ├── conftest.py          # Fixtures (sample article, bias, factcheck data)
│       ├── test_aggregator.py   # 14 tests — reliability score + aggregation
│       ├── test_utils.py        # 11 tests — content hash + source credibility
│       └── test_evaluation_smoke.py # 2 tests — evaluation sanity
│
└── frontend/
    ├── package.json             # React 19 + Vite 8 + all frontend deps
    ├── vite.config.ts           # @/ alias + API proxy to :8000
    └── src/
        ├── App.tsx              # 7 routes + Navbar layout
        ├── api/client.ts        # Axios + TypeScript interfaces + API functions
        ├── components/
        │   ├── Navbar.tsx       # 5-link navigation with icons
        │   ├── ArticleCard.tsx  # Image, badges, reliability meter, source type
        │   ├── ReliabilityMeter.tsx  # Animated gradient progress bar
        │   ├── CategoryBadge.tsx    # Category-specific emoji + color
        │   └── StatsCard.tsx    # Dashboard metric card
        └── pages/
            ├── Home.tsx         # Hero, search, filters, article grid, scrape button
            ├── ArticleDetail.tsx # Bias, trust, claims, flagged tokens
            ├── Stories.tsx      # Cross-source story clusters
            ├── StoryDetail.tsx  # Per-outlet comparison for one story
            ├── Categories.tsx   # Category grid with article counts
            ├── Dashboard.tsx    # Stats cards + Recharts (bar, pie, histogram)
            └── Methodology.tsx  # Scoring formulas + pipeline + datasets
```

---

## Prerequisites

| Tool | Min Version | Install / Check |
|------|-------------|-----------------|
| **Docker** | 27+ | `docker --version` |
| **Docker Compose** | v2.30+ | `docker compose version` |
| **Python** | 3.13+ | `python3 --version` |
| **uv** | 0.11+ | `uv --version` — install: `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **Node.js** | 25+ | `node --version` |
| **pnpm** | 10+ | `pnpm --version` — install: `npm install -g pnpm@10` |

---

## Setup & Running (Step by Step)

> **You need 4-5 terminal windows.** Run each step in order.

### Step 0 — Environment File (one-time)

```bash
cd ~/LIMP/PCL
cp .env.example .env
```

### Step 1 — Infrastructure: PostgreSQL + Redis (Terminal 1)

```bash
docker compose up -d postgres redis
docker compose ps   # Both should show "healthy"
```

### Step 2 — Database Setup

```bash
# Fresh reset (drops everything, runs migrations, verifies schema)
bash scripts/reset_db.sh

# Or just apply migrations on existing DB:
cd backend && uv run alembic upgrade head
```

### Step 3 — Backend API Server (Terminal 2)

```bash
cd ~/LIMP/PCL/backend
uv sync --all-groups                          # First time only
uv run python -m spacy download en_core_web_sm # First time only
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)

### Step 4 — Celery Worker (Terminal 3)

```bash
cd ~/LIMP/PCL/backend
uv run celery -A app.core.celery_app worker -l info -c 2
```

### Step 5 — Frontend (Terminal 4)

```bash
cd ~/LIMP/PCL/frontend
pnpm install   # First time only
pnpm dev
```

Open [http://localhost:5173](http://localhost:5173)

### Step 6 — Celery Beat (Terminal 5, Optional)

```bash
cd ~/LIMP/PCL/backend
uv run celery -A app.core.celery_app beat -l info
```

Auto-triggers scrape every 30 minutes + analysis every 10 minutes + archival at 2 AM.

---

## API Reference

All endpoints are prefixed with `/api/v1`.

| Method | Endpoint | Query Params | Description |
|--------|----------|-------------|-------------|
| `GET` | `/health` | — | Health check |
| `GET` | `/articles` | `page_size`, `cursor`, `category`, `bias`, `trust_min`, `search`, `status` | List articles (cursor-based pagination) |
| `GET` | `/articles/{id}` | — | Full article detail |
| `GET` | `/articles/{id}/analysis` | — | Full analysis breakdown (bias, claims, tokens) |
| `GET` | `/categories` | — | All categories with article counts |
| `GET` | `/stats` | — | Dashboard aggregates (avg scores, distributions, top sources) |
| `GET` | `/stories` | `page_size`, `category`, `min_sources` | Story clusters (multi-source comparison) |
| `GET` | `/stories/{cluster_id}` | — | One story + all source articles |
| `GET` | `/methodology` | — | Scoring formulas + pipeline metadata |
| `POST` | `/scrape/trigger` | — | Dispatch multi-source scrape to Celery |
| `POST` | `/scrape/cluster-backfill` | `limit` | Backfill `story_cluster_id` for analyzed articles |

**Interactive docs:** [http://localhost:8000/api/docs](http://localhost:8000/api/docs)

---

## Reliability Score Formula

```
R = [(1 - B) × 0.35 + T × 0.35 + (1 - S) × 0.15 + (1 - F) × 0.15] × 100
```

| Component | Weight | What it measures |
|-----------|--------|-----------------|
| `1 - B` (bias inversion) | 0.35 | Lower bias → higher reliability |
| `T` (trust score) | 0.35 | Factual verification quality |
| `1 - S` (sensationalism penalty) | 0.15 | Penalises loaded/sensational language |
| `1 - F` (framing neutrality) | 0.15 | Neutral framing → higher reliability |

**Bias Score:** `B = sentiment × 0.15 + bias_types × 0.35 + token_density × 0.20 + framing × 0.30`

**Trust Score:** `T = evidence × 0.50 + source × 0.30 + coverage × 0.20`

Full mathematical specification: [docs/METHODOLOGY.md](docs/METHODOLOGY.md)

---

## Database Schema

### `articles` (41 columns — hot table, last 7 days)

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID PK | Auto-generated |
| `title` | TEXT | Article headline |
| `synopsis` | TEXT | Summary text |
| `source_name` | TEXT | Original publisher (e.g. "The Hindu") |
| `source_type` | VARCHAR(20) | `inshorts`, `rss`, or `newsapi` |
| `content_hash` | VARCHAR(64) UNIQUE | SHA-256 dedup key |
| `status` | VARCHAR(20) | raw → preprocessed → analyzed → failed |
| `bias_score` | FLOAT | 0–1 (from unBIAS module) |
| `bias_label` | VARCHAR | left / center / right |
| `trust_score` | FLOAT | 0–1 (from ClaimBuster module) |
| `reliability_score` | FLOAT | 0–100 (from Aggregator) |
| `framing` | JSONB | India-specific framing analysis |
| `political_lean` | JSONB | Score + label + components |
| `bias_score_components` | JSONB | Decomposed bias sub-scores |
| `trust_score_components` | JSONB | Evidence + source + coverage |
| `reliability_components` | JSONB | All four weighted components |
| `story_cluster_id` | UUID FK | Links to `story_clusters.id` |
| `cluster_similarity` | FLOAT | Cosine similarity to cluster centroid |
| `top_claims` | JSONB | Verified claims with verdicts |
| `flagged_tokens` | JSONB | Biased words + neutral suggestions |

### `story_clusters` (12 columns)

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID PK | Cluster ID |
| `representative_title` | TEXT | First article title |
| `article_count` | INT | Articles in this cluster |
| `unique_sources` | JSONB | List of distinct outlet names |
| `bias_spectrum` | JSONB | `{left: N, center: N, right: N}` |
| `avg_reliability_score` | FLOAT | Mean reliability across articles |
| `centroid_embedding` | JSONB | Mean MiniLM embedding (384-dim) |

### Other tables

- `archived_articles` (42 columns) — Same as articles, for records older than 7 days
- `analysis_runs` — Audit trail of each ML model run per article
- `sources` — Static credibility tier mapping (136 Indian/international outlets)

---

## Documentation

| Document | Description |
|----------|-------------|
| [docs/METHODOLOGY.md](docs/METHODOLOGY.md) | Full mathematical specification of all scoring formulas |
| [docs/DATASETS.md](docs/DATASETS.md) | Benchmark datasets (BABE, LIAR, CLEF, NELA-GT, MBIC) |
| [docs/EVALUATION.md](docs/EVALUATION.md) | Evaluation suites, CI checklist, paper reporting |
| [docs/PARAMETER_PROVENANCE.md](docs/PARAMETER_PROVENANCE.md) | Where each score input is computed and stored |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Detailed architecture + DB schema |
| [docs/UI_BACKEND_MAP.md](docs/UI_BACKEND_MAP.md) | Every UI element mapped to backend fields |
| [docs/MANUAL_VERIFICATION.md](docs/MANUAL_VERIFICATION.md) | Step-by-step flow verification guide |

---

## Environment Variables

All variables live in `.env`. Run `cp .env.example .env` — **the defaults work out of the box.**

### Required (pre-filled)

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `postgresql+asyncpg://...localhost:5432/indiaground` | Async DB connection |
| `DATABASE_URL_SYNC` | `postgresql://...localhost:5432/indiaground` | Sync DB for Alembic + Celery |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | Redis cache |
| `CELERY_BROKER_URL` | `redis://127.0.0.1:6379/0` | Celery message broker |
| `SECRET_KEY` | (generate your own) | App secret key |

### Optional API Keys

| Variable | Purpose | Without It |
|----------|---------|-----------|
| `NEWSAPI_KEY` | Enable NewsAPI.org scraping (free: 100 req/day) | RSS + Inshorts still work |
| `GOOGLE_FACTCHECK_API_KEY` | Professional fact-check lookup | DuckDuckGo evidence still works |

### ML / Performance

| Variable | Default | Purpose |
|----------|---------|---------|
| `ML_DEVICE` | `auto` | GPU detection: cuda > mps > cpu |
| `SCRAPE_INTERVAL_MINUTES` | `30` | Celery beat scrape frequency |

---

## What Works Without API Keys

| Feature | Status |
|---------|--------|
| Multi-source scraping (Inshorts + RSS) | Works |
| Preprocessing (spaCy + langdetect + dedup) | Works |
| Bias detection (VADER + RoBERTa + BART-MNLI) | Works |
| Claim extraction (BART-MNLI two-pass) | Works |
| Evidence retrieval (DuckDuckGo) | Works |
| Claim verification (BART-MNLI NLI) | Works |
| Source credibility (136 outlets) | Works |
| Story clustering | Works |
| All frontend pages | Works |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `psql: command not found` | `sudo apt install postgresql-client` |
| `spaCy model not found` | `cd backend && uv run python -m spacy download en_core_web_sm` |
| Port 5432 connection refused | `docker compose up -d postgres` |
| Port 6379 connection refused | `docker compose up -d redis` |
| Frontend CORS errors | Backend not on port 8000, check `CORS_ORIGINS` in `.env` |
| `ModuleNotFoundError` (Python) | `cd backend && uv sync --all-groups` |
| `Cannot find module` (frontend) | `cd frontend && pnpm install` |
| First analysis very slow | ML models downloading (~2.2GB). Wait 3-5 minutes. |
| Stories page empty | Run scrape + wait for analysis, or: `curl -X POST http://localhost:8000/api/v1/scrape/cluster-backfill` |

---

## License

Academic / educational use — college PCL project.
