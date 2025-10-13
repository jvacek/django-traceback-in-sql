"""Tests for the SQL stacktrace context manager."""

from unittest import mock

from django.db import connection
from django.test import TestCase, override_settings

from sql_traceback import SqlTraceback, sql_traceback


@override_settings(DEBUG=True)
class TestSqlTracebackContextManager(TestCase):
    def setUp(self):
        # Ensure connection.queries is reset before each test
        connection.queries_log.clear()
        # settings.configure()

    def test_function_based_context_manager(self):
        """Test that the function-based context manager adds stacktraces to queries."""
        # First execute a query without the context manager
        with self.assertNumQueries(1):  # noqa: SIM117
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")

        # Verify the query doesn't have a stacktrace comment
        self.assertNotIn("STACKTRACE:", connection.queries[0]["sql"])

        # Clear the queries log
        connection.queries_log.clear()

        # Now execute a query with the context manager
        with sql_traceback(), self.assertNumQueries(1):  # noqa: SIM117
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")

        # Verify the query has a stacktrace comment
        self.assertIn("STACKTRACE:", connection.queries[0]["sql"])
        # Verify the stacktrace contains this test file
        self.assertIn("test_context_manager.py", connection.queries[0]["sql"])

    def test_class_based_context_manager(self):
        """Test that the class-based context manager adds stacktraces to queries."""
        # Clear the queries log
        connection.queries_log.clear()

        # Execute a query with the class-based context manager
        with SqlTraceback(), self.assertNumQueries(1):  # noqa: SIM117
            with connection.cursor() as cursor:
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
        with self.assertNumQueries(2):  # noqa: SIM117
            with sql_traceback():
                # Execute two queries
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 2")

        # Verify both queries have stacktraces
        self.assertIn("STACKTRACE:", connection.queries[0]["sql"])
        self.assertIn("STACKTRACE:", connection.queries[1]["sql"])

    def test_stacktrace_filtering(self):
        """Test that the stacktrace filters out Django framework code."""
        # Clear the queries log
        connection.queries_log.clear()

        # Execute a query with the context manager
        with sql_traceback(), self.assertNumQueries(1):  # noqa: SIM117
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")

        # Verify the query has a stacktrace
        sql_with_stacktrace = connection.queries[0]["sql"]
        self.assertIn("STACKTRACE:", sql_with_stacktrace)

        # Verify Django framework code is filtered out
        self.assertNotIn("django/db/", sql_with_stacktrace)
        self.assertNotIn("django/core/", sql_with_stacktrace)

        # Verify test code is included
        self.assertIn("test_context_manager.py", sql_with_stacktrace)

    @mock.patch.dict("os.environ", {"ENABLE_SQL_TRACEBACK": "0"})
    def test_disabled_via_environment_variable(self):
        """Test that the context manager respects the ENABLE_SQL_TRACEBACK environment variable."""
        # Clear the queries log
        connection.queries_log.clear()

        # Execute a query with the context manager, but with stacktraces disabled
        with sql_traceback(), self.assertNumQueries(1):  # noqa: SIM117
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")

        # Verify the query does not have a stacktrace comment
        self.assertNotIn("STACKTRACE:", connection.queries[0]["sql"])

    def test_avoids_double_stacktrace(self):
        """Test that stacktraces aren't added twice to the same query."""
        # Clear the queries log
        connection.queries_log.clear()

        # Execute a query with nested context managers
        with sql_traceback():  # noqa: SIM117
            with sql_traceback():
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")

        # Check that only one stacktrace comment was added
        sql = connection.queries[0]["sql"]
        self.assertEqual(sql.count("STACKTRACE:"), 1)

    def test_database_backend_identification(self):
        """Test that we can identify which database backend is being used."""
        import os

        db_engine = os.environ.get("DB_ENGINE", "sqlite")
        db_vendor = connection.vendor

        # Verify the correct database backend is being used
        if db_engine == "postgres":
            self.assertEqual(db_vendor, "postgresql")
        elif db_engine == "mysql":
            self.assertEqual(db_vendor, "mysql")
        else:  # sqlite
            self.assertEqual(db_vendor, "sqlite")

        # Execute a simple query to verify the connection works
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            self.assertEqual(result[0], 1)
