"""Store optional teacher reference answers per question."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0014_question_answer_key"
down_revision = "0013_student_release"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("questions")}
    if "answer_key" not in columns:
        op.add_column("questions", sa.Column("answer_key", sa.Text(), nullable=True))


def downgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("questions")}
    if "answer_key" in columns:
        op.drop_column("questions", "answer_key")
