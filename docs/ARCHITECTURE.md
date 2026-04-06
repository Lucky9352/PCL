# IndiaGround — Architecture & Design

## System Overview

IndiaGround is an automated news bias and fact-check platform for Indian media.
It scrapes articles from Inshorts, runs them through a multi-model NLP pipeline,
and presents reliability scores via a React dashboard.

## Architecture Diagram

```
┌─────────────────┐
│   Inshorts       │
│   (10 categories)│
└────────┬────────┘
         │ httpx API client
         ▼
┌─────────────────┐      ┌──────────────┐
│   Celery Beat    │─────▶│ Redis 8      │
│   (every 30 min) │      │ (Broker)     │
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐
│  Scrape Task     │
│  (dedup + store) │
└────────┬────────┘
         │ triggers
         ▼
┌─────────────────────────────────────────────┐
│           Analysis Pipeline                  │
│                                              │
│  ┌──────────────┐                            │
│  │ Preprocessor  │  Clean → spaCy NER →      │
│  │               │  LangDetect → Dedup      │
│  └──────┬───────┘                            │
│         ▼                                    │
│  ┌──────┴──────────────────┐                 │
│  │                         │                 │
│  ▼                         ▼                 │
│  ┌──────────┐    ┌───────────────┐           │
│  │ unBIAS   │    │ ClaimBuster   │           │
│  │ Module   │    │ Module        │           │
│  │          │    │               │           │
│  │ • VADER  │    │ • API / Heur. │           │
│  │ • RoBERTa│    │ • DuckDuckGo  │           │
│  │ • BART   │    │ • Google FC   │           │
│  │ • Dbias  │    │ • BART NLI    │           │
│  └──────┬───┘    └───────┬──────┘           │
│         │                │                   │
│         ▼                ▼                   │
│  ┌──────────────────────────┐                │
│  │     Aggregator           │                │
│  │ reliability = (1-bias)*40│                │
│  │   + trust*40             │                │
│  │   + (1-sensationalism)*20│                │
│  └──────────┬──────────────┘                │
│             │                                │
└─────────────┼────────────────────────────────┘
              │
              ▼
┌─────────────────┐
│  PostgreSQL 18   │
│  (articles,      │
│   analysis_runs, │
│   sources)       │
└────────┬────────┘
         │ FastAPI async
         ▼
┌─────────────────┐
│  React 19 + Vite │
│  Dashboard       │
│                  │
│  • Feed          │
│  • Article Detail│
│  • Categories    │
│  • Dashboard     │
└─────────────────┘
```

## Project Structure

```
PCL/
├── backend/
│   ├── app/
│   │   ├── api/v1/         # FastAPI routers (7 endpoints)
│   │   ├── core/           # Config, Celery, logging
│   │   ├── db/             # SQLAlchemy models + session
│   │   ├── schemas/        # Pydantic request/response
│   │   ├── services/       # Scraper, preprocessor, unBIAS, ClaimBuster, aggregator
│   │   ├── tasks/          # Celery task definitions
│   │   └── utils/          # Hashing, source credibility
│   ├── alembic/            # DB migrations
│   ├── tests/              # Unit tests
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/            # Axios client + TypeScript types
│   │   ├── components/     # Navbar, ArticleCard, ReliabilityMeter, etc.
│   │   ├── lib/            # Utility functions
│   │   └── pages/          # Home, ArticleDetail, Categories, Dashboard
│   ├── vite.config.ts
│   └── package.json
├── docker-compose.yml      # Postgres, Redis, API, Celery worker/beat
├── .env.example
├── package.json            # Monorepo scripts (mirroring limp)
└── pnpm-workspace.yaml
```

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.13, FastAPI, SQLAlchemy (async), Alembic |
| Tasks | Celery, Redis 8 |
| Database | PostgreSQL 18 |
| Frontend | React 19, Vite 8, TailwindCSS v4, Recharts |
| NLP/ML | spaCy, VADER, Transformers (RoBERTa, BART-MNLI), Sentence-Transformers, Dbias |
| Scraping | httpx (JSON API) |

## Database Schema

### articles (hot table — last 7 days)
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | Default uuid4 |
| title | TEXT | |
| synopsis | TEXT | |
| content_hash | VARCHAR(64) UNIQUE | SHA-256(title + published_at) |
| status | VARCHAR(20) | raw → preprocessed → analyzed → failed |
| bias_score | FLOAT | 0–1 |
| bias_label | VARCHAR | left / center / right / unclassified |
| trust_score | FLOAT | 0–1 |
| reliability_score | FLOAT | 0–100 |
| top_claims | JSONB | Array of verified claims |
| flagged_tokens | JSONB | Array of biased word suggestions |

### archived_articles (cold storage — older than 7 days)
Same schema as articles + `archived_at` timestamp.

### analysis_runs (audit trail)
Records raw output from each model run per article.

### sources (credibility tiers)
Static mapping of Indian news sources to credibility tiers.

## Reliability Score Formula

```
reliability = (
    (1 - bias_score)        × 0.40    # lower bias = better
  + trust_score             × 0.40    # higher trust = better
  + (1 - sensationalism)    × 0.20    # lower sensationalism = better
) × 100
```

## API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/articles` | Cursor-based paginated feed |
| GET | `/api/v1/articles/{id}` | Article detail |
| GET | `/api/v1/articles/{id}/analysis` | Full analysis breakdown |
| GET | `/api/v1/categories` | Categories with counts |
| GET | `/api/v1/stats` | Dashboard aggregates |
| POST | `/api/v1/scrape/trigger` | Manual scrape dispatch |
