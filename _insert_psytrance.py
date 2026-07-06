#!/usr/bin/env python3
"""Insert create_psytrance_arrangement tool into server.py."""

TOOL_CODE = r'''

@mcp.tool()
async def mcp_opendaw_create_psytrance_arrangement(
    key_root: str = "F",
    bpm: int = 145,
    bars: int = 16,
    velocity: float = 0.75,
    unit_index: int = -1,
    track_index: int = 0,
    start_beat: float = 0,
) -> str:
    """Create a psytrance arrangement — 145 BPM hypnotic Goa/psychedelic.

    Psytrance (psychedelic trance) is a subgenre of trance born in
    Goa, India (early 1990s) and developed in Israel, Europe. Key:
    - 145-150 BPM, 4/4 time, driving and hypnotic
    - Rolling bassline: 16th notes with a specific "k-b-k-b" pattern
      (kick on downbeat, bass on offbeat, creating a rolling feel)
    - Layered percussion: tight hats, snare rolls, shakers
    - Hypnotic lead: repeated motifs, evolving filter sweeps
    - FM synth sounds, alien textures, sci-fi atmosphere
    - Often in F minor or E minor

    Creates 4 tracks:
    1. Drums (track_index): Kick on every beat, snare on 2&4, tight
       16th hats, shaker pattern, snare roll at end of phrases
    2. Bass (track_index+1): Rolling 16th bassline — kick-aligned
       bass notes with offbeat syncopation, creating the psytrance
       "gallop" feel
    3. Lead (track_index+2): Hypnotic repeated motif with filter
       sweep simulation (velocity variations), octave jumps
    4. Atmosphere (track_index+3): Sparse sustained notes, sci-fi
       pad-like textures on bar starts

    Default key: F minor.
    """
    NOTE_MAP = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4,
                "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9,
                "A#": 10, "Bb": 10, "B": 11}

    root_pc = NOTE_MAP.get(key_root)
    if root_pc is None:
        return json.dumps({"error": f"Invalid key_root '{key_root}'"})

    n_bars = max(4, bars)

    KICK = 36
    SNARE = 38
    CLOSED_HAT = 42
    OPEN_HAT = 46
    SHAKER = 64

    minor_scale = [0, 2, 3, 5, 7, 8, 10]
    bass_oct = (2 + 1) * 12 + root_pc
    lead_oct = (4 + 1) * 12 + root_pc
    atm_oct = (3 + 1) * 12 + root_pc

    def deg_to_pitch(degree, root_note, sc):
        ns = len(sc)
        oct_shift = degree // ns
        idx = degree % ns
        if idx < 0:
            idx += ns
            oct_shift -= 1
        return root_note + oct_shift * 12 + sc[idx]

    drums = []
    bass = []
    lead = []
    atmosphere = []

    # Psytrance rolling bass: 16th pattern
    # Pattern: root on kick (0, 4, 8, 12), octave jumps on offbeats
    bass_16th = [0, 0, 0, 3, 0, 0, 0, 5, 0, 0, 0, 3, 0, 0, 7, 5]

    # Lead motif: hypnotic repeated pattern, cycling every 4 bars
    lead_motif = [0, 7, 5, 3, 0, 7, 10, 7, 0, 5, 3, 0, 7, 3, 0, -1]
    lead_rhythm = [0.25] * 16

    for bar in range(n_bars):
        bar_start = start_beat + bar * 4.0

        # --- Drums ---
        for beat in range(4):
            drums.append({
                "pitch": KICK, "start": round(bar_start + beat, 4),
                "duration": 0.5, "velocity": round(velocity, 3),
            })
        for beat in [1.0, 3.0]:
            drums.append({
                "pitch": SNARE, "start": round(bar_start + beat, 4),
                "duration": 0.2, "velocity": round(velocity * 0.85, 3),
            })
        for h in range(16):
            drums.append({
                "pitch": CLOSED_HAT, "start": round(bar_start + h * 0.25, 4),
                "duration": 0.06, "velocity": round(velocity * 0.3, 3),
            })
        for s in range(8):
            drums.append({
                "pitch": SHAKER, "start": round(bar_start + s * 0.5, 4),
                "duration": 0.1, "velocity": round(velocity * 0.35, 3),
            })
        # Snare roll at end of every 4 bars
        if (bar + 1) % 4 == 0:
            for i in range(8):
                pos = bar_start + 3.0 + i * 0.125
                drums.append({
                    "pitch": SNARE, "start": round(pos, 4),
                    "duration": 0.08,
                    "velocity": round(velocity * (0.3 + 0.08 * i), 3),
                })

        # --- Rolling Bass ---
        for i in range(16):
            deg = bass_16th[(bar * 16 + i) % len(bass_16th)]
            pitch = deg_to_pitch(deg, bass_oct, minor_scale)
            # Velocity: stronger on kick positions (0, 4, 8, 12)
            vel = velocity * (0.9 if i % 4 == 0 else 0.65)
            bass.append({
                "pitch": pitch, "start": round(bar_start + i * 0.25, 4),
                "duration": 0.22, "velocity": round(vel, 3),
            })

        # --- Lead (hypnotic motif) ---
        for i in range(16):
            deg = lead_motif[(bar * 4 + i) % len(lead_motif)]
            pitch = deg_to_pitch(deg, lead_oct, minor_scale)
            dur = lead_rhythm[i % len(lead_rhythm)]
            # Filter sweep simulation: velocity rises through bar
            vel_mod = 0.4 + 0.5 * ((bar * 16 + i) % 64) / 64.0
            lead.append({
                "pitch": pitch, "start": round(bar_start + i * 0.25, 4),
                "duration": round(dur * 0.85, 4),
                "velocity": round(velocity * vel_mod, 3),
            })

        # --- Atmosphere (sustained sci-fi pad) ---
        if bar % 2 == 0:
            atmosphere.append({
                "pitch": deg_to_pitch(3, atm_oct, minor_scale),
                "start": round(bar_start, 4),
                "duration": 4.0, "velocity": round(velocity * 0.35, 3),
            })
            atmosphere.append({
                "pitch": deg_to_pitch(10, atm_oct, minor_scale),
                "start": round(bar_start + 2.0, 4),
                "duration": 2.0, "velocity": round(velocity * 0.3, 3),
            })

    drums.sort(key=lambda n: (n["start"], n["pitch"]))
    bass.sort(key=lambda n: (n["start"], n["pitch"]))
    lead.sort(key=lambda n: (n["start"], n["pitch"]))
    atmosphere.sort(key=lambda n: (n["start"], n["pitch"]))

    results = []
    for i, (notes, label) in enumerate([
        (drums, "drums"), (bass, "bass"), (lead, "lead"), (atmosphere, "atmosphere")
    ]):
        notes_json = json.dumps(notes)
        result = await mcp_opendaw_create_notes_batch(notes_json, unit_index, track_index + i)
        results.append(result)

    try:
        data = json.loads(results[0])
        data["psytrance_arrangement"] = True
        data["bpm"] = bpm
        data["bars"] = n_bars
        data["key_root"] = key_root
        data["tracks"] = {
            "drums": {"track": track_index, "notes": len(drums),
                       "style": "145 BPM: kick 4-on-floor + snare 2&4 + 16th hats + shaker + snare rolls"},
            "bass": {"track": track_index + 1, "notes": len(bass),
                      "style": "rolling 16th bassline, kick-aligned with offbeat gallop"},
            "lead": {"track": track_index + 2, "notes": len(lead),
                      "style": "hypnotic 16th motif with filter sweep velocity curve"},
            "atmosphere": {"track": track_index + 3, "notes": len(atmosphere),
                            "style": "sustained sci-fi pad, minor 3rd and minor 7th"},
        }
        data["total_notes"] = len(drums) + len(bass) + len(lead) + len(atmosphere)
        data["all_tracks_created"] = all(
            json.loads(r).get("success", False) if r else False for r in results
        )
        return json.dumps(data, indent=2)
    except Exception:
        return results[0]
'''

with open("server.py", "a") as f:
    f.write(TOOL_CODE)

print("Inserted create_psytrance_arrangement")
