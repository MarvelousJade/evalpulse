"""Persist one bounded AI diagnosis per evaluation run."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Revision 0001 uses metadata.create_all rather than a frozen table list. A brand-new
    # installation therefore already sees this table through current metadata, while an
    # installation upgrading from the original 0001 schema does not.
    if "run_diagnoses" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "run_diagnoses",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("findings", sa.JSON(), nullable=False),
        sa.Column("actions", sa.JSON(), nullable=False),
        sa.Column("citations", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("usage", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["evaluation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id"),
    )
    op.create_index("ix_run_diagnoses_run_id", "run_diagnoses", ["run_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_run_diagnoses_run_id", table_name="run_diagnoses")
    op.drop_table("run_diagnoses")
