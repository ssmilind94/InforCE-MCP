"""Configured LN endpoints (config/endpoints.yaml) joined with their live $metadata."""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from app.infor.client import LNClient
from app.infor.metadata import PERMISSIONS, EntitySetInfo, OperationInfo, ServiceMetadata, ValidationError


@dataclass
class ServiceConfig:
    name: str
    description: str = ""
    resources: dict[str, set[str] | None] = field(default_factory=dict)  # None = max permissions
    operations: list[str] = field(default_factory=list)


def _parse_permissions(value, where: str) -> set[str] | None:
    if value in (None, "max"):
        return None
    if isinstance(value, list) and all(p in PERMISSIONS for p in value):
        return set(value)
    raise ValueError(f"{where}: permissions must be 'max' or a list from {PERMISSIONS}, got {value!r}")


def load_endpoint_config(path: Path) -> dict[str, ServiceConfig]:
    doc = yaml.safe_load(path.read_text()) or {}
    default = (doc.get("defaults") or {}).get("permissions", "max")
    services = {}
    for name, svc in (doc.get("services") or {}).items():
        svc = svc or {}
        resources = {
            res: _parse_permissions((cfg or {}).get("permissions", default), f"{name}/{res}")
            for res, cfg in (svc.get("resources") or {}).items()
        }
        services[name] = ServiceConfig(name, svc.get("description", ""), resources, list(svc.get("operations") or []))
    return services


class MetadataLoader:
    def __init__(self, client: LNClient, snapshot_dir: Path | None = None):
        self._client = client
        self._snapshot_dir = snapshot_dir
        self._cache: dict[str, ServiceMetadata] = {}
        self._lock = asyncio.Lock()

    async def load(self, service: str) -> ServiceMetadata:
        if service in self._cache:
            return self._cache[service]
        async with self._lock:
            if service not in self._cache:
                snapshot = self._snapshot_dir / f"{service}.json" if self._snapshot_dir else None
                if snapshot and snapshot.exists():
                    doc = json.loads(snapshot.read_text())
                else:
                    doc = await self._client.get_json(f"LN/lnapi/odata/{service}/$metadata")
                self._cache[service] = ServiceMetadata.parse(service, doc)
        return self._cache[service]


class Catalog:
    def __init__(self, services: dict[str, ServiceConfig], loader: MetadataLoader):
        self.services = services
        self._loader = loader

    def _service_config(self, service: str) -> ServiceConfig:
        if service not in self.services:
            raise ValidationError(f"Service {service!r} is not enabled. Available: {sorted(self.services)}")
        return self.services[service]

    async def metadata(self, service: str) -> ServiceMetadata:
        self._service_config(service)
        return await self._loader.load(service)

    async def entity(self, service: str, resource: str) -> tuple[EntitySetInfo, set[str], ServiceMetadata]:
        cfg = self._service_config(service)
        if resource not in cfg.resources:
            raise ValidationError(f"Resource {resource!r} is not enabled for {service}. Available: {sorted(cfg.resources)}")
        meta = await self._loader.load(service)
        es = meta.entity_sets.get(resource)
        if es is None:
            raise ValidationError(f"Resource {resource!r} does not exist in LN service {service}")
        configured = cfg.resources[resource]
        if configured is None:
            allowed = es.supported_permissions
        elif es.level is None:
            allowed = configured
        else:
            allowed = configured & es.supported_permissions
        return es, allowed, meta

    async def operation(self, service: str, name: str) -> tuple[OperationInfo, ServiceMetadata]:
        cfg = self._service_config(service)
        if name not in cfg.operations:
            raise ValidationError(f"Operation {name!r} is not enabled for {service}. Available: {cfg.operations}")
        meta = await self._loader.load(service)
        op = meta.operations.get(name)
        if op is None:
            raise ValidationError(f"Operation {name!r} does not exist in LN service {service}")
        return op, meta
