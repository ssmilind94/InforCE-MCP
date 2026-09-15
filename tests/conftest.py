from pathlib import Path

import httpx
import pytest
import respx

from app.config import COMPANY_PLACEHOLDER
from app.infor.catalog import Catalog, MetadataLoader, load_endpoint_config
from app.infor.client import LNClient
from app.infor.ionapi import IonApiCredentials
from app.infor.ln_service import LNService
from app.infor.token_manager import InforTokenManager

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "metadata"
CREDS = IonApiCredentials(
    tenant="TENANT",
    client_id="ci",
    client_secret="cs",
    gateway_url="https://ionapi.test",
    sso_url="https://sso.test/TENANT/as/",
    token_path="token.oauth2",
    service_account_key="saak",
    service_account_secret="sask",
)
LN_BASE = f"{CREDS.base_url}/LN/lnapi/odata"


@pytest.fixture
def infor():
    """Mocked Infor ION API (token endpoint pre-registered)."""
    with respx.mock(assert_all_called=False) as router:
        router.post(CREDS.token_url).mock(return_value=httpx.Response(
            200, json={"access_token": "infor-token", "expires_in": 7200, "refresh_token": "r1"}))
        yield router


@pytest.fixture
def ln(infor):
    http = httpx.AsyncClient()
    client = LNClient(CREDS, InforTokenManager(CREDS, http), http, max_retries=2, backoff_seconds=0)
    catalog = Catalog(load_endpoint_config(ROOT / "config" / "endpoints.yaml"), MetadataLoader(client, FIXTURES))
    return LNService(client, catalog, default_company=COMPANY_PLACEHOLDER)
