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
import threading
import types
from collections.abc import Callable
from typing import Any, Protocol

from django.db import connection
from django.db.backends.utils import CursorDebugWrapper

from sql_traceback.cursors import StacktraceCursorWrapper, StacktraceDebugCursorWrapper
from sql_traceback.traceback_info import TracebackCollector

__all__ = ["sql_traceback", "SqlTraceback"]


# Thread-local storage for active collector stack
_thread_local = threading.local()


def _get_active_collector() -> TracebackCollector | None:
    """Get the currently active TracebackCollector for this thread.

    Returns:
        The active TracebackCollector, or None if no context is active.
    """
    stack = getattr(_thread_local, "collector_stack", [])
    return stack[-1] if stack else None


def _push_collector(collector: TracebackCollector) -> None:
    """Push a new collector onto the stack for this thread.

    Args:
        collector: The TracebackCollector to push onto the stack.
    """
    if not hasattr(_thread_local, "collector_stack"):
        _thread_local.collector_stack = []
    _thread_local.collector_stack.append(collector)


def _pop_collector() -> None:
    """Pop the current collector from the stack for this thread."""
    if hasattr(_thread_local, "collector_stack") and _thread_local.collector_stack:
        _thread_local.collector_stack.pop()


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

    When used as a context manager (with the 'as' clause), returns a TracebackCollector that
    provides programmatic access to the executed queries and their stack frames.

    Note: When used as a decorator (via SqlTraceback), the collector is not accessible.
          Use the context manager form with 'as' to access query information.

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
        >>> # Access programmatic traceback information
        >>> with sql_traceback() as collector:
        >>>     User.objects.count()
        >>>     for query in collector.queries:
        >>>         print(f"SQL: {query.sql}")
        >>>         for frame in query.frames:
        >>>             print(f"  {frame.path}:{frame.line} in {frame.name}")
        >>>
        >>> # Use with tests and assertNumQueries
        >>> from django.test import TestCase
        >>>
        >>> class MyTest(TestCase):
        >>>     def test_something(self):
        >>>         with sql_traceback(), self.assertNumQueries(1):
        >>>             User.objects.first()
    """
    # Create a collector for this context
    collector = TracebackCollector()

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
        # Register collector as active for this thread (push onto stack)
        _push_collector(collector)

        # Apply cursor patch
        connection.cursor = cursor_with_stacktrace  # pyright: ignore[reportGeneralTypeIssues]
        yield collector
    finally:
        # Unregister collector (pop from stack)
        _pop_collector()

        # Restore original cursor method
        connection.cursor = original_cursor  # pyright: ignore[reportGeneralTypeIssues]


class SqlTraceback:
    """Class-based version of sql_traceback context manager.

    Can be used as a context manager or decorator. Provides the same functionality
    as the sql_traceback function but with a class-based interface.

    When used as a context manager, returns a TracebackCollector for programmatic access.
    When used as a decorator, the collector is not accessible to the decorated function.

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
        >>> # As context manager with programmatic access
        >>> with SqlTraceback() as collector:
        >>>     User.objects.all()
        >>>     print(collector.queries)
        >>>
        >>> # As decorator (no programmatic access)
        >>> @SqlTraceback()
        >>> def my_function():
        >>>     return User.objects.all()
    """

    def __init__(self):
        self._original_cursor: Callable[..., Any] | None = None
        self._collector: TracebackCollector | None = None

    def __enter__(self):
        # Create a collector for this context
        self._collector = TracebackCollector()

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

        # Register collector as active for this thread (push onto stack)
        _push_collector(self._collector)

        # Apply cursor patch
        connection.cursor = cursor_with_stacktrace  # pyright: ignore[reportGeneralTypeIssues]
        return self._collector

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> bool:
        # Restore original cursor method even if an exception occurred
        try:
            # Unregister collector (pop from stack)
            _pop_collector()

            if hasattr(self, "_original_cursor") and self._original_cursor is not None:
                connection.cursor = self._original_cursor  # pyright: ignore[reportGeneralTypeIssues]
        finally:
            # Always reset the stored reference
            self._original_cursor = None
            self._collector = None

        # Don't suppress exceptions
        return False

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """Allow SqlTraceback to be used as a decorator.

        Note: When used as a decorator, the TracebackCollector is not accessible
        to the decorated function. Use the context manager form if you need
        programmatic access to query information.
        """

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with self:
                return func(*args, **kwargs)

        return wrapper
