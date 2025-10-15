import os

from django.db import connection
from django.test import TestCase, override_settings


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
            self.assertIsNotNone(result, "Query result should not be None")
            self.assertEqual(result[0], 1)  # pyright: ignore[reportOptionalSubscript]
