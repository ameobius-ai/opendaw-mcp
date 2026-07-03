"""
openDAW MCP Server — Production
================================
Playwright bridge to a headless openDAW instance.
Every tool performs real operations via page.evaluate() into the V8 context
where the DAW project lives. No stubs, no placeholders.

Architecture:
  MCP Server (Python/FastMCP) → Playwright → headless Chromium → Vite :5174 → @opendaw/studio-sdk
"""

import asyncio
import json
import logging
import subprocess
import os
import atexit
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("opendaw-mcp")
DAW_HOST_DIR = os.environ.get("OPENDAW_HOST_DIR", os.path.join(os.path.dirname(__file__), "..", "headless-daw"))
DAW_URL = os.environ.get("OPENDAW_URL", "http://localhost:5174")
EXPORT_DIR = os.environ.get("OPENDAW_EXPORT_DIR", os.path.join(os.path.dirname(__file__), "..", "exports"))
os.makedirs(EXPORT_DIR, exist_ok=True)

class HeadlessDawBridge:
    """Playwright bridge to headless openDAW."""
    def __init__(self):
        self.page = None; self.playwright = None; self.browser = None
    async def start(self):
        env = dict(os.environ)
        node_dir = os.environ.get("NODE_BIN_DIR", "")
        if node_dir:
            env["PATH"] = node_dir + ":" + env.get("PATH", "")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True, args=["--use-fake-ui-for-media-stream","--autoplay-policy=no-user-gesture-required"])
        self.page = await self.browser.new_page()
        await self.page.goto(DAW_URL, timeout=15000)
        await self.page.wait_for_function("typeof window.DAW !== 'undefined'", timeout=30000)
        await self.page.wait_for_function("typeof window.DAW_InstrumentFactories !== 'undefined'", timeout=30000)
        # Inject helper functions into DAW context — eliminates boilerplate in every tool
        await self.page.evaluate("""() => {
            if (window.DAW_HELPERS) return;  // already injected
            const p = window.DAW;
            window.DAW_HELPERS = {
                // Get AU adapter by index (sorted by index field)
                au: (i) => {
                    const aus = p.rootBoxAdapter.audioUnits.adapters();
                    if (i >= aus.length) throw new Error('No AU at ' + i);
                    return aus[i];
                },
                // Get track adapter by AU index + track index
                track: (auIdx, trackIdx) => {
                    const au = window.DAW_HELPERS.au(auIdx);
                    const tracks = au.tracks.collection.adapters();
                    if (trackIdx >= tracks.length) throw new Error('No track ' + trackIdx + ' on AU ' + auIdx);
                    return tracks[trackIdx];
                },
                // Get region adapter by AU/track/region index
                region: (auIdx, trackIdx, regIdx) => {
                    const track = window.DAW_HELPERS.track(auIdx, trackIdx);
                    const regions = track.regions.collection.asArray();
                    if (regIdx >= regions.length) throw new Error('No region ' + regIdx);
                    return regions[regIdx];
                },
                // Get all AU adapters sorted
                allAUs: () => p.rootBoxAdapter.audioUnits.adapters(),
                // Find instrument AU (first non-output, non-bus)
                instrumentAU: () => {
                    const aus = p.rootBoxAdapter.audioUnits.adapters();
                    const inst = aus.find(a => a.isInstrument);
                    if (!inst) throw new Error('No instrument AU found');
                    return inst;
                },
                // Safe evaluate — wraps in editing.modify
                modify: (fn) => p.editing.modify(fn),
                // Project shortcuts
                project: p,
                api: p.api,
                boxGraph: p.boxGraph,
                editing: p.editing,
                tempoMap: p.tempoMap,
                audioUnitFreeze: p.audioUnitFreeze,
                rootBoxAdapter: p.rootBoxAdapter,
                rootBox: p.rootBox,
                timelineBox: p.timelineBox,
                engine: p.engine,
                primaryAudioUnitBox: p.primaryAudioUnitBox,
                primaryAudioBusBox: p.primaryAudioBusBox,
                uuid: window.DAW_UUID,
                ppqn: window.DAW_PPQN,
            };
        }""")
        logging.info("DAW engine ready!")
    async def evaluate(self, script, timeout=30000):
        """Execute JS in the DAW context. All errors caught and returned."""
        if self.page is None:
            await self.start()
        wrapped = f"""async () => {{ try {{ return await ({script})(); }} catch (e) {{ return {{ __error: e.message, __stack: e.stack }}; }} }}"""
        self.page.set_default_timeout(timeout)
        result = await self.page.evaluate(wrapped)
        if isinstance(result, dict) and "__error" in result:
            return {"error": result["__error"], "stack": result.get("__stack","")}
        return result
    async def stop(self):
        if self.browser: await self.browser.close()
        if self.playwright: await self.playwright.stop()
        self.playwright = None; self.page = None; self.browser = None

bridge = HeadlessDawBridge()
def cleanup():
    try: asyncio.run(bridge.stop())
    except: pass
atexit.register(cleanup)

def _ok(data=None) -> str:
    return json.dumps({"success": True, **(data or {})})
def _err(msg: str) -> str:
    return json.dumps({"error": msg})
def _wrap_eval(result) -> str:
    if isinstance(result, dict) and "error" in result: return json.dumps(result)
    return json.dumps(result)

