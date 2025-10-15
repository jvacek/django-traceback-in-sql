"""Tests for the SQL stacktrace context manager using Django's unittest TestCase."""

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
        """Test that the function-based context manager adds stacktraces to queries."""
        # First execute a query without the context manager
        with self.assertNumQueries(1), connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        # Verify the query doesn't have a stacktrace comment
        self.assertNotIn("STACKTRACE:", connection.queries[0]["sql"])

        # Clear the queries log
        connection.queries_log.clear()

        # Now execute a query with the context manager
        with sql_traceback(), self.assertNumQueries(1), connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        # Verify the query has a stacktrace comment
        self.assertIn("STACKTRACE:", connection.queries[0]["sql"])
        # Verify the stacktrace contains this test file
        self.assertIn("test_context_manager_django.py", connection.queries[0]["sql"])

    def test_class_based_context_manager(self):
        """Test that the class-based context manager adds stacktraces to queries."""
        # Clear the queries log
        connection.queries_log.clear()

        # Execute a query with the class-based context manager
        with SqlTraceback(), self.assertNumQueries(1), connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        # Verify the query has a stacktrace comment
        self.assertIn("STACKTRACE:", connection.queries[0]["sql"])

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

        # Verify the query has a stacktrace comment
        self.assertIn("STACKTRACE:", connection.queries[0]["sql"])

    def test_nested_context_managers(self):
        """Test that the context manager works with assertNumQueries and other context managers."""
        # Clear the queries log
        connection.queries_log.clear()

        # Use with assertNumQueries
        with self.assertNumQueries(2), sql_traceback():
            # Execute two queries
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            with connection.cursor() as cursor:
                cursor.execute("SELECT 2")

        # Verify both queries have stacktraces
        self.assertIn("STACKTRACE:", connection.queries[0]["sql"])
        self.assertIn("STACKTRACE:", connection.queries[1]["sql"])

    def test_avoids_double_stacktrace(self):
        """Test that stacktraces aren't added twice to the same query."""
        # Clear the queries log
        connection.queries_log.clear()

        # Execute a query with nested context managers
        with sql_traceback(), sql_traceback(), connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        # Check that only one stacktrace comment was added
        sql = connection.queries[0]["sql"]
        self.assertEqual(sql.count("STACKTRACE:"), 1)
