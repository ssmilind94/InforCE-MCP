# Infor LN MCP Server (InforCE-MCP)

MCP server (streamable HTTP) that exposes Infor LN OData APIs from the Infor ION API gateway to AI agents.
Clients authenticate with a **bearer token**: either a static token for custom agents, or an OAuth2 access token.
It runs on an Azure Web App and deploys from GitHub Actions.

```
AI agent / MCP client ──Bearer token──▶ /mcp (this server) ──ION service account token──▶ ION API ──▶ LN OData
```

## Current deployment

| | |
|---|---|
| MCP endpoint | `https://inforce-mcp-gxeybyepgcbvcham.centralindia-01.azurewebsites.net/mcp` |
| Health check | `https://inforce-mcp-gxeybyepgcbvcham.centralindia-01.azurewebsites.net/healthz` |
| Azure | Web App `inforce-mcp` (Linux, Python 3.14), resource group `RG-InforVelocity`, Central India |
| Infor | LN DEV tenant via ION API; tested with company `1300` |
| CI/CD | `.github/workflows/deploy.yml`: tests, then deploy on push to `main` |
| Default company | Not set yet (`__LN_COMPANY__`): pass `company` on every call |

Verified live: the read-only smoke test passes 40/40 with a static token and with OAuth2 client credentials.
Create, update, delete and actions are only covered by the mocked tests so far.

## Connecting an agent

