# CodeRabbit DSP Review Patterns + Upstream Issue Coverage

## Session: 2026-07-04 (v1.11.2 release)

## 10 Bug Categories from CodeRabbit (applied to PR #283)

These are recurring DSP bug patterns that CodeRabbit catches. Internalize them before writing new Werkstatt/Apparat/Spielwerk scripts.

### CRITICAL

1. **Undefined variable in output gain** (darksat)
   - Bug: `const outL = Math.pow(10, output/20)` then `io.out[1][i] = ... * outR` — `outR` is never defined.
   - Fix: Use a single `outGain` variable for both channels. Name gain vars explicitly.

2. **Delay buffer too small for modulation excursion** (chorus)
   - Bug: `maxDelay = sr * 0.05` but `depth * center * lfo` can push delay past maxDelay → negative index → NaN.
   - Fix: Buffer must be ≥ 2× the max delay time. For modulated delays, always add headroom.

3. **Negative-index modulo without wrap** (chorus, any fractional delay)
   - Bug: `readL = idxL - delayL + maxDelay` — if `delayL > maxDelay`, result is still negative.
   - Fix: `((idx - delay) % maxDelay + maxDelay) % maxDelay` — safe modulo for negative operands.

### MAJOR

4. **Parameter disabled by scaling** (coldfold)
   - Bug: `slewAmt = this.p.slew / 100` — param range is 0..1, dividing by 100 makes it 0..0.01 (effectively zero).
   - Fix: Use the param value directly. If you need finer control, adjust `@param` range, not post-scale.

5. **Lookahead not actually looking ahead** (lookahead compressor)
   - Bug: `delayed` is read from ring buffer but `io.out[i] = inL * gain` — gain applied to dry, not delayed.
   - Fix: `io.out[i] = delayed * gain` — the whole point of lookahead is gain reduction applies to the delayed copy.

6. **Buffer index never advances** (reverb combs)
   - Bug: Loop reads/writes `c.buf[c.idx]` but `c.idx` is never incremented → stuck on same slot.
   - Fix: `c.idx = (c.idx + 1) % c.len` at end of each comb iteration.

7. **Shared state across stereo channels** (shimmer pitch shifter, reverb damping)
   - Bug: Single `pitchBuf`, `pWriteIdx`, `pitchPhase` for both channels → crosstalk + doubled pitch ratio.
   - Fix: Per-channel arrays: `this.pitchBuf = [new Float32Array(N), new Float32Array(N)]`.

8. **Unstable filter topology** (phaser 2nd-order allpass)
   - Bug: Custom 2nd-order allpass recurrence can diverge, blowing up the audio buffer.
   - Fix: Use standard 1st-order allpass: `y = -a*x + z1; z1 = x + a*y` where `a = (1-tan(πf/sr))/(1+tan(πf/sr))`.

9. **Unidirectional glide** (subcrusher)
   - Bug: `logRatio = log(freq/targetFreq)` then `newLog = logRatio - glideRate` — always decreases, upward glides diverge.
   - Fix: Use `Math.sign(diff)` to steer interpolation direction: `freq = exp(logF + sign(diff) * rate)`.

### MINOR

10. **Markdown fenced code without language tag** (README MD040)
    - Fix: Always add language: ` ```text `, ` ```javascript `, etc.

11. **Swing drops notes at block boundaries** (arpeggiator)
    - Bug: `if (notePos >= to) break` discards swung notes that land past block end.
    - Fix: Remove the break — yield the note anyway. The engine schedules it in the next block.

## Validation Workflow (post-fix)

```python
# After fixing DSP scripts, validate ALL of them via bridge:
code_escaped = json.dumps(code)
script = f'() => {{ try {{ eval({code_escaped}); return {{ ok: true }}; }} catch(e) {{ return {{ ok: false, error: e.message }}; }} }}'
r = await bridge.evaluate(script)
# Expected: {ok: true} for all scripts
```

All 9 fixed scripts passed syntax validation (9/9). The fixes were committed to both openDAW fork (PR #283 branch) and opendaw-mcp scripts/.

## Upstream Issue Coverage (7 issues)

| Issue | Title | Script | PR Comment |
|-------|-------|--------|------------|
| #195 | chorus effect | `werkstatt_chorus.js` | — |
| #133 | allpass/phaser | `werkstatt_phaser.js` | — |
| #91 | DC remove | `werkstatt_darksat.js` (DC blocker) | — |
| #209 | Paulstretch Effect | `werkstatt_paulstretch.js` | ✅ commented |
| #139 | Parameter Modulation Controllers | `werkstatt_envfollower.js` | ✅ commented |
| #241 | Envelope on soundfont player | `werkstatt_adsr_trim.js` | ✅ commented |
| #201 | classic time stretch | `werkstatt_granular_stretch.js` | ✅ commented |

Also commented: #277 (Werkstatt MIDI input) — explained architecture limitation (Werkstatt has no MIDI, need #211 sidechain input or new modulation mechanism).

## Release Workflow (v1.11.2)

1. Fix scripts in `openDAW/examples/` (upstream PR #283 branch)
2. Sync fixed scripts to `opendaw-mcp/scripts/`
3. Version bump: `pyproject.toml`, `server.py`, `server.json`, `README.md` changelog
4. `python3 -m pytest tests/test_utils.py -q` → 93 passed
5. `ruff check server.py` → clean
6. `git commit && git push origin main`
7. `uv build` → dist/opendaw_mcp-X.Y.Z.{whl,tar.gz}
8. `gh release create vX.Y.Z --title "..." --notes "..." dist/*.whl dist/*.tar.gz`
9. CI auto-runs: ci.yml (tests) + publish-mcp.yml (MCP Registry via OIDC)
10. Comment on upstream issues addressed

## PR #9133 update (awesome-mcp-servers)
- Title: "Add opendaw-mcp: 258 MCP tools for agent-native openDAW control"
- Body: updated with 258 tools, 93 tests, v1.11.2, 14 DSP scripts, MCP Registry published
- `gh pr edit` fails (Projects classic deprecation) → use `gh api repos/punkpeye/awesome-mcp-servers/pulls/9133 --method PATCH -f body="$BODY"`
