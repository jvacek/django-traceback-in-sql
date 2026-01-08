"""Tests for Django settings integration and configuration.

This module tests configuration behavior. Frame capture tests are in test_core_functionality.py.
"""

from unittest import mock
from unittest.mock import patch

from django.db import connection
from django.test import TestCase, override_settings

from sql_traceback import sql_traceback
from sql_traceback.parser import _is_stacktrace_enabled


class MockSettings:
    """Mock Django settings for testing."""

    SQL_TRACEBACK_ENABLED = True
    SQL_TRACEBACK_MAX_FRAMES = 15
    SQL_TRACEBACK_FILTER_SITEPACKAGES = True


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

        # Patch the module-level variables directly since they're cached
        with (
            patch("django.conf.settings", mock_settings),
            patch("sql_traceback.config.TRACEBACK_ENABLED", True),
            patch("sql_traceback.config.MAX_STACK_FRAMES", 15),
            patch("sql_traceback.config.FILTER_SITEPACKAGES", True),
        ):
            # Test enabled check
            self.assertTrue(_is_stacktrace_enabled())

    def test_settings_defaults(self):
        """Test that defaults work when settings are missing."""
        # Test that the current settings match expected defaults
        from sql_traceback.config import (
            FILTER_SITEPACKAGES,
            MAX_STACK_FRAMES,
            TRACEBACK_ENABLED,
        )

        # Should use defaults (these are the actual defaults from the module)
        self.assertTrue(TRACEBACK_ENABLED)
        self.assertEqual(MAX_STACK_FRAMES, 15)
        self.assertTrue(FILTER_SITEPACKAGES)

    @mock.patch("sql_traceback.parser.TRACEBACK_ENABLED", False)
    def test_disabled_via_django_setting(self):
        """Test that disabling traceback prevents frame capture."""
        connection.queries_log.clear()

        # Execute a query with the context manager, but with stacktraces disabled
        with sql_traceback() as collector, self.assertNumQueries(1), connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        # Test actual functionality: when disabled, nothing is registered with collector
        # (because add_stacktrace_to_query returns empty frames, and cursors skip collector.add_query)
        self.assertEqual(len(collector.queries), 0, "Collector should be empty when disabled")

    def test_completely_disabled_stacktrace(self):
        """Test behavior when stacktracing is completely disabled."""
        with patch("sql_traceback.parser.TRACEBACK_ENABLED", False):
            from sql_traceback.parser import add_stacktrace_to_query

            sql = "SELECT * FROM users"
            result_sql, result_frames = add_stacktrace_to_query(sql)

            # Test frame capture behavior
            self.assertEqual(result_sql, sql, "Should return original SQL when disabled")
            self.assertEqual(result_frames, [], "Should return empty frames list when disabled")
