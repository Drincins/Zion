"""Add employment documents for formalized employees."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "c1d2e3f4a5b6"
down_revision = "0b9c8d7e6f5a"
branch_labels = None
depends_on = None


employment_document_kind = postgresql.ENUM(
    "employment_order",
    "employment_contract",
    name="employment_document_kind",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    employment_document_kind.create(bind, checkfirst=True)

    op.create_table(
        "employment_document_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("document_kind", employment_document_kind, nullable=False),
        sa.Column("issued_at", sa.Date(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("attachment_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "document_kind", name="uq_employment_document_record_user_kind"),
    )
    op.create_index(
        "ix_employment_document_records_user_kind",
        "employment_document_records",
        ["user_id", "document_kind"],
        unique=False,
    )
    op.create_index(
        "ix_employment_document_records_document_kind",
        "employment_document_records",
        ["document_kind"],
        unique=False,
    )
    op.create_index(
        "ix_employment_document_records_user_id",
        "employment_document_records",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_employment_document_records_user_id", table_name="employment_document_records")
    op.drop_index("ix_employment_document_records_document_kind", table_name="employment_document_records")
    op.drop_index("ix_employment_document_records_user_kind", table_name="employment_document_records")
    op.drop_table("employment_document_records")
    bind = op.get_bind()
    employment_document_kind.drop(bind, checkfirst=True)
