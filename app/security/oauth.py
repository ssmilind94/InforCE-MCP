"""Built-in OAuth2 authorization server for MCP clients using internally issued client IDs and secrets.

Grants:
  client_credentials          machine-to-machine clients
  authorization_code + PKCE   interactive MCP clients configured with a client ID/secret (auto-approved,
                              registered redirect URIs only; the secret is still required at the token endpoint)
  refresh_token
Tokens are stateless HS256 JWTs, so the server can scale out across Azure Web App instances.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlencode

import jwt
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response

from mcp.server.auth.provider import AccessToken, TokenVerifier

SCOPES = ("ln.read", "ln.write")
_PBKDF2_ITERATIONS = 200_000


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def hash_secret(secret: str, *, iterations: int = _PBKDF2_ITERATIONS) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", secret.encode(), salt, iterations)
    return f"pbkdf2_sha256${iterations}${_b64(salt)}${_b64(digest)}"


def verify_secret(secret: str, stored: str) -> bool:
    try:
        algo, iterations, salt, digest = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac("sha256", secret.encode(), _unb64(salt), int(iterations))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(candidate, _unb64(digest))


@dataclass(frozen=True)
class OAuthClient:
    client_id: str
    secret_hash: str
    name: str = ""
    scopes: tuple[str, ...] = SCOPES
    redirect_uris: tuple[str, ...] = ()


class ClientStore:
    def __init__(self, clients: list[OAuthClient]):
        self._clients = {c.client_id: c for c in clients}

    @classmethod
    def from_entries(cls, entries: list[dict]) -> ClientStore:
        return cls([
            OAuthClient(
                client_id=e["client_id"],
                secret_hash=e["secret_hash"],
                name=e.get("name", ""),
                scopes=tuple(e.get("scopes", SCOPES)),
                redirect_uris=tuple(e.get("redirect_uris", [])),
            )
            for e in entries
        ])

    @classmethod
    def load(cls, clients_json: str | None, clients_file: Path | None) -> ClientStore:
        if clients_json:
            return cls.from_entries(json.loads(clients_json))
        if clients_file and clients_file.exists():
            return cls.from_entries(json.loads(clients_file.read_text()))
        return cls([])

    def get(self, client_id: str | None) -> OAuthClient | None:
        return self._clients.get(client_id or "")

    def authenticate(self, client_id: str | None, secret: str | None) -> OAuthClient | None:
        client = self.get(client_id)
        if client and secret and verify_secret(secret, client.secret_hash):
            return client
        return None

    def __len__(self) -> int:
        return len(self._clients)


class TokenIssuer:
    def __init__(self, secret: str, issuer: str, audience: str, *, access_ttl: int = 3600,
                 refresh_ttl: int = 30 * 24 * 3600, code_ttl: int = 300):
        self.secret = secret
        self.issuer = issuer
        self.audience = audience
        self.access_ttl = access_ttl
        self.refresh_ttl = refresh_ttl
        self.code_ttl = code_ttl

    def _encode(self, typ: str, client_id: str, scopes: list[str], ttl: int, **extra) -> tuple[str, int]:
        now = int(time.time())
        claims = {
            "iss": self.issuer, "aud": self.audience, "sub": client_id, "client_id": client_id,
            "scope": " ".join(scopes), "typ": typ, "iat": now, "exp": now + ttl,
            "jti": secrets.token_urlsafe(12), **extra,
        }
        return jwt.encode(claims, self.secret, algorithm="HS256"), now + ttl

    def issue_access(self, client_id: str, scopes: list[str]) -> tuple[str, int]:
        return self._encode("access", client_id, scopes, self.access_ttl)

    def issue_refresh(self, client_id: str, scopes: list[str]) -> tuple[str, int]:
        return self._encode("refresh", client_id, scopes, self.refresh_ttl)

    def issue_code(self, client_id: str, scopes: list[str], redirect_uri: str, code_challenge: str) -> tuple[str, int]:
        return self._encode("code", client_id, scopes, self.code_ttl, redirect_uri=redirect_uri,
                            code_challenge=code_challenge)

    def decode(self, token: str, typ: str) -> dict:
        claims = jwt.decode(token, self.secret, algorithms=["HS256"], audience=self.audience, issuer=self.issuer,
                            options={"require": ["exp", "iat", "sub", "typ"]})
        if claims.get("typ") != typ:
            raise jwt.InvalidTokenError("wrong token type")
        return claims


class JWTTokenVerifier(TokenVerifier):
    def __init__(self, issuer: TokenIssuer):
        self._issuer = issuer

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            claims = self._issuer.decode(token, "access")
        except jwt.PyJWTError:
            return None
        return AccessToken(
            token=token,
            client_id=claims["client_id"],
            scopes=claims.get("scope", "").split(),
            expires_at=claims["exp"],
            resource=self._issuer.audience,
            subject=claims["sub"],
        )


def _error(error: str, description: str, status: int = 400, headers: dict | None = None) -> JSONResponse:
    return JSONResponse({"error": error, "error_description": description}, status_code=status,
                        headers={"Cache-Control": "no-store", **(headers or {})})


def _append_query(url: str, params: dict) -> str:
    return url + ("&" if "?" in url else "?") + urlencode(params)


class OAuthServer:
    def __init__(self, clients: ClientStore, tokens: TokenIssuer, base_url: str):
        self.clients = clients
        self.tokens = tokens
        self.base_url = base_url.rstrip("/")
        self._used_codes: dict[str, int] = {}

    def metadata(self) -> dict:
        return {
            "issuer": self.base_url,
            "authorization_endpoint": f"{self.base_url}/oauth/authorize",
            "token_endpoint": f"{self.base_url}/oauth/token",
            "grant_types_supported": ["authorization_code", "client_credentials", "refresh_token"],
            "response_types_supported": ["code"],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post"],
            "scopes_supported": list(SCOPES),
        }

    async def metadata_endpoint(self, request: Request) -> Response:
        return JSONResponse(self.metadata())

    def _authenticate(self, request: Request, form) -> OAuthClient | None:
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("basic "):
            try:
                client_id, _, secret = base64.b64decode(auth[6:]).decode().partition(":")
            except ValueError:
                return None
            return self.clients.authenticate(unquote(client_id), unquote(secret))
        return self.clients.authenticate(form.get("client_id"), form.get("client_secret"))

    @staticmethod
    def _scopes(client: OAuthClient, requested: str | None, ceiling: list[str] | None = None) -> list[str] | None:
        available = [s for s in client.scopes if ceiling is None or s in ceiling]
        if not requested:
            return available
        wanted = requested.split()
        return wanted if set(wanted) <= set(available) else None

    def _token_response(self, client: OAuthClient, scopes: list[str], *, refresh: bool) -> JSONResponse:
        access, exp = self.tokens.issue_access(client.client_id, scopes)
        body = {"access_token": access, "token_type": "Bearer", "expires_in": exp - int(time.time()),
                "scope": " ".join(scopes)}
        if refresh:
            body["refresh_token"], _ = self.tokens.issue_refresh(client.client_id, scopes)
        return JSONResponse(body, headers={"Cache-Control": "no-store", "Pragma": "no-cache"})

    def _consume_code(self, claims: dict) -> bool:
        now = int(time.time())
        self._used_codes = {j: e for j, e in self._used_codes.items() if e > now}
        if claims["jti"] in self._used_codes:
            return False
        self._used_codes[claims["jti"]] = claims["exp"]
        return True

    async def token_endpoint(self, request: Request) -> Response:
        form = await request.form()
        client = self._authenticate(request, form)
        if client is None:
            return _error("invalid_client", "Client authentication failed", 401, {"WWW-Authenticate": 'Basic realm="mcp"'})
        grant = form.get("grant_type")

        if grant == "client_credentials":
            scopes = self._scopes(client, form.get("scope"))
            if scopes is None:
                return _error("invalid_scope", f"Allowed scopes: {' '.join(client.scopes)}")
            return self._token_response(client, scopes, refresh=False)

        if grant == "authorization_code":
            try:
                claims = self.tokens.decode(form.get("code", ""), "code")
            except jwt.PyJWTError:
                return _error("invalid_grant", "Invalid or expired authorization code")
            if claims["client_id"] != client.client_id or claims.get("redirect_uri") != form.get("redirect_uri"):
                return _error("invalid_grant", "Authorization code was issued to another client or redirect_uri")
            verifier = form.get("code_verifier") or ""
            if not verifier or _b64(hashlib.sha256(verifier.encode()).digest()) != claims.get("code_challenge"):
                return _error("invalid_grant", "PKCE verification failed")
            if not self._consume_code(claims):
                return _error("invalid_grant", "Authorization code already used")
            scopes = self._scopes(client, None, ceiling=claims["scope"].split())
            return self._token_response(client, scopes, refresh=True)

        if grant == "refresh_token":
            try:
                claims = self.tokens.decode(form.get("refresh_token", ""), "refresh")
            except jwt.PyJWTError:
                return _error("invalid_grant", "Invalid or expired refresh token")
            if claims["client_id"] != client.client_id:
                return _error("invalid_grant", "Refresh token was issued to another client")
            scopes = self._scopes(client, form.get("scope"), ceiling=claims["scope"].split())
            if scopes is None:
                return _error("invalid_scope", "Requested scope exceeds the original grant")
            return self._token_response(client, scopes, refresh=True)

        return _error("unsupported_grant_type", "Supported: client_credentials, authorization_code, refresh_token")

    async def authorize_endpoint(self, request: Request) -> Response:
        p = request.query_params
        client = self.clients.get(p.get("client_id"))
        redirect_uri = p.get("redirect_uri")
        if client is None:
            return _error("invalid_client", "Unknown client_id")
        if not redirect_uri or redirect_uri not in client.redirect_uris:
            return _error("invalid_request", "redirect_uri is not registered for this client")
        state = p.get("state")

        def fail(code: str, description: str) -> Response:
            params = {"error": code, "error_description": description, **({"state": state} if state else {})}
            return RedirectResponse(_append_query(redirect_uri, params), status_code=302)

        if p.get("response_type") != "code":
            return fail("unsupported_response_type", "Only response_type=code is supported")
        challenge = p.get("code_challenge")
        if not challenge or p.get("code_challenge_method", "S256") != "S256":
            return fail("invalid_request", "PKCE with code_challenge_method=S256 is required")
        scopes = self._scopes(client, p.get("scope"))
        if scopes is None:
            return fail("invalid_scope", f"Allowed scopes: {' '.join(client.scopes)}")
        code, _ = self.tokens.issue_code(client.client_id, scopes, redirect_uri, challenge)
        return RedirectResponse(_append_query(redirect_uri, {"code": code, **({"state": state} if state else {})}),
                                status_code=302)
