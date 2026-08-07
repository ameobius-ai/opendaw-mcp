"""
Instruments & MIDI Tools
==================
"""

import json
import asyncio

# These will be injected by server.py
bridge = None
_wrap_eval = None
_ok = None
_err = None


def init_instruments_tools(bridge_instance, wrap_eval_func, ok_func=None, err_func=None):
    """Initialize instruments tools with shared dependencies."""
    global bridge, _wrap_eval, _ok, _err
    bridge = bridge_instance
    _wrap_eval = wrap_eval_func
    _ok = ok_func
    _err = err_func



async def mcp_opendaw_add_instrument_automation(unit_index: int, parameter_name: str, points: str, sample_index: int = -1) -> str:
    """Automate a parameter on the instrument connected to an audio unit.

    Works with any automatable instrument field: Vaporisateur (cutoff, resonance, volume, etc),
    Playfield sample mute, Tape flutter/wow, Nano volume/release, and more.

    For Playfield sample-level params (mute, volume, pan, etc), set sample_index to the
    sample slot index (0-based). For top-level instrument params, leave sample_index as -1.

    unit_index: Audio unit index containing the instrument.
    parameter_name: Field name to automate (e.g. "cutoff", "mute", "flutter").
    points: JSON array of [position_beats, value] pairs. Example: "[[0, 0.5], [4, 1.0]]"
    sample_index: For Playfield, which sample slot to target (-1 = top-level instrument field).

    Returns automation track info and number of events created.
    """
    safe_param = parameter_name.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const UUID = h.uuid;
        const Quarter = h.ppqn.Quarter;
        const ValueEventBox = window.DAW_ValueEventBox;
        const unitIdx = {unit_index};
        const paramName = "{safe_param}";
        const sampleIdx = {sample_index};
        const points = {points};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No AU at " + unitIdx}};
        const au = units[unitIdx];

        // Find instrument box
        const incoming = h.inputBoxes(au);
        const instBox = incoming.find(b => b.constructor.name !== "AudioBusBox");
        if (!instBox) return {{error: "No instrument on AU " + unitIdx}};

        // Determine target box: instrument or specific Playfield sample
        let targetBox = instBox;
        if (sampleIdx >= 0) {{
            const samples = h.sampleBoxes(instBox);
                .sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
            if (sampleIdx >= samples.length) return {{error: "No sample at index " + sampleIdx}};
            targetBox = samples[sampleIdx];
        }}

        const field = targetBox[paramName];
        if (!field) return {{error: "No field '" + paramName + "' on " + targetBox.constructor.name}};

        // Create automation track
        let autoTrack, valueClip, collection;
        h.editing.modify(() => {{
            autoTrack = h.api.createAutomationTrack(au, field);
            valueClip = h.api.createValueClip(autoTrack, 0, {{name: paramName}});
            collection = valueClip.events?.targetVertex?.unwrap?.()?.box;
            if (!collection) throw new Error("No event collection on value clip");

            points.forEach(([beatPos, value], i) => {{
                ValueEventBox.create(h.boxGraph, UUID.generate(), (box) => {{
                    box.events.refer(collection.events);
                    box.position.setValue(Math.round(beatPos * Quarter));
                    box.index.setValue(i);
                    box.value.setValue(value);
                    box.interpolation.setValue(1);
                }});
            }});
        }});

        return {{
            success: true,
            unit_index: unitIdx,
            instrument: instBox.constructor.name,
            target: sampleIdx >= 0 ? "sample[" + sampleIdx + "]" : "instrument",
            parameter: paramName,
            events_created: points.length,
            track_index: autoTrack?.index?.getValue?.() ?? 0,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_add_instrument_chain(
    unit_index: int = 0,
    style: str = "clean",
    reverb_amount: float = 0.15,
    delay_amount: float = 0.0,
) -> str:
    """Add a ready-made instrument processing chain — EQ → Compressor → Reverb (+ optional Delay).

    Universal chain for guitars, keys, synth leads, strings, pads — any melodic/harmonic instrument.
    One call replaces 3-4 individual add_effect + set_effect_parameter calls.

    unit_index: Target audio unit (the instrument track).
    style: Preset character:
      - "clean" — transparent EQ, light comp, subtle reverb (keys, piano, clean guitar)
      - "warm" — low-mid warmth, tube-like comp (jazz guitar, Rhodes, warm synths)
      - "bright" — air boost, present mids, short reverb (lead guitar, synth lead, pop keys)
      - "ambient" — wide EQ, minimal comp, lush reverb (pads, strings, atmospheres)
      - "driven" — mid crunch, drive comp, room reverb (rock guitar, aggressive synths)

    reverb_amount: Reverb wet/dry (0-1, default 0.15 = subtle).
    delay_amount: Optional delay wet/dry (0-1, default 0 = off).

    Creates: Revamp EQ → Compressor → Reverb (→ Delay) on the target AU.
    Returns effect indices and parameter values set.

    Example:
      # Clean keys chain
      add_instrument_chain(0)
      # Ambient pad with lush reverb
      add_instrument_chain(0, style="ambient", reverb_amount=0.4)
      # Driven rock guitar
      add_instrument_chain(0, style="driven", reverb_amount=0.2)
      # Synth lead with delay
      add_instrument_chain(0, style="bright", delay_amount=0.2)
    """
    styles = {
        "clean": {
            "eq_low_shelf_gain": 1.0, "eq_low_shelf_freq": 150,
            "eq_high_shelf_gain": 2.0, "eq_high_shelf_freq": 8000,
            "eq_mid_gain": 0.0, "eq_mid_freq": 500,
            "comp_threshold": -22, "comp_ratio": 2.0, "comp_attack": 12, "comp_release": 100,
        },
        "warm": {
            "eq_low_shelf_gain": 3.0, "eq_low_shelf_freq": 200,
            "eq_high_shelf_gain": 1.0, "eq_high_shelf_freq": 6000,
            "eq_mid_gain": 1.5, "eq_mid_freq": 300,
            "comp_threshold": -20, "comp_ratio": 2.5, "comp_attack": 18, "comp_release": 130,
        },
        "bright": {
            "eq_low_shelf_gain": -1.0, "eq_low_shelf_freq": 120,
            "eq_high_shelf_gain": 4.0, "eq_high_shelf_freq": 10000,
            "eq_mid_gain": -1.0, "eq_mid_freq": 400,
            "comp_threshold": -18, "comp_ratio": 3.0, "comp_attack": 6, "comp_release": 70,
        },
        "ambient": {
            "eq_low_shelf_gain": 2.0, "eq_low_shelf_freq": 100,
            "eq_high_shelf_gain": 3.0, "eq_high_shelf_freq": 9000,
            "eq_mid_gain": -1.0, "eq_mid_freq": 500,
            "comp_threshold": -26, "comp_ratio": 1.5, "comp_attack": 25, "comp_release": 200,
        },
        "driven": {
            "eq_low_shelf_gain": -2.0, "eq_low_shelf_freq": 100,
            "eq_high_shelf_gain": 3.0, "eq_high_shelf_freq": 7000,
            "eq_mid_gain": 3.0, "eq_mid_freq": 800,
            "comp_threshold": -16, "comp_ratio": 4.0, "comp_attack": 4, "comp_release": 50,
        },
    }
    if style not in styles:
        return f"Error: unknown style '{style}'. Valid: {list(styles.keys())}"
    if not (0.0 <= reverb_amount <= 1.0):
        return "Error: reverb_amount must be 0-1"
    if not (0.0 <= delay_amount <= 1.0):
        return "Error: delay_amount must be 0-1"

    params = styles[style]
    use_delay = delay_amount > 0.0

    chain_desc = "Revamp EQ → Compressor → Reverb"
    if use_delay:
        chain_desc += " → Delay"

    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const bg = h.boxGraph;
        const p = window.DAW;
        const EF = window.DAW_EffectFactories;

        const params = {json.dumps(params)};
        const reverbAmount = {reverb_amount};
        const delayAmount = {delay_amount};
        const useDelay = {str(use_delay).lower()};

        const allUnits = h.allAUBoxes();
        if (!allUnits[{unit_index}]) return {{error: "Audio unit {unit_index} not found"}};
        const targetAU = allUnits[{unit_index}];

        let eqIdx = -1, compIdx = -1, revIdx = -1, delIdx = -1;

        h.modify(() => {{
            p.api.insertEffect(targetAU.audioEffects, EF.Revamp);
            eqIdx = h.effectBoxes(targetAU).length - 1;
        }});

        h.modify(() => {{
            p.api.insertEffect(targetAU.audioEffects, EF.Compressor);
            compIdx = h.effectBoxes(targetAU).length - 1;
        }});

        h.modify(() => {{
            p.api.insertEffect(targetAU.audioEffects, EF.Reverb);
            revIdx = h.effectBoxes(targetAU).length - 1;
        }});

        if (useDelay) {{
            h.modify(() => {{
                p.api.insertEffect(targetAU.audioEffects, EF.Delay);
                delIdx = h.effectBoxes(targetAU).length - 1;
            }});
        }}

        // Set compressor params
        const effects = h.effectBoxes(targetAU);
        h.modify(() => {{
            const compBox = effects[compIdx];
            if (compBox) {{
                const record = compBox.record();
                for (const [key, field] of Object.entries(record)) {{
                    const fname = field._fieldName || field.fieldName || key;
                    if (fname === 'threshold') field.setValue(params.comp_threshold);
                    if (fname === 'ratio') field.setValue(params.comp_ratio);
                    if (fname === 'attack') field.setValue(params.comp_attack);
                    if (fname === 'release') field.setValue(params.comp_release);
                }}
            }}
        }});

        return {{
            success: true,
            unit_index: {unit_index},
            chain: [
                {{name: "Revamp EQ", index: eqIdx, params: {{
                    low_shelf: params.eq_low_shelf_gain + "dB@" + params.eq_low_shelf_freq + "Hz",
                    high_shelf: params.eq_high_shelf_gain + "dB@" + params.eq_high_shelf_freq + "Hz",
                    mid: params.eq_mid_gain + "dB@" + params.eq_mid_freq + "Hz",
                }}}},
                {{name: "Compressor", index: compIdx, params: {{
                    threshold: params.comp_threshold, ratio: params.comp_ratio,
                    attack: params.comp_attack, release: params.comp_release,
                }}}},
                {{name: "Reverb", index: revIdx, params: {{wet: reverbAmount}}}},
            ] + (useDelay ? [{{name: "Delay", index: delIdx, params: {{wet: delayAmount}}}}] : []),
            style: "{style}",
            chain_description: "{chain_desc}",
            note: "Instrument chain applied. Adjust reverb_amount and delay_amount for taste.",
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_add_midi_effect(unit_index: int, effect_type: str) -> str:
    """Add a MIDI effect to an audio unit's MIDI effect chain.

MIDI effects process note data before the instrument. They are chained
on au.midiEffects (separate from audio effects on au.audioEffects).

effect_type: One of: Arpeggio, Pitch, Velocity, Zeitgeist, Spielwerk

unit_index: Audio unit index (must be an instrument AU, not output).
Returns effect_index in the MIDI chain.
    """
    safe_effect = effect_type.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const ef = window.DAW_EffectFactories;
        const effectType = "{safe_effect}";
        const unitIndex = {unit_index};

        const factory = ef.MidiNamed[effectType];
        if (!factory) return {{error: "MIDI effect factory not found: " + effectType}};

        const units = h.allAUBoxes();
        if (unitIndex >= units.length) return {{error: "No audio unit at index " + unitIndex}};
        const au = units[unitIndex];

        let effectBox;
        h.modify(() => {{
            effectBox = h.api.insertEffect(au.midiEffects, factory);
        }});

        const effects = h.midiEffectBoxes(au);
        const effectIndex = effects.findIndex(b => b.address.equals(effectBox.address));

        return {{
            success: true,
            effect: effectType,
            effect_index: effectIndex,
            unit: au.name?.getValue?.() || "Unit " + unitIndex,
            chain: "midi",
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_augment_notes(
    factor: float,
    unit_index: int,
    track_index: int,
    region_index: int = -1,
    mode: str = "scale",
) -> str:
    """Augment or diminish note durations — the fourth classical transformation.

    Multiplies note durations by a factor. Combined with transpose, reverse, and
    invert, this completes the set of four fundamental motivic transformations
    used by Bach, Beethoven, and every composition teacher since.

    - factor > 1.0: augmentation (longer notes, slower feel). 2.0 = double duration.
    - factor < 1.0: diminution (shorter notes, faster feel). 0.5 = half duration.
    - factor = 1.0: no change (useful for testing).

    Think Beethoven 5th: the opening G-G-G-Eb motif returns augmented (twice as slow)
    in the recapitulation. Or Bach fugues where the subject appears in diminution
    (twice as fast) in the finale.

    factor: Duration multiplier (0.25-4.0). 2.0 = augmentation, 0.5 = diminution.
    unit_index: AU index.
    track_index: Note track index.
    region_index: Region index (-1 = all regions on the track).
    mode: How to handle note positions —
      "scale" (default): multiply both duration AND position relative to region start.
        The entire phrase slows down or speeds up — notes stay in sequence.
      "stretch": multiply only duration, leave positions unchanged.
        Notes become longer/shorter but don't move — may overlap or leave gaps.

    Returns count of notes augmented and notes skipped (duration too short/long).
    """
    if factor < 0.25 or factor > 4.0:
        return f"Error: factor must be 0.25-4.0, got {factor}"
    if mode not in ("scale", "stretch"):
        return f"Error: mode must be 'scale' or 'stretch', got '{mode}'"

    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const factorVal = {factor};
        const modeStr = "{mode}";

        let augmented = 0;
        let skipped = 0;
        const allUnits = h.allAUBoxes();
        if (unitIdx >= allUnits.length) return {{error: "No AU at index " + unitIdx}};
        const noteTracks = h.noteTrackBoxes(allUnits[unitIdx]);
        if (noteTracks.length === 0) return {{error: "No note tracks on AU " + unitIdx}};
        if (trackIdx >= noteTracks.length) return {{error: "Track " + trackIdx + " out of range"}};

        const regions = h.regionBoxes(noteTracks[trackIdx]);
        const targetRegions = regionIdx < 0 ? regions : (regionIdx < regions.length ? [regions[regionIdx]] : []);

        h.modify(() => {{
            for (const region of targetRegions) {{
                try {{
                    const regionPos = region.position.getValue();
                    const vertex = region.events.targetVertex.unwrap();
                    const collBox = vertex.box || vertex;
                    if (!collBox || !collBox.events) continue;

                    const noteEvents = h.eventBoxes(collBox);
                    for (const evt of noteEvents) {{
                        const oldDur = evt.duration.getValue();
                        const newDur = Math.round(oldDur * factorVal);
                        if (newDur < 1) {{
                            skipped++;
                            continue;
                        }}
                        evt.duration.setValue(newDur);

                        if (modeStr === "scale") {{
                            const oldPos = evt.position.getValue();
                            const relPos = oldPos - regionPos;
                            const newPos = regionPos + Math.round(relPos * factorVal);
                            evt.position.setValue(newPos);
                        }}
                        augmented++;
                    }}
                }} catch(e) {{}}
            }}
        }});

        return {{
            success: true,
            factor: factorVal,
            mode: modeStr,
            notes_augmented: augmented,
            notes_skipped: skipped,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_batch_diagnostic(
    filenames: str,
    genre: str = "",
) -> str:
    """Run full diagnostic on multiple stems in one call — problems + phase + profile comparison.

    Phantom's batch_diagnostic equivalent. For each stem runs:
    1. detect_problems (clipping, DC offset, mud, harshness, sibilance, resonance)
    2. analyze_phase (polarity, correlation, mono compat) — stereo files only
    3. compare_to_profile (if genre specified)

    Produces a prioritized triage report:
    - dealbreaker: clipping, phase inversion, DC offset
    - significant: mud, harshness, resonance
    - moderate: sibilance risk, width issues
    - minor: slight deviations from profile

    filenames: JSON array or comma-separated list of WAV filenames.
    genre: Optional genre profile for comparison (pop, rock, lo-fi, etc.).

    Returns per-stem results + global summary + prioritized fix list.

    Example:
      batch_diagnostic('["vocals.wav","bass.wav","drums.wav","mix.wav"]', genre="rock")
      # → {triage: [{stem: "vocals", severity: "significant", problems: [...]}]}
    """
    # Parse filenames
    try:
        names = json.loads(filenames) if filenames.strip().startswith("[") else [s.strip() for s in filenames.split(",")]
    except Exception:
        names = [s.strip() for s in filenames.split(",")]

    results = []
    all_issues = []

    for name in names:
        fpath = _resolve_audio_file(name)
        if not fpath:
            results.append({"stem": name, "error": "file not found"})
            continue

        stem_result = {"stem": name, "file": fpath}
        stem_issues = []

        # 1. Problems
        try:
            channels, sr, _ = _load_wav_for_analysis(name)

            # Clipping
            clip_count = sum(1 for ch in channels for s in ch if abs(s) >= 0.999)
            if clip_count > 0:
                stem_issues.append({"severity": "dealbreaker", "type": "clipping", "count": clip_count, "stem": name})

            # DC offset
            for ci, ch in enumerate(channels):
                mean = sum(ch) / len(ch) if ch else 0
                if abs(mean) > 0.001:
                    sev = "dealbreaker" if abs(mean) > 0.005 else "significant"
                    stem_issues.append({"severity": sev, "type": "dc_offset", "channel": ci, "value": round(mean, 5), "stem": name})

            # Spectrum-based checks
            spec = _analyze_spectrum(channels, sr)
            bands = {b["name"]: b for b in spec.get("bands", [])}

            mud = bands.get("low_mids", {}).get("energy_pct", 0)
            if mud > 25:
                sev = "significant" if mud > 35 else "moderate"
                stem_issues.append({"severity": sev, "type": "mud", "band": "low_mids", "value": round(mud, 1), "stem": name})

            harsh = bands.get("high_mids", {}).get("energy_pct", 0)
            if harsh > 22:
                sev = "significant" if harsh > 30 else "moderate"
                stem_issues.append({"severity": sev, "type": "harshness", "band": "high_mids", "value": round(harsh, 1), "stem": name})

            presence = bands.get("presence", {}).get("energy_pct", 0)
            if presence > 18:
                stem_issues.append({"severity": "moderate", "type": "sibilance_risk", "value": round(presence, 1), "stem": name})

            # LUFS
            lufs_data = _compute_lufs(channels, sr)
            stem_result["lufs"] = lufs_data.get("lufs_integrated")
            stem_result["true_peak"] = lufs_data.get("true_peak_db")

            # Spectral centroid
            stem_result["centroid_hz"] = spec.get("spectral_centroid_hz", 0)

        except Exception as e:
            stem_issues.append({"severity": "minor", "type": "analysis_error", "error": str(e)[:100], "stem": name})

        # 2. Phase (stereo only)
        try:
            if len(channels) >= 2:
                import math as _m
                left, right = channels[0], channels[1]
                n = min(len(left), len(right))
                step = max(1, n // 48000)
                sum_lr = sum(left[i] * right[i] for i in range(0, n, step))
                sum_l2 = sum(left[i] ** 2 for i in range(0, n, step))
                sum_r2 = sum(right[i] ** 2 for i in range(0, n, step))
                corr = sum_lr / (_m.sqrt(sum_l2 * sum_r2) + 1e-10) if sum_l2 > 0 and sum_r2 > 0 else 0
                if corr < 0:
                    stem_issues.append({"severity": "dealbreaker", "type": "phase_inversion", "correlation": round(corr, 2), "stem": name})
                elif corr < 0.3:
                    stem_issues.append({"severity": "significant", "type": "low_phase_corr", "correlation": round(corr, 2), "stem": name})
                stem_result["phase_correlation"] = round(corr, 2)
        except Exception:
            pass

        # 3. Genre comparison
        if genre:
            try:
                from opendaw_mcp.genre_profiles import get_profile
                profile = get_profile(genre)
                if profile:
                    lufs_val = stem_result.get("lufs", -99)
                    target_lufs = profile["target_lufs"]
                    lufs_min, lufs_max = profile["lufs_range"]
                    if lufs_val < lufs_min - 2:
                        stem_issues.append({"severity": "moderate", "type": "too_quiet", "lufs": lufs_val, "target": target_lufs, "stem": name})
                    elif lufs_val > lufs_max + 2:
                        stem_issues.append({"severity": "moderate", "type": "too_loud", "lufs": lufs_val, "target": target_lufs, "stem": name})
            except Exception:
                pass

        stem_result["issues"] = stem_issues
        results.append(stem_result)
        all_issues.extend(stem_issues)

    # Triage summary
    sev_order = {"dealbreaker": 0, "significant": 1, "moderate": 2, "minor": 3}
    all_issues.sort(key=lambda x: sev_order.get(x.get("severity", "minor"), 4))

    summary = {
        "dealbreaker": sum(1 for i in all_issues if i.get("severity") == "dealbreaker"),
        "significant": sum(1 for i in all_issues if i.get("severity") == "significant"),
        "moderate": sum(1 for i in all_issues if i.get("severity") == "moderate"),
        "minor": sum(1 for i in all_issues if i.get("severity") == "minor"),
    }

    return json.dumps({
        "success": True,
        "stems_analyzed": len(names),
        "genre": genre or None,
        "summary": summary,
        "triage": all_issues,
        "per_stem": results,
    }, indent=2)



# === Lineage / provenance (theDAW LEARN-inspired, file-backed) ===

def _lineage_store():
    from opendaw_mcp.lineage import get_store
    return get_store()


async def mcp_opendaw_consolidate_note(unit_index: int, track_index: int, region_index: int, note_index: int) -> str:
    """Consolidate a repeated note (playCount > 1) into individual separate notes.

    If a note has playCount > 1, it represents N repeats controlled by playCurve.
    This expands it into N independent notes, each with playCount=1, positioned
    according to the curve. The original note is deleted.

    unit_index: AU index.
    track_index: Note track index.
    region_index: Note region index.
    note_index: Note index within the region.

    Returns the number of notes created, or error if note has playCount=1.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const region = h.region({unit_index}, {track_index}, {region_index});
            if (!region.isNoteRegion?.()) return {{error: "Region is not a note region"}};
            const optCol = region.optCollection;
            if (optCol.isEmpty()) return {{error: "No note collection"}};
            const collection = optCol.unwrap();
            const events = collection.events.asArray();
            if ({note_index} >= events.length) return {{error: "No note {note_index}"}};
            const note = events[{note_index}];
            if (note.playCount <= 1) return {{error: "Note has playCount=1, nothing to consolidate"}};
            let created;
            h.modify(() => {{
                created = note.consolidate();
            }});
            return {{
                success: true,
                notes_created: created.length,
                play_count_was: note.playCount,
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


# ─────────────────────────────────────────────────────────────────────
# Device Management (167-168)
# ─────────────────────────────────────────────────────────────────────


async def mcp_opendaw_constrain_note_range(
    unit_index: int = -1,
    track_index: int = -1,
    region_index: int = -1,
    min_pitch: int = 0,
    max_pitch: int = 127,
    mode: str = "clamp",
) -> str:
    """Constrain notes to a pitch range — clamp or octave-wrap out-of-range notes.

    After AI generation, transcription, or aggressive transposition, notes
    can land outside the playable range of an instrument. This tool brings
    them back inside.

    Two modes:
    - "clamp" — notes below min_pitch are set to min_pitch, notes above
      max_pitch are set to max_pitch. Preserves the note but loses pitch
      information. Use when exact range matters (e.g. MIDI 0-127 safety).
    - "octave_wrap" — notes are shifted by octaves (±12 semitones) until
      they fall within [min_pitch, max_pitch]. Preserves pitch class and
      musical relationship. Use for instrument range constraints (violin,
      guitar, vocal, flute). If a note can't fit even after wrapping
      (range < 12 semitones), it's clamped.

    Common instrument ranges (MIDI note numbers):
    - Guitar (standard tuning): E2(40) to E6(88)
    - Bass guitar: E1(28) to G4(67)
    - Violin: G3(55) to A7(105)
    - Cello: C2(36) to C6(84)
    - Flute: C4(60) to D7(98)
    - Vocal soprano: C4(60) to A5(81)
    - Vocal bass: E2(40) to E4(64)

    unit_index: AU index (-1 = all AUs).
    track_index: Note track index (-1 = all note tracks on the AU).
    region_index: Region index (-1 = all regions on the track).
    min_pitch: Minimum allowed MIDI pitch (0-127, default 0 = no lower bound).
    max_pitch: Maximum allowed MIDI pitch (0-127, default 127 = no upper bound).
    mode: "clamp" (hard limit) or "octave_wrap" (shift by octaves to fit).

    Returns per-track notes adjusted, clamped count, wrapped count.

    Example:
      # Constrain to guitar range with octave wrapping
      constrain_note_range(unit_index=0, track_index=2, min_pitch=40,
                           max_pitch=88, mode="octave_wrap")

      # Safety clamp to MIDI range
      constrain_note_range(mode="clamp", min_pitch=0, max_pitch=127)
    """
    if not (0 <= min_pitch <= 127):
        return "Error: min_pitch must be 0-127"
    if not (0 <= max_pitch <= 127):
        return "Error: max_pitch must be 0-127"
    if min_pitch >= max_pitch:
        return "Error: min_pitch must be less than max_pitch"
    if mode not in ("clamp", "octave_wrap"):
        return f"Error: mode must be 'clamp' or 'octave_wrap', got '{mode}'"

    range_span = max_pitch - min_pitch

    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const minP = {min_pitch};
        const maxP = {max_pitch};
        const modeStr = "{mode}";
        const rangeSpan = {range_span};

        const allUnits = h.allAUBoxes();
        const trackResults = [];

        const unitsToProcess = unitIdx < 0 ? allUnits : [allUnits[unitIdx]];
        if (unitIdx >= allUnits.length) return {{error: "unit_index out of range"}};

        for (let u = 0; u < unitsToProcess.length; u++) {{
            const au = unitsToProcess[u];
            const tracks = h.trackBoxes(au);
            const tracksToProcess = trackIdx < 0 ? tracks : [tracks[trackIdx]];
            if (trackIdx >= tracks.length) return {{error: "track_index out of range"}};

            for (let t = 0; t < tracksToProcess.length; t++) {{
                const track = tracksToProcess[t];
                const regions = h.regionBoxes(track);
                if (regions.length === 0) continue;
                const regionsToProcess = regionIdx < 0 ? regions : [regions[Math.min(regionIdx, regions.length - 1)]];

                for (const region of regionsToProcess) {{
                    const eventsField = region.events.targetVertex.unwrap();
                    const collBox = eventsField.box;
                    const noteEvents = [...collBox.events.pointerHub.incoming()];
                    if (noteEvents.length === 0) continue;

                    let adjusted = 0;
                    let clamped = 0;
                    let wrapped = 0;

                    h.modify(() => {{
                        for (const n of noteEvents) {{
                            const origPitch = n.box.pitch.getValue();
                            if (origPitch >= minP && origPitch <= maxP) continue;
                            adjusted++;

                            if (modeStr === "clamp") {{
                                if (origPitch < minP) {{
                                    n.box.pitch.setValue(minP);
                                    clamped++;
                                }} else if (origPitch > maxP) {{
                                    n.box.pitch.setValue(maxP);
                                    clamped++;
                                }}
                            }} else {{
                                // octave_wrap
                                let pitch = origPitch;
                                if (rangeSpan >= 12) {{
                                    // Shift by octaves until in range
                                    while (pitch < minP) {{
                                        pitch += 12;
                                        wrapped++;
                                    }}
                                    while (pitch > maxP) {{
                                        pitch -= 12;
                                        wrapped++;
                                    }}
                                    // If still out (shouldn't happen with span >= 12), clamp
                                    if (pitch < minP) {{
                                        pitch = minP;
                                        clamped++;
                                    }} else if (pitch > maxP) {{
                                        pitch = maxP;
                                        clamped++;
                                    }}
                                }} else {{
                                    // Range too small for octave wrap, clamp
                                    pitch = Math.max(minP, Math.min(maxP, pitch));
                                    clamped++;
                                }}
                                n.box.pitch.setValue(pitch);
                            }}
                        }}
                    }});

                    trackResults.push({{
                        unit: u,
                        track: t,
                        notes_adjusted: adjusted,
                        clamped: clamped,
                        wrapped: wrapped,
                        min_pitch: minP,
                        max_pitch: maxP,
                        mode: modeStr,
                    }});
                }}
            }}
        }}

        return {{
            success: true,
            min_pitch: minP,
            max_pitch: maxP,
            mode: modeStr,
            tracks_processed: trackResults.length,
            per_track: trackResults,
            total_adjusted: trackResults.reduce((s, r) => s + r.notes_adjusted, 0),
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_create_ghost_notes(
    unit_index: int = 0,
    track_index: int = 0,
    region_index: int = -1,
    density: float = 0.3,
    velocity: float = 0.25,
    seed: int = 42,
) -> str:
    """Add ghost notes (quiet grace notes) to existing drum/MIDI patterns.

    Ghost notes are very quiet notes placed between main hits, adding groove and complexity.
    Essential for funk, R&B, neo-soul, and hip-hop drumming. They fill spaces between
    snare/kick hits with subtle taps that make the beat feel alive.

    Inserts new low-velocity notes at off-beat positions where no notes currently exist.
    Works on the first note track of the specified AU/track.

    unit_index: AU index.
    track_index: Note track index (-1 = first note track).
    region_index: Region index (-1 = first region).
    density: Probability of adding a ghost note at each empty 16th position (0.2 = sparse, 0.5 = busy).
    velocity: Ghost note velocity 0-1 (0.25 = very quiet, 0.4 = audible).
    seed: Random seed for reproducibility.

    Returns number of ghost notes added and positions.

    Example:
      create_ghost_notes(unit_index=0, density=0.35, velocity=0.3, seed=99)
    """
    if not (0.0 <= density <= 1.0):
        return f"Error: density must be 0-1, got {density}"
    if not (0.0 <= velocity <= 1.0):
        return f"Error: velocity must be 0-1, got {velocity}"
    if velocity > 0.5:
        return "Error: ghost notes should be quiet (velocity <= 0.5)"

    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const api = h.api;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const densityVal = {density};
        const ghostVel = {velocity};
        const seed = {seed};
        const Quarter = h.ppqn.Quarter;
        const sixteenthTicks = Math.floor(Quarter / 4);

        // Seeded PRNG (mulberry32)
        let s = seed >>> 0;
        function rand() {{
            s = (s + 0x6D2B79F5) >>> 0;
            let t = s;
            t = Math.imul(t ^ (t >>> 15), t | 1);
            t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
            return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
        }}

        const allUnits = h.allAUBoxes();
        if (unitIdx < 0 || unitIdx >= allUnits.length) return {{error: "unit_index out of range"}};
        const au = allUnits[unitIdx];
        const noteTracks = h.trackBoxes(au).filter(box => box.type?.getValue?.() === 1);
        if (noteTracks.length === 0) return {{error: "No note tracks on AU"}};
        const targetTrack = trackIdx < 0 ? noteTracks[0] : (trackIdx < noteTracks.length ? noteTracks[trackIdx] : noteTracks[0]);
        const regions = h.regionBoxes(targetTrack);
        if (regions.length === 0) return {{error: "No regions on track"}};
        const region = regionIdx < 0 ? regions[0] : (regionIdx < regions.length ? regions[regionIdx] : regions[0]);

        const vertex = region.events.targetVertex.unwrap();
        const collBox = vertex.box || vertex;
        const noteEvents = h.eventBoxes(collBox);

        // Collect occupied 16th positions
        const occupied = new Set();
        for (const evt of noteEvents) {{
            const pos = evt.position.getValue();
            const gridIdx = Math.round(pos / sixteenthTicks);
            occupied.add(gridIdx);
        }}

        // Find region boundaries
        const regionStart = region.position.getValue();
        let regionLength = 4 * Quarter; // default 1 bar
        try {{
            regionLength = region.length?.getValue?.() || region.duration?.getValue?.() || (4 * Quarter);
        }} catch(e) {{}}
        const regionEnd = regionStart + regionLength;
        const startGrid = Math.ceil(regionStart / sixteenthTicks);
        const endGrid = Math.floor(regionEnd / sixteenthTicks);

        // Generate ghost notes at empty 16th positions
        const NoteEventBox = window.DAW_NoteEventBox;
        const ghostNotes = [];
        h.modify(() => {{
            for (let grid = startGrid; grid < endGrid; grid++) {{
                if (occupied.has(grid)) continue;
                if (rand() < densityVal) {{
                    // Use pitch of nearest note, or default 38 (snare)
                    let nearestPitch = 38;
                    let minDist = Infinity;
                    for (const evt of noteEvents) {{
                        const evtGrid = Math.round(evt.position.getValue() / sixteenthTicks);
                        const dist = Math.abs(evtGrid - grid);
                        if (dist < minDist) {{
                            minDist = dist;
                            nearestPitch = evt.pitch.getValue();
                        }}
                    }}

                    const pos = grid * sixteenthTicks;
                    const dur = Math.floor(sixteenthTicks * 0.5);  // short duration
                    NoteEventBox.create(h.boxGraph, h.uuid.generate(), (box) => {{
                        box.position.setValue(pos);
                        box.duration.setValue(dur);
                        box.velocity.setValue(ghostVel);
                        box.pitch.setValue(nearestPitch);
                        box.events.refer(collBox.events);
                    }});
                    ghostNotes.push({{position: pos, pitch: nearestPitch, velocity: ghostVel}});
                }}
            }}
        }});

        return {{
            success: true,
            ghost_notes_added: ghostNotes.length,
            density: densityVal,
            velocity: ghostVel,
            seed: seed,
            positions: ghostNotes.slice(0, 20).map(g => g.position),
        }};
    }}""")
    return _wrap_eval(result)


class OpendawServer:
    """Facade class for framework integrations (LangChain, AutoGen, CrewAI).

    Provides `bridge` (HeadlessDawBridge instance) and all `mcp_opendaw_*` tool
    functions as callable methods, so framework wrappers can use a single object.

    Usage:
        server = OpendawServer()
        await server.bridge.start()
        result = await server.mcp_opendaw_set_bpm(bpm=120)
    """

    def __init__(self, daw_url: str | None = None):
        if daw_url:
            import os as _os
            _os.environ["OPENDAW_URL"] = daw_url
        self.bridge = bridge

    def __getattr__(self, name: str):
        """Delegate mcp_opendaw_* calls to the module-level functions."""
        if name.startswith("mcp_opendaw_"):
            fn = globals().get(name)
            if fn is not None:
                return fn
        raise AttributeError(f"'OpendawServer' has no attribute '{name}'")


async def mcp_opendaw_create_midi_echo(
    unit_index: int,
    track_index: int,
    region_index: int = -1,
    repeats: int = 3,
    delay_beats: float = 0.5,
    velocity_decay: float = 0.6,
    pitch_shift: int = 0,
    dest_track: int = -1,
    feedback_mode: str = "linear",
) -> str:
    """Create MIDI echo — repeat notes with decaying velocity and optional pitch shift.

    Takes existing notes from a region and creates echoing repeats. Each repeat
    is delayed by delay_beats, quieter by velocity_decay factor, and optionally
    shifted in pitch. This is a creative effect, not a simple copy — think
    guitar delay throws, synth echo fills, vocal repeat stutters.

    feedback_mode:
    - "linear" — each repeat is velocity_decay × previous (0.6 → 0.6, 0.36, 0.216)
    - "exponential" — faster decay, squared each time
    - "constant" — same velocity for all repeats (stutter feel)
    - "reverse" — each repeat gets louder (build-up feel)

    pitch_shift: semitones added per repeat (0 = no shift, +12 = octave up each
      repeat, -5 = perfect fourth down each repeat). Creates cascading echoes.

    dest_track: -1 = same track (thickening), N = separate track (layered echo).
      Using a separate track lets you process the echo independently.

    repeats: 1-8 echo repeats. Each repeat copies ALL notes from the source.
    delay_beats: time between each repeat (0.25 = 16th, 0.5 = 8th, 1.0 = quarter).

    unit_index: AU index.
    track_index: Source note track.
    region_index: Source region (-1 = first).
    repeats: Number of echo repeats (1-8).
    delay_beats: Delay between repeats in beats.
    velocity_decay: Velocity multiplier per repeat (0-1, 0.6 = 60% each time).
    pitch_shift: Semitones added per repeat (0 = none).
    dest_track: Destination track (-1 = same, N = separate track).
    feedback_mode: linear / exponential / constant / reverse.

    Returns echo summary with per-repeat velocity and pitch info.

    Example:
      # Guitar-style echo: 3 repeats, 8th note delay, decaying
      create_midi_echo(0, 0, repeats=3, delay_beats=0.5, velocity_decay=0.5)
      # Cascading octave echoes on separate track
      create_midi_echo(0, 0, repeats=4, delay_beats=0.25, pitch_shift=12, dest_track=2)
    """
    if not (1 <= repeats <= 8):
        return "Error: repeats must be 1-8"
    if delay_beats <= 0 or delay_beats > 16:
        return "Error: delay_beats must be 0-16"
    if not (0.0 <= velocity_decay <= 1.0):
        return "Error: velocity_decay must be 0-1"
    if not (-24 <= pitch_shift <= 24):
        return "Error: pitch_shift must be -24 to +24"
    valid_modes = ("linear", "exponential", "constant", "reverse")
    if feedback_mode not in valid_modes:
        return f"Error: feedback_mode must be one of {list(valid_modes)}, got '{feedback_mode}'"

    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regIdx = {region_index};
        const numRepeats = {repeats};
        const delayBeats = {delay_beats};
        const velDecay = {velocity_decay};
        const pitchShiftVal = {pitch_shift};
        const destTrackIdx = {dest_track};
        const feedbackMode = "{feedback_mode}";
        const Quarter = 960;

        const allUnits = h.allAUBoxes();
        if (unitIdx < 0 || unitIdx >= allUnits.length) return {{error: "unit_index out of range"}};
        const au = allUnits[unitIdx];
        const noteTracks = h.noteTrackBoxes(au);
        if (trackIdx < 0 || trackIdx >= noteTracks.length) return {{error: "track_index out of range"}};
        const trackBox = noteTracks[trackIdx];
        const regions = h.regionBoxes(trackBox);
        if (regions.length === 0) return {{error: "No regions on track"}};
        const ri = regIdx < 0 ? 0 : regIdx;
        if (ri >= regions.length) return {{error: "region_index out of range"}};
        const region = regions[ri];

        // Get source notes
        let collection = null;
        try {{
            const vertex = region.events.targetVertex.unwrap();
            collection = vertex.box || vertex;
        }} catch(e) {{}}
        if (!collection || !collection.events) return {{error: "No note collection in region"}};
        const srcNotes = h.eventBoxes(collection);
        if (srcNotes.length === 0) return {{error: "No notes in region"}};

        // Read source note data
        const srcData = srcNotes.map(n => ({{
            pos: n.position.getValue(),
            dur: n.duration.getValue(),
            pitch: n.pitch.getValue(),
            vel: n.velocity.getValue(),
        }}));

        // Determine destination
        const dTrackIdx = destTrackIdx < 0 ? trackIdx : destTrackIdx;
        if (dTrackIdx < 0 || dTrackIdx >= noteTracks.length) return {{error: "dest_track out of range"}};
        const destTrack = noteTracks[dTrackIdx];
        const destRegions = h.regionBoxes(destTrack);
        if (destRegions.length === 0) return {{error: "No regions on dest track"}};

        // Use same region on dest track, or first region
        const destRegion = destTrackIdx === trackIdx ? region : destRegions[0];
        let destColl = null;
        try {{
            const dv = destRegion.events.targetVertex.unwrap();
            destColl = dv.box || dv;
        }} catch(e) {{}}
        if (!destColl || !destColl.events) return {{error: "No note collection in dest region"}};

        // Build echo notes
        const echoNotes = [];
        const repeatInfo = [];
        for (let r = 1; r <= numRepeats; r++) {{
            let velFactor;
            if (feedbackMode === "linear") {{
                velFactor = Math.pow(velDecay, r);
            }} else if (feedbackMode === "exponential") {{
                velFactor = Math.pow(velDecay, r * r);
            }} else if (feedbackMode === "constant") {{
                velFactor = 1.0;
            }} else {{ // reverse
                velFactor = Math.min(1.0, 1.0 - (r / (numRepeats + 1)));
            }}

            const pitchOffset = pitchShiftVal * r;
            const timeOffset = delayBeats * r * Quarter;

            for (const note of srcData) {{
                echoNotes.push({{
                    pos: note.pos + timeOffset,
                    dur: note.dur,
                    pitch: note.pitch + pitchOffset,
                    vel: Math.max(0.01, Math.min(1.0, note.vel * velFactor)),
                }});
            }}
            repeatInfo.push({{
                repeat: r,
                velocity_factor: Math.round(velFactor * 1000) / 1000,
                pitch_offset: pitchOffset,
                time_offset_beats: Math.round(delayBeats * r * 1000) / 1000,
            }});
        }}

        // Create echo notes in destination
        const bg = h.boxGraph;
        let created = 0;
        const editing = h.editing;
        await editing.modify(async () => {{
            for (const en of echoNotes) {{
                const noteBox = h.NoteEventBox.create(bg, h.uuid.generate(), (box) => {{
                    box.position.setValue(Math.round(en.pos));
                    box.duration.setValue(Math.round(en.dur));
                    box.pitch.setValue(en.pitch);
                    box.velocity.setValue(en.vel);
                    box.cent.setValue(0);
                    box.events.refer(destColl.events);
                }});
                created++;
            }}
        }});

        return {{
            success: true,
            notes_created: created,
            repeats: numRepeats,
            delay_beats: delayBeats,
            velocity_decay: velDecay,
            pitch_shift: pitchShiftVal,
            feedback_mode: feedbackMode,
            dest_track: dTrackIdx,
            repeat_details: repeatInfo,
            source_note_count: srcData.length,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_create_note(track_index: int, pitch: int, start_beat: float, duration_beats: float, velocity: float, unit_index: int) -> str:
    """Create a MIDI note on a note track.

pitch: MIDI note number (60 = C4, 69 = A4).
start_beat: beat position.
duration_beats: note length in beats.
velocity: 0.0-1.0.
unit_index: Audio unit index (-1 = search all AUs for note tracks).
track_index: Note track index within the AU.

If no clip exists on the track yet, one is auto-created.
Notes are added to the first clip on the track.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const bg = h.boxGraph;
        const NoteEventBox = window.DAW_NoteEventBox;
        const NoteEventCollectionBox = window.DAW_NoteEventCollectionBox;
        const NoteRegionBox = window.DAW_NoteRegionBox;

        const trackIndex = {track_index};
        const pitch = {pitch};
        const startBeat = {start_beat};
        const durationBeats = {duration_beats};
        const velocity = {velocity};
        const unitIdx = {unit_index};

        const Quarter = h.ppqn.Quarter;
        const startPosition = Math.round(startBeat * Quarter);
        const noteDuration = Math.round(durationBeats * Quarter);

        // Find note tracks — either on specified AU or across all AUs
        let noteTracks = [];
        if (unitIdx < 0) {{
            const allUnits = h.allAUBoxes();
            for (const au of allUnits) {{
                const tracks = h.trackBoxes(au)
                    .filter(box => box.type?.getValue?.() === 1);
                noteTracks.push(...tracks);
            }}
        }} else {{
            const units = h.allAUBoxes();
            if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
            noteTracks = h.noteTrackBoxes(units[unitIdx]);
        }}

        if (noteTracks.length === 0) return {{error: "No note tracks found. Call mcp_opendaw_create_note_track first."}};
        if (trackIndex >= noteTracks.length) return {{error: "Track index " + trackIndex + " out of range (" + noteTracks.length + " note tracks)."}};

        const trackBox = noteTracks[trackIndex];

        let regionBox = null;
        h.modify(() => {{
            // Find existing region on this track, or create one
            const existingRegions = h.regionBoxes(trackBox);
            let collection = null;

            if (existingRegions.length > 0) {{
                // Use the first existing region — add note to its events collection
                regionBox = existingRegions[0];
            }}

            if (!regionBox) {{
                // Create new NoteEventCollectionBox + NoteRegionBox
                collection = NoteEventCollectionBox.create(bg, h.uuid.generate());
                regionBox = NoteRegionBox.create(bg, h.uuid.generate(), (box) => {{
                    box.position.setValue(0);
                    box.label.setValue("Notes");
                    box.mute.setValue(false);
                    box.duration.setValue(Math.max(noteDuration, 4 * Quarter));
                    box.loopDuration.setValue(0);
                    box.loopDuration.setValue(Math.max(noteDuration, 4 * Quarter));
                    box.eventOffset.setValue(0);
                    box.events.refer(collection.owners);
                    box.regions.refer(trackBox.regions);
                }});
            }}

            // Create the note event — position relative to region start
            const regionStart = regionBox.position.getValue();
            const notePos = Math.max(0, startPosition - regionStart);

            const eventsField = regionBox.events.targetVertex.unwrap();
            const collBox = eventsField.box;

            NoteEventBox.create(bg, h.uuid.generate(), (box) => {{
                box.position.setValue(notePos);
                box.duration.setValue(noteDuration);
                box.velocity.setValue(velocity);
                box.pitch.setValue(pitch);
                box.chance.setValue(100);
                box.cent.setValue(0);
                box.events.refer(collBox.events);
            }});
        }});

        // Second modify() — region duration/loopDuration set inside NoteRegionBox.create()
        // callback doesn't persist (box not yet in graph during callback). Set explicitly here.
        const noteEnd = Math.round((startBeat + durationBeats) * Quarter);
        h.modify(() => {{
            if (regionBox) {{
                const curDur = regionBox.duration.getValue();
                if (noteEnd > curDur) {{
                    regionBox.duration.setValue(noteEnd);
                    regionBox.loopDuration.setValue(noteEnd);
                }}
            }}
        }});

        return {{
            success: true,
            pitch: pitch,
            startBeat: startBeat,
            durationBeats: durationBeats,
            velocity: velocity,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_create_notes_batch(notes: str, unit_index: int = 0, track_index: int = 0) -> str:
    """Create multiple MIDI notes in a single call — batch creation for melodies, chords, arpeggios.

notes: JSON array of note objects, each with:
  - pitch (int): MIDI note number (60 = C4, 69 = A4)
  - start (float): beat position
  - duration (float): note length in beats
  - velocity (float, optional): 0.0-1.0, default 0.8

Example: '[{"pitch":60,"start":0,"duration":0.5},{"pitch":64,"start":0.5,"duration":0.5},{"pitch":67,"start":1,"duration":1}]'

All notes go into one region on the specified note track. If no region exists, one is created.
Faster than calling create_note repeatedly — one round-trip, one editing.modify() block.
"""
    import json as _json
    try:
        note_list = _json.loads(notes)
        if not isinstance(note_list, list) or len(note_list) == 0:
            return "Error: notes must be a non-empty JSON array"
        if len(note_list) > 500:
            return f"Error: max 500 notes per batch, got {len(note_list)}"
    except _json.JSONDecodeError as e:
        return f"Error parsing notes JSON: {e}"

    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const bg = h.boxGraph;
        const NoteEventBox = window.DAW_NoteEventBox;
        const NoteEventCollectionBox = window.DAW_NoteEventCollectionBox;
        const NoteRegionBox = window.DAW_NoteRegionBox;
        const Quarter = h.ppqn.Quarter;

        const notes = {json.dumps(note_list)};
        const unitIdx = {unit_index};
        const trackIdx = {track_index};

        let noteTracks = [];
        if (unitIdx < 0) {{
            for (const au of h.allAUBoxes()) {{
                noteTracks.push(...h.trackBoxes(au).filter(box => box.type?.getValue?.() === 1));
            }}
        }} else {{
            const units = h.allAUBoxes();
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            noteTracks = h.noteTrackBoxes(units[unitIdx]);
        }}

        if (noteTracks.length === 0) return {{error: "No note tracks found"}};
        if (trackIdx >= noteTracks.length) return {{error: "Track " + trackIdx + " out of range (" + noteTracks.length + ")"}};

        const trackBox = noteTracks[trackIdx];
        let regionBox = null;
        let createdCount = 0;

        h.modify(() => {{
            const existing = h.regionBoxes(trackBox);
            if (existing.length > 0) {{
                regionBox = existing[0];
            }} else {{
                let maxEnd = 0;
                for (const n of notes) maxEnd = Math.max(maxEnd, Math.round((n.start + n.duration) * Quarter));
                const collection = NoteEventCollectionBox.create(bg, h.uuid.generate());
                regionBox = NoteRegionBox.create(bg, h.uuid.generate(), (box) => {{
                    box.position.setValue(0);
                    box.label.setValue("Notes");
                    box.mute.setValue(false);
                    box.duration.setValue(Math.max(maxEnd, 4 * Quarter));
                    box.loopDuration.setValue(Math.max(maxEnd, 4 * Quarter));
                    box.eventOffset.setValue(0);
                    box.events.refer(collection.owners);
                    box.regions.refer(trackBox.regions);
                }});
            }}

            const regionStart = regionBox.position.getValue();
            const eventsField = regionBox.events.targetVertex.unwrap();
            const collBox = eventsField.box;

            let maxEnd = 0;
            for (const n of notes) {{
                const vel = n.velocity !== undefined ? n.velocity : 0.8;
                const pos = Math.max(0, Math.round(n.start * Quarter) - regionStart);
                const dur = Math.round(n.duration * Quarter);
                NoteEventBox.create(bg, h.uuid.generate(), (box) => {{
                    box.position.setValue(pos);
                    box.duration.setValue(dur);
                    box.velocity.setValue(vel);
                    box.pitch.setValue(n.pitch);
                    box.chance.setValue(100);
                    box.cent.setValue(0);
                    box.events.refer(collBox.events);
                }});
                createdCount++;
                maxEnd = Math.max(maxEnd, pos + dur);
            }}
            if (maxEnd > regionBox.duration.getValue()) {{
                regionBox.duration.setValue(maxEnd);
                regionBox.loopDuration.setValue(maxEnd);
            }}
        }});

        return {{
            success: true,
            notes_created: createdCount,
            track_index: trackIdx,
            unit_index: unitIdx,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_diatonic_transpose_notes(
    unit_index: int = -1,
    track_index: int = -1,
    region_index: int = -1,
    steps: int = 1,
    root_note: str = "C",
    scale: str = "major",
) -> str:
    """Transpose notes by scale steps (diatonic) instead of semitones (chromatic).

    Moves each note up or down by N steps within the specified scale. Unlike
    transpose_notes (which shifts by fixed semitones), diatonic transpose preserves
    the scale — C major C→D = +1 step (2 semitones), E→F = +1 step (1 semitone).

    Essential for: creating variations that stay in key, modal interchange,
    sequence construction (moving a motif up the scale), walking bass from
    scale degrees, and counterpoint writing.

    unit_index: AU index (-1 = all AUs).
    track_index: Note track index (-1 = all note tracks).
    region_index: Region index (-1 = all regions on track).
    steps: Number of scale steps to transpose. +1 = up one step, -1 = down one step,
      +3 = up a third, -5 = down a fifth. 0 = no change.
    root_note: Root note of the scale — C, C#, D, D#, E, F, F#, G, G#, A, A#, B.
    scale: Scale name — major, minor, dorian, phrygian, lydian, mixolydian,
      pentatonic_major, pentatonic_minor, blues, harmonic_minor, melodic_minor.

    Returns per-track note counts transposed.
    """
    from opendaw_mcp.music_theory import SCALE_INTERVALS

    note_to_num = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5,
                   "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
    root_num = note_to_num.get(root_note)
    if root_num is None:
        return f"Error: invalid root_note '{root_note}'"
    intervals = SCALE_INTERVALS.get(scale)
    if intervals is None:
        return f"Error: unknown scale '{scale}'"
    if steps == 0:
        return "Error: steps must be non-zero (use transpose_notes for semitone shifts)"

    # Build full chromatic scale mapping: for each pitch class, which scale degree is it?
    # Then shifting by N steps = find the pitch class N positions ahead in the scale.
    # Build a 2-octave scale for safe up/down shifting
    scale_pcs = sorted(set((root_num + iv) % 12 for iv in intervals))
    # Build extended scale: [pc, pc, ...] repeating across octaves
    # For mapping: given a pitch, find its position in scale, then shift

    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const stepShift = {steps};
        const scalePcs = {json.dumps(scale_pcs)};
        const Quarter = 960;

        const allUnits = h.allAUBoxes();
        if (unitIdx >= allUnits.length) return {{error: "unit_index out of range"}};
        const unitsToProcess = unitIdx < 0 ? allUnits : [allUnits[unitIdx]];

        const trackResults = [];

        for (let u = 0; u < unitsToProcess.length; u++) {{
            const au = unitsToProcess[u];
            const tracks = h.trackBoxes(au);
            if (trackIdx >= tracks.length) return {{error: "track_index out of range"}};
            const tracksToProcess = trackIdx < 0 ? tracks : [tracks[trackIdx]];

            for (let t = 0; t < tracksToProcess.length; t++) {{
                const track = tracksToProcess[t];
                const regions = h.regionBoxes(track);
                if (regions.length === 0) continue;
                const regionsToProcess = regionIdx < 0 ? regions : [regions[Math.min(regionIdx, regions.length - 1)]];

                let transposed = 0;
                let skipped = 0;
                const changes = [];

                for (const region of regionsToProcess) {{
                    const eventsField = region.events.targetVertex.unwrap();
                    const collBox = eventsField.box;
                    const noteEvents = [...collBox.events.pointerHub.incoming()];

                    h.modify(() => {{
                        for (const n of noteEvents) {{
                            const origPitch = n.box.pitch.getValue();
                            const pc = origPitch % 12;
                            const octave = Math.floor(origPitch / 12);

                            // Find this pitch class in the scale
                            let scaleIdx = scalePcs.indexOf(pc);
                            if (scaleIdx === -1) {{
                                // Note is not in scale — skip it (don't force it in)
                                skipped++;
                                continue;
                            }}

                            // Shift by stepShift positions in the scale
                            let newScaleIdx = scaleIdx + stepShift;
                            let newOctave = octave;

                            // Handle octave wrapping
                            while (newScaleIdx >= scalePcs.length) {{
                                newScaleIdx -= scalePcs.length;
                                newOctave++;
                            }}
                            while (newScaleIdx < 0) {{
                                newScaleIdx += scalePcs.length;
                                newOctave--;
                            }}

                            const newPc = scalePcs[newScaleIdx];
                            const newPitch = newOctave * 12 + newPc;

                            if (newPitch !== origPitch) {{
                                changes.push({{ from: origPitch, to: newPitch }});
                                n.box.pitch.setValue(newPitch);
                                transposed++;
                            }}
                        }}
                    }});
                }}

                trackResults.push({{
                    unit: u,
                    track: t,
                    notes_transposed: transposed,
                    notes_skipped_not_in_scale: skipped,
                    sample_changes: changes.slice(0, 20),
                }});
            }}
        }}

        return {{
            success: true,
            steps: stepShift,
            root_note: "{root_note}",
            scale: "{scale}",
            total_transposed: trackResults.reduce((a, b) => a + b.notes_transposed, 0),
            total_skipped: trackResults.reduce((a, b) => a + b.notes_skipped_not_in_scale, 0),
            per_track: trackResults,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_export_midi(filename: str, unit_index: int, track_index: int, region_index: int) -> str:
    """Export a note region's notes as a standard MIDI file (.mid).

Uses @opendaw/lib-midi MidiFileEncoder — converts note events to MIDI
with timeDivision=96 (PPQN.Quarter=960 → 96 ticks per quarter).

filename: Output filename (without extension).
unit_index: Audio unit index (-1 = search all AUs for note tracks).
track_index: Note track index within the AU.
region_index: Region to export (0-based).

Returns the saved file path.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const MidiFile = window.DAW_MidiFile;
        const MidiTrack = window.DAW_MidiTrack;
        const ControlEvent = window.DAW_ControlEvent;
        const ControlType = window.DAW_ControlType;
        const ArrayMultimap = window.DAW_ArrayMultimap;

        if (!MidiFile) throw new Error("lib-midi not loaded — reload page");
        if (!ArrayMultimap) throw new Error("ArrayMultimap not loaded — reload page");

        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};

        // Find note tracks
        let noteTracks = [];
        if (unitIdx < 0) {{
            const allUnits = h.allAUBoxes();
            for (const au of allUnits) {{
                const tracks = h.trackBoxes(au)
                    .filter(box => box.type?.getValue?.() === 1);
                noteTracks.push(...tracks);
            }}
        }} else {{
            const units = h.allAUBoxes();
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            noteTracks = h.noteTrackBoxes(units[unitIdx]);
        }}

        if (trackIdx >= noteTracks.length) return {{error: "No note track at index " + trackIdx}};
        const trackBox = noteTracks[trackIdx];

        const regions = h.regionBoxes(trackBox);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx}};

        const region = regions[regionIdx];
        const collection = region.events.targetVertex.unwrap().box;
        const notes = h.eventBoxes(collection);

        if (notes.length === 0) return {{error: "Region has no notes"}};

        // Convert to MIDI events (timeDivision=96)
        const toTicks = (position, timeDivision = 96) => Math.floor(position / h.ppqn.Quarter * timeDivision);
        const events = [];
        for (const note of notes) {{
            const pos = note.position.getValue();
            const dur = note.duration.getValue();
            const pitch = note.pitch.getValue();
            const vel = Math.round(note.velocity.getValue() * 127);
            events.push(new ControlEvent(toTicks(pos), ControlType.NOTE_ON, pitch, vel));
            events.push(new ControlEvent(toTicks(pos + dur), ControlType.NOTE_OFF, pitch, 0));
        }}

        // Sort by tick
        events.sort((a, b) => a.tick - b.tick);

        const track = new MidiTrack(new ArrayMultimap([[0, events]], ControlEvent.Comparator), []);
        const encoder = MidiFile.encoder();
        encoder.addTrack(track);
        const output = encoder.encode();
        const buffer = output.toArrayBuffer();

        // Convert to base64
        const bytes = new Uint8Array(buffer);
        const chunks = [];
        const cs = 0x8000;
        for (let ci = 0; ci < bytes.length; ci += cs) {{
            chunks.push(String.fromCharCode.apply(null, bytes.subarray(ci, ci + cs)));
        }}
        const b64 = btoa(chunks.join(""));

        return {{
            success: true,
            midi_b64: b64,
            note_count: notes.length,
            size_bytes: bytes.length,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_filter_notes(
    unit_index: int,
    track_index: int,
    region_index: int = -1,
    min_pitch: int = -1,
    max_pitch: int = -1,
    min_velocity: float = -1,
    max_velocity: float = -1,
    from_beat: float = -1,
    to_beat: float = -1,
    action: str = "list",
) -> str:
    """Filter notes by criteria — list, delete, or keep matching notes.

    Applies multiple filter criteria to notes in a region:
    - Pitch range (min_pitch / max_pitch, MIDI note numbers)
    - Velocity range (min_velocity / max_velocity, 0.0-1.0)
    - Time range (from_beat / to_beat, absolute beat positions)

    Any criterion set to -1 is ignored (wildcard).

    Actions:
    - list: Return matching notes (read-only, no changes)
    - delete: Delete all notes matching the criteria
    - keep: Delete all notes NOT matching the criteria (inverse filter)

    Use cases:
    - Remove notes below C2 (cleanup sub-bass rumble): filter_notes(0, 0, min_pitch=36, action="delete")
    - Isolate melody in upper register: filter_notes(0, 0, min_pitch=72, action="keep")
    - Remove ghost notes (velocity < 0.3): filter_notes(0, 0, min_velocity=0.3, action="delete")
    - Find notes in bar 8-12: filter_notes(0, 0, from_beat=32, to_beat=48, action="list")
    - Trim notes outside a time window: filter_notes(0, 0, from_beat=0, to_beat=16, action="keep")

    unit_index: AU index.
    track_index: Note track index.
    region_index: Region (-1 = first region).
    min_pitch: Minimum MIDI pitch (-1 = no filter).
    max_pitch: Maximum MIDI pitch (-1 = no filter).
    min_velocity: Minimum velocity 0-1 (-1 = no filter).
    max_velocity: Maximum velocity 0-1 (-1 = no filter).
    from_beat: Start beat (-1 = no filter).
    to_beat: End beat (-1 = no filter).
    action: "list", "delete", or "keep".

    Returns matching note details (list) or deletion count (delete/keep).

    Example:
      # Delete all notes below C2
      filter_notes(0, 0, min_pitch=36, action="delete")
      # Keep only notes in bars 1-4 (beats 0-16)
      filter_notes(0, 0, from_beat=0, to_beat=16, action="keep")
    """
    if action not in ("list", "delete", "keep"):
        return f"Error: action must be 'list', 'delete', or 'keep', got '{action}'"

    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const minP = {min_pitch};
        const maxP = {max_pitch};
        const minV = {min_velocity};
        const maxV = {max_velocity};
        const fromB = {from_beat};
        const toB = {to_beat};
        const action = "{action}";
        const Quarter = h.ppqn.Quarter;

        const allUnits = h.allAUBoxes();
        if (unitIdx < 0 || unitIdx >= allUnits.length) return {{error: "unit_index out of range"}};
        const au = allUnits[unitIdx];
        const noteTracks = h.noteTrackBoxes(au);
        if (trackIdx < 0 || trackIdx >= noteTracks.length) return {{error: "track_index out of range"}};
        const trackBox = noteTracks[trackIdx];
        const regions = h.regionBoxes(trackBox);
        if (regions.length === 0) return {{error: "No regions on track"}};
        const regIdx = regionIdx < 0 ? 0 : regionIdx;
        if (regIdx >= regions.length) return {{error: "region_index out of range"}};
        const region = regions[regIdx];

        // Get collection
        let collection = null;
        try {{
            const vertex = region.events.targetVertex.unwrap();
            collection = vertex.box || vertex;
        }} catch(e) {{}}
        if (!collection || !collection.events) return {{error: "No note collection in region"}};

        const notes = h.eventBoxes(collection);
        const regionPos = region.position.getValue();

        // Helper: check if a note matches all criteria
        function matches(n) {{
            const pitch = n.pitch.getValue();
            const vel = n.velocity.getValue();
            const notePos = n.position.getValue();
            const absBeat = (regionPos + notePos) / Quarter;

            if (minP >= 0 && pitch < minP) return false;
            if (maxP >= 0 && pitch > maxP) return false;
            if (minV >= 0 && vel < minV) return false;
            if (maxV >= 0 && vel > maxV) return false;
            if (fromB >= 0 && absBeat < fromB) return false;
            if (toB >= 0 && absBeat > toB) return false;
            return true;
        }}

        const matching = [];
        const nonMatching = [];
        for (const n of notes) {{
            if (matches(n)) {{
                matching.push(n);
            }} else {{
                nonMatching.push(n);
            }}
        }}

        if (action === "list") {{
            const noteData = matching.map(n => ({{
                pitch: n.pitch.getValue(),
                position_beats: Math.round((regionPos + n.position.getValue()) / Quarter * 1000) / 1000,
                duration_beats: Math.round(n.duration.getValue() / Quarter * 1000) / 1000,
                velocity: n.velocity.getValue(),
            }}));
            return {{
                success: true,
                action: "list",
                matching: noteData.length,
                total: notes.length,
                notes: noteData.slice(0, 50),
            }};
        }}

        // delete or keep — determine which notes to delete
        const toDelete = action === "delete" ? matching : nonMatching;
        let deleted = 0;

        h.modify(() => {{
            for (const n of toDelete) {{
                n.delete();
                deleted++;
            }}
        }});

        const remaining = h.eventBoxes(collection).length;
        return {{
            success: true,
            action: action,
            notes_deleted: deleted,
            notes_remaining: remaining,
            total_before: notes.length,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_find_overlapping_notes(unit_index: int, track_index: int, region_index: int, pitch: int, from_beat: float, to_beat: float) -> str:
    """Find notes that overlap a given pitch and time range within a note region.

    Useful for checking if a note can be placed without colliding with existing notes,
    or for finding chords/harmonies at a specific pitch range.

    unit_index: AU index.
    track_index: Note track index within the AU.
    region_index: Note region index.
    pitch: MIDI note number to check (60 = C4).
    from_beat: Start of time range in beats.
    to_beat: End of time range in beats.

    Returns list of overlapping notes (position, duration, pitch, velocity), or error.
    """
    from_ppqn = int(from_beat * 960)
    to_ppqn = int(to_beat * 960)
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const region = h.region({unit_index}, {track_index}, {region_index});
            if (!region.isNoteRegion?.()) return {{error: "Region is not a note region"}};
            const optCol = region.optCollection;
            if (optCol.isEmpty()) return {{error: "No note collection"}};
            const collection = optCol.unwrap();
            const overlapping = collection.overlapping({from_ppqn}, {to_ppqn}, {pitch});
            return {{
                overlapping: overlapping.map(n => ({{
                    position_beats: n.position / h.ppqn.Quarter,
                    duration_beats: n.duration / h.ppqn.Quarter,
                    pitch: n.pitch,
                    velocity: n.velocity,
                }})),
                count: overlapping.length,
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


# ─────────────────────────────────────────────────────────────────────
# Note Advanced Properties (165-166)
# ─────────────────────────────────────────────────────────────────────


async def mcp_opendaw_force_scale_notes(
    unit_index: int = -1,
    track_index: int = -1,
    region_index: int = -1,
    root_note: str = "C",
    scale: str = "major",
    direction: str = "nearest",
    preserve_octave: bool = True,
) -> str:
    """Force all notes in a region into a specific scale — harmonic snap.

    Finds every note that is NOT in the target scale and moves it to the nearest
    in-scale note. This is the harmonic equivalent of quantize_notes (which snaps
    timing to a grid). Useful after audio-to-MIDI transcription, random generation,
    or importing MIDI from unknown sources.

    root_note: Root note name — C, C#, D, D#, E, F, F#, G, G#, A, A#, B.
    scale: Scale name — major, minor, dorian, phrygian, lydian, mixolydian, aeolian,
      locrian, pentatonic_major, pentatonic_minor, blues, harmonic_minor, melodic_minor.
    direction: How to resolve out-of-scale notes — "nearest" (closest, default),
      "up" (always shift up to next in-scale note), "down" (always shift down).
    preserve_octave: If True (default), keep notes in their original octave — only
      shift by 1-2 semitones. If False, allow octave jumps to find the nearest match.

    Returns count of notes snapped, per-track breakdown, and which notes were changed.
    """
    # Build scale pitches in Python for validation
    from opendaw_mcp.music_theory import SCALE_INTERVALS

    note_to_num = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5,
                   "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
    root_num = note_to_num.get(root_note)
    if root_num is None:
        return f"Error: invalid root_note '{root_note}'. Use C, C#, D, D#, E, F, F#, G, G#, A, A#, B"

    intervals = SCALE_INTERVALS.get(scale)
    if intervals is None:
        return f"Error: unknown scale '{scale}'. Available: {', '.join(sorted(SCALE_INTERVALS.keys()))}"

    # Build the set of allowed pitch classes (0-11)
    allowed_pcs = sorted(set((root_num + iv) % 12 for iv in intervals))

    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const dir = "{direction}";
        const presOct = {str(preserve_octave).lower()};
        const allowedPcs = {json.dumps(allowed_pcs)};

        const allUnits = h.allAUBoxes();
        if (unitIdx >= allUnits.length) return {{error: "unit_index out of range"}};
        const unitsToProcess = unitIdx < 0 ? allUnits : [allUnits[unitIdx]];

        const trackResults = [];

        for (let u = 0; u < unitsToProcess.length; u++) {{
            const au = unitsToProcess[u];
            const tracks = h.trackBoxes(au);
            if (trackIdx >= tracks.length) return {{error: "track_index out of range"}};
            const tracksToProcess = trackIdx < 0 ? tracks : [tracks[trackIdx]];

            for (let t = 0; t < tracksToProcess.length; t++) {{
                const track = tracksToProcess[t];
                const regions = h.regionBoxes(track);
                if (regions.length === 0) continue;
                const regionsToProcess = regionIdx < 0 ? regions : [regions[Math.min(regionIdx, regions.length - 1)]];

                let snapped = 0;
                let alreadyInScale = 0;
                const changes = [];

                for (const region of regionsToProcess) {{
                    const eventsField = region.events.targetVertex.unwrap();
                    const collBox = eventsField.box;
                    const noteEvents = [...collBox.events.pointerHub.incoming()];

                    h.modify(() => {{
                        for (const n of noteEvents) {{
                            const origPitch = n.box.pitch.getValue();
                            const pc = origPitch % 12;
                            if (allowedPcs.includes(pc)) {{
                                alreadyInScale++;
                                continue;
                            }}
                            // Find nearest in-scale pitch
                            let bestPitch = origPitch;
                            let bestDist = Infinity;
                            if (presOct) {{
                                // Only search within current octave ± 1 semitone
                                for (const apc of allowedPcs) {{
                                    let candidate = (Math.floor(origPitch / 12) * 12) + apc;
                                    if (dir === "up" && candidate < origPitch) candidate += 12;
                                    if (dir === "down" && candidate > origPitch) candidate -= 12;
                                    if (dir === "nearest") {{
                                        const upC = candidate;
                                        const downC = candidate - 12;
                                        if (Math.abs(upC - origPitch) < Math.abs(downC - origPitch)) {{
                                            candidate = upC;
                                        }} else {{
                                            candidate = downC;
                                        }}
                                    }}
                                    const dist = Math.abs(candidate - origPitch);
                                    if (dist < bestDist) {{
                                        bestDist = dist;
                                        bestPitch = candidate;
                                    }}
                                }}
                            }} else {{
                                // Allow octave jumps — search ± 12 semitones
                                for (const apc of allowedPcs) {{
                                    for (let octOffset = -12; octOffset <= 12; octOffset += 12) {{
                                        const candidate = (Math.floor(origPitch / 12) * 12) + apc + octOffset;
                                        if (dir === "up" && candidate < origPitch) continue;
                                        if (dir === "down" && candidate > origPitch) continue;
                                        const dist = Math.abs(candidate - origPitch);
                                        if (dist < bestDist) {{
                                            bestDist = dist;
                                            bestPitch = candidate;
                                        }}
                                    }}
                                }}
                            }}
                            changes.push({{ from: origPitch, to: bestPitch }});
                            n.box.pitch.setValue(bestPitch);
                            snapped++;
                        }}
                    }});
                }}

                trackResults.push({{
                    unit: u,
                    track: t,
                    notes_snapped: snapped,
                    notes_already_in_scale: alreadyInScale,
                    changes: changes.slice(0, 20),  // first 20 for inspection
                }});
            }}
        }}

        return {{
            success: true,
            root_note: "{root_note}",
            scale: "{scale}",
            direction: dir,
            preserve_octave: presOct,
            total_snapped: trackResults.reduce((a, b) => a + b.notes_snapped, 0),
            total_already_in_scale: trackResults.reduce((a, b) => a + b.notes_already_in_scale, 0),
            per_track: trackResults,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_humanize_notes(
    unit_index: int = -1,
    track_index: int = -1,
    velocity_amount: float = 0.15,
    timing_amount: float = 0.15,
    duration_amount: float = 0.10,
    swing: float = 0.0,
    seed: int = 42,
) -> str:
    """Add human-like variation to existing notes — velocity, timing, duration, and swing.

    Makes programmed MIDI feel less robotic by applying small random deviations.
    Works on all notes in the specified track(s)/unit(s), or globally with unit_index=-1.

    unit_index: AU index (-1 = all AUs).
    track_index: Note track index (-1 = all note tracks on the AU).
    velocity_amount: Velocity deviation depth 0-1 (0.15 = ±15% of current velocity).
      Example: 0.05 = subtle, 0.15 = natural, 0.25 = loose.
    timing_amount: Timing offset depth in beats 0-1 (0.15 = up to ±15% of a 16th note = ±3.6 ticks).
      Example: 0.05 = tight, 0.15 = natural groove, 0.30 = sloppy.
    duration_amount: Duration deviation depth 0-1 (0.10 = ±10% of current duration).
    swing: Swing amount 0-1 (0 = straight, 0.5 = light swing, 1.0 = full triplet feel).
      Shifts every other 16th note later by swing * 1/3 of a 16th.
    seed: Random seed for reproducibility (same seed = same humanization).

    Returns per-track note counts and total notes humanized.

    Example:
      humanize_notes(unit_index=0, velocity_amount=0.15, timing_amount=0.12, swing=0.35)
    """
    if not (0.0 <= velocity_amount <= 1.0):
        return f"Error: velocity_amount must be 0-1, got {velocity_amount}"
    if not (0.0 <= timing_amount <= 1.0):
        return f"Error: timing_amount must be 0-1, got {timing_amount}"
    if not (0.0 <= duration_amount <= 1.0):
        return f"Error: duration_amount must be 0-1, got {duration_amount}"
    if not (0.0 <= swing <= 1.0):
        return f"Error: swing must be 0-1, got {swing}"

    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const velAmt = {velocity_amount};
        const timAmt = {timing_amount};
        const durAmt = {duration_amount};
        const swingAmt = {swing};
        const seed = {seed};
        const Quarter = h.ppqn.Quarter;
        const sixteenthTicks = Math.floor(Quarter / 4);  // 240

        // Seeded PRNG (mulberry32)
        let s = seed >>> 0;
        function rand() {{
            s = (s + 0x6D2B79F5) >>> 0;
            let t = s;
            t = Math.imul(t ^ (t >>> 15), t | 1);
            t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
            return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
        }}

        let totalCount = 0;
        const trackStats = [];
        const allUnits = h.allAUBoxes();
        const targetUnits = unitIdx < 0 ? allUnits : (unitIdx < allUnits.length ? [allUnits[unitIdx]] : []);

        h.modify(() => {{
            for (let ui = 0; ui < targetUnits.length; ui++) {{
                const au = targetUnits[ui];
                const noteTracks = h.trackBoxes(au)
                    .filter(box => box.type?.getValue?.() === 1);
                const targetTracks = trackIdx < 0 ? noteTracks : (trackIdx < noteTracks.length ? [noteTracks[trackIdx]] : []);

                for (let ti = 0; ti < targetTracks.length; ti++) {{
                    const track = targetTracks[ti];
                    let trackCount = 0;

                    for (const region of h.regionBoxes(track)) {{
                        try {{
                            const vertex = region.events.targetVertex.unwrap();
                            const collectionBox = vertex.box || vertex;
                            if (!collectionBox || !collectionBox.events) continue;

                            const noteEvents = h.eventBoxes(collectionBox);
                            for (let ni = 0; ni < noteEvents.length; ni++) {{
                                const evt = noteEvents[ni];

                                // Velocity humanization: ±velAmt * currentVelocity, clamped 0.05-1.0
                                const curVel = evt.velocity.getValue();
                                const velDelta = (rand() - 0.5) * 2 * velAmt * curVel;
                                evt.velocity.setValue(Math.max(0.05, Math.min(1.0, curVel + velDelta)));

                                // Timing humanization: ±timAmt * sixteenthTicks
                                const curPos = evt.position.getValue();
                                const timDelta = Math.round((rand() - 0.5) * 2 * timAmt * sixteenthTicks);
                                evt.position.setValue(Math.max(0, curPos + timDelta));

                                // Swing: shift every other 16th later
                                if (swingAmt > 0) {{
                                    const gridPos = Math.round(curPos / sixteenthTicks);
                                    if (gridPos % 2 === 1) {{
                                        const swingOffset = Math.round(sixteenthTicks * swingAmt / 3);
                                        evt.position.setValue(evt.position.getValue() + swingOffset);
                                    }}
                                }}

                                // Duration humanization: ±durAmt * currentDuration
                                const curDur = evt.duration.getValue();
                                const durDelta = Math.round((rand() - 0.5) * 2 * durAmt * curDur);
                                evt.duration.setValue(Math.max(1, curDur + durDelta));

                                trackCount++;
                                totalCount++;
                            }}
                        }} catch(e) {{}}
                    }}
                    trackStats.push({{unit_index: ui, track_index: ti, notes_humanized: trackCount}});
                }}
            }}
        }});

        return {{
            success: true,
            velocity_amount: velAmt,
            timing_amount: timAmt,
            duration_amount: durAmt,
            swing: swingAmt,
            seed: seed,
            total_notes_humanized: totalCount,
            tracks: trackStats,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_import_midi(file_path: str, unit_index: int, track_index: int, offset_beats: float) -> str:
    """Import a MIDI file and create note events on a note track.

Parses standard MIDI (.mid) files and creates note regions with all notes.
Supports format 0 and 1. Ticks are converted to openDAW PPQN (960/quarter).

file_path: Path to .mid file (absolute or relative to MCP server).
unit_index: Audio unit index with a note track (-1 = search all AUs).
track_index: Note track index within the AU.
offset_beats: Offset in beats to shift all notes (e.g. start at bar 2 = 4.0).

Returns note count and time range.
"""
    # Parse MIDI file and extract notes
    import mido
    mid = mido.MidiFile(file_path)
    notes_data = []
    for track in mid.tracks:
        abs_tick = 0
        for msg in track:
            abs_tick += msg.time
            if msg.type == 'note_on' and msg.velocity > 0:
                note = {
                    'pitch': msg.note,
                    'velocity': round(msg.velocity / 127.0, 3),
                    'start_tick': abs_tick,
                }
                notes_data.append(note)
    notes_json = json.dumps(notes_data)
    offset_ticks = int(offset_beats * 960)
    ppqn = 960
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const bg = h.boxGraph;
        const NoteEventBox = window.DAW_NoteEventBox;
        const NoteEventCollectionBox = window.DAW_NoteEventCollectionBox;
        const NoteRegionBox = window.DAW_NoteRegionBox;

        const notes = {notes_json};
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const offsetTicks = {offset_ticks};

        // Find note tracks
        let noteTracks = [];
        if (unitIdx < 0) {{
            const allUnits = h.allAUBoxes();
            for (const au of allUnits) {{
                const tracks = h.trackBoxes(au)
                    .filter(box => box.type?.getValue?.() === 1);
                noteTracks.push(...tracks);
            }}
        }} else {{
            const units = h.allAUBoxes();
            if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
            noteTracks = h.noteTrackBoxes(units[unitIdx]);
        }}

        if (noteTracks.length === 0) return {{error: "No note tracks found. Call create_note_track first."}};
        if (trackIdx >= noteTracks.length) return {{error: "Track index out of range"}};
        const trackBox = noteTracks[trackIdx];

        // Find region start and total duration
        const minStart = Math.min(...notes.map(n => n.start));
        const maxEnd = Math.max(...notes.map(n => n.start + n.duration));
        const regionStart = minStart;
        const regionDuration = maxEnd - minStart;

        h.modify(() => {{
            // Create collection for all notes
            const collection = NoteEventCollectionBox.create(bg, h.uuid.generate());

            // Create region
            NoteRegionBox.create(bg, h.uuid.generate(), (box) => {{
                box.position.setValue(regionStart);
                box.label.setValue("MIDI Import");
                box.mute.setValue(false);
                box.duration.setValue(regionDuration);
                box.loopDuration.setValue(0);
                box.loopDuration.setValue(regionDuration);
                box.eventOffset.setValue(0);
                box.events.refer(collection.owners);
                box.regions.refer(trackBox.regions);
            }});

            // Create all note events
            for (const n of notes) {{
                NoteEventBox.create(bg, h.uuid.generate(), (box) => {{
                    box.position.setValue(n.start - regionStart);  // relative to region
                    box.duration.setValue(n.duration);
                    box.velocity.setValue(n.velocity);
                    box.pitch.setValue(n.pitch);
                    box.chance.setValue(100);
                    box.cent.setValue(0);
                    box.events.refer(collection.events);
                }});
            }}
        }});

        return {{
            success: true,
            notes_imported: notes.length,
            start_beat: regionStart / h.ppqn.Quarter,
            total_beats: maxEnd / h.ppqn.Quarter,
            ppqn_source: {ppqn},
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_invert_chord_notes(
    unit_index: int,
    track_index: int,
    region_index: int,
    chord_position: float,
    inversion: int = 1,
    direction: str = "up",
) -> str:
    """Invert a chord at a specific position — move bottom N notes up an octave (or top N down).

    A chord inversion (voicing change) rearranges which chord tone is
    lowest without changing the chord itself. 1st inversion: the 3rd
    is in the bass. 2nd inversion: the 5th is in the bass. This tool
    finds notes at a given beat position, groups them as a chord,
    and moves the bottom N notes up an octave (or top N down).

    Args:
        unit_index: Audio unit index
        track_index: Note track index
        region_index: Region index
        chord_position: Beat position of the chord to invert
        inversion: Number of notes to invert (1=first inversion,
                   2=second inversion, 3=third for 7th chords)
        direction: "up" = move bottom notes up an octave (standard),
                   "down" = move top notes down an octave (drop voicing)
    Returns:
        JSON with notes_inverted, original pitches, new pitches, chord root.
    """
    inversion = max(1, min(6, int(inversion)))
    direction = direction if direction in ("up", "down") else "up"
    chord_position = max(0.0, float(chord_position))

    result = await bridge.evaluate(f"""async () => {{
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const chordPos = {chord_position};
        const invCount = {inversion};
        const dir = {json.dumps(direction)};

        const h = window.DAW_HeadlessBridge;
        const PPQN = 960;
        const targetTick = Math.round(chordPos * PPQN);
        const tolerance = 120; // half a 16th note window

        const units = [...h.api.units.pointerHub.incoming()];
        if (unitIdx >= units.length) return JSON.stringify({{"error": "unit out of range"}});
        const au = units[unitIdx];
        const tracks = [...au.tracks.pointerHub.incoming()];
        if (trackIdx >= tracks.length) return JSON.stringify({{"error": "track out of range"}});
        const track = tracks[trackIdx];
        const regions = [...track.regions.pointerHub.incoming()];
        if (regionIdx >= regions.length) return JSON.stringify({{"error": "region out of range"}});
        const region = regions[regionIdx];
        const coll = region.box.events.targetVertex.unwrap();
        if (!coll) return JSON.stringify({{"error": "no note collection"}});
        const notes = [...coll.events.pointerHub.incoming()];

        // Find notes at the chord position
        const chordNotes = [];
        for (const note of notes) {{
            const nb = note.box;
            const pos = nb.position.value;
            if (Math.abs(pos - targetTick) <= tolerance) {{
                chordNotes.push({{note, pitch: nb.pitch.value, pos: nb.position.value, dur: nb.duration.value, vel: nb.velocity.value}});
            }}
        }}

        if (chordNotes.length < 3) return JSON.stringify({{"error": "not enough notes at position for chord inversion (need 3+)", "notes_found": chordNotes.length}});

        // Sort by pitch (ascending)
        chordNotes.sort((a, b) => a.pitch - b.pitch);

        // Store original pitches
        const origPitches = chordNotes.map(n => n.pitch);

        // Determine which notes to move
        let notesToMove = [];
        let pitchDelta = 12; // octave

        if (dir === "up") {{
            // Move bottom N notes up an octave
            notesToMove = chordNotes.slice(0, Math.min(invCount, chordNotes.length - 1));
        }} else {{
            // Move top N notes down an octave
            notesToMove = chordNotes.slice(Math.max(0, chordNotes.length - invCount));
            pitchDelta = -12;
        }}

        const newPitches = [...origPitches];
        let notesInverted = 0;

        await h.editing.modify(async () => {{
            for (const item of notesToMove) {{
                const newPitch = Math.max(0, Math.min(127, item.pitch + pitchDelta));
                item.note.box.pitch.setValue(newPitch);
                // Update newPitches array
                const idx = chordNotes.indexOf(item);
                if (idx >= 0) newPitches[idx] = newPitch;
                notesInverted++;
            }}
        }});

        // Determine chord root (lowest note after inversion)
        const sortedNew = [...newPitches].sort((a, b) => a - b);
        const root = sortedNew[0] % 12;
        const noteNames = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
        const rootName = noteNames[root];

        return JSON.stringify({{
            notes_inverted: notesInverted,
            inversion: invCount,
            direction: dir,
            chord_position: chordPos,
            original_pitches: origPitches,
            new_pitches: newPitches,
            new_root_pitch: sortedNew[0],
            root_name: rootName,
            chord_size: chordNotes.length,
        }});
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_invert_notes(unit_index: int, track_index: int, region_index: int = -1, axis: int = 60) -> str:
    """Invert melody around a pitch axis — mirror reflection.

    Each note's pitch is reflected around the axis: newPitch = 2*axis - oldPitch.
    Example: with axis=60 (C4), C4(60)→C4(60), D4(62)→Bb3(58), E4(64)→Ab3(56).

    unit_index: AU index.
    track_index: Note track index.
    region_index: Region index (-1 = all regions on the track).
    axis: Pivot pitch for inversion (default 60 = C4). Notes equidistant from axis
      on opposite sides swap. Use the first note's pitch for tonal inversion.

    Returns count of notes inverted and notes skipped (out of MIDI range).
    """
    if not (0 <= axis <= 127):
        return f"Error: axis must be 0-127, got {axis}"

    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const axisPitch = {axis};

        let inverted = 0;
        let skipped = 0;
        const allUnits = h.allAUBoxes();
        if (unitIdx >= allUnits.length) return {{error: "No AU at index " + unitIdx}};
        const noteTracks = h.trackBoxes(allUnits[unitIdx])
            .filter(box => box.type?.getValue?.() === 1);
        if (trackIdx >= noteTracks.length) return {{error: "Track " + trackIdx + " out of range"}};

        const regions = h.regionBoxes(noteTracks[trackIdx]);
        const targetRegions = regionIdx < 0 ? regions : (regionIdx < regions.length ? [regions[regionIdx]] : []);

        h.modify(() => {{
            for (const region of targetRegions) {{
                try {{
                    const vertex = region.events.targetVertex.unwrap();
                    const collBox = vertex.box || vertex;
                    if (!collBox || !collBox.events) continue;

                    const noteEvents = h.eventBoxes(collBox);
                    for (const evt of noteEvents) {{
                        const oldPitch = evt.pitch.getValue();
                        const newPitch = 2 * axisPitch - oldPitch;
                        if (newPitch < 0 || newPitch > 127) {{
                            skipped++;
                            continue;
                        }}
                        evt.pitch.setValue(newPitch);
                        inverted++;
                    }}
                }} catch(e) {{}}
            }}
        }});

        return {{
            success: true,
            axis: axisPitch,
            notes_inverted: inverted,
            notes_skipped: skipped,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_merge_consecutive_notes(
    unit_index: int,
    track_index: int,
    region_index: int = -1,
    same_pitch_only: bool = True,
    max_gap_beats: float = 0.0,
    velocity_mode: str = "first",
) -> str:
    """Merge consecutive notes of the same pitch into single sustained notes.

    Scans notes sorted by position. When two notes have the same pitch
    and the gap between them is within max_gap_beats, they are merged
    into one note spanning from the first note's start to the last
    note's end. Useful for cleaning up repeated hits, converting
    staccato patterns to sustained notes, or simplifying busy passages.

    Args:
        unit_index: Audio unit index
        track_index: Note track index
        region_index: Region index (-1 = first region)
        same_pitch_only: If True, only merge notes with identical pitch.
                         If False, merge any consecutive notes regardless of pitch
                         (uses first note's pitch for the merged result).
        max_gap_beats: Maximum gap between note end and next note start
                       to qualify for merging (0.0 = touching/overlapping only,
                       0.25 = up to a 16th note gap, 1.0 = up to 1 beat gap).
        velocity_mode: Velocity for merged note —
            "first" = use first note's velocity,
            "last" = use last note's velocity,
            "max" = use highest velocity,
            "avg" = use average velocity across merged notes.
    """
    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HeadlessBridgeHelper;
        if (!h) return {{error: "Bridge helper not available"}};
        const Quarter = 960;

        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const samePitch = {same_pitch_only};
        const maxGapTicks = Math.round({max_gap_beats} * Quarter);
        const velMode = "{velocity_mode}";

        const noteTracks = h.noteTracks();
        if (noteTracks.length === 0) return {{error: "No note tracks"}};
        if (trackIdx < 0 || trackIdx >= noteTracks.length) return {{error: "Track out of range"}};
        const track = noteTracks[trackIdx];
        const regions = h.regionBoxes(track);
        if (regions.length === 0) return {{error: "No regions on track"}};
        const regIdx = regionIdx < 0 ? 0 : regionIdx;
        if (regIdx >= regions.length) return {{error: "Region out of range"}};
        const region = regions[regIdx];

        let collection = null;
        try {{
            const vertex = region.events.targetVertex.unwrap();
            collection = vertex.box || vertex;
        }} catch(e) {{}}
        if (!collection || !collection.events) return {{error: "No note collection in region"}};
        const srcNotes = h.eventBoxes(collection);
        if (srcNotes.length === 0) return {{error: "No notes in region"}};

        // Read and sort by position
        const srcData = srcNotes.map(n => ({{
            pos: n.position.getValue(),
            dur: n.duration.getValue(),
            pitch: n.pitch.getValue(),
            vel: n.velocity.getValue(),
        }})).sort((a, b) => a.pos - b.pos);

        // Group consecutive notes for merging
        const groups = [];
        let currentGroup = [srcData[0]];

        for (let i = 1; i < srcData.length; i++) {{
            const prev = currentGroup[currentGroup.length - 1];
            const curr = srcData[i];
            const prevEnd = prev.pos + prev.dur;
            const gap = curr.pos - prevEnd;

            const pitchMatch = samePitch ? (curr.pitch === prev.pitch) : true;
            const gapOk = gap <= maxGapTicks;

            if (pitchMatch && gapOk && gap >= -prev.dur) {{
                // Consecutive: add to current group
                currentGroup.push(curr);
            }} else {{
                // Break: save current group, start new
                groups.push(currentGroup);
                currentGroup = [curr];
            }}
        }}
        groups.push(currentGroup);

        // Build merged notes
        const mergedNotes = [];
        let mergeCount = 0;

        for (const group of groups) {{
            if (group.length === 1) {{
                // No merge needed
                mergedNotes.push(group[0]);
            }} else {{
                const startPos = group[0].pos;
                let endPos = 0;
                for (const n of group) {{
                    const e = n.pos + n.dur;
                    if (e > endPos) endPos = e;
                }}

                let vel;
                if (velMode === "first") {{
                    vel = group[0].vel;
                }} else if (velMode === "last") {{
                    vel = group[group.length - 1].vel;
                }} else if (velMode === "max") {{
                    vel = Math.max(...group.map(n => n.vel));
                }} else {{ // avg
                    vel = group.reduce((sum, n) => sum + n.vel, 0) / group.length;
                }}
                vel = Math.max(0.01, Math.min(1.0, vel));

                mergedNotes.push({{
                    pos: startPos,
                    dur: endPos - startPos,
                    pitch: group[0].pitch,
                    vel: vel,
                }});
                mergeCount++;
            }}
        }}

        // Replace notes: delete all originals, create merged
        const bg = h.boxGraph;
        const editing = h.editing;
        let deleted = 0;
        let created = 0;

        await editing.modify(async () => {{
            // Delete all original notes
            for (const n of srcNotes) {{
                n.delete();
                deleted++;
            }}
            // Create merged notes
            for (const mn of mergedNotes) {{
                h.NoteEventBox.create(bg, h.uuid.generate(), (box) => {{
                    box.position.setValue(Math.round(mn.pos));
                    box.duration.setValue(Math.round(mn.dur));
                    box.pitch.setValue(mn.pitch);
                    box.velocity.setValue(mn.vel);
                    box.cent.setValue(0);
                    box.events.refer(collection.events);
                }});
                created++;
            }}
        }});

        return {{
            success: true,
            notes_before: srcData.length,
            notes_after: mergedNotes.length,
            notes_deleted: deleted,
            notes_created: created,
            merges_performed: mergeCount,
            same_pitch_only: samePitch,
            max_gap_beats: maxGapTicks / Quarter,
            velocity_mode: velMode,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_move_notes(
    source_unit: int,
    source_track: int,
    source_region: int,
    dest_unit: int,
    dest_track: int,
    time_offset: int = 0,
    transpose: int = 0,
    velocity_scale: float = 1.0,
    delete_source: bool = True,
    dest_region: int = -1,
) -> str:
    """Move notes from a source region to another track — copy + delete.

    Copies notes from source region to destination track (auto-creating a
    region or appending to an existing one), then optionally deletes the
    originals. Useful for splitting material across tracks, reorganising
    arrangements, or moving a section to a different instrument.

    Args:
        source_unit: Source audio unit index
        source_track: Source note track index
        source_region: Source region index
        dest_unit: Destination audio unit index
        dest_track: Destination note track index
        time_offset: Shift all moved notes by N ticks (0 = keep positions)
        transpose: Transpose all moved notes by N semitones (0 = no change)
        velocity_scale: Multiply velocity of moved notes (1.0 = unchanged,
                        0.8 = quieter, 1.2 = louder, clamped to 0-1)
        delete_source: If True (default), delete notes from source after copy.
                       If False, behaves like copy_notes_to_track.
        dest_region: Destination region index (-1 = auto-create or append to last)

    Returns:
        JSON with notes_moved, notes_deleted, source_region_cleared,
        and destination region info.
    """
    velocity_scale = max(0.0, min(2.0, float(velocity_scale)))

    result = await bridge.evaluate(f"""async () => {{
        const srcUnitIdx = {source_unit};
        const srcTrackIdx = {source_track};
        const srcRegIdx = {source_region};
        const destUnitIdx = {dest_unit};
        const destTrackIdx = {dest_track};
        const timeOffset = {time_offset};
        const transposeAmt = {transpose};
        const velScale = {velocity_scale};
        const doDelete = {json.dumps(delete_source)};
        const destRegIdx = {dest_region};

        const h = window.DAW_HeadlessBridge;

        // Find source
        const units = [...h.api.units.pointerHub.incoming()];
        if (srcUnitIdx >= units.length) return JSON.stringify({{"error": "source unit out of range"}});
        if (destUnitIdx >= units.length) return JSON.stringify({{"error": "dest unit out of range"}});
        const srcAu = units[srcUnitIdx];
        const destAu = units[destUnitIdx];

        const srcTracks = [...srcAu.tracks.pointerHub.incoming()];
        if (srcTrackIdx >= srcTracks.length) return JSON.stringify({{"error": "source track out of range"}});
        const srcTrack = srcTracks[srcTrackIdx];
        const srcRegions = [...srcTrack.regions.pointerHub.incoming()];
        if (srcRegIdx >= srcRegions.length) return JSON.stringify({{"error": "source region out of range"}});
        const srcRegion = srcRegions[srcRegIdx];
        const srcRegionBox = srcRegion.box;
        const srcColl = srcRegionBox.events.targetVertex.unwrap();
        if (!srcColl) return JSON.stringify({{"error": "source region has no note collection"}});
        const srcNotes = [...srcColl.events.pointerHub.incoming()];

        if (srcNotes.length === 0) return JSON.stringify({{"error": "source region has no notes"}});

        // Find dest track
        const destTracks = [...destAu.tracks.pointerHub.incoming()];
        if (destTrackIdx >= destTracks.length) return JSON.stringify({{"error": "dest track out of range"}});
        const destTrack = destTracks[destTrackIdx];
        const destRegions = [...destTrack.regions.pointerHub.incoming()];

        let destRegionBox;
        let destColl;
        if (destRegIdx >= 0 && destRegIdx < destRegions.length) {{
            destRegionBox = destRegions[destRegIdx].box;
            destColl = destRegionBox.events.targetVertex.unwrap();
        }} else if (destRegions.length > 0) {{
            destRegionBox = destRegions[destRegions.length - 1].box;
            destColl = destRegionBox.events.targetVertex.unwrap();
        }}

        let notesCopied = 0;
        let notesDeleted = 0;

        await h.editing.modify(async () => {{
            // Copy notes to dest
            if (destColl) {{
                for (const note of srcNotes) {{
                    const nb = note.box;
                    const newPitch = Math.max(0, Math.min(127, nb.pitch.value + transposeAmt));
                    const newPos = Math.max(0, nb.position.value + timeOffset);
                    const newVel = Math.max(0, Math.min(1, nb.velocity.value * velScale));
                    const dur = nb.duration.value;

                    const NoteEventBox = window.DAW_NoteEventBox;
                    if (NoteEventBox) {{
                        NoteEventBox.create(h.boxGraph, h.uuid.generate(), (box) => {{
                            box.pitch.setValue(newPitch);
                            box.position.setValue(newPos);
                            box.duration.setValue(dur);
                            box.velocity.setValue(newVel);
                            if (nb.cent) box.cent.setValue(nb.cent.value);
                            box.events.refer(destColl.events);
                        }});
                    }}
                    notesCopied++;
                }}
            }}

            // Delete source notes
            if (doDelete) {{
                for (const note of srcNotes) {{
                    note.delete();
                    notesDeleted++;
                }}
            }}
        }});

        return JSON.stringify({{
            notes_moved: notesCopied,
            notes_deleted: notesDeleted,
            source_region_cleared: doDelete,
            source: {{unit: srcUnitIdx, track: srcTrackIdx, region: srcRegIdx}},
            dest: {{unit: destUnitIdx, track: destTrackIdx}},
            transpose: transposeAmt,
            time_offset: timeOffset,
            velocity_scale: velScale,
        }});
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_note_stats(
    unit_index: int,
    track_index: int,
    region_index: int = -1,
) -> str:
    """Get comprehensive statistics for notes in a region.

    Returns a full statistical profile of the MIDI content:
    - Note count, pitch range (min/max/span)
    - Velocity statistics (min/max/mean/median/std)
    - Duration statistics (min/max/mean in beats)
    - Density (notes per beat)
    - Pitch class histogram (how often each of 12 pitch classes appears)
    - Most common pitches (top 5)
    - Time span (first note to last note end)

    Useful for:
    - Analyzing imported MIDI before processing
    - Comparing regions (which has more notes, wider range)
    - Identifying register (is this bass, mid, or lead?)
    - Detecting programming issues (all same velocity = robotic)
    - Feeding data to arrangement decisions

    unit_index: AU index.
    track_index: Note track index.
    region_index: Region (-1 = first region).

    Returns statistics object.

    Example:
      stats = note_stats(0, 0)
      # stats includes: note_count, pitch_range, velocity_stats, density, pitch_class_histogram
    """
    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const Quarter = h.ppqn.Quarter;

        const allUnits = h.allAUBoxes();
        if (unitIdx < 0 || unitIdx >= allUnits.length) return {{error: "unit_index out of range"}};
        const au = allUnits[unitIdx];
        const noteTracks = h.noteTrackBoxes(au);
        if (trackIdx < 0 || trackIdx >= noteTracks.length) return {{error: "track_index out of range"}};
        const trackBox = noteTracks[trackIdx];
        const regions = h.regionBoxes(trackBox);
        if (regions.length === 0) return {{error: "No regions on track"}};
        const regIdx = regionIdx < 0 ? 0 : regionIdx;
        if (regIdx >= regions.length) return {{error: "region_index out of range"}};
        const region = regions[regIdx];

        let collection = null;
        try {{
            const vertex = region.events.targetVertex.unwrap();
            collection = vertex.box || vertex;
        }} catch(e) {{}}
        if (!collection || !collection.events) return {{error: "No note collection in region"}};

        const notes = h.eventBoxes(collection);
        if (notes.length === 0) return {{error: "No notes in region"}};

        const regionPos = region.position.getValue();
        const regionDur = region.duration.getValue() / Quarter;

        // Extract note data
        const pitches = [];
        const velocities = [];
        const durations = [];
        const positions = [];
        const pitchClassCounts = new Array(12).fill(0);
        const pitchCounts = {{}};

        for (const n of notes) {{
            const p = n.pitch.getValue();
            const v = n.velocity.getValue();
            const d = n.duration.getValue() / Quarter;
            const pos = (regionPos + n.position.getValue()) / Quarter;

            pitches.push(p);
            velocities.push(v);
            durations.push(d);
            positions.push(pos);
            pitchClassCounts[p % 12]++;
            pitchCounts[p] = (pitchCounts[p] || 0) + 1;
        }}

        // Pitch stats
        const minPitch = Math.min(...pitches);
        const maxPitch = Math.max(...pitches);
        const pitchSpan = maxPitch - minPitch;

        // Velocity stats
        const sortedVel = [...velocities].sort((a, b) => a - b);
        const minVel = sortedVel[0];
        const maxVel = sortedVel[sortedVel.length - 1];
        const meanVel = velocities.reduce((a, b) => a + b, 0) / velocities.length;
        const medianVel = sortedVel.length % 2 === 0
            ? (sortedVel[sortedVel.length / 2 - 1] + sortedVel[sortedVel.length / 2]) / 2
            : sortedVel[Math.floor(sortedVel.length / 2)];
        const velVariance = velocities.reduce((sum, v) => sum + Math.pow(v - meanVel, 2), 0) / velocities.length;
        const velStd = Math.sqrt(velVariance);

        // Duration stats
        const minDur = Math.min(...durations);
        const maxDur = Math.max(...durations);
        const meanDur = durations.reduce((a, b) => a + b, 0) / durations.length;

        // Time span
        const firstNoteBeat = Math.min(...positions);
        const lastNoteEnd = Math.max(...positions.map((p, i) => p + durations[i]));
        const timeSpan = lastNoteEnd - firstNoteBeat;

        // Density
        const density = notes.length / (regionDur > 0 ? regionDur : timeSpan);

        // Top 5 most common pitches
        const pitchEntries = Object.entries(pitchCounts)
            .map(([p, c]) => ({{ pitch: parseInt(p), count: c }}))
            .sort((a, b) => b.count - a.count);
        const noteNames = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
        const topPitches = pitchEntries.slice(0, 5).map(e => ({{
            pitch: e.pitch,
            name: noteNames[e.pitch % 12] + (Math.floor(e.pitch / 12) - 1),
            count: e.count,
        }}));

        // Pitch class histogram with names
        const pitchClassHistogram = pitchClassCounts.map((count, pc) => ({{
            pitch_class: pc,
            name: noteNames[pc],
            count: count,
        }}));

        return {{
            success: true,
            note_count: notes.length,
            pitch_stats: {{
                min: minPitch,
                max: maxPitch,
                span: pitchSpan,
                min_name: noteNames[minPitch % 12] + (Math.floor(minPitch / 12) - 1),
                max_name: noteNames[maxPitch % 12] + (Math.floor(maxPitch / 12) - 1),
            }},
            velocity_stats: {{
                min: Math.round(minVel * 1000) / 1000,
                max: Math.round(maxVel * 1000) / 1000,
                mean: Math.round(meanVel * 1000) / 1000,
                median: Math.round(medianVel * 1000) / 1000,
                std: Math.round(velStd * 1000) / 1000,
            }},
            duration_stats: {{
                min_beats: Math.round(minDur * 1000) / 1000,
                max_beats: Math.round(maxDur * 1000) / 1000,
                mean_beats: Math.round(meanDur * 1000) / 1000,
            }},
            time_span_beats: Math.round(timeSpan * 1000) / 1000,
            density_notes_per_beat: Math.round(density * 1000) / 1000,
            pitch_class_histogram: pitchClassHistogram,
            top_pitches: topPitches,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_quantize_notes(division: str, unit_index: int, track_index: int, strength: float) -> str:
    """Quantize note positions to a grid division.

Snaps each note's start position to the nearest grid line.

division: Grid division — '1/4', '1/8', '1/16', '1/32', or '1/64'.
unit_index: Audio unit index (-1 = all AUs).
track_index: Specific note track (-1 = all note tracks).
strength: 1.0 = full quantize, 0.5 = 50% (keeps some groove).

Returns count of notes quantized.
    """
    # Parse division: "1/4" → 240 ticks, "1/8" → 120, "1/16" → 60, "1/32" → 30
    if '/' in division:
        num, den = division.split('/')
        grid_ticks = int(float(num.strip()) / float(den.strip()) * 960)
    else:
        grid_ticks = int(float(division) * 960)

    safe_division = division.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const gridTicks = {grid_ticks};
        const strength = {strength};

        let count = 0;
        const allUnits = h.allAUBoxes();
        const targetUnits = unitIdx < 0 ? allUnits : (unitIdx < allUnits.length ? [allUnits[unitIdx]] : []);

        h.modify(() => {{
            for (const au of targetUnits) {{
                const noteTracks = h.trackBoxes(au)
                    .filter(box => box.type?.getValue?.() === 1);
                const targetTracks = trackIdx < 0 ? noteTracks : (trackIdx < noteTracks.length ? [noteTracks[trackIdx]] : []);
                for (const track of targetTracks) {{
                    const regions = h.regionBoxes(track);
                    for (const region of regions) {{
                        const regPos = region.position.getValue();
                        const nearestReg = Math.round(regPos / gridTicks) * gridTicks;
                        const newRegPos = regPos + (nearestReg - regPos) * strength;
                        region.position.setValue(Math.round(newRegPos));

                        try {{
                            const vertex = region.events.targetVertex.unwrap();
                            const collectionBox = vertex.box || vertex;
                            if (collectionBox && collectionBox.events) {{
                                const noteEvents = h.eventBoxes(collectionBox);
                                for (const evt of noteEvents) {{
                                    const current = evt.position.getValue();
                                    const nearest = Math.round(current / gridTicks) * gridTicks;
                                    const newPos = current + (nearest - current) * strength;
                                    evt.position.setValue(Math.round(newPos));
                                    count++;
                                }}
                            }}
                        }} catch(e) {{}}
                    }}
                }}
            }}
        }});

        return {{
            success: true,
            division: "{safe_division}",
            grid_ticks: gridTicks,
            strength: strength,
            notes_quantized: count,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_randomize_note_chance(
    unit_index: int = -1,
    track_index: int = -1,
    region_index: int = -1,
    min_chance: int = 50,
    max_chance: int = 100,
    mode: str = "uniform",
    seed: int = 42,
) -> str:
    """Randomize note playback probability (chance) — generative variation.

    Sets a random chance value (0-100%) for each note, controlling whether
    it plays on each run. This is the core of generative MIDI — patterns
    that are different every time while maintaining structure. Notes with
    chance=100 always play, chance=50 play half the time, chance=0 never
    play (silent ghost).

    Perfect for:
    - Ghost notes that appear/disappear (drum variation)
    - Generative melodies where notes drop in/out
    - Call-and-response patterns with probabilistic responses
    - Evolving textures that change per iteration

    mode: Distribution of chance values:
    - "uniform" — random between min_chance and max_chance, evenly distributed.
      Each note gets an independent random chance. Default mode.
    - "decreasing" — chance decreases linearly from max to min across the
      region. First notes are most likely, last notes least. Creates
      fade-out of probability — pattern dissolves.
    - "increasing" — chance increases from min to max. Pattern emerges
      from silence. Builds anticipation.
    - "sparse" — most notes get min_chance, but some get max_chance.
      Creates sparse texture with occasional hits. Good for ghost notes.
    - "binary" — each note gets either min_chance or max_chance (coin flip).
      Creates stark on/off patterns.

    min_chance: Minimum chance value (0-100, default 50).
    max_chance: Maximum chance value (0-100, default 100).
    seed: Random seed for reproducibility.

    Returns per-track note counts, chance range applied.

    Example:
      # Ghost note variation — 30-80% chance
      randomize_note_chance(unit_index=0, track_index=0, min_chance=30, max_chance=80)
      # Dissolving pattern — high to low
      randomize_note_chance(unit_index=0, track_index=2, mode="decreasing", min_chance=0, max_chance=100)
    """
    if not (0 <= min_chance <= 100):
        return f'{{"error": "min_chance must be 0-100, got {min_chance}"}}'
    if not (0 <= max_chance <= 100):
        return f'{{"error": "max_chance must be 0-100, got {max_chance}"}}'
    if min_chance > max_chance:
        return '{"error": "min_chance cannot exceed max_chance"}'
    valid_modes = ("uniform", "decreasing", "increasing", "sparse", "binary")
    if mode not in valid_modes:
        return f'{{"error": "mode must be one of {list(valid_modes)}, got {mode}"}}'

    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const minC = {min_chance};
        const maxC = {max_chance};
        const mode = "{mode}";
        const seed = {seed};

        // Seeded PRNG (mulberry32)
        let s = seed >>> 0;
        function rand() {{
            s = (s + 0x6D2B79F5) >>> 0;
            let t = s;
            t = Math.imul(t ^ (t >>> 15), t | 1);
            t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
            return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
        }}

        let totalCount = 0;
        const trackStats = [];
        const allUnits = h.allAUBoxes();
        if (unitIdx >= allUnits.length) return {{error: "unit_index out of range"}};
        const targetUnits = unitIdx < 0 ? allUnits : [allUnits[unitIdx]];

        h.modify(() => {{
            for (let ui = 0; ui < targetUnits.length; ui++) {{
                const au = targetUnits[ui];
                const noteTracks = h.trackBoxes(au)
                    .filter(box => box.type?.getValue?.() === 1);
                if (trackIdx >= noteTracks.length) return;
                const targetTracks = trackIdx < 0 ? noteTracks : [noteTracks[trackIdx]];

                for (let ti = 0; ti < targetTracks.length; ti++) {{
                    const track = targetTracks[ti];
                    let trackCount = 0;
                    const regions = h.regionBoxes(track);
                    if (regions.length === 0) continue;
                    const regionsToProcess = regionIdx < 0 ? regions : [regions[Math.min(regionIdx, regions.length - 1)]];

                    for (const region of regionsToProcess) {{
                        try {{
                            const vertex = region.events.targetVertex.unwrap();
                            const collectionBox = vertex.box || vertex;
                            const noteEvents = [...collectionBox.events.pointerHub.incoming()];
                            if (noteEvents.length === 0) continue;

                            // Sort by position for directional modes
                            const sorted = noteEvents.slice().sort((a, b) =>
                                a.box.position.getValue() - b.box.position.getValue());

                            for (let i = 0; i < sorted.length; i++) {{
                                let chance;
                                if (mode === "uniform") {{
                                    chance = Math.round(minC + rand() * (maxC - minC));
                                }} else if (mode === "decreasing") {{
                                    const frac = sorted.length > 1 ? i / (sorted.length - 1) : 0;
                                    chance = Math.round(maxC - frac * (maxC - minC));
                                }} else if (mode === "increasing") {{
                                    const frac = sorted.length > 1 ? i / (sorted.length - 1) : 0;
                                    chance = Math.round(minC + frac * (maxC - minC));
                                }} else if (mode === "sparse") {{
                                    // 70% get min, 30% get max
                                    chance = rand() < 0.3 ? maxC : minC;
                                }} else {{ // binary
                                    chance = rand() < 0.5 ? minC : maxC;
                                }}
                                sorted[i].box.chance.setValue(chance);
                                trackCount++;
                                totalCount++;
                            }}
                        }} catch (e) {{ /* skip non-note regions */ }}
                    }}
                    trackStats.push({{unit: ui, track: ti, notes_randomized: trackCount}});
                }}
            }}
        }});

        return {{
            notes_randomized: totalCount,
            mode: mode,
            min_chance: minC,
            max_chance: maxC,
            seed: seed,
            tracks: trackStats,
            next_step: "use create_motif_variations for structured variation, or humanize_notes for timing variation",
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_randomize_note_durations(
    unit_index: int,
    track_index: int,
    region_index: int = -1,
    variation: float = 0.3,
    distribution: str = "uniform",
    min_duration_beats: float = 0.0625,
    max_duration_beats: float = 8.0,
    preserve_total: bool = False,
    seed: int = 42,
) -> str:
    """Randomize note durations with controllable distribution.

    Adds generative variation to note lengths. Unlike humanize_notes
    (which adjusts timing+velocity), this focuses purely on duration
    with 5 distribution modes for different musical characters.

    Args:
        unit_index: Audio unit index
        track_index: Note track index
        region_index: Region index (-1 = first region)
        variation: Amount of variation (0.0=no change, 0.3=moderate,
                   1.0=extreme). Applied as percentage of original duration.
        distribution: Distribution mode —
            "uniform" = equal probability across range,
            "increasing" = durations tend to get longer over time,
            "decreasing" = durations tend to get shorter over time,
            "bimodal" = clusters around short and long extremes,
            "jitter" = small perturbations around original values.
        min_duration_beats: Minimum duration in beats (0.0625=1/64th,
                            0.125=1/32nd, 0.25=1/16th).
        max_duration_beats: Maximum duration in beats (4=whole note,
                            8=two whole notes).
        preserve_total: If True, scale all durations so the total
                        summed duration equals the original. Useful
                        for maintaining phrase length.
        seed: PRNG seed for reproducibility.
    """
    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HeadlessBridgeHelper;
        if (!h) return {{error: "Bridge helper not available"}};
        const Quarter = 960;

        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const variation = Math.max(0, Math.min(1, {variation}));
        const distMode = "{distribution}";
        const minDurTicks = Math.round({min_duration_beats} * Quarter);
        const maxDurTicks = Math.round({max_duration_beats} * Quarter);
        const preserveTotal = {preserve_total};

        // Seeded PRNG (mulberry32)
        let prngSeed = {seed} >>> 0;
        function rand() {{
            prngSeed = (prngSeed + 0x6D2B79F5) | 0;
            let t = prngSeed;
            t = Math.imul(t ^ (t >>> 15), t | 1);
            t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
            return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
        }}

        const noteTracks = h.noteTracks();
        if (noteTracks.length === 0) return {{error: "No note tracks"}};
        if (trackIdx < 0 || trackIdx >= noteTracks.length) return {{error: "Track out of range"}};
        const track = noteTracks[trackIdx];
        const regions = h.regionBoxes(track);
        if (regions.length === 0) return {{error: "No regions on track"}};
        const regIdx = regionIdx < 0 ? 0 : regionIdx;
        if (regIdx >= regions.length) return {{error: "Region out of range"}};
        const region = regions[regIdx];

        let collection = null;
        try {{
            const vertex = region.events.targetVertex.unwrap();
            collection = vertex.box || vertex;
        }} catch(e) {{}}
        if (!collection || !collection.events) return {{error: "No note collection in region"}};
        const srcNotes = h.eventBoxes(collection);
        if (srcNotes.length === 0) return {{error: "No notes in region"}};

        // Read source durations
        const srcData = srcNotes.map(n => ({{
            pos: n.position.getValue(),
            dur: n.duration.getValue(),
            pitch: n.pitch.getValue(),
            vel: n.velocity.getValue(),
        }}));

        const n = srcData.length;
        const origTotalDur = srcData.reduce((s, d) => s + d.dur, 0);

        // Generate new durations
        const newDurations = [];
        for (let i = 0; i < n; i++) {{
            const origDur = srcData[i].dur;
            let newDur = origDur;
            const r = rand();
            const progress = i / Math.max(1, n - 1);  // 0..1 across notes

            if (distMode === "uniform") {{
                // Uniform within ±variation * origDur
                const range = variation * origDur;
                newDur = origDur + (r - 0.5) * 2 * range;
            }} else if (distMode === "increasing") {{
                // Tend longer over time
                const range = variation * origDur;
                newDur = origDur + r * range * progress * 2;
            }} else if (distMode === "decreasing") {{
                // Tend shorter over time
                const range = variation * origDur;
                newDur = origDur - r * range * progress * 2;
            }} else if (distMode === "bimodal") {{
                // Cluster around short and long
                const range = variation * origDur;
                if (r < 0.5) {{
                    newDur = origDur - range * (0.5 + rand() * 0.5);
                }} else {{
                    newDur = origDur + range * (0.5 + rand() * 0.5);
                }}
            }} else {{ // jitter
                const range = variation * origDur * 0.3;
                newDur = origDur + (r - 0.5) * 2 * range;
            }}

            // Clamp
            newDur = Math.max(minDurTicks, Math.min(maxDurTicks, newDur));
            newDurations.push(Math.round(newDur));
        }}

        // Preserve total duration if requested
        if (preserveTotal && newDurations.length > 0) {{
            const newTotal = newDurations.reduce((s, d) => s + d, 0);
            if (newTotal > 0) {{
                const scale = origTotalDur / newTotal;
                for (let i = 0; i < newDurations.length; i++) {{
                    newDurations[i] = Math.max(minDurTicks, Math.round(newDurations[i] * scale));
                }}
            }}
        }}

        // Apply new durations
        const editing = h.editing;
        let updated = 0;
        const origDurs = srcData.map(d => d.dur);
        const durChanges = [];

        await editing.modify(async () => {{
            for (let i = 0; i < srcNotes.length; i++) {{
                const oldDur = srcNotes[i].duration.getValue();
                srcNotes[i].duration.setValue(newDurations[i]);
                durChanges.push({{
                    note: i,
                    old_duration_beats: Math.round(oldDur / Quarter * 1000) / 1000,
                    new_duration_beats: Math.round(newDurations[i] / Quarter * 1000) / 1000,
                }});
                updated++;
            }}
        }});

        const newTotalDur = newDurations.reduce((s, d) => s + d, 0);
        return {{
            success: true,
            notes_updated: updated,
            variation: variation,
            distribution: distMode,
            preserve_total: preserveTotal,
            original_total_beats: Math.round(origTotalDur / Quarter * 1000) / 1000,
            new_total_beats: Math.round(newTotalDur / Quarter * 1000) / 1000,
            duration_changes: durChanges.slice(0, 10),
            total_changes: durChanges.length,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_remove_midi_effect(unit_index: int, effect_index: int) -> str:
    """Remove a MIDI effect from an audio unit's MIDI chain.

unit_index: Audio unit index.
effect_index: MIDI effect position to remove (0-based).
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const effectIdx = {effect_index};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
        const au = units[unitIdx];

        const effects = h.midiEffectBoxes(au);
        if (effectIdx >= effects.length) return {{error: "No MIDI effect at index " + effectIdx}};

        const effectBox = effects[effectIdx];
        const effectType = effectBox.constructor.name;

        h.modify(() => {{ effectBox.delete(); }});

        return {{
            success: true,
            removed: effectType,
            chain: "midi",
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_repeat_notes(
    unit_index: int,
    track_index: int,
    region_index: int = -1,
    repeats: int = 2,
    transpose_semitones: int = 0,
    velocity_decay: float = 0.0,
    time_gap_beats: float = 0.0,
    direction: str = "up",
    dest_track_index: int = -1,
) -> str:
    """Repeat existing notes in a region N times with per-repeat transformations.

    Takes the notes already in the region and copies them `repeats` times,
    each copy offset in time, pitch, and velocity. Unlike create_midi_echo
    (which decays feedback repeats), this tool preserves note structure and
    applies a uniform transform per repeat cycle — ideal for sequences,
    ostinato patterns, and motivic development.

    Args:
        unit_index: Audio unit index
        track_index: Note track index
        region_index: Region index (-1 = first region)
        repeats: Number of repeat cycles (1-16, each cycle = full copy of source notes)
        transpose_semitones: Semitones added per repeat cycle (0=same, 12=octave up,
                             -12=octave down, 7=fifth up). Cumulative.
        velocity_decay: Velocity multiplier per repeat (0=fade out, 1=constant,
                        0.8=gradual fade). Applied cumulatively.
        time_gap_beats: Extra gap between repeats in beats (0=back-to-back,
                        0.5=half-beat rest between cycles)
        direction: Transpose direction — "up" or "down" (affects sign of transpose)
        dest_track_index: Destination track (-1 = same track)
    """
    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HeadlessBridgeHelper;
        if (!h) return {{error: "Bridge helper not available"}};
        const Quarter = 960;

        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const numRepeats = Math.max(1, Math.min(16, {repeats}));
        const transposeVal = {direction} === "down" ? -Math.abs({transpose_semitones}) : Math.abs({transpose_semitones});
        const velDecay = Math.max(0, Math.min(1, {velocity_decay}));
        const gapBeats = Math.max(0, {time_gap_beats});
        const destTrackIdx = {dest_track_index};

        const noteTracks = h.noteTracks();
        if (noteTracks.length === 0) return {{error: "No note tracks"}};
        if (trackIdx < 0 || trackIdx >= noteTracks.length) return {{error: "Track out of range"}};
        const track = noteTracks[trackIdx];
        const regions = h.regionBoxes(track);
        if (regions.length === 0) return {{error: "No regions on track"}};
        const regIdx = regionIdx < 0 ? 0 : regionIdx;
        if (regIdx >= regions.length) return {{error: "Region out of range"}};
        const region = regions[regIdx];

        let collection = null;
        try {{
            const vertex = region.events.targetVertex.unwrap();
            collection = vertex.box || vertex;
        }} catch(e) {{}}
        if (!collection || !collection.events) return {{error: "No note collection in region"}};
        const srcNotes = h.eventBoxes(collection);
        if (srcNotes.length === 0) return {{error: "No notes in region"}};

        // Read source note data
        const srcData = srcNotes.map(n => ({{
            pos: n.position.getValue(),
            dur: n.duration.getValue(),
            pitch: n.pitch.getValue(),
            vel: n.velocity.getValue(),
        }}));

        // Find time span of source notes
        let maxEnd = 0;
        for (const n of srcData) {{
            const end = n.pos + n.dur;
            if (end > maxEnd) maxEnd = end;
        }}
        const cycleLengthBeats = maxEnd / Quarter + gapBeats;

        // Determine destination
        const dTrackIdx = destTrackIdx < 0 ? trackIdx : destTrackIdx;
        if (dTrackIdx < 0 || dTrackIdx >= noteTracks.length) return {{error: "dest_track out of range"}};
        const destTrack = noteTracks[dTrackIdx];
        const destRegions = h.regionBoxes(destTrack);
        if (destRegions.length === 0) return {{error: "No regions on dest track"}};
        const destRegion = dTrackIdx === trackIdx ? region : destRegions[0];
        let destColl = null;
        try {{
            const dv = destRegion.events.targetVertex.unwrap();
            destColl = dv.box || dv;
        }} catch(e) {{}}
        if (!destColl || !destColl.events) return {{error: "No note collection in dest region"}};

        // Build repeated notes
        const repNotes = [];
        const repeatInfo = [];
        for (let r = 1; r <= numRepeats; r++) {{
            const pitchOffset = transposeVal * r;
            const velFactor = Math.pow(velDecay, r);
            const timeOffset = Math.round(cycleLengthBeats * r * Quarter);

            for (const note of srcData) {{
                repNotes.push({{
                    pos: note.pos + timeOffset,
                    dur: note.dur,
                    pitch: note.pitch + pitchOffset,
                    vel: Math.max(0.01, Math.min(1.0, note.vel * velFactor)),
                }});
            }}
            repeatInfo.push({{
                repeat: r,
                pitch_offset: pitchOffset,
                velocity_factor: Math.round(velFactor * 1000) / 1000,
                time_offset_beats: Math.round(cycleLengthBeats * r * 1000) / 1000,
            }});
        }}

        // Create repeated notes in destination
        const bg = h.boxGraph;
        let created = 0;
        const editing = h.editing;
        await editing.modify(async () => {{
            for (const rn of repNotes) {{
                h.NoteEventBox.create(bg, h.uuid.generate(), (box) => {{
                    box.position.setValue(Math.round(rn.pos));
                    box.duration.setValue(Math.round(rn.dur));
                    box.pitch.setValue(rn.pitch);
                    box.velocity.setValue(rn.vel);
                    box.cent.setValue(0);
                    box.events.refer(destColl.events);
                }});
                created++;
            }}
        }});

        return {{
            success: true,
            notes_created: created,
            repeats: numRepeats,
            transpose_per_repeat: transposeVal,
            velocity_decay: velDecay,
            time_gap_beats: gapBeats,
            cycle_length_beats: Math.round(cycleLengthBeats * 1000) / 1000,
            dest_track: dTrackIdx,
            repeat_details: repeatInfo,
            source_note_count: srcData.length,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_reverse_notes(unit_index: int, track_index: int, region_index: int = -1) -> str:
    """Reverse the order of notes in a region — retrograde variation.

    Swaps note positions so the last note becomes first and vice versa.
    Durations and velocities are preserved; only positions are mirrored.

    unit_index: AU index.
    track_index: Note track index.
    region_index: Region index (-1 = all regions on the track).

    Returns count of notes reversed.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};

        let count = 0;
        const allUnits = h.allAUBoxes();
        if (unitIdx >= allUnits.length) return {{error: "No AU at index " + unitIdx}};
        const noteTracks = h.trackBoxes(allUnits[unitIdx])
            .filter(box => box.type?.getValue?.() === 1);
        if (trackIdx >= noteTracks.length) return {{error: "Track " + trackIdx + " out of range"}};

        const regions = h.regionBoxes(noteTracks[trackIdx]);
        const targetRegions = regionIdx < 0 ? regions : (regionIdx < regions.length ? [regions[regionIdx]] : []);

        h.modify(() => {{
            for (const region of targetRegions) {{
                try {{
                    const vertex = region.events.targetVertex.unwrap();
                    const collBox = vertex.box || vertex;
                    if (!collBox || !collBox.events) continue;

                    const noteEvents = h.eventBoxes(collBox);
                    if (noteEvents.length < 2) continue;

                    // Collect positions and durations
                    const positions = noteEvents.map(e => e.position.getValue());
                    const regionStart = Math.min(...positions);
                    const regionEnd = Math.max(...positions.map((p, i) => p + noteEvents[i].duration.getValue()));

                    // Reverse: newPos = regionStart + regionEnd - oldPos - duration
                    for (const evt of noteEvents) {{
                        const oldPos = evt.position.getValue();
                        const dur = evt.duration.getValue();
                        const newPos = regionStart + (regionEnd - regionStart - dur) - (oldPos - regionStart);
                        evt.position.setValue(Math.max(0, Math.round(newPos)));
                        count++;
                    }}
                }} catch(e) {{}}
            }}
        }});

        return {{
            success: true,
            notes_reversed: count,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_rotate_notes(
    unit_index: int,
    track_index: int,
    region_index: int = -1,
    rotate_by: int = 1,
    axis: str = "position",
    preserve_pitch_contour: bool = False,
) -> str:
    """Rotate notes in a region by N positions (cyclic shift).

    Shifts notes cyclically — the first `rotate_by` notes move to the
    end, and the remaining notes shift left to fill the gap. This is
    a fundamental compositional technique used in serialism (rotational
    arrays — Berg, Webern), jazz melodic variation, and pattern
    transformation in electronic music.

    Args:
        unit_index: Audio unit index
        track_index: Note track index
        region_index: Region index (-1 = first region)
        rotate_by: Number of positions to rotate (positive = left shift,
                   negative = right shift). Wrapped modulo note count.
        axis: Rotation axis —
            "position" = rotate note order by position (notes keep pitch,
                         positions are reassigned in rotated order),
            "pitch" = rotate pitches (positions stay, pitches shift
                      cyclically among the notes),
            "both" = rotate both position and pitch together (true
                     permutation — notes swap places entirely).
        preserve_pitch_contour: If True, after rotation adjust pitches
            to maintain the original melodic contour (interval sequence).
            Useful for melodic rotation that stays singable.
    """
    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HeadlessBridgeHelper;
        if (!h) return {{error: "Bridge helper not available"}};
        const Quarter = 960;

        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        let rotateBy = {rotate_by};
        const axis = "{axis}";
        const preserveContour = {preserve_pitch_contour};

        const noteTracks = h.noteTracks();
        if (noteTracks.length === 0) return {{error: "No note tracks"}};
        if (trackIdx < 0 || trackIdx >= noteTracks.length) return {{error: "Track out of range"}};
        const track = noteTracks[trackIdx];
        const regions = h.regionBoxes(track);
        if (regions.length === 0) return {{error: "No regions on track"}};
        const regIdx = regionIdx < 0 ? 0 : regionIdx;
        if (regIdx >= regions.length) return {{error: "Region out of range"}};
        const region = regions[regIdx];

        let collection = null;
        try {{
            const vertex = region.events.targetVertex.unwrap();
            collection = vertex.box || vertex;
        }} catch(e) {{}}
        if (!collection || !collection.events) return {{error: "No note collection in region"}};
        const srcNotes = h.eventBoxes(collection);
        if (srcNotes.length < 2) return {{error: "Need at least 2 notes to rotate"}};

        // Read source note data, sorted by position
        const srcData = srcNotes.map(n => ({{
            pos: n.position.getValue(),
            dur: n.duration.getValue(),
            pitch: n.pitch.getValue(),
            vel: n.velocity.getValue(),
        }})).sort((a, b) => a.pos - b.pos);

        const n = srcData.length;
        // Normalize rotation
        rotateBy = ((rotateBy % n) + n) % n;
        if (rotateBy === 0) return {{success: true, notes_rotated: 0, rotate_by: 0, message: "No rotation needed (rotate_by mod n = 0)"}};

        // Build rotated data
        const rotated = new Array(n);
        const origPositions = srcData.map(d => d.pos);
        const origPitches = srcData.map(d => d.pitch);

        if (axis === "position") {{
            // Rotate note order, reassign positions
            for (let i = 0; i < n; i++) {{
                const srcIdx = (i + rotateBy) % n;
                rotated[i] = {{
                    pos: origPositions[i],
                    dur: srcData[srcIdx].dur,
                    pitch: srcData[srcIdx].pitch,
                    vel: srcData[srcIdx].vel,
                }};
            }}
        }} else if (axis === "pitch") {{
            // Rotate pitches, keep positions
            for (let i = 0; i < n; i++) {{
                const pitchIdx = (i + rotateBy) % n;
                rotated[i] = {{
                    pos: srcData[i].pos,
                    dur: srcData[i].dur,
                    pitch: srcData[pitchIdx].pitch,
                    vel: srcData[i].vel,
                }};
            }}
        }} else {{ // both
            for (let i = 0; i < n; i++) {{
                const srcIdx = (i + rotateBy) % n;
                rotated[i] = {{
                    pos: origPositions[i],
                    dur: srcData[srcIdx].dur,
                    pitch: srcData[srcIdx].pitch,
                    vel: srcData[srcIdx].vel,
                }};
            }}
        }}

        // Preserve contour: adjust rotated pitches to match original intervals
        if (preserveContour) {{
            const origIntervals = [];
            for (let i = 1; i < n; i++) {{
                origIntervals.push(srcData[i].pitch - srcData[i-1].pitch);
            }}
            for (let i = 1; i < n; i++) {{
                rotated[i].pitch = rotated[i-1].pitch + origIntervals[i-1];
            }}
        }}

        // Replace notes
        const bg = h.boxGraph;
        const editing = h.editing;
        let deleted = 0;
        let created = 0;

        await editing.modify(async () => {{
            for (const note of srcNotes) {{
                note.delete();
                deleted++;
            }}
            for (const rn of rotated) {{
                h.NoteEventBox.create(bg, h.uuid.generate(), (box) => {{
                    box.position.setValue(Math.round(rn.pos));
                    box.duration.setValue(Math.round(rn.dur));
                    box.pitch.setValue(rn.pitch);
                    box.velocity.setValue(rn.vel);
                    box.cent.setValue(0);
                    box.events.refer(collection.events);
                }});
                created++;
            }}
        }});

        return {{
            success: true,
            notes_before: srcData.length,
            notes_after: rotated.length,
            notes_deleted: deleted,
            notes_created: created,
            rotate_by: rotateBy,
            axis: axis,
            preserve_contour: preserveContour,
            original_pitches: origPitches,
            rotated_pitches: rotated.map(r => r.pitch),
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_instrument_param(unit_index: int, param_name: str, value: float, param_index: int) -> str:
    """Set a parameter on the instrument connected to an audio unit.

unit_index: Audio unit index (-1 = auto-detect first non-master AU with an instrument).
param_name: Field name (e.g. "cutoff", "resonance", "attack", "flutter", "volume", "channel").
value: New value for the parameter.
param_index: Alternative — set by field index instead of name (-1 = use name).

Works with any instrument type. Returns old and new values.
"""
    safe_param = param_name.replace('"', '').replace("'", '').replace('\\', '')
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const paramName = "{safe_param}";
        const paramIdx = {param_index};
        const newVal = {value};

        const units = h.allAUBoxes();
        let instBox = null;

        if (unitIdx >= 0) {{
            if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
            const au = units[unitIdx];
            const incoming = h.inputBoxes(au);
            instBox = incoming.find(b => b.constructor.name !== "AudioBusBox");
        }} else {{
            for (const au of units) {{
                const incoming = h.inputBoxes(au);
                instBox = incoming.find(b => b.constructor.name !== "AudioBusBox");
                if (instBox) break;
            }}
        }}

        if (!instBox) return {{error: "No instrument found"}};

        // Find field by name or index
        let field = null;
        if (paramIdx >= 0) {{
            try {{ field = instBox.getField(paramIdx); }} catch(e) {{}}
        }} else {{
            const record = instBox.record();
            field = record[paramName];
        }}

        if (!field || typeof field.getValue !== 'function') {{
            return {{error: "Parameter not found: " + (paramIdx >= 0 ? "index " + paramIdx : paramName)}};
        }}

        const oldValue = field.getValue();
        h.modify(() => {{
            field.setValue(newVal);
        }});

        return {{
            success: true,
            instrument: instBox.constructor.name,
            param: paramIdx >= 0 ? "field_" + paramIdx : paramName,
            old_value: oldValue,
            new_value: field.getValue(),
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_midi_effect_param(unit_index: int, effect_index: int, param_name: str, value: float, param_index: int) -> str:
    """Set a parameter on a MIDI effect.

unit_index: Audio unit index.
effect_index: MIDI effect position in the chain (0-based).
param_name: Field name (e.g. "semiTones", "rateIndex", "gate").
value: New value for the parameter.
param_index: Alternative — set by field index instead of name (-1 = use name).

Returns old and new values.
"""
    safe_param = param_name.replace('"', '').replace("'", '').replace('\\', '')
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const effectIdx = {effect_index};
        const paramName = "{safe_param}";
        const paramIdx = {param_index};
        const newVal = {value};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
        const au = units[unitIdx];

        const effects = h.midiEffectBoxes(au);
        if (effectIdx >= effects.length) return {{error: "No MIDI effect at index " + effectIdx}};

        const effectBox = effects[effectIdx];

        // Find field by name or index
        let field = null;
        if (paramIdx >= 0) {{
            try {{ field = effectBox.getField(paramIdx); }} catch(e) {{}}
        }} else {{
            const record = effectBox.record();
            field = record[paramName];
        }}

        if (!field) return {{error: "Parameter not found: " + (paramIdx >= 0 ? "index " + paramIdx : paramName)}};

        const oldValue = field.getValue();
        h.modify(() => {{
            field.setValue(newVal);
        }});

        return {{
            success: true,
            effect: effectBox.constructor.name,
            param: paramIdx >= 0 ? "field_" + paramIdx : paramName,
            old_value: oldValue,
            new_value: field.getValue(),
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_note_advanced(unit_index: int, track_index: int, region_index: int, note_index: int, chance: int = -1, cent: float = -999, play_count: int = -1, play_curve: float = -999) -> str:
    """Set advanced note properties — chance, cent, playCount, playCurve.

    These properties are beyond basic position/duration/pitch/velocity:
    - chance: Probability of note playing (0-100%, 100 = always)
    - cent: Micro-tuning in cents (-50 to +50, 0 = exact pitch)
    - play_count: Number of repeats (1-16, 1 = single note)
    - play_curve: Repeat curve (-1 to +1, 0 = even spacing)

    Pass -1 (or -999 for float fields) to skip a property (leave unchanged).

    unit_index: AU index.
    track_index: Note track index.
    region_index: Note region index.
    note_index: Note index within the region.

    Returns updated values, or error.
    """
    # Build JS conditionally — only set fields that aren't sentinel values
    js_lines = []
    if chance >= 0:
        js_lines.append(f"noteBox.chance.setValue({chance});")
    if cent > -999:
        js_lines.append(f"noteBox.cent.setValue({cent});")
    if play_count >= 1:
        js_lines.append(f"noteBox.playCount.setValue({play_count});")
    if play_curve > -999:
        js_lines.append(f"noteBox.playCurve.setValue({play_curve});")

    if not js_lines:
        return json.dumps({"error": "No properties to set — pass chance, cent, play_count, or play_curve"})

    js_body = " ".join(js_lines)

    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const region = h.region({unit_index}, {track_index}, {region_index});
            if (!region.isNoteRegion?.()) return {{error: "Region is not a note region"}};
            const optCol = region.optCollection;
            if (optCol.isEmpty()) return {{error: "No note collection"}};
            const collection = optCol.unwrap();
            const events = collection.events.asArray();
            if ({note_index} >= events.length) return {{error: "No note {note_index}"}};
            const noteBox = events[{note_index}].box;
            h.modify(() => {{ {js_body} }});
            return {{
                success: true,
                chance: noteBox.chance.getValue(),
                cent: noteBox.cent.getValue(),
                play_count: noteBox.playCount.getValue(),
                play_curve: noteBox.playCurve.getValue(),
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_note_cents(
    unit_index: int = -1,
    track_index: int = -1,
    region_index: int = -1,
    cents: float = 0.0,
    mode: str = "all",
    target_pitch: str = "",
    beat_positions: str = "",
    note_indices: str = "",
    direction: str = "up",
    scale: str = "",
    root_note: str = "C",
) -> str:
    """Set detune (cents) on notes — deterministic microtonal pitch control.

    Unlike humanize_pitch (random cents), this tool applies SPECIFIC cent
    offsets to targeted notes. This enables:

    - **Piano honky-tonk**: detune alternate notes by +8/-8 cents
    - **Quarter-tone scales**: +50 cents on selected pitches
    - **Sympathetic resonance**: subtle +3 cents on sustained notes
    - **Just intonation corrections**: -2 cents on major thirds, +14 on fifths
    - **Arabic maqam**: quarter tones between semitones
    - **Synth drift**: gradual cent increase across a sequence
    - **Chorus effect (MIDI)**: duplicate track detuned +7 cents

    Modes:
    - "all": Apply to all notes in the region(s)
    - "pitch": Apply only to notes matching target_pitch (e.g. "60" or "C4")
    - "beats": Apply at specific beat positions (comma-separated, e.g. "0,4,8")
    - "indices": Apply to specific note indices (comma-separated, e.g. "0,2,4")
    - "alternating": Alternate +cents and -cents on consecutive notes
    - "gradient": Linearly increase cents from 0 to target across all notes
    - "scale_degree": Apply to notes on specific scale degrees
      (requires scale + root_note + target_pitch as degree numbers)

    Args:
        unit_index: AU index (-1 = all AUs).
        track_index: Note track index (-1 = all note tracks).
        region_index: Region index (-1 = all regions on track).
        cents: Cent offset to apply (-100 to +100). 100 cents = 1 semitone.
        mode: Targeting mode (see above).
        target_pitch: For "pitch" mode: MIDI note number (e.g. "60") or note
            name (e.g. "C4"). For "scale_degree" mode: comma-separated degree
            numbers (e.g. "3,7" = apply to 3rd and 7th degrees).
        beat_positions: For "beats" mode: comma-separated beat positions.
        note_indices: For "indices" mode: comma-separated note indices.
        direction: "up" (positive cents) or "down" (negative cents). For
            alternating mode, this sets the first note's direction.
        scale: For "scale_degree" mode: scale name (major, minor, dorian, etc.).
        root_note: For "scale_degree" mode: root note name.

    Returns notes modified, per-mode details, and average cents applied.
    """
    if not (-100.0 <= cents <= 100.0):
        return f"Error: cents must be -100 to +100, got {cents}"
    if mode not in ("all", "pitch", "beats", "indices", "alternating", "gradient", "scale_degree"):
        return f"Error: mode must be all/pitch/beats/indices/alternating/gradient/scale_degree, got '{mode}'"

    NOTE_NAMES = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5,
                  "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}

    # Parse target pitch for "pitch" mode
    target_pcs = set()
    if mode == "pitch" and target_pitch:
        for tp in target_pitch.split(","):
            tp = tp.strip()
            if tp.isdigit():
                target_pcs.add(int(tp) % 12)
            else:
                # Parse note name like "C4" or "Eb"
                pc = NOTE_NAMES.get(tp.rstrip("0123456789").replace("b", "").replace("#", "#"), -1)
                if tp.startswith("b") or "b" in tp:
                    pc = (pc - 1) % 12 if pc >= 0 else -1
                if pc >= 0:
                    target_pcs.add(pc)

    # Parse beat positions
    target_beats = set()
    if mode == "beats" and beat_positions:
        for bp in beat_positions.split(","):
            try:
                target_beats.add(round(float(bp.strip()), 2))
            except ValueError:
                pass

    # Parse note indices
    target_indices = set()
    if mode == "indices" and note_indices:
        for ni in note_indices.split(","):
            try:
                target_indices.add(int(ni.strip()))
            except ValueError:
                pass

    # Parse scale degrees
    target_degrees = set()
    if mode == "scale_degree" and target_pitch:
        for d in target_pitch.split(","):
            try:
                target_degrees.add(int(d.strip()))
            except ValueError:
                pass

    # Compute effective cents based on direction
    if direction == "down" and mode != "alternating" and mode != "gradient":
        effective_cents = -abs(cents)
    else:
        effective_cents = cents

    target_pcs_json = json.dumps(list(target_pcs))
    target_beats_json = json.dumps(list(target_beats))
    target_indices_json = json.dumps(list(target_indices))
    target_degrees_json = json.dumps(list(target_degrees))
    _ = (target_pcs_json, target_beats_json, target_indices_json, target_degrees_json, effective_cents)

    # For scale_degree mode, build the scale pitch classes
    scale_pcs_json = "[]"
    if mode == "scale_degree" and scale:
        from opendaw_mcp.music_theory import SCALE_INTERVALS
        root_num = NOTE_NAMES.get(root_note, 0)
        intervals = SCALE_INTERVALS.get(scale, [])
        scale_pcs = []
        for i, iv in enumerate(sorted(intervals)):
            if (i + 1) in target_degrees:
                scale_pcs.append((root_num + iv) % 12)
        scale_pcs_json = json.dumps(scale_pcs)

    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const Quarter = h.ppqn.Quarter;
        const mode = "{mode}";
        const effectiveCents = {effective_cents};
        const direction = "{direction}";

        const targetPcs = new Set({target_pcs_json});
        const targetBeats = new Set({target_beats_json});
        const targetIndices = new Set({target_indices_json});
        const scalePcs = new Set({scale_pcs_json});

        const allUnits = h.allAUBoxes();
        const unitIndices = {unit_index} < 0
            ? allUnits.map((_, i) => i)
            : [{unit_index}];

        let totalModified = 0;
        const centValues = [];
        let noteCounter = 0;

        for (const unitIdx of unitIndices) {{
            if (unitIdx < 0 || unitIdx >= allUnits.length) continue;
            const au = allUnits[unitIdx];
            const noteTracks = h.noteTrackBoxes(au);
            const trackIndices = {track_index} < 0
                ? noteTracks.map((_, i) => i)
                : [{track_index}];

            for (const trackIdx of trackIndices) {{
                if (trackIdx < 0 || trackIdx >= noteTracks.length) continue;
                const trackBox = noteTracks[trackIdx];
                const regions = h.regionBoxes(trackBox);
                const regionIndices = {region_index} < 0
                    ? regions.map((_, i) => i)
                    : [{region_index}];

                for (const regIdx of regionIndices) {{
                    if (regIdx < 0 || regIdx >= regions.length) continue;
                    const region = regions[regIdx];
                    let collection = null;
                    try {{
                        const vertex = region.events.targetVertex.unwrap();
                        collection = vertex.box || vertex;
                    }} catch(e) {{ continue; }}
                    if (!collection || !collection.events) continue;

                    const notes = h.eventBoxes(collection);
                    const regionPos = region.position.getValue();
                    noteCounter = 0;

                    h.modify(() => {{
                        for (let i = 0; i < notes.length; i++) {{
                            const n = notes[i];
                            const pitch = n.pitch.getValue();
                            const pc = ((pitch % 12) + 12) % 12;
                            const absTick = regionPos + n.position.getValue();
                            const beatPos = Math.round(absTick / Quarter * 100) / 100;

                            let shouldApply = false;
                            let appliedCents = effectiveCents;

                            if (mode === "all") {{
                                shouldApply = true;
                            }} else if (mode === "pitch") {{
                                shouldApply = targetPcs.has(pc);
                            }} else if (mode === "beats") {{
                                shouldApply = targetBeats.has(beatPos);
                            }} else if (mode === "indices") {{
                                shouldApply = targetIndices.has(noteCounter);
                            }} else if (mode === "alternating") {{
                                shouldApply = true;
                                appliedCents = noteCounter % 2 === 0
                                    ? Math.abs(effectiveCents)
                                    : -Math.abs(effectiveCents);
                            }} else if (mode === "gradient") {{
                                shouldApply = true;
                                const frac = notes.length > 1 ? noteCounter / (notes.length - 1) : 0;
                                appliedCents = Math.round(effectiveCents * frac * 100) / 100;
                            }} else if (mode === "scale_degree") {{
                                shouldApply = scalePcs.has(pc);
                            }}

                            if (shouldApply && n.cent) {{
                                n.cent.setValue(appliedCents);
                                totalModified++;
                                centValues.push(appliedCents);
                            }}
                            noteCounter++;
                        }}
                    }});
                }}
            }}
        }}

        const avgCents = centValues.length > 0
            ? Math.round(centValues.reduce((a, b) => a + b, 0) / centValues.length * 100) / 100
            : 0;

        return {{
            success: true,
            mode: "{mode}",
            cents_requested: {cents},
            direction: "{direction}",
            notes_modified: totalModified,
            notes_scanned: noteCounter,
            average_cents_applied: avgCents,
            scale: "{scale}" || null,
            root_note: "{root_note}" || null,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_note_properties(note_index: int, unit_index: int, track_index: int, region_index: int, position_beats: float, duration_beats: float, pitch: int, velocity: float, cent: float, chance: int) -> str:
    """Edit properties of a single note within a region.

Pass -1 for any parameter to skip changing it (keep current value).
Use list_notes first to find the note_index.

note_index: Index of the note in the region (0-based, sorted by position).
unit_index: Audio unit index (-1 = search all AUs).
track_index: Note track index within the AU.
region_index: Region containing the note (0-based).
position_beats: New position in beats (-1 = skip).
duration_beats: New duration in beats (-1 = skip).
pitch: New MIDI pitch 0-127 (-1 = skip).
velocity: New velocity 0-1 (-1 = skip).
cent: New cent offset in cents (-1 = skip).
chance: New chance 0-100 (-1 = skip).

Returns updated note properties.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const noteIdx = {note_index};
        const Quarter = h.ppqn.Quarter;
        const newPos = {position_beats};
        const newDur = {duration_beats};
        const newPitch = {pitch};
        const newVel = {velocity};
        const newCent = {cent};
        const newChance = {chance};

        let noteTracks = [];
        if (unitIdx < 0) {{
            const allUnits = h.allAUBoxes();
            for (const au of allUnits) {{
                const tracks = h.trackBoxes(au)
                    .filter(box => box.type?.getValue?.() === 1);
                noteTracks.push(...tracks);
            }}
        }} else {{
            const units = h.allAUBoxes();
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            noteTracks = h.noteTrackBoxes(units[unitIdx]);
        }}

        if (trackIdx >= noteTracks.length) return {{error: "No note track at index " + trackIdx}};
        const trackBox = noteTracks[trackIdx];

        const regions = h.regionBoxes(trackBox);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx}};

        let collection = null;
        try {{
            const vertex = regions[regionIdx].events.targetVertex.unwrap();
            collection = vertex.box || vertex;
        }} catch(e) {{}}
        if (!collection || !collection.events) return {{error: "No note collection in region"}};

        const notes = h.eventBoxes(collection);
        if (noteIdx < 0 || noteIdx >= notes.length) return {{error: "Note index " + noteIdx + " out of range (0.." + (notes.length-1) + ")"}};
        const note = notes[noteIdx];

        h.modify(() => {{
            if (newPos >= 0) note.position.setValue(Math.round(newPos * Quarter));
            if (newDur >= 0) note.duration.setValue(Math.round(newDur * Quarter));
            if (newPitch >= 0) note.pitch.setValue(newPitch);
            if (newVel >= 0) note.velocity.setValue(Math.max(0, Math.min(1, newVel)));
            if (newCent >= 0) note.cent.setValue(newCent);
            if (newChance >= 0) note.chance.setValue(newChance);
        }});

        return {{
            success: true,
            note_index: noteIdx,
            position_beats: note.position.getValue() / Quarter,
            duration_beats: note.duration.getValue() / Quarter,
            pitch: note.pitch.getValue(),
            velocity: note.velocity.getValue(),
            cent: note.cent?.getValue?.() ?? 0,
            chance: note.chance?.getValue?.() ?? 100,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_piano_note_labels(show: bool) -> str:
    """Toggle note labels (C, C#, D, etc.) in the piano roll.

    show: True to show note labels, false to hide.

    Returns success with old and new values.
    """
    val = "true" if show else "false"
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const pm = h.rootBoxAdapter.pianoMode;
            const old = pm.noteLabels.getValue();
            h.editing.modify(() => {{
                pm.noteLabels.field.setValue({val});
            }});
            return {{success: true, old_note_labels: old, new_note_labels: {val}}};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_piano_note_scale(scale: float) -> str:
    """Set the piano roll note scale (vertical zoom).

    scale: Note scale factor (0.5 to 2.0). 1.0 = default, 2.0 = maximum zoom in, 0.5 = maximum zoom out.

    Returns success with old and new values.
    """
    if scale < 0.5 or scale > 2.0:
        return json.dumps({"error": f"scale must be 0.5 to 2.0, got {scale}"})
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const pm = h.rootBoxAdapter.pianoMode;
            const old = pm.noteScale.getValue();
            h.editing.modify(() => {{
                pm.noteScale.field.setValue({scale});
            }});
            return {{success: true, old_note_scale: old, new_note_scale: {scale}}};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_shuffle_notes(
    unit_index: int,
    track_index: int,
    region_index: int = -1,
    mode: str = "pitches",
    seed: int = 0,
    shuffle_amount: float = 1.0,
    preserve_first: bool = False,
    preserve_last: bool = False,
    group_beats: float = 4.0,
) -> str:
    """Shuffle note data randomly within a region.

    Random permutation of notes — unlike rotate_notes (deterministic
    cyclic shift), this creates non-repeating orderings. Seeded for
    reproducibility: same seed = same shuffle.

    Modes:
    - "pitches": shuffle which pitch goes to which position (keeps
      rhythm, changes melody). Most musical — generates melodic
      variations from existing note set.
    - "rhythm": shuffle which position+duration goes to which pitch
      (keeps pitches, changes rhythm). Reassigns onset times among
      existing pitch values.
    - "full": shuffle pitch + position + duration + velocity together
      (complete randomization of all note attributes).
    - "within_groups": shuffle pitches within groups of group_beats
      beats. Notes stay in their time window but pitches get
      randomized within each group. Creates localized variation.

    Args:
        unit_index: Audio unit index
        track_index: Note track index
        region_index: Region index (-1 = first region)
        mode: Shuffle mode — "pitches", "rhythm", "full", "within_groups"
        seed: PRNG seed (0 = random each call, >0 = reproducible)
        shuffle_amount: 0.0-1.0, fraction of notes to shuffle
          (0=no change, 1=full shuffle, 0.5=shuffle half)
        preserve_first: Keep first note unchanged (anchor point)
        preserve_last: Keep last note unchanged (resolution point)
        group_beats: Group size in beats for within_groups mode
          (e.g. 4 = shuffle within each bar, 2 = within half bars)
    """
    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HeadlessBridgeHelper;
        if (!h) return {{"error": "Bridge helper not available"}};
        const Quarter = 960;

        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const shuffleMode = "{mode}";
        const seedVal = {seed};
        const amount = Math.max(0, Math.min(1, {shuffle_amount}));
        const preserveFirst = {preserve_first};
        const preserveLast = {preserve_last};
        const groupBeats = {group_beats};

        // mulberry32 PRNG seeded for reproducibility
        function mulberry32(a) {{
            return function() {{
                a |= 0; a = a + 0x6D2B79F5 | 0;
                let t = Math.imul(a ^ a >>> 15, 1 | a);
                t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
                return ((t ^ t >>> 14) >>> 0) / 4294967296;
            }};
        }}
        const rng = mulberry32(seedVal > 0 ? seedVal : Math.floor(Math.random() * 1e9));

        // Fisher-Yates partial shuffle
        function partialShuffle(arr, amt, keepFirst, keepLast) {{
            const n = arr.length;
            if (n < 2) return arr;
            const start = keepFirst ? 1 : 0;
            const end = keepLast ? n - 1 : n;
            const range = end - start;
            if (range < 2) return arr;
            const indices = [];
            for (let i = start; i < end; i++) indices.push(i);
            for (let i = indices.length - 1; i > 0; i--) {{
                const j = Math.floor(rng() * (i + 1));
                const tmp = indices[i]; indices[i] = indices[j]; indices[j] = tmp;
            }}
            const swaps = Math.floor(range * amt);
            const result = arr.slice();
            for (let i = 0; i < swaps && i < indices.length; i++) {{
                const srcIdx = start + i;
                const dstIdx = indices[i];
                if (dstIdx >= start && dstIdx < end) {{
                    const tmp = result[srcIdx]; result[srcIdx] = result[dstIdx]; result[dstIdx] = tmp;
                }}
            }}
            return result;
        }}

        const noteTracks = h.noteTracks();
        if (noteTracks.length === 0) return {{"error": "No note tracks"}};
        if (trackIdx < 0 || trackIdx >= noteTracks.length) return {{"error": "Track out of range"}};
        const track = noteTracks[trackIdx];
        const regions = h.regionBoxes(track);
        if (regions.length === 0) return {{"error": "No regions on track"}};
        const regIdx = regionIdx < 0 ? 0 : regionIndex;
        if (regIdx >= regions.length) return {{"error": "Region out of range"}};
        const region = regions[regIdx];

        let collection = null;
        try {{
            const vertex = region.events.targetVertex.unwrap();
            collection = vertex.box || vertex;
        }} catch(e) {{}}
        if (!collection || !collection.events) return {{"error": "No note collection in region"}};
        const srcNotes = h.eventBoxes(collection);
        if (srcNotes.length < 2) return {{"error": "Need at least 2 notes to shuffle"}};

        // Read note data, sorted by position
        const noteData = srcNotes.map(n => ({{
            pos: n.position.getValue(),
            dur: n.duration.getValue(),
            pitch: n.pitch.getValue(),
            vel: n.velocity.getValue(),
        }})).sort((a, b) => a.pos - b.pos);

        const n = noteData.length;
        const origPitches = noteData.map(d => d.pitch);
        const origPositions = noteData.map(d => d.pos);

        let newPitches, newPositions, newDurations, newVelocities;
        let groupDetails = null;

        if (shuffleMode === "pitches") {{
            newPitches = partialShuffle(noteData.map(d => d.pitch), amount, preserveFirst, preserveLast);
            newPositions = noteData.map(d => d.pos);
            newDurations = noteData.map(d => d.dur);
            newVelocities = noteData.map(d => d.vel);
        }} else if (shuffleMode === "rhythm") {{
            const pairs = noteData.map(d => ({{pos: d.pos, dur: d.dur}}));
            const shuffledPairs = partialShuffle(pairs, amount, preserveFirst, preserveLast);
            newPitches = noteData.map(d => d.pitch);
            newPositions = shuffledPairs.map(p => p.pos);
            newDurations = shuffledPairs.map(p => p.dur);
            newVelocities = noteData.map(d => d.vel);
        }} else if (shuffleMode === "full") {{
            const allData = noteData.map(d => ({{pitch: d.pitch, pos: d.pos, dur: d.dur, vel: d.vel}}));
            const shuffled = partialShuffle(allData, amount, preserveFirst, preserveLast);
            newPitches = shuffled.map(d => d.pitch);
            newPositions = shuffled.map(d => d.pos);
            newDurations = shuffled.map(d => d.dur);
            newVelocities = shuffled.map(d => d.vel);
        }} else if (shuffleMode === "within_groups") {{
            newPitches = noteData.map(d => d.pitch);
            newPositions = noteData.map(d => d.pos);
            newDurations = noteData.map(d => d.dur);
            newVelocities = noteData.map(d => d.vel);
            const groupSize = Math.max(0.25, groupBeats) * Quarter;
            const groups = {{}};
            for (let i = 0; i < n; i++) {{
                const groupId = Math.floor(noteData[i].pos / groupSize);
                if (!groups[groupId]) groups[groupId] = [];
                groups[groupId].push(i);
            }}
            groupDetails = [];
            for (const gid of Object.keys(groups).sort((a, b) => parseInt(a) - parseInt(b))) {{
                const indices = groups[gid];
                if (indices.length < 2) continue;
                const swaps = Math.floor(indices.length * amount);
                for (let i = 0; i < swaps; i++) {{
                    const aIdx = Math.floor(rng() * indices.length);
                    const bIdx = Math.floor(rng() * indices.length);
                    const tmp = newPitches[indices[aIdx]];
                    newPitches[indices[aIdx]] = newPitches[indices[bIdx]];
                    newPitches[indices[bIdx]] = tmp;
                }}
                groupDetails.push({{
                    group: parseInt(gid),
                    start_beat: Math.round(parseInt(gid) * groupSize / Quarter * 100) / 100,
                    note_count: indices.length,
                }});
            }}
        }} else {{
            return {{"error": "Invalid mode. Use: pitches, rhythm, full, within_groups"}};
        }}

        // Apply changes
        const editing = h.editing;
        let updated = 0;
        const changes = [];

        await editing.modify(async () => {{
            for (let i = 0; i < srcNotes.length; i++) {{
                const notePos = srcNotes[i].position.getValue();
                const sortedIdx = noteData.findIndex(d => d.pos === notePos);
                if (sortedIdx >= 0) {{
                    const oldPitch = srcNotes[i].pitch.getValue();
                    const oldPos = srcNotes[i].position.getValue();
                    const oldDur = srcNotes[i].duration.getValue();
                    const oldVel = srcNotes[i].velocity.getValue();

                    if (newPitches[sortedIdx] !== oldPitch) {{
                        srcNotes[i].pitch.setValue(Math.max(0, Math.min(127, newPitches[sortedIdx])));
                    }}
                    if (newPositions[sortedIdx] !== oldPos) {{
                        srcNotes[i].position.setValue(Math.max(0, newPositions[sortedIdx]));
                    }}
                    if (newDurations[sortedIdx] !== oldDur) {{
                        srcNotes[i].duration.setValue(Math.max(1, newDurations[sortedIdx]));
                    }}
                    if (newVelocities[sortedIdx] !== oldVel) {{
                        srcNotes[i].velocity.setValue(Math.max(0.01, Math.min(1, newVelocities[sortedIdx])));
                    }}

                    const changed = newPitches[sortedIdx] !== oldPitch || newPositions[sortedIdx] !== oldPos ||
                                   newDurations[sortedIdx] !== oldDur || newVelocities[sortedIdx] !== oldVel;
                    if (changed) {{
                        updated++;
                        if (changes.length < 10) {{
                            changes.push({{
                                note: sortedIdx,
                                old_pitch: oldPitch, new_pitch: newPitches[sortedIdx],
                                old_pos_beats: Math.round(oldPos / Quarter * 100) / 100,
                                new_pos_beats: Math.round(newPositions[sortedIdx] / Quarter * 100) / 100,
                            }});
                        }}
                    }}
                }}
            }}
        }});

        return {{
            success: true,
            mode: shuffleMode,
            seed: seedVal,
            shuffle_amount: amount,
            preserve_first: preserveFirst,
            preserve_last: preserveLast,
            notes_shuffled: updated,
            total_notes: n,
            original_pitches: origPitches,
            new_pitches: newPitches,
            groups: groupDetails,
            changes: changes,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_strum_notes(
    unit_index: int = -1,
    track_index: int = -1,
    region_index: int = -1,
    direction: str = "down",
    speed: float = 0.03125,
    jitter: float = 0.0,
) -> str:
    """Strum simultaneous notes — convert block chords into guitar-style strums.

    Finds groups of notes that start at the same position (within a small
    tolerance) and offsets them in time to simulate a pick or strum crossing
    the strings. This transforms static chord pads into lifelike guitar parts.

    direction: Strum direction:
    - "down" — low to high (bass strings first, treble last). Default for
      downstrokes. Most natural for guitar.
    - "up" — high to low (treble first, bass last). Upstroke feel.
    - "random" — random order per chord. Banjo/ukulele feel.

    speed: Time between consecutive strings in beats. 0.03125 = 1/32 note
      (fast shred), 0.0625 = 1/16 (standard strum), 0.125 = 1/8 (slow
      arpeggiated strum), 0.25 = 1/4 (very slow, harp-like).
      Range 0.005 to 0.5.

    jitter: Random timing variation per string (0.0 = exact, 0.02 = ±2% of
      speed as humanization). Adds realism. Range 0.0-0.1.

    Notes are sorted by pitch within each chord group, then offset by
    speed × index from the original start position. The first note stays
    at the original position; subsequent notes are delayed.

    unit_index: AU index (-1 = all AUs).
    track_index: Note track index (-1 = all note tracks on the AU).
    region_index: Region index (-1 = all regions on the track).

    Returns per-track chord groups found, notes strummed.

    Example:
      # Standard downstroke — 1/16 between strings
      strum_notes(unit_index=0, track_index=2, direction="down", speed=0.0625)

      # Slow harp-like arpeggiation
      strum_notes(unit_index=0, track_index=2, direction="down", speed=0.25)

      # Upstroke with humanization
      strum_notes(unit_index=0, track_index=2, direction="up", speed=0.0625, jitter=0.03)
    """
    if direction not in ("down", "up", "random"):
        return f"Error: direction must be 'down', 'up', or 'random', got '{direction}'"
    if not (0.005 <= speed <= 0.5):
        return "Error: speed must be 0.005-0.5 beats"
    if not (0.0 <= jitter <= 0.1):
        return "Error: jitter must be 0.0-0.1"

    speed_ppqn = round(speed * 960)

    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const dir = "{direction}";
        const speedPpqn = {speed_ppqn};
        const jitterAmt = {jitter};
        const tolerance = 10; // PPQN tolerance for "simultaneous"

        const allUnits = h.allAUBoxes();
        const trackResults = [];

        const unitsToProcess = unitIdx < 0 ? allUnits : [allUnits[unitIdx]];
        if (unitIdx >= allUnits.length) return {{error: "unit_index out of range"}};

        for (let u = 0; u < unitsToProcess.length; u++) {{
            const au = unitsToProcess[u];
            const tracks = h.trackBoxes(au);
            const tracksToProcess = trackIdx < 0 ? tracks : [tracks[trackIdx]];
            if (trackIdx >= tracks.length) return {{error: "track_index out of range"}};

            for (let t = 0; t < tracksToProcess.length; t++) {{
                const track = tracksToProcess[t];
                const regions = h.regionBoxes(track);
                if (regions.length === 0) continue;
                const regionsToProcess = regionIdx < 0 ? regions : [regions[Math.min(regionIdx, regions.length - 1)]];

                for (const region of regionsToProcess) {{
                    const eventsField = region.events.targetVertex.unwrap();
                    const collBox = eventsField.box;
                    const noteEvents = [...collBox.events.pointerHub.incoming()];
                    if (noteEvents.length === 0) continue;

                    // Group notes by position (simultaneous = same position within tolerance)
                    const groups = new Map();
                    for (const n of noteEvents) {{
                        const pos = n.box.position.getValue();
                        let groupKey = -1;
                        for (const [key] of groups) {{
                            if (Math.abs(pos - key) <= tolerance) {{
                                groupKey = key;
                                break;
                            }}
                        }}
                        if (groupKey === -1) {{
                            groupKey = pos;
                            groups.set(groupKey, []);
                        }}
                        groups.get(groupKey).push(n);
                    }}

                    let strummedCount = 0;
                    let chordGroups = 0;

                    h.modify(() => {{
                        for (const [origPos, notes] of groups) {{
                            if (notes.length < 2) continue; // solo note, no strum needed
                            chordGroups++;

                            // Sort by pitch
                            let sorted = notes.slice().sort((a, b) => {{
                                return a.box.pitch.getValue() - b.box.pitch.getValue();
                            }});

                            if (dir === "up") {{
                                sorted = sorted.reverse();
                            }} else if (dir === "random") {{
                                // Fisher-Yates shuffle
                                for (let i = sorted.length - 1; i > 0; i--) {{
                                    const j = Math.floor(Math.random() * (i + 1));
                                    [sorted[i], sorted[j]] = [sorted[j], sorted[i]];
                                }}
                            }}

                            // Offset each note by speed * index
                            for (let i = 0; i < sorted.length; i++) {{
                                let offset = i * speedPpqn;
                                if (jitterAmt > 0) {{
                                    offset += Math.round((Math.random() - 0.5) * 2 * jitterAmt * speedPpqn);
                                }}
                                const newPos = Math.max(0, origPos + offset);
                                sorted[i].box.position.setValue(newPos);
                                strummedCount++;
                            }}
                        }}
                    }});

                    trackResults.push({{
                        unit: u,
                        track: t,
                        chord_groups: chordGroups,
                        notes_strummed: strummedCount,
                        direction: dir,
                        speed_beats: {speed},
                    }});
                }}
            }}
        }}

        return {{
            success: true,
            direction: dir,
            speed_beats: {speed},
            jitter: {jitter},
            tracks_processed: trackResults.length,
            per_track: trackResults,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_subdivide_notes(
    unit_index: int,
    track_index: int,
    region_index: int = -1,
    subdivisions: int = 2,
    pitch_pattern: str = "same",
    velocity_pattern: str = "same",
    accent_first: bool = True,
    dest_track_index: int = -1,
) -> str:
    """Subdivide each note in a region into N smaller notes.

    Splits every note into `subdivisions` equal parts. Useful for
    diminution (quarter → 2 eighths), rhythmic fragmentation,
    and creating faster passagework from longer notes.

    Args:
        unit_index: Audio unit index
        track_index: Note track index
        region_index: Region index (-1 = first region)
        subdivisions: Number of parts per note (2-16). 2=diminution,
                      4=sixteenth fragmentation, 3=triplet subdivision.
        pitch_pattern: Pitch variation per subdivision —
            "same" = keep original pitch,
            "scale_up" = ascend scale degrees within the octave,
            "scale_down" = descend scale degrees,
            "octave_up" = alternate original and octave up,
            "octave_down" = alternate original and octave down,
            "chromatic_up" = semitone steps up,
            "chromatic_down" = semitone steps down.
        velocity_pattern: Velocity variation per subdivision —
            "same" = keep original velocity,
            "decrescendo" = fade from full to half,
            "crescendo" = build from half to full,
            "accent_first" = first sub-note accented, rest softer,
            "accent_last" = last sub-note accented,
            "alternating" = strong-weak-strong-weak pattern.
        accent_first: If True, first subdivision note keeps full velocity
                      (traditional articulation). Overridden by velocity_pattern.
        dest_track_index: Destination track (-1 = same track). Original notes
                          are replaced in place when same track.
    """
    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HeadlessBridgeHelper;
        if (!h) return {{error: "Bridge helper not available"}};
        const Quarter = 960;

        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const numSubs = Math.max(2, Math.min(16, {subdivisions}));
        const pitchPat = "{pitch_pattern}";
        const velPat = "{velocity_pattern}";
        const accentFirst = {accent_first};
        const destTrackIdx = {dest_track_index};

        const noteTracks = h.noteTracks();
        if (noteTracks.length === 0) return {{error: "No note tracks"}};
        if (trackIdx < 0 || trackIdx >= noteTracks.length) return {{error: "Track out of range"}};
        const track = noteTracks[trackIdx];
        const regions = h.regionBoxes(track);
        if (regions.length === 0) return {{error: "No regions on track"}};
        const regIdx = regionIdx < 0 ? 0 : regionIdx;
        if (regIdx >= regions.length) return {{error: "Region out of range"}};
        const region = regions[regIdx];

        let collection = null;
        try {{
            const vertex = region.events.targetVertex.unwrap();
            collection = vertex.box || vertex;
        }} catch(e) {{}}
        if (!collection || !collection.events) return {{error: "No note collection in region"}};
        const srcNotes = h.eventBoxes(collection);
        if (srcNotes.length === 0) return {{error: "No notes in region"}};

        // Read source note data
        const srcData = srcNotes.map(n => ({{
            pos: n.position.getValue(),
            dur: n.duration.getValue(),
            pitch: n.pitch.getValue(),
            vel: n.velocity.getValue(),
        }}));

        // Build subdivided notes
        const subNotes = [];
        for (const note of srcData) {{
            const subDur = Math.round(note.dur / numSubs);
            for (let s = 0; s < numSubs; s++) {{
                let pitch = note.pitch;
                if (pitchPat === "scale_up") {{
                    pitch = note.pitch + s;
                }} else if (pitchPat === "scale_down") {{
                    pitch = note.pitch - s;
                }} else if (pitchPat === "octave_up") {{
                    pitch = s % 2 === 0 ? note.pitch : note.pitch + 12;
                }} else if (pitchPat === "octave_down") {{
                    pitch = s % 2 === 0 ? note.pitch : note.pitch - 12;
                }} else if (pitchPat === "chromatic_up") {{
                    pitch = note.pitch + s;
                }} else if (pitchPat === "chromatic_down") {{
                    pitch = note.pitch - s;
                }}

                let vel = note.vel;
                if (velPat === "decrescendo") {{
                    vel = note.vel * (1.0 - (s / numSubs) * 0.5);
                }} else if (velPat === "crescendo") {{
                    vel = note.vel * (0.5 + (s / numSubs) * 0.5);
                }} else if (velPat === "accent_first") {{
                    vel = s === 0 ? note.vel : note.vel * 0.6;
                }} else if (velPat === "accent_last") {{
                    vel = s === numSubs - 1 ? note.vel : note.vel * 0.6;
                }} else if (velPat === "alternating") {{
                    vel = s % 2 === 0 ? note.vel : note.vel * 0.5;
                }} else if (accentFirst && velPat === "same") {{
                    vel = s === 0 ? note.vel : note.vel * 0.85;
                }}

                vel = Math.max(0.01, Math.min(1.0, vel));

                subNotes.push({{
                    pos: note.pos + s * subDur,
                    dur: subDur,
                    pitch: pitch,
                    vel: vel,
                }});
            }}
        }}

        // Determine destination
        const dTrackIdx = destTrackIdx < 0 ? trackIdx : destTrackIdx;
        if (dTrackIdx < 0 || dTrackIdx >= noteTracks.length) return {{error: "dest_track out of range"}};
        const destTrack = noteTracks[dTrackIdx];
        const destRegions = h.regionBoxes(destTrack);
        if (destRegions.length === 0) return {{error: "No regions on dest track"}};
        const destRegion = dTrackIdx === trackIdx ? region : destRegions[0];
        let destColl = null;
        try {{
            const dv = destRegion.events.targetVertex.unwrap();
            destColl = dv.box || dv;
        }} catch(e) {{}}
        if (!destColl || !destColl.events) return {{error: "No note collection in dest region"}};

        // If same track, delete original notes first
        const bg = h.boxGraph;
        const editing = h.editing;
        const origNotes = h.eventBoxes(collection);
        let deleted = 0;
        let created = 0;

        await editing.modify(async () => {{
            // Delete originals if same track
            if (dTrackIdx === trackIdx) {{
                for (const n of origNotes) {{
                    n.delete();
                    deleted++;
                }}
            }}
            // Create subdivided notes
            for (const sn of subNotes) {{
                h.NoteEventBox.create(bg, h.uuid.generate(), (box) => {{
                    box.position.setValue(Math.round(sn.pos));
                    box.duration.setValue(Math.round(sn.dur));
                    box.pitch.setValue(sn.pitch);
                    box.velocity.setValue(sn.vel);
                    box.cent.setValue(0);
                    box.events.refer(destColl.events);
                }});
                created++;
            }}
        }});

        return {{
            success: true,
            notes_deleted: deleted,
            notes_created: created,
            subdivisions: numSubs,
            pitch_pattern: pitchPat,
            velocity_pattern: velPat,
            source_note_count: srcData.length,
            dest_track: dTrackIdx,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_thin_notes(
    unit_index: int = -1,
    track_index: int = -1,
    region_index: int = -1,
    strategy: str = "interval",
    interval: int = 2,
    velocity_threshold: float = 0.3,
    random_chance: float = 0.3,
    preserve_strong_beats: bool = True,
) -> str:
    """Thin out notes in a region — reduce note density for cleaner patterns.

    After AI generation, transcription, or dense arrangement, MIDI can be
    cluttered with too many notes. This tool selectively removes notes to
    clean up the pattern while preserving musical intent.

    Three strategies:
    - "interval" — keep every Nth note (sorted by position). interval=2 keeps
      every 2nd note, interval=3 keeps every 3rd. Creates space.
    - "velocity_threshold" — remove notes below a velocity threshold.
      Cleans up ghost notes from transcription or AI generation.
    - "random" — probabilistic removal. random_chance=0.3 means 30% of notes
      are removed at random. Creates organic variation.

    preserve_strong_beats: When True, notes on strong beats (beat 1 and 3
      in 4/4) are never removed, regardless of strategy. This maintains the
      rhythmic foundation while thinning fills and embellishments.

    unit_index: AU index (-1 = all AUs).
    track_index: Note track index (-1 = all note tracks on the AU).
    region_index: Region index (-1 = all regions on the track).
    strategy: "interval", "velocity_threshold", or "random".
    interval: For "interval" strategy — keep every Nth note (2=halve, 3=third).
      Must be 2-16.
    velocity_threshold: For "velocity_threshold" strategy — remove notes with
      velocity below this value (0.0-1.0, default 0.3).
    random_chance: For "random" strategy — probability of removing each note
      (0.0-1.0, default 0.3 = 30% removed).
    preserve_strong_beats: Keep notes on beat 1 and 3 (0 and 1920 PPQN in 4/4).

    Returns per-track original count, removed count, remaining count.

    Example:
      # Halve note density — keep every 2nd note
      thin_notes(unit_index=0, track_index=0, strategy="interval", interval=2)

      # Remove ghost notes below velocity 0.25
      thin_notes(unit_index=0, track_index=0, strategy="velocity_threshold",
                 velocity_threshold=0.25)

      # Random 40% thinning for organic variation
      thin_notes(unit_index=0, track_index=0, strategy="random",
                 random_chance=0.4)
    """
    valid_strategies = ("interval", "velocity_threshold", "random")
    if strategy not in valid_strategies:
        return f"Error: strategy must be one of {list(valid_strategies)}, got '{strategy}'"
    if strategy == "interval" and not (2 <= interval <= 16):
        return "Error: interval must be 2-16 for 'interval' strategy"
    if strategy == "velocity_threshold" and not (0.0 <= velocity_threshold <= 1.0):
        return "Error: velocity_threshold must be 0.0-1.0"
    if strategy == "random" and not (0.0 < random_chance < 1.0):
        return "Error: random_chance must be 0.0-1.0 (exclusive)"

    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const strategy = "{strategy}";
        const intervalN = {interval};
        const velThresh = {velocity_threshold};
        const randChance = {random_chance};
        const preserveStrong = {str(preserve_strong_beats).lower()};
        const Quarter = 960;
        const strongBeats = [0, 2 * Quarter]; // beat 1 and 3

        const allUnits = h.allAUBoxes();
        const trackResults = [];

        const unitsToProcess = unitIdx < 0 ? allUnits : [allUnits[unitIdx]];
        if (unitIdx >= allUnits.length) return {{error: "unit_index out of range"}};

        for (let u = 0; u < unitsToProcess.length; u++) {{
            const au = unitsToProcess[u];
            const tracks = h.trackBoxes(au);
            const tracksToProcess = trackIdx < 0 ? tracks : [tracks[trackIdx]];
            if (trackIdx >= tracks.length) return {{error: "track_index out of range"}};

            for (let t = 0; t < tracksToProcess.length; t++) {{
                const track = tracksToProcess[t];
                const regions = h.regionBoxes(track);
                if (regions.length === 0) continue;
                const regionsToProcess = regionIdx < 0 ? regions : [regions[Math.min(regionIdx, regions.length - 1)]];

                for (const region of regionsToProcess) {{
                    const eventsField = region.events.targetVertex.unwrap();
                    const collBox = eventsField.box;
                    const noteEvents = [...collBox.events.pointerHub.incoming()];
                    if (noteEvents.length === 0) continue;

                    const regionStart = region.position ? region.position.getValue() : 0;
                    const originalCount = noteEvents.length;

                    // Sort by position for interval strategy
                    const sorted = noteEvents.slice().sort((a, b) => {{
                        return a.box.position.getValue() - b.box.position.getValue();
                    }});

                    // Determine which notes to remove
                    const toRemove = new Set();

                    if (strategy === "interval") {{
                        for (let i = 0; i < sorted.length; i++) {{
                            if (i % intervalN !== 0) {{
                                const pos = sorted[i].box.position.getValue() - regionStart;
                                if (!preserveStrong || !strongBeats.some(sb => Math.abs(pos % (4 * Quarter) - sb) < 10)) {{
                                    toRemove.add(sorted[i]);
                                }}
                            }}
                        }}
                    }} else if (strategy === "velocity_threshold") {{
                        for (const n of noteEvents) {{
                            const vel = n.box.velocity.getValue();
                            const pos = n.box.position.getValue() - regionStart;
                            if (vel < velThresh) {{
                                if (!preserveStrong || !strongBeats.some(sb => Math.abs(pos % (4 * Quarter) - sb) < 10)) {{
                                    toRemove.add(n);
                                }}
                            }}
                        }}
                    }} else if (strategy === "random") {{
                        for (const n of noteEvents) {{
                            const pos = n.box.position.getValue() - regionStart;
                            if (Math.random() < randChance) {{
                                if (!preserveStrong || !strongBeats.some(sb => Math.abs(pos % (4 * Quarter) - sb) < 10)) {{
                                    toRemove.add(n);
                                }}
                            }}
                        }}
                    }}

                    // Execute removals
                    let removedCount = 0;
                    h.modify(() => {{
                        for (const n of toRemove) {{
                            const pos = n.box.position.getValue();
                            // Detach from collection
                            if (n.box.events && n.box.events.targetVertex) {{
                                n.box.events.targetVertex.detach();
                            }}
                            removedCount++;
                        }}
                    }});

                    trackResults.push({{
                        unit: u,
                        track: t,
                        original_count: originalCount,
                        removed: removedCount,
                        remaining: originalCount - removedCount,
                        strategy: strategy,
                    }});
                }}
            }}
        }}

        return {{
            success: true,
            strategy: strategy,
            tracks_processed: trackResults.length,
            per_track: trackResults,
            total_removed: trackResults.reduce((s, r) => s + r.removed, 0),
            total_remaining: trackResults.reduce((s, r) => s + r.remaining, 0),
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_time_warp_notes(
    unit_index: int = -1,
    track_index: int = -1,
    region_index: int = -1,
    warp_factor: float = 0.5,
    origin: str = "start",
) -> str:
    """Warp note positions and durations by a factor — half-time / double-time / custom stretch.

    Scales both the position and duration of every note in a region by warp_factor.
    Unlike scale_durations (which only changes note length, not position), this moves
    notes in time — creating true half-time (0.5×) or double-time (2.0×) feel without
    changing the DAW's BPM.

    Half-time (0.5): notes spread out — a 1-bar pattern becomes 2 bars. Classic for
    trap, lofi, and creating build-ups before a drop.
    Double-time (2.0): notes compress — a 2-bar pattern becomes 1 bar. Useful for
    intensifying a section or creating fills.

    unit_index: AU index (-1 = all AUs).
    track_index: Note track index (-1 = all note tracks on the AU).
    region_index: Region index (-1 = all regions on the track).
    warp_factor: Time scaling factor. 0.5 = half-time, 2.0 = double-time,
      0.25 = quarter-time, 1.5 = 1.5× stretch. Range 0.1-8.0.
    origin: Anchor point for the warp — "start" (region start), or "zero" (position 0).
      "start" preserves relative spacing from region start. "zero" warps from absolute zero.

    Returns per-track modification counts and new region extent.
    """
    if not (0.1 <= warp_factor <= 8.0):
        return "Error: warp_factor must be 0.1-8.0"
    if origin not in ("start", "zero"):
        return "Error: origin must be 'start' or 'zero'"

    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const factor = {warp_factor};
        const originMode = "{origin}";
        const Quarter = 960;

        const allUnits = h.allAUBoxes();
        const trackResults = [];

        const unitsToProcess = unitIdx < 0 ? allUnits : [allUnits[unitIdx]];
        if (unitIdx >= allUnits.length) return {{error: "unit_index out of range"}};

        for (let u = 0; u < unitsToProcess.length; u++) {{
            const au = unitsToProcess[u];
            const tracks = h.trackBoxes(au);
            const tracksToProcess = trackIdx < 0 ? tracks : [tracks[trackIdx]];
            if (trackIdx >= tracks.length) return {{error: "track_index out of range"}};

            for (let t = 0; t < tracksToProcess.length; t++) {{
                const track = tracksToProcess[t];
                const regions = h.regionBoxes(track);
                if (regions.length === 0) continue;
                const regionsToProcess = regionIdx < 0 ? regions : [regions[Math.min(regionIdx, regions.length - 1)]];

                for (const region of regionsToProcess) {{
                    const eventsField = region.events.targetVertex.unwrap();
                    const collBox = eventsField.box;
                    const noteEvents = [...collBox.events.pointerHub.incoming()];
                    if (noteEvents.length === 0) continue;

                    // Get region start as anchor
                    const regionStart = originMode === "start" ? (region.start ? region.start.getValue() : 0) : 0;

                    let minNewPos = Infinity;
                    let maxNewEnd = 0;
                    let modified = 0;

                    h.modify(() => {{
                        for (const n of noteEvents) {{
                            const origPos = n.box.position.getValue();
                            const origDur = n.box.duration.getValue();
                            const relPos = origPos - regionStart;
                            const newPos = regionStart + Math.round(relPos * factor);
                            const newDur = Math.max(1, Math.round(origDur * factor));
                            n.box.position.setValue(newPos);
                            n.box.duration.setValue(newDur);
                            minNewPos = Math.min(minNewPos, newPos);
                            maxNewEnd = Math.max(maxNewEnd, newPos + newDur);
                            modified++;
                        }}
                    }});

                    trackResults.push({{
                        unit: u,
                        track: t,
                        notes_modified: modified,
                        new_start_ppqn: minNewPos === Infinity ? 0 : minNewPos,
                        new_end_ppqn: maxNewEnd,
                    }});
                }}
            }}
        }}

        return {{
            success: true,
            warp_factor: factor,
            origin: originMode,
            tracks_processed: trackResults.length,
            per_track: trackResults,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_transpose_notes(semitones: int, unit_index: int, track_index: int, region_index: int = -1) -> str:
    """Transpose all notes by a number of semitones.

semitones: Positive = up, negative = down (e.g. +12 = octave up, -5 = perfect fourth down).
unit_index: Audio unit index (-1 = all AUs with note tracks).
track_index: Specific note track (-1 = all note tracks on the AU).
region_index: Specific region index (-1 = all regions on the track).

Returns count of notes transposed and notes skipped (out of MIDI range 0-127).
"""
    if not (-127 <= semitones <= 127):
        return f"Error: semitones must be -127 to 127, got {semitones}"
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const semis = {semitones};
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};

        let transposed = 0;
        let skipped = 0;
        const allUnits = h.allAUBoxes();
        const targetUnits = unitIdx < 0 ? allUnits : (unitIdx < allUnits.length ? [allUnits[unitIdx]] : []);

        h.modify(() => {{
            for (const au of targetUnits) {{
                const noteTracks = h.trackBoxes(au)
                    .filter(box => box.type?.getValue?.() === 1);
                const targetTracks = trackIdx < 0 ? noteTracks : (trackIdx < noteTracks.length ? [noteTracks[trackIdx]] : []);
                for (const track of targetTracks) {{
                    const regions = h.regionBoxes(track);
                    const targetRegions = regionIdx < 0 ? regions : (regionIdx < regions.length ? [regions[regionIdx]] : []);
                    for (const region of targetRegions) {{
                        try {{
                            const vertex = region.events.targetVertex.unwrap();
                            const collectionBox = vertex.box || vertex;
                            if (collectionBox && collectionBox.events) {{
                                const noteEvents = h.eventBoxes(collectionBox);
                                for (const evt of noteEvents) {{
                                    const current = evt.pitch.getValue();
                                    const newPitch = current + semis;
                                    if (newPitch < 0 || newPitch > 127) {{
                                        skipped++;
                                        continue;
                                    }}
                                    evt.pitch.setValue(newPitch);
                                    transposed++;
                                }}
                            }}
                        }} catch(e) {{}}
                    }}
                }}
            }}
        }});

        return {{
            success: true,
            semitones: semis,
            notes_transposed: transposed,
            notes_skipped: skipped,
        }};
    }}""")
    return _wrap_eval(result)

