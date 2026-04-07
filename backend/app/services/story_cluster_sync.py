"""Persist story clusters to PostgreSQL after each analyzed article.

Compares the article embedding to recent cluster centroids (cosine ≥ threshold).
On match: update running-mean centroid and aggregate metrics.
Otherwise: create a new StoryCluster row.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import numpy as np
from sqlalchemy import func, select

from app.core.logging import logger
from app.services.preprocessor import compute_embedding
from app.services.scoring import compute_source_diversity_score

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.db.models import Article, StoryCluster

CLUSTER_THRESHOLD = 0.75
MAX_CLUSTERS_TO_SCAN = 400


def _embedding_to_numpy(embedding) -> np.ndarray | None:
    if embedding is None:
        return None
    try:
        if hasattr(embedding, "detach"):
            return np.asarray(embedding.detach().cpu().numpy(), dtype=np.float64).flatten()
        return np.asarray(embedding, dtype=np.float64).flatten()
    except Exception as e:
        logger.warning(f"Could not convert embedding: {e}")
        return None


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _refresh_cluster_aggregates(session: Session, cluster: StoryCluster) -> None:
    from app.db.models import Article

    arts = (
        session.execute(select(Article).where(Article.story_cluster_id == cluster.id))
        .scalars()
        .all()
    )
    if not arts:
        cluster.article_count = 0
        cluster.unique_sources = []
        cluster.bias_spectrum = {}
        cluster.source_diversity = None
        cluster.avg_reliability_score = None
        cluster.avg_trust_score = None
        return

    sources: set[str] = set()
    bias_spectrum: dict[str, int] = {}
    rels: list[float] = []
    trusts: list[float] = []

    for a in arts:
        if a.source_name:
            sources.add(a.source_name.strip())
        if a.bias_label:
            bias_spectrum[a.bias_label] = bias_spectrum.get(a.bias_label, 0) + 1
        if a.reliability_score is not None:
            rels.append(float(a.reliability_score))
        if a.trust_score is not None:
            trusts.append(float(a.trust_score))

    cluster.article_count = len(arts)
    cluster.unique_sources = sorted(sources)
    cluster.bias_spectrum = bias_spectrum
    cluster.source_diversity = compute_source_diversity_score(len(sources))
    cluster.avg_reliability_score = round(sum(rels) / len(rels), 1) if rels else None
    cluster.avg_trust_score = round(sum(trusts) / len(trusts), 3) if trusts else None

    arts_sorted = sorted(arts, key=lambda x: x.scraped_at)
    cluster.representative_title = arts_sorted[0].title[:500]


def assign_article_to_cluster(session: Session, article: Article) -> None:
    """Assign analyzed article to best matching StoryCluster or create one.

    No-op if embedding model unavailable or article not suitable.
    """
    from app.db.models import Article as ArticleModel
    from app.db.models import StoryCluster

    if article.status != "analyzed" or article.is_duplicate:
        return

    emb_vec = _embedding_to_numpy(compute_embedding(f"{article.title}. {article.synopsis}"))
    if emb_vec is None:
        return

    clusters = (
        session.execute(
            select(StoryCluster)
            .where(StoryCluster.centroid_embedding.isnot(None))
            .order_by(StoryCluster.updated_at.desc())
            .limit(MAX_CLUSTERS_TO_SCAN)
        )
        .scalars()
        .all()
    )

    best: StoryCluster | None = None
    best_sim = 0.0
    for c in clusters:
        raw = c.centroid_embedding
        if not raw:
            continue
        centroid = np.asarray(raw, dtype=np.float64).flatten()
        if centroid.shape != emb_vec.shape:
            continue
        sim = _cosine(emb_vec, centroid)
        if sim > best_sim:
            best_sim = sim
            best = c

    if best is not None and best_sim >= CLUSTER_THRESHOLD:
        n_existing = session.scalar(
            select(func.count())
            .select_from(ArticleModel)
            .where(ArticleModel.story_cluster_id == best.id)
        )
        n = int(n_existing or 0)
        old = np.asarray(best.centroid_embedding, dtype=np.float64).flatten()
        new_centroid = (old * n + emb_vec) / (n + 1)
        best.centroid_embedding = new_centroid.tolist()
        article.story_cluster_id = best.id
        article.cluster_similarity = round(best_sim, 4)
        _refresh_cluster_aggregates(session, best)
        logger.info(f"Story cluster: assigned article to cluster {best.id} (sim={best_sim:.3f})")
        return

    new_id = uuid.uuid4()
    cluster = StoryCluster(
        id=new_id,
        representative_title=article.title[:500],
        category=article.category,
        article_count=1,
        centroid_embedding=emb_vec.tolist(),
        source_diversity=compute_source_diversity_score(1 if article.source_name else 0),
        bias_spectrum={article.bias_label: 1} if article.bias_label else {},
        avg_reliability_score=round(float(article.reliability_score), 1)
        if article.reliability_score is not None
        else None,
        avg_trust_score=round(float(article.trust_score), 3)
        if article.trust_score is not None
        else None,
        unique_sources=[article.source_name] if article.source_name else [],
    )
    session.add(cluster)
    article.story_cluster_id = new_id
    article.cluster_similarity = 1.0
    logger.info(f"Story cluster: created new cluster {new_id}")
