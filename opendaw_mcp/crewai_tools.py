"""CrewAI tool wrappers for opendaw-mcp.

Usage:
    from opendaw_mcp.crewai_tools import get_crewai_tools

    tools = get_crewai_tools()

    # Use with CrewAI agents
    from crewai import Agent, Task, Crew

    producer = Agent(
        role="Music Producer",
        goal="Create and mix music tracks",
        backstory="Expert producer with 20 years experience",
        tools=tools,
        llm=llm
    )

    task = Task(
        description="Create a dark techno track at 130 BPM and render it",
        agent=producer,
        expected_output="A WAV file with the finished track"
    )

    crew = Crew(agents=[producer], tasks=[task])
    result = crew.kickoff()

Requirements:
    pip install opendaw-mcp crewai
"""

import json
import asyncio
from typing import Optional, Any

try:
    from crewai.tools import BaseTool as CrewAIBaseTool
    CREWAI_AVAILABLE = True
except ImportError:
    try:
        from crewai_tools import BaseTool as CrewAIBaseTool
        CREWAI_AVAILABLE = True
    except ImportError:
        CREWAI_AVAILABLE = False
        CrewAIBaseTool = object  # type: ignore

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
    def wrapper(**kwargs) -> str:
        return asyncio.run(_call_async(tool_name, **kwargs))
    wrapper.__name__ = f"opendaw_{tool_name}"
    return wrapper


class OpendawCrewAITool(CrewAIBaseTool if CREWAI_AVAILABLE else object):
    """Wrapper for a single opendaw-mcp tool as a CrewAI BaseTool."""

    name: str = ""
    description: str = ""
    _func: Any = None

    def __init__(self, name: str, description: str, func, **kwargs):
        if CREWAI_AVAILABLE:
            super().__init__(name=name, description=description, **kwargs)
        self._func = func

    def _run(self, **kwargs) -> str:
        return self._func(**kwargs)


# ─── Tool definitions ─────────────────────────────────────────────

