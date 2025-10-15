"""SQL stacktrace context manager for debugging Django SQL queries.

This module provides a context manager that adds Python stacktraces
to SQL queries as comments, making it easier to trace where queries
originate from in the application code. Useful for debugging N+1 query
issues and other SQL performance problems.

Example:
    from sql_traceback import sql_traceback

    with sql_traceback():
        # Any SQL queries here will have stacktraces added
        users = User.objects.filter(is_active=True)

    # The generated SQL will include a comment like:
    # SELECT * FROM users WHERE is_active = true
    # /*
    # STACKTRACE:
    # # /app/views.py:25 in get_active_users
    # # /app/services/user_service.py:42 in fetch_users
    # */

Configuration in settings.py:
    SQL_TRACEBACK_ENABLED = True  # Enable/disable stacktracing (default: True)
    SQL_TRACEBACK_MAX_FRAMES = 15  # Max number of stack frames (default: 15)
    SQL_TRACEBACK_FILTER_SITEPACKAGES = True  # Filter out third-party packages (including django) (default: True)
    SQL_TRACEBACK_FILTER_TESTING_FRAMEWORKS = True  # Filter out pytest/unittest frames (default: True)
    SQL_TRACEBACK_FILTER_STDLIB = True  # Filter out Python standard library frames (default: True)
    SQL_TRACEBACK_MIN_APP_FRAMES = 1  # Minimum application frames required (default: 1)
"""

import contextlib
import functools
import types
from collections.abc import Callable
from typing import Any, Protocol

from django.db import connection
from django.db.backends.utils import CursorDebugWrapper

from sql_traceback.cursors import StacktraceCursorWrapper, StacktraceDebugCursorWrapper

__all__ = ["sql_traceback", "SqlTraceback"]


class CursorProtocol(Protocol):
    """Protocol for cursor-like objects."""

    def execute(self, sql: str, params: Any = None) -> Any: ...
    def executemany(self, sql: str, param_list: list[Any]) -> Any: ...
    def fetchone(self) -> Any: ...
    def fetchmany(self, size: int = ...) -> list[Any]: ...
    def fetchall(self) -> list[Any]: ...


@contextlib.contextmanager
def sql_traceback():
    """Context manager that adds Python stacktraces to SQL queries.

    This helps with debugging by making it easier to trace where SQL queries originate from
    in the application code. Works with both direct SQL execution and ORM queries.

    Django Settings:
        SQL_TRACEBACK_ENABLED: Enable/disable stacktracing (default: True)
        SQL_TRACEBACK_MAX_FRAMES: Max number of stack frames to include (default: 15)
        SQL_TRACEBACK_FILTER_SITEPACKAGES: Filter out third-party packages (including Django) (default: True)
        SQL_TRACEBACK_FILTER_TESTING_FRAMEWORKS: Filter out pytest/unittest frames (default: True)
        SQL_TRACEBACK_FILTER_STDLIB: Filter out Python standard library frames (default: True)
        SQL_TRACEBACK_MIN_APP_FRAMES: Minimum application frames required (default: 1)

    Examples:
        >>> from sql_traceback import sql_traceback
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

    Can be used as a context manager or decorator. Provides the same functionality
    as the sql_traceback function but with a class-based interface.

    Django Settings:
        SQL_TRACEBACK_ENABLED: Enable/disable stacktracing (default: True)
        SQL_TRACEBACK_MAX_FRAMES: Max number of stack frames to include (default: 15)
        SQL_TRACEBACK_FILTER_SITEPACKAGES: Filter out third-party packages (including Django) (default: True)
        SQL_TRACEBACK_FILTER_TESTING_FRAMEWORKS: Filter out pytest/unittest frames (default: True)
        SQL_TRACEBACK_FILTER_STDLIB: Filter out Python standard library frames (default: True)
        SQL_TRACEBACK_MIN_APP_FRAMES: Minimum application frames required (default: 1)

    Examples:
        >>> from sql_traceback import SqlTraceback
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
        # Restore original cursor method even if an exception occurred
        try:
            if hasattr(self, "_original_cursor") and self._original_cursor is not None:
                connection.cursor = self._original_cursor  # pyright: ignore[reportGeneralTypeIssues]
        finally:
            # Always reset the stored reference
            self._original_cursor = None

        # Don't suppress exceptions
        return False

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """Allow SqlTraceback to be used as a decorator."""

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with self:
                return func(*args, **kwargs)

        return wrapper
