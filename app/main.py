"""ASGI app: MCP over streamable HTTP (/mcp), OAuth2 endpoints and a health check.

Run: uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000
"""
from urllib.parse import urlparse

import httpx
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse

from app import __version__
from app.config import Settings, get_settings
from app.infor.catalog import Catalog, MetadataLoader, load_endpoint_config
from app.infor.client import LNClient
from app.infor.ionapi import load_credentials
from app.infor.ln_service import LNService
from app.infor.token_manager import InforTokenManager
from app.security.oauth import ClientStore, JWTTokenVerifier, OAuthServer, TokenIssuer
from app.security.static_tokens import ChainedTokenVerifier, StaticTokenVerifier
from app.tools import READ_SCOPE, register_tools

INSTRUCTIONS = """Tools for Infor LN (ERP) through the Infor ION API.
Start with ln_list_resources, then ln_describe to learn fields before filtering or writing.
Every data call needs an LN company: pass `company` or rely on the server default.
Use `select` to limit fields. Create/update/delete tools and actions change live ERP data: confirm with the user first.
Sales orders and lines are created with the CreateOrder / CreateLine operations."""


def build_ln_service(settings: Settings) -> LNService:
    creds = load_credentials(settings.ionapi_json, settings.ionapi_file)
    http = httpx.AsyncClient(timeout=settings.infor_timeout_seconds)
    client = LNClient(creds, InforTokenManager(creds, http), http, max_retries=settings.infor_max_retries)
    catalog = Catalog(load_endpoint_config(settings.endpoints_file), MetadataLoader(client, settings.metadata_snapshot_dir))
    return LNService(client, catalog, default_company=settings.ln_default_company, max_top=settings.query_max_top)


def create_app(settings: Settings | None = None, ln_service: LNService | None = None) -> Starlette:
    settings = settings or get_settings()
    ln = ln_service or build_ln_service(settings)

    issuer = TokenIssuer(settings.oauth_jwt_secret, settings.base_url, settings.mcp_resource_url,
                         access_ttl=settings.oauth_access_token_ttl, refresh_ttl=settings.oauth_refresh_token_ttl)
    clients = ClientStore.load(settings.oauth_clients_json, settings.oauth_clients_file)
    oauth = OAuthServer(clients, issuer, settings.base_url)
    static_tokens = StaticTokenVerifier.load(settings.static_tokens_json, settings.static_tokens_file,
                                             audience=settings.mcp_resource_url)

    mcp = MCPServer(
        name="infor-ln-mcp",
        version=__version__,
        instructions=INSTRUCTIONS,
        # Bearer tokens: static tokens (lnmcp_...) for custom agents, or OAuth2 JWT access tokens
        token_verifier=ChainedTokenVerifier(static_tokens, JWTTokenVerifier(issuer)),
        auth=AuthSettings(
            issuer_url=settings.base_url,
            resource_server_url=settings.mcp_resource_url,
            required_scopes=[READ_SCOPE],
            validate_token_resource=False,  # JWTTokenVerifier already enforces the audience
        ),
    )
    register_tools(mcp, ln)

    mcp.custom_route("/.well-known/oauth-authorization-server", methods=["GET"])(oauth.metadata_endpoint)
    mcp.custom_route("/oauth/token", methods=["POST"])(oauth.token_endpoint)
    mcp.custom_route("/oauth/authorize", methods=["GET"])(oauth.authorize_endpoint)

    @mcp.custom_route("/healthz", methods=["GET"])
    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "version": __version__})

    public_host = urlparse(settings.base_url).netloc
    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[public_host, *settings.allowed_hosts, "localhost:*", "127.0.0.1:*"],
        allowed_origins=[settings.base_url, "http://localhost:*", "http://127.0.0.1:*"],
    )
    return mcp.streamable_http_app(stateless_http=True, json_response=True, transport_security=security,
                                   host="0.0.0.0")
