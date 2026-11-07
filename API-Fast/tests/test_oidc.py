"""OIDC relying-party tests: mocked discovery/JWKS/token endpoints + a local RSA key pair."""
from __future__ import annotations

import asyncio
import base64
import json
import time
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from authlib.jose import JsonWebKey, jwt as authlib_jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa

import src.config.settings as settings_mod
from src.security import oidc
from src.security.oidc import (
    OidcConfigError,
    OidcError,
    OidcProvider,
    assert_oidc_configured,
    code_challenge_s256,
    decode_transaction,
    extract_email,
)

ISSUER = "https://idp.test"
CLIENT_ID = "dpu-admin"
CLIENT_SECRET = "very-secret-client-secret"
REDIRECT_URI = "https://attendance.test/auth/sso/callback"
NONCE = "nonce-123"


def run(coro):
    return asyncio.run(coro)


# --------------------------------------------------------------------------- key material


def _rsa_pair(kid: str):
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv_pem = priv.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    pub_pem = priv.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    jwk = JsonWebKey.import_key(pub_pem, {"kty": "RSA", "kid": kid, "use": "sig", "alg": "RS256"}).as_dict()
    return priv_pem, jwk


def _ec_pair(kid: str):
    priv = ec.generate_private_key(ec.SECP256R1())
    priv_pem = priv.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    pub_pem = priv.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    jwk = JsonWebKey.import_key(pub_pem, {"kty": "EC", "kid": kid, "use": "sig", "alg": "ES256"}).as_dict()
    return priv_pem, jwk


RSA1_PRIV, RSA1_JWK = _rsa_pair("rsa-1")
RSA2_PRIV, RSA2_JWK = _rsa_pair("rsa-2")
ROGUE_PRIV, _ROGUE_JWK = _rsa_pair("rsa-1")  # same kid, different key
EC1_PRIV, EC1_JWK = _ec_pair("ec-1")


def make_claims(**overrides) -> dict:
    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "aud": CLIENT_ID,
        "sub": "user-42",
        "iat": now,
        "exp": now + 300,
        "nonce": NONCE,
        "email": "Alice@Example.com",
        "email_verified": True,
        "given_name": "Alice",
        "family_name": "Wonder",
        "preferred_username": "alice",
    }
    for key, value in overrides.items():
        if value is None:
            claims.pop(key, None)
        else:
            claims[key] = value
    return claims


def sign(claims: dict, priv_pem: bytes = RSA1_PRIV, kid: str = "rsa-1", alg: str = "RS256") -> str:
    header = {"alg": alg, "kid": kid}
    return authlib_jwt.encode(header, claims, priv_pem).decode("ascii")


def sign_hs256(claims: dict, secret: str) -> str:
    import jwt as pyjwt

    return pyjwt.encode(claims, secret, algorithm="HS256", headers={"kid": "rsa-1"})


# --------------------------------------------------------------------------- fake IdP


class FakeIdp:
    """httpx.MockTransport handler emulating discovery, JWKS and the token endpoint."""

    def __init__(self):
        self.jwks_keys = [RSA1_JWK, EC1_JWK]
        self.discovery_issuer = ISSUER
        self.calls: dict[str, int] = {"discovery": 0, "jwks": 0, "token": 0}
        self.token_requests: list[httpx.Request] = []
        self.token_response: dict | None = None
        self.token_status = 200

    def discovery_doc(self) -> dict:
        return {
            "issuer": self.discovery_issuer,
            "authorization_endpoint": f"{ISSUER}/authorize",
            "token_endpoint": f"{ISSUER}/token",
            "jwks_uri": f"{ISSUER}/jwks",
            "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post"],
            "id_token_signing_alg_values_supported": ["RS256", "ES256"],
        }

    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/.well-known/openid-configuration":
            self.calls["discovery"] += 1
            return httpx.Response(200, json=self.discovery_doc())
        if path == "/jwks":
            self.calls["jwks"] += 1
            return httpx.Response(200, json={"keys": self.jwks_keys})
        if path == "/token":
            self.calls["token"] += 1
            self.token_requests.append(request)
            if self.token_response is None:
                return httpx.Response(400, json={"error": "invalid_grant"})
            return httpx.Response(self.token_status, json=self.token_response)
        return httpx.Response(404)

    def client_factory(self):
        return httpx.AsyncClient(transport=httpx.MockTransport(self.handler), base_url="")


@pytest.fixture
def oidc_settings(monkeypatch):
    s = settings_mod.settings
    monkeypatch.setattr(s, "OIDC_ENABLED", True)
    monkeypatch.setattr(s, "OIDC_ISSUER", ISSUER)
    monkeypatch.setattr(s, "OIDC_CLIENT_ID", CLIENT_ID)
    monkeypatch.setattr(s, "OIDC_CLIENT_SECRET", CLIENT_SECRET)
    monkeypatch.setattr(s, "OIDC_REDIRECT_URI", REDIRECT_URI)
    monkeypatch.setattr(s, "OIDC_SCOPES", "openid profile email")
    monkeypatch.setattr(s, "OIDC_CLOCK_SKEW_SECONDS", 0)
    monkeypatch.setattr(s, "SECRET_KEY", "unit-test-secret-key-that-is-long-enough-0123456789")
    return s


@pytest.fixture
def idp(oidc_settings):
    return FakeIdp()


@pytest.fixture
def provider(idp):
    return OidcProvider(client_factory=idp.client_factory)


# --------------------------------------------------------------------------- ID token verification


def test_valid_rs256_token(provider):
    claims = run(provider.verify_id_token(sign(make_claims()), NONCE))
    assert claims["sub"] == "user-42"
    assert claims["email"] == "Alice@Example.com"
    assert extract_email(claims) == "alice@example.com"


def test_valid_es256_token(provider):
    token = sign(make_claims(), EC1_PRIV, kid="ec-1", alg="ES256")
    claims = run(provider.verify_id_token(token, NONCE))
    assert claims["sub"] == "user-42"


def test_wrong_issuer_rejected(provider):
    token = sign(make_claims(iss="https://evil.test"))
    with pytest.raises(OidcError) as exc:
        run(provider.verify_id_token(token, NONCE))
    assert exc.value.status_code == 401
    assert "iss" in exc.value.detail


def test_wrong_audience_rejected(provider):
    token = sign(make_claims(aud="some-other-client"))
    with pytest.raises(OidcError) as exc:
        run(provider.verify_id_token(token, NONCE))
    assert "aud" in exc.value.detail


def test_audience_list_without_azp_rejected(provider):
    token = sign(make_claims(aud=[CLIENT_ID, "other-app"]))
    with pytest.raises(OidcError) as exc:
        run(provider.verify_id_token(token, NONCE))
    assert "azp" in exc.value.detail


def test_expired_token_rejected(provider):
    now = int(time.time())
    token = sign(make_claims(iat=now - 600, exp=now - 60))
    with pytest.raises(OidcError) as exc:
        run(provider.verify_id_token(token, NONCE))
    assert "expired" in exc.value.detail


def test_bad_signature_rejected(provider):
    token = sign(make_claims(), ROGUE_PRIV, kid="rsa-1")
    with pytest.raises(OidcError) as exc:
        run(provider.verify_id_token(token, NONCE))
    assert "signature" in exc.value.detail


def test_missing_nonce_rejected(provider):
    token = sign(make_claims(nonce=None))
    with pytest.raises(OidcError) as exc:
        run(provider.verify_id_token(token, NONCE))
    assert "nonce" in exc.value.detail


def test_wrong_nonce_rejected(provider):
    token = sign(make_claims(nonce="replayed-nonce"))
    with pytest.raises(OidcError) as exc:
        run(provider.verify_id_token(token, NONCE))
    assert "nonce" in exc.value.detail


def test_empty_expected_nonce_refused(provider):
    with pytest.raises(OidcError) as exc:
        run(provider.verify_id_token(sign(make_claims()), ""))
    assert exc.value.status_code == 400


def test_hs256_with_app_secret_rejected(provider, oidc_settings):
    """The legacy forgery vector: HS256 signed with the app SECRET_KEY must not log in."""
    token = sign_hs256(make_claims(), oidc_settings.SECRET_KEY)
    with pytest.raises(OidcError) as exc:
        run(provider.verify_id_token(token, NONCE))
    assert "algorithm" in exc.value.detail


def test_alg_none_rejected(provider):
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "kid": "rsa-1"}).encode()).rstrip(b"=")
    body = base64.urlsafe_b64encode(json.dumps(make_claims()).encode()).rstrip(b"=")
    token = f"{header.decode()}.{body.decode()}."
    with pytest.raises(OidcError):
        run(provider.verify_id_token(token, NONCE))


def test_unverified_email_rejected():
    with pytest.raises(OidcError) as exc:
        extract_email(make_claims(email_verified=False))
    assert exc.value.status_code == 401


def test_missing_email_rejected():
    with pytest.raises(OidcError) as exc:
        extract_email(make_claims(email=None, preferred_username="alice"))
    assert exc.value.status_code == 400


# --------------------------------------------------------------------------- JWKS caching & rotation


def test_jwks_cached_between_verifications(provider, idp):
    run(provider.verify_id_token(sign(make_claims()), NONCE))
    run(provider.verify_id_token(sign(make_claims()), NONCE))
    assert idp.calls["discovery"] == 1
    assert idp.calls["jwks"] == 1


def test_key_rotation_refetches_jwks(provider, idp):
    run(provider.verify_id_token(sign(make_claims()), NONCE))
    assert idp.calls["jwks"] == 1
    # IdP rotates: publishes rsa-2 and signs with it
    idp.jwks_keys = [RSA2_JWK]
    token = sign(make_claims(), RSA2_PRIV, kid="rsa-2")
    claims = run(provider.verify_id_token(token, NONCE))
    assert claims["sub"] == "user-42"
    assert idp.calls["jwks"] == 2


def test_unknown_kid_after_refresh_rejected(provider, idp):
    token = sign(make_claims(), RSA2_PRIV, kid="rsa-2")
    with pytest.raises(OidcError) as exc:
        run(provider.verify_id_token(token, NONCE))
    assert "unknown key" in exc.value.detail
    assert idp.calls["jwks"] == 2  # initial fetch + one forced refresh


def test_discovery_issuer_mismatch_rejected(provider, idp):
    idp.discovery_issuer = "https://someone-else.test"
    with pytest.raises(OidcError) as exc:
        run(provider.discovery())
    assert exc.value.status_code == 503
    assert "issuer" in exc.value.detail


# --------------------------------------------------------------------------- PKCE + transaction


def test_start_builds_pkce_request_and_txn(provider):
    result = run(provider.build_authorization_request(company_id="11111111-1111-1111-1111-111111111111", return_to="/company/home"))
    url = urlparse(result["authorizeUrl"])
    qs = {k: v[0] for k, v in parse_qs(url.query).items()}
    assert url.scheme == "https" and url.netloc == "idp.test" and url.path == "/authorize"
    assert qs["response_type"] == "code"
    assert qs["client_id"] == CLIENT_ID
    assert qs["redirect_uri"] == REDIRECT_URI
    assert "openid" in qs["scope"].split()
    assert qs["code_challenge_method"] == "S256"
    assert qs["state"] == result["state"]

    txn = decode_transaction(result["txn"], result["state"])
    assert txn.nonce == qs["nonce"]
    assert txn.company_id == "11111111-1111-1111-1111-111111111111"
    assert txn.return_to == "/company/home"
    assert code_challenge_s256(txn.code_verifier) == qs["code_challenge"]
    assert 43 <= len(txn.code_verifier) <= 128
    # the verifier must never leave through the IdP URL
    assert txn.code_verifier not in result["authorizeUrl"]


def test_txn_state_mismatch_rejected(provider):
    result = run(provider.build_authorization_request())
    with pytest.raises(OidcError) as exc:
        decode_transaction(result["txn"], "tampered-state")
    assert exc.value.status_code == 400


def test_txn_tampered_signature_rejected(provider):
    result = run(provider.build_authorization_request())
    head, body, sig = result["txn"].split(".")
    with pytest.raises(OidcError):
        decode_transaction(f"{head}.{body}.{sig[:-3]}abc", result["state"])


def test_txn_expired_rejected(provider, monkeypatch):
    monkeypatch.setattr(settings_mod.settings, "OIDC_LOGIN_TXN_TTL_SECONDS", -120)
    result = run(provider.build_authorization_request())
    with pytest.raises(OidcError) as exc:
        decode_transaction(result["txn"], result["state"])
    assert "expired" in exc.value.detail


def test_login_with_code_end_to_end(provider, idp):
    start = run(provider.build_authorization_request())
    txn = decode_transaction(start["txn"], start["state"])
    idp.token_response = {
        "access_token": "at-1",
        "token_type": "Bearer",
        "id_token": sign(make_claims(nonce=txn.nonce)),
    }
    claims, got_txn = run(provider.login_with_code("auth-code-1", start["state"], start["txn"]))
    assert claims["sub"] == "user-42"
    assert got_txn.state == start["state"]

    req = idp.token_requests[-1]
    form = {k: v[0] for k, v in parse_qs(req.content.decode()).items()}
    assert form["grant_type"] == "authorization_code"
    assert form["code"] == "auth-code-1"
    assert form["redirect_uri"] == REDIRECT_URI
    assert code_challenge_s256(form["code_verifier"]) == code_challenge_s256(txn.code_verifier)
    assert req.headers["Authorization"].startswith("Basic ")


