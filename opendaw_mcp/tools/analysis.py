"""
Audio Analysis Tools
==============
"""

import json
import asyncio

# These will be injected by server.py
bridge = None
_wrap_eval = None
_ok = None
_err = None


def init_analysis_tools(bridge_instance, wrap_eval_func, ok_func=None, err_func=None):
    """Initialize analysis tools with shared dependencies."""
    global bridge, _wrap_eval, _ok, _err
    bridge = bridge_instance
    _wrap_eval = wrap_eval_func
    _ok = ok_func
    _err = err_func



async def mcp_opendaw_create_progression_from_key(key: str, mode: str = "major", style: str = "pop", unit_index: int = 0, track_index: int = 0, start_beat: float = 0, chord_duration: float = 4) -> str:
    """Auto-generate a diatonic chord progression from a detected key — no manual chord typing.

    Takes key + mode (from detect_key output) and generates a genre-appropriate
    diatonic progression using scale degrees. Eliminates the need to manually
    write [["Am","min"],["F","maj"]...] — just pass key="A", mode="minor".

    key: Root note name (C, C#, D, D#, E, F, F#, G, G#, A, A#, B).
    mode: "major" or "minor" (natural minor scale).
    style: Progression style:
      - "pop" — I-V-vi-IV (major) / i-VI-III-VII (minor) — "four chords of pop"
      - "jazz" — ii-V-I (major) / ii-V-i (minor) — jazz turnaround
      - "rock" — I-IV-V (major) / i-iv-V (minor) — blues/rock
      - "synthwave" — i-VI-III-VII (minor) — synthwave/emotional
      - "folk" — I-IV-vi-V (major) / i-iv-VII-III (minor) — folk/americana
      - "lofi" — ii-V-i (minor) or I-vi-IV-V (major) — lofi/jazzy
    unit_index: AU index with a note track.
    track_index: Note track index within the AU.
    start_beat: Where the progression starts (0 = bar 1).
    chord_duration: Length of each chord in beats (4 = one bar at 4/4).

    Returns: notes_created, chords, voicings, progression (chord names), key, mode.

    Pipeline: detect_key("track.wav") → {key: "A", mode: "minor"} →
              create_progression_from_key("A", "minor", "synthwave") →
              create_harmonic_arrangement("Am-F-C-G")
    """
    if key not in NOTE_TO_PITCH:
        return f"Error: unknown key '{key}'. Valid: {list(NOTE_TO_PITCH.keys())}"
    if mode not in ("major", "minor"):
        return "Error: mode must be 'major' or 'minor'"
    if style not in ("pop", "jazz", "rock", "synthwave", "folk", "lofi"):
        return "Error: style must be pop, jazz, rock, synthwave, folk, or lofi"

    # Diatonic chord qualities by scale degree
    # Major: I-maj, ii-min, iii-min, IV-maj, V-maj (or dom7), vi-min, vii-dim
    # Minor: i-min, ii-dim, III-maj, iv-min, V-maj, VI-maj, VII-maj
    _MAJOR_DEGREES = {0: "maj", 1: "min", 2: "min", 3: "maj", 4: "dom7", 5: "min", 6: "dim"}
    _MINOR_DEGREES = {0: "min", 1: "dim", 2: "maj", 3: "min", 4: "dom7", 5: "maj", 6: "maj"}

    # Scale intervals for roman numeral → semitone offset
    _MAJOR_SCALE = [0, 2, 4, 5, 7, 9, 11]
    _MINOR_SCALE = [0, 2, 3, 5, 7, 8, 10]

    # Progression templates: (degree_indices, style_name)
    _PROGRESSIONS = {
        ("major", "pop"):        [0, 4, 5, 3],      # I-V-vi-IV
        ("major", "jazz"):       [1, 4, 0],          # ii-V-I
        ("major", "rock"):       [0, 3, 4],          # I-IV-V
        ("major", "synthwave"):  [0, 5, 2, 6],       # I-vi-iii-VII (borrowed)
        ("major", "folk"):       [0, 3, 5, 4],       # I-IV-vi-V
        ("major", "lofi"):       [0, 5, 3, 4],       # I-vi-IV-V
        ("minor", "pop"):        [0, 5, 2, 6],       # i-VI-III-VII
        ("minor", "jazz"):       [1, 4, 0],          # ii-V-i
        ("minor", "rock"):       [0, 3, 4],          # i-iv-V
        ("minor", "synthwave"):  [0, 5, 2, 6],       # i-VI-III-VII
        ("minor", "folk"):       [0, 3, 6, 2],       # i-iv-VII-III
        ("minor", "lofi"):       [1, 4, 0],          # ii-V-i
    }

    degrees = _PROGRESSIONS.get((mode, style))
    if degrees is None:
        return f"Error: no progression template for mode={mode}, style={style}"

    scale = _MAJOR_SCALE if mode == "major" else _MINOR_SCALE
    qualities = _MAJOR_DEGREES if mode == "major" else _MINOR_DEGREES

    key_pc = NOTE_TO_PITCH[key]

    # Build chord list for create_chord_progression format: [["C","min"],...]
    chord_list = []
    progression_names = []
    for deg in degrees:
        root_pc = (key_pc + scale[deg]) % 12
        # Find note name from pitch class
        _PC_TO_NAME = {0: "C", 1: "C#", 2: "D", 3: "D#", 4: "E", 5: "F",
                       6: "F#", 7: "G", 8: "G#", 9: "A", 10: "A#", 11: "B"}
        root_name = _PC_TO_NAME[root_pc]
        chord_type = qualities[deg]
        chord_list.append([root_name, chord_type])
        progression_names.append(f"{root_name}{chord_type}")

    # Now delegate to create_chord_progression
    chords_json = json.dumps(chord_list)
    result = await mcp_opendaw_create_chord_progression(
        chords_json, unit_index, track_index, start_beat, chord_duration
    )

    # Augment result with progression metadata
    try:
        parsed = json.loads(result)
        if isinstance(parsed, dict):
            parsed["key"] = key
            parsed["mode"] = mode
            parsed["style"] = style
            parsed["progression"] = progression_names
            return json.dumps(parsed)
    except (json.JSONDecodeError, TypeError):
        pass
    return result


