# Awesome MCP Servers — Submission Draft

## Entry

### opendaw-mcp — Headless DAW for AI Agents

**Repository:** https://github.com/AMEBIUS-team/opendaw-mcp
**Registry:** io.github.AMEBIUS/opendaw-mcp
**PyPI:** `pip install opendaw-mcp`
**License:** Apache-2.0

**Description:** 543 MCP tools for agent-native control of openDAW — a browser-based digital audio workstation. The only fully headless, zero-license music production MCP server: runs in Docker, CI, and cloud without any DAW software or desktop GUI.

**Key features:**
- 543 tools: tracks, notes, effects, mixing, rendering, analysis
- Scriptable DSP (custom JS audio effects)
- 8 genre templates (techno, drum&bass, neurofunk, phonk, etc.)
- Stem separation (7 models, GPU local)
- Suno → DAW end-to-end pipeline
- Offline render with LUFS targeting (-14 Spotify, -16 Apple)
- dawproject export (Ableton/Bitwig interchange)
- Lite agent profile (39 tools) + phase-based loading
- Tool annotations (readOnly/destructive) for agent safety
- MCP spec 2025-06-18 compliant, SDK 1.28
- Eval harness: 5 scenarios with real LUFS (ITU-R BS.1770-4) + sidechain
- Deterministic seeds (SHA-256) for reproducible renders
- OpenSSF Scorecard, SBOM, pip-audit in CI
- 6139 tests, 0 flaky

**Category:** Music / Audio / Creative Tools

**Why it belongs in awesome-mcp-servers:**
Only MCP server offering full DAW control without paid software. Competitors (ableton-mcp, Producer Pal) require Ableton Live ($99+) running on desktop. opendaw-mcp runs anywhere — Docker, CI, cloud, headless server.

---

## Submission targets

1. https://github.com/modelcontextprotocol/servers — PR to `README.md` under appropriate category
2. https://github.com/punkpeye/awesome-mcp-servers — PR or issue
3. https://glama.ai/mcp/servers — already indexed via GitHub URL
4. https://smithery.ai — already published as @macar228228/opendaw-mcp
5. https://mcp.so — submit via website

## PR template for awesome-mcp-servers

```markdown
## Add opendaw-mcp

- [x] My MCP server is publicly available on GitHub
- [x] Has a clear README with installation instructions
- [x] Has an open-source license (Apache-2.0)
- [x] Is actively maintained

**Name:** opendaw-mcp
**Description:** 543 MCP tools for headless music production — zero-license DAW control for AI agents
**Repository:** https://github.com/AMEBIUS-team/opendaw-mcp
**Category:** Music / Audio Production
```
