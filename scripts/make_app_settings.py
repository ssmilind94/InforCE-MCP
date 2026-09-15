"""Generate Azure Web App application settings as JSON for Portal > Environment variables > Advanced edit.

  python scripts/make_app_settings.py --app-url https://<app>.azurewebsites.net \
      [--ionapi Files/InforVelocity.ionapi] [--clients config/clients.azure.json] \
      [--tokens config/tokens.azure.json] [--company __LN_COMPANY__] [--out output/azure-appsettings.json] \
      [--rotate-jwt-secret]

The output contains secrets: it is written with mode 0600 under output/ (git-ignored).
An existing OAUTH_JWT_SECRET in the output file is reused so issued tokens stay valid,
unless --rotate-jwt-secret is given.
"""
import argparse
import json
import os
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import COMPANY_PLACEHOLDER  # noqa: E402
from app.infor.ionapi import IonApiCredentials  # noqa: E402
from app.security.oauth import ClientStore  # noqa: E402
from app.security.static_tokens import StaticTokenVerifier  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--app-url", required=True, help="Public HTTPS URL of the Web App")
    ap.add_argument("--ionapi", type=Path, default=Path("Files/InforVelocity.ionapi"))
    ap.add_argument("--clients", type=Path, default=Path("config/clients.azure.json"),
                    help="Client registry for Azure (create with manage_clients.py --file ...)")
    ap.add_argument("--tokens", type=Path, default=Path("config/tokens.azure.json"),
                    help="Static bearer tokens for Azure (create with manage_tokens.py --file ...); optional")
    ap.add_argument("--company", default=COMPANY_PLACEHOLDER)
    ap.add_argument("--out", type=Path, default=Path("output/azure-appsettings.json"))
    ap.add_argument("--rotate-jwt-secret", action="store_true")
    args = ap.parse_args()

    app_url = args.app_url.rstrip("/")
    if not app_url.startswith("https://"):
        sys.exit("--app-url must be the public https:// URL")

    ionapi = json.loads(args.ionapi.read_text())
    IonApiCredentials.from_dict(ionapi)  # validate before shipping
    if not args.clients.exists():
        sys.exit(f"{args.clients} not found; create a client with: "
                 f"python scripts/manage_clients.py --file {args.clients} create --name <name>")
    clients = json.loads(args.clients.read_text())
    if not len(ClientStore.from_entries(clients)):
        sys.exit(f"{args.clients} has no clients")

    jwt_secret = None
    if args.out.exists() and not args.rotate_jwt_secret:
        previous = {s["name"]: s["value"] for s in json.loads(args.out.read_text())}
        jwt_secret = previous.get("OAUTH_JWT_SECRET")

    settings = {
        "SCM_DO_BUILD_DURING_DEPLOYMENT": "true",
        "PUBLIC_BASE_URL": app_url,
        "LN_DEFAULT_COMPANY": args.company,
        "IONAPI_JSON": json.dumps(ionapi, separators=(",", ":")),
        "OAUTH_JWT_SECRET": jwt_secret or secrets.token_urlsafe(48),
        "OAUTH_CLIENTS_JSON": json.dumps(clients, separators=(",", ":")),
    }
    tokens = json.loads(args.tokens.read_text()) if args.tokens.exists() else []
    if tokens:
        StaticTokenVerifier.from_entries(tokens)  # validate before shipping
        settings["STATIC_TOKENS_JSON"] = json.dumps(tokens, separators=(",", ":"))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(args.out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump([{"name": k, "value": v, "slotSetting": False} for k, v in settings.items()], f, indent=2)
        f.write("\n")
    os.chmod(args.out, 0o600)
    print(f"wrote {args.out} ({len(settings)} settings, {len(clients)} client(s), {len(tokens)} static token(s), "
          f"company={args.company})")
    print("Portal: Web App > Settings > Environment variables > Advanced edit: merge these entries, then Apply.")


if __name__ == "__main__":
    main()
