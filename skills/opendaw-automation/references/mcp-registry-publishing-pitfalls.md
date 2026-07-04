# MCP Registry Publishing — Full Pitfall Chain (4 Attempts)

Official registry: registry.modelcontextprotocol.io
Backed by: Anthropic, GitHub, Microsoft, PulseMCP

## Prerequisites

- `server.json` in repo root — metadata only (name, description, repository, packages)
- `mcp-publisher` CLI: `curl -L "https://github.com/modelcontextprotocol/registry/releases/latest/download/mcp-publisher_$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/').tar.gz" | tar xz mcp-publisher`
- Docker image on ghcr.io (or npm/PyPI package)
- GitHub Actions workflow with `id-token: write` permission for OIDC

## The 4-attempt pitfall chain

### Attempt 1: Docker build fail — git not in runtime stage
**Error**: `exit code: 127` on `RUN git clone` in runtime stage
**Cause**: `node:23-slim` runtime stage doesn't have git. Only the builder stage installed it.
**Fix**: Replace `RUN git clone --depth 1 https://github.com/...` with `COPY . /app/opendaw-mcp` — use the Docker build context instead of cloning.

### Attempt 2: Namespace case mismatch
**Error**: `403 Forbidden: You do not have permission to publish this server. You have permission to publish: io.github.AMEOBIUS/*. Attempting to publish: io.github.ameobius/opendaw-mcp`
**Cause**: GitHub username is `AMEOBIUS` (uppercase). server.json had `io.github.ameobius` (lowercase). MCP Registry requires EXACT case match.
**Fix**: `io.github.AMEOBIUS/opendaw-mcp` everywhere — server.json `name`, Dockerfile `LABEL`, README `mcp-name` comment.

### Attempt 3: OCI package version field
**Error**: `400 Bad Request: OCI packages must not have 'version' field - include version in 'identifier' instead`
**Cause**: `server.json` package object had `"version": "1.0.0"` alongside `"identifier": "ghcr.io/...:1.0.0"`. OCI packages encode version in the image tag, not a separate field.
**Fix**: Remove `"version"` from the package object. Keep version only in: (a) top-level `data['version']`, (b) `identifier` tag `ghcr.io/user/image:VERSION`.

### Attempt 4: SUCCESS ✅
All three fixes applied. Docker build → ghcr.io push → server.json validate → OIDC login → publish.

## server.json template (OCI/Docker)

```json
{
  "$schema": "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json",
  "name": "io.github.AMEOBIUS/opendaw-mcp",
  "title": "openDAW MCP",
  "description": "197 MCP tools for agent-native control of openDAW, a browser-based DAW",
  "version": "1.1.0",
  "repository": {
    "url": "https://github.com/AMEOBIUS/opendaw-mcp",
    "source": "github"
  },
  "packages": [
    {
      "registryType": "oci",
      "identifier": "ghcr.io/ameobius/opendaw-mcp:1.1.0",
      "transport": { "type": "stdio" },
      "environmentVariables": [
        {
          "description": "Path to the headless openDAW host directory",
          "isRequired": true,
          "format": "string",
          "isSecret": false,
          "name": "OPENDAW_HOST_DIR"
        }
      ]
    }
  ]
}
```

**Key constraints:**
- `description` max 100 chars
- `name` MUST match GitHub username case exactly
- OCI packages: NO `version` field in package object
- Docker image tag in `identifier` carries the version

## GitHub Actions workflow (publish-mcp.yml)

On `v*` tag push:
1. Docker build → push to ghcr.io
2. Update server.json version + identifier tag
3. Install mcp-publisher CLI
4. Validate server.json
5. `mcp-publisher login github-oidc` (uses OIDC, no PAT needed)
6. `mcp-publisher publish`

Permissions needed: `id-token: write`, `contents: read`, `packages: write`.

## Dockerfile LABEL (OCI verification)

```dockerfile
LABEL io.modelcontextprotocol.server.name="io.github.AMEOBIUS/opendaw-mcp"
```

## README marker (PyPI verification — for future PyPI publish)

```html
<!-- mcp-name: io.github.AMEOBIUS/opendaw-mcp -->
```

## Verification

```bash
curl "https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.AMEOBIUS/opendaw-mcp"
```

Returns JSON with server metadata, packages, environment variables.

**Note**: The registry search API caches results — after publishing v1.1.0, the search endpoint may still show v1.0.0 for some time. The publish itself succeeds immediately; the cache lag is display-only.

## Re-tagging for new versions

```bash
git tag -d v1.0.0
git push origin :refs/tags/v1.0.0
git tag v1.1.0
git push origin v1.1.0
```

This triggers the publish workflow again. The workflow updates server.json version + identifier tag automatically before publishing.

**v1.1.0 re-tag verified 2026-07-03**: Docker build 4m18s, publish success. Registry API search may cache old version for a while — the publish itself succeeds immediately.

## GitHub Release

After successful publish, create a GitHub Release for visibility:

```bash
gh release create v1.1.0 --title "v1.1.0 — Debugging Tools + MCP Registry" --notes "..."
```

This gives a changelog page on GitHub, shows up in the repo sidebar, and helps discovery.
