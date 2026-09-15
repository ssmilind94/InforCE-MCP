"""Static bearer tokens for MCP clients that do not run an OAuth2 flow (e.g. custom agents).

Clients send `Authorization: Bearer lnmcp_<token_id>_<secret>` on every /mcp request.
Only a SHA-256 hash of the token is stored: tokens carry 256 bits of randomness, so a slow hash adds nothing
and verification stays cheap per request. Registry entries (JSON list):
  {"token_id", "name", "scopes", "token_hash", "created_at", "expires_at"}   (expires_at: unix seconds or null)
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from pathlib import Path

from mcp.server.auth.provider import AccessToken, TokenVerifier

from app.security.oauth import SCOPES

PREFIX = "lnmcp_"


def hash_token(token: str) -> str:
    return "sha256$" + hashlib.sha256(token.encode()).hexdigest()


def generate_token() -> tuple[str, str]:
    """Return (token_id, token)."""
    token_id = secrets.token_hex(6)
    return token_id, f"{PREFIX}{token_id}_{secrets.token_urlsafe(32)}"


@dataclass(frozen=True)
class StaticToken:
    token_id: str
    token_hash: str
    name: str = ""
    scopes: tuple[str, ...] = SCOPES
    expires_at: int | None = None


class StaticTokenVerifier(TokenVerifier):
    def __init__(self, tokens: list[StaticToken], audience: str | None = None):
        self._tokens = {t.token_id: t for t in tokens}
        self._audience = audience

    @classmethod
    def from_entries(cls, entries: list[dict], audience: str | None = None) -> StaticTokenVerifier:
        tokens = []
        for e in entries:
            scopes = tuple(e.get("scopes", SCOPES))
            if unknown := set(scopes) - set(SCOPES):
                raise ValueError(f"static token {e['token_id']} has unknown scopes {sorted(unknown)}")
            tokens.append(StaticToken(token_id=e["token_id"], token_hash=e["token_hash"], name=e.get("name", ""),
                                      scopes=scopes, expires_at=e.get("expires_at")))
        return cls(tokens, audience)

    @classmethod
    def load(cls, tokens_json: str | None, tokens_file: Path | None,
             audience: str | None = None) -> StaticTokenVerifier:
        if tokens_json:
            return cls.from_entries(json.loads(tokens_json), audience)
        if tokens_file and tokens_file.exists():
            return cls.from_entries(json.loads(tokens_file.read_text()), audience)
        return cls([], audience)

    def __len__(self) -> int:
        return len(self._tokens)

    async def verify_token(self, token: str) -> AccessToken | None:
        if not token.startswith(PREFIX):
            return None
        token_id, sep, _ = token[len(PREFIX):].partition("_")
        entry = self._tokens.get(token_id)
        if not sep or entry is None or not hmac.compare_digest(hash_token(token), entry.token_hash):
            return None
        if entry.expires_at is not None and entry.expires_at <= time.time():
            return None
        return AccessToken(token=token, client_id=f"static:{entry.token_id}", scopes=list(entry.scopes),
                           expires_at=entry.expires_at, resource=self._audience,
                           subject=entry.name or entry.token_id)


class ChainedTokenVerifier(TokenVerifier):
    """Accept a token if any verifier accepts it (first match wins)."""

    def __init__(self, *verifiers: TokenVerifier):
        self._verifiers = verifiers

    async def verify_token(self, token: str) -> AccessToken | None:
        for verifier in self._verifiers:
            if (access := await verifier.verify_token(token)) is not None:
                return access
        return None
