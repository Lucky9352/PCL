"""story_clusters and article extensions

Revision ID: b3e8a1c2d4f5
Revises: 62ffb999d45a
Create Date: 2026-04-07

Adds multi-source fields, extended analysis JSONB columns, story clustering,
and matching archived_articles columns for archival consistency.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "b3e8a1c2d4f5"
down_revision: str | None = "62ffb999d45a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "story_clusters",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("representative_title", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("article_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("source_diversity", sa.Float(), nullable=True),
        sa.Column("bias_spectrum", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("avg_reliability_score", sa.Float(), nullable=True),
        sa.Column("avg_trust_score", sa.Float(), nullable=True),
        sa.Column("unique_sources", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "centroid_embedding",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_story_clusters_category", "story_clusters", ["category"], unique=False)
    op.create_index("ix_story_clusters_created_at", "story_clusters", ["created_at"], unique=False)

    op.add_column(
        "articles",
        sa.Column("source_type", sa.String(length=20), server_default="inshorts", nullable=False),
    )
    op.add_column(
        "articles",
        sa.Column("framing", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "articles",
        sa.Column("political_lean", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "articles",
        sa.Column("bias_score_components", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "articles",
        sa.Column("trust_score_components", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "articles",
        sa.Column("reliability_components", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column("articles", sa.Column("model_confidence", sa.Float(), nullable=True))
    op.add_column("articles", sa.Column("story_cluster_id", sa.UUID(), nullable=True))
    op.add_column("articles", sa.Column("cluster_similarity", sa.Float(), nullable=True))

    op.create_foreign_key(
        "fk_articles_story_cluster_id",
        "articles",
        "story_clusters",
        ["story_cluster_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_articles_source_type", "articles", ["source_type"], unique=False)
    op.create_index("ix_articles_story_cluster_id", "articles", ["story_cluster_id"], unique=False)

    # archived_articles — keep in sync with articles for cleanup_task
    op.add_column(
        "archived_articles",
        sa.Column("source_type", sa.String(length=20), server_default="inshorts", nullable=False),
    )
    op.add_column(
        "archived_articles",
        sa.Column("framing", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "archived_articles",
        sa.Column("political_lean", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "archived_articles",
        sa.Column("bias_score_components", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "archived_articles",
        sa.Column("trust_score_components", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "archived_articles",
        sa.Column("reliability_components", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column("archived_articles", sa.Column("model_confidence", sa.Float(), nullable=True))
    op.add_column("archived_articles", sa.Column("story_cluster_id", sa.UUID(), nullable=True))
    op.add_column("archived_articles", sa.Column("cluster_similarity", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("archived_articles", "cluster_similarity")
    op.drop_column("archived_articles", "story_cluster_id")
    op.drop_column("archived_articles", "model_confidence")
    op.drop_column("archived_articles", "reliability_components")
    op.drop_column("archived_articles", "trust_score_components")
    op.drop_column("archived_articles", "bias_score_components")
    op.drop_column("archived_articles", "political_lean")
    op.drop_column("archived_articles", "framing")
    op.drop_column("archived_articles", "source_type")

    op.drop_index("ix_articles_story_cluster_id", table_name="articles")
    op.drop_index("ix_articles_source_type", table_name="articles")
    op.drop_constraint("fk_articles_story_cluster_id", "articles", type_="foreignkey")
    op.drop_column("articles", "cluster_similarity")
    op.drop_column("articles", "story_cluster_id")
    op.drop_column("articles", "model_confidence")
    op.drop_column("articles", "reliability_components")
    op.drop_column("articles", "trust_score_components")
    op.drop_column("articles", "bias_score_components")
    op.drop_column("articles", "political_lean")
    op.drop_column("articles", "framing")
    op.drop_column("articles", "source_type")

    op.drop_index("ix_story_clusters_created_at", table_name="story_clusters")
    op.drop_index("ix_story_clusters_category", table_name="story_clusters")
    op.drop_table("story_clusters")
