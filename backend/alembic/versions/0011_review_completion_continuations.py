"""Add review completion and page-continuation audit fields."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0011_review_completion"
down_revision = "0010_review_severity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    submission_columns = {column["name"] for column in inspector.get_columns("submissions")}
    answer_columns = {column["name"] for column in inspector.get_columns("answers")}
    if "mapping_review_required" not in submission_columns:
        op.add_column("submissions", sa.Column("mapping_review_required", sa.Boolean(), nullable=False, server_default=sa.false()))
    if "sequence" not in answer_columns:
        op.add_column("answers", sa.Column("sequence", sa.Integer(), nullable=False, server_default="1"))
    if "mapping_basis" not in answer_columns:
        op.add_column("answers", sa.Column("mapping_basis", sa.String(length=40), nullable=True))
    if "mapping_confidence" not in answer_columns:
        op.add_column("answers", sa.Column("mapping_confidence", sa.Float(), nullable=True))
    # Earlier versions could not distinguish ordinary uncertainty from an
    # evidence failure, so preserve it as an advisory signal instead of a hold.
    op.execute("UPDATE criterion_evaluations SET review_severity = 'review_recommended' WHERE review_severity = 'review_required' AND review_resolved = FALSE")
    op.execute("UPDATE submissions SET status = 'COMPLETED' WHERE status = 'REVIEW_REQUIRED' AND EXISTS (SELECT 1 FROM answers JOIN criterion_evaluations ON criterion_evaluations.answer_id = answers.id WHERE answers.submission_id = submissions.id) AND NOT EXISTS (SELECT 1 FROM answers JOIN criterion_evaluations ON criterion_evaluations.answer_id = answers.id WHERE answers.submission_id = submissions.id AND criterion_evaluations.review_severity = 'review_required' AND criterion_evaluations.review_resolved = FALSE)")
    op.execute("UPDATE processing_jobs SET stage = 'COMPLETED' WHERE stage = 'REVIEW_REQUIRED' AND submission_id IN (SELECT id FROM submissions WHERE status = 'COMPLETED')")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    submission_columns = {column["name"] for column in inspector.get_columns("submissions")}
    answer_columns = {column["name"] for column in inspector.get_columns("answers")}
    if "mapping_confidence" in answer_columns:
        op.drop_column("answers", "mapping_confidence")
    if "mapping_basis" in answer_columns:
        op.drop_column("answers", "mapping_basis")
    if "sequence" in answer_columns:
        op.drop_column("answers", "sequence")
    if "mapping_review_required" in submission_columns:
        op.drop_column("submissions", "mapping_review_required")
