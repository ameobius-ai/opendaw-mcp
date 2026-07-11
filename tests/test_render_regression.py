"""Render regression test: ensure render output is finite and non-silent.

These assertions guard against the most common render bugs:
- NaN/Inf in audio samples (DSP crash, wrong PPQN)
- Silence (note region duration=0, missing project.copy(), routing bug)

This test runs as part of the standard pytest suite when a bridge is
available (playwright installed + DAW running on localhost:5174).
Otherwise it is skipped.
"""
import json
import math
import os
import pytest

playwright = pytest.importorskip("playwright")
pytestmark = pytest.mark.skipif(
    os.environ.get("OPENDAW_URL") is None,
    reason="OPENDAW_URL not set — needs live DAW on localhost:5174",
)


def _has_non_finite(obj) -> bool:
    """Recursively check for NaN or Infinity in nested structures."""
    if isinstance(obj, float):
        return not math.isfinite(obj)
    if isinstance(obj, dict):
        return any(_has_non_finite(v) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        return any(_has_non_finite(v) for v in obj)
    return False


class TestRenderRegression:
    """Permanent regression guards for render output quality."""

    @pytest.fixture(scope="class")
    def render_result(self):
        from server import OpendawServer
        import asyncio

        async def _render():
            server = OpendawServer()
            await server.bridge.start()
            try:
                await server.mcp_opendaw_set_bpm(120)
                unit = await server.mcp_opendaw_create_synth_track("Vaporisateur")
                unit_data = json.loads(unit)
                unit_idx = unit_data.get("unit_index", 1)
                await server.mcp_opendaw_create_note(
                    unit_index=unit_idx,
                    track_index=0,
                    pitch=60,
                    start_beat=0.0,
                    duration_beats=4.0,
                )
                result = await server.mcp_opendaw_render_full("regression_test.wav", 44100)
                return json.loads(result)
            finally:
                await server.bridge.stop()

        return asyncio.run(_render())

    def test_render_no_exception(self, render_result):
        """Render must complete without AttributeError or other exception."""
        assert render_result.get("success") is True, f"Render failed: {render_result}"

    def test_render_finite(self, render_result):
        """All numeric values in render output must be finite (no NaN/Inf)."""
        assert not _has_non_finite(render_result), "Non-finite value in render output"

    def test_render_non_silent(self, render_result):
        """Render must produce audible audio (max_sample ≥ 0.01)."""
        max_sample = render_result.get("max_sample", 0)
        assert max_sample >= 0.01, (
            f"Render appears silent: max_sample={max_sample} < 0.01. "
            "Possible causes: note region duration=0, missing project.copy(), routing bug."
        )

    def test_render_has_expected_duration(self, render_result):
        """Render must produce a non-trivial number of samples."""
        samples = render_result.get("samples", 0)
        assert samples >= 44100, (
            f"Render too short: {samples} samples (< 1s at 44.1kHz). "
            "Possible cause: PPQN mismatch, note duration not applied."
        )
