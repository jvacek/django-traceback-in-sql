"""Tests for the SQL stacktrace context manager using Django's unittest TestCase.

This module tests context manager behavior and frame capture. String formatting tests
are in test_formatting.py.
"""

from django.db import connection
from django.test import TestCase, override_settings

from sql_traceback import SqlTraceback, sql_traceback


class MockSettings:
    """Mock Django settings for testing."""

    SQL_TRACEBACK_ENABLED = True
    SQL_TRACEBACK_MAX_FRAMES = 15
    SQL_TRACEBACK_FILTER_SITEPACKAGES = True


@override_settings(DEBUG=True)
class TestContextManagerUsage(TestCase):
    """Test different ways to use the SQL traceback context manager.

    This test class covers:
    - Function-based context manager usage
    - Class-based context manager usage
    - Using the context manager as a decorator
    - Nested context manager scenarios
    - Prevention of duplicate stacktraces
    """

    def setUp(self):
        # Ensure connection.queries is reset before each test
        connection.queries_log.clear()

    def test_function_based_context_manager(self):
        """Test that the function-based context manager captures frames."""
        # First execute a query without the context manager (no collector available)
        with self.assertNumQueries(1), connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        # Clear the queries log
        connection.queries_log.clear()

        # Now execute a query with the context manager
        with sql_traceback() as collector, self.assertNumQueries(1), connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        # Test frame capture
        self.assertEqual(len(collector.queries), 1, "Should capture 1 query")
        self.assertGreater(len(collector.frames), 0, "Should have frames")

        # Verify frame contains test file
        frame_paths = [f.path for f in collector.frames]
        self.assertTrue(
            any("test_context_manager_django.py" in path for path in frame_paths), "Should capture frame from test file"
        )

    def test_class_based_context_manager(self):
        """Test that the class-based context manager captures frames."""
        connection.queries_log.clear()

        # Execute a query with the class-based context manager
        with SqlTraceback() as collector, self.assertNumQueries(1), connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        # Test frame capture
        self.assertEqual(len(collector.queries), 1)
        self.assertGreater(len(collector.frames), 0)

    def test_as_decorator(self):
        """Test that the context manager works as a decorator."""

        # Define a decorated function
        @SqlTraceback()
        def execute_query():
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return cursor.fetchone()

        # Clear the queries log
        connection.queries_log.clear()

        # Execute the decorated function
        with self.assertNumQueries(1):
            result = execute_query()

        # Verify the function executed correctly
        self.assertEqual(result[0], 1)

        # Note: In decorator mode, we don't have access to the collector.
        # With Django's execute_wrapper API, the stacktrace is added to SQL
        # sent to the database but not to Django's query log, so we just verify
        # that the decorator works and queries execute successfully.

    def test_nested_context_managers(self):
        """Test that nested collectors work with assertNumQueries."""
        connection.queries_log.clear()

        # Use with assertNumQueries
        with self.assertNumQueries(2), sql_traceback() as collector:
            # Execute two queries
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            with connection.cursor() as cursor:
                cursor.execute("SELECT 2")

        # Test frame capture for both queries
        self.assertEqual(len(collector.queries), 2, "Should capture 2 queries")
        self.assertGreater(len(collector.queries[0].frames), 0)
        self.assertGreater(len(collector.queries[1].frames), 0)

    def test_avoids_double_stacktrace(self):
        """Test that nested collectors don't duplicate frame capture."""
        connection.queries_log.clear()

        # Execute a query with nested context managers
        with sql_traceback() as outer, sql_traceback() as inner, connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        # Only the inner (active) collector should have captured
        self.assertEqual(len(inner.queries), 1, "Inner collector should capture")
        self.assertEqual(len(outer.queries), 0, "Outer collector suspended")
        self.assertGreater(len(inner.frames), 0, "Inner should have frames")
