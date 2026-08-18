"""Add role-aware accounts and backfill existing teacher logins.

Revision ID: 0004_accounts
Revises: 0003_route_persistence_fields
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
import uuid

from app.models import Account

revision = "0004_accounts"
down_revision = "0003_route_persistence_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if "accounts" not in inspect(bind).get_table_names():
        Account.__table__.create(bind=bind)
    # Existing teacher login records become teacher accounts without changing credentials.
    teachers = sa.table("teachers", sa.column("id"), sa.column("email"), sa.column("password_hash"))
    accounts = sa.table("accounts", sa.column("id"), sa.column("email"), sa.column("password_hash"), sa.column("role"), sa.column("teacher_id"))
    existing_teacher_ids = set(bind.execute(sa.select(accounts.c.teacher_id).where(accounts.c.teacher_id.is_not(None))).scalars())
    for teacher in bind.execute(sa.select(teachers.c.id, teachers.c.email, teachers.c.password_hash)):
        if teacher.id not in existing_teacher_ids:
            bind.execute(accounts.insert().values(id=str(uuid.uuid4()), email=teacher.email, password_hash=teacher.password_hash, role="TEACHER", teacher_id=teacher.id))


def downgrade() -> None:
    bind = op.get_bind()
    if "accounts" in inspect(bind).get_table_names():
        Account.__table__.drop(bind=bind)
