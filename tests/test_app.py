"""OAuth2 endpoints and the MCP transport, in-process against a mocked Infor backend."""
import base64
import hashlib
import json
import secrets
from contextlib import asynccontextmanager
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from app.config import Settings
from app.main import create_app
from app.security.oauth import hash_secret
from tests.conftest import LN_BASE

BASE = "http://localhost:8000"
FULL = ("c-full", "s-full-secret")
READ_ONLY = ("c-ro", "s-ro-secret")
REDIRECT = "https://client.test/callback"
MCP_HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
TOOLS = {"ln_list_resources", "ln_describe", "ln_query", "ln_get", "ln_create", "ln_update", "ln_delete",
         "ln_call_operation"}


@pytest.fixture
def app(ln):
    entries = [
        {"client_id": FULL[0], "secret_hash": hash_secret(FULL[1], iterations=1000),
         "scopes": ["ln.read", "ln.write"], "redirect_uris": [REDIRECT]},
        {"client_id": READ_ONLY[0], "secret_hash": hash_secret(READ_ONLY[1], iterations=1000), "scopes": ["ln.read"]},
    ]
    settings = Settings(_env_file=None, oauth_jwt_secret="t" * 40, public_base_url=BASE,
                        oauth_clients_json=json.dumps(entries), ionapi_file=None)
    return create_app(settings, ln_service=ln)


@asynccontextmanager
async def connect(app):
    # The lifespan must start and stop in the same task (anyio cancel scopes), so it runs inside each test.
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=BASE) as client:
            yield client


async def _token(http, client, scope=None):
    data = {"grant_type": "client_credentials", **({"scope": scope} if scope else {})}
    return await http.post("/oauth/token", data=data, auth=client)


async def _mcp(http, token, method, params=None, id=1):
    r = await http.post("/mcp", headers={**MCP_HEADERS, "Authorization": f"Bearer {token}"},
                        json={"jsonrpc": "2.0", "id": id, "method": method, "params": params or {}})
    assert r.status_code == 200, r.text
    return r.json()


async def _initialize(http, token):
    return await _mcp(http, token, "initialize", {
        "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}})


async def test_health(app):
    async with connect(app) as http:
        assert (await http.get("/healthz")).json()["status"] == "ok"


async def test_discovery_metadata(app):
    async with connect(app) as http:
        prm = (await http.get("/.well-known/oauth-protected-resource/mcp")).json()
        assert prm["authorization_servers"][0].rstrip("/") == BASE
        asm = (await http.get("/.well-known/oauth-authorization-server")).json()
        assert asm["token_endpoint"] == f"{BASE}/oauth/token"
        assert {"client_credentials", "authorization_code", "refresh_token"} <= set(asm["grant_types_supported"])


async def test_mcp_requires_bearer_token(app):
    async with connect(app) as http:
        r = await http.post("/mcp", headers=MCP_HEADERS, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        assert r.status_code == 401
        assert "resource_metadata" in r.headers["www-authenticate"]
        r = await http.post("/mcp", headers={**MCP_HEADERS, "Authorization": "Bearer not-a-token"},
                            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        assert r.status_code == 401


async def test_client_credentials(app):
    async with connect(app) as http:
        r = await _token(http, FULL)
        assert r.status_code == 200
        assert r.json()["scope"] == "ln.read ln.write" and "refresh_token" not in r.json()
        assert (await _token(http, (FULL[0], "wrong"))).status_code == 401
        assert (await _token(http, READ_ONLY, scope="ln.write")).json()["error"] == "invalid_scope"


async def test_authorization_code_with_pkce_and_refresh(app):
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    params = {"response_type": "code", "client_id": FULL[0], "redirect_uri": REDIRECT,
              "code_challenge": challenge, "code_challenge_method": "S256", "state": "xyz"}
    async with connect(app) as http:
        evil = await http.get("/oauth/authorize", params={**params, "redirect_uri": "https://evil.test/cb"})
        assert evil.status_code == 400

        r = await http.get("/oauth/authorize", params=params)
        assert r.status_code == 302
        query = parse_qs(urlparse(r.headers["location"]).query)
        assert query["state"] == ["xyz"]
        form = {"grant_type": "authorization_code", "code": query["code"][0], "redirect_uri": REDIRECT,
                "code_verifier": verifier}

        bad = await http.post("/oauth/token", data={**form, "code_verifier": "wrong"}, auth=FULL)
        assert bad.json()["error"] == "invalid_grant"
        ok = await http.post("/oauth/token", data=form, auth=FULL)
        assert ok.status_code == 200 and ok.json()["refresh_token"]
        reused = await http.post("/oauth/token", data=form, auth=FULL)
        assert reused.json()["error"] == "invalid_grant"

        refreshed = await http.post("/oauth/token", auth=FULL,
                                    data={"grant_type": "refresh_token", "refresh_token": ok.json()["refresh_token"]})
        assert refreshed.status_code == 200 and refreshed.json()["access_token"]


async def test_mcp_tools_end_to_end(app, infor):
    infor.get(url__startswith=f"{LN_BASE}/tdapi.slsSalesOrder/Orders").mock(
        return_value=httpx.Response(200, json={"value": [{"SalesOrder": "100000001"}]}))
    async with connect(app) as http:
        token = (await _token(http, FULL)).json()["access_token"]
        init = await _initialize(http, token)
        assert init["result"]["serverInfo"]["name"] == "infor-ln-mcp"

        tools = await _mcp(http, token, "tools/list", id=2)
        assert {t["name"] for t in tools["result"]["tools"]} == TOOLS

        res = await _mcp(http, token, "tools/call", {"name": "ln_query", "arguments": {
            "service": "tdapi.slsSalesOrder", "resource": "Orders", "select": "SalesOrder", "company": "1300"}}, id=3)
        assert not res["result"].get("isError"), res
        assert "100000001" in json.dumps(res["result"])

        res = await _mcp(http, token, "tools/call", {"name": "ln_delete", "arguments": {
            "service": "tdapi.slsSalesOrder", "resource": "Orders", "key": "100000001", "company": "1300"}}, id=4)
        assert res["result"]["isError"] and "not permitted" in json.dumps(res["result"])


async def test_write_tools_require_write_scope(app):
    async with connect(app) as http:
        token = (await _token(http, READ_ONLY)).json()["access_token"]
        await _initialize(http, token)
        res = await _mcp(http, token, "tools/call", {"name": "ln_delete", "arguments": {
            "service": "tcapi.ibdItem", "resource": "Items", "key": "X", "company": "1300"}}, id=2)
        assert res["result"]["isError"] and "ln.write" in json.dumps(res["result"])
