import json

import httpx
import pytest

from app.infor.client import LNError
from app.infor.ln_service import PermissionDenied
from app.infor.metadata import ValidationError
from tests.conftest import LN_BASE

ITEM_URL = f"{LN_BASE}/tcapi.ibdItem/Items('%20%20%20%20%20%20%20%20%201000100')"


async def test_query_sends_company_and_encodes_filter(ln, infor):
    route = infor.get(url__startswith=f"{LN_BASE}/tdapi.slsSalesOrder/Orders").mock(return_value=httpx.Response(
        200, json={"@odata.count": 41, "value": [{"SalesOrder": "1"}, {"SalesOrder": "2"}]}))
    out = await ln.query("tdapi.slsSalesOrder", "Orders", filter="SoldtoBusinessPartner eq '100000001'",
                         select="SalesOrder", top=2, count=True, company="1300")
    req = route.calls.last.request
    assert req.headers["X-Infor-LnCompany"] == "1300"
    assert req.headers["Authorization"] == "Bearer infor-token"
    assert "SoldtoBusinessPartner%20eq%20'100000001'" in str(req.url)
    assert out["total_count"] == 41 and out["returned"] == 2 and out["next_skip"] == 2


async def test_missing_company_fails_before_calling_ln(ln, infor):
    with pytest.raises(ValidationError, match="company"):
        await ln.query("tcapi.ibdItem", "Items")
    assert not any("lnapi" in str(call.request.url) for call in infor.calls)


async def test_permissions_enforced(ln):
    with pytest.raises(PermissionDenied):
        await ln.delete("tdapi.slsSalesOrder", "Orders", "100000001", company="1300")
    with pytest.raises(PermissionDenied):
        await ln.update("tdapi.slsSalesOrder", "ActualDeliveryLines", {}, {"Shipment": "X"}, company="1300")


async def test_unconfigured_resource_rejected(ln):
    with pytest.raises(ValidationError, match="not enabled"):
        await ln.query("tdapi.slsSalesOrder", "Currencies", company="1300")
    with pytest.raises(ValidationError, match="not enabled"):
        await ln.query("tdapi.purPurchaseOrder", "Orders", company="1300")


async def test_update_fetches_etag_then_patches(ln, infor):
    infor.get(url__startswith=ITEM_URL).mock(return_value=httpx.Response(
        200, json={"@odata.etag": 'W/"abc"', "Item": "         1000100"}))
    patch = infor.patch(ITEM_URL).mock(return_value=httpx.Response(200, json={"Description": "New"}))
    out = await ln.update("tcapi.ibdItem", "Items", "         1000100", {"Description": "New"}, company="1300")
    req = patch.calls.last.request
    assert req.headers["If-Match"] == 'W/"abc"'
    assert json.loads(req.content) == {"Description": "New"}
    assert out["updated"] and out["record"] == {"Description": "New"}


async def test_delete_uses_given_etag(ln, infor):
    delete = infor.delete(f"{LN_BASE}/tcapi.comBusinessPartner/BusinessPartners('BP1')").mock(
        return_value=httpx.Response(204))
    out = await ln.delete("tcapi.comBusinessPartner", "BusinessPartners", "BP1", etag='W/"e1"', company="1300")
    assert delete.calls.last.request.headers["If-Match"] == 'W/"e1"'
    assert out["deleted"]


async def test_create(ln, infor):
    with pytest.raises(ValidationError, match="Read-only"):
        await ln.create("tdapi.slsSalesOrder", "Orders", {"SoldtoBusinessPartner": "BP1"}, company="1300")
    post = infor.post(f"{LN_BASE}/tcapi.ibdItem/Items").mock(return_value=httpx.Response(
        201, json={"@odata.context": "ctx", "Item": "NEW"}))
    out = await ln.create("tcapi.ibdItem", "Items", {"Item": "NEW", "Description": "Test"}, company="1300")
    assert json.loads(post.calls.last.request.content) == {"Item": "NEW", "Description": "Test"}
    assert out["record"] == {"Item": "NEW"}


async def test_action_and_function(ln, infor):
    infor.post(f"{LN_BASE}/tdapi.slsSalesOrder/CreateOrder").mock(return_value=httpx.Response(
        200, json={"SalesOrder": "SO1"}))
    out = await ln.call_operation("tdapi.slsSalesOrder", "CreateOrder", {"SoldtoBusinessPartner": "BP1"}, company="1300")
    assert out["result"] == {"SalesOrder": "SO1"}

    fn = infor.get(url__startswith=f"{LN_BASE}/tcapi.ibdItem/GetSegmentedItemKey(").mock(
        return_value=httpx.Response(200, json={"value": "         1000100"}))
    await ln.call_operation("tcapi.ibdItem", "GetSegmentedItemKey", {"Item": "1000100"}, company="1300")
    assert "Item='1000100',Project=null" in str(fn.calls.last.request.url)


async def test_retries_transient_u14(ln, infor):
    route = infor.get(url__startswith=f"{LN_BASE}/tcapi.ibdItem/Items").mock(side_effect=[
        httpx.Response(401, json={"error": {"message": "OAuth [U14]: unknown oauth_consumer_key"}}),
        httpx.Response(200, json={"value": []}),
    ])
    await ln.query("tcapi.ibdItem", "Items", company="1300")
    assert route.call_count == 2


async def test_reauthenticates_with_refresh_token_on_401(ln, infor):
    route = infor.get(url__startswith=f"{LN_BASE}/tcapi.ibdItem/Items").mock(side_effect=[
        httpx.Response(401, json={"error": {"message": "token expired"}}),
        httpx.Response(200, json={"value": []}),
    ])
    await ln.query("tcapi.ibdItem", "Items", company="1300")
    token_calls = [c for c in infor.calls if "token.oauth2" in str(c.request.url)]
    assert route.call_count == 2 and len(token_calls) == 2
    assert b"grant_type=refresh_token" in token_calls[1].request.content


async def test_ln_error_message_surfaces(ln, infor):
    infor.get(url__startswith=f"{LN_BASE}/tdapi.slsSalesOrder/Orders").mock(return_value=httpx.Response(
        422, json={"error": {"code": "ERROR", "message": "Switch to company 100 failed"}}))
    with pytest.raises(LNError, match="Switch to company 100 failed"):
        await ln.query("tdapi.slsSalesOrder", "Orders", company="100")
