"""Regression tests: key-normalization lookups (found via interpreter smoke tests)."""
from opendaw_mcp.genre_profiles import PROFILES, get_profile
from opendaw_mcp.utils import _analyze_dynamics


def test_lo_fi_profile_reachable_with_hyphen():
    profile = get_profile("lo-fi")
    assert profile is not None
    assert profile["target_lufs"] == -16


def test_lo_fi_profile_reachable_with_underscore():
    assert get_profile("lo_fi") is not None


def test_hip_hop_profile_variants():
    for name in ("hip_hop", "hip-hop", "Hip Hop"):
        assert get_profile(name) is not None, name


def test_every_profile_reachable_by_storage_key():
    for key in PROFILES:
        assert get_profile(key) is not None, key


def test_analyze_dynamics_empty_input_uses_canonical_keys():
    result = _analyze_dynamics([], 44100)
    assert "segment_variation_db" in result
    assert "segment_rms variation" not in result
