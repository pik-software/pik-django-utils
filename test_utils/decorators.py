# from django.db.utils import ConnectionHandler
#
#
# connections = ConnectionHandler()
#
#
# def reopen_db_connections(func):
#     def wrapper(*args, **kwargs):
#         for conn in connections.all():
#             conn.close()
#             conn.connect()
#         func(*args, **kwargs)
#     return wrapper
