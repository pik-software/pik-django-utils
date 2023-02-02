from contextlib import contextmanager
import pytest
from celery.contrib.testing import worker, tasks  # noqa: pylint=unused-import
from django.core.cache import caches
from django.test.utils import CaptureQueriesContext


@pytest.fixture(autouse=True)
def clear_caches():
    for cache in caches.all():
        cache.clear()


@pytest.fixture(scope='function')
def assert_num_queries_lte(pytestconfig):
    from django.db import connection  # noqa: django should be initiated

    @contextmanager
    def _assert_num_queries(num):
        with CaptureQueriesContext(connection) as context:
            yield
            queries = len(context)
            if queries > num:
                msg = f"Expected to perform less then {num} queries" \
                      f" but {queries} were done"
                if pytestconfig.getoption('verbose') > 0:
                    sqls = (q['sql'] for q in context.captured_queries)
                    sqls_formatted = '\n\n'.join(sqls)
                    msg += f'\n\nQueries:\n========\n\n{sqls_formatted}'
                else:
                    msg += " (add -v option to show queries)"
                pytest.fail(msg)

    return _assert_num_queries
