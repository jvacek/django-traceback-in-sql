"""Tests for programmatic access to traceback information.

This module tests the TracebackCollector and related functionality for
accessing stack frames and query information programmatically.
"""

import threading

import pytest
from django.contrib.auth.models import User

from sql_traceback import QueryInfo, StackFrame, TracebackCollector, sql_traceback

pytestmark = pytest.mark.django_db


def test_basic_frame_access():
    """Test basic access to stack frames from a single query."""
    with sql_traceback() as collector:
        User.objects.count()

    # Should have exactly one query
    assert len(collector.queries) == 1

    # Check query info
    query = collector.queries[0]
    assert isinstance(query, QueryInfo)
    assert "SELECT COUNT(*)" in query.sql
    assert "STACKTRACE:" in query.sql

    # Check frames
    assert len(query.frames) > 0
    for frame in query.frames:
        assert isinstance(frame, StackFrame)
        assert isinstance(frame.path, str)
        assert isinstance(frame.line, int)
        assert isinstance(frame.name, str)
        assert frame.line > 0


def test_multiple_queries_tracking():
    """Test that multiple queries are tracked separately."""
    with sql_traceback() as collector:
        User.objects.count()  # Query 1
        User.objects.filter(username="test").count()  # Query 2
        User.objects.filter(is_active=True).count()  # Query 3

    # Should have three queries
    assert len(collector.queries) == 3

    # Each query should be distinct
    sqls = [query.sql for query in collector.queries]
    assert len(set(sqls)) == 3  # All different

    # All should have frames
    for query in collector.queries:
        assert len(query.frames) > 0


def test_frame_attributes_validation():
    """Test that frame attributes contain expected values."""
    with sql_traceback() as collector:
        User.objects.count()

    query = collector.queries[0]
    frame = query.frames[0]

    # Path should be a valid file path
    assert frame.path.endswith(".py")

    # Line should be a positive integer
    assert frame.line > 0

    # Name should be a non-empty string (function/method name)
    assert len(frame.name) > 0


def test_last_query_convenience_property():
    """Test the convenience property for accessing the last query's frames."""
    with sql_traceback() as collector:
        # Initially empty
        assert collector.frames == []

        # After first query
        User.objects.count()
        first_frames = collector.frames
        assert len(first_frames) > 0

        # After second query
        User.objects.filter(username="test").count()
        second_frames = collector.frames
        assert len(second_frames) > 0

        # Should return frames from the last query
        assert second_frames == collector.queries[-1].frames


def test_empty_collector():
    """Test collector behavior when no queries are executed."""
    with sql_traceback() as collector:
        pass  # No queries

    # Should be empty
    assert len(collector.queries) == 0
    assert collector.frames == []


def test_nested_contexts():
    """Test that nested sql_traceback contexts work correctly.

    With stack-based collector management, nested contexts work properly:
    - The inner context becomes the active collector
    - After the inner context exits, the outer context resumes as active
    - Both collectors track their respective queries
    """
    with sql_traceback() as outer:
        User.objects.count()  # Query 1 in outer

        with sql_traceback() as inner:
            User.objects.filter(username="test").count()  # Query 1 in inner (inner is active)

        User.objects.filter(is_active=True).count()  # Query 2 in outer (outer resumes)

    # Outer collector should have 2 queries (before and after inner context)
    assert len(outer.queries) == 2

    # Inner collector should have 1 query (only within its context)
    assert len(inner.queries) == 1

    # Queries should be different
    assert outer.queries[0].sql != inner.queries[0].sql
    assert outer.queries[1].sql != inner.queries[0].sql


def test_class_based_context_manager():
    """Test the SqlTraceback class-based context manager."""
    from sql_traceback import SqlTraceback

    with SqlTraceback() as collector:
        User.objects.count()

    # Should work the same as sql_traceback function
    assert isinstance(collector, TracebackCollector)
    assert len(collector.queries) == 1
    assert len(collector.frames) > 0


def test_thread_safety():
    """Test that collectors are thread-safe (thread-local)."""
    results = {}

    def thread_func(thread_id):
        """Run queries in a separate thread."""
        with sql_traceback() as collector:
            # Create users with different usernames
            User.objects.filter(username=f"test_{thread_id}").count()
            results[thread_id] = len(collector.queries)

    # Create and run multiple threads
    threads = []
    for i in range(3):
        thread = threading.Thread(target=thread_func, args=(i,))
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Each thread should have executed exactly 1 query
    assert len(results) == 3
    for query_count in results.values():
        assert query_count == 1


def test_collector_without_as_clause():
    """Test that sql_traceback works without capturing the collector."""
    # This should not raise an error
    with sql_traceback():
        User.objects.count()

    # Verify query was executed (no exception means success)


def test_frame_content_matches_sql_comment():
    """Test that frame data matches what appears in SQL comments."""
    with sql_traceback() as collector:
        User.objects.count()

    query = collector.queries[0]

    # Extract frame info from SQL comment
    for frame in query.frames:
        # Each frame should appear in the SQL as a comment
        expected_line = f"# {frame.path}:{frame.line} in {frame.name}"
        assert expected_line in query.sql


def test_dataclass_attributes():
    """Test that StackFrame and QueryInfo are proper dataclasses."""
    # Create instances directly
    frame = StackFrame(path="/test/file.py", line=42, name="test_func")
    assert frame.path == "/test/file.py"
    assert frame.line == 42
    assert frame.name == "test_func"

    query_info = QueryInfo(sql="SELECT * FROM test", frames=[frame])
    assert query_info.sql == "SELECT * FROM test"
    assert len(query_info.frames) == 1
    assert query_info.frames[0] == frame


def test_collector_add_query_method():
    """Test the add_query method directly."""
    collector = TracebackCollector()

    # Add a query manually
    frame1 = StackFrame(path="/test1.py", line=10, name="func1")
    frame2 = StackFrame(path="/test2.py", line=20, name="func2")
    collector.add_query("SELECT 1", [frame1, frame2])

    # Verify it was added
    assert len(collector.queries) == 1
    assert collector.queries[0].sql == "SELECT 1"
    assert len(collector.queries[0].frames) == 2

    # Add another query
    collector.add_query("SELECT 2", [frame1])
    assert len(collector.queries) == 2


def test_decorator_mode_no_collector():
    """Test that decorator mode doesn't provide programmatic access."""
    from sql_traceback import SqlTraceback

    # When used as decorator, function doesn't get the collector
    @SqlTraceback()
    def query_function():
        User.objects.count()
        return "done"

    result = query_function()
    assert result == "done"
    # No way to access collector in decorator mode (as documented)


def test_exception_handling_in_context():
    """Test that collector is properly cleaned up even when exceptions occur."""
    from sql_traceback.collector_registry import get_active_collector

    # Before context
    assert get_active_collector() is None

    try:
        with sql_traceback():
            User.objects.count()
            # Collector should be active
            assert get_active_collector() is not None
            raise ValueError("Test exception")
    except ValueError:
        pass

    # After context (even with exception), collector should be cleared
    assert get_active_collector() is None


def test_filter_behavior_preserved():
    """Test that frame filtering still works as expected."""
    with sql_traceback() as collector:
        User.objects.count()

    query = collector.queries[0]

    # Should have filtered out Django internal frames
    for frame in query.frames:
        # Frames should not be from Django internals (basic check)
        # This assumes SQL_TRACEBACK_FILTER_SITEPACKAGES is True (default)
        assert "site-packages/django" not in frame.path or "/sql_traceback/" in frame.path
