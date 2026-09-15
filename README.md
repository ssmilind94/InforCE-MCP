# Infor LN MCP Server

MCP server (streamable HTTP) exposing Infor LN OData APIs from the ION API gateway, protected by OAuth2
with internally issued client IDs/secrets. Built for Azure Web Apps.

```
MCP client ──OAuth2 bearer──▶ /mcp (this server) ──service account token──▶ ION API ──▶ LN OData
```

## Layout

| Path | Purpose |
|---|---|
| `config/endpoints.yaml` | Enabled LN services, resources, operations and permissions |
| `app/main.py` | ASGI app factory: `/mcp`, OAuth2 endpoints, `/healthz` |
| `app/tools.py` | MCP tools |
| `app/infor/` | ION API credentials, token cache, HTTP client with retries, `$metadata` parsing, LN operations |
| `app/security/oauth.py` | OAuth2 authorization server (JWT access/refresh tokens) |
| `app/security/static_tokens.py` | Static bearer tokens for custom agents |
| `scripts/check_connectivity.py` | Phase 1 connectivity check |
| `scripts/discover_ln.py` | Probe LN services and write `discovery/ln_endpoint_inventory.*` |
| `scripts/manage_clients.py` | Create/list/delete MCP OAuth clients |
| `scripts/manage_tokens.py` | Create/list/revoke static bearer tokens |
| `scripts/smoke_test.py` | Live read-only end-to-end test through a real MCP client |

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

Every data call needs an LN company: the `company` argument, or `LN_DEFAULT_COMPANY`
(placeholder `__LN_COMPANY__` until decided; calls without a company fail with a clear message).

### Permissions (`permissions: max`)

LN declares a level per entity; the server allows exactly that and never more:

| Resource | LN level | Allowed |
|---|---|---|
| slsSalesOrder `Orders`, `Lines` | Updatable | read, create, update (most fields are read-only; create via `CreateOrder` / `CreateLine`) |
| slsSalesOrder `ActualDeliveryLines` | ReadableByKey | read |
| isaItemSales `ItemsSales`, `ItemsSalesBySalesOffice` | Deletable | read, create, update, delete |
| comBusinessPartner `BusinessPartners`, `SoldtoBusinessPartners` | Deletable | read, create, update, delete |
| ibdItem `Items`, `ItemsBySites` | Deletable | read, create, update, delete |

## Adding an API

1. Find the service: `python scripts/discover_ln.py --services <service>` (or the ION API Gateway portal documentation).
2. Add it to `config/endpoints.yaml` with its resources/operations (optionally `permissions: [read]`).
3. Restart. No code changes are needed.

