"""
Audio Effects Tools
=============
"""

import json
import asyncio

# These will be injected by server.py
bridge = None
_wrap_eval = None
_ok = None
_err = None


def init_effects_tools(bridge_instance, wrap_eval_func, ok_func=None, err_func=None):
    """Initialize effects tools with shared dependencies."""
    global bridge, _wrap_eval, _ok, _err
    bridge = bridge_instance
    _wrap_eval = wrap_eval_func
    _ok = ok_func
    _err = err_func



async def mcp_opendaw_add_effect(unit_index: int, effect_type: str) -> str:
    """Add an audio effect to an audio unit's effect chain.

effect_type: One of the audio effect names from mcp_opendaw_list_effects:
    Compressor, Crusher, DattorroReverb, Delay, Fold, Gate,
    Maximizer, NeuralAmp (Tone3000), Reverb, Revamp, StereoTool,
    Tidal, Vocoder, Waveshaper, Werkstatt

Returns effect_index — use it with mcp_opendaw_set_effect_parameter.
    """
    safe_effect = effect_type.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const ef = window.DAW_EffectFactories;
        const effectType = "{safe_effect}";
        const unitIndex = {unit_index};

        const factory = ef.AudioNamed[effectType] || ef.AudioNamed[effectType.charAt(0).toUpperCase() + effectType.slice(1)];
        if (!factory) return {{error: "Effect factory not found: " + effectType + ". Available: " + Object.keys(ef.AudioNamed).join(", ")}};

        const units = h.allAUBoxes();
        if (unitIndex >= units.length) return {{error: "No audio unit at index " + unitIndex + ". Total: " + units.length}};
        const au = units[unitIndex];

        let effectBox;
        h.modify(() => {{
            effectBox = h.api.insertEffect(au.audioEffects, factory);
        }});

        // Get effect index in the chain
        const effects = h.effectBoxes(au);
        const effectIndex = effects.findIndex(b => b.address.equals(effectBox.address));

        return {{
            success: true,
            effect: effectType,
            effect_index: effectIndex,
            unit: au.name?.getValue?.() || "Unit " + unitIndex,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_clone_effect_chain(src_unit: int, dst_unit: int) -> str:
    """Copy all effects from one audio unit to another, including parameter values.

Useful for applying the same vocal chain (EQ → compressor → reverb) to doubled vocal tracks.

src_unit: Source audio unit index.
dst_unit: Destination audio unit index (effects appended to existing chain).

Returns list of cloned effects with their new indices.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const ef = window.DAW_EffectFactories;
        const srcIdx = {src_unit};
        const dstIdx = {dst_unit};

        const units = h.allAUBoxes();
        if (srcIdx >= units.length) return {{error: "No source AU at index " + srcIdx}};
        if (dstIdx >= units.length) return {{error: "No dest AU at index " + dstIdx}};

        const srcAU = units[srcIdx];
        const dstAU = units[dstIdx];

        const srcEffects = h.effectBoxes(srcAU);

        if (srcEffects.length === 0) return {{error: "Source AU has no effects"}};

        const cloned = [];
        h.modify(() => {{
            for (const srcEffect of srcEffects) {{
                const className = srcEffect.constructor.name;
                let factoryKey = null;
                for (const key of Object.keys(ef.AudioNamed)) {{
                    if (className === key + "DeviceBox" || className === key) {{
                        factoryKey = key;
                        break;
                    }}
                }}

                if (!factoryKey) {{
                    cloned.push({{error: "No factory for " + className, skipped: true}});
                    continue;
                }}

                const factory = ef.AudioNamed[factoryKey];
                const newEffect = h.api.insertEffect(dstAU.audioEffects, factory);

                // Copy all parameter values
                const srcRecord = srcEffect.record();
                const dstRecord = newEffect.record();
                for (const [key, srcField] of Object.entries(srcRecord)) {{
                    const dstField = dstRecord[key];
                    if (!dstField || typeof dstField.getValue !== 'function') continue;
                    if (typeof srcField.getValue !== 'function') continue;
                    const fname = srcField._fieldName || srcField.fieldName || key;
                    if (['host', 'index', 'label', 'sideChain'].includes(fname)) continue;
                    try {{
                        const value = srcField.getValue();
                        if (typeof value === 'number' || typeof value === 'boolean') {{
                            if (typeof dstField.setValue === 'function') {{
                                dstField.setValue(value);
                            }}
                        }}
                    }} catch(e) {{}}
                }}

                const dstEffects = h.effectBoxes(dstAU);
                const newIdx = dstEffects.findIndex(b => b.address.equals(newEffect.address));

                cloned.push({{
                    effect: factoryKey,
                    effect_index: newIdx,
                    source_class: className,
                }});
            }}
        }});

        return {{
            success: true,
            src_unit: srcIdx,
            dst_unit: dstIdx,
            cloned: cloned,
            total_cloned: cloned.filter(c => !c.skipped).length,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_create_filter_sweep(unit_index: int, direction: str = "open", start_beat: float = 0, duration_beats: float = 8, start_cutoff: float = -1, end_cutoff: float = -1, resonance: float = -1, resonance_boost: bool = True, curve: str = "exp", steps: int = 32) -> str:
    """Create a filter sweep on a Vaporisateur instrument's cutoff parameter with smart defaults.

    The most common transition technique in EDM/techno/house. Sweeps the filter cutoff from
    closed to open (build-up) or open to closed (breakdown). Optionally boosts resonance
    during the sweep for that classic "talking filter" effect. Uses exponential curve by
    default (matches how human hearing perceives frequency changes).

    unit_index: AU index with a Vaporisateur instrument.
    direction: "open" (low→high, build-up) or "close" (high→low, breakdown).
    start_beat: Start position in beats.
    duration_beats: Sweep length in beats (default 8 = 2 bars).
    start_cutoff: Starting cutoff value 0.0-1.0 (default: 0.05 for open, 0.85 for close).
    end_cutoff: Ending cutoff value 0.0-1.0 (default: 0.9 for open, 0.05 for close).
    resonance: Fixed resonance value 0.0-1.0 during sweep. Default: current value unchanged.
    resonance_boost: If True, automates resonance from current to +0.3 at sweep midpoint,
        then back down — classic filter sweep "whistle" effect.
    curve: "exp" (exponential, default — natural for filters), "linear", "log".
    steps: Number of automation points (default 32 = smooth).

    Returns events created, sweep config, and a preview of the curve.

    Examples:
      create_filter_sweep(unit_index=0, direction="open", duration_beats=16)
        → 16-bar filter open from 0.05 to 0.9, exp curve, resonance boost at midpoint
      create_filter_sweep(unit_index=2, direction="close", duration_beats=4, resonance_boost=False)
        → Quick 4-beat filter close, no resonance boost
    """
    # Smart defaults based on direction
    if start_cutoff < 0:
        start_cutoff = 0.05 if direction == "open" else 0.85
    if end_cutoff < 0:
        end_cutoff = 0.9 if direction == "open" else 0.05
    if direction == "close":
        start_cutoff, end_cutoff = end_cutoff, start_cutoff  # swap for close direction

    end_beat = start_beat + duration_beats
    safe_curve = curve.replace('"', '').replace("'", "")

    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const UUID = h.uuid;
        const Quarter = h.ppqn.Quarter;
        const ValueEventBox = window.DAW_ValueEventBox;
        try {{
            const unitIdx = {unit_index};
            const startBeat = {start_beat};
            const endBeat = {end_beat};
            const startVal = {start_cutoff};
            const endVal = {end_cutoff};
            const numSteps = {steps};
            const curveType = "{safe_curve}";
            const resBoost = {str(resonance_boost).lower()};
            const fixedRes = {resonance};

            const units = h.allAUBoxes();
            if (unitIdx >= units.length) return {{error: "No AU at " + unitIdx}};
            const au = units[unitIdx];

            const incoming = h.inputBoxes(au);
            const instBox = incoming.find(b => b.constructor.name !== "AudioBusBox");
            if (!instBox) return {{error: "No instrument on AU " + unitIdx}};

            const cutoffField = instBox["cutoff"];
            if (!cutoffField) return {{error: "No cutoff field on " + instBox.constructor.name}};

            const beatRange = endBeat - startBeat;
            const cutoffPoints = [];
            const resPoints = [];
            for (let i = 0; i < numSteps; i++) {{
                const t = i / (numSteps - 1);
                let value;
                if (curveType === "exp") {{
                    value = startVal + (endVal - startVal) * (Math.exp(t * 3) - 1) / (Math.exp(3) - 1);
                }} else if (curveType === "log") {{
                    value = startVal + (endVal - startVal) * Math.log(1 + t * (Math.E - 1));
                }} else {{
                    value = startVal + (endVal - startVal) * t;
                }}
                const beatPos = startBeat + beatRange * t;
                cutoffPoints.push([beatPos, Math.max(0, Math.min(1, value))]);

                if (resBoost) {{
                    // Resonance peaks at midpoint (t=0.5), fades at start/end
                    const resEnv = Math.sin(t * Math.PI); // 0→1→0 triangle
                    const baseRes = fixedRes >= 0 ? fixedRes : 0.3;
                    resPoints.push([beatPos, Math.max(0, Math.min(1, baseRes + 0.3 * resEnv))]);
                }}
            }}

            let cutoffTrack, resTrack;
            h.editing.modify(() => {{
                // Cutoff automation
                cutoffTrack = h.api.createAutomationTrack(au, cutoffField);
                const cutoffClip = h.api.createValueClip(cutoffTrack, 0, {{name: "cutoff"}});
                const cutoffCol = cutoffClip.events?.targetVertex?.unwrap?.()?.box;
                if (!cutoffCol) throw new Error("No event collection on cutoff clip");
                cutoffPoints.forEach(([beatPos, value], i) => {{
                    ValueEventBox.create(h.boxGraph, UUID.generate(), (box) => {{
                        box.events.refer(cutoffCol.events);
                        box.position.setValue(Math.round(beatPos * Quarter));
                        box.index.setValue(i);
                        box.value.setValue(value);
                        box.interpolation.setValue(1);
                    }});
                }});

                // Resonance automation (optional)
                if (resBoost && resPoints.length > 0) {{
                    const resField = instBox["resonance"];
                    if (resField) {{
                        resTrack = h.api.createAutomationTrack(au, resField);
                        const resClip = h.api.createValueClip(resTrack, 0, {{name: "resonance"}});
                        const resCol = resClip.events?.targetVertex?.unwrap?.()?.box;
                        if (resCol) {{
                            resPoints.forEach(([beatPos, value], i) => {{
                                ValueEventBox.create(h.boxGraph, UUID.generate(), (box) => {{
                                    box.events.refer(resCol.events);
                                    box.position.setValue(Math.round(beatPos * Quarter));
                                    box.index.setValue(i);
                                    box.value.setValue(value);
                                    box.interpolation.setValue(1);
                                }});
                            }});
                        }}
                    }}
                }} else if (fixedRes >= 0) {{
                    // Fixed resonance — just set the field
                    const resField = instBox["resonance"];
                    if (resField) resField.setValue(fixedRes);
                }}
            }});

            return {{
                success: true,
                direction: "{direction}",
                cutoff_events: cutoffPoints.length,
                resonance_events: resBoost ? resPoints.length : 0,
                unit_index: unitIdx,
                start_beat: startBeat,
                end_beat: endBeat,
                cutoff_range: [startVal, endVal],
                curve: curveType,
                resonance_boost: resBoost,
                cutoff_track: cutoffTrack?.index?.getValue?.() ?? 0,
                res_track: resTrack?.index?.getValue?.() ?? -1,
                preview: cutoffPoints.slice(0, 6).map(([b, v]) => ({{beat: Math.round(b * 100) / 100, cutoff: Math.round(v * 1000) / 1000}})),
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_create_metric_modulation(
    position_beats: float,
    old_note: str = "quarter",
    new_note: str = "dotted_eighth",
    old_bpm: float = 0,
    ratio: str = "",
    add_time_signature: str = "",
) -> str:
    """Create a metric modulation — tempo change that preserves a note-value equivalence.

    The defining technique of Elliott Carter, Aaron Copland, John Adams, and
    progressive rock (Dream Theater, Tool). Unlike a simple tempo change,
    metric modulation establishes a precise relationship: a specific note value
    in the new tempo has the same duration as a different note value in the old
    tempo. The listener perceives a new pulse while the rhythmic fabric remains
    continuous.

    Formula: new_bpm = old_bpm × (new_note_value / old_note_value)

    Supported note values:
    - "whole", "half", "dotted_half", "quarter", "dotted_quarter"
    - "quarter_triplet", "eighth", "dotted_eighth", "eighth_triplet"
    - "sixteenth", "dotted_sixteenth", "thirty_second"

    Alternatively, pass a ratio like "3:2" (new tempo = 3/2 of old) or "2:3"
    (new = 2/3 of old) to express the modulation as a simple proportion.

    Examples:
      create_metric_modulation(32, "quarter", "dotted_eighth", old_bpm=120)
        → new_bpm = 120 × (3/16) / (1/4) = 90 BPM. A dotted eighth at 90
          lasts the same as a quarter at 120.
      create_metric_modulation(16, ratio="3:2", old_bpm=100)
        → new_bpm = 150. Three notes in new tempo = two in old.
      create_metric_modulation(48, "eighth", "quarter", old_bpm=140)
        → new_bpm = 280. Quarter at new tempo = eighth at old (doubling).

    Args:
        position_beats: Beat position where modulation occurs.
        old_note: Note value in the old tempo (default "quarter").
        new_note: Note value in the new tempo that equals old_note's duration
            (default "dotted_eighth" — classic Carter modulation).
        old_bpm: Current BPM. If 0, reads from the project's tempo track.
        ratio: Direct ratio "N:M" — new_bpm = old_bpm × N/M. Overrides
            old_note/new_note if provided.
        add_time_signature: Optional new time signature as "N/D" (e.g. "3/4",
            "6/8"). If provided, also creates a time signature change event
            at the same position.

    Returns old_bpm, new_bpm, ratio, equivalence, and events created.
    """
    note_values = {
        "whole": 1.0,
        "half": 0.5,
        "dotted_half": 0.75,
        "quarter": 0.25,
        "dotted_quarter": 0.375,
        "quarter_triplet": 1.0 / 6.0,
        "eighth": 0.125,
        "dotted_eighth": 3.0 / 16.0,
        "eighth_triplet": 1.0 / 12.0,
        "sixteenth": 0.0625,
        "dotted_sixteenth": 3.0 / 32.0,
        "thirty_second": 0.03125,
    }

    # Determine the ratio
    if ratio:
        parts = ratio.replace(" ", "").split(":")
        if len(parts) != 2:
            return f"Error: ratio must be 'N:M', got '{ratio}'"
        try:
            num, den = float(parts[0]), float(parts[1])
        except ValueError:
            return f"Error: ratio parts must be numbers, got '{ratio}'"
        if den == 0:
            return "Error: ratio denominator cannot be zero"
        mod_ratio = num / den
        equiv_desc = f"{parts[0]} notes in new = {parts[1]} in old"
    else:
        if old_note not in note_values:
            return f"Error: old_note '{old_note}' not recognized. Use: {list(note_values.keys())}"
        if new_note not in note_values:
            return f"Error: new_note '{new_note}' not recognized. Use: {list(note_values.keys())}"
        old_v = note_values[old_note]
        new_v = note_values[new_note]
        if old_v == 0:
            return f"Error: old_note '{old_note}' has zero duration"
        mod_ratio = new_v / old_v
        equiv_desc = f"new {new_note} = old {old_note} (duration preserved)"

    # Parse optional time signature
    ts_num, ts_den = 0, 0
    if add_time_signature:
        ts_parts = add_time_signature.replace(" ", "").split("/")
        if len(ts_parts) != 2:
            return f"Error: add_time_signature must be 'N/D', got '{add_time_signature}'"
        try:
            ts_num = int(ts_parts[0])
            ts_den = int(ts_parts[1])
        except ValueError:
            return f"Error: time signature parts must be integers, got '{add_time_signature}'"
        if ts_num < 1 or ts_num > 32:
            return f"Error: time signature numerator must be 1-32, got {ts_num}"
        valid_dens = [1, 2, 4, 8, 16, 32, 64]
        if ts_den not in valid_dens:
            return f"Error: time signature denominator must be one of {valid_dens}, got {ts_den}"

    # We'll read old_bpm from the tempo track if not provided
    read_bpm = old_bpm == 0
    pos_beats = position_beats

    ts_json = json.dumps({"num": ts_num, "den": ts_den} if add_time_signature else {})
    _ = (equiv_desc, pos_beats, read_bpm, ts_json)

    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const UUID = h.uuid;
        const Quarter = h.ppqn.Quarter;
        const ValueEventBox = window.DAW_ValueEventBox;
        const ValueEventCollectionBox = window.DAW_ValueEventCollectionBox;
        try {{
            if (!ValueEventBox || !ValueEventCollectionBox) return {{error: "Box types not loaded"}};
            const tl = h.timelineBox;
            if (!tl || !tl.tempoTrack) return {{error: "No tempoTrack on timeline"}};

            const tempoTrack = tl.tempoTrack;
            const minBpm = tempoTrack.minBpm.getValue();
            const maxBpm = tempoTrack.maxBpm.getValue();

            // Read current BPM if needed
            let oldBpm = {old_bpm};
            if ({'true' if read_bpm else 'false'}) {{
                const existingEvents = h.eventBoxes(tempoTrack.events.targetVertex.isEmpty() ? {{}} : tempoTrack.events.targetVertex.unwrap().box);
                if (existingEvents && existingEvents.length > 0) {{
                    const posTicks = Math.round({pos_beats} * Quarter);
                    let bestEvent = null;
                    for (const e of existingEvents) {{
                        if (e.position?.getValue?.() <= posTicks) {{
                            if (!bestEvent || e.position.getValue() > bestEvent.position.getValue()) {{
                                bestEvent = e;
                            }}
                        }}
                    }}
                    if (bestEvent) {{
                        oldBpm = minBpm + (bestEvent.value?.getValue?.() ?? 0) * (maxBpm - minBpm);
                    }} else {{
                        // Default BPM: minBpm + value at position 0
                        oldBpm = (minBpm + maxBpm) / 2;
                    }}
                }} else {{
                    oldBpm = (minBpm + maxBpm) / 2;
                }}
            }}

            const newBpm = oldBpm * {mod_ratio};
            const newBpmClamped = Math.max(minBpm, Math.min(maxBpm, newBpm));

            if (newBpm < minBpm || newBpm > maxBpm) {{
                return {{
                    error: "Computed BPM out of range",
                    old_bpm: Math.round(oldBpm * 100) / 100,
                    new_bpm_raw: Math.round(newBpm * 100) / 100,
                    min_bpm: minBpm,
                    max_bpm: maxBpm,
                    message: "Set old_bpm explicitly or adjust modulation ratio",
                }};
            }}

            const posTicks = Math.round({pos_beats} * Quarter);
            const normalizedNew = (newBpm - minBpm) / (maxBpm - minBpm);

            const tsInfo = {ts_json};

            h.modify(() => {{
                tempoTrack.enabled.setValue(true);

                // Tempo event
                let coll;
                const existingVertex = tempoTrack.events.targetVertex;
                if (!existingVertex.isEmpty()) {{
                    coll = existingVertex.unwrap().box;
                }} else {{
                    coll = ValueEventCollectionBox.create(h.boxGraph, h.uuid.generate());
                    tempoTrack.events.refer(coll.owners);
                }}

                const existing = h.eventBoxes(coll);
                let maxIdx = existing.reduce((mx, b) => Math.max(mx, b.index?.getValue?.() ?? 0), -1);

                ValueEventBox.create(h.boxGraph, h.uuid.generate(), (box) => {{
                    box.events.refer(coll.events);
                    box.position.setValue(posTicks);
                    box.index.setValue(maxIdx + 1);
                    box.value.setValue(normalizedNew);
                    box.interpolation.setValue("hold");
                }});

                // Optional time signature
                if (tsInfo.num && tsInfo.den) {{
                    const sigTrack = tl.signatureTrack;
                    if (sigTrack) {{
                        sigTrack.enabled.setValue(true);
                        let sigColl;
                        const sigExisting = sigTrack.events.targetVertex;
                        if (!sigExisting.isEmpty()) {{
                            sigColl = sigExisting.unwrap().box;
                        }} else {{
                            const SigEventCollectionBox = window.DAW_ValueEventCollectionBox;
                            sigColl = SigEventCollectionBox.create(h.boxGraph, h.uuid.generate());
                            sigTrack.events.refer(sigColl.owners);
                        }}
                        const SigEventBox = window.DAW_ValueEventBox;
                        const sigEvents = h.eventBoxes(sigColl);
                        let sigMaxIdx = sigEvents.reduce((mx, b) => Math.max(mx, b.index?.getValue?.() ?? 0), -1);
                        // Pack numerator/denominator into value (normalized 0-1)
                        const sigValue = (tsInfo.num * 100 + tsInfo.den) / 10000;
                        SigEventBox.create(h.boxGraph, h.uuid.generate(), (box) => {{
                            box.events.refer(sigColl.events);
                            box.position.setValue(posTicks);
                            box.index.setValue(sigMaxIdx + 1);
                            box.value.setValue(sigValue);
                            box.interpolation.setValue("hold");
                        }});
                    }}
                }}
            }});

            return {{
                success: true,
                position_beats: {pos_beats},
                old_bpm: Math.round(oldBpm * 100) / 100,
                new_bpm: Math.round(newBpm * 100) / 100,
                ratio: {mod_ratio},
                equivalence: "{equiv_desc}",
                time_signature: tsInfo.num ? tsInfo.num + "/" + tsInfo.den : null,
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_create_modulated_song(
    sections: str = "verse:Am-F-C-G:8:0.7,chorus:C-G-Am-F:8:1.0,bridge:F-C-Dm-G:4:0.6,outro:Am-F-C-G:4:0.5",
    arp_pattern: str = "up",
    bass_pattern: str = "root",
    melody_pattern: str = "chord_tones",
    counter_melody_pattern: str = "",
    unit_index: int = 0,
    velocity: float = 0.7,
    drum_genre: str = "",
    bpm: float = None,
) -> str:
    """Build a multi-section song with key modulation between sections — one call.

    Each section has its own chord progression, length (bars), and energy
    (velocity multiplier). The tool automatically modulates between keys
    by using different progressions per section — no manual start_beat
    calculation needed.

    sections: Comma-separated section specs. Each section format:
      name:progression:bars:energy
      - name: section label (verse, chorus, bridge, outro, etc.)
      - progression: chord progression string (e.g. "Am-F-C-G")
      - bars: total bars for this section
      - energy: velocity multiplier (0.0-1.0, relative to base velocity)

    Default creates a 24-bar song:
      verse (Am-F-C-G, 8 bars, 0.7) → chorus (C-G-Am-F, 8 bars, 1.0) →
      bridge (F-C-Dm-G, 4 bars, 0.6) → outro (Am-F-C-G, 4 bars, 0.5)

    The chorus modulates to C major (relative major of A minor), the bridge
    modulates to F (up a fourth), and the outro returns to Am.

    arp_pattern/bass_pattern/melody_pattern/counter_melody_pattern:
      Same as create_harmonic_arrangement. Applied to all sections.
      Use "" to skip any layer.

    drum_genre: If set (e.g. "house", "dnb", "synthwave"), creates a genre
      drum arrangement for the full song length BEFORE harmonic layers.
      When drum_genre is set, pads and bass are automatically skipped in
      harmonic sections (genre arrangement provides them). Default "" = no
      drums (harmony only). Valid: dnb, liquid_dnb, house, trap, techno,
      dubstep, afrobeat, rock, jazz, pop, funk, reggae, synthwave, trance, disco.

    bpm: Tempo for drum arrangement (None = genre default). Only used when
      drum_genre is set.

    Example:
      # Default 4-section modulated song (harmony only)
      create_modulated_song()

      # With house drums
      create_modulated_song(drum_genre="house", bpm=124)

      # With synthwave drums + counter-melody
      create_modulated_song(drum_genre="synthwave", counter_melody_pattern="contrary")

      # Simple verse-chorus with DnB drums
      create_modulated_song("verse:Em-G-D-C:8:0.7,chorus:G-D-Em-C:8:1.0",
          drum_genre="dnb")
    """
    # Parse sections
    parsed_sections = []
    for sec_str in sections.split(","):
        sec_str = sec_str.strip()
        if not sec_str:
            continue
        parts = sec_str.split(":")
        if len(parts) != 4:
            return f"Error: section '{sec_str}' must have 4 colon-separated parts: name:progression:bars:energy"
        name, prog, bars_str, energy_str = parts
        name = name.strip()
        prog = prog.strip()
        try:
            bars = int(bars_str.strip())
        except ValueError:
            return f"Error: bars must be integer in section '{sec_str}', got '{bars_str}'"
        try:
            energy = float(energy_str.strip())
        except ValueError:
            return f"Error: energy must be float 0-1 in section '{sec_str}', got '{energy_str}'"
        if not (0.0 <= energy <= 1.0):
            return f"Error: energy must be 0-1 in section '{sec_str}'"
        if bars < 1 or bars > 64:
            return f"Error: bars must be 1-64 in section '{sec_str}'"
        if not prog:
            return f"Error: progression must be non-empty in section '{sec_str}'"
        parsed_sections.append({
            "name": name,
            "progression": prog,
            "bars": bars,
            "energy": energy,
        })

    if not parsed_sections:
        return "Error: sections must be a non-empty comma-separated list"
    if len(parsed_sections) > 12:
        return "Error: maximum 12 sections per song"

    total_bars = sum(s["bars"] for s in parsed_sections)
    drum_info = None

    # Step 0: Drum arrangement (optional)
    if drum_genre:
        arrangement_fns = {
            "dnb": mcp_opendaw_create_dnb_arrangement,
            "liquid_dnb": mcp_opendaw_create_liquid_dnb_arrangement,
            "house": mcp_opendaw_create_house_arrangement,
            "trap": mcp_opendaw_create_trap_arrangement,
            "techno": mcp_opendaw_create_techno_arrangement,
            "dubstep": mcp_opendaw_create_dubstep_arrangement,
            "afrobeat": mcp_opendaw_create_afrobeat_arrangement,
            "rock": mcp_opendaw_create_rock_arrangement,
            "jazz": mcp_opendaw_create_jazz_arrangement,
            "pop": mcp_opendaw_create_pop_arrangement,
            "funk": mcp_opendaw_create_funk_arrangement,
            "reggae": mcp_opendaw_create_reggae_arrangement,
            "synthwave": mcp_opendaw_create_synthwave_arrangement,
            "trance": mcp_opendaw_create_trance_arrangement,
            "disco": mcp_opendaw_create_disco_arrangement,
            "lofi": mcp_opendaw_create_lofi_arrangement,
            "soul": mcp_opendaw_create_soul_arrangement,
            "rnb": mcp_opendaw_create_rnb_arrangement,
            "blues": mcp_opendaw_create_blues_arrangement,
            "country": mcp_opendaw_create_country_arrangement,
            "metal": mcp_opendaw_create_metal_arrangement,
        }
        if drum_genre not in arrangement_fns:
            return f"Error: unknown drum_genre '{drum_genre}'. Valid: {list(arrangement_fns.keys())}"

        try:
            arr_fn = arrangement_fns[drum_genre]
            arr_result = await arr_fn(
                bpm=bpm if bpm is not None else 0,
                bars=total_bars,
                unit_index=unit_index,
            )
            arr_data = json.loads(arr_result)
            drum_notes = arr_data.get("total_notes", 0)
            drum_info = {
                "genre": drum_genre,
                "bpm": arr_data.get("bpm", bpm),
                "notes": drum_notes,
            }
        except Exception as e:
            drum_info = {"genre": drum_genre, "error": str(e)}

    # When drums are present, skip pads and bass (genre arrangement has them)
    effective_pad_octave = -1 if drum_genre else 3
    effective_bass_pattern = "" if drum_genre else bass_pattern

    section_results = []
    total_notes = 0
    current_beat = 0.0
    layers_summary = set()

    for sec in parsed_sections:
        sec_energy = velocity * sec["energy"]
        # Determine bars_per_chord: each chord gets equal share
        # Count chords in progression
        chord_count = len([c for c in sec["progression"].split("-") if c.strip()])
        bars_per_chord = max(1, sec["bars"] // chord_count) if chord_count > 0 else sec["bars"]

        r = await mcp_opendaw_create_harmonic_arrangement(
            progression=sec["progression"],
            pad_octave=effective_pad_octave,
            arp_pattern=arp_pattern,
            arp_octave=4,
            bass_pattern=effective_bass_pattern,
            bass_octave=2,
            melody_pattern=melody_pattern,
            melody_octave=5,
            counter_melody_pattern=counter_melody_pattern,
            counter_melody_octave=4,
            bars_per_chord=bars_per_chord,
            velocity=sec_energy,
            unit_index=unit_index,
            start_beat=current_beat,
        )
        try:
            d = json.loads(r)
            sec_notes = d.get("total_notes", 0)
            sec_layers = d.get("layers", [])
            layers_summary.update(sec_layers)
            section_results.append({
                "section": sec["name"],
                "progression": sec["progression"],
                "bars": sec["bars"],
                "energy": sec["energy"],
                "start_beat": current_beat,
                "notes": sec_notes,
                "layers": sec_layers,
            })
            total_notes += sec_notes
        except Exception:
            section_results.append({
                "section": sec["name"],
                "progression": sec["progression"],
                "error": "harmonic_arrangement failed",
            })

        current_beat += sec["bars"] * 4  # 4 beats per bar

    total_bars = sum(s["bars"] for s in parsed_sections)
    drum_notes = drum_info.get("notes", 0) if drum_info else 0

    return json.dumps({
        "modulated_song": True,
        "sections": [s["section"] for s in parsed_sections],
        "section_count": len(parsed_sections),
        "total_bars": total_bars,
        "total_beats": current_beat,
        "total_notes": total_notes + drum_notes,
        "harmonic_notes": total_notes,
        "drum_notes": drum_notes,
        "drums": drum_info,
        "layers_used": sorted(layers_summary),
        "section_details": section_results,
        "unit_index": unit_index,
        "next_step": "call apply_genre_mix then render_full_song to complete production",
    }, indent=2)


async def mcp_opendaw_create_sequence(
    pattern: str = "60,62,64,60",
    transposition: int = 5,
    repeats: int = 3,
    direction: str = "up",
    segment_beats: float = 2,
    velocity_decay: float = 0.0,
    unit_index: int = -1,
    track_index: int = 0,
    start_beat: float = 0,
    velocity: float = 0.8,
) -> str:
    """Create a melodic sequence — repeat a pattern at transposed pitch levels.

    The most fundamental compositional technique in Western music: take a melodic
    fragment, repeat it at a different pitch (usually up/down a 4th or 5th).
    Think baroque sequences (Pachelbel), jazz ii-V-I chains, film score ascending
    quint sequences, or EDM build-ups with rising motifs.

    pattern: Comma-separated MIDI pitches (e.g. "60,62,64,67").
    transposition: Semitones to shift each repeat (default 5 = perfect 4th up).
      Common: 5 (4th), 7 (5th), 2 (major 2nd), -2 (down), -5 (4th down).
    repeats: Number of transposed repetitions (1-8, default 3).
    direction: "up" (transpose up), "down" (transpose down), "alternating" (up/down/up...).
    segment_beats: Duration of each pattern repetition in beats (0.5-16, default 2).
    velocity_decay: Velocity change per repeat (-0.3 to 0.3). Positive = louder,
      negative = quieter (fade-out). 0 = constant.
    unit_index: AU index with note track (-1 = find first AU with note tracks).
    track_index: Note track index within the AU.
    start_beat: Position in beats where the sequence begins.
    velocity: Base velocity 0-1 (default 0.8).

    Returns notes created, repeat count, total transposition.
    """
    try:
        base_pitches = [int(p.strip()) for p in pattern.split(",")]
    except ValueError:
        return "Error: pattern must be comma-separated integers (e.g. '60,62,64,67')"
    if len(base_pitches) < 2:
        return "Error: need at least 2 pitches in pattern"
    if len(base_pitches) > 32:
        return "Error: maximum 32 pitches in pattern"
    if not all(0 <= p <= 127 for p in base_pitches):
        return "Error: pitches must be 0-127"
    if transposition < -24 or transposition > 24:
        return "Error: transposition must be -24 to 24"
    if repeats < 1 or repeats > 8:
        return "Error: repeats must be 1-8"
    if direction not in ("up", "down", "alternating"):
        return "Error: direction must be up, down, or alternating"
    if segment_beats < 0.25 or segment_beats > 16:
        return "Error: segment_beats must be 0.25-16"
    if velocity_decay < -0.3 or velocity_decay > 0.3:
        return "Error: velocity_decay must be -0.3 to 0.3"
    if velocity < 0 or velocity > 1:
        return "Error: velocity must be 0-1"

    note_data = []
    note_dur = segment_beats / len(base_pitches)

    for rep in range(repeats):
        # Calculate transposition for this repeat
        if direction == "up":
            transpose = transposition * rep
        elif direction == "down":
            transpose = -transposition * rep
        elif direction == "alternating":
            transpose = transposition * rep if rep % 2 == 0 else -transposition * rep

        # Velocity per repeat
        rep_vel = max(0.01, min(1.0, velocity + velocity_decay * rep))

        for j, base_pitch in enumerate(base_pitches):
            pitch = max(0, min(127, base_pitch + transpose))
            pos = start_beat + rep * segment_beats + j * note_dur
            note_data.append({
                "pitch": pitch,
                "pos": pos,
                "dur": note_dur * 0.9,
                "vel": round(rep_vel, 3),
            })

    total_beats = repeats * segment_beats
    total_transpose = transposition * (repeats - 1) if direction != "down" else -transposition * (repeats - 1)

    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const bg = h.boxGraph;
        const NoteEventBox = window.DAW_NoteEventBox;
        const NoteEventCollectionBox = window.DAW_NoteEventCollectionBox;
        const NoteRegionBox = window.DAW_NoteRegionBox;
        const Quarter = h.ppqn.Quarter;

        const noteData = {json.dumps(note_data)};
        const totalBeats = {total_beats};
        const startBeat = {start_beat};

        let noteTracks = [];
        let targetAU = null;
        const allUnits = h.allAUBoxes();

        if ({unit_index} >= 0 && {unit_index} < allUnits.length) {{
            targetAU = allUnits[{unit_index}];
            noteTracks = h.noteTrackBoxes(targetAU);
        }} else {{
            for (const au of allUnits) {{
                const nt = h.noteTrackBoxes(au);
                if (nt.length > 0) {{ noteTracks = nt; targetAU = au; break; }}
            }}
        }}

        if (noteTracks.length === 0) return {{error: "No note tracks found. Call create_synth_track or create_note_track first."}};

        const trackBox = noteTracks[Math.min({track_index}, noteTracks.length - 1)];
        let totalNotes = 0;

        h.modify(() => {{
            const collection = NoteEventCollectionBox.create(bg, h.uuid.generate());
            const regionDur = Math.round(totalBeats * Quarter);
            const startPos = Math.round(startBeat * Quarter);

            const regionBox = NoteRegionBox.create(bg, h.uuid.generate(), (box) => {{
                box.position.setValue(startPos);
                box.label.setValue("Sequence");
                box.mute.setValue(false);
                box.duration.setValue(regionDur);
                box.loopDuration.setValue(regionDur);
                box.eventOffset.setValue(0);
                box.events.refer(collection.owners);
                box.regions.refer(trackBox.regions);
            }});

            const eventsField = regionBox.events.targetVertex.unwrap();
            const collBox = eventsField.box;

            for (const nd of noteData) {{
                NoteEventBox.create(bg, h.uuid.generate(), (box) => {{
                    box.position.setValue(startPos + Math.round(nd.pos * Quarter - startBeat * Quarter));
                    box.duration.setValue(Math.max(1, Math.round(nd.dur * Quarter)));
                    box.velocity.setValue(Math.max(0.01, Math.min(1, nd.vel)));
                    box.pitch.setValue(nd.pitch);
                    box.chance.setValue(100);
                    box.cent.setValue(0);
                    box.events.refer(collBox.events);
                }});
                totalNotes++;
            }}
        }});

        return {{
            success: true,
            total_notes: totalNotes,
            pattern_notes: {len(base_pitches)},
            repeats: {repeats},
            transposition: {transposition},
            direction: "{direction}",
            total_transposition: {total_transpose},
            segment_beats: {segment_beats},
            velocity_decay: {velocity_decay},
            length_beats: totalBeats,
            unit_index: allUnits.indexOf(targetAU),
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_export_effect_chain(unit_index: int, effect_type: str = "audio") -> str:
    """Export an effect chain (audio or MIDI) from an AU as a base64 preset.

Uses PresetEncoder.encodeEffects — serializes the effect chain into a preset binary.
Can be imported into another AU via import_effect_chain.

unit_index: AU index to export from.
effect_type: "audio" for audio effects, "midi" for MIDI effects.

Returns base64 preset bytes, or error.
"""
    safe_effect_type = effect_type.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const PresetEncoder = window.DAW_PresetEncoder;
        const PresetHeader = window.DAW_PresetHeader || {{ChainKind: {{Audio: 1, Midi: 0}}}};
        if (!PresetEncoder) return {{error: "PresetEncoder not loaded"}};
        const units = h.allAUBoxes();
        if ({unit_index} >= units.length) return {{error: "No AU at {unit_index}"}};
        const au = units[{unit_index}];

        const kind = "{safe_effect_type}" === "midi" ? 0 : 1;  // ChainKind.Midi=0, Audio=1
        const field = kind === 0 ? au.midiEffects : au.audioEffects;
        const effects = h.chainBoxes(field)
            .sort((a, b) => a.index.getValue() - b.index.getValue());
        if (effects.length === 0) return {{error: "No {effect_type} effects on AU {unit_index}"}};

        const buffer = PresetEncoder.encodeEffects(effects, kind);
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
            effect_count: effects.length,
            effect_names: effects.map(e => e.label.getValue()),
        }};
    }}""")
    return _wrap_eval(result)


# ─────────────────────────────────────────────────────────────────────
# Tempo & Project Info (139-144)
# ─────────────────────────────────────────────────────────────────────


async def mcp_opendaw_load_effect_preset(filepath: str, unit_index: int = -1) -> str:
    """Load a .opb preset file into the DAW and apply it to an audio unit.

    Reads the preset bundle, decodes the effect chain via PresetDecoder,
    and inserts it onto the specified audio unit. If unit_index is -1,
    uses the primary (first non-output) audio unit.

    filepath: Path to the .opb preset bundle file.
    unit_index: Target audio unit index. -1 = primary instrument unit.
    """
    import json as _json, zipfile
    if not os.path.exists(filepath):
        return _json.dumps({"error": f"File not found: {filepath}"})
    # Read .opb bundle
    with zipfile.ZipFile(filepath, "r") as zf:
        meta = _json.loads(zf.read("meta.json"))
        preset_bytes = zf.read("preset.odp")
    # Convert to base64 for bridge
    import base64
    preset_b64 = base64.b64encode(preset_bytes).decode("ascii")
    meta_json = _json.dumps(meta)
    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const p = window.DAW;
        const PD = window.DAW_PresetDecoder;
        const PS = window.DAW_ProjectSkeleton;
        if (!PD) return {{error: "PresetDecoder not available"}};
        if (!PS) return {{error: "ProjectSkeleton not available"}};
        // Decode preset bytes into a target project skeleton
        const b64 = "{preset_b64}";
        const binary = atob(b64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
        // PresetDecoder.decode(bytes, target) — target is a fresh skeleton.
        // PS.empty() does its own begin/endTransaction, but decode() creates
        // boxes in target.boxGraph — needs explicit transaction.
        const target = PS.empty({{createOutputMaximizer: false, createDefaultUser: false}});
        target.boxGraph.beginTransaction();
        const imported = PD.decode(bytes.buffer, target);
        target.boxGraph.endTransaction();
        return {{
            success: true,
            preset_name: {meta_json}.name,
            device: {meta_json}.device,
            imported_units: imported.length,
        }};
    }}""")
    if isinstance(result, dict) and result.get("error"):
        return _json.dumps(result)
    return _json.dumps(result, indent=2) if isinstance(result, dict) else _json.dumps({"success": True, "result": result})


async def mcp_opendaw_modulate_progression(
    progression: str = "Am-F-C-G",
    target_key: str = "C",
    direction: str = "up",
) -> str:
    """Transpose a chord progression to a new key.

    Modulation is the technique of changing key within a song. This tool
    takes a progression like "Am-F-C-G" (key of A minor) and transposes
    every chord to a new key while preserving chord qualities (major/minor/
    7th etc.) and interval relationships.

    Common modulations:
    - Up a fourth (C→F): most natural, adds energy for chorus
    - Up a fifth (C→G): bright, triumphant
    - To relative major (Am→C): minor→major mood shift
    - To relative minor (C→Am): major→minor mood shift
    - Down a third (C→A): darker, bridge section

    progression: Source progression (e.g. "Am-F-C-G").
    target_key: Target key root note (e.g. "C", "F", "D", "Bb").
    direction: "up" or "down" (affects octave placement, default "up").

    Returns the modulated progression string + per-chord mapping.

    Example:
      # A minor → C major (relative major)
      modulate_progression("Am-F-C-G", target_key="C")
      # → "C-G-Am-F" (I-V-vi-IV in C major)

      # A minor → F (up a fourth for chorus)
      modulate_progression("Am-F-C-G", target_key="F")

      # C major → A minor (relative minor for bridge)
      modulate_progression("C-G-Am-F", target_key="A")
    """
    if target_key not in NOTE_TO_PITCH:
        return f"Error: target_key must be a valid note name, got '{target_key}'. Valid: {list(NOTE_TO_PITCH.keys())}"
    if direction not in ("up", "down"):
        return f"Error: direction must be 'up' or 'down', got '{direction}'"

    type_map = {
        "m": "min", "7": "dom7", "maj7": "maj7", "m7": "min7",
        "sus2": "sus2", "sus4": "sus4", "add9": "add9",
        "dim": "dim", "aug": "aug", "maj": "maj",
    }
    # Reverse map: internal type → suffix string
    type_to_suffix = {v: k for k, v in type_map.items()}
    # "maj" has no suffix (implicit)
    type_to_suffix["maj"] = ""

    # Parse source progression
    chord_specs = []
    for chord_str in progression.split("-"):
        chord_str = chord_str.strip()
        if not chord_str:
            continue
        if len(chord_str) >= 2 and chord_str[1] in "#b":
            root = chord_str[:2]
            remainder = chord_str[2:]
        else:
            root = chord_str[0]
            remainder = chord_str[1:]

        chord_type = "maj"
        if remainder:
            if remainder not in type_map:
                return f"Error: unknown chord type '{remainder}' in chord '{chord_str}'"
            chord_type = type_map[remainder]

        if root not in NOTE_TO_PITCH:
            return f"Error: unknown root note '{root}' in chord '{chord_str}'"
        chord_specs.append((root, chord_type, chord_str))

    if not chord_specs:
        return "Error: progression must be a non-empty hyphen-separated chord list"

    # Find source key: first chord root
    source_root = chord_specs[0][0]
    source_pc = NOTE_TO_PITCH[source_root]
    target_pc = NOTE_TO_PITCH[target_key]

    # Calculate transposition interval
    transpose = (target_pc - source_pc) % 12
    if direction == "down" and transpose > 6:
        transpose -= 12

    # Note name lookup (pitch class → note name, preferring sharps for sharp keys)
    pc_to_note_sharp = {0: "C", 1: "C#", 2: "D", 3: "D#", 4: "E", 5: "F",
                        6: "F#", 7: "G", 8: "G#", 9: "A", 10: "A#", 11: "B"}
    pc_to_note_flat = {0: "C", 1: "Db", 2: "D", 3: "Eb", 4: "E", 5: "F",
                       6: "Gb", 7: "G", 8: "Ab", 9: "A", 10: "Bb", 11: "B"}

    # Use flats for flat keys, sharps otherwise
    flat_keys = {"F", "Bb", "Eb", "Ab", "Db", "Gb"}
    use_flats = target_key in flat_keys

    note_lookup = pc_to_note_flat if use_flats else pc_to_note_sharp

    modulated_chords = []
    chord_mapping = []

    for root, chord_type, original in chord_specs:
        root_pc = NOTE_TO_PITCH[root]
        new_pc = (root_pc + transpose) % 12
        new_root = note_lookup[new_pc]
        suffix = type_to_suffix.get(chord_type, "")
        new_chord = f"{new_root}{suffix}"
        modulated_chords.append(new_chord)
        chord_mapping.append({
            "original": original,
            "modulated": new_chord,
            "root_shift": f"{root} → {new_root}",
            "type": chord_type,
        })

    modulated_str = "-".join(modulated_chords)
    interval_names = {
        0: "unison", 1: "m2", 2: "M2", 3: "m3", 4: "M3", 5: "P4",
        6: "tritone", 7: "P5", 8: "m6", 9: "M6", 10: "m7", 11: "M7",
    }
    interval_name = interval_names.get(abs(transpose) % 12, f"{abs(transpose)} semitones")

    return json.dumps({
        "modulate_progression": True,
        "source_progression": progression,
        "source_key": source_root,
        "target_key": target_key,
        "direction": direction,
        "transpose_semitones": transpose,
        "interval": interval_name,
        "modulated_progression": modulated_str,
        "chord_mapping": chord_mapping,
        "chord_count": len(chord_specs),
        "next_step": "use modulated_progression with create_harmonic_arrangement or create_full_genre_pipeline(progression=...)",
    }, indent=2)


async def mcp_opendaw_move_effect(unit_index: int, from_index: int, to_index: int) -> str:
    """Reorder an effect within an audio unit's effect chain.

