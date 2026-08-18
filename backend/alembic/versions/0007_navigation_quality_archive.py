"""Add archive state and page quality fields."""

from alembic import op
import sqlalchemy as sa


revision = "0007_navigation_quality_archive"
down_revision = "0006_auth_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("classes", "students", "exams", "submissions"):
        op.add_column(table, sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("submission_pages", sa.Column("quality_status", sa.String(length=30), nullable=False, server_default="pending"))
    op.add_column("submission_pages", sa.Column("quality_reason", sa.Text(), nullable=True))
    op.add_column("submission_pages", sa.Column("quality_confidence", sa.Float(), nullable=True))
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TYPE submissionstatus ADD VALUE IF NOT EXISTS 'rescan_required'")


def downgrade() -> None:
    op.drop_column("submission_pages", "quality_confidence")
    op.drop_column("submission_pages", "quality_reason")
    op.drop_column("submission_pages", "quality_status")
    for table in ("submissions", "exams", "students", "classes"):
        op.drop_column(table, "archived_at")
