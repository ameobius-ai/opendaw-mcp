# Publishing Identity Mapping

This document is the **single source of truth** for opendaw-mcp publishing identities.
The project uses a **hybrid identity scheme** — different namespaces for different registries,
each confirmed by the platform's own OIDC/ownership verification.

## Why hybrid?

GitHub repository owner (`AMEBIUS-team`) and external publishing identities are **different entities**.
Migrating all namespaces to `AMEBIUS-team` requires separate package ownership transfers on each platform.
Until each transfer is individually confirmed, the hybrid scheme is the **only correct mapping**.

## Identity mapping

| Platform | Namespace | Status | Verification |
|---|---|---|---|
| GitHub | `AMEBIUS-team/opendaw-mcp` | ✅ Active | Repo owner |
| MCP Registry | `io.github.AMEBIUS/opendaw-mcp` | ✅ Published | OIDC permissions (case-sensitive) |
| GHCR (Docker) | `ghcr.io/ameobius/opendaw-mcp` | ✅ Published | Package ownership |
| PyPI | `opendaw-mcp` | ✅ Published | Package name |
| Smithery | `@macar228228/opendaw-mcp` | ✅ Published | Smithery account |
| Glama | `AMEBIUS-team` | ✅ Indexed | GitHub URL indexing |
| GitHub Sponsors | `aaameobius-crypto` | ✅ Active | Sponsors profile |
| GitHub Pages | `ameobius.github.io` | ✅ Active | Pages deployment |

## Rules

1. **Do NOT** replace all namespaces with `git remote get-url origin` value.
2. **Do NOT** change MCP Registry namespace without OIDC re-verification.
3. **Do NOT** change GHCR ownership without Docker package transfer.
4. **Do NOT** change Smithery namespace without account migration.
5. GitHub repository links **may** use `AMEBIUS-team/opendaw-mcp`.
6. Registry search URL, Dockerfile label, and `server.json` name **must** use `io.github.AMEBIUS/opendaw-mcp`.

## Migration path (future)

If full migration to `AMEBIUS-team` is desired:
1. MCP Registry: re-publish with new namespace + OIDC verification
2. GHCR: request Docker package ownership transfer
3. Smithery: re-publish under new account
4. PyPI: no change needed (name is `opendaw-mcp`, not user-scoped)
5. Update this document after each step
