"""add checklists tables

Revision ID: b9c1d2e3f4a5
Revises: 5b7c8d9e0f12
Create Date: 2026-01-29 00:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b9c1d2e3f4a5"
down_revision = "5b7c8d9e0f12"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "checklists",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("is_scored", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "position_checklist_access",
        sa.Column("position_id", sa.Integer(), nullable=False),
        sa.Column("checklist_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["position_id"], ["positions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["checklist_id"], ["checklists.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("position_id", "checklist_id"),
    )

    op.create_table(
        "checklist_sections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("checklist_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(["checklist_id"], ["checklists.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "checklist_questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("checklist_id", sa.Integer(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("weight", sa.Integer(), nullable=True),
        sa.Column("require_photo", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("require_comment", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("section_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["checklist_id"], ["checklists.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["section_id"], ["checklist_sections.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "checklist_answers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("checklist_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("department", sa.String(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["checklist_id"], ["checklists.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_ca_ck_user_date", "checklist_answers", ["checklist_id", "user_id", "submitted_at"])

    op.create_table(
        "checklist_question_answers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("answer_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("response_value", sa.String(), nullable=True),
        sa.Column("comment", sa.String(), nullable=True),
        sa.Column("photo_path", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["answer_id"], ["checklist_answers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["checklist_questions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_cqa_answer_id", "checklist_question_answers", ["answer_id"])
    op.create_index("ix_cqa_question_id", "checklist_question_answers", ["question_id"])
    op.create_index("ix_cqa_answer_question", "checklist_question_answers", ["answer_id", "question_id"])

    op.create_table(
        "checklist_drafts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("checklist_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("department", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["checklist_id"], ["checklists.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "checklist_id", name="uq_cd_user_checklist"),
    )
    op.create_index("ix_cd_user", "checklist_drafts", ["user_id"])

    op.create_table(
        "checklist_draft_answers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("draft_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("response_value", sa.String(), nullable=True),
        sa.Column("comment", sa.String(), nullable=True),
        sa.Column("photo_path", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["draft_id"], ["checklist_drafts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["checklist_questions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("draft_id", "question_id", name="uq_cda_draft_question"),
    )
    op.create_index("ix_cda_draft_id", "checklist_draft_answers", ["draft_id"])
    op.create_index("ix_cda_question_id", "checklist_draft_answers", ["question_id"])


def downgrade() -> None:
    op.drop_index("ix_cda_question_id", table_name="checklist_draft_answers")
    op.drop_index("ix_cda_draft_id", table_name="checklist_draft_answers")
    op.drop_table("checklist_draft_answers")
    op.drop_index("ix_cd_user", table_name="checklist_drafts")
    op.drop_table("checklist_drafts")
    op.drop_index("ix_cqa_answer_question", table_name="checklist_question_answers")
    op.drop_index("ix_cqa_question_id", table_name="checklist_question_answers")
    op.drop_index("ix_cqa_answer_id", table_name="checklist_question_answers")
    op.drop_table("checklist_question_answers")
    op.drop_index("ix_ca_ck_user_date", table_name="checklist_answers")
    op.drop_table("checklist_answers")
    op.drop_table("checklist_questions")
    op.drop_table("checklist_sections")
    op.drop_table("position_checklist_access")
    op.drop_table("checklists")
