from django.test import TestCase
from django.contrib.auth import get_user_model
from sql_traceback import sql_traceback

User = get_user_model()


class Test(TestCase):
    def test_something(self):
        with sql_traceback(), self.assertNumQueries(0):
            _ = User.objects.count()
