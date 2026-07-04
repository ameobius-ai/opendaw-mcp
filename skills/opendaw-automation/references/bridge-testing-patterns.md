# MCP Bridge Testing Patterns — session 7

How to test openDAW MCP tools without false failures from bridge state loss.

## THE #1 PITFALL: bridge state does NOT persist across Python processes

`from server import bridge` creates a **new** `HeadlessDawBridge()` singleton each time
a Python process starts. The old process's browser/Vite are killed on exit.

**Symptom**: First `bridge.evaluate()` in a new process returns
`"Cannot read properties of undefined (reading 'Vaporisateur')"` or
`"Cannot read properties of undefined (reading 'tracks')"`.

**Root cause**: The new bridge calls `start()`, which launches a fresh Vite + Chromium.
The fresh page has `window.DAW` but lazy-loaded modules (`InstrumentFactories`,
`EffectFactories`, `lib-midi`, etc.) may not be ready yet.

### Fix: single-process + wait-for-ready

ALL test steps (setup + action + verify) must run in ONE `asyncio.run(test())` call
in ONE Python process. Additionally, poll for lazy-load readiness before setup:

```python
import asyncio, json
from server import bridge

async def test():
    # 1. Wait for lazy-loaded modules to be ready
    for i in range(15):
        r = await bridge.evaluate('''() => !!window.DAW_InstrumentFactories''')
        if r is True:
            break
        await asyncio.sleep(2)
    else:
        print("InstrumentFactories NOT ready — check console logs")
        return

    # 2. Setup (synth track, notes, etc.) — all in same process
    r1 = await bridge.evaluate('''() => { ... }''')
    # 3. Action (the tool being tested)
    r2 = await bridge.evaluate('''() => { ... }''')
    # 4. Verify
    r3 = await bridge.evaluate('''() => { ... }''')

asyncio.run(test())
```

### If lazy-load fails after page reload

If `DAW_InstrumentFactories` is `false` even after waiting, the page may need a reload:

```python
await bridge.evaluate('''() => { window.location.reload(); return "reloading"; }''')
await asyncio.sleep(5)  # wait for Vite HMR + module init
# then poll for readiness again
```

This happened in session 7 — after a previous test process killed the browser,
the new bridge's page loaded but `studio-adapters` lazy import didn't complete
until a manual reload.

## THE #2 PITFALL: bare `}` in JS-inside-Python-f-string

When embedding JavaScript inside a Python f-string (triple-quoted), every literal
`{` and `}` in the JS code must be escaped as `{{` and `}}`.

**Symptom**: `SyntaxError: f-string: single '}' is not allowed (line N, column M)`

**This is NOT caught at runtime — it's a Python parse error.** The server won't even
start.

**Common trap**: When adding a new MCP tool via `patch`, the `old_string`/`new_string`
boundary may land inside an f-string. If the new code has a bare `}` (e.g. a JS object
literal close), Python rejects it.

**Fix**: Audit ALL `}` in JS code inside f-strings. Every one must be `}}`.
Use `grep -n "^[^#]*}" server.py` to find suspicious lines, then verify they're
inside f-strings and properly escaped.

### Example of the bug

```python
# BROKEN — bare } inside f-string
result = await bridge.evaluate(f"""() => {{
    return {{success: true}};
}}""", timeout=15000)
#                                             ^ this } closes the f-string expression
#                                             but the } before it is bare → SyntaxError
```

```python
# CORRECT — all } doubled
result = await bridge.evaluate(f"""() => {{
    return {{success: true}};
}}""", timeout=15000)
```

## THE #3 PITFALL: "Cannot construct box while other box is constructing"

When creating boxes inside `p.editing.modify()`, nested `Box.create()` calls can
trigger: `"Error: Cannot construct box while other box is constructing"`.

**Root cause**: `AudioUnitBox.create(graph, uuid, (box) => { ... })` — the callback
runs during construction. If the callback itself creates another box, you get this
error.

