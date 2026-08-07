"""
Rendering & Export Tools
==================
"""

import json
import asyncio

# These will be injected by server.py
bridge = None
_wrap_eval = None
_ok = None
_err = None


def init_rendering_tools(bridge_instance, wrap_eval_func, ok_func=None, err_func=None):
    """Initialize rendering tools with shared dependencies."""
    global bridge, _wrap_eval, _ok, _err
    bridge = bridge_instance
    _wrap_eval = wrap_eval_func
    _ok = ok_func
    _err = err_func



async def mcp_opendaw_auto_gain(target_lufs: float, filename: str = "auto_gain_mix", sample_rate: int = 48000, max_iterations: int = 3) -> str:
    """Auto-adjust output volume to hit a target LUFS.

    Iterative loop: render → measure LUFS → adjust Maximizer threshold → re-render.
    Converges within ±1 LUFS of target.

    target_lufs: Target loudness (Spotify -14, YouTube -14, Apple -16).
    filename: Output filename (without .wav).
    sample_rate: Export sample rate (default 48000).
    max_iterations: Max refinement loops (default 3).

    Returns final LUFS, threshold applied, iterations, and WAV path.
    """
    target = target_lufs
    max_iter = max_iterations if max_iterations else 3
    safe_name = _safe_filename(filename)

    # Step 1: Ensure Maximizer on output AU
    maxi_result = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        const ef = window.DAW_EffectFactories;
        const api = h.api;
        const units = h.allAUBoxes();
        const au = units[0]; // output AU

        const existing = h.effectBoxes(au);
        let maxiBox = existing.find(b => b.constructor.name === "MaximizerDeviceBox");

        if (!maxiBox) {
            h.editing.modify(() => {
                maxiBox = api.insertEffect(au.audioEffects, ef.AudioNamed["Maximizer"]);
            });
        }
        return {
            maximizer_added: !existing.some(b => b.constructor.name === "MaximizerDeviceBox"),
            has_lookahead: !!maxiBox?.lookahead
        };
    }""")
    if isinstance(maxi_result, dict) and "error" in maxi_result:
        return _wrap_eval(maxi_result)

    iterations = []
    current_threshold = max(-24.0, target - 6.0)  # start slightly below target
    current_volume_db = 0.0  # output AU volume in dB

    for i in range(max_iter):
        # Set Maximizer threshold + output AU volume
        await bridge.evaluate(f"""() => {{
            const h = window.DAW_HELPERS;
            const units = h.allAUBoxes();
            const au = units[0]; // output AU
            const maxi = h.effectBoxes(au).find(b => b.constructor.name === "MaximizerDeviceBox");
            if (!maxi) return {{error: "No Maximizer"}};
            h.editing.modify(() => {{
                maxi.threshold.setValue({current_threshold});
                if (maxi.lookahead) maxi.lookahead.setValue(true);
                // Output AU volume — field stores dB directly (min -96, max +6)
                au.volume.setValue({current_volume_db});
            }});
            return {{threshold: {current_threshold}, volume_db: {current_volume_db}}};
        }}""")

        # Render full mix
        render_result = await bridge.evaluate(f"""async () => {{
            const h = window.DAW_HELPERS;
            const OfflineEngineRenderer = window.DAW_OfflineEngineRenderer;
            const Option = window.DAW_Option;
            const WavFile = window.DAW_WavFile;
            return new Promise(async (resolve) => {{
                try {{
                    const progress = {{setValue: (v) => {{}}}};
                    const audioData = await OfflineEngineRenderer.start(h.project, Option.None, progress, undefined, {sample_rate});
                    const wav = WavFile.encodeFloats(audioData);
                    const bytes = new Uint8Array(wav);
                    const chunks = [];
            const chunkSize = 0x8000;
            for (let ci = 0; ci < bytes.length; ci += chunkSize) {{
                chunks.push(String.fromCharCode.apply(null, bytes.subarray(ci, ci + chunkSize)));
            }}
            const binary = chunks.join("");
                    window.__lastExportB64 = btoa(binary);
                    resolve({{success: true, samples: audioData.frames[0]?.length || 0}});
                }} catch(e) {{
                    resolve({{error: e.message}});
                }}
            }});
        }}""", timeout=1200000)
        if isinstance(render_result, dict) and render_result.get("error"):
            iterations.append({"iteration": i+1, "error": render_result["error"]})
            break

        # Save WAV
        import base64 as b64mod
        export_dir = os.environ.get("OPENDAW_EXPORT_DIR", os.path.join(os.path.dirname(__file__), "exports"))
        os.makedirs(export_dir, exist_ok=True)
        b64 = await bridge.evaluate("() => window.__lastExportB64")
        filepath = os.path.join(export_dir, f"{safe_name}.wav")
        if isinstance(b64, str) and b64:
            wav_bytes = b64mod.b64decode(b64)
            with open(filepath, "wb") as f:
                f.write(wav_bytes)

        # Measure LUFS
        lufs_result = await mcp_opendaw_measure_lufs(safe_name)
        lufs_data = json.loads(lufs_result) if isinstance(lufs_result, str) else lufs_result

        if isinstance(lufs_data, dict) and lufs_data.get("error"):
            iterations.append({"iteration": i+1, "error": lufs_data["error"]})
            break

        current_lufs = lufs_data.get("lufs_integrated", -23.0)
        diff = current_lufs - target
        iterations.append({
            "iteration": i + 1,
            "threshold_db": round(current_threshold, 2),
            "volume_db": round(current_volume_db, 2),
            "lufs": current_lufs,
            "diff": round(diff, 2),
        })

        # Converged?
        if abs(diff) <= 1.0:
            break

        # Bidirectional adjustment:
        # - Too quiet (diff < 0): lower Maximizer threshold (more makeup gain)
        # - Too loud (diff > 0): lower output AU volume (attenuation)
        # LUFS change ≈ threshold change (1:1 for Maximizer) and ≈ volume change (1:1)
        if diff < 0:
            # Need louder: decrease threshold
            current_threshold = max(-24.0, current_threshold + diff * 0.8)
        else:
            # Need quieter: decrease volume (negative dB)
            current_volume_db = max(-24.0, current_volume_db - diff * 0.8)

    final = iterations[-1] if iterations else {}
    return json.dumps({
        "success": True,
        "target_lufs": target,
        "final_lufs": final.get("lufs"),
        "final_threshold_db": round(current_threshold, 2),
        "iterations": iterations,
        "converged": abs(final.get("diff", 999)) <= 1.0 if final else False,
        "filepath": os.path.join(os.environ.get("OPENDAW_EXPORT_DIR", os.path.join(os.path.dirname(__file__), "exports")), f"{safe_name}.wav"),
    })


async def mcp_opendaw_create_l_system_melody(
    root: str = "C",
    scale: str = "minor",
    bars: int = 4,
    octave: int = 4,
    preset: str = "fibonacci",
    axiom: str = "",
    rules: str = "",
    symbol_map: str = "",
    iterations: int = 6,
    duration: float = 0.25,
    velocity: float = 0.7,
    rest_symbol: str = "",
    unit_index: int = 0,
    track_index: int = 0,
    start_beat: float = 0,
) -> str:
    """Create a melody using an L-system (Lindenmayer system) — a deterministic rewriting system.

    L-systems generate self-similar, fractal patterns through recursive production rules.
    Each symbol in the expanded string maps to a scale step interval. The cumulative
    sum of intervals determines the melodic contour.

    Unlike Markov chains (stochastic, memory-based) or random walk (zero-order),
    L-systems are fully deterministic — same axiom + rules + iterations always
    produce the same melody. This makes them ideal for:
    - Self-similar melodic structures (fractal music)
    - Deterministic generative composition
    - Algorithmic music based on mathematical systems

    Presets:
      fibonacci — Fibonacci word (A->AB, B->A), golden ratio self-similarity
      cantor    — Cantor set (A->ABA, B->BBB), gaps and self-similar structure
      dragon    — Dragon curve (A->A+B, B->A-B), jagged contour
      koch      — Koch snowflake (A->A+A-A-A+A), angular melody
      sierpinski — Sierpinski triangle (A->BA, B->BA), binary pattern

    Custom: provide axiom, rules (JSON), and symbol_map (JSON) to define your own L-system.

    Args:
        root: Root note name (C, C#, D, ...).
        scale: Scale name (major, minor, dorian, phrygian, lydian, mixolydian,
            harmonic_minor, melodic_minor, pentatonic_major, pentatonic_minor, blues).
        bars: Number of bars (1-32).
        octave: Starting MIDI octave (1-6).
        preset: Preset name (fibonacci, cantor, dragon, koch, sierpinski).
        axiom: Custom axiom string (overrides preset).
        rules: Custom rules as JSON {"A": "AB", "B": "A"}.
        symbol_map: Custom symbol-to-interval map as JSON {"A": 1, "B": -1}.
        iterations: Number of rule applications (1-8). Higher = more complex.
        duration: Note duration in beats (0.0625-4.0).
        velocity: Base velocity 0-1.
        rest_symbol: Symbol that produces a rest (skip note, advance position).
        unit_index: AU index.
        track_index: Note track index.
        start_beat: Starting beat position.

    Returns notes created, L-system string length, and fractal statistics.
    """
    from opendaw_mcp.music_theory import SCALE_INTERVALS

    NOTE_NAMES = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5,
                  "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
    root_num = NOTE_NAMES.get(root, 0)
    intervals = SCALE_INTERVALS.get(scale, SCALE_INTERVALS["minor"])

    if not (1 <= bars <= 32):
        return f"Error: bars must be 1-32, got {bars}"
    if not (1 <= iterations <= 8):
        return f"Error: iterations must be 1-8, got {iterations}"
    if not (0.0625 <= duration <= 4.0):
        return f"Error: duration must be 0.0625-4.0, got {duration}"

    # L-system presets
    PRESETS = {
        "fibonacci": {"axiom": "A", "rules": {"A": "AB", "B": "A"}, "symbol_map": {"A": 1, "B": -1}},
        "cantor": {"axiom": "A", "rules": {"A": "ABA", "B": "BBB"}, "symbol_map": {"A": 2, "B": 0}},
        "dragon": {"axiom": "A", "rules": {"A": "A+B", "B": "A-B"}, "symbol_map": {"A": 1, "B": 1, "+": 3, "-": -3}},
        "koch": {"axiom": "A", "rules": {"A": "A+A-A-A+A"}, "symbol_map": {"A": 1, "+": 2, "-": -2}},
        "sierpinski": {"axiom": "A", "rules": {"A": "BA", "B": "BA"}, "symbol_map": {"A": 1, "B": -1}},
    }

    # Use custom or preset
    if axiom or rules or symbol_map:
        ls_axiom = axiom if axiom else "A"
        try:
            ls_rules = json.loads(rules) if rules else {"A": "AB", "B": "A"}
        except (json.JSONDecodeError, ValueError, TypeError):
            return "Error: invalid rules JSON. Use format like {\"A\": \"AB\", \"B\": \"A\"}"
        try:
            ls_map_raw = json.loads(symbol_map) if symbol_map else {"A": 1, "B": -1}
        except (json.JSONDecodeError, ValueError, TypeError):
            return "Error: invalid symbol_map JSON. Use format like {\"A\": 1, \"B\": -1}"
        ls_map = {k: int(v) for k, v in ls_map_raw.items()}
    else:
        preset_data = PRESETS.get(preset, PRESETS["fibonacci"])
        ls_axiom = preset_data["axiom"]
        ls_rules = preset_data["rules"]
        ls_map = preset_data["symbol_map"]

    # Expand L-system
    current = ls_axiom
    for _ in range(iterations):
        parts = []
        for ch in current:
            parts.append(ls_rules.get(ch, ch))
        current = "".join(parts)
        if len(current) > 2000:
            current = current[:2000]
            break

    # Build scale pitch list spanning 3 octaves
    scale_pitches = []
    for oct_shift in range(-1, 2):
        for iv in intervals:
            pitch = (octave + 1 + oct_shift) * 12 + (root_num + iv) % 12
            scale_pitches.append(pitch)
    scale_pitches = sorted(set(scale_pitches))

    # Map L-system string to notes
    total_notes_target = int(bars * 4 / duration)
    start_idx = len(scale_pitches) // 2
    current_idx = start_idx

    notes = []
    symbol_counts = {}
    step_sequence = []
    note_position_counter = 0

    for i, ch in enumerate(current):
        if note_position_counter >= total_notes_target:
            break

        if rest_symbol and ch == rest_symbol:
            note_position_counter += 1
            continue

        step = ls_map.get(ch, 0)
        symbol_counts[ch] = symbol_counts.get(ch, 0) + 1

        new_idx = current_idx + step
        # Boundary: reflect
        if new_idx < 0:
            new_idx = abs(new_idx)
        elif new_idx >= len(scale_pitches):
            new_idx = 2 * len(scale_pitches) - new_idx - 2
        new_idx = max(0, min(len(scale_pitches) - 1, new_idx))

        actual_step = new_idx - current_idx
        step_sequence.append(actual_step)

        pitch = scale_pitches[new_idx]
        pos = note_position_counter * duration

        notes.append({
            "pitch": pitch,
            "pos": round(pos, 4),
            "dur": duration,
            "vel": velocity,
        })
        current_idx = new_idx
        note_position_counter += 1

    # Statistics
    if notes:
        pitch_range = max(n["pitch"] for n in notes) - min(n["pitch"] for n in notes)
    else:
        pitch_range = 0
    avg_step = sum(abs(s) for s in step_sequence) / len(step_sequence) if step_sequence else 0
    direction_changes = 0
    for i in range(1, len(step_sequence)):
        if step_sequence[i] * step_sequence[i - 1] < 0:
            direction_changes += 1

    # L-system preview (first 80 chars)
    ls_preview = current[:80]

    pitches_json = json.dumps([n["pitch"] for n in notes])
    positions_json = json.dumps([n["pos"] for n in notes])
    durations_json = json.dumps([n["dur"] for n in notes])
    velocities_json = json.dumps([n["vel"] for n in notes])
    _ = (pitches_json, positions_json, durations_json, velocities_json, start_beat)

    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const Quarter = h.ppqn.Quarter;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const startPos = {start_beat};

        const allUnits = h.allAUBoxes();
        if (unitIdx < 0 || unitIdx >= allUnits.length) return {{error: "unit_index out of range"}};
        const au = allUnits[unitIdx];
        const noteTracks = h.noteTrackBoxes(au);
        if (trackIdx < 0 || trackIdx >= noteTracks.length) return {{error: "track_index out of range"}};
        const trackBox = noteTracks[trackIdx];

        const regions = h.regionBoxes(trackBox);
        let collection = null;
        if (regions.length > 0) {{
            try {{
                const vertex = regions[0].events.targetVertex.unwrap();
                collection = vertex.box || vertex;
            }} catch(e) {{}}
        }}
        if (!collection) return {{error: "No region/collection on track"}};

        const pitches = {pitches_json};
        const positions = {positions_json};
        const durations = {durations_json};
        const velocities = {velocities_json};

        let created = 0;
        const noteEvents = [];

        h.modify(() => {{
            let NoteEventBox = h.NoteEventBox;
            if (!NoteEventBox) return;
            for (let i = 0; i < pitches.length; i++) {{
                const posTicks = Math.round((startPos + positions[i]) * Quarter);
                const durTicks = Math.round(durations[i] * Quarter);
                NoteEventBox.create(h.boxGraph, h.uuid.generate(), (box) => {{
                    box.position.setValue(posTicks);
                    box.duration.setValue(durTicks);
                    box.pitch.setValue(pitches[i]);
                    box.velocity.setValue(velocities[i]);
                    box.events.refer(collection.events);
                }});
                created++;
                noteEvents.push({{pitch: pitches[i], pos: positions[i]}});
            }}
        }});

        return {{
            success: true,
            root: "{root}",
            scale: "{scale}",
            bars: {bars},
            preset: "{preset}",
            iterations: {iterations},
            l_system_length: {len(current)},
            notes_created: created,
            fractal_stats: {{
                pitch_range: {pitch_range},
                avg_step: Math.round({avg_step} * 100) / 100,
                direction_changes: {direction_changes},
                self_similar: {len(current) > 10},
            }},
            symbol_distribution: {json.dumps(symbol_counts)},
            l_system_preview: "{ls_preview}",
            note_preview: noteEvents.slice(0, 10),
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_create_synthwave_arrangement(
    bpm: float = 110,
    bars: int = 8,
    root: str = "A",
    octave: int = 2,
    unit_index: int = 0,
    drum_track: int = 0,
    bass_track: int = 1,
    pad_track: int = 2,
    lead_track: int = 3,
    start_beat: float = 0,
    velocity: float = 0.75,
) -> str:
    """Create a full synthwave arrangement — retro drums + arpeggiated bass + dreamy pads + nostalgic lead across 4 tracks.

    80s-inspired synthwave with the signature nostalgic feel — fundamentally different from other electronic genres:
    - Track 0: Drums — retro four-on-floor: kick on every quarter (softer than house),
                     snare on beats 2 & 4, closed hats on all 8ths. The classic 80s
                     drum machine feel — driving but not aggressive, nostalgic not punchy.
    - Track 1: Bass — ARPEGGIATED 16th notes: the engine of synthwave. Root → octave
                     → fifth → octave pattern, driving and relentless. Not sustained
                     like reggae, not sub-drone like techno — arpeggiated movement.
    - Track 2: Pads — sustained minor chords, full bar length. Dreamy, long release,
                     filling the harmonic space. The nostalgic wash underneath.
    - Track 3: Lead — simple nostalgic melody following chord changes, with echo-like
                     call-and-response. Memorable phrases that breathe.

    Uses the classic synthwave progression i-VI-III-VII (Am-F-C-G in A minor) —
    the four chords that define the genre. Different from pop's I-V-vi-IV (same
    chords, different order and tonal centre — synthwave is minor-key, pop is major).

    At 110 BPM (default), this creates the classic synthwave groove — mid-tempo,
    nostalgic, driving. The arpeggiated bass is the fundamental difference from
    all 11 other arrangements: house has off-beat stabs, techno has sub drones,
    synthwave has relentless 16th-note arpeggios.

    bpm: Tempo (90-130, default 110 = classic synthwave).
    bars: Arrangement length (4-16, default 8). Must be multiple of 4 for chord cycle.
    root: Root note (A is the classic synthwave key — Am).
    octave: MIDI octave for bass (2 = A2=45, standard synthwave bass register).
    unit_index: AU index with note tracks.
    drum_track / bass_track / pad_track / lead_track: Track indices.

    Returns notes created per track and total.

    Example:
      create_synthwave_arrangement(bpm=110, root="A", bars=8)
      create_synthwave_arrangement(bpm=100, root="D", bars=16)
    """
    if not (90 <= bpm <= 130):
        return "Error: bpm must be 90-130"
    if bars < 4 or bars > 16:
        return "Error: bars must be 4-16"
    if bars % 4 != 0:
        return "Error: bars must be a multiple of 4 for chord cycle"
    if root not in NOTE_TO_PITCH:
        return f"Error: unknown root '{root}'. Valid: {list(NOTE_TO_PITCH.keys())}"
    if not (0.0 <= velocity <= 1.0):
        return "Error: velocity must be 0-1"
    if not (0 <= octave <= 4):
        return "Error: octave must be 0-4"

    root_pc = NOTE_TO_PITCH[root]
    bass_base = (octave + 1) * 12 + root_pc
    pad_base = (octave + 3) * 12 + root_pc
    lead_base = (octave + 4) * 12 + root_pc

    # i-VI-III-VII chord progression (Am-F-C-G in A minor)
    # 4-bar cycle: each chord gets 1 bar
    chord_changes = [
        (0, 0, "i"),      # Am — tonic minor
        (4, 8, "VI"),     # F  — relative major (8 semitones up)
        (8, 3, "III"),    # C  — major third (3 semitones up)
        (12, 7, "VII"),   # G  — major seventh (7 semitones up)
    ]

    # --- DRUMS: retro four-on-floor (4-bar cycle) ---
    # Kick on every quarter (softer than house), snare on 2 & 4,
    # closed hats on all 8ths. Nostalgic 80s drum machine feel.
    kick_p, snare_p, hat_p = 36, 38, 42
    drum_notes = []
    drum_cycle = 16.0  # 4 bars
    drum_cycles = bars // 4
    for c in range(drum_cycles):
        off = c * drum_cycle
        for bar in range(4):
            bar_off = off + bar * 4
            # Kick on every quarter
            for beat in range(4):
                drum_notes.append({
                    "pitch": kick_p,
                    "start": round(start_beat + bar_off + beat, 4),
                    "duration": 0.25,
                    "velocity": round(velocity * 0.75, 3),  # softer than house
                })
            # Snare on 2 & 4 (beats 1 and 3 in 0-indexed)
            for snare_beat in [1.0, 3.0]:
                drum_notes.append({
                    "pitch": snare_p,
                    "start": round(start_beat + bar_off + snare_beat, 4),
                    "duration": 0.15,
                    "velocity": round(velocity * 0.7, 3),
                })
            # Closed hats on all 8ths
            for hat_beat in [b * 0.5 for b in range(8)]:
                drum_notes.append({
                    "pitch": hat_p,
                    "start": round(start_beat + bar_off + hat_beat, 4),
                    "duration": 0.05,
                    "velocity": round(velocity * 0.5, 3),
                })

    # --- BASS: arpeggiated 16th notes (4-bar cycle) ---
    # The synthwave engine: root → octave → fifth → octave, 16th notes
    # Drives the track forward — not sustained, not stabs, relentless arp
    bass_arp = [0, 12, 7, 12]  # root, octave, fifth, octave
    bass_notes = []
    bass_cycle = 16.0
    bass_cycles = bars // 4
    for c in range(bass_cycles):
        off = c * bass_cycle
        for bar_start, chord_root, _ in chord_changes:
            bar_off = off + bar_start
            for beat_idx in range(16):  # 16 sixteenth notes per bar
                arp_note = bass_arp[beat_idx % 4]
                bass_notes.append({
                    "pitch": bass_base + chord_root + arp_note,
                    "start": round(start_beat + bar_off + beat_idx * 0.25, 4),
                    "duration": 0.2,  # slight overlap for groove
                    "velocity": round(velocity * (0.85 if beat_idx % 4 == 0 else 0.7), 3),
                })

    # --- PADS: sustained minor chords (4-bar cycle) ---
    # Full bar sustain, dreamy wash. Minor triad + octave for richness.
    # i = root+min3+fifth, VI = root+maj3+fifth, III/VII same major triad shape
    pad_voicings = {
        "i":   [0, 3, 7, 12],    # Am: root + min3 + fifth + octave
        "VI":  [0, 4, 7, 12],    # F:  root + maj3 + fifth + octave
        "III": [0, 4, 7, 12],    # C:  root + maj3 + fifth + octave
        "VII": [0, 4, 7, 12],    # G:  root + maj3 + fifth + octave
    }
    pad_notes = []
    pad_cycle = 16.0
    pad_cycles = bars // 4
    for c in range(pad_cycles):
        off = c * pad_cycle
        for bar_start, chord_root, chord_name in chord_changes:
            bar_off = off + bar_start
            voicing = pad_voicings[chord_name]
            for interval in voicing:
                pad_notes.append({
                    "pitch": pad_base + chord_root + interval,
                    "start": round(start_beat + bar_off, 4),
                    "duration": 3.8,  # almost full bar — dreamy sustain
                    "velocity": round(velocity * 0.45, 3),  # soft pads
                })

    # --- LEAD: nostalgic melody (4-bar cycle) ---
    # Simple, memorable phrases following chord changes.
    # Uses chord tones with passing notes. Echo-like call-and-response.
    # Each bar: 2-beat phrase + 2-beat rest (echo space)
    lead_patterns = {
        "i":   [(0.0, 0, 1.0), (1.0, 3, 0.5), (1.5, 7, 0.5), (2.5, 5, 1.0)],     # Am: root, min3, fifth, fourth
        "VI":  [(0.0, 0, 1.0), (1.0, 4, 0.5), (1.5, 7, 0.5), (2.5, 5, 1.0)],     # F:  root, maj3, fifth, fourth
        "III": [(0.0, 0, 0.5), (0.5, 4, 0.5), (1.0, 7, 1.0), (2.5, 4, 1.0)],     # C:  root, maj3, fifth, maj3
        "VII": [(0.0, 7, 1.0), (1.0, 4, 0.5), (1.5, 0, 0.5), (2.5, 7, 1.0)],     # G:  fifth, maj3, root, fifth
    }
    lead_notes = []
    lead_cycle = 16.0
    lead_cycles = bars // 4
    for c in range(lead_cycles):
        off = c * lead_cycle
        for bar_start, chord_root, chord_name in chord_changes:
            bar_off = off + bar_start
            pattern = lead_patterns[chord_name]
            for beat, interval, dur in pattern:
                lead_notes.append({
                    "pitch": lead_base + chord_root + interval,
                    "start": round(start_beat + bar_off + beat, 4),
                    "duration": dur,
                    "velocity": round(velocity * 0.65, 3),
                })

    # Create all notes in batches
    drum_result = await mcp_opendaw_create_notes_batch(
        json.dumps(drum_notes), unit_index, drum_track)
    bass_result = await mcp_opendaw_create_notes_batch(
        json.dumps(bass_notes), unit_index, bass_track)
    pad_result = await mcp_opendaw_create_notes_batch(
        json.dumps(pad_notes), unit_index, pad_track)
    lead_result = await mcp_opendaw_create_notes_batch(
        json.dumps(lead_notes), unit_index, lead_track)

    try:
        drum_data = json.loads(drum_result)
    except Exception:
        drum_data = {"raw": drum_result}
    try:
        bass_data = json.loads(bass_result)
    except Exception:
        bass_data = {"raw": bass_result}
    try:
        pad_data = json.loads(pad_result)
    except Exception:
        pad_data = {"raw": pad_result}
    try:
        lead_data = json.loads(lead_result)
    except Exception:
        lead_data = {"raw": lead_result}

    return json.dumps({
        "synthwave_arrangement": True,
        "bpm": bpm,
        "root": root,
        "bars": bars,
        "tracks": {
            "drums": {"track": drum_track, "notes": len(drum_notes), "result": drum_data.get("notes_created", len(drum_notes))},
            "bass": {"track": bass_track, "notes": len(bass_notes), "result": bass_data.get("notes_created", len(bass_notes))},
            "pad": {"track": pad_track, "notes": len(pad_notes), "result": pad_data.get("notes_created", len(pad_notes))},
            "lead": {"track": lead_track, "notes": len(lead_notes), "result": lead_data.get("notes_created", len(lead_notes))},
        },
        "total_notes": len(drum_notes) + len(bass_notes) + len(pad_notes) + len(lead_notes),
        "drum_pattern": "retro_four_on_floor_soft",
        "bass_pattern": "arpeggiated_16th_root_octave_fifth",
        "pad_type": "sustained_minor_chords_dreamy",
        "lead_type": "nostalgic_melody_echo_phrases",
        "harmony": "i_VI_III_VII_minor",
    }, indent=2)


async def mcp_opendaw_download_audio(url: str, filename: str = "", output_dir: str = "/tmp") -> str:
    """Download an audio file from a URL (e.g. Suno CDN) to local disk.

    Bridges the gap between AI music generators (Suno, Udio) and the DAW:
    generate a track → get audio URL → download → import_audio_to_tracks.
    Without this, you need manual curl/wget outside the MCP pipeline.

    Supports any HTTP(S) URL pointing to WAV/MP3/FLAC/OGG. Uses streaming
    download with timeout. Files saved to /tmp by default (or custom dir).

    url: Direct URL to the audio file (e.g. Suno CDN audio_url from chirp_generate).
    filename: Output filename (default: derived from URL path).
    output_dir: Directory to save (default /tmp). Must exist.

    Returns absolute file path, size, and suggested next step (import_audio_to_tracks).

    Examples:
      # Download a Suno track
      download_audio("https://cdn.suno.ai/abc123.wav")
      # Custom name
      download_audio("https://cdn.suno.ai/abc123.mp3", filename="my_track.mp3")
      # Then import with stem splitting
      import_audio_to_tracks("/tmp/my_track.mp3", mode="bs6")
    """
    import urllib.request
    import urllib.error

    if not url or not url.startswith(("http://", "https://")):
        return json.dumps({"error": "URL must start with http:// or https://"})

    # Derive filename from URL if not provided
    if not filename:
        url_path = url.split("?")[0].split("/")[-1]
        filename = url_path if url_path else "downloaded_audio.wav"
    # Sanitize filename
    filename = filename.replace("/", "_").replace("\\", "_").replace("..", "_")

    if not os.path.isdir(output_dir):
        return json.dumps({"error": f"Output directory does not exist: {output_dir}"})

    output_path = os.path.join(output_dir, filename)

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "opendaw-mcp/1.0"})
        with urllib.request.urlopen(req, timeout=60) as response:
            content_type = response.headers.get("Content-Type", "")
            total = 0
            with open(output_path, "wb") as f:
                while True:
                    chunk = response.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
                    total += len(chunk)

        file_size = os.path.getsize(output_path)
        return json.dumps({
            "downloaded": True,
            "url": url,
            "file_path": output_path,
            "filename": filename,
            "size_bytes": file_size,
            "size_mb": round(file_size / 1024 / 1024, 2),
            "content_type": content_type,
            "next_step": f"import_audio_to_tracks(\"{output_path}\", mode=\"bs6\")",
        }, indent=2)

    except urllib.error.HTTPError as e:
        return json.dumps({"error": f"HTTP {e.code}: {e.reason}", "url": url})
    except urllib.error.URLError as e:
        return json.dumps({"error": f"URL error: {e.reason}", "url": url})
    except Exception as e:
        return json.dumps({"error": str(e), "url": url})


async def mcp_opendaw_export_dawproject(filename: str = "project") -> str:
    """Export the current project as a .dawproject file (Bitwig/Ableton/rePitch compatible format).

    The dawproject format is a ZIP containing project.xml, metadata.xml, and audio samples.
    This enables interoperability with other DAWs that support the dawproject format.

    Args:
        filename: Output filename (without extension). The .dawproject extension is added automatically.

    Returns the file path of the exported .dawproject file.
    """
    safe_fn = filename.replace('"', '').replace('\\', '').replace("'", "").replace(';', '').replace('/', '').replace('..', '')
    export_dir = os.environ.get("OPENDAW_EXPORT_DIR", "/tmp/opendaw-exports")
    result = await bridge.evaluate("""async () => {
        const daw = window.DAW_DawProject;
        const project = window.DAW;
        if (!daw) return {error: "DawProject module not available"};
        if (!project) return {error: "No active project"};
        try {
            const skeleton = {
                boxGraph: project.boxGraph,
                mandatoryBoxes: window.DAW_ProjectSkeleton.findMandatoryBoxes(project.boxGraph)
            };
            const metaData = {application: {name: "openDAW-MCP", version: "1.6.2"}};
            const buffer = await daw.encode(skeleton, window.DAW_sampleManager, metaData);
            // Convert ArrayBuffer to base64 for transfer
            const bytes = new Uint8Array(buffer);
            const chunks = [];
            const cs = 0x8000;
            for (let ci = 0; ci < bytes.length; ci += cs) {
                chunks.push(String.fromCharCode.apply(null, bytes.subarray(ci, ci + cs)));
            }
            const base64 = btoa(chunks.join(""));
            return {
                success: true,
                base64: base64,
                size: bytes.length,
                format: "dawproject"
            };
        } catch(e) {
            return {error: e.message, stack: e.stack?.split('\\n').slice(0, 5).join(' | ')};
        }
    }""")
    r = _wrap_eval(result)
    if '"success": true' in r or '"success":true' in r:
        import base64 as b64mod
        try:
            data = json.loads(r)
            if data.get("success") and data.get("base64"):
                buf = b64mod.b64decode(data["base64"])
                os.makedirs(export_dir, exist_ok=True)
                filepath = os.path.join(export_dir, f"{safe_fn}.dawproject")
                with open(filepath, "wb") as f:
                    f.write(buf)
                return json.dumps({
                    "success": True,
                    "file": filepath,
                    "size": data["size"],
                    "format": "dawproject"
                })
        except Exception as e:
            return json.dumps({"error": str(e)})
    return r


async def mcp_opendaw_export_dry_stem(unit_index: int, filename: str, sample_rate: int = 48000) -> str:
    """Export a single audio unit as a DRY stem (instrument output, no effects/channel strip).

    Unlike export_single_stem (which routes through the channel strip with effects),
    this captures the raw instrument output before any audio effects, sends, or
    volume/pan processing. Useful for freezing, flattening, or re-amping workflows
    where you want the clean instrument signal to process externally.

    unit_index: Audio unit index to export (must be > 0, not the output AU).
    filename: Output filename (without .wav extension).
    sample_rate: Export sample rate (default 48000).

    Returns the path to the exported WAV and audio metadata.
    """
    safe_name = _safe_filename(filename)
    result_temp = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const units = h.allAUBoxes();
        if ({unit_index} >= units.length) return {{error: "No AU at index {unit_index}"}};
        const au = units[{unit_index}];
        return {{
            uuid: h.uuid.toString(au.address.uuid),
            name: au.name?.getValue?.() || 'Unit {unit_index}',
            type: au.type?.getValue?.() ?? 0,
        }};
    }}""")
    if isinstance(result_temp, dict) and "error" in result_temp:
        return _wrap_eval(result_temp)
    if not isinstance(result_temp, dict):
        return _err(f"Failed to get AU info for unit_index {unit_index}")
    stems_map = {
        result_temp['uuid']: {
            "includeAudioEffects": False,
            "includeSends": False,
            "useInstrumentOutput": True,
            "fileName": safe_name
        }
    }
    stems_js = json.dumps(stems_map)
    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const OfflineEngineRenderer = window.DAW_OfflineEngineRenderer;
        const Option = window.DAW_Option;
        const WavFile = window.DAW_WavFile;
        const stemsConfig = {stems_js};

        return new Promise(async (resolve) => {{
            try {{
                const exportConfig = {{stems: stemsConfig}};
                const progress = {{setValue: (v) => {{}}}};
                
                const audioData = await OfflineEngineRenderer.start(
                    h.project, Option.wrap(exportConfig), progress, undefined, {sample_rate}
                );

                const wav = WavFile.encodeFloats(audioData);
                const bytes = new Uint8Array(wav);
                const chunks = [];
            const chunkSize = 0x8000;
            for (let ci = 0; ci < bytes.length; ci += chunkSize) {{ 
                chunks.push(String.fromCharCode.apply(null, bytes.subarray(ci, ci + chunkSize)));
            }}
            const binary = chunks.join("");
                window.__lastExportB64 = btoa(binary);

                let maxSample = 0;
                for (let ch = 0; ch < audioData.frames.length; ch++) {{
                    const frame = audioData.frames[ch];
                    for (let i = 0; i < Math.min(frame.length, 50000); i++) {{
                        maxSample = Math.max(maxSample, Math.abs(frame[i]));
                    }}
                }}

                resolve({{
                    success: true,
                    filename: "{safe_name}.wav",
                    max_sample: maxSample,
                    sample_rate: audioData.sampleRate,
                    channels: audioData.frames.length,
                    duration_seconds: audioData.frames[0].length / audioData.sampleRate,
                    size_bytes: wav.byteLength,
                    dry: true,
                }});
            }} catch(e) {{
                resolve({{error: e.message, stack: e.stack?.slice(0, 400)}});
            }}
        }});
    }}""", timeout=1200000)
    if isinstance(result, dict) and result.get("success"):
        import base64 as b64mod
        export_dir = os.environ.get("OPENDAW_EXPORT_DIR", os.path.join(os.path.dirname(__file__), "exports"))
        os.makedirs(export_dir, exist_ok=True)
        b64 = await bridge.evaluate("() => window.__lastExportB64")
        if isinstance(b64, str) and b64:
            wav_bytes = b64mod.b64decode(b64)
            filepath = os.path.join(export_dir, f"{safe_name}.wav")
            with open(filepath, "wb") as f:
                f.write(wav_bytes)
            result["filepath"] = filepath
            result["file_size_mb"] = round(os.path.getsize(filepath) / (1024*1024), 2)
    return _wrap_eval(result)


async def mcp_opendaw_export_for_platform(
    platform: str = "spotify",
    filename: str = "",
    parent_id: str = "",
    dry_run: bool = False,
    output_name: str = "",
) -> str:
    """Platform bounce: LUFS + true-peak ceiling + optional lineage edge.

    File-only post-master path — no DAW bridge required (dry-run or real export).
    Platforms: spotify(-14/-1), apple(-16/-1), youtube(-14/-1), tidal(-14/-1),
    soundcloud(-14/-1), club(-9/-0.3 dBTP).

    Pipeline:
      1. load WAV from OPENDAW_EXPORT_DIR or absolute path
      2. gain toward platform LUFS
      3. soft-clip to platform TP ceiling
      4. measure + fail if TP exceeds ceiling
      5. write exports/<name>_<platform>.wav
      6. record_lineage(kind=export, op=export)

    platform: spotify | apple | youtube | tidal | soundcloud | club
    filename: input WAV name in exports/ or absolute path
    parent_id: lineage parent node (empty = root export node still recorded)
    dry_run: plan only — no write, no lineage
    output_name: optional basename (without .wav); default <input>_<platform>

    Example:
      export_for_platform(platform="spotify", filename="mix.wav", dry_run=True)
      export_for_platform(platform="apple", filename="mix.wav", parent_id="n_xxx")
    """
    import json as _json
    from opendaw_mcp.smart_export import export_for_platform as _export

    if not filename:
        return _err("filename required", code="INVALID_PARAMETER",
                    hint="Pass a WAV in OPENDAW_EXPORT_DIR or absolute path")
    result = _export(
        platform=platform or "spotify",
        filename=filename,
        parent_id=parent_id or "",
        dry_run=bool(dry_run),
        output_name=output_name or "",
    )
    return _json.dumps(result, indent=2)


# === MCP Tasks: long-ops API (OPENDAW_MCP_TASKS=1) ===

_TASKS_ENABLED = os.environ.get("OPENDAW_MCP_TASKS", "0") == "1"

if _TASKS_ENABLED:
    from opendaw_mcp.tasks import create_task, run_task, get_task, cancel_task, list_tasks

    @mcp.tool(annotations=ToolAnnotations(read_only_hint=True))
    async def mcp_opendaw_task_get(task_id: str) -> str:
        """Poll the status of a long-running task (render, stems).

        Returns: { id, tool, status, progress, result, error, elapsed_s }
        status: pending → running → completed | failed | cancelled
        """
        try:
            return json.dumps(get_task(task_id), indent=2)
        except KeyError:
            return json.dumps({"error": f"Unknown task: {task_id}"})

    @mcp.tool(annotations=ToolAnnotations(read_only_hint=True))
    async def mcp_opendaw_task_list() -> str:
        """List all tasks (most recent first).

        Returns: [{ id, tool, status, progress }, ...]
        """
        return json.dumps(list_tasks(), indent=2)

    @mcp.tool(annotations=ToolAnnotations(destructive_hint=True))
    async def mcp_opendaw_task_cancel(task_id: str) -> str:
        """Request cancellation of a running task.

        Only affects pending or running tasks.
        Returns: { cancelled: true|false }
        """
        return json.dumps({"cancelled": cancel_task(task_id)})

    @mcp.tool(annotations=ToolAnnotations(destructive_hint=True))
    async def mcp_opendaw_task_render_full(filename: str = "full_mix", sample_rate: int = 48000) -> str:
        """Start async render of the full project mix.

        Returns task_id immediately. Poll with task_get.
        This is the non-blocking version of render_full.
        """
        task_id = create_task("render_full", {"filename": filename, "sample_rate": sample_rate})

        async def _do_render(cb):
            cb(0.1)
            result = await mcp_opendaw_render_full(filename, sample_rate)
            cb(1.0)
            return json.loads(result)

        asyncio.create_task(run_task(task_id, _do_render))
        return json.dumps({"task_id": task_id, "status": "pending", "poll": f"task_get(task_id=\"{task_id}\")"})


async def mcp_opendaw_export_mix(filename: str, sample_rate: int = 48000, method: str = "offline") -> str:
    """Render the full project mix to a WAV file.

    Uses OfflineEngineRenderer (same as render_full).
    The 'method' parameter is accepted for backward compatibility but
    always uses offline rendering (faster, no engine needed).

    filename: Output filename (without .wav extension).
    sample_rate: Export sample rate (default 48000).
    method: 'offline' (default), 'realtime', or 'auto' — all use offline.

    Returns the path to the exported WAV and audio metadata.
    """
    return await mcp_opendaw_render_full(filename, sample_rate)


async def mcp_opendaw_export_preset(unit_index: int, include_timeline: bool = False) -> str:
    """Export an audio unit as a preset (base64-encoded binary).