async def mcp_opendaw_set_piano_keyboard(keyboard_type: int) -> str:
    """Set the piano roll keyboard type.

    keyboard_type: One of 88 (full piano), 76 (stage), 61 (compact), 49 (controller).

    Returns success with old and new values.
    """
    valid = [88, 76, 61, 49]
    if keyboard_type not in valid:
        return json.dumps({"error": f"keyboard_type must be one of {valid}, got {keyboard_type}"})
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const pm = h.rootBoxAdapter.pianoMode;
            const old = pm.keyboard.getValue();
            h.editing.modify(() => {{
                pm.keyboard.field.setValue({keyboard_type});
            }});
            return {{success: true, old_keyboard: old, new_keyboard: {keyboard_type}}};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_transcribe_audio(
    filename: str,
    bpm: float = 0,
    unit_index: int = 0,
    drum_track: int = 0,
    melody_track: int = 1,
) -> str:
    """Transcribe a full audio track — drums + melody — into MIDI notes in one call.

    Composite tool that runs transcribe_drums + transcribe_melody on the same
    WAV file, placing drum notes on one track and melody notes on another.
    Eliminates 2 separate calls. Essential for Suno-to-MIDI pipeline:
    download_audio → transcribe_audio → full MIDI reconstruction on 2 tracks.

    Pipeline:
    1. Parse WAV file
    2. Auto-detect BPM (if bpm=0)
    3. Transcribe drums → kick/snare/hat on drum_track (pitch 36/38/42)
    4. Transcribe melody → pitched notes on melody_track (with cents + clarity)
    5. Create MIDI notes via create_notes_batch on both tracks

    Use cases:
    - Extract full groove from a Suno track → remix in DAW
    - Convert a loop to MIDI → quantize, replace instruments, rearrange
    - Capture a performance → edit and enhance

    filename: WAV file name (in exports dir) or absolute path.
    bpm: Tempo for beat conversion (0 = auto-detect).
    unit_index: AU index with note tracks.
    drum_track: Track for drum notes (default 0).
    melody_track: Track for melody notes (default 1).

    Returns: drum notes, melody notes, bpm, duration, band counts, avg clarity.

    Example:
      # Full transcription of a Suno track
      result = transcribe_audio("suno_track.wav", bpm=120)
      # Auto-detect BPM
      result = transcribe_audio("loop.wav")  # bpm=0 → auto-detect
    """
    import os as _os

    export_dir = _os.environ.get("OPENDAW_EXPORT_DIR",
                                  _os.path.join(_os.path.dirname(__file__), "exports"))
    filepath = _os.path.join(export_dir, filename if filename.endswith(".wav") else filename + ".wav")
    if not _os.path.exists(filepath):
        filepath = filename if _os.path.isabs(filename) else _os.path.join(_os.getcwd(), filename)

    if not _os.path.exists(filepath):
        return _err(f"File not found: {filename}")

    try:
        with open(filepath, "rb") as f:
            raw = f.read()
        wav = _parse_wav(raw)
        channels = wav["channels"]
        sr = wav["sample_rate"]

        # Auto-detect BPM
        actual_bpm = bpm
        if not bpm or bpm <= 0:
            bpm_result = _detect_bpm(channels, sr)
            actual_bpm = bpm_result["bpm"]

        # Transcribe drums
        drum_result = _transcribe_drums(channels, sr, bpm=actual_bpm)

        # Transcribe melody
        melody_result = _transcribe_melody(channels, sr, bpm=actual_bpm)

        # Create drum notes on drum_track
        drum_notes_created = 0
        if drum_result["notes"]:
            drum_daw_notes = [{
                "pitch": n["pitch"],
                "start": n["start_beat"],
                "duration": n["duration"],
                "velocity": n["velocity"],
            } for n in drum_result["notes"]]
            drum_notes_result = await mcp_opendaw_create_notes_batch(
                json.dumps(drum_daw_notes), unit_index, drum_track)
            try:
                drum_notes_created = json.loads(drum_notes_result).get("notes_created", len(drum_daw_notes))
            except Exception:
                drum_notes_created = len(drum_daw_notes)

        # Create melody notes on melody_track
        melody_notes_created = 0
        avg_clarity = 0.0
        if melody_result["notes"]:
            melody_daw_notes = [{
                "pitch": n["pitch"],
                "start": n["start_beat"],
                "duration": n["duration"],
                "velocity": n["velocity"],
            } for n in melody_result["notes"]]
            melody_notes_result = await mcp_opendaw_create_notes_batch(
                json.dumps(melody_daw_notes), unit_index, melody_track)
            try:
                melody_notes_created = json.loads(melody_notes_result).get("notes_created", len(melody_daw_notes))
            except Exception:
                melody_notes_created = len(melody_daw_notes)
            avg_clarity = sum(n["clarity"] for n in melody_result["notes"]) / len(melody_result["notes"])

        return json.dumps({
            "success": True,
            "bpm": actual_bpm,
            "duration_seconds": drum_result["duration_seconds"],
            "drums": {
                "track": drum_track,
                "notes_created": drum_notes_created,
                "onset_count": drum_result["onset_count"],
                "band_counts": drum_result["band_counts"],
            },
            "melody": {
                "track": melody_track,
                "notes_created": melody_notes_created,
                "note_count": melody_result["note_count"],
                "avg_clarity": round(avg_clarity, 3),
            },
            "total_notes": drum_notes_created + melody_notes_created,
            "unit_index": unit_index,
        })
    except Exception as e:
        return _err(f"Audio transcription error: {e}")


