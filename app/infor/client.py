"""HTTP client for LN APIs behind the Infor ION API gateway."""
import asyncio
import json
from urllib.parse import quote

import httpx

from app.infor.ionapi import IonApiCredentials
from app.infor.token_manager import InforAuthError, InforTokenManager

_RETRY_STATUS = {429, 502, 503, 504}
_QUERY_SAFE = "',()$:/"


class LNError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(f"LN API error {status}: {message}")
        self.status = status
        self.message = message


def build_query(params: dict | None) -> str:
    """Encode OData query options with %20 for spaces (some OData servers read '+' literally)."""
    if not params:
        return ""
    return "?" + "&".join(f"{k}={quote(str(v), safe=_QUERY_SAFE)}" for k, v in params.items() if v is not None)


def extract_error_message(resp: httpx.Response) -> str:
    try:
        body = resp.json()
    except ValueError:
        return resp.text[:500] or resp.reason_phrase
    err = body.get("error") if isinstance(body, dict) else None
    if isinstance(err, list) and err:
        err = err[0]
    if isinstance(err, dict):
        msg = err.get("message") or json.dumps(err)
        details = [d.get("message", "") for d in err.get("details") or [] if isinstance(d, dict)]
        return msg + (" | " + "; ".join(details) if details else "")
    return json.dumps(body)[:500]


class LNClient:
    def __init__(
        self,
        creds: IonApiCredentials,
        tokens: InforTokenManager,
        http: httpx.AsyncClient,
        *,
        max_retries: int = 3,
        backoff_seconds: float = 0.5,
    ):
        self.creds = creds
        self.tokens = tokens
        self.http = http
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds

    async def request(
        self,
        method: str,
        path: str,
        *,
        company: str | None = None,
        params: dict | None = None,
        json: dict | None = None,
        headers: dict | None = None,
    ) -> httpx.Response:
        url = f"{self.creds.base_url}/{path.lstrip('/')}{build_query(params)}"
        attempt = 0
        reauthenticated = False
        while True:
            try:
                token = await self.tokens.get_token()
            except InforAuthError as e:
                raise LNError(502, str(e)) from e
            h = {"Authorization": f"Bearer {token}", "Accept": "application/json", **(headers or {})}
            if company:
                h["X-Infor-LnCompany"] = company
            try:
                resp = await self.http.request(method, url, json=json, headers=h)
            except httpx.TransportError as e:
                # Only retry when the request cannot have been processed (or is idempotent).
                if attempt < self.max_retries and (method == "GET" or isinstance(e, httpx.ConnectError)):
                    attempt += 1
                    await self._sleep(attempt)
                    continue
                raise LNError(503, f"Infor ION API unreachable: {e}") from e

            status = resp.status_code
            if status < 400:
                return resp
            retry = False
            if status == 401 and "U14" in resp.text:
                retry = True  # LN intermittently rejects valid tokens: "OAuth [U14]: unknown oauth_consumer_key"
            elif status == 401 and not reauthenticated:
                self.tokens.invalidate()
                reauthenticated = True
                continue
            elif status in _RETRY_STATUS:
                retry = True
            if retry and attempt < self.max_retries:
                attempt += 1
                await self._sleep(attempt, resp.headers.get("Retry-After"))
                continue
            raise LNError(status, extract_error_message(resp))

    async def get_json(self, path: str, *, company: str | None = None, params: dict | None = None) -> dict:
        return (await self.request("GET", path, company=company, params=params)).json()

    async def _sleep(self, attempt: int, retry_after: str | None = None) -> None:
        delay = self.backoff_seconds * (2 ** (attempt - 1))
        if retry_after and retry_after.isdigit():
            delay = min(float(retry_after), 10.0)
        await asyncio.sleep(delay)