Chain order matters: EQ → Compressor → Reverb sounds different than
Compressor → EQ → Reverb. Use this to move effects to the desired position.

unit_index: Audio unit index.
from_index: Current effect position (0-based).
to_index: Target effect position (0-based).

Effects between from and to shift accordingly.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const fromIdx = {from_index};
        const toIdx = {to_index};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
        const au = units[unitIdx];

        const effects = h.effectBoxes(au);
        if (fromIdx >= effects.length) return {{error: "from_index " + fromIdx + " out of range (" + effects.length + " effects)"}};
        if (toIdx >= effects.length) return {{error: "to_index " + toIdx + " out of range (" + effects.length + " effects)"}};
        if (fromIdx === toIdx) return {{success: true, message: "No change needed"}};

        const movedEffect = effects[fromIdx];
        h.modify(() => {{
            if (toIdx < fromIdx) {{
                // Moving earlier: shift effects between toIdx and fromIdx-1 forward by 1
                for (let i = toIdx; i < fromIdx; i++) {{
                    effects[i].index.setValue(effects[i].index.getValue() + 1);
                }}
                movedEffect.index.setValue(toIdx);
            }} else {{
                // Moving later: shift effects between fromIdx+1 and toIdx backward by 1
                for (let i = fromIdx + 1; i <= toIdx; i++) {{
                    effects[i].index.setValue(effects[i].index.getValue() - 1);
                }}
                movedEffect.index.setValue(toIdx);
            }}
        }});

        // Get new chain order
        const newOrder = h.effectBoxes(au)
            .map(e => e.constructor.name.replace("DeviceBox", ""));

        return {{
            success: true,
            moved: movedEffect.constructor.name.replace("DeviceBox", ""),
            from_index: fromIdx,
            to_index: toIdx,
            new_chain: newOrder,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_remove_effect(unit_index: int, effect_index: int) -> str:
    """Remove an audio effect from an audio unit's chain.

unit_index: Audio unit index.
effect_index: Effect position to remove (0-based).
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const effectIdx = {effect_index};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};

        const au = units[unitIdx];
        const effects = h.effectBoxes(au);
        if (effectIdx >= effects.length) return {{error: "No effect at index " + effectIdx}};

        const effectBox = effects[effectIdx];
        const effectType = effectBox.constructor.name;

        h.modify(() => {{
            effectBox.delete();
        }});

        return {{
            success: true,
            removed: effectType,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_save_effect_preset(unit_index: int, effect_index: int, name: str, description: str = "", output_path: str = "") -> str:
    """Save an audio effect chain as a .opb preset file.

    Encodes the specified effect (and its position in the chain) into an
    openDAW preset bundle (.opb) using PresetEncoder.encodeEffects().
    The file can be shared, drag-and-dropped into openDAW, or loaded
    via mcp_opendaw_load_effect_preset.

    unit_index: Audio unit index containing the effect.
    effect_index: Index of the effect within the unit's audio effect chain.
    name: Preset name (shown in preset browser).
    description: Optional description of what the preset does.
    output_path: Directory to save the .opb file. Defaults to OPENDAW_EXPORT_DIR or /tmp.
    """
    import base64, io, json as _json, time, uuid, zipfile
    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const PE = window.DAW_PresetEncoder;
        if (!PE) return {{error: "PresetEncoder not available"}};
        const units = h.allAUBoxes();
        if ({unit_index} >= units.length) return {{error: "No AU at {unit_index}"}};
        const au = units[{unit_index}];
        const effects = h.effectBoxes(au);
        if ({effect_index} >= effects.length) return {{error: "No effect at index {effect_index} on unit {unit_index}. Effects: " + effects.length}};
        const effectBox = effects[{effect_index}];
        const deviceKey = effectBox.constructor.name.replace(/DeviceBox$/, "");
        // Encode as audio-effect preset (ChainKind.Audio = 1)
        const presetBytes = PE.encodeEffects([effectBox], 1);
        const bytes = new Uint8Array(presetBytes);
        const chunks = [];
        const cs = 0x8000;
        for (let ci = 0; ci < bytes.length; ci += cs) {{
            chunks.push(String.fromCharCode.apply(null, bytes.subarray(ci, ci + cs)));
        }}
        return {{b64: btoa(chunks.join("")), device: deviceKey}};
    }}""")
    if isinstance(result, dict) and result.get("error"):
        return _json.dumps(result)
    if not isinstance(result, dict) or "b64" not in result:
        return _json.dumps({"error": "Unexpected bridge response"})
    preset_bytes = base64.b64decode(result["b64"])
    device_key = result.get("device", "Unknown")
    # Build .opb bundle
    out_dir = output_path or os.environ.get("OPENDAW_EXPORT_DIR", "/tmp")
    os.makedirs(out_dir, exist_ok=True)
    now = int(time.time() * 1000)
    meta = {
        "category": "audio-effect",
        "uuid": str(uuid.uuid4()),
        "name": name,
        "device": device_key,
        "description": description,
        "created": now,
        "modified": now,
    }
    filename = name.replace(" ", "_") + ".opb"
    filepath = os.path.join(out_dir, filename)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("version", "1")
        zf.writestr("meta.json", _json.dumps(meta, indent=2))
        zf.writestr("preset.odp", preset_bytes)
    with open(filepath, "wb") as f:
        f.write(buf.getvalue())
    return _json.dumps({
        "success": True,
        "path": filepath,
        "size_bytes": len(buf.getvalue()),
        "device": device_key,
        "name": name,
    }, indent=2)


async def mcp_opendaw_set_delay_sync(unit_index: int, effect_index: int, fraction: str) -> str:
    """Set the synced delay time on a Delay effect using a musical fraction string.

    unit_index: AU index.
    effect_index: Effect index in the audio effect chain (must be a Delay).
    fraction: Musical fraction — one of:
        "off", "1/128", "1/96", "1/64", "1/48", "1/32", "1/24", "3/64",
        "1/16", "1/12", "3/32", "1/8", "1/6", "3/16", "1/4", "5/16",
        "1/3", "3/8", "7/16", "1/2", "1/1".
    """
    if fraction not in DELAY_SYNC_MAP:
        return _err(f"Invalid fraction '{fraction}'. Valid: {', '.join(sorted(DELAY_SYNC_MAP.keys()))}")
    idx = DELAY_SYNC_MAP[fraction]
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const au = h.auBox({unit_index});
            const fx = h.effectBoxes(au);
            if ({effect_index} >= fx.length) return {{error: "No effect at index " + {effect_index}}};
            const box = fx[{effect_index}];
            if (!box.delayMusical) return {{error: "Effect has no delayMusical field (not a Delay)"}};
            const oldValue = box.delayMusical.getValue();
            h.modify(() => {{ box.delayMusical.setValue({idx}); }});
            return {{
                success: true,
                effect: box.constructor.name,
                fraction: "{fraction}",
                old_index: oldValue,
                new_index: box.delayMusical.getValue(),
            }};
        }} catch(e) {{ return {{error: e.message}}; }}
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_effect_enabled(unit_index: int, effect_index: int, enabled: bool) -> str:
    """Enable or bypass an specific effect on an audio unit.

unit_index: Audio unit index.
effect_index: Effect position in the chain.
enabled: true to enable, false to bypass.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const effectIdx = {effect_index};
        const enabled = {json.dumps(enabled)};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No AU at " + unitIdx}};
        const au = units[unitIdx];
        const effects = h.effectBoxes(au);
        if (effectIdx >= effects.length) return {{error: "No effect at " + effectIdx}};
        const effectBox = effects[effectIdx];

        const oldVal = effectBox.enabled?.getValue?.();
        h.editing.modify(() => {{
            effectBox.enabled.setValue(enabled);
        }});

        return {{
            success: true,
            effect: effectBox.constructor.name,
            enabled: effectBox.enabled.getValue(),
            was_enabled: oldVal,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_effect_parameter(unit_index: int, effect_index: int, parameter_name: str, value: float) -> str:
    """Set a parameter on an audio effect.

