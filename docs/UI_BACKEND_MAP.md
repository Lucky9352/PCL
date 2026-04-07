# UI ↔ Backend Map

How every frontend page connects to the backend, which API endpoints it hits, what data fields are displayed, and how each score is calculated.

---

## Navigation Bar (`Navbar.tsx`)

Renders on every page. Five links:

| Label | Route | Icon |
|-------|-------|------|
| Feed | `/` | Newspaper |
| Stories | `/stories` | Layers |
| Categories | `/categories` | Grid3X3 |
| Dashboard | `/dashboard` | BarChart3 |
| How It Works | `/methodology` | BookOpen |

Active link is highlighted based on current `pathname`.

---

## 1. Home Page — `/` (`Home.tsx`)

### API Calls

| Trigger | Endpoint | Method | Query Params |
|---------|----------|--------|--------------|
| Page load + scroll | `GET /api/v1/articles` | GET | `page_size`, `cursor`, `category`, `search` |
| "Scrape Now" button | `POST /api/v1/scrape/trigger` | POST | — |

### What the User Sees

| UI Element | Backend Field | Source |
|------------|---------------|--------|
| Article headline | `ArticleCard.title` | `articles.title` column |
| Summary text | `ArticleCard.synopsis` | `articles.synopsis` |
| Article image | `ArticleCard.image_url` | `articles.image_url` |
| Category badge (e.g. "national") | `ArticleCard.category` | `articles.category` |
| Source name (e.g. "The Hindu") | `ArticleCard.source_name` | `articles.source_name` |
| Source type badge (e.g. "rss") | `ArticleCard.source_type` | `articles.source_type` — values: `inshorts`, `rss`, `newsapi` |
| Reliability bar (0–100) | `ArticleCard.reliability_score` | `articles.reliability_score` — computed by `aggregator.compute_reliability_score()` |
| Bias label chip (left/center/right) | `ArticleCard.bias_label` | `articles.bias_label` — thresholded from `political_lean.score`: `<-0.25` → left, `>+0.25` → right, else center |
| Trust score chip | `ArticleCard.trust_score` | `articles.trust_score` — from `claimbuster.analyze_claims()` |
| "Showing X of Y" | `PaginationMeta.total_count` | `SELECT count(*) FROM articles WHERE` (same filters as list query) |
| Time ago (e.g. "2h ago") | `ArticleCard.scraped_at` | `articles.scraped_at` |

### How the Reliability Bar Color Works

| Score Range | Color | Label |
|-------------|-------|-------|
| 80–100 | Green | Highly reliable |
| 60–79 | Blue | Moderately reliable |
| 40–59 | Yellow | Mixed |
| 20–39 | Orange | Low reliability |
| 0–19 | Red | Very low |

Implemented in `ReliabilityMeter.tsx` → `scoreColor()` from `lib/utils.ts`.

### Interactions

