import pytest
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIRequestFactory

from gateway.authentication import APIKeyAuthentication


def build_request(raw_key):
    return APIRequestFactory().post(
        "/api/v1/generate/",
        HTTP_AUTHORIZATION=f"Api-Key {raw_key}",
    )


@pytest.mark.django_db
def test_valid_api_key_authenticates_user(gateway_credentials):
    user, api_key, raw_key = gateway_credentials

    authenticated_user, authenticated_key = APIKeyAuthentication().authenticate(
        build_request(raw_key)
    )

    assert authenticated_user == user
    assert authenticated_key == api_key


@pytest.mark.django_db
def test_invalid_api_key_is_rejected():
    with pytest.raises(AuthenticationFailed, match="Invalid API key"):
        APIKeyAuthentication().authenticate(build_request("pg_invalid"))


@pytest.mark.django_db
def test_revoked_api_key_is_rejected(gateway_credentials):
    _, api_key, raw_key = gateway_credentials
    api_key.revoke()

    with pytest.raises(AuthenticationFailed, match="revoked"):
        APIKeyAuthentication().authenticate(build_request(raw_key))


@pytest.mark.django_db
def test_successful_authentication_updates_last_used_at(gateway_credentials):
    _, api_key, raw_key = gateway_credentials
    assert api_key.last_used_at is None

    APIKeyAuthentication().authenticate(build_request(raw_key))

    api_key.refresh_from_db()
    assert api_key.last_used_at is not None
