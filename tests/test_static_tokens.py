import json
import time

import pytest

from app.security.static_tokens import PREFIX, ChainedTokenVerifier, StaticTokenVerifier, generate_token, hash_token

AUDIENCE = "http://localhost:8000/mcp"


def _entry(token_id, token, **extra):
    return {"token_id": token_id, "token_hash": hash_token(token), "name": "agent", **extra}


@pytest.fixture
def issued():
    return generate_token()


async def test_valid_token(issued):
    token_id, token = issued
    verifier = StaticTokenVerifier.from_entries([_entry(token_id, token, scopes=["ln.read"])], AUDIENCE)
    access = await verifier.verify_token(token)
    assert access.client_id == f"static:{token_id}"
    assert access.scopes == ["ln.read"] and access.resource == AUDIENCE and access.subject == "agent"


async def test_rejected_tokens(issued):
    token_id, token = issued
    verifier = StaticTokenVerifier.from_entries([_entry(token_id, token)])
    other_id, other = generate_token()
    for candidate in (token + "x", f"{PREFIX}{token_id}_wrong", f"{PREFIX}{token_id}", other,
                      token.removeprefix(PREFIX), "eyJhbGciOiJIUzI1NiJ9.e30.sig", ""):
        assert await verifier.verify_token(candidate) is None, candidate


async def test_expiry(issued):
    token_id, token = issued
    expired = StaticTokenVerifier.from_entries([_entry(token_id, token, expires_at=int(time.time()) - 1)])
    assert await expired.verify_token(token) is None
    valid = StaticTokenVerifier.from_entries([_entry(token_id, token, expires_at=int(time.time()) + 3600)])
    assert (await valid.verify_token(token)).expires_at is not None


def test_load_and_scope_validation(tmp_path, issued):
    token_id, token = issued
    path = tmp_path / "tokens.json"
    path.write_text(json.dumps([_entry(token_id, token)]))
    assert len(StaticTokenVerifier.load(None, path)) == 1
    assert len(StaticTokenVerifier.load(None, tmp_path / "missing.json")) == 0
    assert len(StaticTokenVerifier.load("[]", path)) == 0  # JSON setting takes precedence
    with pytest.raises(ValueError, match="unknown scopes"):
        StaticTokenVerifier.from_entries([_entry(token_id, token, scopes=["ln.admin"])])


async def test_chained_verifier_falls_through(issued):
    token_id, token = issued

    class Fallback:
        async def verify_token(self, t):
            return "fallback" if t == "jwt" else None

    chain = ChainedTokenVerifier(StaticTokenVerifier.from_entries([_entry(token_id, token)]), Fallback())
    assert (await chain.verify_token(token)).client_id == f"static:{token_id}"
    assert await chain.verify_token("jwt") == "fallback"
    assert await chain.verify_token("nope") is None
