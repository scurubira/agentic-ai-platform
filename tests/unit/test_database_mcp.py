from __future__ import annotations

import pytest

from mcp_servers.database.server import ensure_read_only_query
from platform_core.errors import AppError


def test_read_only_query_allows_keywords_inside_string_literals() -> None:
    query = "SELECT * FROM prompts WHERE content = 'insert coin to update state';"

    normalized = ensure_read_only_query(query)

    assert normalized == "SELECT * FROM prompts WHERE content = 'insert coin to update state'"


def test_read_only_query_rejects_non_select_statements() -> None:
    with pytest.raises(AppError, match="Only SELECT and WITH queries are allowed"):
        ensure_read_only_query("DELETE FROM prompts")
