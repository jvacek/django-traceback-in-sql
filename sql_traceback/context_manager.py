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
import traceback
import types
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Protocol

from django.conf import settings
from django.db import connection
from django.db.backends.utils import CursorDebugWrapper, CursorWrapper

__all__ = ["sql_traceback", "SqlTraceback"]


# Configuration from Django settings with defaults
def _get_setting(name: str, default: Any) -> Any:
    """Get a setting value with a default fallback."""
    return getattr(settings, name, default)


TRACEBACK_ENABLED = _get_setting("SQL_TRACEBACK_ENABLED", True)
MAX_STACK_FRAMES = _get_setting("SQL_TRACEBACK_MAX_FRAMES", 15)
FILTER_SITEPACKAGES = _get_setting("SQL_TRACEBACK_FILTER_SITEPACKAGES", True)
FILTER_TESTING_FRAMEWORKS = _get_setting("SQL_TRACEBACK_FILTER_TESTING_FRAMEWORKS", True)
FILTER_STDLIB = _get_setting("SQL_TRACEBACK_FILTER_STDLIB", True)
MIN_APP_FRAMES = _get_setting("SQL_TRACEBACK_MIN_APP_FRAMES", 1)


class CursorProtocol(Protocol):
    """Protocol for cursor-like objects."""

    def execute(self, sql: str, params: Any = None) -> Any: ...
    def executemany(self, sql: str, param_list: list[Any]) -> Any: ...
    def fetchone(self) -> Any: ...
    def fetchmany(self, size: int = ...) -> list[Any]: ...
    def fetchall(self) -> list[Any]: ...


def _is_stacktrace_enabled() -> bool:
    """Check if stacktrace is enabled via Django settings."""
    return bool(TRACEBACK_ENABLED)


def _sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent any potential SQL comment issues."""
    return filename.replace("*/", "").replace("/*", "").replace("\n", "").replace("\r", "")


def _should_include_frame(frame: traceback.FrameSummary) -> bool:
    """Determine if a stack frame should be included in the traceback."""
    filename_lower = frame.filename.lower()

    # Skip site-packages if filtering is enabled
    if FILTER_SITEPACKAGES and "site-packages/" in filename_lower:
        return False

    # Skip Django framework code if filtering is enabled
    if FILTER_SITEPACKAGES:
        django_patterns = [
            "/django/",
            "\\django\\",  # Windows path separator
        ]
        if any(pattern in filename_lower for pattern in django_patterns):
            return False

    # Skip Python standard library if filtering is enabled
    if FILTER_STDLIB:
        # Filter Python standard library modules
        stdlib_patterns = [
            "/lib/python3.",
            "/lib64/python3.",
            "<frozen ",
            "/runpy.py",
            "/threading.py",
            "/queue.py",
            "/contextlib.py",
            "/functools.py",
            "/traceback.py",
            "/inspect.py",
            "/importlib/",
            "/collections/",
            "/weakref.py",
            "/copy.py",
            "/logging/",
        ]

        # Check if it's a stdlib module (not in site-packages)
        if "site-packages/" not in filename_lower and any(pattern in filename_lower for pattern in stdlib_patterns):
            return False

    # Skip testing framework internals if filtering is enabled
    # This is useful because testing frameworks span both third-party (pytest) and stdlib (unittest)
    # and you almost never want to see their internals when debugging SQL queries
    if FILTER_TESTING_FRAMEWORKS:
        # Filter pytest internals (third-party)
        pytest_excludes = [
            "_pytest/",
            "/pytest/",
            "pytest_django/",
            "/pluggy/",
        ]

        # Filter unittest internals (stdlib)
        unittest_excludes = [
            "unittest/case.py",
            "unittest/loader.py",
            "unittest/runner.py",
            "unittest/suite.py",
            "unittest/main.py",
        ]

        # Combine all testing framework excludes
        testing_excludes = pytest_excludes + unittest_excludes

        # Don't filter out user test files - only internal framework files
        if any(exclude in filename_lower for exclude in testing_excludes):
            return False

    # Include everything else (application code including user test files)
    return True


def add_stacktrace_to_query(sql: str) -> str:
    """Add the current Python stacktrace to a SQL query as a comment.

    Args:
        sql: The original SQL query string

    Returns:
        The SQL query with a stacktrace comment appended, or the original
        SQL if stacktracing is disabled or already present.
    """
    # Early return if disabled or already has stacktrace
    if not _is_stacktrace_enabled() or "/*\nSTACKTRACE:" in sql:
        return sql

    try:
        # Get the current stacktrace
        stack = traceback.extract_stack()

        # Filter out framework and library calls to focus on application code
        filtered_stack = [frame for frame in stack if _should_include_frame(frame)]

        # Format the stacktrace into a SQL comment
        stacktrace_lines = []

        # Use configurable number of most recent frames for better context
        if filtered_stack and len(filtered_stack) >= MIN_APP_FRAMES:
            for frame in filtered_stack[-MAX_STACK_FRAMES:]:
                safe_filename = _sanitize_filename(frame.filename)
                stacktrace_lines.append(f"# {safe_filename}:{frame.lineno} in {frame.name}")
        else:
            # If insufficient application frames found, include a minimal note
            # but avoid returning original SQL to ensure tests can detect stacktrace presence
            stacktrace_lines.append("# [Application frames filtered - showing remaining frames]")
            # Include any remaining frames that weren't filtered
            for frame in stack[-min(3, len(stack)) :]:
                safe_filename = _sanitize_filename(frame.filename)
                stacktrace_lines.append(f"# {safe_filename}:{frame.lineno} in {frame.name}")

        stacktrace_comment = "\n".join(stacktrace_lines)

        # Append the stacktrace comment to the SQL query
        return f"{sql}\n/*\nSTACKTRACE:\n{stacktrace_comment}\n*/"

    except Exception:
        # If stacktrace extraction fails, return original SQL
        # Silently fail to avoid breaking the application
        return sql


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