def test_login_with_code_nonce_mismatch(provider, idp):
    start = run(provider.build_authorization_request())
    idp.token_response = {"access_token": "at", "token_type": "Bearer", "id_token": sign(make_claims(nonce="other"))}
    with pytest.raises(OidcError) as exc:
        run(provider.login_with_code("code", start["state"], start["txn"]))
    assert "nonce" in exc.value.detail


def test_login_with_code_token_endpoint_error(provider, idp):
    start = run(provider.build_authorization_request())
    idp.token_response = None  # -> 400 invalid_grant
    with pytest.raises(OidcError) as exc:
        run(provider.login_with_code("bad-code", start["state"], start["txn"]))
    assert exc.value.status_code == 401
    assert "invalid_grant" in exc.value.detail


def test_login_with_code_response_without_id_token(provider, idp):
    start = run(provider.build_authorization_request())
    idp.token_response = {"access_token": "at", "token_type": "Bearer"}
    with pytest.raises(OidcError) as exc:
        run(provider.login_with_code("code", start["state"], start["txn"]))
    assert "id_token" in exc.value.detail


# --------------------------------------------------------------------------- settings fail-fast


def test_assert_oidc_configured_disabled_is_noop(monkeypatch):
    s = settings_mod.settings
    monkeypatch.setattr(s, "OIDC_ENABLED", False)
    monkeypatch.setattr(s, "OIDC_ISSUER", "")
    assert_oidc_configured()


def test_assert_oidc_configured_fails_fast(monkeypatch):
    s = settings_mod.settings
    monkeypatch.setattr(s, "OIDC_ENABLED", True)
    monkeypatch.setattr(s, "OIDC_ISSUER", "http://idp.internal")  # plain http, non-local
    monkeypatch.setattr(s, "OIDC_CLIENT_ID", "")
    monkeypatch.setattr(s, "OIDC_REDIRECT_URI", "")
    monkeypatch.setattr(s, "OIDC_SCOPES", "profile")
    with pytest.raises(OidcConfigError) as exc:
        assert_oidc_configured()
    msg = str(exc.value)
    assert "OIDC_ISSUER" in msg and "OIDC_CLIENT_ID" in msg and "OIDC_REDIRECT_URI" in msg and "openid" in msg


def test_assert_oidc_configured_ok(oidc_settings):
    assert_oidc_configured()


# --------------------------------------------------------------------------- HTTP routes (no DB needed)


@pytest.fixture
def client(idp, provider, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from src.config.database import get_db
    from src.routes import auth_routes

    oidc.set_provider(provider)
    app = FastAPI()
    app.include_router(auth_routes.router, prefix="/auth")

    async def _no_db():
        yield None

    app.dependency_overrides[get_db] = _no_db
    try:
        yield TestClient(app)
    finally:
        oidc.set_provider(None)


def test_status_and_start_routes(client):
    status = client.get("/auth/sso/oidc/status").json()
    assert status["enabled"] is True and status["issuer"] == ISSUER

    started = client.post("/auth/sso/oidc/start", json={"companyId": "11111111-1111-1111-1111-111111111111"}).json()
    assert started["authorizeUrl"].startswith(f"{ISSUER}/authorize?")
    assert started["state"] and started["txn"]

    bad = client.post("/auth/sso/oidc/start", json={"returnTo": "https://evil.test/phish"})
    assert bad.status_code == 400


def test_callback_route_rejects_bad_txn(client):
    resp = client.post("/auth/sso/oidc/callback", json={"code": "c", "state": "s", "txn": "garbage"})
    assert resp.status_code == 400
    legacy = client.post("/auth/sso/oidc", json={"idToken": "forged"})
    assert legacy.status_code == 422  # old self-signed idToken contract no longer exists


def test_routes_disabled_return_501(client, monkeypatch):
    monkeypatch.setattr(settings_mod.settings, "OIDC_ENABLED", False)
    assert client.get("/auth/sso/oidc/status").json()["enabled"] is False
    assert client.post("/auth/sso/oidc/start", json={}).status_code == 501
