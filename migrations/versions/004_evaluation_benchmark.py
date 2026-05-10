"""Evaluation benchmark and runs.

Revision ID: 004_evaluation_benchmark
Revises: 003_review_suggestion_profiles
Create Date: 2026-04-30 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004_evaluation_benchmark"
down_revision: str | None = "003_review_suggestion_profiles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "benchmark_products",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("benchmark_set_name", sa.String(length=255), nullable=False),
        sa.Column("platform_name", sa.String(length=64), nullable=False),
        sa.Column("product_external_id", sa.String(length=512), nullable=True),
        sa.Column("product_title", sa.String(length=1024), nullable=False),
        sa.Column("product_url", sa.Text(), nullable=True),
        sa.Column("snapshot_timestamp", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("category", sa.String(length=512), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_benchmark_products_benchmark_set_name"),
        "benchmark_products",
        ["benchmark_set_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_benchmark_products_platform_name"),
        "benchmark_products",
        ["platform_name"],
        unique=False,
    )

    op.create_table(
        "benchmark_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("benchmark_product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("review_external_id", sa.String(length=512), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("plus", sa.Text(), nullable=True),
        sa.Column("minus", sa.Text(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("review_date", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["benchmark_product_id"],
            ["benchmark_products.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_benchmark_reviews_benchmark_product_id"),
        "benchmark_reviews",
        ["benchmark_product_id"],
        unique=False,
    )

    op.create_table(
        "external_summary_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("benchmark_product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform_name", sa.String(length=64), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("pros_text", sa.Text(), nullable=True),
        sa.Column("cons_text", sa.Text(), nullable=True),
        sa.Column("highlights_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("raw_block_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("snapshot_timestamp", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["benchmark_product_id"],
            ["benchmark_products.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_external_summary_snapshots_benchmark_product_id"),
        "external_summary_snapshots",
        ["benchmark_product_id"],
        unique=False,
    )

    op.create_table(
        "generated_summary_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("benchmark_product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("method_name", sa.String(length=100), nullable=False),
        sa.Column("method_version", sa.String(length=50), nullable=True),
        sa.Column("summary_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("text_overall", sa.Text(), nullable=True),
        sa.Column("text_pros", sa.Text(), nullable=True),
        sa.Column("text_cons", sa.Text(), nullable=True),
        sa.Column("text_neutral", sa.Text(), nullable=True),
        sa.Column("key_phrases_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(
            ["benchmark_product_id"],
            ["benchmark_products.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["summary_id"],
            ["summaries.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_generated_summary_snapshots_benchmark_product_id"),
        "generated_summary_snapshots",
        ["benchmark_product_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_generated_summary_snapshots_summary_id"),
        "generated_summary_snapshots",
        ["summary_id"],
        unique=False,
    )

    op.create_table(
        "reference_ledgers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("benchmark_product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reference_version", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["benchmark_product_id"],
            ["benchmark_products.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_reference_ledgers_benchmark_product_id"),
        "reference_ledgers",
        ["benchmark_product_id"],
        unique=False,
    )

    op.create_table(
        "reference_aspects",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ledger_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("aspect_name", sa.String(length=255), nullable=False),
        sa.Column("salience_weight", sa.Float(), nullable=False),
        sa.Column("expected_polarity", sa.String(length=32), nullable=False),
        sa.Column(
            "polarity_distribution_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "rare_but_important",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "aliases_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.ForeignKeyConstraint(
            ["ledger_id"],
            ["reference_ledgers.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_reference_aspects_ledger_id"),
        "reference_aspects",
        ["ledger_id"],
        unique=False,
    )

    op.create_table(
        "reference_evidences",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reference_aspect_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("review_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("section_type", sa.String(length=32), nullable=False),
        sa.Column("polarity", sa.String(length=32), nullable=False),
        sa.Column("evidence_strength", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(
            ["reference_aspect_id"],
            ["reference_aspects.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["review_id"],
            ["benchmark_reviews.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_reference_evidences_reference_aspect_id"),
        "reference_evidences",
        ["reference_aspect_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_reference_evidences_review_id"),
        "reference_evidences",
        ["review_id"],
        unique=False,
    )

    op.create_table(
        "evaluation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("benchmark_set_name", sa.String(length=255), nullable=False),
        sa.Column("run_name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("config_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_evaluation_runs_benchmark_set_name"),
        "evaluation_runs",
        ["benchmark_set_name"],
        unique=False,
    )

    op.create_table(
        "evaluation_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evaluation_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("benchmark_product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("system_name", sa.String(length=128), nullable=False),
        sa.Column("metrics_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("judge_scores_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("notes_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(
            ["evaluation_run_id"],
            ["evaluation_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["benchmark_product_id"],
            ["benchmark_products.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_evaluation_results_evaluation_run_id"),
        "evaluation_results",
        ["evaluation_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_results_benchmark_product_id"),
        "evaluation_results",
        ["benchmark_product_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_results_system_name"),
        "evaluation_results",
        ["system_name"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_evaluation_results_system_name"), table_name="evaluation_results")
    op.drop_index(
        op.f("ix_evaluation_results_benchmark_product_id"),
        table_name="evaluation_results",
    )
    op.drop_index(
        op.f("ix_evaluation_results_evaluation_run_id"),
        table_name="evaluation_results",
    )
    op.drop_table("evaluation_results")

    op.drop_index(op.f("ix_evaluation_runs_benchmark_set_name"), table_name="evaluation_runs")
    op.drop_table("evaluation_runs")

    op.drop_index(op.f("ix_reference_evidences_review_id"), table_name="reference_evidences")
    op.drop_index(
        op.f("ix_reference_evidences_reference_aspect_id"),
        table_name="reference_evidences",
    )
    op.drop_table("reference_evidences")

    op.drop_index(op.f("ix_reference_aspects_ledger_id"), table_name="reference_aspects")
    op.drop_table("reference_aspects")

    op.drop_index(
        op.f("ix_reference_ledgers_benchmark_product_id"),
        table_name="reference_ledgers",
    )
    op.drop_table("reference_ledgers")

    op.drop_index(
        op.f("ix_generated_summary_snapshots_summary_id"),
        table_name="generated_summary_snapshots",
    )
    op.drop_index(
        op.f("ix_generated_summary_snapshots_benchmark_product_id"),
        table_name="generated_summary_snapshots",
    )
    op.drop_table("generated_summary_snapshots")

    op.drop_index(
        op.f("ix_external_summary_snapshots_benchmark_product_id"),
        table_name="external_summary_snapshots",
    )
    op.drop_table("external_summary_snapshots")

    op.drop_index(
        op.f("ix_benchmark_reviews_benchmark_product_id"),
        table_name="benchmark_reviews",
    )
    op.drop_table("benchmark_reviews")

    op.drop_index(op.f("ix_benchmark_products_platform_name"), table_name="benchmark_products")
    op.drop_index(
        op.f("ix_benchmark_products_benchmark_set_name"),
        table_name="benchmark_products",
    )
    op.drop_table("benchmark_products")