@mcp.tool()
async def mcp_opendaw_get_project_state() -> str:
    """Get full project state: BPM, sample rate, playing status, track list, effects chain."""
    result = await bridge.evaluate(f"""() => {{
        const p = window.DAW;
        const eng = p.engine;

        const units = [];
        try {{
            const allAU = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
            allAU.forEach((au, i) => {{
                const effects = [];
                try {{
                    [...au.audioEffects.pointerHub.incoming()].forEach(({{box}}) => {{
                        effects.push(box.constructor?.name || 'Unknown');
                    }});
                }} catch(e) {{}}

                const trackBoxes = [...au.tracks.pointerHub.incoming()].map(({{box}}) => ({{
                    name: box.name?.getValue?.() || box.constructor?.name || 'Track',
                    type: box.type?.getValue?.() ?? 'unknown',
                }}));

                units.push({{
                    name: au.name?.getValue?.() || 'Unit ' + i,
                    tracks: trackBoxes,
                    effects: effects,
                    volume: au.volume?.getValue?.() ?? 0,
                    panning: au.panning?.getValue?.() ?? 0,
                    mute: au.mute?.getValue?.() ?? false,
                    solo: au.solo?.getValue?.() ?? false,
                }});
            }});
        }} catch(e) {{}}

        return {{
            bpm: p.timelineBox?.bpm?.getValue?.() ?? eng.bpm,
            sampleRate: eng.sampleRate,
            isPlaying: !!eng.isPlaying?.getValue?.(),
            position: eng.position?.getValue?.() ?? eng.position,
            audioUnits: units,
            totalBoxes: [...p.boxGraph.boxes()].length,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_transport(action: str) -> str:
    """Control transport: play, stop, or toggle.

action: "play", "stop", or "toggle"
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const eng = h.engine;
        if (eng.isPlaying?.getValue?.()) {{
            eng.stop();
            return {{status: 'stopped'}};
        }} else {{
            eng.play();
            return {{status: 'playing'}};
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

        const markers = [...markerTrack.markers.pointerHub.incoming()].map(({{box}}) => box);
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
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const markerTrack = h.timelineBox?.markerTrack;
        if (!markerTrack) return {{error: "No markerTrack"}};
        const markers = [...markerTrack.markers.pointerHub.incoming()].map(({{box}}) => box);
        return markers.map((m, i) => ({{
            index: i,
            position_beats: m.position.getValue() / h.ppqn.Quarter,
            label: m.label?.getValue?.() ?? "",
            plays: m.plays?.getValue?.() ?? 0,
        }}));
    }}""")
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
        const markers = [...markerTrack.markers.pointerHub.incoming()].map(({{box}}) => box);
        if ({marker_index} >= markers.length) return {{error: "No marker at index {marker_index}"}};
        const target = markers[{marker_index}];
        const label = target.label?.getValue?.() ?? "";
        const pos = target.position?.getValue?.() ?? 0;
        h.modify(() => {{ target.delete(); }});
        const remaining = [...markerTrack.markers.pointerHub.incoming()].length;
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
        const markers = [...markerTrack.markers.pointerHub.incoming()].map(({{box}}) => box);
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
        const markers = [...markerTrack.markers.pointerHub.incoming()].map(({{box}}) => box);
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
            const existing = [...sigTrack.events.pointerHub.incoming()].map(({{box}}) => box);
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
        const allEvents = [...sigTrack.events.pointerHub.incoming()].map(({{box}}) => box);
        const eventList = allEvents.map(e => ({{
            position_beats: e.relativePosition?.getValue?.() / h.ppqn.Quarter ?? 0,
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

            const existingEvents = [...collection.events.pointerHub.incoming()].map(({{box}}) => box);
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
        const events = [...coll.events.pointerHub.incoming()].map(({{box}}) => box);
        const eventList = events.map(e => ({{
            position_beats: e.position?.getValue?.() / h.ppqn.Quarter ?? 0,
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
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const tl = h.timelineBox;
        if (!tl || !tl.tempoTrack) return {{error: "No tempoTrack on timeline"}};

        const tempoTrack = tl.tempoTrack;
        const enabled = tempoTrack.enabled?.getValue?.() ?? false;
        const minBpm = tempoTrack.minBpm?.getValue?.() ?? 60;
        const maxBpm = tempoTrack.maxBpm?.getValue?.() ?? 240;

        const eventsVertex = tempoTrack.events.targetVertex;
        if (eventsVertex.isEmpty()) return {{
            success: true,
            enabled,
            min_bpm: minBpm,
            max_bpm: maxBpm,
            event_count: 0,
            events: [],
        }};

        const collection = eventsVertex.unwrap().box;
        const events = [...collection.events.pointerHub.incoming()].map(({{box}}) => box);
        const eventList = events.map(e => ({{
            position_beats: e.position?.getValue?.() / h.ppqn.Quarter ?? 0,
            bpm: Math.round(minBpm + (e.value?.getValue?.() ?? 0) * (maxBpm - minBpm)),
            interpolation: e.interpolation?.getValue?.() === 1 ? "linear" : "hold",
        }})).sort((a, b) => a.position_beats - b.position_beats);

        return {{
            success: true,
            enabled,
            min_bpm: minBpm,
            max_bpm: maxBpm,
            event_count: events.length,
            events: eventList,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_list_signature_changes() -> str:
    """List all time signature changes on the timeline's signature track.

Returns each signature event with position (beats), numerator, and denominator.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const tl = h.timelineBox;
        if (!tl || !tl.signatureTrack) return {{error: "No signatureTrack on timeline"}};

        const sigTrack = tl.signatureTrack;
        const enabled = sigTrack.enabled?.getValue?.() ?? false;

        const events = [...sigTrack.events.pointerHub.incoming()].map(({{box}}) => box);
        const eventList = events.map(e => ({{
            position_beats: e.relativePosition?.getValue?.() / h.ppqn.Quarter ?? 0,
            numerator: e.nominator?.getValue?.() ?? 4,
            denominator: e.denominator?.getValue?.() ?? 4,
        }})).sort((a, b) => a.position_beats - b.position_beats);

        return {{
            success: true,
            enabled,
            event_count: events.length,
            events: eventList,
        }};
    }}""")
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
        const events = [...sigTrack.events.pointerHub.incoming()].map(({{box}}) => box);
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

        const remaining = [...sigTrack.events.pointerHub.incoming()].map(({{box}}) => box);
        const eventList = remaining.map(e => ({{
            position_beats: e.relativePosition?.getValue?.() / h.ppqn.Quarter ?? 0,
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
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        let trackBox;
        h.modify(() => {{
            trackBox = h.api.createAudioTrack(h.primaryAudioUnitBox);
        }});
        return {{success: !!trackBox, type: 'audio'}};
    }}""")
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
            const units = [...h.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
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

        const units = [...h.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
        const au = units[unitIdx];

        // Get InstrumentBox via au.input.pointerHub.incoming()
        const incoming = [...au.input.pointerHub.incoming()].map(({{box}}) => box);
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

        const units = [...h.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
        const au = units[unitIdx];

        // Get current InstrumentBox
        const incoming = [...au.input.pointerHub.incoming()].map(({{box}}) => box);
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
        const units = [...h.rootBox.audioUnits.pointerHub.incoming()]
            .map(({{box}}) => box)
            .sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
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
        const units = [...h.rootBox.audioUnits.pointerHub.incoming()]
            .map(({{box}}) => box)
            .sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
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
        const units = [...h.rootBox.audioUnits.pointerHub.incoming()]
            .map(({{box}}) => box)
            .sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
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
        const units = [...h.rootBox.audioUnits.pointerHub.incoming()]
            .map(({{box}}) => box)
            .sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
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
        const p = window.DAW;
        const UUID = window.DAW_UUID;
        const AudioUnitBox = window.DAW_AudioUnitBox;
        const TapeDeviceBox = window.DAW_TapeDeviceBox;
        const CaptureAudioBox = window.DAW_CaptureAudioBox;
        const AudioUnitType = window.DAW_AudioUnitType;

        const rootBox = p.rootBox;
        const primaryAudioBusBox = p.primaryAudioBusBox;

        let instrumentAU, tapeDevice, captureBox, trackBox;
        p.editing.modify(() => {{
            // Create CaptureAudioBox
            captureBox = CaptureAudioBox.create(p.boxGraph, UUID.generate());

            // Create instrument AudioUnitBox connected to output bus
            instrumentAU = AudioUnitBox.create(p.boxGraph, UUID.generate(), (box) => {{
                box.type.setValue(AudioUnitType.Instrument);
                box.collection.refer(rootBox.audioUnits);
                box.output.refer(primaryAudioBusBox.input);
                box.capture.refer(captureBox);
                box.index.setValue(0);
                box.volume.setValue(0.767835); // 0 dB (VolumeMapper.decibel(-96,-9,+6) powerByCenter)
            }});

            // Create TapeDeviceBox (audio player instrument)
            tapeDevice = TapeDeviceBox.create(p.boxGraph, UUID.generate(), (box) => {{
                box.label.setValue("{safe_name}");
                box.host.refer(instrumentAU.input);
            }});

            // Create audio track on the instrument AU
            trackBox = p.api.createAudioTrack(instrumentAU);
        }});

        // Find unit_index and track_index
        const allUnits = [...rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box);
        const unitIndex = allUnits.findIndex(au => String(au.address) === String(instrumentAU.address));
        const audioTracks = [...instrumentAU.tracks.pointerHub.incoming()]
            .map(({{box}}) => box)
            .filter(box => box.type?.getValue?.() === 2);
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
        const allUnits = [...rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box);
        const unitIndex = allUnits.findIndex(au => String(au.address) === String(instrumentAU.address));
        const noteTracks = [...instrumentAU.tracks.pointerHub.incoming()]
            .map(({{box}}) => box)
            .filter(box => box.type?.getValue?.() === 1);
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
        const p = window.DAW;
        const UUID = window.DAW_UUID;
        const PPQN = window.DAW_PPQN;
        const Quarter = PPQN.Quarter;
        const AudioFileBox = window.DAW_AudioFileBox;
        const AudioRegionBox = window.DAW_AudioRegionBox;
        const sampleId = "{safe_sample_id}";
        const startBeat = {start_beat};
        const unitIdx = {unit_index};
        const trackIdx = {track_index};

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
        const au = units[unitIdx];

        const audioTracks = [...au.tracks.pointerHub.incoming()]
            .map(({{box}}) => box)
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
        p.editing.modify(() => {{
            audioFileBox = AudioFileBox.create(p.boxGraph, UUID.generate(), (box) => {{
                box.fileName.setValue("{sample_id}");
                box.startInSeconds.setValue(0.0);
                box.endInSeconds.setValue(audioBuffer.duration);
            }});

            regionBox = p.api.createNotStretchedRegion({{
                boxGraph: p.boxGraph,
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
    result = await bridge.evaluate(f"""() => {{
        return new Promise(async (resolve) => {{
            try {{
                if (window.DAW_engineStarted && window.DAW_engineStarted()) {{
                    resolve({{success: true, message: "Engine already started"}});
                    return;
                }}
                await window.DAW_startEngine();
                resolve({{success: true, message: "Engine started"}});
            }} catch(e) {{
                resolve({{error: e.message, stack: e.stack?.slice(0, 300)}});
            }}
        }});
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_list_effects() -> str:
    """List all available audio and MIDI effect types."""
    result = await bridge.evaluate(f"""() => {{
        const ef = window.DAW_EffectFactories;
        return {{
            audio: ef.AudioNamed ? Object.keys(ef.AudioNamed) : [],
            midi: ef.MidiNamed ? Object.keys(ef.MidiNamed) : [],
        }};
    }}""")
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
        const p = window.DAW;
        const api = p.api;
        const ef = window.DAW_EffectFactories;
        const effectType = "{safe_effect}";
        const unitIndex = {unit_index};

        const factory = ef.AudioNamed[effectType];
        if (!factory) return {{error: "Effect factory not found: " + effectType}};

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()]
            .map(({{box}}) => box);
        if (unitIndex >= units.length) return {{error: "No audio unit at index " + unitIndex + ". Total: " + units.length}};
        const au = units[unitIndex];

        let effectBox;
        p.editing.modify(() => {{
            effectBox = api.insertEffect(au.audioEffects, factory);
        }});

        // Get effect index in the chain
        const effects = [...au.audioEffects.pointerHub.incoming()]
            .map(({{box}}) => box)
            .sort((a, b) => a.index.getValue() - b.index.getValue());
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
        const p = window.DAW;
        const api = p.api;
        const ef = window.DAW_EffectFactories;
        const srcIdx = {src_unit};
        const dstIdx = {dst_unit};

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (srcIdx >= units.length) return {{error: "No source AU at index " + srcIdx}};
        if (dstIdx >= units.length) return {{error: "No dest AU at index " + dstIdx}};

        const srcAU = units[srcIdx];
        const dstAU = units[dstIdx];

        const srcEffects = [...srcAU.audioEffects.pointerHub.incoming()]
            .map(({{box}}) => box)
            .sort((a, b) => a.index.getValue() - b.index.getValue());

        if (srcEffects.length === 0) return {{error: "Source AU has no effects"}};

        const cloned = [];
        p.editing.modify(() => {{
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
                const newEffect = api.insertEffect(dstAU.audioEffects, factory);

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

                const dstEffects = [...dstAU.audioEffects.pointerHub.incoming()]
                    .map(({{box}}) => box)
                    .sort((a, b) => a.index.getValue() - b.index.getValue());
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
        const p = window.DAW;
        const unitIdx = {unit_index};
        const fromIdx = {from_index};
        const toIdx = {to_index};

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
        const au = units[unitIdx];

        const effects = [...au.audioEffects.pointerHub.incoming()]
            .map(({{box}}) => box)
            .sort((a, b) => a.index.getValue() - b.index.getValue());
        if (fromIdx >= effects.length) return {{error: "from_index " + fromIdx + " out of range (" + effects.length + " effects)"}};
        if (toIdx >= effects.length) return {{error: "to_index " + toIdx + " out of range (" + effects.length + " effects)"}};
        if (fromIdx === toIdx) return {{success: true, message: "No change needed"}};

        const movedEffect = effects[fromIdx];
        p.editing.modify(() => {{
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
        const newOrder = [...au.audioEffects.pointerHub.incoming()]
            .map(({{box}}) => box)
            .sort((a, b) => a.index.getValue() - b.index.getValue())
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
        const p = window.DAW;
        const UUID = window.DAW_UUID;
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

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (srcIdx >= units.length) return {{error: "No src AU at index " + srcIdx}};

        const srcAU = units[srcIdx];
        const primaryBus = p.primaryAudioBusBox;
        const boxGraph = p.boxGraph;
        const AudioUnitType = window.DAW_AudioUnitType;

        // Aux type = 3 (AudioUnitType.Aux)
        const auxType = AudioUnitType ? AudioUnitType.Aux : 3;

        let sendBox, fxBus, fxUnit;

        p.editing.modify(() => {{
            // 1. Create FX AudioUnitBox (Aux type) — owns the effect chain, output → primary bus
            const existingCount = [...p.rootBox.audioUnits.pointerHub.incoming()].length;
            fxUnit = AudioUnitBox.create(boxGraph, UUID.generate(), (box) => {{
                box.collection.refer(p.rootBox.audioUnits);
                box.output.refer(primaryBus.input);
                box.index.setValue(existingCount);
                box.type.setValue(auxType);
            }});

            // 2. Create FX bus (AudioBusBox) — routes audio INTO fxUnit
            fxBus = AudioBusBox.create(boxGraph, UUID.generate(), (box) => {{
                box.collection.refer(p.rootBox.audioBusses);
                box.output.refer(fxUnit.input);
                box.enabled.setValue(true);
                box.label.setValue(fxName);
            }});

            // 3. Create AuxSendBox: src AU → FX bus (parallel send, no redirect)
            const currentSends = [...srcAU.auxSends.pointerHub.incoming()].length;
            sendBox = AuxSendBox.create(boxGraph, UUID.generate(), (box) => {{
                box.audioUnit.refer(srcAU.auxSends);
                box.targetBus.refer(fxBus.input);
                box.routing.setValue(routingVal);
                box.sendGain.setValue(sendDb);
                box.sendPan.setValue(0.0);
                box.index.setValue(currentSends);
            }});
        }});

        // Get updated unit list to find FX unit index
        const updatedUnits = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        const fxUnitIdx = updatedUnits.findIndex(b => b.address.equals(fxUnit.address));

        const sendIndex = [...srcAU.auxSends.pointerHub.incoming()]
            .map(({{box}}) => box)
            .sort((a, b) => a.index.getValue() - b.index.getValue())
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
        const p = window.DAW;
        const srcIdx = {src_unit};
        const sendIdx = {send_index};
        const levelDb = {level_db};

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (srcIdx >= units.length) return {{error: "No AU at index " + srcIdx}};
        const au = units[srcIdx];

        const sends = [...au.auxSends.pointerHub.incoming()]
            .map(({{box}}) => box)
            .sort((a, b) => a.index.getValue() - b.index.getValue());
        if (sendIdx >= sends.length) return {{error: "No send at index " + sendIdx + " (total: " + sends.length + ")"}};

        p.editing.modify(() => {{
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
        const p = window.DAW;
        const srcIdx = {unit_index};
        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (srcIdx >= units.length) return {{error: "No AU at index " + srcIdx}};
        const au = units[srcIdx];

        const sends = [...au.auxSends.pointerHub.incoming()]
            .map(({{box}}) => box)
            .sort((a, b) => a.index.getValue() - b.index.getValue());

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
        const p = window.DAW;
        const srcIdx = {unit_index};
        const sendIdx = {send_index};
        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (srcIdx >= units.length) return {{error: "No AU at index " + srcIdx}};
        const au = units[srcIdx];

        const sends = [...au.auxSends.pointerHub.incoming()]
            .map(({{box}}) => box)
            .sort((a, b) => a.index.getValue() - b.index.getValue());
        if (sendIdx >= sends.length) return {{error: "No send at index " + sendIdx + " (total: " + sends.length + ")"}};

        const sendBox = sends[sendIdx];
        p.editing.modify(() => {{
            sendBox.delete();
        }});

        return {{
            success: true,
            unit_index: srcIdx,
            removed_send_index: sendIdx,
            remaining_sends: [...au.auxSends.pointerHub.incoming()].length,
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
        const p = window.DAW;
        const srcIdx = {unit_index};
        const sendIdx = {send_index};
        const routingVal = {routing_val};
        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (srcIdx >= units.length) return {{error: "No AU at index " + srcIdx}};
        const au = units[srcIdx];

        const sends = [...au.auxSends.pointerHub.incoming()]
            .map(({{box}}) => box)
            .sort((a, b) => a.index.getValue() - b.index.getValue());
        if (sendIdx >= sends.length) return {{error: "No send at index " + sendIdx}};

        p.editing.modify(() => {{
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
    result = await bridge.evaluate(f"""() => {{
        const p = window.DAW;
        const buses = [...p.rootBox.audioBusses.pointerHub.incoming()].map(({{box}}) => box);
        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));

        const busList = buses.map((box, i) => {{
            let unitIdx = -1;
            try {{
                const targetBox = box.output.targetVertex?.unwrap?.()?.box;
                if (targetBox) {{
                    unitIdx = units.findIndex(u => u.address.equals(targetBox.address));
                }}
            }} catch(e) {{}}
            return {{
                bus_index: i,
                name: box.label?.getValue?.() ?? "Bus " + i,
                enabled: box.enabled?.getValue?.() ?? true,
                unit_index: unitIdx,
            }};
        }});

        return {{
            success: true,
            bus_count: buses.length,
            buses: busList,
        }};
    }}""")
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
        const p = window.DAW;
        const srcIdx = {unit_index};
        const sendIdx = {send_index};
        const panVal = {pan_val};
        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (srcIdx >= units.length) return {{error: "No AU at index " + srcIdx}};
        const au = units[srcIdx];

        const sends = [...au.auxSends.pointerHub.incoming()]
            .map(({{box}}) => box)
            .sort((a, b) => a.index.getValue() - b.index.getValue());
        if (sendIdx >= sends.length) return {{error: "No send at index " + sendIdx}};

        p.editing.modify(() => {{
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
        const p = window.DAW;
        const busIdx = {bus_index};
        const enableVal = {json.dumps(enabled)};
        const buses = [...p.rootBox.audioBusses.pointerHub.incoming()].map(({{box}}) => box);
        if (busIdx >= buses.length) return {{error: "No bus at index " + busIdx + " (total: " + buses.length + ")"}};

        p.editing.modify(() => {{
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
        const p = window.DAW;
        const busIdx = {bus_index};
        const fxUnitIdx = {fx_unit_index};
        const buses = [...p.rootBox.audioBusses.pointerHub.incoming()].map(({{box}}) => box);
        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));

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
        p.editing.modify(() => {{
            // Remove sends pointing to this bus first
            if (targetBus) {{
                for (const au of units) {{
                    const sends = [...au.auxSends.pointerHub.incoming()].map(({{box}}) => box);
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
        const p = window.DAW;
        const unitIdx = {unit_index};
        const effectIdx = {effect_index};

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()]
            .map(({{box}}) => box);
        if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};

        const au = units[unitIdx];
        const effects = [...au.audioEffects.pointerHub.incoming()]
            .map(({{box}}) => box)
            .sort((a, b) => a.index.getValue() - b.index.getValue());
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
        const p = window.DAW;
        const unitIdx = {unit_index};
        const effectIdx = {effect_index};

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
        const au = units[unitIdx];
        const effects = [...au.audioEffects.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => a.index.getValue() - b.index.getValue());
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
        const p = window.DAW;
        const unitIdx = {unit_index};
        const effectIdx = {effect_index};
        const paramName = "{safe_param}";
        const newValue = {value};

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()]
            .map(({{box}}) => box);
        if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};

        const au = units[unitIdx];
        const effects = [...au.audioEffects.pointerHub.incoming()]
            .map(({{box}}) => box)
            .sort((a, b) => a.index.getValue() - b.index.getValue());
        if (effectIdx >= effects.length) return {{error: "No effect at index " + effectIdx}};

        const effectBox = effects[effectIdx];
        const field = effectBox[paramName];
        if (!field || typeof field.setValue !== 'function') {{
            return {{error: "No parameter '" + paramName + "' on " + effectBox.constructor.name}};
        }}

        const oldValue = field.getValue();
        p.editing.modify(() => {{
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
        const p = window.DAW;
        const unitIdx = {unit_index};
        const effectIdx = {effect_index};
        const paramName = "{safe_param}";
        const newValue = "{safe_value}";

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()]
            .map(({{box}}) => box);
        if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};

        const au = units[unitIdx];
        const effects = [...au.audioEffects.pointerHub.incoming()]
            .map(({{box}}) => box)
            .sort((a, b) => a.index.getValue() - b.index.getValue());
        if (effectIdx >= effects.length) return {{error: "No effect at index " + effectIdx}};

        const effectBox = effects[effectIdx];
        const field = effectBox[paramName];
        if (!field || typeof field.setValue !== 'function') {{
            return {{error: "No parameter '" + paramName + "' on " + effectBox.constructor.name}};
        }}

        const oldValue = field.getValue();
        p.editing.modify(() => {{
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
        const p = window.DAW;
        const unitIdx = {unit_index};
        const effectIdx = {effect_index};

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()]
            .map(({{box}}) => box);
        if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};

        const au = units[unitIdx];
        const effects = [...au.audioEffects.pointerHub.incoming()]
            .map(({{box}}) => box)
            .sort((a, b) => a.index.getValue() - b.index.getValue());
        if (effectIdx >= effects.length) return {{error: "No effect at index " + effectIdx}};

        const effectBox = effects[effectIdx];
        const effectType = effectBox.constructor.name;

        p.editing.modify(() => {{
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
    result = await bridge.evaluate(f"""() => {{
        const ef = window.DAW_EffectFactories;
        return {{
            midi: ef.MidiNamed ? Object.keys(ef.MidiNamed) : [],
        }};
    }}""")
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
        const p = window.DAW;
        const api = p.api;
        const ef = window.DAW_EffectFactories;
        const effectType = "{safe_effect}";
        const unitIndex = {unit_index};

        const factory = ef.MidiNamed[effectType];
        if (!factory) return {{error: "MIDI effect factory not found: " + effectType}};

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (unitIndex >= units.length) return {{error: "No audio unit at index " + unitIndex}};
        const au = units[unitIndex];

        let effectBox;
        p.editing.modify(() => {{
            effectBox = api.insertEffect(au.midiEffects, factory);
        }});

        const effects = [...au.midiEffects.pointerHub.incoming()]
            .map(({{box}}) => box)
            .sort((a, b) => a.index.getValue() - b.index.getValue());
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
        const p = window.DAW;
        const unitIdx = {unit_index};
        const effectIdx = {effect_index};

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
        const au = units[unitIdx];

        const effects = [...au.midiEffects.pointerHub.incoming()]
            .map(({{box}}) => box)
            .sort((a, b) => a.index.getValue() - b.index.getValue());
        if (effectIdx >= effects.length) return {{error: "No MIDI effect at index " + effectIdx}};

        const effectBox = effects[effectIdx];
        const effectType = effectBox.constructor.name;

        p.editing.modify(() => {{ effectBox.delete(); }});

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
        const p = window.DAW;
        const unitIdx = {unit_index};

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
        const au = units[unitIdx];
        const effects = [...au.midiEffects.pointerHub.incoming()]
            .map(({{box}}) => box)
            .sort((a, b) => a.index.getValue() - b.index.getValue());

        const chain = effects.map((box, i) => ({{
            index: i,
            type: box.constructor.name,
            enabled: box.enabled?.getValue?.() ?? true,
            label: box.label?.getValue?.() || "",
        }}));

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
        const p = window.DAW;
        const unitIdx = {unit_index};
        const effectIdx = {effect_index};

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
        const au = units[unitIdx];

        const effects = [...au.midiEffects.pointerHub.incoming()]
            .map(({{box}}) => box)
            .sort((a, b) => a.index.getValue() - b.index.getValue());
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
        const p = window.DAW;
        const unitIdx = {unit_index};
        const effectIdx = {effect_index};
        const paramName = "{safe_param}";
        const paramIdx = {param_index};
        const newVal = {value};

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
        const au = units[unitIdx];

        const effects = [...au.midiEffects.pointerHub.incoming()]
            .map(({{box}}) => box)
            .sort((a, b) => a.index.getValue() - b.index.getValue());
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
        p.editing.modify(() => {{
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
        const p = window.DAW;
        const unitIdx = {unit_index};
        let vap = null;

        if (unitIdx >= 0) {{
            const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
            if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
            const au = units[unitIdx];
            const incoming = [...au.input.pointerHub.incoming()].map(({{box}}) => box);
            vap = incoming.find(b => b.constructor.name === "VaporisateurDeviceBox");
        }} else {{
            const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
            for (const au of units) {{
                const incoming = [...au.input.pointerHub.incoming()].map(({{box}}) => box);
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
        const p = window.DAW;
        const unitIdx = {unit_index};
        const oscIdx = {osc_index};
        const paramName = "{safe_param}";
        const newVal = {value};

        let vap = null;
        if (unitIdx >= 0) {{
            const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
            if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
            const au = units[unitIdx];
            const incoming = [...au.input.pointerHub.incoming()].map(({{box}}) => box);
            vap = incoming.find(b => b.constructor.name === "VaporisateurDeviceBox");
        }} else {{
            const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
            for (const au of units) {{
                const incoming = [...au.input.pointerHub.incoming()].map(({{box}}) => box);
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
        p.editing.modify(() => {{
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
        const p = window.DAW;
        const unitIdx = {unit_index};

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        let instBox = null;
        let auName = "";

        if (unitIdx >= 0) {{
            if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
            const au = units[unitIdx];
            auName = au.name?.getValue?.() || "Unit " + unitIdx;
            const incoming = [...au.input.pointerHub.incoming()].map(({{box}}) => box);
            instBox = incoming.find(b => b.constructor.name !== "AudioBusBox");
        }} else {{
            for (const au of units) {{
                const incoming = [...au.input.pointerHub.incoming()].map(({{box}}) => box);
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
        const p = window.DAW;
        const unitIdx = {unit_index};
        const paramName = "{safe_param}";
        const paramIdx = {param_index};
        const newVal = {value};

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        let instBox = null;

        if (unitIdx >= 0) {{
            if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
            const au = units[unitIdx];
            const incoming = [...au.input.pointerHub.incoming()].map(({{box}}) => box);
            instBox = incoming.find(b => b.constructor.name !== "AudioBusBox");
        }} else {{
            for (const au of units) {{
                const incoming = [...au.input.pointerHub.incoming()].map(({{box}}) => box);
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
        p.editing.modify(() => {{
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
        const p = window.DAW;
        const unitIdx = {unit_index};
        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        let pf = null;

        if (unitIdx >= 0) {{
            if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
            const au = units[unitIdx];
            const incoming = [...au.input.pointerHub.incoming()].map(({{box}}) => box);
            pf = incoming.find(b => b.constructor.name === "PlayfieldDeviceBox");
        }} else {{
            for (const au of units) {{
                const incoming = [...au.input.pointerHub.incoming()].map(({{box}}) => box);
                pf = incoming.find(b => b.constructor.name === "PlayfieldDeviceBox");
                if (pf) break;
            }}
        }}

        if (!pf) return {{error: "No Playfield found"}};

        const samples = [...pf.samples.pointerHub.incoming()].map(({{box}}) => box);
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
        const p = window.DAW;
        const unitIdx = {unit_index};
        const sampleIdx = {sample_index};
        const enabledVal = {json.dumps(enabled)};

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        let pf = null;

        if (unitIdx >= 0) {{
            if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
            const au = units[unitIdx];
            const incoming = [...au.input.pointerHub.incoming()].map(({{box}}) => box);
            pf = incoming.find(b => b.constructor.name === "PlayfieldDeviceBox");
        }} else {{
            for (const au of units) {{
                const incoming = [...au.input.pointerHub.incoming()].map(({{box}}) => box);
                pf = incoming.find(b => b.constructor.name === "PlayfieldDeviceBox");
                if (pf) break;
            }}
        }}

        if (!pf) return {{error: "No Playfield found"}};

        const samples = [...pf.samples.pointerHub.incoming()].map(({{box}}) => box);
        if (sampleIdx >= samples.length) return {{error: "No sample at index " + sampleIdx}};

        const sample = samples[sampleIdx];
        const oldVal = sample.enabled.getValue();
        p.editing.modify(() => {{
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
        const p = window.DAW;
        const UUID = window.DAW_UUID;
        const unitIdx = {unit_index};
        const note = {midi_note};
        const name = "{safe_name}";
        const dur = {duration_seconds};

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        let pf = null;

        if (unitIdx >= 0) {{
            if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
            const au = units[unitIdx];
            const incoming = [...au.input.pointerHub.incoming()].map(({{box}}) => box);
            pf = incoming.find(b => b.constructor.name === "PlayfieldDeviceBox");
        }} else {{
            for (const au of units) {{
                const incoming = [...au.input.pointerHub.incoming()].map(({{box}}) => box);
                pf = incoming.find(b => b.constructor.name === "PlayfieldDeviceBox");
                if (pf) break;
            }}
        }}

        if (!pf) return {{error: "No Playfield found"}};

        // Need at least one existing sample to get the class constructor
        const existingSamples = [...pf.samples.pointerHub.incoming()].map(({{box}}) => box);
        if (existingSamples.length === 0) return {{error: "Playfield has no samples — create with InstrumentFactories.Playfield first"}};
        const SampleClass = existingSamples[0].constructor;
        const newIndex = existingSamples.length;

        let result;
        p.editing.modify(() => {{
            const fileUUID = UUID.generate();
            const AudioFileBox = window.DAW_AudioFileBox;
            const fileBox = AudioFileBox.create(p.boxGraph, fileUUID, box => {{
                box.fileName.setValue(name);
                box.endInSeconds.setValue(dur);
            }});

            const sampleBox = SampleClass.create(p.boxGraph, UUID.generate(), box => {{
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
        const p = window.DAW;
        const unitIdx = {unit_index};
        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};

        const au = units[unitIdx];
        const auType = au.type?.getValue?.() ?? "unknown";
        const trackCount = [...au.tracks.pointerHub.incoming()].length;
        const effectCount = [...au.audioEffects.pointerHub.incoming()].length;

        p.editing.modify(() => p.api.deleteAudioUnit(au));

        const remaining = [...p.rootBox.audioUnits.pointerHub.incoming()].length;
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
        const p = window.DAW;
        const unitIdx = {unit_index};

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()]
            .map(({{box}}) => box);
        if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};

        const au = units[unitIdx];
        const effects = [...au.audioEffects.pointerHub.incoming()]
            .map(({{box}}) => box)
            .sort((a, b) => a.index.getValue() - b.index.getValue());

        const chain = effects.map((box, i) => ({{
            index: i,
            type: box.constructor.name,
            enabled: box.enabled?.getValue?.() ?? true,
            label: box.label?.getValue?.() || "",
        }}));

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
        const p = window.DAW;
        const api = p.api;
        const bg = p.boxGraph;
        const UUID = window.DAW_UUID;
        const PPQN = window.DAW_PPQN;
        const NoteEventBox = window.DAW_NoteEventBox;
        const NoteEventCollectionBox = window.DAW_NoteEventCollectionBox;
        const NoteRegionBox = window.DAW_NoteRegionBox;

        const trackIndex = {track_index};
        const pitch = {pitch};
        const startBeat = {start_beat};
        const durationBeats = {duration_beats};
        const velocity = {velocity};
        const unitIdx = {unit_index};

        const Quarter = PPQN.Quarter;
        const startPosition = Math.round(startBeat * Quarter);
        const noteDuration = Math.round(durationBeats * Quarter);

        // Find note tracks — either on specified AU or across all AUs
        // IMPORTANT: pointerHub.incoming() does NOT guarantee order by index field.
        // Sort by index to match DAW_HELPERS.au() ordering (adapters() sorts by index).
        let noteTracks = [];
        if (unitIdx < 0) {{
            const allUnits = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
            for (const au of allUnits) {{
                const tracks = [...au.tracks.pointerHub.incoming()]
                    .map(({{box}}) => box)
                    .filter(box => box.type?.getValue?.() === 1);
                noteTracks.push(...tracks);
            }}
        }} else {{
            const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box)
                .sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
            if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
            noteTracks = [...units[unitIdx].tracks.pointerHub.incoming()]
                .map(({{box}}) => box)
                .filter(box => box.type?.getValue?.() === 1);
        }}

        if (noteTracks.length === 0) return {{error: "No note tracks found. Call mcp_opendaw_create_note_track first."}};
        if (trackIndex >= noteTracks.length) return {{error: "Track index " + trackIndex + " out of range (" + noteTracks.length + " note tracks)."}};

        const trackBox = noteTracks[trackIndex];

        p.editing.modify(() => {{
            // Find existing region on this track, or create one
            const existingRegions = [...trackBox.regions.pointerHub.incoming()].map(({{box}}) => box);
            let regionBox = null;
            let collection = null;

            if (existingRegions.length > 0) {{
                // Use the first existing region — add note to its events collection
                regionBox = existingRegions[0];
            }}

            if (!regionBox) {{
                // Create new NoteEventCollectionBox + NoteRegionBox
                collection = NoteEventCollectionBox.create(bg, UUID.generate());
                regionBox = NoteRegionBox.create(bg, UUID.generate(), (box) => {{
                    box.position.setValue(0);
                    box.label.setValue("Notes");
                    box.mute.setValue(false);
                    box.duration.setValue(Math.max(noteDuration, 4 * Quarter));  // at least 1 bar
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
            
            // Get the events collection box from the region
            // regionBox.events is a PointerField → targetVertex.unwrap() returns a Field
            // whose .box is the NoteEventCollectionBox
            const eventsField = regionBox.events.targetVertex.unwrap();
            const collBox = eventsField.box;
            
            NoteEventBox.create(bg, UUID.generate(), (box) => {{
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
    ppqn_base = mid.ticks_per_beat if mid.ticks_per_beat else 480
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
        const p = window.DAW;
        const bg = p.boxGraph;
        const UUID = window.DAW_UUID;
        const PPQN = window.DAW_PPQN;
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
            const allUnits = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
            for (const au of allUnits) {{
                const tracks = [...au.tracks.pointerHub.incoming()]
                    .map(({{box}}) => box)
                    .filter(box => box.type?.getValue?.() === 1);
                noteTracks.push(...tracks);
            }}
        }} else {{
            const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
            if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
            noteTracks = [...units[unitIdx].tracks.pointerHub.incoming()]
                .map(({{box}}) => box)
                .filter(box => box.type?.getValue?.() === 1);
        }}

        if (noteTracks.length === 0) return {{error: "No note tracks found. Call create_note_track first."}};
        if (trackIdx >= noteTracks.length) return {{error: "Track index out of range"}};
        const trackBox = noteTracks[trackIdx];

        // Find region start and total duration
        const minStart = Math.min(...notes.map(n => n.start));
        const maxEnd = Math.max(...notes.map(n => n.start + n.duration));
        const regionStart = minStart;
        const regionDuration = maxEnd - minStart;

        p.editing.modify(() => {{
            // Create collection for all notes
            const collection = NoteEventCollectionBox.create(bg, UUID.generate());

            // Create region
            NoteRegionBox.create(bg, UUID.generate(), (box) => {{
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
                NoteEventBox.create(bg, UUID.generate(), (box) => {{
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
            start_beat: regionStart / 960,
            total_beats: maxEnd / 960,
            ppqn_source: {ppqn},
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_transpose_notes(semitones: int, unit_index: int, track_index: int) -> str:
    """Transpose all notes by a number of semitones.

semitones: Positive = up, negative = down (e.g. +12 = octave up, -5 = perfect fourth down).
unit_index: Audio unit index (-1 = all AUs with note tracks).
track_index: Specific note track (-1 = all note tracks on the AU).

Returns count of notes transposed.
"""
    result = await bridge.evaluate(f"""() => {{
        const p = window.DAW;
        const semis = {semitones};
        const unitIdx = {unit_index};
        const trackIdx = {track_index};

        let count = 0;
        const allUnits = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        const targetUnits = unitIdx < 0 ? allUnits : (unitIdx < allUnits.length ? [allUnits[unitIdx]] : []);

        p.editing.modify(() => {{
            for (const au of targetUnits) {{
                const noteTracks = [...au.tracks.pointerHub.incoming()]
                    .map(({{box}}) => box)
                    .filter(box => box.type?.getValue?.() === 1);
                const targetTracks = trackIdx < 0 ? noteTracks : (trackIdx < noteTracks.length ? [noteTracks[trackIdx]] : []);
                for (const track of targetTracks) {{
                    const regions = [...track.regions.pointerHub.incoming()].map(({{box}}) => box);
                    for (const region of regions) {{
                        // region.events → targetVertex → field → field.box = NoteEventCollectionBox
                        // collection.events field → incoming = NoteEventBox array
                        try {{
                            const vertex = region.events.targetVertex.unwrap();
                            const collectionBox = vertex.box || vertex;
                            if (collectionBox && collectionBox.events) {{
                                const noteEvents = [...collectionBox.events.pointerHub.incoming()].map(({{box}}) => box);
                                for (const evt of noteEvents) {{
                                    const current = evt.pitch.getValue();
                                    const newPitch = Math.max(0, Math.min(127, current + semis));
                                    evt.pitch.setValue(newPitch);
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
            semitones: semis,
            notes_transposed: count,
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
        const p = window.DAW;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};

        let noteTracks = [];
        if (unitIdx < 0) {{
            const allUnits = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
            for (const au of allUnits) {{
                const tracks = [...au.tracks.pointerHub.incoming()]
                    .map(({{box}}) => box)
                    .filter(box => box.type?.getValue?.() === 1);
                noteTracks.push(...tracks);
            }}
        }} else {{
            const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            noteTracks = [...units[unitIdx].tracks.pointerHub.incoming()]
                .map(({{box}}) => box)
                .filter(box => box.type?.getValue?.() === 1);
        }}

        if (trackIdx >= noteTracks.length) return {{error: "No note track at index " + trackIdx}};
        const trackBox = noteTracks[trackIdx];

        const regions = [...trackBox.regions.pointerHub.incoming()].map(({{box}}) => box);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx + " (total: " + regions.length + ")"}};

        p.editing.modify(() => {{
            regions[regionIdx].delete();
        }});

        return {{
            success: true,
            remaining_regions: [...trackBox.regions.pointerHub.incoming()].length,
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
        const p = window.DAW;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
        const au = units[unitIdx];

        const audioTracks = [...au.tracks.pointerHub.incoming()]
            .map(({{box}}) => box)
            .filter(box => box.type?.getValue?.() === 2);
        if (trackIdx >= audioTracks.length) return {{error: "No audio track at index " + trackIdx + " (total: " + audioTracks.length + ")"}};

        const trackBox = audioTracks[trackIdx];
        const regions = [...trackBox.regions.pointerHub.incoming()].map(({{box}}) => box);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx + " (total: " + regions.length + ")"}};

        p.editing.modify(() => {{
            regions[regionIdx].delete();
        }});

        return {{
            success: true,
            remaining_regions: [...trackBox.regions.pointerHub.incoming()].length,
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
        const p = window.DAW;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const allUnits = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        const targetUnits = unitIdx < 0 ? allUnits : (unitIdx < allUnits.length ? [allUnits[unitIdx]] : []);
        const Quarter = 960;

        const regionList = [];
        for (let ui = 0; ui < targetUnits.length; ui++) {{
            const au = targetUnits[ui];
            const auIdx = allUnits.indexOf(au);
            const noteTracks = [...au.tracks.pointerHub.incoming()]
                .map(({{box}}) => box)
                .filter(box => box.type?.getValue?.() === 1);
            const targetTracks = trackIdx < 0 ? noteTracks : (trackIdx < noteTracks.length ? [noteTracks[trackIdx]] : []);
            for (let ti = 0; ti < targetTracks.length; ti++) {{
                const track = targetTracks[ti];
                const trackIdxActual = noteTracks.indexOf(track);
                const regions = [...track.regions.pointerHub.incoming()].map(({{box}}) => box);
                for (let ri = 0; ri < regions.length; ri++) {{
                    const region = regions[ri];
                    let noteCount = 0;
                    try {{
                        const vertex = region.events.targetVertex.unwrap();
                        const collectionBox = vertex.box || vertex;
                        if (collectionBox && collectionBox.events) {{
                            noteCount = [...collectionBox.events.pointerHub.incoming()].length;
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
        const p = window.DAW;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
        const au = units[unitIdx];
        const Quarter = 960;

        const audioTracks = [...au.tracks.pointerHub.incoming()]
            .map(({{box}}) => box)
            .filter(box => box.type?.getValue?.() === 2);
        const targetTracks = trackIdx < 0 ? audioTracks : (trackIdx < audioTracks.length ? [audioTracks[trackIdx]] : []);

        const regionList = [];
        for (let ti = 0; ti < targetTracks.length; ti++) {{
            const track = targetTracks[ti];
            const trackIdxActual = audioTracks.indexOf(track);
            const regions = [...track.regions.pointerHub.incoming()].map(({{box}}) => box);
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
        const p = window.DAW;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const fadeIn = {fade_in};
        const fadeOut = {fade_out};
        const inSlope = {in_slope};
        const outSlope = {out_slope};

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
        const au = units[unitIdx];

        const audioTracks = [...au.tracks.pointerHub.incoming()]
            .map(({{box}}) => box)
            .filter(box => box.type?.getValue?.() === 2);
        if (trackIdx >= audioTracks.length) return {{error: "No audio track at index " + trackIdx}};
        const track = audioTracks[trackIdx];

        const regions = [...track.regions.pointerHub.incoming()].map(({{box}}) => box);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx}};
        const region = regions[regionIdx];

        if (!region.fading) return {{error: "Region has no fading field"}};

        p.editing.modify(() => {{
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
        const p = window.DAW;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const gainDb = {gain_db};

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
        const au = units[unitIdx];

        const audioTracks = [...au.tracks.pointerHub.incoming()]
            .map(({{box}}) => box)
            .filter(box => box.type?.getValue?.() === 2);
        if (trackIdx >= audioTracks.length) return {{error: "No audio track at index " + trackIdx}};
        const track = audioTracks[trackIdx];

        const regions = [...track.regions.pointerHub.incoming()].map(({{box}}) => box);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx}};
        const region = regions[regionIdx];

        if (!region.gain) return {{error: "Region has no gain field"}};

        p.editing.modify(() => {{
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
        const p = window.DAW;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const gridTicks = {grid_ticks};
        const strength = {strength};

        let count = 0;
        const allUnits = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        const targetUnits = unitIdx < 0 ? allUnits : (unitIdx < allUnits.length ? [allUnits[unitIdx]] : []);

        p.editing.modify(() => {{
            for (const au of targetUnits) {{
                const noteTracks = [...au.tracks.pointerHub.incoming()]
                    .map(({{box}}) => box)
                    .filter(box => box.type?.getValue?.() === 1);
                const targetTracks = trackIdx < 0 ? noteTracks : (trackIdx < noteTracks.length ? [noteTracks[trackIdx]] : []);
                for (const track of targetTracks) {{
                    const regions = [...track.regions.pointerHub.incoming()].map(({{box}}) => box);
                    for (const region of regions) {{
                        // Quantize region position (absolute timeline position)
                        const regPos = region.position.getValue();
                        const nearestReg = Math.round(regPos / gridTicks) * gridTicks;
                        const newRegPos = regPos + (nearestReg - regPos) * strength;
                        region.position.setValue(Math.round(newRegPos));

                        // Also quantize note events within the region (relative positions)
                        try {{
                            const vertex = region.events.targetVertex.unwrap();
                            const collectionBox = vertex.box || vertex;
                            if (collectionBox && collectionBox.events) {{
                                const noteEvents = [...collectionBox.events.pointerHub.incoming()].map(({{box}}) => box);
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
        const p = window.DAW;
        const UUID = window.DAW_UUID;
        const NoteRegionBox = window.DAW_NoteRegionBox;
        const NoteEventCollectionBox = window.DAW_NoteEventCollectionBox;
        const NoteEventBox = window.DAW_NoteEventBox;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const offsetTicks = Math.round({offset_beats} * 960);

        let noteTracks = [];
        if (unitIdx < 0) {{
            const allUnits = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
            for (const au of allUnits) {{
                const tracks = [...au.tracks.pointerHub.incoming()]
                    .map(({{box}}) => box)
                    .filter(box => box.type?.getValue?.() === 1);
                noteTracks.push(...tracks);
            }}
        }} else {{
            const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            noteTracks = [...units[unitIdx].tracks.pointerHub.incoming()]
                .map(({{box}}) => box)
                .filter(box => box.type?.getValue?.() === 1);
        }}

        if (trackIdx >= noteTracks.length) return {{error: "No note track at index " + trackIdx}};
        const trackBox = noteTracks[trackIdx];

        const regions = [...trackBox.regions.pointerHub.incoming()].map(({{box}}) => box);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx}};

        const srcRegion = regions[regionIdx];
        const srcPos = srcRegion.position.getValue();
        const srcDuration = srcRegion.duration.getValue();
        const newPos = srcPos + offsetTicks;

        let newRegionIdx = -1;
        p.editing.modify(() => {{
            // Get source collection
            let srcCollection = null;
            try {{
                const vertex = srcRegion.events.targetVertex.unwrap();
                srcCollection = vertex.box || vertex;
            }} catch(e) {{}}

            if (srcCollection && srcCollection.events) {{
                // Create new collection and copy all note events
                const newCollection = NoteEventCollectionBox.create(p.boxGraph, UUID.generate());
                const srcNotes = [...srcCollection.events.pointerHub.incoming()].map(({{box}}) => box);
                for (const srcNote of srcNotes) {{
                    NoteEventBox.create(p.boxGraph, UUID.generate(), (box) => {{
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
                NoteRegionBox.create(p.boxGraph, UUID.generate(), (box) => {{
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
            const updatedRegions = [...trackBox.regions.pointerHub.incoming()].map(({{box}}) => box);
            newRegionIdx = updatedRegions.length - 1;
        }});

        return {{
            success: true,
            new_region_index: newRegionIdx,
            new_position_beats: newPos / 960,
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
        const p = window.DAW;
        const UUID = window.DAW_UUID;
        const NoteEventBox = window.DAW_NoteEventBox;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const Quarter = 960;

        let noteTracks = [];
        if (unitIdx < 0) {{
            const allUnits = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
            for (const au of allUnits) {{
                const tracks = [...au.tracks.pointerHub.incoming()]
                    .map(({{box}}) => box)
                    .filter(box => box.type?.getValue?.() === 1);
                noteTracks.push(...tracks);
            }}
        }} else {{
            const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            noteTracks = [...units[unitIdx].tracks.pointerHub.incoming()]
                .map(({{box}}) => box)
                .filter(box => box.type?.getValue?.() === 1);
        }}

        if (trackIdx >= noteTracks.length) return {{error: "No note track at index " + trackIdx}};
        const trackBox = noteTracks[trackIdx];

        const regions = [...trackBox.regions.pointerHub.incoming()].map(({{box}}) => box);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx}};

        const srcRegion = regions[regionIdx];
        let collection = null;
        try {{
            const vertex = srcRegion.events.targetVertex.unwrap();
            collection = vertex.box || vertex;
        }} catch(e) {{}}

        if (!collection || !collection.events) return {{error: "No note collection in region"}};

        const notes = [...collection.events.pointerHub.incoming()].map(({{box}}) => box);
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
        p.editing.modify(() => {{
            for (const n of notes) {{
                NoteEventBox.create(p.boxGraph, UUID.generate(), (box) => {{
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
        const p = window.DAW;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const Quarter = 960;

        let noteTracks = [];
        if (unitIdx < 0) {{
            const allUnits = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
            for (const au of allUnits) {{
                const tracks = [...au.tracks.pointerHub.incoming()]
                    .map(({{box}}) => box)
                    .filter(box => box.type?.getValue?.() === 1);
                noteTracks.push(...tracks);
            }}
        }} else {{
            const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            noteTracks = [...units[unitIdx].tracks.pointerHub.incoming()]
                .map(({{box}}) => box)
                .filter(box => box.type?.getValue?.() === 1);
        }}

        if (trackIdx >= noteTracks.length) return {{error: "No note track at index " + trackIdx}};
        const trackBox = noteTracks[trackIdx];

        const regions = [...trackBox.regions.pointerHub.incoming()].map(({{box}}) => box);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx}};

        let collection = null;
        try {{
            const vertex = regions[regionIdx].events.targetVertex.unwrap();
            collection = vertex.box || vertex;
        }} catch(e) {{}}
        if (!collection || !collection.events) return {{error: "No note collection in region"}};

        const notes = [...collection.events.pointerHub.incoming()].map(({{box}}) => box);
        const noteList = notes.map((n, i) => ({{
            index: i,
            position_beats: n.position?.getValue?.() / Quarter ?? 0,
            duration_beats: n.duration?.getValue?.() / Quarter ?? 0,
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
        const p = window.DAW;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const noteIdx = {note_index};
        const Quarter = 960;
        const newPos = {position_beats};
        const newDur = {duration_beats};
        const newPitch = {pitch};
        const newVel = {velocity};
        const newCent = {cent};
        const newChance = {chance};

        let noteTracks = [];
        if (unitIdx < 0) {{
            const allUnits = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
            for (const au of allUnits) {{
                const tracks = [...au.tracks.pointerHub.incoming()]
                    .map(({{box}}) => box)
                    .filter(box => box.type?.getValue?.() === 1);
                noteTracks.push(...tracks);
            }}
        }} else {{
            const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            noteTracks = [...units[unitIdx].tracks.pointerHub.incoming()]
                .map(({{box}}) => box)
                .filter(box => box.type?.getValue?.() === 1);
        }}

        if (trackIdx >= noteTracks.length) return {{error: "No note track at index " + trackIdx}};
        const trackBox = noteTracks[trackIdx];

        const regions = [...trackBox.regions.pointerHub.incoming()].map(({{box}}) => box);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx}};

        let collection = null;
        try {{
            const vertex = regions[regionIdx].events.targetVertex.unwrap();
            collection = vertex.box || vertex;
        }} catch(e) {{}}
        if (!collection || !collection.events) return {{error: "No note collection in region"}};

        const notes = [...collection.events.pointerHub.incoming()].map(({{box}}) => box);
        if (noteIdx < 0 || noteIdx >= notes.length) return {{error: "Note index " + noteIdx + " out of range (0.." + (notes.length-1) + ")"}};
        const note = notes[noteIdx];

        p.editing.modify(() => {{
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
        const p = window.DAW;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const noteIdx = {note_index};

        let noteTracks = [];
        if (unitIdx < 0) {{
            const allUnits = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
            for (const au of allUnits) {{
                const tracks = [...au.tracks.pointerHub.incoming()]
                    .map(({{box}}) => box)
                    .filter(box => box.type?.getValue?.() === 1);
                noteTracks.push(...tracks);
            }}
        }} else {{
            const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            noteTracks = [...units[unitIdx].tracks.pointerHub.incoming()]
                .map(({{box}}) => box)
                .filter(box => box.type?.getValue?.() === 1);
        }}

        if (trackIdx >= noteTracks.length) return {{error: "No note track at index " + trackIdx}};
        const trackBox = noteTracks[trackIdx];

        const regions = [...trackBox.regions.pointerHub.incoming()].map(({{box}}) => box);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx}};

        let collection = null;
        try {{
            const vertex = regions[regionIdx].events.targetVertex.unwrap();
            collection = vertex.box || vertex;
        }} catch(e) {{}}
        if (!collection || !collection.events) return {{error: "No note collection in region"}};

        const notes = [...collection.events.pointerHub.incoming()].map(({{box}}) => box);
        if (noteIdx < 0 || noteIdx >= notes.length) return {{error: "Note index " + noteIdx + " out of range (0.." + (notes.length-1) + ")"}};

        p.editing.modify(() => {{
            notes[noteIdx].delete();
        }});

        const remaining = [...collection.events.pointerHub.incoming()].length;
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
        const p = window.DAW;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const typeVal = {type_val};

        let tracks = [];
        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (unitIdx < 0) {{
            for (const au of units) {{
                const ts = [...au.tracks.pointerHub.incoming()].map(({{box}}) => box);
                tracks.push(...ts);
            }}
        }} else {{
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            tracks = [...units[unitIdx].tracks.pointerHub.incoming()].map(({{box}}) => box);
        }}

        // Filter by type if specified
        const targetTracks = typeVal > 0 ? tracks.filter(t => t.type?.getValue?.() === typeVal) : tracks;
        if (trackIdx >= targetTracks.length) return {{error: "No matching track at index " + trackIdx}};
        const trackBox = targetTracks[trackIdx];

        const regions = [...trackBox.regions.pointerHub.incoming()].map(({{box}}) => box);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx}};

        p.editing.modify(() => {{
            regions[regionIdx].delete();
        }});

        const remaining = [...trackBox.regions.pointerHub.incoming()].length;
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
    result = await bridge.evaluate(f"""() => {{
        const p = window.DAW;
        const PPQN = window.DAW_PPQN;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const rType = "{safe_region_type}";
        const newPos = Math.round({position_beats} * PPQN.Quarter);

        let tracks = [];
        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (unitIdx < 0) {{
            for (const au of units) {{
                const ts = [...au.tracks.pointerHub.incoming()].map(({{box}}) => box);
                tracks.push(...ts);
            }}
        }} else {{
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            tracks = [...units[unitIdx].tracks.pointerHub.incoming()].map(({{box}}) => box);
        }}
        if (trackIdx >= tracks.length) return {{error: "No track at index " + trackIdx}};
        const trackBox = tracks[trackIdx];

        const regions = [...trackBox.regions.pointerHub.incoming()].map(({{box}}) => box);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx}};

        const oldPos = regions[regionIdx].position.getValue();
        p.editing.modify(() => {{
            regions[regionIdx].position.setValue(newPos);
        }});

        return {{
            success: true,
            old_position_beats: oldPos / PPQN.Quarter,
            new_position_beats: newPos / PPQN.Quarter,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_set_region_duration(track_index: int, region_index: int, duration_beats: int, unit_index: int, region_type: str) -> str:
    """Set the duration of a region.

duration_beats: New duration in beats (e.g. 4.0 = 1 bar in 4/4).
"""
    result = await bridge.evaluate(f"""() => {{
        const p = window.DAW;
        const PPQN = window.DAW_PPQN;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const newDur = Math.round({duration_beats} * PPQN.Quarter);

        let tracks = [];
        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (unitIdx < 0) {{
            for (const au of units) {{
                const ts = [...au.tracks.pointerHub.incoming()].map(({{box}}) => box);
                tracks.push(...ts);
            }}
        }} else {{
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            tracks = [...units[unitIdx].tracks.pointerHub.incoming()].map(({{box}}) => box);
        }}
        if (trackIdx >= tracks.length) return {{error: "No track at index " + trackIdx}};
        const trackBox = tracks[trackIdx];

        const regions = [...trackBox.regions.pointerHub.incoming()].map(({{box}}) => box);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx}};

        const oldDur = regions[regionIdx].duration.getValue();
        p.editing.modify(() => {{
            regions[regionIdx].duration.setValue(newDur);
            if (regions[regionIdx].loopDuration) {{
                regions[regionIdx].loopDuration.setValue(newDur);
            }}
        }});

        return {{
            success: true,
            old_duration_beats: oldDur / PPQN.Quarter,
            new_duration_beats: newDur / PPQN.Quarter,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_set_region_mute(track_index: int, region_index: int, mute: bool, unit_index: int, region_type: str) -> str:
    """Mute or unmute a specific region without deleting it.

mute: true to mute, false to unmute.
"""
    result = await bridge.evaluate(f"""() => {{
        const p = window.DAW;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const muteVal = {json.dumps(mute)};

        let tracks = [];
        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (unitIdx < 0) {{
            for (const au of units) {{
                const ts = [...au.tracks.pointerHub.incoming()].map(({{box}}) => box);
                tracks.push(...ts);
            }}
        }} else {{
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            tracks = [...units[unitIdx].tracks.pointerHub.incoming()].map(({{box}}) => box);
        }}
        if (trackIdx >= tracks.length) return {{error: "No track at index " + trackIdx}};
        const trackBox = tracks[trackIdx];

        const regions = [...trackBox.regions.pointerHub.incoming()].map(({{box}}) => box);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx}};

        const oldMute = regions[regionIdx].mute?.getValue?.() ?? false;
        p.editing.modify(() => {{
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
        const p = window.DAW;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};

        let tracks = [];
        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (unitIdx < 0) {{
            for (const au of units) {{
                const ts = [...au.tracks.pointerHub.incoming()].map(({{box}}) => box);
                tracks.push(...ts);
            }}
        }} else {{
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            tracks = [...units[unitIdx].tracks.pointerHub.incoming()].map(({{box}}) => box);
        }}
        if (trackIdx >= tracks.length) return {{error: "No track at index " + trackIdx}};
        const trackBox = tracks[trackIdx];

        const regions = [...trackBox.regions.pointerHub.incoming()].map(({{box}}) => box);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx}};

        const oldLabel = regions[regionIdx].label?.getValue?.() ?? "";
        p.editing.modify(() => {{
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
        const p = window.DAW;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const hueVal = {hue};

        let tracks = [];
        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (unitIdx < 0) {{
            for (const au of units) {{
                const ts = [...au.tracks.pointerHub.incoming()].map(({{box}}) => box);
                tracks.push(...ts);
            }}
        }} else {{
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            tracks = [...units[unitIdx].tracks.pointerHub.incoming()].map(({{box}}) => box);
        }}
        if (trackIdx >= tracks.length) return {{error: "No track at index " + trackIdx}};
        const trackBox = tracks[trackIdx];

        const regions = [...trackBox.regions.pointerHub.incoming()].map(({{box}}) => box);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx}};
        const region = regions[regionIdx];

        if (!region.hue) return {{error: "Region has no hue field"}};
        const oldHue = region.hue?.getValue?.() ?? 0;
        p.editing.modify(() => {{
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
    result = await bridge.evaluate(f"""() => {{
        const p = window.DAW;
        const tl = p.timelineBox;
        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));

        let totalTracks = 0, totalRegions = 0, totalEffects = 0, totalNotes = 0;
        let maxPos = 0;

        for (const au of units) {{
            const tracks = [...au.tracks.pointerHub.incoming()].map(({{box}}) => box);
            totalTracks += tracks.length;
            for (const track of tracks) {{
                const regions = [...track.regions.pointerHub.incoming()].map(({{box}}) => box);
                totalRegions += regions.length;
                for (const reg of regions) {{
                    const endPos = (reg.position?.getValue?.() ?? 0) + (reg.duration?.getValue?.() ?? 0);
                    if (endPos > maxPos) maxPos = endPos;
                    // Count notes in note regions
                    try {{
                        const col = reg.events?.targetVertex?.unwrap()?.box;
                        if (col && col.events) {{
                            totalNotes += [...col.events.pointerHub.incoming()].length;
                        }}
                    }} catch(e) {{}}
                }}
            }}
            const effects = [...au.audioEffects.pointerHub.incoming()].map(({{box}}) => box);
            totalEffects += effects.length;
        }}

        return {{
            bpm: tl?.bpm?.getValue?.() ?? 120,
            time_signature: `${{tl?.signature?.nominator?.getValue?.() ?? 4}}/${{tl?.signature?.denominator?.getValue?.() ?? 4}}`,
            audio_units: units.length,
            tracks: totalTracks,
            regions: totalRegions,
            effects: totalEffects,
            notes: totalNotes,
            duration_beats: maxPos / 960,
            duration_bars: Math.ceil(maxPos / (960 * (tl?.signature?.nominator?.getValue?.() ?? 4))),
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_compact_tracks(unit_index: int) -> str:
    """Remove empty tracks from an audio unit (or all AUs).

Calls ProjectApi.compactTracks() — removes tracks with no regions.
Useful cleanup after deleting regions or editing.

unit_index: Audio unit index (-1 = all AUs).
"""
    result = await bridge.evaluate(f"""() => {{
        const p = window.DAW;
        const unitIdx = {unit_index};
        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));

        const results = [];
        if (unitIdx < 0) {{
            for (let i = 0; i < units.length; i++) {{
                const before = [...units[i].tracks.pointerHub.incoming()].length;
                p.editing.modify(() => p.api.compactTracks(units[i]));
                const after = [...units[i].tracks.pointerHub.incoming()].length;
                results.push({{au: i, before, after, removed: before - after}});
            }}
        }} else {{
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            const before = [...units[unitIdx].tracks.pointerHub.incoming()].length;
            p.editing.modify(() => p.api.compactTracks(units[unitIdx]));
            const after = [...units[unitIdx].tracks.pointerHub.incoming()].length;
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
        const p = window.DAW;
        const PPQN = window.DAW_PPQN;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const loopTicks = Math.round({loop_beats} * PPQN.Quarter);
        const loopOffsetTicks = Math.round({loop_offset_beats} * PPQN.Quarter);
        const eventOffsetTicks = Math.round({event_offset_beats} * PPQN.Quarter);

        let tracks = [];
        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (unitIdx < 0) {{
            for (const au of units) {{
                const ts = [...au.tracks.pointerHub.incoming()].map(({{box}}) => box);
                tracks.push(...ts);
            }}
        }} else {{
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            tracks = [...units[unitIdx].tracks.pointerHub.incoming()].map(({{box}}) => box);
        }}
        if (trackIdx >= tracks.length) return {{error: "No track at index " + trackIdx}};
        const trackBox = tracks[trackIdx];

        const regions = [...trackBox.regions.pointerHub.incoming()].map(({{box}}) => box);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx}};

        const oldLoop = regions[regionIdx].loopDuration?.getValue?.() ?? 0;
        p.editing.modify(() => {{
            regions[regionIdx].loopDuration.setValue(loopTicks);
            if (regions[regionIdx].loopOffset) regions[regionIdx].loopOffset.setValue(loopOffsetTicks);
            if (regions[regionIdx].eventOffset) regions[regionIdx].eventOffset.setValue(eventOffsetTicks);
        }});

        return {{
            success: true,
            old_loop_beats: oldLoop / PPQN.Quarter,
            new_loop_beats: loopTicks / PPQN.Quarter,
            loop_offset_beats: loopOffsetTicks / PPQN.Quarter,
            event_offset_beats: eventOffsetTicks / PPQN.Quarter,
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
        const p = window.DAW;
        const MidiFile = window.DAW_MidiFile;
        const MidiTrack = window.DAW_MidiTrack;
        const ControlEvent = window.DAW_ControlEvent;
        const ControlType = window.DAW_ControlType;
        const ArrayMultimap = window.DAW_ArrayMultimap;
        const PPQN = window.DAW_PPQN;

        if (!MidiFile) throw new Error("lib-midi not loaded — reload page");
        if (!ArrayMultimap) throw new Error("ArrayMultimap not loaded — reload page");

        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};

        // Find note tracks
        let noteTracks = [];
        if (unitIdx < 0) {{
            const allUnits = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
            for (const au of allUnits) {{
                const tracks = [...au.tracks.pointerHub.incoming()]
                    .map(({{box}}) => box)
                    .filter(box => box.type?.getValue?.() === 1);
                noteTracks.push(...tracks);
            }}
        }} else {{
            const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            noteTracks = [...units[unitIdx].tracks.pointerHub.incoming()]
                .map(({{box}}) => box)
                .filter(box => box.type?.getValue?.() === 1);
        }}

        if (trackIdx >= noteTracks.length) return {{error: "No note track at index " + trackIdx}};
        const trackBox = noteTracks[trackIdx];

        const regions = [...trackBox.regions.pointerHub.incoming()].map(({{box}}) => box);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx}};

        const region = regions[regionIdx];
        const collection = region.events.targetVertex.unwrap().box;
        const notes = [...collection.events.pointerHub.incoming()].map(({{box}}) => box);

        if (notes.length === 0) return {{error: "Region has no notes"}};

        // Convert to MIDI events (timeDivision=96)
        const toTicks = (position, timeDivision = 96) => Math.floor(position / PPQN.Quarter * timeDivision);
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
    safe_name = filename.replace('"', '').replace("'", "").replace('\\', '').replace('.wav', '').replace('.WAV', '')
    result = await bridge.evaluate(f"""async () => {{
        const p = window.DAW;
        const OfflineEngineRenderer = window.DAW_OfflineEngineRenderer;
        const Option = window.DAW_Option;
        const WavFile = window.DAW_WavFile;
        const PPQN = window.DAW_PPQN;

        const startPos = Math.round({start_beat} * PPQN.Quarter);
        const endPos = Math.round({end_beat} * PPQN.Quarter);

        return new Promise(async (resolve) => {{
            try {{
                // ExportConfiguration with range — no stems = full mix (1 stem)
                const exportConfig = {{
                    range: {{ start: startPos, end: endPos }}
                }};
                const progress = {{setValue: (v) => {{}}}};
                const copiedProject = p.copy();
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
    safe_name = filename.replace('"', '').replace("'", "").replace('\\', '').replace('.wav', '').replace('.WAV', '')
    result = await bridge.evaluate(f"""async () => {{
        const p = window.DAW;
        const OfflineEngineRenderer = window.DAW_OfflineEngineRenderer;
        const Option = window.DAW_Option;
        const WavFile = window.DAW_WavFile;

        return new Promise(async (resolve) => {{
            try {{
                // Option.None = no stems config → full mix (1 stem, all AUs mixed)
                const progress = {{setValue: (v) => {{}}}};
                const copiedProject = p.copy();
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
    result_temp = await bridge.evaluate(f"""() => {{
        const p = window.DAW;
        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        return units.map((au, i) => ({{
            index: i,
            uuid: window.DAW_UUID.toString(au.address.uuid),
            name: au.name?.getValue?.() || 'Unit ' + i,
            type: au.type?.getValue?.() ?? 0,
        }}));
    }}""")
    stems_map = {}
    if isinstance(result_temp, list):
        for u in result_temp:
            if u.get('type') == 1 or u.get('type') == 'instrument':
                stems_map[u['uuid']] = {
                    "includeAudioEffects": True,
                    "includeSends": True,
                    "useInstrumentOutput": True,
                    "fileName": u.get('name', f"stem_{u['index']}")
                }
    stems_js = json.dumps(stems_map)
    result = await bridge.evaluate(f"""async () => {{
        const p = window.DAW;
        const OfflineEngineRenderer = window.DAW_OfflineEngineRenderer;
        const Option = window.DAW_Option;
        const WavFile = window.DAW_WavFile;
        const stemsConfig = {stems_js};

        return new Promise(async (resolve) => {{
            try {{
                const exportConfig = {{stems: stemsConfig}};
                const progress = {{setValue: (v) => {{}}}};
                const copiedProject = p.copy();
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
            safe_prefix = filename_prefix.replace('"', '').replace("'", "").replace('\\', '').replace('.wav', '')
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
    safe_name = filename.replace('"', '').replace("'", "").replace('\\', '').replace('.wav', '').replace('.WAV', '')
    # Build per-AU stem config — ExportConfiguration.stems is Record<uuid, ExportStemConfiguration>
    result_temp = await bridge.evaluate(f"""() => {{
        const p = window.DAW;
        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box)
            .sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if ({unit_index} >= units.length) return {{error: "No AU at index {unit_index}"}};
        const au = units[{unit_index}];
        return {{
            uuid: window.DAW_UUID.toString(au.address.uuid),
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
            "useInstrumentOutput": True,
            "fileName": safe_name
        }
    }
    stems_js = json.dumps(stems_map)
    result = await bridge.evaluate(f"""async () => {{
        const p = window.DAW;
        const OfflineEngineRenderer = window.DAW_OfflineEngineRenderer;
        const Option = window.DAW_Option;
        const WavFile = window.DAW_WavFile;
        const stemsConfig = {stems_js};

        return new Promise(async (resolve) => {{
            try {{
                const exportConfig = {{stems: stemsConfig}};
                const progress = {{setValue: (v) => {{}}}};
                const copiedProject = p.copy();
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
        const p = window.DAW;
        const UUID = window.DAW_UUID;
        const PPQN = window.DAW_PPQN;
        const Quarter = PPQN.Quarter;
        const ValueEventBox = window.DAW_ValueEventBox;
        const unitIdx = {unit_index};
        const effectIdx = {effect_index};
        const paramName = "{safe_param}";
        const points = {points};

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (unitIdx >= units.length) return {{error: "No AU at " + unitIdx}};
        const au = units[unitIdx];

        const effects = [...au.audioEffects.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => a.index.getValue() - b.index.getValue());
        if (effectIdx >= effects.length) return {{error: "No effect at " + effectIdx}};
        const effectBox = effects[effectIdx];

        const field = effectBox[paramName];
        if (!field) return {{error: "No parameter '" + paramName + "' on " + effectBox.constructor.name}};

        // Create automation track targeting this parameter
        let autoTrack, valueClip, collection;
        p.editing.modify(() => {{
            autoTrack = p.api.createAutomationTrack(au, field);
            valueClip = p.api.createValueClip(autoTrack, 0, {{name: paramName}});
            // Get the event collection from the clip
            collection = valueClip.events?.targetVertex?.unwrap?.()?.box;
            if (!collection) throw new Error("No event collection on value clip");

            // Create value events (automation points)
            points.forEach(([beatPos, value], i) => {{
                ValueEventBox.create(p.boxGraph, UUID.generate(), (box) => {{
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
    result = await bridge.evaluate(f"""() => {{
        const p = window.DAW;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const clipIdx = {clip_idx};

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
        const au = units[unitIdx];

        // Find Value-type tracks (automation)
        const valueTracks = [...au.tracks.pointerHub.incoming()]
            .map(({{box}}) => box)
            .filter(t => t.type?.getValue?.() === 3);

        if (valueTracks.length === 0) return {{error: "No automation tracks on AU " + unitIdx + ". Use add_automation first."}};
        const targetTrack = trackIdx < 0 ? valueTracks[0] : (trackIdx < valueTracks.length ? valueTracks[trackIdx] : null);
        if (!targetTrack) return {{error: "No automation track at index " + trackIdx}};

        let clip;
        p.editing.modify(() => {{
            clip = p.api.createValueClip(targetTrack, clipIdx, {{name: "{safe_name}"}});
        }});

        if (!clip) return {{error: "Failed to create value clip"}};

        return {{
            success: true,
            clip_class: clip.constructor.name,
            label: clip.label?.getValue?.() ?? "",
            duration_beats: clip.duration?.getValue?.() / 960 ?? 0,
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
        const p = window.DAW;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const Quarter = 960;

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
        const au = units[unitIdx];

        // Value tracks = type 3
        let valueTracks = [...au.tracks.pointerHub.incoming()]
            .map(({{box}}) => box)
            .filter(b => b.type?.getValue?.() === 3);

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
                    const evtBoxes = [...collection.events.pointerHub.incoming()].map(({{box}}) => box);
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
        const p = window.DAW;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const Quarter = 960;

        let targetAUs;
        if (unitIdx < 0) {{
            targetAUs = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        }} else {{
            const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            targetAUs = [units[unitIdx]];
        }}

        const regionList = [];
        for (let ui = 0; ui < targetAUs.length; ui++) {{
            const au = targetAUs[ui];
            const allTracks = [...au.tracks.pointerHub.incoming()].map(({{box}}) => box);
            const valueTracks = allTracks.filter(t => t.type?.getValue?.() === 3);
            const targetTracks = trackIdx < 0 ? valueTracks : (trackIdx < valueTracks.length ? [valueTracks[trackIdx]] : []);

            for (let ti = 0; ti < targetTracks.length; ti++) {{
                const track = targetTracks[ti];
                const actualTrackIdx = valueTracks.indexOf(track);
                const regions = [...track.regions.pointerHub.incoming()].map(({{box}}) => box);
                for (let ri = 0; ri < regions.length; ri++) {{
                    const region = regions[ri];
                    regionList.push({{
                        unit_index: unitIdx < 0 ? ui : unitIdx,
                        track_index: actualTrackIdx,
                        region_index: ri,
                        position_beats: region.position?.getValue?.() / Quarter ?? 0,
                        duration_beats: region.duration?.getValue?.() / Quarter ?? 0,
                        loop_offset_beats: region.loopOffset?.getValue?.() / Quarter ?? 0,
                        loop_duration_beats: region.loopDuration?.getValue?.() / Quarter ?? 0,
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
        const p = window.DAW;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const clipIdx = {clip_index};
        const loopVal = {loop_val};
        const reverseVal = {reverse_val};
        const speedVal = {speed_val};

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
        const au = units[unitIdx];

        const allTracks = [...au.tracks.pointerHub.incoming()].map(({{box}}) => box);
        if (trackIdx >= allTracks.length) return {{error: "No track at index " + trackIdx}};
        const track = allTracks[trackIdx];

        const clips = [...track.clips?.pointerHub?.incoming?.() ?? []].map(({{box}}) => box);
        if (clipIdx >= clips.length) return {{error: "No clip at index " + clipIdx}};
        const clip = clips[clipIdx];

        if (!clip.triggerMode) return {{error: "Clip has no triggerMode"}};

        p.editing.modify(() => {{
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
        const p = window.DAW;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const clipIdx = {clip_index};
        const Quarter = 960;
        const hueVal = {hue};
        const muteVal = {mute_val};
        const durVal = {duration_beats};
        const labelVal = {label_val};

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
        const au = units[unitIdx];

        const allTracks = [...au.tracks.pointerHub.incoming()].map(({{box}}) => box);
        if (trackIdx >= allTracks.length) return {{error: "No track at index " + trackIdx}};
        const track = allTracks[trackIdx];

        const clips = [...track.clips?.pointerHub?.incoming?.() ?? []].map(({{box}}) => box);
        if (clipIdx >= clips.length) return {{error: "No clip at index " + clipIdx}};
        const clip = clips[clipIdx];

        p.editing.modify(() => {{
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
            duration_beats: clip.duration?.getValue?.() / Quarter ?? 0,
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
        const p = window.DAW;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const clipIdx = {clip_index};

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
        const au = units[unitIdx];

        const allTracks = [...au.tracks.pointerHub.incoming()].map(({{box}}) => box);
        if (trackIdx >= allTracks.length) return {{error: "No track at index " + trackIdx}};
        const track = allTracks[trackIdx];

        const clips = [...track.clips?.pointerHub?.incoming?.() ?? []].map(({{box}}) => box);
        if (clipIdx >= clips.length) return {{error: "No clip at index " + clipIdx}};

        p.editing.modify(() => {{
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
        const p = window.DAW;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const Quarter = 960;

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
        const au = units[unitIdx];

        const allTracks = [...au.tracks.pointerHub.incoming()].map(({{box}}) => box);
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
                    duration_beats: clip.duration?.getValue?.() / Quarter ?? 0,
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
        const p = window.DAW;
        const srcIdx = {source_unit_index};
        const tgtIdx = {target_unit_index};
        const effIdx = {effect_index};

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (srcIdx >= units.length) return {{error: "No source AU at " + srcIdx}};
        if (tgtIdx >= units.length) return {{error: "No target AU at " + tgtIdx}};
        const sourceAU = units[srcIdx];
        const targetAU = units[tgtIdx];

        const effects = [...targetAU.audioEffects.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => a.index.getValue() - b.index.getValue());
        if (effIdx >= effects.length) return {{error: "No effect at " + effIdx}};
        const effectBox = effects[effIdx];

        if (!effectBox.sideChain || typeof effectBox.sideChain.refer !== 'function') {{
            return {{error: effectBox.constructor.name + " has no sideChain input"}};
        }}

        p.editing.modify(() => {{
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
    result = await bridge.evaluate(f"""() => {{
        const p = window.DAW;
        let deleted = 0;
        p.editing.modify(() => {{
            const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
            // Delete all instrument AUs (keep output AU at index 0)
            for (let i = units.length - 1; i >= 1; i--) {{
                try {{ units[i].delete(); deleted++; }} catch(e) {{}}
            }}
            // Delete all effects on output AU
            const outputAU = units[0];
            if (outputAU) {{
                const effects = [...outputAU.audioEffects.pointerHub.incoming()].map(({{box}}) => box);
                for (const eff of effects) {{
                    try {{ eff.delete(); deleted++; }} catch(e) {{}}
                }}
            }}
        }});
        return {{
            success: true,
            deleted_boxes: deleted,
            remaining_units: [...p.rootBox.audioUnits.pointerHub.incoming()].length,
        }};
    }}""")
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
    result = await bridge.evaluate(f"""() => {{
        const p = window.DAW;
        try {{
            const buffer = p.toArrayBuffer();
            const bytes = new Uint8Array(buffer);
            let binary = "";
            for (let i = 0; i < bytes.length; i++) {{
                binary += String.fromCharCode(bytes[i]);
            }}
            const b64 = btoa(binary);
            window.__lastProjectB64 = b64;
            window.__lastProjectSize = bytes.length;
            return {{
                success: true,
                size_bytes: bytes.length,
                boxes: p.boxGraph.boxes().length,
            }};
        }} catch(e) {{
            return {{error: String(e)}};
        }}
    }}""")
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
        const p = window.DAW;
        const unitIdx = {unit_index};
        const effectIdx = {effect_index};
        const enabled = {json.dumps(enabled)};

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (unitIdx >= units.length) return {{error: "No AU at " + unitIdx}};
        const au = units[unitIdx];
        const effects = [...au.audioEffects.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => a.index.getValue() - b.index.getValue());
        if (effectIdx >= effects.length) return {{error: "No effect at " + effectIdx}};
        const effectBox = effects[effectIdx];

        const oldVal = effectBox.enabled?.getValue?.();
        p.editing.modify(() => {{
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
    result = await bridge.evaluate(f"""() => {{
        const p = window.DAW;
        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        const result = units.map((au, i) => {{
            const tracks = [...au.tracks.pointerHub.incoming()].map(({{box}}) => {{
                const typeVal = box.type?.getValue?.() ?? -1;
                const typeName = typeVal === 0 ? 'undefined' : typeVal === 1 ? 'note' : typeVal === 2 ? 'audio' : typeVal === 3 ? 'automation' : 'unknown:' + typeVal;
                const regions = box.regions ? [...box.regions.pointerHub.incoming()].length : 0;
                const clips = box.clips ? [...box.clips.pointerHub.incoming()].length : 0;
                return {{type: typeName, regions, clips}};
            }});
            const effects = [...au.audioEffects.pointerHub.incoming()].map(({{box}}) => ({{
                type: box.constructor?.name || 'Unknown',
                enabled: box.enabled?.getValue?.() ?? true,
            }})).sort((a, b) => 0); // keep insertion order
            return {{
                index: i,
                name: au.name?.getValue?.() || ('Unit ' + i),
                type: au.type?.getValue?.() || 'unknown',
                volume_raw: au.volume?.getValue?.() ?? 0,
                panning: au.panning?.getValue?.() ?? 0,
                mute: au.mute?.getValue?.() ?? false,
                solo: au.solo?.getValue?.() ?? false,
                tracks,
                effects,
            }};
        }});
        return {{success: true, units: result, total_units: result.length}};
    }}""")
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
    import math
    import struct
    import os as _os

    export_dir = _os.environ.get("OPENDAW_EXPORT_DIR",
                                  _os.path.join(_os.path.dirname(__file__), "exports"))
    filepath = _os.path.join(export_dir, filename if filename.endswith(".wav") else filename + ".wav")

    if not _os.path.exists(filepath):
        return _err(f"File not found: {filepath}")

    try:
        # Parse WAV header manually — openDAW exports 32-bit float WAVs
        # which Python's wave module doesn't support (format code 3)
        with open(filepath, "rb") as f:
            raw = f.read()

        # Parse RIFF header
        if raw[:4] != b"RIFF" or raw[8:12] != b"WAVE":
            return _err("Not a valid WAV file")
        pos = 12
        n_channels = sample_rate = n_frames = 0
        bits_per_sample = 16
        audio_format = 1  # 1=PCM, 3=float32
        audio_data = b""
        while pos < len(raw) - 8:
            chunk_id = raw[pos:pos+4]
            chunk_size = struct.unpack_from("<I", raw, pos+4)[0]
            if chunk_id == b"fmt ":
                audio_format = struct.unpack_from("<H", raw, pos+8)[0]
                n_channels = struct.unpack_from("<H", raw, pos+10)[0]
                sample_rate = struct.unpack_from("<I", raw, pos+12)[0]
                bits_per_sample = struct.unpack_from("<H", raw, pos+22)[0]
            elif chunk_id == b"data":
                audio_data = raw[pos+8:pos+8+chunk_size]
                bytes_per_sample = bits_per_sample // 8
                n_frames = chunk_size // (bytes_per_sample * n_channels)
            pos += 8 + chunk_size + (chunk_size % 2)  # pad to even

        if not audio_data:
            return _err("No data chunk in WAV")

        # Convert to float samples based on format
        if audio_format == 3 and bits_per_sample == 32:
            # 32-bit float
            fmt = f"<{n_frames * n_channels}f"
            samples = list(struct.unpack(fmt, audio_data))
        elif audio_format == 1 and bits_per_sample == 16:
            fmt = f"<{n_frames * n_channels}h"
            samples = struct.unpack(fmt, audio_data)
            samples = [s / 32768.0 for s in samples]
        elif audio_format == 1 and bits_per_sample == 24:
            samples = []
            for i in range(0, len(audio_data), 3):
                val = int.from_bytes(audio_data[i:i+3], byteorder="little", signed=True)
                samples.append(val / 8388608.0)
        elif audio_format == 1 and bits_per_sample == 32:
            fmt = f"<{n_frames * n_channels}i"
            samples = struct.unpack(fmt, audio_data)
            samples = [s / 2147483648.0 for s in samples]
        else:
            return _err(f"Unsupported WAV format: {audio_format}/{bits_per_sample}bit")

        duration_sec = n_frames / sample_rate

        # De-interleave channels
        channels = [[] for _ in range(n_channels)]
        for i, s in enumerate(samples):
            channels[i % n_channels].append(s)

        # ITU-R BS.1770 K-weighting filter coefficients
        # Stage 1: high-shelf biquad (pre-filter)
        # Stage 2: high-pass biquad (RLB)
        # Coefficients for 48kHz from BS.1770-4 Annex
        # Note: using normalized form where b0 is the gain factor
        if sample_rate == 48000:
            # Shelf filter (pre-filter): +4dB high shelf
            f0 = 1681.974450955533
            G = 3.9998432737
            Q = 0.7081754356
            K = math.tan(math.pi * f0 / sample_rate)
            Vh = 10 ** (G / 20.0)
            Vb = 10 ** (G / 40.0)
            a0_ = 1.0 + K / Q + K * K
            s_b0 = (Vh + Vb * K / Q + K * K) / a0_
            s_b1 = 2.0 * (K * K - Vh) / a0_
            s_b2 = (Vh - Vb * K / Q + K * K) / a0_
            s_a0 = 1.0
            s_a1 = 2.0 * (K * K - 1.0) / a0_
            s_a2 = (1.0 - K / Q + K * K) / a0_
            # RLB (highpass): ~38Hz
            f0r = 38.1354708761
            Qr = 0.5003270373
            Kr = math.tan(math.pi * f0r / sample_rate)
            ar0 = 1.0 + Kr / Qr + Kr * Kr
            r_b0 = 1.0 / ar0
            r_b1 = -2.0 / ar0
            r_b2 = 1.0 / ar0
            r_a0 = 1.0
            r_a1 = 2.0 * (Kr * Kr - 1.0) / ar0
            r_a2 = (1.0 - Kr / Qr + Kr * Kr) / ar0
        else:
            # For 44100 — recompute with actual sample_rate
            f0 = 1681.974450955533
            G = 3.9998432737
            Q = 0.7081754356
            K = math.tan(math.pi * f0 / sample_rate)
            Vh = 10 ** (G / 20.0)
            Vb = 10 ** (G / 40.0)
            a0_ = 1.0 + K / Q + K * K
            s_b0 = (Vh + Vb * K / Q + K * K) / a0_
            s_b1 = 2.0 * (K * K - Vh) / a0_
            s_b2 = (Vh - Vb * K / Q + K * K) / a0_
            s_a0 = 1.0
            s_a1 = 2.0 * (K * K - 1.0) / a0_
            s_a2 = (1.0 - K / Q + K * K) / a0_
            f0r = 38.1354708761
            Qr = 0.5003270373
            Kr = math.tan(math.pi * f0r / sample_rate)
            ar0 = 1.0 + Kr / Qr + Kr * Kr
            r_b0 = 1.0 / ar0
            r_b1 = -2.0 / ar0
            r_b2 = 1.0 / ar0
            r_a0 = 1.0
            r_a1 = 2.0 * (Kr * Kr - 1.0) / ar0
            r_a2 = (1.0 - Kr / Qr + Kr * Kr) / ar0

        def apply_biquad(data, b0, b1, b2, a0, a1, a2):
            # Normalize by a0
            b0n, b1n, b2n = b0/a0, b1/a0, b2/a0
            a1n, a2n = a1/a0, a2/a0
            out = [0.0] * len(data)
            x1 = x2 = y1 = y2 = 0.0
            for i in range(len(data)):
                x = data[i]
                y = b0n * x + b1n * x1 + b2n * x2 - a1n * y1 - a2n * y2
                out[i] = y
                x2 = x1; x1 = x
                y2 = y1; y1 = y
            return out

        # Apply K-weighting to each channel
        k_weighted = []
        for ch in channels:
            stage1 = apply_biquad(ch, s_b0, s_b1, s_b2, s_a0, s_a1, s_a2)
            stage2 = apply_biquad(stage1, r_b0, r_b1, r_b2, r_a0, r_a1, r_a2)
            k_weighted.append(stage2)

        # Gated mean squares: 400ms blocks, 75% overlap
        block_size = int(0.4 * sample_rate)
        hop_size = int(0.1 * sample_rate)  # 75% overlap
        if block_size == 0 or hop_size == 0:
            return _err(f"Sample rate too low: {sample_rate}")

        # Channel weights (L/R/C = 1.0, surround = 1.41)
        ch_weights = [1.0] * n_channels
        if n_channels > 2:
            for i in range(2, n_channels):
                ch_weights[i] = 1.41

        blocks_ms = []
        pos = 0
        while pos + block_size <= n_frames:
            block_ms = 0.0
            for ch_idx in range(n_channels):
                ch_data = k_weighted[ch_idx][pos:pos + block_size]
                ms = sum(s * s for s in ch_data) / block_size
                block_ms += ch_weights[ch_idx] * ms
            blocks_ms.append(block_ms)
            pos += hop_size

        if not blocks_ms:
            return _err("Not enough samples for LUFS measurement")

        # Absolute gate: -70 LUFS
        abs_gate_lufs = -70.0
        abs_gate_ms = 10 ** ((abs_gate_lufs + 0.691) / 10.0)

        gated_blocks = [ms for ms in blocks_ms if ms > abs_gate_ms]
        if not gated_blocks:
            return _err("All blocks below absolute gate (-70 LUFS)")

        # Relative gate: -10 LU below mean of absolutely-gated blocks
        mean_ms = sum(gated_blocks) / len(gated_blocks)
        rel_gate_ms = 10 ** ((10 * math.log10(mean_ms) - 0.691 - 10) / 10.0)

        rel_gated = [ms for ms in gated_blocks if ms > rel_gate_ms]
        if not rel_gated:
            # Use absolutely-gated mean as fallback
            final_ms = mean_ms
        else:
            final_ms = sum(rel_gated) / len(rel_gated)

        lufs = -0.691 + 10 * math.log10(final_ms)

        # True peak: max absolute sample across all channels
        max_sample = max(max(abs(s) for s in ch) for ch in channels)
        true_peak_db = 20 * math.log10(max_sample) if max_sample > 0 else -float("inf")

        return json.dumps({
            "success": True,
            "lufs_integrated": round(lufs, 1),
            "true_peak_db": round(true_peak_db, 2),
            "max_sample": round(max_sample, 6),
            "duration_seconds": round(duration_sec, 2),
            "sample_rate": sample_rate,
            "channels": n_channels,
            "blocks_measured": len(blocks_ms),
            "gated_blocks": len(gated_blocks),
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
    safe_name = filename.replace('"', '').replace("'", "").replace('\\', '').replace('.wav', '')

    # Step 1: Ensure Maximizer on output AU
    maxi_result = await bridge.evaluate(f"""() => {{
        const p = window.DAW;
        const ef = window.DAW_EffectFactories;
        const api = p.api;
        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        const au = units[0]; // output AU

        const existing = [...au.audioEffects.pointerHub.incoming()].map(({{box}}) => box);
        let maxiBox = existing.find(b => b.constructor.name === "MaximizerDeviceBox");

        if (!maxiBox) {{
            p.editing.modify(() => {{
                maxiBox = api.insertEffect(au.audioEffects, ef.AudioNamed["Maximizer"]);
            }});
        }}
        return {{
            maximizer_added: !existing.some(b => b.constructor.name === "MaximizerDeviceBox"),
            has_lookahead: !!maxiBox?.lookahead
        }};
    }}""")
    if isinstance(maxi_result, dict) and "error" in maxi_result:
        return _wrap_eval(maxi_result)

    iterations = []
    current_threshold = max(-24.0, target - 6.0)  # start slightly below target
    current_volume_db = 0.0  # output AU volume in dB

    for i in range(max_iter):
        # Set Maximizer threshold + output AU volume
        await bridge.evaluate(f"""() => {{
            const p = window.DAW;
            const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
            const au = units[0]; // output AU
            const maxi = [...au.audioEffects.pointerHub.incoming()].map(({{box}}) => box).find(b => b.constructor.name === "MaximizerDeviceBox");
            if (!maxi) return {{error: "No Maximizer"}};
            p.editing.modify(() => {{
                maxi.threshold.setValue({current_threshold});
                if (maxi.lookahead) maxi.lookahead.setValue(true);
                // Output AU volume — field stores dB directly (min -96, max +6)
                au.volume.setValue({current_volume_db});
            }});
            return {{threshold: {current_threshold}, volume_db: {current_volume_db}}};
        }}""")

        # Render full mix
        render_result = await bridge.evaluate(f"""async () => {{
            const p = window.DAW;
            const OfflineEngineRenderer = window.DAW_OfflineEngineRenderer;
            const Option = window.DAW_Option;
            const WavFile = window.DAW_WavFile;
            return new Promise(async (resolve) => {{
                try {{
                    const progress = {{setValue: (v) => {{}}}};
                    const copied = p.copy();
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
    result = await bridge.evaluate(f"""() => {{
        const p = window.DAW;
        if (p.editing.canUndo) {{
            p.editing.undo();
            return {{success: true, action: "undo"}};
        }}
        return {{success: false, message: "Nothing to undo"}};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_redo() -> str:
    """Redo the last undone operation."""
    result = await bridge.evaluate(f"""() => {{
        const p = window.DAW;
        if (p.editing.canRedo) {{
            p.editing.redo();
            return {{success: true, action: "redo"}};
        }}
        return {{success: false, message: "Nothing to redo"}};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_serialize() -> str:
    """Serialize the current project state to JSON. Returns the serialized project data."""
    result = await bridge.evaluate(f"""() => {{
        const p = window.DAW;
        const json = p.boxGraph.toJSON();
        return {{
            success: true,
            data: json,
            box_count: [...p.boxGraph.boxes()].length,
        }};
    }}""")
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
    
    safe_transient_mode = transient_mode.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const p = window.DAW;
        const UUID = window.DAW_UUID;
        const PPQN = window.DAW_PPQN;
        const Quarter = PPQN.Quarter;
        const AudioFileBox = window.DAW_AudioFileBox;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const sampleId = "{safe_sample_id}";
        const startBeat = {start_beat};
        const playbackRate = {playback_rate};
        const transientMode = {mode_val};
        const sampleBpm = {bpm};

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
        const au = units[unitIdx];

        const audioTracks = [...au.tracks.pointerHub.incoming()]
            .map(({{box}}) => box)
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
        p.editing.modify(() => {{
            audioFileBox = AudioFileBox.create(p.boxGraph, UUID.generate(), (box) => {{
                box.fileName.setValue(sampleId);
                box.startInSeconds.setValue(0.0);
                box.endInSeconds.setValue(audioBuffer.duration);
            }});

            regionBox = p.api.createTimeStretchedRegion({{
                boxGraph: p.boxGraph,
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
        const p = window.DAW;
        const UUID = window.DAW_UUID;
        const PPQN = window.DAW_PPQN;
        const Quarter = PPQN.Quarter;
        const AudioFileBox = window.DAW_AudioFileBox;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const sampleId = "{safe_sample_id}";
        const startBeat = {start_beat};
        const sampleBpm = {bpm};

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
        const au = units[unitIdx];

        const audioTracks = [...au.tracks.pointerHub.incoming()]
            .map(({{box}}) => box)
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
        p.editing.modify(() => {{
            audioFileBox = AudioFileBox.create(p.boxGraph, UUID.generate(), (box) => {{
                box.fileName.setValue(sampleId);
                box.startInSeconds.setValue(0.0);
                box.endInSeconds.setValue(audioBuffer.duration);
            }});

            regionBox = p.api.createPitchStretchedRegion({{
                boxGraph: p.boxGraph,
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
        const p = window.DAW;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const findFree = {json.dumps(find_free_space)};

        // Find the track
        let tracks = [];
        if (unitIdx < 0) {{
            const allUnits = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
            for (const au of allUnits) {{
                tracks.push(...[...au.tracks.pointerHub.incoming()].map(({{box}}) => box));
            }}
        }} else {{
            const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            tracks = [...units[unitIdx].tracks.pointerHub.incoming()].map(({{box}}) => box);
        }}

        if (trackIdx >= tracks.length) return {{error: "No track at index " + trackIdx}};
        const trackBox = tracks[trackIdx];

        const regions = [...trackBox.regions.pointerHub.incoming()].map(({{box}}) => box);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx}};
        const srcRegion = regions[regionIdx];

        // Get the adapter for this region via TrackBoxAdapter.regions.collection
        const TrackBoxAdapter = window.DAW_TrackBoxAdapter;
        const trackAdapter = p.boxAdapters.adapterFor(trackBox, TrackBoxAdapter);
        const regionAdapters = trackAdapter.regions.collection.asArray();
        if (regionIdx >= regionAdapters.length) return {{error: "No region adapter at index " + regionIdx}};
        const regionAdapter = regionAdapters[regionIdx];

        let result2;
        p.editing.modify(() => {{
            const opt = p.api.duplicateRegion(regionAdapter, {{findFreeSpace: findFree}});
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
        const p = window.DAW;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const clipIdx = {clip_index};
        const clipName = "{safe_name}";
        const clipHue = {hue};

        // Find note track
        let noteTracks = [];
        if (unitIdx < 0) {{
            const allUnits = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
            for (const au of allUnits) {{
                noteTracks.push(...[...au.tracks.pointerHub.incoming()]
                    .map(({{box}}) => box)
                    .filter(box => box.type?.getValue?.() === 1));
            }}
        }} else {{
            const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            noteTracks = [...units[unitIdx].tracks.pointerHub.incoming()]
                .map(({{box}}) => box)
                .filter(box => box.type?.getValue?.() === 1);
        }}

        if (trackIdx >= noteTracks.length) return {{error: "No note track at index " + trackIdx}};
        const trackBox = noteTracks[trackIdx];

        let clipBox;
        p.editing.modify(() => {{
            const opts = {{name: clipName}};
            if (clipHue >= 0) opts.hue = clipHue;
            clipBox = p.api.createNoteClip(trackBox, clipIdx, opts);
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
        const p = window.DAW;
        const PPQN = window.DAW_PPQN;
        const Quarter = PPQN.Quarter;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const startBeat = {start_beat};
        const durBeats = {duration_beats};
        const regionName = "{safe_name}";
        const regionHue = {hue};

        let tracks = [];
        if (unitIdx < 0) {{
            for (const au of [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box)) {{
                tracks.push(...[...au.tracks.pointerHub.incoming()].map(({{box}}) => box));
            }}
        }} else {{
            const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            tracks = [...units[unitIdx].tracks.pointerHub.incoming()].map(({{box}}) => box);
        }}

        if (trackIdx >= tracks.length) return {{error: "No track at index " + trackIdx}};
        const trackBox = tracks[trackIdx];
        const trackType = trackBox.type.getValue();

        let regionBox;
        p.editing.modify(() => {{
            const opts = {{}};
            if (regionName) opts.name = regionName;
            if (regionHue >= 0) opts.hue = regionHue;
            const opt = p.api.createTrackRegion(trackBox, Math.round(startBeat * Quarter), Math.round(durBeats * Quarter), opts);
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
        const p = window.DAW;
        const UUID = window.DAW_UUID;
        const AudioFileBox = window.DAW_AudioFileBox;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const clipIdx = {clip_index};
        const sampleId = "{safe_sample_id}";
        const sampleBpm = {bpm};

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
        const au = units[unitIdx];

        const audioTracks = [...au.tracks.pointerHub.incoming()]
            .map(({{box}}) => box)
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
        p.editing.modify(() => {{
            const audioFileBox = AudioFileBox.create(p.boxGraph, UUID.generate(), (box) => {{
                box.fileName.setValue(sampleId);
                box.startInSeconds.setValue(0.0);
                box.endInSeconds.setValue(audioBuffer.duration);
            }});

            clipBox = p.api.createNotStretchedClip({{
                boxGraph: p.boxGraph,
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
        const p = window.DAW;
        const UUID = window.DAW_UUID;
        const AudioFileBox = window.DAW_AudioFileBox;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const clipIdx = {clip_index};
        const sampleId = "{safe_sample_id}";
        const sampleBpm = {bpm};
        const rate = {playback_rate};
        const modeName = "{safe_mode}";

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
        const au = units[unitIdx];

        const audioTracks = [...au.tracks.pointerHub.incoming()].map(({{box}}) => box).filter(box => box.type?.getValue?.() === 2);
        if (trackIdx >= audioTracks.length) return {{error: "No audio track at index " + trackIdx}};
        const trackBox = audioTracks[trackIdx];

        const audioBuffer = window.DAW_localAudioBuffers.get(sampleId);
        if (!audioBuffer) return {{error: "Sample not loaded: " + sampleId}};

        const sample = {{name: sampleId, duration: audioBuffer.duration, bpm: sampleBpm, sample_rate: audioBuffer.sampleRate}};

        const TransientPlayMode = {{Pingpong: 0, Monoton: 1, Cycles: 2, Plode: 3}};
        const tMode = TransientPlayMode[modeName] ?? 0;

        let clipBox;
        p.editing.modify(() => {{
            const audioFileBox = AudioFileBox.create(p.boxGraph, UUID.generate(), (box) => {{
                box.fileName.setValue(sampleId);
                box.startInSeconds.setValue(0.0);
                box.endInSeconds.setValue(audioBuffer.duration);
            }});

            clipBox = p.api.createTimeStretchedClip({{
                boxGraph: p.boxGraph,
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
        const p = window.DAW;
        const UUID = window.DAW_UUID;
        const AudioFileBox = window.DAW_AudioFileBox;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const clipIdx = {clip_index};
        const sampleId = "{safe_sample_id}";
        const sampleBpm = {bpm};

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
        const au = units[unitIdx];

        const audioTracks = [...au.tracks.pointerHub.incoming()].map(({{box}}) => box).filter(box => box.type?.getValue?.() === 2);
        if (trackIdx >= audioTracks.length) return {{error: "No audio track at index " + trackIdx}};
        const trackBox = audioTracks[trackIdx];

        const audioBuffer = window.DAW_localAudioBuffers.get(sampleId);
        if (!audioBuffer) return {{error: "Sample not loaded: " + sampleId}};

        const sample = {{name: sampleId, duration: audioBuffer.duration, bpm: sampleBpm, sample_rate: audioBuffer.sampleRate}};

        let clipBox;
        p.editing.modify(() => {{
            const audioFileBox = AudioFileBox.create(p.boxGraph, UUID.generate(), (box) => {{
                box.fileName.setValue(sampleId);
                box.startInSeconds.setValue(0.0);
                box.endInSeconds.setValue(audioBuffer.duration);
            }});

            clipBox = p.api.createPitchStretchedClip({{
                boxGraph: p.boxGraph,
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

The code must start with a header line:
  // @apparat <name> <version> <update>
  // @werkstatt <name> <version> <update>
  // @spielwerk <name> <version> <update>

The code defines a `Processor` class that the host instantiates in the audio worklet.
@param declarations create parameters: // @param <name> <default> <min> <max> [type] [unit]
@sample declarations create sample slots: // @sample <name>
See the openDAW plans/apparat.md, plans/spielwerk.md for the full API.

device_type: "apparat" (instrument), "werkstatt" (audio effect), "spielwerk" (MIDI effect)
"""
    code_json = json.dumps(code)
    

    safe_device_type = device_type.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(rf"""async () => {{
        const p = window.DAW;
        const allAU = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        const au = allAU[{unit_index}];
        if (!au) return {{error: "Unit {unit_index} not found"}};
        let device = null;
        const dt = "{safe_device_type}".toLowerCase();
        if (dt === "werkstatt") {{
            const fx = [...au.audioEffects.pointerHub.incoming()].map(({{box}}) => box);
            device = fx[{device_index}] || null;
        }} else if (dt === "spielwerk") {{
            const me = au.midiEffects ? [...au.midiEffects.pointerHub.incoming()].map(({{box}}) => box) : [];
            device = me[{device_index}] || null;
        }} else if (dt === "apparat") {{
            const incoming = au.input ? [...au.input.pointerHub.incoming()].map(({{box}}) => box) : [];
            device = incoming.find(b => b.constructor.name === "ApparatDeviceBox") || incoming[0] || null;
        }}
        if (!device) return {{error: "Scriptable device '" + dt + "' not found on unit {unit_index}"}};
        const boxGraph = device.graph;
        const UUID = window.DAW_UUID;
        const headerTag = "{safe_device_type}".toLowerCase();
        const headerPattern = new RegExp('^// @' + headerTag + ' \w+ \d+ \d+\\n');
        const source = {code_json};
        const headerMatch = source.match(headerPattern);
        const userCode = headerMatch ? source.slice(headerMatch[0].length) : source;

        // Parse @param declarations
        const paramRegex = /^\/\/ @param .+$/gm;
        const params = [];
        let m;
        while ((m = paramRegex.exec(userCode)) !== null) {{
            const tokens = m[0].replace(/^\/\/ @param\s+/, '').replace(/\s+\/\/.*$/, '').trim().split(/\s+/);
            if (tokens.length === 0) continue;
            const label = tokens[0];
            let defaultValue = 0, min = 0, max = 1, mapping = 'unipolar', unit = '';
            if (tokens.length >= 2) {{
                const second = tokens[1];
                if (second === 'true' || second === 'false') {{
                    defaultValue = second === 'true' ? 1 : 0; mapping = 'bool';
                }} else if (second === 'bool') {{
                    mapping = 'bool';
                }} else {{
                    defaultValue = parseFloat(second);
                    if (tokens.length >= 4) {{
                        min = parseFloat(tokens[2]); max = parseFloat(tokens[3]);
                        mapping = tokens.length >= 5 ? tokens[4] : 'linear';
                        unit = tokens.length >= 6 ? tokens[5] : '';
                    }}
                }}
            }}
            params.push({{label, defaultValue, min, max, mapping, unit}});
        }}

        // Parse @sample declarations
        const sampleRegex = /^\/\/ @sample .+$/gm;
        const samples = [];
        while ((m = sampleRegex.exec(userCode)) !== null) {{
            const tokens = m[0].replace(/^\/\/ @sample\s+/, '').replace(/\s+\/\/.*$/, '').trim().split(/\s+/);
            if (tokens.length > 0) samples.push({{label: tokens[0]}});
        }}

        // Parse declaration order
        const declRegex = /^\/\/ @(?:param|sample) \S+/gm;
        const order = new Map();
        let idx = 0;
        while ((m = declRegex.exec(userCode)) !== null) {{
            const label = m[0].replace(/^\/\/ @(?:param|sample)\s+/, '').split(/\s+/)[0];
            if (!order.has(label)) order.set(label, idx++);
        }}

        // Compute new update number BEFORE editing.modify (needed for worklet registration outside)
        const currentCode0 = device.code.getValue();
        const currentUpdateMatch0 = currentCode0.match(headerPattern);
        const currentUpdate0 = currentUpdateMatch0 ? parseInt(currentUpdateMatch0[3]) : 0;
        const newUpdate = currentUpdate0 + 1;

        // ALL mutations inside ONE editing.modify() block
        const createdParams = [];
        const createdSamples = [];

        p.editing.modify(() => {{
            // Reconcile parameters
            const existingParamMap = new Map();
            for (const pointer of device.parameters.pointerHub.filter()) {{
                existingParamMap.set(pointer.box.label.getValue(), pointer.box);
            }}
            const seenParamLabels = new Set(params.map(p => p.label));
            for (const [label, pb] of existingParamMap) {{
                if (!seenParamLabels.has(label)) pb.delete();
            }}
            for (const decl of params) {{
                const existing = existingParamMap.get(decl.label);
                if (existing) {{
                    const expectedIdx = order.get(decl.label) ?? 0;
                    if (existing.index.getValue() !== expectedIdx) existing.index.setValue(expectedIdx);
                    createdParams.push({{label: decl.label, index: existing.index.getValue(), value: existing.value.getValue(), defaultValue: existing.defaultValue.getValue()}});
                }} else if (window.DAW_WerkstattParameterBox) {{
                    const pb = window.DAW_WerkstattParameterBox.create(boxGraph, UUID.generate());
                    pb.owner.refer(device.parameters);
                    pb.label.setValue(decl.label);
                    pb.index.setValue(order.get(decl.label) ?? 0);
                    pb.value.setValue(decl.defaultValue);
                    pb.defaultValue.setValue(decl.defaultValue);
                    createdParams.push({{label: decl.label, index: pb.index.getValue(), value: pb.value.getValue(), defaultValue: pb.defaultValue.getValue()}});
                }}
            }}

            // Reconcile samples
            if (device.samples) {{
                const existingSampleMap = new Map();
                for (const pointer of device.samples.pointerHub.filter()) {{
                    existingSampleMap.set(pointer.box.label.getValue(), pointer.box);
                }}
                const seenSampleLabels = new Set(samples.map(s => s.label));
                for (const [label, sb] of existingSampleMap) {{
                    if (!seenSampleLabels.has(label)) sb.delete();
                }}
                for (const decl of samples) {{
                    const existing = existingSampleMap.get(decl.label);
                    if (existing) {{
                        createdSamples.push({{label: decl.label, index: existing.index.getValue()}});
                    }} else if (window.DAW_WerkstattSampleBox) {{
                        const sb = window.DAW_WerkstattSampleBox.create(boxGraph, UUID.generate());
                        sb.owner.refer(device.samples);
                        sb.label.setValue(decl.label);
                        sb.index.setValue(order.get(decl.label) ?? 0);
                        createdSamples.push({{label: decl.label, index: sb.index.getValue()}});
                    }}
                }}
            }}

            // Set code with proper header
            const header = '// @' + headerTag + ' js 1 ' + newUpdate + '\\\\n';
            const fullCode = headerMatch ? source : (header + source);
            device.code.setValue(fullCode);
        }});

        // Try worklet registration (optional, non-fatal)
        let workletRegistered = false;
        let workletError = null;
        try {{
            const ctx = window.DAW_audioContext || (window.AudioContext ? new AudioContext() : null);
            if (ctx) {{
                const uuid = UUID.toString(device.address.uuid);
                const registryName = headerTag + 'Processors';
                const fnName = headerTag;
                const wrappedCode = 'if (typeof globalThis.openDAW === "undefined") {{ globalThis.openDAW = {{}} }} if (typeof globalThis.openDAW.' + registryName + ' === "undefined") {{ globalThis.openDAW.' + registryName + ' = {{}} }} globalThis.openDAW.' + registryName + '["' + uuid + '"] = {{ update: ' + newUpdate + ', create: (function ' + fnName + '() {{ ' + userCode + ' return Processor; }})() }}';
                new Function(wrappedCode);
                const blob = new Blob([wrappedCode], {{type: 'application/javascript'}});
                const blobUrl = URL.createObjectURL(blob);
                await ctx.audioWorklet.addModule(blobUrl);
                URL.revokeObjectURL(blobUrl);
                workletRegistered = true;
            }}
        }} catch(e) {{
            workletError = e.message.substring(0, 200);
        }}

        return {{
            success: true,
            device: device.constructor.name,
            code_length: device.code.getValue().length,
            params_created: createdParams.length,
            params: createdParams,
            samples_created: createdSamples.length,
            samples: createdSamples,
            worklet_registered: workletRegistered,
            worklet_error: workletError,
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
        const p = window.DAW;
        const allAU = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        const au = allAU[{unit_index}];
        if (!au) return {{error: "Unit {unit_index} not found"}};
        let device = null;
        const dt = "{safe_device_type}".toLowerCase();
        if (dt === "werkstatt") {{
            const fx = [...au.audioEffects.pointerHub.incoming()].map(({{box}}) => box);
            device = fx[{device_index}] || null;
        }} else if (dt === "spielwerk") {{
            const me = au.midiEffects ? [...au.midiEffects.pointerHub.incoming()].map(({{box}}) => box) : [];
            device = me[{device_index}] || null;
        }} else if (dt === "apparat") {{
            const incoming = au.input ? [...au.input.pointerHub.incoming()].map(({{box}}) => box) : [];
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
    """List @param declarations on a scriptable device.

Each parameter is a WerkstattParameterBox with: label, index, value, defaultValue.
Parameters are auto-created from `// @param <name> <min> <max> <default> <scaling> <unit>`
declarations in the code. They appear after the code is compiled and loaded.
"""
    safe_device_type = device_type.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const p = window.DAW;
        const allAU = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        const au = allAU[{unit_index}];
        if (!au) return {{error: "Unit {unit_index} not found"}};
        let device = null;
        const dt = "{safe_device_type}".toLowerCase();
        if (dt === "werkstatt") {{
            const fx = [...au.audioEffects.pointerHub.incoming()].map(({{box}}) => box);
            device = fx[{device_index}] || null;
        }} else if (dt === "spielwerk") {{
            const me = au.midiEffects ? [...au.midiEffects.pointerHub.incoming()].map(({{box}}) => box) : [];
            device = me[{device_index}] || null;
        }} else if (dt === "apparat") {{
            const incoming = au.input ? [...au.input.pointerHub.incoming()].map(({{box}}) => box) : [];
            device = incoming.find(b => b.constructor.name === "ApparatDeviceBox") || incoming[0] || null;
        }}
        if (!device) return {{error: "Scriptable device '" + dt + "' not found on unit {unit_index}"}};
        if (!device.parameters) return {{error: "Device has no parameters field"}};
        const params = [...device.parameters.pointerHub.incoming()].map(({{box}}) => box);
        return {{
            success: true,
            device: device.constructor.name,
            params: params.map(param => ({{
                label: param.label.getValue(),
                index: param.index.getValue(),
                value: param.value.getValue(),
                defaultValue: param.defaultValue.getValue(),
            }})),
            param_count: params.length,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_set_script_param(device_type: str, unit_index: int, device_index: int, param_label: str, value: float) -> str:
    """Set a parameter value on a scriptable device by label.

The parameter must exist (created from a `// @param` declaration in the code).
The value is set directly on the WerkstattParameterBox.value field.
"""
    safe_device_type = device_type.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const p = window.DAW;
        const allAU = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        const au = allAU[{unit_index}];
        if (!au) return {{error: "Unit {unit_index} not found"}};
        let device = null;
        const dt = "{safe_device_type}".toLowerCase();
        if (dt === "werkstatt") {{
            const fx = [...au.audioEffects.pointerHub.incoming()].map(({{box}}) => box);
            device = fx[{device_index}] || null;
        }} else if (dt === "spielwerk") {{
            const me = au.midiEffects ? [...au.midiEffects.pointerHub.incoming()].map(({{box}}) => box) : [];
            device = me[{device_index}] || null;
        }} else if (dt === "apparat") {{
            const incoming = au.input ? [...au.input.pointerHub.incoming()].map(({{box}}) => box) : [];
            device = incoming.find(b => b.constructor.name === "ApparatDeviceBox") || incoming[0] || null;
        }}
        if (!device) return {{error: "Scriptable device '" + dt + "' not found on unit {unit_index}"}};
        if (!device.parameters) return {{error: "Device has no parameters field"}};
        const params = [...device.parameters.pointerHub.incoming()].map(({{box}}) => box);
        const targetLabel = {json.dumps(param_label)};
        const param = params.find(p => p.label.getValue() === targetLabel);
        if (!param) return {{error: "Parameter '" + targetLabel + "' not found. Available: " + params.map(p => p.label.getValue()).join(", ")}};
        const oldVal = param.value.getValue();
        p.editing.modify(() => {{
            param.value.setValue({value});
        }});
        return {{
            success: true,
            param: param.label.getValue(),
            old_value: oldVal,
            new_value: param.value.getValue(),
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
        const p = window.DAW;
        const allAU = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        const au = allAU[{unit_index}];
        if (!au) return {{error: "Unit {unit_index} not found"}};
        let device = null;
        const dt = "{safe_device_type}".toLowerCase();
        if (dt === "werkstatt") {{
            const fx = [...au.audioEffects.pointerHub.incoming()].map(({{box}}) => box);
            device = fx[{device_index}] || null;
        }} else if (dt === "spielwerk") {{
            const me = au.midiEffects ? [...au.midiEffects.pointerHub.incoming()].map(({{box}}) => box) : [];
            device = me[{device_index}] || null;
        }} else if (dt === "apparat") {{
            const incoming = au.input ? [...au.input.pointerHub.incoming()].map(({{box}}) => box) : [];
            device = incoming.find(b => b.constructor.name === "ApparatDeviceBox") || incoming[0] || null;
        }}
        if (!device) return {{error: "Scriptable device '" + dt + "' not found on unit {unit_index}"}};
        if (!device.samples) return {{error: "Device has no samples field"}};
        const samples = [...device.samples.pointerHub.incoming()].map(({{box}}) => box);
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
        const p = window.DAW;
        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if ({unit_index} >= units.length) return {{error: "No audio unit at index {unit_index}"}};
        const srcAU = units[{unit_index}];

        const srcType = srcAU.type.getValue();
        const srcLabel = srcAU.label?.getValue() || "Unit";
        const srcVolume = srcAU.volume?.getValue() || 0.767835;

        // Read instrument info
        const srcIncoming = [...srcAU.input.pointerHub.incoming()].map(({{box}}) => box);
        const srcInstrument = srcIncoming.length > 0 ? srcIncoming[0] : null;
        const instrumentFactoryName = srcInstrument?.constructor.name || null;

        // Read effects
        const srcEffects = [...srcAU.audioEffects.pointerHub.incoming()].map(({{box}}) => box)
            .sort((a,b) => a.index.getValue() - b.index.getValue())
            .map(box => ({{type: box.constructor.name}}));

        // Read MIDI effects
        const srcMidiEffects = [...srcAU.midiEffects.pointerHub.incoming()].map(({{box}}) => box)
            .sort((a,b) => a.index.getValue() - b.index.getValue())
            .map(box => ({{type: box.constructor.name}}));

        // Read tracks
        const srcTracks = [...srcAU.tracks.pointerHub.incoming()].map(({{box}}) => box).sort((a,b) => a.index.getValue() - b.index.getValue());

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

            const regions = [...track.regions.pointerHub.incoming()].map(({{box}}) => box);
            const trackNotes = [];
            for (const region of regions) {{
                if (region.constructor.name === 'NoteRegionBox') {{
                    try {{
                        const vertex = region.events.targetVertex.unwrap();
                        const eventsBox = vertex.box || vertex;
                        const notes = [...eventsBox.events.pointerHub.incoming()].map(({{box}}) => box);
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
        const p = window.DAW;
        const AudioUnitBoxAdapter = window.DAW_AudioUnitBoxAdapter;
        if (!AudioUnitBoxAdapter) throw new Error("AudioUnitBoxAdapter not loaded");
        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if ({unit_index} >= units.length) return {{error: "No unit at index {unit_index}"}};
        const au = units[{unit_index}];
        const tracks = [...au.tracks.pointerHub.incoming()].map(({{box}}) => box).sort((a,b) => a.index.getValue() - b.index.getValue());
        if ({track_index} >= tracks.length) return {{error: "No track {track_index} in unit {unit_index}"}};
        const trackBox = tracks[{track_index}];
        const auAdapter = p.boxAdapters.adapterFor(au, AudioUnitBoxAdapter);
        const trackAdapter = p.boxAdapters.adapterFor(trackBox, window.DAW_TrackBoxAdapter);
        p.editing.modify(() => {{
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
        const p = window.DAW;
        const srcUnitIdx = {src_unit_index};
        const srcTrackIdx = {src_track_index};
        const regionIdx = {region_index};
        const dstUnitIdx = {dst_unit_index};
        const dstTrackIdx = {dst_track_index};

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        const srcAU = units[srcUnitIdx];
        const dstAU = units[dstUnitIdx];
        if (!srcAU) return {{error: "Source unit not found"}};
        if (!dstAU) return {{error: "Destination unit not found"}};

        const srcTracks = [...srcAU.tracks.pointerHub.incoming()].map(({{box}}) => box);
        const dstTracks = [...dstAU.tracks.pointerHub.incoming()].map(({{box}}) => box);
        const srcTrack = srcTracks[srcTrackIdx];
        const dstTrack = dstTracks[dstTrackIdx];
        if (!srcTrack) return {{error: "Source track not found"}};
        if (!dstTrack) return {{error: "Destination track not found"}};

        const srcRegions = [...srcTrack.regions.pointerHub.incoming()].map(({{box}}) => box);
        const region = srcRegions[regionIdx];
        if (!region) return {{error: "Region not found"}};

        // Check type compatibility
        const srcType = srcTrack.type?.getValue();
        const dstType = dstTrack.type?.getValue();
        if (srcType !== dstType) return {{error: `Track type mismatch: source=${{srcType}} dest=${{dstType}}`}};

        p.editing.modify(() => {{
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
        const p = window.DAW;
        const UUID = window.DAW_UUID;
        const AudioBusBox = window.DAW_AudioBusBox;
        const TrackBox = window.DAW_TrackBox;
        const AudioUnitBox = window.DAW_AudioUnitBox;
        const AudioUnitType = window.DAW_AudioUnitType;
        const TrackType = window.DAW_TrackType;

        const buses = [...p.rootBox.audioBusses.pointerHub.incoming()].map(({{box}}) => box);
        const newIdx = buses.length;
        let newBus, newUnit;

        // Block 1: Create AudioUnitBox (Aux)
        p.editing.modify(() => {{
            const unitIdx = [...p.rootBox.audioUnits.pointerHub.incoming()].length;
            newUnit = AudioUnitBox.create(p.boxGraph, UUID.generate(), (box) => {{
                box.type.setValue(AudioUnitType.Aux);
                box.collection.refer(p.rootBox.audioUnits);
                box.index.setValue(unitIdx);
            }});
        }});

        // Block 2: Create AudioBusBox + wire output -> unit.input
        // Must be separate block — refer() inside constructor causes
        // deferred pointer update that fails at endTransaction.
        p.editing.modify(() => {{
            newBus = AudioBusBox.create(p.boxGraph, UUID.generate(), (box) => {{
                box.label.setValue();
                box.collection.refer(p.rootBox.audioBusses);
                box.icon.setValue("AudioBus");
            }});
            newBus.output.refer(newUnit.input);
        }});

        // Block 3: Create TrackBox linking to the new unit
        p.editing.modify(() => {{
            TrackBox.create(p.boxGraph, UUID.generate(), (box) => {{
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
        const p = window.DAW;
        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
        if ({unit_index} >= units.length) return {{error: "No unit at {unit_index}"}};
        const au = units[{unit_index}];
        const tracks = [...au.tracks.pointerHub.incoming()].map(({{box}}) => box).sort((a,b) => a.index.getValue() - b.index.getValue());

        // Filter to automation tracks (type 3)
        const autoTracks = tracks.filter(t => t.type?.getValue?.() === 3);
        if ({track_index} >= autoTracks.length) return {{error: "No automation track at index {track_index}"}};
        const track = autoTracks[{track_index}];

        // Collect events from clips (automation uses ValueClipBox, not ValueRegionBox)
        const clips = [...track.clips.pointerHub.incoming()].map(({{box}}) => box);
        const allEvents = [];
        for (const clip of clips) {{
            if (clip.constructor.name === 'ValueClipBox') {{
                try {{
                    const vertex = clip.events.targetVertex.unwrap();
                    const eventsBox = vertex.box || vertex;
                    const events = [...eventsBox.events.pointerHub.incoming()].map(({{box}}) => box);
                    for (const ev of events) {{
                        allEvents.push({{box: ev}});
                    }}
                }} catch(e) {{}}
            }}
        }}

        // Also check regions (in case events are region-based)
        const regions = [...track.regions.pointerHub.incoming()].map(({{box}}) => box);
        for (const region of regions) {{
            if (region.constructor.name === 'ValueRegionBox') {{
                try {{
                    const vertex = region.events.targetVertex.unwrap();
                    const eventsBox = vertex.box || vertex;
                    const events = [...eventsBox.events.pointerHub.incoming()].map(({{box}}) => box);
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
        p.editing.modify(() => {{
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
        const p = window.DAW;
        try {{
            const auAdapter = p.rootBoxAdapter.audioUnits.adapters()[{unit_index}];
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
            p.editing.modify(() => {{
                evt.box.position.setValue({new_ppqn});
            }});
            collection.requestSorting();
            return {{success: true, old_position_ppqn: oldPos, new_position_ppqn: {new_ppqn}, old_position_beats: oldPos / 960, new_position_beats: {new_position_beats}}};
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
        const p = window.DAW;
        try {{
            const auAdapter = p.rootBoxAdapter.audioUnits.adapters()[{unit_index}];
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
            p.editing.modify(() => {{
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
        const p = window.DAW;
        const AudioUnitBoxAdapter = window.DAW_AudioUnitBoxAdapter;
        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box)
            .sort((a, b) => a.index.getValue() - b.index.getValue());
        if ({unit_index} >= units.length) return {{error: "No AU at {unit_index}"}};
        const auBox = units[{unit_index}];
        const adapter = p.boxAdapters.adapterFor(auBox, AudioUnitBoxAdapter);
        let newIdx = auBox.index.getValue();
        p.editing.modify(() => {{
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
        const p = window.DAW;
        const AudioUnitBoxAdapter = window.DAW_AudioUnitBoxAdapter;
        const TrackBoxAdapter = window.DAW_TrackBoxAdapter;
        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box)
            .sort((a, b) => a.index.getValue() - b.index.getValue());
        if ({unit_index} >= units.length) return {{error: "No AU at {unit_index}"}};
        const auBox = units[{unit_index}];
        const auAdapter = p.boxAdapters.adapterFor(auBox, AudioUnitBoxAdapter);
        const tracks = [...auBox.tracks.pointerHub.incoming()].map(({{box}}) => box)
            .sort((a, b) => a.index.getValue() - b.index.getValue());
        if ({track_index} >= tracks.length) return {{error: "No track at {track_index}"}};
        const trackBox = tracks[{track_index}];
        const trackAdapter = p.boxAdapters.adapterFor(trackBox, TrackBoxAdapter);
        p.editing.modify(() => {{
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
        const p = window.DAW;
        const TransferRegions = window.DAW_TransferRegions;
        if (!TransferRegions) return {{error: "TransferRegions not loaded"}};
        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box)
            .sort((a, b) => a.index.getValue() - b.index.getValue());

        if ({src_unit_index} >= units.length) return {{error: "No source AU at {src_unit_index}"}};
        if ({dst_unit_index} >= units.length) return {{error: "No dest AU at {dst_unit_index}"}};

        const srcAU = units[{src_unit_index}];
        const dstAU = units[{dst_unit_index}];

        const srcTracks = [...srcAU.tracks.pointerHub.incoming()].map(({{box}}) => box)
            .sort((a, b) => a.index.getValue() - b.index.getValue());
        const dstTracks = [...dstAU.tracks.pointerHub.incoming()].map(({{box}}) => box)
            .sort((a, b) => a.index.getValue() - b.index.getValue());

        if ({src_track_index} >= srcTracks.length) return {{error: "No source track at {src_track_index}"}};
        if ({dst_track_index} >= dstTracks.length) return {{error: "No dest track at {dst_track_index}"}};

        const srcTrack = srcTracks[{src_track_index}];
        const dstTrack = dstTracks[{dst_track_index}];

        const regions = [...srcTrack.regions.pointerHub.incoming()].map(({{box}}) => box)
            .sort((a, b) => a.position.getValue() - b.position.getValue());
        if ({region_index} >= regions.length) return {{error: "No region at {region_index}"}};

        const srcRegion = regions[{region_index}];
        const regionType = srcRegion.constructor.name;
        const insertPos = Math.round({insert_position} * 960);  // beats to ppqn

        let newRegion;
        p.editing.modify(() => {{
            newRegion = TransferRegions.transfer(srcRegion, dstTrack, insertPos, {delete_js});
        }});

        if (!newRegion) return {{error: "Transfer failed"}};
        return {{
            success: true,
            region_type: newRegion.constructor.name,
            position_beats: newRegion.position.getValue() / 960,
            duration_beats: newRegion.duration.getValue() / 960,
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
        const p = window.DAW;
        const TransferAudioUnits = window.DAW_TransferAudioUnits;
        if (!TransferAudioUnits) return {{error: "TransferAudioUnits not loaded"}};
        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box)
            .sort((a, b) => a.index.getValue() - b.index.getValue());
        if ({unit_index} >= units.length) return {{error: "No AU at {unit_index}"}};

        const srcAU = units[{unit_index}];
        // Find primary audio bus (connected to Output unit's input)
        const outputAU = units.find(u => u.type.getValue() === "output" || u.type.getValue() === 2);
        if (!outputAU) return {{error: "No Output unit found"}};
        const primaryBus = [...outputAU.input.pointerHub.incoming()].map(({{box}}) => box)[0];
        if (!primaryBus) return {{error: "No primary audio bus found"}};

        const skeleton = {{
            boxGraph: p.boxGraph,
            mandatoryBoxes: {{
                primaryAudioBusBox: primaryBus,
                rootBox: p.rootBox,
            }}
        }};

        let newAUs;
        const opts = {{deleteSource: {delete_js}}};
        if ({insert_index} >= 0) opts.insertIndex = {insert_index};
        p.editing.modify(() => {{
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
        const p = window.DAW;
        const PresetEncoder = window.DAW_PresetEncoder;
        if (!PresetEncoder) return {{error: "PresetEncoder not loaded"}};
        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box)
            .sort((a, b) => a.index.getValue() - b.index.getValue());
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
        const p = window.DAW;
        const PresetDecoder = window.DAW_PresetDecoder;
        if (!PresetDecoder) return {{error: "PresetDecoder not loaded"}};
        const b64 = {preset_json};
        // Decode base64 to ArrayBuffer
        const binary = atob(b64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);

        const outputAU = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box)
            .find(u => u.type.getValue() === "output");
        if (!outputAU) return {{error: "No Output unit"}};
        const primaryBus = [...outputAU.input.pointerHub.incoming()].map(({{box}}) => box)[0];
        if (!primaryBus) return {{error: "No primary bus"}};

        const skeleton = {{
            boxGraph: p.boxGraph,
            mandatoryBoxes: {{primaryAudioBusBox: primaryBus, rootBox: p.rootBox}}
        }};

        let newAUs;
        p.editing.modify(() => {{
            newAUs = PresetDecoder.decode(bytes.buffer, skeleton);
        }});

        if (!newAUs || newAUs.length === 0) return {{error: "Import returned no units"}};
        const newAU = newAUs[0];
        const fx = [...newAU.audioEffects.pointerHub.incoming()].map(({{box}}) => box);
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
        const p = window.DAW;
        const PresetDecoder = window.DAW_PresetDecoder;
        if (!PresetDecoder) return {{error: "PresetDecoder not loaded"}};
        const b64 = {preset_json};
        const binary = atob(b64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box)
            .sort((a, b) => a.index.getValue() - b.index.getValue());
        if ({unit_index} >= units.length) return {{error: "No AU at {unit_index}"}};
        const targetAU = units[{unit_index}];

        let attempt;
        p.editing.modify(() => {{
            attempt = PresetDecoder.replaceAudioUnit(bytes.buffer, targetAU, {{
                keepMIDIEffects: {keep_midi},
                keepAudioEffects: {keep_audio},
                keepTimeline: {keep_timeline_js},
            }});
        }});

        if (!attempt.isSuccess()) return {{error: attempt.failureReason()}};
        // Read new state
        const fx = [...targetAU.audioEffects.pointerHub.incoming()].map(({{box}}) => box);
        const inp = targetAU.input.pointerHub.incoming().length > 0
            ? [...targetAU.input.pointerHub.incoming()][0].box.constructor.name : 'none';
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
        const p = window.DAW;
        const PresetEncoder = window.DAW_PresetEncoder;
        const PresetHeader = window.DAW_PresetHeader || {{ChainKind: {{Audio: 1, Midi: 0}}}};
        if (!PresetEncoder) return {{error: "PresetEncoder not loaded"}};
        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box)
            .sort((a, b) => a.index.getValue() - b.index.getValue());
        if ({unit_index} >= units.length) return {{error: "No AU at {unit_index}"}};
        const au = units[{unit_index}];

        const kind = "{safe_effect_type}" === "midi" ? 0 : 1;  // ChainKind.Midi=0, Audio=1
        const field = kind === 0 ? au.midiEffects : au.audioEffects;
        const effects = [...field.pointerHub.incoming()].map(({{box}}) => box)
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
        const p = window.DAW;
        const tempoMap = p.tempoMap;
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
        const p = window.DAW;
        const tempoMap = p.tempoMap;
        if (!tempoMap) return {{error: "tempoMap not available"}};
        const ppqn = tempoMap.secondsToPPQN({seconds});
        const beats = ppqn / 960.0;
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
        const p = window.DAW;
        const tempoMap = p.tempoMap;
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
    result = await bridge.evaluate(f"""() => {{
        const p = window.DAW;
        const lastPPQN = p.lastRegionAction ? p.lastRegionAction() : 0;
        const tempoMap = p.tempoMap;
        let secs = 0;
        try {{ secs = tempoMap ? tempoMap.ppqnToSeconds(lastPPQN) : 0; }} catch(e) {{}}
        return {{
            duration_beats: lastPPQN / 960.0,
            duration_ppqn: lastPPQN,
            duration_seconds: secs,
        }};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_validate_project() -> str:
    """Check if the project is valid — detects overlapping regions on the same track.

    Returns valid (bool) and details about any issues found.
    """
    result = await bridge.evaluate(f"""() => {{
        const p = window.DAW;
        let valid = true;
        let issues = [];
        try {{
            valid = !p.invalid();
        }} catch(e) {{
            issues.push("validation error: " + e.message);
        }}
        if (!valid) {{
            const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
            for (const au of units) {{
                const tracks = [...au.tracks.pointerHub.incoming()].map(({{box}}) => box);
                for (const track of tracks) {{
                    const regions = [...track.regions.pointerHub.incoming()].map(({{box}}) => box)
                        .sort((a, b) => a.position.getValue() - b.position.getValue());
                    for (let i = 1; i < regions.length; i++) {{
                        const prevEnd = regions[i-1].position.getValue() + regions[i-1].duration.getValue();
                        if (prevEnd > regions[i].position.getValue()) {{
                            issues.push("overlap on track: " + (track.label?.getValue?.() || 'unnamed') +
                                " region " + (i-1) + " and " + i);
                        }}
                    }}
                }}
            }}
        }}
        return {{valid: valid, issues: issues}};
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_list_samples() -> str:
    """List all audio file samples used in the project.

    Returns sample UUIDs and metadata for each audio file referenced in the project.
    """
    result = await bridge.evaluate(f"""() => {{
        const p = window.DAW;
        const uuids = p.collectSampleUUIDs ? p.collectSampleUUIDs() : [];
        const samples = uuids.map(uuid => {{
            const hex = Array.from(uuid, b => b.toString(16).padStart(2, '0')).join('');
            return {{uuid: hex}};
        }});
        return {{sample_count: samples.length, samples: samples}};
    }}""")
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
        const p = window.DAW;
        const freeze = p.audioUnitFreeze;
        if (!freeze) return {{error: "audioUnitFreeze not available"}};
        const auAdapters = p.rootBoxAdapter.audioUnits.adapters();
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
        const p = window.DAW;
        const freeze = p.audioUnitFreeze;
        if (!freeze) return {{error: "audioUnitFreeze not available"}};
        const auAdapters = p.rootBoxAdapter.audioUnits.adapters();
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
        const p = window.DAW;
        const freeze = p.audioUnitFreeze;
        if (!freeze) return {{error: "audioUnitFreeze not available"}};
        const auAdapters = p.rootBoxAdapter.audioUnits.adapters();
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
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const aus = h.allAUs();
        const strips = aus.map(au => {{
            const np = au.namedParameter;
            return {{
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
            }};
        }});
        return {{strips: strips, count: strips.length}};
    }}""")
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
        const p = window.DAW;
        const auAdapters = p.rootBoxAdapter.audioUnits.adapters();
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
        const p = window.DAW;
        const auAdapters = p.rootBoxAdapter.audioUnits.adapters();
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
        const p = window.DAW;
        const auAdapters = p.rootBoxAdapter.audioUnits.adapters();
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
            p.editing.modify(() => {{
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
        const p = window.DAW;
        const auAdapters = p.rootBoxAdapter.audioUnits.adapters();
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
        const p = window.DAW;
        const auAdapters = p.rootBoxAdapter.audioUnits.adapters();
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
        const p = window.DAW;
        const auAdapters = p.rootBoxAdapter.audioUnits.adapters();
        if ({unit_index} >= auAdapters.length) return {{error: "No AU at {unit_index}"}};
        const auAdapter = auAdapters[{unit_index}];
        const trackAdapters = auAdapter.tracks.collection.adapters();
        if ({track_index} >= trackAdapters.length) return {{error: "No track {track_index}"}};
        const trackAdapter = trackAdapters[{track_index}];
        const regions = trackAdapter.regions.collection.asArray();
        if ({region_index} >= regions.length) return {{error: "No region {region_index}"}};
        const region = regions[{region_index}];
        try {{
            p.editing.modify(() => {{
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
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const aus = h.allAUs();
        const typeNames = ['undefined', 'notes', 'audio', 'value'];
        const project = h.project;
        return {{
            bpm: project.timelineBox.bpm.getValue(),
            duration_beats: project.lastRegionAction() / 960.0,
            au_count: aus.length,
            units: aus.map(au => {{
                const np = au.namedParameter;
                const tracks = au.tracks.collection.adapters();
                const fxAdapters = au.audioEffects.adapters();
                const midiFxAdapters = au.midiEffects.adapters();
                return {{
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
                    tracks: tracks.map(t => {{
                        const tbox = t.box;
                        const regCount = [...tbox.regions.pointerHub.incoming()].length;
                        const clipCount = [...tbox.clips.pointerHub.incoming()].length;
                        return {{
                            type: typeNames[t.type] || String(t.type),
                            region_count: regCount,
                            clip_count: clipCount,
                        }};
                    }}),
                }};
            }}),
        }};
    }}""")
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
                        position_beats: event.position / 960.0,
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
                max_duration_beats: collection.maxDuration / 960.0,
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
                    position_beats: n.position / 960.0,
                    duration_beats: n.duration / 960.0,
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
            const au = h.au({unit_index});
            const audioFx = au.audioEffects.adapters();
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
        const p = window.DAW;
        try {{
            const sigTrack = p.rootBoxAdapter.timeline.signatureTrack;
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
        const p = window.DAW;
        try {{
            const sigTrack = p.rootBoxAdapter.timeline.signatureTrack;
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
        const p = window.DAW;
        try {{
            const sigTrack = p.rootBoxAdapter.timeline.signatureTrack;
            const adapter = sigTrack.adapterAt({event_index});
            if (adapter.isEmpty()) return {{error: "No signature event at index " + {event_index}}};
            p.editing.modify(() => {{
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
            window.DAW.editing.modify(() => {{
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
            const samples = inst.box.samples ? [...inst.box.samples.pointerHub.incoming()] : [];
            const sampleAdapter = samples.find(s => s.box.index.getValue() === {sample_index});
            if (!sampleAdapter) return {{error: "No sample at index " + {sample_index}}};
            const p = window.DAW;
            const adapter = p.boxAdapters.adapterFor(sampleAdapter.box, inst.constructor);
            p.editing.modify(() => {{
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
            const noteAdapters = [...events.events.pointerHub.incoming()]
                .map(({{box}}) => box)
                .sort((a, b) => a.position.getValue() - b.position.getValue());
            if ({note_index} >= noteAdapters.length) return {{error: "No note at index " + {note_index}}};
            const srcBox = noteAdapters[{note_index}];
            const p = window.DAW;
            const adapter = p.boxAdapters.adapterFor(srcBox, p.NoteEventBoxAdapter || class {{}});
            let newAdapter;
            p.editing.modify(() => {{
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
            const au = h.au({unit_index});
            const fx = au.audioEffects.adapters();
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
            const p = window.DAW;
            const fileAdapter = p.boxAdapters.adapterFor(fileBox, p.AudioFileBoxAdapter || class {{}});
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
    result = await bridge.evaluate(f"""() => {{
        const p = window.DAW;
        try {{
            const sigTrack = p.rootBoxAdapter.timeline.signatureTrack;
            const events = Array.from(sigTrack.iterateAll());
            return {{
                enabled: sigTrack.enabled,
                base_signature: [events[0].nominator, events[0].denominator],
                event_count: events.length - 1,
                events: events.map(e => ({{
                    index: e.index,
                    position_ppqn: e.accumulatedPpqn,
                    bars: e.accumulatedBars,
                    nominator: e.nominator,
                    denominator: e.denominator,
                }})),
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_delete_signature_event(event_index: int) -> str:
    """Delete a time signature change event by index.

    Automatically recalculates relative positions of subsequent events.

    event_index: Index of the signature event (from get_signature_events).

    Returns success or error.
    """
    result = await bridge.evaluate(f"""() => {{
        const p = window.DAW;
        try {{
            const sigTrack = p.rootBoxAdapter.timeline.signatureTrack;
            const adapter = sigTrack.adapterAt({event_index});
            if (adapter.isEmpty()) return {{error: "No signature event at index " + {event_index}}};
            p.editing.modify(() => {{
                sigTrack.deleteAdapter(adapter.unwrap());
            }});
            return {{success: true, deleted_index: {event_index}}};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
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
        const p = window.DAW;
        try {{
            const sigTrack = p.rootBoxAdapter.timeline.signatureTrack;
            p.editing.modify(() => {{
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
            const samples = inst.box.samples ? [...inst.box.samples.pointerHub.incoming()] : [];
            const sampleAdapter = samples.find(s => s.box.index.getValue() === {sample_index});
            if (!sampleAdapter) return {{error: "No sample at index " + {sample_index}}};
            const p = window.DAW;
            const adapter = p.boxAdapters.adapterFor(sampleAdapter.box, inst.constructor);
            p.editing.modify(() => {{
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
            const eventAdapters = [...events.events.pointerHub.incoming()]
                .map(({{box}}) => box)
                .sort((a, b) => a.position.getValue() - b.position.getValue());
            if ({event_index} >= eventAdapters.length) return {{error: "No event at index " + {event_index}}};
            const srcBox = eventAdapters[{event_index}];
            const p = window.DAW;
            const adapter = p.boxAdapters.adapterFor(srcBox, p.ValueEventBoxAdapter || class {{}});
            const origPos = srcBox.position.getValue();
            const origVal = srcBox.value.getValue();
            let newAdapter;
            p.editing.modify(() => {{
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
            window.DAW.editing.modify(() => {{
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
    result = await bridge.evaluate(f"""() => {{
        const p = window.DAW;
        try {{
            const root = p.rootBoxAdapter;
            const aus = root.audioUnits.adapters();
            let trackCount = 0;
            aus.forEach(au => {{ trackCount += au.tracks.collection.adapters().length; }});
            const sigTrack = root.timeline.signatureTrack;
            const sig = sigTrack.storageSignature;
            return {{
                created: root.created.toISOString(),
                time_signature: [sig[0], sig[1]],
                audio_unit_count: aus.length,
                total_track_count: trackCount,
                groove_enabled: root.groove.enabled,
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)

@mcp.tool()
async def mcp_opendaw_list_midi_output_devices() -> str:
    """List all MIDI output devices registered in the project (hardware MIDI outputs).

    Returns id, label, delayInMs, sendTransportMessages for each device.
    """
    result = await bridge.evaluate("""() => {
        const p = window.DAW;
        try {
            const devices = p.rootBoxAdapter.midiOutputDevices;
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
        const p = window.DAW;
        try {{
            const buses = p.rootBoxAdapter.audioBusses.adapters();
            if ({bus_index} >= buses.length) return {{error: "No bus at index " + {bus_index}}};
            const bus = buses[{bus_index}];
            p.editing.modify(() => {{
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
        const p = window.DAW;
        try {{
            const buses = p.rootBoxAdapter.audioBusses.adapters();
            if ({bus_index} >= buses.length) return {{error: "No bus at index " + {bus_index}}};
            const bus = buses[{bus_index}];
            p.editing.modify(() => {{
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
        const p = window.DAW;
        try {
            const aus = p.rootBoxAdapter.audioUnits.adapters();
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
        const p = window.DAW;
        try {{
            const au = p.rootBoxAdapter.audioUnits.adapters()[{au_index}];
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
        const p = window.DAW;
        try {{
            const au = p.rootBoxAdapter.audioUnits.adapters()[{au_index}];
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
        const p = window.DAW;
        try {{
            const au = p.rootBoxAdapter.audioUnits.adapters()[{au_index}];
            if (!au) return {{error: "No AU at index {au_index}"}};
            const effects = au.audioEffects.adapters();
            const modDev = effects[{effect_index}];
            if (!modDev || !(modDev.box instanceof window.DAW_ModularDeviceBox))
                return {{error: "No Modular device at effect {effect_index}"}};
            const modular = modDev.modular();
            const BoxClass = window.{box_global};
            if (!BoxClass) return {{error: "Box class not available: {box_global}"}};
            const graph = p.project.boxGraph;
            const uuid = window.DAW_UUID.generate();
            let newModule;
            p.editing.modify(() => {{
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
        const p = window.DAW;
        try {{
            const au = p.rootBoxAdapter.audioUnits.adapters()[{au_index}];
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
            const graph = p.project.boxGraph;
            const uuid = window.DAW_UUID.generate();
            p.editing.modify(() => {{
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
        const p = window.DAW;
        try {{
            const au = p.rootBoxAdapter.audioUnits.adapters()[{au_index}];
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
                        p.editing.modify(() => {{
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
            p.editing.modify(() => {{
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
        const p = window.DAW;
        try {{
            const au = p.rootBoxAdapter.audioUnits.adapters()[{au_index}];
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
            p.editing.modify(() => {{
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
        const p = window.DAW;
        try {{
            const pm = p.rootBoxAdapter.pianoMode;
            const old = pm.transpose.getValue();
            p.editing.modify(() => {{
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
        const p = window.DAW;
        try {
            const pm = p.rootBoxAdapter.pianoMode;
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
        const p = window.DAW;
        try {{
            const pm = p.rootBoxAdapter.pianoMode;
            const old = pm.keyboard.getValue();
            p.editing.modify(() => {{
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
        const p = window.DAW;
        try {{
            const pm = p.rootBoxAdapter.pianoMode;
            const old = pm.noteScale.getValue();
            p.editing.modify(() => {{
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
        const p = window.DAW;
        try {{
            const pm = p.rootBoxAdapter.pianoMode;
            const old = pm.noteLabels.getValue();
            p.editing.modify(() => {{
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
        const p = window.DAW;
        try {{
            const pm = p.rootBoxAdapter.pianoMode;
            const old = pm.timeRangeInQuarters.getValue();
            p.editing.modify(() => {{
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


def main():
    """Entry point for opendaw-mcp command."""
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    mcp.run(transport=transport)

if __name__ == "__main__":
    main()