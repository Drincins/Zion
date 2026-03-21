"""Init HR fields + payment_formats + employee_positions + attendances

Revision ID: 883548748173
Revises: 5f6d057fc463
Create Date: 2025-09-26 19:12:48.959839
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# --- ВАЖНО: ENUM-тип будем создавать/удалять вручную ---
# можно использовать sa.Enum, у него есть .create/.drop
gender_enum = sa.Enum('male', 'female', name='user_gender')

# revision identifiers, used by Alembic.
revision: str = '883548748173'
down_revision: Union[str, Sequence[str], None] = '5f6d057fc463'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1) создать тип ENUM, если ещё не создан
    bind = op.get_bind()
    gender_enum.create(bind, checkfirst=True)

    # 2) авто-сгенерированные объекты
    op.create_table(
        'payroll_adjustment_types',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_table(
        'training_event_types',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_table(
        'payroll_adjustments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('adjustment_type_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('responsible_id', sa.Integer(), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['adjustment_type_id'], ['payroll_adjustment_types.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['responsible_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payroll_adjustments_adjustment_type_id'), 'payroll_adjustments', ['adjustment_type_id'], unique=False)
    op.create_index(op.f('ix_payroll_adjustments_responsible_id'), 'payroll_adjustments', ['responsible_id'], unique=False)
    op.create_index('ix_payroll_adjustments_user_date', 'payroll_adjustments', ['user_id', 'date'], unique=False)
    op.create_index(op.f('ix_payroll_adjustments_user_id'), 'payroll_adjustments', ['user_id'], unique=False)

    op.create_table(
        'training_event_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_type_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['event_type_id'], ['training_event_types.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_training_event_records_event_type_id'), 'training_event_records', ['event_type_id'], unique=False)
    op.create_index('ix_training_event_records_user_date', 'training_event_records', ['user_id', 'date'], unique=False)
    op.create_index(op.f('ix_training_event_records_user_id'), 'training_event_records', ['user_id'], unique=False)

    # 3) колонка с использованием заранее созданного ENUM-типа
    op.add_column('users', sa.Column('gender', gender_enum, nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # 1) убрать колонку, затем удалить тип (если не используется)
    op.drop_column('users', 'gender')
    bind = op.get_bind()
    gender_enum.drop(bind, checkfirst=True)

    # 2) откат остальных объектов
    op.drop_index(op.f('ix_training_event_records_user_id'), table_name='training_event_records')
    op.drop_index('ix_training_event_records_user_date', table_name='training_event_records')
    op.drop_index(op.f('ix_training_event_records_event_type_id'), table_name='training_event_records')
    op.drop_table('training_event_records')

    op.drop_index(op.f('ix_payroll_adjustments_user_id'), table_name='payroll_adjustments')
    op.drop_index('ix_payroll_adjustments_user_date', table_name='payroll_adjustments')
    op.drop_index(op.f('ix_payroll_adjustments_responsible_id'), table_name='payroll_adjustments')
    op.drop_index(op.f('ix_payroll_adjustments_adjustment_type_id'), table_name='payroll_adjustments')
    op.drop_table('payroll_adjustments')

    op.drop_table('training_event_types')
    op.drop_table('payroll_adjustment_types')
