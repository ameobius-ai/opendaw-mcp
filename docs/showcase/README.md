# Showcase Demos

Three reproducible demos proving opendaw-mcp produces real audio end-to-end.

Combat package: `opendaw-mcp==1.385.0` (PyPI)

## Setup

```bash
pip install opendaw-mcp==1.385.0
```

## Demos

### 1. Techno in 30 seconds
```bash
python examples/showcase/01_techno_30s.py
```
Genre preset → humanize → auto-mix → auto-master → WAV at -14 LUFS.

### 2. Ambient soundscape
```bash
python examples/showcase/02_ambient_pad.py
```
Manual sound design: detuned pad chord, lush reverb, slow filter sweep.

### 3. Suno → DAW pipeline
```bash
python examples/showcase/03_suno_to_daw.py /path/to/suno_track.wav
```
Stem separation → multi-track rebuild → per-stem effects → re-render.

## Expected outputs

Each demo writes a WAV file to `exports/` (or `OPENDAW_EXPORT_DIR`).
Demos 1 and 2 are self-contained (no external files needed).
Demo 3 requires a Suno export WAV (download from suno.com).
