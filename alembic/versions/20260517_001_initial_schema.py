"""Initial services and incidents schema.

Revision ID: 001
Revises:
Create Date: 2026-05-17

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "services",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "environment",
            sa.Enum(
                "production",
                "staging",
                "development",
                name="environment",
            ),
            nullable=False,
        ),
        sa.Column("heartbeat_interval", sa.Integer(), nullable=False),
        sa.Column("grace_period", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("HEALTHY", "UNHEALTHY", "PAUSED", name="servicestatus"),
            nullable=False,
        ),
        sa.Column("last_ping_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "environment", name="uq_service_name_environment"),
    )
    op.create_index(op.f("ix_services_environment"), "services", ["environment"], unique=False)
    op.create_index(
        "ix_services_environment_status",
        "services",
        ["environment", "status"],
        unique=False,
    )
    op.create_index(op.f("ix_services_last_ping_at"), "services", ["last_ping_at"], unique=False)
    op.create_index(op.f("ix_services_name"), "services", ["name"], unique=False)
    op.create_index(op.f("ix_services_status"), "services", ["status"], unique=False)

    op.create_table(
        "incidents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("service_id", sa.Uuid(), nullable=False),
        sa.Column(
            "triggered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("escalation_level", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_incidents_resolved_at"), "incidents", ["resolved_at"], unique=False)
    op.create_index(
        "ix_incidents_service_open",
        "incidents",
        ["service_id", "resolved_at"],
        unique=False,
    )
    op.create_index(op.f("ix_incidents_service_id"), "incidents", ["service_id"], unique=False)
    op.create_index(op.f("ix_incidents_triggered_at"), "incidents", ["triggered_at"], unique=False)


def downgrade() -> None:
    op.drop_table("incidents")
    op.drop_table("services")
    op.execute("DROP TYPE IF EXISTS servicestatus")
    op.execute("DROP TYPE IF EXISTS environment")
