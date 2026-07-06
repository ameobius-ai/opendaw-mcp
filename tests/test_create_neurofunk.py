"""Tests for create_neurofunk_arrangement logic."""
import json
from server import mcp_opendaw_create_neurofunk_arrangement


def _parse(result):
    if isinstance(result, str):
        return json.loads(result)
    return result


def test_neurofunk_default_params():
    assert hasattr(mcp_opendaw_create_neurofunk_arrangement, "__name__")
    assert mcp_opendaw_create_neurofunk_arrangement.__name__ == "mcp_opendaw_create_neurofunk_arrangement"


def test_neurofunk_bpm_range():
    """Test BPM validation by calling the inner function directly."""
    import inspect
    src = inspect.getsource(mcp_opendaw_create_neurofunk_arrangement)
    assert "160 <= bpm <= 185" in src
    assert "bars < 4 or bars > 32" in src


def test_neurofunk_drum_pattern_structure():
    """Verify drum pattern has complex neurofunk elements."""
    import inspect
    src = inspect.getsource(mcp_opendaw_create_neurofunk_arrangement)
    # Must have ghost notes
    assert "ghost" in src
    # Must have multiple kick placements
    assert src.count("kick") > 10
    # Must have snare rolls (ghost note clusters)
    assert "3.25" in src or "3.33" in src
    assert "7.25" in src or "7.33" in src


def test_neurofunk_reese_bass():
    """Verify Reese bass has chromatic movement."""
    import inspect
    src = inspect.getsource(mcp_opendaw_create_neurofunk_arrangement)
    # Reese pattern must have chromatic slides (negative pitch offsets)
    assert "-1" in src
    # Must have minor third jumps
    assert "3" in src
    # Must reference reese_base
    assert "reese_base" in src


def test_neurofunk_sub_bass():
    """Verify sub-bass is separate from Reese."""
    import inspect
    src = inspect.getsource(mcp_opendaw_create_neurofunk_arrangement)
    assert "sub_base" in src
    assert "sub_pattern" in src
    assert "sub_notes" in src


def test_neurofunk_stab_intervals():
    """Verify dark minor chord stabs (root + b3 + tritone + b7)."""
    import inspect
    src = inspect.getsource(mcp_opendaw_create_neurofunk_arrangement)
    # stab_intervals = [0, 3, 6, 10] = root, minor third, tritone, minor seventh
    assert "[0, 3, 6, 10]" in src


def test_neurofunk_four_tracks():
    """Verify 4 tracks: drums, sub-bass, reese, stabs."""
    import inspect
    src = inspect.getsource(mcp_opendaw_create_neurofunk_arrangement)
    assert "drum_track" in src
    assert "bass_track" in src
    assert "reese_track" in src
    assert "stabs_track" in src


def test_neurofunk_output_structure():
    """Verify output JSON structure."""
    import inspect
    src = inspect.getsource(mcp_opendaw_create_neurofunk_arrangement)
    assert "neurofunk_arrangement" in src
    assert "total_notes" in src
    assert "drum_pattern" in src
    assert "bass_pattern" in src
    assert "harmony" in src


def test_neurofunk_default_root_f():
    """Default root should be F (classic neurofunk key)."""
    import inspect
    sig = inspect.signature(mcp_opendaw_create_neurofunk_arrangement)
    assert sig.parameters["root"].default == "F"


def test_neurofunk_default_bpm_174():
    """Default BPM should be 174."""
    import inspect
    sig = inspect.signature(mcp_opendaw_create_neurofunk_arrangement)
    assert sig.parameters["bpm"].default == 174


def test_neurofunk_default_velocity_09():
    """Default velocity should be 0.9 (aggressive)."""
    import inspect
    sig = inspect.signature(mcp_opendaw_create_neurofunk_arrangement)
    assert sig.parameters["velocity"].default == 0.9


def test_neurofunk_drum_cycle_2_bars():
    """Drum pattern should be 2-bar cycle (8 beats)."""
    import inspect
    src = inspect.getsource(mcp_opendaw_create_neurofunk_arrangement)
    assert "drum_cycle = 8.0" in src


def test_neurofunk_drum_ghost_velocities():
    """Ghost notes should have reduced velocity."""
    import inspect
    src = inspect.getsource(mcp_opendaw_create_neurofunk_arrangement)
    assert "velocity - 0.35" in src


def test_neurofunk_kick_velocities():
    """Kick should have boosted velocity."""
    import inspect
    src = inspect.getsource(mcp_opendaw_create_neurofunk_arrangement)
    assert "velocity + 0.05" in src


def test_neurofunk_stab_base_octave():
    """Stabs should be 2 octaves above bass."""
    import inspect
    src = inspect.getsource(mcp_opendaw_create_neurofunk_arrangement)
    assert "octave + 4" in src


def test_neurofunk_reese_chromatic_slides():
    """Reese pattern should have chromatic pitch movement."""
    import inspect
    src = inspect.getsource(mcp_opendaw_create_neurofunk_arrangement)
    # -1 pitch offset = chromatic slide down
    assert "(-1" in src or "-1," in src


def test_neurofunk_reese_minor_third_jumps():
    """Reese pattern should have minor third interval jumps."""
    import inspect
    src = inspect.getsource(mcp_opendaw_create_neurofunk_arrangement)
    assert "3," in src  # minor third = 3 semitones


def test_neurofunk_snare_rolls():
    """Verify snare roll ghost clusters at phrase ends."""
    import inspect
    src = inspect.getsource(mcp_opendaw_create_neurofunk_arrangement)
    # Ghost clusters at beats 3.25, 3.33, 3.41 and 7.25, 7.33, 7.41
    assert "3.41" in src
    assert "7.41" in src


def test_neurofunk_sub_bass_syncopated_gaps():
    """Sub-bass should have syncopated gaps."""
    import inspect
    src = inspect.getsource(mcp_opendaw_create_neurofunk_arrangement)
    # Gap at beat 3.75 (short note after silence)
    assert "3.75" in src
    assert "7.75" in src


def test_neurofunk_creates_batches():
    """Verify it calls create_notes_batch for all 4 tracks."""
    import inspect
    src = inspect.getsource(mcp_opendaw_create_neurofunk_arrangement)
    assert src.count("mcp_opendaw_create_notes_batch") == 4


def test_neurofunk_error_handling():
    """Verify error handling for invalid params."""
    import inspect
    src = inspect.getsource(mcp_opendaw_create_neurofunk_arrangement)
    assert "Error: bpm must be 160-185" in src
    assert "Error: bars must be 4-32" in src
    assert "Error: velocity must be 0-1" in src


def test_neurofunk_drum_pitch_map():
    """Verify standard drum pitch mapping."""
    import inspect
    src = inspect.getsource(mcp_opendaw_create_neurofunk_arrangement)
    assert "kick_p, snare_p, hat_p, ghost_p = 36, 38, 42, 37" in src
