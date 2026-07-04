"""AutoGen tool wrappers for opendaw-mcp.

Usage:
    from opendaw_mcp.autogen_tools import get_autogen_tools

    tools = get_autogen_tools()

    # Register with AutoGen assistant agent
    from autogen import AssistantAgent, UserProxyAgent

    assistant = AssistantAgent("producer", llm_config=llm_config, tools=tools)
    user = UserProxyAgent("user", human_input_mode="NEVER")
    user.initiate_chat(assistant, message="Create a house beat at 124 BPM and render it")

Requirements:
    pip install opendaw-mcp autogen-agentchat
"""

import json
import asyncio
from typing import Optional

try:
    from autogen.tools import Tool as AutoGenTool
    AUTOGEN_AVAILABLE = True
except ImportError:
    try:
        from autogen_core.tools import FunctionTool as AutoGenTool
        AUTOGEN_AVAILABLE = True
    except ImportError:
        AUTOGEN_AVAILABLE = False
        AutoGenTool = None  # type: ignore

from server import OpendawServer


_server: Optional[OpendawServer] = None


async def _get_server() -> OpendawServer:
    global _server
    if _server is None:
        _server = OpendawServer()
        await _server.bridge.start()
    return _server


async def _call_async(tool_name: str, **kwargs) -> str:
    server = await _get_server()
    method = getattr(server, f"mcp_opendaw_{tool_name}")
    result = await method(**kwargs)
    if isinstance(result, str):
        return result
    return json.dumps(result, ensure_ascii=False)


def _make_sync(tool_name: str):
    """Create a sync wrapper around an async MCP tool."""
    def wrapper(**kwargs) -> str:
        return asyncio.run(_call_async(tool_name, **kwargs))
    wrapper.__name__ = f"opendaw_{tool_name}"
    return wrapper


# ─── Tool definitions ─────────────────────────────────────────────

