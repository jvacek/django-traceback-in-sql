"""SQL stacktrace context manager for debugging Django SQL queries.

This module provides a context manager that adds Python stacktraces
to SQL queries as comments, making it easier to trace where queries
originate from in the application code. Useful for debugging N+1 query
issues and other SQL performance problems.

Example:
    from common.sql_traceback import sql_traceback

    with sql_traceback():
        # Any SQL queries here will have stacktraces added
        users = User.objects.filter(is_active=True)
"""

import contextlib
import functools
import os
import traceback
import types
from collections.abc import Callable
from typing import Any, Protocol, TypeVar

from django.db import connection
from django.db.backends.utils import CursorDebugWrapper, CursorWrapper

__all__ = ["sql_traceback", "SqlTraceback"]

# Default values for environment flags
DEFAULT_ENABLE_SQL_TRACEBACK = "1"
DEFAULT_PRINT_SQL_TRACEBACKS = "0"

# Flag to enable printing stacktraces to stderr during tests (default: disabled)
PRINT_SQL_TRACEBACKS = os.environ.get("PRINT_SQL_TRACEBACKS", DEFAULT_PRINT_SQL_TRACEBACKS).lower() in (
    "1",
    "true",
    "yes",
    "y",
)

# Type variables for better type hints
T = TypeVar("T")
ExecuteFunc = Callable[[str, Any, bool, dict[str, Any]], Any]


class CursorProtocol(Protocol):
    """Protocol for cursor-like objects."""

    def execute(self, sql: str, params: Any = None) -> Any: ...
    def executemany(self, sql: str, param_list: list[Any]) -> Any: ...
    def fetchone(self) -> Any: ...
    def fetchmany(self, size: int = ...) -> list[Any]: ...
    def fetchall(self) -> list[Any]: ...


def add_stacktrace_to_query(sql: str) -> str:
    """Add the current Python stacktrace to a SQL query as a comment.

    Args:
        sql: The original SQL query string

    Returns:
        The SQL query with a stacktrace comment appended
    """
    # Check environment variable at runtime to allow test patching
    enable_stacktrace = os.environ.get("ENABLE_SQL_TRACEBACK", DEFAULT_ENABLE_SQL_TRACEBACK).lower() in (
        "1",
        "true",
        "yes",
    )

    # Skip if disabled
    if not enable_stacktrace:
        return sql

    # Check if the SQL already has a stacktrace to avoid adding it twice
    if "/*\nSTACKTRACE:" in sql:
        return sql

    # Get the current stacktrace
    stack = traceback.extract_stack()

    # Filter out framework and library calls to focus on application code
    filtered_stack = []
    for frame in stack:
        # Skip common framework files
        if any(
            exclude in frame.filename.lower()
            for exclude in [
                "django/db/",
                "django/core/",
                "django/contrib/",
                "site-packages/",
                "/lib/python",
                "middleware.py",
                "/db.py",
            ]
        ):
            continue

        # Include application code and test files
        if (
            "test_" in frame.filename
            or "/usermanagement/" in frame.filename
            or not any(exclude in frame.filename.lower() for exclude in ["django", "site-packages"])
        ):
            filtered_stack.append(frame)

    # Format the stacktrace into a SQL comment
    stacktrace_lines = []

    # Use a more compact format for the stacktrace
    if filtered_stack:
        # Take up to 15 most recent frames for better context
        for frame in filtered_stack[-15:]:
            stacktrace_lines.append(f"# {frame.filename}:{frame.lineno} in {frame.name}")
    else:
        # If no application frames found, add a note
        stacktrace_lines.append("# [No application frames found in stacktrace]")

    stacktrace_comment = "\n".join(stacktrace_lines)

    # Append the stacktrace comment to the SQL query
    return f"{sql}\n/*\nSTACKTRACE:\n{stacktrace_comment}\n*/;"


