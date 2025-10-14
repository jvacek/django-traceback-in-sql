# Configuration from Django settings with defaults
from typing import Any

from django.conf import settings


def _get_setting(name: str, default: Any) -> Any:
    """Get a setting value with a default fallback."""
    return getattr(settings, name, default)


TRACEBACK_ENABLED = _get_setting("SQL_TRACEBACK_ENABLED", True)
MAX_STACK_FRAMES = _get_setting("SQL_TRACEBACK_MAX_FRAMES", 15)
FILTER_SITEPACKAGES = _get_setting("SQL_TRACEBACK_FILTER_SITEPACKAGES", True)
FILTER_TESTING_FRAMEWORKS = _get_setting("SQL_TRACEBACK_FILTER_TESTING_FRAMEWORKS", True)
FILTER_STDLIB = _get_setting("SQL_TRACEBACK_FILTER_STDLIB", True)
MIN_APP_FRAMES = _get_setting("SQL_TRACEBACK_MIN_APP_FRAMES", 1)
