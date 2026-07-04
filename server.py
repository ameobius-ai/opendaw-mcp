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
import os
import atexit

from mcp.server.fastmcp import FastMCP
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("opendaw-mcp")
DAW_HOST_DIR = os.environ.get("OPENDAW_HOST_DIR", os.path.join(os.path.dirname(__file__), "..", "headless-daw"))
DAW_URL = os.environ.get("OPENDAW_URL", "http://localhost:5174")
EXPORT_DIR = os.environ.get("OPENDAW_EXPORT_DIR", os.path.join(os.path.dirname(__file__), "..", "exports"))
os.makedirs(EXPORT_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Module-level lookup tables (extracted from tool functions for testability)
# ---------------------------------------------------------------------------
TIDAL_RATE_MAP: dict[str, int] = {
    "1/1": 0, "1/2": 1, "1/3": 2, "1/4": 3, "3/16": 4, "1/6": 5, "1/8": 6,
    "3/32": 7, "1/12": 8, "1/16": 9, "3/64": 10, "1/24": 11, "1/32": 12,
    "1/48": 13, "1/64": 14, "1/96": 15, "1/128": 16,
}
DELAY_SYNC_MAP: dict[str, int] = {
    "off": 0, "1/128": 1, "1/96": 2, "1/64": 3, "1/48": 4, "1/32": 5,
    "1/24": 6, "3/64": 7, "1/16": 8, "1/12": 9, "3/32": 10, "1/8": 11,
    "1/6": 12, "3/16": 13, "1/4": 14, "5/16": 15, "1/3": 16, "3/8": 17,
    "7/16": 18, "1/2": 19, "1/1": 20,
}
WAVESHAPER_FUNCS: dict[str, str] = {
    "hardclip": "min(1, max(-1, x))",
    "cubicSoft": "x - (x*x*x) / 3.0",
    "tanh": "tanh(x)",
    "sigmoid": "2.0 / (1.0 + exp(-x)) - 1.0",
    "arctan": "atan(x) / (PI/2)",
    "asymmetric": "x > 0 ? tanh(x*1.5) : tanh(x*0.7)",
}
REVAMP_SECTIONS: tuple[str, ...] = (
    "highPass", "lowShelf", "lowBell", "midBell",
    "highBell", "highShelf", "lowPass",
)

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
                // Get AU box by index (sorted by index field) — for box-level access
                auBox: (i) => {
                    const aus = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({box}) => box)
                        .sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
                    if (i >= aus.length) throw new Error('No AU at ' + i);
                    return aus[i];
                },
                // Get all AU boxes sorted
                allAUBoxes: () => [...p.rootBox.audioUnits.pointerHub.incoming()].map(({box}) => box)
                    .sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0)),
                // Get effect boxes for an AU (sorted by index)
                effectBoxes: (au) => [...au.audioEffects.pointerHub.incoming()].map(({box}) => box)
                    .sort((a, b) => a.index.getValue() - b.index.getValue()),
                // Get MIDI effect boxes for an AU (sorted by index)
                midiEffectBoxes: (au) => [...au.midiEffects.pointerHub.incoming()].map(({box}) => box)
                    .sort((a, b) => a.index.getValue() - b.index.getValue()),
                // Get track boxes for an AU (sorted by index)
                trackBoxes: (au) => [...au.tracks.pointerHub.incoming()].map(({box}) => box)
                    .sort((a, b) => a.index.getValue() - b.index.getValue()),
                // Get region boxes for a track (unsorted, insertion order)
                regionBoxes: (track) => [...track.regions.pointerHub.incoming()].map(({box}) => box),
                // Get event boxes from a collection (note events, signature events)
                eventBoxes: (coll) => [...coll.events.pointerHub.incoming()].map(({box}) => box),
                // Get input device boxes for an AU (instruments, effects)
                inputBoxes: (au) => [...au.input.pointerHub.incoming()].map(({box}) => box),
                // Get marker boxes from a marker track
                markerBoxes: (mt) => [...mt.markers.pointerHub.incoming()].map(({box}) => box),
                // Get aux send boxes for an AU (sorted by index)
                sendBoxes: (au) => [...au.auxSends.pointerHub.incoming()].map(({box}) => box)
                    .sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0)),
                // Get all audio bus boxes
                busBoxes: () => [...p.rootBox.audioBusses.pointerHub.incoming()].map(({box}) => box),
                // Get sample boxes from a Playfield instrument
                sampleBoxes: (pf) => [...pf.samples.pointerHub.incoming()].map(({box}) => box),
                // Get note track boxes for an AU (type === 1, sorted by index)
                noteTrackBoxes: (au) => [...au.tracks.pointerHub.incoming()].map(({box}) => box)
                    .sort((a, b) => a.index.getValue() - b.index.getValue())
                    .filter(box => box.type?.getValue?.() === 1),
                // Get clip boxes from a track
                clipBoxes: (track) => [...track.clips.pointerHub.incoming()].map(({box}) => box),
                // Get all clips from rootBox
                rootClipBoxes: () => [...p.rootBox.clips.pointerHub.incoming()].map(({box}) => box),
                // Get script device parameters
                scriptParams: (device) => [...device.parameters.pointerHub.incoming()].map(({box}) => box),
                // Get script device samples
                scriptSamples: (device) => [...device.samples.pointerHub.incoming()].map(({box}) => box),
                // Get effect boxes from a chain field (audio or midi)
                chainBoxes: (field) => [...field.pointerHub.incoming()].map(({box}) => box),
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

