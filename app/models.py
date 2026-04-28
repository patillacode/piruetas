from datetime import UTC, datetime
from datetime import date as date_type

from sqlmodel import Field, SQLModel, UniqueConstraint


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    hashed_password: str
    is_admin: bool = Field(default=False)
    session_version: int = Field(default=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Entry(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    date: date_type = Field(index=True)
    content: str = Field(default="")
    word_count: int = Field(default=0)
    share_token: str | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    __table_args__ = (UniqueConstraint("user_id", "date"),)


class Image(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    entry_id: int | None = Field(default=None, foreign_key="entry.id")
    user_id: int = Field(foreign_key="user.id")
    filename: str
    original_name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RecoveryCode(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    code_hash: str
    used: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
