from collections.abc import Mapping, Sequence
from typing import Any

from django.db.backends.utils import CursorDebugWrapper, CursorWrapper
from sql_traceback.parser import add_stacktrace_to_query


class StacktraceCursorWrapper(CursorWrapper):
    """A cursor wrapper that adds stacktrace comments to executed SQL queries."""

    def __init__(self, cursor: Any, db: Any) -> None:
        super().__init__(cursor, db)  # pyright: ignore[reportArgumentType]

    def execute(self, sql: str, params: Any = None) -> Any:
        modified_sql = add_stacktrace_to_query(sql)
        return super().execute(modified_sql, params)

    def executemany(self, sql: str, param_list: Sequence[Sequence[Any] | Mapping[str, Any] | None]) -> Any:
        modified_sql = add_stacktrace_to_query(sql)
        return super().executemany(modified_sql, param_list)


class StacktraceDebugCursorWrapper(CursorDebugWrapper):
    """A debug cursor wrapper that adds stacktrace comments to executed SQL queries."""

    def __init__(self, cursor: Any, db: Any) -> None:
        super().__init__(cursor, db)  # pyright: ignore[reportArgumentType]

    def execute(self, sql: str, params: Any = None) -> Any:
        modified_sql = add_stacktrace_to_query(sql)
        return super().execute(modified_sql, params)

    def executemany(self, sql: str, param_list: Sequence[Sequence[Any] | Mapping[str, Any] | None]) -> Any:
        modified_sql = add_stacktrace_to_query(sql)
        return super().executemany(modified_sql, param_list)
