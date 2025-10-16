from django.contrib.auth.models import User


def get_user_count():
    return User.objects.count()
