"""Add indexes used by production review and processing queries."""

from alembic import op
from sqlalchemy import inspect

revision = "0016_production_hardening"
down_revision = "0015_drive_import_batches"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    indexes = {
        "exams": ("ix_exams_class_id", ["class_id"]),
        "submissions": ("ix_submissions_student_archived_created", ["student_id", "archived_at", "created_at"]),
        "teacher_overrides": ("ix_teacher_overrides_teacher_id", ["teacher_id"]),
        "review_suggestions": ("ix_review_suggestions_evaluation_status", ["evaluation_id", "status"]),
        "criterion_evaluations": ("ix_criterion_evaluations_answer_review", ["answer_id", "review_severity", "review_resolved"]),
        "ai_artifacts": ("ix_ai_artifacts_cache_lookup", ["operation", "prompt_version", "input_hash"]),
    }
    for table, (name, columns) in indexes.items():
        if table in tables and name not in {index["name"] for index in inspect(bind).get_indexes(table)}:
            op.create_index(name, table, columns)


def downgrade() -> None:
    bind = op.get_bind()
    for table, name in (
        ("ai_artifacts", "ix_ai_artifacts_cache_lookup"),
        ("criterion_evaluations", "ix_criterion_evaluations_answer_review"),
        ("review_suggestions", "ix_review_suggestions_evaluation_status"),
        ("teacher_overrides", "ix_teacher_overrides_teacher_id"),
        ("submissions", "ix_submissions_student_archived_created"),
        ("exams", "ix_exams_class_id"),
    ):
        if table in inspect(bind).get_table_names() and name in {index["name"] for index in inspect(bind).get_indexes(table)}:
            op.drop_index(name, table_name=table)
