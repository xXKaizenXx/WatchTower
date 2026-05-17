from datetime import UTC, datetime

from sqlalchemy import func
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(UTC)


class TimestampMixin(SQLModel):
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column_kwargs={"server_default": func.now()},
        nullable=False,
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()},
        nullable=False,
    )
