"""Manage static MCP bearer tokens (for custom agents that send a fixed Authorization header).

  python scripts/manage_tokens.py create --name "sales-agent" [--scopes ln.read ln.write] [--expires-days 365]
  python scripts/manage_tokens.py list
  python scripts/manage_tokens.py revoke <token_id>

Tokens are shown once and stored only as SHA-256 hashes in the tokens file (default config/tokens.json).
On Azure, put the file content in the STATIC_TOKENS_JSON app setting (scripts/make_app_settings.py --tokens).
--expires-days 0 creates a token that never expires.
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.security.oauth import SCOPES  # noqa: E402
from app.security.static_tokens import generate_token, hash_token  # noqa: E402


def _load(path: Path) -> list[dict]:
    return json.loads(path.read_text()) if path.exists() else []


def _save(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, indent=2) + "\n")
    os.chmod(path, 0o600)


def _when(ts: int | None) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d %H:%M UTC") if ts else "never"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", type=Path, default=Path("config/tokens.json"))
    sub = ap.add_subparsers(dest="cmd", required=True)
    create = sub.add_parser("create")
    create.add_argument("--name", required=True)
    create.add_argument("--scopes", nargs="+", default=list(SCOPES), choices=SCOPES)
    create.add_argument("--expires-days", type=int, default=365, help="0 = never expires")
    sub.add_parser("list")
    revoke = sub.add_parser("revoke")
    revoke.add_argument("token_id")
    args = ap.parse_args()

    entries = _load(args.file)
    if args.cmd == "create":
        token_id, token = generate_token()
        now = int(time.time())
        expires_at = now + args.expires_days * 86400 if args.expires_days > 0 else None
        entries.append({"token_id": token_id, "name": args.name, "scopes": args.scopes,
                        "token_hash": hash_token(token), "created_at": now, "expires_at": expires_at})
        _save(args.file, entries)
        print(f"token_id: {token_id}\ntoken:    {token}\nexpires:  {_when(expires_at)}\n"
              "(store the token now; it cannot be shown again)")
    elif args.cmd == "list":
        now = time.time()
        for e in entries:
            expired = " EXPIRED" if e.get("expires_at") and e["expires_at"] <= now else ""
            print(f"{e['token_id']}  name={e.get('name')!r}  scopes={e.get('scopes')}  "
                  f"expires={_when(e.get('expires_at'))}{expired}")
    elif args.cmd == "revoke":
        remaining = [e for e in entries if e["token_id"] != args.token_id]
        if len(remaining) == len(entries):
            sys.exit(f"token {args.token_id} not found")
        _save(args.file, remaining)
        print(f"revoked {args.token_id} (update STATIC_TOKENS_JSON on Azure for it to take effect)")


if __name__ == "__main__":
    main()
