# Inspect Phase — Agent Guide

## When to use this phase
```
OPENDAW_MCP_MODE=phase
switch_phase("inspect")
```

## Core workflow

### 1. Project overview
```
get_full_project_state()
get_project_info()
```

### 2. List tracks, regions, effects
```
list_tracks()
list_note_regions()
list_audio_regions()
list_effects()
list_audio_buses()
list_markers()
list_clips()
list_automation_events()
```

### 3. Effect state
```
get_effect_state(unit_index=0, effect_index=0)
```

### 4. BPM detection
```
detect_bpm()
```

### 5. Metering (after mastering)
```
read_meter()  # read LUFS/correlation/spectrum from output meter
```

### 6. Analysis
```
analyze_mix()        # LUFS, dynamic range, spectrum
analyze_dynamics()   # dynamic range, crest factor
analyze_spectrum()   # frequency balance
analyze_stereo()     # stereo width, phase
```

### 7. Raw JavaScript (power users)
```
evaluate_raw(script="return window.DAW_project.units.size()")
```

## Metering trio
After auto_master, three verification meters are available:
- **LUFS meter** (auto-placed by auto_master) — integrated/short-term/momentary loudness
- **Correlation meter** — stereo phase -1 to +1, mono compatibility
- **Spectrum analyzer** — peak freq, centroid, rolloff, band levels

## Verification workflow
```
# After mastering in mix phase:
switch_phase("inspect")
read_meter()          # check LUFS ≈ target
analyze_mix()         # full analysis
analyze_spectrum()    # frequency balance
analyze_stereo()      # stereo phase check
```

## Token optimization
Use `OPENDAW_MCP_OUTPUT_LIMIT=2000` to truncate bulky JSON responses.
Dicts get field truncation, lists get first N items with total/shown counts.
