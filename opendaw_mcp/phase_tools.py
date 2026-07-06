"""Phase-based tool loading for opendaw-mcp.

When OPENDAW_MCP_MODE=phase, tools are loaded by phase.
Agent calls switch_phase("compose") to activate compose tools.

Phases:
  inspect  — read-only: project state, list tracks/regions/effects, meters
  compose  — create tracks, instruments, notes, regions, sections, arrangements
  mix      — effects, sends, buses, mixing, mastering, genre effects
  render   — render, export, audio I/O, time/pitch stretch

Meta-tools (arrange_full_song, produce_full_track, produce_and_master,
auto_master) are available in ALL phases since they chain multiple phases.
"""

# Tools available in each phase
PHASE_TOOLS = {
    "inspect": {
        "mcp_opendaw_get_full_project_state", "mcp_opendaw_get_project_info",
        "mcp_opendaw_list_tracks", "mcp_opendaw_list_note_regions",
        "mcp_opendaw_list_audio_regions", "mcp_opendaw_list_effects",
        "mcp_opendaw_list_audio_buses", "mcp_opendaw_list_markers",
        "mcp_opendaw_list_automation_events", "mcp_opendaw_list_clips",
        "mcp_opendaw_list_signature_changes", "mcp_opendaw_list_tempo_changes",
        "mcp_opendaw_get_effect_state", "mcp_opendaw_get_bpm",
        "mcp_opendaw_detect_bpm", "mcp_opendaw_read_meter",
        "mcp_opendaw_evaluate_raw", "mcp_opendaw_analyze_mix",
        "mcp_opendaw_analyze_dynamics", "mcp_opendaw_analyze_harmonic_rhythm",
        "mcp_opendaw_analyze_melody", "mcp_opendaw_analyze_spectrum",
        "mcp_opendaw_analyze_stereo",
    },
    "compose": {
        # Tracks & instruments
        "mcp_opendaw_create_audio_track", "mcp_opendaw_create_note_track",
        "mcp_opendaw_create_synth_track", "mcp_opendaw_create_instrument_track",
        "mcp_opendaw_delete_track", "mcp_opendaw_copy_audiounit",
        "mcp_opendaw_move_audio_unit", "mcp_opendaw_delete_audio_unit",
        # Notes
        "mcp_opendaw_create_note", "mcp_opendaw_create_notes_batch",
        "mcp_opendaw_delete_note", "mcp_opendaw_set_note_properties",
        "mcp_opendaw_set_note_advanced", "mcp_opendaw_set_note_cents",
        "mcp_opendaw_scale_velocity", "mcp_opendaw_map_velocity_by_pitch",
        "mcp_opendaw_apply_velocity_curve", "mcp_opendaw_apply_velocity_lfo",
        "mcp_opendaw_apply_velocity_pattern",
        "mcp_opendaw_humanize_notes", "mcp_opendaw_humanize_timing",
        "mcp_opendaw_transposenotes", "mcp_opendaw_reverse_notes",
        "mcp_opendaw_invert_notes", "mcp_opendaw_quantize_notes",
        # Regions
        "mcp_opendaw_create_track_region", "mcp_opendaw_delete_region",
        "mcp_opendaw_duplicate_region", "mcp_opendaw_split_note_region",
        "mcp_opendaw_merge_note_regions",
        # Compositional tools
        "mcp_opendaw_create_drum_pattern", "mcp_opendaw_create_bassline",
        "mcp_opendaw_create_melody", "mcp_opendaw_create_chord_progression",
        "mcp_opendaw_create_arpeggio", "mcp_opendaw_create_harmony",
        "mcp_opendaw_create_counterpoint", "mcp_opendaw_create_riff",
        "mcp_opendaw_create_hook", "mcp_opendaw_create_lick",
        "mcp_opendaw_create_turnaround", "mcp_opendaw_create_descant",
        "mcp_opendaw_create_counter_melody", "mcp_opendaw_create_solo",
        "mcp_opendaw_create_etude", "mcp_opendaw_create_cadence",
        "mcp_opendaw_create_trade_solos",
        # Sections
        "mcp_opendaw_create_intro", "mcp_opendaw_create_verse",
        "mcp_opendaw_create_prechorus", "mcp_opendaw_create_chorus",
        "mcp_opendaw_create_interlude", "mcp_opendaw_create_transition",
        "mcp_opendaw_create_bridge", "mcp_opendaw_create_outro",
        "mcp_opendaw_create_coda",
        # Structure
        "mcp_opendaw_arrange_full_song", "mcp_opendaw_produce_full_track",
        "mcp_opendaw_produce_and_master",
        "mcp_opendaw_add_marker", "mcp_opendaw_set_bpm",
        "mcp_opendaw_add_tempo_change", "mcp_opendaw_add_signature_change",
        # World rhythm
        "mcp_opendaw_create_clave", "mcp_opendaw_create_cross_rhythm",
        "mcp_opendaw_create_euclidean_rhythm",
        # Advanced composition
        "mcp_opendaw_add_passing_tones", "mcp_opendaw_add_neighbor_tones",
        "mcp_opendaw_add_suspension", "mcp_opendaw_add_anticipation",
        "mcp_opendaw_add_chord_tension", "mcp_opendaw_accent_beats",
        # Scriptable devices (composition)
        "mcp_opendaw_set_script_device_code", "mcp_opendaw_get_script_device_code",
        "mcp_opendaw_list_script_params", "mcp_opendaw_set_script_param",
        "mcp_opendaw_list_script_samples",
    },
    "mix": {
        # Effects
        "mcp_opendaw_add_effect", "mcp_opendaw_set_effect_parameter",
        "mcp_opendaw_set_effect_parameter_int", "mcp_opendaw_set_effect_parameter_bool",
        "mcp_opendaw_set_effect_parameter_string",
        "mcp_opendaw_delete_effect", "mcp_opendaw_move_effect",
        "mcp_opendaw_clone_effect", "mcp_opendaw_clone_effect_chain",
        # Mixing
        "mcp_opendaw_create_send", "mcp_opendaw_set_track_volume",
        "mcp_opendaw_set_track_panning", "mcp_opendaw_apply_mix_preset",
        "mcp_opendaw_create_audio_bus", "mcp_opendaw_set_bus_volume",
        "mcp_opendaw_delete_audio_bus", "mcp_opendaw_move_audio_unit",
        # Mastering
        "mcp_opendaw_add_mastering_chain", "mcp_opendaw_auto_master",
        "mcp_opendaw_auto_gain", "mcp_opendaw_add_genre_effects",
        # Automation
        "mcp_opendaw_add_automation", "mcp_opendaw_add_instrument_automation",
        # Chains
        "mcp_opendaw_add_drum_chain", "mcp_opendaw_add_bass_chain",
        "mcp_opendaw_add_vocal_chain", "mcp_opendaw_add_instrument_chain",
        # MIDI effects
        "mcp_opendaw_add_midi_effect",
        # Instrument params
        "mcp_opendaw_set_instrument_param", "mcp_opendaw_list_instrument_params",
        "mcp_opendaw_set_osc_param", "mcp_opendaw_list_osc_params",
    },
    "render": {
        "mcp_opendaw_render_full", "mcp_opendaw_render_full_format",
        "mcp_opendaw_render_full_song", "mcp_opendaw_export_stems",
        "mcp_opendaw_export_stems_format", "mcp_opendaw_export_region_audio",
        "mcp_opendaw_load_audio", "mcp_opendaw_place_audio_region",
        "mcp_opendaw_create_audio_clip", "mcp_opendaw_create_time_stretched_clip",
        "mcp_opendaw_create_pitch_stretched_clip",
        "mcp_opendaw_set_audio_region_fade", "mcp_opendaw_set_audio_region_gain",
        "mcp_opendaw_save_preset", "mcp_opendaw_load_preset",
        "mcp_opendaw_transfer_region", "mcp_opendaw_transfer_audiounit",
    },
}

# Meta-tools available in all phases
ALL_PHASE_TOOLS = {
    "mcp_opendaw_get_full_project_state", "mcp_opendaw_evaluate_raw",
    "mcp_opendaw_switch_phase",
}

# Current phase (mutable)
_current_phase = "compose"
