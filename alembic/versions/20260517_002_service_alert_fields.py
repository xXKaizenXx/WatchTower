"""Add ping token and per-service alert configuration.

Revision ID: 002
Revises: 001
Create Date: 2026-05-17

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "services",
        sa.Column("ping_token_hash", sa.String(length=64), nullable=True),
    )
    op.add_column("services", sa.Column("webhook_url", sa.String(length=2048), nullable=True))
    op.add_column("services", sa.Column("sms_phone", sa.String(length=32), nullable=True))
    op.add_column(
        "services",
        sa.Column("enable_sms_alerts", sa.Boolean(), server_default="false", nullable=False),
    )
    op.execute(
        "UPDATE services SET ping_token_hash = "
        "'0000000000000000000000000000000000000000000000000000000000000000' "
        "WHERE ping_token_hash IS NULL"
    )
    op.alter_column("services", "ping_token_hash", nullable=False)


def downgrade() -> None:
    op.drop_column("services", "enable_sms_alerts")
    op.drop_column("services", "sms_phone")
    op.drop_column("services", "webhook_url")
    op.drop_column("services", "ping_token_hash")