Uses PresetEncoder.encode — serializes the AU with all dependencies (instrument, effects,
MIDI effects, optionally tracks/regions/notes) into a binary preset format.
Output is base64-encoded for transport over JSON.

unit_index: AU index to export (must be an instrument, not Output).
include_timeline: If true, include tracks/regions/notes in the preset.

Returns base64-encoded preset bytes and metadata, or error.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const PresetEncoder = window.DAW_PresetEncoder;
        if (!PresetEncoder) return {{error: "PresetEncoder not loaded"}};
        const units = h.allAUBoxes();
        if ({unit_index} >= units.length) return {{error: "No AU at {unit_index}"}};
        const srcAU = units[{unit_index}];
        if (srcAU.type.getValue() === "output") return {{error: "Cannot export Output unit"}};

        const buffer = PresetEncoder.encode(srcAU, {{includeTimeline: {str(include_timeline).lower()}}});
        // Convert ArrayBuffer to base64
        const bytes = new Uint8Array(buffer);
        const chunks = [];
            const chunkSize = 0x8000;
            for (let ci = 0; ci < bytes.length; ci += chunkSize) {{
                chunks.push(String.fromCharCode.apply(null, bytes.subarray(ci, ci + chunkSize)));
            }}
            const binary = chunks.join("");
        const base64 = btoa(binary);
        return {{
            success: true,
            preset_b64: base64,
            size_bytes: bytes.length,
            unit_type: srcAU.type.getValue(),
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_export_single_stem(unit_index: int, filename: str, sample_rate: int) -> str:
    """Export a single audio unit as a stem WAV with its effect chain applied.

Unlike export_stems (which exports ALL stems in one pass), this exports
just one AU — faster when you only need a specific stem.

unit_index: Audio unit index to export (must be > 0, not the output AU).
filename: Output filename.
sample_rate: Export sample rate.

The stem includes all effects on that AU's chain (EQ, compression, reverb, etc).
"""
    safe_name = _safe_filename(filename)
    # Build per-AU stem config — ExportConfiguration.stems is Record<uuid, ExportStemConfiguration>
    result_temp = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const units = h.allAUBoxes();
        if ({unit_index} >= units.length) return {{error: "No AU at index {unit_index}"}};
        const au = units[{unit_index}];
        return {{
            uuid: h.uuid.toString(au.address.uuid),
            name: au.name?.getValue?.() || 'Unit {unit_index}',
            type: au.type?.getValue?.() ?? 0,
        }};
    }}""")
    if isinstance(result_temp, dict) and "error" in result_temp:
        return _wrap_eval(result_temp)
    if not isinstance(result_temp, dict):
        return _err(f"Failed to get AU info for unit_index {unit_index}")
    stems_map = {
        result_temp['uuid']: {
            "includeAudioEffects": True,
            "includeSends": True,
            "useInstrumentOutput": False,
            "fileName": safe_name
        }
    }
    stems_js = json.dumps(stems_map)
    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const OfflineEngineRenderer = window.DAW_OfflineEngineRenderer;
        const Option = window.DAW_Option;
        const WavFile = window.DAW_WavFile;
        const stemsConfig = {stems_js};

        return new Promise(async (resolve) => {{
            try {{
                const exportConfig = {{stems: stemsConfig}};
                const progress = {{setValue: (v) => {{}}}};
                
                const audioData = await OfflineEngineRenderer.start(
                    h.project, Option.wrap(exportConfig), progress, undefined, {sample_rate}
                );

                const wav = WavFile.encodeFloats(audioData);
                const bytes = new Uint8Array(wav);
                const chunks = [];
            const chunkSize = 0x8000;
            for (let ci = 0; ci < bytes.length; ci += chunkSize) {{ 
                chunks.push(String.fromCharCode.apply(null, bytes.subarray(ci, ci + chunkSize)));
            }}
            const binary = chunks.join("");
                window.__lastExportB64 = btoa(binary);

                let maxSample = 0;
                for (let ch = 0; ch < audioData.frames.length; ch++) {{
                    const frame = audioData.frames[ch];
                    for (let i = 0; i < Math.min(frame.length, 50000); i++) {{
                        maxSample = Math.max(maxSample, Math.abs(frame[i]));
                    }}
                }}

                resolve({{
                    success: true,
                    filename: "{safe_name}.wav",
                    max_sample: maxSample,
                    sample_rate: audioData.sampleRate,
                    channels: audioData.frames.length,
                    duration_seconds: audioData.frames[0].length / audioData.sampleRate,
                    size_bytes: wav.byteLength,
                }});
            }} catch(e) {{
                resolve({{error: e.message, stack: e.stack?.slice(0, 400)}});
            }}
        }});
    }}""", timeout=1200000)
    # Save WAV file if export succeeded
    if isinstance(result, dict) and result.get("success"):
        import base64 as b64mod
        export_dir = os.environ.get("OPENDAW_EXPORT_DIR", os.path.join(os.path.dirname(__file__), "exports"))
        os.makedirs(export_dir, exist_ok=True)
        b64 = await bridge.evaluate("() => window.__lastExportB64")
        if isinstance(b64, str) and b64:
            wav_bytes = b64mod.b64decode(b64)
            filepath = os.path.join(export_dir, f"{safe_name}.wav")
            with open(filepath, "wb") as f:
                f.write(wav_bytes)
            result["filepath"] = filepath
            result["file_size_mb"] = round(os.path.getsize(filepath) / (1024*1024), 2)
    return _wrap_eval(result)


