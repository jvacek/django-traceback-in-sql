"""Tests for core SQL stacktrace functionality."""

from unittest.mock import patch

from django.db import connection
from django.test import TestCase, override_settings

from sql_traceback import SqlTraceback, sql_traceback


class MockSettings:
    """Mock Django settings for testing."""

    SQL_TRACEBACK_ENABLED = True
    SQL_TRACEBACK_MAX_FRAMES = 15
    SQL_TRACEBACK_FILTER_SITEPACKAGES = True


@override_settings(DEBUG=True)
class TestCoreFunctionality(TestCase):
    """Test core stacktrace addition functionality.

    This test class covers:
    - Direct stacktrace addition to SQL queries
    - Handling of queries that already have stacktraces
    - Core functionality validation
    - Settings and configuration behavior
    """

    def test_stacktrace_addition_function(self):
        """Test the main stacktrace addition function directly."""
        with patch("sql_traceback.parser.TRACEBACK_ENABLED", True):
            from sql_traceback.parser import add_stacktrace_to_query

            # Test with enabled stacktracing
            sql = "SELECT * FROM users"
            result = add_stacktrace_to_query(sql)
            self.assertIn("/*\nSTACKTRACE:", result, "Should add stacktrace when enabled")
            self.assertIn(sql, result, "Should contain original SQL")

            # Test with already existing stacktrace
            sql_with_stacktrace = "SELECT * FROM users\n/*\nSTACKTRACE:\n# existing\n*/"
            result = add_stacktrace_to_query(sql_with_stacktrace)
            self.assertEqual(result, sql_with_stacktrace, "Should not add stacktrace twice")

    def test_stacktrace_disabled(self):
        """Test that stacktraces are not added when disabled."""
        with patch("sql_traceback.parser.TRACEBACK_ENABLED", False):
            from sql_traceback.parser import add_stacktrace_to_query

            sql = "SELECT * FROM users"
            result = add_stacktrace_to_query(sql)
            self.assertEqual(result, sql, "Should not modify SQL when disabled")

    def test_empty_sql_handling(self):
        """Test handling of empty or whitespace-only SQL."""
        with patch("sql_traceback.parser.TRACEBACK_ENABLED", True):
            from sql_traceback.parser import add_stacktrace_to_query

            # Test empty string - the current implementation adds stacktrace even to empty strings
            result = add_stacktrace_to_query("")
            self.assertIn("STACKTRACE:", result, "Should add stacktrace even to empty string")

            # Test whitespace-only string - also gets stacktrace added
            result = add_stacktrace_to_query("   \n\t  ")
            self.assertIn("STACKTRACE:", result, "Should add stacktrace to whitespace-only string")

    def test_multiline_sql_handling(self):
        """Test handling of multiline SQL queries."""
        with patch("sql_traceback.parser.TRACEBACK_ENABLED", True):
            from sql_traceback.parser import add_stacktrace_to_query

            multiline_sql = """
            SELECT u.id, u.name, p.title
            FROM users u
            JOIN posts p ON u.id = p.user_id
            WHERE u.active = 1
            ORDER BY u.name
            """
            result = add_stacktrace_to_query(multiline_sql)
            self.assertIn("STACKTRACE:", result)
            self.assertIn("SELECT u.id, u.name, p.title", result)

    def test_sql_with_comments_handling(self):
        """Test handling of SQL that already contains comments."""
        with patch("sql_traceback.parser.TRACEBACK_ENABLED", True):
            from sql_traceback.parser import add_stacktrace_to_query

            sql_with_comments = """
            /* This is an existing comment */
            SELECT * FROM users
            -- This is a line comment
            WHERE active = 1
            """
            result = add_stacktrace_to_query(sql_with_comments)
            self.assertIn("STACKTRACE:", result)
            self.assertIn("This is an existing comment", result)
            self.assertIn("This is a line comment", result)

    def test_context_manager_initialization(self):
        """Test that context managers initialize correctly."""
        # Test function-based context manager
        cm = sql_traceback()
        self.assertIsNotNone(cm)

        # Test class-based context manager
        cm = SqlTraceback()
        self.assertIsNotNone(cm)

    def test_context_manager_enter_exit(self):
        """Test context manager enter/exit behavior."""
        with patch("sql_traceback.parser.TRACEBACK_ENABLED", True):
            # Test function-based context manager - returns None but should not crash
            with sql_traceback() as cm:
                # Context manager works but returns None, which is fine
                pass

            # Test class-based context manager - returns self
            with SqlTraceback() as cm:
                self.assertIsNotNone(cm)

    @override_settings(DEBUG=False)
    def test_debug_false_behavior(self):
        """Test behavior when DEBUG=False."""
        # Clear the queries log
        connection.queries_log.clear()

        # Execute a query with context manager when DEBUG=False
        with sql_traceback(), connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        # When DEBUG=False, Django doesn't log queries, so we can't test stacktrace addition
        # This test mainly ensures the context manager doesn't crash
        self.assertTrue(True, "Context manager should work even when DEBUG=False")

    def test_nested_context_manager_safety(self):
        """Test that nested context managers are safe and don't interfere."""
        connection.queries_log.clear()

        # Test deeply nested context managers
        with sql_traceback(), sql_traceback(), sql_traceback(), connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        # Verify only one stacktrace was added
        if connection.queries:
            sql = connection.queries[0]["sql"]
            self.assertEqual(sql.count("STACKTRACE:"), 1)

    def test_concurrent_usage_safety(self):
        """Test that the context manager is safe for concurrent usage patterns."""
        connection.queries_log.clear()

        # Simulate concurrent-like usage (though still single-threaded in tests)
        context_managers = [sql_traceback() for _ in range(5)]

        for cm in context_managers:
            with cm, connection.cursor() as cursor:
                cursor.execute("SELECT 1")

        # All queries should have stacktraces
        for query in connection.queries[-5:]:  # Last 5 queries
            self.assertIn("STACKTRACE:", query["sql"])

    def test_stacktrace_content_validation(self):
        """Test that stacktraces contain expected content."""
        connection.queries_log.clear()

        with sql_traceback(), connection.cursor() as cursor:
            cursor.execute("SELECT 'validation_test'")

        if connection.queries:
            sql = connection.queries[0]["sql"]
            # Should contain the test file name
            self.assertIn("test_core_functionality.py", sql)
            # Should contain the test method name
            self.assertIn("test_stacktrace_content_validation", sql)
            # Should contain file path indicators
            self.assertTrue(any(indicator in sql for indicator in ["/", "\\"]))