- **Search bar**: Filters articles by `title ILIKE` or `synopsis ILIKE`
- **Category chips**: Filters by exact `category` match
- **"Scrape Now"**: Dispatches `scrape_inshorts` Celery task → scrapes Inshorts + RSS + NewsAPI → triggers `analyze_pending_articles`
- **"Show More"**: Loads next page using cursor-based pagination (`next_cursor` = last article's UUID)

---

## 2. Article Detail — `/article/:id` (`ArticleDetail.tsx`)

### API Call

| Endpoint | Method |
|----------|--------|
| `GET /api/v1/articles/:id` | GET |

Returns full `ArticleDetail` schema.

### What the User Sees

#### Header Section

| UI Element | Backend Field | How Calculated |
|------------|---------------|----------------|
| Title | `title` | Direct from scraper |
| Synopsis | `synopsis` | Inshorts: 60-word summary. RSS: `trafilatura` extraction or feed summary |
| Image | `image_url` | From source HTML or RSS `<enclosure>` |
| Original Source link | `source_url` | Direct URL to original article |
| Category badge | `category` | From Inshorts category or RSS topic mapping |
| Reliability meter | `reliability_score` | **Formula**: `R = [(1-B)×0.35 + T×0.35 + (1-S)×0.15 + (1-F)×0.15] × 100` |
| "View Story Comparison" link | `story_cluster_id` | If article belongs to a `StoryCluster`, links to `/story/:cluster_id` |

#### Bias Analysis Card (shown when `analysis_status === "complete"`)

| UI Element | Backend Field | How Calculated |
|------------|---------------|----------------|
| Bias Score (0.000–1.000) | `bias_score` | `B = sentiment×0.15 + type_severity×0.35 + token_density×0.20 + framing×0.30` |
| Bias Label | `bias_label` | From `political_lean.label`: maps score `>0.25` → right, `<-0.25` → left |
| Sentiment Label | `sentiment_label` | Combined VADER(headline)×0.4 + RoBERTa(body)×0.6, then thresholded |
| Sentiment Score | `sentiment_score` | Float in [-1, 1] from combined model |
| Bias Types | `bias_types` | BART-MNLI zero-shot over labels: political bias, sensationalism, loaded language, framing bias, omission bias |

#### Trust & Claims Card

| UI Element | Backend Field | How Calculated |
|------------|---------------|----------------|
| Trust Score (0.000–1.000) | `trust_score` | `T = evidence×0.50 + source×0.30 + coverage×0.20` |
| Source Credibility | `source_credibility_tier` | Lookup from `source_credibility.py` dictionary (136 outlets) |
| Claims list | `top_claims[]` | Each claim has: |
| → Claim text | `top_claims[].text` | Two-pass BART-MNLI zero-shot (`get_checkworthy_claims`) |
| → Check-worthiness | `top_claims[].checkworthiness` | Combined score from pass 1 (0.45 thresh) + pass 2 (0.35×S1+0.65×S2, 0.50 thresh) |
| → Verdict | `top_claims[].verdict` | BART-MNLI NLI: SUPPORTS / REFUTES / NOT_ENOUGH_INFO |
| → Confidence | `top_claims[].confidence` | NLI model softmax probability for the winning label |
| → Evidence URLs | `top_claims[].evidence_urls` | DuckDuckGo "fact check" search + Google Fact Check Tools API |

#### Flagged Tokens Section

| UI Element | Backend Field | How Calculated |
|------------|---------------|----------------|
| Flagged word | `flagged_tokens[].word` | Dictionary match from 100+ India-specific biased terms |
| Suggestion | `flagged_tokens[].suggestion` | Neutral alternative from the dictionary |

Words are highlighted in the synopsis text using string matching.

---

## 3. Stories Page — `/stories` (`Stories.tsx`)

### API Call

| Endpoint | Method | Query Params |
|----------|--------|--------------|
| `GET /api/v1/stories` | GET | `page_size=30`, `min_sources=2` |

### What the User Sees

Each story card shows a cluster of articles about the same event from different outlets.

| UI Element | Backend Field | How Calculated |
|------------|---------------|----------------|
| Story title | `representative_title` | Title of the first article that seeded the cluster |
| Source pills | `unique_sources[]` | Distinct `source_name` values from clustered articles |
| Article count | `article_count` | Count of articles in this cluster |
| Bias Spectrum bar | `bias_spectrum` | Dict `{left: N, center: N, right: N}` — how many articles lean each way |
| Avg Reliability | `avg_reliability_score` | Mean of `reliability_score` across all clustered articles |
| Avg Trust | `avg_trust_score` | Mean of `trust_score` across all clustered articles |

### Bias Spectrum Visualization

The horizontal bar in each story card shows proportional segments:

| Segment | Color | Meaning |
|---------|-------|---------|
| Left | Blue | Articles classified as left-leaning |
| Center | Gray | Centrist articles |
| Right | Red/Orange | Right-leaning articles |

Width of each segment = `count / total_articles × 100%`.

### How Story Clustering Works (backend)

1. When an article is analyzed, `story_cluster_sync.assign_article_to_cluster()` runs
2. It computes the article's embedding using `all-MiniLM-L6-v2` (384-dim sentence embedding)
3. Compares against all existing cluster centroids using cosine similarity
4. If `similarity > 0.75` → joins that cluster; centroid is updated as running mean
5. If no match → creates a new `StoryCluster`
6. Cluster-level metrics (source diversity, bias spectrum, avg scores) are recomputed

---

## 4. Story Detail — `/story/:id` (`StoryDetail.tsx`)

### API Call

| Endpoint | Method |
|----------|--------|
| `GET /api/v1/stories/:cluster_id` | GET |

### What the User Sees

#### Cluster Overview

| UI Element | Backend Field |
|------------|---------------|
| Story title | `cluster.representative_title` |
| Total articles | `cluster.article_count` |
| Sources covered | `cluster.unique_sources[]` |
| Avg Reliability | `cluster.avg_reliability_score` |

#### Per-Article Comparison

For each article in the cluster:

| UI Element | Backend Field |
|------------|---------------|
| Article title | `articles[].title` |
| Synopsis | `articles[].synopsis` |
| Source name + type | `articles[].source_name`, `articles[].source_type` |
| Published time | `articles[].published_at` |
| Reliability score | `articles[].reliability_score` |
| Bias label | `articles[].bias_label` |
| Trust score | `articles[].trust_score` |
| Cluster similarity | `articles[].cluster_similarity` — cosine similarity to cluster centroid |
| Link to full detail | `/article/:id` |
| Original source link | `articles[].source_url` |

---

## 5. Categories Page — `/categories` (`Categories.tsx`)

### API Calls

| Trigger | Endpoint | Query Params |
|---------|----------|--------------|
| Page load | `GET /api/v1/categories` | — |
| Category click | `GET /api/v1/articles` | `page_size=20`, `category=<selected>` |

### What the User Sees

| UI Element | Backend Field |
|------------|---------------|
| Category name | `name` |
| Article count per category | `count` |
| Articles grid (on click) | Same as Home page `ArticleCard` |

---

## 6. Dashboard — `/dashboard` (`Dashboard.tsx`)

### API Call

| Endpoint | Method |
|----------|--------|
| `GET /api/v1/stats` | GET |

### What the User Sees

#### Summary Cards (top row)

| Card | Backend Field | Description |
|------|---------------|-------------|
| Total Articles | `total_articles` | `SELECT count(*) FROM articles` |
| Analyzed | `analyzed_articles` | `WHERE analysis_status = 'complete'` |
| Avg Bias Score | `avg_bias_score` | `AVG(bias_score)` of analyzed articles |
| Avg Trust Score | `avg_trust_score` | `AVG(trust_score)` of analyzed articles |

#### Reliability by Category (bar chart)

| Axis | Backend Field |
|------|---------------|
| X-axis: Category names | `articles_by_category[].category` |
| Y-axis: Avg reliability | `articles_by_category[].avg_reliability_score` |

Data: One bar per category showing average reliability.

#### Bias Distribution (pie chart)

| Slice | Backend Field |
|-------|---------------|
| Left | `bias_distribution.left` |
| Center | `bias_distribution.center` |
| Right | `bias_distribution.right` |

Data: Count of articles per bias label.

#### Trust Distribution (histogram)

| Bucket | Backend Field |
|--------|---------------|
| 0.0–0.2 | `trust_distribution["0.0-0.2"]` |
| 0.2–0.4 | `trust_distribution["0.2-0.4"]` |
| 0.4–0.6 | `trust_distribution["0.4-0.6"]` |
| 0.6–0.8 | `trust_distribution["0.6-0.8"]` |
| 0.8–1.0 | `trust_distribution["0.8-1.0"]` |

Buckets use half-open intervals `[lo, hi)` except the last `[0.8, 1.0]`.

#### Top Sources Table

| Column | Backend Field |
|--------|---------------|
| Source | `top_sources[].source_name` |
| Articles | `top_sources[].count` |
| Avg Reliability | `top_sources[].avg_reliability_score` |

---

## 7. Methodology Page — `/methodology` (`Methodology.tsx`)

### API Call

| Endpoint | Method |
|----------|--------|
| `GET /api/v1/methodology` | GET |

### What the User Sees

This page explains the scoring system to users. Data comes from `scoring.SCORING_METHODOLOGY` on the backend.

| Section | Source |
|---------|--------|
| Pipeline overview | `pipeline.overview` |
| Pipeline stages (5 stages) | `pipeline.stages[]` — name, description, models used |
| Reliability formula | Hardcoded in frontend matching `methodology.reliability_score.formula` |
| Bias score formula | Hardcoded matching `methodology.bias_score` |
| Trust score formula | Hardcoded matching `methodology.trust_score` |
| Source credibility tiers | `pipeline.source_credibility.tier_mapping` |
| Evaluation datasets | `datasets_used_for_evaluation[]` — name, size, task, citation |
| Political lean note | `methodology.political_lean.note` |

---

## Score Calculation Summary (Quick Reference)

### Bias Score (B) ∈ [0, 1]

```
B = sentiment_extremity × 0.15
  + bias_type_severity  × 0.35
  + token_bias_density  × 0.20
  + framing_deviation   × 0.30
```

- `sentiment_extremity` = |VADER(headline) × 0.40 + RoBERTa(body) × 0.60|
- `bias_type_severity` = (detected_types / 5 + avg_confidence) / 2
- `token_bias_density` = min(flagged_tokens / word_count × 10, 1.0)
- `framing_deviation` = 1 − P("neutral factual reporting") from BART-MNLI

### Trust Score (T) ∈ [0, 1]

```
T = evidence_trust × 0.50
  + source_trust   × 0.30
  + coverage_score × 0.20
```

- `evidence_trust` = mean NLI score per claim
- `source_trust` = {high: 0.9, medium: 0.6, low: 0.3, unknown: 0.5}
- `coverage_score` = verified_claims / total_claims

### Reliability Score (R) ∈ [0, 100]

```
R = [(1-B) × 0.35 + T × 0.35 + (1-S) × 0.15 + (1-F) × 0.15] × 100
```

- `S` = sensationalism (0.70 if detected, 0.50 for loaded language, 0 otherwise)
- `F` = framing_deviation

### Political Lean (L) ∈ [-1, 1]

```
L = source_bias_numeric × 0.60 + framing_lean × 0.40
```

- `L > +0.25` → "right", `L < -0.25` → "left", else "center"

---

## File Reference

| Frontend File | Backend Endpoint | Backend Service |
|---------------|-----------------|-----------------|
| `Home.tsx` | `/articles`, `/scrape/trigger` | `scrape_task.py`, query on `articles` table |
| `ArticleDetail.tsx` | `/articles/:id` | Direct DB fetch via `ArticleDetail` schema |
| `Stories.tsx` | `/stories` | `stories.py` → `story_clusters` table |
| `StoryDetail.tsx` | `/stories/:id` | `stories.py` → join `story_clusters` + `articles` |
| `Categories.tsx` | `/categories`, `/articles` | `categories.py` → `GROUP BY category` |
| `Dashboard.tsx` | `/stats` | `stats.py` → aggregate queries on `articles` |
| `Methodology.tsx` | `/methodology` | `methodology.py` → `scoring.SCORING_METHODOLOGY` |
| `ArticleCard.tsx` | (no direct call) | Receives `ArticleCard` props from parent pages |
| `ReliabilityMeter.tsx` | (no direct call) | Pure display component for score bar |