async def mcp_opendaw_export_stems(filename_prefix: str, sample_rate: int) -> str:
    """Export each audio unit as a separate stem WAV file.

Uses OfflineEngineRenderer with per-AU ExportConfiguration.
Each instrument AU gets its own stem with effects included.
Returns list of exported stem files.

Workflow: create_instrument_track(s) → load_audio → place_audio_region(s) →
          add_effect(s) → export_stems
"""
    # Build stems config — ExportConfiguration.stems is Record<uuid, ExportStemConfiguration>
    result_temp = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        const units = h.allAUBoxes();
        return units.map((au, i) => ({
            index: i,
            uuid: h.uuid.toString(au.address.uuid),
            name: au.name?.getValue?.() || 'Unit ' + i,
            type: au.type?.getValue?.() ?? 0,
        }));
    }""")
    stems_map = {}
    if isinstance(result_temp, list):
        for u in result_temp:
            if u.get('type') == 1 or u.get('type') == 'instrument':
                stems_map[u['uuid']] = {
                    "includeAudioEffects": True,
                    "includeSends": True,
                    "useInstrumentOutput": False,
                    "fileName": u.get('name', f"stem_{u['index']}")
                }
    stems_js = json.dumps(stems_map)
    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const OfflineEngineRenderer = window.DAW_OfflineEngineRenderer;
        const Option = window.DAW_Option;
        const WavFile = window.DAW_WavFile;
        const stemsConfig = {stems_js};

        return new Promise(async (resolve) => {{
            try {{
                const exportConfig = {{stems: stemsConfig}};
                const progress = {{setValue: (v) => {{}}}};
                
                const audioData = await OfflineEngineRenderer.start(
                    h.project, Option.wrap(exportConfig), progress, undefined, {sample_rate}
                );

                const wav = WavFile.encodeFloats(audioData);
                const bytes = new Uint8Array(wav);
                const chunks = [];
            const chunkSize = 0x8000;
            for (let ci = 0; ci < bytes.length; ci += chunkSize) {{ 
                chunks.push(String.fromCharCode.apply(null, bytes.subarray(ci, ci + chunkSize)));
            }}
            const binary = chunks.join("");
                window.__lastExportB64 = btoa(binary);

                let maxSample = 0;
                for (let ch = 0; ch < audioData.frames.length; ch++) {{
                    const frame = audioData.frames[ch];
                    for (let i = 0; i < Math.min(frame.length, 50000); i++) {{
                        maxSample = Math.max(maxSample, Math.abs(frame[i]));
                    }}
                }}

                resolve({{
                    success: true,
                    frames: audioData.frames.length,
                    samples: audioData.frames[0].length,
                    max_sample: maxSample,
                    size: wav.byteLength,
                    sample_rate: audioData.sampleRate,
                    num_stems: Object.keys(stemsConfig).length,
                }});
            }} catch(e) {{
                resolve({{error: e.message, stack: e.stack?.slice(0, 400)}});
            }}
        }});
    }}""", timeout=1200000)
    # Save WAV file if export succeeded
    if isinstance(result, dict) and result.get("success"):
        import base64 as b64mod
        export_dir = os.environ.get("OPENDAW_EXPORT_DIR", os.path.join(os.path.dirname(__file__), "exports"))
        os.makedirs(export_dir, exist_ok=True)
        b64 = await bridge.evaluate("() => window.__lastExportB64")
        if isinstance(b64, str) and b64:
            wav_bytes = b64mod.b64decode(b64)
            safe_prefix = _safe_filename(filename_prefix)
            filepath = os.path.join(export_dir, f"{safe_prefix}_stems.wav")
            with open(filepath, "wb") as f:
                f.write(wav_bytes)
            result["filepath"] = filepath
            result["file_size_mb"] = round(os.path.getsize(filepath) / (1024*1024), 2)
    return _wrap_eval(result)