**Fix**: Create boxes in sequence, NOT inside another box's init callback. Only set
field values in the callback. Create dependent boxes AFTER the parent:

```javascript
// BROKEN
p.editing.modify(() => {
    const au = AudioUnitBox.create(graph, uuid, (box) => {
        box.type.setValue(AudioUnitType.Instrument);
        const capture = CaptureAudioBox.create(graph, uuid); // ← ERROR
        box.capture.refer(capture);
    });
});

// CORRECT
p.editing.modify(() => {
    const capture = CaptureAudioBox.create(graph, uuid);
    const au = AudioUnitBox.create(graph, uuid, (box) => {
        box.type.setValue(AudioUnitType.Instrument);
        box.capture.refer(capture); // ← OK: just referencing, not creating
    });
});
```

## Creating a synth track for testing (verified pattern)

The correct way to create an instrument AU with a synth for note playback tests:

```javascript
p.editing.modify(() => {
    const captureBox = CaptureAudioBox.create(p.boxGraph, UUID.generate());
    const instrumentAU = AudioUnitBox.create(p.boxGraph, UUID.generate(), (box) => {
        box.type.setValue(AudioUnitType.Instrument);
        box.collection.refer(rootBox.audioUnits);
        box.output.refer(primaryAudioBusBox.input);
        box.capture.refer(captureBox);
        box.index.setValue(0);
        box.volume.setValue(0.767835); // 0 dB
    });
    factory.create(p.boxGraph, instrumentAU.input, "Test", IconSymbol.Piano);
    trackBox = p.api.createNoteTrack(instrumentAU);
});
```

**Key**: `factory.create(graph, au.input, name, icon)` — NOT `factory.create(graph, uuid, callback)`.
The factory API is different from Box.create.

## ProjectApi native methods (for future tools)

`ProjectApi` (accessed via `p.api`) has methods we haven't exposed yet:

| Method | Description |
|--------|-------------|
| `duplicateRegion(region, {findFreeSpace})` | Native region duplication — cleaner than manual box copy |
| `exportMIDI(collection, name)` | Exports MIDI via Files.save (browser dialog — NOT for headless) |
| `exportAudio(owner, name)` | Exports audio via Files.save (browser dialog — NOT for headless) |
| `quantiseNotes(notes, opts)` | Native quantize with positionQuantisation/durationQuantisation/offset |
| `createAutomationTrack(au, target, insertIndex)` | Automation track for parameter |
| `compactTracks(au)` | Remove empty tracks |
| `replaceMIDIInstrument(target, factory, attachment)` | Swap synth device |
| `duplicateNotes(notes)` | Duplicate note selection (shifts flush after source) |

**Note**: `exportMIDI`/`exportAudio` use `Files.save` (browser download dialog).
For headless export, use the underlying `NoteMidiExport.fromCollection(collection)`
+ `MidiFile.encoder()` directly, then transfer via base64.

## lib-midi lazy-load (added session 7)

Added to `main.ts` for MIDI export support:

```typescript
const midi = await import("@opendaw/lib-midi");
w.DAW_MidiFile = midi.MidiFile;
w.DAW_MidiTrack = midi.MidiTrack;
w.DAW_ControlEvent = midi.ControlEvent;
w.DAW_ControlType = midi.ControlType;

const std = await import("@opendaw/lib-std");
w.DAW_ArrayMultimap = std.ArrayMultimap;
```

## MIDI export approach (no browser dialog)

`NoteMidiExport.toFile` uses `Files.save` (browser dialog). For headless:

1. Get note collection via `region.events.targetVertex.unwrap().box`
2. Get notes via `collection.events.pointerHub.incoming()`
3. Convert each note to `ControlEvent` (NOTE_ON + NOTE_OFF pair)
4. `toTicks(pos) = Math.floor(pos / PPQN.Quarter * 96)` — 960→96 conversion
5. `new MidiTrack(new ArrayMultimap([[0, events]], ControlEvent.Comparator), [])`
6. `MidiFile.encoder().addTrack(track).encode().toArrayBuffer()`
7. Convert ArrayBuffer → base64 → transfer to Python → save as .mid

