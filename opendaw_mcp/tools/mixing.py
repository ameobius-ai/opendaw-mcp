"""
Mixing & Automation Tools
===================
"""

import json
import asyncio

# These will be injected by server.py
bridge = None
_wrap_eval = None
_ok = None
_err = None


def init_mixing_tools(bridge_instance, wrap_eval_func, ok_func=None, err_func=None):
    """Initialize mixing tools with shared dependencies."""
    global bridge, _wrap_eval, _ok, _err
    bridge = bridge_instance
    _wrap_eval = wrap_eval_func
    _ok = ok_func
    _err = err_func



async def mcp_opendaw_add_automation(unit_index: int, effect_index: int, parameter_name: str, points: str) -> str:
    """Add parameter automation to an effect on an audio unit.

Creates an automation track + value clip + value events.
Automation points control the parameter over time.

unit_index: Audio unit index.
effect_index: Effect position in the chain.
parameter_name: Parameter to automate (e.g. "cutoff", "volume", "mix").
points: JSON array of [position_beats, value_0_to_1] pairs.
        Example: "[[0, 0.5], [4, 1.0], [8, 0.5]]"

The parameter must be automatable (Field<Pointers.Automation>).
    """
    safe_param = parameter_name.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const UUID = h.uuid;
        const PPQN = h.ppqn;
        const Quarter = PPQN.Quarter;
        const ValueEventBox = window.DAW_ValueEventBox;
        const unitIdx = {unit_index};
        const effectIdx = {effect_index};
        const paramName = "{safe_param}";
        const points = {points};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No AU at " + unitIdx}};
        const au = units[unitIdx];

        const effects = h.effectBoxes(au);
        if (effectIdx >= effects.length) return {{error: "No effect at " + effectIdx}};
        const effectBox = effects[effectIdx];

        const field = effectBox[paramName];
        if (!field) return {{error: "No parameter '" + paramName + "' on " + effectBox.constructor.name}};

        // Create automation track targeting this parameter
        let autoTrack, valueClip, collection;
        h.editing.modify(() => {{
            autoTrack = h.api.createAutomationTrack(au, field);
            valueClip = h.api.createValueClip(autoTrack, 0, {{name: paramName}});
            // Get the event collection from the clip
            collection = valueClip.events?.targetVertex?.unwrap?.()?.box;
            if (!collection) throw new Error("No event collection on value clip");

            // Create value events (automation points)
            points.forEach(([beatPos, value], i) => {{
                ValueEventBox.create(h.boxGraph, UUID.generate(), (box) => {{
                    box.events.refer(collection.events);
                    box.position.setValue(Math.round(beatPos * Quarter));
                    box.index.setValue(i);
                    box.value.setValue(value);
                    box.interpolation.setValue(1); // linear
                }});
            }});
        }});

        return {{
            success: true,
            parameter: paramName,
            effect: effectBox.constructor.name,
            track: String(autoTrack.address),
            clip: String(valueClip.address),
            points: points.length,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_automation_sweep(unit_index: int, parameter_name: str, start_beat: float, end_beat: float, start_value: float, end_value: float, steps: int = 16, curve: str = "linear") -> str:
    """Create a smooth automation sweep (ramp) between two values over a beat range.

    Generates multiple automation events with interpolated values, creating smooth parameter
    transitions (filter sweeps, volume fades, pitch drops, etc.) in one call.
    Automatically creates the automation track if it doesn't exist yet.

    unit_index: AU index.
    parameter_name: Instrument parameter to automate (e.g. "cutoff", "volume", "resonance").
    start_beat: Start position in beats.
    end_beat: End position in beats.
    start_value: Starting normalized value (0.0-1.0).
    end_value: Ending normalized value (0.0-1.0).
    steps: Number of interpolation points (default 16, more = smoother).
    curve: "linear" (even spacing), "exp" (exponential, good for filter sweeps), "log" (logarithmic).

    Returns the number of events created and a preview of the first few points.

    Example: Filter sweep from closed (0.1) to open (0.9) over 16 beats:
      automation_sweep(unit_index=0, parameter_name="cutoff", start_beat=0, end_beat=16, start_value=0.1, end_value=0.9, steps=32, curve="exp")
    """
    safe_param = parameter_name.replace('"', '').replace('\\', '').replace("'", "")
    safe_curve = curve.replace('"', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const UUID = h.uuid;
        const Quarter = h.ppqn.Quarter;
        const ValueEventBox = window.DAW_ValueEventBox;
        try {{
            const unitIdx = {unit_index};
            const paramName = "{safe_param}";
            const startBeat = {start_beat};
            const endBeat = {end_beat};
            const startVal = {start_value};
            const endVal = {end_value};
            const numSteps = {steps};
            const curveType = "{safe_curve}";

            const units = h.allAUBoxes();
            if (unitIdx >= units.length) return {{error: "No AU at " + unitIdx}};
            const au = units[unitIdx];

            // Find instrument box
            const incoming = h.inputBoxes(au);
            const instBox = incoming.find(b => b.constructor.name !== "AudioBusBox");
            if (!instBox) return {{error: "No instrument on AU " + unitIdx}};

            const field = instBox[paramName];
            if (!field) return {{error: "No field '" + paramName + "' on " + instBox.constructor.name}};

            const beatRange = endBeat - startBeat;
            const points = [];
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
                points.push([beatPos, Math.max(0, Math.min(1, value))]);
            }}

            // Create automation track + value clip + events
            let autoTrack, collection;
            h.editing.modify(() => {{
                autoTrack = h.api.createAutomationTrack(au, field);
                const valueClip = h.api.createValueClip(autoTrack, 0, {{name: paramName}});
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
                events_created: points.length,
                parameter: paramName,
                unit_index: unitIdx,
                start_beat: startBeat,
                end_beat: endBeat,
                value_range: [startVal, endVal],
                curve: curveType,
                track_index: autoTrack?.index?.getValue?.() ?? 0,
                events_preview: points.slice(0, 5).map(([b, v]) => ({{position_beats: Math.round(b * 100) / 100, value: Math.round(v * 1000) / 1000}})),
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_create_audio_bus(name: str) -> str:
    """Create a new audio bus (aux bus) with its own audio unit and track.

Follows the upstream AudioBusFactory.createAudioBus pattern:
creates AudioUnitBox (Aux) + AudioBusBox + TrackBox, wires them together.
Uses separate editing.modify() blocks — pointer refer() inside box
constructor fails due to deferred pointer update resolution.

name: Bus label.

Returns the new bus index.
"""
    safe_name = name.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const UUID = h.uuid;
        const AudioBusBox = window.DAW_AudioBusBox;
        const TrackBox = window.DAW_TrackBox;
        const AudioUnitBox = window.DAW_AudioUnitBox;
        const AudioUnitType = window.DAW_AudioUnitType;
        const TrackType = window.DAW_TrackType;

        const buses = h.busBoxes();
        const newIdx = buses.length;
        let newBus, newUnit;

        // Block 1: Create AudioUnitBox (Aux)
        h.editing.modify(() => {{
            const unitIdx = h.allAUBoxes().length;
            newUnit = AudioUnitBox.create(h.boxGraph, UUID.generate(), (box) => {{
                box.type.setValue(AudioUnitType.Aux);
                box.collection.refer(h.rootBox.audioUnits);
                box.index.setValue(unitIdx);
            }});
        }});

        // Block 2: Create AudioBusBox + wire output -> unit.input
        // Must be separate block — refer() inside constructor causes
        // deferred pointer update that fails at endTransaction.
        h.editing.modify(() => {{
            newBus = AudioBusBox.create(h.boxGraph, UUID.generate(), (box) => {{
                box.label.setValue();
                box.collection.refer(h.rootBox.audioBusses);
                box.icon.setValue("AudioBus");
            }});
            newBus.output.refer(newUnit.input);
        }});

        // Block 3: Create TrackBox linking to the new unit
        h.editing.modify(() => {{
            TrackBox.create(h.boxGraph, UUID.generate(), (box) => {{
                box.tracks.refer(newUnit.tracks);
                box.target.refer(newUnit);
                box.index.setValue(0);
                box.type.setValue(TrackType.Undefined);
            }});
        }});

        return {{success: true, bus_index: newIdx, label: "{safe_name}", unit_uuid: String(newUnit.address).slice(0,8)}};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_create_automation_event(unit_index: int, track_index: int, position_beats: float, value: float, interpolation: str = "linear", curve_slope: float = 0.5) -> str:
    """Create a single automation event at a specific position on a value track.

    Adds a point to the automation curve with the given interpolation type.
    If an event already exists at the same position, its value is updated.

    unit_index: AU index.
    track_index: Value (automation) track index.
    position_beats: Position in beats (float).
    value: Normalized value 0.0-1.0.
    interpolation: "none" (step), "linear" (ramp), or "curve" (custom slope).
    curve_slope: Slope for curve interpolation (0.0-1.0, 0.5 = linear). Only used if interpolation="curve".

    Returns the created/updated event info, or error.
    """
    ppqn_val = int(position_beats * 960)

    safe_interpolation = interpolation.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const track = h.track({unit_index}, {track_index});
            const regions = track.regions.collection.asArray();
            if (regions.length === 0) return {{error: "No value regions on track"}};
            const region = regions[0];
            if (!region.isValueRegion?.()) return {{error: "Region is not a value region"}};
            const optCol = region.optCollection;
            if (optCol.isEmpty()) return {{error: "No event collection"}};
            const collection = optCol.unwrap();
            let created;
            h.modify(() => {{
                const interpType = "{safe_interpolation}";
                let interpolation;
                if (interpType === "none") interpolation = {{type: "none"}};
                else if (interpType === "curve") interpolation = {{type: "curve", slope: {curve_slope}}};
                else interpolation = {{type: "linear"}};
                created = collection.createEvent({{
                    position: {ppqn_val},
                    index: 0,
                    value: {value},
                    interpolation: interpolation,
                }});
            }});
            return {{
                success: true,
                position: created.position,
                value: created.value,
                interpolation: created.interpolation.type,
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_create_drum_solo(
    solo_type: str = "rock",
    bars: int = 4,
    velocity: float = 0.9,
    unit_index: int = -1,
    track_index: int = 0,
    start_beat: float = 0,
    seed: int = 42,
) -> str:
    """Create a genre-specific drum solo with rudimental vocabulary.

    Generates a complete drum solo using vocabulary appropriate to the
    chosen style. Unlike create_drum_fill (short transition), this tool
    creates a full multi-bar solo with phrasing, build-ups, climax, and
    genre-specific rudimental patterns:

    - **rock**: Thunderous 16th-note double kick patterns, crash accents,
      tom fills, snare ghost notes, building intensity. John Bonham,
      Neil Peart, Danny Carey.
    - **jazz**: Brushes + sticks, comping patterns, ride bell, press rolls,
      polyrhythmic phrasing, trading 4s feel. Max Roach, Elvin Jones,
      Tony Williams.
    - **funk**: Ghost-note heavy 16th-note grooves, hi-hat splashes,
      pocket fills, James Brown/Bootsy aesthetic. Clyde Stubblefield,
      Jabo Starks, Bernard Purdie.
    - **latin**: Cascara, mambo bell, timbale fills, clave-based phrasing,
      6/8 feel options. Tito Puente, Mongo Santamaria.
    - **marching**: Rudimental solo — paradiddles, flams, drags, roll
      building, double-stroke open rolls. DCI, snare line vocabulary.

    solo_type: rock | jazz | funk | latin | marching
    bars: Solo length (2-16, default 4)
    velocity: Base velocity 0-1 (drum solos are loud, default 0.9)
    seed: PRNG seed for reproducibility

    Returns notes created and solo characteristics.

    Example:
      create_drum_solo(solo_type="rock", bars=4)
      create_drum_solo(solo_type="jazz", bars=8)
      create_drum_solo(solo_type="marching", bars=4, seed=100)
    """
    VALID_SOLO_TYPES = ["rock", "jazz", "funk", "latin", "marching"]
    if solo_type not in VALID_SOLO_TYPES:
        return json.dumps({"error": f"Invalid solo_type '{solo_type}'. Valid: {VALID_SOLO_TYPES}"})
    if bars < 2 or bars > 16:
        return json.dumps({"error": "bars must be 2-16"})
    if not (0.0 <= velocity <= 1.0):
        return json.dumps({"error": "velocity must be 0-1"})

    # GM Drum pitches
    KICK = 36
    SNARE = 38
    HAT = 42
    OPEN_HAT = 46
    RIDE = 51
    CRASH = 49
    TOM1 = 48  # high tom
    TOM2 = 45  # mid tom
    TOM3 = 41  # floor tom
    TOM4 = 36  # kick-position tom (bass drum)
    CROSS_STICK = 37
    MAMBO_BELL = 57
    TIMBALE = 65

    # Seeded PRNG
    def mulberry32(s):
        a = s & 0xFFFFFFFF
        while True:
            a = (a + 0x6D2B79F5) & 0xFFFFFFFF
            t = a
            t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
            t ^= t + ((t ^ (t >> 7)) & 0xFFFFFFFF)
            yield (t & 0xFFFFFFFF) / 0x100000000

    rng = mulberry32(seed)

    notes = []
    bar_beats = 4.0

    # --- Helper: add a note ---
    def add_note(pitch, start, dur, vel):
        notes.append({"pitch": pitch, "start": round(start, 4), "duration": dur, "velocity": round(min(1.0, vel), 3)})

    # --- Helper: rudiment patterns ---
    def paradiddle(start, pitch=SNARE, vel=velocity):
        """RLRR LRLL — 8 notes, paradiddle rudiment."""
        pattern = [1, 0, 1, 1, 0, 1, 0, 0]  # 1=accent, 0=quiet
        for i, acc in enumerate(pattern):
            v = vel * (0.9 if acc else 0.5)
            add_note(pitch, start + i * 0.25, 0.12, v)

    def flam(start, pitch=SNARE, vel=velocity):
        """Flam: grace note + main note."""
        add_note(pitch, start, 0.08, vel * 0.5)
        add_note(pitch, start + 0.02, 0.12, vel * 0.95)

    def drag(start, pitch=SNARE, vel=velocity):
        """Drag: two grace notes + main note."""
        add_note(pitch, start - 0.06, 0.06, vel * 0.4)
        add_note(pitch, start - 0.03, 0.06, vel * 0.4)
        add_note(pitch, start, 0.12, vel * 0.9)

    def open_roll(start, beats=1.0, pitch=SNARE, vel=velocity):
        """Double-stroke open roll — 16th notes."""
        n = int(beats * 4)
        for i in range(n):
            v = vel * (0.85 + next(rng) * 0.15)
            add_note(pitch, start + i * 0.25, 0.1, v)

    def tom_descent(start, vel=velocity):
        """Descending tom fill: TOM1→TOM2→TOM3→TOM4."""
        toms = [TOM1, TOM2, TOM3, TOM4]
        for i, t in enumerate(toms):
            for j in range(2):
                add_note(t, start + (i * 2 + j) * 0.25, 0.15, vel * (0.9 - i * 0.05))

    # --- Generate solo per style ---
    for bar in range(bars):
        bar_start = start_beat + bar * bar_beats
        intensity = 0.6 + 0.4 * (bar / max(1, bars - 1))  # builds to climax
        bar_vel = velocity * intensity

        if solo_type == "rock":
            # Rock: double kick 16ths, crash accents, tom fills
            # Bars 1-2: groove with kick variations
            # Last 2 bars: tom fills + crash climax
            if bar < bars - 2:
                # Groove: kick on 1, 2.5, snare on 2, 4
                add_note(KICK, bar_start, 0.2, bar_vel)
                add_note(HAT, bar_start, 0.04, bar_vel * 0.5)
                add_note(HAT, bar_start + 0.5, 0.04, bar_vel * 0.4)
                add_note(SNARE, bar_start + 1.0, 0.12, bar_vel)
                add_note(HAT, bar_start + 1.0, 0.04, bar_vel * 0.4)
                add_note(KICK, bar_start + 1.5, 0.2, bar_vel * 0.9)
                add_note(HAT, bar_start + 1.5, 0.04, bar_vel * 0.4)
                add_note(HAT, bar_start + 2.0, 0.04, bar_vel * 0.5)
                add_note(KICK, bar_start + 2.5, 0.2, bar_vel)
                add_note(HAT, bar_start + 2.5, 0.04, bar_vel * 0.4)
                add_note(SNARE, bar_start + 3.0, 0.12, bar_vel)
                add_note(HAT, bar_start + 3.0, 0.04, bar_vel * 0.4)
                add_note(KICK, bar_start + 3.5, 0.2, bar_vel * 0.9)
                add_note(HAT, bar_start + 3.5, 0.04, bar_vel * 0.4)
                # End-of-bar fill: ghost notes
                if next(rng) < 0.5:
                    for g in range(4):
                        add_note(SNARE, bar_start + 3.75 + g * 0.06, 0.04, bar_vel * 0.3)
            else:
                # Fill bars: tom descent + crash
                tom_descent(bar_start, bar_vel)
                if bar == bars - 1:
                    # Final crash
                    add_note(CRASH, bar_start + 3.5, 0.5, bar_vel)
                    add_note(KICK, bar_start + 3.5, 0.3, bar_vel)
                else:
                    # Mid fill: paradiddle on snare
                    paradiddle(bar_start + 2.0, SNARE, bar_vel)

        elif solo_type == "jazz":
            # Jazz: ride pattern, comping, press rolls, building
            # Swing ride: 1, 2&, 3, 4& (long-short swing)
            ride_pattern = [(0.0, bar_vel), (0.66, bar_vel * 0.6), (1.0, bar_vel),
                           (1.66, bar_vel * 0.6), (2.0, bar_vel), (2.66, bar_vel * 0.6),
                           (3.0, bar_vel), (3.66, bar_vel * 0.6)]
            for pos, v in ride_pattern:
                add_note(RIDE, bar_start + pos, 0.3, v)
                add_note(HAT, bar_start + pos, 0.04, v * 0.3)  # feathered hat

            # Hi-hat on 2 and 4 (foot)
            add_note(HAT, bar_start + 1.0, 0.1, bar_vel * 0.4)
            add_note(HAT, bar_start + 3.0, 0.1, bar_vel * 0.4)

            # Comping: random snare/kick accents
            comp_positions = [0.5, 1.5, 2.5, 3.5]
            for pos in comp_positions:
                if next(rng) < 0.5:
                    comp_pitch = SNARE if next(rng) < 0.6 else KICK
                    add_note(comp_pitch, bar_start + pos, 0.1, bar_vel * 0.7)

            # Last bar: press roll build
            if bar == bars - 1:
                open_roll(bar_start + 2.0, 2.0, SNARE, bar_vel)
                add_note(CRASH, bar_start + 4.0 - 0.1, 0.5, bar_vel)

        elif solo_type == "funk":
            # Funk: ghost-note 16ths, hi-hat splashes, pocket fills
            # 16th-note hat pattern with ghost snare
            for i in range(16):
                pos = i * 0.25
                v = bar_vel * (0.5 + 0.3 * (1 if i % 4 == 0 else 0))
                add_note(HAT if i % 2 == 0 else OPEN_HAT, bar_start + pos, 0.04, v * 0.5)
                # Ghost snare on off-16ths
                if i % 2 == 1 and next(rng) < 0.6:
                    add_note(SNARE, bar_start + pos, 0.06, bar_vel * 0.3)
            # Kick pattern: syncopated
            kick_positions = [0.0, 0.75, 2.0, 2.75, 3.5]
            for pos in kick_positions:
                add_note(KICK, bar_start + pos, 0.15, bar_vel * 0.9)
            # Snare backbeat
            add_note(SNARE, bar_start + 1.0, 0.12, bar_vel)
            add_note(SNARE, bar_start + 3.0, 0.12, bar_vel)
            # Fill: drag on last bar
            if bar == bars - 1:
                drag(bar_start + 3.5, SNARE, bar_vel)

        elif solo_type == "latin":
            # Latin: cascara + mambo bell + timbale fills
            # Cascara pattern (2-3 clave)
            cascara = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]
            cascara_accents = [1, 0, 1, 0, 0, 1, 0, 0]
            for i, pos in enumerate(cascara):
                v = bar_vel * (0.8 if cascara_accents[i] else 0.4)
                add_note(CROSS_STICK, bar_start + pos, 0.08, v)

            # Mambo bell
            bell_positions = [0.0, 1.0, 1.5, 2.5, 3.0]
            for pos in bell_positions:
                add_note(MAMBO_BELL, bar_start + pos, 0.15, bar_vel * 0.7)

            # Kick on clave beats
            add_note(KICK, bar_start, 0.15, bar_vel * 0.8)
            add_note(KICK, bar_start + 2.5, 0.15, bar_vel * 0.8)
            add_note(KICK, bar_start + 3.0, 0.15, bar_vel * 0.8)

            # Timbale fill on last 2 bars
            if bar >= bars - 2:
                fill_start = bar_start + 2.0
                for i in range(8):
                    add_note(TIMBALE, fill_start + i * 0.25, 0.1, bar_vel * (0.7 + next(rng) * 0.3))

        elif solo_type == "marching":
            # Marching: rudimental solo — paradiddles, flams, drags, rolls
            rudiment = bar % 4
            if rudiment == 0:
                # Paradiddles
                paradiddle(bar_start, SNARE, bar_vel)
                paradiddle(bar_start + 2.0, SNARE, bar_vel)
            elif rudiment == 1:
                # Flams
                for i in range(4):
                    flam(bar_start + i * 1.0, SNARE, bar_vel)
            elif rudiment == 2:
                # Drags
                for i in range(4):
                    drag(bar_start + i * 1.0, SNARE, bar_vel)
            else:
                # Open roll building
                roll_len = 1.0 + next(rng) * 1.0
                open_roll(bar_start, roll_len, SNARE, bar_vel)
                # Accent at end
                add_note(CRASH, bar_start + roll_len, 0.3, bar_vel)
                # More rolls
                open_roll(bar_start + roll_len + 0.5, bar_beats - roll_len - 0.5, SNARE, bar_vel * 0.9)

    notes.sort(key=lambda n: (n["start"], n["pitch"]))

    result = await mcp_opendaw_create_notes_batch(
        json.dumps(notes), unit_index, track_index)

    try:
        data = json.loads(result)
    except Exception:
        data = {"raw": result}

    data["drum_solo"] = True
    data["solo_type"] = solo_type
    data["bars"] = bars
    data["notes_generated"] = len(notes)
    data["characteristics"] = {
        "rock": "double kick 16ths, crash accents, tom fills, ghost notes, intensity build to climax",
        "jazz": "swing ride pattern, comping, press rolls, hi-hat feathering, polyrhythmic phrasing",
        "funk": "ghost-note 16ths, hi-hat splashes, syncopated kick, pocket fills, drag endings",
        "latin": "cascara, mambo bell, timbale fills, clave-based phrasing, 2-3 clave",
        "marching": "rudimental: paradiddles, flams, drags, open rolls, accent building, DCI vocabulary",
    }.get(solo_type, "")

    return json.dumps(data, indent=2)


async def mcp_opendaw_create_mute_automation(unit_index: int, events: str) -> str:
    """Create timed mute/unmute automation events on an audio unit.

    Essential for section dynamics: mute drums during breakdowns, unmute for drops,
    create structural silences. Each event is a (beat, mute_state) pair — mute at
    beat X, unmute at beat Y. Replaces multiple set_track_mute calls with one
    automation track that plays back predictably every time.

    unit_index: AU index to automate mute on.
    events: JSON array of [beat, muted] pairs. beat = position in beats,
        muted = true (silence) or false (audible).
        Example: [[0, false], [16, true], [24, false]] = audible 0-16, muted 16-24, audible 24+

    Returns events created, mute schedule, and track index.

    Examples:
      create_mute_automation(unit_index=0, events='[[0,false],[16,true],[24,false]]')
        → Drums audible for 16 beats, muted for 8 (breakdown), back on at 24
      create_mute_automation(unit_index=2, events='[[0,true],[8,false]]')
        → Bass silent for intro, kicks in at beat 8
    """
    try:
        import json
        event_list = json.loads(events)
        if not isinstance(event_list, list) or len(event_list) == 0:
            return "Error: events must be a non-empty JSON array of [beat, muted] pairs"
        for e in event_list:
            if not isinstance(e, (list, tuple)) or len(e) != 2:
                return "Error: each event must be [beat, muted] pair"
    except Exception as e:
        return f"Error parsing events: {e}"

    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const UUID = h.uuid;
        const Quarter = h.ppqn.Quarter;
        const ValueEventBox = window.DAW_ValueEventBox;
        try {{
            const unitIdx = {unit_index};
            const eventData = {events};

            const units = h.allAUBoxes();
            if (unitIdx >= units.length) return {{error: "No AU at " + unitIdx}};
            const au = units[unitIdx];

            const muteField = au["mute"];
            if (!muteField) return {{error: "No mute field on AU"}};

            let autoTrack;
            h.editing.modify(() => {{
                autoTrack = h.api.createAutomationTrack(au, muteField);
                const muteClip = h.api.createValueClip(autoTrack, 0, {{name: "mute"}});
                const muteCol = muteClip.events?.targetVertex?.unwrap?.()?.box;
                if (!muteCol) throw new Error("No event collection on mute clip");
                eventData.forEach(([beatPos, muted], i) => {{
                    ValueEventBox.create(h.boxGraph, UUID.generate(), (box) => {{
                        box.events.refer(muteCol.events);
                        box.position.setValue(Math.round(beatPos * Quarter));
                        box.index.setValue(i);
                        box.value.setValue(muted ? 1 : 0);
                        box.interpolation.setValue(0); // step, no interpolation for boolean
                    }});
                }});
            }});

            return {{
                success: true,
                events_created: eventData.length,
                unit_index: unitIdx,
                track_index: autoTrack?.index?.getValue?.() ?? 0,
                schedule: eventData.map(([b, m]) => ({{beat: b, state: m ? "muted" : "audible"}})),
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_create_send(src_unit: int, name: str, send_level_db: float, routing: str) -> str:
    """Create a parallel FX send bus from an audio unit.

Creates a NEW AudioBusBox (FX bus) with its own AudioUnitBox, then sends
a copy of src_unit's signal to that FX bus via AuxSendBox. The dry signal
continues to the main output unchanged — this is a parallel send, not a redirect.

After creating the send, add effects (Reverb, Delay) to the FX bus unit using
add_effect(fx_unit_index, effect_type). The FX bus unit index is returned.

src_unit: Source audio unit index (the instrument sending signal).
name: Name for the FX bus (e.g. "Reverb Bus", "Delay Bus").
send_level_db: Send level in dB (-∞ to +12). -6dB is a good starting point.
routing: 'pre' (pre-fader) or 'post' (post-fader, default).

Returns send_index on src AU, and fx_unit_index (the new FX bus AU index for
adding effects).

Workflow: create_instrument_track → create_send → add_effect(Reverb on fx_unit_index)
"""
    routing_val = json.dumps(routing)


    safe_name = name.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const AuxSendBox = window.DAW_AuxSendBox;
        const AudioBusBox = window.DAW_AudioBusBox;
        const AudioUnitBox = window.DAW_AudioUnitBox;
        const TrackBox = window.DAW_TrackBox;  // may be undefined
        if (!AuxSendBox) return {{error: "AuxSendBox not loaded"}};
        if (!AudioBusBox) return {{error: "AudioBusBox not loaded"}};
        if (!AudioUnitBox) return {{error: "AudioUnitBox not loaded"}};

        const srcIdx = {src_unit};
        const sendDb = {send_level_db};
        const routingVal = {routing_val};
        const fxName = "{safe_name}";

        const units = h.allAUBoxes();
        if (srcIdx >= units.length) return {{error: "No src AU at index " + srcIdx}};

        const srcAU = units[srcIdx];
        const primaryBus = h.primaryAudioBusBox;
        const boxGraph = h.boxGraph;
        const AudioUnitType = window.DAW_AudioUnitType;

        // Aux type = 3 (AudioUnitType.Aux)
        const auxType = AudioUnitType ? AudioUnitType.Aux : 3;

        let sendBox, fxBus, fxUnit;

        h.modify(() => {{
            // 1. Create FX AudioUnitBox (Aux type) — owns the effect chain, output → primary bus
            const existingCount = h.allAUBoxes().length;
            fxUnit = AudioUnitBox.create(boxGraph, h.uuid.generate(), (box) => {{
                box.collection.refer(h.rootBox.audioUnits);
                box.output.refer(primaryBus.input);
                box.index.setValue(existingCount);
                box.type.setValue(auxType);
            }});

            // 2. Create FX bus (AudioBusBox) — routes audio INTO fxUnit
            fxBus = AudioBusBox.create(boxGraph, h.uuid.generate(), (box) => {{
                box.collection.refer(h.rootBox.audioBusses);
                box.output.refer(fxUnit.input);
                box.enabled.setValue(true);
                box.label.setValue(fxName);
            }});

            // 3. Create AuxSendBox: src AU → FX bus (parallel send, no redirect)
            const currentSends = h.sendBoxes(srcAU).length;
            sendBox = AuxSendBox.create(boxGraph, h.uuid.generate(), (box) => {{
                box.audioUnit.refer(srcAU.auxSends);
                box.targetBus.refer(fxBus.input);
                box.routing.setValue(routingVal);
                box.sendGain.setValue(sendDb);
                box.sendPan.setValue(0.0);
            }});
        }});

        // Get updated unit list to find FX unit index
        const updatedUnits = h.allAUBoxes();
        const fxUnitIdx = updatedUnits.findIndex(b => b.address.equals(fxUnit.address));

        const sendIndex = h.sendBoxes(srcAU)
            .findIndex(b => b.address.equals(sendBox.address));

        return {{
            success: true,
            send_index: sendIndex,
            src_unit: srcIdx,
            fx_unit_index: fxUnitIdx,
            fx_bus_name: fxName,
            send_level_db: sendDb,
            routing: routingVal === 0 ? "pre" : "post",
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_create_solo(
    solo_type: str = "bebop",
    key_root: str = "C",
    scale_type: str = "major",
    bars: int = 8,
    octave: int = 4,
    velocity: float = 0.8,
    unit_index: int = -1,
    track_index: int = 0,
    start_beat: float = 0,
    seed: int = 42,
) -> str:
    """Create a genre-specific melodic solo over a chord progression.

    Generates a complete solo line using vocabulary appropriate to the
    chosen style. Unlike generate_melody (contour-guided) or
    create_random_walk (stepwise), this tool uses genre-specific
    soloing techniques:

    - **bebop**: Chromatic approach tones, chord-tone targeting on
      strong beats, enclosure (upper+lower chromatic neighbor),
      bebop scale passing notes, ii-V-I arpeggio fluency.
      Charlie Parker, Dizzy Gillespie, Clifford Brown.
    - **blues**: Minor pentatonic + blue notes (b5, b3 bent),
      repetition of short motifs with variation, call-response
      phrasing, string-bending aesthetic via pitch slides.
      B.B. King, Eric Clapton, Stevie Ray Vaughan.
    - **rock**: Pentatonic positions, repeated riffs, wide interval
      jumps, rhythmic syncopation, climax-building through register
      shifts. Jimmy Page, Hendrix, Gilmour.
    - **jazz_swing**: Swing 8th notes, guide-tone lines,
      chord-tone on beat 1+3, arpeggio + approach patterns.
      Lester Young, Sonny Rollins.
    - **fusion**: Mixolydian/dorian modes, odd-meter phrasing,
      wide intervals, chromatic passing, rhythmic displacement.
      Metheny, Brecker, Holdsworth.

    solo_type: bebop | blues | rock | jazz_swing | fusion
    key_root: Root note (C, C#, D, ... B)
    scale_type: major | minor | dorian | mixolydian | blues | pentatonic_minor
    bars: Solo length (4-32, default 8)
    octave: MIDI octave for solo (4 = C4=60)
    velocity: Base velocity 0-1
    seed: PRNG seed for reproducibility

    Returns notes created and solo characteristics.

    Example:
      create_solo(solo_type="bebop", key_root="F", scale_type="major", bars=8)
      create_solo(solo_type="blues", key_root="A", scale_type="blues", bars=12)
      create_solo(solo_type="rock", key_root="E", scale_type="pentatonic_minor", bars=16)
    """
    NOTE_MAP = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4,
                "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9,
                "A#": 10, "Bb": 10, "B": 11}

    SCALES = {
        "major": [0, 2, 4, 5, 7, 9, 11],
        "minor": [0, 2, 3, 5, 7, 8, 10],
        "dorian": [0, 2, 3, 5, 7, 9, 10],
        "mixolydian": [0, 2, 4, 5, 7, 9, 10],
        "blues": [0, 3, 5, 6, 7, 10],
        "pentatonic_minor": [0, 3, 5, 7, 10],
    }

    VALID_SOLO_TYPES = ["bebop", "blues", "rock", "jazz_swing", "fusion"]

    root_pc = NOTE_MAP.get(key_root)
    if root_pc is None:
        return json.dumps({"error": f"Invalid key_root '{key_root}'"})
    if scale_type not in SCALES:
        return json.dumps({"error": f"Invalid scale_type '{scale_type}'. Valid: {list(SCALES.keys())}"})
    if solo_type not in VALID_SOLO_TYPES:
        return json.dumps({"error": f"Invalid solo_type '{solo_type}'. Valid: {VALID_SOLO_TYPES}"})
    if bars < 4 or bars > 32:
        return json.dumps({"error": "bars must be 4-32"})
    if not (0.0 <= velocity <= 1.0):
        return json.dumps({"error": "velocity must be 0-1"})
    if not (0 <= octave <= 7):
        return json.dumps({"error": "octave must be 0-7"})

    scale = SCALES[scale_type]
    base = (octave + 1) * 12 + root_pc

    # Seeded PRNG (mulberry32)
    def mulberry32(s):
        a = s & 0xFFFFFFFF
        while True:
            a = (a + 0x6D2B79F5) & 0xFFFFFFFF
            t = a
            t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
            t ^= t + ((t ^ (t >> 7)) & 0xFFFFFFFF)
            yield (t & 0xFFFFFFFF) / 0x100000000

    rng = mulberry32(seed)

    # Chord progression per bar (ii-V-I for bebop/jazz, I-IV-V for blues, etc.)
    if solo_type in ("bebop", "jazz_swing"):
        # ii-V-I-VI (turnaround) in major, or i-iv-V7-i in minor
        prog = [1, 4, 0, 5]  # scale degrees: ii, V, I, vi
    elif solo_type == "blues":
        prog = [0, 0, 0, 0, 3, 3, 0, 0, 5, 3, 0, 4]  # 12-bar blues
    elif solo_type == "rock":
        prog = [0, 0, 4, 4, 5, 5, 0, 0]  # I-I-IV-IV-V-V-I-I
    elif solo_type == "fusion":
        prog = [0, 3, 4, 0, 5, 4, 3, 0]  # modal-ish
    else:
        prog = [0] * bars

    def deg_to_pitch(degree, root_note, sc):
        ns = len(sc)
        oct_shift = degree // ns
        idx = degree % ns
        if idx < 0:
            idx += ns
            oct_shift -= 1
        return root_note + oct_shift * 12 + sc[idx]

    def chromatic_approach(target_pitch, from_below=True):
        """Chromatic approach tone one semitone below/above target."""
        return target_pitch - 1 if from_below else target_pitch + 1

    def enclosure(target_pitch):
        """Bebop enclosure: upper chromatic + lower chromatic + target."""
        return [target_pitch + 1, target_pitch - 1, target_pitch]

    notes = []
    bar_beats = 4.0

    for bar in range(bars):
        bar_start = start_beat + bar * bar_beats
        chord_degree = prog[bar % len(prog)]

        # Chord tones for this bar
        chord_tones = [0, 2, 4]  # root, 3rd, 5th relative to chord degree
        chord_pitches = [deg_to_pitch(chord_degree + ct, base, scale) for ct in chord_tones]

        if solo_type == "bebop":
            # Bebop: chromatic approaches, enclosures, bebop scale passing
            # 8th note line with chromatic passing
            positions = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]
            for j, pos in enumerate(positions):
                if next(rng) < 0.3:
                    # Rest
                    continue
                # Target chord tone on beats 1 and 3
                if j % 4 == 0:
                    target = chord_pitches[j // 4 % len(chord_pitches)]
                    if next(rng) < 0.4:
                        # Enclosure: 2 chromatic approach notes + target
                        enc = enclosure(target)
                        for k, ep in enumerate(enc):
                            if k < 2 and pos + k * 0.25 < bar_beats:
                                notes.append({
                                    "pitch": ep, "start": round(bar_start + pos + k * 0.25, 4),
                                    "duration": 0.25, "velocity": round(velocity * 0.7, 3),
                                })
                            elif k == 2:
                                notes.append({
                                    "pitch": ep, "start": round(bar_start + pos + 0.5, 4),
                                    "duration": 0.5, "velocity": round(velocity * 0.9, 3),
                                })
                    else:
                        notes.append({
                            "pitch": target, "start": round(bar_start + pos, 4),
                            "duration": 0.5, "velocity": round(velocity * 0.9, 3),
                        })
                else:
                    # Passing tone or scale tone
                    sc_deg = int(next(rng) * 7) - 3 + chord_degree
                    pitch = deg_to_pitch(sc_deg, base, scale)
                    if next(rng) < 0.3:
                        # Chromatic passing tone
                        pitch = chromatic_approach(pitch, from_below=next(rng) < 0.5)
                    notes.append({
                        "pitch": pitch, "start": round(bar_start + pos, 4),
                        "duration": 0.5, "velocity": round(velocity * 0.75, 3),
                    })

        elif solo_type == "blues":
            # Blues: pentatonic riffs, blue notes, repetition + variation
            blues_degrees = [0, 3, 5, 6, 7, 10, 12, 10, 7, 5, 3, 0]  # blue note scale
            # Short riffs of 3-4 notes, repeated with variation
            riff_len = 3 + int(next(rng) * 2)
            riff = [blues_degrees[int(next(rng) * len(blues_degrees))] for _ in range(riff_len)]
            riff_pos = 0
            pos = 0.0
            while pos < bar_beats:
                deg = riff[riff_pos % len(riff)]
                dur = 0.5 if next(rng) < 0.7 else 0.25
                # Blue note bend: occasionally add b5
                if next(rng) < 0.15:
                    deg = 6  # blue note
                vel = velocity * (0.7 + next(rng) * 0.3)
                notes.append({
                    "pitch": base + deg, "start": round(bar_start + pos, 4),
                    "duration": dur, "velocity": round(vel, 3),
                })
                pos += dur
                riff_pos += 1
                # Occasional pause for phrasing
                if next(rng) < 0.15:
                    pos += 0.5

        elif solo_type == "rock":
            # Rock: pentatonic riffs, repeated, register climaxes
            rock_degrees = [0, 3, 5, 7, 10, 12, 15, 12, 10, 7, 5, 3]
            # Build a riff and repeat it
            riff = [rock_degrees[int(next(rng) * len(rock_degrees))] for _ in range(4)]
            positions = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]
            for j, pos in enumerate(positions):
                deg = riff[j % len(riff)]
                # Register shift every 4 bars
                oct_shift = 12 * (bar // 4) if bar >= 4 and bar % 4 == 0 else 0
                vel = velocity * (0.7 + 0.3 * (j % 2))  # accent beats 1,3
                notes.append({
                    "pitch": base + deg + oct_shift, "start": round(bar_start + pos, 4),
                    "duration": 0.5, "velocity": round(vel, 3),
                })

        elif solo_type == "jazz_swing":
            # Jazz swing: swung 8ths, guide tones, arpeggios
            # Swing: long-short 8th note pairs (0.66, 0.34)
            pos = 0.0
            beat_num = 0
            while pos < bar_beats - 0.1:
                dur = 0.66 if beat_num % 2 == 0 else 0.34
                # Guide tone: 3rd or 7th of chord
                if beat_num % 4 == 0:
                    deg = chord_degree + (2 if next(rng) < 0.5 else 4)
                else:
                    deg = chord_degree + int(next(rng) * 5) - 2
                pitch = deg_to_pitch(deg, base, scale)
                vel = velocity * (0.8 + 0.2 * (1 if beat_num % 2 == 0 else 0.5))
                notes.append({
                    "pitch": pitch, "start": round(bar_start + pos, 4),
                    "duration": round(dur, 4), "velocity": round(vel, 3),
                })
                pos += dur
                beat_num += 1

        elif solo_type == "fusion":
            # Fusion: wide intervals, chromatic passing, rhythmic displacement
            positions = [0.0, 0.75, 1.5, 2.25, 2.75, 3.5]  # irregular
            for j, pos in enumerate(positions):
                if pos >= bar_beats:
                    break
                # Wide interval jump
                base_deg = chord_degree + int(next(rng) * 7)
                pitch = deg_to_pitch(base_deg, base, scale)
                if next(rng) < 0.3:
                    # Octave jump
                    pitch += 12
                if next(rng) < 0.25:
                    # Chromatic passing
                    pitch = chromatic_approach(pitch, next(rng) < 0.5)
                dur = 0.5 if j % 2 == 0 else 0.25
                vel = velocity * (0.65 + next(rng) * 0.35)
                notes.append({
                    "pitch": pitch, "start": round(bar_start + pos, 4),
                    "duration": dur, "velocity": round(vel, 3),
                })

    notes.sort(key=lambda n: (n["start"], n["pitch"]))

    result = await mcp_opendaw_create_notes_batch(
        json.dumps(notes), unit_index, track_index)

    try:
        data = json.loads(result)
    except Exception:
        data = {"raw": result}

    data["solo"] = True
    data["solo_type"] = solo_type
    data["key_root"] = key_root
    data["scale_type"] = scale_type
    data["bars"] = bars
    data["notes_generated"] = len(notes)
    data["progression"] = prog[:min(len(prog), bars)]
    data["characteristics"] = {
        "bebop": "chromatic approach tones, enclosures, bebop scale passing, chord-tone targeting",
        "blues": "pentatonic riffs, blue notes (b5), repetition + variation, call-response",
        "rock": "pentatonic positions, repeated riffs, register climaxes, rhythmic syncopation",
        "jazz_swing": "swung 8ths (0.66/0.34), guide-tone lines, arpeggio patterns",
        "fusion": "wide intervals, chromatic passing, rhythmic displacement, modal",
    }.get(solo_type, "")

    return json.dumps(data, indent=2)


async def mcp_opendaw_create_solo_automation(
    solo_track: int,
    total_tracks: int,
    start_beat: float,
    end_beat: float,
    unit_indices: str = "",
) -> str:
    """Mute all tracks except the solo track for a beat range, then restore.

    Essential production technique: spotlight one element (bass solo, drum
    break, vocal spotlight) while everything else drops out. Without this you
    need N separate create_mute_automation calls with coordinated timing — this
    tool does it in one shot and guarantees all tracks return audible after.

    Internally calls create_mute_automation for each non-solo track with events
    [[0, false], [start_beat, true], [end_beat, false]] — audible before solo,
    muted during, audible after.

    solo_track: Track index that stays audible throughout (0-based).
    total_tracks: Total number of tracks to manage (e.g. 4 for a 4-track
        arrangement).
    start_beat: Beat position where solo begins (others mute).
    end_beat: Beat position where solo ends (others unmute).
    unit_indices: Optional comma-separated AU indices (e.g. "0,1,2,3").
        If empty, uses 0..total_tracks-1.

    Returns per-track mute schedule and confirmation.

    Examples:
      # Drum break: drums solo for 4 beats (1 bar at 120 BPM)
      create_solo_automation(solo_track=0, total_tracks=4, start_beat=8, end_beat=12)
      # Bass spotlight at bar 9
      create_solo_automation(solo_track=1, total_tracks=4, start_beat=32, end_beat=40)
    """
    # Parse unit indices
    if unit_indices:
        try:
            indices = [int(x.strip()) for x in unit_indices.split(",")]
        except ValueError:
            return "Error: unit_indices must be comma-separated integers"
        if len(indices) != total_tracks:
            return f"Error: expected {total_tracks} unit indices, got {len(indices)}"
    else:
        indices = list(range(total_tracks))

    if not (0 <= solo_track < total_tracks):
        return f"Error: solo_track must be 0..{total_tracks - 1}"
    if start_beat >= end_beat:
        return "Error: end_beat must be greater than start_beat"

    events = json.dumps([[0.0, False], [start_beat, True], [end_beat, False]])
    results = []
    for i, au_idx in enumerate(indices):
        if i == solo_track:
            results.append({"track": i, "unit_index": au_idx, "status": "solo (stays audible)"})
            continue
        try:
            r = await mcp_opendaw_create_mute_automation(au_idx, events)
            results.append({"track": i, "unit_index": au_idx, "result": json.loads(r)})
        except Exception as e:
            results.append({"track": i, "unit_index": au_idx, "error": str(e)})

    return json.dumps({
        "solo_automation": True,
        "solo_track": solo_track,
        "total_tracks": total_tracks,
        "solo_range": [start_beat, end_beat],
        "tracks_muted": total_tracks - 1,
        "per_track": results,
    }, indent=2)


async def mcp_opendaw_create_volume_fade(unit_index: int, direction: str = "out", start_beat: float = 0, duration_beats: float = 4, start_volume_db: float = 0, end_volume_db: float = -60, curve: str = "exp", steps: int = 24) -> str:
    """Create a volume fade automation on an audio unit — fade in or fade out.

    The most common mix technique for intros, outros, breakdowns, and section transitions.
    Creates volume automation events on the AU's volume parameter, ramping from one dB
    level to another. Uses exponential curve by default (natural for amplitude perception).

    unit_index: AU index.
    direction: "out" (fade out, volume decreases) or "in" (fade in, volume increases).
    start_beat: Start position in beats.
    duration_beats: Fade length in beats (default 4 = 1 bar).
    start_volume_db: Starting volume in dB (default: 0 for out, -60 for in).
    end_volume_db: Ending volume in dB (default: -60 for out, 0 for in).
    curve: "exp" (exponential, default — natural for amplitude), "linear", "log".
    steps: Number of automation points (default 24 = smooth).

    Returns events created, fade config, and dB range.

    Examples:
      create_volume_fade(unit_index=0, direction="out", duration_beats=8)
        → 8-beat fade out from 0 dB to -60 dB, exp curve
      create_volume_fade(unit_index=2, direction="in", duration_beats=4, end_volume_db=-3)
        → 4-beat fade in from -60 dB to -3 dB
    """
    # Smart defaults based on direction
    if direction == "in":
        if start_volume_db == 0 and end_volume_db == -60:
            start_volume_db, end_volume_db = -60, 0
    elif direction == "out":
        pass  # defaults already correct

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
            const startDb = {start_volume_db};
            const endDb = {end_volume_db};
            const numSteps = {steps};
            const curveType = "{safe_curve}";

            const units = h.allAUBoxes();
            if (unitIdx >= units.length) return {{error: "No AU at " + unitIdx}};
            const au = units[unitIdx];

            const volField = au["volume"];
            if (!volField) return {{error: "No volume field on AU"}};

            // Convert dB to normalized volume value using VolumeMapper
            // openDAW uses powerByCenter(-96, -9, +6) mapping
            // We approximate: normalized = 10^(dB/20) mapped to 0..1 range
            // For automation we use the field's constraints if available
            const constraints = volField.constraints;
            const minDb = -96, centerDb = -9, maxDb = 6;

            function dbToNorm(db) {{
                if (db <= minDb) return 0;
                if (db >= maxDb) return 1;
                // powerByCenter: exponential mapping through center point
                if (db < centerDb) {{
                    const t = (db - minDb) / (centerDb - minDb);
                    return t * t * 0.5; // lower half: quadratic
                }} else {{
                    const t = (db - centerDb) / (maxDb - centerDb);
                    return 0.5 + t * 0.5; // upper half: linear
                }}
            }}

            const beatRange = endBeat - startBeat;
            const points = [];
            for (let i = 0; i < numSteps; i++) {{
                const t = i / (numSteps - 1);
                let dbVal;
                if (curveType === "exp") {{
                    // Exponential dB ramp: slow start, accelerating
                    dbVal = startDb + (endDb - startDb) * (Math.exp(t * 3) - 1) / (Math.exp(3) - 1);
                }} else if (curveType === "log") {{
                    dbVal = startDb + (endDb - startDb) * Math.log(1 + t * (Math.E - 1));
                }} else {{
                    dbVal = startDb + (endDb - startDb) * t;
                }}
                const beatPos = startBeat + beatRange * t;
                const normVal = dbToNorm(dbVal);
                points.push([beatPos, normVal]);
            }}

            let autoTrack;
            h.editing.modify(() => {{
                autoTrack = h.api.createAutomationTrack(au, volField);
                const volClip = h.api.createValueClip(autoTrack, 0, {{name: "volume"}});
                const volCol = volClip.events?.targetVertex?.unwrap?.()?.box;
                if (!volCol) throw new Error("No event collection on volume clip");
                points.forEach(([beatPos, value], i) => {{
                    ValueEventBox.create(h.boxGraph, UUID.generate(), (box) => {{
                        box.events.refer(volCol.events);
                        box.position.setValue(Math.round(beatPos * Quarter));
                        box.index.setValue(i);
                        box.value.setValue(value);
                        box.interpolation.setValue(1);
                    }});
                }});
            }});

            return {{
                success: true,
                direction: "{direction}",
                events_created: points.length,
                unit_index: unitIdx,
                start_beat: startBeat,
                end_beat: endBeat,
                db_range: [startDb, endDb],
                curve: curveType,
                track_index: autoTrack?.index?.getValue?.() ?? 0,
                preview: points.slice(0, 6).map(([b, v]) => ({{beat: Math.round(b * 100) / 100, vol_norm: Math.round(v * 1000) / 1000}})),
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_move_automation_event(unit_index: int, track_index: int, event_index: int, new_position_beats: float) -> str:
    """Move an automation event to a new position on the timeline.

    unit_index: AU index.
    track_index: Value (automation) track index.
    event_index: Event index (from list_automation_events).
    new_position_beats: New position in beats (float).

    Returns success with old and new positions.
    """
    new_ppqn = int(new_position_beats * 960)
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const auAdapter = h.allAUs()[{unit_index}];
            if (!auAdapter) return {{error: "No AU at {unit_index}"}};
            const tracks = auAdapter.tracks.collection.adapters();
            if ({track_index} >= tracks.length) return {{error: "No track {track_index}"}};
            const track = tracks[{track_index}];
            const regions = track.regions.collection.asArray();
            if (regions.length === 0) return {{error: "No regions on track"}};
            const region = regions[0];
            if (!region.isValueRegion?.()) return {{error: "Not a value region"}};
            const optCol = region.optCollection;
            if (optCol.isEmpty()) return {{error: "No event collection"}};
            const collection = optCol.unwrap();
            const events = collection.events.asArray();
            if ({event_index} >= events.length) return {{error: "No event {event_index} (found " + events.length + ")"}};
            const evt = events[{event_index}];
            const oldPos = evt.position;
            h.editing.modify(() => {{
                evt.box.position.setValue({new_ppqn});
            }});
            collection.requestSorting();
            return {{success: true, old_position_ppqn: oldPos, new_position_ppqn: {new_ppqn}, old_position_beats: oldPos / h.ppqn.Quarter, new_position_beats: {new_position_beats}}};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_remove_audio_bus(bus_index: int, fx_unit_index: int) -> str:
    """Remove an FX audio bus and its associated audio unit.

Provide either bus_index (from list_audio_buses) or fx_unit_index (from create_send).
Cannot remove the primary output bus (index 0).

bus_index: Bus index to remove (must be > 0, i.e. not primary).
fx_unit_index: Alternative — the FX AU index returned by create_send.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const busIdx = {bus_index};
        const fxUnitIdx = {fx_unit_index};
        const buses = h.busBoxes();
        const units = h.allAUBoxes();

        let targetBus = null;
        let targetUnit = null;

        if (busIdx >= 0) {{
            if (busIdx === 0) return {{error: "Cannot remove primary output bus"}};
            if (busIdx >= buses.length) return {{error: "No bus at index " + busIdx}};
            targetBus = buses[busIdx];
            // Find associated AU
            try {{
                const targetBox = targetBus.output.targetVertex?.unwrap?.()?.box;
                if (targetBox) targetUnit = units.find(u => u.address.equals(targetBox.address));
            }} catch(e) {{}}
        }} else if (fxUnitIdx >= 0) {{
            if (fxUnitIdx >= units.length) return {{error: "No AU at index " + fxUnitIdx}};
            targetUnit = units[fxUnitIdx];
            // Find bus that routes to this AU
            for (const b of buses) {{
                try {{
                    const tb = b.output.targetVertex?.unwrap?.()?.box;
                    if (tb && tb.address.equals(targetUnit.address)) {{ targetBus = b; break; }}
                }} catch(e) {{}}
            }}
        }} else {{
            return {{error: "Provide bus_index or fx_unit_index"}};
        }}

        if (!targetBus && !targetUnit) return {{error: "Could not find bus or unit to remove"}};

        const busName = targetBus?.label?.getValue?.() ?? "unknown";
        h.modify(() => {{
            // Remove sends pointing to this bus first
            if (targetBus) {{
                for (const au of units) {{
                    const sends = h.sendBoxes(au);
                    for (const s of sends) {{
                        try {{
                            const tb = s.targetBus.targetVertex?.unwrap?.()?.box;
                            if (tb && tb.address.equals(targetBus.address)) s.delete();
                        }} catch(e) {{}}
                    }}
                }}
            }}
            // Delete bus and unit
            if (targetBus) targetBus.delete();
            if (targetUnit) targetUnit.delete();
        }});

        return {{
            success: true,
            removed_bus_name: busName,
            removed_fx_unit_index: fxUnitIdx >= 0 ? fxUnitIdx : (targetUnit ? units.findIndex(u => u.address.equals(targetUnit.address)) : -1),
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_remove_send(unit_index: int, send_index: int) -> str:
    """Remove an aux send from an audio unit.

unit_index: Source audio unit index.
send_index: Send index to remove (from list_sends).
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const srcIdx = {unit_index};
        const sendIdx = {send_index};
        const units = h.allAUBoxes();
        if (srcIdx >= units.length) return {{error: "No AU at index " + srcIdx}};
        const au = units[srcIdx];

        const sends = h.sendBoxes(au);
        if (sendIdx >= sends.length) return {{error: "No send at index " + sendIdx + " (total: " + sends.length + ")"}};

        const sendBox = sends[sendIdx];
        h.modify(() => {{
            sendBox.delete();
        }});

        return {{
            success: true,
            unit_index: srcIdx,
            removed_send_index: sendIdx,
            remaining_sends: h.sendBoxes(au).length,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_automation_interpolation(unit_index: int, track_index: int, region_index: int, event_index: int, interpolation: str, curve_slope: float = 0.5) -> str:
    """Set the interpolation type of an existing automation event.

    Changes how the automation curve transitions from this event to the next.

    unit_index: AU index.
    track_index: Value (automation) track index.
    region_index: Region index containing the event.
    event_index: Event index within the region's collection.
    interpolation: "none" (step/hold), "linear" (straight ramp), or "curve" (custom slope).
    curve_slope: Slope for curve interpolation (0.0-1.0). Only used if interpolation="curve".

    Returns success, or error.
    """

    safe_interpolation = interpolation.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const region = h.region({unit_index}, {track_index}, {region_index});
            if (!region.isValueRegion?.()) return {{error: "Region is not a value region"}};
            const optCol = region.optCollection;
            if (optCol.isEmpty()) return {{error: "No event collection"}};
            const collection = optCol.unwrap();
            const events = collection.events.asArray();
            if ({event_index} >= events.length) return {{error: "No event {event_index}"}};
            const event = events[{event_index}];
            h.modify(() => {{
                const interpType = "{safe_interpolation}";
                let interpolation;
                if (interpType === "none") interpolation = {{type: "none"}};
                else if (interpType === "curve") interpolation = {{type: "curve", slope: {curve_slope}}};
                else interpolation = {{type: "linear"}};
                event.interpolation = interpolation;
            }});
            return {{
                success: true,
                interpolation: event.interpolation.type,
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


# ─────────────────────────────────────────────────────────────────────
# Note Collection Analysis (163-164)
# ─────────────────────────────────────────────────────────────────────


async def mcp_opendaw_set_bus_color(bus_index: int, hue: int) -> str:
    """Set the color (hue 0-360) of an audio bus.

    bus_index: Bus index.
    hue: Color hue 0-360 (HSL).

    Returns success or error.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const buses = h.rootBoxAdapter.audioBusses.adapters();
            if ({bus_index} >= buses.length) return {{error: "No bus at index " + {bus_index}}};
            const bus = buses[{bus_index}];
            h.editing.modify(() => {{
                bus.colorField.setValue({hue});
            }});
            return {{success: true, bus_index: {bus_index}, hue: {hue}}};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


# ─── Modular System ──────────────────────────────────────────────────


async def mcp_opendaw_set_bus_enabled(bus_index: int, enabled: bool) -> str:
    """Enable or mute an audio bus (FX bus A/B comparison).

bus_index: Bus index from list_audio_buses (0 = primary output).
enabled: True to enable, False to mute.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const busIdx = {bus_index};
        const enableVal = {json.dumps(enabled)};
        const buses = h.busBoxes();
        if (busIdx >= buses.length) return {{error: "No bus at index " + busIdx + " (total: " + buses.length + ")"}};

        h.modify(() => {{
            buses[busIdx].enabled.setValue(enableVal);
        }});

        return {{
            success: true,
            bus_index: busIdx,
            enabled: enableVal,
            bus_name: buses[busIdx].label?.getValue?.() ?? "Bus " + busIdx,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_bus_label(bus_index: int, label: str) -> str:
    """Set the label (name) of an audio bus.

    bus_index: Bus index from create_audio_bus.
    label: New name for the bus (e.g. "Reverb Bus", "Drum Bus").

    Returns success or error.
    """
    safe_label = json.dumps(label)
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const buses = h.rootBoxAdapter.audioBusses.adapters();
            if ({bus_index} >= buses.length) return {{error: "No bus at index " + {bus_index}}};
            const bus = buses[{bus_index}];
            h.editing.modify(() => {{
                bus.labelField.setValue({safe_label});
            }});
            return {{success: true, bus_index: {bus_index}, label: {safe_label}}};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_send_level(src_unit: int, send_index: int, level_db: float) -> str:
    """Set the send level for an existing aux send.

src_unit: Source audio unit index.
send_index: Send index on the source AU (from create_send return).
level_db: Send level in dB.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const srcIdx = {src_unit};
        const sendIdx = {send_index};
        const levelDb = {level_db};

        const units = h.allAUBoxes();
        if (srcIdx >= units.length) return {{error: "No AU at index " + srcIdx}};
        const au = units[srcIdx];

        const sends = h.sendBoxes(au);
        if (sendIdx >= sends.length) return {{error: "No send at index " + sendIdx + " (total: " + sends.length + ")"}};

        h.modify(() => {{
            sends[sendIdx].sendGain.setValue(levelDb);
        }});

        return {{
            success: true,
            src_unit: srcIdx,
            send_index: sendIdx,
            new_level_db: levelDb,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_send_pan(unit_index: int, send_index: int, pan: float) -> str:
    """Set the stereo pan for an aux send (-1.0 = full left, 0.0 = center, 1.0 = full right).

unit_index: Source audio unit index.
send_index: Send index on the source AU.
pan: Pan value from -1.0 (left) to 1.0 (right).
"""
    pan_val = json.dumps(pan)
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const srcIdx = {unit_index};
        const sendIdx = {send_index};
        const panVal = {pan_val};
        const units = h.allAUBoxes();
        if (srcIdx >= units.length) return {{error: "No AU at index " + srcIdx}};
        const au = units[srcIdx];

        const sends = h.sendBoxes(au);
        if (sendIdx >= sends.length) return {{error: "No send at index " + sendIdx}};

        h.modify(() => {{
            sends[sendIdx].sendPan.setValue(panVal);
        }});

        return {{
            success: true,
            unit_index: srcIdx,
            send_index: sendIdx,
            pan: panVal,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_send_routing(unit_index: int, send_index: int, routing: str) -> str:
    """Set the routing mode for an aux send (pre-fader or post-fader).

unit_index: Source audio unit index.
send_index: Send index on the source AU.
routing: 'pre' (pre-fader, before volume/pan) or 'post' (post-fader, default).
"""
    routing_val = json.dumps(routing)
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const srcIdx = {unit_index};
        const sendIdx = {send_index};
        const routingVal = {routing_val};
        const units = h.allAUBoxes();
        if (srcIdx >= units.length) return {{error: "No AU at index " + srcIdx}};
        const au = units[srcIdx];

        const sends = h.sendBoxes(au);
        if (sendIdx >= sends.length) return {{error: "No send at index " + sendIdx}};

        h.modify(() => {{
            sends[sendIdx].routing.setValue(routingVal);
        }});

        return {{
            success: true,
            unit_index: srcIdx,
            send_index: sendIdx,
            routing: routingVal === 0 ? "pre" : "post",
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_stereo_tool_panning(unit_index: int, effect_index: int, panning_mixing: int) -> str:
    """Set the panning mixing mode on a StereoTool effect.

    unit_index: AU index.
    effect_index: Effect index in the audio effect chain (must be a StereoTool).
    panning_mixing: Panning law (0=linear, 1=equal-power, or other supported values).
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const au = h.auBox({unit_index});
            const fx = h.effectBoxes(au);
            if ({effect_index} >= fx.length) return {{error: "No effect at index " + {effect_index}}};
            const fxAdapter = fx[{effect_index}];
            const box = fxAdapter.box;
            if (!box.panningMixing) return {{error: "Effect has no panningMixing (not a StereoTool)"}};
            const oldValue = box.panningMixing.getValue();
            h.modify(() => {{
                box.panningMixing.setValue({panning_mixing});
            }});
            return {{
                success: true,
                effect: box.constructor.name,
                old_value: oldValue,
                new_value: box.panningMixing.getValue(),
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_update_automation_event(unit_index: int, track_index: int, event_index: int, value: float = -1, interpolation: str = "", curve_slope: float = -1) -> str:
    """Update an existing automation event's value and/or interpolation.

    Only updates parameters that are provided (value >= 0, non-empty interpolation, curve_slope >= 0).

    unit_index: AU index.
    track_index: Value (automation) track index.
    event_index: Event index (from list_automation_events).
    value: New normalized value 0.0-1.0 (skip if -1).
    interpolation: "none", "linear", or "curve" (skip if empty string).
    curve_slope: Slope for curve interpolation 0.0-1.0 (skip if -1).

    Returns success with updated values.
    """
    updates = []
    if value >= 0:
        updates.append(f"evt.box.value.setValue({value});")
    if interpolation:
        if interpolation == "none":
            updates.append("evt.interpolation = {type: 'none'};")
        elif interpolation == "linear":
            updates.append("evt.interpolation = {type: 'linear'};")
        elif interpolation == "curve" and curve_slope >= 0:
            updates.append(f"evt.interpolation = {{type: 'curve', slope: {curve_slope}}};")
    update_js = "\n                ".join(updates)
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const auAdapter = h.allAUs()[{unit_index}];
            if (!auAdapter) return {{error: "No AU at {unit_index}"}};
            const tracks = auAdapter.tracks.collection.adapters();
            if ({track_index} >= tracks.length) return {{error: "No track {track_index}"}};
            const track = tracks[{track_index}];
            const regions = track.regions.collection.asArray();
            if (regions.length === 0) return {{error: "No regions on track"}};
            const region = regions[0];
            if (!region.isValueRegion?.()) return {{error: "Not a value region"}};
            const optCol = region.optCollection;
            if (optCol.isEmpty()) return {{error: "No event collection"}};
            const collection = optCol.unwrap();
            const events = collection.events.asArray();
            if ({event_index} >= events.length) return {{error: "No event {event_index}"}};
            const evt = events[{event_index}];
            const oldVal = evt.value;
            const oldInterp = evt.interpolation.type;
            h.editing.modify(() => {{
                const evt2 = collection.events.asArray()[{event_index}];
                {update_js}
            }});
            const updated = collection.events.asArray()[{event_index}];
            return {{success: true, old_value: oldVal, new_value: updated.value, old_interpolation: oldInterp, new_interpolation: updated.interpolation.type}};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