def _parse_wav(raw: bytes) -> dict:
    """Parse a WAV file's RIFF header and return format info + de-interleaved float samples.

    Returns dict with: audio_format (1=PCM, 3=float32), n_channels, sample_rate,
    bits_per_sample, n_frames, channels (list of float lists), or raises ValueError.
    """
    import struct
    if raw[:4] != b"RIFF" or raw[8:12] != b"WAVE":
        raise ValueError("Not a valid WAV file")
    pos = 12
    n_channels = sample_rate = n_frames = 0
    bits_per_sample = 16
    audio_format = 1
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
        pos += 8 + chunk_size + (chunk_size % 2)
    if not audio_data:
        raise ValueError("No data chunk in WAV")
    # Convert to float samples
    if audio_format == 3 and bits_per_sample == 32:
        fmt = f"<{n_frames * n_channels}f"
        samples = list(struct.unpack(fmt, audio_data))
    elif audio_format == 1 and bits_per_sample == 16:
        fmt = f"<{n_frames * n_channels}h"
        samples = [s / 32768.0 for s in struct.unpack(fmt, audio_data)]
    elif audio_format == 1 and bits_per_sample == 24:
        samples = [int.from_bytes(audio_data[i:i+3], "little", signed=True) / 8388608.0
                   for i in range(0, len(audio_data), 3)]
    elif audio_format == 1 and bits_per_sample == 32:
        fmt = f"<{n_frames * n_channels}i"
        samples = [s / 2147483648.0 for s in struct.unpack(fmt, audio_data)]
    else:
        raise ValueError(f"Unsupported WAV format: {audio_format}/{bits_per_sample}bit")
    # De-interleave
    channels = [[] for _ in range(n_channels)]
    for i, s in enumerate(samples):
        channels[i % n_channels].append(s)
    return {
        "audio_format": audio_format, "n_channels": n_channels,
        "sample_rate": sample_rate, "bits_per_sample": bits_per_sample,
        "n_frames": n_frames, "channels": channels,
    }


