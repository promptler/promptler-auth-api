"""
App Check: a copied API key without a fresh, Google-signed token from a real
install must not get through once enforcement is on.
"""
import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.config import settings
from app.core import app_check

PROJECT = "999734172564"
APP_ID = "1:999734172564:ios:225d857b60866a0d2c0d81"
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def make_token(key=KEY, sub=APP_ID, aud=None, iss=None, exp_in=3600):
    now = int(time.time())
    claims = {
        "sub": sub,
        "aud": aud or [f"projects/{PROJECT}", "projects/promptler-v27"],
        "iss": iss or f"https://firebaseappcheck.googleapis.com/{PROJECT}",
        "iat": now,
        "exp": now + exp_in,
    }
    return jwt.encode(claims, key, algorithm="RS256", headers={"typ": "JWT", "kid": "test"})


@pytest.fixture(autouse=True)
def app_check_on(monkeypatch):
    monkeypatch.setattr(settings, "APP_CHECK_PROJECT_NUMBER", PROJECT)
    monkeypatch.setattr(settings, "APP_CHECK_APP_IDS", APP_ID)
    monkeypatch.setattr(settings, "ENFORCE_APP_CHECK", True)
    fake = SimpleNamespace(get_signing_key_from_jwt=lambda token: SimpleNamespace(key=KEY.public_key()))
    monkeypatch.setattr(app_check, "_jwks", lambda: fake)


EVENT = "/v1/events/issue-report"


def post(client, token=None, key="app-key-new"):
    headers = {"Authorization": f"Bearer {key}"}
    if token:
        headers["X-Firebase-AppCheck"] = token
    return client.post(EVENT, json={}, headers=headers)


def test_valid_token_verifies():
    assert app_check.verify_app_check_token(make_token()) == APP_ID


@pytest.mark.parametrize("token", [
    make_token(key=OTHER_KEY),
    make_token(exp_in=-60),
    make_token(sub="1:999734172564:ios:someotherapp"),
    make_token(aud=["projects/123", "projects/other"]),
    make_token(iss="https://firebaseappcheck.googleapis.com/123"),
    "not-a-jwt",
])
def test_bad_tokens_fail(token):
    assert not app_check.app_check_passes(token)


def test_enforced_key_without_token_is_refused(client):
    r = post(client)
    assert r.status_code == 401
    assert r.json()["detail"] == "App verification failed"


def test_enforced_key_with_valid_token_gets_past_auth(client):
    r = post(client, token=make_token())
    assert r.status_code not in (401, 403), r.text  # 422: the empty body fails validation, after auth


def test_log_only_mode_lets_old_builds_through(client, monkeypatch):
    monkeypatch.setattr(settings, "ENFORCE_APP_CHECK", False)
    assert post(client).status_code not in (401, 403)


def test_admin_key_skips_app_check(client):
    assert post(client, key="admin-key").status_code not in (401, 403)
