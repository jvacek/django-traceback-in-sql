from services import get_user_count


def layer1():
    """First layer of function calls."""
    return layer2()


def layer2():
    """Second layer of function calls."""
    return layer3()


def layer3():
    """Third layer that calls the actual service."""
    return get_user_count()
