# SQL Stacktrace Context Manager

[![Test Suite](https://github.com/jvacek/django-traceback-in-sql/actions/workflows/test.yml/badge.svg)](https://github.com/jvacek/django-traceback-in-sql/actions/workflows/test.yml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

[![image](https://img.shields.io/pypi/v/django-traceback-in-sql.svg)](https://pypi.python.org/pypi/django-traceback-in-sql)
[![image](https://img.shields.io/pypi/l/django-traceback-in-sql.svg)](https://github.com/astral-sh/django-traceback-in-sql/blob/main/LICENSE)
[![image](https://img.shields.io/pypi/pyversions/django-traceback-in-sql.svg)](https://pypi.python.org/pypi/django-traceback-in-sql)
![PyPI - Versions from Framework Classifiers](https://img.shields.io/pypi/frameworkversions/django/django-traceback-in-sql)


A utility for adding Python stacktraces to Django SQL queries as comments.

This can help figuring out where are queries getting triggered from, for example for tracking down N+1 queries.

## Features

- **Targeted Application**: Apply stacktraces only where needed, rather than globally
- **Multiple Interfaces**: Available as a function-based context manager, class-based context manager, or decorator
- **Test Compatible**: Works seamlessly with Django's `assertNumQueries` and other test utilities
- **Stacktrace Filtering**: Focuses on application code by filtering out framework/library frames
- **More tests than code**: Tested on Python 3.9—3.13, Django 4.2 and 5.2, with SQLite, PostgreSQL, and MySQL as databases

## Usage

### As a Context Manager

```python
from sql_traceback import sql_traceback, SqlTraceback

# Function-based style
with sql_traceback():
    # Queries here will have stacktraces added
    user = User.objects.select_related('profile').get(id=1)
    user.profile.do_a_thing()

# or

with SqlTraceback():
    # Queries here will have stacktraces added
    user = User.objects.select_related('profile').get(id=1)
    user.profile.do_a_thing()
```

### With Django Tests

My preferred usecase as this will print out the location of the n+1 query (if there is one)

```python
from django.test import TestCase
from sql_traceback import sql_traceback

class MyTest(TestCase):
    def test_something(self):
        with sql_traceback(), self.assertNumQueries(1):
            user = User.objects.select_related('profile').get(id=1)
            user.profile.do_a_thing()
```

### As a Decorator

```python
from sql_traceback import SqlTraceback

@SqlTraceback()
def get_active_users():
    return User.objects.filter(is_active=True)
```

## Example SQL query Output

```SQL
SELECT "auth_user"."id", "auth_user"."username" FROM "auth_user" LIMIT 1;
/*
STACKTRACE:
# /path/to/my_project/my_app/views.py:42 in get_user
# /path/to/my_project/my_app/services.py:23 in fetch_data
*/;
```

## Configuration

The context manager behavior can be controlled through environment variables:

- `ENABLE_SQL_TRACEBACK=1` - Enable/disable stacktrace generation (default: enabled)
- `PRINT_SQL_TRACEBACKS=1` - Print stacktraces to stderr during tests (default: disabled)

## Development

### Running Tests

This project uses **tox** to test against multiple database backends (SQLite, PostgreSQL, MySQL) and multiple Python versions (3.10, 3.11, 3.12, 3.13).

**📚 For detailed testing documentation, see [TESTING.md](TESTING.md)**
**🚀 For quick setup instructions, see [QUICKSTART.md](QUICKSTART.md)**

#### Quick Start

```bash
# Build test container (one-time setup)
make build

# Start database containers
make up

# Run all tests (21 environments)
make test

# Or test specific combinations
make test TOX_ENV=py312-django52-sqlite
make test TOX_ENV=py312-django52-postgres
make test TOX_ENV=py310-django42-mysql
```

#### No Local Dependencies Needed!

All tests run inside Docker with UV managing multiple Python versions and tox handling test environments. Database drivers (psycopg, mysqlclient) are pre-installed in the container.

#### Test Specific Combinations

```bash
# Single environment
make test TOX_ENV=py312-django52-postgres
make test TOX_ENV=py313-django52-mysql

# Multiple environments
make test TOX_ENV="py312-django{42,52}-sqlite"

# All Django 5.2 environments
make test TOX_ENV="py{310,311,312,313}-django52-{sqlite,postgres,mysql}"

# See all available environments
docker-compose run --rm test tox list
```

#### Available Commands

```bash
make help              # Show all available commands and examples
make test              # Run all tests (21 environments)
make test TOX_ENV=...  # Run specific environment(s)
make build             # Build test container
make up                # Start database containers
make down              # Stop containers
make clean             # Remove containers and volumes
make shell             # Open shell in test container
```

### CI/CD

The project uses GitHub Actions with a test matrix covering:

- **Python versions**: 3.10, 3.11, 3.12, 3.13
- **Django versions**: 4.2 LTS, 5.2 LTS
- **Databases**: SQLite, PostgreSQL, MySQL
- **Total**: 21 test combinations run in parallel

The CI uses the same Docker + tox setup as local development, ensuring consistency.

See the [GitHub Actions workflow](.github/workflows/test.yml) for implementation details.
