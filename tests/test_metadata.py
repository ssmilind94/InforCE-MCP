import json

import pytest

from app.infor.metadata import ServiceMetadata, ValidationError
from tests.conftest import FIXTURES


def _load(service: str) -> ServiceMetadata:
    return ServiceMetadata.parse(service, json.loads((FIXTURES / f"{service}.json").read_text()))


@pytest.fixture(scope="module")
def sales():
    return _load("tdapi.slsSalesOrder")


@pytest.fixture(scope="module")
def items():
    return _load("tcapi.ibdItem")


def test_permissions_follow_ln_levels(sales, items):
    assert sales.entity_sets["Orders"].supported_permissions == {"read", "create", "update"}
    assert sales.entity_sets["ActualDeliveryLines"].supported_permissions == {"read"}
    assert items.entity_sets["Items"].supported_permissions == {"read", "create", "update", "delete"}
    assert sales.entity_sets["Orders"].optimistic_concurrency


def test_composite_key_path(sales):
    lines = sales.entity_sets["Lines"]
    key = {"SalesOrder": "100000001", "Line": 10, "SequenceNumber": 0}
    assert lines.key_path(key, sales) == "(SalesOrder='100000001',Line=10,SequenceNumber=0)"


def test_single_key_keeps_padding_and_escapes_quotes(items):
    es = items.entity_sets["Items"]
    assert es.key_path("         1000100", items) == "('%20%20%20%20%20%20%20%20%201000100')"
    assert es.key_path({"Item": "O'Brien"}, items) == "('O''Brien')"


def test_key_errors(sales):
    lines = sales.entity_sets["Lines"]
    with pytest.raises(ValidationError, match="composite"):
        lines.key_path("100000001", sales)
    with pytest.raises(ValidationError, match="missing"):
        lines.key_path({"SalesOrder": "1", "Line": 10}, sales)
    with pytest.raises(ValidationError, match="not valid"):
        lines.key_path({"SalesOrder": "1", "Line": "ten", "SequenceNumber": 0}, sales)


def test_payload_validation(sales, items):
    with pytest.raises(ValidationError, match="Read-only"):
        sales.entity_sets["Orders"].validate_payload({"SoldtoBusinessPartner": "X"}, "create")
    sales.entity_sets["Orders"].validate_payload({"PlannedDeliveryDate": "2026-10-01T00:00:00Z"}, "update")
    with pytest.raises(ValidationError, match="Description"):
        items.entity_sets["Items"].validate_payload({"Descripton": "x"}, "update")
    with pytest.raises(ValidationError, match="Read-only"):
        items.entity_sets["Items"].validate_payload({"Item": "x"}, "update")


def test_operations(sales, items):
    create = sales.operations["CreateOrder"]
    assert create.kind == "action" and create.is_write
    with pytest.raises(ValidationError, match="SoldtoBusinessPartner"):
        create.validate({})
    fn = items.operations["GetSegmentedItemKey"]
    assert fn.kind == "function" and not fn.is_write
    assert fn.function_path({"Item": "1000100"}, items) == "GetSegmentedItemKey(Item='1000100',Project=null)"


def test_describe_enum_and_complex_types(sales):
    orders = sales.entity_sets["Orders"]
    enum_field = next(f for f in orders.fields.values() if f.type in sales.enums)
    described = sales.describe_field(enum_field, read_only=enum_field.computed)
    assert described["type"] == "enum" and described["allowed_values"]
    line_param = next(p for p in sales.operations["CalculateLineAmounts"].parameters if p.name == "Line")
    assert sales.describe_field(line_param)["type"].startswith("object:")
