# SQL Stacktrace Context Manager

A utility for adding Python stacktraces to Django SQL queries as comments.

This can help figuring out where are queries getting triggered from, for example for tracking down N+1 queries.

## Features

- **Targeted Application**: Apply stacktraces only where needed, rather than globally
- **Multiple Interfaces**: Available as a function-based context manager, class-based context manager, or decorator
- **Test Compatible**: Works seamlessly with Django's `assertNumQueries` and other test utilities
- **Stacktrace Filtering**: Focuses on application code by filtering out framework/library frames

## Usage

### As a Context Manager

```python
from sql_pythonstack import sql_stacktrace, SqlStacktrace

# Function-based style
with sql_stacktrace():
    # Queries here will have stacktraces added
    user = User.objects.select_related('profile').get(id=1)
    user.profile.do_a_thing()

# or

with SqlStacktrace():
    # Queries here will have stacktraces added
    user = User.objects.select_related('profile').get(id=1)
    user.profile.do_a_thing()
```

### With Django Tests

My preferred usecase as this will print out the location of the n+1 query (if there is one)

```python
from django.test import TestCase
from sql_pythonstack import sql_stacktrace

class MyTest(TestCase):
    def test_something(self):
        with sql_stacktrace(), self.assertNumQueries(1):
            user = User.objects.select_related('profile').get(id=1)
            user.profile.do_a_thing()
```

### As a Decorator

```python
from sql_pythonstack import SqlStacktrace

@SqlStacktrace()
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

- `ENABLE_SQL_STACKTRACE=1` - Enable/disable stacktrace generation (default: enabled)
- `PRINT_SQL_STACKTRACES=1` - Print stacktraces to stderr during tests (default: disabled)
