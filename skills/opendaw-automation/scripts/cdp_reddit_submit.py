#!/usr/bin/env python3
"""
Submit a text post to a Reddit subreddit via CloakBrowser CDP.

Prerequisites:
- CloakBrowser running with CDP on port 9222
- User logged into Reddit (token_v2 cookie present)
- VPN exit IP NOT in Reddit's blocklist (verify first!)

Usage:
    python3 cdp_reddit_submit.py --subreddit mcp --title "Your Title" --body "Your body text"

If the API submit returns 403, the IP is blocked — ask the user to switch HideMyIP VPN server.
"""
import argparse, json, time, urllib.request, websocket

CDP_URL = "http://127.0.0.1:9222"

def create_tab():
    """Create a fresh tab and return its webSocketDebuggerUrl."""
    req = urllib.request.Request(f"{CDP_URL}/json/new?about:blank", method="PUT")
    resp = urllib.request.urlopen(req, timeout=5)
    data = json.loads(resp.read())
    return data["webSocketDebuggerUrl"]

def close_tab(ws_url):
    """Close a tab by its WS URL."""
    tab_id = ws_url.split("/devtools/page/")[1]
    try:
        urllib.request.urlopen(f"{CDP_URL}/json/close/{tab_id}", timeout=3)
    except Exception:
        pass

class CDPSession:
    def __init__(self, ws_url, timeout=30):
        self.ws = websocket.create_connection(ws_url, timeout=timeout)
        self.ws.settimeout(timeout)
        self._id = 0

    def call(self, method, params=None):
        self._id += 1
        msg = {"id": self._id, "method": method}
        if params:
            msg["params"] = params
        self.ws.send(json.dumps(msg))
        while True:
            raw = self.ws.recv()
            data = json.loads(raw)
            if data.get("id") == self._id:
                return data

    def eval(self, expression, await_promise=False):
        return self.call("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": await_promise,
        })

    def close(self):
        self.ws.close()

def check_ip_blocked(cdp):
    """Check if Reddit blocks the current IP by hitting the API."""
    r = cdp.eval("""
        fetch('https://www.reddit.com/api/v1/me', {credentials: 'include'})
            .then(r => r.text())
            .then(t => t.startsWith('<body') || t.startsWith('<!doctype') ? 'BLOCKED' : t.substring(0, 200))
            .catch(e => 'ERR:' + e.message)
    """, await_promise=True)
    result = r.get("result", {}).get("result", {}).get("value", "")
    return result == "BLOCKED"

def submit_via_api(cdp, title, body, subreddit_id):
    """Submit a text post via Reddit API from browser context (has cookies)."""
    r = cdp.eval(f"""
    (async () => {{
      const csrf = document.cookie.split(';').map(c=>c.trim()).find(c=>c.startsWith('csrf_token=')).split('=')[1];
      const recaptcha = document.querySelector('textarea[name="g-recaptcha-response"]');
      const recaptchaVal = recaptcha ? recaptcha.value : '';
      const formData = new URLSearchParams();
      formData.append('title', {json.dumps(title)});
      formData.append('text', {json.dumps(body)});
      formData.append('sr', {json.dumps(subreddit_id)});
      formData.append('kind', 'self');
      formData.append('api_type', 'json');
      formData.append('g-recaptcha-response', recaptchaVal);
      const resp = await fetch('https://www.reddit.com/api/submit', {{
        method: 'POST', credentials: 'include',
        headers: {{'Content-Type': 'application/x-www-form-urlencoded', 'X-Modhash': csrf}},
        body: formData.toString()
      }});
      const text = await resp.text();
      return JSON.stringify({{status: resp.status, body: text.substring(0, 1000)}});
    }})()
    """, await_promise=True)
    return json.loads(r.get("result", {}).get("result", {}).get("value", "{}"))

def main():
    parser = argparse.ArgumentParser(description="Submit a text post to Reddit via CloakBrowser CDP")
    parser.add_argument("--subreddit", required=True, help="Subreddit name (e.g. 'mcp')")
    parser.add_argument("--title", required=True, help="Post title")
    parser.add_argument("--body", required=True, help="Post body (markdown)")
    parser.add_argument("--check-only", action="store_true", help="Only check if IP is blocked, don't submit")
    args = parser.parse_args()

    ws_url = create_tab()
    cdp = CDPSession(ws_url)

    try:
        cdp.call("Page.enable")

        # Navigate to submit page
        print(f"Navigating to r/{args.subreddit}/submit...")
        cdp.call("Page.navigate", {"url": f"https://www.reddit.com/r/{args.subreddit}/submit"})
        time.sleep(6)

        # Check if redirected to login (IP blocked or not logged in)
        r = cdp.eval("window.location.href")
        url = r.get("result", {}).get("result", {}).get("value", "")
        if "/login" in url:
            print("BLOCKED: Redirected to login page. IP is blocked or cookies expired.")
            print("Fix: Ask user to switch HideMyIP VPN server (Kyiv/Moscow/other).")
            return

        # Check IP block via API
        if check_ip_blocked(cdp):
            print("BLOCKED: Reddit API returns block page. IP is in blocklist.")
            print("Fix: Ask user to switch HideMyIP VPN server.")
            return

        if args.check_only:
            print("OK: IP is not blocked, user is logged in.")
            return

        # Get subreddit ID from hidden input
        r = cdp.eval('document.querySelector(\'input[name="subredditId"]\')?.value || "NOT_FOUND"')
        sub_id = r.get("result", {}).get("result", {}).get("value", "NOT_FOUND")
        if sub_id == "NOT_FOUND":
            print("ERROR: Could not find subredditId hidden input")
            return

        print(f"Subreddit ID: {sub_id}")
        print(f"Submitting post: {args.title}")

        result = submit_via_api(cdp, args.title, args.body, sub_id)
        print(f"Status: {result.get('status')}")
        if result.get("status") == 200:
            print("SUCCESS: Post submitted!")
        elif result.get("status") == 403:
            print("BLOCKED: 403 Forbidden — IP is in Reddit's blocklist.")
            print("Fix: Ask user to switch HideMyIP VPN server.")
        else:
            print(f"Response: {result.get('body', '')[:500]}")

    finally:
        cdp.close()
        close_tab(ws_url)

if __name__ == "__main__":
    main()