async def mcp_opendaw_export_stems_format(filename_prefix: str, sample_rate: int, format: str = "wav", bitrate: str = "320k") -> str:
    """Export stems as separate files and convert each to MP3 or FLAC.

    filename_prefix: Prefix for stem filenames.
    sample_rate: Export sample rate.
    format: 'wav' (default), 'mp3', or 'flac'.
    bitrate: MP3 bitrate (default '320k').

    Runs export_stems, then converts each stem WAV to the requested format via ffmpeg.
    """
    # First export stems as WAV
    wav_result = await mcp_opendaw_export_stems(filename_prefix, sample_rate)
    wav_data = _unwrap_eval(wav_result)
    if isinstance(wav_data, dict) and wav_data.get("error"):
        return wav_result
    fmt = format.lower().strip().replace('"', '').replace("'", "")
    if fmt == "wav":
        return wav_result
    # Convert each stem
    stems = wav_data.get("stems", []) if isinstance(wav_data, dict) else []
    converted = []
    for stem in stems:
        if isinstance(stem, dict) and stem.get("filename"):
            stem_name = stem["filename"].replace(".wav", "")
            conv = await mcp_opendaw_convert_audio(stem_name, fmt, bitrate, -1)
            conv_data = _unwrap_eval(conv)
            if isinstance(conv_data, dict) and conv_data.get("success"):
                converted.append({
                    "stem": stem_name,
                    "output": conv_data.get("output"),
                    "size_mb": conv_data.get("output_size_mb"),
                })
    return _wrap_eval({
        "format": fmt,
        "stems_wav": stems,
        "stems_converted": converted,
        "total_converted": len(converted),
    })


