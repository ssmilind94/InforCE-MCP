"""LN operations behind the MCP tools: permission checks, validation and OData request building."""
from __future__ import annotations

from app.config import COMPANY_PLACEHOLDER
from app.infor.catalog import Catalog
from app.infor.client import LNClient
from app.infor.metadata import ValidationError


class PermissionDenied(Exception):
    pass


def _clean(body):
    if isinstance(body, dict):
        return {k: v for k, v in body.items() if k != "@odata.context"}
    return body


class LNService:
    def __init__(self, client: LNClient, catalog: Catalog, *, default_company: str, max_top: int = 500):
        self.client = client
        self.catalog = catalog
        self.default_company = default_company
        self.max_top = max_top

    def resolve_company(self, company: str | None) -> str:
        resolved = (company or self.default_company or "").strip()
        if not resolved or resolved == COMPANY_PLACEHOLDER:
            raise ValidationError("No LN company specified. Pass `company` or configure LN_DEFAULT_COMPANY.")
        return resolved

    @staticmethod
    def _require(allowed: set[str], permission: str, service: str, resource: str) -> None:
        if permission not in allowed:
            raise PermissionDenied(f"'{permission}' is not permitted on {service}/{resource} (allowed: {sorted(allowed)})")

    @staticmethod
    def _path(service: str, resource: str) -> str:
        return f"LN/lnapi/odata/{service}/{resource}"

    async def list_resources(self) -> dict:
        services = []
        for name, cfg in self.catalog.services.items():
            entry = {"service": name, "description": cfg.description, "resources": [], "operations": []}
            try:
                for res in cfg.resources:
                    es, allowed, _ = await self.catalog.entity(name, res)
                    entry["resources"].append({
                        "resource": res,
                        "description": es.description,
                        "keys": es.keys,
                        "permissions": sorted(allowed),
                    })
                for op_name in cfg.operations:
                    op, _ = await self.catalog.operation(name, op_name)
                    entry["operations"].append({
                        "operation": op_name,
                        "kind": op.kind,
                        "required_parameters": [p.name for p in op.parameters if not p.nullable],
                    })
            except Exception as e:  # metadata unavailable: still show what is configured
                entry["error"] = str(e)
                entry["resources"] = entry["resources"] or list(cfg.resources)
                entry["operations"] = entry["operations"] or cfg.operations
            services.append(entry)
        return {"default_company": None if self.default_company == COMPANY_PLACEHOLDER else self.default_company,
                "services": services}

    async def describe(self, service: str, name: str) -> dict:
        meta = await self.catalog.metadata(service)
        if name in self.catalog.services[service].operations:
            op, meta = await self.catalog.operation(service, name)
            return {
                "service": service,
                "operation": name,
                "kind": op.kind,
                "writes_data": op.is_write,
                "parameters": [meta.describe_field(p) for p in op.parameters],
                "returns": {"type": op.return_type, "collection": op.returns_collection},
            }
        es, allowed, meta = await self.catalog.entity(service, name)
        return {
            "service": service,
            "resource": name,
            "description": es.description,
            "keys": [meta.describe_field(es.fields[k]) for k in es.keys],
            "permissions": sorted(allowed),
            "requires_etag_for_changes": es.optimistic_concurrency,
            "fields": [meta.describe_field(f, read_only=f.computed) for f in es.fields.values()],
            "navigations": es.navigations,
        }

    async def query(self, service, resource, *, filter=None, select=None, orderby=None, expand=None,
                    top=25, skip=0, count=False, company=None) -> dict:
        es, allowed, _ = await self.catalog.entity(service, resource)
        self._require(allowed, "read", service, resource)
        co = self.resolve_company(company)
        top = max(1, min(int(top or 25), self.max_top))
        skip = max(0, int(skip or 0))
        params = {"$filter": filter, "$select": select, "$orderby": orderby, "$expand": expand,
                  "$top": top, "$skip": skip or None, "$count": "true" if count else None}
        data = await self.client.get_json(self._path(service, resource), company=co, params=params)
        items = data.get("value", [])
        return {
            "company": co,
            "total_count": data.get("@odata.count"),
            "returned": len(items),
            "next_skip": skip + len(items) if len(items) == top else None,
            "items": items,
        }

    async def get(self, service, resource, key, *, select=None, expand=None, company=None) -> dict:
        es, allowed, meta = await self.catalog.entity(service, resource)
        self._require(allowed, "read", service, resource)
        co = self.resolve_company(company)
        path = self._path(service, resource) + es.key_path(key, meta)
        data = await self.client.get_json(path, company=co, params={"$select": select, "$expand": expand})
        return {"company": co, "record": _clean(data)}

    async def create(self, service, resource, data, *, company=None) -> dict:
        es, allowed, _ = await self.catalog.entity(service, resource)
        self._require(allowed, "create", service, resource)
        es.validate_payload(data, "create")
        co = self.resolve_company(company)
        resp = await self.client.request("POST", self._path(service, resource), company=co, json=data,
                                         headers={"Prefer": "return=representation"})
        return {"company": co, "created": True, "record": _clean(resp.json()) if resp.content else None}

    async def update(self, service, resource, key, data, *, etag=None, company=None) -> dict:
        es, allowed, meta = await self.catalog.entity(service, resource)
        self._require(allowed, "update", service, resource)
        es.validate_payload(data, "update")
        co = self.resolve_company(company)
        path = self._path(service, resource) + es.key_path(key, meta)
        etag = etag or await self._current_etag(es, path, co)
        headers = {"Prefer": "return=representation", **({"If-Match": etag} if etag else {})}
        resp = await self.client.request("PATCH", path, company=co, json=data, headers=headers)
        return {"company": co, "updated": True, "record": _clean(resp.json()) if resp.content else None}

    async def delete(self, service, resource, key, *, etag=None, company=None) -> dict:
        es, allowed, meta = await self.catalog.entity(service, resource)
        self._require(allowed, "delete", service, resource)
        co = self.resolve_company(company)
        path = self._path(service, resource) + es.key_path(key, meta)
        etag = etag or await self._current_etag(es, path, co)
        await self.client.request("DELETE", path, company=co, headers={"If-Match": etag} if etag else None)
        return {"company": co, "deleted": True, "key": key}

    async def call_operation(self, service, operation, parameters=None, *, company=None) -> dict:
        op, meta = await self.catalog.operation(service, operation)
        parameters = parameters or {}
        op.validate(parameters)
        co = self.resolve_company(company)
        base = f"LN/lnapi/odata/{service}/"
        if op.kind == "function":
            data = await self.client.get_json(base + op.function_path(parameters, meta), company=co)
        else:
            resp = await self.client.request("POST", base + operation, company=co, json=parameters)
            data = resp.json() if resp.content else None
        return {"company": co, "operation": operation, "result": _clean(data)}

    async def _current_etag(self, es, path: str, company: str) -> str | None:
        if not es.optimistic_concurrency:
            return None
        current = await self.client.get_json(path, company=company, params={"$select": ",".join(es.keys)})
        return current.get("@odata.etag")