## Local development

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
cp .env.example .env
.venv/bin/python scripts/manage_clients.py jwt-secret        # put into OAUTH_JWT_SECRET
.venv/bin/python scripts/manage_clients.py create --name "my-client" \
    [--redirect-uri https://claude.ai/api/mcp/auth_callback]   # redirect URI only for interactive clients
.venv/bin/uvicorn app.main:create_app --factory --port 8000
```

Tests:

```bash
.venv/bin/python -m pytest                                   # unit + in-process OAuth/MCP tests (Infor mocked)
.venv/bin/python scripts/smoke_test.py --client-id ... --client-secret ... --company 1300   # live, read-only
```

## Azure deployment (GitHub Actions → Linux Python 3.14 Web App)

`.github/workflows/deploy.yml` runs the tests on every push and PR. On `main` it zip-deploys `app/`,
`config/endpoints.yaml` and `requirements.txt`; App Service installs the requirements. The workflow then
polls `/healthz`. The deploy job is skipped until `AZURE_WEBAPP_NAME` is set.

One-time setup:

1. **Web App** (Portal > Settings > Configuration > General settings)
   - Startup command:
     `python -m uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips="*"`
   - SCM Basic Auth Publishing Credentials: **On** (needed for the publish profile)
   - HTTPS Only: **On**. Always On: **On**.
2. **OAuth clients for Azure.** Keep them separate from local clients; `config/clients*.json` is git-ignored:
   ```bash
   .venv/bin/python scripts/manage_clients.py --file config/clients.azure.json create --name "my-client" \
       [--redirect-uri https://claude.ai/api/mcp/auth_callback]
   ```
3. **App Settings:**
   ```bash
   .venv/bin/python scripts/make_app_settings.py --app-url https://<app>.azurewebsites.net [--company <LN company>]
   ```
   Paste the entries from `output/azure-appsettings.json` into Portal > Settings > Environment variables >
   Advanced edit, merging with what is already there, then Apply. The file holds secrets and has mode 0600.
   Reruns keep `OAUTH_JWT_SECRET`; `--rotate-jwt-secret` invalidates all issued tokens.
4. **GitHub** (Settings > Secrets and variables > Actions)
   - Variable `AZURE_WEBAPP_NAME` = `<app>`
   - Variable `AZURE_WEBAPP_URL` = the app's `https://` default domain from the Overview page. New apps can have
     a unique hostname such as `<app>-<hash>.<region>.azurewebsites.net`; use the same URL for `--app-url`.
   - Secret `AZURE_WEBAPP_PUBLISH_PROFILE` = contents of Portal > Overview > Download publish profile
5. Push to `main`, or run the workflow manually. Then verify:
   `.venv/bin/python scripts/smoke_test.py --base-url https://<app>.azurewebsites.net --client-id ... --client-secret ... --company <LN company>`

Adding an API or a client changes something different:
- New API: edit `config/endpoints.yaml` and push. The deploy restarts the app.
- New client: rerun steps 2 and 3, then update `OAUTH_CLIENTS_JSON` in the Portal.

Tokens are stateless JWTs, so the app can scale out. One exception: single use of an authorization code is
enforced per instance, in memory. With several instances, a code could be redeemed once on each instance
during its 5-minute lifetime. It stays bound to the client secret and PKCE either way.

## Authentication

`/mcp` accepts two kinds of token in `Authorization: Bearer <token>`:

| Token | For | Obtained |
|---|---|---|
| Static token `lnmcp_<id>_<secret>` | Custom agents and scripts with a fixed header | `scripts/manage_tokens.py` |
| OAuth2 JWT access token | OAuth-capable MCP clients | `POST /oauth/token` (see below) |

Both kinds use the same scopes: `ln.read` for any access, `ln.write` for create, update, delete and actions.

### Static bearer tokens

```bash
.venv/bin/python scripts/manage_tokens.py --file config/tokens.azure.json create --name "sales-agent" \
    [--scopes ln.read] [--expires-days 365]      # default: both scopes, 365 days; 0 = never expires
.venv/bin/python scripts/manage_tokens.py --file config/tokens.azure.json list
.venv/bin/python scripts/manage_tokens.py --file config/tokens.azure.json revoke <token_id>
```

- Each token is shown once. Only its SHA-256 hash is stored.
- Locally the server reads `config/tokens.json`. On Azure, rerun `scripts/make_app_settings.py` and apply the
  `STATIC_TOKENS_JSON` setting. Changing the setting restarts the app, and that's when creating or revoking a
  token takes effect.

Custom agent example (Python MCP SDK):

```python
import os

import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

headers = {"Authorization": f"Bearer {os.environ['MCP_BEARER_TOKEN']}"}
async with httpx2.AsyncClient(headers=headers, timeout=180) as http:
    async with streamable_http_client("https://<app host>/mcp", http_client=http) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("ln_query", {
                "service": "tcapi.ibdItem", "resource": "Items", "select": "Item,Description", "top": 5,
                "company": "1300"})
```

Keep tokens in a secret store or environment variable, not in source code. Use a separate token for each
agent so you can revoke one without affecting the others.

## OAuth2

- Metadata: `/.well-known/oauth-authorization-server`, `/.well-known/oauth-protected-resource/mcp`
- Token: `POST /oauth/token` with `client_credentials`, `authorization_code` (PKCE S256), `refresh_token`;
  client auth via HTTP Basic or form fields.
- Authorize: `GET /oauth/authorize` (auto-approved for registered clients and exact registered redirect URIs).
- Scopes: `ln.read` (required for `/mcp`), `ln.write` (create/update/delete/actions).
- Tokens are HS256 JWTs signed with `OAUTH_JWT_SECRET`; client secrets are stored as PBKDF2 hashes.

## Configuration

| Variable | Default | Notes |
|---|---|---|
| `IONAPI_JSON` / `IONAPI_FILE` | `Files/InforVelocity.ionapi` | Backend service account `.ionapi`; on Azure the file content goes in the `IONAPI_JSON` App Setting |
| `LN_DEFAULT_COMPANY` | `__LN_COMPANY__` | Default `X-Infor-LnCompany` |
| `ENDPOINTS_FILE` | `config/endpoints.yaml` | |
| `PUBLIC_BASE_URL` | `http://localhost:8000` | Public URL; OAuth issuer and token audience |
| `ALLOWED_HOSTS` | `[]` | Extra accepted Host headers (JSON list) |
| `OAUTH_JWT_SECRET` | (required) | At least 32 characters |
| `OAUTH_CLIENTS_JSON` / `OAUTH_CLIENTS_FILE` | `config/clients.json` | Client registry |
| `STATIC_TOKENS_JSON` / `STATIC_TOKENS_FILE` | `config/tokens.json` | Static bearer token registry (hashes) |
| `OAUTH_ACCESS_TOKEN_TTL` / `OAUTH_REFRESH_TOKEN_TTL` | 3600 / 2592000 | Seconds |
| `INFOR_MAX_RETRIES`, `INFOR_TIMEOUT_SECONDS`, `QUERY_MAX_TOP` | 3, 60, 500 | |

## LN behaviour worth knowing

- Company-specific tables fail with "Table does not exist" when no company is sent.
- LN intermittently returns `401 OAuth [U14]: unknown oauth_consumer_key` for valid tokens; the client retries.
- Item keys are segmented and space-padded (e.g. `'         1000100'`); `GetSegmentedItemKey` builds them
  (LN returns the value URL-encoded).
- All enabled resources use optimistic concurrency (`If-Match` ETag) for update/delete.
