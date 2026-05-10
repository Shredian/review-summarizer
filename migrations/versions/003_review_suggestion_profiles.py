"""Review suggestion profiles and events.

Revision ID: 003_review_suggestion_profiles
Revises: 002_aspect_evidence_artifacts
Create Date: 2026-04-25 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_review_suggestion_profiles"
down_revision: str | None = "002_aspect_evidence_artifacts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_suggestion_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("reviews_count", sa.Integer(), nullable=False),
        sa.Column("segments_count", sa.Integer(), nullable=False),
        sa.Column("source_hash", sa.String(length=128), nullable=False),
        sa.Column(
            "profile_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("built_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id"),
    )
    op.create_index(
        op.f("ix_product_suggestion_profiles_product_id"),
        "product_suggestion_profiles",
        ["product_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_product_suggestion_profiles_status"),
        "product_suggestion_profiles",
        ["status"],
        unique=False,
    )

    op.create_table(
        "user_suggestion_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("reviews_count", sa.Integer(), nullable=False),
        sa.Column("source_hash", sa.String(length=128), nullable=False),
        sa.Column(
            "profile_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("built_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(
        op.f("ix_user_suggestion_profiles_user_id"),
        "user_suggestion_profiles",
        ["user_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_user_suggestion_profiles_status"),
        "user_suggestion_profiles",
        ["status"],
        unique=False,
    )

    op.create_table(
        "review_suggestion_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("context_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("field", sa.String(length=20), nullable=False),
        sa.Column("current_text_before", sa.Text(), nullable=True),
        sa.Column(
            "suggestions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("selected_suggestion", sa.Text(), nullable=True),
        sa.Column("current_text_after", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_review_suggestion_events_context_id"),
        "review_suggestion_events",
        ["context_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_review_suggestion_events_created_at"),
        "review_suggestion_events",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_review_suggestion_events_event_type"),
        "review_suggestion_events",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_review_suggestion_events_product_id"),
        "review_suggestion_events",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        "ix_review_suggestion_events_product_created",
        "review_suggestion_events",
        ["product_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_review_suggestion_events_user_created",
        "review_suggestion_events",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_review_suggestion_events_user_id"),
        "review_suggestion_events",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_review_suggestion_events_user_id"), table_name="review_suggestion_events"
    )
    op.drop_index("ix_review_suggestion_events_user_created", table_name="review_suggestion_events")
    op.drop_index(
        "ix_review_suggestion_events_product_created", table_name="review_suggestion_events"
    )
    op.drop_index(
        op.f("ix_review_suggestion_events_product_id"), table_name="review_suggestion_events"
    )
    op.drop_index(
        op.f("ix_review_suggestion_events_event_type"), table_name="review_suggestion_events"
    )
    op.drop_index(
        op.f("ix_review_suggestion_events_created_at"), table_name="review_suggestion_events"
    )
    op.drop_index(
        op.f("ix_review_suggestion_events_context_id"), table_name="review_suggestion_events"
    )
    op.drop_table("review_suggestion_events")

    op.drop_index(op.f("ix_user_suggestion_profiles_status"), table_name="user_suggestion_profiles")
    op.drop_index(
        op.f("ix_user_suggestion_profiles_user_id"), table_name="user_suggestion_profiles"
    )
    op.drop_table("user_suggestion_profiles")

    op.drop_index(
        op.f("ix_product_suggestion_profiles_status"), table_name="product_suggestion_profiles"
    )
    op.drop_index(
        op.f("ix_product_suggestion_profiles_product_id"), table_name="product_suggestion_profiles"
    )
    op.drop_table("product_suggestion_profiles")