_TOOL_DEFS = [
    {"name": "opendaw_set_bpm",
     "description": "Set the project tempo in BPM (60-240). Use when changing the speed of the track.",
     "tool": "set_bpm", "args": {"bpm": float}},
    {"name": "opendaw_transport",
     "description": "Control playback: 'play', 'stop', or 'toggle'.",
     "tool": "transport", "args": {"action": str}},
    {"name": "opendaw_set_time_signature",
     "description": "Set time signature (e.g. 4/4, 3/4, 6/8).",
     "tool": "set_time_signature", "args": {"numerator": int, "denominator": int}},
    {"name": "opendaw_create_synth_track",
     "description": "Create a new synthesizer track. Returns unit_index. Use when adding a new instrument.",
     "tool": "create_synth_track", "args": {"name": str}},
    {"name": "opendaw_create_audio_track",
     "description": "Create a new audio track on the primary audio unit.",
     "tool": "create_audio_track", "args": {}},
    {"name": "opendaw_list_tracks",
     "description": "List all tracks with their type, effects, and regions. Use to inspect the current project.",
     "tool": "list_tracks", "args": {}},
    {"name": "opendaw_add_effect",
     "description": "Add an audio effect to a track. Types: Delay, Dattorro (reverb), Compressor, Waveshaper, Crusher, Fold, StereoTool, Revamp (EQ), Tidal (LFO), Vocoder, NeuralAmp, Maximizer, Modular, Werkstatt.",
     "tool": "add_effect", "args": {"unit_index": int, "effect_type": str}},
    {"name": "opendaw_set_effect_parameter",
     "description": "Set a parameter on an audio effect. Use opendaw_list_effect_parameters first to see available params.",
     "tool": "set_effect_parameter", "args": {"unit_index": int, "effect_index": int, "param": str, "value": float}},
    {"name": "opendaw_list_effect_parameters",
     "description": "List all parameters of an effect with current values and ranges.",
     "tool": "list_effect_parameters", "args": {"unit_index": int, "effect_index": int}},
    {"name": "opendaw_create_note",
     "description": "Create a MIDI note. Pitch: 60=C4, 62=D4, 64=E4, 67=G4, 72=C5. Position/duration in PPQN (960=quarter note). Velocity 0.0-1.0.",
     "tool": "create_note",
     "args": {"unit_index": int, "track_index": int, "region_index": int, "pitch": int, "position": int, "duration": int, "velocity": float}},
    {"name": "opendaw_list_notes",
     "description": "List all MIDI notes in a region.",
     "tool": "list_notes", "args": {"unit_index": int, "track_index": int, "region_index": int}},
    {"name": "opendaw_quantize_notes",
     "description": "Quantize note positions to a grid. Division in PPQN: 960=quarter, 480=8th, 240=16th.",
     "tool": "quantize_notes", "args": {"unit_index": int, "track_index": int, "region_index": int, "division": int}},
    {"name": "opendaw_set_track_volume",
     "description": "Set track volume in dB. 0=unity, -6=half volume, +6=double. Range: -96 to +6.",
     "tool": "set_track_volume", "args": {"unit_index": int, "volume_db": float}},
    {"name": "opendaw_set_track_panning",
     "description": "Set track panning. -1.0=full left, 0.0=center, 1.0=full right.",
     "tool": "set_track_panning", "args": {"unit_index": int, "panning": float}},
    {"name": "opendaw_set_track_mute",
     "description": "Mute (true) or unmute (false) a track.",
     "tool": "set_track_mute", "args": {"unit_index": int, "muted": bool}},
    {"name": "opendaw_get_mixer_state",
     "description": "Get the full mixer state — all tracks with volume, pan, mute, solo. Use to inspect the mix.",
     "tool": "get_mixer_state", "args": {}},
    {"name": "opendaw_render_full",
     "description": "Render the entire project as a stereo WAV file. Use when the track is finished.",
     "tool": "render_full", "args": {"output_path": str}},
    {"name": "opendaw_export_stems",
     "description": "Export each track as a separate stem WAV file. Use for stem delivery or remixing.",
     "tool": "export_stems", "args": {"output_dir": str}},
    {"name": "opendaw_measure_lufs",
     "description": "Measure LUFS (loudness) and true peak of a WAV file. Spotify target: -14 LUFS, Apple: -16.",
     "tool": "measure_lufs", "args": {"file_path": str}},
    {"name": "opendaw_auto_gain",
     "description": "Auto-adjust output volume to hit a target LUFS. Use for mastering to streaming platforms.",
     "tool": "auto_gain", "args": {"target_lufs": float}},
    {"name": "opendaw_create_drum_pattern",
     "description": "Create a drum beat from compact notation. x=hit, o=accent, .=rest, X=ghost. Lanes separated by | (kick|snare|hihat). Each lane = 16 steps (one bar of 16th notes). Example: 'x...x...x...x...|o.......o.....o.|..x...x...x...x.'",
     "tool": "create_drum_pattern", "args": {"pattern": str, "unit_index": int}},
    {"name": "opendaw_create_notes_batch",
     "description": "Create multiple MIDI notes from a list in one call. More efficient than calling create_note repeatedly. Each note: {pitch, position, duration, velocity?}.",
     "tool": "create_notes_batch", "args": {"notes": list, "unit_index": int, "track_index": int}},
    {"name": "opendaw_create_chord_progression",
     "description": "Create chords from names — auto-voiced and positioned. Examples: Cm, Fm7, Gdom7, Am7, Dmaj7.",
     "tool": "create_chord_progression", "args": {"chords": list, "unit_index": int, "track_index": int, "duration": int}},
    {"name": "opendaw_add_mastering_chain",
     "description": "Add EQ + Compressor + Maximizer to the output bus with a style preset. Styles: balanced, warm, loud, transparent.",
     "tool": "add_mastering_chain", "args": {"style": str}},
    {"name": "opendaw_create_song_structure",
     "description": "Create arrangement markers (intro/verse/chorus/bridge/outro) from a section list. Each section: {name, length_in_bars}.",
     "tool": "create_song_structure", "args": {"sections": list}},
    {"name": "opendaw_automation_sweep",
     "description": "Create a smooth automation ramp (filter sweep, volume fade) in one call. Curves: linear, exp, log.",
     "tool": "automation_sweep",
     "args": {"unit_index": int, "effect_index": int, "param_name": str, "start_position": int, "end_position": int, "start_value": float, "end_value": float, "curve": str}},
    {"name": "opendaw_apply_mix_preset",
     "description": "Apply volume/pan/mute/solo to all tracks at once. Named presets: lofi, house, balanced, wide. Or pass custom JSON.",
     "tool": "apply_mix_preset", "args": {"preset": str}},
    {"name": "opendaw_split_stems",
     "description": "Split an audio file into stems using SOTA AI models (BS-Roformer, HTDemucs, SCNet). Modes: ensemble, scnet, bs6, polarformer, dereverb, drumsep, denoise. Runs on GPU. Optional auto-import into DAW.",
     "tool": "split_stems", "args": {"file_path": str, "mode": str, "auto_import": bool}},
]

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


def get_crewai_tools(categories: Optional[list[str]] = None) -> list[CrewAIBaseTool]:
    """Get CrewAI tools for opendaw-mcp.

    Args:
        categories: Filter by category. None = all tools.
                    Options: "transport", "tracks", "effects", "notes",
                    "mixer", "export", "orchestration", "stems"

    Returns:
        List of CrewAI BaseTool objects.

    Raises:
        ImportError: If crewai is not installed.
    """
    if not CREWAI_AVAILABLE:
        raise ImportError(
            "crewai is not installed. Install with: pip install crewai"
        )

    allowed_names = None
    if categories:
        allowed_names = set()
        for cat in categories:
            allowed_names.update(_CATEGORY_MAP.get(cat, []))

    tools = []
    for defn in _TOOL_DEFS:
        if allowed_names and defn["name"] not in allowed_names:
            continue
        tool = OpendawCrewAITool(
            name=defn["name"],
            description=defn["description"],
            func=_make_sync(defn["tool"]),
        )
        tools.append(tool)

    return tools


async def cleanup():
    """Stop the DAW bridge. Call when done with the tools."""
    global _server
    if _server is not None:
        await _server.bridge.stop()
        _server = None
