"""
openDAW MCP Server — Playwright Bridge (verified May 2026)
Launches a headless Chromium pointing at the Vite-hosted DAW,
then exposes real DAW operations as MCP tools via page.evaluate().

Requirements (pip): mcp>=1.27, playwright>=1.60, pydantic>=2.13
Also: npx/vite in PATH (nvm node v23+), Playwright chromium installed.
"""
import asyncio
import json
import logging
import subprocess
import os
import atexit
from mcp.server.fastmcp import FastMCP
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("opendaw-mcp")

class HeadlessDawBridge:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None
        self.vite_process = None

    async def start(self):
        daw_path = os.environ.get(
            "OPENDAW_HOST_PATH",
            os.path.expanduser("~/projects/creative-studio/agent-daw/headless-daw")
        )
        self.vite_process = subprocess.Popen(
            ["npx", "vite", "dev"],
            cwd=daw_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, "PORT": "5174"}
        )
        await asyncio.sleep(3)

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-web-security",
                "--enable-features=SharedArrayBuffer",
            ]
        )
        self.page = await self.browser.new_page()
        logger.info("Loading DAW at http://localhost:5174 ...")
        await self.page.goto("http://localhost:5174")
        await self.page.wait_for_function(
            "typeof window.DAW !== 'undefined'", timeout=30000
        )
        logger.info("DAW engine ready (sampleRate=44100)")

    async def evaluate(self, script: str):
        """Execute JS in the DAW's V8 context. `_proj` = window.DAW."""
        if not self.page:
            await self.start()
        try:
            return await self.page.evaluate(f"""async () => {{
                try {{
                    const _proj = window.DAW;
                    const _ef = window.DAW_EffectFactories;
                    {script}
                }} catch (e) {{
                    return {{ error: e.message }};
                }}
            }}""")
        except Exception as e:
            return {"error": str(e)}

    async def stop(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        if self.vite_process:
            self.vite_process.terminate()

bridge = HeadlessDawBridge()

def cleanup():
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(bridge.stop(), loop)
    except RuntimeError:
        asyncio.run(bridge.stop())
atexit.register(cleanup)


# ── Transport & Engine ──────────────────────────────────────

@mcp.tool()
async def mcp_opendaw_transport(action: str) -> str:
    """Control DAW transport: 'play', 'stop', or 'setPosition'."""
    if action not in ("play", "stop"):
        return "Error: action must be 'play' or 'stop'"
    return str(await bridge.evaluate(f"""
        _proj.engine.{action}();
        return '{action} executed';
    """))

@mcp.tool()
async def mcp_opendaw_set_bpm(bpm: float) -> str:
    """Set the project tempo in BPM."""
    return str(await bridge.evaluate(f"""
        _proj.editing.modify(() => _proj.api.setBpm({bpm}));
        return 'BPM set to {bpm}';
    """))

@mcp.tool()
async def mcp_opendaw_get_engine_state() -> str:
    """Get current engine state: sampleRate, bpm, isPlaying, position, cpuLoad."""
    return str(await bridge.evaluate("""
        const eng = _proj.engine;
        return {
            sampleRate: eng.sampleRate,
            isPlaying: !!eng.isPlaying,
            cpuLoad: eng.cpuLoad,
        };
    """))


# ── Track Management ────────────────────────────────────────

@mcp.tool()
async def mcp_opendaw_create_audio_track() -> str:
    """Create a new audio track on the primary audio unit."""
    return str(await bridge.evaluate("""
        let trackBox;
        _proj.editing.modify(() => {
            trackBox = _proj.api.createAudioTrack(_proj.primaryAudioUnitBox);
        });
        return trackBox ? 'Audio track created' : 'Failed';
    """))

@mcp.tool()
async def mcp_opendaw_create_note_track() -> str:
    """Create a new MIDI/note track on the primary audio unit."""
    return str(await bridge.evaluate("""
        let trackBox;
        _proj.editing.modify(() => {
            trackBox = _proj.api.createNoteTrack(_proj.primaryAudioUnitBox);
        });
        return trackBox ? 'Note track created' : 'Failed';
    """))

@mcp.tool()
async def mcp_opendaw_list_boxes() -> str:
    """List all boxes in the project graph (tracks, effects, buses, etc.)."""
    return str(await bridge.evaluate("""
        const allBoxes = [..._proj.boxGraph.boxes()];
        return allBoxes.map(b => ({
            type: b.constructor?.name || 'unknown',
        }));
    """))


# ── Effects ─────────────────────────────────────────────────

@mcp.tool()
async def mcp_opendaw_insert_audio_effect(effect_name: str) -> str:
    """Insert an audio effect on the primary audio unit.
    Available: Compressor, Crusher, DattorroReverb, Delay, Fold, Gate,
    Maximizer, NeuralAmp, Reverb, Revamp, StereoTool, Tidal, Vocoder,
    Waveshaper, Werkstatt"""
    return str(await bridge.evaluate(f"""
        const factory = _ef.AudioNamed["{effect_name}"];
        if (!factory) return {{ error: 'Unknown effect: {effect_name}' }};
        let box;
        _proj.editing.modify(() => {{
            box = _proj.api.insertEffect(
                _proj.primaryAudioUnitBox.audioEffects,
                factory
            );
        }});
        return box ? '{effect_name} inserted' : 'Failed';
    """))

@mcp.tool()
async def mcp_opendaw_insert_midi_effect(effect_name: str) -> str:
    """Insert a MIDI effect. Available: Arpeggio, Pitch, Spielwerk, Velocity, Zeitgeist"""
    return str(await bridge.evaluate(f"""
        const factory = _ef.MidiNamed["{effect_name}"];
        if (!factory) return {{ error: 'Unknown MIDI effect: {effect_name}' }};
        let box;
        _proj.editing.modify(() => {{
            box = _proj.api.insertEffect(
                _proj.primaryAudioUnitBox.midiEffects,
                factory
            );
        }});
        return box ? '{effect_name} inserted' : 'Failed';
    """))

@mcp.tool()
async def mcp_opendaw_list_effects() -> str:
    """List all available effect names (audio + MIDI)."""
    return str(await bridge.evaluate("""
        return {
            audio: Object.keys(_ef.AudioNamed),
            midi: Object.keys(_ef.MidiNamed),
        };
    """))


# ── Mixing ──────────────────────────────────────────────────

@mcp.tool()
async def mcp_opendaw_set_volume(volume_db: float) -> str:
    """Set the primary audio unit volume in dB (0.0 = unity, -12.0 = reduction)."""
    return str(await bridge.evaluate(f"""
        _proj.editing.modify(() => {{
            _proj.primaryAudioUnitBox.volume.setValue({volume_db});
        }});
        return 'Volume set to {volume_db} dB';
    """))

@mcp.tool()
async def mcp_opendaw_set_panning(pan: float) -> str:
    """Set the primary audio unit panning (-1.0 = full left, 0.0 = center, 1.0 = full right)."""
    return str(await bridge.evaluate(f"""
        _proj.editing.modify(() => {{
            _proj.primaryAudioUnitBox.panning.setValue({pan});
        }});
        return 'Panning set to {pan}';
    """))

@mcp.tool()
async def mcp_opendaw_set_mute(muted: bool) -> str:
    """Mute or unmute the primary audio unit."""
    val = "true" if muted else "false"
    return str(await bridge.evaluate(f"""
        _proj.editing.modify(() => {{
            _proj.primaryAudioUnitBox.mute.setValue({val});
        }});
        return 'Mute set to {val}';
    """))

@mcp.tool()
async def mcp_opendaw_set_solo(solo: bool) -> str:
    """Solo or unsolo the primary audio unit."""
    val = "true" if solo else "false"
    return str(await bridge.evaluate(f"""
        _proj.editing.modify(() => {{
            _proj.primaryAudioUnitBox.solo.setValue({val});
        }});
        return 'Solo set to {val}';
    """))


# ── Undo/Redo ───────────────────────────────────────────────

@mcp.tool()
async def mcp_opendaw_undo() -> str:
    """Undo the last editing operation."""
    return str(await bridge.evaluate("""
        _proj.editing.undo();
        return 'Undo executed';
    """))

@mcp.tool()
async def mcp_opendaw_redo() -> str:
    """Redo the last undone operation."""
    return str(await bridge.evaluate("""
        _proj.editing.redo();
        return 'Redo executed';
    """))


# ── Export ───────────────────────────────────────────────────

@mcp.tool()
async def mcp_opendaw_export_audio(filename: str = "export.wav") -> str:
    """Export the project audio to a WAV file."""
    return str(await bridge.evaluate(f"""
        const result = await _proj.api.exportAudio(_proj, "{filename}");
        return {{ exported: true, filename: "{filename}" }};
    """))


# ── Raw Evaluate (escape hatch) ─────────────────────────────

@mcp.tool()
async def mcp_opendaw_evaluate(script: str) -> str:
    """Execute arbitrary JavaScript in the DAW context.
    Available globals: _proj (Project), _ef (EffectFactories).
    Must return a JSON-serializable value."""
    return str(await bridge.evaluate(script))


if __name__ == "__main__":
    mcp.run()
