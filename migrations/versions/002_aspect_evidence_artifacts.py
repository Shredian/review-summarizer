"""Add tables for aspect-evidence artifacts.

Revision ID: 002_aspect_evidence_artifacts
Revises: 001_initial
Create Date: 2026-04-16 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002_aspect_evidence_artifacts"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "aspect_mentions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("review_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("summary_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("span_text", sa.Text(), nullable=False),
        sa.Column("section_type", sa.String(length=30), nullable=False),
        sa.Column("aspect_raw", sa.String(length=255), nullable=False),
        sa.Column("aspect_candidate", sa.String(length=255), nullable=False),
        sa.Column("sentiment_label", sa.String(length=20), nullable=False),
        sa.Column("sentiment_score", sa.Float(), nullable=True),
        sa.Column("extractor_confidence", sa.Float(), nullable=True),
        sa.Column("extractor_version", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["summary_id"], ["summaries.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_aspect_mentions_id"), "aspect_mentions", ["id"], unique=False)
    op.create_index(
        op.f("ix_aspect_mentions_product_id"),
        "aspect_mentions",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_aspect_mentions_review_id"),
        "aspect_mentions",
        ["review_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_aspect_mentions_summary_id"),
        "aspect_mentions",
        ["summary_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_aspect_mentions_section_type"),
        "aspect_mentions",
        ["section_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_aspect_mentions_aspect_candidate"),
        "aspect_mentions",
        ["aspect_candidate"],
        unique=False,
    )
    op.create_index(
        op.f("ix_aspect_mentions_sentiment_label"),
        "aspect_mentions",
        ["sentiment_label"],
        unique=False,
    )

    op.create_table(
        "aspect_clusters",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("summary_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("aspect_name", sa.String(length=255), nullable=False),
        sa.Column("aliases_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("total_mentions", sa.Integer(), nullable=False),
        sa.Column("positive_mentions", sa.Integer(), nullable=False),
        sa.Column("negative_mentions", sa.Integer(), nullable=False),
        sa.Column("neutral_mentions", sa.Integer(), nullable=False),
        sa.Column("mixed_mentions", sa.Integer(), nullable=False),
        sa.Column("importance_score", sa.Float(), nullable=False),
        sa.Column("prevalence_score", sa.Float(), nullable=False),
        sa.Column("polarity_balance_score", sa.Float(), nullable=False),
        sa.Column("rarity_flag", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["summary_id"], ["summaries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_aspect_clusters_id"), "aspect_clusters", ["id"], unique=False)
    op.create_index(
        op.f("ix_aspect_clusters_product_id"),
        "aspect_clusters",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_aspect_clusters_summary_id"),
        "aspect_clusters",
        ["summary_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_aspect_clusters_aspect_name"),
        "aspect_clusters",
        ["aspect_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_aspect_clusters_rarity_flag"),
        "aspect_clusters",
        ["rarity_flag"],
        unique=False,
    )

    op.create_table(
        "summary_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("summary_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "selected_aspects_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "dropped_aspects_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "diagnostics_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("planner_version", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["summary_id"], ["summaries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("summary_id"),
    )
    op.create_index(op.f("ix_summary_plans_id"), "summary_plans", ["id"], unique=False)
    op.create_index(
        op.f("ix_summary_plans_summary_id"),
        "summary_plans",
        ["summary_id"],
        unique=True,
    )

    op.create_table(
        "summary_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("summary_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("aspect_cluster_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("review_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evidence_text", sa.Text(), nullable=False),
        sa.Column("evidence_rank", sa.Integer(), nullable=False),
        sa.Column("used_in_final_summary", sa.Boolean(), nullable=False),
        sa.Column("supports_polarity", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["aspect_cluster_id"],
            ["aspect_clusters.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["summary_id"], ["summaries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_summary_evidence_id"), "summary_evidence", ["id"], unique=False)
    op.create_index(
        op.f("ix_summary_evidence_summary_id"),
        "summary_evidence",
        ["summary_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_summary_evidence_aspect_cluster_id"),
        "summary_evidence",
        ["aspect_cluster_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_summary_evidence_review_id"),
        "summary_evidence",
        ["review_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_summary_evidence_evidence_rank"),
        "summary_evidence",
        ["evidence_rank"],
        unique=False,
    )
    op.create_index(
        op.f("ix_summary_evidence_supports_polarity"),
        "summary_evidence",
        ["supports_polarity"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_summary_evidence_supports_polarity"), table_name="summary_evidence")
    op.drop_index(op.f("ix_summary_evidence_evidence_rank"), table_name="summary_evidence")
    op.drop_index(op.f("ix_summary_evidence_review_id"), table_name="summary_evidence")
    op.drop_index(op.f("ix_summary_evidence_aspect_cluster_id"), table_name="summary_evidence")
    op.drop_index(op.f("ix_summary_evidence_summary_id"), table_name="summary_evidence")
    op.drop_index(op.f("ix_summary_evidence_id"), table_name="summary_evidence")
    op.drop_table("summary_evidence")

    op.drop_index(op.f("ix_summary_plans_summary_id"), table_name="summary_plans")
    op.drop_index(op.f("ix_summary_plans_id"), table_name="summary_plans")
    op.drop_table("summary_plans")

    op.drop_index(op.f("ix_aspect_clusters_rarity_flag"), table_name="aspect_clusters")
    op.drop_index(op.f("ix_aspect_clusters_aspect_name"), table_name="aspect_clusters")
    op.drop_index(op.f("ix_aspect_clusters_summary_id"), table_name="aspect_clusters")
    op.drop_index(op.f("ix_aspect_clusters_product_id"), table_name="aspect_clusters")
    op.drop_index(op.f("ix_aspect_clusters_id"), table_name="aspect_clusters")
    op.drop_table("aspect_clusters")

    op.drop_index(op.f("ix_aspect_mentions_sentiment_label"), table_name="aspect_mentions")
    op.drop_index(op.f("ix_aspect_mentions_aspect_candidate"), table_name="aspect_mentions")
    op.drop_index(op.f("ix_aspect_mentions_section_type"), table_name="aspect_mentions")
    op.drop_index(op.f("ix_aspect_mentions_summary_id"), table_name="aspect_mentions")
    op.drop_index(op.f("ix_aspect_mentions_review_id"), table_name="aspect_mentions")
    op.drop_index(op.f("ix_aspect_mentions_product_id"), table_name="aspect_mentions")
    op.drop_index(op.f("ix_aspect_mentions_id"), table_name="aspect_mentions")
    op.drop_table("aspect_mentions")