**Velocity conversion**: openDAW stores velocity as 0-100 (Float32Field).
MIDI expects 0-127. Formula: `Math.round(velocity * 127 / 100)`.

## THE #4 PITFALL: editing.modify() required for ALL mutations (session 7)

**Symptom**: `"Error: Modification only prohibited in transaction mode"`

**Root cause**: Any `field.setValue()`, `api.compactTracks()`, or other box graph mutation
MUST be wrapped in `p.editing.modify(() => { ... })`. Without the transaction wrapper,
the BoxGraph rejects modifications.

**Example**: `api.compactTracks(au)` looks like a read-only call but it deletes empty
tracks — it's a mutation. Must be:

```javascript
p.editing.modify(() => p.api.compactTracks(units[i]));
```

**Rule of thumb**: if the call changes any field value or box structure, wrap it.
Read-only calls (`getValue()`, `pointerHub.incoming()`, `api.createNoteTrack()` during
setup) are fine without wrapping — BUT `createNoteTrack` itself is usually called inside
a `modify()` block alongside other setup, so it's typically already wrapped.

## THE #5 PITFALL: lazy-load modules need page reload (session 7)

**Symptom**: `DAW_InstrumentFactories` is `false` even after polling for 30+ seconds
in a fresh bridge session.

**Root cause**: When new lazy-load imports are added to `main.ts` (e.g. lib-midi,
ArrayMultimap), the currently running Vite HMR may not re-execute the module init
code. The page needs a full reload to trigger the `await import(...)` calls.

**Fix**:
```python
await bridge.evaluate('''() => { window.location.reload(); return "reloading"; }''')
await asyncio.sleep(5)  # wait for Vite + module init
# then poll for readiness
for i in range(20):
    r = await bridge.evaluate('''() => ({
        daw: !!window.DAW,
        factories: !!window.DAW_InstrumentFactories,
        midi: !!window.DAW_MidiFile,
    })''')
    if all(r.values()): break
    await asyncio.sleep(2)
```

**This also happens** when a previous Python process killed the browser and the new
bridge starts a fresh Chromium — the `studio-adapters` lazy import sometimes doesn't
complete until a manual reload.

## THE #6 PITFALL: AudioUnitBox has NO name field (session 7)

**Symptom**: Want to rename an AU → `box.name.setValue("New Name")` → `TypeError: box.name.setValue is not a function`

**Root cause**: `AudioUnitBox` field 1 is `type` (StringField for "output"/"instrument"),
NOT a name. There is no `name` field at the box level. The AU display name lives on
the instrument device, accessible only via `AudioUnitBoxAdapter.label` →
`input.adapter().labelField.getValue()`.

**Workaround**: AU name is set at creation time via `factory.create(graph, au.input, name, icon)`.
To "rename", delete and recreate. For region labels, `NoteRegionBox.label` IS a StringField
and works at box level: `region.label.setValue("New Label")`.

## THE #7 PITFALL: f-string `}}` escaping in heredoc tests (session 8)

When running complex bridge tests from Python CLI, `python3 -c "..."` with f-strings containing JS requires doubling every `{` and `}`. This is error-prone and unreadable.

**Fix**: Use heredoc (`<< 'PYEOF'`) with regular triple-quoted strings:

```python
# GOOD — heredoc, no f-string escaping
python3 << 'PYEOF'
import asyncio, sys
sys.path.insert(0, '.')
from server import bridge

async def test():
    r = await bridge.evaluate("""() => {
        const p = window.DAW;
        return {success: true};
    }""", timeout=15000)
    print(r)

asyncio.run(test())
PYEOF
```

When you need Python variable interpolation inside JS, use string concatenation:
```python
auIdx = r.get('auIdx', 1)
r2 = await bridge.evaluate("""() => {
    const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({box}) => box);
    const au = units[""" + str(auIdx) + """];
    return {ok: true};
}""", timeout=15000)
```

