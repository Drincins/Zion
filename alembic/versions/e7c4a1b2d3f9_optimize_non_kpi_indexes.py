"""Optimize non-KPI indexes (payroll, checklists, access links).

Revision ID: e7c4a1b2d3f9
Revises: d9b1e7c4f2a0
Create Date: 2026-03-08 00:30:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e7c4a1b2d3f9"
down_revision: Union[str, Sequence[str], None] = "d9b1e7c4f2a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_user_restaurants_restaurant_id",
        "user_restaurants",
        ["restaurant_id"],
        unique=False,
    )

    op.create_index(
        "ix_position_permissions_permission_id",
        "position_permissions",
        ["permission_id"],
        unique=False,
    )
    op.create_index(
        "ix_role_permissions_permission_id",
        "role_permissions",
        ["permission_id"],
        unique=False,
    )
    op.create_index(
        "ix_user_permissions_permission_id",
        "user_permissions",
        ["permission_id"],
        unique=False,
    )

    op.create_index(
        "ix_users_company_fired",
        "users",
        ["company_id", "fired"],
        unique=False,
    )
    op.create_index(
        "ix_users_role_id",
        "users",
        ["role_id"],
        unique=False,
    )

    op.create_index(
        "ix_payroll_adjustments_rest_type_date_user",
        "payroll_adjustments",
        ["restaurant_id", "adjustment_type_id", "date", "user_id"],
        unique=False,
    )
    op.create_index(
        "ix_payroll_adjustments_responsible_date",
        "payroll_adjustments",
        ["responsible_id", "date"],
        unique=False,
    )
    op.create_index(
        "ix_payroll_salary_results_period_user",
        "payroll_salary_results",
        ["period_start", "period_end", "user_id"],
        unique=False,
    )

    op.create_index(
        "ix_payroll_advance_statements_rest_created",
        "payroll_advance_statements",
        ["restaurant_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_payroll_advance_statements_status_created",
        "payroll_advance_statements",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_payroll_advance_statements_creator_created",
        "payroll_advance_statements",
        ["created_by_id", "created_at"],
        unique=False,
    )

    op.create_index(
        "ix_checklists_company_created_at",
        "checklists",
        ["company_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_checklists_company_creator",
        "checklists",
        ["company_id", "created_by"],
        unique=False,
    )

    op.create_index(
        "ix_checklist_sections_checklist_order",
        "checklist_sections",
        ["checklist_id", "order"],
        unique=False,
    )
    op.create_index(
        "ix_checklist_questions_checklist_order",
        "checklist_questions",
        ["checklist_id", "order"],
        unique=False,
    )
    op.create_index(
        "ix_checklist_questions_section_order",
        "checklist_questions",
        ["section_id", "order"],
        unique=False,
    )

    op.create_index(
        "ix_ca_ck_submitted",
        "checklist_answers",
        ["checklist_id", "submitted_at"],
        unique=False,
    )
    op.create_index(
        "ix_ca_ck_dept_submitted",
        "checklist_answers",
        ["checklist_id", "department", "submitted_at"],
        unique=False,
    )

    op.create_index(
        "ix_employee_change_events_user_created",
        "employee_change_events",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_employee_change_events_field_created",
        "employee_change_events",
        ["field", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_employee_change_events_created_id",
        "employee_change_events",
        ["created_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_employee_change_events_created_id", table_name="employee_change_events")
    op.drop_index("ix_employee_change_events_field_created", table_name="employee_change_events")
    op.drop_index("ix_employee_change_events_user_created", table_name="employee_change_events")

    op.drop_index("ix_ca_ck_dept_submitted", table_name="checklist_answers")
    op.drop_index("ix_ca_ck_submitted", table_name="checklist_answers")

    op.drop_index("ix_checklist_questions_section_order", table_name="checklist_questions")
    op.drop_index("ix_checklist_questions_checklist_order", table_name="checklist_questions")
    op.drop_index("ix_checklist_sections_checklist_order", table_name="checklist_sections")

    op.drop_index("ix_checklists_company_creator", table_name="checklists")
    op.drop_index("ix_checklists_company_created_at", table_name="checklists")

    op.drop_index("ix_payroll_advance_statements_creator_created", table_name="payroll_advance_statements")
    op.drop_index("ix_payroll_advance_statements_status_created", table_name="payroll_advance_statements")
    op.drop_index("ix_payroll_advance_statements_rest_created", table_name="payroll_advance_statements")

    op.drop_index("ix_payroll_salary_results_period_user", table_name="payroll_salary_results")
    op.drop_index("ix_payroll_adjustments_responsible_date", table_name="payroll_adjustments")
    op.drop_index("ix_payroll_adjustments_rest_type_date_user", table_name="payroll_adjustments")

    op.drop_index("ix_users_role_id", table_name="users")
    op.drop_index("ix_users_company_fired", table_name="users")

    op.drop_index("ix_user_permissions_permission_id", table_name="user_permissions")
    op.drop_index("ix_role_permissions_permission_id", table_name="role_permissions")
    op.drop_index("ix_position_permissions_permission_id", table_name="position_permissions")

    op.drop_index("ix_user_restaurants_restaurant_id", table_name="user_restaurants")
