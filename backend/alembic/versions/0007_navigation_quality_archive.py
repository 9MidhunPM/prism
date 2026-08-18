"""Add archive state and page quality fields."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0007_navigation_quality_archive"
down_revision = "0006_auth_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    columns = {
        table: {column["name"] for column in inspector.get_columns(table)}
        for table in inspector.get_table_names()
    }
    for table in ("classes", "students", "exams", "submissions"):
        if "archived_at" not in columns.get(table, set()):
            op.add_column(table, sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    if "quality_status" not in columns.get("submission_pages", set()):
        op.add_column("submission_pages", sa.Column("quality_status", sa.String(length=30), nullable=False, server_default="pending"))
    if "quality_reason" not in columns.get("submission_pages", set()):
        op.add_column("submission_pages", sa.Column("quality_reason", sa.Text(), nullable=True))
    if "quality_confidence" not in columns.get("submission_pages", set()):
        op.add_column("submission_pages", sa.Column("quality_confidence", sa.Float(), nullable=True))
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TYPE submissionstatus ADD VALUE IF NOT EXISTS 'RESCAN_REQUIRED'")


def downgrade() -> None:
    op.drop_column("submission_pages", "quality_confidence")
    op.drop_column("submission_pages", "quality_reason")
    op.drop_column("submission_pages", "quality_status")
    for table in ("submissions", "exams", "students", "classes"):
        op.drop_column(table, "archived_at")
