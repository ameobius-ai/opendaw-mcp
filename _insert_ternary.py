#!/usr/bin/env python3
"""Insert create_ternary_form tool into server.py."""

TOOL_CODE = r'''

@mcp.tool()
async def mcp_opendaw_create_ternary_form(
    key_root: str = "C",
    scale_name: str = "major",
    a_bars: int = 8,
    b_bars: int = 8,
    a_prime_ornamented: bool = True,
    b_contrast: str = "trio",
    velocity: float = 0.7,
    unit_index: int = -1,
    track_index: int = 0,
    start_beat: float = 0,
) -> str:
    """Create ternary form — ABA with contrasting middle section.

    Ternary form (ABA) is one of the most fundamental structures in
    Western music. The outer A sections are related (often identical,
    or A' with ornamentation), while the middle B section provides
    contrast. Used in:

    - Minuet & Trio (Haydn, Mozart): A=minuet, B=trio, A=minuet da capo
    - Da capo aria (Baroque opera): A=main aria, B=contrasting middle
      emotion, A=ornamented return
    - Chopin Nocturnes: A=lyrical theme, B=agitated middle, A=ornamented
    - Pop/jazz ballads: A=head, B=bridge/solo, A=head out

    B section contrast types:
      - trio: Subdominant key (IV), smoother rhythm, thinner texture.
        Classical minuet & trio.
      - dominant: Dominant key (V), more active rhythm, builds tension.
        Beethoven scherzo style.
      - relative: Relative minor/major, darker/lighter character.
        Schubert impromptu middle sections.
      - episode: Same key, completely different melodic material.
        Chopin nocturne B sections.
      - development: Fragmentation of A material, modulating.
        Late classical/romantic expansion.

    A' (return): If a_prime_ornamented=True, adds passing tones,
    trill-like ornaments, and slight rhythmic variation to the A
    material. Da capo aria / Chopin nocturne practice.

    Melody on track_index, bass on track_index+1.
    """
    NOTE_MAP = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4,
                "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9,
                "A#": 10, "Bb": 10, "B": 11}

    SCALE_INTERVALS = {
        "major": [0, 2, 4, 5, 7, 9, 11],
        "minor": [0, 2, 3, 5, 7, 8, 10],
        "dorian": [0, 2, 3, 5, 7, 9, 10],
        "phrygian": [0, 1, 3, 5, 7, 8, 10],
        "lydian": [0, 2, 4, 6, 7, 9, 11],
        "mixolydian": [0, 2, 4, 5, 7, 9, 10],
        "aeolian": [0, 2, 3, 5, 7, 8, 10],
        "locrian": [0, 1, 3, 5, 6, 8, 10],
        "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
        "melodic_minor": [0, 2, 3, 5, 7, 9, 11],
        "pentatonic_major": [0, 2, 4, 7, 9],
        "pentatonic_minor": [0, 3, 5, 7, 10],
        "blues": [0, 3, 5, 6, 7, 10],
        "whole_tone": [0, 2, 4, 6, 8, 10],
    }

    valid_contrasts = ["trio", "dominant", "relative", "episode", "development"]
    if b_contrast not in valid_contrasts:
        return json.dumps({"error": f"Invalid b_contrast '{b_contrast}'. Valid: {valid_contrasts}"})
    if scale_name not in SCALE_INTERVALS:
        return json.dumps({"error": f"Invalid scale '{scale_name}'. Valid: {list(SCALE_INTERVALS.keys())}"})

    root_pc = NOTE_MAP.get(key_root)
    if root_pc is None:
        return json.dumps({"error": f"Invalid key_root '{key_root}'"})

    scale = SCALE_INTERVALS[scale_name]
    melody_oct = (3 + 1) * 12 + root_pc
    bass_oct = (2 + 1) * 12 + root_pc

    def deg_to_pitch(degree, root_note, sc):
        ns = len(sc)
        oct_shift = degree // ns
        idx = degree % ns
        if idx < 0:
            idx += ns
            oct_shift -= 1
        return root_note + oct_shift * 12 + sc[idx]

    import random as _rng
    rng = _rng.Random(77)

    # Determine B section key
    if b_contrast == "trio":
        b_root_pc = (root_pc + 5) % 12  # subdominant
        b_scale = scale
    elif b_contrast == "dominant":
        b_root_pc = (root_pc + 7) % 12
        b_scale = scale
    elif b_contrast == "relative":
        if scale_name == "minor":
            b_root_pc = (root_pc + 3) % 12  # relative major
            b_scale = SCALE_INTERVALS["major"]
        else:
            b_root_pc = (root_pc + 9) % 12  # relative minor
            b_scale = SCALE_INTERVALS["minor"]
    else:
        b_root_pc = root_pc
        b_scale = scale

    b_melody_oct = (3 + 1) * 12 + b_root_pc
    b_bass_oct = (2 + 1) * 12 + b_root_pc

    # A section material: stepwise, lyrical
    a_degrees = [0, 2, 1, 0, -1, 0, 2, 4]
    a_rhythm = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
    a_bass_deg = [0, 0, 4, 4]

    # B section material: varies by contrast type
    if b_contrast == "trio":
        # Smoother, longer notes
        b_degrees = [0, 3, 2, 0, -1, 0, 3, 2]
        b_rhythm = [1.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        b_bass_deg = [0, 0, 3, 3]
    elif b_contrast == "dominant":
        # More active, eighth notes
        b_degrees = [0, 2, 4, 2, 5, 4, 2, 0]
        b_rhythm = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        b_bass_deg = [0, 4, 0, 4]
    elif b_contrast == "relative":
        # Darker/lighter, wider intervals
        b_degrees = [0, 5, 3, 0, 7, 5, 3, 0]
        b_rhythm = [1.0, 0.5, 0.5, 1.0, 0.5, 0.5, 0.5, 0.5]
        b_bass_deg = [0, 0, 5, 5]
    elif b_contrast == "episode":
        # Same key, different material — leaps
        b_degrees = [7, 2, 5, 0, 9, 4, 7, 2]
        b_rhythm = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        b_bass_deg = [0, 5, 3, 4]
    else:  # development
        # Fragmentation of A material
        b_degrees = a_degrees[:4] + [4, 2, 0, -1]
        b_rhythm = [0.5, 0.5, 0.25, 0.25, 0.5, 0.5, 0.5, 0.5]
        b_bass_deg = [0, 0, 4, 4]

    all_melody = []
    all_bass = []

    # ================================================================
    # A section
    # ================================================================
    beat = start_beat
    for bar in range(max(2, a_bars)):
        bar_start = beat
        for i in range(len(a_degrees)):
            pitch = deg_to_pitch(a_degrees[i] + (bar % 3) - 1, melody_oct, scale)
            dur = a_rhythm[i % len(a_rhythm)]
            all_melody.append({
                "pitch": pitch, "start": round(bar_start, 4),
                "duration": round(dur * 0.9, 4),
                "velocity": round(velocity * 0.95, 3),
            })
            bar_start += dur
        for b in range(4):
            bidx = (bar * 4 + b) % len(a_bass_deg)
            bp = deg_to_pitch(a_bass_deg[bidx], bass_oct, scale)
            all_bass.append({
                "pitch": bp, "start": round(beat + b, 4),
                "duration": 0.9, "velocity": round(velocity * 0.8, 3),
            })
        beat += 4.0

    a_end = beat  # save for reference

    # ================================================================
    # B section (contrast)
    # ================================================================
    for bar in range(max(2, b_bars)):
        bar_start = beat
        for i in range(len(b_degrees)):
            pitch = deg_to_pitch(b_degrees[i] + (bar % 2), b_melody_oct, b_scale)
            dur = b_rhythm[i % len(b_rhythm)]
            # B section slightly different velocity character
            vel_mult = 0.85 if b_contrast in ("trio", "relative") else 0.9
            all_melody.append({
                "pitch": pitch, "start": round(bar_start, 4),
                "duration": round(dur * 0.9, 4),
                "velocity": round(velocity * vel_mult, 3),
            })
            bar_start += dur
        for b in range(4):
            bidx = (bar * 4 + b) % len(b_bass_deg)
            bp = deg_to_pitch(b_bass_deg[bidx], b_bass_oct, b_scale)
            all_bass.append({
                "pitch": bp, "start": round(beat + b, 4),
                "duration": 0.9, "velocity": round(velocity * 0.75, 3),
            })
        beat += 4.0

    # ================================================================
    # A' section (return, optionally ornamented)
    # ================================================================
    for bar in range(max(2, a_bars)):
        bar_start = beat
        for i in range(len(a_degrees)):
            deg = a_degrees[i] + (bar % 3) - 1
            dur = a_rhythm[i % len(a_rhythm)]

            if a_prime_ornamented and rng.random() < 0.35:
                # Add ornament: passing tone or trill-like neighbor
                ornament_deg = deg + rng.choice([1, -1, 2, -2])
                all_melody.append({
                    "pitch": deg_to_pitch(ornament_deg, melody_oct, scale),
                    "start": round(bar_start, 4),
                    "duration": round(dur * 0.3, 4),
                    "velocity": round(velocity * 0.7, 3),
                })
                all_melody.append({
                    "pitch": deg_to_pitch(deg, melody_oct, scale),
                    "start": round(bar_start + dur * 0.3, 4),
                    "duration": round(dur * 0.6, 4),
                    "velocity": round(velocity * 0.95, 3),
                })
            else:
                all_melody.append({
                    "pitch": deg_to_pitch(deg, melody_oct, scale),
                    "start": round(bar_start, 4),
                    "duration": round(dur * 0.9, 4),
                    "velocity": round(velocity * 0.95, 3),
                })
            bar_start += dur
        for b in range(4):
            bidx = (bar * 4 + b) % len(a_bass_deg)
            bp = deg_to_pitch(a_bass_deg[bidx], bass_oct, scale)
            all_bass.append({
                "pitch": bp, "start": round(beat + b, 4),
                "duration": 0.9, "velocity": round(velocity * 0.8, 3),
            })
        beat += 4.0

    all_melody.sort(key=lambda n: (n["start"], n["pitch"]))
    all_bass.sort(key=lambda n: (n["start"], n["pitch"]))

    melody_json = json.dumps(all_melody)
    melody_result = await mcp_opendaw_create_notes_batch(melody_json, unit_index, track_index)

    bass_json = json.dumps(all_bass)
    bass_result = await mcp_opendaw_create_notes_batch(bass_json, unit_index, track_index + 1)

    total_bars = max(2, a_bars) + max(2, b_bars) + max(2, a_bars)
    try:
        data = json.loads(melody_result)
        data["ternary_form"] = True
        data["sections"] = {
            "A": {"bars": max(2, a_bars), "start": start_beat,
                  "end": start_beat + max(2, a_bars) * 4.0,
                  "key": key_root, "character": "main_theme"},
            "B": {"bars": max(2, b_bars),
                  "start": start_beat + max(2, a_bars) * 4.0,
                  "end": start_beat + (max(2, a_bars) + max(2, b_bars)) * 4.0,
                  "key_root_pc": b_root_pc,
                  "contrast": b_contrast,
                  "character": "contrasting_middle"},
            "A_prime": {"bars": max(2, a_bars),
                        "start": start_beat + (max(2, a_bars) + max(2, b_bars)) * 4.0,
                        "end": start_beat + total_bars * 4.0,
                        "ornamented": a_prime_ornamented,
                        "character": "da_capo_return"},
        }
        data["total_bars"] = total_bars
        data["key_root"] = key_root
        data["scale_name"] = scale_name
        data["b_contrast"] = b_contrast
        data["b_key_root_pc"] = b_root_pc
        data["a_prime_ornamented"] = a_prime_ornamented
        data["melody_notes_created"] = len(all_melody)
        data["bass_notes_created"] = len(all_bass)
        data["melody_track"] = track_index
        data["bass_track"] = track_index + 1
        try:
            data["bass_result_status"] = json.loads(bass_result).get("success", False) if bass_result else False
        except Exception:
            data["bass_result_status"] = False
        return json.dumps(data, indent=2)
    except Exception:
        return melody_result
'''

with open("server.py", "a") as f:
    f.write(TOOL_CODE)

print("Inserted create_ternary_form")
