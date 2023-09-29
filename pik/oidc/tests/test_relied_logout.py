from unittest.mock import patch, Mock
from urllib.parse import urlencode

import django.test
import pytest
from django.urls import reverse

from rest_framework import status


@pytest.mark.django_db
@django.test.override_settings(OIDC_PIK_CLIENT_ID="TEST_CLIENT_ID")
@patch("social_core.backends.open_id_connect.OpenIdConnectAuth.oidc_config",
       Mock(return_value={
           'end_session_endpoint': 'http://op/openid/end-session/'}))
def test_logout(client):
    client.session['id_token'] = '{testidtoken}'
    resp = client.get(reverse('admin:logout'))
    assert resp.status_code == status.HTTP_302_FOUND
    params = urlencode({
        "post_logout_redirect_uri": "http://testserver/logout/"})
    assert resp['Location'] == f'http://op/openid/end-session/?{params}'
    assert client.session.get('id_token') is None
