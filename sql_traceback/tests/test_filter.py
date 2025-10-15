from unittest.mock import Mock, patch

from django.db import connection
from django.test import TestCase, override_settings

from sql_traceback import sql_traceback
from sql_traceback.filter import should_include_frame


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
        with sql_traceback(), self.assertNumQueries(1), connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        # Verify the query has a stacktrace
        sql_with_stacktrace = connection.queries[0]["sql"]
        self.assertIn("STACKTRACE:", sql_with_stacktrace)

        # Verify Django framework code is filtered out
        self.assertNotIn("django/db/", sql_with_stacktrace)
        self.assertNotIn("django/core/", sql_with_stacktrace)

        # Verify test code is included
        self.assertIn("test_filter.py", sql_with_stacktrace)

    def test_frame_filtering_logic(self):
        """Test the detailed frame filtering logic."""
        # Test with site-packages filtering enabled
        with patch("sql_traceback.filter.FILTER_SITEPACKAGES", True):
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
                result = should_include_frame(frame)
                self.assertEqual(result, expected, f"For '{filename}', expected {expected}, got {result}")

    def test_disabled_site_packages_filtering(self):
        """Test behavior when site-packages filtering is disabled."""
        # Test with site-packages filtering disabled
        with patch("sql_traceback.filter.FILTER_SITEPACKAGES", False):
            # Mock frame from site-packages
            frame = Mock()
            frame.filename = "/path/to/site-packages/package/file.py"
            frame.lineno = 42
            frame.name = "test_function"

            # Should be included when filtering is disabled
            result = should_include_frame(frame)
            self.assertTrue(result, "Site-packages should be included when filtering is disabled")
