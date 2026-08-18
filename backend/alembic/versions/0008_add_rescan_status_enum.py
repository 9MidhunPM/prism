"""Add SQLAlchemy's enum-name value for rescan-required submissions."""

from alembic import op


revision = "0008_add_rescan_status_enum"
down_revision = "0007_navigation_quality_archive"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TYPE submissionstatus ADD VALUE IF NOT EXISTS 'RESCAN_REQUIRED'")


def downgrade() -> None:
    # PostgreSQL cannot safely remove an enum value in place.
    pass
