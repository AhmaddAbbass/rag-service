"""create corpora and attempts

Revision ID: 0002_corpora_attempts
Revises: 0001_users_sessions
Create Date: 2026-01-15 12:21:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_corpora_attempts"
down_revision = "0001_users_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "corpora",
        sa.Column("corpus_id", sa.String(), primary_key=True, nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("book_name", sa.String(), nullable=True),
        sa.Column("source_path", sa.String(), nullable=False),
        sa.Column("source_sha256", sa.String(), nullable=False),
        sa.Column("source_len_chars", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("latest_success_attempt_id", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "attempts",
        sa.Column("attempt_id", sa.String(), primary_key=True, nullable=False),
        sa.Column("corpus_id", sa.String(), nullable=False),
        sa.Column("runner_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False),
        sa.Column("artifacts", postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["corpus_id"], ["corpora.corpus_id"], ondelete="CASCADE"),
    )
    op.create_index("ix_attempts_corpus_id", "attempts", ["corpus_id"])


def downgrade() -> None:
    op.drop_index("ix_attempts_corpus_id", table_name="attempts")
    op.drop_table("attempts")
    op.drop_table("corpora")
