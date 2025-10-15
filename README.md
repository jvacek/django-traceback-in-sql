# Django SQL Stacktrace

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
from sql_traceback import sql_traceback

with sql_traceback():
    user = User.objects.select_related('profile').get(id=1)
    user.profile.do_something()
```

### As a decorator

```python
from sql_traceback import SqlTraceback

@SqlTraceback()
def get_users():
    return User.objects.filter(is_active=True)
```

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
