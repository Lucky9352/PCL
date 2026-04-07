# Manual Verification Guide

Step-by-step guide to verify the complete IndiaGround flow from a fresh database reset. Each step includes **what to run** and **how to verify it worked**.

---

## Prerequisites

Make sure you have installed:

- Docker (27+) and Docker Compose (v2.30+)
- Python 3.13+ with `uv` (0.11+)
- Node.js 25+ with `pnpm` (10+)
- PostgreSQL client (`psql`) — install with `sudo apt install postgresql-client`

---

## Step 0: Environment Setup

```bash
cd ~/LIMP/PCL
cp .env.example .env   # Only needed first time
```

**Verify:** `cat .env` should show all variables filled in.

---

## Step 1: Start Infrastructure

```bash
docker compose up -d postgres redis
```

**Verify:**

```bash
docker compose ps
```

Expected output:
```
NAME             STATUS           PORTS
pcl-postgres-1   Up (healthy)    0.0.0.0:5432->5432/tcp
pcl-redis-1      Up (healthy)    0.0.0.0:6379->6379/tcp
```

Both must show `(healthy)`. If not, wait 10 seconds and check again.

---

## Step 2: Reset Database (Clean Slate)

```bash
bash scripts/reset_db.sh
```

**Verify — you should see:**

```
[1/5] Dropping all tables...
  ✓ All tables dropped
[2/5] Verifying empty database...
  ✓ Database is clean (0 tables)
[3/5] Running Alembic migrations...
  Running upgrade  -> 62ffb999d45a, initial_schema
  Running upgrade 62ffb999d45a -> b3e8a1c2d4f5, story_clusters and article extensions
  ✓ Migrations applied successfully
[4/5] Verifying schema...
  ✓ articles (41 columns)
  ✓ story_clusters (12 columns)
  ✓ archived_articles (42 columns)
  ✓ analysis_runs (6 columns)
  ✓ sources (5 columns)
  ✓ alembic_version (1 columns)
  ✓ All expected tables exist
  ✓ articles table has 41 columns (extended schema confirmed)
[5/5] Flushing Redis...
  ✓ Redis flushed
  Database reset complete!
```

**Double-check with psql:**

```bash
PGPASSWORD=indiaground psql -h localhost -U indiaground -d indiaground -c "\dt"
```

Should list 6 tables: `alembic_version`, `analysis_runs`, `archived_articles`, `articles`, `sources`, `story_clusters`.

```bash
PGPASSWORD=indiaground psql -h localhost -U indiaground -d indiaground -c "SELECT count(*) FROM articles;"
```

Should return `0` — no articles yet.

---

## Step 3: Install Dependencies (first time only)

**Backend:**

```bash
cd ~/LIMP/PCL/backend
uv sync --all-groups
uv run python -m spacy download en_core_web_sm
```

**Frontend:**

```bash
cd ~/LIMP/PCL/frontend
pnpm install
```

---

## Step 4: Start Backend API Server (Terminal 1)

```bash
cd ~/LIMP/PCL/backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Verify:**

```bash
curl -s http://localhost:8000/api/v1/health | python3 -m json.tool
```

Expected:
```json
{
    "success": true,
    "data": {
        "status": "healthy",
        "service": "IndiaGround API",
        "version": "0.1.0"
    }
}
```

**Verify empty database response:**

```bash
curl -s http://localhost:8000/api/v1/articles | python3 -m json.tool
```

Expected: `"data": []`, `"total_count": 0`.

---

## Step 5: Start Celery Worker (Terminal 2)

```bash
cd ~/LIMP/PCL/backend
uv run celery -A app.core.celery_app worker -l info -c 2
```

**Verify — look for this in the output:**

```
[tasks]
  . app.tasks.analyze_task.analyze_pending_articles
  . app.tasks.cleanup_task.archive_old_articles
  . app.tasks.cluster_task.backfill_story_clusters
  . app.tasks.scrape_task.scrape_inshorts
```

And then: `celery@<hostname> ready.`

---

## Step 6: Trigger Scrape

```bash
curl -s -X POST http://localhost:8000/api/v1/scrape/trigger | python3 -m json.tool
```

**Verify response:**

```json
{
    "success": true,
    "data": {
        "message": "Multi-source scrape task dispatched",
        "task_id": "..."
    }
}
```

**Watch Terminal 2 (Celery worker) for scrape progress:**

```
🕷️ Starting multi-source scrape job
  Scraping Inshorts category: national
  ...
  Inshorts: ~91 inserted, ~9 skipped
  Google News RSS: fetched ~120 articles
  RSS feeds: ~264 inserted, ~0 skipped
  ✅ Multi-source scrape complete: ~355 inserted
```

**Then watch for analysis pipeline:**

```
🔬 Starting analysis pipeline for pending articles
  Processing 50 articles
  Preprocessing: <article title>...
  → Running bias analysis...
  → Running local hybrid fact-check analysis...
  → Aggregating scores...
  ✅ Complete: reliability=XX.X bias=X.XXX trust=X.XXX
  ...
