#!/usr/bin/env python3
"""
Navigate to a URL via CloakBrowser CDP and extract page text.
Usage: python3 cdp_navigate.py <url> [wait_seconds]

Returns: page title, final URL, body innerText (first 5000 chars).

Prerequisites:
- CloakBrowser running with CDP on port 9222
- websocket-client installed (pip install websocket-client)
"""
import json, sys, time, websocket

CDP_URL = "http://127.0.0.1:9222"

def cdp_send(ws, method, params=None, id_=1):
    msg = {"id": id_, "method": method}
    if params:
        msg["params"] = params
    ws.send(json.dumps(msg))
    while True:
        raw = ws.recv()
        data = json.loads(raw)
        if data.get("id") == id_:
            return data

def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://api.ipify.org"
    wait = int(sys.argv[2]) if len(sys.argv) > 2 else 8

    # Create fresh tab
    import urllib.request
    req = urllib.request.Request(f"{CDP_URL}/json/new?about:blank", method='PUT')
    resp = urllib.request.urlopen(req, timeout=5)
    tab = json.loads(resp.read())
    ws_url = tab["webSocketDebuggerUrl"]

    ws = websocket.create_connection(ws_url, timeout=30)
    ws.settimeout(20)

    cdp_send(ws, "Page.enable", id_=1)
    cdp_send(ws, "Page.navigate", {"url": url}, id_=2)
    time.sleep(wait)

    r = cdp_send(ws, "Runtime.evaluate", {
        "expression": f"JSON.stringify({{url: window.location.href, title: document.title, body: document.body ? document.body.innerText.substring(0, 5000) : 'NO BODY'}})",
        "returnByValue": True
    }, id_=10)
    val = r.get("result", {}).get("result", {}).get("value", "NO VALUE")
    print(val)

    ws.close()

if __name__ == "__main__":
    main()
