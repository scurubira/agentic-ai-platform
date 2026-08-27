from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Callable, Protocol

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    delete,
    select,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Connection, Engine


class ConversationStore(Protocol):
    def load_messages(self, session_id: str) -> list[dict[str, str]]: ...

    def save_turn(self, session_id: str, *, user_message: str, assistant_message: str) -> None: ...


def _utc_now() -> datetime:
    return datetime.now(UTC)


class InMemoryConversationStore:
    def __init__(
        self,
        *,
        retention: timedelta = timedelta(days=1),
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._retention = retention
        self._clock = clock
        self._store: dict[str, list[tuple[datetime, dict[str, str]]]] = {}

    def _purge_expired(self) -> None:
        cutoff = self._clock() - self._retention
        for session_id, messages in list(self._store.items()):
            retained = [(created_at, message) for created_at, message in messages if created_at > cutoff]
            if retained:
                self._store[session_id] = retained
            else:
                del self._store[session_id]

    def load_messages(self, session_id: str) -> list[dict[str, str]]:
        self._purge_expired()
        return [dict(message) for _, message in self._store.get(session_id, [])]

    def save_turn(self, session_id: str, *, user_message: str, assistant_message: str) -> None:
        self._purge_expired()
        now = self._clock()
        self._store.setdefault(session_id, []).extend(
            [
                (now, {"role": "user", "content": user_message}),
                (now, {"role": "assistant", "content": assistant_message}),
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
    retention: timedelta = timedelta(days=1)
    clock: Callable[[], datetime] = field(default=_utc_now, repr=False)

    @classmethod
    def from_url(
        cls,
        database_url: str,
        *,
        retention: timedelta = timedelta(days=1),
    ) -> "PostgresConversationStore":
        return cls(engine=create_engine(database_url, future=True, pool_pre_ping=True), retention=retention)

    def create_tables(self) -> None:
        metadata.create_all(self.engine)

    def load_messages(self, session_id: str) -> list[dict[str, str]]:
        query = (
            select(messages_table.c.role, messages_table.c.content)
            .where(messages_table.c.session_id == session_id)
            .order_by(messages_table.c.id.asc())
        )
        with self.engine.begin() as connection:
            self._purge_expired(connection)
            return [
                {"role": str(row.role), "content": str(row.content)}
                for row in connection.execute(query).mappings().all()
            ]

    def save_turn(self, session_id: str, *, user_message: str, assistant_message: str) -> None:
        now = self.clock()
        with self.engine.begin() as connection:
            self._purge_expired(connection)
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

    def _purge_expired(self, connection: Connection) -> None:
        cutoff = self.clock() - self.retention
        connection.execute(delete(messages_table).where(messages_table.c.created_at <= cutoff))
        connection.execute(delete(sessions_table).where(sessions_table.c.updated_at <= cutoff))
