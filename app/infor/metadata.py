"""Parse LN OData CSDL-JSON $metadata into entity sets, fields, permissions and operations."""
from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import get_close_matches
from urllib.parse import quote

PERMISSIONS = ("read", "create", "update", "delete")

# LN states each entity's supported operation level in the entity type description,
# e.g. "Item_ is Deletable." Levels are cumulative.
_LEVEL_PERMISSIONS = {
    "readablebykey": {"read"},
    "readable": {"read"},
    "creatable": {"read", "create"},
    "updatable": {"read", "create", "update"},
    "deletable": {"read", "create", "update", "delete"},
}
_LEVEL_RE = re.compile(r"\bis (\w+)\.?\s*$")
_INTEGER = {"Edm.Byte", "Edm.SByte", "Edm.Int16", "Edm.Int32", "Edm.Int64"}
_NUMBER = {"Edm.Double", "Edm.Single", "Edm.Decimal"}
_UNQUOTED = {"Edm.DateTimeOffset", "Edm.Date", "Edm.Guid", "Edm.TimeOfDay", "Edm.Duration"}
_COMPUTED = "@Org.OData.Core.V1.Computed"
_DESCRIPTION = "@Core.Description"


class ValidationError(ValueError):
    """Input does not match the LN metadata."""


@dataclass
class FieldInfo:
    name: str
    type: str
    nullable: bool = True
    computed: bool = False
    description: str | None = None
    collection: bool = False


@dataclass
class EntitySetInfo:
    name: str
    type_name: str
    description: str | None
    keys: list[str]
    fields: dict[str, FieldInfo]
    navigations: dict[str, str]
    level: str | None
    optimistic_concurrency: bool

    @property
    def supported_permissions(self) -> set[str]:
        return set(_LEVEL_PERMISSIONS.get((self.level or "").lower(), {"read"}))

    def key_path(self, key, meta: ServiceMetadata) -> str:
        if not isinstance(key, dict):
            if len(self.keys) != 1:
                raise ValidationError(f"{self.name} has a composite key; pass an object with {self.keys}")
            key = {self.keys[0]: key}
        missing = [k for k in self.keys if k not in key]
        extra = [k for k in key if k not in self.keys]
        if missing or extra:
            raise ValidationError(f"{self.name} key must have exactly {self.keys} (missing={missing}, unexpected={extra})")
        parts = [meta.literal(key[k], self.fields[k].type) for k in self.keys]
        if len(parts) == 1:
            return f"({parts[0]})"
        return "(" + ",".join(f"{k}={p}" for k, p in zip(self.keys, parts)) + ")"

    def validate_payload(self, data, mode: str) -> None:
        if not isinstance(data, dict) or not data:
            raise ValidationError("data must be a non-empty object of field names to values")
        known = set(self.fields) | set(self.navigations)
        unknown = [k for k in data if k not in known]
        if unknown:
            hints = {k: get_close_matches(k, known, n=3) for k in unknown}
            raise ValidationError(f"Unknown fields for {self.name}: {hints} (use ln_describe to list fields)")
        read_only = [k for k in data if k in self.fields and self.fields[k].computed]
        if mode == "update":
            read_only += [k for k in data if k in self.keys and k not in read_only]
        if read_only:
            raise ValidationError(f"Read-only fields cannot be set on {mode}: {read_only}")


@dataclass
class ParameterInfo:
    name: str
    type: str
    nullable: bool = True
    collection: bool = False


@dataclass
class OperationInfo:
    name: str
    kind: str  # "action" | "function"
    parameters: list[ParameterInfo]
    return_type: str | None
    returns_collection: bool

    @property
    def is_write(self) -> bool:
        return self.kind == "action"

    def validate(self, params) -> None:
        if not isinstance(params, dict):
            raise ValidationError("parameters must be an object")
        names = {p.name for p in self.parameters}
        unknown = [k for k in params if k not in names]
        if unknown:
            hints = {k: get_close_matches(k, names, n=3) for k in unknown}
            raise ValidationError(f"Unknown parameters for {self.name}: {hints}")
        missing = [p.name for p in self.parameters if not p.nullable and params.get(p.name) in (None, "")]
        if missing:
            raise ValidationError(f"Missing required parameters for {self.name}: {missing}")

    def function_path(self, params: dict, meta: ServiceMetadata) -> str:
        args = ",".join(f"{p.name}={meta.literal(params.get(p.name), p.type)}" for p in self.parameters)
        return f"{self.name}({args})"


