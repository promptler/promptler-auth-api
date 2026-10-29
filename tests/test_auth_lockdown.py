"""
The shared app key ships inside the iOS binary, so it must not be enough to
create, overwrite, edit or delete someone's profile on its own.
"""
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from app.api.v1 import auth

APP = {"Authorization": "Bearer app-key-new"}
OLD_APP = {"Authorization": "Bearer app-key-old"}
ADMIN = {"Authorization": "Bearer admin-key"}
USER = "001234.abcdef"


def sign_in_body(**extra):
    return {"apple_user_id": USER, "timestamp": datetime.now(timezone.utc).isoformat(), **extra}


@pytest.fixture
def token_for(monkeypatch):
    """Makes the Apple verifier accept tokens of the form 'valid-for:<sub>'."""
    def verify(token):
        if token.startswith("valid-for:"):
            return token.split(":", 1)[1]
        raise HTTPException(status_code=401, detail="Invalid identity token")

    monkeypatch.setattr(auth.apple_verifier, "verify_and_extract_user_id", verify)
    return lambda sub: f"valid-for:{sub}"


# ── API keys ──

def test_unknown_key_is_rejected(client):
    assert client.post("/v1/auth/apple", json=sign_in_body(), headers={"Authorization": "Bearer nope"}).status_code == 401


def test_old_and_new_app_keys_both_work_during_rotation(client, token_for):
    for headers in (APP, OLD_APP):
        r = client.post("/v1/auth/apple", json=sign_in_body(identity_token=token_for(USER)), headers=headers)
        assert r.status_code == 200, r.text


# ── POST /auth/apple ──

def test_sign_in_without_identity_token_is_rejected_before_touching_the_db(client, db):
    r = client.post("/v1/auth/apple", json=sign_in_body(), headers=APP)
    assert r.status_code == 401
    assert r.json()["detail"] == "Identity token required"
    assert not db.queried


def test_sign_in_with_another_users_token_is_rejected(client, db, token_for):
    r = client.post("/v1/auth/apple", json=sign_in_body(identity_token=token_for("someone.else")), headers=APP)
    assert r.status_code == 401
    assert not db.queried


def test_sign_in_with_invalid_token_is_rejected(client, db, token_for):
    r = client.post("/v1/auth/apple", json=sign_in_body(identity_token="forged"), headers=APP)
    assert r.status_code == 401
    assert not db.queried


def test_sign_in_with_matching_token_creates_the_profile(client, db, token_for):
    r = client.post("/v1/auth/apple", json=sign_in_body(identity_token=token_for(USER)), headers=APP)
    assert r.status_code == 200, r.text
    assert r.json()["created"] is True
    assert db.queried


# ── PATCH / DELETE /auth/apple/{id} ──

PATCH_BODY = {"device_profile": {"model": "iPhone"}, "timestamp": "2026-10-28T00:00:00Z"}


@pytest.mark.parametrize("method", ["patch", "delete"])
def test_app_key_alone_cannot_change_a_user(client, db, method):
    r = client.request(method.upper(), f"/v1/auth/apple/{USER}", json=PATCH_BODY if method == "patch" else None, headers=APP)
    assert r.status_code == 401
    assert not db.queried, "must refuse before looking the user up, so the route can't probe accounts"


@pytest.mark.parametrize("method", ["patch", "delete"])
def test_another_users_token_cannot_change_a_user(client, db, token_for, method):
    headers = {**APP, "X-Apple-Identity-Token": token_for("someone.else")}
    r = client.request(method.upper(), f"/v1/auth/apple/{USER}", json=PATCH_BODY if method == "patch" else None, headers=headers)
    assert r.status_code == 403
    assert not db.queried


@pytest.mark.parametrize("method", ["patch", "delete"])
def test_own_token_can_change_own_user(client, db, token_for, method):
    headers = {**APP, "X-Apple-Identity-Token": token_for(USER)}
    r = client.request(method.upper(), f"/v1/auth/apple/{USER}", json=PATCH_BODY if method == "patch" else None, headers=headers)
    assert r.status_code == 404  # authorized; the fake DB has no such user
    assert db.queried


@pytest.mark.parametrize("method", ["patch", "delete"])
def test_admin_key_can_change_any_user_without_a_token(client, db, method):
    r = client.request(method.upper(), f"/v1/auth/apple/{USER}", json=PATCH_BODY if method == "patch" else None, headers=ADMIN)
    assert r.status_code == 404
    assert db.queried
