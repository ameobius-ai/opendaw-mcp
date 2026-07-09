---
name: opendaw-workflow-recipes
description: End-to-end workflow recipes for opendaw-mcp — Suno remix, diagnose+fix, master for platform, stem-based mixing.
---

# Workflow Recipes

## 1. Suno Remix Pipeline

Download Suno track → separate stems → import to openDAW → remix → render.

```
Step 1: Generate or download Suno track (WAV)
Step 2: separate_stems("suno_track.wav", model="bs6")
        → 6 stems: bass, drums, vocals, other, guitar, piano
Step 3: For each stem: load_audio → place_audio_region on separate track
Step 4: detect_bpm("suno_track.wav") → set_bpm(result)
Step 5: Add new instruments alongside stems (create_instrument_track)
Step 6: Mix: add_drum_chain, add_bass_chain, add_vocal_chain
Step 7: render_and_analyze → check LUFS, spectrum
Step 8: auto_master(platform="spotify")
Step 9: render_full → final output
```

## 2. Diagnose + Fix Mix

When mix sounds wrong but you don't know why.

```
Step 1: render_and_analyze("current_mix")
Step 2: detect_problems("current_mix.wav")
        → Check: clipping? DC offset? mud? harshness?
Step 3: analyze_phase("current_mix.wav")
        → Check: phase inversion? mono compat?
Step 4: export_stems → detect_frequency_masking
        → Which stems fight?
Step 5: Based on findings:
        - Clipping → reduce channel volumes
        - Mud → EQ cut 300-400 Hz on muddy stems
        - Harshness → EQ cut 3 kHz on harsh stems
        - Masking → cut weaker stem in conflict band
Step 6: render_and_analyze → verify fixes
```

## 3. Master for Platform

```
Step 1: render_and_analyze("pre_master")
Step 2: compare_to_profile("pre_master.wav", genre)
        → See where mix deviates from genre standard
Step 3: auto_master(platform="spotify", style="balanced")
        → Adds mastering chain automatically
Step 4: render_and_analyze("mastered")
        → Verify LUFS is -14 ±1
Step 5: If LUFS off: auto_gain(target_lufs=-14)
Step 6: render_full → final output
```

## 4. Stem-Based Mixing

```
Step 1: separate_stems("full_mix.wav", model="ensemble")
Step 2: Load each stem into openDAW on separate tracks
Step 3: detect_frequency_masking between all stem pairs
Step 4: EQ each stem based on masking findings
Step 5: add_drum_chain on drums track
Step 6: add_bass_chain on bass track
Step 7: add_vocal_chain on vocals track
Step 8: add_mastering_chain on output bus
Step 9: render_and_analyze → verify
```

## 5. A/B Against Reference

```
Step 1: Load reference track in exports dir
Step 2: render_and_analyze("my_mix")
Step 3: compare_to_reference("my_mix.wav", "reference.wav")
        → See exact deltas in LUFS, spectrum, stereo, dynamics
Step 4: Apply fixes based on suggestions
Step 5: Re-render, re-compare
Step 6: Iterate until deltas < 2 in all dimensions
```

## Genre Quick Reference

| Genre | LUFS | Spectral centroid | Stereo | Dynamics |
|-------|------|-------------------|--------|----------|
| Pop | -10 | 2500-4000 Hz | 0.3-0.5 | 6-10 dB |
| Rock | -10 | 2000-3500 Hz | 0.4-0.6 | 7-12 dB |
| Hip-Hop | -10 | 1800-3000 Hz | 0.25-0.45 | 5-9 dB |
| EDM | -8 | 3000-5000 Hz | 0.5-0.8 | 4-7 dB |
| Lo-Fi | -16 | 1000-2000 Hz | 0.15-0.35 | 8-14 dB |
| Ambient | -20 | 2000-4000 Hz | 0.5-0.8 | 12-20 dB |
| Cinematic | -18 | 1500-3000 Hz | 0.4-0.7 | 12-18 dB |

Use `compare_to_profile(filename, genre)` for automated comparison.
