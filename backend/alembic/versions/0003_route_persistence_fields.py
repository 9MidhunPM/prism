"""Add normalized fields required by active application routes.

Revision ID: 0003_route_persistence_fields
Revises: 0002_processing_jobs
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

from app.models import EvaluationEvidence, ReviewSuggestion

revision = "0003_route_persistence_fields"
down_revision = "0002_processing_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = inspector.get_table_names()
    columns = {table: {column["name"] for column in inspector.get_columns(table)} for table in tables}
    # 0001 historically used metadata.create_all, so these may already exist
    # on a fresh database. The guard also supports databases created before
    # these normalized route-persistence tables were added.
    if EvaluationEvidence.__tablename__ not in tables:
        EvaluationEvidence.__table__.create(bind=bind)
    if ReviewSuggestion.__tablename__ not in tables:
        ReviewSuggestion.__table__.create(bind=bind)
    additions = {
        "teachers": [("created_at", sa.DateTime(timezone=True), True, None)],
        "submission_pages": [("mime_type", sa.String(length=100), False, "application/octet-stream")],
        "answers": [("prompt_version", sa.String(length=50), False, "perception_v1")],
    }
    for table, fields in additions.items():
        if table not in columns:
            continue
        for name, type_, nullable, default in fields:
            if name not in columns[table]:
                op.add_column(table, sa.Column(name, type_, nullable=nullable, server_default=default))


def downgrade() -> None:
    bind = op.get_bind()
    tables = inspect(bind).get_table_names()
    if ReviewSuggestion.__tablename__ in tables:
        ReviewSuggestion.__table__.drop(bind=bind)
    if EvaluationEvidence.__tablename__ in tables:
        EvaluationEvidence.__table__.drop(bind=bind)
