"""Add persistent processing jobs.

Revision ID: 0002_processing_jobs
Revises: 0001_initial_schema
"""

from alembic import op
from sqlalchemy import inspect

from app.models import ProcessingJob

revision = "0002_processing_jobs"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if "processing_jobs" not in inspect(bind).get_table_names():
        ProcessingJob.__table__.create(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    if "processing_jobs" in inspect(bind).get_table_names():
        ProcessingJob.__table__.drop(bind=bind)
