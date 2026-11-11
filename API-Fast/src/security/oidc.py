"""OpenID Connect relying party (RP) for enterprise SSO.

Implements the Authorization Code flow with PKCE (RFC 7636) against a single
configured IdP:

* provider discovery (``/.well-known/openid-configuration``) with issuer check
* JWKS fetch + cache, refetch on unknown ``kid`` (key rotation) with a
  refresh rate limit
* ID token verification with asymmetric algorithms only (``RS256``/``ES256``)
  and ``iss`` / ``aud`` / ``exp`` / ``iat`` / ``nonce`` / ``azp`` checks
* a stateless, HS256-signed login transaction (``txn``) that carries the
  ``state``, ``nonce`` and PKCE ``code_verifier`` so the flow works across API
  replicas without shared storage.  The browser keeps the ``txn`` in
  ``sessionStorage``; the ``code_verifier`` never travels through the IdP.

Library choice: ``authlib`` (RFC 7515/7517/7518 JOSE + ``CodeIDToken`` claim
validation) and ``httpx`` (already a dependency) for discovery/JWKS/token
requests.  ``python-jose`` was rejected: it is barely maintained and had
signature-related CVEs (2024-33663/33664).  ``PyJWT`` stays for the app's own
HS256 tokens so nothing else changes.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import secrets
import time
import warnings
from dataclasses import dataclass
from typing import Any, Callable, Optional
from urllib.parse import urlencode

import httpx
import jwt as pyjwt

from authlib.deprecate import AuthlibDeprecationWarning

with warnings.catch_warnings():
    # authlib 1.9 flags authlib.jose as deprecated in favour of joserfc; it stays
    # supported through the 1.x line, which is what requirements.txt pins.
    warnings.simplefilter("ignore", AuthlibDeprecationWarning)
    from authlib.jose import JsonWebKey, JsonWebToken
    from authlib.jose.errors import JoseError as AuthlibJoseError
    from authlib.oidc.core import CodeIDToken

# authlib 1.9 raises claim errors from joserfc while signature/decoding errors still
# come from authlib.jose; treat both families as "invalid token".
try:
    from joserfc.errors import JoseError as JoserfcJoseError
except Exception:  # pragma: no cover - older authlib without joserfc
    JoserfcJoseError = AuthlibJoseError
_JOSE_ERRORS: tuple[type[Exception], ...] = (AuthlibJoseError, JoserfcJoseError)

from ..config.settings import settings

logger = logging.getLogger("dpu.oidc")

ALLOWED_ID_TOKEN_ALGS = ("RS256", "ES256")
TXN_TYP = "oidc_txn"
DISCOVERY_SUFFIX = "/.well-known/openid-configuration"
_REQUIRED_DISCOVERY_KEYS = ("issuer", "authorization_endpoint", "token_endpoint", "jwks_uri")
_MIN_JWKS_REFRESH_INTERVAL = 30.0  # seconds; protects the IdP from kid-spray refetch storms


class OidcConfigError(RuntimeError):
    """Raised at startup when OIDC is enabled but incomplete."""


class OidcError(Exception):
    """Login-time failure; routes translate it to an HTTPException."""

    def __init__(self, detail: str, status_code: int = 401):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _issuer() -> str:
    return (settings.OIDC_ISSUER or "").strip().rstrip("/")


def oidc_enabled() -> bool:
    return bool(getattr(settings, "OIDC_ENABLED", False))


def _is_local_http(url: str) -> bool:
    return url.startswith("http://localhost") or url.startswith("http://127.0.0.1")


def validate_oidc_settings(cfg=settings) -> list[str]:
    """Return a list of configuration problems (empty = OK)."""
    problems: list[str] = []
    issuer = (cfg.OIDC_ISSUER or "").strip()
    client_id = (cfg.OIDC_CLIENT_ID or "").strip()
    redirect_uri = (cfg.OIDC_REDIRECT_URI or "").strip()
    scopes = (cfg.OIDC_SCOPES or "").split()
    if not issuer:
        problems.append("OIDC_ISSUER is required")
    elif not (issuer.startswith("https://") or _is_local_http(issuer)):
        problems.append("OIDC_ISSUER must be an https:// URL (http allowed for localhost only)")
    if not client_id:
        problems.append("OIDC_CLIENT_ID is required")
    if not redirect_uri:
        problems.append("OIDC_REDIRECT_URI is required")
    elif not (redirect_uri.startswith("https://") or _is_local_http(redirect_uri)):
        problems.append("OIDC_REDIRECT_URI must be an absolute https:// URL (http allowed for localhost only)")
    if "openid" not in scopes:
        problems.append("OIDC_SCOPES must include 'openid'")
    return problems


def assert_oidc_configured(cfg=settings) -> None:
    """Fail fast at import/startup when OIDC_ENABLED=true but the RP is misconfigured."""
    if not bool(getattr(cfg, "OIDC_ENABLED", False)):
        return
    problems = validate_oidc_settings(cfg)
    if problems:
        raise OidcConfigError("OIDC_ENABLED=true but misconfigured: " + "; ".join(problems))


# --------------------------------------------------------------------------- PKCE / txn helpers


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def generate_code_verifier() -> str:
    # 64 random bytes -> 86 chars, inside the RFC 7636 43..128 range
    return _b64url(secrets.token_bytes(64))


def code_challenge_s256(verifier: str) -> str:
    return _b64url(hashlib.sha256(verifier.encode("ascii")).digest())


@dataclass
class LoginTransaction:
    state: str
    nonce: str
    code_verifier: str
    company_id: Optional[str] = None
    return_to: Optional[str] = None


def _txn_ttl() -> int:
    return int(getattr(settings, "OIDC_LOGIN_TXN_TTL_SECONDS", 600) or 600)


def encode_transaction(txn: LoginTransaction) -> str:
    now = int(time.time())
    payload: dict[str, Any] = {
        "typ": TXN_TYP,
        "state": txn.state,
        "nonce": txn.nonce,
        "cv": txn.code_verifier,
        "iat": now,
        "exp": now + _txn_ttl(),
    }
    if txn.company_id:
        payload["companyId"] = str(txn.company_id)
    if txn.return_to:
        payload["returnTo"] = txn.return_to
    return pyjwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decode_transaction(token: str, expected_state: str) -> LoginTransaction:
    try:
        payload = pyjwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except pyjwt.ExpiredSignatureError:
        raise OidcError("SSO login expired, please start again", 400) from None
    except Exception:
        raise OidcError("Invalid SSO login transaction", 400) from None
    if payload.get("typ") != TXN_TYP:
        raise OidcError("Invalid SSO login transaction", 400)
    state = payload.get("state") or ""
    if not expected_state or not secrets.compare_digest(state, expected_state):
        raise OidcError("SSO state mismatch", 400)
    return LoginTransaction(
        state=state,
        nonce=payload.get("nonce") or "",
        code_verifier=payload.get("cv") or "",
        company_id=payload.get("companyId"),
        return_to=payload.get("returnTo"),
    )


# --------------------------------------------------------------------------- provider


def _default_client_factory() -> httpx.AsyncClient:
    timeout = float(getattr(settings, "OIDC_HTTP_TIMEOUT_SECONDS", 10.0) or 10.0)
    return httpx.AsyncClient(timeout=timeout, follow_redirects=False)


@dataclass
class _Cached:
    value: Any = None
    fetched_at: float = 0.0


class OidcProvider:
    """Relying-party client for the configured issuer.

    ``client_factory`` is injectable so tests can plug an ``httpx.MockTransport``.
    """

    def __init__(self, client_factory: Optional[Callable[[], httpx.AsyncClient]] = None):
        self._client_factory = client_factory or _default_client_factory
        self._discovery = _Cached()
        self._jwks = _Cached()
        self._jwks_last_refresh_attempt = 0.0
        self._discovery_lock = asyncio.Lock()
        self._jwks_lock = asyncio.Lock()
        self._jwt = JsonWebToken(list(ALLOWED_ID_TOKEN_ALGS))

    # ----- configuration accessors
    @property
    def issuer(self) -> str:
        return _issuer()

    @property
    def client_id(self) -> str:
        return (settings.OIDC_CLIENT_ID or "").strip()

    @property
    def client_secret(self) -> str:
        return (getattr(settings, "OIDC_CLIENT_SECRET", "") or "").strip()

    @property
    def redirect_uri(self) -> str:
        return (getattr(settings, "OIDC_REDIRECT_URI", "") or "").strip()

    @property
    def scopes(self) -> str:
        return " ".join((getattr(settings, "OIDC_SCOPES", "") or "openid profile email").split())

    @property
    def _cache_ttl(self) -> float:
        return float(getattr(settings, "OIDC_JWKS_CACHE_SECONDS", 3600) or 3600)

    @property
    def _leeway(self) -> int:
        return int(getattr(settings, "OIDC_CLOCK_SKEW_SECONDS", 60) or 60)

    def reset_cache(self) -> None:
        self._discovery = _Cached()
        self._jwks = _Cached()
        self._jwks_last_refresh_attempt = 0.0

    # ----- HTTP
    async def _get_json(self, url: str) -> dict:
        async with self._client_factory() as client:
            try:
                resp = await client.get(url, headers={"Accept": "application/json"})
            except httpx.HTTPError as exc:
                raise OidcError(f"OIDC provider unreachable: {exc.__class__.__name__}", 503) from exc
        if resp.status_code != 200:
            raise OidcError(f"OIDC provider returned HTTP {resp.status_code} for {url}", 503)
        try:
            data = resp.json()
        except ValueError:
            raise OidcError("OIDC provider returned invalid JSON", 503) from None
        if not isinstance(data, dict):
            raise OidcError("OIDC provider returned an unexpected document", 503)
        return data

    # ----- discovery
    async def discovery(self) -> dict:
        now = time.monotonic()
        if self._discovery.value is not None and now - self._discovery.fetched_at < self._cache_ttl:
            return self._discovery.value
        async with self._discovery_lock:
            now = time.monotonic()
            if self._discovery.value is not None and now - self._discovery.fetched_at < self._cache_ttl:
                return self._discovery.value
            doc = await self._get_json(self.issuer + DISCOVERY_SUFFIX)
            missing = [k for k in _REQUIRED_DISCOVERY_KEYS if not doc.get(k)]
            if missing:
                raise OidcError(f"OIDC discovery document missing: {', '.join(missing)}", 503)
            if str(doc["issuer"]).rstrip("/") != self.issuer:
                # OIDC Discovery 4.3: issuer in the document MUST match the one we asked for
                raise OidcError("OIDC discovery issuer mismatch", 503)
            self._discovery = _Cached(value=doc, fetched_at=now)
            return doc

    # ----- JWKS
    async def _fetch_jwks(self) -> Any:
        doc = await self.discovery()
        data = await self._get_json(doc["jwks_uri"])
        keys = data.get("keys")
        if not isinstance(keys, list) or not keys:
            raise OidcError("OIDC JWKS document has no keys", 503)
        try:
            key_set = JsonWebKey.import_key_set(data)
        except Exception:
            raise OidcError("OIDC JWKS document is invalid", 503) from None
        self._jwks = _Cached(value=key_set, fetched_at=time.monotonic())
        return key_set

    async def jwks(self, force_refresh: bool = False) -> Any:
        now = time.monotonic()
        fresh = self._jwks.value is not None and now - self._jwks.fetched_at < self._cache_ttl
        if fresh and not force_refresh:
            return self._jwks.value
        async with self._jwks_lock:
            now = time.monotonic()
            fresh = self._jwks.value is not None and now - self._jwks.fetched_at < self._cache_ttl
            if fresh and not force_refresh:
                return self._jwks.value
            if force_refresh and self._jwks.value is not None:
                if now - self._jwks_last_refresh_attempt < _MIN_JWKS_REFRESH_INTERVAL:
                    return self._jwks.value
                self._jwks_last_refresh_attempt = now
            return await self._fetch_jwks()

    # ----- ID token
    @staticmethod
    def _peek_header(id_token: str) -> dict:
        try:
            header_b64 = id_token.split(".")[0]
            padded = header_b64 + "=" * (-len(header_b64) % 4)
            header = json.loads(base64.urlsafe_b64decode(padded))
        except Exception:
            raise OidcError("Malformed ID token", 401) from None
        if not isinstance(header, dict):
            raise OidcError("Malformed ID token", 401)
        return header

    def _claims_options(self) -> dict:
        return {
            "iss": {"essential": True, "value": self.issuer},
            "aud": {"essential": True, "value": self.client_id},
            "exp": {"essential": True},
            "iat": {"essential": True},
            "sub": {"essential": True},
        }

    async def verify_id_token(
        self,
        id_token: str,
        nonce: str,
        access_token: Optional[str] = None,
    ) -> dict:
        """Verify signature + standard claims; returns the claims dict. Raises OidcError."""
        if not nonce:
            raise OidcError("SSO login transaction has no nonce", 400)
        header = self._peek_header(id_token)
        alg = header.get("alg")
        if alg not in ALLOWED_ID_TOKEN_ALGS:
            raise OidcError(f"ID token algorithm not allowed: {alg}", 401)
        kid = header.get("kid")

        key_set = await self.jwks()
        if kid and not self._has_kid(key_set, kid):
            key_set = await self.jwks(force_refresh=True)
            if not self._has_kid(key_set, kid):
                raise OidcError("ID token signed with unknown key", 401)
        elif not kid and len(key_set.keys) != 1:
            raise OidcError("ID token has no kid and provider publishes multiple keys", 401)

        key = key_set.find_by_kid(kid) if kid else key_set.keys[0]
        params: dict[str, Any] = {"nonce": nonce, "client_id": self.client_id}
        if access_token:
            params["access_token"] = access_token
        try:
            claims = self._jwt.decode(
                id_token,
                key,
                claims_cls=CodeIDToken,
                claims_options=self._claims_options(),
                claims_params=params,
            )
            claims.validate(leeway=self._leeway)
        except _JOSE_ERRORS as exc:
            code = getattr(exc, "error", None) or exc.__class__.__name__
            description = getattr(exc, "description", None)
            detail = f"Invalid ID token: {code}" + (f" ({description})" if description else "")
            raise OidcError(detail, 401) from exc
        except OidcError:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("oidc id_token verification failed: %s", exc.__class__.__name__)
            raise OidcError("Invalid ID token", 401) from exc
        if "nonce" not in claims:
            raise OidcError("Invalid ID token: missing_claim nonce", 401)
        return dict(claims)

    @staticmethod
    def _has_kid(key_set: Any, kid: str) -> bool:
        return any(getattr(k, "kid", None) == kid for k in key_set.keys)

    # ----- authorization code flow
    async def build_authorization_request(
        self,
        company_id: Optional[str] = None,
        return_to: Optional[str] = None,
    ) -> dict:
        doc = await self.discovery()
        txn = LoginTransaction(
            state=secrets.token_urlsafe(32),
            nonce=secrets.token_urlsafe(32),
            code_verifier=generate_code_verifier(),
            company_id=str(company_id) if company_id else None,
            return_to=return_to,
        )
        query = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": self.scopes,
            "state": txn.state,
            "nonce": txn.nonce,
            "code_challenge": code_challenge_s256(txn.code_verifier),
            "code_challenge_method": "S256",
        }
        sep = "&" if "?" in doc["authorization_endpoint"] else "?"
        return {
            "authorizeUrl": doc["authorization_endpoint"] + sep + urlencode(query),
            "state": txn.state,
            "txn": encode_transaction(txn),
            "expiresIn": _txn_ttl(),
        }

    async def exchange_code(self, code: str, code_verifier: str) -> dict:
        doc = await self.discovery()
        form = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "code_verifier": code_verifier,
            "client_id": self.client_id,
        }
        auth = None
        if self.client_secret:
            methods = doc.get("token_endpoint_auth_methods_supported") or ["client_secret_basic"]
            if "client_secret_basic" in methods:
                auth = (self.client_id, self.client_secret)
            else:
                form["client_secret"] = self.client_secret
        async with self._client_factory() as client:
            try:
                post_kwargs: dict[str, Any] = {
                    "data": form,
                    "headers": {"Accept": "application/json"},
                }
                if auth is not None:
                    post_kwargs["auth"] = auth
                resp = await client.post(doc["token_endpoint"], **post_kwargs)
            except httpx.HTTPError as exc:
                raise OidcError(f"OIDC token endpoint unreachable: {exc.__class__.__name__}", 503) from exc
        try:
            body = resp.json()
        except ValueError:
            body = {}
        if resp.status_code != 200 or not isinstance(body, dict):
            err = body.get("error") if isinstance(body, dict) else None
            logger.warning("oidc token exchange failed status=%s error=%s", resp.status_code, err)
            raise OidcError(f"OIDC code exchange failed: {err or resp.status_code}", 401)
        if not body.get("id_token"):
            raise OidcError("OIDC token response has no id_token", 401)
        return body

    async def login_with_code(self, code: str, state: str, txn_token: str) -> tuple[dict, LoginTransaction]:
        """Full callback: verify txn/state, exchange the code, verify the ID token."""
        txn = decode_transaction(txn_token, state)
        if not code:
            raise OidcError("Missing authorization code", 400)
        tokens = await self.exchange_code(code, txn.code_verifier)
        claims = await self.verify_id_token(tokens["id_token"], txn.nonce, tokens.get("access_token"))
        return claims, txn


_provider: Optional[OidcProvider] = None


def get_provider() -> OidcProvider:
    global _provider
    if _provider is None:
        _provider = OidcProvider()
    return _provider


def set_provider(provider: Optional[OidcProvider]) -> None:
    """Test hook / dependency override."""
    global _provider
    _provider = provider


def extract_email(claims: dict) -> str:
    """Email used to map an IdP identity to a Member. Refuses unverified emails."""
    email = (claims.get("email") or claims.get("upn") or claims.get("preferred_username") or "").strip()
    if not email or "@" not in email:
        raise OidcError("OIDC token missing email claim", 400)
    if claims.get("email_verified") is False:
        raise OidcError("SSO email is not verified by the identity provider", 401)
    return email.lower()
