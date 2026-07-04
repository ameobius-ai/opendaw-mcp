# Send/Return Routing — openDAW headless

How to create parallel FX send buses (reverb, delay) via MCP. Verified July 2 session 4.

## Architecture

A send/return bus in openDAW is THREE boxes working together:

```
src AU (synth/instrument)
  ├── output → primaryBus.input (dry signal, untouched)
  └── auxSends → AuxSendBox
                    ├── targetBus → fxBus.input (wet copy of src signal)
                    └── sendGain = -6dB (send level)

fxBus (AudioBusBox)
  └── output → fxUnit.input (routes bus audio INTO the FX unit)

fxUnit (AudioUnitBox, type=Aux)
  ├── audioEffects: [Reverb, Delay, ...] (effect chain lives here)
  └── output → primaryBus.input (wet signal joins dry at main output)
```

The dry signal from src AU goes straight to primary bus. The AuxSendBox creates
a parallel copy at the specified send level, routed through the FX bus → FX unit
(where effects process it) → back to primary bus. Both dry and wet arrive at the
output.

## WRONG topology (first attempt — breaks main signal)

```javascript
// DO NOT DO THIS — redirects dst AU output, killing its main path
dstAU.output.refer(fxBus.input);  // ← BREAKS dst AU's route to primary bus
sendBox.targetBus.refer(fxBus.input);
```

This caused mix=0 (total silence) because the dst AU was disconnected from the
primary bus. The send is supposed to be a PARALLEL copy, not a redirect.

## CORRECT topology (verified working)

```javascript
p.editing.modify(() => {
    // 1. Create FX AudioUnitBox (Aux type) — owns the effect chain
    //    Output goes to primary bus (where dry + wet mix)
    const existingCount = [...p.rootBox.audioUnits.pointerHub.incoming()].length;
    fxUnit = AudioUnitBox.create(boxGraph, UUID.generate(), (box) => {
        box.collection.refer(p.rootBox.audioUnits);
        box.output.refer(primaryBus.input);  // ← FX unit → primary bus
        box.index.setValue(existingCount);
        box.type.setValue(auxType);  // AudioUnitType.Aux = 3
    });

    // 2. Create FX bus (AudioBusBox) — routes audio INTO fxUnit
    fxBus = AudioBusBox.create(boxGraph, UUID.generate(), (box) => {
        box.collection.refer(p.rootBox.audioBusses);
        box.output.refer(fxUnit.input);  // ← bus → FX unit (not primary bus!)
        box.enabled.setValue(true);
        box.label.setValue(fxName);
    });

    // 3. Create AuxSendBox: src AU → FX bus (parallel send, NO redirect)
    sendBox = AuxSendBox.create(boxGraph, UUID.generate(), (box) => {
        box.audioUnit.refer(srcAU.auxSends);
        box.targetBus.refer(fxBus.input);  // ← send targets the bus
        box.routing.setValue(routingVal);  // 0=pre, 1=post
        box.sendGain.setValue(sendDb);     // dB directly (field stores physical units)
        box.sendPan.setValue(0.0);
        box.index.setValue(currentSends);
    });
});
```

## Key points

- **AudioUnitType.Aux = 3** — the FX unit is type Aux, not Instrument
- **fxUnit.output → primaryBus.input** — wet signal joins dry at the main bus
- **fxBus.output → fxUnit.input** — the bus routes INTO the FX unit (not to primary bus directly)
- **send.targetBus → fxBus.input** — the send targets the bus, not the FX unit
- **No TrackBox needed** — in headless mode, tracks are for UI/timeline only.
  Audio routing works through box pointers, not tracks.
- **sendGain in dB** — field stores physical units (like all openDAW fields)

## MCP usage

