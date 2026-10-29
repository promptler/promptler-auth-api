"""
Behind the Cloudflare Tunnel every request reaches the app from the proxy, so rate
limits must count the visitor's IP (CF-Connecting-IP), not the socket address.
Invalid tokens get one generic message; details stay in the server log.
"""
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.config import settings
from app.core.apple_auth import apple_verifier
from app.core.security import client_ip


def fake_request(headers=None, host="10.0.1.5"):
    return SimpleNamespace(headers={k.lower(): v for k, v in (headers or {}).items()}, client=SimpleNamespace(host=host))


def test_uses_cloudflare_visitor_ip():
    assert client_ip(fake_request({"CF-Connecting-IP": " 203.0.113.9 "})) == "203.0.113.9"


def test_two_visitors_behind_the_same_proxy_get_separate_buckets():
    a = client_ip(fake_request({"CF-Connecting-IP": "203.0.113.9"}))
    b = client_ip(fake_request({"CF-Connecting-IP": "198.51.100.7"}))
    assert a != b


def test_falls_back_to_socket_address_without_the_header():
    assert client_ip(fake_request()) == "10.0.1.5"


def test_header_ignored_when_trust_is_off(monkeypatch):
    monkeypatch.setattr(settings, "TRUST_CF_CONNECTING_IP", False)
    assert client_ip(fake_request({"CF-Connecting-IP": "203.0.113.9"})) == "10.0.1.5"


def test_no_client_at_all():
    assert client_ip(SimpleNamespace(headers={}, client=None)) == "unknown"


def test_garbage_identity_token_gets_a_generic_message():
    with pytest.raises(HTTPException) as e:
        apple_verifier.verify_token("forged.token.value")
    assert e.value.status_code == 401
    assert e.value.detail == "Invalid identity token"
