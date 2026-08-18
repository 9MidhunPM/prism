"""Separate mandatory review holds from advisory recommendations."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0010_review_severity"
down_revision = "0009_membership_review"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("criterion_evaluations")}
    if "review_severity" not in columns:
        op.add_column("criterion_evaluations", sa.Column("review_severity", sa.String(length=30), nullable=True))
    # Existing unresolved flags were blocking before severity existed, so retain
    # that conservative behavior rather than silently completing old papers.
    op.execute("UPDATE criterion_evaluations SET review_severity = 'review_required' WHERE needs_review = TRUE AND review_severity IS NULL")


def downgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("criterion_evaluations")}
    if "review_severity" in columns:
        op.drop_column("criterion_evaluations", "review_severity")
