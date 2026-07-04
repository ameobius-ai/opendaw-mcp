# Werkstatt MIDI Input Limitation + Release Pitfalls

## Werkstatt Cannot Receive MIDI Notes (#277) — Architectural

### The limitation

Issue #277 asked: can Werkstatt scripts receive MIDI input (from clips, not keyboard) to trigger an ADSR envelope?

**Answer: No.** Werkstatt is an `AudioEffectDeviceProcessor`, NOT a `NoteEventTarget`. The `UserProcessor` interface in `WerkstattDeviceProcessor.ts` (line 39) only exposes:

```typescript
interface UserProcessor {
    process(io: UserIO, block: Block): void
    paramChanged?(label: string, value: number): void
}
```

No `noteOn`/`noteOff` callbacks. The `Block` type (`processing.ts` line 26) carries only `{index, p0, p1, s0, s1, bpm, flags}` — no MIDI events field.

### Apparat is the ONLY scriptable device with MIDI

`ApparatDeviceProcessor` implements `NoteEventTarget` and its `UserProcessor` has:
```typescript
interface UserProcessor {  // Apparat
    process(output, block): void
    noteOn?(pitch, velocity, cent, id): void
    noteOff?(id): void
    reset?(): void
    paramChanged?(label, value): void
}
```

Events flow: MIDI clip → `NoteEventSource` → `handleEvent(event)` → `proc.noteOn(...)` / `proc.noteOff(...)`.

### Verified by source inspection

All `implements` patterns in core-processors:
- `AudioEffectDeviceProcessor`: Compressor, Vocoder, Nop, Reverb, Crusher, Werkstatt, Gate, StereoTool, Revamp, NeuralAmp, DattorroReverb, Fold, Delay, Tidal, Maximizer, Waveshaper
- `NoteEventTarget`: Apparat, Soundfont, Vaporisateur, Nano, MIDIOutput, Playfield

**Werkstatt has `eventInput.clear()` in `reset()` but never receives note events** — `eventInput` is from `AudioProcessor` base class, cleared but not routed to user code.

### Workaround: envelope-followed modulation

For #277, wrote `werkstatt_ringmod_env.js` — ring modulator where **input audio amplitude** triggers an ADSR-style envelope that modulates the carrier frequency. Route a drum track into the Werkstatt input; transient peaks act as "note ons".

Parameters: `freq` (Hz), `modDepth` (0–1), `modRange` (octave multiplier), `attack`, `release`, `threshold`, `mix`, `output`.

This is the closest possible workaround without upstream architectural changes. A real fix would require Werkstatt to implement `NoteEventTarget` and add `noteOn`/`noteOff` to the Werkstatt `UserProcessor` interface — André's call.

### Comment posted on issue #277

Posted architectural explanation + workaround link via `curl --http1.1 --resolve api.github.com:443:140.82.121.6 -X POST ...issues/277/comments`. Comment ID: 4880844610.

## PyPI stale wheel pitfall

`uv publish` (without explicit file args) uploads ALL files in `dist/`. If `dist/` contains wheels from previous versions (e.g. v1.11.6.tar.gz when publishing v1.11.8), PyPI returns:

```
400 Bad Request: File already exists ('opendaw_mcp-1.11.6.tar.gz', with blake2_256 hash '...')
```

**Fix:** Before `uv build`, clean dist:
```bash
rm -f dist/opendaw_mcp-*.whl dist/opendaw_mcp-*.tar.gz
uv build
# Now dist/ only has the new version
uv publish  # or: uv publish dist/opendaw_mcp-X.Y.Z-py3-none-any.whl dist/opendaw_mcp-X.Y.Z.tar.gz
```

**Note:** If the error appears but the NEW version's files uploaded successfully before the old ones errored, the new version IS on PyPI. Verify with `curl -s https://pypi.org/pypi/opendaw-mcp/json | python3 -c "import sys,json; print(json.load(sys.stdin)['info']['version'])"`.

## GitHub release JSON body escaping

**Pitfall:** Building the GitHub release JSON body via inline `python3 -c "import json; print(json.dumps({...}))"` with apostrophes in the body text (e.g. "What's New") breaks shell escaping — the `'` inside the f-string conflicts with the outer `'...'` shell quoting, producing `SyntaxError: unexpected character after line continuation character`.

**Fix:** Write the JSON body to a temp file via `write_file`, then:
```bash
curl -s --http1.1 --resolve api.github.com:443:140.82.121.6 \
  -X POST -H "Authorization: token $GH_TOKEN" \
  -H "Content-Type: application/json" \
  -d @/tmp/release_body.json \
  "https://api.github.com/repos/AMEOBIUS/opendaw-mcp/releases"
```

Never inline complex JSON in shell `python3 -c` — always use a file.

## Session state (2026-07-04)

- v1.11.8 on PyPI ✅ (wheel + sdist)
- 26 DSP scripts (15 Werkstatt + 5 Apparat + 6 Spielwerk)
- PR #283 updated: title "feat: 26 Werkstatt + Apparat + Spielwerk DSP script examples", pushed to feat/werkstatt-examples
- Issue #277 commented with architectural explanation + workaround
- GitHub release v1.11.8 NOT yet created (JSON escape broke on last step — needs retry with temp file approach)
- 93 tests pass, ruff clean
