from __future__ import annotations

import re
from typing import Any

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

from platform_core.errors import AppError

_FORBIDDEN_SQL_PATTERN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|comment|merge|copy)\b",
    re.IGNORECASE,
)


class DatabaseMCPServer:
    def __init__(self, database_url: str) -> None:
        self._engine: Engine = create_engine(database_url, future=True, pool_pre_ping=True)

    def list_tables(self) -> list[str]:
        return sorted(inspect(self._engine).get_table_names())

    def describe_table(self, table_name: str) -> list[dict[str, Any]]:
        return [dict(column) for column in inspect(self._engine).get_columns(table_name)]

    def execute_readonly_query(self, query: str) -> list[dict[str, Any]]:
        normalized_query = query.strip().strip(";")
        lowered = normalized_query.lower()
        if not (lowered.startswith("select") or lowered.startswith("with")):
            raise AppError("Only SELECT and WITH queries are allowed", status_code=400)
        if _FORBIDDEN_SQL_PATTERN.search(lowered):
            raise AppError("Only read-only SQL is allowed", status_code=400)
        with self._engine.begin() as connection:
            return [dict(row) for row in connection.execute(text(normalized_query)).mappings().all()]
