"""Add teacher-controlled result release and student account state."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0013_student_release"
down_revision = "0012_durable_page_media"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    account_columns = {column["name"] for column in inspector.get_columns("accounts")}
    submission_columns = {column["name"] for column in inspector.get_columns("submissions")}
    if "disabled_at" not in account_columns:
        op.add_column("accounts", sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True))
    if "must_change_password" not in account_columns:
        op.add_column("accounts", sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()))
    if "released_at" not in submission_columns:
        op.add_column("submissions", sa.Column("released_at", sa.DateTime(timezone=True), nullable=True))
    if "released_by_teacher_id" not in submission_columns:
        op.add_column("submissions", sa.Column("released_by_teacher_id", sa.String(length=36), sa.ForeignKey("teachers.id"), nullable=True))


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    account_columns = {column["name"] for column in inspector.get_columns("accounts")}
    submission_columns = {column["name"] for column in inspector.get_columns("submissions")}
    if "released_by_teacher_id" in submission_columns:
        op.drop_column("submissions", "released_by_teacher_id")
    if "released_at" in submission_columns:
        op.drop_column("submissions", "released_at")
    if "must_change_password" in account_columns:
        op.drop_column("accounts", "must_change_password")
    if "disabled_at" in account_columns:
        op.drop_column("accounts", "disabled_at")
