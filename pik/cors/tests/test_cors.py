import pytest
import rest_framework.test
from corsheaders.middleware import ACCESS_CONTROL_ALLOW_ORIGIN
from pik.cors.models import Cors


CORS_HEADERS = {
    "HTTP_ORIGIN": "http://allien",
    "HTTP_REFERER": "http://allien",
}


PREFLIGHT_HEADERS = {
    'HTTP_ACCESS_CONTROL_REQUEST_METHOD': 'Authentication',
    **CORS_HEADERS
}


@pytest.mark.django_db
def test_cors_preflight_missing():
    client = rest_framework.test.APIClient()
    response = client.options("/login/", **PREFLIGHT_HEADERS)
    assert 'ACCESS_CONTROL_ALLOW_ORIGIN' not in response
    assert response.content == b''
    assert response.status_code == 200


@pytest.mark.django_db
def test_cors_preflight():
    Cors.objects.create(cors='allien')
    client = rest_framework.test.APIClient()
    response = client.options("/login/", **PREFLIGHT_HEADERS)
    assert response[ACCESS_CONTROL_ALLOW_ORIGIN] == "http://allien"
    assert response.content == b''
    assert response.status_code == 200


@pytest.mark.django_db
def test_cors_missing():
    client = rest_framework.test.APIClient()
    response = client.get("/login/", **CORS_HEADERS)
    assert 'ACCESS_CONTROL_ALLOW_ORIGIN' not in response
    assert response.status_code == 200


@pytest.mark.django_db
def test_cors():
    Cors.objects.create(cors='allien')
    client = rest_framework.test.APIClient()

    response = client.get("/login/", **CORS_HEADERS)
    assert response[ACCESS_CONTROL_ALLOW_ORIGIN] == "http://allien"
    assert response.status_code == 200
