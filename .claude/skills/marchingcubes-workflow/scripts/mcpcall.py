"""Minimal MCP streamable-HTTP client for the MCP-for-Unity server.

usage: python mcpcall.py <port> <tool> [json-args] [--code-file path] [--key-file key=path ...]
       python mcpcall.py <port> resource <uri>

Set UNITY_INSTANCE=Name@hash to pin every call to one Editor when several are
attached to the same server (pass-through as the tool argument unity_instance).
See references/unity-mcp.md.
"""
import json, os, sys, urllib.request

def post(port, sid, payload, timeout=600):
    body = json.dumps(payload).encode()
    hdr = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    if sid: hdr["Mcp-Session-Id"] = sid
    req = urllib.request.Request(f"http://127.0.0.1:{port}/mcp", data=body, method="POST", headers=hdr)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        sid2 = r.headers.get("Mcp-Session-Id"); txt = r.read().decode("utf-8", "replace")
    msgs = []
    for line in txt.splitlines():
        if line.startswith("data:"):
            try: msgs.append(json.loads(line[5:].strip()))
            except Exception: pass
    if not msgs:
        try: msgs = [json.loads(txt)]
        except Exception: pass
    return sid2, msgs

def session(port):
    sid, _ = post(port, None, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                               "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                                          "clientInfo": {"name": "claude-probe", "version": "0"}}})
    try: post(port, sid, {"jsonrpc": "2.0", "method": "notifications/initialized"})
    except Exception: pass
    return sid

def main():
    port = int(sys.argv[1]); what = sys.argv[2]
    sid = session(port)
    inst = os.environ.get("UNITY_INSTANCE")
    if inst:
        _, m9 = post(port, sid, {"jsonrpc": "2.0", "id": 9, "method": "tools/call",
                         "params": {"name": "set_active_instance", "arguments": {"instance": inst}}})
        r9 = next((m for m in m9 if m.get("id") == 9), None)
        print("[set_active_instance]", json.dumps(r9)[:300] if r9 else m9, file=sys.stderr)
    if what == "resource":
        _, msgs = post(port, sid, {"jsonrpc": "2.0", "id": 2, "method": "resources/read", "params": {"uri": sys.argv[3]}})
        res = next((m for m in msgs if m.get("id") == 2), None)
        print(json.dumps(res.get("result", res), indent=1)[:20000] if res else msgs)
        return
    args = {}
    rest = sys.argv[3:]
    if rest and not rest[0].startswith("--"):
        args = json.loads(rest[0]); rest = rest[1:]
    i = 0
    while i < len(rest):
        if rest[i] == "--code-file":
            args["code"] = open(rest[i + 1], encoding="utf-8").read(); i += 2
        elif rest[i] == "--key-file":
            k, p = rest[i + 1].split("=", 1); args[k] = open(p, encoding="utf-8").read(); i += 2
        else:
            i += 1
    if inst and "unity_instance" not in args: args["unity_instance"] = inst
    _, msgs = post(port, sid, {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": what, "arguments": args}})
    res = next((m for m in msgs if m.get("id") == 2), None)
    if res is None:
        print(json.dumps(msgs)[:5000]); return
    if "error" in res:
        print("ERROR", json.dumps(res["error"])[:5000]); return
    for c in res["result"].get("content", []):
        if c.get("type") == "text":
            t = c["text"]
            try:
                j = json.loads(t)
                if isinstance(j, dict) and "data" in j and isinstance(j["data"], dict) and "result" in j["data"]:
                    print(j["data"]["result"]); continue
                print(json.dumps(j, indent=1)[:20000]); continue
            except Exception:
                pass
            print(t[:20000])
        else:
            print(c)

if __name__ == "__main__":
    main()