```python
# 1. Create a send bus from unit 1
result = create_send(src_unit=1, name="Reverb Bus", send_level_db=-6.0, routing="post")
# → {success: true, send_index: 0, fx_unit_index: 2, fx_bus_name: "Reverb Bus"}

# 2. Add effects to the FX bus unit (use fx_unit_index from step 1)
add_effect(unit_index=2, effect_type="reverb")  # case-insensitive since session 5
# → {success: true, effect_index: 0}

# 3. Adjust send level
set_send_level(src_unit=1, send_index=0, level_db=-20.0)
# → {success: true, new_level_db: -20}

# 4. Pan the send (stereo spread)
set_send_pan(src_unit=1, send_index=0, pan=0.5)  # 0.5 = right
# → {success: true, pan: 0.5}

# 5. Switch routing pre/post fader
set_send_routing(src_unit=1, send_index=0, routing="pre")
# → {success: true, routing: "pre"}

# 6. List all sends on a unit
list_sends(unit_index=1)
# → {success: true, send_count: 1, sends: [{send_index: 0, target_bus_name: "Reverb Bus", ...}]}

# 7. List all buses in project
list_audio_buses()
# → {success: true, bus_count: 2, buses: [{bus_index: 0, name: "Output", ...}, {bus_index: 1, name: "Reverb Bus", ...}]}

# 8. Mute/unmute FX bus for A/B comparison
set_bus_enabled(bus_index=1, enabled=False)  # mute
set_bus_enabled(bus_index=1, enabled=True)   # unmute

# 9. Export — dry + wet both present
export_mix(filename="mix_with_reverb.wav")

# 10. Clean up — remove FX bus + AU + all associated sends
remove_audio_bus(bus_index=1)  # or remove_audio_bus(fx_unit_index=2)
# → {success: true, removed_bus_name: "Reverb Bus", removed_fx_unit_index: 2}

# 11. Or remove just one send (keep FX bus)
remove_send(unit_index=1, send_index=0)
```

## Complete send/bus toolkit (51 MCP tools, session 5)

| Tool | Purpose |
|------|---------|
| `create_send` | Create parallel FX bus + send |
| `set_send_level` | Adjust send gain (dB) |
| `set_send_pan` | Stereo pan send (-1..1) |
| `set_send_routing` | Pre/post fader switch |
| `list_sends` | Inspect all sends on AU |
| `remove_send` | Delete single send |
| `list_audio_buses` | List all buses (primary + FX) |
| `set_bus_enabled` | Mute/unmute bus (A/B) |
| `remove_audio_bus` | Delete FX bus + AU + sends |

## DSP processing chain (AudioDeviceChain.#wire)

The openDAW DSP engine wires sends in `AudioDeviceChain.#wire()`:

1. Source (instrument/tape) → effects chain → channel strip
2. If `includeSends`: for each AuxSendBox on the AU:
   - `auxSend.setAudioSource(source.audioOutput)` — copies post-effect signal
   - `target.inputAsAudioBus().addAudioSource(auxSend.audioOutput)` — feeds FX bus
3. Channel strip → output bus (primary or assigned)

Send level is applied by `AuxSendDeviceProcessor.processAudio()`:
- `gain = dbToGain(sendGain.getValue())` — converts dB to linear gain
- Applies pan: `gainL = (1 - max(0, pan)) * gain`, `gainR = (1 + min(0, pan)) * gain`
- Multiplies source by gain → output

## Test results (July 2 sessions 4-5)

- create_send(src=1, "Reverb Bus", -6dB) → fx_unit_index=2, send_index=0 ✅
- export_mix: max_sample=0.538 (audio present) ✅
- set_send_level(-20dB) → peak dropped to 0.403 (send level controls output) ✅
- 3 AUs in state: Unit 0 (primary), Unit 1 (synth), Unit 2 (FX bus) ✅
- Dual send test (Reverb + Delay bus): list_sends shows 2, remove 0 → 1, remove 0 → 0 ✅
- set_send_pan(0.5) → list_sends confirms pan=0.5 ✅
- set_send_routing: post→pre→post switching verified ✅
- list_audio_buses: ["Output", "Reverb Bus"] with unit indices ✅
- set_bus_enabled: mute→unmute FX bus verified ✅
- remove_audio_bus(bus_index=1): bus + AU + sends all cleaned up, verified via list_audio_buses + list_sends ✅

## Pitfalls

- **Do NOT redirect dst AU output** — the send is a parallel copy, not a redirect.
  Redirecting `dstAU.output.refer(fxBus.input)` breaks the dst AU's main path → silence.
- **Effect names are case-insensitive** since July 2 session 5 — `add_effect("reverb")` works, auto-matched to `"Reverb"`.
  Available: Compressor, Crusher, DattorroReverb, Delay, Fold, Gate, Maximizer, NeuralAmp,
  Reverb, Revamp, StereoTool, Tidal, Vocoder, Waveshaper, Werkstatt.
- **export_mix filename safe_name** — the sanitizer strips characters not in
  `alnum + -_.`. If `.wav` becomes `wav`, the dot was missing from the allowed set
  (fixed July 2: added `.` to allowed chars).
- **AudioBusBox.output can only point to one input** — if you set it twice, the second
  refer replaces the first. Create the FX unit FIRST, then point the bus at it.
