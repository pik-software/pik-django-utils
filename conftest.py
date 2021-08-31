from contextlib import contextmanager

import pytest
from celery.contrib.testing import worker, tasks  # noqa: pylint=unused-import
from django.test.utils import CaptureQueriesContext

from test_project import celery_app as django_celery_app


@pytest.fixture(scope='session')
def base_url(live_server):
    return live_server.url


# CELERY

@pytest.fixture(name='celery_session_app', scope='session')
def celery_session_app_fixture(request):
    """Session Fixture: Return app for session fixtures."""
    yield django_celery_app


@pytest.fixture(scope='session')
def celery_session_worker(request,
                          celery_session_app,
                          celery_worker_pool,
                          celery_worker_parameters):
    """Session Fixture: Start worker that lives throughout test suite."""
    with worker.start_worker(celery_session_app,
                             pool=celery_worker_pool,
                             **celery_worker_parameters) as worker_context:
        yield worker_context


@pytest.fixture(scope='function', autouse=True)
def _skip_sensitive(request):
    """Pytest-selenium patch: don't Skip destructive tests"""


# HELPERS

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
                    msg += '\n\nQueries:\n========\n\n%s' % '\n\n'.join(sqls)
                else:
                    msg += " (add -v option to show queries)"
                pytest.fail(msg)

    return _assert_num_queries
