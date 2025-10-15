"""Tests for the SQL stacktrace context manager using pytest-django."""

import pytest
from django.contrib.auth import get_user_model
from django.db import connection

from sql_traceback import SqlTraceback, sql_traceback


User = get_user_model()


@pytest.mark.django_db
class TestContextManagerWithPytestDjango:
    """Test SQL traceback functionality using pytest-django's query assertion fixtures.

    This test class demonstrates integration with pytest-django's django_assert_num_queries
    fixture and shows how stacktraces are added while maintaining query counting accuracy.
    It also tests pytest executable filtering to ensure clean stacktraces without pytest
    framework noise while preserving user test file information.
    """

    def test_single_query_with_stacktrace(self, django_assert_num_queries, settings):
        """Test that stacktraces are added to a single query with precise query counting."""
        settings.DEBUG = True
        # Clear any existing queries
        connection.queries_log.clear()

        # Use pytest-django's assertion fixture to verify exactly 1 query
        with django_assert_num_queries(1), sql_traceback(), connection.cursor() as cursor:
            cursor.execute("SELECT 1 as test_value")

        # Verify the query has a stacktrace comment
        assert "STACKTRACE:" in connection.queries[0]["sql"]
        # Verify the stacktrace contains this test file
        assert "test_context_manager_pytest.py" in connection.queries[0]["sql"]

        # Verify pytest executable filtering works
        sql_with_stacktrace = connection.queries[0]["sql"]
        assert "/bin/pytest" not in sql_with_stacktrace
        assert "\\Scripts\\pytest.exe" not in sql_with_stacktrace
        assert "_pytest/" not in sql_with_stacktrace
        assert "pytest_django/" not in sql_with_stacktrace
        assert "/pluggy/" not in sql_with_stacktrace

    def test_multiple_queries_with_stacktrace(self, django_assert_num_queries, settings):
        """Test that stacktraces are added to multiple queries with precise counting."""
        settings.DEBUG = True
        # Clear any existing queries
        connection.queries_log.clear()

        # Use pytest-django's assertion fixture to verify exactly 3 queries
        with django_assert_num_queries(3), sql_traceback(), connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.execute("SELECT 2")
            cursor.execute("SELECT 3")

        # Verify all queries have stacktraces
        for i in range(3):
            assert "STACKTRACE:" in connection.queries[i]["sql"]
            assert "test_context_manager_pytest.py" in connection.queries[i]["sql"]

    def test_no_queries_assertion(self, django_assert_num_queries, settings):
        """Test that no queries are executed when none are expected."""
        settings.DEBUG = True
        # Clear any existing queries
        connection.queries_log.clear()

        # Use pytest-django's assertion fixture to verify no queries
        with django_assert_num_queries(0), sql_traceback():
            # Just some Python code that doesn't touch the database
            result = 1 + 1
            assert result == 2

    def test_query_inspection_with_captured_context(self, django_assert_num_queries, settings):
        """Test inspecting captured queries with stacktraces using the context manager."""
        settings.DEBUG = True
        # Clear any existing queries
        connection.queries_log.clear()

        # Use the context manager to capture and inspect queries
        with django_assert_num_queries(2) as captured, sql_traceback(), connection.cursor() as cursor:
            cursor.execute("SELECT 'first' as query_type")
            cursor.execute("SELECT 'second' as query_type")

        # Verify we captured exactly 2 queries
        assert len(captured.captured_queries) == 2

        # Inspect each captured query for stacktraces
        for query in captured.captured_queries:
            assert "STACKTRACE:" in query["sql"]
            # Verify original SQL is preserved
            assert "SELECT" in query["sql"]
            assert "query_type" in query["sql"]

    def test_class_based_context_manager_with_assertion(self, django_assert_num_queries, settings):
        """Test class-based context manager with pytest-django query assertions."""
        settings.DEBUG = True
        # Clear any existing queries
        connection.queries_log.clear()

        # Use class-based context manager with query assertion
        with django_assert_num_queries(1), SqlTraceback(), connection.cursor() as cursor:
            cursor.execute("SELECT 'class_based' as context_type")

        # Verify stacktrace was added
        assert "STACKTRACE:" in connection.queries[0]["sql"]
        assert "class_based" in connection.queries[0]["sql"]

    def test_decorator_usage_with_assertion(self, django_assert_num_queries, settings):
        """Test decorator usage with pytest-django query assertions."""
        settings.DEBUG = True

        @sql_traceback()
        def execute_decorated_query():
            with connection.cursor() as cursor:
                cursor.execute("SELECT 'decorated' as usage_type")
                return cursor.fetchone()

        # Clear any existing queries
        connection.queries_log.clear()

        # Execute decorated function with query assertion
        with django_assert_num_queries(1):
            result = execute_decorated_query()

        # Verify function executed correctly
        assert result[0] == "decorated"

        # Verify stacktrace was added
        assert "STACKTRACE:" in connection.queries[0]["sql"]
        assert "decorated" in connection.queries[0]["sql"]

    def test_nested_with_max_queries(self, django_assert_max_num_queries, settings):
        """Test with django_assert_max_num_queries to ensure we don't exceed expected queries."""
        settings.DEBUG = True
        # Clear any existing queries
        connection.queries_log.clear()

        # Use max queries assertion - we'll execute 2 but allow up to 3
        with django_assert_max_num_queries(3), sql_traceback(), connection.cursor() as cursor:
            cursor.execute("SELECT 'max_test_1' as test")
            cursor.execute("SELECT 'max_test_2' as test")

        # Verify both queries have stacktraces
        assert len(connection.queries) == 2
        for query in connection.queries:
            assert "STACKTRACE:" in query["sql"]
            assert "max_test" in query["sql"]

    def test_without_stacktrace_for_comparison(self, django_assert_num_queries, settings):
        """Test queries without stacktrace context manager for comparison."""
        settings.DEBUG = True
        # Clear any existing queries
        connection.queries_log.clear()

        # Execute query without stacktrace context manager
        with django_assert_num_queries(1), connection.cursor() as cursor:
            cursor.execute("SELECT 'no_stacktrace' as test")

        # Verify query does NOT have stacktrace
        assert "STACKTRACE:" not in connection.queries[0]["sql"]
        # But verify the original SQL is there
        assert "no_stacktrace" in connection.queries[0]["sql"]

    def test_function_based_context_manager_pytest_style(self, django_assert_num_queries, settings):
        """Test function-based context manager using pytest-style assertions."""
        settings.DEBUG = True
        # Clear any existing queries
        connection.queries_log.clear()

        # First execute a query without the context manager
        with django_assert_num_queries(1), connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        # Verify the query doesn't have a stacktrace comment
        assert "STACKTRACE:" not in connection.queries[0]["sql"]

        # Clear the queries log
        connection.queries_log.clear()

        # Now execute a query with the context manager
        with django_assert_num_queries(1), sql_traceback(), connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        # Verify the query has a stacktrace comment
        assert "STACKTRACE:" in connection.queries[0]["sql"]
        # Verify the stacktrace contains this test file
        assert "test_context_manager_pytest.py" in connection.queries[0]["sql"]

    def test_avoids_double_stacktrace_pytest_style(self, django_assert_num_queries, settings):
        """Test that stacktraces aren't added twice to the same query using pytest."""
        settings.DEBUG = True
        # Clear the queries log
        connection.queries_log.clear()

        # Execute a query with nested context managers
        with django_assert_num_queries(1), sql_traceback(), sql_traceback(), connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        # Check that only one stacktrace comment was added
        sql = connection.queries[0]["sql"]
        assert sql.count("STACKTRACE:") == 1

    def test_pytest_executable_filtering_with_user_model(self, django_assert_num_queries, settings):
        """Test pytest executable filtering with User model queries."""
        settings.DEBUG = True
        connection.queries_log.clear()

        # Execute the exact scenario from the reported issue
        with sql_traceback(), django_assert_num_queries(1):
            _ = User.objects.count()

        # Verify stacktrace was added but pytest executable is filtered out
        sql_with_stacktrace = connection.queries[0]["sql"]
        assert "STACKTRACE:" in sql_with_stacktrace
        assert "test_context_manager_pytest.py" in sql_with_stacktrace

        # Verify pytest executable and internals are filtered out
        assert "/bin/pytest" not in sql_with_stacktrace
        assert "\\Scripts\\pytest.exe" not in sql_with_stacktrace
        assert "_pytest/" not in sql_with_stacktrace
        assert "pytest_django/" not in sql_with_stacktrace
        assert "/pluggy/" not in sql_with_stacktrace

    def test_pytest_filtering_can_be_disabled(self, django_assert_num_queries, settings):
        """Test that pytest filtering can be disabled via settings."""
        settings.DEBUG = True
        settings.SQL_TRACEBACK_FILTER_TESTING_FRAMEWORKS = False
        connection.queries_log.clear()

        with sql_traceback(), django_assert_num_queries(1):
            User.objects.count()

        # Verify stacktrace was added and this test file is included
        sql_with_stacktrace = connection.queries[0]["sql"]
        assert "STACKTRACE:" in sql_with_stacktrace
        assert "test_context_manager_pytest.py" in sql_with_stacktrace
