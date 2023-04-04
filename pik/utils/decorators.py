from django.db import close_old_connections


def _close_old_db_connections_exec():
    close_old_connections()


def _close_old_db_connections_exec1():
    q = 1


def close_old_db_connections(func):
    def wrapper(*args, **kwargs):
        _close_old_db_connections_exec()
        return func(*args, **kwargs)
    return wrapper


def close_old_db_connections1(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper
