"""Manage MCP OAuth2 clients (internally generated client IDs and secrets).

  python scripts/manage_clients.py create --name "Claude" [--scopes ln.read ln.write] [--redirect-uri URI ...]
  python scripts/manage_clients.py list
  python scripts/manage_clients.py delete <client_id>
  python scripts/manage_clients.py jwt-secret

Secrets are shown once and stored only as PBKDF2 hashes in the clients file
(default config/clients.json). On Azure, put the file content in the OAUTH_CLIENTS_JSON app setting.
"""
import argparse
import json
import os
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.security.oauth import SCOPES, hash_secret  # noqa: E402


def _load(path: Path) -> list[dict]:
    return json.loads(path.read_text()) if path.exists() else []


def _save(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, indent=2) + "\n")
    os.chmod(path, 0o600)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", type=Path, default=Path("config/clients.json"))
    sub = ap.add_subparsers(dest="cmd", required=True)
    create = sub.add_parser("create")
    create.add_argument("--name", required=True)
    create.add_argument("--scopes", nargs="+", default=list(SCOPES), choices=SCOPES)
    create.add_argument("--redirect-uri", action="append", default=[])
    sub.add_parser("list")
    delete = sub.add_parser("delete")
    delete.add_argument("client_id")
    sub.add_parser("jwt-secret")
    args = ap.parse_args()

    if args.cmd == "jwt-secret":
        print(secrets.token_urlsafe(48))
        return

    entries = _load(args.file)
    if args.cmd == "create":
        client_id = f"ln-mcp-{secrets.token_hex(8)}"
        secret = secrets.token_urlsafe(40)
        entries.append({"client_id": client_id, "name": args.name, "scopes": args.scopes,
                        "redirect_uris": args.redirect_uri, "secret_hash": hash_secret(secret)})
        _save(args.file, entries)
        print(f"client_id:     {client_id}\nclient_secret: {secret}\n(store the secret now; it cannot be shown again)")
    elif args.cmd == "list":
        for e in entries:
            print(f"{e['client_id']}  name={e.get('name')!r}  scopes={e.get('scopes')}  redirect_uris={e.get('redirect_uris')}")
    elif args.cmd == "delete":
        remaining = [e for e in entries if e["client_id"] != args.client_id]
        if len(remaining) == len(entries):
            sys.exit(f"client {args.client_id} not found")
        _save(args.file, remaining)
        print(f"deleted {args.client_id}")


if __name__ == "__main__":
    main()