async def mcp_opendaw_load_audio(file_path: str, name: str) -> str:
    """Load an audio file (WAV/MP3/FLAC/OGG) into the DAW project.

file_path: Absolute path to the audio file on disk. If the file is inside
           the headless-daw/public/ directory, it will be fetched via URL
           (much faster for large files). Otherwise loaded via base64.
name: Optional display name (defaults to filename).
"""
    fname = name.replace('"', '').replace("'", "").replace('\\', '')
    # Read file and encode as base64
    import base64 as b64mod
    with open(file_path, 'rb') as f:
        audio_b64 = b64mod.b64encode(f.read()).decode('ascii')
    result = await bridge.evaluate(f"""() => {{
        return new Promise(async (resolve) => {{
            try {{
                const b64 = "{audio_b64}";
                const binary = atob(b64);
                const bytes = new Uint8Array(binary.length);
                for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);

                const audioCtx = window.DAW_audioContext;
                const audioBuffer = await audioCtx.decodeAudioData(bytes.buffer);

                const id = window.DAW_UUID.generate();
                const idStr = window.DAW_UUID.toString(id);
                window.DAW_localAudioBuffers.set(id, audioBuffer);
                window.DAW_localAudioBuffers.set(idStr, audioBuffer);
                window.DAW_fileNameToAudioBuffer.set(idStr, audioBuffer);

                resolve({{
                    success: true,
                    id: idStr,
                    name: "{fname}",
                    duration: audioBuffer.duration,
                    sample_rate: audioBuffer.sampleRate,
                    channels: audioBuffer.numberOfChannels,
                    size_bytes: bytes.length,
                }});
            }} catch(e) {{
                resolve({{error: e.message, stack: e.stack?.slice(0, 300)}});
            }}
        }});
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_measure_lufs(filename: str) -> str:
    """Measure LUFS (integrated) and true peak of an exported WAV file.

    Uses ITU-R BS.1770-4 simplified algorithm:
    - K-weighting: 2nd-order high-shelf (+4dB @ ~1.5kHz) + highpass (~38Hz)
    - Gated mean squares (400ms blocks, 75% overlap, -10 LU relative gate)
    - Integrated LUFS = -0.691 + 10*log10(gated mean square)

    filename: Name of the WAV file in the exports directory (without path).

    Returns: LUFS (integrated), true peak (dBTP), max sample, duration seconds.
    """
    import os as _os

    export_dir = _os.environ.get("OPENDAW_EXPORT_DIR",
                                  _os.path.join(_os.path.dirname(__file__), "exports"))
    filepath = _os.path.join(export_dir, filename if filename.endswith(".wav") else filename + ".wav")

    if not _os.path.exists(filepath):
        return _err(f"File not found: {filepath}")

    try:
        with open(filepath, "rb") as f:
            raw = f.read()
        wav = _parse_wav(raw)
        lufs_data = _compute_lufs(wav["channels"], wav["sample_rate"])
        return json.dumps({
            "success": True,
            **lufs_data,
            "duration_seconds": round(wav["n_frames"] / wav["sample_rate"], 2),
            "sample_rate": wav["sample_rate"],
            "channels": wav["n_channels"],
        })
    except Exception as e:
        return _err(f"LUFS measurement error: {e}")


async def mcp_opendaw_render_and_analyze(
    filename: str = "render_analysis",
    sample_rate: int = 48000,
    analysis_depth: str = "full",
) -> str:
    """Render the current project and run full audio analysis in one call.

    Combines export_audio + analyze_mix into a single tool — the feedback loop
    for iterative mixing. Agent renders, listens, and gets concrete numbers:
    LUFS, spectrum, stereo, dynamics, and prioritized suggestions.

    This is the 'ears' tool. After making mix changes, call this to verify:
    1. Renders project to WAV via offline engine
    2. Runs full mix analysis (LUFS, spectrum, stereo, dynamics)
    3. Returns concrete numbers + prioritized suggestions

    filename: Output filename (without .wav extension).
    sample_rate: Render sample rate (48000 recommended).
    analysis_depth: "full" (all analyses) or "quick" (LUFS + spectrum only).

    Returns analysis JSON with mix_suggestions, master_check, and file path.

    Example:
      # After adjusting mix
      result = render_and_analyze("my_mix")
      # → {lufs: -14.2, spectrum: {...}, suggestions: [...], file: "..."}
    """
    # Step 1: Render
    try:
        render_result = await mcp_opendaw_render_full(filename, sample_rate)
        render_data = json.loads(render_result)
        if not render_data.get("success"):
            return json.dumps({"error": "Render failed", "details": render_result})
    except Exception as e:
        return _err(f"Render error: {e}")

    # Step 2: Analyze
    wav_name = filename if filename.endswith(".wav") else filename + ".wav"
    try:
        if analysis_depth == "quick":
            analysis = await mcp_opendaw_measure_lufs(wav_name)
            spec = await mcp_opendaw_analyze_spectrum(wav_name)
            return json.dumps({
                "success": True,
                "render_file": wav_name,
                "lufs": json.loads(analysis),
                "spectrum": json.loads(spec),
            }, indent=2)
        else:
            analysis = await mcp_opendaw_analyze_mix(wav_name)
            return analysis
    except Exception as e:
        return _err(f"Analysis error: {e}")


async def mcp_opendaw_render_full(filename: str = "full_mix", sample_rate: int = 48000) -> str:
    """Render the entire project as a single stereo WAV file (full mixdown).

    filename: Output filename (without .wav extension).
    sample_rate: Export sample rate (default 48000).

    Uses OfflineEngineRenderer with Option.None (no stems config = full mix).
    Renders from beat 0 to the end of the last region.

    Returns the path to the exported WAV and audio metadata.
    """
    safe_name = _safe_filename(filename)
    # Render timeout: 1200s (20 min). Default bridge timeout is 30s, which kills
    # any non-trivial render. A 272s song with 7 stems in a Web Worker takes real
    # time. The worker does 12M+ sample operations. Headroom prevents premature kill.
    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const OfflineEngineRenderer = window.DAW_OfflineEngineRenderer;
        const Option = window.DAW_Option;
        const WavFile = window.DAW_WavFile;

        return new Promise(async (resolve) => {{
            try {{
                // Option.None = no stems config → full mix (1 stem, all AUs mixed)
                const progress = {{setValue: (v) => {{}}}};
                console.time("project.copy");
                // project.copy() is required — without it, OfflineEngineRenderer
                // fails with "Already connected" because the live engine's
                // AudioWorkletNode is already connected to the live AudioContext.
                const projectCopy = h.project.copy();
                console.timeEnd("project.copy");
                console.time("render");
                const audioData = await OfflineEngineRenderer.start(
                    projectCopy, Option.None, progress, undefined, {sample_rate}
                );
                console.timeEnd("render");
                console.time("encode");
                const wav = WavFile.encodeFloats(audioData);
                const bytes = new Uint8Array(wav);
                const chunks = [];
            const chunkSize = 0x8000;
            for (let ci = 0; ci < bytes.length; ci += chunkSize) {{ 
                chunks.push(String.fromCharCode.apply(null, bytes.subarray(ci, ci + chunkSize)));
            }}
            const binary = chunks.join("");
                console.timeEnd("encode");
                window.__lastExportB64 = btoa(binary);

                let maxSample = 0;
                for (let ch = 0; ch < audioData.frames.length; ch++) {{
                    const frame = audioData.frames[ch];
                    for (let i = 0; i < Math.min(frame.length, 100000); i++) {{
                        maxSample = Math.max(maxSample, Math.abs(frame[i]));
                    }}
                }}

                resolve({{
                    success: true,
                    filename: "{safe_name}.wav",
                    frames: audioData.frames.length,
                    samples: audioData.frames[0]?.length || 0,
                    max_sample: maxSample,
                    has_audio: maxSample > 0.001,
                    size: wav.byteLength,
                    sample_rate: audioData.sampleRate,
                }});
            }} catch(e) {{
                resolve({{error: e.message, stack: e.stack?.slice(0, 400)}});
            }}
        }});
    }}""", timeout=1200000)
    # Save WAV file if export succeeded
    if isinstance(result, dict) and result.get("success"):
        import base64 as b64mod
        export_dir = os.environ.get("OPENDAW_EXPORT_DIR", os.path.join(os.path.dirname(__file__), "exports"))
        os.makedirs(export_dir, exist_ok=True)
        b64 = await bridge.evaluate("() => window.__lastExportB64")
        if isinstance(b64, str) and b64:
            wav_bytes = b64mod.b64decode(b64)
            filepath = os.path.join(export_dir, f"{safe_name}.wav")
            with open(filepath, "wb") as f:
                f.write(wav_bytes)
            result["filepath"] = filepath
            result["file_size_mb"] = round(os.path.getsize(filepath) / (1024*1024), 2)
    return _wrap_eval(result)


