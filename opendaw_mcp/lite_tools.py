"""Lite mode essential tools — curated list of 39 tools.

When OPENDAW_MCP_MODE=lite, only these tools are registered with the MCP server.
This reduces the tool schema payload by ~93% (557→39 tools), saving tokens
for agents that only need basic track production capabilities.

Full mode registers all 557 decorated tools including advanced
orchestration, DSP scripting, stem separation, genre arrangements, and
composition tools.

Note: Meta-tools (arrange_full_song, produce_full_track, produce_and_master,
auto_master, add_genre_effects, read_meter) are internal functions called
by decorated tools — they don't need @mcp.tool() decorators.
"""

LITE_TOOLS: list[str] = [
    # Project & info (4)
    "mcp_opendaw_get_full_project_state",
    "mcp_opendaw_get_project_info",
    "mcp_opendaw_list_tracks",
    "mcp_opendaw_list_note_regions",

    # Tracks (3)
    "mcp_opendaw_create_audio_track",
    "mcp_opendaw_create_note_track",
    "mcp_opendaw_delete_track",

    # Instruments (2)
    "mcp_opendaw_create_synth_track",
    "mcp_opendaw_create_instrument_track",

    # Notes (4)
    "mcp_opendaw_create_note",
    "mcp_opendaw_create_notes_batch",
    "mcp_opendaw_delete_note",
    "mcp_opendaw_set_note_properties",

    # Regions (2)
    "mcp_opendaw_create_track_region",
    "mcp_opendaw_delete_region",

    # Effects (4)
    "mcp_opendaw_add_effect",
    "mcp_opendaw_list_effects",
    "mcp_opendaw_set_effect_parameter",
    "mcp_opendaw_get_effect_state",

    # Mixing (3)
    "mcp_opendaw_create_send",
    "mcp_opendaw_set_track_volume",
    "mcp_opendaw_set_track_panning",

    # BPM (2)
    "mcp_opendaw_detect_bpm",
    "mcp_opendaw_set_bpm",

    # Render (2)
    "mcp_opendaw_render_full",
    "mcp_opendaw_export_stems",

    # Compositional building blocks (5)
    "mcp_opendaw_create_drum_pattern",
    "mcp_opendaw_create_bassline",
    "mcp_opendaw_create_melody",
    "mcp_opendaw_create_chord_progression",
    "mcp_opendaw_apply_mix_preset",

    # Markers (1)
    "mcp_opendaw_add_marker",

    # Scriptable devices (5)
    "mcp_opendaw_set_script_device_code",
    "mcp_opendaw_get_script_device_code",
    "mcp_opendaw_list_script_params",
    "mcp_opendaw_set_script_param",
    "mcp_opendaw_list_script_samples",

    # Audio (2)
    "mcp_opendaw_load_audio",
    "mcp_opendaw_place_audio_region",
]
