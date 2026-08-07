"""
Transport Tools
===============
Project transport control: play, stop, position, tempo, markers, time signatures.
"""

import json
import asyncio
from mcp.types import ToolAnnotations

# These will be injected by server.py
bridge = None
_wrap_eval = None


def init_transport_tools(bridge_instance, wrap_eval_func):
    """Initialize transport tools with shared dependencies."""
    global bridge, _wrap_eval
    bridge = bridge_instance
    _wrap_eval = wrap_eval_func



async def mcp_opendaw_add_marker(position_beats: int, label: str) -> str:
    """Add a timeline marker at a position.

Markers label song structure points (Verse, Chorus, Bridge, etc.).
Visible on the timeline ruler.

position_beats: Position in beats.
label: Marker text (e.g. "Verse 1", "Chorus", "Drop").
"""
    safe_label = label.replace('"', '').replace("'", '').replace('\\', '')
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const MarkerBox = window.DAW_MarkerBox;
        if (!MarkerBox) return {{error: "MarkerBox not loaded — reload page"}};

        const markerTrack = h.timelineBox?.markerTrack;
        if (!markerTrack) return {{error: "No markerTrack on timeline"}};

        const pos = Math.round({position_beats} * h.ppqn.Quarter);
        let markerIdx = -1;

        h.modify(() => {{
            MarkerBox.create(h.boxGraph, h.uuid.generate(), (box) => {{
                box.position.setValue(pos);
                box.plays.setValue(0);
                box.label.setValue("{safe_label}");
                box.hue.setValue(0);
                box.track.refer(markerTrack.markers);
            }});
        }});

        const markers = h.markerBoxes(markerTrack);

        markerIdx = markers.length - 1;
        return {{
            success: true,
            marker_index: markerIdx,
            position_beats: pos / h.ppqn.Quarter,
            label: "{safe_label}",
            total_markers: markers.length,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_add_signature_change(position_beats: int, numerator: int, denominator: int) -> str:
    """Add a time signature change at a specific position in the track.

Unlike set_time_signature (which sets the global default), this creates
a SignatureEventBox on the timeline's signature track, allowing time
signature changes mid-track (e.g. 4/4 → 3/4 → 4/4).

position_beats: Position in beats where the change occurs.
numerator: Number of beats per bar (top number).
denominator: Note value per beat (bottom number: 4=quarter, 8=eighth).

Returns the created signature event details.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const SignatureEventBox = window.DAW_SignatureEventBox;
        const posTicks = Math.round({position_beats} * h.ppqn.Quarter);
        const nom = {numerator};
        const denom = {denominator};

        if (!SignatureEventBox) return {{error: "SignatureEventBox not loaded — reload page"}};
        const tl = h.timelineBox;
        if (!tl || !tl.signatureTrack) return {{error: "No signatureTrack on timeline"}};

        const sigTrack = tl.signatureTrack;

        let created;
        h.modify(() => {{
            // Find next index
            const existing = h.eventBoxes(sigTrack);
            const maxIndex = existing.reduce((mx, b) => Math.max(mx, b.index?.getValue?.() ?? 0), -1);
            const idx = maxIndex + 1;

            created = SignatureEventBox.create(h.boxGraph, h.uuid.generate(), (box) => {{
                box.events.refer(sigTrack.events);
                box.index.setValue(idx);
                box.relativePosition.setValue(posTicks);
                box.nominator.setValue(nom);
                box.denominator.setValue(denom);
            }});
        }});

        // List all signature events
        const allEvents = h.eventBoxes(sigTrack);
        const eventList = allEvents.map(e => ({{
            position_beats: (e.relativePosition?.getValue?.() ?? 0) / h.ppqn.Quarter,
            numerator: e.nominator?.getValue?.() ?? 4,
            denominator: e.denominator?.getValue?.() ?? 4,
        }})).sort((a, b) => a.position_beats - b.position_beats);

        return {{
            success: true,
            position_beats: {position_beats},
            numerator: nom,
            denominator: denom,
            total_events: allEvents.length,
            events: eventList,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_add_tempo_change(position_beats: float, bpm: float, interpolation: str) -> str:
    """Add a tempo (BPM) change at a specific position in the track.

Creates a ValueEventBox on the timeline's tempo track, allowing BPM
automation mid-track (e.g. 120 BPM → 90 BPM → 140 BPM).

The tempo track uses normalized values (0..1) mapped to minBpm..maxBpm
(default 60..240). This tool handles the conversion automatically.

position_beats: Position in beats where the tempo change occurs.
bpm: Target BPM (60-240).
interpolation: 'linear' for smooth transition, 'hold' for instant jump.

Returns the created tempo event and full tempo map.
"""
    interp_val = json.dumps(interpolation)
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const ValueEventBox = window.DAW_ValueEventBox;
        const ValueEventCollectionBox = window.DAW_ValueEventCollectionBox;
        const posTicks = Math.round({position_beats} * h.ppqn.Quarter);
        const targetBpm = {bpm};
        const interpVal = {interp_val};

        if (!ValueEventBox || !ValueEventCollectionBox) return {{error: "Box types not loaded — reload page"}};
        const tl = h.timelineBox;
        if (!tl || !tl.tempoTrack) return {{error: "No tempoTrack on timeline"}};

        const tempoTrack = tl.tempoTrack;
        const minBpm = tempoTrack.minBpm.getValue();
        const maxBpm = tempoTrack.maxBpm.getValue();
        const normalizedValue = (targetBpm - minBpm) / (maxBpm - minBpm);

        h.modify(() => {{
            tempoTrack.enabled.setValue(true);

            let collection;
            const existingVertex = tempoTrack.events.targetVertex;
            if (!existingVertex.isEmpty()) {{
                collection = existingVertex.unwrap().box;
            }} else {{
                collection = ValueEventCollectionBox.create(h.boxGraph, h.uuid.generate());
                tempoTrack.events.refer(collection.owners);
            }}

            const existingEvents = h.eventBoxes(collection);
            const maxIndex = existingEvents.reduce((mx, b) => Math.max(mx, b.index?.getValue?.() ?? 0), -1);

            ValueEventBox.create(h.boxGraph, h.uuid.generate(), (box) => {{
                box.events.refer(collection.events);
                box.position.setValue(posTicks);
                box.index.setValue(maxIndex + 1);
                box.value.setValue(Math.max(0, Math.min(1, normalizedValue)));
                box.interpolation.setValue(interpVal);
            }});
        }});

        const coll = tempoTrack.events.targetVertex.unwrap().box;
        const events = h.eventBoxes(coll);
        const eventList = events.map(e => ({{
            position_beats: (e.position?.getValue?.() ?? 0) / h.ppqn.Quarter,
            bpm: Math.round(minBpm + (e.value?.getValue?.() ?? 0) * (maxBpm - minBpm)),
            interpolation: e.interpolation?.getValue?.() === 1 ? "linear" : "hold",
        }})).sort((a, b) => a.position_beats - b.position_beats);

        return {{
            success: true,
            position_beats: {position_beats},
            bpm: targetBpm,
            min_bpm: minBpm,
            max_bpm: maxBpm,
            total_events: events.length,
            events: eventList,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_redo() -> str:
    """Redo the last undone operation."""
    result = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        if (h.editing.canRedo) {
            h.editing.redo();
            return {success: true, action: "redo"};
        }
        return {success: false, message: "Nothing to redo"};
    }""")
    return _wrap_eval(result)


async def mcp_opendaw_serialize() -> str:
    """Serialize the current project state to JSON. Returns the serialized project data."""
    result = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        const json = h.boxGraph.toJSON();
        return {
            success: true,
            data: json,
            box_count: [...h.boxGraph.boxes()].length,
        };
    }""")
    return _wrap_eval(result)


async def mcp_opendaw_set_bpm(bpm: int) -> str:
    """Set the project tempo in BPM."""
    _finish = _log_tool_call("set_bpm")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        h.modify(() => h.api.setBpm({bpm}));
        return {{success: true, bpm: h.timelineBox?.bpm?.getValue?.()}};
    }}""")
    _finish(True)
    return _wrap_eval(result)


