import pytest


@pytest.fixture(name='pik_module', params=[
    'core', 'libs', 'utils'
])
def pik_module_fixture(request):
    return request.param


def test_import_pik_namespace():
    assert __import__('pik')


def test_import_pik_packages(pik_module):
    assert __import__(f'pik.{pik_module}')
