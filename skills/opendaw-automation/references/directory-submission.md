# MCP Directory Submission

## awesome-mcp-servers (punkpeye)

Largest community MCP server list (~50k servers indexed via Glama). PR-based submission.

### Procedure
1. Fork: `gh repo fork punkpeye/awesome-mcp-servers --clone=false`
2. Clone your fork: `git clone --depth 1 https://github.com/AMEOBIUS/awesome-mcp-servers.git /tmp/awesome-mcp-servers`
3. Find the right category section in README.md (e.g. `### 🎨 Art & Culture` for DAW/music tools)
4. Add entry in alphabetical order within the section. Format:
   ```
   - [AMEOBIUS/opendaw-mcp](https://github.com/AMEOBIUS/opendaw-mcp) 🐍 🏠 🍎 🪟 🐧 - 194 MCP tools for agent-native control of openDAW, a browser-based DAW. Playwright bridge to headless Chromium: tracks, instruments, effects, MIDI, automation, modular synth, scriptable DSP, stem export, LUFS measurement.
   ```
5. Legend emojis: 🐍=Python, 📇=TypeScript, 🏠=Local, ☁️=Cloud, 🍎=macOS, 🪟=Windows, 🐧=Linux
6. `git checkout -b add-opendaw-mcp && git add README.md && git commit -m "Add opendaw-mcp: ..." && git push origin add-opendaw-mcp`
7. `gh pr create --repo punkpeye/awesome-mcp-servers --head AMEOBIUS:add-opendaw-mcp --base main --title "..." --body "..."`
8. Wait for review (community-maintained, may take days)

### Existing DAW MCP servers in the list (for context)
- reaper-mcp (129 tools, Python)
- flstudio-mcp (67 tools, Python)
- ableton-mind (Ableton Live, TypeScript)

### Our submission
- PR #9133: https://github.com/punkpeye/awesome-mcp-servers/pull/9133
- Submitted 2026-07-03
- Updated 2026-07-03: title synced to "243 tools", body rewritten with full feature list

### ⚠️ Updating PR title/body: GraphQL deprecation workaround

`gh pr edit` fails with: `GraphQL: Projects (classic) is being deprecated in favor of the new Projects experience`. The CLI uses GraphQL for PR edits which now errors.

**Fix**: Use REST API directly:
```bash
gh api repos/punkpeye/awesome-mcp-servers/pulls/9133 \
  --method PATCH \
  -f title="Add opendaw-mcp: 243 MCP tools for agent-native openDAW control" \
  -f body="..." \
  --jq '.title'
```
This bypasses GraphQL entirely. Confirmed working 2026-07-03.

### ⚠️ Glama badge requirement (NEW as of 2026-07-03)

The awesome-mcp-servers bot now requires ALL submissions to:
1. **Be listed on Glama.ai** — submit at https://glama.ai/mcp/servers (requires account registration via browser, no public API)
2. **Pass Glama checks** — server must start and respond to MCP introspection (tools/list). Dockerfile must be uploaded to Glama directly.
3. **Add a Glama score badge** to the PR entry, format:
   ```
   [![AMEOBIUS/opendaw-mcp MCP server](https://glama.ai/mcp/servers/AMEOBIUS/opendaw-mcp/badges/score.svg)](https://glama.ai/mcp/servers/AMEOBIUS/opendaw-mcp)
   ```

**This is a hard blocker** — without Glama listing + badge, the PR will not be merged. Glama registration is manual (browser form, SPA, no API endpoint found). Requires:
- Account on glama.ai
- Dockerfile in the repo (we have one)
- Server that responds to `tools/list` introspection (our SSE transport + lazy bridge init handles this — `tools/list` returns metadata without starting the bridge)

## Glama.ai

**NOT auto-indexing** (confirmed again 2026-07-03, 2nd check). Despite having `mcp` and `model-context-protocol` GitHub topics + MCP Registry publication for 24h+, Glama did NOT index our repo. The `/mcp/servers/submit` URL returns a search page (not a form). No public API endpoint for submission found. Glama now has 50,845 servers — they likely need manual registration through their SPA.

Glama requires manual registration through their SPA (browser-only, needs JS). The `gh pr comment` on PR #9133 confirmed: "Ensure your server is listed on Glama. If it isn't already, submit it at https://glama.ai/mcp/servers and verify that it passes all checks."

**Procedure (manual, requires browser):**
1. Register account on glama.ai
2. Submit server via their web form (needs GitHub URL + Dockerfile)
3. Wait for introspection check (server must respond to `tools/list`)
4. Once indexed, add score badge to awesome-mcp-servers PR
5. Score badge URL: `https://glama.ai/mcp/servers/AMEOBIUS/opendaw-mcp/badges/score.svg`

**Glama server page (once indexed):** `https://glama.ai/mcp/servers/AMEOBIUS/opendaw-mcp`
**Check if indexed:** `curl -s "https://glama.ai/mcp/servers?query=opendaw" | grep -i opendaw`

## Official MCP Registry (registry.modelcontextprotocol.io)

**This IS the official MCP Registry** — corrected 2026-07-03. It is NOT just docs. It hosts server metadata (server.json), provides a REST API for discovery, and is backed by Anthropic, GitHub, PulseMCP, and Microsoft. Downstream aggregators (including Glama) consume this registry.

See `references/mcp-registry-publishing.md` for the full publishing procedure (server.json, mcp-publisher CLI, GitHub Actions OIDC workflow, namespace case sensitivity pitfalls).

**✅ Published 2026-07-03** — `io.github.AMEOBIUS/opendaw-mcp` v1.0.0 live in registry. Docker image on ghcr.io. This is the primary discovery channel — Glama and other aggregators pull from this registry.

## Other directories (researched 2026-07-03)

- **mcp.run** — now "Turbo MCP", enterprise gateway. NOT a public directory for submit.
- **Smithery.ai** — "Publish on Smithery", potential directory. Requires npm package format. Not yet attempted.

## GitHub repo optimization

Before submitting to directories:
1. Update repo description: `gh repo edit AMEBIUS/opendaw-mcp --description "194 MCP tools for agent-native control of openDAW..."`
2. Add topics: `gh api repos/AMEOBIUS/opendaw-mcp/topics --method PUT --input -` with JSON `{"names":[...]}` (18 topics as of v1.9.6)
3. Ensure README has badges (CI, License, MCP Tools count, Tests, Lint, MCP Registry)
4. Ensure CI passes
5. Ensure TOOL_CATALOG.md is up to date
6. Ensure Dockerfile + entrypoint.sh + .dockerignore exist (required for Glama)
7. Ensure mcp.json + pyproject.toml exist (standard project packaging)
8. Add MCP Registry badge to README: `[![MCP Registry](https://img.shields.io/badge/MCP%20Registry-Published-blue)](https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.AMEOBIUS/opendaw-mcp)`
9. Ensure `server.json` exists in repo root (required for MCP Registry)
10. **Social preview** — custom OpenGraph banner in `assets/social-preview.png` (1280×640). Generate SVG → convert via `cairosvg.svg2png()`. GitHub repo settings → Social preview → upload (manual web UI, no API). See `references/v1.9.6-measure-lufs-refactor-social-preview-2026-07-03.md` for SVG template structure.
