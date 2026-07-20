"""Unit tests for smart export (P3) — platform bounce + lineage edge."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from opendaw_mcp.lineage import LineageStore, reset_default_store
from opendaw_mcp.smart_export import (
    PLATFORM_PRESETS,
    VALID_PLATFORMS,
    export_for_platform,
    get_platform_preset,
    write_float32_wav,
)


def _tone_wav(path: Path, *, seconds: float = 1.2, sr: int = 48000, amp: float = 0.25, freq: float = 440.0) -> Path:
    n = int(seconds * sr)
    ch = []
    for i in range(n):
        t = i / sr
        ch.append(amp * math.sin(2 * math.pi * freq * t))
    # stereo
    write_float32_wav(path, [ch, list(ch)], sr)
    return path


@pytest.fixture
def export_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    lineage_path = tmp_path / "lineage.json"
    monkeypatch.setenv("OPENDAW_EXPORT_DIR", str(export_dir))
    monkeypatch.setenv("OPENDAW_LINEAGE_PATH", str(lineage_path))
    reset_default_store()
    return export_dir, lineage_path


class TestPresets:
    def test_all_platforms_present(self):
        assert set(PLATFORM_PRESETS) == {
            "spotify",
            "apple",
            "youtube",
            "tidal",
            "soundcloud",
            "club",
        }
        assert VALID_PLATFORMS == set(PLATFORM_PRESETS)

    def test_spotify_and_apple_lufs(self):
        assert get_platform_preset("spotify")["target_lufs"] == -14.0
        assert get_platform_preset("apple")["target_lufs"] == -16.0
        assert get_platform_preset("club")["ceiling_dbtp"] == -0.3

    def test_invalid_platform(self):
        with pytest.raises(ValueError):
            get_platform_preset("myspace")


class TestExport:
    def test_dry_run_no_write(self, export_env):
        export_dir, _ = export_env
        src = _tone_wav(export_dir / "mix.wav")
        r = export_for_platform("spotify", str(src), dry_run=True)
        assert r["success"] is True
        assert r["dry_run"] is True
        assert r["plan"]["target_lufs"] == -14.0
        assert r["plan"]["ceiling_dbtp"] == -1.0
        # no platform file
        outs = list(export_dir.glob("*_spotify.wav"))
        assert outs == []

    def test_export_spotify_writes_and_ceiling(self, export_env):
        export_dir, lineage_path = export_env
        _tone_wav(export_dir / "premix.wav", amp=0.2)
        r = export_for_platform("spotify", "premix.wav", parent_id="")
        assert r["success"] is True, r
        assert Path(r["output_path"]).is_file()
        assert r["metrics"]["true_peak_db"] <= -1.0 + 0.05
        assert r["ceiling_ok"] is True
        # LUFS near target (tone may land a bit off; allow 2 LU)
        assert abs(r["metrics"]["lufs_integrated"] - (-14.0)) < 2.5
        assert "lineage" in r
        assert lineage_path.exists()

    def test_export_apple_quieter_target(self, export_env):
        export_dir, _ = export_env
        _tone_wav(export_dir / "premix.wav", amp=0.2)
        r = export_for_platform("apple", "premix.wav")
        assert r["success"] is True, r
        assert r["target_lufs"] == -16.0
        assert r["metrics"]["true_peak_db"] <= -1.0 + 0.05

    def test_invalid_platform_error(self, export_env):
        export_dir, _ = export_env
        _tone_wav(export_dir / "premix.wav")
        r = export_for_platform("napster", "premix.wav")
        assert "error" in r
        assert r["error_code"] == "INVALID_PARAMETER"

    def test_missing_file(self, export_env):
        r = export_for_platform("spotify", "does_not_exist.wav")
        assert "error" in r
        assert r["error_code"] == "NOT_FOUND"

    def test_lineage_parent_edge(self, export_env):
        export_dir, lineage_path = export_env
        store = LineageStore(lineage_path)
        parent = store.record(kind="render", path="premix.wav", label="premix")
        pid = parent["node"]["id"]
        _tone_wav(export_dir / "premix.wav", amp=0.15)
        r = export_for_platform(
            "youtube",
            "premix.wav",
            parent_id=pid,
            lineage_store=store,
        )
        assert r["success"] is True, r
        assert r["lineage"]["parent_id"] == pid
        data = store.load()
        edges = [e for e in data["edges"] if e["parent_id"] == pid]
        assert len(edges) == 1
        assert edges[0]["op"] == "export"
        assert edges[0]["params"]["platform"] == "youtube"

    def test_unknown_parent_lineage_error(self, export_env):
        export_dir, lineage_path = export_env
        store = LineageStore(lineage_path)
        _tone_wav(export_dir / "premix.wav", amp=0.15)
        r = export_for_platform(
            "spotify",
            "premix.wav",
            parent_id="n_missing_parent",
            lineage_store=store,
        )
        # export may still write file; lineage_error expected
        assert r.get("success") is True
        assert "lineage_error" in r
        assert r["lineage_error"]["error_code"] == "NOT_FOUND"

    def test_club_louder_ceiling(self, export_env):
        export_dir, _ = export_env
        _tone_wav(export_dir / "premix.wav", amp=0.2)
        r = export_for_platform("club", "premix.wav")
        assert r["success"] is True, r
        assert r["target_lufs"] == -9.0
        assert r["ceiling_dbtp"] == -0.3
        assert r["metrics"]["true_peak_db"] <= -0.3 + 0.05

    def test_strict_ceiling_fail_path(self, export_env, monkeypatch):
        """Force a broken limiter path to ensure fail-if-TP-above-ceiling."""
        export_dir, _ = export_env
        _tone_wav(export_dir / "premix.wav", amp=0.9)

        import opendaw_mcp.smart_export as se

        # No-op limiter + forced huge gain → peak well above -1 dBTP
        monkeypatch.setattr(se, "_soft_clip_channels", lambda ch, c: ch)
        monkeypatch.setattr(se, "_plan_gain", lambda i, t: 4.0)
        # Prevent touch-up path from re-capping gain via max_touch
        monkeypatch.setattr(
            se,
            "_compute_lufs",
            lambda channels, sr: {
                "lufs_integrated": -8.0,
                "true_peak_db": 6.0,
                "max_sample": 2.0,
                "blocks_measured": 1,
                "gated_blocks": 1,
            },
        )

        r = se.export_for_platform("spotify", "premix.wav", strict_ceiling=True)
        assert "error" in r, r
        assert "True peak" in r["error"] or "ceiling" in r["error"].lower()


class TestServerToolPresence:
    def test_tool_in_server_source(self):
        src = Path(__file__).resolve().parents[1] / "server.py"
        text = src.read_text(encoding="utf-8")
        assert "async def mcp_opendaw_export_for_platform" in text
        assert '__version__ = "1.391.0"' in text
