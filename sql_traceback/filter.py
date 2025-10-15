"""Stack frame filtering utilities for SQL stacktraces.

This module contains functions for filtering and sanitizing stack frames
to produce clean, readable stacktraces that focus on application code.
"""

import traceback

from sql_traceback.config import (
    FILTER_SITEPACKAGES,
    FILTER_STDLIB,
    FILTER_TESTING_FRAMEWORKS,
)

__all__ = ["should_include_frame", "sanitize_filename"]


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent any potential SQL comment issues.

    Args:
        filename: The filename to sanitize

    Returns:
        A sanitized filename safe to include in SQL comments
    """
    return filename.replace("*/", "").replace("/*", "").replace("\n", "").replace("\r", "")


def should_include_frame(frame: traceback.FrameSummary) -> bool:
    """Determine if a stack frame should be included in the traceback.

    Args:
        frame: The stack frame to evaluate

    Returns:
        True if the frame should be included in the stacktrace, False otherwise
    """
    filename_lower = frame.filename.lower()

    # Skip site-packages if filtering is enabled
    if FILTER_SITEPACKAGES and "site-packages/" in filename_lower:
        return False

    # Skip Django framework code if filtering is enabled
    if FILTER_SITEPACKAGES:
        django_patterns = [
            "/django/",
            "\\django\\",  # Windows path separator
        ]
        if any(pattern in filename_lower for pattern in django_patterns):
            return False

    # Skip Python standard library if filtering is enabled
    if FILTER_STDLIB:
        # Filter Python standard library modules
        stdlib_patterns = [
            "/lib/python3.",
            "/lib64/python3.",
            "<frozen ",
            "/runpy.py",
            "/threading.py",
            "/queue.py",
            "/contextlib.py",
            "/functools.py",
            "/traceback.py",
            "/inspect.py",
            "/importlib/",
            "/collections/",
            "/weakref.py",
            "/copy.py",
            "/logging/",
        ]

        # Check if it's a stdlib module (not in site-packages)
        if "site-packages/" not in filename_lower and any(pattern in filename_lower for pattern in stdlib_patterns):
            return False

    # Skip testing framework internals if filtering is enabled
    # This is useful because testing frameworks span both third-party (pytest) and stdlib (unittest)
    # and you almost never want to see their internals when debugging SQL queries
    if FILTER_TESTING_FRAMEWORKS:
        # Filter pytest internals (third-party)
        pytest_excludes = [
            "_pytest/",
            "pytest_django/",
            "/pluggy/",
        ]

        # Filter pytest executables - these are entry points, not useful for SQL debugging
        pytest_executable_excludes = [
            "/bin/pytest",
            "/scripts/pytest.exe",  # Windows (lowercased for case-insensitive matching)
            "\\scripts\\pytest.exe",  # Windows with backslashes (lowercased)
        ]

        # Filter unittest internals (stdlib)
        unittest_excludes = [
            "unittest/case.py",
            "unittest/loader.py",
            "unittest/runner.py",
            "unittest/suite.py",
            "unittest/main.py",
        ]

        # Combine all testing framework excludes
        testing_excludes = pytest_excludes + pytest_executable_excludes + unittest_excludes

        # Don't filter out user test files - only internal framework files
        if any(exclude in filename_lower for exclude in testing_excludes):
            return False

    # Include everything else (application code including user test files)
    return True
