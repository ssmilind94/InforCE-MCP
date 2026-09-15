"""Application settings, read from environment variables (or a local .env file)."""
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Placeholder until the LN company is decided; tools fail clearly unless a company is passed per call.
COMPANY_PLACEHOLDER = "__LN_COMPANY__"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Infor ION API ---
    ionapi_file: Path | None = Path("Files/InforVelocity.ionapi")
    ionapi_json: str | None = None  # full .ionapi content; takes precedence (App Setting on Azure)
    ln_default_company: str = COMPANY_PLACEHOLDER
    endpoints_file: Path = Path("config/endpoints.yaml")
    metadata_snapshot_dir: Path | None = None  # optional offline $metadata snapshots (<service>.json)
    infor_timeout_seconds: float = 60.0
    infor_max_retries: int = 3
    query_max_top: int = 500

    # --- MCP server / OAuth2 ---
    public_base_url: str = "http://localhost:8000"
    allowed_hosts: list[str] = []  # extra Host headers to accept, e.g. ["myapp.azurewebsites.net"]
    oauth_jwt_secret: str = Field(min_length=32)
    oauth_access_token_ttl: int = 3600
    oauth_refresh_token_ttl: int = 30 * 24 * 3600
    oauth_clients_json: str | None = None  # JSON list of clients; takes precedence over the file
    oauth_clients_file: Path | None = Path("config/clients.json")
    static_tokens_json: str | None = None  # JSON list of static bearer tokens; takes precedence over the file
    static_tokens_file: Path | None = Path("config/tokens.json")

    @property
    def base_url(self) -> str:
        return self.public_base_url.rstrip("/")

    @property
    def mcp_resource_url(self) -> str:
        return f"{self.base_url}/mcp"


@lru_cache
def get_settings() -> Settings:
    return Settings()
