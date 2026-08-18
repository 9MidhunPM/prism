"""Add revocable opaque authentication sessions.

Revision ID: 0006_auth_sessions
Revises: 0005_submission_source_hash
"""

from alembic import op
from sqlalchemy import inspect

from app.models import AuthSession

revision = "0006_auth_sessions"
down_revision = "0005_submission_source_hash"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if AuthSession.__tablename__ not in inspect(op.get_bind()).get_table_names():
        AuthSession.__table__.create(bind=op.get_bind())


def downgrade() -> None:
    if AuthSession.__tablename__ in inspect(op.get_bind()).get_table_names():
        AuthSession.__table__.drop(bind=op.get_bind())
