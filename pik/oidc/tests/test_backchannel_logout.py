from importlib import import_module
from unittest.mock import patch, Mock

from jose import JWTError
import pytest

import django.test
from django.conf import settings
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status


@pytest.fixture(name='backchannel_logout_url')
def backchannel_logout_url_fixture():
    return reverse(
        'auth-api:oidc_backchannel_logout', kwargs={'backend': 'pik'})


@pytest.fixture(name='session_store')
def session_store_fixture():
    return import_module(settings.SESSION_ENGINE).SessionStore()


@pytest.mark.django_db
def test_wrong_method(backchannel_logout_url):
    client = django.test.Client()
    response = client.get(backchannel_logout_url)
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.django_db
@patch('pik.oidc.backends.PIKOpenIdConnectAuth.'
       'validate_and_return_logout_token',
       Mock(return_value={'sid': 'test_sid'}))
def test_success(backchannel_logout_url, session_store):
    cache.set('oidc_sid_userdata_test_sid', ['userdata'])
    cache.set('oidc_sid_tokens_test_sid', ['token'])
    client = django.test.Client()
    session_key = client.session.session_key
    cache.set('oidc_sid_sessions_test_sid', [session_key])
    response = client.post(backchannel_logout_url)
    assert response.status_code == status.HTTP_200_OK
    assert cache.get('oidc_sessions_test_token') is None
    assert cache.get('oidc_userdata_test_token') is None
    assert cache.get('oidc_tokens_test_token') is None
    assert not client.session.exists(client.session.session_key)


@pytest.mark.django_db
@patch('social_core.backends.open_id_connect.OpenIdConnectAuth.find_valid_key',
       Mock)
@patch('jose.jwk.construct', Mock())
@patch('jose.jwt.decode',
       Mock(side_effect=JWTError('Signature verification failed')))
def test_wrong_sign(backchannel_logout_url):
    client = django.test.Client()
    response = client.post(backchannel_logout_url)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
@patch('jose.jwk.construct', Mock())
@patch('jose.jwt.decode',
       Mock(return_value={'aud': '24', 'iss': 'test_provider'}))
@patch('pik.oidc.backends.PIKOpenIdConnectAuth.find_valid_key',
       Mock)
@patch('pik.oidc.backends.PIKOpenIdConnectAuth.id_token_issuer',
       Mock(return_value="test_provider"))
@patch('pik.oidc.backends.PIKOpenIdConnectAuth.get_key_and_secret',
       Mock(return_value=('42', '')))
def test_wrong_client(backchannel_logout_url):
    cache.set('oidc_userdata_test_token', 'testuserinfo')
    client = django.test.Client()
    response = client.post(backchannel_logout_url)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.content == b'Token error: Invalid audience'
    assert cache.get('oidc_userdata_test_token') == 'testuserinfo'


@pytest.mark.django_db
@patch('social_core.backends.open_id_connect.OpenIdConnectAuth.find_valid_key',
       Mock(return_value=None))
def test_missing_token(backchannel_logout_url):
    cache.set('oidc_userdata_test_token', 'testuserinfo')
    client = django.test.Client()
    response = client.post(backchannel_logout_url)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert cache.get('oidc_userdata_test_token') == 'testuserinfo'