**Never** use f-strings for large JS blocks unless the tool itself is being added to server.py (where f-string escaping is mandatory).

## Session 9 new tools verified

| Tool | Test | Result |
|------|------|--------|
| `set_audio_region_fade` | fade_in=0.5s, fade_out=1.0s, inSlope=0.75, outSlope=0.25 | ✅ |
| `set_audio_region_gain` | gain=-6dB on test region | ✅ |
| `list_value_regions` | 1 automation region: position=0, duration=8 beats, label="Auto Region" | ✅ |

## THE #8 PITFALL: InstrumentFactories not ready in new bridge (session 9)

**Symptom**: `DAW_InstrumentFactories` is `undefined` even after `window.DAW` and `DAW_EffectFactories` are ready. All `create_synth_track` / `createAnyInstrument` calls fail with `"Cannot read properties of undefined (reading 'Tape')"`.

**Root cause**: `main.ts` lazy-loads `InstrumentFactories` via `await import("@opendaw/studio-adapters")`. The bridge `start()` method only waited for `DAW` and `DAW_EffectFactories` — not `DAW_InstrumentFactories`. In a fresh Chromium, the dynamic import races and sometimes loses.

**Fix (applied to server.py bridge.start())**: Added `wait_for_function("typeof window.DAW_InstrumentFactories !== 'undefined'", timeout=15000)` after EffectFactories check. Falls back to a warning if it doesn't load.

```python
# In HeadlessDawBridge.start():
await self.page.wait_for_function(
    "typeof window.DAW_EffectFactories !== 'undefined'", timeout=10000
)
# NEW: wait for InstrumentFactories (lazy-loaded)
try:
    await self.page.wait_for_function(
        "typeof window.DAW_InstrumentFactories !== 'undefined'", timeout=15000
    )
except Exception:
    logger.warning("InstrumentFactories not loaded — create_synth_track may fail")
```

## THE #9 PITFALL: AudioRegionBox requires file + events pointers (session 9)

**Symptom**: `"Pointer {AudioRegionBox:PointerField (file) ...requires an edge."` or `"Pointer ... (events) ...requires an edge."`

**Root cause**: AudioRegionBox has two mandatory PointerFields:
- Field 2: `file` → must point to an `AudioFileBox`
- Field 5: `events` → must point to a `ValueEventCollectionBox`

Both are `mandatory: true` — the BoxGraph rejects the transaction if either edge is missing.

**Fix**: Create both boxes first, then reference them in the AudioRegionBox constructor:

```javascript
p.editing.modify(() => {
    const fileBox = AudioFileBox.create(p.boxGraph, UUID.generate(), box => {
        box.fileName.setValue("test.wav");
        box.startInSeconds.setValue(0);
        box.endInSeconds.setValue(4);
    });
    const eventCollection = ValueEventCollectionBox.create(p.boxGraph, UUID.generate());
    AudioRegionBox.create(p.boxGraph, UUID.generate(), box => {
        box.position.setValue(0);
        box.duration.setValue(4 * 960);
        box.label.setValue("TestRegion");
        box.mute.setValue(false);
        box.gain.setValue(0);
        box.fading.in.setValue(0);
        box.fading.out.setValue(0);
        box.file.refer(fileBox);           // ← mandatory pointer
        box.events.refer(eventCollection.owners);  // ← mandatory pointer
        box.regions.refer(track.regions);
    });
});
```

**Note**: `box.file.refer(fileBox)` — refer to the box directly, NOT `fileBox.file` (AudioFileBox has no `file` field).

## THE #10 PITFALL: Vite listens on IPv6 [::1], not IPv4 127.0.0.1 (session July 2026)

**Symptom**: `ss -tlnp | grep 5174` returns nothing. `lsof -i :5174` returns nothing. `curl http://127.0.0.1:5174` returns empty. Bridge `start()` fails with `net::ERR_CONNECTION_REFUSED at http://localhost:5174/` after 15s timeout.

