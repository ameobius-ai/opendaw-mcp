"""LangChain tool wrappers for opendaw-mcp.

Usage:
    from opendaw_mcp.langchain_tools import OpendawToolkit

    toolkit = OpendawToolkit()
    tools = toolkit.get_tools()

    # Use with LangChain agent
    from langchain.agents import initialize_agent
    agent = initialize_agent(tools, llm, agent="zero-shot-react-description")
    agent.run("Create a house beat at 124 BPM and render it")
"""

import json
import asyncio
from typing import Optional

try:
    from langchain.tools import BaseTool, StructuredTool
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    BaseTool = object  # type: ignore

from server import OpendawServer


class OpendawToolkit:
    """Wraps opendaw-mcp MCP tools as LangChain Tool objects.

    Automatically starts the bridge on first use.

    Args:
        daw_url: URL of the openDAW dev server (default: http://localhost:5174)
        auto_start: Start the bridge automatically on first tool call
    """

    def __init__(self, daw_url: str = "http://localhost:5174", auto_start: bool = True):
        self.server = OpendawServer(daw_url=daw_url)
        self._auto_start = auto_start
        self._started = False

    async def _ensure_started(self):
        if self._auto_start and not self._started:
            await self.server.bridge.start()
            self._started = True

    async def _call_tool(self, tool_name: str, **kwargs) -> str:
        await self._ensure_started()
        method = getattr(self.server, f"mcp_opendaw_{tool_name}")
        result = await method(**kwargs)
        if isinstance(result, str):
            return result
        return json.dumps(result, ensure_ascii=False)

    def get_tools(self, categories: Optional[list[str]] = None) -> list[BaseTool]:
        """Get LangChain tools for opendaw-mcp.

        Args:
            categories: Filter by category. None = all tools.
                       Options: "transport", "tracks", "effects", "notes",
                       "mixer", "automation", "export", "orchestration", etc.

        Returns:
            List of LangChain Tool objects.
        """
        if not LANGCHAIN_AVAILABLE:
            raise ImportError(
                "langchain is not installed. Install with: pip install langchain"
            )

        tool_specs = _get_tool_specs(categories)
        tools = []

        for spec in tool_specs:
            def make_fn(name=spec["name"]):
                async def _async_fn(**kwargs) -> str:
                    return await self._call_tool(name, **kwargs)

                def _sync_fn(**kwargs) -> str:
                    return asyncio.run(_async_fn(**kwargs))

                _sync_fn.__name__ = f"opendaw_{name}"
                _sync_fn.__doc__ = spec["description"]
                return _sync_fn

            tool = StructuredTool.from_function(
                make_fn(),
                name=f"opendaw_{spec['name']}",
                description=spec["description"],
                args_schema=spec.get("args_schema"),
            )
            tools.append(tool)

        return tools


# ─── Tool specifications ────────────────────────────────────────────

_TRANSPORT_TOOLS = [
    {"name": "set_bpm", "description": "Set the project tempo in BPM (60-240). Use for changing the speed of the track.",
     "args": {"bpm": {"type": "float", "description": "Tempo in BPM"}}},
    {"name": "transport", "description": "Control playback: play, stop, or toggle.",
     "args": {"action": {"type": "str", "description": "play, stop, or toggle"}}},
    {"name": "set_time_signature", "description": "Set time signature (e.g. 4/4, 3/4, 6/8).",
     "args": {"numerator": {"type": "int"}, "denominator": {"type": "int"}}},
    {"name": "set_position", "description": "Set playback position in beats.",
     "args": {"position": {"type": "float"}}},
]

_TRACK_TOOLS = [
    {"name": "create_synth_track", "description": "Create a new synthesizer track with a note track. Returns unit_index.",
     "args": {"name": {"type": "str", "description": "Track name"}}},
    {"name": "create_audio_track", "description": "Create a new audio track on the primary audio unit.",
     "args": {}},
    {"name": "create_note_track", "description": "Create a note/MIDI track on an audio unit.",
     "args": {"unit_index": {"type": "int"}}},
    {"name": "list_tracks", "description": "List all tracks across all audio units with their type and effects.",
     "args": {}},
    {"name": "delete_track", "description": "Delete a track and all its regions, clips, and notes.",
     "args": {"unit_index": {"type": "int"}, "track_index": {"type": "int"}}},
]

_EFFECT_TOOLS = [
    {"name": "add_effect", "description": "Add an audio effect (Delay, Dattorro/reverb, Compressor, Waveshaper, Crusher, etc.) to a track's effect chain.",
     "args": {"unit_index": {"type": "int"}, "effect_type": {"type": "str", "description": "Effect name (case-insensitive)"}}},
    {"name": "set_effect_parameter", "description": "Set a parameter on an audio effect. Use list_effect_parameters first to see available params.",
     "args": {"unit_index": {"type": "int"}, "effect_index": {"type": "int"}, "param": {"type": "str"}, "value": {"type": "float"}}},
    {"name": "list_effect_parameters", "description": "List all parameters of an effect with current values.",
     "args": {"unit_index": {"type": "int"}, "effect_index": {"type": "int"}}},
    {"name": "remove_effect", "description": "Remove an audio effect from a track.",
     "args": {"unit_index": {"type": "int"}, "effect_index": {"type": "int"}}},
]

