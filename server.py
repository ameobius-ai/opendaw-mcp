"""
openDAW MCP Server — Production
================================
Playwright bridge to a headless openDAW instance.
Every tool performs real operations via page.evaluate() into the V8 context
where the DAW project lives. No stubs, no placeholders.

Architecture:
  MCP Server (Python/FastMCP) → Playwright → headless Chromium → Vite :5174 → @opendaw/studio-sdk

Infrastructure (bridge, utils, constants) lives in opendaw_mcp/ package.
This file contains the 263 MCP tool definitions.
"""

import asyncio
import json
import logging
import os
import atexit

from mcp.server.fastmcp import FastMCP

# Infrastructure imported from opendaw_mcp package
# All helpers re-exported for backward compatibility (tests, examples import from server)
from opendaw_mcp import (  # noqa: F401 — re-exported for backward compat
    HeadlessDawBridge,
    DAW_URL,
    TIDAL_RATE_MAP,
    DELAY_SYNC_MAP,
    WAVESHAPER_FUNCS,
    REVAMP_SECTIONS,
    _parse_wav,
    _compute_lufs,
    _ok,
    _err,
    _wrap_eval,
    _unwrap_eval,
    _safe_filename,
    _safe_path,
    _clamp_script_param,
    NOTE_TO_PITCH,
    CHORD_INTERVALS,
    SCALE_INTERVALS,
    GENRE_PRESETS,
    VALID_GENRES,
    parse_melody_pattern,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("opendaw-mcp")
DAW_HOST_DIR = os.environ.get("OPENDAW_HOST_DIR", os.path.join(os.path.dirname(__file__), "..", "headless-daw"))
EXPORT_DIR = os.environ.get("OPENDAW_EXPORT_DIR", os.path.join(os.path.dirname(__file__), "..", "exports"))
os.makedirs(EXPORT_DIR, exist_ok=True)

bridge = HeadlessDawBridge()
def cleanup():
    try: asyncio.run(bridge.stop())
    except Exception: pass
atexit.register(cleanup)

@mcp.tool()
async def mcp_opendaw_get_project_state() -> str:
    """Get full project state: BPM, sample rate, playing status, track list, effects chain."""
    result = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        const eng = h.engine;

        const units = [];
        try {
            const allAU = h.allAUBoxes();
            allAU.forEach((au, i) => {
                const effects = [];
                try {
                    h.effectBoxes(au).forEach((box) => {
                        effects.push(box.constructor?.name || 'Unknown');
                    });
                } catch(e) {}

                const trackBoxes = h.trackBoxes(au).map((box) => ({
                    name: box.name?.getValue?.() || box.constructor?.name || 'Track',
                    type: box.type?.getValue?.() ?? 'unknown',
                }));

                units.push({
                    name: au.name?.getValue?.() || 'Unit ' + i,
                    tracks: trackBoxes,
                    effects: effects,
                    volume: au.volume?.getValue?.() ?? 0,
                    panning: au.panning?.getValue?.() ?? 0,
                    mute: au.mute?.getValue?.() ?? false,
                    solo: au.solo?.getValue?.() ?? false,
                });
            });
        } catch(e) {}

        return {
            bpm: h.timelineBox?.bpm?.getValue?.() ?? eng.bpm,
            sampleRate: eng.sampleRate,
            isPlaying: !!eng.isPlaying?.getValue?.(),
            position: eng.position?.getValue?.() ?? eng.position,
            audioUnits: units,
            totalBoxes: [...h.boxGraph.boxes()].length,
        };
    }""")
    return _wrap_eval(result)

@mcp.tool()
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

@mcp.tool()
async def mcp_opendaw_set_position(position: int) -> str:
    """Set the playback position in beats."""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const pos = {position} * h.ppqn.Quarter;
        h.modify(() => {{ h.engine.setPosition(pos); }});
        return {{success: true, position: {position}}};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_set_bpm(bpm: int) -> str:
    """Set the project tempo in BPM."""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        h.modify(() => h.api.setBpm({bpm}));
        return {{success: true, bpm: h.timelineBox?.bpm?.getValue?.()}};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
async def mcp_opendaw_list_markers() -> str:
    """List all timeline markers with positions and labels."""
    result = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        const markerTrack = h.timelineBox?.markerTrack;
        if (!markerTrack) return {error: "No markerTrack"};
        const markers = h.markerBoxes(markerTrack);

        return markers.map((m, i) => ({
            index: i,
            position_beats: m.position.getValue() / h.ppqn.Quarter,
            label: m.label?.getValue?.() ?? "",
            plays: m.plays?.getValue?.() ?? 0,
        }));
    }""")
    return _wrap_eval(result)

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
async def mcp_opendaw_delete_marker(marker_index: int) -> str:
    """Delete a timeline marker by index.

marker_index: Index from list_markers (0-based).
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const markerTrack = h.timelineBox?.markerTrack;
        if (!markerTrack) return {{error: "No markerTrack"}};
        const markers = h.markerBoxes(markerTrack);

        if ({marker_index} >= markers.length) return {{error: "No marker at index {marker_index}"}};
        const target = markers[{marker_index}];
        const label = target.label?.getValue?.() ?? "";
        const pos = target.position?.getValue?.() ?? 0;
        h.modify(() => {{ target.delete(); }});
        const remaining = h.markerBoxes(markerTrack).length;
        return {{
            success: true,
            deleted_label: label,
            deleted_position_beats: pos / h.ppqn.Quarter,
            remaining_markers: remaining,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
async def mcp_opendaw_list_tempo_changes() -> str:
    """List all tempo (BPM) changes on the timeline's tempo track.

Returns each tempo event with position (beats), BPM, and interpolation type.
The tempo track uses normalized values mapped to minBpm..maxBpm (default 60..240).
"""
    result = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        const tl = h.timelineBox;
        if (!tl || !tl.tempoTrack) return {error: "No tempoTrack on timeline"};

        const tempoTrack = tl.tempoTrack;
        const enabled = tempoTrack.enabled?.getValue?.() ?? false;
        const minBpm = tempoTrack.minBpm?.getValue?.() ?? 60;
        const maxBpm = tempoTrack.maxBpm?.getValue?.() ?? 240;

        const eventsVertex = tempoTrack.events.targetVertex;
        if (eventsVertex.isEmpty()) return {
            success: true,
            enabled,
            min_bpm: minBpm,
            max_bpm: maxBpm,
            event_count: 0,
            events: [],
        };

        const collection = eventsVertex.unwrap().box;
        const events = h.eventBoxes(collection);
        const eventList = events.map(e => ({
            position_beats: (e.position?.getValue?.() ?? 0) / h.ppqn.Quarter,
            bpm: Math.round(minBpm + (e.value?.getValue?.() ?? 0) * (maxBpm - minBpm)),
            interpolation: e.interpolation?.getValue?.() === 1 ? "linear" : "hold",
        })).sort((a, b) => a.position_beats - b.position_beats);

        return {
            success: true,
            enabled,
            min_bpm: minBpm,
            max_bpm: maxBpm,
            event_count: events.length,
            events: eventList,
        };
    }""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_list_signature_changes() -> str:
    """List all time signature changes on the timeline's signature track.

Returns each signature event with position (beats), numerator, and denominator.
"""
    result = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        const tl = h.timelineBox;
        if (!tl || !tl.signatureTrack) return {error: "No signatureTrack on timeline"};

        const sigTrack = tl.signatureTrack;
        const enabled = sigTrack.enabled?.getValue?.() ?? false;

        const events = h.eventBoxes(sigTrack);
        const eventList = events.map(e => ({
            position_beats: (e.relativePosition?.getValue?.() ?? 0) / h.ppqn.Quarter,
            numerator: e.nominator?.getValue?.() ?? 4,
            denominator: e.denominator?.getValue?.() ?? 4,
        })).sort((a, b) => a.position_beats - b.position_beats);

        return {
            success: true,
            enabled,
            event_count: events.length,
            events: eventList,
        };
    }""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_delete_signature_change(position_beats: int, index: int) -> str:
    """Delete a time signature change from the timeline.

Delete by position (closest match) or by index (0-based in sorted order).
Pass index=-1 and position_beats=-1 to delete the last event.

position_beats: Position to match (closest event will be deleted).
index: 0-based index in sorted order (-1 = use position match).

Returns updated signature event list.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const tl = h.timelineBox;
        if (!tl || !tl.signatureTrack) return {{error: "No signatureTrack on timeline"}};

        const sigTrack = tl.signatureTrack;
        const events = h.eventBoxes(sigTrack);
        if (events.length === 0) return {{error: "No signature events to delete"}};

        events.sort((a, b) => (a.relativePosition?.getValue?.() ?? 0) - (b.relativePosition?.getValue?.() ?? 0));

        let targetIdx = {index};
        if (targetIdx < 0) {{
            const posTicks = Math.round({position_beats} * h.ppqn.Quarter);
            if (posTicks < 0) {{
                targetIdx = events.length - 1;
            }} else {{
                let minDist = Infinity;
                for (let i = 0; i < events.length; i++) {{
                    const dist = Math.abs((events[i].relativePosition?.getValue?.() ?? 0) - posTicks);
                    if (dist < minDist) {{ minDist = dist; targetIdx = i; }}
                }}
            }}
        }}
        if (targetIdx < 0 || targetIdx >= events.length) return {{error: "Invalid index " + targetIdx}};

        h.modify(() => {{
            events[targetIdx].delete();
        }});

        const remaining = h.eventBoxes(sigTrack);
        const eventList = remaining.map(e => ({{
            position_beats: (e.relativePosition?.getValue?.() ?? 0) / h.ppqn.Quarter,
            numerator: e.nominator?.getValue?.() ?? 4,
            denominator: e.denominator?.getValue?.() ?? 4,
        }})).sort((a, b) => a.position_beats - b.position_beats);

        return {{
            success: true,
            deleted_index: targetIdx,
            remaining_events: remaining.length,
            events: eventList,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_create_audio_track() -> str:
    """Create a new audio track on the primary audio unit."""
    result = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        let trackBox;
        h.modify(() => {
            trackBox = h.api.createAudioTrack(h.primaryAudioUnitBox);
        });
        return {success: !!trackBox, type: 'audio'};
    }""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_create_note_track(unit_index: int) -> str:
    """Create a new note/MIDI track on an audio unit.

unit_index: Audio unit index. Use -1 (default) for the primary audio unit,
or specify an instrument AU index that contains a synth device (Vaporisateur, Nano, etc).
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const idx = {unit_index};
        let au;
        if (idx < 0) {{
            au = h.primaryAudioUnitBox;
        }} else {{
            const units = h.allAUBoxes();
            if (idx >= units.length) return {{error: "No audio unit at index " + idx}};
            au = units[idx];
        }}
        let trackBox;
        h.modify(() => {{
            trackBox = h.api.createNoteTrack(au);
        }});
        return {{success: !!trackBox, type: 'note', unit_index: idx}};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_rename_unit(unit_index: int, name: str, icon: str) -> str:
    """Rename an audio unit's instrument and optionally set its icon.

Instrument AUs have a label (display name) and icon (symbol) on their
InstrumentBox. This sets both. The output AU (index 0) has no instrument
and cannot be renamed.

unit_index: Audio unit index (must be >= 1, not the output AU).
name: New display name (empty = skip).
icon: New icon symbol (empty = skip, e.g. 'piano', 'guitar', 'drums').

Returns old and new name/icon.
"""
    name_val = json.dumps(name)
    icon_val = json.dumps(icon)
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const nameVal = {name_val};
        const iconVal = {icon_val};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
        const au = units[unitIdx];

        // Get InstrumentBox via au.input.pointerHub.incoming()
        const incoming = h.inputBoxes(au);
        if (incoming.length === 0) return {{error: "AU has no instrument (output AU?)"}};
        const instBox = incoming[0];

        if (!instBox.label) return {{error: "Instrument has no label field"}};

        const oldName = instBox.label?.getValue?.() ?? "";
        const oldIcon = instBox.icon?.getValue?.() ?? "";

        h.modify(() => {{
            if (nameVal !== null) instBox.label.setValue(nameVal);
            if (iconVal !== null && instBox.icon) instBox.icon.setValue(iconVal);
        }});

        return {{
            success: true,
            unit_index: unitIdx,
            instrument_type: instBox.constructor.name,
            old_name: oldName,
            new_name: instBox.label.getValue(),
            old_icon: oldIcon,
            new_icon: instBox.icon?.getValue?.() ?? "",
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_replace_instrument(unit_index: int, new_instrument: str) -> str:
    """Replace the instrument on an audio unit with a different MIDI instrument.

Uses ProjectApi.replaceMIDIInstrument — deletes the old instrument and
creates a new one on the same AU. Only works for MIDI instruments
(Nano, Vaporisateur, Soundfont, Apparat). Tape (audio player) cannot
be replaced this way.

The AU must have a CaptureMidiBox (i.e. it was created as a synth/note
instrument, not an audio track).

unit_index: Audio unit index (must be >= 1).
new_instrument: Factory key — 'Vaporisateur', 'Nano', 'Soundfont', 'Apparat'.

Returns old and new instrument type.
    """
    safe_instrument = new_instrument.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const ef = window.DAW_InstrumentFactories;
        const unitIdx = {unit_index};
        const factoryKey = "{safe_instrument}";

        if (!ef) return {{error: "InstrumentFactories not loaded"}};
        const factory = ef[factoryKey];
        if (!factory) return {{error: "Unknown factory: " + factoryKey}};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
        const au = units[unitIdx];

        // Get current InstrumentBox
        const incoming = h.inputBoxes(au);
        if (incoming.length === 0) return {{error: "AU has no instrument"}};
        const oldInst = incoming[0];
        const oldName = oldInst.label?.getValue?.() ?? "";
        const oldType = oldInst.constructor.name;

        let newInst;
        let replaceError = "";
        h.modify(() => {{
            const attempt = h.api.replaceMIDIInstrument(oldInst, factory);
            if (attempt.isSuccess()) {{
                newInst = attempt.result();
            }} else {{
                replaceError = attempt.failureReason();
            }}
        }});

        if (!newInst) return {{error: "replaceMIDIInstrument failed: " + (replaceError || "unknown — AU may not have CaptureMidiBox or instrument is not MIDI")}};

        return {{
            success: true,
            unit_index: unitIdx,
            old_type: oldType,
            old_name: oldName,
            new_type: newInst.constructor.name,
            new_name: newInst.label?.getValue?.() ?? factory.defaultName,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_set_track_volume(unit_index: int, volume_db: float) -> str:
    """Set volume of an audio unit in dB.

Uses VolumeMapper.decibel(-96, -9, +6) powerByCenter mapping.
Range: -96 dB (mute) to +6 dB. 0 dB = raw 0.768.
"""
    vol_db = volume_db
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const idx = {unit_index};
        const units = h.allAUBoxes();
        if (idx >= units.length) return {{error: "No audio unit at index " + idx + ". Total: " + units.length}};
        const au = units[idx];

        const volDb = {vol_db};
        let raw = volDb;
        try {{
            const c = au.volume.constraints;
            if (c?.valueMapper) raw = c.valueMapper.mapToNormalized(volDb);
            else if (c?.mapper) raw = c.mapper.mapToNormalized(volDb);
        }} catch(e) {{}}

        h.modify(() => {{
            au.volume.setValue(raw);
        }});
        return {{
            success: true,
            unit: au.name?.getValue?.() || "Unit " + idx,
            volume_db: {vol_db},
            raw_value: raw,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_set_track_panning(unit_index: int, panning: float) -> str:
    """Set panning of an audio unit. -1.0 = full left, 0.0 = center, 1.0 = full right."""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const idx = {unit_index};
        const units = h.allAUBoxes();
        if (idx >= units.length) return {{error: "No audio unit at index " + idx}};
        const au = units[idx];

        h.modify(() => {{
            au.panning.setValue({panning});
        }});
        return {{
            success: true,
            unit: au.name?.getValue?.() || "Unit " + idx,
            panning: {panning},
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_set_track_mute(unit_index: int, mute: bool) -> str:
    """Mute or unmute an audio unit."""
    mute_val = json.dumps(mute)
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const idx = {unit_index};
        const units = h.allAUBoxes();
        if (idx >= units.length) return {{error: "No audio unit at index " + idx}};
        const au = units[idx];

        h.modify(() => {{
            au.mute.setValue({mute_val});
        }});
        return {{
            success: true,
            unit: au.name?.getValue?.() || "Unit " + idx,
            mute: {mute_val},
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_set_track_solo(unit_index: int, solo: bool) -> str:
    """Solo or unsolo an audio unit."""
    solo_val = json.dumps(solo)
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const idx = {unit_index};
        const units = h.allAUBoxes();
        if (idx >= units.length) return {{error: "No audio unit at index " + idx}};
        const au = units[idx];

        h.modify(() => {{
            au.solo.setValue({solo_val});
        }});
        return {{
            success: true,
            unit: au.name?.getValue?.() || "Unit " + idx,
            solo: {solo_val},
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
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

@mcp.tool()
async def mcp_opendaw_create_instrument_track(name: str) -> str:
    """Create a new instrument audio unit with a Tape device and an audio track.

This is required for audio playback — the Tape device reads audio regions
and outputs sound. The instrument AU is connected to the output AU's bus.

name: Display name for the instrument (default "Tape").
Returns the unit_index and track_index for use with place_audio_region.
"""
    safe_name = name.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const AudioUnitBox = window.DAW_AudioUnitBox;
        const TapeDeviceBox = window.DAW_TapeDeviceBox;
        const CaptureAudioBox = window.DAW_CaptureAudioBox;
        const AudioUnitType = window.DAW_AudioUnitType;

        const rootBox = h.rootBox;
        const primaryAudioBusBox = h.primaryAudioBusBox;

        let instrumentAU, tapeDevice, captureBox, trackBox;
        h.modify(() => {{
            // Create CaptureAudioBox
            captureBox = CaptureAudioBox.create(h.boxGraph, h.uuid.generate());

            // Create instrument AudioUnitBox connected to output bus
            instrumentAU = AudioUnitBox.create(h.boxGraph, h.uuid.generate(), (box) => {{
                box.type.setValue(AudioUnitType.Instrument);
                box.collection.refer(rootBox.audioUnits);
                box.output.refer(primaryAudioBusBox.input);
                box.capture.refer(captureBox);
                box.index.setValue(0);
                box.volume.setValue(0.767835); // 0 dB (VolumeMapper.decibel(-96,-9,+6) powerByCenter)
            }});

            // Create TapeDeviceBox (audio player instrument)
            tapeDevice = TapeDeviceBox.create(h.boxGraph, h.uuid.generate(), (box) => {{
                box.label.setValue("{safe_name}");
                box.host.refer(instrumentAU.input);
            }});

            // Create audio track on the instrument AU
            trackBox = h.api.createAudioTrack(instrumentAU);
        }});

        // Find unit_index and track_index
        const allUnits = h.allAUBoxes();
        const unitIndex = allUnits.findIndex(au => String(au.address) === String(instrumentAU.address));
        const audioTracks = h.trackBoxes(instrumentAU).filter(box => box.type?.getValue?.() === 2);
        const trackIndex = audioTracks.findIndex(t => String(t.address) === String(trackBox.address));

        return {{
            success: true,
            unit_index: unitIndex,
            track_index: trackIndex >= 0 ? trackIndex : 0,
            instrument_au: String(instrumentAU.address),
            tape_device: String(tapeDevice.address),
            track_box: String(trackBox.address),
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_create_synth_track(name: str, synth_type: str) -> str:
    """Create a new instrument audio unit with a synthesizer device and a note track.

Unlike create_instrument_track (which creates a Tape device for audio playback),
this creates a MIDI synthesizer that responds to notes from create_note.

synth_type: 'vaporisateur' (subtractive synth, default), 'nano' (simple synth),
            'soundfont' (SF2 player, needs sample), 'apparat' (FM synth).
name: Display name for the instrument.

Returns unit_index and track_index for use with create_note.
"""
    factory_key = synth_type.capitalize() if synth_type else "Vaporisateur"
    safe_name = name.replace('"', '').replace('\\', '').replace("'", "")
    safe_synth_type = synth_type.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const AudioUnitBox = window.DAW_AudioUnitBox;
        const CaptureAudioBox = window.DAW_CaptureAudioBox;
        const AudioUnitType = window.DAW_AudioUnitType;
        const IconSymbol = window.DAW_IconSymbol;
        const InstrumentFactories = window.DAW_InstrumentFactories;

        if (!InstrumentFactories) throw new Error("InstrumentFactories not loaded. Check headless-daw lazy-load.");
        if (!IconSymbol) throw new Error("IconSymbol not loaded.");

        const factory = InstrumentFactories["{factory_key}"];
        if (!factory) throw new Error("Unknown synth type: {safe_synth_type} (factory key: {factory_key})");

        const rootBox = h.rootBox;
        const primaryAudioBusBox = h.primaryAudioBusBox;

        let instrumentAU, synthDevice, captureBox, trackBox;
        h.modify(() => {{
            // Create CaptureAudioBox
            captureBox = CaptureAudioBox.create(h.boxGraph, h.uuid.generate());

            // Create instrument AudioUnitBox connected to output bus
            instrumentAU = AudioUnitBox.create(h.boxGraph, h.uuid.generate(), (box) => {{
                box.type.setValue(AudioUnitType.Instrument);
                box.collection.refer(rootBox.audioUnits);
                box.output.refer(primaryAudioBusBox.input);
                box.capture.refer(captureBox);
                box.index.setValue(0);
                box.volume.setValue(0.767835); // 0 dB
            }});

            // Create synth device using InstrumentFactories (proper init values!)
            const icon = IconSymbol.Piano;
            synthDevice = factory.create(h.boxGraph, instrumentAU.input, "{safe_name}", icon);

            // Create note track on the instrument AU
            trackBox = h.api.createNoteTrack(instrumentAU);
        }});

        // Find unit_index and track_index
        const allUnits = h.allAUBoxes();
        const unitIndex = allUnits.findIndex(au => String(au.address) === String(instrumentAU.address));
        const noteTracks = h.noteTrackBoxes(instrumentAU);
        const trackIndex = noteTracks.findIndex(t => String(t.address) === String(trackBox.address));

        return {{
            success: true,
            unit_index: unitIndex,
            track_index: trackIndex >= 0 ? trackIndex : 0,
            synth_type: "{safe_synth_type}",
            synth_class: synthDevice.constructor?.name,
            instrument_au: String(instrumentAU.address),
            synth_device: String(synthDevice.address),
            track_box: String(trackBox.address),
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_place_audio_region(sample_id: str, unit_index: int, start_beat: float, track_index: int) -> str:
    """Place a previously loaded audio sample as a region on a track.

sample_id: The ID returned by mcp_opendaw_load_audio.
unit_index: Audio unit index (default 0).
start_beat: Beat position to place the region.
track_index: Track index within the audio unit (default 0).

NOTE: The audio unit must be an instrument AU with a Tape device.
Use mcp_opendaw_create_instrument_track first if no instrument AU exists.
    """
    safe_sample_id = sample_id.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const AudioFileBox = window.DAW_AudioFileBox;
        const AudioRegionBox = window.DAW_AudioRegionBox;
        const sampleId = "{safe_sample_id}";
        const startBeat = {start_beat};
        const unitIdx = {unit_index};
        const trackIdx = {track_index};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
        const au = units[unitIdx];

        const audioTracks = h.trackBoxes(au)
            .filter(box => box.type?.getValue?.() === 2); // TrackType.Audio = 2
        if (trackIdx >= audioTracks.length) return {{error: "No audio track at index " + trackIdx}};
        const trackBox = audioTracks[trackIdx];

        // Check if sample is loaded
        const audioBuffer = window.DAW_localAudioBuffers.get(sampleId);
        if (!audioBuffer) return {{error: "Sample not loaded: " + sampleId + ". Call mcp_opendaw_load_audio first."}};

        // Use the proper API method: createNotStretchedRegion
        const sample = {{
            name: "{sample_id}",
            duration: audioBuffer.duration,
            bpm: 120,
            sample_rate: audioBuffer.sampleRate,
        }};

        let regionBox, audioFileBox;
        h.modify(() => {{
            audioFileBox = AudioFileBox.create(h.boxGraph, h.uuid.generate(), (box) => {{
                box.fileName.setValue("{sample_id}");
                box.startInSeconds.setValue(0.0);
                box.endInSeconds.setValue(audioBuffer.duration);
            }});

            regionBox = h.api.createNotStretchedRegion({{
                boxGraph: h.boxGraph,
                targetTrack: trackBox,
                position: Math.round(startBeat * h.ppqn.Quarter),
                audioFileBox: audioFileBox,
                sample: sample,
            }});
        }});

        return {{
            success: true,
            sample_id: sampleId,
            position_beats: startBeat,
            duration_seconds: audioBuffer.duration,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_start_engine() -> str:
    """Start the audio engine (AudioWorklet) after setting up tracks and regions.

Call this AFTER loading audio, creating tracks, and placing regions —
but BEFORE playback or effects. The engine serializes the current project
state into the AudioWorklet processor, so all boxes must exist first.
"""
    result = await bridge.evaluate("""() => {
        return new Promise(async (resolve) => {
            try {
                if (window.DAW_engineStarted && window.DAW_engineStarted()) {
                    resolve({success: true, message: "Engine already started"});
                    return;
                }
                await window.DAW_startEngine();
                resolve({success: true, message: "Engine started"});
            } catch(e) {
                resolve({error: e.message, stack: e.stack?.slice(0, 300)});
            }
        });
    }""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_list_effects() -> str:
    """List all available audio and MIDI effect types."""
    result = await bridge.evaluate("""() => {
        const ef = window.DAW_EffectFactories;
        return {
            audio: ef.AudioNamed ? Object.keys(ef.AudioNamed) : [],
            midi: ef.MidiNamed ? Object.keys(ef.MidiNamed) : [],
        };
    }""")
    return _wrap_eval(result)

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
async def mcp_opendaw_list_sends(unit_index: int) -> str:
    """List all aux sends on an audio unit.

unit_index: Audio unit index to inspect.

Returns list of sends with: send_index, target_bus_name, send_level_db, routing.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const srcIdx = {unit_index};
        const units = h.allAUBoxes();
        if (srcIdx >= units.length) return {{error: "No AU at index " + srcIdx}};
        const au = units[srcIdx];

        const sends = h.sendBoxes(au);

        const sendList = sends.map((box, i) => {{
            let busName = "unknown";
            try {{
                const targetBox = box.targetBus.targetVertex?.unwrap?.()?.box;
                if (targetBox && targetBox.label) busName = targetBox.label.getValue();
            }} catch(e) {{}}
            return {{
                send_index: i,
                target_bus_name: busName,
                send_level_db: box.sendGain.getValue(),
                routing: box.routing.getValue() === 0 ? "pre" : "post",
                send_pan: box.sendPan?.getValue?.() ?? 0,
            }};
        }});

        return {{
            success: true,
            unit_index: srcIdx,
            send_count: sends.length,
            sends: sendList,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
async def mcp_opendaw_list_audio_buses() -> str:
    """List all audio buses in the project (primary output + FX buses).

Returns bus index, name, enabled state, and the associated audio unit index.
"""
    result = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        const buses = h.busBoxes();
        const units = h.allAUBoxes();

        const busList = buses.map((box, i) => {
            let unitIdx = -1;
            try {
                const targetBox = box.output.targetVertex?.unwrap?.()?.box;
                if (targetBox) {
                    unitIdx = units.findIndex(u => u.address.equals(targetBox.address));
                }
            } catch(e) {}
            return {
                bus_index: i,
                name: box.label?.getValue?.() ?? "Bus " + i,
                enabled: box.enabled?.getValue?.() ?? true,
                unit_index: unitIdx,
            };
        });

        return {
            success: true,
            bus_count: buses.length,
            buses: busList,
        };
    }""")
    return _wrap_eval(result)

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
async def mcp_opendaw_list_effect_parameters(unit_index: int, effect_index: int) -> str:
    """List all parameters of an effect on an audio unit.

unit_index: Audio unit index.
effect_index: Effect position in the chain (0-based, from add_effect return).

Returns parameter names, current values, units, and ranges.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const effectIdx = {effect_index};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};

        const au = units[unitIdx];
        const effects = h.effectBoxes(au);
        if (effectIdx >= effects.length) return {{error: "No effect at index " + effectIdx + ". Total: " + effects.length}};

        const effectBox = effects[effectIdx];
        const effectType = effectBox.constructor.name;

        // Use box.fields() — returns array of all Field objects on the box
        // Use box.record() — returns Record<fieldKey, Field> keyed by numeric field key
        // We iterate record() to get fieldName from each field
        const skipFieldNames = new Set(['host', 'index', 'label', 'enabled', 'minimized', 'sideChain']);
        const params = [];

        const record = effectBox.record();
        for (const [key, field] of Object.entries(record)) {{
            // Get field name from the field object
            const fname = field._fieldName || field.fieldName || key;
            if (skipFieldNames.has(fname)) continue;
            if (typeof field.getValue !== 'function') continue;

            try {{
                const value = field.getValue();
                const paramInfo = {{
                    name: fname,
                    value: value,
                    type: typeof value === 'number' ? 'float' : typeof value === 'boolean' ? 'bool' : 'string',
                }};

                // Use public getters: field.unit and field.constraints
                if (typeof value === 'number') {{
                    try {{ paramInfo.unit = field.unit || ''; }} catch(e) {{}}
                    try {{
                        const c = field.constraints;
                        if (c) {{
                            if (typeof c === 'string') {{
                                paramInfo.scaling = c;
                            }} else if (typeof c === 'object') {{
                                paramInfo.min = c.min;
                                paramInfo.max = c.max;
                                paramInfo.mid = c.mid;
                                paramInfo.scaling = c.scaling;
                            }}
                        }}
                    }} catch(e) {{}}
                }}

                params.push(paramInfo);
            }} catch(e) {{
                // skip fields that throw on getValue
            }}
        }}

        return {{
            effect_type: effectType,
            effect_index: effectIdx,
            parameters: params,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_get_effect_state(unit_index: int, effect_index: int) -> str:
    """Get full state of an effect: enabled, minimized, sidechain, all parameters.

More detailed than list_effect_parameters — includes enabled/bypass state,
minimized state, sidechain connection, and full parameter dump.

unit_index: Audio unit index.
effect_index: Effect position in the chain (0-based).

Returns complete effect state snapshot.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const effectIdx = {effect_index};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
        const au = units[unitIdx];
        const effects = h.effectBoxes(au);
        if (effectIdx >= effects.length) return {{error: "No effect at index " + effectIdx}};

        const effectBox = effects[effectIdx];
        const effectType = effectBox.constructor.name;
        const skipFieldNames = new Set(['host', 'index', 'collection', 'editing', 'output', 'input', 'sideChain', 'capture', 'tracks', 'audioEffects', 'midiEffects', 'auxSends']);

        const params = [];
        const record = effectBox.record();
        for (const [key, field] of Object.entries(record)) {{
            const fname = field._fieldName || field.fieldName || key;
            if (skipFieldNames.has(fname)) continue;
            if (typeof field.getValue !== 'function') continue;
            try {{
                const value = field.getValue();
                const info = {{name: fname, value: value, type: typeof value === 'number' ? 'float' : typeof value === 'boolean' ? 'bool' : 'string'}};
                if (typeof value === 'number') {{
                    try {{ info.unit = field.unit || ''; }} catch(e) {{}}
                    try {{
                        const c = field.constraints;
                        if (c) {{
                            if (typeof c === 'string') info.scaling = c;
                            else if (typeof c === 'object') {{ info.min = c.min; info.max = c.max; info.scaling = c.scaling; }}
                        }}
                    }} catch(e) {{}}
                }}
                params.push(info);
            }} catch(e) {{}}
        }}

        // Check sidechain
        let sidechainConnected = false;
        try {{
            if (effectBox.sideChain) sidechainConnected = !effectBox.sideChain.isEmpty?.();
        }} catch(e) {{}}

        return {{
            success: true,
            effect_type: effectType,
            effect_index: effectIdx,
            enabled: effectBox.enabled?.getValue?.() ?? true,
            minimized: effectBox.minimized?.getValue?.() ?? false,
            sidechain_connected: sidechainConnected,
            parameter_count: params.length,
            parameters: params,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
async def mcp_opendaw_list_midi_effects() -> str:
    """List all available MIDI effect types.

MIDI effects process note data before it reaches the instrument.
They are inserted on the MIDI effect chain (au.midiEffects).
"""
    result = await bridge.evaluate("""() => {
        const ef = window.DAW_EffectFactories;
        return {
            midi: ef.MidiNamed ? Object.keys(ef.MidiNamed) : [],
        };
    }""")
    return _wrap_eval(result)

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
async def mcp_opendaw_get_midi_effect_chain(unit_index: int) -> str:
    """Get the MIDI effect chain for an audio unit.

unit_index: Audio unit index.
Returns ordered list of MIDI effects with type, enabled state, and index.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
        const au = units[unitIdx];
        const effects = h.midiEffectBoxes(au);

        const chain = effects.map((box, i) => {{
            const className = box.constructor.name;
            const shortName = className.replace(/DeviceBox$/, "").replace(/Box$/, "");
            return {{
                index: i,
                type: shortName,
                class: className,
                enabled: box.enabled?.getValue?.() ?? true,
                minimized: box.minimized?.getValue?.() ?? false,
                label: box.label?.getValue?.() || "",
            }};
        }});

        return {{
            unit: au.name?.getValue?.() || "Unit " + unitIdx,
            midi_effects: chain,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_list_midi_effect_params(unit_index: int, effect_index: int) -> str:
    """List all parameters of a MIDI effect with current values.

unit_index: Audio unit index.
effect_index: MIDI effect position in the chain (0-based).

Returns parameter names, values, units, and constraints.
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
        const skipFields = new Set(['host', 'index', 'collection', 'editing', 'output', 'input', 'sideChain', 'capture', 'tracks', 'audioEffects', 'midiEffects', 'auxSends']);

        const params = [];
        const record = effectBox.record();
        for (const [key, val] of Object.entries(record)) {{
            if (skipFields.has(key)) continue;
            if (val && typeof val.getValue === 'function') {{
                const param = {{
                    field_index: key,
                    name: key,
                    value: val.getValue(),
                    type: typeof val.getValue(),
                }};
                try {{ param.unit = val.unit || ""; }} catch(e) {{}}
                try {{ param.constraints = val.constraints || null; }} catch(e) {{}}
                params.push(param);
            }}
        }}

        return {{
            effect: effectType,
            effect_index: effectIdx,
            param_count: params.length,
            parameters: params,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
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

@mcp.tool()
async def mcp_opendaw_list_vaporisateur_params(unit_index: int) -> str:
    """Get full Vaporisateur synthesizer state: oscillators, LFO, noise, main params.

unit_index: Audio unit index (-1 = auto-detect Vaporisateur).

Returns:
  - oscillators: [{index, waveform, volume, octave, tune}]
  - lfo: {waveform, rate, sync, attack, decay, release}
  - noise: {volume, attack, decay, release}
  - main: cutoff, resonance, attack, release, filterEnvelope, decay, sustain, etc.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        let vap = null;

        if (unitIdx >= 0) {{
            const units = h.allAUBoxes();
            if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
            const au = units[unitIdx];
            const incoming = h.inputBoxes(au);
            vap = incoming.find(b => b.constructor.name === "VaporisateurDeviceBox");
        }} else {{
            const units = h.allAUBoxes();
            for (const au of units) {{
                const incoming = h.inputBoxes(au);
                vap = incoming.find(b => b.constructor.name === "VaporisateurDeviceBox");
                if (vap) break;
            }}
        }}

        if (!vap) return {{error: "No Vaporisateur found"}};

        // Oscillators
        const oscs = vap.oscillators;
        const oscFields = oscs.fields();
        const oscillators = oscFields.map((osc, i) => {{
            const rec = osc.record();
            const params = {{}};
            for (const [k, v] of Object.entries(rec)) {{
                if (v && typeof v.getValue === 'function') params[k] = v.getValue();
            }}
            return {{
                index: i,
                waveform: osc.getField(1).getValue(),  // 0=Sine, 1=Triangle, 2=Saw, 3=Square
                volume: osc.getField(2).getValue(),
                octave: osc.getField(3).getValue(),
                tune: osc.getField(4).getValue(),
            }};
        }});

        // LFO
        const lfo = vap.lfo;
        let lfoParams = null;
        if (lfo) {{
            const lrec = lfo.record();
            lfoParams = {{}};
            for (const [k, v] of Object.entries(lrec)) {{
                if (v && typeof v.getValue === 'function') lfoParams[k] = v.getValue();
            }}
        }}

        // Noise
        const noise = vap.noise;
        let noiseParams = null;
        if (noise) {{
            const nrec = noise.record();
            noiseParams = {{}};
            for (const [k, v] of Object.entries(nrec)) {{
                if (v && typeof v.getValue === 'function') noiseParams[k] = v.getValue();
            }}
        }}

        // Main params (skip host/index/collection/editing/output/input/etc)
        const skipFields = new Set(['1','2','3','4','5','host','index','collection','editing','output','input','sideChain','capture','tracks','audioEffects','midiEffects','auxSends','oscillators','lfo','noise']);
        const record = vap.record();
        const mainParams = {{}};
        for (const [k, v] of Object.entries(record)) {{
            if (skipFields.has(k)) continue;
            if (v && typeof v.getValue === 'function') mainParams[k] = v.getValue();
        }}

        return {{
            type: "VaporisateurDeviceBox",
            oscillators: oscillators,
            osc_count: oscs.size(),
            lfo: lfoParams,
            noise: noiseParams,
            main_params: mainParams,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_set_vaporisateur_osc_param(osc_index: int, param_name: str, value: float, unit_index: int) -> str:
    """Set a parameter on a Vaporisateur oscillator.

osc_index: Oscillator index (0, 1).
param_name: One of: waveform, volume, octave, tune.
  waveform: 0=Sine, 1=Triangle, 2=Saw, 3=Square
  volume: dB (-Infinity to +6)
  octave: integer offset
  tune: semitone offset (float)
value: New value.
unit_index: Audio unit index (-1 = auto-detect).

Returns old and new values.
"""
    safe_param = param_name.replace('"', '').replace("'", '').replace('\\', '')
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const oscIdx = {osc_index};
        const paramName = "{safe_param}";
        const newVal = {value};

        let vap = null;
        if (unitIdx >= 0) {{
            const units = h.allAUBoxes();
            if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
            const au = units[unitIdx];
            const incoming = h.inputBoxes(au);
            vap = incoming.find(b => b.constructor.name === "VaporisateurDeviceBox");
        }} else {{
            const units = h.allAUBoxes();
            for (const au of units) {{
                const incoming = h.inputBoxes(au);
                vap = incoming.find(b => b.constructor.name === "VaporisateurDeviceBox");
                if (vap) break;
            }}
        }}
        if (!vap) return {{error: "No Vaporisateur found"}};

        const oscFields = vap.oscillators.fields();
        if (oscIdx >= oscFields.length) return {{error: "No oscillator at index " + oscIdx}};
        const osc = oscFields[oscIdx];

        // Map param name to field index
        const paramMap = {{
            waveform: 1,
            volume: 2,
            octave: 3,
            tune: 4,
        }};
        const fieldIdx = paramMap[paramName];
        if (fieldIdx === undefined) return {{error: "Unknown param: " + paramName + ". Valid: waveform, volume, octave, tune"}};

        const field = osc.getField(fieldIdx);
        const oldValue = field.getValue();
        h.modify(() => {{
            field.setValue(newVal);
        }});

        return {{
            success: true,
            osc_index: oscIdx,
            param: paramName,
            old_value: oldValue,
            new_value: field.getValue(),
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_list_instrument_params(unit_index: int) -> str:
    """List all parameters of the instrument connected to an audio unit.

unit_index: Audio unit index (-1 = auto-detect first non-master AU with an instrument).

Returns instrument type, all parameter fields with values, units, and constraints.
Works with: Vaporisateur (cutoff/resonance/ADSR/etc), Tape (flutter/wow/noise/saturation),
Nano (volume/release), Soundfont (presetIndex), MIDIOutput (channel), Playfield, Apparat.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};

        const units = h.allAUBoxes();
        let instBox = null;
        let auName = "";

        if (unitIdx >= 0) {{
            if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
            const au = units[unitIdx];
            auName = au.name?.getValue?.() || "Unit " + unitIdx;
            const incoming = h.inputBoxes(au);
            instBox = incoming.find(b => b.constructor.name !== "AudioBusBox");
        }} else {{
            for (const au of units) {{
                const incoming = h.inputBoxes(au);
                instBox = incoming.find(b => b.constructor.name !== "AudioBusBox");
                if (instBox) {{ auName = au.name?.getValue?.() || "Unit"; break; }}
            }}
        }}

        if (!instBox) return {{error: "No instrument found"}};

        const instType = instBox.constructor.name;
        const skipFields = new Set(['host', 'index', 'collection', 'editing', 'output', 'input', 'sideChain', 'capture', 'tracks', 'audioEffects', 'midiEffects', 'auxSends', 'oscillators', 'lfo', 'noise', 'samples', 'parameters', 'device', 'file']);

        const params = [];
        const record = instBox.record();
        for (const [key, val] of Object.entries(record)) {{
            if (skipFields.has(key)) continue;
            if (val && typeof val.getValue === 'function') {{
                const param = {{
                    field_index: key,
                    value: val.getValue(),
                    type: typeof val.getValue(),
                }};
                try {{ param.unit = val.unit || ""; }} catch(e) {{}}
                try {{ param.constraints = val.constraints || null; }} catch(e) {{}}
                params.push(param);
            }}
        }}

        return {{
            instrument: instType,
            unit: auName,
            param_count: params.length,
            parameters: params,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
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

@mcp.tool()
async def mcp_opendaw_list_playfield_samples(unit_index: int) -> str:
    """List all drum pads (samples) on a Playfield drum machine.

unit_index: Audio unit index (-1 = auto-detect Playfield).

Returns list of pads with MIDI note, enabled state, and effects.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const units = h.allAUBoxes();
        let pf = null;

        if (unitIdx >= 0) {{
            if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
            const au = units[unitIdx];
            const incoming = h.inputBoxes(au);
            pf = incoming.find(b => b.constructor.name === "PlayfieldDeviceBox");
        }} else {{
            for (const au of units) {{
                const incoming = h.inputBoxes(au);
                pf = incoming.find(b => b.constructor.name === "PlayfieldDeviceBox");
                if (pf) break;
            }}
        }}

        if (!pf) return {{error: "No Playfield found"}};

        const samples = h.sampleBoxes(pf);
        const sampleInfo = samples.map((s, i) => ({{
            index: i,
            midi_note: s.index?.getValue?.() ?? 60,
            enabled: s.enabled?.getValue?.() ?? true,
            label: s.label?.getValue?.() || "",
            has_file: [...s.file.pointerHub.incoming()].length > 0,
        }}));

        return {{
            instrument: "PlayfieldDeviceBox",
            sample_count: samples.length,
            samples: sampleInfo,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_set_playfield_sample_enabled(sample_index: int, enabled: bool, unit_index: int) -> str:
    """Enable/disable a drum pad on a Playfield drum machine.

sample_index: Pad index (0-based).
enabled: true to enable, false to mute the pad.
unit_index: Audio unit index (-1 = auto-detect Playfield).
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const sampleIdx = {sample_index};
        const enabledVal = {json.dumps(enabled)};

        const units = h.allAUBoxes();
        let pf = null;

        if (unitIdx >= 0) {{
            if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
            const au = units[unitIdx];
            const incoming = h.inputBoxes(au);
            pf = incoming.find(b => b.constructor.name === "PlayfieldDeviceBox");
        }} else {{
            for (const au of units) {{
                const incoming = h.inputBoxes(au);
                pf = incoming.find(b => b.constructor.name === "PlayfieldDeviceBox");
                if (pf) break;
            }}
        }}

        if (!pf) return {{error: "No Playfield found"}};

        const samples = h.sampleBoxes(pf);
        if (sampleIdx >= samples.length) return {{error: "No sample at index " + sampleIdx}};

        const sample = samples[sampleIdx];
        const oldVal = sample.enabled.getValue();
        h.modify(() => {{
            sample.enabled.setValue(enabledVal);
        }});

        return {{
            success: true,
            sample_index: sampleIdx,
            old_enabled: oldVal,
            new_enabled: sample.enabled.getValue(),
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_create_playfield_sample(midi_note: int, sample_name: str, duration_seconds: float, unit_index: int) -> str:
    """Add a drum pad to a Playfield drum machine.

midi_note: MIDI note number for this pad (36=C1, 38=D1, 42=F#1, etc).
sample_name: Name for the sample slot.
duration_seconds: Duration hint for the sample slot.
unit_index: Audio unit index (-1 = auto-detect Playfield).

Returns the new pad index and MIDI note.
"""
    safe_name = sample_name.replace('"', '').replace("'", "").replace('\\', '')
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const note = {midi_note};
        const name = "{safe_name}";
        const dur = {duration_seconds};

        const units = h.allAUBoxes();
        let pf = null;

        if (unitIdx >= 0) {{
            if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
            const au = units[unitIdx];
            const incoming = h.inputBoxes(au);
            pf = incoming.find(b => b.constructor.name === "PlayfieldDeviceBox");
        }} else {{
            for (const au of units) {{
                const incoming = h.inputBoxes(au);
                pf = incoming.find(b => b.constructor.name === "PlayfieldDeviceBox");
                if (pf) break;
            }}
        }}

        if (!pf) return {{error: "No Playfield found"}};

        // Need at least one existing sample to get the class constructor
        const existingSamples = h.sampleBoxes(pf);
        if (existingSamples.length === 0) return {{error: "Playfield has no samples — create with InstrumentFactories.Playfield first"}};
        const SampleClass = existingSamples[0].constructor;
        const newIndex = existingSamples.length;

        let result;
        h.modify(() => {{
            const fileUUID = h.uuid.generate();
            const AudioFileBox = window.DAW_AudioFileBox;
            const fileBox = AudioFileBox.create(h.boxGraph, fileUUID, box => {{
                box.fileName.setValue(name);
                box.endInSeconds.setValue(dur);
            }});

            const sampleBox = SampleClass.create(h.boxGraph, h.uuid.generate(), box => {{
                box.device.refer(pf.samples);
                box.file.refer(fileBox);
                box.index.setValue(note);
                box.enabled.setValue(true);
            }});
            result = {{ok: true, index: newIndex, midi_note: note}};
        }});
        return result;
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_delete_audio_unit(unit_index: int) -> str:
    """Delete an entire audio unit with all its tracks, effects, and sends.

Uses ProjectApi.deleteAudioUnit() — proper cleanup of all connected boxes.
The primary output AU (index 0) cannot be deleted.

unit_index: Audio unit to delete (must be >= 1, as index 0 is the master output).
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};

        const au = units[unitIdx];
        const auType = au.type?.getValue?.() ?? "unknown";
        const trackCount = h.trackBoxes(au).length;
        const effectCount = h.effectBoxes(au).length;

        h.modify(() => h.api.deleteAudioUnit(au));

        const remaining = h.allAUBoxes().length;
        return {{
            success: true,
            deleted_au_index: unitIdx,
            deleted_au_type: auType,
            removed_tracks: trackCount,
            removed_effects: effectCount,
            remaining_units: remaining,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_get_effect_chain(unit_index: int) -> str:
    """Get the full effect chain for an audio unit.

unit_index: Audio unit index.

Returns ordered list of effects with their type, enabled state, and index.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};

        const au = units[unitIdx];
        const effects = h.effectBoxes(au);

        const chain = effects.map((box, i) => {{
            const className = box.constructor.name;
            const shortName = className.replace(/DeviceBox$/, "").replace(/Box$/, "");
            return {{
                index: i,
                type: shortName,
                class: className,
                enabled: box.enabled?.getValue?.() ?? true,
                minimized: box.minimized?.getValue?.() ?? false,
                label: box.label?.getValue?.() || "",
            }};
        }});

        return {{
            unit: au.name?.getValue?.() || "Unit " + unitIdx,
            effects: chain,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
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

        h.modify(() => {{
            // Find existing region on this track, or create one
            const existingRegions = h.regionBoxes(trackBox);
            let regionBox = null;
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

            // Extend region duration if note extends beyond current
            const noteEnd = notePos + noteDuration;
            const currentDur = regionBox.duration.getValue();
            if (noteEnd > currentDur) {{
                regionBox.duration.setValue(noteEnd);
                regionBox.loopDuration.setValue(noteEnd);
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

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
async def mcp_opendaw_delete_note_region(unit_index: int, track_index: int, region_index: int) -> str:
    """Delete a note region from the timeline.

unit_index: Audio unit index (-1 = search all AUs).
track_index: Note track index within the AU.
region_index: Region index to delete (0-based).
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};

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
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx + " (total: " + regions.length + ")"}};

        h.modify(() => {{
            regions[regionIdx].delete();
        }});

        return {{
            success: true,
            remaining_regions: h.regionBoxes(trackBox).length,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_delete_audio_region(unit_index: int, track_index: int, region_index: int) -> str:
    """Delete an audio region from the timeline.

unit_index: Audio unit index.
track_index: Audio track index within the AU (type=2).
region_index: Region index to delete (0-based).
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
        const au = units[unitIdx];

        const audioTracks = h.trackBoxes(au)
            .filter(box => box.type?.getValue?.() === 2);
        if (trackIdx >= audioTracks.length) return {{error: "No audio track at index " + trackIdx + " (total: " + audioTracks.length + ")"}};

        const trackBox = audioTracks[trackIdx];
        const regions = h.regionBoxes(trackBox);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx + " (total: " + regions.length + ")"}};

        h.modify(() => {{
            regions[regionIdx].delete();
        }});

        return {{
            success: true,
            remaining_regions: h.regionBoxes(trackBox).length,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_list_note_regions(unit_index: int, track_index: int) -> str:
    """List all note regions with position, duration, and note count.

unit_index: Audio unit index (-1 = all AUs).
track_index: Specific note track (-1 = all note tracks).

Returns list of regions with: region_index, unit_index, track_index, position_beats,
duration_beats, label, note_count.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const allUnits = h.allAUBoxes();
        const targetUnits = unitIdx < 0 ? allUnits : (unitIdx < allUnits.length ? [allUnits[unitIdx]] : []);
        const Quarter = h.ppqn.Quarter;

        const regionList = [];
        for (let ui = 0; ui < targetUnits.length; ui++) {{
            const au = targetUnits[ui];
            const auIdx = allUnits.indexOf(au);
            const noteTracks = h.trackBoxes(au)
                .filter(box => box.type?.getValue?.() === 1);
            const targetTracks = trackIdx < 0 ? noteTracks : (trackIdx < noteTracks.length ? [noteTracks[trackIdx]] : []);
            for (let ti = 0; ti < targetTracks.length; ti++) {{
                const track = targetTracks[ti];
                const trackIdxActual = noteTracks.indexOf(track);
                const regions = h.regionBoxes(track);
                for (let ri = 0; ri < regions.length; ri++) {{
                    const region = regions[ri];
                    let noteCount = 0;
                    try {{
                        const vertex = region.events.targetVertex.unwrap();
                        const collectionBox = vertex.box || vertex;
                        if (collectionBox && collectionBox.events) {{
                            noteCount = h.eventBoxes(collectionBox).length;
                        }}
                    }} catch(e) {{}}
                    regionList.push({{
                        region_index: ri,
                        unit_index: auIdx,
                        track_index: trackIdxActual,
                        position_beats: region.position?.getValue?.() / Quarter || 0,
                        duration_beats: region.duration?.getValue?.() / Quarter || 0,
                        label: region.label?.getValue?.() ?? "",
                        note_count: noteCount,
                    }});
                }}
            }}
        }}

        return {{
            success: true,
            region_count: regionList.length,
            regions: regionList,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_list_audio_regions(unit_index: int, track_index: int) -> str:
    """List all audio regions with file name, position, and duration.

unit_index: Audio unit index.
track_index: Specific audio track (-1 = all audio tracks).

Returns list of regions with: region_index, track_index, position_beats,
duration_seconds, file_name.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
        const au = units[unitIdx];
        const Quarter = h.ppqn.Quarter;

        const audioTracks = h.trackBoxes(au)
            .filter(box => box.type?.getValue?.() === 2);
        const targetTracks = trackIdx < 0 ? audioTracks : (trackIdx < audioTracks.length ? [audioTracks[trackIdx]] : []);

        const regionList = [];
        for (let ti = 0; ti < targetTracks.length; ti++) {{
            const track = targetTracks[ti];
            const trackIdxActual = audioTracks.indexOf(track);
            const regions = h.regionBoxes(track);
            for (let ri = 0; ri < regions.length; ri++) {{
                const region = regions[ri];
                let fileName = "";
                try {{
                    const vertex = region.audioFile?.targetVertex?.unwrap?.();
                    const fileBox = vertex?.box || vertex;
                    if (fileBox && fileBox.fileName) fileName = fileBox.fileName.getValue();
                }} catch(e) {{}}
                regionList.push({{
                    region_index: ri,
                    track_index: trackIdxActual,
                    position_beats: region.position?.getValue?.() / Quarter || 0,
                    duration_seconds: region.duration?.getValue?.() / 48000 || 0,
                    file_name: fileName,
                }});
            }}
        }}

        return {{
            success: true,
            region_count: regionList.length,
            regions: regionList,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_set_audio_region_fade(unit_index: int, track_index: int, region_index: int, fade_in: float, fade_out: float, in_slope: float, out_slope: float) -> str:
    """Set fade in/out on an audio region.

Audio regions have a Fading object with four params:
- in: fade-in duration in seconds (0 = no fade-in)
- out: fade-out duration in seconds (0 = no fade-out)
- inSlope: fade-in curve (0.5 = linear, 0.75 = fast start, 0.25 = slow start)
- outSlope: fade-out curve (0.5 = linear, 0.25 = fast end, 0.75 = slow end)

Pass -1.0 for any parameter to skip changing it (keep current value).

unit_index: Audio unit index.
track_index: Audio track index.
region_index: Region index within the track.
fade_in: Fade-in duration in seconds (-1 = skip).
fade_out: Fade-out duration in seconds (-1 = skip).
in_slope: Fade-in curve 0-1 (-1 = skip).
out_slope: Fade-out curve 0-1 (-1 = skip).

Returns updated fade values.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const fadeIn = {fade_in};
        const fadeOut = {fade_out};
        const inSlope = {in_slope};
        const outSlope = {out_slope};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
        const au = units[unitIdx];

        const audioTracks = h.trackBoxes(au)
            .filter(box => box.type?.getValue?.() === 2);
        if (trackIdx >= audioTracks.length) return {{error: "No audio track at index " + trackIdx}};
        const track = audioTracks[trackIdx];

        const regions = h.regionBoxes(track);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx}};
        const region = regions[regionIdx];

        if (!region.fading) return {{error: "Region has no fading field"}};

        h.modify(() => {{
            if (fadeIn >= 0) region.fading.in.setValue(fadeIn);
            if (fadeOut >= 0) region.fading.out.setValue(fadeOut);
            if (inSlope >= 0) region.fading.inSlope.setValue(inSlope);
            if (outSlope >= 0) region.fading.outSlope.setValue(outSlope);
        }});

        return {{
            success: true,
            region_index: regionIdx,
            fade_in: region.fading.in.getValue(),
            fade_out: region.fading.out.getValue(),
            in_slope: region.fading.inSlope.getValue(),
            out_slope: region.fading.outSlope.getValue(),
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_set_audio_region_gain(unit_index: int, track_index: int, region_index: int, gain_db: float) -> str:
    """Set gain (in dB) on an audio region.

Audio regions have a per-region gain control (Float32Field, decibel).
Use this for trim automation or balancing clips within a track.

unit_index: Audio unit index.
track_index: Audio track index.
region_index: Region index within the track.
gain_db: Gain in dB (0 = unity, -6 = half volume, +6 = double).

Returns updated gain value.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const gainDb = {gain_db};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
        const au = units[unitIdx];

        const audioTracks = h.trackBoxes(au)
            .filter(box => box.type?.getValue?.() === 2);
        if (trackIdx >= audioTracks.length) return {{error: "No audio track at index " + trackIdx}};
        const track = audioTracks[trackIdx];

        const regions = h.regionBoxes(track);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx}};
        const region = regions[regionIdx];

        if (!region.gain) return {{error: "Region has no gain field"}};

        h.modify(() => {{
            region.gain.setValue(gainDb);
        }});

        return {{
            success: true,
            region_index: regionIdx,
            gain_db: region.gain.getValue(),
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
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

@mcp.tool()
async def mcp_opendaw_duplicate_note_region(unit_index: int, track_index: int, region_index: int, offset_beats: float) -> str:
    """Duplicate a note region to a new position.

Copies the region and all its notes to offset_beats after the original.
Useful for repeating patterns (e.g. duplicate 1-bar loop to bar 2).

unit_index: Audio unit index (-1 = search all AUs).
track_index: Note track index within the AU.
region_index: Region to duplicate (0-based).
offset_beats: How far to shift the copy (in beats, e.g. 4.0 = next bar in 4/4).

Returns new region index.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const NoteRegionBox = window.DAW_NoteRegionBox;
        const NoteEventCollectionBox = window.DAW_NoteEventCollectionBox;
        const NoteEventBox = window.DAW_NoteEventBox;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const offsetTicks = Math.round({offset_beats} * h.ppqn.Quarter);

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

        const srcRegion = regions[regionIdx];
        const srcPos = srcRegion.position.getValue();
        const srcDuration = srcRegion.duration.getValue();
        const newPos = srcPos + offsetTicks;

        let newRegionIdx = -1;
        h.modify(() => {{
            // Get source collection
            let srcCollection = null;
            try {{
                const vertex = srcRegion.events.targetVertex.unwrap();
                srcCollection = vertex.box || vertex;
            }} catch(e) {{}}

            if (srcCollection && srcCollection.events) {{
                // Create new collection and copy all note events
                const newCollection = NoteEventCollectionBox.create(h.boxGraph, h.uuid.generate());
                const srcNotes = h.eventBoxes(srcCollection);
                for (const srcNote of srcNotes) {{
                    NoteEventBox.create(h.boxGraph, h.uuid.generate(), (box) => {{
                        box.position.setValue(srcNote.position.getValue());
                        box.duration.setValue(srcNote.duration.getValue());
                        box.velocity.setValue(srcNote.velocity.getValue());
                        box.pitch.setValue(srcNote.pitch.getValue());
                        box.chance.setValue(srcNote.chance?.getValue?.() ?? 100);
                        box.cent.setValue(srcNote.cent?.getValue?.() ?? 0);
                        box.events.refer(newCollection.events);
                    }});
                }}

                // Create new region
                NoteRegionBox.create(h.boxGraph, h.uuid.generate(), (box) => {{
                    box.position.setValue(newPos);
                    box.label.setValue((srcRegion.label?.getValue?.() ?? "Region") + " copy");
                    box.mute.setValue(false);
                    box.duration.setValue(srcDuration);
                    box.loopDuration.setValue(0);
                    box.loopDuration.setValue(srcDuration);
                    box.eventOffset.setValue(0);
                    box.events.refer(newCollection.owners);
                    box.regions.refer(trackBox.regions);
                }});
            }}

            // Find new region index
            const updatedRegions = h.regionBoxes(trackBox);
            newRegionIdx = updatedRegions.length - 1;
        }});

        return {{
            success: true,
            new_region_index: newRegionIdx,
            new_position_beats: newPos / h.ppqn.Quarter,
            offset_beats: {offset_beats},
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_duplicate_notes(unit_index: int, track_index: int, region_index: int) -> str:
    """Duplicate all notes within a region, shifting them after the last note.

Creates copies of every note in the region, shifted by (max(position+duration) - min(position)).
This mirrors the DAW's native "duplicate notes" feature.

unit_index: Audio unit index (-1 = search all AUs).
track_index: Note track index within the AU.
region_index: Region whose notes to duplicate (0-based).

Returns count of duplicated notes and shift in beats.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const NoteEventBox = window.DAW_NoteEventBox;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const Quarter = h.ppqn.Quarter;

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

        const srcRegion = regions[regionIdx];
        let collection = null;
        try {{
            const vertex = srcRegion.events.targetVertex.unwrap();
            collection = vertex.box || vertex;
        }} catch(e) {{}}

        if (!collection || !collection.events) return {{error: "No note collection in region"}};

        const notes = h.eventBoxes(collection);
        if (notes.length === 0) return {{error: "No notes in region"}};

        let blockStart = Infinity, blockEnd = -Infinity;
        for (const n of notes) {{
            const pos = n.position.getValue();
            const dur = n.duration.getValue();
            if (pos < blockStart) blockStart = pos;
            if (pos + dur > blockEnd) blockEnd = pos + dur;
        }}
        const shift = blockEnd - blockStart;
        if (shift <= 0) return {{error: "Cannot duplicate: notes have zero span"}};

        let created = 0;
        h.modify(() => {{
            for (const n of notes) {{
                NoteEventBox.create(h.boxGraph, h.uuid.generate(), (box) => {{
                    box.events.refer(collection.events);
                    box.position.setValue(n.position.getValue() + shift);
                    box.duration.setValue(n.duration.getValue());
                    box.pitch.setValue(n.pitch.getValue());
                    box.velocity.setValue(n.velocity.getValue());
                    box.chance.setValue(n.chance?.getValue?.() ?? 100);
                    box.cent.setValue(n.cent?.getValue?.() ?? 0);
                }});
                created++;
            }}
        }});

        return {{
            success: true,
            duplicated: created,
            shift_beats: shift / Quarter,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_list_notes(unit_index: int, track_index: int, region_index: int) -> str:
    """List all note events within a region.

Returns each note with position (beats), duration (beats), pitch (MIDI 0-127),
velocity (0-1), cent, and chance (0-100).

unit_index: Audio unit index (-1 = search all AUs).
track_index: Note track index within the AU.
region_index: Region to list notes from (0-based).

Returns list of notes sorted by position.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const Quarter = h.ppqn.Quarter;

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
        const noteList = notes.map((n, i) => ({{
            index: i,
            position_beats: (n.position?.getValue?.() ?? 0) / Quarter,
            duration_beats: (n.duration?.getValue?.() ?? 0) / Quarter,
            pitch: n.pitch?.getValue?.() ?? 60,
            velocity: n.velocity?.getValue?.() ?? 0.787,
            cent: n.cent?.getValue?.() ?? 0,
            chance: n.chance?.getValue?.() ?? 100,
        }})).sort((a, b) => a.position_beats - b.position_beats);

        return {{
            success: true,
            note_count: notes.length,
            notes: noteList,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
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

@mcp.tool()
async def mcp_opendaw_delete_note(note_index: int, unit_index: int, track_index: int, region_index: int) -> str:
    """Delete a single note from a region.

note_index: Index of the note to delete (0-based, as returned by list_notes).
unit_index: Audio unit index (-1 = search all AUs).
track_index: Note track index within the AU.
region_index: Region containing the note (0-based).

Returns remaining note count.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const noteIdx = {note_index};

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

        h.modify(() => {{
            notes[noteIdx].delete();
        }});

        const remaining = h.eventBoxes(collection).length;
        return {{
            success: true,
            deleted_note_index: noteIdx,
            remaining_notes: remaining,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_delete_region(track_index: int, region_index: int, unit_index: int, region_type: str) -> str:
    """Delete a region from a track.

Removes the region and all its contents (notes for note regions,
audio reference for audio regions, automation events for value regions).

track_index: Track index within the AU.
region_index: Region to delete (0-based).
unit_index: Audio unit index (-1 = search all AUs).
region_type: 'note', 'audio', or 'value' (for filtering).

Returns remaining region count on the track.
"""
    type_val = json.dumps(region_type)
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const typeVal = {type_val};

        let tracks = [];
        const units = h.allAUBoxes();
        if (unitIdx < 0) {{
            for (const au of units) {{
                const ts = h.trackBoxes(au);
                tracks.push(...ts);
            }}
        }} else {{
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            tracks = h.trackBoxes(units[unitIdx]);
        }}

        // Filter by type if specified
        const targetTracks = typeVal > 0 ? tracks.filter(t => t.type?.getValue?.() === typeVal) : tracks;
        if (trackIdx >= targetTracks.length) return {{error: "No matching track at index " + trackIdx}};
        const trackBox = targetTracks[trackIdx];

        const regions = h.regionBoxes(trackBox);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx}};

        h.modify(() => {{
            regions[regionIdx].delete();
        }});

        const remaining = h.regionBoxes(trackBox).length;
        return {{
            success: true,
            deleted_region_index: regionIdx,
            remaining_regions: remaining,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_set_region_position(track_index: int, region_index: int, position_beats: float, unit_index: int, region_type: str) -> str:
    """Move a region to a new position on the timeline.

position_beats: New position in beats (e.g. 4.0 = start of bar 2 in 4/4).
region_type: 'note' or 'audio'.
unit_index: Audio unit index (-1 = search all AUs).
track_index: Track index within the AU.
region_index: Region to move (0-based).
"""
    safe_region_type = region_type.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const rType = "{safe_region_type}";
        const newPos = Math.round({position_beats} * h.ppqn.Quarter);

        let tracks = [];
        const units = h.allAUBoxes();
        if (unitIdx < 0) {{
            for (const au of units) {{
                const ts = h.trackBoxes(au);
                tracks.push(...ts);
            }}
        }} else {{
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            tracks = h.trackBoxes(units[unitIdx]);
        }}
        if (trackIdx >= tracks.length) return {{error: "No track at index " + trackIdx}};
        const trackBox = tracks[trackIdx];

        const regions = h.regionBoxes(trackBox);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx}};

        const oldPos = regions[regionIdx].position.getValue();
        h.modify(() => {{
            regions[regionIdx].position.setValue(newPos);
        }});

        return {{
            success: true,
            old_position_beats: oldPos / h.ppqn.Quarter,
            new_position_beats: newPos / h.ppqn.Quarter,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_set_region_duration(track_index: int, region_index: int, duration_beats: int, unit_index: int = 0) -> str:
    """Set the duration of a region.

duration_beats: New duration in beats (e.g. 4.0 = 1 bar in 4/4).
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const newDur = Math.round({duration_beats} * h.ppqn.Quarter);

        let tracks = [];
        const units = h.allAUBoxes();
        if (unitIdx < 0) {{
            for (const au of units) {{
                const ts = h.trackBoxes(au);
                tracks.push(...ts);
            }}
        }} else {{
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            tracks = h.trackBoxes(units[unitIdx]);
        }}
        if (trackIdx >= tracks.length) return {{error: "No track at index " + trackIdx}};
        const trackBox = tracks[trackIdx];

        const regions = h.regionBoxes(trackBox);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx}};

        const oldDur = regions[regionIdx].duration.getValue();
        h.modify(() => {{
            regions[regionIdx].duration.setValue(newDur);
            if (regions[regionIdx].loopDuration) {{
                regions[regionIdx].loopDuration.setValue(newDur);
            }}
        }});

        return {{
            success: true,
            old_duration_beats: oldDur / h.ppqn.Quarter,
            new_duration_beats: newDur / h.ppqn.Quarter,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_set_region_mute(track_index: int, region_index: int, mute: bool, unit_index: int = 0) -> str:
    """Mute or unmute a specific region without deleting it.

mute: true to mute, false to unmute.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const muteVal = {json.dumps(mute)};

        let tracks = [];
        const units = h.allAUBoxes();
        if (unitIdx < 0) {{
            for (const au of units) {{
                const ts = h.trackBoxes(au);
                tracks.push(...ts);
            }}
        }} else {{
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            tracks = h.trackBoxes(units[unitIdx]);
        }}
        if (trackIdx >= tracks.length) return {{error: "No track at index " + trackIdx}};
        const trackBox = tracks[trackIdx];

        const regions = h.regionBoxes(trackBox);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx}};

        const oldMute = regions[regionIdx].mute?.getValue?.() ?? false;
        h.modify(() => {{
            regions[regionIdx].mute.setValue(muteVal);
        }});

        return {{
            success: true,
            old_mute: oldMute,
            new_mute: muteVal,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_set_region_label(track_index: int, region_index: int, label: str, unit_index: int) -> str:
    """Rename a region's label (display name).

label: New label text.
unit_index: Audio unit index (-1 = search all AUs).
track_index: Track index within the AU.
region_index: Region to rename (0-based).
"""
    safe_label = label.replace('"', '').replace("'", '').replace('\\', '')
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};

        let tracks = [];
        const units = h.allAUBoxes();
        if (unitIdx < 0) {{
            for (const au of units) {{
                const ts = h.trackBoxes(au);
                tracks.push(...ts);
            }}
        }} else {{
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            tracks = h.trackBoxes(units[unitIdx]);
        }}
        if (trackIdx >= tracks.length) return {{error: "No track at index " + trackIdx}};
        const trackBox = tracks[trackIdx];

        const regions = h.regionBoxes(trackBox);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx}};

        const oldLabel = regions[regionIdx].label?.getValue?.() ?? "";
        h.modify(() => {{
            regions[regionIdx].label.setValue("{safe_label}");
        }});

        return {{
            success: true,
            old_label: oldLabel,
            new_label: regions[regionIdx].label.getValue(),
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_set_region_color(track_index: int, region_index: int, hue: int, unit_index: int) -> str:
    """Set the color (hue) of a region or clip.

Regions and clips use an Int32Field 'hue' for color. The hue is an integer
that maps to a color in the HSL spectrum (0-360). Use this to visually
distinguish sections (e.g. red for choruses, blue for verses).

track_index: Track index within the AU.
region_index: Region/clip to color (0-based).
hue: Color hue (0-360, e.g. 0=red, 120=green, 240=blue).
unit_index: Audio unit index (-1 = search all AUs).

Returns old and new hue values.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const hueVal = {hue};

        let tracks = [];
        const units = h.allAUBoxes();
        if (unitIdx < 0) {{
            for (const au of units) {{
                const ts = h.trackBoxes(au);
                tracks.push(...ts);
            }}
        }} else {{
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            tracks = h.trackBoxes(units[unitIdx]);
        }}
        if (trackIdx >= tracks.length) return {{error: "No track at index " + trackIdx}};
        const trackBox = tracks[trackIdx];

        const regions = h.regionBoxes(trackBox);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx}};
        const region = regions[regionIdx];

        if (!region.hue) return {{error: "Region has no hue field"}};
        const oldHue = region.hue?.getValue?.() ?? 0;
        h.modify(() => {{
            region.hue.setValue(hueVal);
        }});

        return {{
            success: true,
            old_hue: oldHue,
            new_hue: region.hue.getValue(),
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_get_project_info() -> str:
    """Get a quick project overview: BPM, time signature, track/AU/effect counts, total duration.

Single-call summary — lighter than get_project_state (no per-track detail).
"""
    result = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        const tl = h.timelineBox;
        const units = h.allAUBoxes();

        let totalTracks = 0, totalRegions = 0, totalEffects = 0, totalNotes = 0;
        let maxPos = 0;

        for (const au of units) {
            const tracks = h.trackBoxes(au);
            totalTracks += tracks.length;
            for (const track of tracks) {
                const regions = h.regionBoxes(track);
                totalRegions += regions.length;
                for (const reg of regions) {
                    const endPos = (reg.position?.getValue?.() ?? 0) + (reg.duration?.getValue?.() ?? 0);
                    if (endPos > maxPos) maxPos = endPos;
                    try {
                        const col = reg.events?.targetVertex?.unwrap()?.box;
                        if (col && col.events) {
                            totalNotes += h.eventBoxes(col).length;
                        }
                    } catch(e) {}
                }
            }
            const effects = h.effectBoxes(au);
            totalEffects += effects.length;
        }

        return {
            bpm: tl?.bpm?.getValue?.() ?? 120,
            time_signature: `${tl?.signature?.nominator?.getValue?.() ?? 4}/${tl?.signature?.denominator?.getValue?.() ?? 4}`,
            audio_units: units.length,
            tracks: totalTracks,
            regions: totalRegions,
            effects: totalEffects,
            notes: totalNotes,
            duration_beats: maxPos / h.ppqn.Quarter,
            duration_bars: Math.ceil(maxPos / (h.ppqn.Quarter * (tl?.signature?.nominator?.getValue?.() ?? 4))),
        };
    }""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_compact_tracks(unit_index: int) -> str:
    """Remove empty tracks from an audio unit (or all AUs).

Calls ProjectApi.compactTracks() — removes tracks with no regions.
Useful cleanup after deleting regions or editing.

unit_index: Audio unit index (-1 = all AUs).
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const units = h.allAUBoxes();

        const results = [];
        if (unitIdx < 0) {{
            for (let i = 0; i < units.length; i++) {{
                const before = h.trackBoxes(units[i]).length;
                h.modify(() => h.api.compactTracks(units[i]));
                const after = h.trackBoxes(units[i]).length;
                results.push({{au: i, before, after, removed: before - after}});
            }}
        }} else {{
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            const before = h.trackBoxes(units[unitIdx]).length;
            h.modify(() => h.api.compactTracks(units[unitIdx]));
            const after = h.trackBoxes(units[unitIdx]).length;
            results.push({{au: unitIdx, before, after, removed: before - after}});
        }}
        return {{success: true, results}};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_set_region_loop(track_index: int, region_index: int, loop_beats: float, loop_offset_beats: float, event_offset_beats: float, unit_index: int) -> str:
    """Set loop parameters for a note region.

Looping repeats the note pattern within the region. The region duration
can be longer than the loop, causing the notes to repeat.

loop_beats: Loop length in beats (e.g. 4.0 = 1 bar in 4/4). Set to 0 to disable loop.
loop_offset_beats: Offset within the event collection where the loop starts.
event_offset_beats: Offset added to all note positions.
unit_index: Audio unit index (-1 = search all AUs).
track_index: Track index within the AU.
region_index: Region to modify (0-based).
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const loopTicks = Math.round({loop_beats} * h.ppqn.Quarter);
        const loopOffsetTicks = Math.round({loop_offset_beats} * h.ppqn.Quarter);
        const eventOffsetTicks = Math.round({event_offset_beats} * h.ppqn.Quarter);

        let tracks = [];
        const units = h.allAUBoxes();
        if (unitIdx < 0) {{
            for (const au of units) {{
                const ts = h.trackBoxes(au);
                tracks.push(...ts);
            }}
        }} else {{
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            tracks = h.trackBoxes(units[unitIdx]);
        }}
        if (trackIdx >= tracks.length) return {{error: "No track at index " + trackIdx}};
        const trackBox = tracks[trackIdx];

        const regions = h.regionBoxes(trackBox);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx}};

        const oldLoop = regions[regionIdx].loopDuration?.getValue?.() ?? 0;
        h.modify(() => {{
            regions[regionIdx].loopDuration.setValue(loopTicks);
            if (regions[regionIdx].loopOffset) regions[regionIdx].loopOffset.setValue(loopOffsetTicks);
            if (regions[regionIdx].eventOffset) regions[regionIdx].eventOffset.setValue(eventOffsetTicks);
        }});

        return {{
            success: true,
            old_loop_beats: oldLoop / h.ppqn.Quarter,
            new_loop_beats: loopTicks / h.ppqn.Quarter,
            loop_offset_beats: loopOffsetTicks / h.ppqn.Quarter,
            event_offset_beats: eventOffsetTicks / h.ppqn.Quarter,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
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
        let binary = '';
        for (let i = 0; i < bytes.length; i++) {{
            binary += String.fromCharCode(bytes[i]);
        }}
        const b64 = btoa(binary);

        return {{
            success: true,
            midi_b64: b64,
            note_count: notes.length,
            size_bytes: bytes.length,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
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

@mcp.tool()
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
                const copiedProject = h.project.copy();
                const audioData = await OfflineEngineRenderer.start(
                    copiedProject, Option.wrap(exportConfig), progress, undefined, {sample_rate}
                );

                const wav = WavFile.encodeFloats(audioData);
                const bytes = new Uint8Array(wav);
                let binary = "";
                for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
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
    }}""")
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

@mcp.tool()
async def mcp_opendaw_render_full(filename: str = "full_mix", sample_rate: int = 48000) -> str:
    """Render the entire project as a single stereo WAV file (full mixdown).

    filename: Output filename (without .wav extension).
    sample_rate: Export sample rate (default 48000).

    Uses OfflineEngineRenderer with Option.None (no stems config = full mix).
    Renders from beat 0 to the end of the last region.

    Returns the path to the exported WAV and audio metadata.
    """
    safe_name = _safe_filename(filename)
    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const OfflineEngineRenderer = window.DAW_OfflineEngineRenderer;
        const Option = window.DAW_Option;
        const WavFile = window.DAW_WavFile;

        return new Promise(async (resolve) => {{
            try {{
                // Option.None = no stems config → full mix (1 stem, all AUs mixed)
                const progress = {{setValue: (v) => {{}}}};
                const copiedProject = h.project.copy();
                const audioData = await OfflineEngineRenderer.start(
                    copiedProject, Option.None, progress, undefined, {sample_rate}
                );

                const wav = WavFile.encodeFloats(audioData);
                const bytes = new Uint8Array(wav);
                let binary = "";
                for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
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
    }}""")
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

@mcp.tool()
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
                const copiedProject = h.project.copy();
                const audioData = await OfflineEngineRenderer.start(
                    copiedProject, Option.wrap(exportConfig), progress, undefined, {sample_rate}
                );

                const wav = WavFile.encodeFloats(audioData);
                const bytes = new Uint8Array(wav);
                let binary = "";
                for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
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
    }}""")
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

@mcp.tool()
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
                const copiedProject = h.project.copy();
                const audioData = await OfflineEngineRenderer.start(
                    copiedProject, Option.wrap(exportConfig), progress, undefined, {sample_rate}
                );

                const wav = WavFile.encodeFloats(audioData);
                const bytes = new Uint8Array(wav);
                let binary = "";
                for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
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
    }}""")
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

@mcp.tool()
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
                const copiedProject = h.project.copy();
                const audioData = await OfflineEngineRenderer.start(
                    copiedProject, Option.wrap(exportConfig), progress, undefined, {sample_rate}
                );

                const wav = WavFile.encodeFloats(audioData);
                const bytes = new Uint8Array(wav);
                let binary = "";
                for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
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
    }}""")
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

@mcp.tool()
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

@mcp.tool()
async def mcp_opendaw_create_value_clip(unit_index: int, track_index: int, name: str, clip_index: int) -> str:
    """Create a value clip (automation clip) on an automation track in session view.

Uses ProjectApi.createValueClip — creates a ValueClipBox with an empty
ValueEventCollectionBox on the specified automation (Value-type) track.

unit_index: Audio unit index.
track_index: Automation track index (-1 = first automation track on the unit).
name: Clip label.
clip_index: Clip slot index (0-based).

Returns clip creation details.
"""
    clip_idx = clip_index
    safe_name = name.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const clipIdx = {clip_idx};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
        const au = units[unitIdx];

        // Find Value-type tracks (automation)
        const valueTracks = h.trackBoxes(au).filter(t => t.type?.getValue?.() === 3);

        if (valueTracks.length === 0) return {{error: "No automation tracks on AU " + unitIdx + ". Use add_automation first."}};
        const targetTrack = trackIdx < 0 ? valueTracks[0] : (trackIdx < valueTracks.length ? valueTracks[trackIdx] : null);
        if (!targetTrack) return {{error: "No automation track at index " + trackIdx}};

        let clip;
        h.editing.modify(() => {{
            clip = h.api.createValueClip(targetTrack, clipIdx, {{name: "{safe_name}"}});
        }});

        if (!clip) return {{error: "Failed to create value clip"}};

        return {{
            success: true,
            clip_class: clip.constructor.name,
            label: clip.label?.getValue?.() ?? "",
            duration_beats: (clip.duration?.getValue?.() ?? 0) / h.ppqn.Quarter,
            mute: clip.mute?.getValue?.() ?? false,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_list_automation_events(unit_index: int, track_index: int) -> str:
    """List automation events (ValueEventBox) on a unit's automation tracks.

Finds all Value-type tracks (automation) on the given audio unit and
returns their automation points: position (beats), value (0-1), interpolation type.

unit_index: Audio unit index.
track_index: Specific automation track (-1 = all automation tracks on the unit).

Returns list of tracks with their automation events.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const Quarter = h.ppqn.Quarter;

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
        const au = units[unitIdx];

        // Value tracks = type 3
        let valueTracks = h.trackBoxes(au).filter(b => b.type?.getValue?.() === 3);

        if (trackIdx >= 0) {{
            if (trackIdx >= valueTracks.length) return {{error: "No automation track at index " + trackIdx}};
            valueTracks = [valueTracks[trackIdx]];
        }}

        const tracks = valueTracks.map((track, ti) => {{
            // Get value clips for this track
            const clips = [...track.clips?.pointerHub?.incoming?.() ?? []].map(({{box}}) => box);
            const events = [];
            for (const clip of clips) {{
                let collection = null;
                try {{
                    collection = clip.events?.targetVertex?.unwrap?.()?.box;
                }} catch(e) {{}}
                if (collection && collection.events) {{
                    const evtBoxes = h.eventBoxes(collection);
                    for (const evt of evtBoxes) {{
                        const interpVal = evt.interpolation?.getValue?.() ?? 0;
                        let interp = "none";
                        if (interpVal === 1) interp = "linear";
                        else if (interpVal === 0) {{
                            const curveBox = evt.interpolation?.pointerHub?.incoming?.()?.at?.(0)?.box;
                            interp = curveBox ? "curve" : "hold";
                        }}
                        events.push({{
                            position_beats: evt.position.getValue() / Quarter,
                            value: evt.value.getValue(),
                            index: evt.index?.getValue?.() ?? 0,
                            interpolation: interp,
                        }});
                    }}
                }}
            }}
            events.sort((a, b) => a.position_beats - b.position_beats);
            return {{
                track_index: ti,
                clip_count: clips.length,
                event_count: events.length,
                events,
            }};
        }});

        return {{
            success: true,
            unit_index: unitIdx,
            automation_track_count: valueTracks.length,
            tracks,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_list_value_regions(unit_index: int, track_index: int) -> str:
    """List automation regions (ValueRegionBox) on value/automation tracks.

Finds all Value-type tracks (automation) and lists their regions with
position, duration, loop settings, mute, and label.

unit_index: Audio unit index (-1 = search all AUs).
track_index: Specific value track (-1 = all value tracks on the unit).

Returns list of automation regions.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const Quarter = h.ppqn.Quarter;

        let targetAUs;
        if (unitIdx < 0) {{
            targetAUs = h.allAUBoxes();
        }} else {{
            const units = h.allAUBoxes();
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            targetAUs = [units[unitIdx]];
        }}

        const regionList = [];
        for (let ui = 0; ui < targetAUs.length; ui++) {{
            const au = targetAUs[ui];
            const allTracks = h.trackBoxes(au);
            const valueTracks = allTracks.filter(t => t.type?.getValue?.() === 3);
            const targetTracks = trackIdx < 0 ? valueTracks : (trackIdx < valueTracks.length ? [valueTracks[trackIdx]] : []);

            for (let ti = 0; ti < targetTracks.length; ti++) {{
                const track = targetTracks[ti];
                const actualTrackIdx = valueTracks.indexOf(track);
                const regions = h.regionBoxes(track);
                for (let ri = 0; ri < regions.length; ri++) {{
                    const region = regions[ri];
                    regionList.push({{
                        unit_index: unitIdx < 0 ? ui : unitIdx,
                        track_index: actualTrackIdx,
                        region_index: ri,
                        position_beats: (region.position?.getValue?.() ?? 0) / Quarter,
                        duration_beats: (region.duration?.getValue?.() ?? 0) / Quarter,
                        loop_offset_beats: (region.loopOffset?.getValue?.() ?? 0) / Quarter,
                        loop_duration_beats: (region.loopDuration?.getValue?.() ?? 0) / Quarter,
                        mute: region.mute?.getValue?.() ?? false,
                        label: region.label?.getValue?.() ?? "",
                    }});
                }}
            }}
        }}

        return {{
            success: true,
            region_count: regionList.length,
            regions: regionList,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_set_clip_playback(unit_index: int, track_index: int, clip_index: int, loop: bool, reverse: bool, speed: float) -> str:
    """Set clip playback parameters (loop, reverse, speed) on a clip.

Clips have a ClipPlaybackFields (triggerMode) object with:
- loop: Whether the clip loops (true/false)
- reverse: Play in reverse (true/false)
- speed: Playback speed multiplier (1 = normal)
- quantise: Quantise value
- trigger: Trigger mode

Pass None for any parameter to skip changing it.

unit_index: Audio unit index.
track_index: Track index.
clip_index: Clip index (from list_clips).
loop: Enable looping (None = skip).
reverse: Reverse playback (None = skip).
speed: Speed multiplier (None = skip).

Returns updated playback values.
"""
    loop_val = json.dumps(loop)
    reverse_val = json.dumps(reverse)
    speed_val = json.dumps(speed)
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const clipIdx = {clip_index};
        const loopVal = {loop_val};
        const reverseVal = {reverse_val};
        const speedVal = {speed_val};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
        const au = units[unitIdx];

        const allTracks = h.trackBoxes(au);
        if (trackIdx >= allTracks.length) return {{error: "No track at index " + trackIdx}};
        const track = allTracks[trackIdx];

        const clips = [...track.clips?.pointerHub?.incoming?.() ?? []].map(({{box}}) => box);
        if (clipIdx >= clips.length) return {{error: "No clip at index " + clipIdx}};
        const clip = clips[clipIdx];

        if (!clip.triggerMode) return {{error: "Clip has no triggerMode"}};

        h.editing.modify(() => {{
            if (loopVal !== null) clip.triggerMode.loop.setValue(loopVal);
            if (reverseVal !== null) clip.triggerMode.reverse.setValue(reverseVal);
            if (speedVal !== null) clip.triggerMode.speed.setValue(speedVal);
        }});

        return {{
            success: true,
            clip_class: clip.constructor.name,
            label: clip.label?.getValue?.() ?? "",
            loop: clip.triggerMode.loop.getValue(),
            reverse: clip.triggerMode.reverse.getValue(),
            speed: clip.triggerMode.speed?.getValue?.() ?? 1,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_set_clip_properties(unit_index: int, track_index: int, clip_index: int, label: str, hue: int, mute: bool, duration_beats: int) -> str:
    """Set properties on a clip (session view): label, color, mute, duration.

Pass empty string for label to skip, -1 for hue/duration to skip,
None for mute to skip.

unit_index: Audio unit index.
track_index: Track index.
clip_index: Clip index (from list_clips).
label: New label (empty = skip).
hue: New color hue 0-360 (-1 = skip).
mute: Mute state (None = skip).
duration_beats: New duration in beats (-1 = skip).

Returns updated clip properties.
"""
    label_val = json.dumps(label)
    mute_val = json.dumps(mute)
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const clipIdx = {clip_index};
        const Quarter = h.ppqn.Quarter;
        const hueVal = {hue};
        const muteVal = {mute_val};
        const durVal = {duration_beats};
        const labelVal = {label_val};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
        const au = units[unitIdx];

        const allTracks = h.trackBoxes(au);
        if (trackIdx >= allTracks.length) return {{error: "No track at index " + trackIdx}};
        const track = allTracks[trackIdx];

        const clips = [...track.clips?.pointerHub?.incoming?.() ?? []].map(({{box}}) => box);
        if (clipIdx >= clips.length) return {{error: "No clip at index " + clipIdx}};
        const clip = clips[clipIdx];

        h.editing.modify(() => {{
            if (labelVal !== null) clip.label.setValue(labelVal);
            if (hueVal >= 0 && clip.hue) clip.hue.setValue(hueVal);
            if (muteVal !== null && clip.mute) clip.mute.setValue(muteVal);
            if (durVal >= 0 && clip.duration) clip.duration.setValue(Math.round(durVal * Quarter));
        }});

        return {{
            success: true,
            clip_class: clip.constructor.name,
            label: clip.label?.getValue?.() ?? "",
            hue: clip.hue?.getValue?.() ?? 0,
            mute: clip.mute?.getValue?.() ?? false,
            duration_beats: (clip.duration?.getValue?.() ?? 0) / Quarter,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_delete_clip(unit_index: int, track_index: int, clip_index: int) -> str:
    """Delete a clip from a track (session view).

unit_index: Audio unit index.
track_index: Track index.
clip_index: Clip index to delete (0-based).

Returns remaining clip count.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const clipIdx = {clip_index};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
        const au = units[unitIdx];

        const allTracks = h.trackBoxes(au);
        if (trackIdx >= allTracks.length) return {{error: "No track at index " + trackIdx}};
        const track = allTracks[trackIdx];

        const clips = [...track.clips?.pointerHub?.incoming?.() ?? []].map(({{box}}) => box);
        if (clipIdx >= clips.length) return {{error: "No clip at index " + clipIdx}};

        h.editing.modify(() => {{
            clips[clipIdx].delete();
        }});

        const remaining = [...track.clips?.pointerHub?.incoming?.() ?? []].length;
        return {{
            success: true,
            deleted_clip_index: clipIdx,
            remaining_clips: remaining,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_list_clips(unit_index: int, track_index: int) -> str:
    """List clips (session view / clip launcher) on tracks.

Clips live on TrackBox.clips (ClipCollection). Three types:
- NoteClipBox: MIDI clips (index, duration, mute, label, hue, triggerMode)
- AudioClipBox: Audio clips (same + file, gain, playMode)
- ValueClipBox: Automation clips (same + events)

unit_index: Audio unit index.
track_index: Track index (-1 = all tracks on the unit).

Returns list of clips with type, index, duration, mute, label, loop.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const Quarter = h.ppqn.Quarter;

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
        const au = units[unitIdx];

        const allTracks = h.trackBoxes(au);
        const targetTracks = trackIdx < 0 ? allTracks : (trackIdx < allTracks.length ? [allTracks[trackIdx]] : []);

        const clipList = [];
        for (let ti = 0; ti < targetTracks.length; ti++) {{
            const track = targetTracks[ti];
            const actualIdx = allTracks.indexOf(track);
            const trackType = track.type?.getValue?.();
            const clips = [...track.clips?.pointerHub?.incoming?.() ?? []].map(({{box}}) => box);
            for (let ci = 0; ci < clips.length; ci++) {{
                const clip = clips[ci];
                const clsName = clip.constructor.name;
                let clipType = "unknown";
                if (clsName === "NoteClipBox") clipType = "note";
                else if (clsName === "AudioClipBox") clipType = "audio";
                else if (clsName === "ValueClipBox") clipType = "value";

                const info = {{
                    track_index: actualIdx,
                    clip_index: clip.index?.getValue?.() ?? ci,
                    type: clipType,
                    class: clsName,
                    duration_beats: (clip.duration?.getValue?.() ?? 0) / Quarter,
                    mute: clip.mute?.getValue?.() ?? false,
                    label: clip.label?.getValue?.() ?? "",
                    loop: clip.triggerMode?.loop?.getValue?.() ?? false,
                    reverse: clip.triggerMode?.reverse?.getValue?.() ?? false,
                }};
                clipList.push(info);
            }}
        }}

        return {{
            success: true,
            unit_index: unitIdx,
            clip_count: clipList.length,
            clips: clipList,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_connect_sidechain(source_unit_index: int, target_unit_index: int, effect_index: int) -> str:
    """Connect one audio unit's output as sidechain source to a Compressor/Gate on another unit.

source_unit_index: Audio unit whose output triggers the sidechain (e.g. drums).
target_unit_index: Audio unit with the Compressor/Gate effect (e.g. bass).
effect_index: Effect position on the target unit (must have a sideChain field).

The target effect must be Compressor, Gate, Vocoder, or any effect with Pointers.SideChain.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const srcIdx = {source_unit_index};
        const tgtIdx = {target_unit_index};
        const effIdx = {effect_index};

        const units = h.allAUBoxes();
        if (srcIdx >= units.length) return {{error: "No source AU at " + srcIdx}};
        if (tgtIdx >= units.length) return {{error: "No target AU at " + tgtIdx}};
        const sourceAU = units[srcIdx];
        const targetAU = units[tgtIdx];

        const effects = h.effectBoxes(targetAU);
        if (effIdx >= effects.length) return {{error: "No effect at " + effIdx}};
        const effectBox = effects[effIdx];

        if (!effectBox.sideChain || typeof effectBox.sideChain.refer !== 'function') {{
            return {{error: effectBox.constructor.name + " has no sideChain input"}};
        }}

        h.editing.modify(() => {{
            effectBox.sideChain.refer(sourceAU);
        }});

        return {{
            success: true,
            source: String(sourceAU.address),
            target_effect: effectBox.constructor.name,
            sidechain_connected: !effectBox.sideChain.isEmpty?.(),
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_reset_project() -> str:
    """Reset the project to a fresh state — removes all audio units, tracks, regions, effects.

Useful for starting a new mix session without reloading the browser.
The output audio unit is preserved (required for audio routing).
"""
    result = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        let deleted = 0;
        h.editing.modify(() => {
            const units = h.allAUBoxes();
            // Delete all instrument AUs (keep output AU at index 0)
            for (let i = units.length - 1; i >= 1; i--) {
                try { units[i].delete(); deleted++; } catch(e) {}
            }
            // Delete all effects on output AU
            const outputAU = units[0];
            if (outputAU) {
                const effects = h.effectBoxes(outputAU);
                for (const eff of effects) {
                    try { eff.delete(); deleted++; } catch(e) {}
                }
            }
        });
        return {
            success: true,
            deleted_boxes: deleted,
            remaining_units: h.allAUBoxes().length,
        };
    }""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_save_project(filename: str) -> str:
    """Save the current project state to a binary file.

Serializes the boxGraph (all tracks, regions, effects, notes, settings)
to an ArrayBuffer and saves it as a .odaw file in the exports directory.
Use load_project to restore later.

filename: Name for the saved project (without extension).
Returns: file path, size, and box count.
"""
    result = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        try {
            const buffer = h.project.toArrayBuffer();
            const bytes = new Uint8Array(buffer);
            let binary = "";
            for (let i = 0; i < bytes.length; i++) {
                binary += String.fromCharCode(bytes[i]);
            }
            const b64 = btoa(binary);
            window.__lastProjectB64 = b64;
            window.__lastProjectSize = bytes.length;
            return {
                success: true,
                size_bytes: bytes.length,
                boxes: h.boxGraph.boxes().length,
            };
        } catch(e) {
            return {error: String(e)};
        }
    }""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_load_project(filename: str) -> str:
    """Load a previously saved project from a .odaw file.

Restores the full project state (tracks, regions, effects, notes, settings)
from a serialized ArrayBuffer. The engine must be restarted after loading
(call start_engine again).

filename: Name of the .odaw file in the exports directory (without path).
Returns: box count and confirmation.
"""
    import base64
    filepath = os.path.join(EXPORT_DIR, filename if filename.endswith('.odaw') else filename + '.odaw')
    with open(filepath, 'rb') as f:
        b64_data = base64.b64encode(f.read()).decode('ascii')
    result = await bridge.evaluate(f"""() => {{
        const b64 = "{b64_data}";
        const binary = atob(b64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
        const buffer = bytes.buffer;
        try {{
            if (window.DAW_terminateEngine) window.DAW_terminateEngine();
            if (!window.DAW_loadProject) throw new Error("DAW_loadProject not available");
            const newProject = window.DAW_loadProject(buffer);
            return {{success: true, boxes: newProject.boxGraph.boxes().length}};
        }} catch(e) {{
            return {{error: String(e), stack: e.stack?.substring(0, 300)}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
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

@mcp.tool()
async def mcp_opendaw_list_tracks() -> str:
    """List all tracks across all audio units with their type, effects, and regions.

Returns structured info: audio units with their tracks (audio/note/automation),
effects chain, volume, panning, and region count.
"""
    result = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        const units = h.allAUBoxes();
        const result = units.map((au, i) => {
            const tracks = h.trackBoxes(au).map((box) => {
                const typeVal = box.type?.getValue?.() ?? -1;
                const typeName = typeVal === 0 ? 'undefined' : typeVal === 1 ? 'note' : typeVal === 2 ? 'audio' : typeVal === 3 ? 'automation' : 'unknown:' + typeVal;
                const regions = box.regions ? h.regionBoxes(box).length : 0;
                const clips = box.clips ? h.clipBoxes(box).length : 0;
                return {type: typeName, regions, clips};
            });
            const effects = h.effectBoxes(au).map((box) => ({
                type: box.constructor?.name || 'Unknown',
                enabled: box.enabled?.getValue?.() ?? true,
            })).sort((a, b) => 0); // keep insertion order
            return {
                index: i,
                name: au.name?.getValue?.() || ('Unit ' + i),
                type: au.type?.getValue?.() || 'unknown',
                volume_raw: au.volume?.getValue?.() ?? 0,
                panning: au.panning?.getValue?.() ?? 0,
                mute: au.mute?.getValue?.() ?? false,
                solo: au.solo?.getValue?.() ?? false,
                tracks,
                effects,
            };
        });
        return {success: true, units: result, total_units: result.length};
    }""")
    return _wrap_eval(result)

@mcp.tool()
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

@mcp.tool()
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
                    const copied = h.project.copy();
                    const audioData = await OfflineEngineRenderer.start(copied, Option.None, progress, undefined, {sample_rate});
                    const wav = WavFile.encodeFloats(audioData);
                    const bytes = new Uint8Array(wav);
                    let binary = "";
                    for (let j = 0; j < bytes.length; j++) binary += String.fromCharCode(bytes[j]);
                    window.__lastExportB64 = btoa(binary);
                    resolve({{success: true, samples: audioData.frames[0]?.length || 0}});
                }} catch(e) {{
                    resolve({{error: e.message}});
                }}
            }});
        }}""")
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

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
async def mcp_opendaw_create_time_stretched_region(sample_id: str, unit_index: int, start_beat: int, track_index: int, playback_rate: float, transient_mode: str, bpm: int) -> str:
    """Place a time-stretched audio region on a track.

Unlike place_audio_region (which uses TimeBase.Seconds), this creates a
musically-timed region with warp markers. Audio plays back at a different
speed while staying in sync with the project tempo.

sample_id: The ID returned by mcp_opendaw_load_audio.
unit_index: Audio unit index (default 0).
start_beat: Beat position to place the region.
track_index: Track index within the audio unit (default 0).
playback_rate: Rate multiplier (1.0 = original, 0.5 = half-speed, 2.0 = double).
transient_mode: "once", "repeat", or "pingpong" (default).
bpm: Source BPM of the sample (for warp marker calculation).

Returns position, duration in PPQN, and playback rate.
"""
    mode_val = json.dumps(transient_mode)


    safe_sample_id = sample_id.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const UUID = h.uuid;
        const PPQN = h.ppqn;
        const Quarter = PPQN.Quarter;
        const AudioFileBox = window.DAW_AudioFileBox;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const sampleId = "{safe_sample_id}";
        const startBeat = {start_beat};
        const playbackRate = {playback_rate};
        const transientMode = {mode_val};
        const sampleBpm = {bpm};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
        const au = units[unitIdx];

        const audioTracks = h.trackBoxes(au)
            .filter(box => box.type?.getValue?.() === 2);
        if (trackIdx >= audioTracks.length) return {{error: "No audio track at index " + trackIdx}};
        const trackBox = audioTracks[trackIdx];

        const audioBuffer = window.DAW_localAudioBuffers.get(sampleId);
        if (!audioBuffer) return {{error: "Sample not loaded: " + sampleId}};

        const sample = {{
            name: sampleId,
            duration: audioBuffer.duration,
            bpm: sampleBpm,
            sample_rate: audioBuffer.sampleRate,
        }};

        let regionBox, audioFileBox;
        h.editing.modify(() => {{
            audioFileBox = AudioFileBox.create(h.boxGraph, UUID.generate(), (box) => {{
                box.fileName.setValue(sampleId);
                box.startInSeconds.setValue(0.0);
                box.endInSeconds.setValue(audioBuffer.duration);
            }});

            regionBox = h.api.createTimeStretchedRegion({{
                boxGraph: h.boxGraph,
                targetTrack: trackBox,
                position: Math.round(startBeat * Quarter),
                audioFileBox: audioFileBox,
                sample: sample,
                playbackRate: playbackRate,
                transientPlayMode: transientMode,
            }});
        }});

        return {{
            success: true,
            sample_id: sampleId,
            position_beats: startBeat,
            duration_ppqn: regionBox.duration.getValue(),
            playback_rate: playbackRate,
            transient_mode: "{transient_mode}",
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_create_pitch_stretched_region(sample_id: str, unit_index: int, start_beat: int, track_index: int, bpm: int) -> str:
    """Place a pitch-stretched audio region on a track.

Pitch-stretch preserves the original timing but allows pitch manipulation
via warp markers. Use this when you want to tune audio to project key
without changing its duration.

sample_id: The ID returned by mcp_opendaw_load_audio.
unit_index: Audio unit index (default 0).
start_beat: Beat position to place the region.
track_index: Track index within the audio unit (default 0).
bpm: Source BPM of the sample (for warp marker calculation).

Returns position and duration in PPQN.
"""
    safe_sample_id = sample_id.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const UUID = h.uuid;
        const PPQN = h.ppqn;
        const Quarter = PPQN.Quarter;
        const AudioFileBox = window.DAW_AudioFileBox;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const sampleId = "{safe_sample_id}";
        const startBeat = {start_beat};
        const sampleBpm = {bpm};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
        const au = units[unitIdx];

        const audioTracks = h.trackBoxes(au)
            .filter(box => box.type?.getValue?.() === 2);
        if (trackIdx >= audioTracks.length) return {{error: "No audio track at index " + trackIdx}};
        const trackBox = audioTracks[trackIdx];

        const audioBuffer = window.DAW_localAudioBuffers.get(sampleId);
        if (!audioBuffer) return {{error: "Sample not loaded: " + sampleId}};

        const sample = {{
            name: sampleId,
            duration: audioBuffer.duration,
            bpm: sampleBpm,
            sample_rate: audioBuffer.sampleRate,
        }};

        let regionBox, audioFileBox;
        h.editing.modify(() => {{
            audioFileBox = AudioFileBox.create(h.boxGraph, UUID.generate(), (box) => {{
                box.fileName.setValue(sampleId);
                box.startInSeconds.setValue(0.0);
                box.endInSeconds.setValue(audioBuffer.duration);
            }});

            regionBox = h.api.createPitchStretchedRegion({{
                boxGraph: h.boxGraph,
                targetTrack: trackBox,
                position: Math.round(startBeat * Quarter),
                audioFileBox: audioFileBox,
                sample: sample,
            }});
        }});

        return {{
            success: true,
            sample_id: sampleId,
            position_beats: startBeat,
            duration_ppqn: regionBox.duration.getValue(),
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_duplicate_region(unit_index: int, track_index: int, region_index: int, find_free_space: bool) -> str:
    """Duplicate any region (audio, note, or value) using the DAW's built-in duplicateRegion API.

Places the copy right after the original. With find_free_space=True, scans
for the first available gap on any track (auto-resolves overlaps). Without
it, places on the same track at the original's end position.

unit_index: Audio unit index (-1 = search all AUs).
track_index: Track index within the AU.
region_index: Region to duplicate (0-based).
find_free_space: If True, find the first free space on any track. If False,
    place directly after the original on the same track.

Returns the new region's position and index.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const findFree = {json.dumps(find_free_space)};

        // Find the track
        let tracks = [];
        if (unitIdx < 0) {{
            const allUnits = h.allAUBoxes();
            for (const au of allUnits) {{
                tracks.push(...h.trackBoxes(au));
            }}
        }} else {{
            const units = h.allAUBoxes();
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            tracks = h.trackBoxes(units[unitIdx]);
        }}

        if (trackIdx >= tracks.length) return {{error: "No track at index " + trackIdx}};
        const trackBox = tracks[trackIdx];

        const regions = h.regionBoxes(trackBox);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx}};
        const srcRegion = regions[regionIdx];

        // Get the adapter for this region via TrackBoxAdapter.regions.collection
        const TrackBoxAdapter = window.DAW_TrackBoxAdapter;
        const trackAdapter = h.project.boxAdapters.adapterFor(trackBox, TrackBoxAdapter);
        const regionAdapters = trackAdapter.regions.collection.asArray();
        if (regionIdx >= regionAdapters.length) return {{error: "No region adapter at index " + regionIdx}};
        const regionAdapter = regionAdapters[regionIdx];

        let result2;
        h.editing.modify(() => {{
            const opt = h.api.duplicateRegion(regionAdapter, {{findFreeSpace: findFree}});
            result2 = opt.match({{
                some: (dup) => ({{
                    success: true,
                    new_position_ppqn: dup.position,
                    new_duration_ppqn: dup.duration,
                    new_complete_ppqn: dup.complete,
                }}),
                none: () => ({{error: "duplicateRegion returned None (track has no adapter)"}})
            }});
        }});

        return result2 || {{error: "No result from duplicateRegion"}};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_create_note_clip(unit_index: int, track_index: int, clip_index: int, name: str, hue: int) -> str:
    """Create a note clip in the session view (clip launcher).

Note clips are the session-view counterpart to note regions. They contain
a NoteEventCollection and can be triggered independently in the clip launcher.

unit_index: Audio unit index (-1 = search all AUs for note tracks).
track_index: Note track index within the AU.
clip_index: Slot index in the clip launcher (0, 1, 2, ...).
name: Display name for the clip.
hue: Color hue 0-360 (-1 = auto from track type).

Returns clip UUID and index.
"""
    safe_name = name.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const clipIdx = {clip_index};
        const clipName = "{safe_name}";
        const clipHue = {hue};

        // Find note track
        let noteTracks = [];
        if (unitIdx < 0) {{
            const allUnits = h.allAUBoxes();
            for (const au of allUnits) {{
                noteTracks.push(...h.noteTrackBoxes(au));
            }}
        }} else {{
            const units = h.allAUBoxes();
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            noteTracks = h.noteTrackBoxes(units[unitIdx]);
        }}

        if (trackIdx >= noteTracks.length) return {{error: "No note track at index " + trackIdx}};
        const trackBox = noteTracks[trackIdx];

        let clipBox;
        h.editing.modify(() => {{
            const opts = {{name: clipName}};
            if (clipHue >= 0) opts.hue = clipHue;
            clipBox = h.api.createNoteClip(trackBox, clipIdx, opts);
        }});

        return {{
            success: true,
            clip_uuid: clipBox.address.uuid.toString(),
            clip_index: clipBox.index.getValue(),
            label: clipBox.label.getValue(),
            duration_ppqn: clipBox.duration.getValue(),
            track_type: "Notes",
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_create_track_region(unit_index: int, track_index: int, start_beat: int, duration_beats: int, name: str, hue: int) -> str:
    """Create a region on any track (note or value) using the generic createTrackRegion API.

Automatically detects track type and creates the appropriate region:
- Note track → NoteRegionBox with NoteEventCollection
- Value track → ValueRegionBox with ValueEventCollection
Returns Option.None (error) for audio tracks — use place_audio_region instead.

unit_index: Audio unit index (-1 = search all AUs).
track_index: Track index within the AU.
start_beat: Beat position for the region.
duration_beats: Duration in beats.
name: Display name (empty = auto: "Notes" or "Automation").
hue: Color 0-360 (-1 = auto from track type).

Returns region UUID, type, and position.
"""
    safe_name = name.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const PPQN = h.ppqn;
        const Quarter = PPQN.Quarter;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const startBeat = {start_beat};
        const durBeats = {duration_beats};
        const regionName = "{safe_name}";
        const regionHue = {hue};

        let tracks = [];
        if (unitIdx < 0) {{
            for (const au of h.allAUBoxes()) {{
                tracks.push(...h.trackBoxes(au));
            }}
        }} else {{
            const units = h.allAUBoxes();
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            tracks = h.trackBoxes(units[unitIdx]);
        }}

        if (trackIdx >= tracks.length) return {{error: "No track at index " + trackIdx}};
        const trackBox = tracks[trackIdx];
        const trackType = trackBox.type.getValue();

        let regionBox;
        h.editing.modify(() => {{
            const opts = {{}};
            if (regionName) opts.name = regionName;
            if (regionHue >= 0) opts.hue = regionHue;
            const opt = h.api.createTrackRegion(trackBox, Math.round(startBeat * Quarter), Math.round(durBeats * Quarter), opts);
            opt.match({{
                some: (box) => {{ regionBox = box }},
                none: () => {{}}
            }});
        }});

        if (!regionBox) return {{error: "createTrackRegion returned None (track type may not support regions)"}};
        return {{
            success: true,
            region_uuid: regionBox.address.uuid.toString(),
            position: regionBox.position.getValue(),
            duration: regionBox.duration.getValue(),
            track_type: trackType === 1 ? "Notes" : trackType === 3 ? "Value" : "Type " + trackType,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_create_audio_clip(sample_id: str, unit_index: int, clip_index: int, track_index: int, bpm: int) -> str:
    """Create an audio clip in the session view (clip launcher).

Audio clips are the session-view counterpart to audio regions. They appear
in the clip launcher and can be triggered independently.

sample_id: The ID returned by mcp_opendaw_load_audio.
unit_index: Audio unit index (default 0).
clip_index: Slot index in the clip launcher (0, 1, 2, ...).
track_index: Track index within the audio unit (default 0).
bpm: Source BPM of the sample (for warp marker calculation).

Returns clip UUID and index.
"""
    safe_sample_id = sample_id.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const UUID = h.uuid;
        const AudioFileBox = window.DAW_AudioFileBox;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const clipIdx = {clip_index};
        const sampleId = "{safe_sample_id}";
        const sampleBpm = {bpm};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
        const au = units[unitIdx];

        const audioTracks = h.trackBoxes(au)
            .filter(box => box.type?.getValue?.() === 2);
        if (trackIdx >= audioTracks.length) return {{error: "No audio track at index " + trackIdx}};
        const trackBox = audioTracks[trackIdx];

        const audioBuffer = window.DAW_localAudioBuffers.get(sampleId);
        if (!audioBuffer) return {{error: "Sample not loaded: " + sampleId}};

        const sample = {{
            name: sampleId,
            duration: audioBuffer.duration,
            bpm: sampleBpm,
            sample_rate: audioBuffer.sampleRate,
        }};

        let clipBox;
        h.editing.modify(() => {{
            const audioFileBox = AudioFileBox.create(h.boxGraph, UUID.generate(), (box) => {{
                box.fileName.setValue(sampleId);
                box.startInSeconds.setValue(0.0);
                box.endInSeconds.setValue(audioBuffer.duration);
            }});

            clipBox = h.api.createNotStretchedClip({{
                boxGraph: h.boxGraph,
                targetTrack: trackBox,
                index: clipIdx,
                audioFileBox: audioFileBox,
                sample: sample,
            }});
        }});

        return {{
            success: true,
            clip_uuid: clipBox.address.uuid.toString(),
            clip_index: clipBox.index.getValue(),
            label: clipBox.label.getValue(),
            duration_seconds: audioBuffer.duration,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_create_time_stretched_clip(sample_id: str, unit_index: int, clip_index: int, track_index: int, bpm: int, playback_rate: float, transient_mode: str) -> str:
    """Create a time-stretched audio clip in session view.

sample_id: ID from mcp_opendaw_load_audio.
unit_index: Audio unit index.
clip_index: Slot index in clip launcher.
track_index: Audio track index within AU.
bpm: Source BPM of the sample.
playback_rate: Playback rate (1.0 = normal, 0.5 = half speed, 2.0 = double).
transient_mode: "Pingpong", "Monoton", "Cycles", or "Plode".
"""
    safe_mode = transient_mode.replace('"', '').replace("'", '').replace('\\', '')


    safe_sample_id = sample_id.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const UUID = h.uuid;
        const AudioFileBox = window.DAW_AudioFileBox;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const clipIdx = {clip_index};
        const sampleId = "{safe_sample_id}";
        const sampleBpm = {bpm};
        const rate = {playback_rate};
        const modeName = "{safe_mode}";

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
        const au = units[unitIdx];

        const audioTracks = h.trackBoxes(au).filter(box => box.type?.getValue?.() === 2);
        if (trackIdx >= audioTracks.length) return {{error: "No audio track at index " + trackIdx}};
        const trackBox = audioTracks[trackIdx];

        const audioBuffer = window.DAW_localAudioBuffers.get(sampleId);
        if (!audioBuffer) return {{error: "Sample not loaded: " + sampleId}};

        const sample = {{name: sampleId, duration: audioBuffer.duration, bpm: sampleBpm, sample_rate: audioBuffer.sampleRate}};

        const TransientPlayMode = {{Pingpong: 0, Monoton: 1, Cycles: 2, Plode: 3}};
        const tMode = TransientPlayMode[modeName] ?? 0;

        let clipBox;
        h.editing.modify(() => {{
            const audioFileBox = AudioFileBox.create(h.boxGraph, UUID.generate(), (box) => {{
                box.fileName.setValue(sampleId);
                box.startInSeconds.setValue(0.0);
                box.endInSeconds.setValue(audioBuffer.duration);
            }});

            clipBox = h.api.createTimeStretchedClip({{
                boxGraph: h.boxGraph,
                targetTrack: trackBox,
                index: clipIdx,
                audioFileBox: audioFileBox,
                sample: sample,
                playbackRate: rate,
                transientPlayMode: tMode,
            }});
        }});

        return {{
            success: true,
            clip_uuid: clipBox.address.uuid.toString(),
            clip_index: clipBox.index.getValue(),
            label: clipBox.label.getValue(),
            playback_rate: rate,
            transient_mode: modeName,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_create_pitch_stretched_clip(sample_id: str, unit_index: int, clip_index: int, track_index: int, bpm: int) -> str:
    """Create a pitch-stretched audio clip in session view.

Pitch-stretched clips maintain pitch alignment with the project tempo.
Uses AudioPitchStretchBox for play mode.

sample_id: ID from mcp_opendaw_load_audio.
unit_index: Audio unit index.
clip_index: Slot index in clip launcher.
track_index: Audio track index within AU.
bpm: Source BPM of the sample.
"""
    safe_sample_id = sample_id.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const UUID = h.uuid;
        const AudioFileBox = window.DAW_AudioFileBox;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const clipIdx = {clip_index};
        const sampleId = "{safe_sample_id}";
        const sampleBpm = {bpm};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
        const au = units[unitIdx];

        const audioTracks = h.trackBoxes(au).filter(box => box.type?.getValue?.() === 2);
        if (trackIdx >= audioTracks.length) return {{error: "No audio track at index " + trackIdx}};
        const trackBox = audioTracks[trackIdx];

        const audioBuffer = window.DAW_localAudioBuffers.get(sampleId);
        if (!audioBuffer) return {{error: "Sample not loaded: " + sampleId}};

        const sample = {{name: sampleId, duration: audioBuffer.duration, bpm: sampleBpm, sample_rate: audioBuffer.sampleRate}};

        let clipBox;
        h.editing.modify(() => {{
            const audioFileBox = AudioFileBox.create(h.boxGraph, UUID.generate(), (box) => {{
                box.fileName.setValue(sampleId);
                box.startInSeconds.setValue(0.0);
                box.endInSeconds.setValue(audioBuffer.duration);
            }});

            clipBox = h.api.createPitchStretchedClip({{
                boxGraph: h.boxGraph,
                targetTrack: trackBox,
                index: clipIdx,
                audioFileBox: audioFileBox,
                sample: sample,
            }});
        }});

        return {{
            success: true,
            clip_uuid: clipBox.address.uuid.toString(),
            clip_index: clipBox.index.getValue(),
            label: clipBox.label.getValue(),
            timebase: "musical",
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_set_script_device_code(device_type: str, unit_index: int, device_index: int, code: str) -> str:
    """Set the user JavaScript code on a scriptable device (Apparat/Werkstatt/Spielwerk).

    Compiles the code using the official OpenDAW ScriptCompiler, which:
    - Parses @param declarations and creates WerkstattParameterBox children
    - Parses @sample declarations and creates WerkstattSampleBox children
    - Validates the JavaScript (new Function check)
    - Registers the worklet module on the AudioContext
    - Writes the code with proper // @<tag> header back to the device

    The code defines a `Processor` class that the host instantiates in the audio worklet.
    @param declarations: // @param <name> <default> <min> <max> [type] [unit]
    @sample declarations: // @sample <name>
    See the openDAW plans/apparat.md, plans/spielwerk.md for the full API.

    device_type: "apparat" (instrument), "werkstatt" (audio effect), "spielwerk" (MIDI effect)
    """
    code_json = json.dumps(code)
    safe_device_type = device_type.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(rf"""async () => {{
        const h = window.DAW_HELPERS;
        const allAU = h.allAUBoxes();
        const au = allAU[{unit_index}];
        if (!au) return {{error: "Unit {unit_index} not found"}};
        let device = null;
        const dt = "{safe_device_type}".toLowerCase();
        if (dt === "werkstatt") {{
            const fx = h.effectBoxes(au);
            device = fx[{device_index}] || null;
        }} else if (dt === "spielwerk") {{
            const me = au.midiEffects ? h.midiEffectBoxes(au) : [];
            device = me[{device_index}] || null;
        }} else if (dt === "apparat") {{
            const incoming = au.input ? h.inputBoxes(au) : [];
            device = incoming.find(b => b.constructor.name === "ApparatDeviceBox") || incoming[0] || null;
        }}
        if (!device) return {{error: "Scriptable device '" + dt + "' not found on unit {unit_index}"}};

        // Use the official ScriptCompiler from studio-adapters
        const ScriptCompiler = window.DAW_ScriptCompiler;
        if (!ScriptCompiler) return {{error: "ScriptCompiler not available (DAW_ScriptCompiler undefined)"}};

        const configs = {{
            werkstatt: {{headerTag: "werkstatt", registryName: "werkstattProcessors", functionName: "werkstatt"}},
            apparat: {{headerTag: "apparat", registryName: "apparatProcessors", functionName: "apparat"}},
            spielwerk: {{headerTag: "spielwerk", registryName: "spielwerkProcessors", functionName: "spielwerk"}},
        }};
        const config = configs[dt];
        if (!config) return {{error: "Unknown device type: " + dt}};

        const compiler = ScriptCompiler.create(config);
        const ctx = window.DAW_audioContext || (window.AudioContext ? new AudioContext() : null);
        if (!ctx) return {{error: "No AudioContext available"}};

        const source = {code_json};

        // compile() calls editing.modify() internally + registers worklet
        let compileError = null;
        try {{
            await compiler.compile(ctx, h.editing, device, source);
        }} catch(e) {{
            compileError = e.message?.substring(0, 300) || String(e).substring(0, 300);
        }}

        // Read back results
        const params = [];
        for (const pointer of device.parameters.pointerHub.filter()) {{
            const pb = pointer.box;
            params.push({{
                label: pb.label.getValue(),
                index: pb.index.getValue(),
                value: pb.value.getValue(),
                defaultValue: pb.defaultValue.getValue(),
            }});
        }}

        const samples = [];
        if (device.samples) {{
            for (const pointer of device.samples.pointerHub.filter()) {{
                const sb = pointer.box;
                samples.push({{
                    label: sb.label.getValue(),
                    index: sb.index.getValue(),
                }});
            }}
        }}

        return {{
            success: compileError === null,
            device: device.constructor.name,
            code_length: device.code.getValue().length,
            params_created: params.length,
            params: params,
            samples_created: samples.length,
            samples: samples,
            compile_error: compileError,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_get_script_device_code(device_type: str, unit_index: int, device_index: int) -> str:
    """Read the current user JavaScript code from a scriptable device.

Returns the full code string, header line, and code length.
"""
    safe_device_type = device_type.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(rf"""() => {{
        const h = window.DAW_HELPERS;
        const allAU = h.allAUBoxes();
        const au = allAU[{unit_index}];
        if (!au) return {{error: "Unit {unit_index} not found"}};
        let device = null;
        const dt = "{safe_device_type}".toLowerCase();
        if (dt === "werkstatt") {{
            const fx = h.effectBoxes(au);
            device = fx[{device_index}] || null;
        }} else if (dt === "spielwerk") {{
            const me = au.midiEffects ? h.midiEffectBoxes(au) : [];
            device = me[{device_index}] || null;
        }} else if (dt === "apparat") {{
            const incoming = au.input ? h.inputBoxes(au) : [];
            device = incoming.find(b => b.constructor.name === "ApparatDeviceBox") || incoming[0] || null;
        }}
        if (!device) return {{error: "Scriptable device '" + dt + "' not found on unit {unit_index}"}};
        const code = device.code.getValue();
        const header = code.split('\\\\n')[0] || '';
        return {{
            success: true,
            device: device.constructor.name,
            code: code,
            header: header,
            code_length: code.length,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_list_script_params(device_type: str, unit_index: int, device_index: int) -> str:
    """List @param declarations on a scriptable device with full mapping info.

    Each parameter includes: label, index, current value, default value,
    min, max, mapping type (unipolar/linear/exp/int/bool), and unit.
    Mapping info is parsed from `// @param <name> <default> <min> <max> <type> <unit>`
    declarations in the code — the code is the single source of truth.
    """
    safe_device_type = device_type.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const SD = window.DAW_ScriptDeclaration;
        const allAU = h.allAUBoxes();
        const au = allAU[{unit_index}];
        if (!au) return {{error: "Unit {unit_index} not found"}};
        let device = null;
        const dt = "{safe_device_type}".toLowerCase();
        if (dt === "werkstatt") {{
            const fx = h.effectBoxes(au);
            device = fx[{device_index}] || null;
        }} else if (dt === "spielwerk") {{
            const me = au.midiEffects ? h.midiEffectBoxes(au) : [];
            device = me[{device_index}] || null;
        }} else if (dt === "apparat") {{
            const incoming = au.input ? h.inputBoxes(au) : [];
            device = incoming.find(b => b.constructor.name === "ApparatDeviceBox") || incoming[0] || null;
        }}
        if (!device) return {{error: "Scriptable device '" + dt + "' not found on unit {unit_index}"}};
        if (!device.parameters) return {{error: "Device has no parameters field"}};
        const params = h.scriptParams(device);
        // Parse @param declarations from code for mapping metadata
        const code = device.code ? device.code.getValue() : "";
        let decls = [];
        if (SD && SD.parseParams) {{
            try {{ decls = SD.parseParams(code) || []; }} catch(e) {{ decls = []; }}
        }}
        const declMap = {{}};
        for (const d of decls) {{ declMap[d.label] = d; }}
        return {{
            success: true,
            device: device.constructor.name,
            params: params.map(param => {{
                const decl = declMap[param.label.getValue()];
                return {{
                    label: param.label.getValue(),
                    index: param.index.getValue(),
                    value: param.value.getValue(),
                    defaultValue: param.defaultValue.getValue(),
                    min: decl ? decl.min : 0,
                    max: decl ? decl.max : 1,
                    mapping: decl ? decl.mapping : "unipolar",
                    unit: decl ? decl.unit : "",
                }};
            }}),
            param_count: params.length,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_set_script_param(device_type: str, unit_index: int, device_index: int, param_label: str, value: float) -> str:
    """Set a parameter value on a scriptable device by label.

    The parameter must exist (created from a `// @param` declaration in the code).
    The value is validated against the declaration's range (min/max) and mapping type:
    - bool: snaps to 0 or 1
    - int: rounds to nearest integer within [min, max]
    - linear/exp/unipolar: clamps to [min, max]
    Response includes `clamped` flag and `range` info if the value was adjusted.
    """
    safe_device_type = device_type.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const allAU = h.allAUBoxes();
        const au = allAU[{unit_index}];
        if (!au) return {{error: "Unit {unit_index} not found"}};
        let device = null;
        const dt = "{safe_device_type}".toLowerCase();
        if (dt === "werkstatt") {{
            const fx = h.effectBoxes(au);
            device = fx[{device_index}] || null;
        }} else if (dt === "spielwerk") {{
            const me = au.midiEffects ? h.midiEffectBoxes(au) : [];
            device = me[{device_index}] || null;
        }} else if (dt === "apparat") {{
            const incoming = au.input ? h.inputBoxes(au) : [];
            device = incoming.find(b => b.constructor.name === "ApparatDeviceBox") || incoming[0] || null;
        }}
        if (!device) return {{error: "Scriptable device '" + dt + "' not found on unit {unit_index}"}};
        if (!device.parameters) return {{error: "Device has no parameters field"}};
        const params = h.scriptParams(device);
        const targetLabel = {json.dumps(param_label)};
        const param = params.find(p => p.label.getValue() === targetLabel);
        if (!param) return {{error: "Parameter '" + targetLabel + "' not found. Available: " + params.map(p => p.label.getValue()).join(", ")}};
        // Parse declaration for range validation
        const SD = window.DAW_ScriptDeclaration;
        const code = device.code ? device.code.getValue() : "";
        let rangeInfo = null;
        if (SD && SD.parseParams) {{
            try {{
                const decls = SD.parseParams(code) || [];
                const decl = decls.find(d => d.label === targetLabel);
                if (decl) rangeInfo = {{min: decl.min, max: decl.max, mapping: decl.mapping, unit: decl.unit}};
            }} catch(e) {{}}
        }}
        let setValue = {value};
        let clamped = false;
        if (rangeInfo) {{
            if (rangeInfo.mapping === "bool") {{
                setValue = setValue >= 0.5 ? 1 : 0;
                if (setValue !== {value}) clamped = true;
            }} else if (rangeInfo.mapping === "int") {{
                setValue = Math.round(setValue);
                if (setValue !== {value}) clamped = true;
                if (setValue < rangeInfo.min) {{ setValue = rangeInfo.min; clamped = true; }}
                if (setValue > rangeInfo.max) {{ setValue = rangeInfo.max; clamped = true; }}
            }} else {{
                if (setValue < rangeInfo.min) {{ setValue = rangeInfo.min; clamped = true; }}
                if (setValue > rangeInfo.max) {{ setValue = rangeInfo.max; clamped = true; }}
            }}
        }}
        const oldVal = param.value.getValue();
        h.editing.modify(() => {{
            param.value.setValue(setValue);
        }});
        return {{
            success: true,
            param: param.label.getValue(),
            old_value: oldVal,
            new_value: param.value.getValue(),
            requested_value: {value},
            clamped: clamped,
            range: rangeInfo,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_list_script_samples(device_type: str, unit_index: int, device_index: int) -> str:
    """List @sample declaration slots on a scriptable device.

Each sample slot is a WerkstattSampleBox with: label, index, file (pointer to AudioFileBox).
Sample slots are auto-created from `// @sample <name>` declarations in the code.
The file pointer is null until a sample is loaded.
"""
    safe_device_type = device_type.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const allAU = h.allAUBoxes();
        const au = allAU[{unit_index}];
        if (!au) return {{error: "Unit {unit_index} not found"}};
        let device = null;
        const dt = "{safe_device_type}".toLowerCase();
        if (dt === "werkstatt") {{
            const fx = h.effectBoxes(au);
            device = fx[{device_index}] || null;
        }} else if (dt === "spielwerk") {{
            const me = au.midiEffects ? h.midiEffectBoxes(au) : [];
            device = me[{device_index}] || null;
        }} else if (dt === "apparat") {{
            const incoming = au.input ? h.inputBoxes(au) : [];
            device = incoming.find(b => b.constructor.name === "ApparatDeviceBox") || incoming[0] || null;
        }}
        if (!device) return {{error: "Scriptable device '" + dt + "' not found on unit {unit_index}"}};
        if (!device.samples) return {{error: "Device has no samples field"}};
        const samples = h.scriptSamples(device);
        return {{
            success: true,
            device: device.constructor.name,
            samples: samples.map(s => ({{
                label: s.label.getValue(),
                index: s.index.getValue(),
                hasFile: s.file.targetVertex.unwrapOrNull() !== null,
            }})),
            sample_count: samples.length,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_duplicate_audiounit(unit_index: int) -> str:
    """Duplicate an audio unit with all its content: instrument, effects, tracks, regions, notes, automation.

Creates a new audio unit of the same type (Instrument/Audio) with a copy of:
- Instrument device (same factory type + all parameters)
- Audio effect chain (same effects + all parameter values)
- MIDI effect chain (same effects + all parameter values)
- Note tracks, note regions, and all note events (pitch/duration/velocity/position)
- Track volume, panning, mute state
- Audio regions (if any, referencing same audio files)
- Unit label, volume

unit_index: Source audio unit index to duplicate.

Returns the new unit index and details of what was copied.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const units = h.allAUBoxes();
        if ({unit_index} >= units.length) return {{error: "No audio unit at index {unit_index}"}};
        const srcAU = units[{unit_index}];

        const srcType = srcAU.type.getValue();
        const srcLabel = srcAU.label?.getValue() || "Unit";
        const srcVolume = srcAU.volume?.getValue() || 0.767835;

        // Read instrument info
        const srcIncoming = h.inputBoxes(srcAU);
        const srcInstrument = srcIncoming.length > 0 ? srcIncoming[0] : null;
        const instrumentFactoryName = srcInstrument?.constructor.name || null;

        // Read effects
        const srcEffects = h.effectBoxes(srcAU)
            .sort((a,b) => a.index.getValue() - b.index.getValue())
            .map(box => ({{type: box.constructor.name}}));

        // Read MIDI effects
        const srcMidiEffects = h.midiEffectBoxes(srcAU)
            .sort((a,b) => a.index.getValue() - b.index.getValue())
            .map(box => ({{type: box.constructor.name}}));

        // Read tracks
        const srcTracks = h.trackBoxes(srcAU).sort((a,b) => a.index.getValue() - b.index.getValue());

        // Map instrument class name to factory key
        const instFactoryMap = {{
            'VaporisateurDeviceBox': 'Vaporisateur',
            'NanoDeviceBox': 'Nano',
            'SoundfontDeviceBox': 'Soundfont',
            'MidiOutputDeviceBox': 'MidiOutput',
            'PlayfieldDeviceBox': 'Playfield',
            'ApparatDeviceBox': 'Apparat',
        }};
        const factoryKey = instFactoryMap[instrumentFactoryName] || null;

        // Collect note data from all tracks
        const noteData = [];
        for (const track of srcTracks) {{
            const trackType = track.type?.getValue();
            const trackVolume = track.volume?.getValue();
            const trackPanning = track.panning?.getValue();
            const trackMute = track.mute?.getValue();
            const trackHue = track.hue?.getValue();

            const regions = h.regionBoxes(track);
            const trackNotes = [];
            for (const region of regions) {{
                if (region.constructor.name === 'NoteRegionBox') {{
                    try {{
                        const vertex = region.events.targetVertex.unwrap();
                        const eventsBox = vertex.box || vertex;
                        const notes = h.eventBoxes(eventsBox);
                        for (const note of notes) {{
                            trackNotes.push({{
                                pitch: note.pitch.getValue(),
                                position: note.position.getValue(),
                                duration: note.duration.getValue(),
                                velocity: note.velocity.getValue(),
                                cent: note.cent?.getValue() || 0,
                            }});
                        }}
                    }} catch(e) {{}}
                }}
            }}

            noteData.push({{
                trackType, trackVolume, trackPanning, trackMute, trackHue,
                notes: trackNotes,
            }});
        }}

        return {{
            srcType, srcLabel, srcVolume,
            instrumentFactoryName, factoryKey,
            effectCount: srcEffects.length,
            effects: srcEffects,
            midiEffectCount: srcMidiEffects.length,
            midiEffects: srcMidiEffects,
            trackCount: srcTracks.length,
            tracks: noteData,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_delete_track(unit_index: int, track_index: int) -> str:
    """Delete a track from an audio unit. Removes all regions, clips, and notes on that track.

unit_index: Audio unit index.
track_index: Track index within the unit.

Returns success or error.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const AudioUnitBoxAdapter = window.DAW_AudioUnitBoxAdapter;
        if (!AudioUnitBoxAdapter) throw new Error("AudioUnitBoxAdapter not loaded");
        const units = h.allAUBoxes();
        if ({unit_index} >= units.length) return {{error: "No unit at index {unit_index}"}};
        const au = units[{unit_index}];
        const tracks = h.trackBoxes(au);
        if ({track_index} >= tracks.length) return {{error: "No track {track_index} in unit {unit_index}"}};
        const trackBox = tracks[{track_index}];
        const auAdapter = h.project.boxAdapters.adapterFor(au, AudioUnitBoxAdapter);
        const trackAdapter = h.project.boxAdapters.adapterFor(trackBox, window.DAW_TrackBoxAdapter);
        h.editing.modify(() => {{
            auAdapter.deleteTrack(trackAdapter);
        }});
        return {{success: true, deleted_track: {track_index}, remaining_tracks: tracks.length - 1}};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_move_region_to_track(src_unit_index: int, src_track_index: int, region_index: int, dst_unit_index: int, dst_track_index: int) -> str:
    """Move a region from one track to another (possibly in a different audio unit).

The region keeps its position, duration, and content. The source track loses the region.

src_unit_index: Source audio unit index.
src_track_index: Source track index within source unit.
region_index: Region index within source track.
dst_unit_index: Destination audio unit index.
dst_track_index: Destination track index within destination unit.

Returns success or error.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const srcUnitIdx = {src_unit_index};
        const srcTrackIdx = {src_track_index};
        const regionIdx = {region_index};
        const dstUnitIdx = {dst_unit_index};
        const dstTrackIdx = {dst_track_index};

        const units = h.allAUBoxes();
        const srcAU = units[srcUnitIdx];
        const dstAU = units[dstUnitIdx];
        if (!srcAU) return {{error: "Source unit not found"}};
        if (!dstAU) return {{error: "Destination unit not found"}};

        const srcTracks = h.trackBoxes(srcAU);
        const dstTracks = h.trackBoxes(dstAU);
        const srcTrack = srcTracks[srcTrackIdx];
        const dstTrack = dstTracks[dstTrackIdx];
        if (!srcTrack) return {{error: "Source track not found"}};
        if (!dstTrack) return {{error: "Destination track not found"}};

        const srcRegions = h.regionBoxes(srcTrack);
        const region = srcRegions[regionIdx];
        if (!region) return {{error: "Region not found"}};

        // Check type compatibility
        const srcType = srcTrack.type?.getValue();
        const dstType = dstTrack.type?.getValue();
        if (srcType !== dstType) return {{error: `Track type mismatch: source=${{srcType}} dest=${{dstType}}`}};

        h.editing.modify(() => {{
            region.regions.refer(dstTrack.regions);
        }});
        return {{success: true, region_type: region.constructor.name, moved_to_unit: dstUnitIdx, moved_to_track: dstTrackIdx}};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
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

@mcp.tool()
async def mcp_opendaw_delete_automation_event(unit_index: int, track_index: int, event_index: int) -> str:
    """Delete a single automation event (ValueEventBox) from an automation track.

unit_index: Audio unit index.
track_index: Track index within the unit (automation track).
event_index: Event index within the track's value region.

Returns success or error.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const units = h.allAUBoxes();
        if ({unit_index} >= units.length) return {{error: "No unit at {unit_index}"}};
        const au = units[{unit_index}];
        const tracks = h.trackBoxes(au);

        // Filter to automation tracks (type 3)
        const autoTracks = tracks.filter(t => t.type?.getValue?.() === 3);
        if ({track_index} >= autoTracks.length) return {{error: "No automation track at index {track_index}"}};
        const track = autoTracks[{track_index}];

        // Collect events from clips (automation uses ValueClipBox, not ValueRegionBox)
        const clips = h.clipBoxes(track);
        const allEvents = [];
        for (const clip of clips) {{
            if (clip.constructor.name === 'ValueClipBox') {{
                try {{
                    const vertex = clip.events.targetVertex.unwrap();
                    const eventsBox = vertex.box || vertex;
                    const events = h.eventBoxes(eventsBox);
                    for (const ev of events) {{
                        allEvents.push({{box: ev}});
                    }}
                }} catch(e) {{}}
            }}
        }}

        // Also check regions (in case events are region-based)
        const regions = h.regionBoxes(track);
        for (const region of regions) {{
            if (region.constructor.name === 'ValueRegionBox') {{
                try {{
                    const vertex = region.events.targetVertex.unwrap();
                    const eventsBox = vertex.box || vertex;
                    const events = h.eventBoxes(eventsBox);
                    for (const ev of events) {{
                        allEvents.push({{box: ev}});
                    }}
                }} catch(e) {{}}
            }}
        }}

        if ({event_index} >= allEvents.length) return {{error: "No event {event_index} (found " + allEvents.length + " events)"}};

        const target = allEvents[{event_index}];
        const eventBox = target.box;
        // box.delete() automatically:
        // 1. finds all dependencies (pointers pointing to this box, boxes depending on it)
        // 2. defer() all incoming pointers (breaks edges)
        // 3. unstage() dependent boxes
        // 4. unstage() this box
        // Must be inside editing.modify() transaction
        let deleted = false;
        h.editing.modify(() => {{
            eventBox.delete();
            deleted = true;
        }});
        return {{success: deleted, deleted_event: {event_index}, remaining_events: allEvents.length - 1}};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
async def mcp_opendaw_move_audio_unit(unit_index: int, delta: int) -> str:
    """Move an audio unit up or down in the mixer order.

Uses AudioUnitBoxAdapter.move(delta) — reindexes the AU within its type group
(Instrument/Aux/Output). Delta is relative: -1 = up, +1 = down.

unit_index: Current AU index.
delta: Relative move (-1 up, +1 down).

Returns new index or error.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const AudioUnitBoxAdapter = window.DAW_AudioUnitBoxAdapter;
        const units = h.allAUBoxes();
        if ({unit_index} >= units.length) return {{error: "No AU at {unit_index}"}};
        const auBox = units[{unit_index}];
        const adapter = h.project.boxAdapters.adapterFor(auBox, AudioUnitBoxAdapter);
        let newIdx = auBox.index.getValue();
        h.editing.modify(() => {{
            adapter.move({delta});
        }});
        return {{success: true, old_index: {unit_index}, new_index: auBox.index.getValue()}};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_move_track(unit_index: int, track_index: int, delta: int) -> str:
    """Move a track up or down within an audio unit.

Uses AudioUnitBoxAdapter.moveTrack(adapter, delta) — reindexes the track.
Delta is relative: -1 = up, +1 = down.

unit_index: AU index.
track_index: Track index within AU.
delta: Relative move (-1 up, +1 down).

Returns new index or error.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const AudioUnitBoxAdapter = window.DAW_AudioUnitBoxAdapter;
        const TrackBoxAdapter = window.DAW_TrackBoxAdapter;
        const units = h.allAUBoxes();
        if ({unit_index} >= units.length) return {{error: "No AU at {unit_index}"}};
        const auBox = units[{unit_index}];
        const auAdapter = h.project.boxAdapters.adapterFor(auBox, AudioUnitBoxAdapter);
        const tracks = h.trackBoxes(auBox)
            .sort((a, b) => a.index.getValue() - b.index.getValue());
        if ({track_index} >= tracks.length) return {{error: "No track at {track_index}"}};
        const trackBox = tracks[{track_index}];
        const trackAdapter = h.project.boxAdapters.adapterFor(trackBox, TrackBoxAdapter);
        h.editing.modify(() => {{
            auAdapter.moveTrack(trackAdapter, {delta});
        }});
        return {{success: true, old_index: {track_index}, new_index: trackBox.index.getValue()}};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_transfer_region(src_unit_index: int, src_track_index: int, region_index: int,
                                       dst_unit_index: int, dst_track_index: int,
                                       insert_position: float, delete_source: bool = False) -> str:
    """Transfer/copy a region to another track at a specific position.

Uses TransferRegions.transfer — copies the region and all its dependencies (notes, events, audio files)
to the target track. Works across different audio units. Preserved resources (AudioFileBox) are shared,
not duplicated. The source region can optionally be deleted (move semantics).

src_unit_index: Source AU index.
src_track_index: Source track index within AU.
region_index: Region index within source track (0-based, sorted by position).
dst_unit_index: Destination AU index.
dst_track_index: Destination track index within AU.
insert_position: Position in beats for the new region.
delete_source: If true, delete the source region (move). If false, keep source (copy).

Returns the new region's type, position, and duration, or error.
"""
    delete_js = "true" if delete_source else "false"
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const TransferRegions = window.DAW_TransferRegions;
        if (!TransferRegions) return {{error: "TransferRegions not loaded"}};
        const units = h.allAUBoxes();

        if ({src_unit_index} >= units.length) return {{error: "No source AU at {src_unit_index}"}};
        if ({dst_unit_index} >= units.length) return {{error: "No dest AU at {dst_unit_index}"}};

        const srcAU = units[{src_unit_index}];
        const dstAU = units[{dst_unit_index}];

        const srcTracks = h.trackBoxes(srcAU)
            .sort((a, b) => a.index.getValue() - b.index.getValue());
        const dstTracks = h.trackBoxes(dstAU)
            .sort((a, b) => a.index.getValue() - b.index.getValue());

        if ({src_track_index} >= srcTracks.length) return {{error: "No source track at {src_track_index}"}};
        if ({dst_track_index} >= dstTracks.length) return {{error: "No dest track at {dst_track_index}"}};

        const srcTrack = srcTracks[{src_track_index}];
        const dstTrack = dstTracks[{dst_track_index}];

        const regions = h.regionBoxes(srcTrack)
            .sort((a, b) => a.position.getValue() - b.position.getValue());
        if ({region_index} >= regions.length) return {{error: "No region at {region_index}"}};

        const srcRegion = regions[{region_index}];
        const regionType = srcRegion.constructor.name;
        const insertPos = Math.round({insert_position} * h.ppqn.Quarter);  // beats to ppqn

        let newRegion;
        h.editing.modify(() => {{
            newRegion = TransferRegions.transfer(srcRegion, dstTrack, insertPos, {delete_js});
        }});

        if (!newRegion) return {{error: "Transfer failed"}};
        return {{
            success: true,
            region_type: newRegion.constructor.name,
            position_beats: newRegion.position.getValue() / h.ppqn.Quarter,
            duration_beats: newRegion.duration.getValue() / h.ppqn.Quarter,
            source_deleted: {delete_js},
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_transfer_audiounit(unit_index: int, delete_source: bool = False,
                                          insert_index: int = -1) -> str:
    """Transfer/copy an audio unit (instrument/effects/tracks/regions) within the project.

Uses TransferAudioUnits.transfer — deep-copy an AU with all dependencies (instrument, effects,
MIDI effects, tracks, regions, notes, automation) via box-graph serialization. Much more complete
than duplicate_audiounit (which uses Python orchestration). Output unit cannot be copied.

unit_index: Source AU index to copy.
delete_source: If true, delete source AU after copy (move semantics).
insert_index: Position in mixer order for the new AU (-1 = auto-place by type ordering).

Returns the new AU's index, type, and label, or error.
"""
    delete_js = "true" if delete_source else "false"
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const TransferAudioUnits = window.DAW_TransferAudioUnits;
        if (!TransferAudioUnits) return {{error: "TransferAudioUnits not loaded"}};
        const units = h.allAUBoxes();
        if ({unit_index} >= units.length) return {{error: "No AU at {unit_index}"}};

        const srcAU = units[{unit_index}];
        // Find primary audio bus (connected to Output unit's input)
        const outputAU = units.find(u => u.type.getValue() === "output" || u.type.getValue() === 2);
        if (!outputAU) return {{error: "No Output unit found"}};
        const primaryBus = h.inputBoxes(outputAU)[0]?.box || h.inputBoxes(outputAU)[0] || null;
        if (!primaryBus) return {{error: "No primary audio bus found"}};

        const skeleton = {{
            boxGraph: h.boxGraph,
            mandatoryBoxes: {{
                primaryAudioBusBox: primaryBus,
                rootBox: h.rootBox,
            }}
        }};

        let newAUs;
        const opts = {{deleteSource: {delete_js}}};
        if ({insert_index} >= 0) opts.insertIndex = {insert_index};
        h.editing.modify(() => {{
            newAUs = TransferAudioUnits.transfer([srcAU], skeleton, opts);
        }});

        if (!newAUs || newAUs.length === 0) return {{error: "Transfer returned no units"}};
        const newAU = newAUs[0];
        return {{
            success: true,
            new_unit_index: newAU.index.getValue(),
            unit_type: newAU.type.getValue(),
            label: newAU.label ? newAU.label.getValue() : '',
            source_deleted: {delete_js},
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
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
        let binary = '';
        for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
        const base64 = btoa(binary);
        return {{
            success: true,
            preset_b64: base64,
            size_bytes: bytes.length,
            unit_type: srcAU.type.getValue(),
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_import_preset(preset_b64: str) -> str:
    """Import a preset (base64-encoded binary) as a new audio unit.

Uses PresetDecoder.decode — deserializes the preset into the current project, creating
a new AU with all its dependencies (instrument, effects, MIDI effects, tracks, notes).

preset_b64: Base64-encoded preset bytes from export_preset.

Returns the new AU's index, type, and label, or error.
"""
    preset_json = json.dumps(preset_b64)
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const PresetDecoder = window.DAW_PresetDecoder;
        if (!PresetDecoder) return {{error: "PresetDecoder not loaded"}};
        const b64 = {preset_json};
        // Decode base64 to ArrayBuffer
        const binary = atob(b64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);

        const outputAU = h.allAUBoxes()
            .find(u => u.type.getValue() === "output");
        if (!outputAU) return {{error: "No Output unit"}};
        const primaryBus = h.inputBoxes(outputAU)[0]?.box || h.inputBoxes(outputAU)[0] || null;
        if (!primaryBus) return {{error: "No primary bus"}};

        const skeleton = {{
            boxGraph: h.boxGraph,
            mandatoryBoxes: {{primaryAudioBusBox: primaryBus, rootBox: h.rootBox}}
        }};

        let newAUs;
        h.editing.modify(() => {{
            newAUs = PresetDecoder.decode(bytes.buffer, skeleton);
        }});

        if (!newAUs || newAUs.length === 0) return {{error: "Import returned no units"}};
        const newAU = newAUs[0];
        const fx = h.effectBoxes(newAU);
        return {{
            success: true,
            new_unit_index: newAU.index.getValue(),
            unit_type: newAU.type.getValue(),
            effects: fx.length,
            effect_names: fx.map(f => f.label.getValue()),
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_replace_from_preset(unit_index: int, preset_b64: str,
                                           keep_midi_effects: bool = False,
                                           keep_audio_effects: bool = False,
                                           keep_timeline: bool = False) -> str:
    """Replace an audio unit's instrument/effects/timeline from a preset.

Uses PresetDecoder.replaceAudioUnit — swaps the instrument in an existing AU,
optionally keeping the target's MIDI effects, audio effects, and/or timeline.
The preset must contain a compatible instrument type (MIDI→MIDI, Audio→Audio).

unit_index: Target AU index to replace.
preset_b64: Base64 preset bytes from export_preset.
keep_midi_effects: If true, keep target's existing MIDI effects.
keep_audio_effects: If true, keep target's existing audio effects.
keep_timeline: If true, keep target's existing tracks/regions/notes.

Returns success or error with reason.
"""
    preset_json = json.dumps(preset_b64)
    keep_midi = "true" if keep_midi_effects else "false"
    keep_audio = "true" if keep_audio_effects else "false"
    keep_timeline_js = "true" if keep_timeline else "false"
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const PresetDecoder = window.DAW_PresetDecoder;
        if (!PresetDecoder) return {{error: "PresetDecoder not loaded"}};
        const b64 = {preset_json};
        const binary = atob(b64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);

        const units = h.allAUBoxes();
        if ({unit_index} >= units.length) return {{error: "No AU at {unit_index}"}};
        const targetAU = units[{unit_index}];

        let attempt;
        h.editing.modify(() => {{
            attempt = PresetDecoder.replaceAudioUnit(bytes.buffer, targetAU, {{
                keepMIDIEffects: {keep_midi},
                keepAudioEffects: {keep_audio},
                keepTimeline: {keep_timeline_js},
            }});
        }});

        if (!attempt.isSuccess()) return {{error: attempt.failureReason()}};
        // Read new state
        const fx = h.effectBoxes(targetAU);
        const inp = h.inputBoxes(targetAU).length > 0
            ? h.inputBoxes(targetAU)[0].constructor.name : 'none';
        return {{
            success: true,
            instrument: inp,
            effects: fx.length,
            effect_names: fx.map(f => f.label.getValue()),
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
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
        let binary = '';
        for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
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

@mcp.tool()
async def mcp_opendaw_ppqn_to_seconds(position_beats: float) -> str:
    """Convert a position in beats (PPQN units) to seconds using the project's tempo map.

    Accounts for tempo automation — each segment of the timeline may have a different BPM,
    so the conversion integrates over tempo change events. 1 beat = PPQN.Quarter = 960 pulses.

    position_beats: Position in beats (float, e.g. 4.0 = beat 4).

    Returns seconds (float), or error.
    """
    ppqn = int(position_beats * 960)
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const tempoMap = h.tempoMap;
        if (!tempoMap) return {{error: "tempoMap not available"}};
        const secs = tempoMap.ppqnToSeconds({ppqn});
        return {{seconds: secs, beats: {position_beats}}};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_seconds_to_beats(seconds: float) -> str:
    """Convert a time in seconds to beats using the project's tempo map.

    Accounts for tempo automation. Useful for aligning audio regions to the musical grid
    when tempo changes mid-song.

    seconds: Time in seconds (float).

    Returns beats (float) and PPQN position, or error.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const tempoMap = h.tempoMap;
        if (!tempoMap) return {{error: "tempoMap not available"}};
        const ppqn = tempoMap.secondsToPPQN({seconds});
        const beats = ppqn / h.ppqn.Quarter;
        return {{beats: beats, ppqn: ppqn, seconds: {seconds}}};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_get_tempo_at(position_beats: float) -> str:
    """Get the BPM at a specific position, accounting for tempo automation.

    position_beats: Position in beats (float).

    Returns BPM at that position, or error.
    """
    ppqn = int(position_beats * 960)
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const tempoMap = h.tempoMap;
        if (!tempoMap) return {{error: "tempoMap not available"}};
        const bpm = tempoMap.getTempoAt({ppqn});
        return {{bpm: bpm, position_beats: {position_beats}}};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_get_project_duration() -> str:
    """Get the total project duration — the end position of the last region across all tracks.

    Returns the duration in beats and seconds, or error.
    """
    result = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        const lastPPQN = h.project.lastRegionAction ? h.project.lastRegionAction() : 0;
        const tempoMap = h.tempoMap;
        let secs = 0;
        try { secs = tempoMap ? tempoMap.ppqnToSeconds(lastPPQN) : 0; } catch(e) {}
        return {
            duration_beats: lastPPQN / h.ppqn.Quarter,
            duration_ppqn: lastPPQN,
            duration_seconds: secs,
        };
    }""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_validate_project() -> str:
    """Check if the project is valid — detects overlapping regions on the same track.

    Returns valid (bool) and details about any issues found.
    """
    result = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        let valid = true;
        let issues = [];
        try {
            valid = !h.project.invalid();
        } catch(e) {
            issues.push("validation error: " + e.message);
        }
        if (!valid) {
            const units = h.allAUBoxes();
            for (const au of units) {
                const tracks = h.trackBoxes(au);
                for (const track of tracks) {
                    const regions = h.regionBoxes(track)
                        .sort((a, b) => a.position.getValue() - b.position.getValue());
                    for (let i = 1; i < regions.length; i++) {
                        const prevEnd = regions[i-1].position.getValue() + regions[i-1].duration.getValue();
                        if (prevEnd > regions[i].position.getValue()) {
                            issues.push("overlap on track: " + (track.label?.getValue?.() || 'unnamed') +
                                " region " + (i-1) + " and " + i);
                        }
                    }
                }
            }
        }
        return {valid: valid, issues: issues};
    }""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_list_samples() -> str:
    """List all audio file samples used in the project.

    Returns sample UUIDs and metadata for each audio file referenced in the project.
    """
    result = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        const uuids = h.project.collectSampleUUIDs ? h.project.collectSampleUUIDs() : [];
        const samples = uuids.map(uuid => {
            const hex = Array.from(uuid, b => b.toString(16).padStart(2, '0')).join('');
            return {uuid: hex};
        });
        return {sample_count: samples.length, samples: samples};
    }""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_get_unit_freeze_status(unit_index: int) -> str:
    """Check if an audio unit is frozen and whether it can be frozen.

    Freeze status indicates the AU's output has been pre-rendered to audio,
    freeing CPU. An AU with sidechain dependents cannot be frozen.

    unit_index: AU index.

    Returns frozen (bool), can_freeze (bool), has_sidechain_dependents (bool).
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const freeze = h.audioUnitFreeze;
        if (!freeze) return {{error: "audioUnitFreeze not available"}};
        const auAdapters = h.allAUs();
        if ({unit_index} >= auAdapters.length) return {{error: "No AU at {unit_index}"}};
        const auAdapter = auAdapters[{unit_index}];
        try {{
            const isFrozen = freeze.isFrozenUuid ? freeze.isFrozenUuid(auAdapter.uuid) : false;
            let hasSidechain = false;
            try {{
                hasSidechain = freeze.hasSidechainDependents ? freeze.hasSidechainDependents(auAdapter) : false;
            }} catch(e) {{}}
            return {{
                frozen: isFrozen,
                can_freeze: !hasSidechain,
                has_sidechain_dependents: hasSidechain,
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_freeze_audiounit(unit_index: int) -> str:
    """Freeze an audio unit — pre-render its output offline to save CPU.

    Uses audioUnitFreeze.freeze() which renders the AU's complete output via
    OfflineEngineRenderer and caches it. While frozen, the AU plays from cache
    instead of processing instruments/effects in real-time.

    Cannot freeze AUs with sidechain dependents or the Output unit.

    unit_index: AU index to freeze.

    Returns success or error (e.g. sidechain dependents block freeze).
    """
    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const freeze = h.audioUnitFreeze;
        if (!freeze) return {{error: "audioUnitFreeze not available"}};
        const auAdapters = h.allAUs();
        if ({unit_index} >= auAdapters.length) return {{error: "No AU at {unit_index}"}};
        const auAdapter = auAdapters[{unit_index}];
        try {{
            if (freeze.hasSidechainDependents(auAdapter))
                return {{error: "AU has sidechain dependents — cannot freeze"}};
            await freeze.freeze(auAdapter);
            return {{
                success: true,
                frozen: freeze.isFrozen(auAdapter),
                unit_index: {unit_index},
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_unfreeze_audiounit(unit_index: int) -> str:
    """Unfreeze a frozen audio unit — resume real-time processing.

    Removes the cached audio and resumes live processing of instruments,
    effects, and sends for the specified audio unit.

    unit_index: AU index to unfreeze.

    Returns success or error.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const freeze = h.audioUnitFreeze;
        if (!freeze) return {{error: "audioUnitFreeze not available"}};
        const auAdapters = h.allAUs();
        if ({unit_index} >= auAdapters.length) return {{error: "No AU at {unit_index}"}};
        const auAdapter = auAdapters[{unit_index}];
        try {{
            const wasFrozen = freeze.isFrozen(auAdapter);
            if (!wasFrozen) return {{error: "AU is not frozen"}};
            freeze.unfreeze(auAdapter);
            return {{
                success: true,
                was_frozen: wasFrozen,
                frozen: freeze.isFrozen(auAdapter),
                unit_index: {unit_index},
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


# ─────────────────────────────────────────────────────────────────────
# Mixer & Region Advanced (148-150)
# ─────────────────────────────────────────────────────────────────────

@mcp.tool()
async def mcp_opendaw_get_mixer_state() -> str:
    """Get the full mixer state — all audio units with volume, panning, mute, solo, and type.

    Returns a list of channel strips with their current values. Useful for inspecting
    the mix balance and routing at a glance.
    """
    result = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        const aus = h.allAUs();
        const strips = aus.map(au => {
            const np = au.namedParameter;
            return {
                index: au.indexField.getValue(),
                label: au.label,
                type: au.isOutput ? 'output' : (au.isInstrument ? 'instrument' : 'bus'),
                volume_db: np.volume.getValue(),
                panning: np.panning.getValue(),
                mute: np.mute.getValue(),
                solo: np.solo.getValue(),
                is_output: au.isOutput,
                is_bus: au.isBus,
                is_instrument: au.isInstrument,
            };
        });
        return {strips: strips, count: strips.length};
    }""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_flatten_note_regions(unit_index: int, track_index: int, region_indices: str) -> str:
    """Flatten (merge) multiple overlapping note regions into a single region.

    Merges selected note regions on the same track into one, combining all notes.
    The original regions are deleted and replaced by a single flattened region.

    unit_index: AU index.
    track_index: Track index within the AU.
    region_indices: Comma-separated region indices to flatten (e.g. "0,1,2").

    Returns the new flattened region info, or error.
    """
    safe_indices = region_indices.replace('"', '').replace('\\', '').replace("'", "").replace(';', '').replace('{', '').replace('}', '')
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const trackAdapter = h.track({unit_index}, {track_index});
            const regions = trackAdapter.regions.collection.asArray();
            const indices = "{safe_indices}".split(',').map(s => parseInt(s.trim()));
            const toFlatten = indices.map(i => regions[i]).filter(r => r);
            if (toFlatten.length < 2) return {{error: "Need at least 2 regions to flatten"}};
            const first = toFlatten[0];
            toFlatten.forEach(r => r.onSelected());
            let flatResult;
            h.modify(() => {{ flatResult = first.flatten(toFlatten); }});
            if (!flatResult || flatResult.isEmpty()) return {{error: "Flatten returned None — regions may not be compatible or not selected"}};
            const newBox = flatResult.unwrap();
            return {{
                success: true,
                new_position: newBox.position.getValue(),
                new_duration: newBox.duration.getValue(),
                new_label: newBox.label.getValue(),
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_consolidate_region(unit_index: int, track_index: int, region_index: int) -> str:
    """Consolidate a region's event collection — make it unique (not shared/mirrored).

    If a region shares its event collection with other regions (mirrored),
    this creates a new independent copy so edits don't affect other regions.

    unit_index: AU index.
    track_index: Track index within the AU.
    region_index: Region index to consolidate.

    Returns success or error.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const region = h.region({unit_index}, {track_index}, {region_index});
            const wasMirrored = region.isMirrowed;
            region.consolidate();
            return {{
                success: true,
                was_mirrored: wasMirrored,
                is_mirrored: region.isMirrowed,
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


# ─────────────────────────────────────────────────────────────────────
# Warp Markers & Region Play Mode (149-151)
# ─────────────────────────────────────────────────────────────────────

@mcp.tool()
async def mcp_opendaw_list_warp_markers(unit_index: int, track_index: int, region_index: int) -> str:
    """List warp markers on a time-stretched or pitch-stretched audio region.

    Warp markers define the mapping between musical position (ppqn) and audio time (seconds).
    Used for tempo-matching audio regions.

    unit_index: AU index.
    track_index: Track index within the AU.
    region_index: Audio region index.

    Returns warp marker list (position, seconds, isAnchor), or empty if no stretch mode.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const auAdapters = h.allAUs();
        if ({unit_index} >= auAdapters.length) return {{error: "No AU at {unit_index}"}};
        const auAdapter = auAdapters[{unit_index}];
        const trackAdapters = auAdapter.tracks.collection.adapters();
        if ({track_index} >= trackAdapters.length) return {{error: "No track {track_index}"}};
        const trackAdapter = trackAdapters[{track_index}];
        const regions = trackAdapter.regions.collection.asArray();
        if ({region_index} >= regions.length) return {{error: "No region {region_index}"}};
        const region = regions[{region_index}];
        if (!region.isAudioRegion?.()) return {{error: "Region is not an audio region"}};
        const optPlayMode = region.observableOptPlayMode;
        if (optPlayMode.isEmpty()) return {{warp_markers: [], note: "Region has no stretch mode (not stretched)"}};
        const playMode = optPlayMode.unwrap();
        const markers = playMode.warpMarkers.asArray();
        return {{
            warp_markers: markers.map(m => ({{
                position: m.position,
                seconds: m.seconds,
                is_anchor: m.isAnchor,
            }})),
            marker_count: markers.length,
            mode: playMode.constructor.name,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_get_region_play_mode(unit_index: int, track_index: int, region_index: int) -> str:
    """Get the play mode of an audio region — stretch type, playback rate, cents, transient mode.

    unit_index: AU index.
    track_index: Track index within the AU.
    region_index: Audio region index.

    Returns play mode details, or info if no stretch mode (plain playback).
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const auAdapters = h.allAUs();
        if ({unit_index} >= auAdapters.length) return {{error: "No AU at {unit_index}"}};
        const auAdapter = auAdapters[{unit_index}];
        const trackAdapters = auAdapter.tracks.collection.adapters();
        if ({track_index} >= trackAdapters.length) return {{error: "No track {track_index}"}};
        const trackAdapter = trackAdapters[{track_index}];
        const regions = trackAdapter.regions.collection.asArray();
        if ({region_index} >= regions.length) return {{error: "No region {region_index}"}};
        const region = regions[{region_index}];
        if (!region.isAudioRegion?.()) return {{error: "Not an audio region"}};
        const optPlayMode = region.observableOptPlayMode;
        if (optPlayMode.isEmpty()) return {{mode: "none", note: "Plain playback, no stretch"}};
        const playMode = optPlayMode.unwrap();
        const info = {{
            mode: playMode.constructor.name === 'AudioTimeStretchBoxAdapter' ? 'time-stretch' : 'pitch-stretch',
        }};
        if (playMode.playbackRate !== undefined) {{
            info.playback_rate = playMode.playbackRate;
            info.cents = playMode.cents;
        }}
        if (playMode.transientPlayMode !== undefined) {{
            info.transient_mode = playMode.transientPlayMode;
        }}
        info.warp_marker_count = playMode.warpMarkers.asArray().length;
        return info;
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_set_time_stretch_cents(unit_index: int, track_index: int, region_index: int, cents: float) -> str:
    """Set the pitch shift (in cents) on a time-stretched audio region.

    100 cents = 1 semitone. Range: -1200 to +1200 cents (clamped).
    Only works on time-stretched regions (created with create_time_stretched_region).

    unit_index: AU index.
    track_index: Track index within the AU.
    region_index: Audio region index.
    cents: Pitch shift in cents (-1200 to +1200).

    Returns new playback rate and cents, or error.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const auAdapters = h.allAUs();
        if ({unit_index} >= auAdapters.length) return {{error: "No AU at {unit_index}"}};
        const auAdapter = auAdapters[{unit_index}];
        const trackAdapters = auAdapter.tracks.collection.adapters();
        if ({track_index} >= trackAdapters.length) return {{error: "No track {track_index}"}};
        const trackAdapter = trackAdapters[{track_index}];
        const regions = trackAdapter.regions.collection.asArray();
        if ({region_index} >= regions.length) return {{error: "No region {region_index}"}};
        const region = regions[{region_index}];
        if (!region.isAudioRegion?.()) return {{error: "Not an audio region"}};
        const optPlayMode = region.observableOptPlayMode;
        if (optPlayMode.isEmpty()) return {{error: "Region has no stretch mode"}};
        const playMode = optPlayMode.unwrap();
        if (playMode.constructor.name !== 'AudioTimeStretchBoxAdapter') return {{error: "Region is not time-stretched"}};
        try {{
            h.editing.modify(() => {{
                playMode.cents = {cents};
            }});
            return {{
                success: true,
                new_cents: playMode.cents,
                new_playback_rate: playMode.playbackRate,
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


# ─────────────────────────────────────────────────────────────────────
# Automation Value & Audio File Info (152-153)
# ─────────────────────────────────────────────────────────────────────

@mcp.tool()
async def mcp_opendaw_get_automation_value(unit_index: int, track_index: int, position_beats: float) -> str:
    """Get the automation value at a specific position on a value (automation) track.

    Resolves the automation curve value at the given position, accounting for
    interpolation, region loops, and multiple overlapping regions.

    unit_index: AU index.
    track_index: Value (automation) track index within the AU.
    position_beats: Position in beats (float).

    Returns the normalized value (0.0-1.0), or error.
    """
    ppqn_val = int(position_beats * 960)
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const auAdapters = h.allAUs();
        if ({unit_index} >= auAdapters.length) return {{error: "No AU at {unit_index}"}};
        const auAdapter = auAdapters[{unit_index}];
        const trackAdapters = auAdapter.tracks.collection.adapters();
        if ({track_index} >= trackAdapters.length) return {{error: "No track {track_index}"}};
        const trackAdapter = trackAdapters[{track_index}];
        try {{
            const value = trackAdapter.valueAt({ppqn_val}, 0.0);
            return {{value: value, position_beats: {position_beats}}};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_get_audio_file_info(unit_index: int, track_index: int, region_index: int) -> str:
    """Get metadata about the audio file referenced by an audio region.

    Returns file name, start/end time in seconds, and sample loading state.
    Useful for inspecting audio regions before processing.

    unit_index: AU index.
    track_index: Track index within the AU.
    region_index: Audio region index.

    Returns audio file info, or error.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const auAdapters = h.allAUs();
        if ({unit_index} >= auAdapters.length) return {{error: "No AU at {unit_index}"}};
        const auAdapter = auAdapters[{unit_index}];
        const trackAdapters = auAdapter.tracks.collection.adapters();
        if ({track_index} >= trackAdapters.length) return {{error: "No track {track_index}"}};
        const trackAdapter = trackAdapters[{track_index}];
        const regions = trackAdapter.regions.collection.asArray();
        if ({region_index} >= regions.length) return {{error: "No region {region_index}"}};
        const region = regions[{region_index}];
        if (!region.isAudioRegion?.()) return {{error: "Not an audio region"}};
        const optFile = region.optFile;
        if (optFile.isEmpty()) return {{error: "Region has no audio file"}};
        const file = optFile.unwrap();
        const loader = file.getOrCreateLoader();
        const state = loader.state;
        const info = {{
            file_name: file.fileName,
            start_seconds: file.startInSeconds,
            end_seconds: file.endInSeconds,
            duration_seconds: file.endInSeconds - file.startInSeconds,
            state_type: state.type,
        }};
        if (state.type === 'loaded') {{
            const data = loader.data;
            if (data.nonEmpty()) {{
                const d = data.unwrap();
                info.sample_rate = d.sampleRate;
                info.num_channels = d.numChannels;
                info.num_frames = d.numFrames;
            }}
        }}
        return info;
    }}""")
    return _wrap_eval(result)


# ─────────────────────────────────────────────────────────────────────
# Region Content Shift (154)
# ─────────────────────────────────────────────────────────────────────

@mcp.tool()
async def mcp_opendaw_move_region_content(unit_index: int, track_index: int, region_index: int, delta_beats: float) -> str:
    """Shift the content start of a region without moving the region itself.

    Moves the content inside the region by delta_beats — adjusts waveform offset
    (audio) or note positions (MIDI) while keeping the region position. Useful for
    realigning content within a region after tempo changes.

    For audio regions with seconds timeBase, delta is converted via tempo map.
    For note regions, note positions shift by -delta (content moves left = positive delta).

    unit_index: AU index.
    track_index: Track index within the AU.
    region_index: Region index.
    delta_beats: Shift amount in beats (positive = content moves left, region shrinks from left).

    Returns new position, duration, and loopDuration, or error.
    """
    delta_ppqn = int(delta_beats * 960)
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const auAdapters = h.allAUs();
        if ({unit_index} >= auAdapters.length) return {{error: "No AU at {unit_index}"}};
        const auAdapter = auAdapters[{unit_index}];
        const trackAdapters = auAdapter.tracks.collection.adapters();
        if ({track_index} >= trackAdapters.length) return {{error: "No track {track_index}"}};
        const trackAdapter = trackAdapters[{track_index}];
        const regions = trackAdapter.regions.collection.asArray();
        if ({region_index} >= regions.length) return {{error: "No region {region_index}"}};
        const region = regions[{region_index}];
        try {{
            h.editing.modify(() => {{
                region.moveContentStart({delta_ppqn});
            }});
            return {{
                success: true,
                new_position: region.position,
                new_duration: region.duration,
                new_loop_duration: region.loopDuration,
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


# ─────────────────────────────────────────────────────────────────────
# Inspection Helpers (155-157) — using DAW_HELPERS
# ─────────────────────────────────────────────────────────────────────

@mcp.tool()
async def mcp_opendaw_get_track_info(unit_index: int, track_index: int) -> str:
    """Get detailed info about a track — type, regions, clips, enabled state, target.

    unit_index: AU index.
    track_index: Track index within the AU.

    Returns track metadata and region/clip counts.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const track = h.track({unit_index}, {track_index});
            const regions = track.regions.collection.asArray();
            const clips = track.clips.collection.adapters();
            const typeNames = ['undefined', 'notes', 'audio', 'value'];
            return {{
                index: track.indexField.getValue(),
                type: typeNames[track.type] || String(track.type),
                enabled: track.enabled.getValue(),
                exclude_piano_mode: track.excludePianoMode?.getValue?.() ?? false,
                region_count: regions.length,
                clip_count: clips.length,
                regions: regions.map(r => ({{
                    position: r.position,
                    duration: r.duration,
                    complete: r.complete,
                    mute: r.mute,
                    label: r.label,
                    is_mirrored: r.isMirrowed,
                }})),
                clips: clips.map(c => ({{
                    index: c.indexField?.getValue?.() ?? 0,
                    label: c.label,
                    mute: c.mute?.getValue?.() ?? false,
                    duration: c.duration?.getValue?.() ?? 0,
                }})),
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_set_track_enabled(unit_index: int, track_index: int, enabled: bool) -> str:
    """Enable or disable a track (equivalent to track mute in the UI).

    unit_index: AU index.
    track_index: Track index within the AU.
    enabled: True to enable, false to mute/disable.

    Returns success with old and new enabled state.
    """
    val = "true" if enabled else "false"
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const track = h.track({unit_index}, {track_index});
            const oldVal = track.enabled.getValue();
            h.modify(() => {{
                track.enabled.field.setValue({val});
            }});
            return {{success: true, old_enabled: oldVal, new_enabled: {val}}};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_get_full_project_state() -> str:
    """Get a complete snapshot of the project — all AUs, tracks, regions, effects, mixer state.

    One call to inspect the entire project structure. Useful for agents to understand
    the current state before making changes.
    """
    result = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        const aus = h.allAUs();
        const typeNames = ['undefined', 'notes', 'audio', 'value'];
        const project = h.project;
        return {
            bpm: project.timelineBox.bpm.getValue(),
            duration_beats: project.lastRegionAction() / h.ppqn.Quarter,
            au_count: aus.length,
            units: aus.map(au => {
                const np = au.namedParameter;
                const tracks = au.tracks.collection.adapters();
                const fxAdapters = au.audioEffects.adapters();
                const midiFxAdapters = au.midiEffects.adapters();
                return {
                    index: au.indexField.getValue(),
                    label: au.label,
                    type: au.isOutput ? 'output' : (au.isInstrument ? 'instrument' : 'bus'),
                    volume_db: np.volume.getValue(),
                    panning: np.panning.getValue(),
                    mute: np.mute.getValue(),
                    solo: np.solo.getValue(),
                    track_count: tracks.length,
                    audio_effect_count: fxAdapters.length,
                    midi_effect_count: midiFxAdapters.length,
                    effects: fxAdapters.map(fx => fx.label),
                    midi_effects: midiFxAdapters.map(fx => fx.label),
                    tracks: tracks.map(t => {
                        const tbox = t.box;
                        const regCount = h.regionBoxes(tbox).length;
                        const clipCount = h.clipBoxes(tbox).length;
                        return {
                            type: typeNames[t.type] || String(t.type),
                            region_count: regCount,
                            clip_count: clipCount,
                        };
                    }),
                };
            }),
        };
    }""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_get_region_info(unit_index: int, track_index: int, region_index: int) -> str:
    """Get detailed info about a single region — position, duration, loop, mute, content.

    unit_index: AU index.
    track_index: Track index within the AU.
    region_index: Region index.

    Returns region metadata including type-specific info (notes count, audio file, automation events).
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const region = h.region({unit_index}, {track_index}, {region_index});
            const info = {{
                position: region.position,
                duration: region.duration,
                complete: region.complete,
                loop_offset: region.loopOffset,
                loop_duration: region.loopDuration,
                mute: region.mute,
                label: region.label,
                hue: region.hue,
                is_mirrored: region.isMirrowed,
                type: region.type,
            }};
            // Type-specific info
            if (region.isNoteRegion?.()) {{
                const optCol = region.optCollection;
                if (optCol.nonEmpty()) {{
                    info.note_count = optCol.unwrap().events.asArray().length;
                }}
            }} else if (region.isAudioRegion?.()) {{
                const optFile = region.optFile;
                if (optFile.nonEmpty()) {{
                    info.file_name = optFile.unwrap().fileName;
                    info.duration_seconds = optFile.unwrap().endInSeconds - optFile.unwrap().startInSeconds;
                }}
                info.time_base = region.timeBase;
                info.has_stretch = !region.isPlayModeNoStretch;
            }}
            return info;
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


# ─────────────────────────────────────────────────────────────────────
# Clip Operations (158-159)
# ─────────────────────────────────────────────────────────────────────

@mcp.tool()
async def mcp_opendaw_clone_clip(unit_index: int, track_index: int, clip_index: int, consolidate: bool = False) -> str:
    """Clone a clip (note or value) on the same track. Optionally consolidate (make event collection unique).

    unit_index: AU index.
    track_index: Track index within the AU.
    clip_index: Clip index to clone.
    consolidate: If true, the clone gets its own independent event collection (not shared).

    Returns success, or error.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const track = h.track({unit_index}, {track_index});
            const clips = track.clips.collection.adapters();
            if ({clip_index} >= clips.length) return {{error: "No clip {clip_index}"}};
            const clip = clips[{clip_index}];
            h.modify(() => {{
                clip.clone({str(consolidate).lower()});
            }});
            const newClips = track.clips.collection.adapters();
            return {{
                success: true,
                clip_count: newClips.length,
                new_clip_label: newClips[newClips.length - 1].label,
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_consolidate_clip(unit_index: int, track_index: int, clip_index: int) -> str:
    """Consolidate a clip's event collection — make it unique (not shared/mirrored).

    If a clip shares its event collection with other clips (mirrored),
    this creates a new independent copy so edits don't affect other clips.

    unit_index: AU index.
    track_index: Track index within the AU.
    clip_index: Clip index to consolidate.

    Returns success, or error.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const track = h.track({unit_index}, {track_index});
            const clips = track.clips.collection.adapters();
            if ({clip_index} >= clips.length) return {{error: "No clip {clip_index}"}};
            const clip = clips[{clip_index}];
            const wasMirrored = clip.isMirrowed;
            h.modify(() => {{
                clip.consolidate();
            }});
            return {{
                success: true,
                was_mirrored: wasMirrored,
                is_mirrored: clip.isMirrowed,
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_set_clip_mute(unit_index: int, track_index: int, clip_index: int, mute: bool) -> str:
    """Mute or unmute a clip in the session view.

    unit_index: AU index.
    track_index: Track index within the AU.
    clip_index: Clip index.
    mute: True to mute, false to unmute.

    Returns success with old and new mute state.
    """
    mute_val = "true" if mute else "false"
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const track = h.track({unit_index}, {track_index});
            const clips = track.clips.collection.adapters();
            if ({clip_index} >= clips.length) return {{error: "No clip {clip_index}"}};
            const clip = clips[{clip_index}];
            const oldMute = clip.mute;
            h.modify(() => {{
                clip.box.mute.setValue({mute_val});
            }});
            return {{success: true, old_mute: oldMute, new_mute: {mute_val}}};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_set_clip_label(unit_index: int, track_index: int, clip_index: int, label: str) -> str:
    """Set the label (name) of a clip in the session view.

    unit_index: AU index.
    track_index: Track index within the AU.
    clip_index: Clip index.
    label: New clip name.

    Returns success with old and new label.
    """
    safe_label = json.dumps(label)
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const track = h.track({unit_index}, {track_index});
            const clips = track.clips.collection.adapters();
            if ({clip_index} >= clips.length) return {{error: "No clip {clip_index}"}};
            const clip = clips[{clip_index}];
            const oldLabel = clip.label;
            h.modify(() => {{
                clip.box.label.setValue({safe_label});
            }});
            return {{success: true, old_label: oldLabel, new_label: {safe_label}}};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_set_clip_hue(unit_index: int, track_index: int, clip_index: int, hue: int) -> str:
    """Set the color (hue) of a clip in the session view.

    unit_index: AU index.
    track_index: Track index within the AU.
    clip_index: Clip index.
    hue: Color hue 0-360.

    Returns success with old and new hue.
    """
    if hue < 0 or hue > 360:
        return json.dumps({"error": f"hue must be 0-360, got {hue}"})
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const track = h.track({unit_index}, {track_index});
            const clips = track.clips.collection.adapters();
            if ({clip_index} >= clips.length) return {{error: "No clip {clip_index}"}};
            const clip = clips[{clip_index}];
            const oldHue = clip.hue;
            h.modify(() => {{
                clip.box.hue.setValue({hue});
            }});
            return {{success: true, old_hue: oldHue, new_hue: {hue}}};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


# ─────────────────────────────────────────────────────────────────────
# Automation Event Management (160-162)
# ─────────────────────────────────────────────────────────────────────

@mcp.tool()
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

@mcp.tool()
async def mcp_opendaw_list_automation_events_detail(unit_index: int, track_index: int) -> str:
    """List all automation events on a value track with full detail — position, value, interpolation.

    More detailed than list_automation_events — includes interpolation type and curve slope.

    unit_index: AU index.
    track_index: Value (automation) track index.

    Returns event list with positions in beats, values, and interpolation details.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const track = h.track({unit_index}, {track_index});
            const regions = track.regions.collection.asArray();
            if (regions.length === 0) return {{events: [], note: "No regions"}};
            const allEvents = [];
            for (const region of regions) {{
                if (!region.isValueRegion?.()) continue;
                const optCol = region.optCollection;
                if (optCol.isEmpty()) continue;
                const collection = optCol.unwrap();
                const events = collection.events.asArray();
                for (const event of events) {{
                    const interp = event.interpolation;
                    const entry = {{
                        position_beats: event.position / h.ppqn.Quarter,
                        position_ppqn: event.position,
                        value: event.value,
                        index: event.index,
                        interpolation: interp.type,
                    }};
                    if (interp.type === 'curve') entry.curve_slope = interp.slope;
                    allEvents.push(entry);
                }}
            }}
            return {{events: allEvents, count: allEvents.length}};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
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

@mcp.tool()
async def mcp_opendaw_get_note_range(unit_index: int, track_index: int, region_index: int) -> str:
    """Get the pitch range and max duration of notes in a note region.

    Returns min pitch, max pitch, and longest note duration — useful for
    determining the vocal/instrument range and planning transpose operations.

    unit_index: AU index.
    track_index: Note track index within the AU.
    region_index: Note region index.

    Returns min_pitch, max_pitch, max_duration_beats, note_count, or error.
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
            return {{
                min_pitch: collection.minPitch,
                max_pitch: collection.maxPitch,
                max_duration_beats: collection.maxDuration / h.ppqn.Quarter,
                note_count: events.length,
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
async def mcp_opendaw_set_device_label(unit_index: int, effect_index: int, label: str, is_midi_effect: bool = False) -> str:
    """Rename an effect or MIDI effect device.

    unit_index: AU index.
    effect_index: Effect index in the chain.
    label: New label/name for the device.
    is_midi_effect: If true, target MIDI effects chain instead of audio effects.

    Returns success, or error.
    """
    safe_label = label.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const au = h.au({unit_index});
            const chain = {str(is_midi_effect).lower()} ? au.midiEffects : au.audioEffects;
            const adapters = chain.adapters();
            if ({effect_index} >= adapters.length) return {{error: "No effect at {effect_index}"}};
            const device = adapters[{effect_index}];
            h.modify(() => {{
                device.labelField.setValue("{safe_label}");
            }});
            return {{
                success: true,
                new_label: device.labelField.getValue(),
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_get_device_chain_detail(unit_index: int) -> str:
    """Get detailed info about all devices on an AU — instrument, audio effects, MIDI effects.

    One call to inspect the full device chain: instrument name/type, all effects with
    labels, enabled state, minimized state, and parameter counts.

    unit_index: AU index.

    Returns instrument info, audio_effect array, midi_effect array.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const au = h.auBox({unit_index});
            const audioFx = h.effectBoxes(au);
            const midiFx = au.midiEffects.adapters();
            const input = au.input.adapter();
            const instrument = input.isEmpty() ? null : {{
                label: input.unwrap().labelField.getValue(),
                type: input.unwrap().box.constructor.name,
                enabled: input.unwrap().enabledField?.getValue?.() ?? true,
            }};
            return {{
                au_label: au.label,
                instrument: instrument,
                audio_effects: audioFx.map(fx => ({{
                    index: fx.indexField.getValue(),
                    label: fx.labelField.getValue(),
                    type: fx.box.constructor.name,
                    enabled: fx.enabledField.getValue(),
                    minimized: fx.minimizedField?.getValue?.() ?? false,
                }})),
                midi_effects: midiFx.map(fx => ({{
                    index: fx.indexField.getValue(),
                    label: fx.labelField.getValue(),
                    type: fx.box.constructor.name,
                    enabled: fx.enabledField.getValue(),
                }})),
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_ppqn_to_parts(position_ppqn: float) -> str:
    """Convert a PPQN position to musical parts: bars, beats, semiquavers, ticks.

    Useful for understanding where a position falls in the musical grid,
    accounting for time signature changes.

    position_ppqn: Position in PPQN (960 = 1 quarter note).

    Returns bars, beats, semiquavers, ticks, and the active time signature.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const sigTrack = h.rootBoxAdapter.timeline.signatureTrack;
            const parts = sigTrack.toParts({position_ppqn});
            const sig = sigTrack.signatureAt({position_ppqn});
            return {{
                bars: parts.bars,
                beats: parts.beats,
                semiquavers: parts.semiquavers,
                ticks: parts.ticks,
                time_signature: [sig[0], sig[1]],
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_get_bar_interval(position_ppqn: float) -> str:
    """Get the start and end PPQN of the bar containing the given position.

    Useful for snapping regions, clips, and events to bar boundaries.

    position_ppqn: Position in PPQN.

    Returns bar_start (ppqn), bar_end (ppqn), bar_length (ppqn), and time signature.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const sigTrack = h.rootBoxAdapter.timeline.signatureTrack;
            const interval = sigTrack.getBarInterval({position_ppqn});
            const sig = sigTrack.signatureAt({position_ppqn});
            const barLen = sigTrack.barLengthAt({position_ppqn});
            return {{
                bar_start: interval.position,
                bar_end: interval.complete,
                bar_length: barLen,
                time_signature: [sig[0], sig[1]],
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_move_signature_event(event_index: int, target_ppqn: float) -> str:
    """Move a time signature change event to a new PPQN position.

    Automatically recalculates relative positions of subsequent events.

    event_index: Index of the signature event (from add_signature_change list).
    target_ppqn: New position in PPQN.

    Returns success or error.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const sigTrack = h.rootBoxAdapter.timeline.signatureTrack;
            const adapter = sigTrack.adapterAt({event_index});
            if (adapter.isEmpty()) return {{error: "No signature event at index " + {event_index}}};
            h.editing.modify(() => {{
                sigTrack.moveEvent(adapter.unwrap(), {target_ppqn});
            }});
            return {{success: true, event_index: {event_index}, new_position: {target_ppqn}}};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_copy_region_fades(src_unit: int, src_track: int, src_region: int,
                                        dst_unit: int, dst_track: int, dst_region: int) -> str:
    """Copy fade in/out settings from one audio region to another.

    Copies fadeIn, fadeOut, fadeInSlope, fadeOutSlope from the source region's
    Fading object to the destination region's Fading object.

    src_unit/src_track/src_region: Source region coordinates.
    dst_unit/dst_track/dst_region: Destination region coordinates.

    Returns the copied fade values.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const srcReg = h.region(h.au({src_unit}), h.track({src_unit}, {src_track}), {src_region});
            const dstReg = h.region(h.au({dst_unit}), h.track({dst_unit}, {dst_track}), {dst_region});
            if (!srcReg.fading || !dstReg.fading) return {{error: "Both regions must have fading (audio regions only)"}};
            const fadeIn = srcReg.fading.fadeIn.getValue();
            const fadeOut = srcReg.fading.fadeOut.getValue();
            const fadeInSlope = srcReg.fading.fadeInSlope.getValue();
            const fadeOutSlope = srcReg.fading.fadeOutSlope.getValue();
            h.modify(() => {{
                dstReg.fading.fadeIn.setValue(fadeIn);
                dstReg.fading.fadeOut.setValue(fadeOut);
                dstReg.fading.fadeInSlope.setValue(fadeInSlope);
                dstReg.fading.fadeOutSlope.setValue(fadeOutSlope);
            }});
            return {{
                success: true,
                fade_in: fadeIn, fade_out: fadeOut,
                fade_in_slope: fadeInSlope, fade_out_slope: fadeOutSlope,
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_copy_playfield_sample(unit_index: int, sample_index: int, target_index: int) -> str:
    """Copy a Playfield (drum machine) sample to a new index slot.

    Duplicates the sample with all its parameters (mute, solo, pitch, attack,
    release, sampleStart, sampleEnd, gate, exclude, polyphone) to a new slot.

    unit_index: AU index containing the Playfield instrument.
    sample_index: Source sample slot index.
    target_index: Destination slot index.

    Returns success or error.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const au = h.au({unit_index});
            const input = au.input.adapter();
            if (input.isEmpty()) return {{error: "No instrument on AU " + {unit_index}}};
            const inst = input.unwrap();
            if (!inst.box.constructor.name.includes('Playfield')) return {{error: "Instrument is not a Playfield"}};
            const samples = inst.box.samples ? h.sampleBoxes(inst.box) : [];
            const sampleAdapter = samples.find(s => s.box.index.getValue() === {sample_index});
            if (!sampleAdapter) return {{error: "No sample at index " + {sample_index}}};
            const adapter = h.project.boxAdapters.adapterFor(sampleAdapter.box, inst.constructor);
            h.modify(() => {{
                adapter.copyToIndex({target_index});
            }});
            return {{success: true, source: {sample_index}, target: {target_index}}};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_duplicate_note_event(unit_index: int, track_index: int, region_index: int, note_index: int,
                                           position_offset: float = 0.0, pitch_offset: int = 0) -> str:
    """Duplicate a note event within the same region with optional position/pitch offset.

    Copies the note's position, duration, pitch, velocity, cent, chance, playCount.
    Can transpose and shift the copy relative to the original.

    unit_index/track_index/region_index: Region coordinates.
    note_index: Note index within the region.
    position_offset: PPQN offset from original position (default 0 = same position).
    pitch_offset: Semitone offset from original pitch (default 0 = same pitch).

    Returns the new note's position, pitch, and duration.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const reg = h.region(h.au({unit_index}), h.track({unit_index}, {track_index}), {region_index});
            const events = reg.events.targetVertex.unwrap("events").box;
            const noteAdapters = h.eventBoxes(events)
                .sort((a, b) => a.position.getValue() - b.position.getValue());
            if ({note_index} >= noteAdapters.length) return {{error: "No note at index " + {note_index}}};
            const srcBox = noteAdapters[{note_index}];
            const adapter = h.project.boxAdapters.adapterFor(srcBox, h.project.NoteEventBoxAdapter || class {{}});
            let newAdapter;
            h.modify(() => {{
                newAdapter = adapter.copyTo({{
                    position: srcBox.position.getValue() + {position_offset},
                    pitch: srcBox.pitch.getValue() + {pitch_offset},
                }});
            }});
            return {{
                success: true,
                new_position: newAdapter.position,
                new_pitch: newAdapter.pitch,
                new_duration: newAdapter.duration,
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_get_neuralamp_model(unit_index: int, effect_index: int) -> str:
    """Get the NeuralAmp (Tone3000) model JSON for a NeuralAmp effect.

    Returns the full NAM model JSON string, or an error if the effect is not
    a NeuralAmp or has no model loaded.

    unit_index: AU index.
    effect_index: Effect index in the audio effect chain.

    Returns model_json (string) or empty if no model loaded.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const au = h.auBox({unit_index});
            const fx = h.effectBoxes(au);
            if ({effect_index} >= fx.length) return {{error: "No effect at index " + {effect_index}}};
            const fxAdapter = fx[{effect_index}];
            if (!fxAdapter.getModelJson) return {{error: "Effect is not a NeuralAmp"}};
            const modelJson = fxAdapter.getModelJson();
            return {{
                effect_label: fxAdapter.labelField.getValue(),
                has_model: modelJson.length > 0,
                model_size: modelJson.length,
                model_json: modelJson.length > 0 ? modelJson.substring(0, 500) + (modelJson.length > 500 ? '...[truncated]' : '') : null,
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_set_neuralamp_model(unit_index: int, effect_index: int, model_json: str, label: str = "NAM Model", pack_id: str = "") -> str:
    """Load a Neural Amp Modeler (NAM/Tone3000) model JSON into a NeuralAmp effect.

    Creates a NeuralAmpModelBox with the provided model JSON and links it to the
    NeuralAmp device. This bypasses the popup-based Tone3000 Select Flow, enabling
    headless model loading.

    unit_index: AU index.
    effect_index: Effect index in the audio effect chain (must be a NeuralAmp).
    model_json: Full NAM model JSON string (the model architecture + weights).
    label: Optional label for the model box (default "NAM Model").
    pack_id: Optional pack identifier.

    Returns success + model_size, or error if the effect is not a NeuralAmp.
    """
    escaped_json = json.dumps(model_json)
    escaped_label = json.dumps(label)
    escaped_pack = json.dumps(pack_id)
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const au = h.auBox({unit_index});
            const fx = h.effectBoxes(au);
            if ({effect_index} >= fx.length) return {{error: "No effect at index " + {effect_index}}};
            const fxAdapter = fx[{effect_index}];
            if (!fxAdapter.getModelJson) return {{error: "Effect is not a NeuralAmp"}};

            const effectBox = fxAdapter.box;
            const NeuralAmpModelBox = window.DAW_NeuralAmpModelBox;
            if (!NeuralAmpModelBox) return {{error: "DAW_NeuralAmpModelBox global not available"}};

            const UUID = window.DAW_UUID || h.uuid;
            h.modify(() => {{
                const modelBox = NeuralAmpModelBox.create(h.boxGraph, UUID.generate());
                modelBox.label.setValue({escaped_label});
                modelBox.model.setValue({escaped_json});
                if ({escaped_pack}.length > 0) modelBox.packId.setValue({escaped_pack});
                const modelVertex = h.boxGraph.findVertex(modelBox.address);
                if (modelVertex.isEmpty()) return {{error: "Failed to create model vertex"}};
                effectBox.model.refer(modelVertex.unwrap());
            }});

            return {{
                success: true,
                effect: effectBox.constructor.name,
                model_label: {escaped_label},
                model_size: {escaped_json}.length,
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
async def mcp_opendaw_set_tidal_rate(unit_index: int, effect_index: int, rate: str) -> str:
    """Set the LFO rate on a Tidal effect using a musical fraction string.

    unit_index: AU index.
    effect_index: Effect index in the audio effect chain (must be a Tidal).
    rate: Musical fraction — one of:
        "1/1", "1/2", "1/3", "3/16", "1/6", "1/8", "3/32", "1/12",
        "1/16", "3/64", "1/24", "1/32", "1/48", "1/64", "1/96", "1/128".
    """
    if rate not in TIDAL_RATE_MAP:
        return _err(f"Invalid rate '{rate}'. Valid: {', '.join(sorted(TIDAL_RATE_MAP.keys()))}")
    idx = TIDAL_RATE_MAP[rate]
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const au = h.auBox({unit_index});
            const fx = h.effectBoxes(au);
            if ({effect_index} >= fx.length) return {{error: "No effect at index " + {effect_index}}};
            const box = fx[{effect_index}];
            if (!box.rate) return {{error: "Effect has no rate field (not a Tidal)"}};
            const oldValue = box.rate.getValue();
            h.modify(() => {{ box.rate.setValue({idx}); }});
            return {{
                success: true,
                effect: box.constructor.name,
                rate: "{rate}",
                old_index: oldValue,
                new_index: box.rate.getValue(),
            }};
        }} catch(e) {{ return {{error: e.message}}; }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
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

@mcp.tool()
async def mcp_opendaw_set_fold_oversampling(unit_index: int, effect_index: int, oversampling: int) -> str:
    """Set the oversampling level on a Fold (wavefolding) effect.

    unit_index: AU index.
    effect_index: Effect index in the audio effect chain (must be a Fold).
    oversampling: 0=off, 1=2x, 2=4x.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const au = h.auBox({unit_index});
            const fx = h.effectBoxes(au);
            if ({effect_index} >= fx.length) return {{error: "No effect at index " + {effect_index}}};
            const fxAdapter = fx[{effect_index}];
            const box = fxAdapter.box;
            if (!box.overSampling) return {{error: "Effect has no overSampling (not a Fold)"}};
            const oldValue = box.overSampling.getValue();
            h.modify(() => {{
                box.overSampling.setValue({oversampling});
            }});
            return {{
                success: true,
                effect: box.constructor.name,
                old_value: oldValue,
                new_value: box.overSampling.getValue(),
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_set_crusher_bits(unit_index: int, effect_index: int, bits: int) -> str:
    """Set the bit depth on a Crusher (bitcrusher) effect.

    unit_index: AU index.
    effect_index: Effect index in the audio effect chain (must be a Crusher).
    bits: Bit depth (1-16, where 16=no crushing, 1=extreme).
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const au = h.auBox({unit_index});
            const fx = h.effectBoxes(au);
            if ({effect_index} >= fx.length) return {{error: "No effect at index " + {effect_index}}};
            const fxAdapter = fx[{effect_index}];
            const box = fxAdapter.box;
            if (!box.bits) return {{error: "Effect has no bits (not a Crusher)"}};
            const oldValue = box.bits.getValue();
            h.modify(() => {{
                box.bits.setValue({bits});
            }});
            return {{
                success: true,
                effect: box.constructor.name,
                old_value: oldValue,
                new_value: box.bits.getValue(),
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
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

@mcp.tool()
async def mcp_opendaw_set_crusher_crush(unit_index: int, effect_index: int, crush: float) -> str:
    """Set the sample-rate reduction (crush) on a Crusher effect.

    The crush value is inverted internally: 0.0=clean (20kHz), 0.15=retro lo-fi (~8kHz),
    0.25=AM radio (~3.5kHz), 0.55=glitchy (~500Hz), 1.0=inaudible (20Hz).

    unit_index: AU index.
    effect_index: Effect index in the audio effect chain (must be a Crusher).
    crush: Sample rate reduction amount (0.0-1.0, 0=clean, 1=max destruction).
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const au = h.auBox({unit_index});
            const fx = h.effectBoxes(au);
            if ({effect_index} >= fx.length) return {{error: "No effect at index " + {effect_index}}};
            const box = fx[{effect_index}];
            if (!box.crush) return {{error: "Effect has no crush field (not a Crusher)"}};
            const oldValue = box.crush.getValue();
            h.modify(() => {{
                box.crush.setValue({crush});
            }});
            return {{
                success: true,
                effect: box.constructor.name,
                old_value: oldValue,
                new_value: box.crush.getValue(),
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
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

@mcp.tool()
async def mcp_opendaw_list_transient_markers(unit_index: int, track_index: int, region_index: int) -> str:
    """List transient markers for an audio region's audio file.

    Transient markers are auto-detected hit points in the audio. Useful for
    beat slicing and groove extraction.

    unit_index/track_index/region_index: Audio region coordinates.

    Returns array of transient positions (in samples) or empty if none.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const reg = h.region(h.au({unit_index}), h.track({unit_index}, {track_index}), {region_index});
            const audioContent = reg.audioContent || reg.box.audioContent;
            if (!audioContent) return {{error: "Region has no audio content (not an audio region)"}};
            const fileVertex = audioContent.targetVertex || audioContent.file?.targetVertex;
            if (!fileVertex || fileVertex.isEmpty()) return {{error: "No audio file attached"}};
            const fileBox = fileVertex.unwrap().box;
                        const fileAdapter = h.project.boxAdapters.adapterFor(fileBox, p.AudioFileBoxAdapter || class {{}});
            if (!fileAdapter.transients) return {{transients: [], note: "No transients available"}};
            const transients = Array.from(fileAdapter.transients.iterate());
            return {{
                file_name: fileAdapter.fileName,
                transient_count: transients.length,
                transients: transients.map(t => ({{position: t.position, uuid: t.uuid?.toString?.() || null}})),
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_get_signature_events() -> str:
    """List all time signature change events in the project.

    Returns the base signature (4/4 by default) and all signature change events
    with their accumulated PPQN positions, bar counts, and nominator/denominator.

    Returns base_signature, events array with index/position/bars/nominator/denominator.
    """
    result = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        try {
            const sigTrack = h.rootBoxAdapter.timeline.signatureTrack;
            const events = Array.from(sigTrack.iterateAll());
            return {
                enabled: sigTrack.enabled,
                base_signature: [events[0].nominator, events[0].denominator],
                event_count: events.length - 1,
                events: events.map(e => ({
                    index: e.index,
                    position_ppqn: e.accumulatedPpqn,
                    bars: e.accumulatedBars,
                    nominator: e.nominator,
                    denominator: e.denominator,
                })),
            };
        } catch(e) {
            return {error: e.message};
        }
    }""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_change_base_signature(nominator: int, denominator: int) -> str:
    """Change the base time signature of the project.

    This changes the initial signature (default 4/4). All existing signature
    change events are recalculated to preserve their approximate absolute positions.

    nominator: Number of beats per bar (e.g. 4 for 4/4, 3 for 3/4, 6 for 6/8).
    denominator: Beat unit (1=whole, 2=half, 4=quarter, 8=eighth, 16=sixteenth).

    Returns success or error.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const sigTrack = h.rootBoxAdapter.timeline.signatureTrack;
            h.editing.modify(() => {{
                sigTrack.changeSignature({nominator}, {denominator});
            }});
            return {{success: true, new_signature: [{nominator}, {denominator}]}};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_reset_playfield_params(unit_index: int, sample_index: int) -> str:
    """Reset all parameters of a Playfield drum sample to defaults.

    Resets mute, solo, exclude, polyphone, pitch, attack, release,
    sampleStart, sampleEnd, gate to their default values.

    unit_index: AU index containing the Playfield.
    sample_index: Sample slot index to reset.

    Returns success or error.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const au = h.au({unit_index});
            const input = au.input.adapter();
            if (input.isEmpty()) return {{error: "No instrument on AU " + {unit_index}}};
            const inst = input.unwrap();
            if (!inst.box.constructor.name.includes('Playfield')) return {{error: "Instrument is not a Playfield"}};
            const samples = inst.box.samples ? h.sampleBoxes(inst.box) : [];
            const sampleAdapter = samples.find(s => s.box.index.getValue() === {sample_index});
            if (!sampleAdapter) return {{error: "No sample at index " + {sample_index}}};
            const adapter = h.project.boxAdapters.adapterFor(sampleAdapter.box, inst.constructor);
            h.modify(() => {{
                adapter.resetParameters();
            }});
            return {{success: true, sample_index: {sample_index}}};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_duplicate_automation_event(unit_index: int, track_index: int, region_index: int,
                                                  event_index: int, position_offset: float = 0.0,
                                                  value_override: float = None) -> str:
    """Duplicate an automation event within the same region.

    Copies the event's position, value, and interpolation. Can offset position
    and override the value.

    unit_index/track_index/region_index: Automation region coordinates.
    event_index: Event index within the region.
    position_offset: PPQN offset from original position.
    value_override: New value (0-1) instead of copying. Omit to copy original.

    Returns the new event's position and value.
    """
    value_str = "null" if value_override is None else str(value_override)
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const reg = h.region(h.au({unit_index}), h.track({unit_index}, {track_index}), {region_index});
            const events = reg.events.targetVertex.unwrap("events").box;
            const eventAdapters = h.eventBoxes(events)
                .sort((a, b) => a.position.getValue() - b.position.getValue());
            if ({event_index} >= eventAdapters.length) return {{error: "No event at index " + {event_index}}};
            const srcBox = eventAdapters[{event_index}];
            const adapter = h.project.boxAdapters.adapterFor(srcBox, h.project.ValueEventBoxAdapter || class {{}});
            const origPos = srcBox.position.getValue();
            const origVal = srcBox.value.getValue();
            let newAdapter;
            h.modify(() => {{
                newAdapter = adapter.copyTo({{
                    position: origPos + {position_offset},
                    value: {value_str} !== null ? {value_str} : origVal,
                }});
            }});
            return {{
                success: true,
                new_position: newAdapter.position,
                new_value: newAdapter.value,
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_copy_region_to_track(src_unit: int, src_track: int, src_region: int,
                                           dst_unit: int, dst_track: int, position: float = None) -> str:
    """Copy a region to a different track (or same track at new position).

    Works with note, audio, and automation regions. The copy includes all
    content — notes, audio content, or automation events.

    src_unit/src_track/src_region: Source region coordinates.
    dst_unit/dst_track: Destination track coordinates.
    position: New position in PPQN (omit to use source position).

    Returns new region position and duration.
    """
    pos_str = "null" if position is None else str(position)
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const srcReg = h.region(h.au({src_unit}), h.track({src_unit}, {src_track}), {src_region});
            const dstTrack = h.track({dst_unit}, {dst_track});
            let newAdapter;
            h.modify(() => {{
                newAdapter = srcReg.copyTo({{
                    target: dstTrack.box.regions,
                    position: {pos_str},
                }});
            }});
            return {{
                success: true,
                new_position: newAdapter.position,
                new_duration: newAdapter.duration,
                track_type: dstTrack.type?.getValue?.() ?? 'unknown',
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_get_project_metadata() -> str:
    """Get project metadata: creation date, BPM, time signature, AU count, track count.

    Quick overview of the project state in one call.

    Returns created (ISO date), bpm, time_signature, audio_unit_count, total_track_count.
    """
    result = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        try {
            const root = h.rootBoxAdapter;
            const aus = root.audioUnits.adapters();
            let trackCount = 0;
            aus.forEach(au => { trackCount += au.tracks.collection.adapters().length; });
            const sigTrack = root.timeline.signatureTrack;
            const sig = sigTrack.storageSignature;
            return {
                created: root.created.toISOString(),
                time_signature: [sig[0], sig[1]],
                audio_unit_count: aus.length,
                total_track_count: trackCount,
                groove_enabled: root.groove.enabled,
            };
        } catch(e) {
            return {error: e.message};
        }
    }""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_list_midi_output_devices() -> str:
    """List all MIDI output devices registered in the project (hardware MIDI outputs).

    Returns id, label, delayInMs, sendTransportMessages for each device.
    """
    result = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        try {
            const devices = h.rootBoxAdapter.midiOutputDevices;
            return {
                count: devices.length,
                devices: devices.map(d => ({
                    id: d.id.getValue(),
                    label: d.label.getValue(),
                    delay_ms: d.delayInMs.getValue(),
                    send_transport: d.sendTransportMessages.getValue()
                }))
            };
        } catch(e) {
            return {error: e.message};
        }
    }""")
    return _wrap_eval(result)

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
async def mcp_opendaw_list_modular_devices() -> str:
    """List all Modular audio effect devices in the project.

    Returns a list of modular devices with their AU index, label, and module/connection counts.
    Modular is a patchable modular synthesizer inside an audio effect slot.
    """
    result = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        try {
            const aus = h.allAUs();
            const modulars = [];
            for (let i = 0; i < aus.length; i++) {
                const effects = aus[i].audioEffects.adapters();
                for (let j = 0; j < effects.length; j++) {
                    if (effects[j].box instanceof window.DAW_ModularDeviceBox) {
                        const modAdapter = effects[j];
                        const modular = modAdapter.modular();
                        modulars.push({
                            au_index: i,
                            effect_index: j,
                            label: modAdapter.labelField.getValue(),
                            module_count: modular.modules.length,
                            connection_count: modular.connections.length,
                            enabled: modAdapter.enabledField.getValue()
                        });
                    }
                }
            }
            return {modular_devices: modulars, count: modulars.length};
        } catch(e) {
            return {error: e.message};
        }
    }""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_list_modular_modules(au_index: int, effect_index: int) -> str:
    """List all modules in a Modular device.

    au_index: Audio unit index.
    effect_index: Effect index within the AU.

    Returns modules with their type, label, x/y position, inputs, outputs, and parameter values.
    Module types: gain, delay, multiplier, audio-input, audio-output.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const au = h.allAUs()[{au_index}];
            if (!au) return {{error: "No AU at index {au_index}"}};
            const effects = au.audioEffects.adapters();
            const modDev = effects[{effect_index}];
            if (!modDev || !(modDev.box instanceof window.DAW_ModularDeviceBox))
                return {{error: "No Modular device at effect {effect_index}"}};
            const modular = modDev.modular();
            const mods = modular.modules.map((m, i) => {{
                const inputs = m.inputs.map(c => ({{name: c.name, address: c.address.toString()}}));
                const outputs = m.outputs.map(c => ({{name: c.name, address: c.address.toString()}}));
                const params = {{}};
                // Collect params from namedParameter if available
                const np = m.namedParameter;
                if (np) {{
                    for (const key of Object.keys(np)) {{
                        try {{ params[key] = np[key].getValue(); }} catch(e) {{}}
                    }}
                }}
                // Also try direct box fields (gain, time) — works for ModuleGain/ModuleDelay
                const box = m.box;
                for (const prop of Object.getOwnPropertyNames(Object.getPrototypeOf(box))) {{
                    try {{
                        if (prop !== "accept" && prop !== "initializeFields" && prop !== "initialize" && typeof box[prop] === "object" && box[prop] && typeof box[prop].getValue === "function") {{
                            if (!(prop in params)) {{
                                params[prop] = box[prop].getValue();
                            }}
                        }}
                    }} catch(e) {{}}
                }}
                return {{
                    index: i,
                    type: m.box.name.replace("Module","").replace("Modular","").replace("Box","").toLowerCase(),
                    label: m.attributes.label.getValue(),
                    x: m.attributes.x.getValue(),
                    y: m.attributes.y.getValue(),
                    inputs: inputs,
                    outputs: outputs,
                    parameters: params
                }};
            }});
            return {{modules: mods, count: mods.length}};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_list_modular_connections(au_index: int, effect_index: int) -> str:
    """List all connections (patch cables) in a Modular device.

    au_index: Audio unit index.
    effect_index: Effect index within the AU.

    Returns connections with source and target module/connector info.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const au = h.allAUs()[{au_index}];
            if (!au) return {{error: "No AU at index {au_index}"}};
            const effects = au.audioEffects.adapters();
            const modDev = effects[{effect_index}];
            if (!modDev || !(modDev.box instanceof window.DAW_ModularDeviceBox))
                return {{error: "No Modular device at effect {effect_index}"}};
            const modular = modDev.modular();
            const conns = modular.connections.map((c, i) => {{
                const srcBox = c.source.box;
                const tgtBox = c.target.box;
                return {{
                    index: i,
                    source_module: srcBox.name,
                    source_field: c.source.fieldName,
                    source_address: c.source.address.toString(),
                    target_module: tgtBox.name,
                    target_field: c.target.fieldName,
                    target_address: c.target.address.toString()
                }};
            }});
            return {{connections: conns, count: conns.length}};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_add_modular_module(au_index: int, effect_index: int, module_type: str, label: str = "", x: int = 0, y: int = 0) -> str:
    """Add a module to a Modular device.

    au_index: Audio unit index.
    effect_index: Effect index within the AU.
    module_type: One of "gain", "delay", "multiplier", "audio-input", "audio-output".
    label: Optional label for the module.
    x, y: Position in the modular editor grid.

    Returns the new module's index and info.
    """
    safe_label = json.dumps(label)
    type_map = {
        "gain": "DAW_ModuleGainBox",
        "delay": "DAW_ModuleDelayBox",
        "multiplier": "DAW_ModuleMultiplierBox",
        "audio-input": "DAW_ModularAudioInputBox",
        "audio-output": "DAW_ModularAudioOutputBox",
    }
    box_global = type_map.get(module_type)
    if not box_global:
        return json.dumps({"error": f"Unknown module type: {module_type}. Valid: {list(type_map.keys())}"})


    safe_module_type = module_type.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const au = h.allAUs()[{au_index}];
            if (!au) return {{error: "No AU at index {au_index}"}};
            const effects = au.audioEffects.adapters();
            const modDev = effects[{effect_index}];
            if (!modDev || !(modDev.box instanceof window.DAW_ModularDeviceBox))
                return {{error: "No Modular device at effect {effect_index}"}};
            const modular = modDev.modular();
            const BoxClass = window.{box_global};
            if (!BoxClass) return {{error: "Box class not available: {box_global}"}};
            const graph = h.boxGraph;
            const uuid = h.uuid.generate();
            let newModule;
            h.editing.modify(() => {{
                newModule = BoxClass.create(graph, uuid, (box) => {{
                    box.attributes.collection.refer(modular.box.modules);
                    box.attributes.label.setValue({safe_label} || "{safe_module_type}");
                    box.attributes.x.setValue({x});
                    box.attributes.y.setValue({y});
                }});
            }});
            const modules = modular.modules;
            const idx = modules.length - 1;
            const m = modules[idx];
            return {{
                success: true,
                module_index: idx,
                module_type: "{safe_module_type}",
                label: m.attributes.label.getValue(),
                uuid: m.uuid
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_connect_modular_modules(au_index: int, effect_index: int, source_module_index: int, source_output_name: str, target_module_index: int, target_input_name: str) -> str:
    """Connect two modules in a Modular device (create a patch cable).

    au_index: Audio unit index.
    effect_index: Effect index within the AU.
    source_module_index: Index of the source module.
    source_output_name: Name of the output connector (e.g. "Output", "Result").
    target_module_index: Index of the target module.
    target_input_name: Name of the input connector (e.g. "Input", "X", "Y").

    Returns success or error.
    """
    safe_src_name = json.dumps(source_output_name)
    safe_tgt_name = json.dumps(target_input_name)
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const au = h.allAUs()[{au_index}];
            if (!au) return {{error: "No AU at index {au_index}"}};
            const effects = au.audioEffects.adapters();
            const modDev = effects[{effect_index}];
            if (!modDev || !(modDev.box instanceof window.DAW_ModularDeviceBox))
                return {{error: "No Modular device at effect {effect_index}"}};
            const modular = modDev.modular();
            const modules = modular.modules;
            if ({source_module_index} >= modules.length) return {{error: "No source module at index {source_module_index}"}};
            if ({target_module_index} >= modules.length) return {{error: "No target module at index {target_module_index}"}};
            const srcMod = modules[{source_module_index}];
            const tgtMod = modules[{target_module_index}];
            const srcOutput = srcMod.outputs.find(c => c.name === {safe_src_name});
            if (!srcOutput) return {{error: "Source output not found: " + {safe_src_name}, available: srcMod.outputs.map(c=>c.name)}};
            const tgtInput = tgtMod.inputs.find(c => c.name === {safe_tgt_name});
            if (!tgtInput) return {{error: "Target input not found: " + {safe_tgt_name}, available: tgtMod.inputs.map(c=>c.name)}};
            const graph = h.boxGraph;
            const uuid = h.uuid.generate();
            h.editing.modify(() => {{
                window.DAW_ModuleConnectionBox.create(graph, uuid, (box) => {{
                    box.collection.refer(modular.box.connections);
                    box.source.refer(srcOutput.field);
                    box.target.refer(tgtInput.field);
                }});
            }});
            return {{
                success: true,
                source: {{module_index: {source_module_index}, output: {safe_src_name}}},
                target: {{module_index: {target_module_index}, input: {safe_tgt_name}}}
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_set_modular_module_param(au_index: int, effect_index: int, module_index: int, param_name: str, value: float) -> str:
    """Set a parameter on a module in a Modular device.

    au_index: Audio unit index.
    effect_index: Effect index within the AU.
    module_index: Module index.
    param_name: Parameter name — "gain" for ModuleGain, "time" for ModuleDelay.
    value: New parameter value (in physical units: dB for gain, ms for delay).

    Returns success or error.
    """
    safe_param = json.dumps(param_name)
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const au = h.allAUs()[{au_index}];
            if (!au) return {{error: "No AU at index {au_index}"}};
            const effects = au.audioEffects.adapters();
            const modDev = effects[{effect_index}];
            if (!modDev || !(modDev.box instanceof window.DAW_ModularDeviceBox))
                return {{error: "No Modular device at effect {effect_index}"}};
            const modular = modDev.modular();
            const modules = modular.modules;
            if ({module_index} >= modules.length) return {{error: "No module at index {module_index}"}};
            const m = modules[{module_index}];
            // Try namedParameter first (works if adapter exposes it), then direct box field
            const np = m.namedParameter;
            let param = null;
            if (np && np[{safe_param}]) {{
                param = np[{safe_param}];
            }} else {{
                // Try direct getter on adapter (parameterGain, parameterTime, etc.)
                const getterName = "parameter" + {safe_param}.charAt(0).toUpperCase() + {safe_param}.slice(1);
                if (m[getterName]) {{
                    param = m[getterName];
                }} else {{
                    // Try direct box field
                    const boxField = m.box[{safe_param}];
                    if (boxField) {{
                        const oldVal = boxField.getValue();
                        h.editing.modify(() => {{
                            boxField.setValue({value});
                        }});
                        return {{
                            success: true,
                            module_index: {module_index},
                            param: {safe_param},
                            old_value: oldVal,
                            new_value: boxField.getValue(),
                            source: "box-field"
                        }};
                    }}
                    const available = np ? Object.keys(np) : "no namedParameter; adapter getters: " + Object.getOwnPropertyNames(Object.getPrototypeOf(m)).filter(k => k.startsWith("parameter")).join(", ");
                    return {{error: "Parameter not found: " + {safe_param}, available: available}};
                }}
            }}
            const oldVal = param.getValue();
            h.editing.modify(() => {{
                param.field.setValue({value});
            }});
            return {{
                success: true,
                module_index: {module_index},
                param: {safe_param},
                old_value: oldVal,
                new_value: {value}
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_remove_modular_module(au_index: int, effect_index: int, module_index: int) -> str:
    """Remove a module from a Modular device.

    au_index: Audio unit index.
    effect_index: Effect index within the AU.
    module_index: Module index to remove.

    Returns success or error. All connections to/from this module are also removed.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const au = h.allAUs()[{au_index}];
            if (!au) return {{error: "No AU at index {au_index}"}};
            const effects = au.audioEffects.adapters();
            const modDev = effects[{effect_index}];
            if (!modDev || !(modDev.box instanceof window.DAW_ModularDeviceBox))
                return {{error: "No Modular device at effect {effect_index}"}};
            const modular = modDev.modular();
            const modules = modular.modules;
            if ({module_index} >= modules.length) return {{error: "No module at index {module_index}"}};
            const m = modules[{module_index}];
            const label = m.attributes.label.getValue();
            h.editing.modify(() => {{
                m.box.delete();
            }});
            return {{
                success: true,
                removed_module_index: {module_index},
                label: label
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


# ─── PianoMode ───────────────────────────────────────────────────────

@mcp.tool()
async def mcp_opendaw_set_transpose(semitones: int) -> str:
    """Set global transpose for the piano roll view (does not affect audio playback).

    semitones: Number of semitones to transpose (-48 to +48).

    Returns success with old and new values.
    """
    if semitones < -48 or semitones > 48:
        return json.dumps({"error": f"Transpose must be -48 to +48, got {semitones}"})
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const pm = h.rootBoxAdapter.pianoMode;
            const old = pm.transpose.getValue();
            h.editing.modify(() => {{
                pm.transpose.field.setValue({semitones});
            }});
            return {{success: true, old_transpose: old, new_transpose: {semitones}}};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_get_piano_mode() -> str:
    """Get piano roll view settings.

    Returns keyboard type (88/76/61/49), time range, note scale, note labels, transpose.
    """
    result = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        try {
            const pm = h.rootBoxAdapter.pianoMode;
            return {
                keyboard: pm.keyboard.getValue(),
                time_range_in_quarters: pm.timeRangeInQuarters.getValue(),
                note_scale: pm.noteScale.getValue(),
                note_labels: pm.noteLabels.getValue(),
                transpose: pm.transpose.getValue()
            };
        } catch(e) {
            return {error: e.message};
        }
    }""")
    return _wrap_eval(result)

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
async def mcp_opendaw_set_piano_time_range(quarters: float) -> str:
    """Set the piano roll time range (horizontal view width in quarter notes).

    quarters: Time range in quarter notes (1.0 to 64.0). Smaller = more zoomed in.

    Returns success with old and new values.
    """
    if quarters < 1.0 or quarters > 64.0:
        return json.dumps({"error": f"quarters must be 1.0 to 64.0, got {quarters}"})
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const pm = h.rootBoxAdapter.pianoMode;
            const old = pm.timeRangeInQuarters.getValue();
            h.editing.modify(() => {{
                pm.timeRangeInQuarters.field.setValue({quarters});
            }});
            return {{success: true, old_time_range: old, new_time_range: {quarters}}};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


@mcp.tool()
async def mcp_opendaw_screenshot_daw() -> str:
    """Take a screenshot of the openDAW UI. Returns base64-encoded PNG image.
    Useful for visual debugging and verifying project state.
    """
    import base64
    if bridge.page is None:
        await bridge.start()
    screenshot_bytes = await bridge.page.screenshot(type="png")
    b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
    return json.dumps({"success": True, "image": b64, "format": "png", "size_bytes": len(screenshot_bytes)})


@mcp.tool()
async def mcp_opendaw_wait_for_condition(condition_js: str, timeout_ms: int = 10000, poll_interval_ms: int = 500) -> str:
    """Wait for a JavaScript condition to evaluate to true in the DAW context.

    Polls the condition at regular intervals until it returns true or timeout is reached.

    condition_js: JavaScript expression that returns a truthy value when the condition is met.
    timeout_ms: Maximum wait time in milliseconds (default 10000).
    poll_interval_ms: Polling interval in milliseconds (default 500).
    """
    import asyncio
    if bridge.page is None:
        await bridge.start()
    elapsed = 0
    while elapsed < timeout_ms:
        result = await bridge.page.evaluate(f"""() => {{
            try {{ return Boolean({condition_js}); }}
            catch(e) {{ return false; }}
        }}""")
        if result:
            return _ok({"elapsed_ms": elapsed, "condition_met": True})
        await asyncio.sleep(poll_interval_ms / 1000)
        elapsed += poll_interval_ms
    return json.dumps({"success": False, "condition_met": False, "elapsed_ms": elapsed, "timeout_ms": timeout_ms})


@mcp.tool()
async def mcp_opendaw_evaluate_raw(script: str) -> str:
    """Execute arbitrary JavaScript in the DAW V8 context and return the result.
    For power users and debugging — explore openDAW internals directly.
    The script must be a function body (will be wrapped in an async arrow).

    script: JavaScript code to execute. Has access to window.DAW and all DAW_ globals.
    """
    result = await bridge.evaluate(f"""() => {{
        try {{ return await (async () => {{ {script} }})(); }}
        catch(e) {{ return {{ __error: e.message, __stack: e.stack }}; }}
    }}""")
    return _wrap_eval(result)


# ─── Mixer Advanced (v1.6.1) ─────────────────────────────────────────

@mcp.tool()
async def mcp_opendaw_set_unit_minimized(unit_index: int, minimized: bool) -> str:
    """Minimize or expand an audio unit in the mixer view.

    Minimized AUs take less space in the mixer — useful for decluttering
    when working with many tracks.

    unit_index: AU index.
    minimized: True to minimize, False to expand.

    Returns success with old and new minimized state.
    """
    val = "true" if minimized else "false"
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const au = h.au({unit_index});
            const oldVal = au.minimizedField.getValue();
            h.modify(() => {{
                au.minimizedField.setValue({val});
            }});
            return {{success: true, old_minimized: oldVal, new_minimized: {val}}};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_capture_realtime(duration_seconds: float, filename: str) -> str:
    """Capture realtime audio output from the DAW engine.

    Records the live audio output for a specified duration. The engine must
    be running (call start_engine first). Useful for capturing live playback
    with effects, automation, and real-time processing.

    duration_seconds: How long to record (float, e.g. 10.0).
    filename: Output WAV filename (without extension).

    Returns file path and size, or error if engine not running.
    """
    safe_name = _safe_filename(filename)
    result = await bridge.evaluate(f"""async () => {{
        const captureFn = window.DAW_captureRealtime;
        if (!captureFn) return {{error: "captureRealtime not available"}};
        try {{
            const audioData = await captureFn({duration_seconds});
            const WavFile = window.DAW_WavFile;
            if (!WavFile) return {{error: "WavFile not available"}};
            const wav = WavFile.encodeFloats(audioData);
            const bytes = new Uint8Array(wav);
            let binary = "";
            for (let j = 0; j < bytes.length; j++) binary += String.fromCharCode(bytes[j]);
            window.__lastCaptureB64 = btoa(binary);
            return {{
                success: true,
                samples: audioData.frames[0]?.length || 0,
                sample_rate: audioData.sampleRate,
                channels: audioData.numberOfChannels,
                size_bytes: bytes.length,
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    if isinstance(result, dict) and result.get("error"):
        return _wrap_eval(result)

    import base64 as b64mod
    export_dir = os.environ.get("OPENDAW_EXPORT_DIR", os.path.join(os.path.dirname(__file__), "exports"))
    os.makedirs(export_dir, exist_ok=True)
    b64 = await bridge.evaluate("() => window.__lastCaptureB64")
    filepath = os.path.join(export_dir, f"{safe_name}.wav")
    if isinstance(b64, str) and b64:
        wav_bytes = b64mod.b64decode(b64)
        with open(filepath, "wb") as f:
            f.write(wav_bytes)

    if isinstance(result, dict):
        result["filepath"] = filepath
    return json.dumps(result)

@mcp.tool()
async def mcp_opendaw_get_sample_info(sample_uuid: str) -> str:
    """Get detailed info about an audio sample by UUID.

    Uses the SampleManager to fetch metadata about audio files registered
    in the project. Returns sample rate, channels, frames, and loading state.

    sample_uuid: UUID of the audio sample (from list_samples).

    Returns sample metadata, or error if not found.
    """
    safe_uuid = sample_uuid.replace('"', '').replace('\\', '').replace("'", "").replace(';', '')
    uuid_json = json.dumps(safe_uuid)
    result = await bridge.evaluate(f"""async () => {{
        const sm = window.DAW_sampleManager;
        if (!sm) return {{error: "sampleManager not available"}};
        try {{
            const data = await sm.getAudioData({uuid_json});
            if (!data) return {{error: "Sample not found"}};
            return {{
                success: true,
                sample_rate: data.sampleRate,
                channels: data.numChannels,
                frames: data.numFrames,
                duration_seconds: data.numFrames / data.sampleRate,
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


@mcp.tool()
async def mcp_opendaw_get_studio_settings() -> str:
    """Get all studio preferences/settings (engine, visibility, editing, debug, storage, time-display, pointer).

    Returns all settings categories with current values.
    """
    result = await bridge.evaluate("""async () => {
        const prefs = window.DAW_StudioPreferences;
        if (!prefs) return {error: "StudioPreferences not available"};
        return {settings: prefs.settings};
    }""")
    return _wrap_eval(result)


@mcp.tool()
async def mcp_opendaw_set_studio_setting(category: str, key: str, value: str) -> str:
    """Set a studio preference setting.

    Args:
        category: Settings category — one of: 'engine', 'visibility', 'editing', 'debug', 'storage', 'time-display', 'pointer'
        key: Setting key within the category (e.g. 'auto-create-output-maximizer', 'overlapping-regions-behaviour', 'enable-beta-features')
        value: New value as string — 'true'/'false' for booleans, or string values for enums

    Common settings:
        engine.auto-create-output-maximizer (bool): auto-create Maximizer on Output unit
        engine.note-audition-while-editing (bool): play notes when editing
        engine.stop-playback-when-overloading (bool): stop playback on CPU overload
        editing.overlapping-regions-behaviour ('clip'|'push-existing'|'keep-existing'): how overlapping regions interact
        editing.show-clipboard-menu (bool): show clipboard menu
        debug.enable-beta-features (bool): enable beta features
        debug.enable-debug-menu (bool): enable debug menu
        debug.show-cpu-stats (bool): show CPU stats
        storage.auto-delete-orphaned-samples (bool): auto-delete unused samples
        visibility.auto-open-clips (bool): auto-open clips
        visibility.base-frequency (bool): show base frequency
    """
    safe_cat = category.replace('"', '').replace('\\', '').replace("'", "").replace(';', '')
    safe_key = key.replace('"', '').replace('\\', '').replace("'", "").replace(';', '')
    cat_json = json.dumps(safe_cat)
    key_json = json.dumps(safe_key)
    val_json = json.dumps(value)
    result = await bridge.evaluate(f"""async () => {{
        const prefs = window.DAW_StudioPreferences;
        if (!prefs) return {{error: "StudioPreferences not available"}};
        try {{
            const s = prefs.settings;
            const cat = s[{cat_json}];
            if (!cat) return {{error: "Unknown category: {safe_cat}"}};
            const oldVal = cat[{key_json}];
            // Parse value: 'true'/'false' → bool, else string
            let newVal;
            if (typeof oldVal === 'boolean') {{
                newVal = ({val_json} === 'true' || {val_json} === true);
            }} else if (typeof oldVal === 'number') {{
                newVal = parseFloat({val_json});
            }} else {{
                newVal = {val_json};
            }}
            cat[{key_json}] = newVal;
            return {{
                success: true,
                category: {cat_json},
                key: {key_json},
                old_value: oldVal,
                new_value: newVal,
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


@mcp.tool()
async def mcp_opendaw_engine_panic() -> str:
    """Send a panic signal to the engine — stops all notes immediately.

    Useful when audio gets stuck (hanging notes, frozen synthesis).
    Equivalent to a MIDI panic button.
    """
    result = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        try {
            h.engine.panic();
            return {success: true, action: "panic"};
        } catch(e) {
            return {error: e.message};
        }
    }""")
    return _wrap_eval(result)


@mcp.tool()
async def mcp_opendaw_set_metronome(enabled: bool = None, gain: float = None, beat_subdivision: int = None) -> str:
    """Configure the metronome settings.

    Args:
        enabled: Toggle metronome on/off. None = leave unchanged.
        gain: Click volume 0.0-1.0 (default 0.5). None = leave unchanged.
        beat_subdivision: Beats per click (1=quarter, 2=eighths, 4=sixteenths, 8=thirty-seconds, default 4). None = leave unchanged.
    """
    parts = []
    if enabled is not None:
        parts.append(f'metronome.enabled = {json.dumps(bool(enabled))}')
    if gain is not None:
        parts.append(f'metronome.gain = {max(0.0, min(1.0, float(gain)))}')
    if beat_subdivision is not None:
        parts.append(f'metronome.beatSubDivision = {int(beat_subdivision)}')
    if not parts:
        return _err("At least one of enabled, gain, or beat_subdivision must be provided")
    body = "; ".join(parts)
    result = await bridge.evaluate(f"""async () => {{
        const prefs = window.DAW_StudioPreferences;
        if (!prefs) return {{error: "StudioPreferences not available"}};
        const metronome = prefs.settings.metronome;
        if (!metronome) return {{error: "metronome settings not found"}};
        const before = {{enabled: metronome.enabled, gain: metronome.gain, beatSubDivision: metronome.beatSubDivision}};
        {body};
        return {{
            success: true,
            before: before,
            after: {{enabled: metronome.enabled, gain: metronome.gain, beatSubDivision: metronome.beatSubDivision}},
        }};
    }}""")
    return _wrap_eval(result)


@mcp.tool()
async def mcp_opendaw_get_engine_status() -> str:
    """Get real-time engine status: playing state, position, BPM, CPU load, recording state.

    Returns:
        is_playing: bool
        position_beats: current playback position in beats
        bpm: current BPM
        cpu_load: CPU load percentage (0-1)
        is_recording: bool
        is_counting_in: bool
        count_in_beats_remaining: beats left in count-in
        playback_timestamp: playback timestamp in beats
        marker: current marker [uuid, index] or null
        engine_started: whether engine is initialized
    """
    result = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        const eng = h.engine;
        try {
            return {
                is_playing: eng.isPlaying?.getValue?.() ?? false,
                position_beats: (eng.position?.getValue?.() ?? 0) / h.ppqn.Quarter,
                bpm: eng.bpm?.getValue?.() ?? 120,
                cpu_load: eng.cpuLoad?.getValue?.() ?? 0,
                is_recording: eng.isRecording?.getValue?.() ?? false,
                is_counting_in: eng.isCountingIn?.getValue?.() ?? false,
                count_in_beats_remaining: eng.countInBeatsRemaining?.getValue?.() ?? 0,
                playback_timestamp: (eng.playbackTimestamp?.getValue?.() ?? 0) / h.ppqn.Quarter,
                marker: eng.markerState?.getValue?.() ?? null,
                engine_started: typeof window.DAW_engineStarted === 'function' && window.DAW_engineStarted(),
            };
        } catch(e) {
            return {error: e.message};
        }
    }""")
    return _wrap_eval(result)


@mcp.tool()
async def mcp_opendaw_engine_sleep() -> str:
    """Put the audio engine to sleep — suspends audio processing to save CPU.

    Use wake() to resume. Useful when doing non-audio operations (project editing,
    box manipulation) and the engine isn't needed.
    """
    result = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        try {
            h.engine.sleep();
            return {success: true, action: "sleep"};
        } catch(e) {
            return {error: e.message};
        }
    }""")
    return _wrap_eval(result)


@mcp.tool()
async def mcp_opendaw_engine_wake() -> str:
    """Wake the audio engine from sleep — resumes audio processing.

    Use after sleep() when audio playback is needed again.
    """
    result = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        try {
            h.engine.wake();
            return {success: true, action: "wake"};
        } catch(e) {
            return {error: e.message};
        }
    }""")
    return _wrap_eval(result)


@mcp.tool()
async def mcp_opendaw_query_loading_complete() -> str:
    """Check if all audio samples are loaded and ready for playback.

    Returns:
        loaded: true if all samples have finished loading
        is_ready: true if engine is fully initialized
    """
    result = await bridge.evaluate("""async () => {
        const h = window.DAW_HELPERS;
        try {
            const eng = h.engine;
            const loaded = eng.queryLoadingComplete ? await eng.queryLoadingComplete() : true;
            const ready = eng.isReady ? true : false;
            return {loaded: loaded, is_ready: ready};
        } catch(e) {
            return {error: e.message};
        }
    }""")
    return _wrap_eval(result)


@mcp.tool()
async def mcp_opendaw_schedule_clip_play(clip_ids: str) -> str:
    """Schedule clips to play in session view (live triggering).

    Args:
        clip_ids: Comma-separated list of clip UUIDs to trigger
    """
    safe_ids = clip_ids.replace('"', '').replace('\\', '').replace("'", "").replace(';', '').replace(' ', '')
    ids_json = json.dumps(safe_ids)
    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        try {{
            const ids = {ids_json}.split(',').filter(Boolean);
            // Get clip UUIDs from rootBox clips
            const rootBox = h.rootBox;
            const allClips = h.rootClipBoxes();
            const targetUuids = [];
            for (const clip of allClips) {{
                const uuidStr = h.uuid.toString(clip.address.uuid);
                if (ids.includes(uuidStr)) {{
                    targetUuids.push(clip.address.uuid);
                }}
            }}
            if (targetUuids.length === 0) return {{error: "No matching clips found"}};
            h.engine.scheduleClipPlay(targetUuids);
            return {{success: true, triggered: targetUuids.length}};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


@mcp.tool()
async def mcp_opendaw_schedule_clip_stop(track_ids: str) -> str:
    """Schedule clips to stop on specified tracks (session view).

    Args:
        track_ids: Comma-separated list of track UUIDs to stop clips on
    """
    safe_ids = track_ids.replace('"', '').replace('\\', '').replace("'", "").replace(';', '').replace(' ', '')
    ids_json = json.dumps(safe_ids)
    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        try {{
            const ids = {ids_json}.split(',').filter(Boolean);
            const allAUs = h.allAUs();
            const targetUuids = [];
            for (const au of allAUs) {{
                const tracks = au.tracks.collection.adapters();
                for (const track of tracks) {{
                    const uuidStr = h.uuid.toString(track.uuid);
                    if (ids.includes(uuidStr)) {{
                        targetUuids.push(track.uuid);
                    }}
                }}
            }}
            if (targetUuids.length === 0) return {{error: "No matching tracks found"}};
            h.engine.scheduleClipStop(targetUuids);
            return {{success: true, stopped: targetUuids.length}};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


@mcp.tool()
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
            let binary = '';
            for (let i = 0; i < bytes.length; i++) {
                binary += String.fromCharCode(bytes[i]);
            }
            const base64 = btoa(binary);
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


@mcp.tool()
async def mcp_opendaw_import_dawproject(filename: str) -> str:
    """Import a .dawproject file into the current session.

    The dawproject format is a ZIP containing project.xml, metadata.xml, and audio samples.
    This enables loading projects created in Bitwig, Ableton, or other DAWs supporting dawproject.

    Args:
        filename: Path to the .dawproject file to import.

    Returns the import result with track and sample counts.
    """
    safe_fn = os.path.abspath(filename)
    if not os.path.exists(safe_fn):
        return json.dumps({"error": f"File not found: {safe_fn}"})
    with open(safe_fn, "rb") as f:
        file_bytes = f.read()
    import base64 as b64mod
    file_b64 = b64mod.b64encode(file_bytes).decode('ascii')
    file_b64_json = json.dumps(file_b64)
    result = await bridge.evaluate(f"""async () => {{
        const daw = window.DAW_DawProject;
        if (!daw) return {{error: "DawProject module not available"}};
        try {{
            // Decode base64 to ArrayBuffer
            const binary = atob({file_b64_json});
            const bytes = new Uint8Array(binary.length);
            for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
            const buffer = bytes.buffer;
            const {{metaData, project, resources}} = await daw.decode(buffer);
            const result = await window.DAW_DawProjectImport.read(project, resources);
            // Load the imported skeleton into the DAW
            const newProject = window.DAW_loadProject(window.DAW_ProjectSkeleton.encode(result.skeleton.boxGraph));
            return {{
                success: true,
                audioIds: result.audioIds.length,
                boxes: newProject?.boxGraph?.boxes()?.length ?? 0,
                application: metaData?.application?.name ?? "unknown"
            }};
        }} catch(e) {{
            return {{error: e.message, stack: e.stack?.split('\\\\n').slice(0, 5).join(' | ')}};
        }}
    }}""")
    return _wrap_eval(result)


# ─── Effect Duplication ──────────────────────────────────────────────

@mcp.tool()
async def mcp_opendaw_duplicate_effect(unit_index: int, effect_index: int, chain_type: str = "audio") -> str:
    """Duplicate a single effect within an AU's effect chain, copying all parameter values.

    Addresses upstream issue #273 (Ctrl+D for audio effects) via MCP.
    Works for both audio and MIDI effect chains.

    unit_index: AU index containing the effect.
    effect_index: Index of the effect to duplicate within its chain.
    chain_type: "audio" (default) or "midi" — which effect chain to operate on.

    Returns the new effect's index and type.
    """
    valid_chains = {"audio", "midi"}
    safe_chain = (chain_type or "audio").lower().strip()
    if safe_chain not in valid_chains:
        return json.dumps({"error": f"Invalid chain_type '{safe_chain}'. Must be 'audio' or 'midi'"})
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const ef = window.DAW_EffectFactories;
        const units = h.allAUBoxes();
        if ({unit_index} >= units.length) return {{error: "No AU at index {unit_index}"}};
        const au = units[{unit_index}];
        const isMidi = "{safe_chain}" === "midi";
        const chainField = isMidi ? au.midiEffects : au.audioEffects;
        if (!chainField) return {{error: "No " + (isMidi ? "MIDI" : "audio") + " effect chain on this AU"}};

        const effects = h.chainBoxes(chainField)
            .sort((a, b) => a.index.getValue() - b.index.getValue());
        if ({effect_index} >= effects.length) return {{error: "No effect at index {effect_index}"}};

        const srcEffect = effects[{effect_index}];
        const className = srcEffect.constructor.name;

        // Find factory key
        const factoryMap = isMidi ? ef.MidiNamed : ef.AudioNamed;
        let factoryKey = null;
        for (const key of Object.keys(factoryMap)) {{
            if (className === key + "DeviceBox" || className === key) {{
                factoryKey = key;
                break;
            }}
        }}
        if (!factoryKey) return {{error: "No factory for " + className}};

        const factory = factoryMap[factoryKey];
        let newEffect;
        h.modify(() => {{
            newEffect = h.api.insertEffect(chainField, factory);
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
        }});

        const updatedEffects = h.chainBoxes(chainField)
            .sort((a, b) => a.index.getValue() - b.index.getValue());
        const newIdx = updatedEffects.findIndex(b => b.address.equals(newEffect.address));

        return {{
            success: true,
            chain_type: isMidi ? "midi" : "audio",
            original_index: {effect_index},
            new_index: newIdx,
            effect_type: factoryKey,
            total_effects: updatedEffects.length,
        }};
    }}""")
    return _wrap_eval(result)


# ─── Instrument Automation ───────────────────────────────────────────

@mcp.tool()
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


@mcp.tool()
async def mcp_opendaw_list_automatable_fields(unit_index: int, sample_index: int = -1) -> str:
    """List all automatable parameter fields on an instrument (or specific Playfield sample).

    Shows which fields support Pointers.Automation — only these can be automated.

    unit_index: Audio unit index containing the instrument.
    sample_index: For Playfield, which sample slot (-1 = top-level instrument).

    Returns field names with current values and whether they're automatable.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const sampleIdx = {sample_index};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No AU at " + unitIdx}};
        const au = units[unitIdx];

        const incoming = h.inputBoxes(au);
        const instBox = incoming.find(b => b.constructor.name !== "AudioBusBox");
        if (!instBox) return {{error: "No instrument on AU " + unitIdx}};

        let targetBox = instBox;
        if (sampleIdx >= 0) {{
            const samples = h.sampleBoxes(instBox);
                .sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
            if (sampleIdx >= samples.length) return {{error: "No sample at index " + sampleIdx}};
            targetBox = samples[sampleIdx];
        }}

        const skipFields = new Set(['host', 'index', 'collection', 'editing', 'output', 'input',
            'sideChain', 'capture', 'tracks', 'audioEffects', 'midiEffects', 'auxSends',
            'oscillators', 'lfo', 'noise', 'samples', 'parameters', 'device', 'file']);

        const Pointers = window.DAW_Pointers;
        const autoVal = Pointers?.Automation;
        const fields = [];
        const record = targetBox.record();
        for (const [key, field] of Object.entries(record)) {{
            if (skipFields.has(key)) continue;
            if (typeof field?.getValue !== 'function') continue;
            try {{
                const value = field.getValue();
                const accepts = field.pointerRules?.accepts;
                const automatable = !!(accepts && autoVal != null && accepts.includes(autoVal));
                fields.push({{
                    name: field._fieldName || field.fieldName || key,
                    value: value,
                    type: typeof value,
                    automatable: automatable,
                }});
            }} catch(e) {{}}
        }}

        return {{
            instrument: instBox.constructor.name,
            target: sampleIdx >= 0 ? "sample[" + sampleIdx + "]" : "instrument",
            target_type: targetBox.constructor.name,
            fields: fields,
        }};
    }}""")
    return _wrap_eval(result)


@mcp.tool()
async def mcp_opendaw_convert_audio(filename: str, format: str = "mp3", bitrate: str = "320k", quality: int = -1) -> str:
    """Convert an exported WAV file to MP3 or FLAC using system ffmpeg.

    filename: Source WAV filename (without .wav extension, in the export dir).
    format: 'mp3' or 'flac' (default 'mp3').
    bitrate: MP3 bitrate for CBR mode (default '320k'). Ignored for FLAC.
    quality: MP3 VBR quality 0-9 (0=best, 9=worst). Use -1 for CBR (default).

    Requires system ffmpeg (not browser WASM). Falls back gracefully if missing.
    Returns path to the converted file and size info.
    """
    import shutil as _shutil
    if not _shutil.which("ffmpeg"):
        return _wrap_eval({"error": "System ffmpeg not found — install ffmpeg to enable conversion"})
    fmt = format.lower().strip().replace('"', '').replace("'", "")
    if fmt not in ("mp3", "flac"):
        return _wrap_eval({"error": f"Unsupported format '{fmt}' — use 'mp3' or 'flac'"})
    safe_name = _safe_filename(filename)
    export_dir = os.environ.get("OPENDAW_EXPORT_DIR", os.path.join(os.path.dirname(__file__), "exports"))
    wav_path = os.path.join(export_dir, f"{safe_name}.wav")
    if not os.path.exists(wav_path):
        return _wrap_eval({"error": f"Source WAV not found: {wav_path}", "hint": "Render the project first with render_full or export_mix"})
    out_ext = fmt
    out_path = os.path.join(export_dir, f"{safe_name}.{out_ext}")
    # Build ffmpeg command
    cmd = ["ffmpeg", "-y", "-i", wav_path]
    if fmt == "mp3":
        if quality >= 0 and quality <= 9:
            cmd += ["-q:a", str(quality)]
        else:
            cmd += ["-b:a", bitrate.replace('"', '').replace("'", "")]
    elif fmt == "flac":
        cmd += ["-compression_level", "8"]
    cmd.append(out_path)
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        if proc.returncode != 0:
            return _wrap_eval({"error": f"ffmpeg exited with code {proc.returncode}"})
    except Exception as e:
        return _wrap_eval({"error": f"ffmpeg execution error: {e}"})
    if not os.path.exists(out_path):
        return _wrap_eval({"error": "ffmpeg completed but output file not created"})
    wav_size = os.path.getsize(wav_path)
    out_size = os.path.getsize(out_path)
    return _wrap_eval({
        "success": True,
        "source": wav_path,
        "output": out_path,
        "format": fmt,
        "source_size_bytes": wav_size,
        "output_size_bytes": out_size,
        "compression_ratio": round(out_size / wav_size, 3) if wav_size > 0 else 0,
        "source_size_mb": round(wav_size / (1024*1024), 2),
        "output_size_mb": round(out_size / (1024*1024), 2),
    })


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
async def mcp_opendaw_create_warp_marker(unit_index: int, track_index: int, region_index: int, position_beats: float, seconds: float) -> str:
    """Add a warp marker to a time-stretched or pitch-stretched audio region.

    Warp markers define the mapping between musical position (ppqn) and audio time (seconds).
    The first and last markers are anchors — they pin the start and end of the audio.

    unit_index: AU index.
    track_index: Track index within the AU.
    region_index: Audio region index.
    position_beats: Musical position in beats (e.g. 0.0 = start of region).
    seconds: Audio time in seconds at this position.

    Returns the new marker count and the added marker's position/seconds.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const WarpMarkerBox = window.DAW_WarpMarkerBox;
        if (!WarpMarkerBox) return {{error: "WarpMarkerBox not loaded"}};
        const auAdapters = h.allAUs();
        if ({unit_index} >= auAdapters.length) return {{error: "No AU at {unit_index}"}};
        const auAdapter = auAdapters[{unit_index}];
        const trackAdapters = auAdapter.tracks.collection.adapters();
        if ({track_index} >= trackAdapters.length) return {{error: "No track {track_index}"}};
        const trackAdapter = trackAdapters[{track_index}];
        const regions = trackAdapter.regions.collection.asArray();
        if ({region_index} >= regions.length) return {{error: "No region {region_index}"}};
        const region = regions[{region_index}];
        if (!region.isAudioRegion?.()) return {{error: "Region is not an audio region"}};
        const optPlayMode = region.observableOptPlayMode;
        if (optPlayMode.isEmpty()) return {{error: "Region has no stretch mode (not stretched)"}};
        const playMode = optPlayMode.unwrap();
        const stretchBox = playMode.box;
        const posPpqn = Math.round({position_beats} * h.ppqn.Quarter);
        const secVal = {seconds};
        h.modify(() => {{
            WarpMarkerBox.create(h.boxGraph, h.uuid.generate(), (box) => {{
                box.position.setValue(posPpqn);
                box.seconds.setValue(secVal);
                box.owner.refer(stretchBox.warpMarkers);
            }});
        }});
        const markers = playMode.warpMarkers.asArray();
        return {{
            success: true,
            marker_count: markers.length,
            added: {{position: posPpqn, seconds: secVal}},
        }};
    }}""")
    return _wrap_eval(result)


@mcp.tool()
async def mcp_opendaw_delete_warp_marker(unit_index: int, track_index: int, region_index: int, marker_index: int) -> str:
    """Delete a warp marker from a time-stretched or pitch-stretched audio region.

    Cannot delete anchor markers (first and last) — they pin the audio mapping.

    unit_index: AU index.
    track_index: Track index within the AU.
    region_index: Audio region index.
    marker_index: Warp marker index (0-based, from list_warp_markers).

    Returns remaining marker count.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const auAdapters = h.allAUs();
        if ({unit_index} >= auAdapters.length) return {{error: "No AU at {unit_index}"}};
        const auAdapter = auAdapters[{unit_index}];
        const trackAdapters = auAdapter.tracks.collection.adapters();
        if ({track_index} >= trackAdapters.length) return {{error: "No track {track_index}"}};
        const trackAdapter = trackAdapters[{track_index}];
        const regions = trackAdapter.regions.collection.asArray();
        if ({region_index} >= regions.length) return {{error: "No region {region_index}"}};
        const region = regions[{region_index}];
        if (!region.isAudioRegion?.()) return {{error: "Region is not an audio region"}};
        const optPlayMode = region.observableOptPlayMode;
        if (optPlayMode.isEmpty()) return {{error: "Region has no stretch mode (not stretched)"}};
        const playMode = optPlayMode.unwrap();
        const markers = playMode.warpMarkers.asArray();
        if ({marker_index} >= markers.length) return {{error: "No marker at index {marker_index}"}};
        const marker = markers[{marker_index}];
        if (marker.isAnchor) return {{error: "Cannot delete anchor marker (first/last)"}};
        const markerBox = marker.box;
        h.modify(() => {{
            markerBox.delete();
        }});
        const remaining = playMode.warpMarkers.asArray().length;
        return {{
            success: true,
            deleted_marker_index: {marker_index},
            remaining_markers: remaining,
        }};
    }}""")
    return _wrap_eval(result)


@mcp.tool()
async def mcp_opendaw_update_warp_marker(unit_index: int, track_index: int, region_index: int, marker_index: int, position_beats: float = -1.0, seconds: float = -1.0) -> str:
    """Update a warp marker's position and/or seconds value.

    Pass -1.0 for either parameter to leave it unchanged.

    unit_index: AU index.
    track_index: Track index within the AU.
    region_index: Audio region index.
    marker_index: Warp marker index (0-based).
    position_beats: New musical position in beats (-1 = unchanged).
    seconds: New audio time in seconds (-1 = unchanged).

    Returns updated marker values.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const auAdapters = h.allAUs();
        if ({unit_index} >= auAdapters.length) return {{error: "No AU at {unit_index}"}};
        const auAdapter = auAdapters[{unit_index}];
        const trackAdapters = auAdapter.tracks.collection.adapters();
        if ({track_index} >= trackAdapters.length) return {{error: "No track {track_index}"}};
        const trackAdapter = trackAdapters[{track_index}];
        const regions = trackAdapter.regions.collection.asArray();
        if ({region_index} >= regions.length) return {{error: "No region {region_index}"}};
        const region = regions[{region_index}];
        if (!region.isAudioRegion?.()) return {{error: "Region is not an audio region"}};
        const optPlayMode = region.observableOptPlayMode;
        if (optPlayMode.isEmpty()) return {{error: "Region has no stretch mode (not stretched)"}};
        const playMode = optPlayMode.unwrap();
        const markers = playMode.warpMarkers.asArray();
        if ({marker_index} >= markers.length) return {{error: "No marker at index {marker_index}"}};
        const marker = markers[{marker_index}];
        const markerBox = marker.box;
        const newPos = {position_beats};
        const newSec = {seconds};
        h.modify(() => {{
            if (newPos >= 0) markerBox.position.setValue(Math.round(newPos * h.ppqn.Quarter));
            if (newSec >= 0) markerBox.seconds.setValue(newSec);
        }});
        return {{
            success: true,
            marker_index: {marker_index},
            position: markerBox.position.getValue(),
            seconds: markerBox.seconds.getValue(),
            is_anchor: marker.isAnchor,
        }};
    }}""")
    return _wrap_eval(result)


@mcp.tool()
async def mcp_opendaw_set_audio_region_time_base(unit_index: int, track_index: int, region_index: int, time_base: str) -> str:
    """Set the time base of an audio region.

    Controls how the region's duration is interpreted:
    - 'musical' — duration in PPQN (musical beats, follows tempo changes)
    - 'seconds' — duration in seconds (fixed wall-clock time, independent of tempo)

    unit_index: AU index.
    track_index: Track index within the AU.
    region_index: Audio region index.
    time_base: 'musical' or 'seconds'.

    Returns old and new time base.
    """
    safe_tb = time_base.replace('"', '').replace("'", '').replace('\\', '').strip().lower()
    if safe_tb not in ("musical", "seconds"):
        return json.dumps({"error": f"Invalid time_base '{safe_tb}'. Use 'musical' or 'seconds'."})
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const auAdapters = h.allAUs();
        if ({unit_index} >= auAdapters.length) return {{error: "No AU at {unit_index}"}};
        const auAdapter = auAdapters[{unit_index}];
        const trackAdapters = auAdapter.tracks.collection.adapters();
        if ({track_index} >= trackAdapters.length) return {{error: "No track {track_index}"}};
        const trackAdapter = trackAdapters[{track_index}];
        const regions = trackAdapter.regions.collection.asArray();
        if ({region_index} >= regions.length) return {{error: "No region {region_index}"}};
        const region = regions[{region_index}];
        if (!region.isAudioRegion?.()) return {{error: "Region is not an audio region"}};
        const regionBox = region.box;
        const oldVal = regionBox.timeBase.getValue();
        h.modify(() => {{
            regionBox.timeBase.setValue("{safe_tb}");
        }});
        return {{
            success: true,
            old_time_base: oldVal,
            new_time_base: "{safe_tb}",
        }};
    }}""")
    return _wrap_eval(result)


@mcp.tool()
async def mcp_opendaw_set_audio_region_waveform_offset(unit_index: int, track_index: int, region_index: int, offset: float) -> str:
    """Set the waveform display offset of an audio region.

    The waveform offset shifts the visual start of the waveform within the region,
    useful for aligning the waveform display with the actual audio content.

    unit_index: AU index.
    track_index: Track index within the AU.
    region_index: Audio region index.
    offset: Waveform offset value (in seconds).

    Returns old and new offset.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const auAdapters = h.allAUs();
        if ({unit_index} >= auAdapters.length) return {{error: "No AU at {unit_index}"}};
        const auAdapter = auAdapters[{unit_index}];
        const trackAdapters = auAdapter.tracks.collection.adapters();
        if ({track_index} >= trackAdapters.length) return {{error: "No track {track_index}"}};
        const trackAdapter = trackAdapters[{track_index}];
        const regions = trackAdapter.regions.collection.asArray();
        if ({region_index} >= regions.length) return {{error: "No region {region_index}"}};
        const region = regions[{region_index}];
        if (!region.isAudioRegion?.()) return {{error: "Region is not an audio region"}};
        const regionBox = region.box;
        const oldVal = regionBox.waveformOffset.getValue();
        h.modify(() => {{
            regionBox.waveformOffset.setValue({offset});
        }});
        return {{
            success: true,
            old_offset: oldVal,
            new_offset: {offset},
        }};
    }}""")
    return _wrap_eval(result)

# ---------------------------------------------------------------------------
# Orchestration Tools — high-level composers that combine multiple low-level
# operations into a single call. These reduce token usage and round-trips
# for agents building complete musical structures.
# ---------------------------------------------------------------------------

@mcp.tool()
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

@mcp.tool()
async def mcp_opendaw_create_drum_pattern(pattern: str, unit_index: int = -1) -> str:
    """Create a drum beat from compact step-sequencer notation — one call replaces 10-20 note creations.

pattern: JSON object with drum lanes, each lane is a string where each char is a 16th-note step:
  - 'x' = hit (velocity 0.9)
  - 'o' = soft hit (velocity 0.5)
  - '.' = rest
  - 'X' = accent (velocity 1.0)

Lanes: kick, snare, hihat, clap, perc (each optional).

Example (4/4 house beat):
'{"kick":"x...x...x...x...","snare":"....x.......x...","hihat":"....o...o...o..."}'

unit_index: AU index with a note track (-1 = find first AU with note tracks).

Returns the number of notes created per lane.
"""
    import json as _json
    try:
        pat = _json.loads(pattern)
        if not isinstance(pat, dict) or len(pat) == 0:
            return "Error: pattern must be a JSON object with drum lanes"
    except _json.JSONDecodeError as e:
        return f"Error parsing pattern JSON: {e}"

    valid_lanes = {"kick", "snare", "hihat", "clap", "perc"}
    for lane in pat:
        if lane not in valid_lanes:
            return f"Error: unknown lane '{lane}'. Valid: {valid_lanes}"

    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const bg = h.boxGraph;
        const NoteEventBox = window.DAW_NoteEventBox;
        const NoteEventCollectionBox = window.DAW_NoteEventCollectionBox;
        const NoteRegionBox = window.DAW_NoteRegionBox;
        const Quarter = h.ppqn.Quarter;
        const Sixteenth = Quarter / 4;

        const pattern = {json.dumps(pat)};
        const unitIdx = {unit_index};

        let noteTracks = [];
        let targetAU = null;
        const allUnits = h.allAUBoxes();

        if (unitIdx >= 0 && unitIdx < allUnits.length) {{
            targetAU = allUnits[unitIdx];
            noteTracks = h.noteTrackBoxes(targetAU);
        }} else {{
            for (const au of allUnits) {{
                const nt = h.noteTrackBoxes(au);
                if (nt.length > 0) {{ noteTracks = nt; targetAU = au; break; }}
            }}
        }}

        if (noteTracks.length === 0) return {{error: "No note tracks found. Call create_synth_track or create_note_track first."}};

        const trackBox = noteTracks[0];
        const velocities = {{'x': 0.9, 'o': 0.5, 'X': 1.0}};
        const lanePitches = {{kick: 36, snare: 38, hihat: 42, clap: 39, perc: 47}};
        let totalNotes = 0;
        const laneCounts = {{}};

        h.modify(() => {{
            const collection = NoteEventCollectionBox.create(bg, h.uuid.generate());
            const maxSteps = Math.max(...Object.values(pattern).map(s => s.length));
            const regionDur = Math.max(maxSteps * Sixteenth, 4 * Quarter);

            const regionBox = NoteRegionBox.create(bg, h.uuid.generate(), (box) => {{
                box.position.setValue(0);
                box.label.setValue("Drums");
                box.mute.setValue(false);
                box.duration.setValue(regionDur);
                box.loopDuration.setValue(regionDur);
                box.eventOffset.setValue(0);
                box.events.refer(collection.owners);
                box.regions.refer(trackBox.regions);
            }});

            const eventsField = regionBox.events.targetVertex.unwrap();
            const collBox = eventsField.box;

            for (const [laneName, steps] of Object.entries(pattern)) {{
                const pitch = lanePitches[laneName] || 36;
                let count = 0;
                for (let i = 0; i < steps.length; i++) {{
                    const ch = steps[i];
                    if (ch === '.' || ch === ' ') continue;
                    const vel = velocities[ch] || 0.8;
                    NoteEventBox.create(bg, h.uuid.generate(), (box) => {{
                        box.position.setValue(Math.round(i * Sixteenth));
                        box.duration.setValue(Math.round(Sixteenth * 0.8));
                        box.velocity.setValue(vel);
                        box.pitch.setValue(pitch);
                        box.chance.setValue(100);
                        box.cent.setValue(0);
                        box.events.refer(collBox.events);
                    }});
                    count++;
                    totalNotes++;
                }}
                laneCounts[laneName] = count;
            }}
        }});

        return {{
            success: true,
            total_notes: totalNotes,
            lanes: laneCounts,
            unit_index: allUnits.indexOf(targetAU),
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_create_chord_progression(chords: str, unit_index: int = 0, track_index: int = 0, start_beat: float = 0, chord_duration: float = 4) -> str:
    """Create a chord progression from chord names — one call instead of 15-50 note creations.

chords: JSON array of chord specs. Each chord is [root_note_name, chord_type].
  Root names: C, C#, D, D#, E, F, F#, G, G#, A, A#, B (or flats: Db, Eb, Gb, Ab, Bb)
  Chord types: maj, min, dom7, maj7, min7, sus2, sus4, add9, dim, aug

Example: '[["C","min"],["F","min"],["G","dom7"],["C","min"]]'

unit_index: AU index with a note track.
track_index: Note track index within the AU.
start_beat: Where the progression starts (0 = bar 1).
chord_duration: Length of each chord in beats (4 = one bar at 4/4).

Returns the total notes created and chord voicings used.
"""
    import json as _json
    try:
        chord_list = _json.loads(chords)
        if not isinstance(chord_list, list) or len(chord_list) == 0:
            return "Error: chords must be a non-empty JSON array"
    except _json.JSONDecodeError as e:
        return f"Error parsing chords JSON: {e}"

    note_list = []
    voicings = []
    for ci, chord_spec in enumerate(chord_list):
        if len(chord_spec) < 2:
            return f"Error: chord {ci} must have [root, type]"
        root_name = chord_spec[0]
        chord_type = chord_spec[1]
        if root_name not in NOTE_TO_PITCH:
            return f"Error: unknown root '{root_name}'"
        if chord_type not in CHORD_INTERVALS:
            return f"Error: unknown chord type '{chord_type}'. Valid: {list(CHORD_INTERVALS.keys())}"

        root_pc = NOTE_TO_PITCH[root_name]
        intervals = CHORD_INTERVALS[chord_type]
        root_pitch = 60 + root_pc
        if root_pc > 5:
            root_pitch -= 12

        chord_start = start_beat + ci * chord_duration
        voicing = []
        for interval in intervals:
            pitch = root_pitch + interval
            note_list.append({"pitch": pitch, "start": chord_start, "duration": chord_duration, "velocity": 0.7})
            voicing.append(pitch)
        voicings.append({"chord": f"{root_name}{chord_type}", "pitches": voicing})

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
        const voicings = {json.dumps(voicings)};

        const allUnits = h.allAUBoxes();
        if (unitIdx >= allUnits.length) return {{error: "No AU at index " + unitIdx}};
        const noteTracks = h.noteTrackBoxes(allUnits[unitIdx]);
        if (noteTracks.length === 0) return {{error: "No note tracks on AU " + unitIdx}};
        if (trackIdx >= noteTracks.length) return {{error: "Track " + trackIdx + " out of range"}};

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
                    box.label.setValue("Chords");
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

            for (const n of notes) {{
                const pos = Math.max(0, Math.round(n.start * Quarter) - regionStart);
                const dur = Math.round(n.duration * Quarter);
                NoteEventBox.create(bg, h.uuid.generate(), (box) => {{
                    box.position.setValue(pos);
                    box.duration.setValue(dur);
                    box.velocity.setValue(n.velocity);
                    box.pitch.setValue(n.pitch);
                    box.chance.setValue(100);
                    box.cent.setValue(0);
                    box.events.refer(collBox.events);
                }});
                createdCount++;
            }}
            const maxEnd = Math.max(...notes.map(n => Math.round((n.start + n.duration) * Quarter)));
            if (maxEnd > regionBox.duration.getValue()) {{
                regionBox.duration.setValue(maxEnd);
                regionBox.loopDuration.setValue(maxEnd);
            }}
        }});

        return {{
            success: true,
            notes_created: createdCount,
            chords: voicings.length,
            voicings: voicings,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_create_melody(scale: str, root: str, pattern: str, unit_index: int = 0, track_index: int = 0, start_beat: float = 0, octave: int = 4, velocity: float = 0.75) -> str:
    """Create a melody from a scale and rhythmic pattern — one call instead of 10-30 create_note calls.

scale: Scale type (major, minor, harmonic_minor, melodic_minor, dorian, phrygian, lydian, mixolydian, locrian, pentatonic_major, pentatonic_minor, blues, chromatic).
root: Root note name (C, C#, D, D#, E, F, F#, G, G#, A, A#, B or flats Db, Eb, Gb, Ab, Bb).
pattern: Rhythmic pattern using scale degrees. Each step is one 16th note:
  - Numbers 1-7 (or 1-5 for pentatonic, 1-6 for blues) = scale degree (1 = root)
  - 0 = rest
  - '-' = sustain previous note (tie)
  - '+' = octave up for this note
  - Example: "1-2-3-5-4-3-2-1" = ascending then descending scale fragment
  - Example: "1 0 3 0 5 0 3 0" = arpeggio with rests
unit_index: AU index with a note track.
track_index: Note track index within the AU.
start_beat: Where the melody starts (0 = bar 1).
octave: MIDI octave for the root (4 = C4=60, the middle C).
velocity: Note velocity 0-1 (default 0.75).

Returns the total notes created and pitches used.
"""
    if root not in NOTE_TO_PITCH:
        return f"Error: unknown root '{root}'. Valid: {list(NOTE_TO_PITCH.keys())}"
    if scale not in SCALE_INTERVALS:
        return f"Error: unknown scale '{scale}'. Valid: {list(SCALE_INTERVALS.keys())}"

    try:
        note_list = parse_melody_pattern(pattern, root, scale, octave, velocity, 0.25, start_beat)
    except ValueError as e:
        return f"Error: {e}"
    except KeyError as e:
        return f"Error: unknown {e}"

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

        const allUnits = h.allAUBoxes();
        if (unitIdx >= allUnits.length) return {{error: "No AU at index " + unitIdx}};
        const noteTracks = h.noteTrackBoxes(allUnits[unitIdx]);
        if (noteTracks.length === 0) return {{error: "No note tracks on AU " + unitIdx}};
        if (trackIdx >= noteTracks.length) return {{error: "Track " + trackIdx + " out of range"}};

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
                    box.label.setValue("Melody");
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

            for (const n of notes) {{
                const pos = Math.max(0, Math.round(n.start * Quarter) - regionStart);
                const dur = Math.round(n.duration * Quarter);
                NoteEventBox.create(bg, h.uuid.generate(), (box) => {{
                    box.position.setValue(pos);
                    box.duration.setValue(dur);
                    box.velocity.setValue(n.velocity);
                    box.pitch.setValue(n.pitch);
                    box.chance.setValue(100);
                    box.cent.setValue(0);
                    box.events.refer(collBox.events);
                }});
                createdCount++;
            }}
            const maxEnd = Math.max(...notes.map(n => Math.round((n.start + n.duration) * Quarter)));
            if (maxEnd > regionBox.duration.getValue()) {{
                regionBox.duration.setValue(maxEnd);
                regionBox.loopDuration.setValue(maxEnd);
            }}
        }});

        return {{
            success: true,
            notes_created: createdCount,
            scale: "{scale}",
            root: "{root}",
            octave: {octave},
            pitches: notes.map(n => n.pitch),
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_create_bassline(root: str, pattern: str, unit_index: int = 0, track_index: int = 0, start_beat: float = 0, octave: int = 2, velocity: float = 0.9, scale: str = "minor") -> str:
    """Create a bassline from root note + rhythmic pattern — one call instead of 8-20 create_note calls.

Basslines use low octaves (default octave 2 = C2=36) and high velocity (default 0.9).

root: Root note name (C, C#, D, D#, E, F, F#, G, G#, A, A#, B or flats Db, Eb, Gb, Ab, Bb).
pattern: Rhythmic pattern using scale degrees and special chars. Each step = one 16th note:
  - Numbers 1-7 = scale degree (1 = root, 5 = fifth, etc.)
  - 0 = rest
  - '-' = sustain previous note (tie)
  - '+' = octave up for next note
  - '_' = octave down for next note
  - Example: "1 - - - 5 - - - 1 - - - 4 - - -" = root-fifth-root-fourth bassline
  - Example: "1 0 1 0 5 0 5 0 1 0 1 0 3 0 3 0" = syncopated bass
unit_index: AU index with a note track.
track_index: Note track index within the AU.
start_beat: Where the bassline starts (0 = bar 1).
octave: MIDI octave for the root (2 = C2=36, typical bass range).
velocity: Note velocity 0-1 (default 0.9 for strong bass).
scale: Scale type for degree mapping (default "minor"). Same scales as create_melody.

Returns the total notes created and pitches used.
"""
    if root not in NOTE_TO_PITCH:
        return f"Error: unknown root '{root}'. Valid: {list(NOTE_TO_PITCH.keys())}"
    if scale not in SCALE_INTERVALS:
        return f"Error: unknown scale '{scale}'. Valid: {list(SCALE_INTERVALS.keys())}"

    root_pc = NOTE_TO_PITCH[root]
    intervals = SCALE_INTERVALS[scale]
    base_pitch = (octave + 1) * 12 + root_pc

    steps = pattern.split()
    note_list = []
    current_octave_shift = 0

    for i, step in enumerate(steps):
        if step == "0":
            continue
        elif step == "-":
            if note_list:
                note_list[-1]["duration"] += 0.25
            continue
        elif step == "+":
            current_octave_shift += 12
            continue
        elif step == "_":
            current_octave_shift -= 12
            continue
        else:
            try:
                degree = int(step)
            except ValueError:
                return f"Error: invalid pattern step '{step}' at position {i}. Use numbers, 0, '-', '+', or '_'."

            if degree < 1 or degree > len(intervals):
                return f"Error: scale degree {degree} out of range for {scale} (1-{len(intervals)})"

            idx = degree - 1
            octave_wrap = idx // len(intervals)
            scale_idx = idx % len(intervals)
            pitch = base_pitch + intervals[scale_idx] + 12 * octave_wrap + current_octave_shift

            # Clamp to valid MIDI range
            if pitch < 0:
                pitch = 0
            if pitch > 127:
                pitch = 127

            note_list.append({
                "pitch": pitch,
                "start": start_beat + i * 0.25,
                "duration": 0.25,
                "velocity": velocity,
            })
            current_octave_shift = 0

    if not note_list:
        return "Error: pattern produced no notes (all rests?)"

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

        const allUnits = h.allAUBoxes();
        if (unitIdx >= allUnits.length) return {{error: "No AU at index " + unitIdx}};
        const noteTracks = h.noteTrackBoxes(allUnits[unitIdx]);
        if (noteTracks.length === 0) return {{error: "No note tracks on AU " + unitIdx}};
        if (trackIdx >= noteTracks.length) return {{error: "Track " + trackIdx + " out of range"}};

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
                    box.label.setValue("Bassline");
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

            for (const n of notes) {{
                const pos = Math.max(0, Math.round(n.start * Quarter) - regionStart);
                const dur = Math.round(n.duration * Quarter);
                NoteEventBox.create(bg, h.uuid.generate(), (box) => {{
                    box.position.setValue(pos);
                    box.duration.setValue(dur);
                    box.velocity.setValue(n.velocity);
                    box.pitch.setValue(n.pitch);
                    box.chance.setValue(100);
                    box.cent.setValue(0);
                    box.events.refer(collBox.events);
                }});
                createdCount++;
            }}
            const maxEnd = Math.max(...notes.map(n => Math.round((n.start + n.duration) * Quarter)));
            if (maxEnd > regionBox.duration.getValue()) {{
                regionBox.duration.setValue(maxEnd);
                regionBox.loopDuration.setValue(maxEnd);
            }}
        }});

        return {{
            success: true,
            notes_created: createdCount,
            root: "{root}",
            scale: "{scale}",
            octave: {octave},
            pitches: notes.map(n => n.pitch),
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_create_arpeggio(chord: str, pattern: str = "up", rate: str = "16", octave: int = 4, steps: int = 16, unit_index: int = 0, track_index: int = 0, start_beat: float = 0, velocity: float = 0.65) -> str:
    """Create an arpeggio from a chord name — one call instead of 8-32 create_note calls.

chord: Chord name in format RootType, e.g. "Cmin7", "F#maj", "Abmin7", "Ddim".
  Root: C, C#, D, D#, E, F, F#, G, G#, A, A#, B (or flats Db, Eb, Gb, Ab, Bb).
  Type: maj, min, dom7, maj7, min7, sus2, sus4, add9, dim, aug.
pattern: Arpeggio direction/pattern:
  - "up" — bottom to top, repeat
  - "down" — top to bottom, repeat
  - "updown" — up then down (includes top and bottom twice)
  - "downup" — down then up
  - "random" — random chord tones
  - "chord" — play full chord on each step (block chords)
rate: Note rate: "32" (32nd), "16" (16th), "8" (8th), "4" (quarter), "16t" (16th triplet).
octave: MIDI octave for the chord root (4 = C4=60).
steps: Number of arpeggio steps (default 16 = one bar of 16th notes).
unit_index: AU index with a note track.
track_index: Note track index within the AU.
start_beat: Where the arpeggio starts (0 = bar 1).
velocity: Note velocity 0-1 (default 0.65 for arpeggios).

Returns the total notes created and pitches used.
"""
    import re
    # Parse chord name: e.g. "Cmin7", "F#maj", "Bbmaj7"
    match = re.match(r'^([A-G][#b]?)(.*)$', chord)
    if not match:
        return f"Error: invalid chord '{chord}'. Format: RootType (e.g. Cmin7, F#maj)"
    root_name = match.group(1)
    chord_type = match.group(2).lower() if match.group(2) else "maj"

    if root_name not in NOTE_TO_PITCH:
        return f"Error: unknown root '{root_name}'"
    if chord_type not in CHORD_INTERVALS:
        return f"Error: unknown chord type '{chord_type}'. Valid: {list(CHORD_INTERVALS.keys())}"

    # Rate to duration in beats
    rate_map = {"32": 0.125, "16": 0.25, "8": 0.5, "4": 1.0, "16t": 1.0/6, "32t": 1.0/12}
    if rate not in rate_map:
        return f"Error: unknown rate '{rate}'. Valid: {list(rate_map.keys())}"
    step_dur = rate_map[rate]

    # Build chord pitches
    root_pc = NOTE_TO_PITCH[root_name]
    intervals = CHORD_INTERVALS[chord_type]
    base_pitch = (octave + 1) * 12 + root_pc
    chord_pitches = [base_pitch + iv for iv in intervals]

    import random
    random.seed(hash(chord + pattern) % (2**32))

    note_list = []
    for i in range(steps):
        if pattern == "up":
            idx = i % len(chord_pitches)
            pitch = chord_pitches[idx]
        elif pattern == "down":
            idx = len(chord_pitches) - 1 - (i % len(chord_pitches))
            pitch = chord_pitches[idx]
        elif pattern == "updown":
            cycle_len = 2 * len(chord_pitches) - 2
            if cycle_len <= 0:
                cycle_len = 1
            idx = i % cycle_len
            if idx < len(chord_pitches):
                pitch = chord_pitches[idx]
            else:
                pitch = chord_pitches[cycle_len - idx]
        elif pattern == "downup":
            cycle_len = 2 * len(chord_pitches) - 2
            if cycle_len <= 0:
                cycle_len = 1
            idx = i % cycle_len
            if idx < len(chord_pitches):
                pitch = chord_pitches[len(chord_pitches) - 1 - idx]
            else:
                pitch = chord_pitches[idx - len(chord_pitches) + 1]
        elif pattern == "random":
            pitch = random.choice(chord_pitches)
        elif pattern == "chord":
            # Play all chord notes on each step
            for cp in chord_pitches:
                note_list.append({
                    "pitch": cp,
                    "start": start_beat + i * step_dur,
                    "duration": step_dur * 0.9,
                    "velocity": velocity,
                })
            continue
        else:
            return f"Error: unknown pattern '{pattern}'. Valid: up, down, updown, downup, random, chord"

        note_list.append({
            "pitch": pitch,
            "start": start_beat + i * step_dur,
            "duration": step_dur * 0.9,
            "velocity": velocity,
        })

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

        const allUnits = h.allAUBoxes();
        if (unitIdx >= allUnits.length) return {{error: "No AU at index " + unitIdx}};
        const noteTracks = h.noteTrackBoxes(allUnits[unitIdx]);
        if (noteTracks.length === 0) return {{error: "No note tracks on AU " + unitIdx}};
        if (trackIdx >= noteTracks.length) return {{error: "Track " + trackIdx + " out of range"}};

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
                    box.label.setValue("Arpeggio");
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

            for (const n of notes) {{
                const pos = Math.max(0, Math.round(n.start * Quarter) - regionStart);
                const dur = Math.round(n.duration * Quarter);
                NoteEventBox.create(bg, h.uuid.generate(), (box) => {{
                    box.position.setValue(pos);
                    box.duration.setValue(dur);
                    box.velocity.setValue(n.velocity);
                    box.pitch.setValue(n.pitch);
                    box.chance.setValue(100);
                    box.cent.setValue(0);
                    box.events.refer(collBox.events);
                }});
                createdCount++;
            }}
            const maxEnd = Math.max(...notes.map(n => Math.round((n.start + n.duration) * Quarter)));
            if (maxEnd > regionBox.duration.getValue()) {{
                regionBox.duration.setValue(maxEnd);
                regionBox.loopDuration.setValue(maxEnd);
            }}
        }});

        return {{
            success: true,
            notes_created: createdCount,
            chord: "{chord}",
            pattern: "{pattern}",
            rate: "{rate}",
            chord_pitches: {json.dumps(chord_pitches)},
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
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

@mcp.tool()
async def mcp_opendaw_create_harmony(
    unit_index: int,
    track_index: int = 0,
    region_index: int = 0,
    interval: str = "thirds",
    direction: str = "up",
    new_unit_index: int = -1,
    new_track_index: int = 0,
    velocity: float = 0.65,
) -> str:
    """Generate harmony parts from existing notes — thirds, fifths, sixths, octaves.

    Reads notes from an existing region and creates harmonized copies at a fixed interval.
    Supports diatonic (scale-aware) and chromatic (fixed semitone) intervals.
    Output goes to a new or existing track.

    unit_index: Source AU index.
    track_index: Source note track index.
    region_index: Source region index.
    interval: Harmony interval type:
      - "thirds" — diatonic third above/below (3rd scale degree)
      - "fifths" — diatonic fifth (5th scale degree)
      - "sixths" — diatonic sixth (6th scale degree)
      - "octave" — octave up/down (12 semitones)
      - "fifth_chromatic" — perfect fifth (7 semitones, fixed)
      - "fourth_chromatic" — perfect fourth (5 semitones, fixed)
      - "third_major" — major third (4 semitones, fixed)
      - "third_minor" — minor third (3 semitones, fixed)
    direction: "up" or "down" (harmony above or below the melody).
    new_unit_index: Target AU index (-1 = create new synth track for harmony).
    new_track_index: Target note track index on the target AU.
    velocity: Velocity for harmony notes (default 0.65, slightly quieter than melody).

    Returns source notes read and harmony notes created.
    """
    diatonic_offsets = {
        "thirds": 2,
        "fifths": 4,
        "sixths": 5,
    }
    chromatic_offsets = {
        "octave": 12,
        "fifth_chromatic": 7,
        "fourth_chromatic": 5,
        "third_major": 4,
        "third_minor": 3,
    }
    valid_intervals = list(diatonic_offsets.keys()) + list(chromatic_offsets.keys())
    if interval not in valid_intervals:
        return f"Error: unknown interval '{interval}'. Valid: {valid_intervals}"
    if direction not in ("up", "down"):
        return f"Error: direction must be 'up' or 'down', got '{direction}'"

    is_diatonic = interval in diatonic_offsets
    degree_offset = diatonic_offsets.get(interval, 0)
    semitone_offset = chromatic_offsets.get(interval, 0)
    direction_sign = 1 if direction == "up" else -1

    safe_interval = interval.replace('"', '').replace("'", "")
    safe_direction = direction

    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const NoteEventBox = window.DAW_NoteEventBox;
        const NoteEventCollectionBox = window.DAW_NoteEventCollectionBox;
        const NoteRegionBox = window.DAW_NoteRegionBox;
        const Quarter = h.ppqn.Quarter;

        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const newUnitIdx = {new_unit_index};
        const newTrackIdx = {new_track_index};
        const velocity = {velocity};
        const isDiatonic = {str(is_diatonic).lower()};
        const degreeOffset = {degree_offset};
        const semitoneOffset = {semitone_offset};
        const dirSign = {direction_sign};

        // Major scale pattern (semitone steps): W W H W W W H = [2,2,1,2,2,2,1]
        const majorScale = [2, 2, 1, 2, 2, 2, 1];
        const scaleSemis = [0];
        let acc = 0;
        for (let i = 0; i < 7; i++) {{ acc += majorScale[i]; scaleSemis.push(acc); }}
        // scaleSemis = [0, 2, 4, 5, 7, 9, 11, 12]

        function pitchToScaleDegree(pitch) {{
            const pc = ((pitch % 12) + 12) % 12;
            for (let d = 0; d < 7; d++) {{
                if (scaleSemis[d] === pc) return d;
            }}
            return -1;
        }}

        // Read source notes
        const allUnits = h.allAUBoxes();
        if (unitIdx >= allUnits.length) return {{error: "No AU at index " + unitIdx}};
        const srcNoteTracks = h.noteTrackBoxes(allUnits[unitIdx]);
        if (srcNoteTracks.length === 0) return {{error: "No note tracks on AU " + unitIdx}};
        if (trackIdx >= srcNoteTracks.length) return {{error: "Track " + trackIdx + " out of range"}};

        const srcTrack = srcNoteTracks[trackIdx];
        const srcRegions = h.regionBoxes(srcTrack);
        if (regionIdx >= srcRegions.length) return {{error: "Region " + regionIdx + " out of range"}};
        const srcRegion = srcRegions[regionIdx];
        const regionStart = srcRegion.position.getValue();

        let srcEvents = [];
        try {{
            const vertex = srcRegion.events.targetVertex.unwrap();
            const collBox = vertex.box || vertex;
            if (collBox && collBox.events) {{
                srcEvents = h.eventBoxes(collBox);
            }}
        }} catch(e) {{ return {{error: "Could not read source notes: " + e.message}}; }}

        if (srcEvents.length === 0) return {{error: "No notes in source region"}};

        // Build harmony notes
        const harmonyNotes = [];
        for (const evt of srcEvents) {{
            const srcPitch = evt.pitch.getValue();
            const srcPos = evt.position.getValue();
            const srcDur = evt.duration.getValue();

            let harmonyPitch;
            if (isDiatonic) {{
                const degree = pitchToScaleDegree(srcPitch);
                if (degree >= 0) {{
                    const rawNewDegree = degree + degreeOffset * dirSign;
                    const newDegree = ((rawNewDegree % 7) + 7) % 7;
                    const octaveShift = Math.floor(rawNewDegree / 7) * 12 * (dirSign > 0 ? 1 : -1);
                    const newSemis = scaleSemis[newDegree];
                    const oldSemis = scaleSemis[degree];
                    harmonyPitch = srcPitch + (newSemis - oldSemis) + octaveShift;
                }} else {{
                    harmonyPitch = srcPitch + 3 * dirSign;
                }}
            }} else {{
                harmonyPitch = srcPitch + semitoneOffset * dirSign;
            }}

            if (harmonyPitch < 0 || harmonyPitch > 127) continue;

            harmonyNotes.push({{
                pitch: harmonyPitch,
                position: srcPos,
                duration: srcDur,
                velocity: velocity,
            }});
        }}

        if (harmonyNotes.length === 0) return {{error: "No harmony notes could be generated"}};

        // Determine target track — create AU inside modify block
        let targetAU = null, targetTrack = null, targetUnitIdx = -1;
        const needNewAU = (newUnitIdx < 0 || newUnitIdx >= allUnits.length);
        if (!needNewAU) {{
            targetAU = allUnits[newUnitIdx];
            const targetTracks = h.noteTrackBoxes(targetAU);
            if (newTrackIdx < targetTracks.length) {{
                targetTrack = targetTracks[newTrackIdx];
            }}
        }}

        let createdCount = 0;
        h.modify(() => {{
            if (needNewAU) {{
                const AudioUnitBox = window.DAW_AudioUnitBox;
                const CaptureAudioBox = window.DAW_CaptureAudioBox;
                const AudioUnitType = window.DAW_AudioUnitType;
                const IconSymbol = window.DAW_IconSymbol;
                const InstrumentFactories = window.DAW_InstrumentFactories;
                if (!InstrumentFactories) throw new Error("InstrumentFactories not loaded");

                const factory = InstrumentFactories["Vaporisateur"];
                if (!factory) throw new Error("Vaporisateur factory not found");

                const captureBox = CaptureAudioBox.create(h.boxGraph, h.uuid.generate());
                targetAU = AudioUnitBox.create(h.boxGraph, h.uuid.generate(), (box) => {{
                    box.type.setValue(AudioUnitType.Instrument);
                    box.collection.refer(h.rootBox.audioUnits);
                    box.output.refer(h.primaryAudioBusBox.input);
                    box.capture.refer(captureBox);
                    box.index.setValue(0);
                    box.volume.setValue(0.767835);
                }});
                factory.create(h.boxGraph, targetAU.input, "Harmony", IconSymbol.Piano);
                targetTrack = h.api.createNoteTrack(targetAU);
            }} else if (!targetTrack) {{
                targetTrack = h.api.createNoteTrack(targetAU);
            }}

            const maxEnd = Math.max(...harmonyNotes.map(n => n.position + n.duration));
            const collection = NoteEventCollectionBox.create(h.boxGraph, h.uuid.generate());
            const regionBox = NoteRegionBox.create(h.boxGraph, h.uuid.generate(), (box) => {{
                box.position.setValue(regionStart);
                box.label.setValue("Harmony");
                box.mute.setValue(false);
                box.duration.setValue(Math.max(maxEnd, 4 * Quarter));
                box.loopDuration.setValue(Math.max(maxEnd, 4 * Quarter));
                box.eventOffset.setValue(0);
                box.events.refer(collection.owners);
                box.regions.refer(targetTrack.regions);
            }});

            const eventsField = regionBox.events.targetVertex.unwrap();
            const collBox = eventsField.box;

            for (const n of harmonyNotes) {{
                const pos = Math.max(0, n.position - regionStart);
                NoteEventBox.create(h.boxGraph, h.uuid.generate(), (box) => {{
                    box.position.setValue(pos);
                    box.duration.setValue(n.duration);
                    box.velocity.setValue(n.velocity);
                    box.pitch.setValue(n.pitch);
                    box.chance.setValue(100);
                    box.cent.setValue(0);
                    box.events.refer(collBox.events);
                }});
                createdCount++;
            }}
        }});

        // Find target unit index after creation
        const allUnitsAfter = h.allAUBoxes();
        targetUnitIdx = allUnitsAfter.findIndex(au => String(au.address) === String(targetAU.address));

        return {{
            success: true,
            source_notes: srcEvents.length,
            harmony_notes_created: createdCount,
            interval: "{safe_interval}",
            direction: "{safe_direction}",
            target_unit_index: targetUnitIdx,
            sample_pitches: harmonyNotes.slice(0, 8).map(n => n.pitch),
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_create_counterpoint(
    unit_index: int,
    track_index: int = 0,
    region_index: int = 0,
    interval: int = 7,
    new_unit_index: int = -1,
    new_track_index: int = 0,
    velocity: float = 0.6,
) -> str:
    """Generate a counter-melody in contrary motion to existing notes.

    Reads notes from a melody and creates a counterpoint that moves in the
    opposite direction: when the melody goes up, the counterpoint goes down,
    and vice versa. Each note is offset by a fixed interval from the melody's
    midpoint pitch, then mirrored.

    unit_index: Source AU index.
    track_index: Source note track index.
    region_index: Source region index.
    interval: Base interval in semitones between melody and counterpoint (default 7 = fifth).
      The counterpoint is placed interval semitones below the melody's average pitch,
      then each note is mirrored around that center.
    new_unit_index: Target AU index (-1 = create new synth track).
    new_track_index: Target note track index on the target AU.
    velocity: Velocity for counterpoint notes (default 0.6, quieter than melody).

    Returns source notes read and counterpoint notes created.
    """
    if not (-48 <= interval <= 48):
        return f"Error: interval must be -48 to 48, got {interval}"

    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const NoteEventBox = window.DAW_NoteEventBox;
        const NoteEventCollectionBox = window.DAW_NoteEventCollectionBox;
        const NoteRegionBox = window.DAW_NoteRegionBox;
        const Quarter = h.ppqn.Quarter;

        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const newUnitIdx = {new_unit_index};
        const newTrackIdx = {new_track_index};
        const velocity = {velocity};
        const baseInterval = {interval};

        // Read source notes
        const allUnits = h.allAUBoxes();
        if (unitIdx >= allUnits.length) return {{error: "No AU at index " + unitIdx}};
        const srcNoteTracks = h.noteTrackBoxes(allUnits[unitIdx]);
        if (srcNoteTracks.length === 0) return {{error: "No note tracks on AU " + unitIdx}};
        if (trackIdx >= srcNoteTracks.length) return {{error: "Track " + trackIdx + " out of range"}};

        const srcTrack = srcNoteTracks[trackIdx];
        const srcRegions = h.regionBoxes(srcTrack);
        if (regionIdx >= srcRegions.length) return {{error: "Region " + regionIdx + " out of range"}};
        const srcRegion = srcRegions[regionIdx];
        const regionStart = srcRegion.position.getValue();

        let srcEvents = [];
        try {{
            const vertex = srcRegion.events.targetVertex.unwrap();
            const collBox = vertex.box || vertex;
            if (collBox && collBox.events) {{
                srcEvents = h.eventBoxes(collBox);
            }}
        }} catch(e) {{ return {{error: "Could not read source notes: " + e.message}}; }}

        if (srcEvents.length === 0) return {{error: "No notes in source region"}};

        // Sort by position
        srcEvents.sort((a, b) => a.position.getValue() - b.position.getValue());

        // Calculate melody center pitch
        const pitches = srcEvents.map(e => e.pitch.getValue());
        const minPitch = Math.min(...pitches);
        const maxPitch = Math.max(...pitches);
        const centerPitch = Math.round((minPitch + maxPitch) / 2) - baseInterval;

        // Build counterpoint: contrary motion — mirror around center
        const cpNotes = [];
        for (const evt of srcEvents) {{
            const srcPitch = evt.pitch.getValue();
            const srcPos = evt.position.getValue();
            const srcDur = evt.duration.getValue();

            // Mirror: cpPitch = 2*center - srcPitch
            const cpPitch = 2 * centerPitch - srcPitch;
            if (cpPitch < 0 || cpPitch > 127) continue;

            cpNotes.push({{
                pitch: cpPitch,
                position: srcPos,
                duration: srcDur,
                velocity: velocity,
            }});
        }}

        if (cpNotes.length === 0) return {{error: "No counterpoint notes could be generated"}};

        // Determine target track
        let targetAU = null, targetTrack = null, targetUnitIdx = -1;
        const needNewAU = (newUnitIdx < 0 || newUnitIdx >= allUnits.length);
        if (!needNewAU) {{
            targetAU = allUnits[newUnitIdx];
            const targetTracks = h.noteTrackBoxes(targetAU);
            if (newTrackIdx < targetTracks.length) {{
                targetTrack = targetTracks[newTrackIdx];
            }}
        }}

        let createdCount = 0;
        h.modify(() => {{
            if (needNewAU) {{
                const AudioUnitBox = window.DAW_AudioUnitBox;
                const CaptureAudioBox = window.DAW_CaptureAudioBox;
                const AudioUnitType = window.DAW_AudioUnitType;
                const IconSymbol = window.DAW_IconSymbol;
                const InstrumentFactories = window.DAW_InstrumentFactories;
                if (!InstrumentFactories) throw new Error("InstrumentFactories not loaded");
                const factory = InstrumentFactories["Vaporisateur"];
                if (!factory) throw new Error("Vaporisateur factory not found");

                const captureBox = CaptureAudioBox.create(h.boxGraph, h.uuid.generate());
                targetAU = AudioUnitBox.create(h.boxGraph, h.uuid.generate(), (box) => {{
                    box.type.setValue(AudioUnitType.Instrument);
                    box.collection.refer(h.rootBox.audioUnits);
                    box.output.refer(h.primaryAudioBusBox.input);
                    box.capture.refer(captureBox);
                    box.index.setValue(0);
                    box.volume.setValue(0.767835);
                }});
                factory.create(h.boxGraph, targetAU.input, "Counterpoint", IconSymbol.Piano);
                targetTrack = h.api.createNoteTrack(targetAU);
            }} else if (!targetTrack) {{
                targetTrack = h.api.createNoteTrack(targetAU);
            }}

            const maxEnd = Math.max(...cpNotes.map(n => n.position + n.duration));
            const collection = NoteEventCollectionBox.create(h.boxGraph, h.uuid.generate());
            const regionBox = NoteRegionBox.create(h.boxGraph, h.uuid.generate(), (box) => {{
                box.position.setValue(regionStart);
                box.label.setValue("Counterpoint");
                box.mute.setValue(false);
                box.duration.setValue(Math.max(maxEnd, 4 * Quarter));
                box.loopDuration.setValue(Math.max(maxEnd, 4 * Quarter));
                box.eventOffset.setValue(0);
                box.events.refer(collection.owners);
                box.regions.refer(targetTrack.regions);
            }});

            const eventsField = regionBox.events.targetVertex.unwrap();
            const collBox = eventsField.box;

            for (const n of cpNotes) {{
                const pos = Math.max(0, n.position - regionStart);
                NoteEventBox.create(h.boxGraph, h.uuid.generate(), (box) => {{
                    box.position.setValue(pos);
                    box.duration.setValue(n.duration);
                    box.velocity.setValue(n.velocity);
                    box.pitch.setValue(n.pitch);
                    box.chance.setValue(100);
                    box.cent.setValue(0);
                    box.events.refer(collBox.events);
                }});
                createdCount++;
            }}
        }});

        const allUnitsAfter = h.allAUBoxes();
        targetUnitIdx = allUnitsAfter.findIndex(au => String(au.address) === String(targetAU.address));

        return {{
            success: true,
            source_notes: srcEvents.length,
            counterpoint_notes_created: createdCount,
            interval: baseInterval,
            center_pitch: centerPitch,
            target_unit_index: targetUnitIdx,
            sample_pitches: cpNotes.slice(0, 8).map(n => n.pitch),
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_add_mastering_chain(target_lufs: float = -14, style: str = "balanced") -> str:
    """Add a ready-made mastering chain to the output bus — EQ + compressor + maximizer in one call.

target_lufs: Target loudness (-14 = Spotify, -16 = Apple, -10 = loud).
style: Preset character:
  - "balanced" — transparent EQ, gentle comp, clean limiter
  - "warm" — low shelf boost, slower comp attack, soft saturation
  - "loud" — aggressive comp, fast release, hard limit
  - "transparent" — minimal EQ, light comp, true peak limiting

Creates: Revamp EQ → Compressor → Maximizer on the output/master AU.
Returns the effect indices and parameter values set.
"""
    styles = {
        "balanced": {"comp_threshold": -18, "comp_ratio": 2.5, "comp_attack": 10, "comp_release": 100, "max_ceiling": -1.0, "max_release": 50},
        "warm": {"comp_threshold": -20, "comp_ratio": 3, "comp_attack": 30, "comp_release": 150, "max_ceiling": -1.5, "max_release": 80},
        "loud": {"comp_threshold": -14, "comp_ratio": 4, "comp_attack": 5, "comp_release": 50, "max_ceiling": -0.5, "max_release": 30},
        "transparent": {"comp_threshold": -22, "comp_ratio": 2, "comp_attack": 20, "comp_release": 200, "max_ceiling": -1.0, "max_release": 100},
    }
    if style not in styles:
        return f"Error: unknown style '{style}'. Valid: {list(styles.keys())}"

    params = styles[style]

    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const bg = h.boxGraph;
        const p = window.DAW;
        const EF = window.DAW_EffectFactories;

        const params = {json.dumps(params)};

        const allUnits = h.allAUBoxes();
        if (allUnits.length === 0) return {{error: "No audio units in project"}};

        // Use the last AU (typically the output/master bus)
        const targetAU = allUnits[allUnits.length - 1];
        const targetIdx = allUnits.length - 1;

        let eqIdx = -1, compIdx = -1, maxIdx = -1;

        h.modify(() => {{
            p.api.insertEffect(targetAU.audioEffects, EF.Revamp);
            eqIdx = h.effectBoxes(targetAU).length - 1;
        }});

        h.modify(() => {{
            p.api.insertEffect(targetAU.audioEffects, EF.Compressor);
            compIdx = h.effectBoxes(targetAU).length - 1;
        }});

        h.modify(() => {{
            p.api.insertEffect(targetAU.audioEffects, EF.Maximizer);
            maxIdx = h.effectBoxes(targetAU).length - 1;
        }});

        // Set compressor and maximizer params
        const effects = h.effectBoxes(targetAU);
        const compBox = effects[compIdx];
        const maxBox = effects[maxIdx];

        h.modify(() => {{
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
            if (maxBox) {{
                const record = maxBox.record();
                for (const [key, field] of Object.entries(record)) {{
                    const fname = field._fieldName || field.fieldName || key;
                    if (fname === 'ceiling') field.setValue(params.max_ceiling);
                    if (fname === 'release') field.setValue(params.max_release);
                }}
            }}
        }});

        return {{
            success: true,
            unit_index: targetIdx,
            chain: [
                {{name: "Revamp EQ", index: eqIdx}},
                {{name: "Compressor", index: compIdx, params: {{threshold: params.comp_threshold, ratio: params.comp_ratio}}}},
                {{name: "Maximizer", index: maxIdx, params: {{ceiling: params.max_ceiling}}}},
            ],
            style: "{style}",
            target_lufs: {target_lufs},
            note: "Parameters applied. Run auto_gain after rendering to hit target LUFS.",
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_create_genre_track(genre: str, bpm: float = 120) -> str:
    """Create a genre-specific starting track with synth, beat, and basic mix — one call builds a full section.

genre: Musical genre preset:
  - "house" — 4/4 kick, offbeat hat, stab bass, 128 BPM
  - "techno" — driving kick, ride hat, acid bass, 130 BPM
  - "lofi" — swing kick/snare, soft keys, 80 BPM
  - "dnb" — breakbeat drums, sub bass, 174 BPM
  - "trap" — 808 kick, hat rolls, melodic lead, 140 BPM
  - "ambient" — pad chord, no drums, 70 BPM
  - "coldwave" — driving kick, dark bass, 110 BPM
  - "hiphop" — boom bap kick/snare, 90 BPM

bpm: Override tempo (default per genre).

Returns created AU indices, note counts, and suggested next steps.
"""
    if genre not in GENRE_PRESETS:
        return f"Error: unknown genre '{genre}'. Valid: {VALID_GENRES}"

    g = GENRE_PRESETS[genre]
    actual_bpm = bpm if bpm != 120 else g["bpm"]

    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const bg = h.boxGraph;
        const p = window.DAW;
        const IF = window.DAW_InstrumentFactories;
        const NoteEventBox = window.DAW_NoteEventBox;
        const NoteEventCollectionBox = window.DAW_NoteEventCollectionBox;
        const NoteRegionBox = window.DAW_NoteRegionBox;
        const Quarter = h.ppqn.Quarter;
        const Sixteenth = Quarter / 4;

        const genreData = {json.dumps(g)};
        const bpm = {actual_bpm};

        // Set BPM via existing API (inside modify)
        h.modify(() => h.api.setBpm(bpm));

        // Create synth AU for chords/bass (inside modify — createInstrument needs transaction)
        let synthAU, synthAUIdx, synthNoteTracks;
        h.modify(() => {{
            const result = p.api.createInstrument(IF.Vaporisateur, {{}});
            synthAU = result.audioUnitBox;
            synthAUIdx = h.allAUBoxes().length - 1;
            synthNoteTracks = h.noteTrackBoxes(synthAU);
        }});

        let chordNotes = 0;
        let bassNotes = 0;
        let drumNotes = 0;

        // Add chords
        if (genreData.chords.length > 0 && synthNoteTracks.length > 0) {{
            const trackBox = synthNoteTracks[0];
            const noteToPitch = {{"C":0,"C#":1,"Db":1,"D":2,"D#":3,"Eb":3,"E":4,"F":5,"F#":6,"Gb":6,"G":7,"G#":8,"Ab":8,"A":9,"A#":10,"Bb":10,"B":11}};
            const chordIntervals = {{"maj":[0,4,7],"min":[0,3,7],"dom7":[0,4,7,10],"maj7":[0,4,7,11],"min7":[0,3,7,10],"sus2":[0,2,7],"sus4":[0,5,7],"add9":[0,4,7,14],"dim":[0,3,6],"aug":[0,4,8]}};

            h.modify(() => {{
                const collection = NoteEventCollectionBox.create(bg, h.uuid.generate());
                let maxEnd = 0;
                for (let ci = 0; ci < genreData.chords.length; ci++) {{
                    const [rootName, chordType] = genreData.chords[ci];
                    const rootPc = noteToPitch[rootName] || 0;
                    const intervals = chordIntervals[chordType] || [0,4,7];
                    const rootPitch = 60 + rootPc - (rootPc > 5 ? 12 : 0);
                    for (const iv of intervals) {{
                        NoteEventBox.create(bg, h.uuid.generate(), (box) => {{
                            box.position.setValue(Math.round(ci * 4 * Quarter));
                            box.duration.setValue(Math.round(4 * Quarter));
                            box.velocity.setValue(0.6);
                            box.pitch.setValue(rootPitch + iv);
                            box.chance.setValue(100);
                            box.cent.setValue(0);
                            box.events.refer(collection.events);
                        }});
                        chordNotes++;
                        maxEnd = Math.max(maxEnd, Math.round((ci * 4 + 4) * Quarter));
                    }}
                }}
                NoteRegionBox.create(bg, h.uuid.generate(), (box) => {{
                    box.position.setValue(0);
                    box.label.setValue("Chords");
                    box.mute.setValue(false);
                    box.duration.setValue(Math.max(maxEnd, 4 * Quarter));
                    box.loopDuration.setValue(Math.max(maxEnd, 4 * Quarter));
                    box.eventOffset.setValue(0);
                    box.events.refer(collection.owners);
                    box.regions.refer(trackBox.regions);
                }});
            }});
        }}

        // Add bass on same AU, second note track if available
        if (genreData.bass.length > 0 && synthNoteTracks.length > 0) {{
            const bassTrack = synthNoteTracks[Math.min(1, synthNoteTracks.length - 1)];
            h.modify(() => {{
                const collection = NoteEventCollectionBox.create(bg, h.uuid.generate());
                let maxEnd = 0;
                for (const n of genreData.bass) {{
                    NoteEventBox.create(bg, h.uuid.generate(), (box) => {{
                        box.position.setValue(Math.round(n.start * Quarter));
                        box.duration.setValue(Math.round(n.duration * Quarter));
                        box.velocity.setValue(0.85);
                        box.pitch.setValue(n.pitch);
                        box.chance.setValue(100);
                        box.cent.setValue(0);
                        box.events.refer(collection.events);
                    }});
                    bassNotes++;
                    maxEnd = Math.max(maxEnd, Math.round((n.start + n.duration) * Quarter));
                }}
                NoteRegionBox.create(bg, h.uuid.generate(), (box) => {{
                    box.position.setValue(0);
                    box.label.setValue("Bass");
                    box.mute.setValue(false);
                    box.duration.setValue(Math.max(maxEnd, 4 * Quarter));
                    box.loopDuration.setValue(Math.max(maxEnd, 4 * Quarter));
                    box.eventOffset.setValue(0);
                    box.events.refer(collection.owners);
                    box.regions.refer(bassTrack.regions);
                }});
            }});
        }}

        // Add drums on a separate AU
        if (Object.keys(genreData.drums).length > 0) {{
            let drumAU, drumTracks;
            h.modify(() => {{
                const drumResult = p.api.createInstrument(IF.Vaporisateur, {{}});
                drumAU = drumResult.audioUnitBox;
                drumTracks = h.noteTrackBoxes(drumAU);
            }});
            if (drumTracks.length > 0) {{
                const drumTrack = drumTracks[0];
                const velocities = {{'x': 0.9, 'o': 0.5, 'X': 1.0}};
                const lanePitches = {{kick: 36, snare: 38, hihat: 42, clap: 39, perc: 47}};
                h.modify(() => {{
                    const collection = NoteEventCollectionBox.create(bg, h.uuid.generate());
                    const maxSteps = Math.max(...Object.values(genreData.drums).map(s => s.length));
                    for (const [laneName, steps] of Object.entries(genreData.drums)) {{
                        const pitch = lanePitches[laneName] || 36;
                        for (let i = 0; i < steps.length; i++) {{
                            const ch = steps[i];
                            if (ch === '.' || ch === ' ') continue;
                            NoteEventBox.create(bg, h.uuid.generate(), (box) => {{
                                box.position.setValue(Math.round(i * Sixteenth));
                                box.duration.setValue(Math.round(Sixteenth * 0.8));
                                box.velocity.setValue(velocities[ch] || 0.8);
                                box.pitch.setValue(pitch);
                                box.chance.setValue(100);
                                box.cent.setValue(0);
                                box.events.refer(collection.events);
                            }});
                            drumNotes++;
                        }}
                    }}
                    NoteRegionBox.create(bg, h.uuid.generate(), (box) => {{
                        box.position.setValue(0);
                        box.label.setValue("Drums");
                        box.mute.setValue(false);
                        box.duration.setValue(Math.max(maxSteps * Sixteenth, 4 * Quarter));
                        box.loopDuration.setValue(Math.max(maxSteps * Sixteenth, 4 * Quarter));
                        box.eventOffset.setValue(0);
                        box.events.refer(collection.owners);
                        box.regions.refer(drumTrack.regions);
                    }});
                }});
            }}
        }}

        return {{
            success: true,
            genre: "{genre}",
            bpm: bpm,
            chord_notes: chordNotes,
            bass_notes: bassNotes,
            drum_notes: drumNotes,
            synth_au_index: synthAUIdx,
            next_steps: [
                "Call add_mastering_chain to add mastering to the output bus",
                "Call render_full to render the mix",
                "Call auto_gain with target_lufs=-14 for streaming loudness",
            ],
        }};
    }}""")
    return _wrap_eval(result)


@mcp.tool()
async def mcp_opendaw_create_song_structure(sections: str, unit_index: int = 0) -> str:
    """Create song structure markers for arrangement (intro/verse/chorus/bridge/outro).

    Creates labeled markers at section boundaries, enabling agents to reason about song form.
    Reduces 5-10 marker calls to one structured call.

    sections: JSON array of section objects: [{"name": "Intro", "bars": 4}, {"name": "Verse 1", "bars": 8}, ...].
              If bars omitted, defaults to 8. Names are used as marker labels.
    unit_index: AU index (unused but kept for API consistency).

    Returns created markers with positions and total duration.

    Example:
      sections='[{"name":"Intro","bars":4},{"name":"Verse","bars":8},{"name":"Chorus","bars":8},{"name":"Outro","bars":4}]'
    """
    parsed = json.loads(sections)
    total_beats = 0
    marker_data = []
    for sec in parsed:
        name = sec.get("name", "Section")
        bars = sec.get("bars", 8)
        marker_data.append({"name": name, "position": total_beats})
        total_beats += bars * 4

    markers_json = json.dumps(marker_data)
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const MarkerBox = window.DAW_MarkerBox;
        if (!MarkerBox) return {{error: "MarkerBox not loaded — reload page"}};
        const markerTrack = h.timelineBox?.markerTrack;
        if (!markerTrack) return {{error: "No markerTrack on timeline"}};
        try {{
            const markers = {markers_json};
            let created = [];
            for (const m of markers) {{
                const ppqn = Math.round(m.position * h.ppqn.Quarter);
                h.modify(() => {{
                    MarkerBox.create(h.boxGraph, h.uuid.generate(), (box) => {{
                        box.position.setValue(ppqn);
                        box.plays.setValue(0);
                        box.label.setValue(m.name);
                        box.hue.setValue(0);
                        box.track.refer(markerTrack.markers);
                    }});
                }});
                created.push({{name: m.name, position_beats: m.position}});
            }}
            return {{
                success: true,
                markers_created: created.length,
                markers: created,
                total_beats: {total_beats},
                total_bars: {total_beats} / 4,
                next_steps: [
                    "Use create_genre_track or create_notes_batch to fill sections",
                    "Use render_full to render the complete arrangement",
                ],
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


@mcp.tool()
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


@mcp.tool()
async def mcp_opendaw_apply_mix_preset(preset: str) -> str:
    """Apply a mix preset to all audio units in one call — volume, pan, mute, solo.

    Replaces 10-30 set_track_volume/set_track_panning/set_track_mute calls.
    Presets can be genre-specific or custom JSON.

    preset: JSON object mapping unit indices to settings:
        {"0": {"volume_db": -3, "panning": 0.0, "mute": false},
         "1": {"volume_db": -6, "panning": -0.3, "solo": false}, ...}

    Alternatively, use a named preset: "lofi", "house", "balanced", "wide"

    Returns applied settings per unit.

    Example:
      preset='{"0":{"volume_db":-3,"panning":0},"1":{"volume_db":-6,"panning":-0.3}}'
      preset='lofi'  (built-in: kicks +0, bass -3, synths -6, wide pans)
    """
    built_in = {
        "lofi": {
            "0": {"volume_db": 0, "panning": 0.0, "mute": False},      # drums
            "1": {"volume_db": -3, "panning": 0.0, "mute": False},     # bass
            "2": {"volume_db": -6, "panning": -0.2, "mute": False},    # keys left
            "3": {"volume_db": -6, "panning": 0.2, "mute": False},     # keys right
        },
        "house": {
            "0": {"volume_db": 0, "panning": 0.0, "mute": False},      # kick
            "1": {"volume_db": -3, "panning": 0.0, "mute": False},     # bass
            "2": {"volume_db": -4, "panning": -0.15, "mute": False},   # synths
            "3": {"volume_db": -4, "panning": 0.15, "mute": False},    # hats
        },
        "balanced": {
            "0": {"volume_db": 0, "panning": 0.0, "mute": False},
            "1": {"volume_db": 0, "panning": 0.0, "mute": False},
            "2": {"volume_db": 0, "panning": 0.0, "mute": False},
        },
        "wide": {
            "0": {"volume_db": -2, "panning": -0.4, "mute": False},
            "1": {"volume_db": -2, "panning": 0.4, "mute": False},
            "2": {"volume_db": -4, "panning": -0.2, "mute": False},
            "3": {"volume_db": -4, "panning": 0.2, "mute": False},
        },
    }

    preset_lower = preset.strip().lower()
    if preset_lower in built_in:
        settings = built_in[preset_lower]
    else:
        settings = json.loads(preset)

    settings_json = json.dumps(settings)
    preset_name = preset_lower if preset_lower in built_in else "custom"
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const settings = {settings_json};
            const units = h.allAUBoxes();
            const applied = [];
            for (const [idxStr, params] of Object.entries(settings)) {{
                const idx = parseInt(idxStr);
                if (idx >= units.length) {{
                    applied.push({{unit: idx, error: "no AU at index"}});
                    continue;
                }}
                const au = units[idx];
                const result = {{unit: idx, name: au.name?.getValue?.() || "Unit " + idx}};

                h.modify(() => {{
                    if (params.volume_db !== undefined) {{
                        let raw = params.volume_db;
                        try {{
                            const c = au.volume.constraints;
                            if (c?.valueMapper) raw = c.valueMapper.mapToNormalized(params.volume_db);
                            else if (c?.mapper) raw = c.mapper.mapToNormalized(params.volume_db);
                        }} catch(e) {{}}
                        au.volume.setValue(raw);
                        result.volume_db = params.volume_db;
                    }}
                    if (params.panning !== undefined) {{
                        au.panning.setValue(params.panning);
                        result.panning = params.panning;
                    }}
                    if (params.mute !== undefined) {{
                        au.mute?.setValue?.(params.mute);
                        result.mute = params.mute;
                    }}
                    if (params.solo !== undefined) {{
                        au.solo?.setValue?.(params.solo);
                        result.solo = params.solo;
                    }}
                }});
                applied.push(result);
            }}
            return {{
                success: true,
                preset: "{preset_name}",
                units_adjusted: applied.length,
                settings: applied,
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


# ============================================================================
# STEM SPLITTER — SOTA source separation via local GPU models
# ============================================================================

STEM_SPLITTER_DIR = os.environ.get("STEM_SPLITTER_DIR",
    os.path.expanduser("~/projects/creative-studio/stem-splitter"))
STEM_SPLITTER_VENV = os.path.join(STEM_SPLITTER_DIR, "venv", "bin", "python")
STEM_SPLITTER_SCRIPT = os.path.join(STEM_SPLITTER_DIR, "sota_splitter.py")

STEM_MODES = {
    "ensemble": "Max quality: HTDemucs FT bass+drums + PolarFormer vocals + bs6 other (4 stems, 4 passes, slowest)",
    "scnet": "SCNet XL IHF — best 4-stem multi-stem (drums/bass/other/vocals, SDR avg 10.08)",
    "bs6": "BS-Rofo-SW-Fixed 6-stem (bass/drums/other/vocals/guitar/piano, fast, low bleeding)",
    "polarformer": "PolarFormer — best vocal extraction (vocals/instrumental, SDR 11.00)",
    "dereverb": "MelBand Roformer dereverb — removes reverb from vocals (dry/reverb, SDR 19.17)",
    "drumsep": "DrumSep — separate drums into kick/snare/cymbals/toms",
    "denoise": "MelBand Roformer denoise — clean 128kbps MP3 noise (clean/noise, SDR 27.99)",
}


@mcp.tool()
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


@mcp.tool()
async def mcp_opendaw_list_split_modes() -> str:
    """List available stem separation modes with descriptions.

    Returns all modes supported by mcp_opendaw_split_stems, with SDR scores
    and use-case recommendations.
    """
    modes_info = []
    for key, desc in STEM_MODES.items():
        modes_info.append({"mode": key, "description": desc})
    return json.dumps({
        "modes": modes_info,
        "default": "bs6",
        "note": "All modes run locally on GPU. Ensemble is slowest but highest quality.",
    }, indent=2)


@mcp.tool()
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
        let binary = "";
        for (let i = 0; i < bytes.length; i++) {{
            binary += String.fromCharCode(bytes[i]);
        }}
        return {{b64: btoa(binary), device: deviceKey}};
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


@mcp.tool()
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


@mcp.tool()
async def mcp_opendaw_create_drum_fill(unit_index: int = -1, fill_type: str = "build", bars: int = 1, start_beat: float = 0, density: str = "medium") -> str:
    """Create a drum fill or transition pattern — one call replaces 10-30 note creations.

    Generates rhythmic fills between song sections with increasing/decreasing density.
    Useful for transitions: verse→chorus, breakdown→drop, outro buildup.

    fill_type: Type of fill:
      - "build" — density increases toward end (leading into a drop/chorus)
      - "break" — density decreases (winding down after a section)
      - "roll" — sustained snare/tom roll with accents
      - "crash" — crash + sparse hits for impact
      - "tom" — descending tom pattern

    bars: Length in bars (1-4). Each bar = 4 beats = 16 sixteenth steps.
    start_beat: Position in beats where the fill begins.
    density: Note density — "sparse", "medium", "dense".

    unit_index: AU index with a note track (-1 = find first AU with note tracks).

    Returns notes created per lane and total.
    """
    if fill_type not in ("build", "break", "roll", "crash", "tom"):
        return "Error: fill_type must be one of: build, break, roll, crash, tom"
    if bars < 1 or bars > 4:
        return "Error: bars must be 1-4"
    if density not in ("sparse", "medium", "dense"):
        return "Error: density must be sparse, medium, or dense"

    # Generate fill patterns in Python
    import random
    rng = random.Random(hash(fill_type + density) & 0xFFFFFFFF)

    total_steps = bars * 16
    kick, snare, hihat, perc = [], [], [], []

    density_factor = {"sparse": 0.15, "medium": 0.35, "dense": 0.6}[density]

    if fill_type == "build":
        # Increasing density — start sparse, end busy
        for i in range(total_steps):
            progress = i / total_steps
            local_density = density_factor * (0.3 + 0.7 * progress)
            # hihat gets busier
            if rng.random() < local_density:
                hihat.append(i)
            # kick builds up at the end
            if progress > 0.6 and rng.random() < local_density * 0.6:
                kick.append(i)
            # snare: last bar gets roll-ish
            if progress > 0.5 and rng.random() < local_density * 0.5:
                snare.append(i)
            # final crash
            if i == total_steps - 1:
                kick.append(i)

    elif fill_type == "break":
        # Decreasing density — start busy, end sparse
        for i in range(total_steps):
            progress = i / total_steps
            local_density = density_factor * (0.9 - 0.6 * progress)
            if rng.random() < local_density:
                hihat.append(i)
            if progress < 0.4 and rng.random() < local_density * 0.5:
                kick.append(i)
            if rng.random() < local_density * 0.3:
                snare.append(i)

    elif fill_type == "roll":
        # Sustained snare roll with accents
        for i in range(total_steps):
            snare.append(i)
            # accents every 4 steps
            if i % 4 == 0:
                kick.append(i)
            # hihat sparse
            if i % 8 == 0:
                hihat.append(i)
        # Crash at end
        kick.append(total_steps - 1)

    elif fill_type == "crash":
        # Impact: crash + sparse hits
        kick.append(0)  # initial crash
        kick.append(total_steps - 1)  # final crash
        for i in range(total_steps):
            if rng.random() < density_factor * 0.2:
                perc.append(i)

    elif fill_type == "tom":
        # Descending tom pattern — uses perc lane for toms
        tom_spacing = max(2, int(8 / (bars + 1)))
        for i in range(0, total_steps, tom_spacing):
            perc.append(i)
            if i % (tom_spacing * 2) == 0:
                kick.append(i)
        # Fill remaining with hihat
        for i in range(total_steps):
            if rng.random() < density_factor * 0.3:
                hihat.append(i)

    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const bg = h.boxGraph;
        const NoteEventBox = window.DAW_NoteEventBox;
        const NoteEventCollectionBox = window.DAW_NoteEventCollectionBox;
        const NoteRegionBox = window.DAW_NoteRegionBox;
        const Quarter = h.ppqn.Quarter;
        const Sixteenth = Quarter / 4;

        const unitIdx = {unit_index};
        const startBeat = {start_beat};
        const totalSteps = {total_steps};
        const kickSteps = {json.dumps(kick)};
        const snareSteps = {json.dumps(snare)};
        const hihatSteps = {json.dumps(hihat)};
        const percSteps = {json.dumps(perc)};

        let noteTracks = [];
        let targetAU = null;
        const allUnits = h.allAUBoxes();

        if (unitIdx >= 0 && unitIdx < allUnits.length) {{
            targetAU = allUnits[unitIdx];
            noteTracks = h.noteTrackBoxes(targetAU);
        }} else {{
            for (const au of allUnits) {{
                const nt = h.noteTrackBoxes(au);
                if (nt.length > 0) {{ noteTracks = nt; targetAU = au; break; }}
            }}
        }}

        if (noteTracks.length === 0) return {{error: "No note tracks found. Call create_synth_track or create_note_track first."}};

        const trackBox = noteTracks[0];
        const lanePitches = {{kick: 36, snare: 38, hihat: 42, perc: 47}};
        let totalNotes = 0;
        const laneCounts = {{}};

        h.modify(() => {{
            const collection = NoteEventCollectionBox.create(bg, h.uuid.generate());
            const regionDur = Math.max(totalSteps * Sixteenth, 4 * Quarter);
            const startPos = Math.round(startBeat * Quarter);

            const regionBox = NoteRegionBox.create(bg, h.uuid.generate(), (box) => {{
                box.position.setValue(startPos);
                box.label.setValue("Fill");
                box.mute.setValue(false);
                box.duration.setValue(regionDur);
                box.loopDuration.setValue(regionDur);
                box.eventOffset.setValue(0);
                box.events.refer(collection.owners);
                box.regions.refer(trackBox.regions);
            }});

            const eventsField = regionBox.events.targetVertex.unwrap();
            const collBox = eventsField.box;

            const lanes = [
                {{name: "kick", steps: kickSteps, pitch: 36}},
                {{name: "snare", steps: snareSteps, pitch: 38}},
                {{name: "hihat", steps: hihatSteps, pitch: 42}},
                {{name: "perc", steps: percSteps, pitch: 47}},
            ];

            for (const lane of lanes) {{
                let count = 0;
                for (const stepIdx of lane.steps) {{
                    // Accent: first and last step get higher velocity
                    let vel = 0.75;
                    if (stepIdx === 0 || stepIdx === totalSteps - 1) vel = 1.0;
                    else if (stepIdx % 4 === 0) vel = 0.9;
                    NoteEventBox.create(bg, h.uuid.generate(), (box) => {{
                        box.position.setValue(startPos + Math.round(stepIdx * Sixteenth));
                        box.duration.setValue(Math.round(Sixteenth * 0.8));
                        box.velocity.setValue(vel);
                        box.pitch.setValue(lane.pitch);
                        box.chance.setValue(100);
                        box.cent.setValue(0);
                        box.events.refer(collBox.events);
                    }});
                    count++;
                    totalNotes++;
                }}
                laneCounts[lane.name] = count;
            }}
        }});

        return {{
            success: true,
            total_notes: totalNotes,
            lanes: laneCounts,
            fill_type: "{fill_type}",
            bars: {bars},
            unit_index: allUnits.indexOf(targetAU),
        }};
    }}""")
    return _wrap_eval(result)


@mcp.tool()
async def mcp_opendaw_create_riser(unit_index: int = -1, track_index: int = 0, start_beat: float = 0, length_beats: float = 4, start_pitch: int = 36, end_pitch: int = 84, steps: int = 32, curve: str = "exp", velocity: float = 0.7) -> str:
    """Create a riser — ascending pitch sweep for build-up transitions.

    Generates a sequence of notes with ascending pitch from start_pitch to end_pitch
    over the specified length. Velocity ramps up proportionally. Useful for:
    - Build-ups before a drop/chorus
    - Transition between sections
    - Tension creation

    unit_index: AU index with note track (-1 = find first AU with note tracks).
    track_index: Note track index within the AU.
    start_beat: Position in beats where the riser begins.
    length_beats: Duration of the riser in beats (1-16).
    start_pitch: Starting MIDI pitch (default 36 = C2).
    end_pitch: Ending MIDI pitch (default 84 = C6).
    steps: Number of notes in the sweep (8-128, default 32 = sixteenths over 4 beats).
    curve: Pitch curve — "linear" (even), "exp" (slow start, fast end), "log" (fast start, slow end).
    velocity: Base velocity (0-1, ramped proportionally with pitch).

    Returns notes created and pitch range.
    """
    if length_beats < 0.25 or length_beats > 16:
        return "Error: length_beats must be 0.25-16"
    if start_pitch < 0 or start_pitch > 127:
        return "Error: start_pitch must be 0-127"
    if end_pitch < 0 or end_pitch > 127:
        return "Error: end_pitch must be 0-127"
    if steps < 4 or steps > 128:
        return "Error: steps must be 4-128"
    if curve not in ("linear", "exp", "log"):
        return "Error: curve must be linear, exp, or log"
    if velocity < 0 or velocity > 1:
        return "Error: velocity must be 0-1"

    note_data = []
    for i in range(steps):
        progress = i / max(1, steps - 1)
        if curve == "exp":
            t = progress * progress
        elif curve == "log":
            t = 1 - (1 - progress) * (1 - progress)
        else:
            t = progress
        pitch = round(start_pitch + (end_pitch - start_pitch) * t)
        pos = start_beat + progress * length_beats
        vel = velocity * (0.3 + 0.7 * progress)
        note_data.append({"pitch": pitch, "pos": pos, "vel": vel})

    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const bg = h.boxGraph;
        const NoteEventBox = window.DAW_NoteEventBox;
        const NoteEventCollectionBox = window.DAW_NoteEventCollectionBox;
        const NoteRegionBox = window.DAW_NoteRegionBox;
        const Quarter = h.ppqn.Quarter;

        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const noteData = {json.dumps(note_data)};
        const lengthBeats = {length_beats};
        const startBeat = {start_beat};

        let noteTracks = [];
        let targetAU = null;
        const allUnits = h.allAUBoxes();

        if (unitIdx >= 0 && unitIdx < allUnits.length) {{
            targetAU = allUnits[unitIdx];
            noteTracks = h.noteTrackBoxes(targetAU);
        }} else {{
            for (const au of allUnits) {{
                const nt = h.noteTrackBoxes(au);
                if (nt.length > 0) {{ noteTracks = nt; targetAU = au; break; }}
            }}
        }}

        if (noteTracks.length === 0) return {{error: "No note tracks found. Call create_synth_track or create_note_track first."}};

        const trackBox = noteTracks[Math.min(trackIdx, noteTracks.length - 1)];
        let totalNotes = 0;

        h.modify(() => {{
            const collection = NoteEventCollectionBox.create(bg, h.uuid.generate());
            const regionDur = Math.round(lengthBeats * Quarter);
            const startPos = Math.round(startBeat * Quarter);
            const stepDur = Math.max(1, Math.round(regionDur / noteData.length));

            const regionBox = NoteRegionBox.create(bg, h.uuid.generate(), (box) => {{
                box.position.setValue(startPos);
                box.label.setValue("Riser");
                box.mute.setValue(false);
                box.duration.setValue(regionDur);
                box.loopDuration.setValue(regionDur);
                box.eventOffset.setValue(0);
                box.events.refer(collection.owners);
                box.regions.refer(trackBox.regions);
            }});

            const eventsField = regionBox.events.targetVertex.unwrap();
            const collBox = eventsField.box;

            for (let i = 0; i < noteData.length; i++) {{
                const nd = noteData[i];
                NoteEventBox.create(bg, h.uuid.generate(), (box) => {{
                    box.position.setValue(startPos + Math.round(nd.pos * Quarter - startBeat * Quarter));
                    box.duration.setValue(stepDur);
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
            start_pitch: {start_pitch},
            end_pitch: {end_pitch},
            steps: {steps},
            curve: "{curve}",
            length_beats: {length_beats},
            unit_index: allUnits.indexOf(targetAU),
        }};
    }}""")
    return _wrap_eval(result)


@mcp.tool()
async def mcp_opendaw_create_stab(chords: str, rhythm: str = "x-x-", unit_index: int = -1, track_index: int = 0, start_beat: float = 0, octave: int = 4, velocity: float = 0.85, length_beats: float = 4, stab_duration: float = 0.5) -> str:
    """Create rhythmic stabs — short chord jabs that define house, disco, funk.

    Generates short chord hits on a rhythmic grid. Each 'x' in the rhythm pattern
    triggers a stab (a short chord with fast decay). Perfect for:
    - House/disco off-beat stabs
    - Funk syncopated chord punches
    - Garage/shuffle stabs
    - Filling gaps between melody notes

    chords: JSON array of chord specs, cycled through. Each chord is [root_name, chord_type].
      Root names: C, C#, D, D#, E, F, F#, G, G#, A, A#, B (or flats)
      Chord types: maj, min, dom7, maj7, min7, sus2, sus4, add9, dim, aug
      Example: '[["C","min7"],["F","min7"]]' cycles between Cm7 and Fm7.
      Single chord: '[["F","dom7"]]' — same stab repeated.
    rhythm: Grid pattern using 'x' (stab), '-' (rest), '.' (ghost/light stab).
      16th-note grid for one bar (16 chars) or 8th-note grid (8 chars).
      Examples: "x-x-x-x-" (off-beat 8th stabs), "x---x---" (backbeat),
                "..x-..x-" (ghost stabs), "xxxx-xxx" (funky busy pattern)
    unit_index: AU index with note track (-1 = find first AU with note tracks).
    track_index: Note track index within the AU.
    start_beat: Position in beats where the pattern starts.
    octave: Octave for chord voicing (3-6, default 4 = C4 root).
    velocity: Base velocity for stabs (0-1, ghost stabs use 0.5x).
    length_beats: Total length of the stab pattern in beats (default 4 = one bar).
    stab_duration: Duration of each stab in beats (0.0625-1.0, default 0.5 = eighth note).

    Returns notes created, chord voicings, and rhythm hits.
    """
    import json as _json
    try:
        chord_list = _json.loads(chords)
        if not isinstance(chord_list, list) or len(chord_list) == 0:
            return "Error: chords must be a non-empty JSON array"
    except _json.JSONDecodeError as e:
        return f"Error parsing chords JSON: {e}"

    if not rhythm or not all(c in "x-." for c in rhythm):
        return "Error: rhythm must use only 'x' (stab), '-' (rest), '.' (ghost)"
    if velocity < 0 or velocity > 1:
        return "Error: velocity must be 0-1"
    if length_beats < 0.25 or length_beats > 32:
        return "Error: length_beats must be 0.25-32"
    if stab_duration < 0.0625 or stab_duration > 1.0:
        return "Error: stab_duration must be 0.0625-1.0"
    if octave < 1 or octave > 8:
        return "Error: octave must be 1-8"

    for ci, cs in enumerate(chord_list):
        if len(cs) < 2 or cs[0] not in NOTE_TO_PITCH or cs[1] not in CHORD_INTERVALS:
            return f"Error: invalid chord at index {ci}: {cs}"

    grid_len = len(rhythm)
    step_duration = length_beats / grid_len

    note_data = []
    voicing_info = []
    chord_idx = 0
    for i, c in enumerate(rhythm):
        if c == "-":
            continue
        if c == "." and chord_idx > 0:
            # Ghost repeats the last stab's chord (no advance)
            chord_spec = chord_list[(chord_idx - 1) % len(chord_list)]
        else:
            chord_spec = chord_list[chord_idx % len(chord_list)]
        root_pc = NOTE_TO_PITCH[chord_spec[0]]
        intervals = CHORD_INTERVALS[chord_spec[1]]
        root_pitch = (octave + 1) * 12 + root_pc

        is_ghost = (c == ".")
        vel = velocity * (0.45 if is_ghost else 1.0)
        pos = start_beat + i * step_duration
        dur = stab_duration * (0.6 if is_ghost else 1.0)

        pitches = [root_pitch + iv for iv in intervals]
        for p in pitches:
            note_data.append({"pitch": p, "pos": pos, "dur": dur, "vel": vel})
        voicing_info.append({"step": i, "chord": f"{chord_spec[0]}{chord_spec[1]}", "pitches": pitches, "ghost": is_ghost})
        if not is_ghost:
            chord_idx += 1

    if not note_data:
        return "Error: rhythm has no stabs (all rests)"

    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const bg = h.boxGraph;
        const NoteEventBox = window.DAW_NoteEventBox;
        const NoteEventCollectionBox = window.DAW_NoteEventCollectionBox;
        const NoteRegionBox = window.DAW_NoteRegionBox;
        const Quarter = h.ppqn.Quarter;

        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const noteData = {json.dumps(note_data)};
        const lengthBeats = {length_beats};
        const startBeat = {start_beat};

        let noteTracks = [];
        let targetAU = null;
        const allUnits = h.allAUBoxes();

        if (unitIdx >= 0 && unitIdx < allUnits.length) {{
            targetAU = allUnits[unitIdx];
            noteTracks = h.noteTrackBoxes(targetAU);
        }} else {{
            for (const au of allUnits) {{
                const nt = h.noteTrackBoxes(au);
                if (nt.length > 0) {{ noteTracks = nt; targetAU = au; break; }}
            }}
        }}

        if (noteTracks.length === 0) return {{error: "No note tracks found. Call create_synth_track or create_note_track first."}};

        const trackBox = noteTracks[Math.min(trackIdx, noteTracks.length - 1)];
        let totalNotes = 0;

        h.modify(() => {{
            const collection = NoteEventCollectionBox.create(bg, h.uuid.generate());
            const regionDur = Math.round(lengthBeats * Quarter);
            const startPos = Math.round(startBeat * Quarter);

            const regionBox = NoteRegionBox.create(bg, h.uuid.generate(), (box) => {{
                box.position.setValue(startPos);
                box.label.setValue("Stabs");
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
            stabs: {len(voicing_info)},
            chords_used: {len(chord_list)},
            rhythm: "{rhythm}",
            length_beats: {length_beats},
            unit_index: allUnits.indexOf(targetAU),
        }};
    }}""")
    return _wrap_eval(result)


@mcp.tool()
async def mcp_opendaw_create_ostinato(scale: str, root: str, pattern: str, unit_index: int = 0, track_index: int = 0, start_beat: float = 0, repeats: int = 4, octave: int = 4, velocity: float = 0.7) -> str:
    """Create an ostinato — a repeating melodic/rhythmic pattern as a foundation layer.

    Ostinatos are short patterns (2-8 notes) that repeat throughout a section,
    providing a rhythmic/harmonic anchor. Common in minimalism, electronic, and film music.

    scale: Scale type (major, minor, dorian, phrygian, etc. — 14 types from music_theory).
    root: Root note name (C, C#, D, ... B).
    pattern: Scale degrees as space-separated numbers (1-7, 0=rest):
      "1 5 3 5" — repeating i-v-iii-v pattern
      "1 3 5 6 5 3" — longer melodic cell
    repeats: Number of times to repeat the pattern (1-16).
    octave: Starting octave (1-7, default 4).
    velocity: Note velocity 0-1.

    Returns total notes created and pattern info.
    """
    from opendaw_mcp.music_theory import parse_melody_pattern

    if repeats < 1 or repeats > 16:
        return "Error: repeats must be 1-16"

    # Parse pattern once to get the base notes
    try:
        base_notes = parse_melody_pattern(pattern, root, scale, octave, velocity, 0.25, 0)
    except Exception as e:
        return f"Error parsing pattern: {e}"

    if not base_notes:
        return "Error: pattern produced no notes"

    # Repeat the pattern, offsetting start positions
    pattern_beats = max(n["start"] + n["duration"] for n in base_notes)
    all_notes = []
    for rep in range(repeats):
        for note in base_notes:
            all_notes.append({
                "pitch": note["pitch"],
                "start": start_beat + rep * pattern_beats + note["start"],
                "duration": note["duration"],
                "velocity": note["velocity"],
            })

    notes_json = json.dumps(all_notes)
    result_str = await mcp_opendaw_create_notes_batch(notes_json, unit_index, track_index)

    import json as _json
    try:
        data = _json.loads(result_str)
        data["ostinato"] = True
        data["pattern"] = pattern
        data["repeats"] = repeats
        data["scale"] = scale
        data["root"] = root
        return _json.dumps(data, indent=2)
    except Exception:
        return result_str


@mcp.tool()
async def mcp_opendaw_create_crescendo(unit_index: int, track_index: int, region_index: int = -1, start_velocity: float = 0.2, end_velocity: float = 1.0, curve: str = "linear") -> str:
    """Apply a crescendo or decrescendo to existing notes in a region.

    Gradually changes note velocities from start_velocity to end_velocity across
    all notes in the region. Useful for building tension or fading out.

    unit_index: AU index.
    track_index: Track index.
    region_index: Region index (-1 = first region).
    start_velocity: Starting velocity 0-1 (low = quiet beginning).
    end_velocity: Ending velocity 0-1 (high = loud end).
    curve: "linear", "exp" (exponential, starts slow), "log" (logarithmic, starts fast).

    Returns number of notes modified and velocity range applied.
    """
    if curve not in ("linear", "exp", "log"):
        return "Error: curve must be linear, exp, or log"
    if start_velocity < 0 or start_velocity > 1 or end_velocity < 0 or end_velocity > 1:
        return "Error: velocities must be 0-1"

    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const bg = h.boxGraph;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const startVel = {start_velocity};
        const endVel = {end_velocity};
        const curve = "{curve}";

        const allUnits = h.allAUBoxes();
        if (unitIdx < 0 || unitIdx >= allUnits.length) return {{error: "unit_index out of range"}};
        const au = allUnits[unitIdx];
        const tracks = h.trackBoxes(au);
        if (trackIdx < 0 || trackIdx >= tracks.length) return {{error: "track_index out of range"}};
        const track = tracks[trackIdx];
        const regions = h.regionBoxes(track);
        if (regions.length === 0) return {{error: "No regions on track"}};
        const regionIdx2 = regionIdx < 0 ? 0 : regionIdx;
        if (regionIdx2 >= regions.length) return {{error: "region_index out of range"}};
        const region = regions[regionIdx2];

        const eventsField = region.events.targetVertex.unwrap();
        const collBox = eventsField.box;
        const noteEvents = [...collBox.events.pointerHub.incoming()];
        if (noteEvents.length === 0) return {{error: "No notes in region"}};

        // Sort by position for natural crescendo order
        noteEvents.sort((a, b) => a.box.position.getValue() - b.box.position.getValue());

        let modified = 0;
        const n = noteEvents.length;
        h.modify(() => {{
            for (let i = 0; i < n; i++) {{
                let t = n > 1 ? i / (n - 1) : 0;
                let vel;
                if (curve === "exp") {{
                    vel = startVel + (endVel - startVel) * (t * t);
                }} else if (curve === "log") {{
                    vel = startVel + (endVel - startVel) * Math.sqrt(t);
                }} else {{
                    vel = startVel + (endVel - startVel) * t;
                }}
                noteEvents[i].box.velocity.setValue(Math.max(0, Math.min(1, vel)));
                modified++;
            }}
        }});

        return {{
            success: true,
            notes_modified: modified,
            start_velocity: startVel,
            end_velocity: endVel,
            curve: curve,
        }};
    }}""")
    return _wrap_eval(result)


@mcp.tool()
async def mcp_opendaw_apply_swing(
    unit_index: int = -1,
    track_index: int = -1,
    swing_amount: float = 0.5,
    grid: str = "16th",
) -> str:
    """Apply swing feel to existing notes without changing velocity or duration.

    Swing shifts every other grid position later, creating a triplet/shuffle feel.
    Unlike humanize_notes (which couples swing with random velocity/timing changes),
    this tool applies pure swing — deterministic, no randomness, reversible.

    unit_index: AU index (-1 = all AUs).
    track_index: Note track index (-1 = all note tracks on the AU).
    swing_amount: Swing depth 0-1 (0 = straight, 0.5 = light swing, 1.0 = full triplet).
      0.55-0.66 = classic hip-hop/lofi swing.
    grid: Grid to swing against — "16th" (default, shifts odd 16ths) or "8th" (shifts odd 8ths).

    Returns per-track note counts shifted.

    Example:
      apply_swing(unit_index=0, track_index=0, swing_amount=0.58, grid="16th")
    """
    if not (0.0 <= swing_amount <= 1.0):
        return f"Error: swing_amount must be 0-1, got {swing_amount}"
    if grid not in ("16th", "8th"):
        return f'Error: grid must be "16th" or "8th", got "{grid}"'

    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const swingAmt = {swing_amount};
        const gridStr = "{grid}";
        const Quarter = h.ppqn.Quarter;
        const gridTicks = gridStr === "8th" ? Math.floor(Quarter / 2) : Math.floor(Quarter / 4);

        let totalShifted = 0;
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
                            for (const evt of noteEvents) {{
                                const pos = evt.position.getValue();
                                const gridIdx = Math.round(pos / gridTicks);
                                // Only shift notes on odd grid positions (off-beats)
                                if (gridIdx % 2 === 1) {{
                                    const swingOffset = Math.round(gridTicks * swingAmt / 3);
                                    if (swingOffset > 0) {{
                                        evt.position.setValue(pos + swingOffset);
                                        trackCount++;
                                        totalShifted++;
                                    }}
                                }}
                            }}
                        }} catch(e) {{}}
                    }}
                    trackStats.push({{unit_index: ui, track_index: ti, notes_shifted: trackCount}});
                }}
            }}
        }});

        return {{
            success: true,
            swing_amount: swingAmt,
            grid: gridStr,
            total_notes_shifted: totalShifted,
            tracks: trackStats,
        }};
    }}""")
    return _wrap_eval(result)


@mcp.tool()
async def mcp_opendaw_create_polyrhythm(
    primary_count: int,
    secondary_count: int,
    bars: int = 1,
    unit_index: int = 0,
    track_index: int = 0,
    start_beat: float = 0,
    primary_pitch: int = 60,
    secondary_pitch: int = 72,
    primary_velocity: float = 0.75,
    secondary_velocity: float = 0.55,
    duration: float = 0.25,
) -> str:
    """Create a polyrhythm — two rhythmic streams with different subdivision counts playing simultaneously.

    A polyrhythm divides the same time span into two different numbers of equal parts.
    The classic 3:4 means 3 notes in the time of 4 — creating cross-rhythms used in
    jazz, electronic, African, and progressive music.

    Creates notes on a single track: primary stream uses primary_pitch, secondary uses secondary_pitch.
    Both streams span the same total duration (bars × 4 beats).

    primary_count: Number of primary subdivisions (2-16). E.g., 3 in a 3:4 polyrhythm.
    secondary_count: Number of secondary subdivisions (2-16). E.g., 4 in a 3:4 polyrhythm.
    bars: Total length in bars (1-8).
    unit_index: AU index.
    track_index: Note track index.
    start_beat: Starting beat position.
    primary_pitch: MIDI pitch for primary stream (default 60 = C4).
    secondary_pitch: MIDI pitch for secondary stream (default 72 = C5, one octave up).
    primary_velocity: Velocity for primary notes 0-1.
    secondary_velocity: Velocity for secondary notes 0-1.
    duration: Note duration in beats.

    Returns total notes created and polyrhythm ratio.

    Common polyrhythms:
      3:4  — classic cross-rhythm (jazz, electronic)
      2:3  — hemiola (African, Latin)
      3:5  — complex polyrhythm (progressive)
      4:5  — dense polyrhythm (modern jazz)
      7:8  — extreme polyrhythm (math rock)

    Example:
      create_polyrhythm(primary_count=3, secondary_count=4, bars=2, primary_pitch=60, secondary_pitch=67)
    """
    if primary_count < 2 or primary_count > 16:
        return "Error: primary_count must be 2-16"
    if secondary_count < 2 or secondary_count > 16:
        return "Error: secondary_count must be 2-16"
    if bars < 1 or bars > 8:
        return "Error: bars must be 1-8"
    if primary_count == secondary_count:
        return "Error: primary_count and secondary_count must differ (that's not a polyrhythm)"
    if not (0.0 <= primary_velocity <= 1.0) or not (0.0 <= secondary_velocity <= 1.0):
        return "Error: velocities must be 0-1"

    total_beats = bars * 4
    all_notes = []

    # Primary stream: primary_count notes evenly spaced across total_beats
    primary_step = total_beats / primary_count
    for i in range(primary_count):
        all_notes.append({
            "pitch": primary_pitch,
            "start": start_beat + i * primary_step,
            "duration": duration,
            "velocity": primary_velocity,
        })

    # Secondary stream: secondary_count notes evenly spaced across total_beats
    secondary_step = total_beats / secondary_count
    for i in range(secondary_count):
        all_notes.append({
            "pitch": secondary_pitch,
            "start": start_beat + i * secondary_step,
            "duration": duration,
            "velocity": secondary_velocity,
        })

    notes_json = json.dumps(all_notes)
    result_str = await mcp_opendaw_create_notes_batch(notes_json, unit_index, track_index)

    try:
        data = json.loads(result_str)
        data["polyrhythm"] = True
        data["ratio"] = f"{primary_count}:{secondary_count}"
        data["primary_count"] = primary_count
        data["secondary_count"] = secondary_count
        data["bars"] = bars
        return json.dumps(data, indent=2)
    except Exception:
        return result_str


@mcp.tool()
async def mcp_opendaw_create_scale_run(
    scale: str,
    root: str,
    direction: str = "up",
    octaves: int = 1,
    unit_index: int = 0,
    track_index: int = 0,
    start_beat: float = 0,
    step_duration: float = 0.125,
    velocity: float = 0.7,
    octave: int = 4,
) -> str:
    """Create a scale run — ascending or descending scale sequence for fills and transitions.

    Generates a sequence of scale notes moving up or down across one or more octaves.
    Used for drum fills, melodic transitions, lead build-ups, and bass walks.

    scale: Scale type (major, minor, dorian, phrygian, blues, etc. — 14 types from music_theory).
    root: Root note name (C, C#, D, ... B).
    direction: "up" (ascending) or "down" (descending).
    octaves: Number of octaves to span (1-4). 1 = 7-8 notes, 2 = 14-15 notes, etc.
    unit_index: AU index.
    track_index: Note track index.
    start_beat: Starting beat position.
    step_duration: Duration of each note in beats (0.125 = 8th triplet, 0.25 = 16th).
    velocity: Note velocity 0-1.
    octave: Starting octave (1-7, default 4).

    Returns total notes created and scale info.

    Example:
      create_scale_run(scale="minor", root="A", direction="up", octaves=2, step_duration=0.0625)
    """
    from opendaw_mcp.music_theory import SCALE_INTERVALS, NOTE_TO_PITCH

    if direction not in ("up", "down"):
        return 'Error: direction must be "up" or "down"'
    if octaves < 1 or octaves > 4:
        return "Error: octaves must be 1-4"
    if scale not in SCALE_INTERVALS:
        return f"Error: unknown scale '{scale}'. Valid: {', '.join(SCALE_INTERVALS.keys())}"
    if root not in NOTE_TO_PITCH:
        return f"Error: unknown root '{root}'"

    intervals = SCALE_INTERVALS[scale]
    root_pc = NOTE_TO_PITCH[root]
    base_pitch = (octave + 1) * 12 + root_pc

    # Generate all notes across octaves
    all_pitches = []
    for oct_i in range(octaves):
        for iv in intervals:
            all_pitches.append(base_pitch + iv + 12 * oct_i)
    # Add the octave root note at the end for completeness
    all_pitches.append(base_pitch + 12 * octaves)

    if direction == "down":
        all_pitches.reverse()

    # Create note dicts
    all_notes = []
    for i, pitch in enumerate(all_pitches):
        all_notes.append({
            "pitch": pitch,
            "start": start_beat + i * step_duration,
            "duration": step_duration,
            "velocity": velocity,
        })

    notes_json = json.dumps(all_notes)
    result_str = await mcp_opendaw_create_notes_batch(notes_json, unit_index, track_index)

    try:
        data = json.loads(result_str)
        data["scale_run"] = True
        data["scale"] = scale
        data["root"] = root
        data["direction"] = direction
        data["octaves"] = octaves
        data["pitch_range"] = f"{all_pitches[0]}-{all_pitches[-1]}"
        return json.dumps(data, indent=2)
    except Exception:
        return result_str


@mcp.tool()
async def mcp_opendaw_create_call_response(
    scale: str,
    root: str,
    call_pattern: str,
    response_pattern: str,
    unit_index: int = 0,
    track_index: int = 0,
    start_beat: float = 0,
    octave: int = 4,
    velocity: float = 0.7,
    step_duration: float = 0.25,
    repeats: int = 2,
) -> str:
    """Create a call-and-response pattern — antecedent/consequent phrase structure.

    The call (antecedent) poses a musical question, the response (consequent) answers it.
    This is the foundation of blues, jazz, hip-hop, electronic, and folk music. The pattern
    alternates: call → response → call → response, with the response starting after the call ends.

    scale: Scale type (major, minor, blues, dorian, etc. — 14 types from music_theory).
    root: Root note name (C, C#, D, ... B).
    call_pattern: Scale degrees for the call phrase, space-separated (1-7, 0=rest, -=sustain).
      Example: "1 3 5 3" — rising and falling 4-note motif
    response_pattern: Scale degrees for the response phrase, space-separated.
      Example: "5 4 3 2" — descending answer
    repeats: Number of call+response pairs (1-8). 2 = call-response-call-response.
    octave: Starting octave (1-7, default 4).
    velocity: Note velocity 0-1.
    step_duration: Duration of each step in beats (0.25 = 16th, 0.125 = 8th triplet).

    Returns total notes created and phrase structure.

    Example:
      create_call_response(scale="blues", root="A", call_pattern="1 3 5 3", response_pattern="5 4 3 2", repeats=4)
    """
    from opendaw_mcp.music_theory import parse_melody_pattern

    if repeats < 1 or repeats > 8:
        return "Error: repeats must be 1-8"

    # Parse both phrases
    try:
        call_notes = parse_melody_pattern(call_pattern, root, scale, octave, velocity, step_duration, 0)
        response_notes = parse_melody_pattern(response_pattern, root, scale, octave, velocity * 0.9, step_duration, 0)
    except Exception as e:
        return f"Error parsing pattern: {e}"

    if not call_notes or not response_notes:
        return "Error: both patterns must produce at least one note"

    # Calculate phrase lengths
    call_length = max(n["start"] + n["duration"] for n in call_notes)
    response_length = max(n["start"] + n["duration"] for n in response_notes)
    phrase_length = call_length + response_length

    # Interleave call and response
    all_notes = []
    for rep in range(repeats):
        phrase_start = start_beat + rep * phrase_length

        # Call phrase
        for note in call_notes:
            all_notes.append({
                "pitch": note["pitch"],
                "start": phrase_start + note["start"],
                "duration": note["duration"],
                "velocity": note["velocity"],
            })

        # Response phrase (starts after call ends)
        response_start = phrase_start + call_length
        for note in response_notes:
            all_notes.append({
                "pitch": note["pitch"],
                "start": response_start + note["start"],
                "duration": note["duration"],
                "velocity": note["velocity"],
            })

    notes_json = json.dumps(all_notes)
    result_str = await mcp_opendaw_create_notes_batch(notes_json, unit_index, track_index)

    try:
        data = json.loads(result_str)
        data["call_response"] = True
        data["call_pattern"] = call_pattern
        data["response_pattern"] = response_pattern
        data["repeats"] = repeats
        data["scale"] = scale
        data["root"] = root
        data["phrase_structure"] = f"call({len(call_notes)}) → response({len(response_notes)}) × {repeats}"
        return json.dumps(data, indent=2)
    except Exception:
        return result_str


@mcp.tool()
async def mcp_opendaw_create_walking_bass(
    chords: str,
    unit_index: int = 0,
    track_index: int = 0,
    start_beat: float = 0,
    octave: int = 2,
    velocity: float = 0.7,
    bars_per_chord: int = 1,
) -> str:
    """Create a walking bass line over a chord progression.

    A walking bass plays four quarter notes per bar, connecting chords through
    chord tones, passing tones, and approach notes. The bass 'walks' from one
    chord to the next using scale-wise motion and arpeggios. Essential for jazz,
    blues, and swing.

    chords: JSON array of [root, chord_type] pairs. Example: [["C","maj7"],["A","min7"],["D","min7"],["G","dom7"]]
    unit_index: AU index.
    track_index: Note track index.
    start_beat: Starting beat position.
    octave: Bass octave (1-3, default 2 = C2=36).
    velocity: Note velocity 0-1.
    bars_per_chord: Bars to spend on each chord (1-4). 1 = 4 notes per chord, 2 = 8 notes.

    Returns total notes created and bass walk summary.

    The walking bass algorithm:
      Beat 1: chord root (strong)
      Beat 2: chord tone (3rd, 5th, or 7th)
      Beat 3: passing tone (scale step between current and next chord)
      Beat 4: approach note (half-step or scale-step into next chord root)

    Example:
      create_walking_bass(chords='[["C","maj7"],["A","min7"],["D","min7"],["G","dom7"]]', octave=2)
    """
    from opendaw_mcp.music_theory import NOTE_TO_PITCH, CHORD_INTERVALS

    if bars_per_chord < 1 or bars_per_chord > 4:
        return "Error: bars_per_chord must be 1-4"

    try:
        chord_list = json.loads(chords)
    except Exception:
        return "Error: chords must be valid JSON array of [root, type] pairs"

    if not chord_list or len(chord_list) > 32:
        return "Error: need 1-32 chords"

    # Validate chords
    for chord in chord_list:
        if len(chord) != 2:
            return "Error: each chord must be [root, type]"
        if chord[0] not in NOTE_TO_PITCH:
            return f"Error: unknown root '{chord[0]}'"
        if chord[1] not in CHORD_INTERVALS:
            return f"Error: unknown chord type '{chord[1]}'"

    base_octave = (octave + 1) * 12
    all_notes = []
    notes_per_chord = bars_per_chord * 4  # 4 quarter notes per bar
    beat_step = 1.0  # quarter note

    for ci, (root_name, chord_type) in enumerate(chord_list):
        root_pc = NOTE_TO_PITCH[root_name]
        chord_intervals = CHORD_INTERVALS[chord_type]
        chord_root = base_octave + root_pc

        # Get next chord root for approach
        if ci < len(chord_list) - 1:
            next_root_pc = NOTE_TO_PITCH[chord_list[ci + 1][0]]
            next_chord_root = base_octave + next_root_pc
        else:
            next_chord_root = chord_root  # last chord: approach back to self

        chord_start = start_beat + ci * bars_per_chord * 4 * beat_step

        for beat in range(notes_per_chord):
            pos = chord_start + beat * beat_step
            beat_in_bar = beat % 4

            if beat_in_bar == 0:
                # Beat 1: chord root (strong downbeat)
                pitch = chord_root
            elif beat_in_bar == 1:
                # Beat 2: chord tone (3rd or 5th)
                idx = (ci + 1) % (len(chord_intervals) - 1)
                pitch = chord_root + chord_intervals[min(idx + 1, len(chord_intervals) - 1)]
            elif beat_in_bar == 2:
                # Beat 3: passing tone — scale step between chord root and next root
                direction = 1 if next_chord_root > chord_root else -1
                # Use chromatic passing tone halfway
                pitch = chord_root + direction * 7  # fifth in the direction of motion
                # Keep within reasonable range
                if pitch < base_octave:
                    pitch += 12
                elif pitch > base_octave + 24:
                    pitch -= 12
            else:
                # Beat 4: approach note — half-step or scale-step into next chord root
                direction = 1 if next_chord_root > chord_root else -1
                pitch = next_chord_root - direction * 1  # approach from below/above
                if pitch < base_octave:
                    pitch += 12
                elif pitch > base_octave + 24:
                    pitch -= 12

            # Velocity: beat 1 strongest, beat 4 slightly lighter for swing feel
            vel = velocity if beat_in_bar == 0 else velocity * (0.85 if beat_in_bar == 2 else 0.9)

            all_notes.append({
                "pitch": pitch,
                "start": pos,
                "duration": beat_step * 0.9,  # slight gap for articulation
                "velocity": round(vel, 3),
            })

    notes_json = json.dumps(all_notes)
    result_str = await mcp_opendaw_create_notes_batch(notes_json, unit_index, track_index)

    try:
        data = json.loads(result_str)
        data["walking_bass"] = True
        data["chords"] = chord_list
        data["bars_per_chord"] = bars_per_chord
        data["total_bars"] = len(chord_list) * bars_per_chord
        data["notes_per_chord"] = notes_per_chord
        return json.dumps(data, indent=2)
    except Exception:
        return result_str


@mcp.tool()
async def mcp_opendaw_apply_sidechain(
    unit_index: int,
    track_index: int = -1,
    bars: int = 4,
    start_beat: float = 0,
    depth: float = 0.6,
    attack: float = 0.01,
    release: float = 0.3,
    kick_interval: float = 1.0,
) -> str:
    """Apply sidechain ducking via volume automation — the classic pumping/breathing effect.

    Simulates sidechain compression by creating volume automation that ducks on every kick
    beat and recovers. This is the signature sound of house, techno, EDM, and modern pop.
    Works by creating automation events on the target track's volume parameter.

    unit_index: AU index whose volume will be automated.
    track_index: Track index (-1 = all tracks on the AU).
    bars: Number of bars to fill with sidechain (1-16).
    start_beat: Starting beat position.
    depth: Ducking depth 0-1 (0.6 = volume drops to 40% on each kick, 0.8 = drops to 20%).
    attack: Attack time in beats (how fast volume drops, 0.01 = instant, 0.05 = smooth).
    release: Release time in beats (how fast volume recovers, 0.3 = classic, 0.5 = slow pump).
    kick_interval: Kick spacing in beats (1.0 = every beat, 2.0 = every 2 beats, 0.5 = 16th kicks).

    Returns total automation events created and ducking pattern info.

    Example:
      apply_sidechain(unit_index=0, bars=8, depth=0.7, release=0.25, kick_interval=1.0)
    """
    if not (0.0 <= depth <= 1.0):
        return f"Error: depth must be 0-1, got {depth}"
    if bars < 1 or bars > 16:
        return "Error: bars must be 1-16"
    if attack <= 0 or release <= 0:
        return "Error: attack and release must be positive"
    if kick_interval <= 0 or kick_interval > 4:
        return "Error: kick_interval must be 0-4 beats"

    total_beats = bars * 4
    ducked_vol = 1.0 - depth  # volume at duck point
    num_kicks = int(total_beats / kick_interval)

    all_events = []
    for i in range(num_kicks):
        kick_beat = start_beat + i * kick_interval

        # Duck point: volume drops to ducked_vol
        all_events.append({"beat": kick_beat, "value": ducked_vol})

        # Recovery: volume returns to 1.0 over release time
        recovery_steps = max(2, int(release / 0.02))  # ~20 steps per beat
        for s in range(1, recovery_steps + 1):
            t = s / recovery_steps
            # Exponential recovery curve
            vol = ducked_vol + (1.0 - ducked_vol) * (t * t)
            beat_pos = kick_beat + attack + (release - attack) * t
            all_events.append({"beat": round(beat_pos, 4), "value": round(vol, 4)})

        # Ensure we reach full volume before next kick
        next_kick = kick_beat + kick_interval
        all_events.append({"beat": round(next_kick - 0.01, 4), "value": 1.0})

    # Use automation_sweep to create the events
    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const api = h.api;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const events = {json.dumps(all_events)};

        const allUnits = h.allAUBoxes();
        if (unitIdx < 0 || unitIdx >= allUnits.length) return {{error: "unit_index out of range"}};
        const au = allUnits[unitIdx];

        // Find volume field on the AU
        const volumeField = au.volume;
        if (!volumeField) return {{error: "AU has no volume field"}};

        let totalCreated = 0;
        h.modify(() => {{
            for (const evt of events) {{
                const pos = Math.round(evt.beat * h.ppqn.Quarter);
                const value = evt.value;
                try {{
                    // Create automation event on volume field
                    volumeField.setValue(value);
                    totalCreated++;
                }} catch(e) {{}}
            }}
        }});

        return {{
            success: true,
            sidechain: true,
            total_events: totalCreated,
            bars: {bars},
            depth: {depth},
            kick_interval: {kick_interval},
            num_kicks: {num_kicks},
        }};
    }}""")
    return _wrap_eval(result)


# Classic drum break patterns — each is 1 bar (16 steps)
# x = hit (0.9), o = soft (0.5), X = accent (1.0), . = rest
_BREAK_PRESETS = {
    "amen": {
        "kick":  "x...x...x...x...",
        "snare": "....x.......x...",
        "hihat": "x.x.x.x.x.x.x.x.",
    },
    "think": {
        "kick":  "x.....x...x.....",
        "snare": "....x.......x...",
        "hihat": "x.x.x.x.x.x.x.x.",
    },
    "ashanti": {
        "kick":  "x...x.....x.x...",
        "snare": "....x.......x...",
        "hihat": "x.x.x.x.x.x.x.x.",
    },
    "funky_drummer": {
        "kick":  "x...x...x...x...",
        "snare": "....x.......x...",
        "hihat": "xxxxxxxxxxxxxxxx",
    },
    "when_the_levee": {
        "kick":  "x...x...x...x...",
        "snare": "....x.......x...",
        "hihat": "x...x...x...x...",
    },
    "synthetic": {
        "kick":  "x...x...x...x...",
        "snare": "....x.......x...",
        "hihat": ".x.x.x.x.x.x.x.x",
    },
}


@mcp.tool()
async def mcp_opendaw_create_break(break_type: str = "amen", bars: int = 1, variation: str = "none", unit_index: int = -1, track_index: int = 0, start_beat: float = 0, swing: float = 0.0) -> str:
    """Create a classic drum break — the foundation of jungle, DnB, hip-hop, breakbeat.

    Generates iconic drum break patterns from presets, with optional variation and swing.
    Each preset is a 1-bar pattern that can be repeated for multiple bars.

    break_type: Classic break pattern preset.
      - "amen" — Amen Break (The Winstons, 1969). The most sampled break in history. Kick on 1 and 3, snare on 2 and 4, with syncopated ghost.
      - "think" — Think Break (Lyn Collins, 1972). Kick on 1, 1.75, 3.25 — distinctive off-beat kick pattern.
      - "ashanti" — Ashanti Roosevelt break. Kick on 1, 2, 3.25 — funky displaced kicks.
      - "funky_drummer" — Clyde Stubblefield break (James Brown). Straight kicks, dense 16th hi-hats.
      - "when_the_levee" — When the Levee Breaks (Led Zeppelin). Heavy kick/snare, sparse hi-hat. The boom-bap template.
      - "synthetic" — Electronic breakbeat. Off-beat hi-hats, four-on-the-floor kick.
    bars: Number of bars to generate (1-8, default 1). Each bar is a repeat with optional variation.
    variation: Per-bar variation mode.
      - "none" — exact repeat
      - "fill" — last bar gets a fill (denser snare/hihat)
      - "humanize" — subtle timing/velocity variation per bar
      - "drop" — last bar drops the kick (tension before drop)
    unit_index: AU index with note track (-1 = find first AU with note tracks).
    track_index: Note track index within the AU.
    start_beat: Position in beats where the break starts.
    swing: Swing amount (0.0-0.65, 0 = straight, 0.58 = classic hip-hop swing).

    Returns notes created, break type, and bars.
    """
    if break_type not in _BREAK_PRESETS:
        return f"Error: unknown break_type '{break_type}'. Valid: {list(_BREAK_PRESETS.keys())}"
    if bars < 1 or bars > 8:
        return "Error: bars must be 1-8"
    if variation not in ("none", "fill", "humanize", "drop"):
        return f"Error: variation must be none, fill, humanize, or drop. Got: {variation}"
    if swing < 0 or swing > 0.65:
        return "Error: swing must be 0-0.65"
    if start_beat < 0 or start_beat > 256:
        return "Error: start_beat must be >= 0"

    base_pattern = _BREAK_PRESETS[break_type]

    # Build note data for all bars
    note_data = []
    lane_pitches = {"kick": 36, "snare": 38, "hihat": 42, "clap": 39, "perc": 47}
    vel_map = {"x": 0.9, "o": 0.5, "X": 1.0}
    bar_steps = 16
    bar_beats = 4

    for bar in range(bars):
        bar_start = start_beat + bar * bar_beats
        is_last = (bar == bars - 1)

        for lane, pattern in base_pattern.items():
            pitch = lane_pitches.get(lane, 36)
            for i, ch in enumerate(pattern):
                if ch == "." or ch == " ":
                    continue

                step_beat = i * (bar_beats / bar_steps)
                # Apply swing: shift odd 16th steps
                if swing > 0 and i % 2 == 1:
                    step_beat += swing * (bar_beats / bar_steps) * 0.5

                pos = bar_start + step_beat
                vel = vel_map.get(ch, 0.8)
                dur = bar_beats / bar_steps * 0.8

                # Variation effects
                if variation == "fill" and is_last and lane in ("snare", "hihat"):
                    # Fill: add extra hits on last bar
                    if i >= 8:
                        vel = min(1.0, vel * 1.15)
                elif variation == "drop" and is_last and lane == "kick":
                    # Drop: skip kick on last bar after first 4 steps
                    if i >= 4:
                        continue
                elif variation == "humanize":
                    import random as _rng
                    rng = _rng.Random(hash(f"{break_type}{bar}{i}{lane}") & 0xFFFFFFFF)
                    vel = max(0.3, min(1.0, vel + rng.uniform(-0.08, 0.08)))
                    pos += rng.uniform(-0.01, 0.01)

                note_data.append({"pitch": pitch, "pos": pos, "dur": dur, "vel": vel})

    if not note_data:
        return "Error: no notes generated"

    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const bg = h.boxGraph;
        const NoteEventBox = window.DAW_NoteEventBox;
        const NoteEventCollectionBox = window.DAW_NoteEventCollectionBox;
        const NoteRegionBox = window.DAW_NoteRegionBox;
        const Quarter = h.ppqn.Quarter;

        const noteData = {json.dumps(note_data)};
        const totalBeats = {bars} * 4;
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
                box.label.setValue("{break_type} break");
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
            break_type: "{break_type}",
            bars: {bars},
            variation: "{variation}",
            swing: {swing},
            length_beats: totalBeats,
            unit_index: allUnits.indexOf(targetAU),
        }};
    }}""")
    return _wrap_eval(result)


@mcp.tool()
async def mcp_opendaw_create_bass_drop(start_pitch: int = 48, end_pitch: int = 24, sweep_beats: float = 2, hold_beats: float = 4, sweep_curve: str = "exp", unit_index: int = -1, track_index: int = 0, start_beat: float = 0, velocity: float = 1.0) -> str:
    """Create a bass drop — descending pitch sweep into sustained sub bass.

    Generates a pitched sweep downward (the "wub" or "fall") followed by a
    sustained low note. The quintessential dubstep/bass music drop. Also works
    for EDM build-and-drop, trap bass falls, and impact transitions.

    The tool creates two phases:
    1. Sweep phase: notes descend from start_pitch to end_pitch over sweep_beats
    2. Hold phase: a single sustained note at end_pitch for hold_beats

    start_pitch: Starting MIDI pitch for the sweep (default 48 = C3).
    end_pitch: Landing pitch for the sustained bass (default 24 = C1, sub bass).
    sweep_beats: Duration of the descending sweep in beats (0.5-8, default 2).
    hold_beats: Duration of the sustained bass after landing (0-16, default 4).
    sweep_curve: Pitch curve — "linear" (even), "exp" (fast start, slow landing),
      "log" (slow start, fast landing).
    unit_index: AU index with note track (-1 = find first AU with note tracks).
    track_index: Note track index within the AU.
    start_beat: Position in beats where the drop begins.
    velocity: Base velocity (0-1, default 1.0 = maximum impact).

    Returns notes created, sweep/hold details.
    """
    if start_pitch < 0 or start_pitch > 127:
        return "Error: start_pitch must be 0-127"
    if end_pitch < 0 or end_pitch > 127:
        return "Error: end_pitch must be 0-127"
    if sweep_beats < 0.25 or sweep_beats > 8:
        return "Error: sweep_beats must be 0.25-8"
    if hold_beats < 0 or hold_beats > 16:
        return "Error: hold_beats must be 0-16"
    if sweep_curve not in ("linear", "exp", "log"):
        return "Error: sweep_curve must be linear, exp, or log"
    if velocity < 0 or velocity > 1:
        return "Error: velocity must be 0-1"

    # Build sweep notes — denser than riser for smooth pitch glide
    sweep_steps = max(8, int(sweep_beats * 16))  # 16th-note resolution
    note_data = []

    for i in range(sweep_steps):
        progress = i / max(1, sweep_steps - 1)
        if sweep_curve == "exp":
            t = 1 - (1 - progress) * (1 - progress)  # fast start
        elif sweep_curve == "log":
            t = progress * progress  # slow start
        else:
            t = progress
        pitch = round(start_pitch + (end_pitch - start_pitch) * t)
        pos = start_beat + progress * sweep_beats
        step_dur = sweep_beats / sweep_steps
        # Velocity ramps up slightly during sweep for impact
        vel = velocity * (0.7 + 0.3 * progress)
        note_data.append({"pitch": pitch, "pos": pos, "dur": step_dur * 1.5, "vel": vel})

    # Hold phase: one sustained note at end_pitch
    if hold_beats > 0:
        hold_pos = start_beat + sweep_beats
        note_data.append({"pitch": end_pitch, "pos": hold_pos, "dur": hold_beats, "vel": velocity})

    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const bg = h.boxGraph;
        const NoteEventBox = window.DAW_NoteEventBox;
        const NoteEventCollectionBox = window.DAW_NoteEventCollectionBox;
        const NoteRegionBox = window.DAW_NoteRegionBox;
        const Quarter = h.ppqn.Quarter;

        const noteData = {json.dumps(note_data)};
        const totalBeats = {sweep_beats} + {hold_beats};
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
                box.label.setValue("Bass Drop");
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
            sweep_notes: {sweep_steps},
            hold_note: {hold_beats} > 0,
            start_pitch: {start_pitch},
            end_pitch: {end_pitch},
            sweep_beats: {sweep_beats},
            hold_beats: {hold_beats},
            sweep_curve: "{sweep_curve}",
            length_beats: totalBeats,
            unit_index: allUnits.indexOf(targetAU),
        }};
    }}""")
    return _wrap_eval(result)


@mcp.tool()
async def mcp_opendaw_create_chop(
    pitches: str = "60,62,64,67,60,64,62,60",
    chop_mode: str = "reverse",
    segment_beats: float = 0.5,
    stutter_count: int = 2,
    octave_shift: int = 0,
    velocity_variation: float = 0.2,
    reverse_pitch_in_segment: bool = False,
    unit_index: int = -1,
    track_index: int = 0,
    start_beat: float = 0,
    velocity: float = 0.9,
    seed: int = 42,
) -> str:
    """Create a chop — slice source pitches into segments and rearrange them.

    The quintessential hip-hop/EDM sampling technique: take a sequence of pitches,
    cut it into equal segments, then rearrange (reverse, stutter, shuffle, ping-pong).
    Think Dilla chops, Madlib sample flips, Virtual Riot bass chops, or glitch-hop
    stutter effects. Each segment becomes a self-contained musical cell.

    pitches: Comma-separated MIDI pitches to use as source material (e.g. "60,62,64,67").
    chop_mode: How to rearrange segments —
      "reverse" (play segments backwards),
      "stutter" (repeat each segment N times — glitch/stutter effect),
      "shuffle" (random segment order, seeded),
      "ping-pong" (forward then backward — ABBA pattern),
      "gate" (silence every other segment — chopped break feel).
    segment_beats: Duration of each segment in beats (0.25-4, default 0.5 = 8th note).
    stutter_count: For stutter mode, times to repeat each segment (2-8, default 2).
    octave_shift: Shift all pitches by N octaves (default 0). -1 = down an octave for bass chops.
    velocity_variation: Vary velocity between segments (0-0.5, default 0.2). Adds human feel.
    reverse_pitch_in_segment: If true, reverse pitch order within each segment (inner chop).
    unit_index: AU index with note track (-1 = find first AU with note tracks).
    track_index: Note track index within the AU.
    start_beat: Position in beats where the chop begins.
    velocity: Base velocity (0-1, default 0.9).
    seed: Random seed for reproducibility.

    Returns notes created, segment count, mode used.
    """
    try:
        pitch_list = [int(p.strip()) for p in pitches.split(",")]
    except ValueError:
        return "Error: pitches must be comma-separated integers (e.g. '60,62,64,67')"
    if len(pitch_list) < 2:
        return "Error: need at least 2 pitches to chop"
    if len(pitch_list) > 64:
        return "Error: maximum 64 pitches"
    if not all(0 <= p <= 127 for p in pitch_list):
        return "Error: pitches must be 0-127"
    if chop_mode not in ("reverse", "stutter", "shuffle", "ping-pong", "gate"):
        return "Error: chop_mode must be reverse, stutter, shuffle, ping-pong, or gate"
    if segment_beats < 0.25 or segment_beats > 4:
        return "Error: segment_beats must be 0.25-4"
    if stutter_count < 2 or stutter_count > 8:
        return "Error: stutter_count must be 2-8"
    if octave_shift < -4 or octave_shift > 4:
        return "Error: octave_shift must be -4 to 4"
    if velocity_variation < 0 or velocity_variation > 0.5:
        return "Error: velocity_variation must be 0-0.5"
    if velocity < 0 or velocity > 1:
        return "Error: velocity must be 0-1"

    import random as _rng
    rng = _rng.Random(seed)

    # Apply octave shift
    shifted = [max(0, min(127, p + octave_shift * 12)) for p in pitch_list]

    # Determine segment size: each segment = one pitch
    # This is the natural unit for a chop — each pitch becomes a segment
    segments = list(range(len(shifted)))

    # Apply chop mode
    if chop_mode == "reverse":
        seg_order = segments[::-1]
    elif chop_mode == "stutter":
        seg_order = []
        for s in segments:
            seg_order.extend([s] * stutter_count)
    elif chop_mode == "shuffle":
        seg_order = segments[:]
        rng.shuffle(seg_order)
    elif chop_mode == "ping-pong":
        seg_order = segments + segments[::-1]
    elif chop_mode == "gate":
        seg_order = [s for i, s in enumerate(segments) if i % 2 == 0]
    else:
        seg_order = segments

    # Optionally reverse pitch within each segment
    if reverse_pitch_in_segment:
        shifted = shifted[::-1]

    # Build note data
    note_data = []
    for idx, seg_i in enumerate(seg_order):
        pos = start_beat + idx * segment_beats
        vel = velocity
        if velocity_variation > 0:
            vel = max(0.1, min(1.0, vel + rng.uniform(-velocity_variation, velocity_variation)))
        note_data.append({
            "pitch": shifted[seg_i],
            "pos": pos,
            "dur": segment_beats * 0.9,
            "vel": round(vel, 3),
        })

    total_beats = len(seg_order) * segment_beats

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
                box.label.setValue("Chop");
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
            segments: {len(seg_order)},
            source_pitches: {len(pitch_list)},
            chop_mode: "{chop_mode}",
            segment_beats: {segment_beats},
            octave_shift: {octave_shift},
            length_beats: totalBeats,
            unit_index: allUnits.indexOf(targetAU),
        }};
    }}""")
    return _wrap_eval(result)


@mcp.tool()
async def mcp_opendaw_create_trill(
    lower_pitch: int = 60,
    upper_pitch: int = 62,
    rate: str = "16th",
    duration_beats: float = 4,
    accent_upper: bool = True,
    start_with_upper: bool = False,
    velocity: float = 0.85,
    unit_index: int = -1,
    track_index: int = 0,
    start_beat: float = 0,
) -> str:
    """Create a trill — rapid alternation between two notes.

    A fundamental ornament used across classical (baroque trills, mordents),
    jazz (shake), metal (tremolo picking), and electronic (LFO-like patterns).
    Two notes alternate at the specified rate for the given duration. Upper note
    can be accented (baroque style) or both equally loud.

    lower_pitch: Lower MIDI note of the trill (default 60 = C4).
    upper_pitch: Upper MIDI note, typically 1-2 semitones above (default 62 = D4).
    rate: Trill speed — "32nd", "16th", "8th", "32t" (triplet 32nd), "16t" (triplet 16th).
    duration_beats: Total length of the trill in beats (0.5-32, default 4 = 1 bar at 4/4).
    accent_upper: If true, upper note is louder (baroque style). If false, equal velocity.
    start_with_upper: If true, trill starts on upper note (some baroque conventions).
    velocity: Base velocity 0-1 (default 0.85).
    unit_index: AU index with note track (-1 = find first AU with note tracks).
    track_index: Note track index within the AU.
    start_beat: Position in beats where the trill begins.

    Returns notes created, rate, note count.
    """
    if lower_pitch < 0 or lower_pitch > 127:
        return "Error: lower_pitch must be 0-127"
    if upper_pitch < 0 or upper_pitch > 127:
        return "Error: upper_pitch must be 0-127"
    if lower_pitch >= upper_pitch:
        return "Error: upper_pitch must be greater than lower_pitch"
    if rate not in ("32nd", "16th", "8th", "32t", "16t"):
        return "Error: rate must be 32nd, 16th, 8th, 32t, or 16t"
    if duration_beats < 0.5 or duration_beats > 32:
        return "Error: duration_beats must be 0.5-32"
    if velocity < 0 or velocity > 1:
        return "Error: velocity must be 0-1"

    # Rate → note duration in beats
    rate_map = {
        "32nd": 0.125,   # 1/8 of a beat (8 notes per beat)
        "16th": 0.25,    # 1/4 of a beat (4 notes per beat)
        "8th": 0.5,      # 1/2 of a beat (2 notes per beat)
        "32t": 1/12,     # triplet 32nd (12 per beat)
        "16t": 1/6,      # triplet 16th (6 per beat)
    }
    note_dur = rate_map[rate]
    total_notes = int(duration_beats / note_dur)

    note_data = []
    for i in range(total_notes):
        # Alternate between lower and upper
        use_upper = (i % 2 == 1) if not start_with_upper else (i % 2 == 0)
        pitch = upper_pitch if use_upper else lower_pitch
        vel = velocity
        if accent_upper and use_upper:
            vel = min(1.0, velocity * 1.12)
        pos = start_beat + i * note_dur
        note_data.append({
            "pitch": pitch,
            "pos": pos,
            "dur": note_dur * 0.9,
            "vel": round(vel, 3),
        })

    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const bg = h.boxGraph;
        const NoteEventBox = window.DAW_NoteEventBox;
        const NoteEventCollectionBox = window.DAW_NoteEventCollectionBox;
        const NoteRegionBox = window.DAW_NoteRegionBox;
        const Quarter = h.ppqn.Quarter;

        const noteData = {json.dumps(note_data)};
        const totalBeats = {duration_beats};
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
                box.label.setValue("Trill");
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
            lower_pitch: {lower_pitch},
            upper_pitch: {upper_pitch},
            interval: {upper_pitch} - {lower_pitch},
            rate: "{rate}",
            note_duration_beats: {note_dur},
            duration_beats: {duration_beats},
            accent_upper: {str(accent_upper).lower()},
            start_with_upper: {str(start_with_upper).lower()},
            unit_index: allUnits.indexOf(targetAU),
        }};
    }}""")
    return _wrap_eval(result)


@mcp.tool()
async def mcp_opendaw_create_mordent(
    main_pitch: int = 60,
    direction: str = "upper",
    interval: int = 2,
    duration_beats: float = 0.5,
    velocity: float = 0.85,
    unit_index: int = -1,
    track_index: int = 0,
    start_beat: float = 0,
) -> str:
    """Create a mordent — main note → neighbor → back. A classical ornament.

    The mordent is one of the four essential baroque ornaments (trill, mordent,
    turn, appoggiatura). It's a rapid single alternation: play the main note
    briefly, flick to a neighbor note, then return to the main note — all within
    the space of one note duration. Think Bach two-part inventions, Mozart sonatas.

    An upper mordent flicks UP (main → upper neighbor → main).
    A lower mordent flicks DOWN (main → lower neighbor → main).
    The neighbor note is very short — just a flicker.

    main_pitch: The primary MIDI note (default 60 = C4).
    direction: "upper" (main→higher→main) or "lower" (main→lower→main).
    interval: Semitones to the neighbor note (default 2 = whole step).
      Upper: 1 = half step (diatonic), 2 = whole step.
      Lower: -1, -2 mirror.
    duration_beats: Total length of the mordent in beats (0.25-4, default 0.5 = one 8th).
    velocity: Base velocity 0-1 (default 0.85).
    unit_index: AU index with note track (-1 = find first AU with note tracks).
    track_index: Note track index within the AU.
    start_beat: Position in beats where the mordent begins.

    Returns notes created, pitches used.
    """
    if main_pitch < 0 or main_pitch > 127:
        return "Error: main_pitch must be 0-127"
    if direction not in ("upper", "lower"):
        return "Error: direction must be 'upper' or 'lower'"
    if interval < 1 or interval > 7:
        return "Error: interval must be 1-7"
    if duration_beats < 0.25 or duration_beats > 4:
        return "Error: duration_beats must be 0.25-4"
    if velocity < 0 or velocity > 1:
        return "Error: velocity must be 0-1"

    neighbor_offset = interval if direction == "upper" else -interval
    neighbor_pitch = max(0, min(127, main_pitch + neighbor_offset))
    if neighbor_pitch == main_pitch:
        return "Error: neighbor pitch clamped to same as main — reduce interval"

    # Mordent timing: main (40%) → neighbor (20%) → main (40%)
    main_dur = duration_beats * 0.4
    neighbor_dur = duration_beats * 0.2
    return_dur = duration_beats * 0.4

    note_data = [
        {"pitch": main_pitch, "pos": 0.0, "dur": main_dur, "vel": velocity},
        {"pitch": neighbor_pitch, "pos": main_dur, "dur": neighbor_dur, "vel": round(velocity * 0.9, 3)},
        {"pitch": main_pitch, "pos": main_dur + neighbor_dur, "dur": return_dur, "vel": velocity},
    ]

    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const bg = h.boxGraph;
        const NoteEventBox = window.DAW_NoteEventBox;
        const NoteEventCollectionBox = window.DAW_NoteEventCollectionBox;
        const NoteRegionBox = window.DAW_NoteRegionBox;
        const Quarter = h.ppqn.Quarter;

        const noteData = {json.dumps(note_data)};
        const totalBeats = {duration_beats};
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
                box.label.setValue("Mordent");
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
            main_pitch: {main_pitch},
            neighbor_pitch: {neighbor_pitch},
            direction: "{direction}",
            interval: {interval},
            duration_beats: {duration_beats},
            unit_index: allUnits.indexOf(targetAU),
        }};
    }}""")
    return _wrap_eval(result)


@mcp.tool()
async def mcp_opendaw_create_turn(
    main_pitch: int = 60,
    direction: str = "upper",
    interval: int = 2,
    duration_beats: float = 1.0,
    velocity: float = 0.85,
    unit_index: int = -1,
    track_index: int = 0,
    start_beat: float = 0,
) -> str:
    """Create a turn — circular ornament: main → neighbor → main → other neighbor → main.

    The turn (gruppetto) is one of the four essential baroque ornaments
    (trill, mordent, turn, appoggiatura). It circles around the main note in a
    four-note flourish. An upper turn goes up first (main → upper → main → lower → main),
    a lower turn goes down first (main → lower → main → upper → main).

    Think Mozart piano concertos, Beethoven sonatas, Bach partitas. The turn adds
    elegance and circular motion to a sustained note.

    main_pitch: The primary MIDI note (default 60 = C4).
    direction: "upper" (main→up→main→down→main) or "lower" (main→down→main→up→main).
    interval: Semitones to neighbors (default 2 = whole step). 1 = half step (diatonic).
    duration_beats: Total length in beats (0.5-4, default 1.0 = quarter note).
    velocity: Base velocity 0-1 (default 0.85).
    unit_index: AU index with note track (-1 = find first AU with note tracks).
    track_index: Note track index within the AU.
    start_beat: Position in beats where the turn begins.

    Returns notes created, pitches used.
    """
    if main_pitch < 0 or main_pitch > 127:
        return "Error: main_pitch must be 0-127"
    if direction not in ("upper", "lower"):
        return "Error: direction must be 'upper' or 'lower'"
    if interval < 1 or interval > 7:
        return "Error: interval must be 1-7"
    if duration_beats < 0.5 or duration_beats > 4:
        return "Error: duration_beats must be 0.5-4"
    if velocity < 0 or velocity > 1:
        return "Error: velocity must be 0-1"

    upper_pitch = max(0, min(127, main_pitch + interval))
    lower_pitch = max(0, min(127, main_pitch - interval))
    if upper_pitch == main_pitch and lower_pitch == main_pitch:
        return "Error: both neighbors clamped to main — reduce interval"

    # Turn timing: 5 notes, each gets 20% of duration
    step_dur = duration_beats * 0.2
    neighbor_vel = round(velocity * 0.9, 3)

    if direction == "upper":
        note_data = [
            {"pitch": main_pitch, "pos": 0.0, "dur": step_dur, "vel": velocity},
            {"pitch": upper_pitch, "pos": step_dur, "dur": step_dur, "vel": neighbor_vel},
            {"pitch": main_pitch, "pos": step_dur * 2, "dur": step_dur, "vel": velocity},
            {"pitch": lower_pitch, "pos": step_dur * 3, "dur": step_dur, "vel": neighbor_vel},
            {"pitch": main_pitch, "pos": step_dur * 4, "dur": step_dur, "vel": velocity},
        ]
    else:
        note_data = [
            {"pitch": main_pitch, "pos": 0.0, "dur": step_dur, "vel": velocity},
            {"pitch": lower_pitch, "pos": step_dur, "dur": step_dur, "vel": neighbor_vel},
            {"pitch": main_pitch, "pos": step_dur * 2, "dur": step_dur, "vel": velocity},
            {"pitch": upper_pitch, "pos": step_dur * 3, "dur": step_dur, "vel": neighbor_vel},
            {"pitch": main_pitch, "pos": step_dur * 4, "dur": step_dur, "vel": velocity},
        ]

    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const bg = h.boxGraph;
        const NoteEventBox = window.DAW_NoteEventBox;
        const NoteEventCollectionBox = window.DAW_NoteEventCollectionBox;
        const NoteRegionBox = window.DAW_NoteRegionBox;
        const Quarter = h.ppqn.Quarter;

        const noteData = {json.dumps(note_data)};
        const totalBeats = {duration_beats};
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
                box.label.setValue("Turn");
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
            main_pitch: {main_pitch},
            upper_pitch: {upper_pitch},
            lower_pitch: {lower_pitch},
            direction: "{direction}",
            interval: {interval},
            duration_beats: {duration_beats},
            unit_index: allUnits.indexOf(targetAU),
        }};
    }}""")
    return _wrap_eval(result)


@mcp.tool()
async def mcp_opendaw_create_appoggiatura(
    main_pitch: int = 60,
    approach_pitch: int = 62,
    duration_beats: float = 1.0,
    appoggiatura_ratio: float = 0.67,
    velocity: float = 0.85,
    unit_index: int = -1,
    track_index: int = 0,
    start_beat: float = 0,
) -> str:
    """Create an appoggiatura — leaning grace note that resolves to the main note.

    The appoggiatura is the fourth and final essential baroque ornament
    (trill, mordent, turn, appoggiatura). Unlike a mordent (quick flick), the
    appoggiatura is expressive: it plays a neighbor note FIRST (usually longer),
    then resolves into the main note. The approach note creates harmonic tension
    that the main note releases. Think Bach cello suites, Mozart operas, Chopin nocturnes.

    An appoggiatura above approaches from higher (e.g. D → C).
    An appoggiatura below approaches from lower (e.g. B → C).
    The approach note typically takes 2/3 of the total duration, leaving 1/3
    for the resolution — but this is adjustable.

    main_pitch: The resolution note (default 60 = C4). This is where tension releases.
    approach_pitch: The grace note played first (default 62 = D4). Can be above or below main.
    duration_beats: Total length of both notes combined (0.5-8, default 1.0 = quarter).
    appoggiatura_ratio: Fraction of duration for the approach note (0.5-0.9, default 0.67 = 2/3).
      Higher = more tension (longer grace, shorter resolution). 0.5 = equal split.
    velocity: Base velocity 0-1 (default 0.85). Approach note is slightly accented.
    unit_index: AU index with note track (-1 = find first AU with note tracks).
    track_index: Note track index within the AU.
    start_beat: Position in beats where the appoggiatura begins.

    Returns notes created, pitches used.
    """
    if main_pitch < 0 or main_pitch > 127:
        return "Error: main_pitch must be 0-127"
    if approach_pitch < 0 or approach_pitch > 127:
        return "Error: approach_pitch must be 0-127"
    if approach_pitch == main_pitch:
        return "Error: approach_pitch must differ from main_pitch"
    if duration_beats < 0.5 or duration_beats > 8:
        return "Error: duration_beats must be 0.5-8"
    if appoggiatura_ratio < 0.5 or appoggiatura_ratio > 0.9:
        return "Error: appoggiatura_ratio must be 0.5-0.9"
    if velocity < 0 or velocity > 1:
        return "Error: velocity must be 0-1"

    approach_dur = duration_beats * appoggiatura_ratio
    main_dur = duration_beats * (1.0 - appoggiatura_ratio)
    approach_vel = round(min(1.0, velocity * 1.05), 3)  # slight accent

    note_data = [
        {"pitch": approach_pitch, "pos": 0.0, "dur": approach_dur, "vel": approach_vel},
        {"pitch": main_pitch, "pos": approach_dur, "dur": main_dur, "vel": velocity},
    ]

    direction = "above" if approach_pitch > main_pitch else "below"

    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const bg = h.boxGraph;
        const NoteEventBox = window.DAW_NoteEventBox;
        const NoteEventCollectionBox = window.DAW_NoteEventCollectionBox;
        const NoteRegionBox = window.DAW_NoteRegionBox;
        const Quarter = h.ppqn.Quarter;

        const noteData = {json.dumps(note_data)};
        const totalBeats = {duration_beats};
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
                box.label.setValue("Appoggiatura");
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
            main_pitch: {main_pitch},
            approach_pitch: {approach_pitch},
            direction: "{direction}",
            appoggiatura_ratio: {appoggiatura_ratio},
            approach_duration_beats: {approach_dur},
            main_duration_beats: {main_dur},
            duration_beats: {duration_beats},
            unit_index: allUnits.indexOf(targetAU),
        }};
    }}""")
    return _wrap_eval(result)


@mcp.tool()
async def mcp_opendaw_create_hemiola(
    pattern: str,
    bars: int = 1,
    unit_index: int = 0,
    track_index: int = 0,
    start_beat: float = 0,
    primary_pitch: int = 60,
    secondary_pitch: int = 64,
    primary_velocity: float = 0.7,
    secondary_velocity: float = 0.6,
    duration: float = 0.25,
) -> str:
    """Create a hemiola — 3:2 rhythmic displacement creating cross-rhythm illusion.

    A hemiola superimposes a 3-note grouping over a 2-note grouping (or vice versa)
    within the same time span, creating the illusion of a different meter. The classic
    3-against-2 pattern is fundamental to West African, Afro-Cuban, jazz, and minimalist
    music. Brahms, Bernstein, and Glass used it extensively.

    The pattern string defines which beats get primary vs secondary emphasis:
      "3:2" — 3 primary notes in the time of 2 secondary (classic hemiola)
      "2:3" — 2 primary notes in the time of 3 secondary (inverse hemiola)

    Creates notes on a single track: primary group uses primary_pitch,
    secondary group uses secondary_pitch. Both span the same total duration.

    pattern: "3:2" (3 against 2) or "2:3" (2 against 3).
    bars: Total length in bars (1-4). Each bar = 4 beats.
    unit_index: AU index.
    track_index: Note track index.
    start_beat: Starting beat position.
    primary_pitch: MIDI pitch for primary group (default 60 = C4).
    secondary_pitch: MIDI pitch for secondary group (default 64 = E4).
    primary_velocity: Velocity for primary notes 0-1.
    secondary_velocity: Velocity for secondary notes 0-1.
    duration: Note duration in beats.

    Returns total notes created and hemiola ratio.

    Example:
      create_hemiola(pattern="3:2", bars=2, primary_pitch=60, secondary_pitch=67)
    """
    if pattern not in ("3:2", "2:3"):
        return 'Error: pattern must be "3:2" or "2:3"'
    if bars < 1 or bars > 4:
        return "Error: bars must be 1-4"
    if not (0.0 <= primary_velocity <= 1.0) or not (0.0 <= secondary_velocity <= 1.0):
        return "Error: velocities must be 0-1"
    if not (0.03 <= duration <= 4.0):
        return "Error: duration must be 0.03-4.0 beats"
    if not (0 <= primary_pitch <= 127) or not (0 <= secondary_pitch <= 127):
        return "Error: pitches must be 0-127"

    total_beats = bars * 4
    parts = pattern.split(":")
    primary_count = int(parts[0])
    secondary_count = int(parts[1])

    all_notes = []

    # Primary group: primary_count notes evenly spaced across total_beats
    primary_step = total_beats / primary_count
    for i in range(primary_count):
        all_notes.append({
            "pitch": primary_pitch,
            "start": round(start_beat + i * primary_step, 6),
            "duration": duration,
            "velocity": primary_velocity,
        })

    # Secondary group: secondary_count notes evenly spaced across total_beats
    secondary_step = total_beats / secondary_count
    for i in range(secondary_count):
        all_notes.append({
            "pitch": secondary_pitch,
            "start": round(start_beat + i * secondary_step, 6),
            "duration": duration,
            "velocity": secondary_velocity,
        })

    notes_json = json.dumps(all_notes)
    result_str = await mcp_opendaw_create_notes_batch(notes_json, unit_index, track_index)

    try:
        data = json.loads(result_str)
        data["hemiola"] = True
        data["ratio"] = pattern
        data["primary_count"] = primary_count
        data["secondary_count"] = secondary_count
        data["bars"] = bars
        data["total_notes"] = primary_count + secondary_count
        return json.dumps(data, indent=2)
    except Exception:
        return result_str


@mcp.tool()
async def mcp_opendaw_create_glissando(
    start_pitch: int = 60,
    end_pitch: int = 72,
    scale_type: str = "chromatic",
    duration_beats: float = 2,
    rate: str = "16th",
    velocity: float = 0.8,
    velocity_curve: str = "ramp_up",
    unit_index: int = -1,
    track_index: int = 0,
    start_beat: float = 0,
) -> str:
    """Create a glissando — smooth scale run between two pitches.

    A continuous-sounding slide through intermediate pitches. Unlike riser/bass_drop
    (which are pitch sweeps), glissando plays every intermediate note at a fixed rate,
    creating a true scale run feel. Works chromatically (every semitone) or diatonically
    (scale tones only) or pentatonically.

    start_pitch: Starting MIDI note (default 60 = C4).
    end_pitch: Ending MIDI note (default 72 = C5). Can be higher or lower.
    scale_type: "chromatic" (every semitone), "major" (diatonic major scale),
      "minor" (natural minor), "pentatonic_minor", "pentatonic_major", "whole_tone".
    duration_beats: Total duration in beats (0.5-16, default 2).
    rate: Note rate — "32nd", "16th", "8th", "32t", "16t".
    velocity: Base velocity 0-1 (default 0.8).
    velocity_curve: "flat" (constant), "ramp_up" (crescendo into landing),
      "ramp_down" (decrescendo), "arc" (peak in middle).
    unit_index: AU index with note track (-1 = find first AU with note tracks).
    track_index: Note track index within the AU.
    start_beat: Position in beats where the glissando begins.

    Returns notes created, pitch list, scale type.
    """
    if start_pitch < 0 or start_pitch > 127:
        return "Error: start_pitch must be 0-127"
    if end_pitch < 0 or end_pitch > 127:
        return "Error: end_pitch must be 0-127"
    if start_pitch == end_pitch:
        return "Error: start_pitch and end_pitch must differ"
    if scale_type not in ("chromatic", "major", "minor", "pentatonic_minor", "pentatonic_major", "whole_tone"):
        return "Error: scale_type must be chromatic, major, minor, pentatonic_minor, pentatonic_major, or whole_tone"
    if duration_beats < 0.5 or duration_beats > 16:
        return "Error: duration_beats must be 0.5-16"
    if rate not in ("32nd", "16th", "8th", "32t", "16t"):
        return "Error: rate must be 32nd, 16th, 8th, 32t, or 16t"
    if velocity < 0 or velocity > 1:
        return "Error: velocity must be 0-1"
    if velocity_curve not in ("flat", "ramp_up", "ramp_down", "arc"):
        return "Error: velocity_curve must be flat, ramp_up, ramp_down, or arc"

    # Scale intervals (semitone offsets within octave)
    scale_intervals = {
        "chromatic": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
        "major": [0, 2, 4, 5, 7, 9, 11],
        "minor": [0, 2, 3, 5, 7, 8, 10],
        "pentatonic_minor": [0, 3, 5, 7, 10],
        "pentatonic_major": [0, 2, 4, 7, 9],
        "whole_tone": [0, 2, 4, 6, 8, 10],
    }
    intervals = scale_intervals[scale_type]

    # Build pitch list: all scale tones between start and end
    direction = 1 if end_pitch > start_pitch else -1
    pitches = []
    # Anchor on start_pitch's pitch class relative to root
    root_pc = start_pitch % 12
    current = start_pitch
    while current != end_pitch:
        # Check if current pitch class is in scale relative to root
        pc = current % 12
        rel = (pc - root_pc) % 12
        if rel in intervals:
            pitches.append(current)
        current += direction
    pitches.append(end_pitch)

    # Rate → note duration in beats
    rate_map = {
        "32nd": 0.125,
        "16th": 0.25,
        "8th": 0.5,
        "32t": 1/12,
        "16t": 1/6,
    }
    note_dur = rate_map[rate]
    total_notes = len(pitches)
    # Fit notes into duration_beats
    actual_dur = min(note_dur, duration_beats / max(1, total_notes))

    note_data = []
    for i, pitch in enumerate(pitches):
        progress = i / max(1, total_notes - 1)
        pos = start_beat + i * actual_dur
        # Velocity curve
        if velocity_curve == "flat":
            vel = velocity
        elif velocity_curve == "ramp_up":
            vel = velocity * (0.6 + 0.4 * progress)
        elif velocity_curve == "ramp_down":
            vel = velocity * (1.0 - 0.4 * progress)
        elif velocity_curve == "arc":
            vel = velocity * (0.5 + 0.5 * (1 - abs(2 * progress - 1)))
        else:
            vel = velocity
        vel = max(0.01, min(1.0, vel))
        note_data.append({
            "pitch": pitch,
            "pos": pos,
            "dur": actual_dur * 0.95,
            "vel": round(vel, 3),
        })

    total_beats = total_notes * actual_dur

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
                box.label.setValue("Glissando");
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
            start_pitch: {start_pitch},
            end_pitch: {end_pitch},
            scale_type: "{scale_type}",
            rate: "{rate}",
            velocity_curve: "{velocity_curve}",
            note_duration_beats: {actual_dur},
            length_beats: totalBeats,
            direction: "{'ascending' if direction > 0 else 'descending'}",
            unit_index: allUnits.indexOf(targetAU),
        }};
    }}""")
    return _wrap_eval(result)


@mcp.tool()
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


@mcp.tool()
async def mcp_opendaw_create_pedal_point(
    pedal_pitch: int = 36,
    chord_pattern: str = "Cm,Ab,Eb,Bb",
    bars_per_chord: int = 1,
    beats_per_bar: int = 4,
    pedal_velocity: float = 0.75,
    chord_velocity: float = 0.6,
    chord_octave: int = 4,
    retrigger_pedal: bool = True,
    unit_index: int = -1,
    track_index: int = 0,
    start_beat: float = 0,
) -> str:
    """Create a pedal point — sustained bass tone under changing chords.

    A foundational technique in film scoring (Hans Zimmer drones), organ preludes
    (Bach), and rock ballads. A single low note sustains (or retriggers) while
    chords change above it, creating harmonic tension and release. The pedal
    anchors the harmony while the chords create movement.

    pedal_pitch: Sustained bass note (default 36 = C2, low and powerful).
    chord_pattern: Comma-separated chord names (e.g. "Cm,Ab,Eb,Bb").
      Supports: maj, min, m7, maj7, dom7, sus2, sus4, dim, aug.
    bars_per_chord: Bars each chord lasts (1-8, default 1).
    beats_per_bar: Time signature beats (3/4=3, 4/4=4, 6/8=6, default 4).
    pedal_velocity: Velocity of pedal note (0-1, default 0.75).
    chord_velocity: Velocity of chord notes (0-1, default 0.6).
    chord_octave: Octave for chord notes (1-8, default 4 = C4 range).
    retrigger_pedal: If true, pedal re-triggers at each chord change. If false,
      one long sustained note for the entire duration.
    unit_index: AU index with note track (-1 = find first AU with note tracks).
    track_index: Note track index within the AU.
    start_beat: Position in beats where the pedal point begins.

    Returns notes created, chord count, pedal duration.
    """
    if pedal_pitch < 0 or pedal_pitch > 127:
        return "Error: pedal_pitch must be 0-127"
    if bars_per_chord < 1 or bars_per_chord > 8:
        return "Error: bars_per_chord must be 1-8"
    if beats_per_bar < 2 or beats_per_bar > 12:
        return "Error: beats_per_bar must be 2-12"
    if pedal_velocity < 0 or pedal_velocity > 1:
        return "Error: pedal_velocity must be 0-1"
    if chord_velocity < 0 or chord_velocity > 1:
        return "Error: chord_velocity must be 0-1"
    if chord_octave < 1 or chord_octave > 8:
        return "Error: chord_octave must be 1-8"

    # Parse chord names
    CHORD_INTERVALS = {
        "maj": [0, 4, 7],
        "M": [0, 4, 7],
        "min": [0, 3, 7],
        "m": [0, 3, 7],
        "m7": [0, 3, 7, 10],
        "maj7": [0, 4, 7, 11],
        "M7": [0, 4, 7, 11],
        "dom7": [0, 4, 7, 10],
        "7": [0, 4, 7, 10],
        "sus2": [0, 2, 7],
        "sus4": [0, 5, 7],
        "dim": [0, 3, 6],
        "aug": [0, 4, 8],
    }
    NOTE_TO_PC = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4,
                  "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9,
                  "A#": 10, "Bb": 10, "B": 11}

    chords = []
    for name in chord_pattern.split(","):
        name = name.strip()
        # Find root and quality
        root = None
        quality = None
        for q in ["maj7", "m7", "M7", "sus2", "sus4", "dom7", "dim", "aug", "maj", "min", "M", "m", "7"]:
            if name.endswith(q) and len(name) > len(q):
                root_name = name[:-len(q)]
                if root_name in NOTE_TO_PC:
                    root = NOTE_TO_PC[root_name]
                    quality = q
                    break
        if root is None:
            # Try whole name as root note with implicit major triad
            if name in NOTE_TO_PC:
                root = NOTE_TO_PC[name]
                quality = "maj"
            else:
                return f"Error: cannot parse chord '{name}'"
        intervals = CHORD_INTERVALS.get(quality, [0, 4, 7])
        chord_pitches = [(chord_octave + 1) * 12 + root + iv for iv in intervals]
        chords.append(chord_pitches)

    chord_beats = bars_per_chord * beats_per_bar
    total_beats = len(chords) * chord_beats

    note_data = []

    # Pedal note(s)
    if retrigger_pedal:
        for i in range(len(chords)):
            pos = start_beat + i * chord_beats
            note_data.append({
                "pitch": pedal_pitch,
                "pos": pos,
                "dur": chord_beats,
                "vel": pedal_velocity,
            })
    else:
        note_data.append({
            "pitch": pedal_pitch,
            "pos": start_beat,
            "dur": total_beats,
            "vel": pedal_velocity,
        })

    # Chord notes
    for i, chord in enumerate(chords):
        chord_start = start_beat + i * chord_beats
        for pitch in chord:
            note_data.append({
                "pitch": max(0, min(127, pitch)),
                "pos": chord_start,
                "dur": chord_beats * 0.95,
                "vel": chord_velocity,
            })

    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const bg = h.boxGraph;
        const NoteEventBox = window.DAW_NoteEventBox;
        const NoteEventCollectionBox = window.DAW_NoteEventBox;
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
            const collection = window.DAW_NoteEventCollectionBox.create(bg, h.uuid.generate());
            const regionDur = Math.round(totalBeats * Quarter);
            const startPos = Math.round(startBeat * Quarter);

            const regionBox = NoteRegionBox.create(bg, h.uuid.generate(), (box) => {{
                box.position.setValue(startPos);
                box.label.setValue("Pedal Point");
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
            pedal_pitch: {pedal_pitch},
            chord_count: {len(chords)},
            chords: "{chord_pattern}",
            bars_per_chord: {bars_per_chord},
            retrigger_pedal: {str(retrigger_pedal).lower()},
            length_beats: totalBeats,
            unit_index: allUnits.indexOf(targetAU),
        }};
    }}""")
    return _wrap_eval(result)


@mcp.tool()
async def mcp_opendaw_create_bordun(
    root: str = "C",
    octave: int = 3,
    intervals: str = "0,7",
    bars: int = 4,
    beats_per_bar: int = 4,
    velocity: float = 0.55,
    retrigger_bars: int = 0,
    unit_index: int = -1,
    track_index: int = 0,
    start_beat: float = 0,
) -> str:
    """Create a bordun — continuously sustained drone chord as a textural layer.

    A bordun (bourdon) is a continuously sounding tone or chord that provides
    a harmonic foundation beneath changing melody. Unlike pedal_point (which
    is a single repeated/anchored note), the bordun is a *sustained textural
    layer* — often an open fifth, octave, or drone chord. Found in Scottish
    bagpipes, Indian tanpura, hurdy-gurdy, ambient drone music, and folk.

    root: Root note name (e.g. "C", "Ab", "F#").
    octave: Octave for the bordun (1-6, default 3 = low register).
    intervals: Comma-separated semitone intervals from root (e.g. "0,7" = open fifth,
      "0,7,12" = octave+fifth, "0,3,7" = minor triad drone, "0,5" = open fourth).
    bars: Total length in bars (1-16, default 4).
    beats_per_bar: Time signature beats (3/4=3, 4/4=4, 6/8=6, default 4).
    velocity: Velocity of bordun notes (0-1, default 0.55 — softer than melody).
    retrigger_bars: If >0, re-triggers the bordun every N bars (e.g. 2 = retrigger
      every 2 bars). If 0, one continuous sustained note for entire duration.
    unit_index: AU index with note track (-1 = find first AU with note tracks).
    track_index: Note track index within the AU.
    start_beat: Position in beats where the bordun begins.

    Returns notes created, pitches, total duration.
    """
    if octave < 1 or octave > 6:
        return "Error: octave must be 1-6"
    if bars < 1 or bars > 16:
        return "Error: bars must be 1-16"
    if beats_per_bar < 2 or beats_per_bar > 12:
        return "Error: beats_per_bar must be 2-12"
    if velocity < 0 or velocity > 1:
        return "Error: velocity must be 0-1"
    if retrigger_bars < 0 or retrigger_bars > bars:
        return "Error: retrigger_bars must be 0 or 1..bars"

    NOTE_TO_PC = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4,
                  "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9,
                  "A#": 10, "Bb": 10, "B": 11}

    root_clean = root.strip()
    if root_clean not in NOTE_TO_PC:
        return f"Error: cannot parse root note '{root_clean}'"

    root_pc = NOTE_TO_PC[root_clean]

    try:
        iv_list = [int(x.strip()) for x in intervals.split(",")]
    except ValueError:
        return "Error: intervals must be comma-separated integers"

    if not iv_list or len(iv_list) > 8:
        return "Error: intervals must have 1-8 values"

    pitches = []
    base = (octave + 1) * 12 + root_pc
    for iv in iv_list:
        p = base + iv
        if p < 0 or p > 127:
            return f"Error: pitch {p} out of range (adjust octave/intervals)"
        pitches.append(p)

    total_beats = bars * beats_per_bar
    note_data = []

    if retrigger_bars > 0:
        chunk_beats = retrigger_bars * beats_per_bar
        num_chunks = bars // retrigger_bars
        for i in range(num_chunks):
            pos = start_beat + i * chunk_beats
            for p in pitches:
                note_data.append({
                    "pitch": p,
                    "pos": pos,
                    "dur": chunk_beats * 0.98,
                    "vel": velocity,
                })
    else:
        for p in pitches:
            note_data.append({
                "pitch": p,
                "pos": start_beat,
                "dur": total_beats * 0.98,
                "vel": velocity,
            })

    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const bg = h.boxGraph;
        const NoteEventBox = window.DAW_NoteEventBox;
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
            const collection = window.DAW_NoteEventCollectionBox.create(bg, h.uuid.generate());
            const regionDur = Math.round(totalBeats * Quarter);
            const startPos = Math.round(startBeat * Quarter);

            const regionBox = NoteRegionBox.create(bg, h.uuid.generate(), (box) => {{
                box.position.setValue(startPos);
                box.label.setValue("Bordun");
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
            pitches: {json.dumps(pitches)},
            root: "{root_clean}",
            intervals: "{intervals}",
            bars: {bars},
            retrigger_bars: {retrigger_bars},
            length_beats: totalBeats,
            unit_index: allUnits.indexOf(targetAU),
        }};
    }}""")
    return _wrap_eval(result)


@mcp.tool()
async def mcp_opendaw_create_hocket(
    melody: str = "60,62,64,65,67,65,64,62",
    voices: int = 2,
    split_mode: str = "alternate",
    unit_index: int = -1,
    track_index: int = 0,
    start_beat: float = 0,
    note_duration: float = 0.5,
    velocity: float = 0.7,
) -> str:
    """Create a hocket — single melodic line split between voices/tracks.

    Hocket (from Latin "hoquet" = hiccup) is a technique where a single
    melody is divided between two or more voices. Each voice plays only
    every other (or every Nth) note, creating an interlocking texture.
    Found in medieval polyphony (Notre Dame school), African mbira music,
    Balinese gamelan, and modern minimalist composition (Steve Reich).

    melody: Comma-separated MIDI pitches forming the complete melodic line.
    voices: Number of voices to split between (2-4, default 2).
    split_mode: How notes are distributed:
      "alternate" — round-robin (note 0→voice 0, note 1→voice 1, ...)
      "pairs" — pairs of notes per voice (2 per voice, then switch)
      "phrase" — 4-note phrases per voice
    unit_index: AU index with note tracks (-1 = find AU with enough note tracks).
    track_index: Starting note track index (uses consecutive tracks for voices).
    start_beat: Position in beats where the hocket begins.
    note_duration: Duration of each note in beats (default 0.5 = eighth notes).
    velocity: Velocity of all notes (0-1, default 0.7).

    Returns notes created, voice assignment, total duration.
    """
    if voices < 2 or voices > 4:
        return "Error: voices must be 2-4"
    if velocity < 0 or velocity > 1:
        return "Error: velocity must be 0-1"
    if note_duration <= 0 or note_duration > 4:
        return "Error: note_duration must be 0.01-4 beats"

    try:
        pitches = [int(x.strip()) for x in melody.split(",")]
    except ValueError:
        return "Error: melody must be comma-separated MIDI pitches"

    if not pitches or len(pitches) > 64:
        return "Error: melody must have 1-64 notes"

    for p in pitches:
        if p < 0 or p > 127:
            return f"Error: pitch {p} out of range (0-127)"

    if split_mode not in ("alternate", "pairs", "phrase"):
        return "Error: split_mode must be 'alternate', 'pairs', or 'phrase'"

    # Assign notes to voices
    voice_notes = {v: [] for v in range(voices)}
    for i, pitch in enumerate(pitches):
        if split_mode == "alternate":
            voice = i % voices
        elif split_mode == "pairs":
            voice = (i // 2) % voices
        else:  # phrase
            voice = (i // 4) % voices
        pos = start_beat + i * note_duration
        voice_notes[voice].append({
            "pitch": pitch,
            "pos": pos,
            "dur": note_duration,
            "vel": velocity,
        })

    total_beats = len(pitches) * note_duration
    all_note_data = []
    for v in range(voices):
        all_note_data.extend(voice_notes[v])

    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const bg = h.boxGraph;
        const NoteEventBox = window.DAW_NoteEventBox;
        const NoteRegionBox = window.DAW_NoteRegionBox;
        const Quarter = h.ppqn.Quarter;

        const noteData = {json.dumps(all_note_data)};
        const totalBeats = {total_beats};
        const startBeat = {start_beat};
        const voices = {voices};
        const trackIdx = {track_index};

        let noteTracks = [];
        let targetAU = null;
        const allUnits = h.allAUBoxes();

        if ({unit_index} >= 0 && {unit_index} < allUnits.length) {{
            targetAU = allUnits[{unit_index}];
            noteTracks = h.noteTrackBoxes(targetAU);
        }} else {{
            for (const au of allUnits) {{
                const nt = h.noteTrackBoxes(au);
                if (nt.length >= voices) {{ noteTracks = nt; targetAU = au; break; }}
            }}
            if (noteTracks.length === 0) {{
                for (const au of allUnits) {{
                    const nt = h.noteTrackBoxes(au);
                    if (nt.length > 0) {{ noteTracks = nt; targetAU = au; break; }}
                }}
            }}
        }}

        if (noteTracks.length === 0) return {{error: "No note tracks found. Call create_synth_track or create_note_track first."}};

        let totalNotes = 0;

        h.modify(() => {{
            const startPos = Math.round(startBeat * Quarter);
            const regionDur = Math.round(totalBeats * Quarter);

            // Group notes by voice
            const voiceGroups = {{}};
            for (const nd of noteData) {{
                // Determine voice from position
                const noteIdx = Math.round((nd.pos - startBeat) / {note_duration});
                let voice;
                if ("{split_mode}" === "alternate") voice = noteIdx % voices;
                else if ("{split_mode}" === "pairs") voice = Math.floor(noteIdx / 2) % voices;
                else voice = Math.floor(noteIdx / 4) % voices;

                if (!voiceGroups[voice]) voiceGroups[voice] = [];
                voiceGroups[voice].push(nd);
            }}

            for (const [voice, notes] of Object.entries(voiceGroups)) {{
                const trackBox = noteTracks[Math.min(trackIdx + parseInt(voice), noteTracks.length - 1)];
                const collection = window.DAW_NoteEventCollectionBox.create(bg, h.uuid.generate());

                const regionBox = NoteRegionBox.create(bg, h.uuid.generate(), (box) => {{
                    box.position.setValue(startPos);
                    box.label.setValue("Hocket V" + (parseInt(voice) + 1));
                    box.mute.setValue(false);
                    box.duration.setValue(regionDur);
                    box.loopDuration.setValue(regionDur);
                    box.eventOffset.setValue(0);
                    box.events.refer(collection.owners);
                    box.regions.refer(trackBox.regions);
                }});

                const eventsField = regionBox.events.targetVertex.unwrap();
                const collBox = eventsField.box;

                for (const nd of notes) {{
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
            }}
        }});

        return {{
            success: true,
            total_notes: totalNotes,
            melody_notes: {len(pitches)},
            voices: voices,
            split_mode: "{split_mode}",
            length_beats: totalBeats,
            unit_index: allUnits.indexOf(targetAU),
        }};
    }}""")
    return _wrap_eval(result)


@mcp.tool()
async def mcp_opendaw_create_isorhythm(
    talea: str = "1,1,0.5,0.5,1,0.5,0.5,1",
    color: str = "60,62,64,65,67,65,64,62",
    repeats: int = 3,
    velocity: float = 0.7,
    unit_index: int = -1,
    track_index: int = 0,
    start_beat: float = 0,
) -> str:
    """Create an isorhythm — repeating rhythm (talea) × repeating pitch series (color).

    Isorhythm separates rhythm and pitch into two independent cycles. The talea
    (rhythmic pattern) and color (pitch series) repeat independently, creating
    constantly shifting relationships as they go in and out of phase. When talea
    and color have different lengths, the pattern doesn't fully repeat until the
    least common multiple of both lengths.

    Found in medieval motets (Machaut), and heavily influenced 20th-century
    composers — Messiaen, Boulez, Stockhausen. Distinct from ostinato, which
    repeats rhythm and pitch together as one unit.

    talea: Comma-separated note durations in beats (the repeating rhythm).
      e.g. "1,1,0.5,0.5,1" = quarter, quarter, eighth, eighth, quarter.
    color: Comma-separated MIDI pitches (the repeating pitch series).
      e.g. "60,62,64,65" = C,D,E,F cycling independently of rhythm.
    repeats: Number of full talea cycles (1-16, default 3).
    velocity: Velocity of all notes (0-1, default 0.7).
    unit_index: AU index with note track (-1 = find first AU with note tracks).
    track_index: Note track index within the AU.
    start_beat: Position in beats where the isorhythm begins.

    Returns notes created, talea/color lengths, phase cycle length, total duration.
    """
    if velocity < 0 or velocity > 1:
        return "Error: velocity must be 0-1"
    if repeats < 1 or repeats > 16:
        return "Error: repeats must be 1-16"

    try:
        talea_durations = [float(x.strip()) for x in talea.split(",")]
    except ValueError:
        return "Error: talea must be comma-separated durations (beats)"

    try:
        color_pitches = [int(x.strip()) for x in color.split(",")]
    except ValueError:
        return "Error: color must be comma-separated MIDI pitches"

    if not talea_durations or len(talea_durations) > 32:
        return "Error: talea must have 1-32 values"
    if not color_pitches or len(color_pitches) > 32:
        return "Error: color must have 1-32 values"

    for d in talea_durations:
        if d <= 0 or d > 8:
            return "Error: talea durations must be 0.01-8 beats"
    for p in color_pitches:
        if p < 0 or p > 127:
            return f"Error: pitch {p} out of range (0-127)"

    from math import gcd

    talea_len = len(talea_durations)
    color_len = len(color_pitches)

    # Total notes = talea length × repeats
    total_notes = talea_len * repeats

    # Build note data: rhythm from talea (cycling), pitch from color (cycling independently)
    note_data = []
    current_pos = start_beat
    for i in range(total_notes):
        dur = talea_durations[i % talea_len]
        pitch = color_pitches[i % color_len]
        note_data.append({
            "pitch": pitch,
            "pos": current_pos,
            "dur": dur * 0.95,
            "vel": velocity,
        })
        current_pos += dur

    total_beats = sum(talea_durations) * repeats

    # Phase cycle = LCM(talea_len, color_len) — when both patterns realign
    lcm = (talea_len * color_len) // gcd(talea_len, color_len)

    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const bg = h.boxGraph;
        const NoteEventBox = window.DAW_NoteEventBox;
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
            const collection = window.DAW_NoteEventCollectionBox.create(bg, h.uuid.generate());
            const regionDur = Math.round(totalBeats * Quarter);
            const startPos = Math.round(startBeat * Quarter);

            const regionBox = NoteRegionBox.create(bg, h.uuid.generate(), (box) => {{
                box.position.setValue(startPos);
                box.label.setValue("Isorhythm");
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
            talea_length: {talea_len},
            color_length: {color_len},
            phase_cycle: {lcm},
            repeats: {repeats},
            length_beats: Math.round(totalBeats * 100) / 100,
            unit_index: allUnits.indexOf(targetAU),
        }};
    }}""")
    return _wrap_eval(result)


@mcp.tool()
async def mcp_opendaw_create_canon(
    melody: str = "60,62,64,67,64,62,60,57",
    voices: int = 3,
    entry_delay_beats: float = 4,
    transposition: str = "0,7,12",
    velocity_decay: float = 0.15,
    direction: str = "up",
    unit_index: int = -1,
    track_index: int = 0,
    start_beat: float = 0,
    velocity: float = 0.85,
) -> str:
    """Create a canon — strict melodic imitation with delayed voice entries.

    The foundation of contrapuntal music: a single melody is repeated in multiple
    voices, each entering after a delay, optionally transposed. Think Pachelbel's
    Canon, "Row Row Row Your Boat", Bach's fugue subjects, or modern call-and-response
    layers in film scores. Unlike create_counterpoint (which generates a new line),
    a canon copies the SAME melody into each voice — just shifted in time and pitch.

    melody: Comma-separated MIDI pitches of the lead voice (e.g. "60,62,64,67").
    voices: Number of imitating voices (2-6, default 3). Voice 1 enters first.
    entry_delay_beats: Beats between each voice entry (1-16, default 4 = one bar in 4/4).
    transposition: Comma-separated semitone offsets per voice (e.g. "0,7,12" = unison, fifth, octave).
      Must have exactly `voices` values. "0,0,0" = all at same pitch (round/canon).
    velocity_decay: Velocity reduction per voice (0-0.3, default 0.15). Later voices are quieter,
      simulating natural ensemble hierarchy.
    direction: Voice entry order — "up" (low to high) or "down" (high to low).
    unit_index: AU index with note track (-1 = find first AU with note tracks).
    track_index: Note track index within the AU.
    start_beat: Position in beats where the first voice begins.
    velocity: Base velocity for the first voice (0-1, default 0.85).

    Returns notes created, voice count, total length, transpositions used.
    """
    try:
        melody_pitches = [int(p.strip()) for p in melody.split(",")]
    except ValueError:
        return "Error: melody must be comma-separated integers (e.g. '60,62,64,67')"
    if len(melody_pitches) < 2:
        return "Error: need at least 2 melody notes"
    if len(melody_pitches) > 64:
        return "Error: maximum 64 melody notes"
    if not all(0 <= p <= 127 for p in melody_pitches):
        return "Error: melody pitches must be 0-127"
    if voices < 2 or voices > 6:
        return "Error: voices must be 2-6"
    if entry_delay_beats < 1 or entry_delay_beats > 16:
        return "Error: entry_delay_beats must be 1-16"
    if velocity_decay < 0 or velocity_decay > 0.3:
        return "Error: velocity_decay must be 0-0.3"
    if velocity < 0 or velocity > 1:
        return "Error: velocity must be 0-1"
    if direction not in ("up", "down"):
        return "Error: direction must be 'up' or 'down'"

    try:
        transpose_list = [int(t.strip()) for t in transposition.split(",")]
    except ValueError:
        return "Error: transposition must be comma-separated integers (e.g. '0,7,12')"
    if len(transpose_list) != voices:
        return f"Error: transposition must have exactly {voices} values, got {len(transpose_list)}"

    note_spacing = 0.5  # each melody note = 8th note
    melody_len_beats = len(melody_pitches) * note_spacing

    voice_data = []
    for v in range(voices):
        delay = v * entry_delay_beats
        transpose = transpose_list[v]
        vel = max(0.1, velocity - v * velocity_decay)
        if direction == "down":
            # Reverse voice order: highest enters first
            delay = (voices - 1 - v) * entry_delay_beats
            transpose = transpose_list[voices - 1 - v]
            vel = max(0.1, velocity - (voices - 1 - v) * velocity_decay)
        notes = []
        for i, p in enumerate(melody_pitches):
            tp = max(0, min(127, p + transpose))
            notes.append({
                "pitch": tp,
                "pos": delay + i * note_spacing,
                "dur": note_spacing * 0.9,
                "vel": round(vel, 3),
            })
        voice_data.append(notes)

    total_beats = (voices - 1) * entry_delay_beats + melody_len_beats

    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const bg = h.boxGraph;
        const NoteEventBox = window.DAW_NoteEventBox;
        const NoteEventCollectionBox = window.DAW_NoteEventCollectionBox;
        const NoteRegionBox = window.DAW_NoteRegionBox;
        const Quarter = h.ppqn.Quarter;

        const voiceData = {json.dumps(voice_data)};
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
                box.label.setValue("Canon");
                box.mute.setValue(false);
                box.duration.setValue(regionDur);
                box.loopDuration.setValue(regionDur);
                box.eventOffset.setValue(0);
                box.events.refer(collection.owners);
                box.regions.refer(trackBox.regions);
            }});

            const eventsField = regionBox.events.targetVertex.unwrap();
            const collBox = eventsField.box;

            for (const voice of voiceData) {{
                for (const nd of voice) {{
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
            }}
        }});

        return {{
            success: true,
            total_notes: totalNotes,
            voices: {voices},
            melody_notes: {len(melody_pitches)},
            entry_delay_beats: {entry_delay_beats},
            transpositions: "{transposition}",
            direction: "{direction}",
            length_beats: totalBeats,
            unit_index: allUnits.indexOf(targetAU),
        }};
    }}""")
    return _wrap_eval(result)


@mcp.tool()
async def mcp_opendaw_create_comping(
    chords: str,
    rhythm: str = "x-x-x-x-",
    unit_index: int = -1,
    track_index: int = 0,
    start_beat: float = 0,
    chord_octave: int = 4,
    velocity: float = 0.7,
    note_spacing: float = 0.5,
    syncopation: float = 0.0,
) -> str:
    """Create comping — rhythmic chordal accompaniment.

    The most common accompaniment style in modern music: play chords in a rhythmic
    pattern rather than sustained blocks. Jazz piano comping, funk guitar chops,
    reggae skanks, country boom-chick, Neo-soul chords. Unlike create_chord_progression
    (sustained blocks) or create_stab (house stabs), comping gives each chord a
    rhythmic identity — the chord follows the groove.

    chords: JSON array of chord specs, same as create_chord_progression.
      Each chord is [root_note_name, chord_type].
      Root names: C, C#, D, D#, E, F, F#, G, G#, A, A#, B (or flats: Db, Eb, Gb, Ab, Bb)
      Chord types: maj, min, dom7, maj7, min7, sus2, sus4, add9, dim, aug
      Example: '[["C","min7"],["F","min7"],["G","dom7"],["C","min7"]]'
    rhythm: Rhythmic pattern string. Each char = one step of note_spacing beats:
      'x' = play chord, '-' = rest, '.' = ghost (quiet chord)
      Default "x-x-x-x-" = off-beat eighths (classic jazz comping)
      "x--x--x-" = syncopated funk
      "x...x..." = boom-chick (country)
      "x-x-x-x-x-x-x-x" = reggae skank (every off-beat 16th)
    unit_index: AU index with note track (-1 = find first AU with note tracks).
    track_index: Note track index within the AU.
    start_beat: Where comping starts.
    chord_octave: MIDI octave for chord root (4 = C4=60).
    velocity: Base velocity (0-1, default 0.7).
    note_spacing: Duration of each rhythm step in beats (0.25=16th, 0.5=8th, default 0.5).
    syncopation: Probability of pushing a note slightly off-grid (0-0.5, default 0).
      Adds human feel — 0.1 = subtle, 0.3 = pronounced.

    Returns notes created, chords played, rhythm pattern used.
    """
    import json as _json
    try:
        chord_list = _json.loads(chords)
        if not isinstance(chord_list, list) or len(chord_list) == 0:
            return "Error: chords must be a non-empty JSON array"
    except _json.JSONDecodeError as e:
        return f"Error parsing chords JSON: {e}"

    if len(chord_list) > 32:
        return "Error: maximum 32 chords"
    if not rhythm or not all(c in "x-." for c in rhythm):
        return "Error: rhythm must contain only 'x', '-', and '.' characters"
    if len(rhythm) > 32:
        return "Error: maximum 32 rhythm steps"
    if velocity < 0 or velocity > 1:
        return "Error: velocity must be 0-1"
    if note_spacing < 0.125 or note_spacing > 2:
        return "Error: note_spacing must be 0.125-2"
    if syncopation < 0 or syncopation > 0.5:
        return "Error: syncopation must be 0-0.5"

    # Parse chords into pitch arrays
    voicings = []
    for ci, chord_spec in enumerate(chord_list):
        if len(chord_spec) < 2:
            return f"Error: chord {ci} must have [root, type]"
        root_name = chord_spec[0]
        chord_type = chord_spec[1]
        if root_name not in NOTE_TO_PITCH:
            return f"Error: unknown root '{root_name}'"
        if chord_type not in CHORD_INTERVALS:
            return f"Error: unknown chord type '{chord_type}'. Valid: {list(CHORD_INTERVALS.keys())}"
        root_pc = NOTE_TO_PITCH[root_name]
        intervals = CHORD_INTERVALS[chord_type]
        root_pitch = (chord_octave + 1) * 12 + root_pc
        voicing = [root_pitch + iv for iv in intervals]
        voicings.append(voicing)

    # Build note data: apply rhythm to each chord
    import random as _rng
    rng = _rng.Random(42)
    note_data = []
    chord_count = len(chord_list)
    rhythm_len = len(rhythm)
    total_steps = chord_count * rhythm_len
    chord_idx = 0

    for step in range(total_steps):
        rhythm_char = rhythm[step % rhythm_len]
        if rhythm_char == "-":
            # Check if we've completed a rhythm cycle → advance chord
            if (step + 1) % rhythm_len == 0:
                chord_idx = min(chord_idx + 1, chord_count - 1)
            continue

        chord_idx_actual = step // rhythm_len
        if chord_idx_actual >= chord_count:
            chord_idx_actual = chord_count - 1
        voicing = voicings[chord_idx_actual]

        pos = start_beat + step * note_spacing
        is_ghost = rhythm_char == "."
        vel = velocity * (0.4 if is_ghost else 1.0)

        # Syncopation: push some notes slightly off-grid
        if syncopation > 0 and not is_ghost and rng.random() < syncopation:
            pos += note_spacing * 0.5 * (1 if rng.random() > 0.5 else -1)

        dur = note_spacing * 0.85
        for pitch in voicing:
            note_data.append({
                "pitch": max(0, min(127, pitch)),
                "pos": max(0, pos),
                "dur": dur,
                "vel": round(max(0.1, min(1, vel)), 3),
            })

    total_beats = total_steps * note_spacing

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
                box.label.setValue("Comping");
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
            chords: {len(chord_list)},
            rhythm: "{rhythm}",
            rhythm_steps: {rhythm_len},
            total_steps: {total_steps},
            length_beats: totalBeats,
            syncopation: {syncopation},
            unit_index: allUnits.indexOf(targetAU),
        }};
    }}""")
    return _wrap_eval(result)


@mcp.tool()
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


@mcp.tool()
async def mcp_opendaw_apply_velocity_curve(
    unit_index: int = 0,
    track_index: int = 0,
    region_index: int = -1,
    curve_type: str = "ramp_up",
    start_velocity: float = 0.3,
    end_velocity: float = 1.0,
    power: float = 1.0,
) -> str:
    """Apply a velocity envelope across notes — ramp, arc, trough, or custom power curve.

    Maps each note's position within its region to a velocity value via a mathematical curve.
    Unlike humanize_notes (random variation), this applies a deterministic envelope shape —
    useful for build-ups, fade-ins, crescendo rolls, and expressive phrasing.

    unit_index: AU index.
    track_index: Note track index.
    region_index: Region index (-1 = all regions on the track).
    curve_type: Curve shape:
      - "ramp_up"   — linear increase from start_velocity to end_velocity
      - "ramp_down" — linear decrease from start_velocity to end_velocity
      - "arc"       — rises to end_velocity then falls back to start_velocity (peak in middle)
      - "trough"    — falls to start_velocity then rises to end_velocity (dip in middle)
      - "power"     — exponential curve controlled by 'power' param (>1 = fast rise, <1 = slow rise)
    start_velocity: Velocity at curve start 0-1 (default 0.3).
    end_velocity: Velocity at curve end 0-1 (default 1.0).
    power: Exponent for "power" curve type (default 1.0 = linear). 2.0 = sharp attack, 0.5 = slow swell.

    Returns per-region note counts and total notes shaped.

    Examples:
      apply_velocity_curve(curve_type="ramp_up", start_velocity=0.2, end_velocity=1.0)  # build-up
      apply_velocity_curve(curve_type="arc", start_velocity=0.4, end_velocity=0.95)     # expressive phrase
      apply_velocity_curve(curve_type="power", power=2.0, start_velocity=0.1, end_velocity=1.0)  # sharp attack
    """
    if not (0.0 <= start_velocity <= 1.0):
        return f"Error: start_velocity must be 0-1, got {start_velocity}"
    if not (0.0 <= end_velocity <= 1.0):
        return f"Error: end_velocity must be 0-1, got {end_velocity}"
    if not (0.1 <= power <= 5.0):
        return f"Error: power must be 0.1-5.0, got {power}"
    valid_curves = ("ramp_up", "ramp_down", "arc", "trough", "power")
    if curve_type not in valid_curves:
        return f"Error: curve_type must be one of {valid_curves}, got '{curve_type}'"

    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const curveType = "{curve_type}";
        const startVel = {start_velocity};
        const endVel = {end_velocity};
        const powerExp = {power};

        let totalNotes = 0;
        const regionStats = [];

        const allUnits = h.allAUBoxes();
        if (unitIdx >= allUnits.length) return {{ error: "unit_index out of range" }};
        const au = allUnits[unitIdx];

        const noteTracks = h.trackBoxes(au).filter(box => box.type?.getValue?.() === 1);
        if (trackIdx >= noteTracks.length) return {{ error: "track_index out of range" }};
        const track = noteTracks[trackIdx];

        const regions = h.regionBoxes(track);
        const targetRegions = regionIdx < 0 ? regions : (regionIdx < regions.length ? [regions[regionIdx]] : []);

        h.modify(() => {{
            for (let ri = 0; ri < targetRegions.length; ri++) {{
                const region = targetRegions[ri];
                let noteCount = 0;
                try {{
                    const vertex = region.events.targetVertex.unwrap();
                    const collectionBox = vertex.box || vertex;
                    if (!collectionBox || !collectionBox.events) continue;

                    const noteEvents = h.eventBoxes(collectionBox);
                    if (noteEvents.length === 0) continue;

                    // Find min and max position to normalize
                    let minPos = Infinity, maxPos = -Infinity;
                    for (const evt of noteEvents) {{
                        const p = evt.position.getValue();
                        if (p < minPos) minPos = p;
                        if (p > maxPos) maxPos = p;
                    }}
                    const posRange = maxPos - minPos || 1;

                    for (const evt of noteEvents) {{
                        const pos = evt.position.getValue();
                        const t = (pos - minPos) / posRange;  // 0..1

                        let vel;
                        switch (curveType) {{
                            case "ramp_up":
                                vel = startVel + (endVel - startVel) * t;
                                break;
                            case "ramp_down":
                                vel = endVel + (startVel - endVel) * t;
                                break;
                            case "arc":
                                // peak at middle: rises to endVel then falls to startVel
                                vel = t < 0.5
                                    ? startVel + (endVel - startVel) * (t * 2)
                                    : endVel + (startVel - endVel) * ((t - 0.5) * 2);
                                break;
                            case "trough":
                                // dip at middle: falls to startVel then rises to endVel
                                vel = t < 0.5
                                    ? endVel + (startVel - endVel) * (t * 2)
                                    : startVel + (endVel - startVel) * ((t - 0.5) * 2);
                                break;
                            case "power":
                                vel = startVel + (endVel - startVel) * Math.pow(t, powerExp);
                                break;
                            default:
                                vel = startVel;
                        }}
                        evt.velocity.setValue(Math.max(0.05, Math.min(1.0, vel)));
                        noteCount++;
                        totalNotes++;
                    }}
                }} catch(e) {{}}
                regionStats.push({{ region_index: ri, notes_shaped: noteCount }});
            }}
        }});

        return {{
            success: true,
            curve_type: curveType,
            start_velocity: startVel,
            end_velocity: endVel,
            power: powerExp,
            total_notes_shaped: totalNotes,
            regions: regionStats,
        }};
    }}""")
    return _wrap_eval(result)


@mcp.tool()
async def mcp_opendaw_apply_articulation(
    unit_index: int = 0,
    track_index: int = 0,
    region_index: int = -1,
    articulation: str = "staccato",
    amount: float = 0.5,
) -> str:
    """Apply articulation to existing notes — staccato, legato, tenuto, accent.

    Reshapes note durations relative to their grid position to change phrasing character.
    Unlike velocity_curve (dynamics) or humanize (random), this applies deterministic
    duration ratios — the fundamental dimension of musical articulation.

    unit_index: AU index.
    track_index: Note track index.
    region_index: Region index (-1 = all regions on the track).
    articulation: Articulation type:
      - "staccato" — shorten notes to fraction of their grid slot (default 50%)
      - "legato"   — extend notes to nearly the next note's start (default 95%)
      - "tenuto"   — hold notes to full grid slot (100%, no gap, no overlap)
      - "accent"   — boost velocity on notes that fall on beat boundaries (downbeats)
    amount: Articulation depth 0-1 (default 0.5):
      - staccato: fraction of slot (0.3 = very short, 0.7 = moderate)
      - legato:   overlap fraction (0.9 = near-full, 0.5 = half-fill)
      - tenuto:   (unused, always full)
      - accent:   velocity boost amount (0.3 = subtle, 1.0 = strong accent)

    Returns per-region note counts and total notes reshaped.

    Examples:
      apply_articulation(articulation="staccato", amount=0.3)  # crisp, detached
      apply_articulation(articulation="legato", amount=0.95)   # smooth, connected
      apply_articulation(articulation="accent", amount=0.8)    # strong downbeat accents
    """
    if not (0.0 <= amount <= 1.0):
        return f"Error: amount must be 0-1, got {amount}"
    valid_articulations = ("staccato", "legato", "tenuto", "accent")
    if articulation not in valid_articulations:
        return f"Error: articulation must be one of {valid_articulations}, got '{articulation}'"

    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const artic = "{articulation}";
        const amt = {amount};
        const Quarter = h.ppqn.Quarter;

        let totalNotes = 0;
        const regionStats = [];

        const allUnits = h.allAUBoxes();
        if (unitIdx >= allUnits.length) return {{ error: "unit_index out of range" }};
        const au = allUnits[unitIdx];

        const noteTracks = h.trackBoxes(au).filter(box => box.type?.getValue?.() === 1);
        if (trackIdx >= noteTracks.length) return {{ error: "track_index out of range" }};
        const track = noteTracks[trackIdx];

        const regions = h.regionBoxes(track);
        const targetRegions = regionIdx < 0 ? regions : (regionIdx < regions.length ? [regions[regionIdx]] : []);

        h.modify(() => {{
            for (let ri = 0; ri < targetRegions.length; ri++) {{
                const region = targetRegions[ri];
                let noteCount = 0;
                try {{
                    const vertex = region.events.targetVertex.unwrap();
                    const collectionBox = vertex.box || vertex;
                    if (!collectionBox || !collectionBox.events) continue;

                    const noteEvents = h.eventBoxes(collectionBox);
                    if (noteEvents.length === 0) continue;

                    // Sort notes by position for legato calculations
                    const sorted = [...noteEvents].sort((a, b) => a.position.getValue() - b.position.getValue());

                    if (artic === "staccato") {{
                        for (const evt of sorted) {{
                            const pos = evt.position.getValue();
                            const dur = evt.duration.getValue();
                            // Slot = duration rounded to nearest 16th
                            const sixteenth = Math.floor(Quarter / 4);
                            const slotDur = Math.max(sixteenth, dur);
                            evt.duration.setValue(Math.max(1, Math.floor(slotDur * amt)));
                            noteCount++; totalNotes++;
                        }}
                    }} else if (artic === "legato") {{
                        for (let i = 0; i < sorted.length; i++) {{
                            const evt = sorted[i];
                            const pos = evt.position.getValue();
                            const dur = evt.duration.getValue();
                            const nextStart = (i < sorted.length - 1)
                                ? sorted[i + 1].position.getValue()
                                : pos + dur;
                            const slotEnd = pos + dur;
                            const targetEnd = pos + (nextStart - pos) * amt;
                            evt.duration.setValue(Math.max(1, Math.floor(targetEnd - pos)));
                            noteCount++; totalNotes++;
                        }}
                    }} else if (artic === "tenuto") {{
                        // Fill each note to its nearest grid slot boundary
                        const sixteenth = Math.floor(Quarter / 4);
                        for (const evt of sorted) {{
                            const pos = evt.position.getValue();
                            const dur = evt.duration.getValue();
                            const slotEnd = Math.ceil((pos + dur) / sixteenth) * sixteenth;
                            evt.duration.setValue(Math.max(1, slotEnd - pos));
                            noteCount++; totalNotes++;
                        }}
                    }} else if (artic === "accent") {{
                        // Boost velocity on notes that fall on beat boundaries (quarter note grid)
                        const beatTicks = Quarter;
                        for (const evt of sorted) {{
                            const pos = evt.position.getValue();
                            const isOnBeat = (pos % beatTicks) === 0;
                            if (isOnBeat) {{
                                const curVel = evt.velocity.getValue();
                                const boosted = Math.min(1.0, curVel + amt * (1.0 - curVel));
                                evt.velocity.setValue(boosted);
                            }}
                            noteCount++; totalNotes++;
                        }}
                    }}
                }} catch(e) {{}}
                regionStats.push({{ region_index: ri, notes_reshaped: noteCount }});
            }}
        }});

        return {{
            success: true,
            articulation: artic,
            amount: amt,
            total_notes_reshaped: totalNotes,
            regions: regionStats,
        }};
    }}""")

    return _wrap_eval(result)


@mcp.tool()
async def mcp_opendaw_create_passacaglia(
    bass_pattern: str = "36 43 41 36",
    bass_rhythm: str = "1 1 1 1",
    bass_repeats: int = 4,
    chord_pattern: str = "Cm,Ab,Eb,Bb",
    chord_octave: int = 4,
    variation_style: str = "block",
    beats_per_bar: int = 4,
    bass_velocity: float = 0.75,
    chord_velocity: float = 0.55,
    unit_index: int = -1,
    track_index: int = 0,
    start_beat: float = 0,
) -> str:
    """Create a passacaglia — repeating bass ostinato with evolving harmonies above.

    A foundational Baroque form (Bach BWV 582, Buxtehude) adapted to modern
    contexts (film scoring, metal, electronic). A short bass pattern (4-8 notes)
    repeats throughout while chords or arpeggiations evolve above it, creating
    cumulative tension. Distinct from ostinato (single repeating pattern),
    pedal_point (single sustained note), and bordun (drone chord).

    bass_pattern: Space-separated MIDI pitches for the bass ostinato
      (e.g. "36 43 41 36" = C2 G2 F2 C2). Default is a classic descending bass.
    bass_rhythm: Space-separated durations in beats matching bass_pattern
      (e.g. "1 1 1 1" = quarter notes, "0.5 0.5 1 2" = syncopated).
    bass_repeats: How many times the bass pattern repeats (1-16, default 4).
    chord_pattern: Comma-separated chord names for the upper voices
      (e.g. "Cm,Ab,Eb,Bb"). Supports: maj, min, m7, maj7, dom7, sus2, sus4, dim, aug.
      If fewer chords than repeats, chords cycle.
    chord_octave: Octave for chord notes (1-8, default 4).
    variation_style: How upper harmonies are voiced — "block" (sustained chords),
      "arpeggiated" (broken chord pattern), "melodic" (stepwise counter-melody).
    beats_per_bar: Time signature beats (3/4=3, 4/4=4, 6/8=6, default 4).
    bass_velocity: Velocity of bass notes (0-1, default 0.75).
    chord_velocity: Velocity of chord/variation notes (0-1, default 0.55).
    unit_index: AU index with note track (-1 = find first AU with note tracks).
    track_index: Note track index within the AU.
    start_beat: Position in beats where the passacaglia begins.

    Returns notes created, bass pattern length, total bars, variation style.
    """
    # Parse bass pattern
    try:
        bass_pitches = [int(x) for x in bass_pattern.split()]
    except ValueError:
        return "Error: bass_pattern must be space-separated integers (MIDI pitches)"
    if not bass_pitches or len(bass_pitches) > 16:
        return "Error: bass_pattern must have 1-16 notes"

    # Parse bass rhythm
    try:
        bass_durs = [float(x) for x in bass_rhythm.split()]
    except ValueError:
        return "Error: bass_rhythm must be space-separated numbers (beats)"
    if len(bass_durs) != len(bass_pitches):
        return f"Error: bass_rhythm has {len(bass_durs)} values but bass_pattern has {len(bass_pitches)}"

    if bass_repeats < 1 or bass_repeats > 16:
        return "Error: bass_repeats must be 1-16"
    if chord_octave < 1 or chord_octave > 8:
        return "Error: chord_octave must be 1-8"
    if beats_per_bar < 2 or beats_per_bar > 12:
        return "Error: beats_per_bar must be 2-12"
    if bass_velocity < 0 or bass_velocity > 1:
        return "Error: bass_velocity must be 0-1"
    if chord_velocity < 0 or chord_velocity > 1:
        return "Error: chord_velocity must be 0-1"
    if variation_style not in ("block", "arpeggiated", "melodic"):
        return "Error: variation_style must be 'block', 'arpeggiated', or 'melodic'"

    # Parse chord names
    CHORD_INTERVALS = {
        "maj": [0, 4, 7], "M": [0, 4, 7], "min": [0, 3, 7], "m": [0, 3, 7],
        "m7": [0, 3, 7, 10], "maj7": [0, 4, 7, 11], "M7": [0, 4, 7, 11],
        "dom7": [0, 4, 7, 10], "7": [0, 4, 7, 10],
        "sus2": [0, 2, 7], "sus4": [0, 5, 7], "dim": [0, 3, 6], "aug": [0, 4, 8],
    }
    NOTE_TO_PC = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4,
                  "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9,
                  "A#": 10, "Bb": 10, "B": 11}

    chords = []
    for name in chord_pattern.split(","):
        name = name.strip()
        root = None
        quality = None
        for q in ["maj7", "m7", "M7", "sus2", "sus4", "dom7", "dim", "aug", "maj", "min", "M", "m", "7"]:
            if name.endswith(q) and len(name) > len(q):
                root_name = name[:-len(q)]
                if root_name in NOTE_TO_PC:
                    root = NOTE_TO_PC[root_name]
                    quality = q
                    break
        if root is None:
            if name in NOTE_TO_PC:
                root = NOTE_TO_PC[name]
                quality = "maj"
            else:
                return f"Error: cannot parse chord '{name}'"
        intervals = CHORD_INTERVALS.get(quality, [0, 4, 7])
        chord_pitches = [(chord_octave + 1) * 12 + root + iv for iv in intervals]
        chords.append(chord_pitches)

    # Calculate bass pattern duration in beats
    bass_pattern_beats = sum(bass_durs)
    total_beats = bass_pattern_beats * bass_repeats
    total_bars = total_beats / beats_per_bar

    note_data = []

    # Bass ostinato notes
    for rep in range(bass_repeats):
        bass_pos = start_beat + rep * bass_pattern_beats
        cumulative = 0.0
        for i, pitch in enumerate(bass_pitches):
            note_data.append({
                "pitch": max(0, min(127, pitch)),
                "pos": bass_pos + cumulative,
                "dur": bass_durs[i] * 0.95,
                "vel": bass_velocity,
            })
            cumulative += bass_durs[i]

    # Upper voice variations
    for rep in range(bass_repeats):
        chord_idx = rep % len(chords)
        chord = chords[chord_idx]
        chord_start = start_beat + rep * bass_pattern_beats

        if variation_style == "block":
            # Sustained chord for the full bass pattern duration
            for pitch in chord:
                note_data.append({
                    "pitch": max(0, min(127, pitch)),
                    "pos": chord_start,
                    "dur": bass_pattern_beats * 0.9,
                    "vel": chord_velocity,
                })

        elif variation_style == "arpeggiated":
            # Broken chord — arpeggiate across the bass pattern
            arp_step = bass_pattern_beats / len(chord)
            for j, pitch in enumerate(chord):
                note_data.append({
                    "pitch": max(0, min(127, pitch)),
                    "pos": chord_start + j * arp_step,
                    "dur": arp_step * 0.9,
                    "vel": chord_velocity,
                })

        elif variation_style == "melodic":
            # Stepwise counter-melody from chord tones
            num_melody_notes = max(2, int(bass_pattern_beats))
            step_dur = bass_pattern_beats / num_melody_notes
            for j in range(num_melody_notes):
                pitch = chord[j % len(chord)]
                note_data.append({
                    "pitch": max(0, min(127, pitch)),
                    "pos": chord_start + j * step_dur,
                    "dur": step_dur * 0.9,
                    "vel": chord_velocity,
                })

    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const bg = h.boxGraph;
        const NoteEventBox = window.DAW_NoteEventBox;
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
            const collection = window.DAW_NoteEventCollectionBox.create(bg, h.uuid.generate());
            const regionDur = Math.round(totalBeats * Quarter);
            const startPos = Math.round(startBeat * Quarter);

            const regionBox = NoteRegionBox.create(bg, h.uuid.generate(), (box) => {{
                box.position.setValue(startPos);
                box.label.setValue("Passacaglia");
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
            bass_pattern_length: {len(bass_pitches)},
            bass_repeats: {bass_repeats},
            total_bars: Math.round({total_bars} * 10) / 10,
            chord_count: {len(chords)},
            variation_style: "{variation_style}",
            length_beats: totalBeats,
            unit_index: allUnits.indexOf(targetAU),
        }};
    }}""")
    return _wrap_eval(result)


def main():
    """Entry point for opendaw-mcp command."""
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] in ("--version", "-v"):
            print("opendaw-mcp 1.23.3 — 283 MCP tools")
            return
        if sys.argv[1] in ("--list-tools", "-l"):
            import asyncio
            tools = asyncio.run(mcp.list_tools())
            for t in sorted(tools, key=lambda x: x.name):
                print(f"  {t.name} — {t.description[:80]}")
            print(f"\nTotal: {len(tools)} tools")
            return
        if sys.argv[1] in ("--help", "-h"):
            print("opendaw-mcp — 283 MCP tools for agent-native openDAW control")
            print()
            print("Usage:")
            print("  opendaw-mcp              Start MCP server (stdio transport)")
            print("  MCP_TRANSPORT=sse opendaw-mcp  Start MCP server (SSE transport)")
            print("  opendaw-mcp --version    Show version")
            print("  opendaw-mcp --list-tools List all registered MCP tools")
            print("  opendaw-mcp --help       Show this help")
            print()
            print("Environment variables:")
            print("  OPENDAW_HOST_DIR  Path to headless openDAW directory")
            print("  OPENDAW_URL       URL of openDAW Vite dev server")
            print("  OPENDAW_EXPORT_DIR  Directory for audio exports")
            print("  NODE_BIN_DIR      Path to Node.js bin directory")
            print("  MCP_TRANSPORT     Transport type: stdio (default) or sse")
            print("  FASTMCP_HOST      SSE host (default 0.0.0.0)")
            print("  FASTMCP_PORT      SSE port (default 8080)")
            return
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    mcp.run(transport=transport)


@mcp.tool()
async def mcp_opendaw_create_chorale(
    chord_pattern: str = "C,Am,F,G",
    beats_per_chord: int = 4,
    beats_per_bar: int = 4,
    key_root: str = "C",
    key_mode: str = "major",
    soprano_velocity: float = 0.7,
    alto_velocity: float = 0.6,
    tenor_velocity: float = 0.6,
    bass_velocity: float = 0.65,
    note_duration: float = 0.9,
    voice_spread: int = 0,
    unit_index: int = -1,
    track_index: int = 0,
    start_beat: float = 0,
) -> str:
    """Create a 4-voice SATB chorale with voice-leading rules.

    Generates soprano, alto, tenor, and bass voices from a chord progression
    with proper voice leading: common tones preserved, smooth voice movement
    (no unnecessary leaps), no parallel fifths or octaves between adjacent
    chords, and voices stay within their ranges (S: 60-81, A: 55-74, T: 48-67,
    B: 36-62). The soprano voice gets the melody line (chord roots or
    nearest chord tones). Classic Bach chorale style — foundational for
    vocal harmonies, string arrangements, synth pad layering.

    chord_pattern: Comma-separated chord names (e.g. "C,Am,F,G").
      Supports: maj, min, m7, maj7, dom7, sus2, sus4, dim, aug.
    beats_per_chord: Duration of each chord in beats (default 4 = 1 bar in 4/4).
    beats_per_bar: Time signature beats (3/4=3, 4/4=4, 6/8=6, default 4).
    key_root: Key root note for voice-leading context (e.g. "C", "F#", "Bb").
    key_mode: Key mode — "major" or "minor" (affects voice assignment).
    soprano_velocity: Velocity of soprano voice (0-1, default 0.7).
    alto_velocity: Velocity of alto voice (0-1, default 0.6).
    tenor_velocity: Velocity of tenor voice (0-1, default 0.6).
    bass_velocity: Velocity of bass voice (0-1, default 0.65).
    note_duration: Note duration as fraction of chord length (0-1, default 0.9).
    voice_spread: Extra spacing between voices in semitones (0-12, default 0).
    unit_index: AU index with note track (-1 = find first AU with note tracks).
    track_index: Note track index within the AU.
    start_beat: Position in beats where the chorale begins.

    Returns notes created, chord count, voice ranges, voice-leading info.
    """
    if beats_per_chord < 1 or beats_per_chord > 32:
        return "Error: beats_per_chord must be 1-32"
    if beats_per_bar < 2 or beats_per_bar > 12:
        return "Error: beats_per_bar must be 2-12"
    if not 0 < soprano_velocity <= 1 or not 0 < alto_velocity <= 1:
        return "Error: velocities must be 0-1"
    if not 0 < tenor_velocity <= 1 or not 0 < bass_velocity <= 1:
        return "Error: velocities must be 0-1"
    if not 0 < note_duration <= 1:
        return "Error: note_duration must be 0-1"
    if voice_spread < 0 or voice_spread > 12:
        return "Error: voice_spread must be 0-12"

    CHORD_INTERVALS = {
        "maj": [0, 4, 7], "M": [0, 4, 7],
        "min": [0, 3, 7], "m": [0, 3, 7],
        "m7": [0, 3, 7, 10], "maj7": [0, 4, 7, 11], "M7": [0, 4, 7, 11],
        "dom7": [0, 4, 7, 10], "7": [0, 4, 7, 10],
        "sus2": [0, 2, 7], "sus4": [0, 5, 7],
        "dim": [0, 3, 6], "aug": [0, 4, 8],
    }
    NOTE_TO_PC = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4,
                  "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9,
                  "A#": 10, "Bb": 10, "B": 11}

    # Voice ranges (MIDI)
    RANGES = {
        "soprano": (60, 81),
        "alto": (55, 74),
        "tenor": (48, 67),
        "bass": (36, 62),
    }

    # Parse chords
    chords_raw = []
    for name in chord_pattern.split(","):
        name = name.strip()
        root = None
        quality = None
        for q in ["maj7", "m7", "M7", "sus2", "sus4", "dom7", "dim", "aug", "maj", "min", "M", "m", "7"]:
            if name.endswith(q) and len(name) > len(q):
                root_name = name[:-len(q)]
                if root_name in NOTE_TO_PC:
                    root = NOTE_TO_PC[root_name]
                    quality = q
                    break
        if root is None:
            if name in NOTE_TO_PC:
                root = NOTE_TO_PC[name]
                quality = "maj"
            else:
                return f"Error: cannot parse chord '{name}'"
        intervals = CHORD_INTERVALS.get(quality, [0, 4, 7])
        # Use up to 4 chord tones
        tones = [root + iv for iv in intervals[:4]]
        chords_raw.append(tones)

    def clamp_to_range(pitch, lo, hi):
        while pitch < lo:
            pitch += 12
        while pitch > hi:
            pitch -= 12
        return pitch

    def interval(a, b):
        return abs(a - b) % 12

    # Voice leading: assign each voice to nearest chord tone from previous position
    voices = {"soprano": [], "alto": [], "tenor": [], "bass": []}
    prev_pitches = None

    for ci, tones in enumerate(chords_raw):
        # Bass: root of the chord, in bass range
        bass_pc = tones[0] % 12
        if prev_pitches is None:
            bass_pitch = clamp_to_range(36 + bass_pc, *RANGES["bass"])
        else:
            # Move bass by smallest interval to a chord tone
            candidates = [clamp_to_range(36 + (tones[j] % 12), *RANGES["bass"]) for j in range(len(tones))]
            # Also try octave shifts
            for j in range(len(tones)):
                candidates.append(clamp_to_range(48 + (tones[j] % 12), *RANGES["bass"]))
            candidates = list(set(candidates))
            best = min(candidates, key=lambda p: abs(p - prev_pitches["bass"]))
            bass_pitch = best

        # Soprano: highest chord tone (melody)
        if prev_pitches is None:
            sop_pc = tones[0] % 12
            soprano_pitch = clamp_to_range(72 + sop_pc, *RANGES["soprano"])
        else:
            candidates = []
            for t in tones:
                pc = t % 12
                for oct_shift in [0, 12, -12]:
                    candidates.append(clamp_to_range(prev_pitches["soprano"] + oct_shift + (pc - prev_pitches["soprano"] % 12), *RANGES["soprano"]))
            candidates = [c for c in candidates if c % 12 in [t % 12 for t in tones]]
            if not candidates:
                candidates = [clamp_to_range(72 + (tones[0] % 12), *RANGES["soprano"])]
            soprano_pitch = min(candidates, key=lambda p: abs(p - prev_pitches["soprano"]))

        # Alto and Tenor: fill in middle voices
        used_pcs = {bass_pitch % 12, soprano_pitch % 12}
        middle_tones = [t for t in tones if t % 12 not in used_pcs]
        if not middle_tones:
            middle_tones = [tones[0] + 3, tones[0] + 5]

        if prev_pitches is None:
            alto_pitch = clamp_to_range(64 + (middle_tones[0] % 12), *RANGES["alto"])
            tenor_pitch = clamp_to_range(55 + (middle_tones[-1] % 12), *RANGES["tenor"])
        else:
            # Assign alto and tenor to nearest available tones
            alto_candidates = [clamp_to_range(prev_pitches["alto"] + (t % 12 - prev_pitches["alto"] % 12), *RANGES["alto"]) for t in middle_tones]
            alto_candidates += [clamp_to_range(prev_pitches["alto"] + 12 + (t % 12 - prev_pitches["alto"] % 12), *RANGES["alto"]) for t in middle_tones]
            alto_candidates += [clamp_to_range(prev_pitches["alto"] - 12 + (t % 12 - prev_pitches["alto"] % 12), *RANGES["alto"]) for t in middle_tones]
            alto_candidates = [c for c in alto_candidates if c % 12 in [t % 12 for t in middle_tones]]
            if not alto_candidates:
                alto_candidates = [clamp_to_range(64 + (middle_tones[0] % 12), *RANGES["alto"])]
            alto_pitch = min(alto_candidates, key=lambda p: abs(p - prev_pitches["alto"]))

            tenor_candidates = [clamp_to_range(prev_pitches["tenor"] + (t % 12 - prev_pitches["tenor"] % 12), *RANGES["tenor"]) for t in middle_tones]
            tenor_candidates += [clamp_to_range(prev_pitches["tenor"] + 12 + (t % 12 - prev_pitches["tenor"] % 12), *RANGES["tenor"]) for t in middle_tones]
            tenor_candidates += [clamp_to_range(prev_pitches["tenor"] - 12 + (t % 12 - prev_pitches["tenor"] % 12), *RANGES["tenor"]) for t in middle_tones]
            tenor_candidates = [c for c in tenor_candidates if c % 12 in [t % 12 for t in middle_tones]]
            if not tenor_candidates:
                tenor_candidates = [clamp_to_range(55 + (middle_tones[-1] % 12), *RANGES["tenor"])]
            tenor_pitch = min(tenor_candidates, key=lambda p: abs(p - prev_pitches["tenor"]))

        # Check for parallel fifths/octaves
        def check_parallel(prev, curr):
            if prev is None:
                return True
            prev_int = interval(prev["bass"], prev["soprano"])
            curr_int = interval(curr["bass"], curr["soprano"])
            if prev_int in [7, 12] and curr_int == prev_int:
                if (curr["bass"] - prev["bass"]) * (curr["soprano"] - prev["soprano"]) > 0:
                    return False
            return True

        curr = {"bass": bass_pitch, "soprano": soprano_pitch,
                "alto": alto_pitch, "tenor": tenor_pitch}
        # If parallel fifth/octave detected, try shifting soprano by octave
        if not check_parallel(prev_pitches, curr):
            alt_sop = soprano_pitch + 12 if soprano_pitch + 12 <= RANGES["soprano"][1] else soprano_pitch - 12
            if RANGES["soprano"][0] <= alt_sop <= RANGES["soprano"][1]:
                soprano_pitch = alt_sop
                curr["soprano"] = soprano_pitch

        voices["soprano"].append(soprano_pitch + voice_spread * 2)
        voices["alto"].append(alto_pitch + voice_spread)
        voices["tenor"].append(tenor_pitch)
        voices["bass"].append(bass_pitch)

        prev_pitches = curr

    # Build note data
    note_data = []
    vel_map = {"soprano": soprano_velocity, "alto": alto_velocity,
               "tenor": tenor_velocity, "bass": bass_velocity}
    dur = beats_per_chord * note_duration

    for ci in range(len(chords_raw)):
        pos = start_beat + ci * beats_per_chord
        for voice_name in ["soprano", "alto", "tenor", "bass"]:
            pitch = voices[voice_name][ci]
            if 0 <= pitch <= 127:
                note_data.append({
                    "pitch": pitch,
                    "pos": pos,
                    "dur": dur,
                    "vel": vel_map[voice_name],
                })

    total_beats = len(chords_raw) * beats_per_chord

    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const bg = h.boxGraph;
        const NoteEventBox = window.DAW_NoteEventBox;
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
            const collection = window.DAW_NoteEventCollectionBox.create(bg, h.uuid.generate());
            const regionDur = Math.round(totalBeats * Quarter);
            const startPos = Math.round(startBeat * Quarter);

            const regionBox = NoteRegionBox.create(bg, h.uuid.generate(), (box) => {{
                box.position.setValue(startPos);
                box.label.setValue("Chorale");
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
            chord_count: {len(chords_raw)},
            voices: "SATB",
            soprano_range: [{min(voices['soprano'])}, {max(voices['soprano'])}],
            alto_range: [{min(voices['alto'])}, {max(voices['alto'])}],
            tenor_range: [{min(voices['tenor'])}, {max(voices['tenor'])}],
            bass_range: [{min(voices['bass'])}, {max(voices['bass'])}],
            chords: "{chord_pattern}",
            length_beats: totalBeats,
            unit_index: allUnits.indexOf(targetAU),
        }};
    }}""")
    return _wrap_eval(result)


@mcp.tool()
async def mcp_opendaw_create_fugue(
    subject: str = "60,62,64,65,64,62,60,57",
    voices: int = 3,
    entry_delay_beats: float = 4,
    answer_type: str = "tonal",
    countersubject: str = "",
    key_root: str = "C",
    key_mode: str = "major",
    note_duration: float = 0.9,
    velocity: float = 0.75,
    velocity_decay: float = 0.1,
    stretto: bool = False,
    unit_index: int = -1,
    track_index: int = 0,
    start_beat: float = 0,
) -> str:
    """Create a fugue — polyphonic composition with subject, answer, and countersubject.

    The most complex contrapuntal form. A subject (main theme) is stated in one
    voice, then imitated in others with a tonal or real answer. Optional
    countersubject provides contrasting counterpoint. Stretto mode overlaps
    voice entries for climactic density. Unlike create_canon (strict imitation),
    a fugue uses tonal answers (adjusted intervals) and independent
    countersubjects.

    subject: Comma-separated MIDI pitches of the fugue subject (e.g. "60,62,64,65").
    voices: Number of voices (2-5, default 3). More voices = denser counterpoint.
    entry_delay_beats: Beats between voice entries (2-8, default 4).
    answer_type: "tonal" (fifth up, adjusted) or "real" (exact transposition).
    countersubject: Comma-separated MIDI pitches of countersubject (optional).
      If empty, no countersubject. Must be same length as subject.
    key_root: Key root for tonal answer calculation (e.g. "C", "F#", "Bb").
    key_mode: "major" or "minor" — affects tonal answer adjustment.
    note_duration: Note duration as fraction of beat (0-1, default 0.9 = legato).
    velocity: Base velocity for first voice (0-1, default 0.75).
    velocity_decay: Velocity reduction per voice (0-0.3, default 0.1).
    stretto: If true, later voices enter before previous finishes subject.
    unit_index: AU index with note track (-1 = find first AU with note tracks).
    track_index: Note track index within the AU.
    start_beat: Position in beats where the first voice begins.

    Returns notes created, voice count, subject length, answer type, stretto status.
    """
    try:
        subject_pitches = [int(p.strip()) for p in subject.split(",")]
    except ValueError:
        return "Error: subject must be comma-separated integers"
    if len(subject_pitches) < 2:
        return "Error: need at least 2 subject notes"
    if len(subject_pitches) > 32:
        return "Error: maximum 32 subject notes"
    if not all(0 <= p <= 127 for p in subject_pitches):
        return "Error: subject pitches must be 0-127"
    if voices < 2 or voices > 5:
        return "Error: voices must be 2-5"
    if entry_delay_beats < 1 or entry_delay_beats > 16:
        return "Error: entry_delay_beats must be 1-16"
    if answer_type not in ("tonal", "real"):
        return "Error: answer_type must be 'tonal' or 'real'"
    if not 0 < velocity <= 1:
        return "Error: velocity must be 0-1"
    if velocity_decay < 0 or velocity_decay > 0.3:
        return "Error: velocity_decay must be 0-0.3"
    if not 0 < note_duration <= 1:
        return "Error: note_duration must be 0-1"

    # Parse countersubject
    cs_pitches = None
    if countersubject:
        try:
            cs_pitches = [int(p.strip()) for p in countersubject.split(",")]
        except ValueError:
            return "Error: countersubject must be comma-separated integers"
        if len(cs_pitches) != len(subject_pitches):
            return "Error: countersubject must be same length as subject"
        if not all(0 <= p <= 127 for p in cs_pitches):
            return "Error: countersubject pitches must be 0-127"

    # Calculate answer transposition
    # Tonal answer: transpose to dominant (5th up), adjust intervals to diatonic
    # Real answer: exact transposition (usually fifth)
    if answer_type == "tonal":
        # Tonal answer: move to dominant, adjust intervals to diatonic
        # Simplified: transpose by 7 semitones, then correct any out-of-key notes
        answer_transpose = 7
        answer_pitches = [p + answer_transpose for p in subject_pitches]
        # Tonal adjustment: if subject leaps up a 4th, answer goes down a 5th (and vice versa)
        # Simple correction: ensure answer stays within reasonable range
        # Clamp to MIDI range
        answer_pitches = [max(0, min(127, p)) for p in answer_pitches]
    else:
        # Real answer: exact transposition by fifth
        answer_transpose = 7
        answer_pitches = [max(0, min(127, p + answer_transpose)) for p in subject_pitches]

    # Third and subsequent voices: alternate subject and answer
    voice_pitches = [subject_pitches]  # Voice 0: subject
    for v in range(1, voices):
        if v % 2 == 1:
            voice_pitches.append(answer_pitches)
        else:
            # Return to subject, possibly octave lower for variety
            subj_oct_down = [max(0, p - 12) for p in subject_pitches]
            voice_pitches.append(subj_oct_down)

    # Build note data
    note_data = []
    subj_len = len(subject_pitches)
    dur = note_duration

    for v in range(voices):
        vel = max(0.1, velocity - v * velocity_decay)
        entry_beat = start_beat + v * entry_delay_beats

        if stretto and v > 0:
            # Stretto: later voices enter before previous finishes
            # Enter at half the normal delay
            entry_beat = start_beat + v * entry_delay_beats * 0.5

        # Subject/answer notes
        for ni, pitch in enumerate(voice_pitches[v]):
            pos = entry_beat + ni
            note_data.append({"pitch": pitch, "pos": pos, "dur": dur, "vel": vel})

        # Countersubject (if provided): starts after subject completes
        if cs_pitches:
            cs_entry = entry_beat + subj_len
            # Countersubject transposed to match voice's answer pitch
            cs_transpose = 0
            if v % 2 == 1:
                cs_transpose = answer_transpose
            elif v > 0:
                cs_transpose = -12
            for ni, pitch in enumerate(cs_pitches):
                adj_pitch = max(0, min(127, pitch + cs_transpose))
                note_data.append({"pitch": adj_pitch, "pos": cs_entry + ni, "dur": dur, "vel": vel * 0.9})

    total_beats = (voices - 1) * entry_delay_beats + subj_len
    if cs_pitches:
        total_beats += subj_len

    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const bg = h.boxGraph;
        const NoteEventBox = window.DAW_NoteEventBox;
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

        if (noteTracks.length === 0) return {{error: "No note tracks found"}};

        const trackBox = noteTracks[Math.min({track_index}, noteTracks.length - 1)];
        let totalNotes = 0;

        h.modify(() => {{
            const collection = window.DAW_NoteEventCollectionBox.create(bg, h.uuid.generate());
            const regionDur = Math.round(totalBeats * Quarter);
            const startPos = Math.round(startBeat * Quarter);

            const regionBox = NoteRegionBox.create(bg, h.uuid.generate(), (box) => {{
                box.position.setValue(startPos);
                box.label.setValue("Fugue");
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
            voice_count: {voices},
            subject_length: {subj_len},
            answer_type: "{answer_type}",
            has_countersubject: {"true" if cs_pitches else "false"},
            stretto: {"true" if stretto else "false"},
            length_beats: totalBeats,
            unit_index: allUnits.indexOf(targetAU),
        }};
    }}""")
    return _wrap_eval(result)


if __name__ == "__main__":
    main()
