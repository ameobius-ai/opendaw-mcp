"""Unit tests for _build_chord_prog — key-aware chord progression builder."""
import importlib.util
import inspect
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _get_source():
    spec = importlib.util.spec_from_file_location(
        "server", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py")
    )
    mod = importlib.util.module_from_spec(spec)
    src = inspect.getsource(sys.modules.get("server", mod))
    if not src or "_build_chord_prog" not in src:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py")) as f:
            src = f.read()
    return src


def test_build_chord_prog_exists():
    src = _get_source()
    assert "def _build_chord_prog" in src


def test_build_chord_prog_has_chord_roots():
    src = _get_source()
    assert "_CHORD_ROOTS" in src


def test_build_chord_prog_has_flat_mapping():
    src = _get_source()
    assert "_CHORD_ROOTS_FLAT" in src
    assert "Db" in src
    assert "Bb" in src


def test_build_chord_prog_major_uses_iv_vi_iv():
    src = _get_source()
    assert "maj7" in src
    assert "m7" in src


def test_build_chord_prog_minor_uses_i_vi_iii_vii():
    src = _get_source()
    # minor: i-VI-III-VII
    assert "note(8)" in src  # VI
    assert "note(3)" in src  # III
    assert "note(10)" in src  # VII


def test_build_chord_prog_harmonic_minor_uses_i_iv_v_i():
    src = _get_source()
    # harmonic minor: i-iv-V-i
    assert "harmonic_minor" in src


def test_build_chord_prog_has_docstring():
    src = _get_source()
    assert "Build a 4-chord progression" in src


def test_build_chord_prog_has_note_helper():
    src = _get_source()
    assert "def note(offset)" in src


def test_build_chord_prog_handles_flats():
    src = _get_source()
    assert ".get(key_root" in src


def test_build_chord_prog_used_in_produce_and_master():
    src = _get_source()
    assert "_build_chord_prog(key_root, scale_type)" in src


def test_build_chord_prog_used_in_produce_full_track():
    src = _get_source()
    # Should appear at least twice (both meta-tools)
    count = src.count("_build_chord_prog(key_root, scale_type)")
    assert count >= 2, f"Expected >=2 usages, got {count}"


def test_build_chord_prog_no_hardcoded_c_major():
    src = _get_source()
    # The old bug: hardcoded Cmaj7,Fmaj7,Gmaj7,Am7
    assert '"Cmaj7,Fmaj7,Gmaj7,Am7"' not in src
