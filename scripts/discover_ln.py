"""Phase 2: discover LN OData services and build an endpoint inventory.

LN does not expose a service catalog via API, so services are found by probing
`LN/lnapi/odata/<service>/$metadata` for known/candidate names. Re-run with extra
names to extend the inventory later.

Usage:
  python scripts/discover_ln.py [--ionapi FILE] [--services a.b c.d ...] [--company 1300]
Outputs:
  discovery/ln_endpoint_inventory.json / .md  (committed)
  output/metadata/<service>.json               (raw, git-ignored)
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))
import check_connectivity as conn  # noqa: E402

DEFAULT_SERVICES = """
tdapi.slsSalesOrder tdapi.slsSalesContract tdapi.purPurchaseOrder tdapi.purPurchaseRequisition
tdapi.ipuItemPurchase tdapi.isaItemSales tcapi.comBusinessPartner tcapi.comContact tcapi.ibdItem
tiapi.sfcProductionOrder tsapi.socServiceOrder tsapi.ctmServiceContract tpapi.pdmProject
""".split()


def fetch(cfg, token, rel, company=None, retries=3):
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    if company:
        headers["X-Infor-LnCompany"] = company
    url = f"{cfg['iu']}/{cfg['ti']}/{rel}"
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=120) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            status, body = e.code, e.read()
            # LN intermittently rejects valid tokens with "OAuth [U14]: unknown oauth_consumer_key"
            transient_401 = status == 401 and b"U14" in body
            if status not in (429, 500, 502, 503, 504) and not transient_401:
                return status, body
        except Exception as e:  # network error
            status, body = -1, str(e).encode()
        time.sleep(2 * (attempt + 1))
    return status, body


def summarize(svc, metadata):
    ns = metadata.get(svc, {})
    container = next((v for v in ns.values() if isinstance(v, dict) and v.get("$Kind") == "EntityContainer"), {})
    entity_sets, operations = {}, []
    for name, d in container.items():
        if name.startswith("$") or not isinstance(d, dict):
            continue
        if "$Action" in d or "$Function" in d:
            target = d.get("$Action") or d.get("$Function")
            operations.append({"name": name, "kind": "action" if "$Action" in d else "function",
                               "target": target})
            continue
        if "$Type" not in d:
            continue
        type_name = d["$Type"].split(".")[-1]
        t = ns.get(type_name, {})
        props = {k: v for k, v in t.items() if not k.startswith("$") and isinstance(v, dict)}
        entity_sets[name] = {
            "type": type_name,
            "key": t.get("$Key", []),
            "properties": sorted(k for k, v in props.items() if v.get("$Kind") != "NavigationProperty"),
            "navigations": sorted(k for k, v in props.items() if v.get("$Kind") == "NavigationProperty"),
        }
    return {"base_path": f"LN/lnapi/odata/{svc}", "entity_sets": entity_sets, "operations": operations}


def to_markdown(tenant, inventory, failed):
    out = [f"# LN OData endpoint inventory ({tenant})", "",
           "Base URL: `{iu}/{tenant}/LN/lnapi/odata/<service>/<resource>` — company via `X-Infor-LnCompany` header.", "",
           "| Service | Entity sets | Operations |", "|---|---|---|"]
    for svc, d in inventory.items():
        out.append(f"| `{svc}` | {len(d['entity_sets'])} | {len(d['operations'])} |")
    if failed:
        out += ["", "Not reachable during this run: " + ", ".join(f"`{s}` ({c})" for s, c in failed.items())]
    for svc, d in inventory.items():
        out += ["", f"## {svc}", "", "| Resource | Kind | Key | Properties | Navigations |", "|---|---|---|---|---|"]
        for n, e in d["entity_sets"].items():
            out.append(f"| {n} | entity set | {', '.join(e['key'])} | {len(e['properties'])} | {len(e['navigations'])} |")
        for o in d["operations"]:
            out.append(f"| {o['name']} | {o['kind']} | | | |")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ionapi", default="Files/InforVelocity.ionapi")
    ap.add_argument("--services", nargs="*", default=DEFAULT_SERVICES)
    ap.add_argument("--company", default=None)
    args = ap.parse_args()

    cfg = conn.load_ionapi(args.ionapi)
    token = conn.get_token(cfg)
    os.makedirs("output/metadata", exist_ok=True)
    os.makedirs("discovery", exist_ok=True)

    def probe(svc):
        return (svc, *fetch(cfg, token, f"LN/lnapi/odata/{svc}/$metadata", args.company))

    with ThreadPoolExecutor(4) as ex:
        results = list(ex.map(probe, args.services))

    inventory, failed = {}, {}
    for svc, status, body in results:
        if status != 200:
            failed[svc] = status
            print(f"[miss] {svc} -> {status} {body[:120].decode('utf-8', 'replace')}")
            continue
        with open(f"output/metadata/{svc}.json", "wb") as f:
            f.write(body)
        inventory[svc] = summarize(svc, json.loads(body))
        d = inventory[svc]
        print(f"[ok]   {svc}: {len(d['entity_sets'])} entity sets, {len(d['operations'])} operations")

    with open("discovery/ln_endpoint_inventory.json", "w") as f:
        json.dump(inventory, f, indent=2)
    with open("discovery/ln_endpoint_inventory.md", "w") as f:
        f.write(to_markdown(cfg["ti"], inventory, failed))
    print(f"\n{len(inventory)} services inventoried, {len(failed)} missing -> discovery/ln_endpoint_inventory.md")


if __name__ == "__main__":
    main()
