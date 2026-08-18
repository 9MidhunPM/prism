"""Persist original and processed page media with submission metadata."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0012_durable_page_media"
down_revision = "0011_review_completion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("submission_pages")}
    if "original_data" not in columns:
        op.add_column("submission_pages", sa.Column("original_data", sa.LargeBinary(), nullable=True))
    if "processed_data" not in columns:
        op.add_column("submission_pages", sa.Column("processed_data", sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("submission_pages")}
    if "processed_data" in columns:
        op.drop_column("submission_pages", "processed_data")
    if "original_data" in columns:
        op.drop_column("submission_pages", "original_data")