async def mcp_opendaw_transcribe_drums(
    filename: str,
    bpm: float = 0,
    sensitivity: float = 1.5,
    unit_index: int = 0,
    track_index: int = 0,
) -> str:
    """Transcribe drum onsets from an audio file into MIDI notes on a DAW track.

    Audio-to-MIDI drum transcription — converts a drum recording (or any audio
    with percussive content) into MIDI notes. Pure Python, no external deps.

    Pipeline:
    1. Parse WAV file
    2. Split into 3 frequency bands (kick <250Hz, snare 250-2500Hz, hat >2500Hz)
    3. Per-band onset detection (energy spike above local average)
    4. Classify each onset: kick (pitch 36), snare (38), hat (42)
    5. Estimate velocity from onset amplitude
    6. Convert onset times to beat positions (if bpm provided)
    7. Create MIDI notes on the specified track via create_notes_batch

    Use cases:
    - Extract a drum groove from a Suno track → reuse as MIDI pattern
    - Transcribe a real drum recording → edit/quantize in DAW
    - Replace original drums with a different instrument

    filename: WAV file name (in exports dir) or absolute path.
    bpm: Tempo for beat conversion (0 = auto-detect via detect_bpm first).
    sensitivity: Onset detection threshold (1.0=more sensitive, 2.0=less, default 1.5).
    unit_index: AU index with note tracks.
    track_index: Track to place transcribed notes.

    Returns: notes created, onset count, band counts (kick/snare/hat), bpm, duration.

    Example:
      # Transcribe a drum loop from a downloaded Suno track
      result = transcribe_drums("suno_track.wav", bpm=120)
      # Auto-detect BPM first
      result = transcribe_drums("drum_loop.wav")  # bpm=0 → auto-detect
    """
    import os as _os

    export_dir = _os.environ.get("OPENDAW_EXPORT_DIR",
                                  _os.path.join(_os.path.dirname(__file__), "exports"))
    filepath = _os.path.join(export_dir, filename if filename.endswith(".wav") else filename + ".wav")
    if not _os.path.exists(filepath):
        filepath = filename if _os.path.isabs(filename) else _os.path.join(_os.getcwd(), filename)

    if not _os.path.exists(filepath):
        return _err(f"File not found: {filename}")

    try:
        with open(filepath, "rb") as f:
            raw = f.read()
        wav = _parse_wav(raw)
        channels = wav["channels"]
        sr = wav["sample_rate"]

        # Auto-detect BPM if not provided
        actual_bpm = bpm
        if not bpm or bpm <= 0:
            bpm_result = _detect_bpm(channels, sr)
            actual_bpm = bpm_result["bpm"]

        # Transcribe drums
        result = _transcribe_drums(channels, sr, bpm=actual_bpm, sensitivity=sensitivity)

        if not result["notes"]:
            return json.dumps({
                "success": True,
                "notes_created": 0,
                "bpm": actual_bpm,
                "duration_seconds": result["duration_seconds"],
                "message": "No drum onsets detected — try lowering sensitivity"
            })

        # Convert to DAW note format and create on track
        daw_notes = []
        for n in result["notes"]:
            daw_notes.append({
                "pitch": n["pitch"],
                "start": n["start_beat"],
                "duration": n["duration"],
                "velocity": n["velocity"],
            })

        notes_result = await mcp_opendaw_create_notes_batch(
            json.dumps(daw_notes), unit_index, track_index)

        try:
            notes_data = json.loads(notes_result)
        except Exception:
            notes_data = {"raw": notes_result}

        return json.dumps({
            "success": True,
            "notes_created": len(daw_notes),
            "bpm": actual_bpm,
            "onset_count": result["onset_count"],
            "band_counts": result["band_counts"],
            "duration_seconds": result["duration_seconds"],
            "track_index": track_index,
            "unit_index": unit_index,
            "notes_result": notes_data.get("notes_created", len(daw_notes)),
        })
    except Exception as e:
        return _err(f"Drum transcription error: {e}")


