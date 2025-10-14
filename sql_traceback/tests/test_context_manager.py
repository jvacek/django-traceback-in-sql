"""Tests for the SQL stacktrace context manager."""

import os
from unittest import mock
from unittest.mock import Mock, patch

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
        with self.assertNumQueries(1):
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")

        # Verify the query doesn't have a stacktrace comment
        self.assertNotIn("STACKTRACE:", connection.queries[0]["sql"])

        # Clear the queries log
        connection.queries_log.clear()

        # Now execute a query with the context manager
        with sql_traceback(), self.assertNumQueries(1):
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
        with SqlTraceback(), self.assertNumQueries(1):
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
        with self.assertNumQueries(2):
            with sql_traceback():
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
        with sql_traceback():
            with sql_traceback():
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")

        # Check that only one stacktrace comment was added
        sql = connection.queries[0]["sql"]
        self.assertEqual(sql.count("STACKTRACE:"), 1)


@override_settings(DEBUG=True)
class TestSettingsConfiguration(TestCase):
    """Test Django settings integration and configuration options.

    This test class covers:
    - Django settings loading and integration
    - Default configuration values
    - Disabled stacktracing via settings
    - Settings validation and behavior
    """

    def setUp(self):
        connection.queries_log.clear()

    def test_django_settings_integration(self):
        """Test that Django settings are properly loaded."""
        mock_settings = MockSettings()

        with patch("django.conf.settings", mock_settings):
            # Patch the module-level variables directly since they're cached
            with (
                patch("sql_traceback.context_manager.TRACEBACK_ENABLED", True),
                patch("sql_traceback.context_manager.MAX_STACK_FRAMES", 15),
                patch("sql_traceback.context_manager.FILTER_SITEPACKAGES", True),
            ):
                from sql_traceback.context_manager import _is_stacktrace_enabled

                # Test enabled check
                self.assertTrue(_is_stacktrace_enabled())

    def test_settings_defaults(self):
        """Test that defaults work when settings are missing."""
        # Test that the current settings match expected defaults
        from sql_traceback.context_manager import (
            TRACEBACK_ENABLED,
            MAX_STACK_FRAMES,
            FILTER_SITEPACKAGES,
        )

        # Should use defaults (these are the actual defaults from the module)
        self.assertTrue(TRACEBACK_ENABLED)
        self.assertEqual(MAX_STACK_FRAMES, 15)
        self.assertTrue(FILTER_SITEPACKAGES)

    @mock.patch("sql_traceback.context_manager.TRACEBACK_ENABLED", False)
    def test_disabled_via_django_setting(self):
        """Test that the context manager respects the SQL_TRACEBACK_ENABLED Django setting."""
        # Clear the queries log
        connection.queries_log.clear()

        # Execute a query with the context manager, but with stacktraces disabled
        with sql_traceback(), self.assertNumQueries(1):
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")

        # Verify the query does not have a stacktrace comment
        self.assertNotIn("STACKTRACE:", connection.queries[0]["sql"])

    def test_completely_disabled_stacktrace(self):
        """Test behavior when stacktracing is completely disabled."""
        with patch("sql_traceback.context_manager.TRACEBACK_ENABLED", False):
            from sql_traceback.context_manager import add_stacktrace_to_query

            sql = "SELECT * FROM users"
            result = add_stacktrace_to_query(sql)
            self.assertEqual(result, sql, "Should return original SQL when disabled")


@override_settings(DEBUG=True)
class TestStacktraceFiltering(TestCase):
    """Test stacktrace filtering logic and frame inclusion/exclusion.

    This test class covers:
    - Django framework code filtering
    - Site-packages filtering (enabled/disabled)
    - Application code inclusion
    - Frame filtering logic and edge cases
    """

    def setUp(self):
        connection.queries_log.clear()

    def test_stacktrace_filtering_comprehensive(self):
        """Test that the stacktrace filters out Django framework code."""
        # Clear the queries log
        connection.queries_log.clear()

        # Execute a query with the context manager
        with sql_traceback(), self.assertNumQueries(1):
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

    def test_frame_filtering_logic(self):
        """Test the detailed frame filtering logic."""
        # Test with site-packages filtering enabled
        with patch("sql_traceback.context_manager.FILTER_SITEPACKAGES", True):
            from sql_traceback.context_manager import _should_include_frame

            # Mock traceback frame
            def create_mock_frame(filename):
                frame = Mock()
                frame.filename = filename
                frame.lineno = 42
                frame.name = "test_function"
                return frame

            # Test cases for frame inclusion
            test_cases = [
                # Should be excluded (Django framework)
                ("/path/to/django/db/models.py", False),
                ("/usr/lib/python3.9/django/core/handlers.py", False),
                # Should be excluded (site-packages when filtering enabled)
                ("/path/to/site-packages/package/file.py", False),
                # Should be included (application files)
                ("/app/views.py", True),
                ("/project/models.py", True),
                # Should be included (test files)
                ("/app/test_something.py", True),
                ("/project/tests/test_views.py", True),
            ]

            for filename, expected in test_cases:
                frame = create_mock_frame(filename)
                result = _should_include_frame(frame)
                self.assertEqual(result, expected, f"For '{filename}', expected {expected}, got {result}")

    def test_disabled_site_packages_filtering(self):
        """Test behavior when site-packages filtering is disabled."""
        # Test with site-packages filtering disabled
        with patch("sql_traceback.context_manager.FILTER_SITEPACKAGES", False):
            from sql_traceback.context_manager import _should_include_frame

            # Mock frame from site-packages
            frame = Mock()
            frame.filename = "/path/to/site-packages/package/file.py"
            frame.lineno = 42
            frame.name = "test_function"

            # Should be included when filtering is disabled
            result = _should_include_frame(frame)
            self.assertTrue(result, "Site-packages should be included when filtering is disabled")


@override_settings(DEBUG=True)
class TestCoreFunctionality(TestCase):
    """Test core stacktrace addition functionality.

    This test class covers:
    - Direct stacktrace addition to SQL queries
    - Handling of queries that already have stacktraces
    - Core functionality validation
    """

    def test_stacktrace_addition_function(self):
        """Test the main stacktrace addition function directly."""
        with patch("sql_traceback.context_manager.TRACEBACK_ENABLED", True):
            from sql_traceback.context_manager import add_stacktrace_to_query

            # Test with enabled stacktracing
            sql = "SELECT * FROM users"
            result = add_stacktrace_to_query(sql)
            self.assertIn("/*\nSTACKTRACE:", result, "Should add stacktrace when enabled")
            self.assertIn(sql, result, "Should contain original SQL")

            # Test with already existing stacktrace
            sql_with_stacktrace = "SELECT * FROM users\n/*\nSTACKTRACE:\n# existing\n*/"
            result = add_stacktrace_to_query(sql_with_stacktrace)
            self.assertEqual(result, sql_with_stacktrace, "Should not add stacktrace twice")


@override_settings(DEBUG=True)
class TestEnvironmentIntegration(TestCase):
    """Test database backend identification and environment integration.

    This test class covers:
    - Database backend detection (SQLite, PostgreSQL, MySQL)
    - Environment variable handling
    - Basic database connectivity validation
    """

    def test_database_backend_identification(self):
        """Test that we can identify which database backend is being used."""
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
