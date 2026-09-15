"""Phase 1: verify Infor ION API connectivity using a backend service account .ionapi file.

Usage: python check_connectivity.py [path/to/file.ionapi] [extra/relative/path ...]
Secrets and tokens are never printed.
"""
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

IONAPI = sys.argv[1] if len(sys.argv) > 1 else "Files/InforVelocity.ionapi"
EXTRA_PATHS = sys.argv[2:]


def load_ionapi(path):
    with open(path) as f:
        return json.load(f)


def get_token(cfg):
    url = cfg["pu"] + cfg["ot"]
    body = urllib.parse.urlencode({
        "grant_type": "password",
        "username": cfg["saak"],
        "password": cfg["sask"],
        "client_id": cfg["ci"],
        "client_secret": cfg["cs"],
    }).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    started = time.time()
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    print(f"[token] OK in {time.time() - started:.2f}s  type={data.get('token_type')}  "
          f"expires_in={data.get('expires_in')}s  refresh_token={'yes' if data.get('refresh_token') else 'no'}")
    return data["access_token"]


def probe(cfg, token, rel_path):
    url = f"{cfg['iu']}/{cfg['ti']}/{rel_path.lstrip('/')}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            status, ctype, body = resp.status, resp.headers.get("Content-Type"), resp.read()
    except urllib.error.HTTPError as e:
        status, ctype, body = e.code, e.headers.get("Content-Type"), e.read()
    except Exception as e:  # network errors
        print(f"[probe] {rel_path} -> ERROR {e}")
        return
    snippet = body[:300].decode("utf-8", "replace").replace("\n", " ")
    print(f"[probe] {rel_path} -> {status} ({ctype}, {len(body)} bytes)\n        {snippet}")


def main():
    cfg = load_ionapi(IONAPI)
    print(f"tenant={cfg['ti']}  gateway={cfg['iu']}  client={cfg['cn']}")
    try:
        token = get_token(cfg)
    except urllib.error.HTTPError as e:
        print(f"[token] FAILED {e.code}: {e.read()[:300].decode('utf-8', 'replace')}")
        sys.exit(1)

    paths = EXTRA_PATHS or [
        "Mingle/SocialService.Svc/User/Detail",  # gateway + identity sanity check
        "LN/lnapi/odata/$metadata",                # LN OData root (may 404 without a service name)
    ]
    for p in paths:
        probe(cfg, token, p)


if __name__ == "__main__":
    main()
