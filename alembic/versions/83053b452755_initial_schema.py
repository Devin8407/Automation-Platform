"""initial schema

Revision ID: 83053b452755
Revises:
Create Date: 2026-08-12 15:32:24.279175

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "83053b452755"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# PostgreSQL enum types.
workflow_status = postgresql.ENUM(
    "RUNNING",
    "COMPLETED",
    "FAILED",
    "CANCELLED",
    name="workflowstatus",
    create_type=False,
)

task_status = postgresql.ENUM(
    "PENDING",
    "RUNNING",
    "COMPLETED",
    "FAILED",
    "CANCELLED",
    name="taskstatus",
    create_type=False,
)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    # Create PostgreSQL enum types explicitly so their lifecycle is
    # deterministic across upgrade/downgrade operations.
    workflow_status.create(bind, checkfirst=True)
    task_status.create(bind, checkfirst=True)

    op.create_table(
        "workflow_definitions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "task_definitions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workflow_definition_id", sa.UUID(), nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("plugin_type", sa.String(), nullable=False),
        sa.Column(
            "configuration",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("max_tries", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["workflow_definition_id"],
            ["workflow_definitions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workflow_definition_id",
            "key",
            name="uq_task_definition_workflow_key",
        ),
    )

    op.create_index(
        op.f("ix_task_definitions_workflow_definition_id"),
        "task_definitions",
        ["workflow_definition_id"],
        unique=False,
    )

    op.create_table(
        "trigger_definitions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workflow_definition_id", sa.UUID(), nullable=False),
        sa.Column("plugin_type", sa.String(), nullable=False),
        sa.Column(
            "configuration",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["workflow_definition_id"],
            ["workflow_definitions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_trigger_definitions_workflow_definition_id"),
        "trigger_definitions",
        ["workflow_definition_id"],
        unique=False,
    )

    op.create_table(
        "workflow_executions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "workflow_definition_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "status",
            workflow_status,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["workflow_definition_id"],
            ["workflow_definitions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_workflow_executions_workflow_definition_id"),
        "workflow_executions",
        ["workflow_definition_id"],
        unique=False,
    )

    op.create_table(
        "chronological_trigger_state",
        sa.Column(
            "trigger_definition_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "next_run_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["trigger_definition_id"],
            ["trigger_definitions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("trigger_definition_id"),
    )

    op.create_index(
        op.f("ix_chronological_trigger_state_next_run_at"),
        "chronological_trigger_state",
        ["next_run_at"],
        unique=False,
    )

    op.create_table(
        "task_definition_dependencies",
        sa.Column(
            "task_definition_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "depends_on_task_definition_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["depends_on_task_definition_id"],
            ["task_definitions.id"],
        ),
        sa.ForeignKeyConstraint(
            ["task_definition_id"],
            ["task_definitions.id"],
        ),
        sa.PrimaryKeyConstraint(
            "task_definition_id",
            "depends_on_task_definition_id",
        ),
    )

    op.create_table(
        "task_executions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "workflow_execution_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "task_definition_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("plugin_type", sa.String(), nullable=False),
        sa.Column(
            "configuration",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "status",
            task_status,
            nullable=False,
        ),
        sa.Column(
            "remaining_dependencies",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "parent_task_ids",
            postgresql.ARRAY(sa.UUID()),
            nullable=False,
        ),
        sa.Column(
            "child_task_ids",
            postgresql.ARRAY(sa.UUID()),
            nullable=False,
        ),
        sa.Column(
            "remaining_tries",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "output",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "error_message",
            sa.String(),
            nullable=True,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["task_definition_id"],
            ["task_definitions.id"],
        ),
        sa.ForeignKeyConstraint(
            ["workflow_execution_id"],
            ["workflow_executions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_task_executions_task_definition_id"),
        "task_executions",
        ["task_definition_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_task_executions_workflow_execution_id"),
        "task_executions",
        ["workflow_execution_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index(
        op.f("ix_task_executions_workflow_execution_id"),
        table_name="task_executions",
    )
    op.drop_index(
        op.f("ix_task_executions_task_definition_id"),
        table_name="task_executions",
    )
    op.drop_table("task_executions")

    op.drop_table("task_definition_dependencies")

    op.drop_index(
        op.f("ix_chronological_trigger_state_next_run_at"),
        table_name="chronological_trigger_state",
    )
    op.drop_table("chronological_trigger_state")

    op.drop_index(
        op.f("ix_workflow_executions_workflow_definition_id"),
        table_name="workflow_executions",
    )
    op.drop_table("workflow_executions")

    op.drop_index(
        op.f("ix_trigger_definitions_workflow_definition_id"),
        table_name="trigger_definitions",
    )
    op.drop_table("trigger_definitions")

    op.drop_index(
        op.f("ix_task_definitions_workflow_definition_id"),
        table_name="task_definitions",
    )
    op.drop_table("task_definitions")

    op.drop_table("workflow_definitions")

    # Drop the PostgreSQL enum types after all dependent columns are gone.
    bind = op.get_bind()
    task_status.drop(bind, checkfirst=True)
    workflow_status.drop(bind, checkfirst=True)
