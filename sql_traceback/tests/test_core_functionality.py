"""Tests for core SQL stacktrace functionality.

This module tests frame capture behavior. String formatting tests are in test_formatting.py.
"""

from unittest.mock import patch

from django.db import connection
from django.test import TestCase, override_settings

from sql_traceback import SqlTraceback, sql_traceback
from sql_traceback.traceback_info import StackFrame


class MockSettings:
    """Mock Django settings for testing."""

    SQL_TRACEBACK_ENABLED = True
    SQL_TRACEBACK_MAX_FRAMES = 15
    SQL_TRACEBACK_FILTER_SITEPACKAGES = True


@override_settings(DEBUG=True)
class TestCoreFunctionality(TestCase):
    """Test core stacktrace frame capture functionality.

    This test class covers:
    - Frame capture and extraction
    - Handling of queries that already have stacktraces
    - Core functionality validation
    - Settings and configuration behavior
    """

    def test_stacktrace_addition_function(self):
        """Test that stacktrace frames are captured correctly."""
        with patch("sql_traceback.parser.TRACEBACK_ENABLED", True):
            from sql_traceback.parser import add_stacktrace_to_query

            # Test with enabled stacktracing
            sql = "SELECT * FROM users"
            result_sql, result_frames = add_stacktrace_to_query(sql)

            # Test frames directly
            self.assertGreater(len(result_frames), 0, "Should capture frames when enabled")

            # Validate frame structure
            first_frame = result_frames[0]
            self.assertIsInstance(first_frame, StackFrame)
            self.assertTrue(first_frame.path.endswith(".py"))
            self.assertGreater(first_frame.line, 0)
            self.assertIn("test_stacktrace_addition_function", first_frame.name)

            # Test that SQL contains original query
            self.assertIn(sql, result_sql)

            # Test with already existing stacktrace
            sql_with_stacktrace = "SELECT * FROM users\n/*\nSTACKTRACE:\n# existing\n*/"
            result_sql, result_frames = add_stacktrace_to_query(sql_with_stacktrace)
            self.assertEqual(result_sql, sql_with_stacktrace, "Should not add stacktrace twice")
            self.assertEqual(result_frames, [], "Should return empty frames when already present")

    def test_stacktrace_disabled(self):
        """Test that frame capture is disabled when configured."""
        with patch("sql_traceback.parser.TRACEBACK_ENABLED", False):
            from sql_traceback.parser import add_stacktrace_to_query

            sql = "SELECT * FROM users"
            result_sql, result_frames = add_stacktrace_to_query(sql)
            self.assertEqual(result_sql, sql, "Should not modify SQL when disabled")
            self.assertEqual(result_frames, [], "Should return empty frames when disabled")

    def test_empty_sql_handling(self):
        """Test handling of empty or whitespace-only SQL."""
        with patch("sql_traceback.parser.TRACEBACK_ENABLED", True):
            from sql_traceback.parser import add_stacktrace_to_query

            # Test empty string - should still capture frames
            result_sql, result_frames = add_stacktrace_to_query("")
            self.assertGreater(len(result_frames), 0, "Should capture frames even for empty SQL")

            # Test whitespace-only string
            result_sql, result_frames = add_stacktrace_to_query("   \n\t  ")
            self.assertGreater(len(result_frames), 0, "Should capture frames for whitespace-only SQL")

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
            result_sql, result_frames = add_stacktrace_to_query(multiline_sql)

            # Test frames captured
            self.assertGreater(len(result_frames), 0)
            self.assertIn("SELECT u.id, u.name, p.title", result_sql)

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
            result_sql, result_frames = add_stacktrace_to_query(sql_with_comments)

            # Test frames captured
            self.assertGreater(len(result_frames), 0)

            # Verify original SQL preserved
            self.assertIn("This is an existing comment", result_sql)
            self.assertIn("This is a line comment", result_sql)

    def test_context_manager_initialization(self):
        """Test that context managers initialize correctly."""
        # Test function-based context manager
        cm = sql_traceback()
        self.assertIsNotNone(cm)

        # Test class-based context manager
        cm = SqlTraceback()
        self.assertIsNotNone(cm)

    def test_context_manager_enter_exit(self):
        """Test context manager enter/exit behavior returns collector."""
        with patch("sql_traceback.parser.TRACEBACK_ENABLED", True):
            # Test function-based context manager returns collector
            with sql_traceback() as collector:
                self.assertIsNotNone(collector)
                self.assertEqual(len(collector.queries), 0, "Should start empty")

            # Test class-based context manager returns collector
            with SqlTraceback() as collector:
                self.assertIsNotNone(collector)
                self.assertEqual(len(collector.queries), 0, "Should start empty")

    @override_settings(DEBUG=False)
    def test_debug_false_behavior(self):
        """Test behavior when DEBUG=False."""
        connection.queries_log.clear()

        # Execute a query with context manager when DEBUG=False
        with sql_traceback() as collector, connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        # When DEBUG=False, Django doesn't log queries, but collector should still work
        self.assertGreater(len(collector.queries), 0, "Collector should work even when DEBUG=False")
        self.assertGreater(len(collector.frames), 0, "Should capture frames")

    def test_nested_context_manager_safety(self):
        """Test that nested collectors work independently."""
        connection.queries_log.clear()

        # Test deeply nested context managers
        with (
            sql_traceback() as outer,
            sql_traceback() as middle,
            sql_traceback() as inner,
            connection.cursor() as cursor,
        ):
            cursor.execute("SELECT 1")

        # Only the innermost (active) collector should capture
        self.assertEqual(len(inner.queries), 1, "Inner collector should capture")
        self.assertEqual(len(middle.queries), 0, "Middle collector not active")
        self.assertEqual(len(outer.queries), 0, "Outer collector not active")

        # Verify frames exist
        self.assertGreater(len(inner.queries[0].frames), 0)

    def test_concurrent_usage_safety(self):
        """Test that collectors work independently in sequence."""
        connection.queries_log.clear()

        collectors = []
        for _ in range(5):
            with sql_traceback() as collector:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                collectors.append(collector)

        # All collectors should have captured their query
        for collector in collectors:
            self.assertEqual(len(collector.queries), 1, "Each collector should have 1 query")
            self.assertGreater(len(collector.frames), 0, "Each should have frames")

    def test_frame_content_validation(self):
        """Test that captured frames contain expected information."""
        connection.queries_log.clear()

        with sql_traceback() as collector, connection.cursor() as cursor:
            cursor.execute("SELECT 'validation_test'")

        # Test frames directly
        self.assertEqual(len(collector.queries), 1)
        frames = collector.queries[0].frames
        self.assertGreater(len(frames), 0)

        # Validate frame content
        frame_paths = [f.path for f in frames]
        frame_names = [f.name for f in frames]

        # Should contain test file
        self.assertTrue(any("test_core_functionality.py" in path for path in frame_paths))

        # Should contain test method name
        self.assertTrue(any("test_frame_content_validation" in name for name in frame_names))

        # All frames should have valid line numbers
        self.assertTrue(all(f.line > 0 for f in frames))
