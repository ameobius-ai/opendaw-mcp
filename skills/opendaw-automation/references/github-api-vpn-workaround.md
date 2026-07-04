# GitHub API VPN DNS Hijack Workaround

## Problem

Under HideMyIP VPN (TUN mode, routes ALL traffic), the VPN's DNS server at `10.255.255.254` returns a bogus IP `103.27.157.38` for `api.github.com`. This IP refuses connections on port 443.

**Symptom**: `gh` CLI GraphQL and REST calls fail with:
```
Post "https://api.github.com/graphql": dial tcp 103.27.157.38:443: connect: connection refused
Get "https://api.github.com/repos/...": dial tcp 103.27.157.38:443: connect: connection refused
```

**Git protocol (push/pull/fetch) works fine** — only the API endpoint is affected.

## Diagnosis

```bash
nslookup api.github.com    # → 103.27.157.38 (WRONG, VPN DNS)
dig +short api.github.com @8.8.8.8   # → 140.82.121.6 (CORRECT, Google DNS)
```

## Fix

### 1. Get the real GitHub API IP
```bash
GH_IP=$(dig +short api.github.com @8.8.8.8)
```

### 2. Extract gh auth token (compatibility note)

`gh auth token` may not work in all gh CLI versions ("unknown command token for gh auth"). Fallback:

```bash
TOKEN=$(grep oauth_token ~/.config/gh/hosts.yml | awk '{print $2}')
```

Token location: `~/.config/gh/hosts.yml` under `github.com:` → `oauth_token:`.

### 3. curl with --resolve

```bash
curl -s --connect-timeout 15 \
  --resolve api.github.com:443:$GH_IP \
  -H "Authorization: token $TOKEN" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/OWNER/REPO/issues/N/comments"
```

### POST/PATCH examples

```bash
# Comment on an issue
curl -s --resolve api.github.com:443:$GH_IP \
  -H "Authorization: token $TOKEN" \
  -H "Accept: application/vnd.github+json" \
  -X POST "https://api.github.com/repos/OWNER/REPO/issues/N/comments" \
  -d '{"body":"comment text"}'

# Update PR title/body
curl -s --resolve api.github.com:443:$GH_IP \
  -H "Authorization: token $TOKEN" \
  -H "Accept: application/vnd.github+json" \
  -X PATCH "https://api.github.com/repos/OWNER/REPO/pulls/N" \
  -d '{"title":"new title","body":"new body"}'
```

### Parse JSON response
```bash
... | python3 -c "import json,sys; data=json.load(sys.stdin); [print(item) for item in data]"
```

## HTTP/2 stream closure pitfall

Even with `--resolve`, curl may fail with `HTTP/2 stream 1 was not closed cleanly before end of the underlying stream` (exit code 92). This happens when the VPN's TLS interception conflicts with HTTP/2 multiplexing.

**Fix**: Add `--http1.1` to force HTTP/1.1:

```bash
curl -s --http1.1 --resolve api.github.com:443:$GH_IP \
  -H "Authorization: token $TOKEN" \
  "https://api.github.com/repos/OWNER/REPO/issues/N"
```

This is a persistent issue under HideMyIP VPN TUN mode — always include `--http1.1` for GitHub API calls through the VPN.

## Scope

- Affects: GitHub REST API, GitHub GraphQL API (anything hitting api.github.com)
- Does NOT affect: git push/pull/fetch (uses github.com, not api.github.com, and git has its own DNS resolution)
- SOCKS5 proxy (127.0.0.1:11080) also routes through the same VPN — not a workaround

## Notes

- GitHub IPs change periodically — always resolve fresh with `dig @8.8.8.8`
- The `--resolve` flag tells curl to use the specified IP for that host:port, bypassing system DNS
- Multiple GitHub API IPs may work (140.82.121.x range typically)