async def mcp_opendaw_set_groove_shuffle(amount: int) -> str:
    """Set the groove/shuffle (swing) amount for the project.

amount: 0.0 = straight (no swing), 1.0 = full swing.
Typical values: 0.15 = light swing, 0.25 = moderate, 0.5 = strong triplet feel.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const grooveVertex = h.rootBox?.groove?.targetVertex;
        if (!grooveVertex) return {{error: "No groove on rootBox"}};
        const grooveBox = grooveVertex.unwrap().box;
        const oldAmount = grooveBox.amount?.getValue?.() ?? 0;
        h.modify(() => {{
            grooveBox.amount.setValue({amount});
        }});
        return {{
            success: true,
            old_amount: oldAmount,
            new_amount: grooveBox.amount.getValue(),
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_loop_region(from_beat: int, to_beat: int, enabled: bool) -> str:
    """Set the playback loop region.

When enabled, playback loops between from_beat and to_beat.
Set enabled=false to disable loop (region is kept but inactive).

from_beat: Loop start in beats.
to_beat: Loop end in beats.
enabled: Whether loop is active.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const PPQN = h.ppqn;
        const loop = h.timelineBox?.loopArea;
        if (!loop) return {{error: "No loopArea on timeline"}};

        const fromTicks = Math.round({from_beat} * PPQN.Quarter);
        const toTicks = Math.round({to_beat} * PPQN.Quarter);
        const oldEnabled = loop.enabled?.getValue?.() ?? false;
        const oldFrom = loop.from?.getValue?.() ?? 0;
        const oldTo = loop.to?.getValue?.() ?? 0;

        h.modify(() => {{
            loop.from.setValue(fromTicks);
            loop.to.setValue(toTicks);
            loop.enabled.setValue({json.dumps(enabled)});
        }});

        return {{
            success: true,
            enabled: {json.dumps(enabled)},
            from_beats: fromTicks / PPQN.Quarter,
            to_beats: toTicks / PPQN.Quarter,
            old_enabled: oldEnabled,
            old_from_beats: oldFrom / PPQN.Quarter,
            old_to_beats: oldTo / PPQN.Quarter,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_marker_label(marker_index: int, label: str) -> str:
    """Rename a timeline marker.

marker_index: Index from list_markers (0-based).
label: New label text.
"""
    safe_label = label.replace('"', '').replace("'", '').replace('\\', '')
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const markerTrack = h.timelineBox?.markerTrack;
        if (!markerTrack) return {{error: "No markerTrack"}};
        const markers = h.markerBoxes(markerTrack);

        if ({marker_index} >= markers.length) return {{error: "No marker at index {marker_index}"}};
        const marker = markers[{marker_index}];
        const oldLabel = marker.label?.getValue?.() ?? "";
        h.modify(() => {{ marker.label.setValue("{safe_label}"); }});
        return {{
            success: true,
            marker_index: {marker_index},
            old_label: oldLabel,
            new_label: marker.label.getValue(),
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_marker_position(marker_index: int, position_beats: int) -> str:
    """Move a timeline marker to a new position.

marker_index: Index from list_markers (0-based).
position_beats: New position in beats.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const markerTrack = h.timelineBox?.markerTrack;
        if (!markerTrack) return {{error: "No markerTrack"}};
        const markers = h.markerBoxes(markerTrack);

        if ({marker_index} >= markers.length) return {{error: "No marker at index {marker_index}"}};
        const marker = markers[{marker_index}];
        const oldPos = marker.position?.getValue?.() ?? 0;
        const newPos = Math.round({position_beats} * h.ppqn.Quarter);
        h.modify(() => {{ marker.position.setValue(newPos); }});
        return {{
            success: true,
            marker_index: {marker_index},
            label: marker.label?.getValue?.() ?? "",
            old_position_beats: oldPos / h.ppqn.Quarter,
            new_position_beats: newPos / h.ppqn.Quarter,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_marker_repeat(marker_index: int, repeat_count: int) -> str:
    """Set the repeat count on a timeline marker.

marker_index: Index from list_markers (0-based).
repeat_count: 0 = infinite repeat, 1-16 = N repeats.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const markerTrack = h.timelineBox?.markerTrack;
        if (!markerTrack) return {{error: "No markerTrack"}};
        const markers = h.markerBoxes(markerTrack);
        if ({marker_index} >= markers.length) return {{error: "No marker at index {marker_index}"}};
        const marker = markers[{marker_index}];
        if (!marker.box.plays) return {{error: "Marker has no plays field"}};
        const oldPlays = marker.box.plays?.getValue?.() ?? 1;
        h.modify(() => {{ marker.box.plays.setValue({repeat_count}); }});
        return {{
            success: true,
            marker_index: {marker_index},
            old_repeat: oldPlays,
            new_repeat: marker.box.plays.getValue(),
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_position(position: int) -> str:
    """Set the playback position in beats."""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const pos = {position} * h.ppqn.Quarter;
        h.modify(() => {{ h.engine.setPosition(pos); }});
        return {{success: true, position: {position}}};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_time_signature(numerator: int, denominator: int) -> str:
    """Set the project time signature (e.g. 4/4, 3/4, 6/8, 7/8).

numerator: Number of beats per bar (top number, e.g. 4, 3, 6, 7).
denominator: Note value per beat (bottom number: 4=quarter, 8=eighth).
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const tl = h.timelineBox;
        if (!tl || !tl.signature) return {{error: "timelineBox.signature not found"}};
        h.modify(() => {{
            tl.signature.nominator.setValue({numerator});
            tl.signature.denominator.setValue({denominator});
        }});
        return {{
            success: true,
            numerator: tl.signature.nominator.getValue(),
            denominator: tl.signature.denominator.getValue(),
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_tuning(frequency: int) -> str:
    """Set the A4 base frequency (concert pitch tuning).

frequency: A4 frequency in Hz. Default 440. Common alternatives: 432 (verdi), 415 (baroque), 466 (baroque organ).
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const bf = h.rootBox?.baseFrequency;
        if (!bf) return {{error: "No baseFrequency on rootBox"}};
        const old = bf.getValue();
        h.modify(() => {{
            bf.setValue({frequency});
        }});
        return {{
            success: true,
            old_frequency: old,
            new_frequency: bf.getValue(),
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_transport(action: str) -> str:
    """Control transport: play, stop, or toggle.

action: "play", "stop", or "toggle"
"""
    valid_actions = {"play", "stop", "toggle"}
    act = (action or "toggle").lower().strip()
    if act not in valid_actions:
        return json.dumps({"error": f"Invalid action '{act}'. Must be one of: {', '.join(sorted(valid_actions))}"})
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const eng = h.engine;
        const isPlaying = !!eng.isPlaying?.getValue?.();
        if ('{act}' === 'play') {{
            if (!isPlaying) eng.play();
            return {{status: 'playing'}};
        }} else if ('{act}' === 'stop') {{
            if (isPlaying) eng.stop();
            return {{status: 'stopped'}};
        }} else {{
            if (isPlaying) {{ eng.stop(); return {{status: 'stopped'}}; }}
            else {{ eng.play(); return {{status: 'playing'}}; }}
        }}
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_undo() -> str:
    """Undo the last editing operation."""
    result = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        if (h.editing.canUndo) {
            h.editing.undo();
            return {success: true, action: "undo"};
        }
        return {success: false, message: "Nothing to undo"};
    }""")
    return _wrap_eval(result)