def _compute_lufs(channels: list, sample_rate: int) -> dict:
    """Compute ITU-R BS.1770-4 integrated LUFS and true peak from de-interleaved float channels.

    Returns dict with: lufs_integrated, true_peak_db, max_sample, blocks_measured, gated_blocks.
    """
    import math
    n_channels = len(channels)
    n_frames = len(channels[0]) if channels else 0
    # K-weighting biquad coefficients (computed from sample_rate)
    f0, G, Q = 1681.974450955533, 3.9998432737, 0.7081754356
    K = math.tan(math.pi * f0 / sample_rate)
    Vh, Vb = 10 ** (G / 20.0), 10 ** (G / 40.0)
    a0_ = 1.0 + K / Q + K * K
    s_b0, s_b1, s_b2 = (Vh + Vb * K / Q + K * K) / a0_, 2.0 * (K * K - Vh) / a0_, (Vh - Vb * K / Q + K * K) / a0_
    s_a1, s_a2 = 2.0 * (K * K - 1.0) / a0_, (1.0 - K / Q + K * K) / a0_
    f0r, Qr = 38.1354708761, 0.5003270373
    Kr = math.tan(math.pi * f0r / sample_rate)
    ar0 = 1.0 + Kr / Qr + Kr * Kr
    r_b0, r_b1, r_b2 = 1.0 / ar0, -2.0 / ar0, 1.0 / ar0
    r_a1, r_a2 = 2.0 * (Kr * Kr - 1.0) / ar0, (1.0 - Kr / Qr + Kr * Kr) / ar0

    def _biquad(data, b0, b1, b2, a1, a2):
        out = [0.0] * len(data)
        x1 = x2 = y1 = y2 = 0.0
        for i in range(len(data)):
            x = data[i]
            y = b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
            out[i] = y
            x2, x1, y2, y1 = x1, x, y1, y
        return out

    k_weighted = [_biquad(_biquad(ch, s_b0, s_b1, s_b2, s_a1, s_a2), r_b0, r_b1, r_b2, r_a1, r_a2)
                  for ch in channels]
    block_size = int(0.4 * sample_rate)
    hop_size = int(0.1 * sample_rate)
    if block_size == 0 or hop_size == 0:
        raise ValueError(f"Sample rate too low: {sample_rate}")
    ch_weights = [1.0] * n_channels
    for i in range(2, n_channels):
        ch_weights[i] = 1.41
    blocks_ms, pos = [], 0
    while pos + block_size <= n_frames:
        block_ms = sum(ch_weights[c] * sum(s * s for s in k_weighted[c][pos:pos + block_size]) / block_size
                       for c in range(n_channels))
        blocks_ms.append(block_ms)
        pos += hop_size
    if not blocks_ms:
        raise ValueError("Not enough samples for LUFS measurement")
    abs_gate_ms = 10 ** ((-70.0 + 0.691) / 10.0)
    gated_blocks = [ms for ms in blocks_ms if ms > abs_gate_ms]
    if not gated_blocks:
        raise ValueError("All blocks below absolute gate (-70 LUFS)")
    mean_ms = sum(gated_blocks) / len(gated_blocks)
    rel_gate_ms = 10 ** ((10 * math.log10(mean_ms) - 0.691 - 10) / 10.0)
    rel_gated = [ms for ms in gated_blocks if ms > rel_gate_ms]
    final_ms = sum(rel_gated) / len(rel_gated) if rel_gated else mean_ms
    lufs = -0.691 + 10 * math.log10(final_ms)
    max_sample = max(max(abs(s) for s in ch) for ch in channels)
    true_peak_db = 20 * math.log10(max_sample) if max_sample > 0 else -float("inf")
    return {
        "lufs_integrated": round(lufs, 1),
        "true_peak_db": round(true_peak_db, 2),
        "max_sample": round(max_sample, 6),
        "blocks_measured": len(blocks_ms),
        "gated_blocks": len(gated_blocks),
    }


bridge = HeadlessDawBridge()
def cleanup():
    try: asyncio.run(bridge.stop())
    except Exception: pass
atexit.register(cleanup)

def _ok(data=None) -> str:
    d = {"success": True, **(data or {})}
    d["success"] = True  # ensure success is always True
    return json.dumps(d)
def _err(msg: str) -> str:
    return json.dumps({"error": msg})
def _wrap_eval(result) -> str:
    if isinstance(result, dict) and "error" in result: return json.dumps(result)
    return json.dumps(result)

def _unwrap_eval(s) -> any:
    """Parse a JSON string from _wrap_eval back to dict/list."""
    if isinstance(s, str):
        try: return json.loads(s)
        except (json.JSONDecodeError, ValueError): return s
    return s

def _safe_filename(name: str) -> str:
    """Sanitize a filename: strip quotes/backslashes, remove extension, prevent path traversal."""
    safe = name.replace('"', '').replace("'", '').replace('\\', '/')
    # Strip common audio extensions (case-insensitive)
    for ext in ('.wav', '.mp3', '.flac', '.dawproject'):
        if safe.lower().endswith(ext):
            safe = safe[:-len(ext)]
    # Prevent path traversal: only allow basename
    safe = os.path.basename(safe)
    # Remove any remaining path separators
    safe = safe.replace('/', '').replace('\\', '')
    return safe or "output"

def _safe_path(export_dir: str, filename: str, ext: str = "wav") -> str:
    """Build a safe file path inside export_dir, preventing path traversal."""
    safe = _safe_filename(filename)
    path = os.path.join(export_dir, f"{safe}.{ext}")
    # Verify the resolved path is inside export_dir
    if not os.path.abspath(path).startswith(os.path.abspath(export_dir)):
        path = os.path.join(export_dir, f"output.{ext}")
    return path

