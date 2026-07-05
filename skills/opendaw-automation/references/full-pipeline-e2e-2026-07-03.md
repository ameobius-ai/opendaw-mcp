# Full Production Pipeline E2E (2026-07-03)

End-to-end verification of the complete production workflow with audio rendering.

## Pipeline

```
set_bpm(120) → set_time_signature(4,4)
→ create_synth_track("Synth", "Vaporisateur") → unit_index=1
→ create_note_track(1) → create_track_region(1, 0, 0, 16, "Chords", 200)
→ create_note ×12 (4 chords: Am-F-C-G, 3 notes each, 4-beat duration)
→ set_vaporisateur_osc_param("0", "waveform", 2, 1)  # Saw
→ set_vaporisateur_osc_param("1", "waveform", 2, 1)  # Saw, -1 octave
→ create_synth_track("Drums", "Playfield") → unit_index=2
→ create_note_track(2) → create_track_region(2, 0, 0, 16, "Drums", 15)
→ create_note ×14 (4 kick, 2 snare, 8 hihat)
→ add_effect(1, "Reverb")  # reverb on synth
→ add_automation(1, 0, "cutoff", "[[0,0.1],[4,0.8],[8,0.3],[12,0.9],[16,0.1]]")
→ set_track_volume(1, "-6") → set_track_volume(2, "-3")
→ add_marker(0, "Intro") → add_marker(16, "Verse")
→ render_full("full_mix", 48000)
→ export_stems("stems", 48000)
→ render_range(0, 4, "bar1_preview", 48000)
→ get_full_project_state()
```

## Results

| Tool | Samples | max_sample | Size | Audio? |
|------|---------|------------|------|--------|
| render_full | 1,824,000 | 0.5387 | 13.92 MB | ✅ |
| export_stems | 1,824,000 | 0.8414 | — | ✅ |
| render_range (0-4) | 1,536,000 | 0.4216 | — | ✅ |

3 AUs: Output (0 FX), Drums/Playfield (0 FX), Synth/Vaporisateur (1 FX = Reverb).

## Gotchas encountered

1. **`set_vaporisateur_osc_param` arg order** — example had `(synth_uid, 0, "waveform", 2)` but correct is `("0", "waveform", 2, synth_uid)`. osc_index is STRING, unit_index is LAST arg.
2. **`add_automation` on Reverb "cutoff"** — Reverb doesn't have a "cutoff" parameter. Automation should target the instrument (Vaporisateur) not the effect. Warning: "No parameter 'cutoff' on ReverbDeviceBox". Non-fatal — pipeline continues.
3. **`export_stems` needs args** — `export_stems("stems", 48000)`, not `export_stems()`. Both `filename_prefix` and `sample_rate` are required.
4. **PYTHONPATH** — running examples from `examples/` dir needs `PYTHONPATH=.` to find `server` module: `PYTHONPATH=. python3 examples/full_production_pipeline.py`
5. **Vite path** — Vite is at `agent-daw/headless-daw/`, NOT `agent-daw/opendaw-mcp/headless-daw/`. Wrong path → "no such file or directory".
6. **Render timeout** — 16-beat render at 48kHz takes ~10-15s. Use `timeout 300` on the Python side.

## File output

WAV files saved to `OPENDAW_EXPORT_DIR` (default: `opendaw-mcp/exports/`):
- `full_mix.wav` — 13.92 MB
- `stems_*.wav` — per-AU stems
- `bar1_preview.wav` — first 4 beats

All via base64 round-trip: JS `btoa()` → `window.__lastExportB64` → Python `base64.b64decode()` → file write.
