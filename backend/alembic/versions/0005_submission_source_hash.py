"""Add exact submission source identity.

Revision ID: 0005_submission_source_hash
Revises: 0004_accounts
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0005_submission_source_hash"
down_revision = "0004_accounts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("submissions")}
    if "source_hash" not in columns:
        op.add_column("submissions", sa.Column("source_hash", sa.String(length=64), nullable=True))
        op.create_index("ix_submissions_source_hash", "submissions", ["source_hash"])


def downgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("submissions")}
    if "source_hash" in columns:
        op.drop_index("ix_submissions_source_hash", table_name="submissions")
        op.drop_column("submissions", "source_hash")
