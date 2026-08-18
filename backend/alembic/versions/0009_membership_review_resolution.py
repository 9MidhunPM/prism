"""Add multi-class membership and resolved-review workflow fields."""

from alembic import op
import sqlalchemy as sa


revision = "0009_membership_review_resolution"
down_revision = "0008_add_rescan_status_enum"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "class_memberships",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("class_id", sa.String(length=36), sa.ForeignKey("classes.id"), nullable=False),
        sa.Column("student_id", sa.String(length=36), sa.ForeignKey("students.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("class_id", "student_id", name="uq_class_membership"),
    )
    op.create_index("ix_class_memberships_class_id", "class_memberships", ["class_id"])
    op.create_index("ix_class_memberships_student_id", "class_memberships", ["student_id"])
    op.add_column("criterion_evaluations", sa.Column("review_resolved", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("criterion_evaluations", sa.Column("review_resolution", sa.String(length=20), nullable=True))
    op.add_column("criterion_evaluations", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE criterion_evaluations SET review_resolved = TRUE WHERE needs_review = FALSE")


def downgrade() -> None:
    op.drop_column("criterion_evaluations", "reviewed_at")
    op.drop_column("criterion_evaluations", "review_resolution")
    op.drop_column("criterion_evaluations", "review_resolved")
    op.drop_table("class_memberships")
