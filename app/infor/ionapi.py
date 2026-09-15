"""Load Infor ION API backend service account credentials (.ionapi)."""
import json
from dataclasses import dataclass
from pathlib import Path

_REQUIRED = ("ti", "ci", "cs", "iu", "pu", "ot", "saak", "sask")


@dataclass(frozen=True)
class IonApiCredentials:
    tenant: str
    client_id: str
    client_secret: str
    gateway_url: str
    sso_url: str
    token_path: str
    service_account_key: str
    service_account_secret: str

    @classmethod
    def from_dict(cls, data: dict) -> "IonApiCredentials":
        missing = [k for k in _REQUIRED if not data.get(k)]
        if missing:
            raise ValueError(f".ionapi is missing {missing}; a backend service account file (with saak/sask) is required")
        return cls(
            tenant=data["ti"],
            client_id=data["ci"],
            client_secret=data["cs"],
            gateway_url=data["iu"].rstrip("/"),
            sso_url=data["pu"],
            token_path=data["ot"],
            service_account_key=data["saak"],
            service_account_secret=data["sask"],
        )

    @property
    def token_url(self) -> str:
        return self.sso_url.rstrip("/") + "/" + self.token_path.lstrip("/")

    @property
    def base_url(self) -> str:
        return f"{self.gateway_url}/{self.tenant}"


def load_credentials(ionapi_json: str | None, ionapi_file: Path | None) -> IonApiCredentials:
    if ionapi_json:
        return IonApiCredentials.from_dict(json.loads(ionapi_json))
    if ionapi_file and ionapi_file.exists():
        return IonApiCredentials.from_dict(json.loads(ionapi_file.read_text()))
    raise ValueError("No Infor credentials: set IONAPI_JSON or IONAPI_FILE")