@dataclass
class ServiceMetadata:
    service: str
    entity_sets: dict[str, EntitySetInfo]
    operations: dict[str, OperationInfo]
    enums: dict[str, dict[str, str | None]]
    complex_types: dict[str, dict[str, FieldInfo]]
    type_definitions: dict[str, str]

    @classmethod
    def parse(cls, service: str, doc: dict) -> ServiceMetadata:
        namespaces = {k: v for k, v in doc.items() if not k.startswith("$") and isinstance(v, dict)}
        if service not in namespaces:
            raise ValueError(f"Metadata does not contain namespace {service}")
        enums, complex_types, entity_types, typedefs = {}, {}, {}, {}
        for ns_name, ns in namespaces.items():
            for name, defn in ns.items():
                if not isinstance(defn, dict):
                    continue
                fq, kind = f"{ns_name}.{name}", defn.get("$Kind")
                if kind == "EnumType":
                    enums[fq] = {m: defn.get(f"{m}{_DESCRIPTION}") for m in defn if not m.startswith("$") and "@" not in m}
                elif kind == "ComplexType":
                    complex_types[fq] = _parse_fields(defn)
                elif kind == "EntityType":
                    entity_types[fq] = defn
                elif kind in ("TypeDefinition", "DEFINITION"):
                    typedefs[fq] = defn.get("$UnderlyingType", "Edm.String")

        container = next(
            (v for v in namespaces[service].values() if isinstance(v, dict) and v.get("$Kind") == "EntityContainer"), {}
        )
        entity_sets, operations = {}, {}
        for name, entry in container.items():
            if name.startswith("$") or not isinstance(entry, dict):
                continue
            if "$Action" in entry or "$Function" in entry:
                target = entry.get("$Action") or entry.get("$Function")
                ns_name, _, short = target.rpartition(".")
                overloads = namespaces.get(ns_name, {}).get(short) or [{}]
                defn = next((o for o in overloads if not o.get("$IsBound")), overloads[0])
                ret = defn.get("$ReturnType") or {}
                operations[name] = OperationInfo(
                    name=name,
                    kind="action" if "$Action" in entry else "function",
                    parameters=[
                        ParameterInfo(p["$Name"], p.get("$Type", "Edm.String"), p.get("$Nullable", True), bool(p.get("$Collection")))
                        for p in defn.get("$Parameter", [])
                    ],
                    return_type=ret.get("$Type"),
                    returns_collection=bool(ret.get("$Collection")),
                )
            elif "$Type" in entry:
                etype = entity_types.get(entry["$Type"], {})
                description = etype.get(_DESCRIPTION)
                match = _LEVEL_RE.search(description or "")
                entity_sets[name] = EntitySetInfo(
                    name=name,
                    type_name=entry["$Type"],
                    description=description,
                    keys=[k for k in etype.get("$Key", []) if isinstance(k, str)],
                    fields=_parse_fields(etype),
                    navigations={
                        k: v.get("$Type", "").rpartition(".")[2]
                        for k, v in _members(etype).items()
                        if v.get("$Kind") == "NavigationProperty"
                    },
                    level=match.group(1) if match else None,
                    optimistic_concurrency=bool(entry.get("@Org.OData.Core.V1.OptimisticConcurrency")),
                )
        return cls(service, entity_sets, operations, enums, complex_types, typedefs)

    def literal(self, value, edm_type: str) -> str:
        """Format a value as a URL-encoded OData literal for key segments and function arguments."""
        edm_type = self.type_definitions.get(edm_type, edm_type)
        try:
            if value is None:
                lit = "null"
            elif edm_type in _INTEGER:
                lit = str(int(value))
            elif edm_type in _NUMBER:
                lit = str(float(value))
            elif edm_type == "Edm.Boolean":
                lit = "true" if str(value).lower() in ("true", "1") else "false"
            elif edm_type in _UNQUOTED:
                lit = str(value)
            elif edm_type in self.enums:
                lit = f"{edm_type}'{value}'"
            else:
                lit = "'" + str(value).replace("'", "''") + "'"
        except (TypeError, ValueError) as e:
            raise ValidationError(f"Value {value!r} is not valid for type {edm_type}") from e
        return quote(lit, safe="'.-_")

    def type_label(self, edm_type: str) -> str:
        edm_type = self.type_definitions.get(edm_type, edm_type)
        if edm_type in self.enums:
            return "enum"
        if edm_type in self.complex_types:
            return f"object:{edm_type.rpartition('.')[2]}"
        return {
            **{t: "integer" for t in _INTEGER},
            **{t: "number" for t in _NUMBER},
            "Edm.String": "string",
            "Edm.Boolean": "boolean",
            "Edm.DateTimeOffset": "datetime",
            "Edm.Date": "date",
        }.get(edm_type, edm_type)

    def describe_field(self, f: FieldInfo | ParameterInfo, *, read_only: bool | None = None) -> dict:
        out = {"name": f.name, "type": self.type_label(f.type)}
        if getattr(f, "description", None):
            out["description"] = f.description
        if f.collection:
            out["collection"] = True
        if not f.nullable:
            out["nullable"] = False
        if read_only:
            out["read_only"] = True
        resolved = self.type_definitions.get(f.type, f.type)
        if resolved in self.enums:
            out["allowed_values"] = {k: v for k, v in self.enums[resolved].items()}
        if resolved in self.complex_types:
            out["fields"] = [self.describe_field(sub) for sub in self.complex_types[resolved].values()]
        return out


def _members(defn: dict) -> dict[str, dict]:
    return {k: v for k, v in defn.items() if not k.startswith(("$", "@")) and isinstance(v, dict)}


def _parse_fields(defn: dict) -> dict[str, FieldInfo]:
    return {
        k: FieldInfo(
            name=k,
            type=v.get("$Type", "Edm.String"),
            nullable=v.get("$Nullable", True),
            computed=bool(v.get(_COMPUTED)),
            description=v.get(_DESCRIPTION),
            collection=bool(v.get("$Collection")),
        )
        for k, v in _members(defn).items()
        if v.get("$Kind") != "NavigationProperty"
    }