_TOOL_DEFS = [
    # Transport
    {
        "name": "opendaw_set_bpm",
        "description": "Set the project tempo in BPM (60-240). Use when changing the speed/tempo of the track.",
        "func": _make_sync("set_bpm"),
        "args": {"bpm": float},
    },
    {
        "name": "opendaw_transport",
        "description": "Control playback: 'play', 'stop', or 'toggle'.",
        "func": _make_sync("transport"),
        "args": {"action": str},
    },
    {
        "name": "opendaw_set_time_signature",
        "description": "Set time signature (e.g. 4/4, 3/4, 6/8).",
        "func": _make_sync("set_time_signature"),
        "args": {"numerator": int, "denominator": int},
    },
    # Tracks
    {
        "name": "opendaw_create_synth_track",
        "description": "Create a new synthesizer track. Returns unit_index. Use when adding a new instrument.",
        "func": _make_sync("create_synth_track"),
        "args": {"name": str},
    },
    {
        "name": "opendaw_create_audio_track",
        "description": "Create a new audio track on the primary audio unit.",
        "func": _make_sync("create_audio_track"),
        "args": {},
    },
    {
        "name": "opendaw_list_tracks",
        "description": "List all tracks with their type, effects, and regions. Use to inspect the current project.",
        "func": _make_sync("list_tracks"),
        "args": {},
    },
    # Effects
    {
        "name": "opendaw_add_effect",
        "description": "Add an audio effect to a track. Types: Delay, Dattorro (reverb), Compressor, Waveshaper, Crusher, Fold, StereoTool, Revamp (EQ), Tidal (LFO), Vocoder, NeuralAmp, Maximizer, Modular, Werkstatt.",
        "func": _make_sync("add_effect"),
        "args": {"unit_index": int, "effect_type": str},
    },
    {
        "name": "opendaw_set_effect_parameter",
        "description": "Set a parameter on an audio effect. Use opendaw_list_effect_parameters first to see available params.",
        "func": _make_sync("set_effect_parameter"),
        "args": {"unit_index": int, "effect_index": int, "param": str, "value": float},
    },
    {
        "name": "opendaw_list_effect_parameters",
        "description": "List all parameters of an effect with current values and ranges.",
        "func": _make_sync("list_effect_parameters"),
        "args": {"unit_index": int, "effect_index": int},
    },
    # Notes
    {
        "name": "opendaw_create_note",
        "description": "Create a MIDI note. Pitch: 60=C4, 62=D4, 64=E4, 67=G4, 72=C5. Position/duration in PPQN (960=quarter note). Velocity 0.0-1.0.",
        "func": _make_sync("create_note"),
        "args": {"unit_index": int, "track_index": int, "region_index": int, "pitch": int, "position": int, "duration": int, "velocity": float},
    },
    {
        "name": "opendaw_list_notes",
        "description": "List all MIDI notes in a region.",
        "func": _make_sync("list_notes"),
        "args": {"unit_index": int, "track_index": int, "region_index": int},
    },
    {
        "name": "opendaw_quantize_notes",
        "description": "Quantize note positions to a grid. Division in PPQN: 960=quarter, 480=8th, 240=16th.",
        "func": _make_sync("quantize_notes"),
        "args": {"unit_index": int, "track_index": int, "region_index": int, "division": int},
    },
    # Mixer
    {
        "name": "opendaw_set_track_volume",
        "description": "Set track volume in dB. 0=unity, -6=half volume, +6=double. Range: -96 to +6.",
        "func": _make_sync("set_track_volume"),
        "args": {"unit_index": int, "volume_db": float},
    },
    {
        "name": "opendaw_set_track_panning",
        "description": "Set track panning. -1.0=full left, 0.0=center, 1.0=full right.",
        "func": _make_sync("set_track_panning"),
        "args": {"unit_index": int, "panning": float},
    },
    {
        "name": "opendaw_set_track_mute",
        "description": "Mute (true) or unmute (false) a track.",
        "func": _make_sync("set_track_mute"),
        "args": {"unit_index": int, "muted": bool},
    },
    {
        "name": "opendaw_get_mixer_state",
        "description": "Get the full mixer state — all tracks with volume, pan, mute, solo. Use to inspect the mix.",
        "func": _make_sync("get_mixer_state"),
        "args": {},
    },
    # Export
    {
        "name": "opendaw_render_full",
        "description": "Render the entire project as a stereo WAV file. Use when the track is finished.",
        "func": _make_sync("render_full"),
        "args": {"output_path": str},
    },
    {
        "name": "opendaw_export_stems",
        "description": "Export each track as a separate stem WAV file. Use for stem delivery or remixing.",
        "func": _make_sync("export_stems"),
        "args": {"output_dir": str},
    },
    {
        "name": "opendaw_measure_lufs",
        "description": "Measure LUFS (loudness) and true peak of a WAV file. Spotify target: -14 LUFS, Apple: -16.",
        "func": _make_sync("measure_lufs"),
        "args": {"file_path": str},
    },
    {
        "name": "opendaw_auto_gain",
        "description": "Auto-adjust output volume to hit a target LUFS. Use for mastering to streaming platforms.",
        "func": _make_sync("auto_gain"),
        "args": {"target_lufs": float},
    },
    # Orchestration
    {
        "name": "opendaw_create_drum_pattern",
        "description": "Create a drum beat from compact notation. x=hit, o=accent, .=rest, X=ghost. Lanes separated by | (kick|snare|hihat). Each lane = 16 steps (one bar of 16th notes). Example: 'x...x...x...x...|o.......o.....o.|..x...x...x...x.'",
        "func": _make_sync("create_drum_pattern"),
        "args": {"pattern": str, "unit_index": int},
    },
    {
        "name": "opendaw_create_notes_batch",
        "description": "Create multiple MIDI notes from a list in one call. More efficient than calling create_note repeatedly. Each note: {pitch, position, duration, velocity?}.",
        "func": _make_sync("create_notes_batch"),
        "args": {"notes": list, "unit_index": int, "track_index": int},
    },
    {
        "name": "opendaw_create_chord_progression",
        "description": "Create chords from names — auto-voiced and positioned. Examples: Cm, Fm7, Gdom7, Am7, Dmaj7.",
        "func": _make_sync("create_chord_progression"),
        "args": {"chords": list, "unit_index": int, "track_index": int, "duration": int},
    },
    {
        "name": "opendaw_add_mastering_chain",
        "description": "Add EQ + Compressor + Maximizer to the output bus with a style preset. Styles: balanced, warm, loud, transparent.",
        "func": _make_sync("add_mastering_chain"),
        "args": {"style": str},
    },
    {
        "name": "opendaw_create_song_structure",
        "description": "Create arrangement markers (intro/verse/chorus/bridge/outro) from a section list. Each section: {name, length_in_bars}.",
        "func": _make_sync("create_song_structure"),
        "args": {"sections": list},
    },
    {
        "name": "opendaw_automation_sweep",
        "description": "Create a smooth automation ramp (filter sweep, volume fade) in one call. Curves: linear, exp, log.",
        "func": _make_sync("automation_sweep"),
        "args": {"unit_index": int, "effect_index": int, "param_name": str, "start_position": int, "end_position": int, "start_value": float, "end_value": float, "curve": str},
    },
    {
        "name": "opendaw_apply_mix_preset",
        "description": "Apply volume/pan/mute/solo to all tracks at once. Named presets: lofi, house, balanced, wide. Or pass custom JSON.",
        "func": _make_sync("apply_mix_preset"),
        "args": {"preset": str},
    },
    # Stems
    {
        "name": "opendaw_split_stems",
        "description": "Split an audio file into stems using SOTA AI models (BS-Roformer, HTDemucs, SCNet). Modes: ensemble, scnet, bs6, polarformer, dereverb, drumsep, denoise. Runs on GPU. Optional auto-import into DAW.",
        "func": _make_sync("split_stems"),
        "args": {"file_path": str, "mode": str, "auto_import": bool},
    },
]


