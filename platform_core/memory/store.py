from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, MetaData, String, Table, create_engine, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine


class ConversationStore(Protocol):
    def load_messages(self, session_id: str) -> list[dict[str, str]]: ...

    def save_turn(self, session_id: str, *, user_message: str, assistant_message: str) -> None: ...


class InMemoryConversationStore:
    def __init__(self) -> None:
        self._store: dict[str, list[dict[str, str]]] = {}

    def load_messages(self, session_id: str) -> list[dict[str, str]]:
        return list(self._store.get(session_id, []))

    def save_turn(self, session_id: str, *, user_message: str, assistant_message: str) -> None:
        self._store.setdefault(session_id, []).extend(
            [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_message},
            ]
        )


metadata = MetaData()

sessions_table = Table(
    "sessions",
    metadata,
    Column("id", String(128), primary_key=True),
    Column("created_at", DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False),
    Column("updated_at", DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False),
)

messages_table = Table(
    "messages",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("session_id", ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
    Column("role", String(32), nullable=False),
    Column("content", String, nullable=False),
    Column("metadata", JSON, default=dict, nullable=False),
    Column("created_at", DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False),
)


@dataclass
class PostgresConversationStore:
    engine: Engine

    @classmethod
    def from_url(cls, database_url: str) -> "PostgresConversationStore":
        return cls(engine=create_engine(database_url, future=True, pool_pre_ping=True))

    def create_tables(self) -> None:
        metadata.create_all(self.engine)

    def load_messages(self, session_id: str) -> list[dict[str, str]]:
        query = (
            select(messages_table.c.role, messages_table.c.content)
            .where(messages_table.c.session_id == session_id)
            .order_by(messages_table.c.id.asc())
        )
        with self.engine.begin() as connection:
            return [
                {"role": str(row.role), "content": str(row.content)}
                for row in connection.execute(query).mappings().all()
            ]

    def save_turn(self, session_id: str, *, user_message: str, assistant_message: str) -> None:
        now = datetime.now(UTC)
        with self.engine.begin() as connection:
            connection.execute(
                pg_insert(sessions_table)
                .values(id=session_id, created_at=now, updated_at=now)
                .on_conflict_do_nothing(index_elements=[sessions_table.c.id]),
            )
            connection.execute(sessions_table.update().where(sessions_table.c.id == session_id).values(updated_at=now))
            connection.execute(
                messages_table.insert(),
                [
                    {
                        "session_id": session_id,
                        "role": "user",
                        "content": user_message,
                        "metadata": {},
                        "created_at": now,
                    },
                    {
                        "session_id": session_id,
                        "role": "assistant",
                        "content": assistant_message,
                        "metadata": {},
                        "created_at": now,
                    },
                ],
            )