class StacktraceCursorWrapper(CursorWrapper):
    """A cursor wrapper that adds stacktrace comments to executed SQL queries."""

    def __init__(self, cursor: Any, db: Any) -> None:
        super().__init__(cursor, db)  # pyright: ignore[reportArgumentType]

    def execute(self, sql: str, params: Any = None) -> Any:
        sql = add_stacktrace_to_query(sql)
        return super().execute(sql, params)

    def executemany(self, sql: str, param_list: list[Any]) -> Any:
        sql = add_stacktrace_to_query(sql)
        return super().executemany(sql, param_list)


class StacktraceDebugCursorWrapper(CursorDebugWrapper):
    """A debug cursor wrapper that adds stacktrace comments to executed SQL queries."""

    def __init__(self, cursor: Any, db: Any) -> None:
        super().__init__(cursor, db)  # pyright: ignore[reportArgumentType]

    def execute(self, sql: str, params: Any = None) -> Any:
        modified_sql = add_stacktrace_to_query(sql)
        return super().execute(modified_sql, params)

    def executemany(self, sql: str, param_list: list[Any]) -> Any:
        sql = add_stacktrace_to_query(sql)
        return super().executemany(sql, param_list)


@contextlib.contextmanager
def sql_traceback():
    """Context manager that adds Python stacktraces to SQL queries.

    This helps with debugging by making it easier to trace where SQL queries originate from
    in the application code. Works with both direct SQL execution and ORM queries.

    Examples:
        >>> from common.sql_traceback import sql_traceback
        >>>
        >>> # Use with ORM queries
        >>> with sql_traceback():
        >>>     users = User.objects.filter(is_active=True)
        >>>
        >>> # Use with tests and assertNumQueries
        >>> from django.test import TestCase
        >>>
        >>> class MyTest(TestCase):
        >>>     def test_something(self):
        >>>         with sql_traceback(), self.assertNumQueries(1):
        >>>             User.objects.first()
    """
    # Save original cursor method
    original_cursor = connection.cursor

    # Define patched cursor method
    @functools.wraps(original_cursor)
    def cursor_with_stacktrace(*args: Any, **kwargs: Any) -> Any:
        cursor = original_cursor(*args, **kwargs)

        # If Django is in debug mode, it will use CursorDebugWrapper
        if isinstance(cursor, CursorDebugWrapper):
            return StacktraceDebugCursorWrapper(cursor.cursor, cursor.db)
        return StacktraceCursorWrapper(cursor, connection)

    try:
        # Apply cursor patch
        connection.cursor = cursor_with_stacktrace  # pyright: ignore[reportGeneralTypeIssues]
        yield
    finally:
        # Restore original cursor method
        connection.cursor = original_cursor  # pyright: ignore[reportGeneralTypeIssues]


class SqlTraceback:
    """Class-based version of sql_traceback context manager.

    Can be used as a context manager or decorator.

    Examples:
        >>> from common.sql_traceback import SqlTraceback
        >>>
        >>> # As context manager
        >>> with SqlTraceback():
        >>>     User.objects.all()
        >>>
        >>> # As decorator
        >>> @SqlTraceback()
        >>> def my_function():
        >>>     return User.objects.all()
    """

    def __init__(self):
        self._original_cursor: Callable[..., Any] | None = None

    def __enter__(self):
        # Save original cursor method
        self._original_cursor = connection.cursor

        # Define patched cursor method
        @functools.wraps(self._original_cursor)
        def cursor_with_stacktrace(*args: Any, **kwargs: Any) -> Any:
            if self._original_cursor is None:
                return connection.cursor(*args, **kwargs)

            cursor = self._original_cursor(*args, **kwargs)

            # If Django is in debug mode, it will use CursorDebugWrapper
            if isinstance(cursor, CursorDebugWrapper):
                return StacktraceDebugCursorWrapper(cursor.cursor, cursor.db)
            return StacktraceCursorWrapper(cursor, connection)

        # Apply cursor patch
        connection.cursor = cursor_with_stacktrace  # pyright: ignore[reportGeneralTypeIssues]
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> bool:
        # Restore original cursor method
        if self._original_cursor is not None:
            connection.cursor = self._original_cursor  # pyright: ignore[reportGeneralTypeIssues]
            self._original_cursor = None

        # Don't suppress exceptions
        return False

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with self:
                return func(*args, **kwargs)

        return wrapper