def get_autogen_tools(categories: Optional[list[str]] = None) -> list:
    """Get AutoGen tools for opendaw-mcp.

    Args:
        categories: Filter by category. None = all tools.
                    Options: "transport", "tracks", "effects", "notes",
                    "mixer", "export", "orchestration", "stems"

    Returns:
        List of AutoGen Tool/FunctionTool objects.

    Raises:
        ImportError: If autogen is not installed.
    """
    if not AUTOGEN_AVAILABLE:
        raise ImportError(
            "autogen is not installed. Install with: pip install autogen-agentchat"
        )

    # Category mapping (same as LangChain toolkit)
    _CATEGORY_MAP = {
        "transport": ["opendaw_set_bpm", "opendaw_transport", "opendaw_set_time_signature"],
        "tracks": ["opendaw_create_synth_track", "opendaw_create_audio_track", "opendaw_list_tracks"],
        "effects": ["opendaw_add_effect", "opendaw_set_effect_parameter", "opendaw_list_effect_parameters"],
        "notes": ["opendaw_create_note", "opendaw_list_notes", "opendaw_quantize_notes"],
        "mixer": ["opendaw_set_track_volume", "opendaw_set_track_panning", "opendaw_set_track_mute", "opendaw_get_mixer_state"],
        "export": ["opendaw_render_full", "opendaw_export_stems", "opendaw_measure_lufs", "opendaw_auto_gain"],
        "orchestration": ["opendaw_create_drum_pattern", "opendaw_create_notes_batch", "opendaw_create_chord_progression",
                          "opendaw_add_mastering_chain", "opendaw_create_song_structure", "opendaw_automation_sweep",
                          "opendaw_apply_mix_preset"],
        "stems": ["opendaw_split_stems"],
    }

    allowed_names = None
    if categories:
        allowed_names = set()
        for cat in categories:
            allowed_names.update(_CATEGORY_MAP.get(cat, []))

    tools = []
    for defn in _TOOL_DEFS:
        if allowed_names and defn["name"] not in allowed_names:
            continue

        # AutoGen v0.2+ Tool format
        try:
            tool = AutoGenTool(
                name=defn["name"],
                description=defn["description"],
                func_or_tool=defn["func"],
                args=defn["args"],
            )
        except TypeError:
            # AutoGen v0.4+ FunctionTool format
            tool = AutoGenTool(
                func=defn["func"],
                name=defn["name"],
                description=defn["description"],
            )
        tools.append(tool)

    return tools


async def cleanup():
    """Stop the DAW bridge. Call when done with the tools."""
    global _server
    if _server is not None:
        await _server.bridge.stop()
        _server = None
