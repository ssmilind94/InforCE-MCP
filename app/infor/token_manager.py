"""Cached OAuth2 token for the Infor backend service account (password grant + refresh)."""
import asyncio
import time

import httpx

from app.infor.ionapi import IonApiCredentials


class InforAuthError(Exception):
    pass


class InforTokenManager:
    def __init__(self, creds: IonApiCredentials, http: httpx.AsyncClient, *, expiry_skew: int = 120):
        self._creds = creds
        self._http = http
        self._skew = expiry_skew
        self._token: str | None = None
        self._refresh_token: str | None = None
        self._expires_at = 0.0
        self._lock = asyncio.Lock()

    async def get_token(self) -> str:
        if self._valid():
            return self._token
        async with self._lock:
            if self._valid():
                return self._token
            data = None
            if self._refresh_token:
                try:
                    data = await self._request({"grant_type": "refresh_token", "refresh_token": self._refresh_token})
                except InforAuthError:
                    data = None
            if data is None:
                data = await self._request({
                    "grant_type": "password",
                    "username": self._creds.service_account_key,
                    "password": self._creds.service_account_secret,
                })
            self._token = data["access_token"]
            self._refresh_token = data.get("refresh_token")
            self._expires_at = time.monotonic() + max(int(data.get("expires_in", 3600)) - self._skew, 30)
            return self._token

    def invalidate(self) -> None:
        """Drop the access token (keeps the refresh token) so the next call re-authenticates."""
        self._token = None
        self._expires_at = 0.0

    def _valid(self) -> bool:
        return self._token is not None and time.monotonic() < self._expires_at

    async def _request(self, form: dict) -> dict:
        form = {**form, "client_id": self._creds.client_id, "client_secret": self._creds.client_secret}
        try:
            resp = await self._http.post(self._creds.token_url, data=form, timeout=30)
        except httpx.HTTPError as e:
            raise InforAuthError(f"Infor token endpoint unreachable: {e}") from e
        if resp.status_code != 200:
            raise InforAuthError(f"Infor token request failed ({resp.status_code}): {resp.text[:200]}")
        return resp.json()