async def mcp_opendaw_render_full_format(filename: str = "full_mix", sample_rate: int = 48000, format: str = "wav", bitrate: str = "320k") -> str:
    """Render the entire project and convert to MP3 or FLAC in one step.

    filename: Output filename (without extension).
    sample_rate: Export sample rate (default 48000).
    format: 'wav' (default), 'mp3', or 'flac'. MP3/FLAC uses system ffmpeg.
    bitrate: MP3 bitrate for CBR (default '320k'). Ignored for WAV/FLAC.

    Combines render_full + convert_audio. Returns both WAV and converted file paths.
    """
    # First render to WAV
    wav_result = await mcp_opendaw_render_full(filename, sample_rate)
    if "error" in str(wav_result).lower() and "success" not in str(wav_result).lower():
        return wav_result
    fmt = format.lower().strip().replace('"', '').replace("'", "")
    if fmt == "wav":
        return wav_result
    # Then convert
    conv_result = await mcp_opendaw_convert_audio(filename, fmt, bitrate, -1)
    return _wrap_eval({
        "render": _unwrap_eval(wav_result),
        "conversion": _unwrap_eval(conv_result),
        "format": fmt,
        "filename": f"{filename}.{fmt if fmt != 'wav' else 'wav'}",
    })


async def mcp_opendaw_render_full_song(
    filename: str = "full_song",
    sample_rate: int = 48000,
    tail_beats: int = 4,
) -> str:
    """Render the entire project — auto-detects song length from all regions.

    Scans all note and audio regions across all tracks to find the latest
    ending point, then renders from beat 0 to that point plus a configurable
    tail for reverb/delay tails. No manual beat counting needed.

    This closes the pipeline gap: after create_song_with_variations (or any
    arrangement tool), call render_full_song to get the final WAV.

    filename: Output filename (without .wav extension).
    sample_rate: Export sample rate (default 48000).
    tail_beats: Extra beats at the end for reverb/delay tails (default 4 = 1 bar).

    Returns the path to the exported WAV, song duration in seconds, and
    audio metadata (peak, has_audio).

    Example:
      # After building a song
      create_song_with_variations("dnb")
      render_full_song(filename="my_dnb_track")

      # Shorter tail for tight electronic
      render_full_song(filename="techno_mix", tail_beats=2)
    """
    safe_name = _safe_filename(filename)

    # Phase 1: Find the latest region end across all tracks
    length_result = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        const Quarter = h.ppqn.Quarter;

        let maxEndPpq = 0;
        let maxEndBeat = 0;
        let regionCount = 0;
        let trackCount = 0;

        const allUnits = h.allAUBoxes();
        for (const au of allUnits) {
            const tracks = h.trackBoxes(au);
            trackCount += tracks.length;
            for (const track of tracks) {
                const regions = h.regionBoxes(track);
                for (const region of regions) {
                    try {
                        const rStart = region.position.getValue();
                        const rDur = region.duration.getValue();
                        const rEnd = rStart + rDur;
                        if (rEnd > maxEndPpq) maxEndPpq = rEnd;
                        regionCount++;
                    } catch(e) {}
                }
            }
        }

        // Also check audio regions
        for (const au of allUnits) {
            try {
                const audioRegions = h.audioRegionBoxes ? h.audioRegionBoxes(au) : [];
                for (const ar of audioRegions) {
                    try {
                        const aStart = ar.position.getValue();
                        const aDur = ar.duration.getValue();
                        const aEnd = aStart + aDur;
                        if (aEnd > maxEndPpq) maxEndPpq = aEnd;
                    } catch(e) {}
                }
            } catch(e) {}
        }

        maxEndBeat = Math.ceil(maxEndPpq / Quarter);
        return {
            max_end_beat: maxEndBeat,
            max_end_ppq: maxEndPpq,
            region_count: regionCount,
            track_count: trackCount,
        };
    }""")

    try:
        len_data = json.loads(length_result) if isinstance(length_result, str) else length_result
    except Exception:
        len_data = length_result if isinstance(length_result, dict) else {}

    if not isinstance(len_data, dict) or len_data.get("max_end_beat") is None:
        return json.dumps({"error": "Failed to detect song length", "raw": str(length_result)[:200]})

    max_end_beat = int(len_data.get("max_end_beat", 0))
    region_count = int(len_data.get("region_count", 0))
    track_count = int(len_data.get("track_count", 0))

    if max_end_beat <= 0:
        return json.dumps({"error": "No regions found — create an arrangement first"})

    # Add tail for reverb/delay
    total_beats = max_end_beat + tail_beats

    # Phase 2: Render from 0 to total_beats
    render_result = await mcp_opendaw_render_range(
        start_beat=0,
        end_beat=total_beats,
        filename=safe_name,
        sample_rate=sample_rate,
    )

    try:
        render_data = json.loads(render_result) if isinstance(render_result, str) else render_result
    except Exception:
        render_data = {"raw": str(render_result)[:200]}

    # Calculate duration
    _ = total_beats  # used in render

    return json.dumps({
        "render_full_song": True,
        "filename": f"{safe_name}.wav",
        "detected_length_beats": max_end_beat,
        "tail_beats": tail_beats,
        "total_beats": total_beats,
        "regions_scanned": region_count,
        "tracks_scanned": track_count,
        "render_result": render_data,
        "filepath": render_data.get("filepath") if isinstance(render_data, dict) else None,
        "file_size_mb": render_data.get("file_size_mb") if isinstance(render_data, dict) else None,
        "has_audio": render_data.get("has_audio") if isinstance(render_data, dict) else None,
        "max_sample": render_data.get("max_sample") if isinstance(render_data, dict) else None,
        "sample_rate": render_data.get("sample_rate", sample_rate) if isinstance(render_data, dict) else sample_rate,
        "next_step": "WAV file saved to exports directory. Use a media player or DAW to listen.",
    }, indent=2)


async def mcp_opendaw_render_range(start_beat: int, end_beat: int, filename: str, sample_rate: int = 48000) -> str:
    """Render only a portion of the project (e.g. chorus only) for quick A/B comparison.