_NOTE_TOOLS = [
    {"name": "create_note", "description": "Create a MIDI note. Pitch 60=C4, 62=D4, 64=E4, 67=G4. Position/duration in PPQN (960=quarter note).",
     "args": {"unit_index": {"type": "int"}, "track_index": {"type": "int"}, "region_index": {"type": "int"},
              "pitch": {"type": "int", "description": "MIDI pitch 0-127"}, "position": {"type": "int", "description": "PPQN position"},
              "duration": {"type": "int", "description": "PPQN duration"}, "velocity": {"type": "float", "description": "0.0-1.0"}}},
    {"name": "list_notes", "description": "List all notes in a region.",
     "args": {"unit_index": {"type": "int"}, "track_index": {"type": "int"}, "region_index": {"type": "int"}}},
    {"name": "quantize_notes", "description": "Quantize note positions to a grid division.",
     "args": {"unit_index": {"type": "int"}, "track_index": {"type": "int"}, "region_index": {"type": "int"},
              "division": {"type": "int", "description": "Grid in PPQN (480=8th, 240=16th)"}}},
]

_MIXER_TOOLS = [
    {"name": "set_track_volume", "description": "Set track volume in dB (0=unity, -6=half, +6=double).",
     "args": {"unit_index": {"type": "int"}, "volume_db": {"type": "float"}}},
    {"name": "set_track_panning", "description": "Set track panning (-1.0=full left, 0.0=center, 1.0=full right).",
     "args": {"unit_index": {"type": "int"}, "panning": {"type": "float"}}},
    {"name": "set_track_mute", "description": "Mute or unmute a track.",
     "args": {"unit_index": {"type": "int"}, "muted": {"type": "bool"}}},
    {"name": "get_mixer_state", "description": "Get the full mixer state — all tracks with volume, pan, mute, solo.",
     "args": {}},
]

_EXPORT_TOOLS = [
    {"name": "render_full", "description": "Render the entire project as a stereo WAV file.",
     "args": {"output_path": {"type": "str"}}},
    {"name": "export_stems", "description": "Export each track as a separate stem WAV file.",
     "args": {"output_dir": {"type": "str"}}},
    {"name": "measure_lufs", "description": "Measure LUFS (loudness) and true peak of a WAV file. Spotify target: -14 LUFS.",
     "args": {"file_path": {"type": "str"}}},
    {"name": "auto_gain", "description": "Auto-adjust output volume to hit a target LUFS.",
     "args": {"target_lufs": {"type": "float"}}},
]

_ORCHESTRATION_TOOLS = [
    {"name": "create_drum_pattern", "description": "Create a drum beat from compact notation. x=hit, o=accent, .=rest. Lanes separated by | (kick|snare|hihat). Each lane=16 steps.",
     "args": {"pattern": {"type": "str", "description": "e.g. 'x...x...x...x...|o.......o.....o.|..x...x...x...x.'"},
              "unit_index": {"type": "int"}}},
    {"name": "create_notes_batch", "description": "Create multiple MIDI notes from a JSON array in one call. More efficient than calling create_note repeatedly.",
     "args": {"notes": {"type": "list", "description": "List of {pitch, position, duration, velocity?}"},
              "unit_index": {"type": "int"}, "track_index": {"type": "int"}}},
    {"name": "create_chord_progression", "description": "Create chords from names (Cm, Fm7, Gdom7, etc.) — auto-voiced and positioned.",
     "args": {"chords": {"type": "list", "description": "List of chord names"},
              "unit_index": {"type": "int"}, "track_index": {"type": "int"}, "duration": {"type": "int"}}},
    {"name": "add_mastering_chain", "description": "Add EQ + Compressor + Maximizer to the output bus with a style preset.",
     "args": {"style": {"type": "str", "description": "balanced, warm, loud, or transparent"}}},
    {"name": "create_song_structure", "description": "Create arrangement markers (intro/verse/chorus/bridge/outro) from a section list.",
     "args": {"sections": {"type": "list", "description": "List of {name, length}"}}},
]

_STEM_TOOLS = [
    {"name": "split_stems", "description": "Split an audio file into stems using SOTA AI models (BS-Roformer, HTDemucs, SCNet). 7 modes. Runs on GPU. Optional auto-import into DAW.",
     "args": {"file_path": {"type": "str"}, "mode": {"type": "str", "description": "ensemble, scnet, bs6, polarformer, dereverb, drumsep, denoise"},
              "auto_import": {"type": "bool"}}},
]

_ALL_CATEGORIES = {
    "transport": _TRANSPORT_TOOLS,
    "tracks": _TRACK_TOOLS,
    "effects": _EFFECT_TOOLS,
    "notes": _NOTE_TOOLS,
    "mixer": _MIXER_TOOLS,
    "export": _EXPORT_TOOLS,
    "orchestration": _ORCHESTRATION_TOOLS,
    "stems": _STEM_TOOLS,
}


def _get_tool_specs(categories: Optional[list[str]] = None) -> list[dict]:
    if categories is None:
        categories = list(_ALL_CATEGORIES.keys())
    specs = []
    for cat in categories:
        specs.extend(_ALL_CATEGORIES.get(cat, []))
    return specs
