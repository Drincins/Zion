"""Add tables for payroll advance statements."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "2c4d5e6f7a89"
down_revision = "1f4e9d8ab123"
branch_labels = None
depends_on = None


def upgrade():
    # Drop stray enum if it was created by a failed run, then recreate cleanly.
    op.execute("DROP TYPE IF EXISTS payroll_advance_status")
    status_enum = postgresql.ENUM(
        "draft",
        "review",
        "confirmed",
        "ready",
        "posted",
        name="payroll_advance_status",
        create_type=False,
    )
    status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "payroll_advance_statements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column(
            "status",
            status_enum,
            nullable=False,
            server_default="draft",
        ),
        sa.Column("date_from", sa.Date(), nullable=False),
        sa.Column("date_to", sa.Date(), nullable=False),
        sa.Column("restaurant_id", sa.Integer(), sa.ForeignKey("restaurants.id", ondelete="SET NULL"), nullable=True),
        sa.Column(
            "subdivision_id",
            sa.Integer(),
            sa.ForeignKey("restaurant_subdivisions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("salary_percent", sa.Numeric(5, 2), nullable=True),
        sa.Column("fixed_only", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("filters", sa.JSON(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_payroll_advance_statements_restaurant",
        "payroll_advance_statements",
        ["restaurant_id"],
    )
    op.create_index(
        "ix_payroll_advance_statements_subdivision",
        "payroll_advance_statements",
        ["subdivision_id"],
    )
    op.create_index(
        "ix_payroll_advance_statements_created_by",
        "payroll_advance_statements",
        ["created_by_id"],
    )
    op.create_index(
        "ix_payroll_advance_statements_updated_by",
        "payroll_advance_statements",
        ["updated_by_id"],
    )
    op.alter_column("payroll_advance_statements", "status", server_default=None)
    op.alter_column("payroll_advance_statements", "fixed_only", server_default=None)

    op.create_table(
        "payroll_advance_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "statement_id",
            sa.Integer(),
            sa.ForeignKey("payroll_advance_statements.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("restaurant_id", sa.Integer(), sa.ForeignKey("restaurants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("position_id", sa.Integer(), sa.ForeignKey("positions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("staff_code", sa.String(), nullable=True),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("position_name", sa.String(), nullable=True),
        sa.Column("calculated_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("final_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("manual", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_payroll_advance_items_statement_user",
        "payroll_advance_items",
        ["statement_id", "user_id"],
    )
    op.alter_column("payroll_advance_items", "calculated_amount", server_default=None)
    op.alter_column("payroll_advance_items", "final_amount", server_default=None)
    op.alter_column("payroll_advance_items", "manual", server_default=None)

    permissions_table = sa.table(
        "permissions",
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.String()),
    )
    op.bulk_insert(
        permissions_table,
        [
            {"code": "payroll.advance.view", "name": "Авансы: доступ", "description": "Доступ к разделу авансов"},
            {"code": "payroll.advance.create", "name": "Авансы: создать черновик", "description": "Формирование черновика аванса"},
            {"code": "payroll.advance.edit", "name": "Авансы: редактировать", "description": "Правка сумм в черновике аванса"},
            {"code": "payroll.advance.status.review", "name": "Авансы: отправить на проверку", "description": "Перевод черновика в статус проверки"},
            {"code": "payroll.advance.status.confirm", "name": "Авансы: подтвердить", "description": "Подтверждение черновика аванса"},
            {"code": "payroll.advance.status.ready", "name": "Авансы: готов к выдаче", "description": "Отметить ведомость готовой к выдаче"},
            {"code": "payroll.advance.status.all", "name": "Авансы: управление статусами", "description": "Полное управление статусами ведомости аванса"},
            {"code": "payroll.advance.download", "name": "Авансы: скачать файл", "description": "Скачивание файла ведомости аванса"},
            {"code": "payroll.advance.post", "name": "Авансы: записать в финансы", "description": "Запись аванса в журнал финансов"},
        ],
    )


def downgrade():
    op.drop_index("ix_payroll_advance_statements_updated_by", table_name="payroll_advance_statements")
    op.drop_index("ix_payroll_advance_statements_created_by", table_name="payroll_advance_statements")
    op.drop_index("ix_payroll_advance_statements_subdivision", table_name="payroll_advance_statements")
    op.drop_index("ix_payroll_advance_statements_restaurant", table_name="payroll_advance_statements")
    op.drop_index("ix_payroll_advance_items_statement_user", table_name="payroll_advance_items")
    op.drop_table("payroll_advance_items")
    op.drop_table("payroll_advance_statements")
    op.execute("DROP TYPE IF EXISTS payroll_advance_status")
    op.execute(
        "DELETE FROM permissions WHERE code IN ("
        "'payroll.advance.view', 'payroll.advance.create', 'payroll.advance.edit', "
        "'payroll.advance.status.review', 'payroll.advance.status.confirm', "
        "'payroll.advance.status.ready', 'payroll.advance.status.all', "
        "'payroll.advance.download', 'payroll.advance.post'"
        ")"
    )
