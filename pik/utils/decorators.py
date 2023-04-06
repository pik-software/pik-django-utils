from django.db import close_old_connections


def close_old_db_connections(func):
    def wrapper(*args, **kwargs):
        close_old_connections()
        return func(*args, **kwargs)
    return wrapper