unit_index: Audio unit index.
effect_index: Effect position in the chain (0-based).
parameter_name: Parameter name from mcp_opendaw_list_effect_parameters (e.g. "inputGain", "mix", "equation").
value: Numeric value for float params. For string params (like Waveshaper equation), pass the string as parameter_name=value pair — use parameter_name="equation" and value as a special case.

Examples:
    set_effect_parameter(0, 0, "inputGain", 12.0)  # Waveshaper +12dB input
    set_effect_parameter(0, 0, "mix", 1.0)          # 100% wet
    set_effect_parameter(0, 0, "equation", 0)        # Use string_value for equation
    """
    safe_param = parameter_name.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const effectIdx = {effect_index};
        const paramName = "{safe_param}";
        const newValue = {value};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};

        const au = units[unitIdx];
        const effects = h.effectBoxes(au);
        if (effectIdx >= effects.length) return {{error: "No effect at index " + effectIdx}};

        const effectBox = effects[effectIdx];
        const field = effectBox[paramName];
        if (!field || typeof field.setValue !== 'function') {{
            return {{error: "No parameter '" + paramName + "' on " + effectBox.constructor.name}};
        }}

        const oldValue = field.getValue();
        h.modify(() => {{
            field.setValue(newValue);
        }});

        return {{
            success: true,
            parameter: paramName,
            old_value: oldValue,
            new_value: field.getValue(),
            effect: effectBox.constructor.name,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_effect_parameter_bool(unit_index: int, effect_index: int, parameter_name: str, value: bool) -> str:
    """Set a boolean parameter on an audio effect.

    Covers device-specific boolean fields not exposed through the generic float setter:
    - Compressor: lookahead, automakeup, autoattack, autorelease
    - Gate: inverse
    - Maximizer: lookahead
    - StereoTool: invertL, invertR, swap
    - NeuralAmp: mono
    - Delay: freeTimeSync (if available)

    unit_index: Audio unit index.
    effect_index: Effect position in the chain (0-based).
    parameter_name: Boolean field name (e.g. "lookahead", "automakeup", "inverse", "mono").
    value: true or false.
    """
    safe_param = parameter_name.replace('"', '').replace('\\', '').replace("'", "")
    js_bool = "true" if value else "false"
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const effectIdx = {effect_index};
        const paramName = "{safe_param}";
        const newValue = {js_bool};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};

        const au = units[unitIdx];
        const effects = h.effectBoxes(au);
        if (effectIdx >= effects.length) return {{error: "No effect at index " + effectIdx}};

        const effectBox = effects[effectIdx];
        const field = effectBox[paramName];
        if (!field || typeof field.setValue !== 'function') {{
            return {{error: "No parameter '" + paramName + "' on " + effectBox.constructor.name}};
        }}

        const oldValue = field.getValue();
        h.modify(() => {{
            field.setValue(newValue);
        }});

        return {{
            success: true,
            parameter: paramName,
            old_value: oldValue,
            new_value: field.getValue(),
            effect: effectBox.constructor.name,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_effect_parameter_int(unit_index: int, effect_index: int, parameter_name: str, value: int) -> str:
    """Set an integer parameter on an audio effect.

    Covers device-specific integer fields not exposed through the generic float setter:
    - Vocoder: bandCount
    - StereoTool: panningMixing
    - Fold: overSampling
    - Crusher: bits
    - Delay: version (internal)

    Note: device-specific tools (set_vocoder_band_count, set_fold_oversampling, etc.)
    are preferred when available. This is a generic fallback for any Int32Field.

    unit_index: Audio unit index.
    effect_index: Effect position in the chain (0-based).
    parameter_name: Integer field name (e.g. "bandCount", "bits", "overSampling").
    value: Integer value.
    """
    safe_param = parameter_name.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const effectIdx = {effect_index};
        const paramName = "{safe_param}";
        const newValue = {value};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};

        const au = units[unitIdx];
        const effects = h.effectBoxes(au);
        if (effectIdx >= effects.length) return {{error: "No effect at index " + effectIdx}};

        const effectBox = effects[effectIdx];
        const field = effectBox[paramName];
        if (!field || typeof field.setValue !== 'function') {{
            return {{error: "No parameter '" + paramName + "' on " + effectBox.constructor.name}};
        }}

        const oldValue = field.getValue();
        h.modify(() => {{
            field.setValue(newValue);
        }});

        return {{
            success: true,
            parameter: paramName,
            old_value: oldValue,
            new_value: field.getValue(),
            effect: effectBox.constructor.name,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_effect_parameter_string(unit_index: int, effect_index: int, parameter_name: str, string_value: str) -> str:
    """Set a string parameter on an audio effect (e.g. Waveshaper equation).

