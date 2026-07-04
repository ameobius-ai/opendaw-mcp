# Full Production Pipeline v2 — Scriptable Device Chain (2026-07-03)

End-to-end pipeline combining all three scriptable device types (Apparat + Werkstatt + Spielwerk) with stock instruments and effects, rendered to WAV.

## Pipeline

```
set_bpm(128)
→ create_synth_track("SubBass", "apparat") → unit_index=1
→ set_script_device_code("apparat", 1, 0, apparat_subcrusher.js) → 10 params
→ set_script_param("apparat", 1, 0, "cutoff", 600)
→ set_script_param("apparat", 1, 0, "drive", 0.5)
→ create_note_track(1) → create_track_region(1, 0, 0, 16, "bassline", -1)
→ create_note ×32 (A1/C2/D2 eighth-note bassline, 16 beats)
→ add_effect(1, "Werkstatt") → effect_index=0
→ set_script_device_code("werkstatt", 1, 0, werkstatt_darksat.js) → 5 params
→ set_script_param("werkstatt", 1, 0, "drive", 0.6)
→ create_synth_track("LeadArp", "vaporisateur") → unit_index=2
→ add_midi_effect(2, "Spielwerk")
→ set_script_device_code("spielwerk", 2, 0, spielwerk_arpeggiator.js) → 6 params
→ set_script_param("spielwerk", 2, 0, "rate", 0.125)
→ create_note_track(2) → create_track_region(2, 0, 0, 16, "chords", -1)
→ create_note ×12 (Am-F-C-G chord stabs, 4 chords × 3 notes)
→ add_effect(2, "Delay") → effect_index=0
→ set_effect_parameter(2, 0, "time", 0.375)
→ set_effect_parameter(2, 0, "feedback", 0.35)
→ set_effect_parameter(2, 0, "mix", 0.3)
→ render_full("production_v2", 48000)
```

## Results

| Component | Tool | Params | Notes | Render |
|-----------|------|--------|-------|--------|
| Bass synth | Apparat SubCrusher | 10 | 32 bass notes | ❌ silence (scriptable) |
| Bass saturation | Werkstatt DarkSat | 5 | drive=0.6, tone=0.4 | ❌ silence (scriptable) |
| Lead synth | Vaporisateur | stock | 12 chord notes | ✅ audio |
| MIDI arp | Spielwerk Arpeggiator | 6 | rate=1/8, swing=0.15 | untested |
| Delay | stock Delay | 3 | time=3/8, mix=0.3 | ✅ |
| **Render** | render_full | — | 2.0 MB WAV | partial (Vaporisateur only) |

## Key patterns

### Scriptable device chain order
1. Create instrument AU (`create_synth_track`)
2. Set script code (`set_script_device_code`) — compiles @param declarations, registers worklet
3. Tune params (`set_script_param`)
4. Create note track + region + notes
5. Add audio effects AFTER instrument (`add_effect` → `set_script_device_code` for Werkstatt)

### MIDI effect chain order
1. Create instrument AU
2. Add MIDI effect (`add_midi_effect`) — BEFORE notes, so it processes incoming MIDI
3. Set Spielwerk code
4. Create note track + region + held notes (feed the arpeggiator)

### Held notes for arpeggiator
Spielwerk arpeggiator reads `events` iterator for note-on/off. For chord stabs that feed the arp:
- Use longer durations (e.g. 3.5 beats) so notes stay "held" while arp generates
- Chord: `(0, 45, 3.5), (0, 48, 3.5), (0, 52, 3.5)` = A minor held for 3.5 beats

### Render limitation
Scriptable device processors (Apparat, Werkstatt, Spielwerk) register via `audioContext.audioWorklet.addModule()` on the main thread AudioContext. The `OfflineEngineRenderer` uses a separate Worker — scriptable device code may not propagate. Stock instruments (Vaporisateur, Playfield) and stock effects (Delay, Reverb) render correctly.

**Workaround for full render**: bounce scriptable tracks to audio first (freeze), then render. Or use realtime capture via `capture_realtime` with engine playing.

## Example file

`examples/full_production_pipeline_v2.py` — 189 lines, self-contained, loads DSP scripts from `scripts/` directory.

## Overlap note

`references/warp-marker-crud-2026-07-03.md` and `references/warp-marker-crud-and-region-controls-2026-07-03.md` cover the same v1.8.1 warp marker CRUD tools. The latter is more comprehensive (also covers v1.8.2 region controls). The former is a subset — candidate for consolidation by the curator.
