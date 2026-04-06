# IndiaGround

**Automated News Bias & Fact-Check Platform for India**

IndiaGround scrapes Indian news from Inshorts, runs each article through a multi-model NLP pipeline (bias detection + fact-checking), and presents a scored reliability result — similar to [Ground News](https://ground.news).

> **Target**: College PCL demo (local deployment). Backend is primary evaluation criterion.

---

## Status

| Phase | Module | Status |
|-------|--------|--------|
| 1 | Scraper (Inshorts, 10 categories, Playwright + BS4) | ✅ Done |
| 2 | Preprocessing (text clean, spaCy NER, langdetect, semantic dedup) | ✅ Done |
| 3 | unBIAS Module (VADER + RoBERTa + BART-MNLI + Dbias) | ✅ Done |
| 4 | ClaimBuster Module (API + heuristic, DuckDuckGo, Google FC, NLI) | ✅ Done |
| 5 | Aggregator (reliability formula, unit tests) | ✅ Done |
| 6 | Backend API (FastAPI, 7 endpoints, async, cursor pagination) | ✅ Done |
| 7 | Frontend (React 19, 4 pages, dark theme, Recharts) | ✅ Done |
| 8 | Docker Compose (Postgres, Redis, API, Worker, Beat) | ✅ Done |
| 9 | Tests (22 unit tests passing) | ✅ Done |
| 10 | Docs & Architecture | ✅ Done |

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
| **NLP/ML** | spaCy, VADER, Transformers, Sentence-Transformers, Dbias | Latest |
| **ML Models** | BART-MNLI, RoBERTa, all-MiniLM-L6-v2 | HuggingFace |
| **Scraping** | Playwright (headless Chromium) + httpx/BS4 fallback | Latest |
| **Package Mgmt** | pnpm (frontend), uv (backend) | 10 / 0.11+ |

---

## Architecture

```
┌──────────────────┐
│   Inshorts.com    │  10 categories (national, business, sports, world,
│   (news source)   │  politics, technology, startup, entertainment,
└────────┬─────────┘  science, automobile)
         │
         │  Playwright headless / httpx+BS4 fallback
         ▼
┌──────────────────┐       ┌──────────────┐
│   Celery Beat     │──────▶│   Redis 8     │
│   (every 30 min)  │       │   (broker)    │
└────────┬─────────┘       └──────────────┘
         │
         ▼
┌──────────────────┐
│  Scrape Task      │  SHA-256 dedup → PostgreSQL
└────────┬─────────┘
         │  triggers on new articles
         ▼
┌────────────────────────────────────────────┐
│         ANALYSIS PIPELINE                  │
│                                            │
│  1. Preprocessor                           │
│     └─ Text clean → spaCy NER → LangDetect│
│        → Sentence-Transformers dedup (>0.92)│
│                                            │
│  2. unBIAS Module (HOW things are said)    │
│     ├─ VADER (headline sentiment)          │
│     ├─ RoBERTa (body sentiment)            │
│     ├─ BART-MNLI (multi-label bias types)  │
│     └─ Dbias (token-level flagging)        │
│                                            │
│  3. ClaimBuster Module (WHAT is true)      │
│     ├─ ClaimBuster API / heuristic fallback│
│     ├─ DuckDuckGo evidence retrieval       │
│     ├─ Google Fact Check Tools API         │
│     └─ BART-MNLI NLI verification          │
│                                            │
│  4. Aggregator                             │
│     └─ reliability = (1-bias)*0.40         │
│          + trust*0.40                      │
│          + (1-sensationalism)*0.20          │
│        scaled to 0-100                     │
└────────────────┬───────────────────────────┘
                 │
                 ▼
┌──────────────────┐       ┌──────────────────┐
│  PostgreSQL 18    │◀──────│  FastAPI (async)  │
│  (articles,       │       │  7 REST endpoints │
│   analysis_runs,  │       └────────┬─────────┘
│   sources)        │                │
└──────────────────┘                ▼
                          ┌──────────────────┐
                          │  React 19 + Vite  │
                          │  (dark theme UI)  │
                          │                   │
                          │  • Home feed      │
                          │  • Article detail  │
                          │  • Categories     │
                          │  • Dashboard      │
                          └──────────────────┘
```

---

## Project Structure

```
PCL/
├── package.json                 # Monorepo root scripts (pnpm dev, lint, test:be, etc.)
├── pnpm-workspace.yaml          # packages: ["frontend"]
├── docker-compose.yml           # Postgres + Redis + API + Celery Worker + Beat
├── .env                         # Local config (copy from .env.example)
├── .env.example                 # Documented env var template
├── .gitignore                   # Root gitignore
├── README.md                    # ← This file
├── docs/
│   └── ARCHITECTURE.md          # Detailed architecture & DB schema docs
│
├── backend/
│   ├── .python-version          # 3.13
│   ├── pyproject.toml           # All Python deps + ruff + pytest config
│   ├── Dockerfile               # Python 3.13 + uv + spaCy + Playwright
│   ├── .dockerignore
│   ├── alembic.ini              # DB migration config
│   ├── alembic/
│   │   ├── env.py               # Async-aware, imports all models
│   │   ├── script.py.mako       # Migration template
│   │   └── versions/            # Auto-generated migration files
│   ├── app/
│   │   ├── main.py              # FastAPI app factory + CORS + rate limiting
│   │   ├── core/
│   │   │   ├── __init__.py      # Pydantic BaseSettings (all env vars, ML device detection)
│   │   │   ├── config.py        # Re-export convenience
│   │   │   ├── celery_app.py    # Celery + Redis + beat schedule
│   │   │   └── logging.py       # Loguru structured JSON logging
│   │   ├── db/
│   │   │   ├── base.py          # SQLAlchemy DeclarativeBase
│   │   │   ├── models.py        # Article, ArchivedArticle, AnalysisRun, Source
│   │   │   ├── session.py       # Async engine + session factory
│   │   │   └── __init__.py      # Clean exports
│   │   ├── schemas/
│   │   │   ├── article.py       # Request/response schemas (card, detail, analysis)
│   │   │   ├── analysis.py      # ClaimSchema, BiasAnalysisSchema, FactCheckSchema
│   │   │   ├── stats.py         # DashboardStats, CategoryStats, SourceStats
│   │   │   └── __init__.py
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── router.py    # Aggregated router (5 sub-routers)
│   │   │       ├── health.py    # GET /health
│   │   │       ├── articles.py  # GET /articles, GET /{id}, GET /{id}/analysis
│   │   │       ├── categories.py # GET /categories
│   │   │       ├── stats.py     # GET /stats (full dashboard aggregates)
│   │   │       └── scrape.py    # POST /scrape/trigger
│   │   ├── services/
│   │   │   ├── scraper.py       # Playwright + BS4 Inshorts scraper (286 lines)
│   │   │   ├── preprocessor.py  # Text clean + spaCy + langdetect + dedup (220 lines)
│   │   │   ├── unbias.py        # VADER + RoBERTa + BART-MNLI + Dbias (314 lines)
│   │   │   ├── claimbuster.py   # API + heuristic + DDG + Google FC + NLI (360 lines)
│   │   │   └── aggregator.py    # Reliability formula + aggregation (98 lines)
│   │   ├── tasks/
│   │   │   ├── scrape_task.py   # Celery periodic scrape (every 30 min)
│   │   │   ├── analyze_task.py  # Full 5-step analysis pipeline
│   │   │   └── cleanup_task.py  # 7-day article archival
│   │   └── utils/
│   │       ├── hashing.py       # SHA-256 content hash for dedup
│   │       └── source_credibility.py  # 50+ Indian sources → credibility tiers
│   └── tests/
│       ├── conftest.py          # Fixtures (sample article, bias, factcheck data)
│       ├── test_aggregator.py   # 11 tests — reliability score formula + aggregation
│       └── test_utils.py        # 11 tests — content hash + source credibility lookup
│
└── frontend/
    ├── package.json             # React 19 + Vite 8 + all frontend deps
    ├── tsconfig.json            # Root TS config (references app + node)
    ├── tsconfig.app.json        # App TS config (TS 6.0 compatible)
    ├── tsconfig.node.json       # Node TS config
    ├── vite.config.ts           # @/ alias + API proxy to :8000
    ├── postcss.config.mjs       # TailwindCSS v4
    ├── eslint.config.js         # React hooks + refresh
    ├── index.html               # SEO meta + Google Fonts (Inter, JetBrains Mono)
    ├── public/
    │   ├── favicon.svg          # Shield icon
    │   └── icons.svg            # Icon sprites
    └── src/
        ├── main.tsx             # React Query + Router + StrictMode
        ├── App.tsx              # 4 routes + Navbar layout
        ├── index.css            # Design system (164 lines — colors, animations, glass)
        ├── api/
        │   └── client.ts        # Axios + all TypeScript interfaces + 6 API functions
        ├── lib/
        │   └── utils.ts         # cn(), scoreColor(), biasColor(), timeAgo()
        ├── components/
        │   ├── Navbar.tsx       # Glassmorphism nav + gradient logo + active states
        │   ├── ArticleCard.tsx  # Image, badge, reliability meter, hover animations
        │   ├── ReliabilityMeter.tsx  # Animated gradient progress bar
        │   ├── CategoryBadge.tsx    # 10 categories with emoji + colors
        │   └── StatsCard.tsx    # Accent glow + icon + metric display
        └── pages/
            ├── Home.tsx         # Hero, search, category filters, article grid, scrape button
            ├── ArticleDetail.tsx # Full analysis: bias, trust, claims, flagged tokens (512 lines)
            ├── Categories.tsx   # Category grid with article counts
            └── Dashboard.tsx    # Stats cards + Recharts (bar, pie, histogram)
```

---

## Prerequisites

You need these installed before anything else:

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

> **You need 4-5 terminal windows.** Run each step in order. Each section = one terminal.

### Step 0 — Environment File (one-time)

```bash
cd ~/LIMP/PCL
cp .env.example .env
# The defaults work out of the box for local dev.
# API keys are optional — the system uses built-in fallbacks.
```

---

### Step 1 — Infrastructure: PostgreSQL + Redis (Terminal 1)

```bash
cd ~/LIMP/PCL

# Start the database and cache containers
docker compose up postgres redis -d

# Verify both are healthy (wait 10-15 seconds)
docker compose ps
# Should show:
#   postgres   running (healthy)
#   redis      running (healthy)
```

**What this does:**
- Starts **PostgreSQL 18** on port `5432` — stores all articles, analysis results, scores
- Starts **Redis 8** on port `6379` — message broker for Celery task queue
- `-d` = runs in background so your terminal stays free
- Data persists in a Docker volume (`pgdata`) between restarts

**Useful docker commands:**
```bash
docker compose ps              # Check status
docker compose logs postgres   # PostgreSQL logs
docker compose logs redis      # Redis logs
docker compose down            # Stop containers (data survives)
docker compose down -v         # Stop + DELETE all data (fresh start)
```

---

### Step 2 — Backend Setup & API Server (Terminal 2)

```bash
cd ~/LIMP/PCL/backend

# Install all Python dependencies (first time only, ~2 min)
uv sync --all-groups

# Download spaCy English model (first time only, ~15MB)
uv run python -m spacy download en_core_web_sm

# Install Playwright browser (first time only, ~130MB)
uv run playwright install chromium

# Create database tables (first time, or after model changes)
uv run alembic revision --autogenerate -m "initial_schema"
uv run alembic upgrade head

# Start the API server (auto-reloads on code changes)
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Verify:** Open [http://localhost:8000/api/docs](http://localhost:8000/api/docs) — you should see the Swagger UI.

---

### Step 3 — Celery Worker (Terminal 3)

```bash
cd ~/LIMP/PCL/backend

# Start the worker that processes scrape + analysis tasks
uv run celery -A app.core.celery_app worker -l info -c 2
```

**What this does:**
- Listens on Redis for task messages
- When a scrape is triggered, it runs the Playwright scraper
- After scraping, automatically runs the full NLP analysis pipeline
- `-c 2` = 2 concurrent worker threads

**You should see output like:**
```
[tasks]
  . app.tasks.analyze_task.analyze_pending_articles
  . app.tasks.cleanup_task.archive_old_articles
  . app.tasks.scrape_task.scrape_inshorts
```

---

### Step 4 — Frontend (Terminal 4)

```bash
cd ~/LIMP/PCL/frontend

# Install Node dependencies (first time only)
pnpm install

# Start Vite dev server
pnpm dev
```

**Verify:** Open [http://localhost:5173](http://localhost:5173) — you should see the IndiaGround dark-themed UI.

---

### Step 5 — Celery Beat (Terminal 5, Optional)

```bash
cd ~/LIMP/PCL/backend

# Start the periodic scheduler
uv run celery -A app.core.celery_app beat -l info
```

**What this does:**
- Automatically triggers a scrape every 30 minutes
- Triggers article archival at 2:00 AM daily
- Without this, you can still scrape manually via the UI or API

---

## Testing the Platform

### Quick Test Flow

```bash
# 1. Health check (should work immediately after Step 2)
curl http://localhost:8000/api/v1/health
# → {"success":true,"data":{"status":"healthy","service":"IndiaGround API","version":"0.1.0"}}

# 2. Trigger a scrape (requires Step 3 — Celery worker running)
curl -X POST http://localhost:8000/api/v1/scrape/trigger
# → {"success":true,"data":{"message":"Scrape task dispatched","task_id":"..."}}

# 3. Watch Terminal 3 (Celery) — you'll see:
#    🕷️ Starting Inshorts scrape job
#    Scraping Inshorts category: national
#    ...
#    ✅ Scrape complete: 45 inserted, 0 duplicates skipped
#    🔬 Starting analysis pipeline for pending articles
#    → Running bias analysis...
#    → Running fact-check analysis...
#    → Aggregating scores...
#    ✅ Complete: reliability=72.3 bias=0.234 trust=0.789

# 4. List articles (after scrape completes — takes 2-5 min first time)
curl "http://localhost:8000/api/v1/articles?page_size=5" | python3 -m json.tool

# 5. Get article detail (replace {ID} with a real UUID from step 4)
curl "http://localhost:8000/api/v1/articles/{ID}" | python3 -m json.tool

# 6. Get analysis breakdown
curl "http://localhost:8000/api/v1/articles/{ID}/analysis" | python3 -m json.tool

# 7. Categories
curl http://localhost:8000/api/v1/categories | python3 -m json.tool

# 8. Dashboard stats
curl http://localhost:8000/api/v1/stats | python3 -m json.tool
```

### UI Testing

1. **Home** ([localhost:5173](http://localhost:5173)) — Click "Scrape Now", watch articles appear
2. Click any article → **Article Detail** — Full bias/trust breakdown, flagged tokens, claim verdicts
3. **Categories** ([localhost:5173/categories](http://localhost:5173/categories)) — Browse by topic
4. **Dashboard** ([localhost:5173/dashboard](http://localhost:5173/dashboard)) — Charts and analytics

### Unit Tests

```bash
cd ~/LIMP/PCL/backend
uv run pytest -v
# → 22 passed (11 aggregator + 11 utils)
```

### Frontend Build Check

```bash
cd ~/LIMP/PCL/frontend
pnpm build
# → ✓ built in ~400ms
```

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
| `GET` | `/stats` | — | Dashboard aggregates (avg bias/trust, distributions, top sources) |
| `POST` | `/scrape/trigger` | — | Dispatch a manual scrape job to Celery |

**Interactive docs:** [http://localhost:8000/api/docs](http://localhost:8000/api/docs) (Swagger UI, only in dev mode)

---

## Root Monorepo Scripts

Run from the repo root (`~/LIMP/PCL`):

| Script | What it does |
|--------|-------------|
| `pnpm dev` | Start Vite dev server (frontend) |
| `pnpm build` | Production build (frontend) |
| `pnpm preview` | Preview production build |
| `pnpm lint` | ESLint check (frontend) |
| `pnpm lint:fix` | ESLint auto-fix (frontend) |
| `pnpm typecheck` | TypeScript type check (frontend) |
| `pnpm lint:be` | Ruff lint (backend) |
| `pnpm format:be` | Ruff format (backend) |
| `pnpm format:be:check` | Check Ruff formatting (backend) |
| `pnpm test:be` | Run pytest (backend) |
| `pnpm lint:all` | Lint frontend + backend |
| `pnpm check` | All quality gates (lint + typecheck + test + format) |
| `pnpm ci` | Full CI pipeline (check + build) |

---

## Full Docker Deployment

To run **everything** in Docker (no local Python/Node needed):

```bash
cd ~/LIMP/PCL
cp .env.example .env
docker compose up --build
```

This starts 5 services:

| Service | Port | Purpose |
|---------|------|---------|
| `postgres` | 5432 | PostgreSQL 18 database |
| `redis` | 6379 | Redis 8 message broker |
| `api` | 8000 | FastAPI server (auto-runs migrations) |
| `celery-worker` | — | Processes scrape + analysis tasks |
| `celery-beat` | — | Periodic scheduler (scrape every 30 min) |

---

## Database Schema

### `articles` (hot table — last 7 days)

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID PK | Auto-generated |
| `title` | TEXT | Article headline |
| `synopsis` | TEXT | 60-word summary |
| `author` | TEXT | Writer name |
| `published_at` | TIMESTAMPTZ | Original publish time |
| `category` | VARCHAR | national, business, sports, etc. |
| `source_name` | TEXT | Original publisher |
| `source_url` | TEXT | Link to original article |
| `content_hash` | VARCHAR(64) UNIQUE | SHA-256 dedup key |
| `status` | VARCHAR(20) | raw → preprocessed → analyzed → failed |
| `bias_score` | FLOAT | 0–1 (1 = highly biased) |
| `bias_label` | VARCHAR | left / center / right / unclassified |
| `sentiment_score` | FLOAT | -1 to +1 |
| `trust_score` | FLOAT | 0–1 (1 = trustworthy) |
| `reliability_score` | FLOAT | 0–100 (final score) |
| `top_claims` | JSONB | Verified claims array |
| `flagged_tokens` | JSONB | Biased words + replacements |

### `archived_articles` — Same schema, for articles older than 7 days

### `analysis_runs` — Audit trail of each model run per article

### `sources` — Static credibility tier mapping (50+ Indian outlets)

---

## Reliability Score Formula

```
reliability = (
    (1 - bias_score)        × 0.40    # lower bias = better
  + trust_score             × 0.40    # higher trust = better
  + (1 - sensationalism)    × 0.20    # lower sensationalism = better
) × 100
```

---

## Environment Variables — Complete Guide

All variables live in `.env` at the repo root. Run `cp .env.example .env` to start — **the defaults work out of the box for local dev**. You do NOT need any API keys to run the platform.

### Quick Answer: What do I NEED?

**For local dev with `docker compose up postgres redis -d`:** Nothing. The `.env.example` has working defaults for everything. Just copy it.

**For the fullest experience (optional):** Get a ClaimBuster API key (free, 2 minutes).

---

### 🔴 REQUIRED — Infrastructure (already set in .env.example)

These are pre-filled in `.env.example` and work with `docker compose up postgres redis -d`. **You don't need to change them.**

| Variable | Default Value | What It Does |
|----------|--------------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://indiaground:indiaground@localhost:5432/indiaground` | Async connection to PostgreSQL. Used by FastAPI for all DB reads/writes. |
| `DATABASE_URL_SYNC` | `postgresql://indiaground:indiaground@localhost:5432/indiaground` | Sync connection. Used by Alembic (migrations) and Celery tasks (which run in sync context). |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | Redis connection for general caching. |
| `CELERY_BROKER_URL` | `redis://127.0.0.1:6379/0` | Redis as Celery's message broker. When you click "Scrape Now", the message goes here. |
| `CELERY_RESULT_BACKEND` | `redis://127.0.0.1:6379/0` | Where Celery stores task results (e.g., "scrape done, 45 articles"). |
| `SECRET_KEY` | `replace-with-long-random-string...` | Used for hashing/signing. Any random 50+ char string works for local dev. |

**Without these:** The app won't start. But you never need to change them for local dev — the defaults match `docker-compose.yml`.

---

### 🟡 REQUIRED BUT PRE-FILLED — App Config

| Variable | Default | What It Does | Without It |
|----------|---------|-------------|-----------|
| `APP_ENV` | `development` | Controls debug mode. Set to `production` to disable Swagger docs. | Defaults to `development`. |
| `DEBUG` | `1` | Enables `/api/docs` Swagger UI and verbose error messages. | Swagger UI and detailed errors are hidden. |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Which frontend URLs the API accepts requests from. | Frontend gets CORS errors and can't talk to backend. |
| `VITE_API_URL` | `http://localhost:8000` | Frontend env var — where the React app sends API requests. | Frontend defaults to same-origin (works with Vite proxy). |

---

### 🟢 OPTIONAL — External API Keys

**None of these are needed.** The platform works fully without them. They just enhance the fact-checking quality.

#### `CLAIMBUSTER_API_KEY`

| | |
|---|---|
| **What it does** | Sends article text to ClaimBuster's API to get per-sentence check-worthiness scores (0–1). Returns the most "claim-like" sentences. |
| **Without it** | Uses a built-in **heuristic fallback** that detects claims by looking for: percentages, large numbers (crore/lakh/million), attribution words (according to, said, reported), superlatives, and trend words. Works well enough for a demo. |
| **How to get it (free)** | 1. Go to [https://idir.uta.edu/claimbuster/](https://idir.uta.edu/claimbuster/) <br> 2. Click "Register" and create an account <br> 3. After login, your API key is shown on the dashboard <br> 4. Set `CLAIMBUSTER_API_KEY=your-key-here` in `.env` |
| **Rate limit** | 100 requests/day on free tier. More than enough for a demo. |

#### `GOOGLE_FACTCHECK_API_KEY`

| | |
|---|---|
| **What it does** | Queries the [Google Fact Check Tools API](https://toolbox.google.com/factcheck/explorer) to check if professional fact-checkers have already verified a claim. Returns existing fact-check articles with ratings. |
| **Without it** | This step is **skipped entirely**. DuckDuckGo evidence retrieval still works. The NLI verification still runs. You just don't get links to existing professional fact-checks. |
| **How to get it (free)** | 1. Go to [https://console.cloud.google.com/](https://console.cloud.google.com/) <br> 2. Create a project (or use existing) <br> 3. Go to APIs & Services → Library <br> 4. Search "Fact Check Tools" and enable it <br> 5. Go to APIs & Services → Credentials → Create Credentials → API Key <br> 6. Set `GOOGLE_FACTCHECK_API_KEY=your-key-here` in `.env` |
| **Rate limit** | 10,000 requests/day free. |

#### `SERPAPI_KEY`

| | |
|---|---|
| **What it does** | Would be used for Google Search-based evidence retrieval for claims. |
| **Without it** | Uses **DuckDuckGo search** instead (via the `duckduckgo-search` Python package). This is actually what runs by default — the code uses DuckDuckGo directly, not SerpAPI. SerpAPI is a placeholder for future enhancement. |
| **How to get it** | Go to [https://serpapi.com/](https://serpapi.com/) — 100 free searches/month. **Not recommended** — DuckDuckGo works fine. |

---

### 🔵 OPTIONAL — ML / Performance

| Variable | Default | What It Does | Without It |
|----------|---------|-------------|-----------|
| `ML_DEVICE` | `auto` | Controls which hardware runs ML models. `auto` detects best available: NVIDIA GPU (`cuda`) > Apple Silicon (`mps`) > `cpu`. | Defaults to `auto` which picks CPU if no GPU found. Works fine, just slower (~30s per article vs ~5s on GPU). |
| `SCRAPE_INTERVAL_MINUTES` | `30` | How often Celery Beat auto-triggers a scrape. | Defaults to 30 minutes. You can always scrape manually via UI or API regardless. |
| `HF_HOME` | `~/.cache/huggingface` | Where HuggingFace downloads ML models (~2.2GB total). | Models download to `~/.cache/huggingface`. Set this only if you want them elsewhere. |

---

### Summary: What Actually Runs Without Any API Keys

| Feature | With API Key | Without API Key (default) |
|---------|-------------|--------------------------|
| **Scraping** | N/A | ✅ Works (Playwright + BS4) |
| **Preprocessing** | N/A | ✅ Works (spaCy + langdetect + sentence-transformers) |
| **Bias Detection** | N/A | ✅ Works (VADER + RoBERTa + BART-MNLI + Dbias — all local models) |
| **Claim Extraction** | ClaimBuster API (better accuracy) | ✅ **Heuristic fallback** (pattern matching — good enough for demo) |
| **Evidence Retrieval** | SerpAPI (Google results) | ✅ **DuckDuckGo** (works, no key needed) |
| **Fact-Check Lookup** | Google FC API (professional fact-checks) | ⚠️ **Skipped** (no existing fact-check links, but NLI verification still runs) |
| **Claim Verification** | N/A | ✅ Works (BART-MNLI NLI — fully local) |
| **Source Credibility** | N/A | ✅ Works (built-in dict of 50+ Indian sources) |
| **Aggregator** | N/A | ✅ Works (formula runs on whatever data is available) |
| **Frontend** | N/A | ✅ Works (shows all analysis results) |

**Bottom line: `cp .env.example .env` and you're done. Everything works.**

---

## Known Notes

- **First scrape takes 2-5 minutes** — Playwright renders 10 Inshorts category pages sequentially.
- **First analysis downloads ~2.2GB of ML models** — BART-MNLI (~1.6GB), RoBERTa (~500MB), MiniLM (~90MB). Cached at `~/.cache/huggingface` after first download.
- **All API keys are optional** — the system works without any external API keys.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Executable doesn't exist` (Playwright) | `cd backend && uv run playwright install chromium` |
| `spaCy model not found` | `cd backend && uv run python -m spacy download en_core_web_sm` |
| `connection refused` on port 5432 | PostgreSQL not running — `docker compose up postgres -d` |
| `connection refused` on port 6379 | Redis not running — `docker compose up redis -d` |
| Frontend shows "Failed to load articles" | Backend not running on port 8000, or CORS issue |
| `ModuleNotFoundError` in Python | Run `cd backend && uv sync --all-groups` |
| `Cannot find module` in frontend | Run `cd frontend && pnpm install` |
| Celery worker shows no tasks | Make sure `CELERY_BROKER_URL` in `.env` points to running Redis |

---

## License

Academic / educational use — college PCL project.