start_beat: Start position in beats (0 = project start).
end_beat: End position in beats.
filename: Output filename (without .wav extension).
sample_rate: Export sample rate (default 48000).

Uses OfflineEngineRenderer with custom range. Faster than full export for
checking specific sections during mixing.

Returns the path to the exported WAV and audio metadata.
"""
    safe_name = _safe_filename(filename)
    # Render timeout: 1200s. Same rationale as render_full.
    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const OfflineEngineRenderer = window.DAW_OfflineEngineRenderer;
        const Option = window.DAW_Option;
        const WavFile = window.DAW_WavFile;

        const startPos = Math.round({start_beat} * h.ppqn.Quarter);
        const endPos = Math.round({end_beat} * h.ppqn.Quarter);

        return new Promise(async (resolve) => {{
            try {{
                // ExportConfiguration with range — no stems = full mix (1 stem)
                const exportConfig = {{
                    range: {{ start: startPos, end: endPos }}
                }};
                const progress = {{setValue: (v) => {{}}}};
                // No project.copy() — OfflineEngineRenderer.start() manages loopArea
                // internally and restores it. The worker gets its own snapshot via
                // source.toArrayBuffer() inside create(). Deep-copy was the bottleneck.
                const audioData = await OfflineEngineRenderer.start(
                    h.project, Option.wrap(exportConfig), progress, undefined, {sample_rate}
                );

                const wav = WavFile.encodeFloats(audioData);
                const bytes = new Uint8Array(wav);
                const chunks = [];
            const chunkSize = 0x8000;
            for (let ci = 0; ci < bytes.length; ci += chunkSize) {{ 
                chunks.push(String.fromCharCode.apply(null, bytes.subarray(ci, ci + chunkSize)));
            }}
            const binary = chunks.join("");
                window.__lastExportB64 = btoa(binary);

                let maxSample = 0;
                for (let ch = 0; ch < audioData.frames.length; ch++) {{
                    const frame = audioData.frames[ch];
                    for (let i = 0; i < Math.min(frame.length, 50000); i++) {{
                        maxSample = Math.max(maxSample, Math.abs(frame[i]));
                    }}
                }}

                resolve({{
                    success: true,
                    filename: "{safe_name}.wav",
                    frames: audioData.frames.length,
                    samples: audioData.frames[0]?.length || 0,
                    max_sample: maxSample,
                    has_audio: maxSample > 0.001,
                    size: wav.byteLength,
                    sample_rate: audioData.sampleRate,
                    range_beats: "{start_beat}-{end_beat}",
                }});
            }} catch(e) {{
                resolve({{error: e.message, stack: e.stack?.slice(0, 400)}});
            }}
        }});
    }}""", timeout=1200000)
    # Save WAV file if export succeeded
    if isinstance(result, dict) and result.get("success"):
        import base64 as b64mod
        export_dir = os.environ.get("OPENDAW_EXPORT_DIR", os.path.join(os.path.dirname(__file__), "exports"))
        os.makedirs(export_dir, exist_ok=True)
        b64 = await bridge.evaluate("() => window.__lastExportB64")
        if isinstance(b64, str) and b64:
            wav_bytes = b64mod.b64decode(b64)
            filepath = os.path.join(export_dir, f"{safe_name}.wav")
            with open(filepath, "wb") as f:
                f.write(wav_bytes)
            result["filepath"] = filepath
            result["file_size_mb"] = round(os.path.getsize(filepath) / (1024*1024), 2)
    return _wrap_eval(result)