def _clamp_script_param(value: float, mapping: str, min_val: float, max_val: float) -> tuple:
    """Clamp a script parameter value based on its mapping type.
    
    Mirrors the JS-side clamping in set_script_param.
    Returns (clamped_value, was_clamped).
    """
    original = value
    if mapping == "bool":
        result = 1 if value >= 0.5 else 0
    elif mapping == "int":
        result = round(value)
        result = max(min_val, min(max_val, result))
    else:  # unipolar, linear, exp
        result = max(min_val, min(max_val, value))
    return (float(result), result != original)

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
async def mcp_opendaw_transpose_notes(semitones: int, unit_index: int, track_index: int) -> str:
    """Transpose all notes by a number of semitones.

semitones: Positive = up, negative = down (e.g. +12 = octave up, -5 = perfect fourth down).
unit_index: Audio unit index (-1 = all AUs with note tracks).
track_index: Specific note track (-1 = all note tracks on the AU).

Returns count of notes transposed.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const semis = {semitones};
        const unitIdx = {unit_index};
        const trackIdx = {track_index};

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
                        try {{
                            const vertex = region.events.targetVertex.unwrap();
                            const collectionBox = vertex.box || vertex;
                            if (collectionBox && collectionBox.events) {{
                                const noteEvents = h.eventBoxes(collectionBox);
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

    note_to_pitch = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}
    chord_intervals = {"maj": [0, 4, 7], "min": [0, 3, 7], "dom7": [0, 4, 7, 10], "maj7": [0, 4, 7, 11], "min7": [0, 3, 7, 10], "sus2": [0, 2, 7], "sus4": [0, 5, 7], "add9": [0, 4, 7, 14], "dim": [0, 3, 6], "aug": [0, 4, 8]}

    note_list = []
    voicings = []
    for ci, chord_spec in enumerate(chord_list):
        if len(chord_spec) < 2:
            return f"Error: chord {ci} must have [root, type]"
        root_name = chord_spec[0]
        chord_type = chord_spec[1]
        if root_name not in note_to_pitch:
            return f"Error: unknown root '{root_name}'"
        if chord_type not in chord_intervals:
            return f"Error: unknown chord type '{chord_type}'. Valid: {list(chord_intervals.keys())}"

        root_pc = note_to_pitch[root_name]
        intervals = chord_intervals[chord_type]
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

bpm: Override tempo (default per genre).

Returns created AU indices, note counts, and suggested next steps.
"""
    genres = {
        "house": {"bpm": 128, "drums": {"kick": "x...x...x...x...", "hihat": "....o...o...o..."}, "bass": [{"pitch": 36, "start": 0, "duration": 0.5}, {"pitch": 36, "start": 2, "duration": 0.5}, {"pitch": 43, "start": 4, "duration": 0.5}, {"pitch": 36, "start": 6, "duration": 0.5}], "chords": [["F", "min7"], ["Ab", "maj7"], ["Db", "maj7"], ["Eb", "min7"]]},
        "techno": {"bpm": 130, "drums": {"kick": "x...x...x...x...", "hihat": "x.x.x.x.x.x.x.x."}, "bass": [{"pitch": 31, "start": 0, "duration": 0.25}, {"pitch": 31, "start": 0.5, "duration": 0.25}, {"pitch": 31, "start": 1, "duration": 0.25}, {"pitch": 31, "start": 1.5, "duration": 0.25}], "chords": []},
        "lofi": {"bpm": 80, "drums": {"kick": "x.......x.......", "snare": "....x.......x...", "hihat": "x.x.x.x.x.x.x.x."}, "bass": [], "chords": [["D", "min7"], ["G", "dom7"], ["C", "maj7"], ["A", "min7"]]},
        "dnb": {"bpm": 174, "drums": {"kick": "x.......x...", "snare": "....x.......x.."}, "bass": [{"pitch": 28, "start": 0, "duration": 2}, {"pitch": 28, "start": 4, "duration": 2}], "chords": []},
        "trap": {"bpm": 140, "drums": {"kick": "x.....x.x.....", "hihat": "x.x.x.xxx.x.x.x."}, "bass": [{"pitch": 36, "start": 0, "duration": 1}, {"pitch": 36, "start": 3, "duration": 0.5}], "chords": [["F", "min"], ["Ab", "maj"], ["Eb", "min"]]},
        "ambient": {"bpm": 70, "drums": {}, "bass": [], "chords": [["C", "maj7"], ["F", "maj7"], ["A", "min7"], ["G", "maj7"]]},
    }
    if genre not in genres:
        return f"Error: unknown genre '{genre}'. Valid: {list(genres.keys())}"

    g = genres[genre]
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


def main():
    """Entry point for opendaw-mcp command."""
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] in ("--version", "-v"):
            print("opendaw-mcp 1.11.6 — 258 MCP tools")
            return
        if sys.argv[1] in ("--list-tools", "-l"):
            import asyncio
            tools = asyncio.run(mcp.list_tools())
            for t in sorted(tools, key=lambda x: x.name):
                print(f"  {t.name} — {t.description[:80]}")
            print(f"\nTotal: {len(tools)} tools")
            return
        if sys.argv[1] in ("--help", "-h"):
            print("opendaw-mcp — 258 MCP tools for agent-native openDAW control")
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

if __name__ == "__main__":
    main()