**Root cause**: Vite 8.x binds to `[::1]:5174` (IPv6 localhost) by default. `ss` and `lsof` on WSL may not show IPv6 listeners. `curl http://127.0.0.1:5174` fails because 127.0.0.1 is IPv4. But `curl http://localhost:5174` works because `localhost` resolves to `::1` in WSL's DNS.

**Fix**: 
- Don't rely on `ss`/`lsof` to verify Vite is running — use `curl http://localhost:5174 | head -3` or `curl http://[::1]:5174 | head -3`
- If bridge `start()` fails with CONNECTION_REFUSED, wait longer (Vite may still be starting). 15-18s warmup is typical.
- If `OPENDAW_URL` env var is set to `http://127.0.0.1:5174`, it will fail. Use `http://localhost:5174` (default) or `http://[::1]:5174`.
- `netstat -tlnp` DOES show IPv6: `tcp6 0 0 ::1:5174 :::* LISTEN`

**Verification command**:
```bash
netstat -tlnp 2>/dev/null | grep 5174  # shows tcp6 ::1:5174
curl -s http://localhost:5174 | head -3  # returns HTML
```

## THE #11 PITFALL: Chromium/Vite processes leak after bridge.stop() — blocks ALL terminals

**Symptom**: After running an E2E test script (`python3 << 'PYEOF' ... PYEOF`) that calls `bridge.start()` / `bridge.stop()`, foreground terminal commands start returning `[Command interrupted] exit_code=130`. Background processes pile up. `echo hi` hangs. The entire terminal subsystem is blocked.

**Root cause**: `bridge.stop()` calls `browser.close()` and `p.stop()`, but on WSL the Chromium subprocess and Vite dev server child processes sometimes survive as orphans. These zombie processes hold file descriptors and PTY slots, causing new terminal commands to hang waiting for a free PTY.

**Detection**: `process(action='list')` shows multiple stuck sessions with `status: running` for Vite/chromium commands. Even `process(action='kill')` on stuck sessions may not free the PTY.

**Fix (prevention)**: Always run E2E tests in a **background** terminal with `notify_on_complete=true`, never foreground. This isolates the Chromium lifecycle from the foreground PTY:

```python
# GOOD — background process, isolated PTY
terminal(
    command="cd opendaw-mcp && source venv/bin/activate && python3 << 'PYEOF' ...",
    background=True,
    notify_on_complete=True,
    timeout=60
)

# BAD — foreground, blocks PTY if Chromium leaks
terminal(
    command="cd opendaw-mcp && source venv/bin/activate && python3 << 'PYEOF' ...",
    timeout=60
)
```

**Fix (recovery)**: Once terminals are stuck, the only reliable recovery is:
1. `process(action='list')` to find ALL running sessions
2. `process(action='kill')` on each one
3. If foreground still hangs, the session shell itself may need restart (user action)

**NEVER use `pkill`** — on WSL it can kill the agent's own parent process. Use targeted `kill <PID>` only.

## THE #12 PITFALL: git operations hang when Chromium is stuck

**Symptom**: After E2E bridge tests, `git commit` / `git push` / `git status` hang indefinitely — even from background processes.

**Root cause**: Git may be waiting for a lock file held by a previously killed git process, or the PTY subsystem is still blocked by orphaned Chromium processes from the bridge test.

**Fix**: Kill all orphaned processes first (via `process(action='list')` + `process(action='kill')`), then retry git. If git still hangs, the file changes are saved but uncommitted — they can be committed in the next session after a clean restart.

## THE #11.5 PITFALL: kanban complete needs --board flag

**Symptom**: `hermes kanban complete t_XXXX` returns `cannot complete t_XXXX (unknown id or terminal state)` even though the task exists.

**Root cause**: `hermes kanban complete` without `--board` looks in the default board, not `producers`. Task is on the `producers` board.

**Fix**: Always use `hermes kanban --board producers complete t_XXXX`. Also, `claim` before `complete` — tasks in `ready` state may reject `complete` without being claimed first:
```bash
hermes kanban --board producers claim t_XXXX
hermes kanban --board producers complete t_XXXX
```