🔬 Analysis complete: 50 processed, 0 failed
```

The first batch downloads ML models (~2.2GB) on first run. Subsequent runs are instant.

Wait until you see multiple "Analysis complete" messages with `0 failed`.

---

## Step 7: Verify Database Has Data

```bash
PGPASSWORD=indiaground psql -h localhost -U indiaground -d indiaground -c "
SELECT
    count(*) as total,
    count(*) FILTER (WHERE status = 'analyzed') as analyzed,
    count(*) FILTER (WHERE analysis_status = 'complete') as complete,
    count(*) FILTER (WHERE story_cluster_id IS NOT NULL) as clustered,
    count(DISTINCT source_type) as source_types,
    round(avg(reliability_score)::numeric, 2) as avg_reliability
FROM articles;
"
```

**Expected (approximate):**

| total | analyzed | complete | clustered | source_types | avg_reliability |
|-------|----------|----------|-----------|--------------|-----------------|
| ~350+ | ~348+ | ~348+ | ~348+ | 2 | ~40-50 |

**Key checks:**
- `total > 300` — multi-source scraping is working
- `analyzed ≈ total - 7` (some may be skipped as non-English or duplicate)
- `complete ≈ analyzed` — all analyzed articles have full scores
- `clustered ≈ complete` — all articles are assigned to story clusters
- `source_types = 2` (inshorts + rss; 3 if NewsAPI key is set)

**Check source distribution:**

```bash
PGPASSWORD=indiaground psql -h localhost -U indiaground -d indiaground -c "
SELECT source_type, count(*) FROM articles GROUP BY source_type;
"
```

Expected: `inshorts ~91`, `rss ~264`.

**Check story clusters:**

```bash
PGPASSWORD=indiaground psql -h localhost -U indiaground -d indiaground -c "
SELECT count(*) as total_clusters,
       count(*) FILTER (WHERE article_count >= 2) as multi_article,
       count(*) FILTER (WHERE jsonb_array_length(unique_sources) >= 2) as multi_source
FROM story_clusters;
"
```

Expected: `total_clusters ~300+`, `multi_article 20+`, `multi_source 15+`.

---

## Step 8: Verify All API Endpoints

Run each and check the response:

```bash
# 1. Health
curl -s http://localhost:8000/api/v1/health | python3 -m json.tool
# ✓ success: true

# 2. Articles list (with data)
curl -s "http://localhost:8000/api/v1/articles?page_size=3" | python3 -m json.tool
# ✓ data has 3 articles with reliability_score, bias_label, trust_score

# 3. Single article detail
ARTICLE_ID=$(curl -s "http://localhost:8000/api/v1/articles?page_size=1" | python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0]['id'])")
curl -s "http://localhost:8000/api/v1/articles/$ARTICLE_ID" | python3 -m json.tool
# ✓ Full detail with framing, political_lean, bias_score_components

# 4. Article analysis
curl -s "http://localhost:8000/api/v1/articles/$ARTICLE_ID/analysis" | python3 -m json.tool
# ✓ analysis_status: "complete", all score components present

# 5. Categories
curl -s http://localhost:8000/api/v1/categories | python3 -m json.tool
# ✓ Multiple categories with counts (national, business, sports, etc.)

# 6. Stats / Dashboard
curl -s http://localhost:8000/api/v1/stats | python3 -m json.tool
# ✓ total_articles > 0, avg scores present, trust_distribution populated

# 7. Stories (multi-source)
curl -s "http://localhost:8000/api/v1/stories?min_sources=2" | python3 -m json.tool
# ✓ Stories with unique_sources arrays containing 2+ outlets

