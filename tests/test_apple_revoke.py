"""
Account deletion revokes the user's Sign in with Apple tokens (App Review 5.1.1(v)).
Apple's endpoints are faked with httpx.MockTransport; nothing leaves the machine.
"""
import asyncio
import base64
from urllib.parse import parse_qs

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException

from app.api.v1 import auth
from app.config import settings
from app.core import apple_revoke

APP = {"Authorization": "Bearer app-key-new"}
USER = "001234.abcdef"


@pytest.fixture
def siwa_key(monkeypatch):
    """A throwaway P-256 key standing in for the .p8 from Apple Developer > Keys."""
    key = ec.generate_private_key(ec.SECP256R1())
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    monkeypatch.setattr(settings, "APPLE_SIWA_KEY_ID", "KEY123")
    monkeypatch.setattr(settings, "APPLE_SIWA_PRIVATE_KEY_B64", base64.b64encode(pem).decode())
    return key


class FakeApple:
    """Records calls to Apple's token and revoke endpoints."""

    def __init__(self, exchange_status=200, exchange_body=None, revoke_status=200):
        self.calls = []
        self.exchange_status = exchange_status
        self.exchange_body = exchange_body if exchange_body is not None else {
            "access_token": "at", "refresh_token": "rt", "id_token": "it",
        }
        self.revoke_status = revoke_status

    def handler(self, request: httpx.Request) -> httpx.Response:
        form = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
        self.calls.append((str(request.url), form))
        if str(request.url) == apple_revoke.APPLE_TOKEN_URL:
            body = self.exchange_body if self.exchange_status == 200 else {"error": "invalid_grant"}
            return httpx.Response(self.exchange_status, json=body)
        return httpx.Response(self.revoke_status)

    @property
    def transport(self):
        return httpx.MockTransport(self.handler)


def revoke(code, apple):
    return asyncio.run(apple_revoke.revoke_with_authorization_code(code, transport=apple.transport))


def test_client_secret_is_signed_by_our_key_for_our_app(siwa_key):
    secret = apple_revoke.client_secret(now=1_000_000)

    assert jwt.get_unverified_header(secret) == {"alg": "ES256", "kid": "KEY123", "typ": "JWT"}
    claims = jwt.decode(
        secret, siwa_key.public_key(), algorithms=["ES256"],
        audience="https://appleid.apple.com", options={"verify_exp": False},
    )
    assert claims == {
        "iss": "TEAMID",
        "iat": 1_000_000,
        "exp": 1_000_300,
        "aud": "https://appleid.apple.com",
        "sub": "com.promptler.ios.PromptlerV27",
    }


def test_exchanges_the_code_then_revokes_the_refresh_token(siwa_key):
    apple = FakeApple()

    assert revoke("one-time-code", apple) is True

    (token_url, exchange), (revoke_url, revocation) = apple.calls
    assert token_url == apple_revoke.APPLE_TOKEN_URL
    assert exchange["code"] == "one-time-code"
    assert exchange["grant_type"] == "authorization_code"
    assert exchange["client_id"] == "com.promptler.ios.PromptlerV27"
    assert revoke_url == apple_revoke.APPLE_REVOKE_URL
    assert revocation["token"] == "rt"
    assert revocation["token_type_hint"] == "refresh_token"
    assert revocation["client_secret"] == exchange["client_secret"]


def test_falls_back_to_the_access_token_when_apple_sends_no_refresh_token(siwa_key):
    apple = FakeApple(exchange_body={"access_token": "at"})

    assert revoke("code", apple) is True
    assert apple.calls[1][1]["token"] == "at"
    assert apple.calls[1][1]["token_type_hint"] == "access_token"


def test_rejected_code_reports_failure_without_revoking(siwa_key):
    apple = FakeApple(exchange_status=400)

    assert revoke("expired-code", apple) is False
    assert len(apple.calls) == 1


def test_failed_revocation_reports_failure(siwa_key):
    assert revoke("code", FakeApple(revoke_status=400)) is False


def test_network_error_reports_failure_instead_of_raising(siwa_key):
    def boom(request):
        raise httpx.ConnectError("down")

    result = asyncio.run(apple_revoke.revoke_with_authorization_code("code", transport=httpx.MockTransport(boom)))
    assert result is False


def test_without_a_key_nothing_is_sent(monkeypatch):
    monkeypatch.setattr(settings, "APPLE_SIWA_KEY_ID", "")
    apple = FakeApple()

    assert revoke("code", apple) is False
    assert apple.calls == []


# ── DELETE /auth/apple/{id} ──

@pytest.fixture
def token_for(monkeypatch):
    def verify(token):
        if token.startswith("valid-for:"):
            return token.split(":", 1)[1]
        raise HTTPException(status_code=401, detail="Invalid identity token")

    monkeypatch.setattr(auth.apple_verifier, "verify_and_extract_user_id", verify)
    return lambda sub: f"valid-for:{sub}"


@pytest.fixture
def revoked_codes(monkeypatch):
    codes = []

    async def fake_revoke(code, transport=None):
        codes.append(code)
        return True

    monkeypatch.setattr(auth.apple_revoke, "revoke_with_authorization_code", fake_revoke)
    return codes


def test_delete_revokes_with_the_code_the_app_sends(client, token_for, revoked_codes):
    headers = {**APP, "X-Apple-Identity-Token": token_for(USER), "X-Apple-Authorization-Code": "one-time-code"}

    r = client.delete(f"/v1/auth/apple/{USER}", headers=headers)

    assert r.status_code == 404  # the fake DB has no profile; the Apple link is still revoked
    assert revoked_codes == ["one-time-code"]


def test_delete_without_a_code_does_not_revoke(client, token_for, revoked_codes):
    r = client.delete(f"/v1/auth/apple/{USER}", headers={**APP, "X-Apple-Identity-Token": token_for(USER)})

    assert r.status_code == 404
    assert revoked_codes == []


def test_unauthorized_delete_never_reaches_apple(client, token_for, revoked_codes):
    headers = {**APP, "X-Apple-Identity-Token": token_for("someone.else"), "X-Apple-Authorization-Code": "stolen"}

    r = client.delete(f"/v1/auth/apple/{USER}", headers=headers)

    assert r.status_code == 403
    assert revoked_codes == []
