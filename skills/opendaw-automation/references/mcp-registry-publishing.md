# Official MCP Registry Publishing

The **MCP Registry** (registry.modelcontextprotocol.io) is the official centralized metadata repository for MCP servers, backed by Anthropic, GitHub, PulseMCP, and Microsoft. Currently in preview.

**Registry URL:** https://registry.modelcontextprotocol.io
**Docs:** https://modelcontextprotocol.io/registry
**GitHub:** https://github.com/modelcontextprotocol/registry

## How it works

The registry hosts **metadata only** (not code/binaries). It points to packages on npm, PyPI, Docker Hub, GHCR, etc. Downstream aggregators (Glama, Smithery, etc.) consume the registry API to discover servers.

## server.json format

Create `server.json` in the repo root:

```json
{
  "$schema": "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json",
  "name": "io.github.USERNAME/server-name",
  "title": "Human Title",
  "description": "Max 100 chars description",
  "version": "1.0.0",
  "repository": {
    "url": "https://github.com/USERNAME/server-name",
    "source": "github"
  },
  "packages": [
    {
      "registryType": "oci",
      "identifier": "ghcr.io/username/server-name:1.0.0",
      "transport": { "type": "stdio" },
      "environmentVariables": [
        {
          "description": "...",
          "isRequired": true,
          "format": "string",
          "isSecret": false,
          "name": "ENV_VAR_NAME"
        }
      ]
    }
  ]
}
```

### Namespace rules (CRITICAL)

- Name format: reverse DNS — `io.github.USERNAME/server-name`
- **USERNAME must EXACTLY match GitHub username case** — `io.github.AMEOBIUS/*` not `io.github.ameobius/*`
- Case mismatch → 403 Forbidden: "You do not have permission to publish this server"
- With GitHub auth, name MUST start with `io.github.your-username/`

### Package types

| Type | registryType | Verification method |
|------|-------------|---------------------|
| npm | `"npm"` | `mcpName` property in package.json matching server name |
| PyPI | `"pypi"` | `mcp-name: $SERVER_NAME` string in README (can be in HTML comment) |
| Docker/OCI | `"oci"` | `LABEL io.modelcontextprotocol.server.name="..."` in Dockerfile |
| NuGet | `"nuget"` | `mcp-name: $SERVER_NAME` string in README |
| MCPB | `"mcpb"` | `.mcpb` file on GitHub/GitLab releases + `fileSha256` |

### OCI-specific rules

- **NO `version` field in the package object** — version goes in the identifier tag only (`ghcr.io/user/image:1.0.0`). Including `version` → 400 Bad Request: "OCI packages must not have 'version' field"
- `identifier` format: `registry/namespace/repository:tag` (e.g., `ghcr.io/ameobius/server:1.0.0`)
- GHCR image names must be **lowercase** even if GitHub username is uppercase

### Description limit

**Max 100 characters** — longer descriptions get 422 Unprocessable Entity.

## mcp-publisher CLI

Download:
```bash
curl -L "https://github.com/modelcontextprotocol/registry/releases/latest/download/mcp-publisher_$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/').tar.gz" | tar xz mcp-publisher
```

Commands:
- `mcp-publisher init` — generate server.json template
- `mcp-publisher validate` — validate against registry (no publish)
- `mcp-publisher login github` — interactive device code flow (needs browser)
- `mcp-publisher login github-oidc` — GitHub Actions OIDC (no browser, needs `id-token: write`)
- `mcp-publisher publish` — publish to registry
- `mcp-publisher status` — update server version status

**Note**: `mcp-publisher login github` does NOT read `GITHUB_TOKEN` from env. It uses device code flow requiring manual browser auth. Use `github-oidc` in GitHub Actions instead.

## GitHub Actions publish workflow

Trigger on version tags (`v*`). Key steps:

```yaml
name: Publish to MCP Registry
on:
  push:
    tags: ["v*"]
jobs:
  publish:
    runs-on: ubuntu-latest
    permissions:
      id-token: write    # Required for OIDC
      contents: read
      packages: write    # Required for ghcr.io push
    steps:
      - uses: actions/checkout@v4
      # Build + push Docker image to ghcr.io
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ghcr.io/username/server-name:${{ steps.version.outputs.VERSION }}
      # Update version in server.json dynamically
      - name: Update version in server.json
        run: |
          VERSION=${{ steps.version.outputs.VERSION }}
          python3 -c "
          import json
          with open('server.json') as f:
              data = json.load(f)
          data['version'] = '$VERSION'
          data['packages'][0]['identifier'] = f'ghcr.io/username/server-name:$VERSION'
          with open('server.json', 'w') as f:
              json.dump(data, f, indent=2)
          "
      # Install mcp-publisher + publish
      - run: curl -L ... | tar xz mcp-publisher
      - run: ./mcp-publisher validate
      - run: ./mcp-publisher login github-oidc
      - run: ./mcp-publisher publish
```

**Important**: For OCI packages, the workflow must NOT set `data['packages'][0]['version']` — only `data['version']` (top-level) and `data['packages'][0]['identifier']` (with tag).

## Pitfalls (learned 2026-07-03, 4 attempts)

1. **Namespace case sensitivity** — `io.github.ameobius` → 403. Must be `io.github.AMEOBIUS` (exact GitHub username). #1 most common publish failure.
2. **Description >100 chars** — 422 Unprocessable Entity. Keep it terse.
3. **Dockerfile `git clone` in runtime stage** — git not installed in runtime stage → exit code 127. Use `COPY . /app` from build context instead.
4. **OCI `version` field** — including `"version": "1.0.0"` in an OCI package object → 400 Bad Request. Version goes in the identifier tag ONLY (`ghcr.io/user/image:1.0.0`). The workflow must not set `data['packages'][0]['version']`.
5. **`mcp-publisher login github` needs browser** — device code flow. Use `github-oidc` in Actions, or manual browser auth locally.
6. **`mcp-publisher login none`** — returns 404 (anonymous auth not available in production).
7. **GHCR image names must be lowercase** — `ghcr.io/ameobius/server-name` (lowercase), even if GitHub username is uppercase.
8. **Retagging after fixes** — delete remote tag (`git push origin :refs/tags/v1.0.0`), recreate local (`git tag -d v1.0.0 && git tag v1.0.0`), push (`git push origin v1.0.0`).
9. **Docker build takes ~4 min** — openDAW built from source in Actions. Cache from previous runs speeds up subsequent builds.
10. **awesome-mcp-servers requires Glama badge** — PR bot asks for Glama.ai score badge. Glama requires manual browser registration (no public API). Official MCP Registry publication may eventually bypass this requirement.

## Verification after publish

```bash
curl "https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.USERNAME/server-name"
```

Should return the server metadata in JSON.

## Our publish status

**✅ PUBLISHED 2026-07-03** — `io.github.AMEOBIUS/opendaw-mcp` v1.0.0

- Docker image: `ghcr.io/ameobius/opendaw-mcp:1.0.0`
- Registry API: `https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.AMEOBIUS/opendaw-mcp`
- 4 attempts: git clone fix → namespace case fix → OCI version field fix → ✅ success
- awesome-mcp-servers PR #9133: submitted, blocked on Glama badge requirement
