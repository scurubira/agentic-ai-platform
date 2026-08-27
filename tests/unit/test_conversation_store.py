from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine

from platform_core.memory.store import InMemoryConversationStore, PostgresConversationStore


class MutableClock:
    def __init__(self, current: datetime) -> None:
        self.current = current

    def __call__(self) -> datetime:
        return self.current


def test_in_memory_store_removes_conversation_after_24_hours() -> None:
    clock = MutableClock(datetime(2026, 8, 26, 12, tzinfo=UTC))
    store = InMemoryConversationStore(retention=timedelta(hours=24), clock=clock)
    store.save_turn("session", user_message="Olá", assistant_message="Oi")

    clock.current += timedelta(hours=24)

    assert store.load_messages("session") == []


def test_in_memory_store_keeps_conversation_before_24_hours() -> None:
    clock = MutableClock(datetime(2026, 8, 26, 12, tzinfo=UTC))
    store = InMemoryConversationStore(retention=timedelta(hours=24), clock=clock)
    store.save_turn("session", user_message="Olá", assistant_message="Oi")

    clock.current += timedelta(hours=23, minutes=59)

    assert store.load_messages("session") == [
        {"role": "user", "content": "Olá"},
        {"role": "assistant", "content": "Oi"},
    ]


def test_database_store_removes_conversation_after_24_hours() -> None:
    clock = MutableClock(datetime(2026, 8, 26, 12, tzinfo=UTC))
    store = PostgresConversationStore(
        engine=create_engine("sqlite://", future=True),
        retention=timedelta(hours=24),
        clock=clock,
    )
    store.create_tables()
    store.save_turn("session", user_message="Olá", assistant_message="Oi")

    clock.current += timedelta(hours=24)

    assert store.load_messages("session") == []
