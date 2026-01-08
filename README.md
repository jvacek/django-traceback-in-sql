# django-traceback-in-sql

[![Test Suite](https://github.com/jvacek/django-traceback-in-sql/actions/workflows/test.yml/badge.svg)](https://github.com/jvacek/django-traceback-in-sql/actions/workflows/test.yml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

[![PyPi Version](https://img.shields.io/pypi/v/django-traceback-in-sql.svg)](https://pypi.python.org/pypi/django-traceback-in-sql)
[![image](https://img.shields.io/pypi/l/django-traceback-in-sql.svg)](https://github.com/astral-sh/django-traceback-in-sql/blob/main/LICENSE)
[![Supported Python Versions](https://img.shields.io/pypi/pyversions/django-traceback-in-sql.svg)](https://pypi.python.org/pypi/django-traceback-in-sql)
[![Supported Django versions](https://img.shields.io/pypi/frameworkversions/django/django-traceback-in-sql)](https://pypi.python.org/pypi/django-traceback-in-sql)

Annotates the stacktrace into the SQL query as a comment at runtime. Helpful for tracking down where queries are ran from within code, for example for analysing query counts in unit tests when trying to prevent N+1s.

## Compatibility

- Python 3.9–3.13
- Django 4.2, 5.2
- SQLite, PostgreSQL, MySQL

## Quick Examples

### Find N+1 queries in Django unit tests

```python
from django.contrib.auth import get_user_model
from django.test import TestCase
from sql_traceback import sql_traceback


User = get_user_model()


class Test(TestCase):
    def test_something(self):
        with sql_traceback(), self.assertNumQueries(0):
            _ = User.objects.count()
```

If the assert gets triggered, you will see something like the following output:

```text
E   AssertionError: 1 != 0 : 1 queries executed, 0 expected
E   Captured queries were:
E   1. SELECT COUNT(*) AS `__count` FROM `auth_user`
E   /*
E   STACKTRACE:
E   # /path/to/tests/test_test_test.py:12 in test_something
E   */
```

### In pytest-django tests

The above equivalent would look like so

```python
import pytest
from django.contrib.auth import get_user_model
from sql_traceback import sql_traceback


User = get_user_model()


@pytest.mark.django_db
def test_something(django_assert_num_queries):
    with sql_traceback(), django_assert_num_queries(0):
        _ = User.objects.count()
```

and when `pytest` is ran with the `-v` flag, you will see the following in the output

```text
E               Queries:
E               ========
E
E               SELECT COUNT(*) AS `__count` FROM `auth_user`
E               /*
E               STACKTRACE:
E               # /path/to/tests/tests/test_test_test.py:12 in test_something
E               */
```

### As a context manager

```python
from django.db import connection
from sql_traceback import sql_traceback
from services import get_user_count

with sql_traceback():
    get_user_count()

print(connection.queries[-1]['sql'])
```

Should print output

```text
SELECT COUNT(*) AS "__count" FROM "auth_user"
/*
STACKTRACE:
# /path/to/project/services.py:5 in get_user_count
*/
```

### As a decorator

```python
from sql_traceback import SqlTraceback

@SqlTraceback()
def get_users():
    return User.objects.filter(is_active=True)
```

### Programmatic Access to Traceback Information

When used as a context manager with the `as` clause, `sql_traceback()` returns a collector that provides programmatic access to executed queries and their stack frames:

```python
from sql_traceback import sql_traceback
from django.contrib.auth import get_user_model

User = get_user_model()

with sql_traceback() as collector:
    User.objects.count()
    User.objects.filter(username="admin").exists()

# Access all queries and their stack frames
for query in collector.queries:
    print(f"SQL: {query.sql}")
    for frame in query.frames:
        print(f"  {frame.path}:{frame.line} in {frame.name}")

# Convenience property: access frames from the last query only
for frame in collector.frames:
    print(f"{frame.path}:{frame.line} in {frame.name}")
```

The collector provides:

- `collector.queries` - List of `QueryInfo` objects, one per executed query
- `collector.frames` - Convenience property returning frames from the last query

Each `QueryInfo` object has:

- `sql` - The SQL query string (with traceback comment)
- `frames` - List of `StackFrame` objects

Each `StackFrame` object has:

- `path` - File path where the frame is located
- `line` - Line number in the file
- `name` - Function or method name

Note: Programmatic access is only available when using the context manager form with `as`. The decorator form (`@SqlTraceback()`) does not provide access to the collector.

## Configuration

Optional settings in your Django `settings.py`:

```python
SQL_TRACEBACK_ENABLED = True                      # Enable/disable stacktracing (default: True)
SQL_TRACEBACK_MAX_FRAMES = 15                     # Max number of stack frames (default: 15)
SQL_TRACEBACK_FILTER_SITEPACKAGES = True          # Filter out third-party packages (e.g., **django**, requests, pluggy, etc.) (default: True)
SQL_TRACEBACK_FILTER_TESTING_FRAMEWORKS = True    # Filter out pytest/unittest frames (pytest + unittest) (default: True)
SQL_TRACEBACK_FILTER_STDLIB = True                # Filter out Python standard library frames (e.g., threading, contextlib, etc.) (default: True)
SQL_TRACEBACK_MIN_APP_FRAMES = 1                  # Minimum application frames required (default: 1)
```