# 8. Story detail
STORY_ID=$(curl -s "http://localhost:8000/api/v1/stories?min_sources=2&page_size=1" | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; print(d[0]['id'] if d else 'none')")
curl -s "http://localhost:8000/api/v1/stories/$STORY_ID" | python3 -m json.tool
# ✓ cluster info + array of articles from different sources

# 9. Methodology
curl -s http://localhost:8000/api/v1/methodology | python3 -m json.tool
# ✓ Scoring formulas, pipeline stages, datasets

# 10. Trigger scrape (verify dispatch)
curl -s -X POST http://localhost:8000/api/v1/scrape/trigger | python3 -m json.tool
# ✓ success: true (with task_id)
```

---

## Step 9: Verify Frontend (Terminal 3)

```bash
cd ~/LIMP/PCL/frontend
pnpm dev
```

Open [http://localhost:5173](http://localhost:5173).

### Checklist

| Page | URL | What to Check |
|------|-----|---------------|
| **Home** | `/` | Articles grid with images, reliability bars, source badges. Search works. Category filters work. "Scrape Now" button triggers scrape. |
| **Article Detail** | Click any article | Full analysis visible: bias score, trust score, claims with verdicts, flagged tokens highlighted in synopsis |
| **Stories** | `/stories` | Story cards with multiple sources, bias spectrum bar, "View Story" links work |
| **Story Detail** | Click any story | Cluster overview + per-article comparison from different outlets |
| **Categories** | `/categories` | Category grid with counts, clicking shows articles |
| **Dashboard** | `/dashboard` | Stats cards, reliability bar chart, bias pie chart, trust histogram, top sources table |
| **How It Works** | `/methodology` | Pipeline stages, scoring formulas, source credibility tiers, evaluation datasets |

---

## Step 10: Run Automated Tests

```bash
# Backend tests (27 tests)
cd ~/LIMP/PCL/backend
uv run pytest -v
# ✓ All 27 passed

# Evaluation sanity checks
uv run python -c "
from evaluation.evaluate_scoring import run_scoring_sanity
from evaluation.evaluate_tokens import run_synthetic_token_check
r1 = run_scoring_sanity()
r2 = run_synthetic_token_check()
assert r1['status'] == 'pass', f'Scoring failed: {r1}'
assert r2['status'] == 'pass', f'Tokens failed: {r2}'
print('✅ All evaluation checks passed')
"

# Ruff linting
uv run ruff check app/ evaluation/ tests/ --select E,F,I --ignore E501
# ✓ All checks passed

# Frontend TypeScript + build
cd ~/LIMP/PCL/frontend
npx tsc --noEmit && pnpm build
# ✓ Built successfully
```

Or run the all-in-one verification script:

```bash
cd ~/LIMP/PCL
bash scripts/verify_stack.sh
```

---

## Step 11: Verify Analysis Quality (Spot Check)

Pick an analyzed article and verify the scores make sense:

```bash
PGPASSWORD=indiaground psql -h localhost -U indiaground -d indiaground -c "
SELECT title, source_name, source_type,
       bias_score, bias_label, trust_score,
       reliability_score, analysis_status,
       jsonb_pretty(political_lean) as political_lean,
       jsonb_pretty(bias_score_components) as bias_components,
       jsonb_pretty(trust_score_components) as trust_components,
       jsonb_pretty(reliability_components) as reliability_components
FROM articles
WHERE analysis_status = 'complete'
ORDER BY reliability_score DESC
LIMIT 1;
"
```

**Check that:**
- `bias_score` is between 0 and 1
- `trust_score` is between 0 and 1
- `reliability_score` is between 0 and 100
- `political_lean` has `score`, `label`, `source_contribution`, `framing_contribution`
- `bias_score_components` includes `sentiment_extremity`, `bias_type_severity`, `token_bias_density`, `framing_deviation` (and optional `weights`)
- `trust_score_components` has `evidence_trust`, `source_trust`, `coverage_score`
- `reliability_components` has `bias_inversion`, `trust`, `sensationalism_penalty`, `framing_neutrality`

---

## Step 12: Evaluation suites (offline benchmarks)

These scripts do **not** require a running API. They validate formulas and (optionally) compare the ML pipeline to public benchmarks.

```bash
cd ~/LIMP/PCL/backend

# Always run in CI (no downloaded datasets)
uv run python -m evaluation.evaluate_scoring
uv run python -m evaluation.evaluate_tokens
uv run pytest tests/test_evaluation_smoke.py -q

# Full orchestrator: scoring + tokens always; BABE/LIAR/CLEF only if files exist under evaluation/datasets/
uv run python -m evaluation.run_all --data-dir evaluation/datasets --sample 200
```

**Expected without datasets:** `evaluate_scoring` prints `"all_passed": true`; `run_all` prints `SKIP` lines for missing TSV/CSV but exits 0.

**Documentation:** [EVALUATION.md](./EVALUATION.md), [DATASETS.md](./DATASETS.md), [PARAMETER_PROVENANCE.md](./PARAMETER_PROVENANCE.md).

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `reset_db.sh` says "psql: command not found" | `sudo apt install postgresql-client` |
| Docker "permission denied" | `sudo usermod -aG docker $USER` and re-login, or prefix with `sudo` |
| Celery worker hangs on first article | ML models are downloading (~2.2GB first time). Wait 3-5 minutes. |
| `stories` endpoint returns empty | Make sure analysis has completed. Run: `curl -X POST http://localhost:8000/api/v1/scrape/cluster-backfill` |
| Frontend shows blank | Check that API is running on port 8000 and Vite proxy is configured |
| "Module not found" errors | `cd backend && uv sync --all-groups` or `cd frontend && pnpm install` |
| Tests fail with import errors | Make sure you're running from the `backend/` directory: `cd backend && uv run pytest` |

---

## Summary: Complete Flow in One Script

After the initial setup (dependencies installed, `.env` copied), the complete verification from fresh DB is:

```bash
# Start infra
docker compose up -d postgres redis

# Reset DB
bash scripts/reset_db.sh

# Terminal 1: API
cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Worker
cd backend && uv run celery -A app.core.celery_app worker -l info -c 2

# Terminal 3: Frontend
cd frontend && pnpm dev

# Trigger scrape
curl -X POST http://localhost:8000/api/v1/scrape/trigger

# Wait for analysis (~5-10 min first time, ~2 min after models cached)
# Then verify at http://localhost:5173
```
