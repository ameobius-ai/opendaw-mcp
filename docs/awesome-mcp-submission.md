# Awesome MCP Servers — Submission Draft

> Updated 2026-07-20. Live PR: https://github.com/punkpeye/awesome-mcp-servers/pull/9690

## Entry

### opendaw-mcp — Headless DAW for AI Agents

**Repository:** https://github.com/aaameobius-crypto/opendaw-mcp  
**Also:** https://github.com/AMEOBIUS/opendaw-mcp (mirror / badge target)  
**Registry:** io.github.AMEOBIUS/opendaw-mcp (published; version lag possible)  
**Smithery:** https://smithery.ai/server/@macar228228/opendaw-mcp (published)  
**PyPI:** `pip install opendaw-mcp`  
**License:** Apache-2.0

**Description:** 532+ MCP tools for agent-native control of openDAW — a browser-based digital audio workstation. The only fully headless, zero-license music production MCP server: runs in Docker, CI, and cloud without any DAW software or desktop GUI.

**Key features:**
- 532+ tools: tracks, notes, effects, mixing, rendering, analysis
- Lineage / process history / smart export / prompt inference (agent memory)
- Scriptable DSP (custom JS audio effects, Werkstatt)
- 37+ genre arrangements (house, techno, DnB, neurofunk, phonk, coldwave, …)
- Stem separation (7 SOTA models local GPU: BS-Roformer, HTDemucs FT, SCNet, PolarFormer, …)
- Suno → stems → openDAW end-to-end pipeline
- Offline render with LUFS targeting (-14 Spotify, -16 Apple) — **no limiter required** if peaks disciplined
- Spectral targets / mix recipes (sub+bass / presence / air) not graphic-EQ toys
- dawproject export (Ableton/Bitwig interchange)
- Lite agent profile + phase-based loading
- Tool annotations (readOnly/destructive) for agent safety
- Headless E2E smoke CI (Playwright + minimal test host)
- Eval harness + bridge latency bench
- OpenSSF Scorecard, SBOM, pip-audit in CI

**Category:** Music / Audio / Creative Tools

**Why it belongs in awesome-mcp-servers:**
Only MCP server offering full DAW control without paid software. Competitors (ableton-mcp, Producer Pal) require Ableton Live ($99+) running on desktop. opendaw-mcp runs anywhere — Docker, CI, cloud, headless server.

---

## Submission status (2026-07-20)

| Target | Status |
|---|---|
| punkpeye/awesome-mcp-servers | **PR open** #9690 |
| Smithery | **published** `@macar228228/opendaw-mcp` |
| MCP Registry | **published** (refresh version when release cut) |
| glama.ai | indexed via GitHub |
| mcp.so | optional website submit |

## PR template for awesome-mcp-servers

```markdown
## Add opendaw-mcp

- [x] My MCP server is publicly available on GitHub
- [x] Has a clear README with installation instructions
- [x] Has an open-source license (Apache-2.0)
- [x] Is actively maintained

**Name:** opendaw-mcp
**Description:** 532+ MCP tools for headless music production — zero-license DAW control for AI agents
**Repository:** https://github.com/aaameobius-crypto/opendaw-mcp
**Category:** Music / Audio Production
```
