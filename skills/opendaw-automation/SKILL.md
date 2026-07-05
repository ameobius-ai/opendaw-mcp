---
name: opendaw-automation
description: "openDAW automation — 435 MCP tools via Playwright. 80+ orchestration tools. Full DAW control. v1.261.0. 13 agent skills. 111 DSP scripts (92 Werkstatt + 9 Apparat + 10 Spielwerk). Stem splitter integration (7 SOTA models, GPU local). Preset save/load (.opb). 3300 unit tests. Scriptable params mapping-aware. Suno integration pipeline (download → analyze → remix → render). See references/"
tags: [opendaw, audio, daw, headless, mcp, playwright]
---

# openDAW Automation Meta-Skill

435 MCP tools (mcp_opendaw_* prefix; 384 total async defs including start/stop/evaluate). Full DAW control via Playwright headless Chromium → openDAW Vite dev server. Published at https://github.com/AMEOBIUS/opendaw-mcp (Apache-2.0, CI green). MCP Registry: io.github.AMEOBIUS/opendaw-mcp. **v1.261.0** — 13 agent skills (adaptive-mix-mastering, suno-to-opendaw, dsp-script-authoring, opendaw-automation, opendaw-track-architecture, opendaw-sound-design, opendaw-effect-routing, opendaw-genres, opendaw-composition-patterns, opendaw-dsp-chains, lyrics-pipeline). 111 DSP scripts (92 Werkstatt + 9 Apparat + 10 Spielwerk). 3300 unit tests. Suno integration pipeline: download_audio → remix_track → render_full.

## References (read these before working on opendaw-mcp)

