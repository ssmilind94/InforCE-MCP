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
| `scripts/check_connectivity.py` | Phase 1 connectivity check |
| `scripts/discover_ln.py` | Probe LN services and write `discovery/ln_endpoint_inventory.*` |
| `scripts/manage_clients.py` | Create/list/delete MCP OAuth clients |
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
| `IONAPI_JSON` / `IONAPI_FILE` | `Files/InforVelocity.ionapi` | Backend service account `.ionapi`; use `IONAPI_JSON` (Key Vault reference) on Azure |
| `LN_DEFAULT_COMPANY` | `__LN_COMPANY__` | Default `X-Infor-LnCompany` |
| `ENDPOINTS_FILE` | `config/endpoints.yaml` | |
| `PUBLIC_BASE_URL` | `http://localhost:8000` | Public URL; OAuth issuer and token audience |
| `ALLOWED_HOSTS` | `[]` | Extra accepted Host headers (JSON list) |
| `OAUTH_JWT_SECRET` | (required) | At least 32 characters |
| `OAUTH_CLIENTS_JSON` / `OAUTH_CLIENTS_FILE` | `config/clients.json` | Client registry |
| `OAUTH_ACCESS_TOKEN_TTL` / `OAUTH_REFRESH_TOKEN_TTL` | 3600 / 2592000 | Seconds |
| `INFOR_MAX_RETRIES`, `INFOR_TIMEOUT_SECONDS`, `QUERY_MAX_TOP` | 3, 60, 500 | |

## LN behaviour worth knowing

- Company-specific tables fail with "Table does not exist" when no company is sent.
- LN intermittently returns `401 OAuth [U14]: unknown oauth_consumer_key` for valid tokens; the client retries.
- Item keys are segmented and space-padded (e.g. `'         1000100'`); `GetSegmentedItemKey` builds them
  (LN returns the value URL-encoded).
- All enabled resources use optimistic concurrency (`If-Match` ETag) for update/delete.
