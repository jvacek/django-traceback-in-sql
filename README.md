# Django SQL Stacktrace

[![Test Suite](https://github.com/jvacek/django-traceback-in-sql/actions/workflows/test.yml/badge.svg)](https://github.com/jvacek/django-traceback-in-sql/actions/workflows/test.yml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

[![PyPi Version](https://img.shields.io/pypi/v/django-traceback-in-sql.svg)](https://pypi.python.org/pypi/django-traceback-in-sql)
[![image](https://img.shields.io/pypi/l/django-traceback-in-sql.svg)](https://github.com/astral-sh/django-traceback-in-sql/blob/main/LICENSE)
[![Supported Python Versions](https://img.shields.io/pypi/pyversions/django-traceback-in-sql.svg)](https://pypi.python.org/pypi/django-traceback-in-sql)
[![Supported Django versions](https://img.shields.io/pypi/frameworkversions/django/django-traceback-in-sql)](https://pypi.python.org/pypi/django-traceback-in-sql)

## Quick Examples

### Find N+1 queries in tests

```python
from sql_traceback import sql_traceback

class MyTest(TestCase):
    def test_something(self):
        with sql_traceback(), self.assertNumQueries(1):
            users = User.objects.all()
            for user in users:
                print(user.profile.name)
```

If the assert gets triggered, you will see the following output:

```text
AssertionError: 2 != 1 : Unexpected queries detected:
1. SELECT "app_profile"."id", "app_profile"."user_id", "app_profile"."name" FROM "app_profile" WHERE "app_profile"."user_id" = 1
   /*
    STACKTRACE:
    # /path/to/my_project/views.py:42 in get_user
    # /path/to/my_project/services.py:23 in fetch_data
    */;
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
SQL_TRACEBACK_ENABLED = True              # Enable/disable (default: True)
SQL_TRACEBACK_MAX_FRAMES = 15             # Stack depth (default: 15)
SQL_TRACEBACK_FILTER_SITEPACKAGES = True  # Hide library frames (default: True)
```

## Compatibility

- Python 3.9–3.13
- Django 4.2, 5.2
- SQLite, PostgreSQL, MySQL