async def mcp_opendaw_transcribe_melody(
    filename: str,
    bpm: float = 0,
    unit_index: int = 0,
    track_index: int = 0,
) -> str:
    """Transcribe monophonic melody from an audio file into MIDI notes on a DAW track.

    Audio-to-MIDI melody transcription — converts a monophonic instrument
    recording (bass, vocal, lead synth, horn) into MIDI notes. Pure Python,
    no external deps.

    Pipeline:
    1. Parse WAV file
    2. Frame-by-frame autocorrelation pitch detection
    3. Convert frequency → MIDI pitch (with cents deviation for tuning accuracy)
    4. Group consecutive similar-pitch frames into sustained notes
    5. Estimate velocity from frame energy
    6. Create MIDI notes on the specified track via create_notes_batch

    Use cases:
    - Extract a bass line from a Suno track → reuse as MIDI
    - Transcribe a vocal melody → harmonize or transform
    - Capture a horn line → arrange for other instruments
    - Convert any monophonic audio to editable MIDI

    filename: WAV file name (in exports dir) or absolute path.
    bpm: Tempo for beat conversion (0 = auto-detect via detect_bpm).
    unit_index: AU index with note tracks.
    track_index: Track to place transcribed notes.

    Returns: notes created, note count, bpm, duration, average clarity.

    Example:
      # Transcribe a bass line from a Suno track
      result = transcribe_melody("suno_bass.wav", bpm=120)
      # Auto-detect BPM
      result = transcribe_melody("vocal.wav")  # bpm=0 → auto-detect
    """
    import os as _os

    export_dir = _os.environ.get("OPENDAW_EXPORT_DIR",
                                  _os.path.join(_os.path.dirname(__file__), "exports"))
    filepath = _os.path.join(export_dir, filename if filename.endswith(".wav") else filename + ".wav")
    if not _os.path.exists(filepath):
        filepath = filename if _os.path.isabs(filename) else _os.path.join(_os.getcwd(), filename)

    if not _os.path.exists(filepath):
        return _err(f"File not found: {filename}")

    try:
        with open(filepath, "rb") as f:
            raw = f.read()
        wav = _parse_wav(raw)
        channels = wav["channels"]
        sr = wav["sample_rate"]

        # Auto-detect BPM if not provided
        actual_bpm = bpm
        if not bpm or bpm <= 0:
            bpm_result = _detect_bpm(channels, sr)
            actual_bpm = bpm_result["bpm"]

        # Transcribe melody
        result = _transcribe_melody(channels, sr, bpm=actual_bpm)

        if not result["notes"]:
            return json.dumps({
                "success": True,
                "notes_created": 0,
                "bpm": actual_bpm,
                "duration_seconds": result["duration_seconds"],
                "message": "No pitched content detected"
            })

        # Convert to DAW note format
        daw_notes = []
        for n in result["notes"]:
            daw_notes.append({
                "pitch": n["pitch"],
                "start": n["start_beat"],
                "duration": n["duration"],
                "velocity": n["velocity"],
            })

        notes_result = await mcp_opendaw_create_notes_batch(
            json.dumps(daw_notes), unit_index, track_index)

        try:
            notes_data = json.loads(notes_result)
        except Exception:
            notes_data = {"raw": notes_result}

        # Average clarity across all notes
        avg_clarity = sum(n["clarity"] for n in result["notes"]) / len(result["notes"])

        return json.dumps({
            "success": True,
            "notes_created": len(daw_notes),
            "bpm": actual_bpm,
            "note_count": result["note_count"],
            "duration_seconds": result["duration_seconds"],
            "avg_clarity": round(avg_clarity, 3),
            "track_index": track_index,
            "unit_index": unit_index,
            "notes_result": notes_data.get("notes_created", len(daw_notes)),
            "first_notes": result["notes"][:5],  # preview
        })
    except Exception as e:
        return _err(f"Melody transcription error: {e}")