async def mcp_opendaw_separate_stems(
    input_file: str,
    model: str = "bs6",
    output_dir: str = "",
) -> str:
    """Separate audio into stems using SOTA AI models — SCNet, BS-Roformer, PolarFormer.

    Uses the creative-studio stem-splitter pipeline (much better than Demucs alone).
    Models available:
    - "ensemble": Max quality — HTDemucs FT + PolarFormer vocals + BS-Roformer (3 passes)
    - "scnet": SCNet XL — best 4-stem (drums, bass, other, vocals), SDR 10.08
    - "bs6": BS-Roformer 6-stem (bass, drums, other, vocals, guitar, piano) — fast
    - "polarformer": Best vocal extraction (vocals + instrumental), SDR 11.00
    - "dereverb": Remove reverb from vocals (dry + reverb)
    - "drumsep": Separate drums into kick/snare/toms/cymbals
    - "denoise": Clean noise from low-quality audio (128kbps MP3)

    input_file: Path to audio file (absolute or relative to cwd).
    model: Model name from the list above.
    output_dir: Output directory (default: /tmp/stems).

    Returns paths to separated stem files.

    Example:
      separate_stems("suno_track.wav", model="bs6")
      # → {stems: {bass: "...", drums: "...", vocals: "...", ...}}
    """
    import subprocess as _sp
    import os as _os

    splitter = _os.environ.get("SOTA_SPLITTER_PATH", "sota_splitter.py")
    if not _os.path.exists(splitter):
        return _err(f"Stem splitter not found at {splitter}")

    if not _os.path.isabs(input_file):
        input_file = _os.path.join(_os.getcwd(), input_file)
    if not _os.path.exists(input_file):
        return _err(f"Input file not found: {input_file}")

    out = output_dir or "/tmp/stems"
    _os.makedirs(out, exist_ok=True)

    try:
        result = _sp.run(
            ["python3", splitter, input_file, "-m", model, "-o", out],
            capture_output=True, text=True, timeout=600,
        )
        if result.returncode != 0:
            return _err(f"Separation failed: {result.stderr[-500:]}")

        # List output stems
        stems = {}
        for f in sorted(_os.listdir(out)):
            if f.endswith(".wav"):
                stems[f.replace(".wav", "")] = _os.path.join(out, f)

        return json.dumps({
            "success": True,
            "model": model,
            "input": input_file,
            "output_dir": out,
            "stems": stems,
            "stem_count": len(stems),
            "stderr_tail": result.stderr[-200:] if result.stderr else "",
        }, indent=2)
    except _sp.TimeoutExpired:
        return _err("Separation timed out (600s limit)")
    except Exception as e:
        return _err(f"Separation error: {e}")


# ═══════════════════════════════════════════════════════════════════
# GENRE PROFILES + REFERENCE COMPARISON
# ═══════════════════════════════════════════════════════════════════


async def mcp_opendaw_split_stems(input_path: str, mode: str = "bs6", output_dir: str = "", import_to_daw: bool = False) -> str:
    """Split an audio file into stems using SOTA open-source separation models.

    Runs locally on GPU (GTX 1650 4GB, ~4.5 min for 4-min track).
    All models trained at 44100Hz — auto-resampling handled internally.

    input_path: Absolute path to input audio file (WAV/MP3/FLAC/OGG).
    mode: Separation mode (default "bs6"):
        - "ensemble": Max quality, 4 passes (bass/drums/vocals/other). Slowest, best SDR.
        - "scnet": 4-stem (drums/bass/other/vocals). Best single-pass multi-stem.
        - "bs6": 6-stem (bass/drums/other/vocals/guitar/piano). Fast, low bleeding.
        - "polarformer": Vocal extraction only (vocals/instrumental).
        - "dereverb": Remove reverb from vocals (dry/reverb).
        - "drumsep": Drum separation (kick/snare/cymbals/toms).
        - "denoise": Noise cleanup for low-quality sources (clean/noise).
    output_dir: Directory for stem files (default: /tmp/stems_<input_basename>).
    import_to_daw: If True, load each stem into the DAW and return sample IDs
                   for use with place_audio_region. Requires DAW bridge running.

    Returns list of stem file paths (and sample IDs if import_to_daw=True).

    Workflow:
      split_stems("track.wav", "bs6") → 6 stem WAVs
      split_stems("track.wav", "ensemble", import_to_daw=True) → 4 stems loaded into DAW
    """
    import asyncio

    if not os.path.exists(input_path):
        return json.dumps({"error": f"Input not found: {input_path}"})
    if mode not in STEM_MODES:
        return json.dumps({"error": f"Unknown mode: {mode}. Available: {list(STEM_MODES.keys())}"})
    if not os.path.exists(STEM_SPLITTER_SCRIPT):
        return json.dumps({"error": f"Stem splitter not found at {STEM_SPLITTER_SCRIPT}. Set STEM_SPLITTER_DIR env var."})
    if not os.path.exists(STEM_SPLITTER_VENV):
        return json.dumps({"error": f"venv not found at {STEM_SPLITTER_VENV}"})

    if not output_dir:
        base = os.path.splitext(os.path.basename(input_path))[0]
        output_dir = f"/tmp/stems_{base}"

    cmd = [STEM_SPLITTER_VENV, STEM_SPLITTER_SCRIPT, input_path, "-o", output_dir, "-m", mode, "-d", "cuda"]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await proc.communicate()
        output_text = stdout.decode("utf-8", errors="replace") if stdout else ""

        if proc.returncode != 0:
            return json.dumps({
                "error": "Stem splitter failed",
                "returncode": proc.returncode,
                "output": output_text[-500:],
            })

        # Collect stem files
        stems = []
        for fname in sorted(os.listdir(output_dir)):
            if fname.endswith(".wav"):
                fpath = os.path.join(output_dir, fname)
                stems.append({
                    "name": os.path.splitext(fname)[0],
                    "path": fpath,
                    "size_mb": round(os.path.getsize(fpath) / 1024 / 1024, 1),
                })

        result = {
            "success": True,
            "mode": mode,
            "mode_desc": STEM_MODES[mode],
            "input": input_path,
            "output_dir": output_dir,
            "stems": stems,
            "stem_count": len(stems),
        }

        # Optionally import each stem into DAW
        if import_to_daw and stems:
            imported = []
            for stem in stems:
                load_result = await mcp_opendaw_load_audio(stem["path"], stem["name"])
                load_data = json.loads(load_result)
                if "id" in load_data:
                    imported.append({
                        "name": stem["name"],
                        "sample_id": load_data["id"],
                        "duration": load_data.get("duration", 0),
                    })
                else:
                    imported.append({
                        "name": stem["name"],
                        "error": load_data.get("error", "load failed"),
                    })
            result["imported"] = imported

        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})

