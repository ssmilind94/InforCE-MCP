"""MCP tools over the configured Infor LN endpoints (config/endpoints.yaml).

The tools are generic and constrained by configuration, so enabling another LN API is a config change.
"""
from collections.abc import Awaitable, Callable
from typing import Annotated, Any

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from app.infor.client import LNError
from app.infor.ln_service import LNService, PermissionDenied
from app.infor.metadata import ValidationError

READ_SCOPE = "ln.read"
WRITE_SCOPE = "ln.write"

Service = Annotated[str, Field(description="LN service, e.g. 'tdapi.slsSalesOrder' (see ln_list_resources)")]
Resource = Annotated[str, Field(description="Resource (entity set) in the service, e.g. 'Orders'")]
Key = Annotated[
    str | int | dict[str, Any],
    Field(description="Record key: the value for single-key resources, or an object with every key field, e.g. "
                      '{"SalesOrder": "100000001", "Line": 10, "SequenceNumber": 0}. String keys are exact, '
                      "including leading spaces in segmented item codes."),
]
Data = Annotated[dict[str, Any], Field(description="Field names and values (see ln_describe for writable fields)")]
Company = Annotated[str | None, Field(description="LN company number (X-Infor-LnCompany). Omit to use the server default.")]
Etag = Annotated[str | None, Field(description="@odata.etag from a previous read for strict optimistic concurrency. "
                                               "If omitted, the current ETag is fetched just before the change.")]

READ = ToolAnnotations(readOnlyHint=True, openWorldHint=True)
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=True)
DESTRUCTIVE = ToolAnnotations(readOnlyHint=False, destructiveHint=True, openWorldHint=True)


def _require_scope(scope: str) -> None:
    token = get_access_token()
    if token is not None and scope not in token.scopes:
        raise ToolError(f"The access token lacks the '{scope}' scope required for this tool")


async def _call(scope: str, fn: Callable[[], Awaitable[dict]]) -> dict:
    _require_scope(scope)
    try:
        return await fn()
    except (ValidationError, PermissionDenied, LNError) as e:
        raise ToolError(str(e)) from e


def register_tools(mcp: MCPServer, ln: LNService) -> None:
    enabled = "; ".join(
        f"{name} [{', '.join([*cfg.resources, *cfg.operations])}]" for name, cfg in ln.catalog.services.items()
    )

    @mcp.tool(annotations=READ, description=(
        "List the enabled Infor LN services, their resources (keys and permitted operations) and callable "
        f"operations. Start here. Enabled: {enabled}"))
    async def ln_list_resources() -> dict:
        return await _call(READ_SCOPE, ln.list_resources)

    @mcp.tool(annotations=READ, description=(
        "Describe a resource (fields with types, enum values, read-only flags, keys, permissions) or an operation "
        "(parameters). Use before filtering, creating, updating or calling operations."))
    async def ln_describe(
        service: Service,
        name: Annotated[str, Field(description="Resource or operation name, e.g. 'Orders' or 'CreateOrder'")],
    ) -> dict:
        return await _call(READ_SCOPE, lambda: ln.describe(service, name))

    @mcp.tool(annotations=READ, description=(
        "Query records from an LN resource using OData options. Records can have 100+ fields, so use `select`. "
        "Example filter: \"SoldtoBusinessPartner eq '100000001' and OrderDate ge 2026-01-01T00:00:00Z\". "
        "Page with top/skip (next_skip is returned when more records may exist)."))
    async def ln_query(
        service: Service,
        resource: Resource,
        filter: Annotated[str | None, Field(description="OData $filter expression")] = None,
        select: Annotated[str | None, Field(description="Comma-separated fields to return")] = None,
        orderby: Annotated[str | None, Field(description="OData $orderby, e.g. 'OrderDate desc'")] = None,
        expand: Annotated[str | None, Field(description="Navigation properties to expand, e.g. 'LineRefs'")] = None,
        top: Annotated[int, Field(ge=1, le=500, description="Max records to return")] = 25,
        skip: Annotated[int, Field(ge=0, description="Records to skip")] = 0,
        count: Annotated[bool, Field(description="Include total_count")] = False,
        company: Company = None,
    ) -> dict:
        return await _call(READ_SCOPE, lambda: ln.query(
            service, resource, filter=filter, select=select, orderby=orderby, expand=expand,
            top=top, skip=skip, count=count, company=company))

    @mcp.tool(annotations=READ, description="Get one LN record by key.")
    async def ln_get(
        service: Service,
        resource: Resource,
        key: Key,
        select: Annotated[str | None, Field(description="Comma-separated fields to return")] = None,
        expand: Annotated[str | None, Field(description="Navigation properties to expand")] = None,
        company: Company = None,
    ) -> dict:
        return await _call(READ_SCOPE, lambda: ln.get(service, resource, key, select=select, expand=expand,
                                                      company=company))

    @mcp.tool(annotations=WRITE, description=(
        "Create a record in an LN resource. Changes live ERP data. Sales orders and order lines are created with "
        "ln_call_operation (CreateOrder / CreateLine) because their resource fields are read-only."))
    async def ln_create(service: Service, resource: Resource, data: Data, company: Company = None) -> dict:
        return await _call(WRITE_SCOPE, lambda: ln.create(service, resource, data, company=company))

    @mcp.tool(annotations=WRITE, description="Partially update (PATCH) an LN record. Changes live ERP data.")
    async def ln_update(
        service: Service, resource: Resource, key: Key, data: Data, etag: Etag = None, company: Company = None
    ) -> dict:
        return await _call(WRITE_SCOPE, lambda: ln.update(service, resource, key, data, etag=etag, company=company))

    @mcp.tool(annotations=DESTRUCTIVE, description="Delete an LN record. Permanently removes live ERP data.")
    async def ln_delete(service: Service, resource: Resource, key: Key, etag: Etag = None, company: Company = None) -> dict:
        return await _call(WRITE_SCOPE, lambda: ln.delete(service, resource, key, etag=etag, company=company))

    @mcp.tool(annotations=WRITE, description=(
        "Call an LN service operation. Actions (e.g. CreateOrder, CreateLine) change data; functions "
        "(e.g. GetSegmentedItemKey) only read. Use ln_describe for parameters."))
    async def ln_call_operation(
        service: Service,
        operation: Annotated[str, Field(description="Operation name, e.g. 'CreateOrder'")],
        parameters: Annotated[dict[str, Any] | None, Field(description="Operation parameters")] = None,
        company: Company = None,
    ) -> dict:
        async def run() -> dict:
            op, _ = await ln.catalog.operation(service, operation)
            _require_scope(WRITE_SCOPE if op.is_write else READ_SCOPE)
            return await ln.call_operation(service, operation, parameters, company=company)

        return await _call(READ_SCOPE, run)
