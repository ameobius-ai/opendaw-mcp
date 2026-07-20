# E2E Pivot Plan: Minimal Test Host

## Problem
openDAW dashboard SPA doesn't respond to programmatic interaction in headless Chromium.
`window.opendaw` exists but `window.opendaw.service` stays null — React UI requires real
user interaction to transition from dashboard to studio. This is not fixable from bridge.py.

## Pivot: Separate CI bootstrap from production bridge

### Current state
- `opendaw_mcp/bridge.py` — production bridge, starts Playwright → openDAW dashboard.
  Works when a user manually creates a project. Fails in CI headless.
- 13 commits on `claude/headless-e2e-smoke`, all CI fixes for infra (Rust, SSL, paths).
- PR #3 open, not merged.

### Plan

#### 1. Revert bridge.py to production state
bridge.py must NOT contain CI-specific hacks (Clean Slate clicking, dashboard detection,
direct hash routes). Revert to `wait_for_function("window.opendaw.service")`.

#### 2. Create `tests/e2e/test_host/` — minimal HTML test host
A single-page app that:
- imports `@opendaw/studio-core` (Engine, Project, AudioOfflineRenderer)
- creates a `Project` programmatically via `DawProjectService`
- exposes `window.opendaw = { service, InstrumentFactories, ... }` on load
- NO React, NO dashboard, NO user interaction required

This is the same pattern as `e2e_modular_smoke.py` but with a minimal host
instead of the full studio app.

#### 3. Update workflow to build test host
```yaml
- name: Build test host
  run: |
    cd tests/e2e/test_host
    npm install
    npm run build  # vite build → dist/
```
Then Vite serves `tests/e2e/test_host/dist/` on :5174.

#### 4. Smoke test uses test host URL
`OPENDAW_URL=https://localhost:5174` points to test host, not full openDAW studio.
bridge.py connects, `window.opendaw.service` is immediately available.

### Key files to create
- `tests/e2e/test_host/index.html` — minimal HTML shell
- `tests/e2e/test_host/main.ts` — import studio-core, create project, expose API
- `tests/e2e/test_host/package.json` — depends on `@opendaw/studio-core`
- `tests/e2e/test_host/vite.config.ts` — Vite config with SSL

### What reverts
- bridge.py → revert to `wait_for_function("window.opendaw.service")`
- Remove: Clean Slate click, dashboard detection, hash route fallback
- Keep: all other review fixes (server.bridge assignment, math.isfinite, Vite logs, etc.)

### What stays
- `.github/workflows/headless-e2e.yml` — same structure, different build target
- `tests/e2e/test_bridge_smoke.py` — same test logic
- PR #3 — same branch, additional commits

### Risks
- `@opendaw/studio-core` may require browser APIs (AudioContext, SharedArrayBuffer)
  that need crossOriginIsolated — test host must serve with COOP/COEP headers
- Project creation API may be complex — need to study DawProjectService
- OfflineEngineRenderer may be better suited than full Engine for headless

### Alternative: @opendaw/studio-sdk
Currently empty (only version export). If it eventually provides a programmatic
API for project creation + rendering, test host becomes trivial. File an issue
upstream requesting this.
