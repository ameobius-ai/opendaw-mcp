"""opendaw-mcp — MCP server for controlling openDAW programmatically.

Usage:
    from server import OpendawServer

Usage (framework wrappers):
    from opendaw_mcp.langchain_tools import OpendawToolkit
    from opendaw_mcp.autogen_tools import OpendawAutoGenToolkit
    from opendaw_mcp.crewai_tools import OpendawCrewAITool
"""

from .constants import (
    TIDAL_RATE_MAP,
    DELAY_SYNC_MAP,
    WAVESHAPER_FUNCS,
    REVAMP_SECTIONS,
)
from .bridge import HeadlessDawBridge, DAW_URL
from .utils import (
    _parse_wav,
    _compute_lufs,
    _ok,
    _err,
    _wrap_eval,
    _unwrap_eval,
    _safe_filename,
    _safe_path,
    _clamp_script_param,
    _detect_bpm,
    _detect_key,
    _transcribe_drums,
    _transcribe_melody,
)
from .music_theory import (
    NOTE_TO_PITCH,
    CHORD_INTERVALS,
    SCALE_INTERVALS,
    GENRE_PRESETS,
    VALID_GENRES,
    VALID_CHORD_TYPES,
    VALID_SCALE_TYPES,
    chord_to_pitches,
    scale_to_pitches,
    parse_melody_pattern,
)

__all__ = [
    "HeadlessDawBridge",
    "DAW_URL",
    "TIDAL_RATE_MAP",
    "DELAY_SYNC_MAP",
    "WAVESHAPER_FUNCS",
    "REVAMP_SECTIONS",
    "_parse_wav",
    "_compute_lufs",
    "_ok",
    "_err",
    "_wrap_eval",
    "_unwrap_eval",
    "_safe_filename",
    "_safe_path",
    "_clamp_script_param",
    "_detect_bpm",
    "_detect_key",
    "_transcribe_drums",
    "_transcribe_melody",
    "NOTE_TO_PITCH",
    "CHORD_INTERVALS",
    "SCALE_INTERVALS",
    "GENRE_PRESETS",
    "VALID_GENRES",
    "VALID_CHORD_TYPES",
    "VALID_SCALE_TYPES",
    "chord_to_pitches",
    "scale_to_pitches",
    "parse_melody_pattern",
]
