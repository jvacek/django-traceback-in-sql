from collections.abc import Mapping, Sequence
from typing import Any

from django.db.backends.utils import CursorDebugWrapper, CursorWrapper

from sql_traceback.collector_registry import get_active_collector
from sql_traceback.parser import add_stacktrace_to_query


def _execute_with_stacktrace(execute_fn: Any, sql: str, *args: Any, **kwargs: Any) -> Any:
    """Execute SQL with stacktrace tracking.

    Args:
        execute_fn: The parent class's execute/executemany method
        sql: The SQL query to execute
        *args: Additional arguments to pass to execute_fn
        **kwargs: Additional keyword arguments to pass to execute_fn

    Returns:
        Result from execute_fn
    """
    modified_sql, frames = add_stacktrace_to_query(sql)

    # Register query with collector if one is active
    collector = get_active_collector()
    if collector and frames:
        collector.add_query(modified_sql, frames)

    return execute_fn(modified_sql, *args, **kwargs)


class StacktraceCursorWrapper(CursorWrapper):
    """A cursor wrapper that adds stacktrace comments to executed SQL queries."""

    def __init__(self, cursor: Any, db: Any) -> None:
        super().__init__(cursor, db)  # pyright: ignore[reportArgumentType]

    def execute(self, sql: str, params: Any = None) -> Any:
        return _execute_with_stacktrace(super().execute, sql, params)

    def executemany(self, sql: str, param_list: Sequence[Sequence[Any] | Mapping[str, Any] | None]) -> Any:
        return _execute_with_stacktrace(super().executemany, sql, param_list)


class StacktraceDebugCursorWrapper(CursorDebugWrapper):
    """A debug cursor wrapper that adds stacktrace comments to executed SQL queries."""

    def __init__(self, cursor: Any, db: Any) -> None:
        super().__init__(cursor, db)  # pyright: ignore[reportArgumentType]

    def execute(self, sql: str, params: Any = None) -> Any:
        return _execute_with_stacktrace(super().execute, sql, params)

    def executemany(self, sql: str, param_list: Sequence[Sequence[Any] | Mapping[str, Any] | None]) -> Any:
        return _execute_with_stacktrace(super().executemany, sql, param_list)