- **`references/pitfalls-2026-07-04.md`** — CRITICAL pitfalls: Werkstatt/Apparat/Spielwerk API contracts, Maximizer at index 0, script param mapping, PyPI token location, bridge evaluate returns dict, create_audio_track has no args, Spielwerk ASI semicolon bug
- **`references/dsp-script-library.md`** — 111 DSP scripts catalog (92 Werkstatt + 9 Apparat + 10 Spielwerk) with patterns for all 3 device types. Includes CodeRabbit DSP review patterns (8 recurring bug categories), per-script implementation notes, and the correct bridge testing workflow for new scripts. **Spielwerk block.from/to vs Werkstatt block.p0/p1 pitfall documented.**
- **`references/github-api-vpn-workaround.md`** — GitHub API DNS hijack workaround: VPN returns bogus 103.27.157.38 for api.github.com. Fix with `curl --resolve` + token extraction from hosts.yml. gh CLI token command compatibility notes.
- **`references/upstream-issue-coverage.md`** — mapping of our DSP scripts to 8 open upstream issues (#195, #133, #91, #209, #139, #241, #201, #188) for PR communication. Includes "NOT covered" list for issues requiring core engine/UI work
- **`references/coderabbit-review-and-release-2026-07-04.md`** — CodeRabbit DSP review cycle (10 bug categories), gh CLI PR management, release workflow with GitHub releases as PyPI fallback
- **`references/coderabbit-dsp-review-and-issue-coverage-2026-07-04.md`** — Updated CodeRabbit patterns (11 categories with fixes), JS syntax validation workflow, 7-issue coverage map (#195 #133 #91 #209 #139 #241 #201), v1.11.2 release workflow, gh api PATCH workaround
- **`references/werkstatt-midi-limitation-and-release-pitfalls-2026-07-04.md`** — Werkstatt MIDI input architectural limitation (#277): only Apparat has NoteEventTarget, Werkstatt UserProcessor has no noteOn/noteOff. Envelope follower workaround. PyPI stale wheel pitfall (clean dist/ before uv build). GitHub release JSON escaping (use temp file, not inline python3 -c).

## Key facts

### Project layout
- MCP server: `opendaw-mcp/server.py` (~33000 lines, 385 tools)
- Headless host: `headless-daw/` (Vite on port 5174, COOP/COEP → crossOriginIsolated)
- openDAW upstream: `openDAW/` (git remote: upstream → andremichelle/openDAW)
- Tests: `tests/test_utils.py` (3050 unit), `tests/test_integration.py` (E2E, auto-skip if DAW not running)
- DSP scripts: `scripts/werkstatt_*.js`, `scripts/apparat_*.js`, `scripts/spielwerk_*.js`

### Bridge architecture
- `HeadlessDawBridge` class — Playwright → headless Chromium → openDAW
- `bridge.evaluate(script)` returns dict/list/None (NOT string). MCP tools wrap with `_wrap_eval()` → `json.dumps()`
- **Bridge is a singleton** — state lost between Python processes. All tool calls must be in one `asyncio.run()`
- `bridge.start()` auto-called on first `evaluate()`. Waits for `DAW_InstrumentFactories` global.
- DAW_URL = 5174. Python venv at `opendaw-mcp/venv/`

### Upstream
- main = upstream/main = `e17f7789` (162 commits FF, no divergence)
- **andremichelle closes AI-generated issues** (#278/#281/#282). Don't open new issues. PRs with real code are OK.
- PR #280: delay DSP lazy-init fix — **CLOSED** (andremichelle explained: our headless setup imports device processors on main thread before sampleRate is set via worklet globals; this is a bundler issue on our side, not an upstream bug. Do NOT resubmit.)
- PR #283: 111 DSP script examples in `examples/{werkstatt,apparat,spielwerk}/` — covers 11 open upstream issues (#91, #133, #138, #139, #188, #195, #201, #209, #241, #277). **All 19 CodeRabbit findings fixed** (2 quick fixes: arpeggiator `block.from`/`block.to`, chorus buffer `sr*0.1`→`sr*0.15`; 2 heavy-lift: reverb stereo L/R comb banks with decorrelated delay times + M/S width on wet tail, paulstretch separate read/write cursors + frame emission gating; 15 were stale comments on already-fixed code). 14 commits, 27 files, mergeable=true. `gh pr edit` fails with GraphQL deprecation error — use REST API with `curl --http1.1 --resolve` instead.
- `npm install` forbidden in openDAW repo — node_modules empty, turbo/tsc unavailable. Runtime test via bridge.
- **GitHub API DNS hijack under VPN**: VPN DNS (10.255.255.254) returns `103.27.157.38` for `api.github.com` — a bogus IP that refuses connections. `gh` CLI GraphQL/REST calls fail. **Fix**: `dig +short api.github.com @8.8.8.8` → real IP (e.g. `140.82.121.6`), then `curl --http1.1 --resolve api.github.com:443:140.82.121.6 -H "Authorization: token $(grep oauth_token ~/.config/gh/hosts.yml | awk '{print $2}')" ...`. **`--http1.1` is required** — HTTP/2 through VPN TLS causes `curl: (92) HTTP/2 stream 1 was not closed cleanly`. `gh auth token` may not work in all gh versions — extract from `~/.config/gh/hosts.yml`. Git push/pull works fine (git protocol), only the API is affected.
- **CodeRabbit stale reviews**: CodeRabbit may post comments on outdated file versions even after fixes were pushed in a later commit. **This session: 17 of 19 CodeRabbit comments were stale** — the code had already been fixed in prior commits. Only 2 were actionable (arpeggiator `block.from`/`block.to`, chorus buffer size). Always read the current file state before acting on a CodeRabbit finding — if the code already looks fixed, the comment is stale. Only act on findings that match current code. To verify which are actionable: fetch the comment's file path, read the current file, check if the reported pattern still exists.

### Scriptable device APIs (3 types — all confirmed)

**Werkstatt (audio effect):** `process(io, block)` where `io={src:[ch0,ch1], out:[ch0,ch1]}`, `block={s0,s1,...}`. Params via `paramChanged(label, value)`. `sampleRate` on globalThis. **MIDI input NOT available** — Werkstatt implements `AudioEffectDeviceProcessor`, NOT `NoteEventTarget`. The `UserProcessor` interface has only `process()` + `paramChanged()` — no `noteOn`/`noteOff`. The `Block` type (`{index, p0, p1, s0, s1, bpm, flags}`) carries no MIDI events. If a user needs MIDI-triggered behavior in an audio effect, use **envelope following** from input audio amplitude as a workaround (see `werkstatt_ringmod_env.js` — #277). For actual MIDI note input, only Apparat is suitable.

**Apparat (instrument):** `process(output, block)` where `output=[Float32Array, Float32Array]`. NO input — generates audio. Same `paramChanged`. **MIDI input IS available** — Apparat implements `NoteEventTarget`, `UserProcessor` has optional `noteOn?(pitch, velocity, cent, id)` and `noteOff?(id)` callbacks. This is the ONLY scriptable device type that receives MIDI note events.

**Spielwerk (MIDI effect):** `*process(block, events)` — MUST be generator, yields note events. `block={from,to,bpm,...}`, `events` is Iterable of MIDI events. Optional `reset()`. Processes MIDI events in the MIDI effect chain (before instrument).

**CRITICAL: Spielwerk `block` uses `from`/`to`, NOT `p0`/`p1`.** The Spielwerk `UserBlock` interface (`SpielwerkDeviceProcessor.ts` line 57) is `{from, to, bpm, s0, s1, flags}`. This is different from Werkstatt/Apparat's `Block` type (`{p0, p1, s0, s1, bpm, flags, index}`). Using `block.p0`/`block.p1` in a Spielwerk script silently produces `undefined` and breaks note scheduling. CodeRabbit caught this in `spielwerk_arpeggiator.js`.

**ASI pitfall:** Add `;` after last class field before `*process` to prevent `field = value * process(...)` misparse.

### Maximizer at effect index 0
Upstream auto-adds Maximizer to Output unit. Always find devices by class name, not hardcoded index:
```javascript
const fx = h.effectBoxes(au);
const werkIdx = fx.findIndex(b => b.constructor.name === 'WerkstattDeviceBox');
```

### @param mapping (v1.11.2+)
**4 types ONLY: `linear`, `exp`, `int`, `bool`.** There is NO `unipolar` type in ScriptCompiler — if you omit the type or write `unipolar`, the param gets default mapping (0–1 range) but the `@param` line format is `// @param <name> <default> <min> <max> <type> [unit]`. Default value is MANDATORY. `list_script_params` returns full metadata (min/max/type/unit) via `ScriptDeclaration.parseParams()`. `set_script_param` validates+clamps (bool snaps, int rounds, linear/exp clamps). Returns `clamped` flag.

### Orchestration tools (8)
`create_notes_batch`, `create_drum_pattern`, `create_chord_progression`, `add_mastering_chain`, `create_genre_track`, `create_song_structure`, `automation_sweep`, `apply_mix_preset`.

### Stem Splitter tools (2, v1.12.1+)
`split_stems(input_path, mode, output_dir, import_to_daw)` — runs SOTA separation locally on GPU. 7 modes: ensemble, scnet, bs6, polarformer, dereverb, drumsep, denoise. Optional auto-import into DAW (loads each stem via `load_audio`, returns sample IDs). Uses `sota_splitter.py` in `~/projects/creative-studio/stem-splitter/`. See stem-splitter-local skill for model details.
`list_split_modes()` — returns all modes with SDR scores and descriptions.

**Stem splitter path resolution**: `STEM_SPLITTER_DIR` env var (default `~/projects/creative-studio/stem-splitter`). Uses `venv/bin/python` directly (NOT `source venv/bin/activate` — activate doesn't persist between terminal calls and may pick up wrong venv).

### PyPI publishing (WORKING — token saved)
Token IS in `credentials/credentials.db` → `accounts` table, service='pypi', username='__token__', password column = full `pypi-AgE...` token. Extract: `python3 -c "import json,subprocess; out=subprocess.check_output(['python3','credentials/credman.py','export','--table','accounts']); data=json.loads(out); [print(a['password'],end='') for a in data['accounts'] if a.get('service')=='pypi' and a.get('username')=='__token__']"`. Save to temp file, then `UV_PUBLISH_TOKEN="$(cat /tmp/.pypi_token)" uv publish dist/opendaw_mcp-X.Y.Z-*.whl dist/opendaw_mcp-X.Y.Z-*.tar.gz` — **pass explicit file paths** to avoid re-uploading old versions in dist/ (PyPI rejects duplicate uploads). **The user had to provide this token THREE TIMES because previous sessions failed to persist it — when the user gives you a credential, SAVE IT IMMEDIATELY in credentials.db, do not assume it's already there or that "it'll be in the next session". The user was visibly frustrated ("я тебе уже 3й раз его скидываю"). This is a FIRST-CLASS lesson: credential persistence is step 1, not an afterthought.** Build: `uv build` → wheel+sdist in `dist/`. GitHub release: `curl --resolve api.github.com:443:140.82.121.6 -X POST -H "Authorization: token $TOKEN" ... repos/AMEOBIUS/opendaw-mcp/releases -d '{"tag_name":"vX.Y.Z",...}'`. MCP Registry auto-publishes via CI workflow `publish-mcp.yml` using GitHub OIDC (no token needed).

### Release amend workflow (when you forgot a file in the release commit)
If you committed the version bump but forgot a script/README change, use `git commit --amend --no-edit` to fold the new files into the release commit, then `git push --force-with-lease origin main`. This keeps the release commit atomic (all version+scripts+README in one commit). **Pitfall**: PyPI is already published at this point — the amend only affects the Git history, not the published package. The next `uv build` would produce the same version with the missing files, so if you need the missing files on PyPI too, you must bump the version again (e.g. v1.11.5 → v1.11.6) and re-publish. Alternatively, ensure ALL files are staged before the first commit.

### External blockers
- PR#9133 (punkpeye/awesome-mcp-servers) — awaiting merge, body updated via `gh api` PATCH
- **appcypher/awesome-mcp-servers** — PR creation BLOCKED. Both `gh pr create` (GraphQL permission error) and `gh api` REST (404) fail. Fork synced, branch pushed, README edited — but cannot create PR. Likely repo-level fork PR restriction. Do not retry without different approach.
- mcp.so #3003 — awaiting moderator
- awesome-mcp-servers #338 — awaiting moderator
- Social promotion (HN/Twitter/Reddit) — needs user action (Reddit IP blocked, 0 karma)

### gh CLI PR management (pitfalls)
`gh pr edit` fails with `GraphQL: Projects (classic) is being deprecated`. **Use REST API instead**: `gh api repos/OWNER/REPO/pulls/N --method PATCH -f title="..." -f body="..."`. For body with special chars, use `-F body=@file.md` or set via shell variable: `BODY=$(cat file.md) && gh api ... -f body="$BODY"`.

### JS syntax validation for DSP scripts
To validate Werkstatt/Apparat/Spielwerk scripts compile before committing:
```python
# bridge.evaluate() wraps script in `async () => { return await (script)(); }`
# So pass a FUNCTION EXPRESSION, not raw code:
code_escaped = json.dumps(code)
script = f'() => {{ try {{ eval({code_escaped}); return {{ ok: true }}; }} catch(e) {{ return {{ ok: false, error: e.message }}; }} }}'
r = await bridge.evaluate(script)
# r is a dict: {ok: true} or {ok: false, error: "..."}
```
`new Function(code)` does NOT work — it tries to execute the script body as an expression, and `// @werkstatt ...` + `class Processor {}` is not a valid expression. Use `eval()` inside a function wrapper.

### Example script signatures (pitfall)

When writing example scripts calling MCP tools directly (`server.mcp_opendaw_*`), check actual signatures:
- `create_drum_pattern(pattern: str, unit_index: int = -1)` — pattern FIRST
- `create_notes_batch(notes: str, unit_index: int = 0, track_index: int = 0)` — notes FIRST
- `set_track_volume(unit_index: int, volume_db: float)` — only 2 args, no track_index
- Init: `await server.bridge.start()` + call `server.mcp_opendaw_*` directly. NO `Server()` class.

