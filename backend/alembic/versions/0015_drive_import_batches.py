"""Add Google Drive batch import manifests."""

from alembic import op
import sqlalchemy as sa


revision = "0015_drive_import_batches"
down_revision = "0014_question_answer_key"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("drive_import_batches", sa.Column("id", sa.String(36), primary_key=True), sa.Column("teacher_id", sa.String(36), sa.ForeignKey("teachers.id"), nullable=False), sa.Column("exam_id", sa.String(36), sa.ForeignKey("exams.id"), nullable=False), sa.Column("root_folder_id", sa.String(255), nullable=False), sa.Column("state", sa.String(30), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_drive_import_batches_teacher_id", "drive_import_batches", ["teacher_id"])
    op.create_index("ix_drive_import_batches_exam_id", "drive_import_batches", ["exam_id"])
    op.create_table("drive_import_items", sa.Column("id", sa.String(36), primary_key=True), sa.Column("batch_id", sa.String(36), sa.ForeignKey("drive_import_batches.id"), nullable=False), sa.Column("folder_id", sa.String(255), nullable=False), sa.Column("folder_name", sa.String(255), nullable=False), sa.Column("student_id", sa.String(36), sa.ForeignKey("students.id"), nullable=True), sa.Column("pages", sa.JSON(), nullable=False), sa.Column("status", sa.String(30), nullable=False), sa.Column("error", sa.Text(), nullable=True))
    op.create_index("ix_drive_import_items_batch_id", "drive_import_items", ["batch_id"])
    op.create_index("ix_drive_import_items_student_id", "drive_import_items", ["student_id"])


def downgrade() -> None:
    op.drop_table("drive_import_items")
    op.drop_table("drive_import_batches")
