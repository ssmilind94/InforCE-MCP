"""Live end-to-end smoke test (read-only): bearer token -> MCP client -> every configured LN resource.

  python scripts/smoke_test.py --base-url http://localhost:8000 \
      --client-id ln-mcp-... --client-secret ... --company 1300          # OAuth2 client_credentials
  MCP_BEARER_TOKEN=lnmcp_... python scripts/smoke_test.py --base-url ... --company 1300   # static token
"""
import argparse
import asyncio
import json
import os
import sys

import httpx
import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

EXPECTED_TOOLS = {"ln_list_resources", "ln_describe", "ln_query", "ln_get", "ln_create", "ln_update", "ln_delete",
                  "ln_call_operation"}


class Runner:
    def __init__(self, session: ClientSession):
        self.session = session
        self.results: list[tuple[str, bool, str]] = []

    def check(self, name: str, ok: bool, detail: str = "") -> bool:
        self.results.append((name, ok, detail))
        print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")
        return ok

    async def call(self, tool: str, args: dict) -> tuple[bool, dict | str]:
        res = await self.session.call_tool(tool, args)
        data = res.structured_content
        if isinstance(data, dict) and set(data) == {"result"}:
            data = data["result"]
        if data is None:
            text = "".join(getattr(c, "text", "") for c in res.content)
            try:
                data = json.loads(text)
            except ValueError:
                data = text
        return bool(res.is_error), data


async def run(args) -> int:
    if args.token:
        token = args.token
        print("INFO  using static bearer token (no OAuth2 exchange)")
    else:
        resp = httpx.post(f"{args.base_url}/oauth/token", data={"grant_type": "client_credentials"},
                          auth=(args.client_id, args.client_secret), timeout=30)
        resp.raise_for_status()
        token = resp.json()["access_token"]
        print(f"PASS  oauth client_credentials  scope={resp.json()['scope']!r}")

    headers = {"Authorization": f"Bearer {token}"}
    async with httpx2.AsyncClient(headers=headers, timeout=httpx2.Timeout(180)) as http:
        async with streamable_http_client(f"{args.base_url}/mcp", http_client=http) as (read, write):
            async with ClientSession(read, write) as session:
                r = Runner(session)
                init = await session.initialize()
                r.check("mcp initialize", init.server_info.name == "infor-ln-mcp",
                        f"server={init.server_info.name} protocol={init.protocol_version}")

                tools = {t.name for t in (await session.list_tools()).tools}
                r.check("tools/list", tools == EXPECTED_TOOLS, f"{len(tools)} tools")

                err, catalog = await r.call("ln_list_resources", {})
                r.check("ln_list_resources", not err and all("error" not in s for s in catalog["services"]),
                        "" if not err else str(catalog)[:300])
                services = catalog["services"] if not err else []

                for svc in services:
                    for res in svc["resources"]:
                        name = f"{svc['service']}/{res['resource']}"
                        err, desc = await r.call("ln_describe", {"service": svc["service"], "name": res["resource"]})
                        r.check(f"describe {name}", not err, f"fields={len(desc.get('fields', [])) if not err else desc}"
                                f" permissions={res['permissions']}")

                        err, page = await r.call("ln_query", {
                            "service": svc["service"], "resource": res["resource"], "select": ",".join(res["keys"]),
                            "top": 2, "count": True, "company": args.company})
                        if not r.check(f"query {name}", not err,
                                       f"total={page.get('total_count')} returned={page.get('returned')}" if not err else str(page)[:300]):
                            continue
                        if not page["items"]:
                            continue
                        row = page["items"][0]
                        key = {k: row[k] for k in res["keys"]}
                        key_arg = key if len(key) > 1 else row[res["keys"][0]]
                        err, rec = await r.call("ln_get", {"service": svc["service"], "resource": res["resource"],
                                                           "key": key_arg, "company": args.company})
                        ok = not err and all(rec["record"].get(k) == v for k, v in key.items())
                        r.check(f"get {name}", ok, json.dumps(key) if ok else str(rec)[:300])

                    for op in svc["operations"]:
                        err, desc = await r.call("ln_describe", {"service": svc["service"], "name": op["operation"]})
                        r.check(f"describe {svc['service']}/{op['operation']}", not err,
                                f"kind={op['kind']} required={op['required_parameters']}")

                err, out = await r.call("ln_query", {
                    "service": "tcapi.comBusinessPartner", "resource": "BusinessPartners",
                    "filter": "contains(Name,'a')", "select": "BusinessPartner,Name", "orderby": "BusinessPartner",
                    "top": 3, "company": args.company})
                r.check("query with filter/orderby", not err, f"returned={out.get('returned')}" if not err else str(out)[:300])

                err, out = await r.call("ln_query", {
                    "service": "tdapi.slsSalesOrder", "resource": "Orders", "select": "SalesOrder",
                    "expand": "LineRefs($select=Line,Item,OrderedQuantity)", "top": 1, "company": args.company})
                r.check("query with expand", not err,
                        f"lines={len(out['items'][0].get('LineRefs', [])) if not err and out['items'] else 0}" if not err else str(out)[:300])

                err, out = await r.call("ln_call_operation", {
                    "service": "tcapi.ibdItem", "operation": "GetSegmentedItemKey",
                    "parameters": {"Item": "1000100"}, "company": args.company})
                r.check("function GetSegmentedItemKey", not err, str(out)[:200])

                err, out = await r.call("ln_delete", {"service": "tdapi.slsSalesOrder", "resource": "Orders",
                                                      "key": "100000001", "company": args.company})
                r.check("guard: delete not permitted on Orders", err and "not permitted" in str(out), str(out)[:150])

                err, out = await r.call("ln_query", {"service": "tcapi.ibdItem", "resource": "Items", "top": 1})
                r.check("guard: company placeholder", err and "company" in str(out).lower(), str(out)[:150])

    failed = [n for n, ok, _ in r.results if not ok]
    print(f"\n{len(r.results) - len(failed)}/{len(r.results)} checks passed" + (f"; failed: {failed}" if failed else ""))
    return 1 if failed else 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--client-id")
    ap.add_argument("--client-secret")
    ap.add_argument("--token", default=os.environ.get("MCP_BEARER_TOKEN"),
                    help="Static bearer token (default: $MCP_BEARER_TOKEN); replaces --client-id/--client-secret")
    ap.add_argument("--company", required=True)
    args = ap.parse_args()
    if not args.token and not (args.client_id and args.client_secret):
        ap.error("pass --token (or MCP_BEARER_TOKEN) or both --client-id and --client-secret")
    sys.exit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