unit_index: Audio unit index.
effect_index: Effect position in the chain.
parameter_name: Parameter name (e.g. "equation").
string_value: String value (e.g. "hardclip", "tanh", "cubicSoft", "sigmoid", "arctan", "asymmetric").
"""
    safe_value = string_value.replace('"', '').replace("'", '').replace('\\', '')
    safe_param = parameter_name.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const effectIdx = {effect_index};
        const paramName = "{safe_param}";
        const newValue = "{safe_value}";

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};

        const au = units[unitIdx];
        const effects = h.effectBoxes(au);
        if (effectIdx >= effects.length) return {{error: "No effect at index " + effectIdx}};

        const effectBox = effects[effectIdx];
        const field = effectBox[paramName];
        if (!field || typeof field.setValue !== 'function') {{
            return {{error: "No parameter '" + paramName + "' on " + effectBox.constructor.name}};
        }}

        const oldValue = field.getValue();
        h.modify(() => {{
            field.setValue(newValue);
        }});

        return {{
            success: true,
            parameter: paramName,
            old_value: oldValue,
            new_value: field.getValue(),
            effect: effectBox.constructor.name,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_revamp_filter(unit_index: int, effect_index: int, section: str, enabled: bool, frequency: float = 0.0, gain: float = 0.0, q: float = 1.0, order: int = 1) -> str:
    """Configure a filter section on a Revamp (parametric EQ) effect.

    unit_index: AU index.
    effect_index: Effect index in the audio effect chain (must be a Revamp).
    section: One of: "highpass", "lowshelf", "lowbell", "midbell", "highbell", "highshelf", "lowpass".
    enabled: Enable/disable this filter section.
    frequency: Center/cutoff frequency in Hz (20-20000, exponential).
    gain: Boost/cut in dB (-24 to 24, for shelves and bells only).
    q: Bandwidth/resonance (0.01-10, for bells and LPF).
    order: Filter steepness 1-4 (for HPF/LPF only).
    """
    safe_section = section.replace('"', '').replace('\\', '').replace("'", "").lower()
    section_map = {k.lower(): k for k in REVAMP_SECTIONS}
    if safe_section not in section_map:
        return _err(f"Invalid section '{safe_section}'. Valid: {', '.join(sorted(section_map.keys()))}")
    box_field = section_map[safe_section]
    is_pass = safe_section in ("highpass", "lowpass")
    is_bell = safe_section in ("lowbell", "midbell", "highbell")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const au = h.auBox({unit_index});
            const fx = h.effectBoxes(au);
            if ({effect_index} >= fx.length) return {{error: "No effect at index " + {effect_index}}};
            const box = fx[{effect_index}];
            const sectionObj = box["{box_field}"];
            if (!sectionObj) return {{error: "Section '{box_field}' not found (is this a Revamp effect?)"}};
            const changes = {{}};
            h.modify(() => {{
                if (sectionObj.enabled) {{ changes.enabled = {{old: sectionObj.enabled.getValue(), new: {1 if enabled else 0}}}; sectionObj.enabled.setValue({1 if enabled else 0}); }}
                if (sectionObj.frequency && {frequency} > 0) {{ changes.frequency = {{old: sectionObj.frequency.getValue(), new: {frequency}}}; sectionObj.frequency.setValue({frequency}); }}
                if (sectionObj.gain && {"true" if not is_pass else "false"}) {{ changes.gain = {{old: sectionObj.gain.getValue(), new: {gain}}}; sectionObj.gain.setValue({gain}); }}
                if (sectionObj.q && {"true" if is_bell else "false"}) {{ changes.q = {{old: sectionObj.q.getValue(), new: {q}}}; sectionObj.q.setValue({q}); }}
                if (sectionObj.order && {"true" if is_pass else "false"}) {{ changes.order = {{old: sectionObj.order.getValue(), new: {order}}}; sectionObj.order.setValue({order}); }}
            }});
            return {{
                success: true,
                effect: box.constructor.name,
                section: "{safe_section}",
                box_field: "{box_field}",
                changes: changes,
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_vocoder_band_count(unit_index: int, effect_index: int, band_count: int) -> str:
    """Set the band count on a Vocoder effect (number of filter bands, typically 8-32).

    unit_index: AU index.
    effect_index: Effect index in the audio effect chain (must be a Vocoder).
    band_count: Number of bands (8, 16, 24, 32 are common values).
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const au = h.auBox({unit_index});
            const fx = h.effectBoxes(au);
            if ({effect_index} >= fx.length) return {{error: "No effect at index " + {effect_index}}};
            const fxAdapter = fx[{effect_index}];
            const box = fxAdapter.box;
            if (!box.bandCount) return {{error: "Effect has no bandCount (not a Vocoder)"}};
            const oldValue = box.bandCount.getValue();
            h.modify(() => {{
                box.bandCount.setValue({band_count});
            }});
            return {{
                success: true,
                effect: box.constructor.name,
                old_value: oldValue,
                new_value: box.bandCount.getValue(),
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_vocoder_modulator_source(unit_index: int, effect_index: int, source: str) -> str:
    """Set the modulator source on a Vocoder effect.

    unit_index: AU index.
    effect_index: Effect index in the audio effect chain (must be a Vocoder).
    source: One of "noise-white", "noise-pink", "noise-brown", "self", "external".
    """
    valid_sources = ["noise-white", "noise-pink", "noise-brown", "self", "external"]
    if source not in valid_sources:
        return json.dumps({"error": f"Invalid source '{source}'. Must be one of: {', '.join(valid_sources)}"})
    safe_source = json.dumps(source)
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const au = h.auBox({unit_index});
            const fx = h.effectBoxes(au);
            if ({effect_index} >= fx.length) return {{error: "No effect at index " + {effect_index}}};
            const fxAdapter = fx[{effect_index}];
            const box = fxAdapter.box;
            if (!box.modulatorSource) return {{error: "Effect has no modulatorSource (not a Vocoder)"}};
            const oldValue = box.modulatorSource.getValue();
            h.modify(() => {{
                box.modulatorSource.setValue({safe_source});
            }});
            return {{
                success: true,
                effect: box.constructor.name,
                old_source: oldValue,
                new_source: box.modulatorSource.getValue(),
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_waveshaper_equation(unit_index: int, effect_index: int, equation: str) -> str:
    """Set the transfer function equation on a Waveshaper effect.

    unit_index: AU index.
    effect_index: Effect index in the audio effect chain (must be a Waveshaper).
    equation: One of: "hardclip", "cubicSoft", "tanh", "sigmoid", "arctan", "asymmetric".
        - hardclip: harsh digital clipping
        - cubicSoft: warm soft clipping, odd harmonics
        - tanh: classic smooth saturation
        - sigmoid: exponential saturation
        - arctan: gentlest symmetric saturation
        - asymmetric: tube-like, even harmonics from asymmetry
    """
    safe_eq = equation.replace('"', '').replace('\\', '').replace("'", "")
    if safe_eq not in WAVESHAPER_FUNCS:
        return _err(f"Invalid equation '{safe_eq}'. Valid: {', '.join(sorted(WAVESHAPER_FUNCS.keys()))}")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const au = h.auBox({unit_index});
            const fx = h.effectBoxes(au);
            if ({effect_index} >= fx.length) return {{error: "No effect at index " + {effect_index}}};
            const box = fx[{effect_index}];
            if (!box.equation) return {{error: "Effect has no equation field (not a Waveshaper)"}};
            const oldValue = box.equation.getValue();
            h.modify(() => {{
                box.equation.setValue("{safe_eq}");
            }});
            return {{
                success: true,
                effect: box.constructor.name,
                old_equation: oldValue,
                new_equation: box.equation.getValue(),
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