1. Get a bearer token from the server admin (see [Static bearer tokens](#static-bearer-tokens)).
2. Send it on every request: `Authorization: Bearer lnmcp_<id>_<secret>`.
3. Start with `ln_list_resources`, then `ln_describe`, then query or write.

Python (MCP SDK):

```python
import asyncio
import os

import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

MCP_URL = "https://inforce-mcp-gxeybyepgcbvcham.centralindia-01.azurewebsites.net/mcp"


async def main() -> None:
    headers = {"Authorization": f"Bearer {os.environ['MCP_BEARER_TOKEN']}"}
    async with httpx2.AsyncClient(headers=headers, timeout=180) as http:
        async with streamable_http_client(MCP_URL, http_client=http) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("ln_query", {
                    "service": "tcapi.ibdItem", "resource": "Items", "select": "Item,Description", "top": 5,
                    "company": "1300"})
                print(result.content[0].text)  # JSON text; result.is_error is True on failures


asyncio.run(main())
```

curl (raw JSON-RPC):

```bash
curl -s https://inforce-mcp-gxeybyepgcbvcham.centralindia-01.azurewebsites.net/mcp \
  -H "Authorization: Bearer $MCP_BEARER_TOKEN" \
  -H "Accept: application/json, text/event-stream" -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"ln_list_resources","arguments":{}}}'
```

Keep tokens in a secret store or environment variable, never in source code.

## MCP tools

| Tool | Scope | Purpose |
|---|---|---|
| `ln_list_resources` | ln.read | Enabled services, resources (keys, permissions), operations |
| `ln_describe` | ln.read | Fields (types, enums, read-only), keys, operation parameters |
| `ln_query` | ln.read | OData `$filter/$select/$orderby/$expand/$top/$skip/$count` |
| `ln_get` | ln.read | One record by key |
| `ln_create` | ln.write | POST a record |
| `ln_update` | ln.write | PATCH a record (ETag handled automatically or passed explicitly) |
| `ln_delete` | ln.write | DELETE a record |
| `ln_call_operation` | ln.read (functions) / ln.write (actions) | e.g. `CreateOrder`, `CreateLine`, `GetSegmentedItemKey` |

Every data call needs an LN company: the `company` argument, or `LN_DEFAULT_COMPANY`. Until a default is
configured, a call without a company fails with a clear message.

### Enabled endpoints and permissions (`permissions: max`)

LN declares a level per entity; the server allows exactly that and never more:

| Service | Resource | LN level | Allowed |
|---|---|---|---|
| `tdapi.slsSalesOrder` | `Orders`, `Lines` | Updatable | read, create, update (most fields are read-only; create via `CreateOrder` / `CreateLine`) |
| `tdapi.slsSalesOrder` | `ActualDeliveryLines` | ReadableByKey | read |
| `tdapi.isaItemSales` | `ItemsSales`, `ItemsSalesBySalesOffice` | Deletable | read, create, update, delete |
| `tcapi.comBusinessPartner` | `BusinessPartners`, `SoldtoBusinessPartners` | Deletable | read, create, update, delete |
| `tcapi.ibdItem` | `Items`, `ItemsBySites` | Deletable | read, create, update, delete |

Operations: `CreateOrder`, `CreateLine`, `SimulateAdditionalCostLines`, `CalculateLineAmounts`
(`tdapi.slsSalesOrder`) and `GetSegmentedItemKey` (`tcapi.ibdItem`).

## Authentication

`/mcp` accepts two kinds of token in `Authorization: Bearer <token>`:

| Token | For | Obtained |
|---|---|---|
| Static token `lnmcp_<id>_<secret>` | Custom agents and scripts with a fixed header | `scripts/manage_tokens.py` |
| OAuth2 JWT access token | OAuth-capable MCP clients | `POST /oauth/token` |

Both kinds use the same scopes: `ln.read` for any access, `ln.write` for create, update, delete and actions.
Missing, invalid, expired or revoked tokens get `401`.

### Static bearer tokens

```bash
.venv/bin/python scripts/manage_tokens.py --file config/tokens.azure.json create --name "sales-agent" \
    [--scopes ln.read] [--expires-days 365]      # default: both scopes, 365 days; 0 = never expires
.venv/bin/python scripts/manage_tokens.py --file config/tokens.azure.json list
.venv/bin/python scripts/manage_tokens.py --file config/tokens.azure.json revoke <token_id>
```

- Each token is shown once. Only its SHA-256 hash is stored, in a git-ignored registry file.
- Locally the server reads `config/tokens.json`. On Azure the registry is the `STATIC_TOKENS_JSON` App Setting:
  after creating or revoking a token, [update the App Settings](#app-settings). The app restarts, and the
  change takes effect then.
- Use one token per agent, so you can revoke one without affecting the others. Give read-only agents
  `--scopes ln.read`.

### OAuth2

- Metadata: `/.well-known/oauth-authorization-server`, `/.well-known/oauth-protected-resource/mcp`
- Token: `POST /oauth/token` with `client_credentials`, `authorization_code` (PKCE S256), `refresh_token`;
  client auth via HTTP Basic or form fields.
- Authorize: `GET /oauth/authorize` (auto-approved for registered clients and exact registered redirect URIs).
- Clients: `scripts/manage_clients.py --file config/clients.azure.json create --name ... [--scopes ...] [--redirect-uri ...]`
  (redirect URIs only for interactive clients, e.g. `https://claude.ai/api/mcp/auth_callback`).
- Tokens are HS256 JWTs signed with `OAUTH_JWT_SECRET`; client secrets are stored as PBKDF2 hashes.
- Tokens are stateless, so the app can scale out. One exception: single use of an authorization code is enforced
  per instance, in memory. With several instances, a code could be redeemed once on each instance during its
  5-minute lifetime. It stays bound to the client secret and PKCE either way.

## Adding an API

1. Find the service: `python scripts/discover_ln.py --services <service>` (or the ION API Gateway portal documentation).
2. Add it to `config/endpoints.yaml` with its resources/operations (optionally `permissions: [read]`).
3. Push to `main`. The workflow tests and redeploys. No code changes are needed.

## Layout

| Path | Purpose |
|---|---|
| `config/endpoints.yaml` | Enabled LN services, resources, operations and permissions |
| `app/main.py` | ASGI app factory: `/mcp`, OAuth2 endpoints, `/healthz` |
| `app/tools.py` | MCP tools |
| `app/infor/` | ION API credentials, token cache, HTTP client with retries, `$metadata` parsing, LN operations |
| `app/security/oauth.py` | OAuth2 authorization server (JWT access/refresh tokens) |
| `app/security/static_tokens.py` | Static bearer tokens for custom agents |
| `scripts/check_connectivity.py` | ION API connectivity check |
| `scripts/discover_ln.py` | Probe LN services and write `discovery/ln_endpoint_inventory.*` |
| `scripts/manage_clients.py` | Create/list/delete MCP OAuth clients |
| `scripts/manage_tokens.py` | Create/list/revoke static bearer tokens |
| `scripts/make_app_settings.py` | Build the Azure App Settings JSON (credentials, clients, tokens) |
| `scripts/smoke_test.py` | Live read-only end-to-end test through a real MCP client |
| `.github/workflows/deploy.yml` | Test and deploy workflow |

Never committed (git-ignored): `Files/` (`.ionapi`, Azure and client credentials), `.env`, `config/clients*.json`,
`config/tokens*.json`, `output/`.

## Local development

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
cp .env.example .env
.venv/bin/python scripts/manage_clients.py jwt-secret        # put into OAUTH_JWT_SECRET
.venv/bin/python scripts/manage_tokens.py create --name "local-agent"          # static token (config/tokens.json)
.venv/bin/python scripts/manage_clients.py create --name "my-client"          # optional OAuth2 client
.venv/bin/uvicorn app.main:create_app --factory --port 8000
```

Tests:

```bash
.venv/bin/python -m pytest          # unit + in-process OAuth/static-token/MCP tests (Infor mocked)
MCP_BEARER_TOKEN=lnmcp_... .venv/bin/python scripts/smoke_test.py --base-url <url> --company 1300   # live, read-only
.venv/bin/python scripts/smoke_test.py --base-url <url> --client-id ... --client-secret ... --company 1300
```

## Azure deployment

`.github/workflows/deploy.yml` runs the tests on every push and PR. On `main` it zip-deploys `app/`,
`config/endpoints.yaml` and `requirements.txt`; App Service installs the requirements. The workflow then
polls `/healthz`. The deploy job is skipped until `AZURE_WEBAPP_NAME` is set.

### One-time setup

1. **Web App** (Linux, Python 3.14), under Configuration > General settings:
   - Startup command:
     `python -m uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips="*"`
   - SCM Basic Auth Publishing Credentials: **On** (needed for the publish profile)
   - HTTPS Only: **On**. Always On: **On**.
2. **Clients and tokens for Azure.** Keep them separate from local ones:
   `manage_clients.py --file config/clients.azure.json ...` and `manage_tokens.py --file config/tokens.azure.json ...`
3. **App Settings.** See [below](#app-settings).
4. **GitHub** (Settings > Secrets and variables > Actions)
   - Variable `AZURE_WEBAPP_NAME` = `<app>`
   - Variable `AZURE_WEBAPP_URL` = the app's `https://` default domain from the Overview page. New apps can have
     a unique hostname such as `<app>-<hash>.<region>.azurewebsites.net`.
   - Secret `AZURE_WEBAPP_PUBLISH_PROFILE` = the publish profile (Portal > Overview > Download publish profile)
5. Push to `main`, or run `gh workflow run test-and-deploy`. Then run the smoke test against the app URL.

### App Settings

```bash
.venv/bin/python scripts/make_app_settings.py --app-url https://<app host> \
    [--clients config/clients.azure.json] [--tokens config/tokens.azure.json] [--company <LN company>]
```

This writes `output/azure-appsettings.json` with mode 0600: `IONAPI_JSON`, `OAUTH_JWT_SECRET`,
`OAUTH_CLIENTS_JSON`, `STATIC_TOKENS_JSON`, `PUBLIC_BASE_URL`, `LN_DEFAULT_COMPANY`,
`SCM_DO_BUILD_DURING_DEPLOYMENT`. Apply it one of two ways:

- Azure CLI:
  `az webapp config appsettings set -g <rg> -n <app> --settings @output/azure-appsettings.json -o none`
- Portal: Environment variables > Advanced edit. Merge the entries, then Apply.

Reruns keep `OAUTH_JWT_SECRET`; `--rotate-jwt-secret` invalidates every issued OAuth2 token.

The CLI route used for this deployment signs in as a service principal with the **Website Contributor** role on
the Web App only. Its credentials stay in `Files/azure-sp.env`.

## Configuration

| Variable | Default | Notes |
|---|---|---|
| `IONAPI_JSON` / `IONAPI_FILE` | `Files/InforVelocity.ionapi` | Backend service account `.ionapi`; on Azure the file content goes in `IONAPI_JSON` |
| `LN_DEFAULT_COMPANY` | `__LN_COMPANY__` | Default `X-Infor-LnCompany` |
| `ENDPOINTS_FILE` | `config/endpoints.yaml` | |
| `PUBLIC_BASE_URL` | `http://localhost:8000` | Public URL; OAuth issuer and token audience |
| `ALLOWED_HOSTS` | `[]` | Extra accepted Host headers (JSON list), e.g. for a custom domain |
| `OAUTH_JWT_SECRET` | (required) | At least 32 characters |
| `OAUTH_CLIENTS_JSON` / `OAUTH_CLIENTS_FILE` | `config/clients.json` | OAuth2 client registry (hashes) |
| `STATIC_TOKENS_JSON` / `STATIC_TOKENS_FILE` | `config/tokens.json` | Static bearer token registry (hashes) |
| `OAUTH_ACCESS_TOKEN_TTL` / `OAUTH_REFRESH_TOKEN_TTL` | 3600 / 2592000 | Seconds |
| `INFOR_MAX_RETRIES`, `INFOR_TIMEOUT_SECONDS`, `QUERY_MAX_TOP` | 3, 60, 500 | |

## LN behaviour worth knowing

- Company-specific tables fail with "Table does not exist" when no company is sent.
- LN intermittently returns `401 OAuth [U14]: unknown oauth_consumer_key` for valid tokens; the client retries.
- Item keys are segmented and space-padded (e.g. `'         1000100'`); `GetSegmentedItemKey` builds them
  (LN returns the value URL-encoded).
- All enabled resources use optimistic concurrency (`If-Match` ETag) for update/delete.
