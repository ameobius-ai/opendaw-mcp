"""Unit tests for prompt inference — metrics → Suno style packages."""

from __future__ import annotations

from pathlib import Path

import pytest

from opendaw_mcp.prompt_inference import (
    PACKAGES,
    _resolve_hint,
    _score_package,
    infer_from_metrics,
    infer_suno_prompt,
    metrics_from_analysis,
)
from opendaw_mcp.lineage import LineageStore, reset_default_store


# ---------------------------------------------------------------------------
# Fixture metrics (no audio I/O)
# ---------------------------------------------------------------------------

def _coldwave_metrics() -> dict:
    return {
        "bpm": 110.0,
        "bpm_confidence": 0.8,
        "key": "A",
        "mode": "minor",
        "key_confidence": 0.7,
        "spectral_centroid_hz": 1600.0,
        "low_high_ratio": 2.4,
        "sub_bass_pct": 18.0,
        "bass_pct": 28.0,
        "presence_pct": 4.5,
        "brilliance_pct": 2.0,
        "crest_factor_db": 12.0,
        "transient_density": 4.0,
        "lufs_integrated": -14.0,
        "true_peak_db": -1.0,
        "duration_seconds": 180.0,
    }


def _folk_metrics() -> dict:
    return {
        "bpm": 90.0,
        "bpm_confidence": 0.75,
        "key": "E",
        "mode": "minor",
        "key_confidence": 0.65,
        "spectral_centroid_hz": 1800.0,
        "low_high_ratio": 1.1,
        "sub_bass_pct": 10.0,
        "bass_pct": 18.0,
        "presence_pct": 10.0,
        "brilliance_pct": 6.0,
        "crest_factor_db": 15.0,
        "transient_density": 1.5,
        "lufs_integrated": -16.0,
        "true_peak_db": -2.0,
        "duration_seconds": 210.0,
    }


def _cloud_metrics() -> dict:
    return {
        "bpm": 82.0,
        "bpm_confidence": 0.7,
        "key": "C",
        "mode": "minor",
        "key_confidence": 0.6,
        "spectral_centroid_hz": 1200.0,
        "low_high_ratio": 2.8,
        "sub_bass_pct": 22.0,
        "bass_pct": 30.0,
        "presence_pct": 5.0,
        "brilliance_pct": 3.0,
        "crest_factor_db": 10.0,
        "transient_density": 3.0,
        "lufs_integrated": -12.0,
        "true_peak_db": -0.8,
        "duration_seconds": 150.0,
    }


def _empty_metrics() -> dict:
    return {
        "bpm": None,
        "bpm_confidence": 0.0,
        "key": None,
        "mode": None,
        "key_confidence": 0.0,
        "spectral_centroid_hz": 0.0,
        "low_high_ratio": 0.0,
    }


class TestHintResolve:
    def test_coldwave_aliases(self):
        assert _resolve_hint("coldwave") == "darksynth_coldwave"
        assert _resolve_hint("Darksynth") == "darksynth_coldwave"
        assert _resolve_hint("post-punk") == "darksynth_coldwave"

    def test_folk_aliases(self):
        assert _resolve_hint("folk") == "folk_horror"
        assert _resolve_hint("folk-horror") == "folk_horror"

    def test_cloud_aliases(self):
        assert _resolve_hint("lofi") == "cloud_bedroom"
        assert _resolve_hint("cloud rap") == "cloud_bedroom"

    def test_unknown(self):
        assert _resolve_hint("mathcore-extratone") is None
        assert _resolve_hint(None) is None
        assert _resolve_hint("") is None


class TestScoreBuckets:
    def test_coldwave_wins_on_coldwave_metrics(self):
        m = _coldwave_metrics()
        scores = {pkg["id"]: _score_package(pkg, m)[0] for pkg in PACKAGES}
        assert max(scores, key=scores.get) == "darksynth_coldwave"
        assert scores["darksynth_coldwave"] > 0.5

    def test_folk_wins_on_folk_metrics(self):
        m = _folk_metrics()
        scores = {pkg["id"]: _score_package(pkg, m)[0] for pkg in PACKAGES}
        assert max(scores, key=scores.get) == "folk_horror"

    def test_cloud_wins_on_cloud_metrics(self):
        m = _cloud_metrics()
        scores = {pkg["id"]: _score_package(pkg, m)[0] for pkg in PACKAGES}
        assert max(scores, key=scores.get) == "cloud_bedroom"


class TestInferFromMetrics:
    def test_coldwave_package(self):
        r = infer_from_metrics(_coldwave_metrics())
        assert r["success"] is True
        assert r["package_id"] == "darksynth_coldwave"
        assert "darksynth" in r["style"].lower() or "coldwave" in r["style"].lower()
        assert "BPM" in r["style"]
        assert r["bpm"] == 110.0
        assert r["key"] == "A minor"
        assert r["negatives"]
        assert r["confidence"] > 0.45
        assert r["used_generic"] is False
        # no vendor hype
        assert "studio-grade" not in r["style"]
        assert "modern mastering" not in r["style"]

    def test_folk_package(self):
        r = infer_from_metrics(_folk_metrics())
        assert r["package_id"] == "folk_horror"
        assert "folk" in r["style"].lower()

    def test_cloud_package(self):
        r = infer_from_metrics(_cloud_metrics())
        assert r["package_id"] == "cloud_bedroom"
        assert "cloud" in r["style"].lower() or "lo-fi" in r["style"].lower() or "lofi" in r["style"].replace("-", "")

    def test_genre_hint_boost(self):
        # coldwave-ish bpm but force folk via hint
        m = _coldwave_metrics()
        m["bpm"] = 100.0
        r = infer_from_metrics(m, genre_hint="folk horror")
        assert r["package_id"] == "folk_horror"
        assert any("genre_hint" in x for x in r["match_reasons"])

    def test_low_confidence_generic(self):
        r = infer_from_metrics(_empty_metrics())
        assert r["success"] is True
        assert r["used_generic"] is True
        assert r["package_id"] is None
        assert r["low_confidence"] is True
        assert "BPM" in r["style"]
        # still no hype soup
        assert "crisp production" not in r["style"]

    def test_compact_vs_full(self):
        m = _coldwave_metrics()
        compact = infer_from_metrics(m, compact=True)
        full = infer_from_metrics(m, compact=False)
        assert compact["package_id"] == full["package_id"]
        assert len(full["style"]) >= len(compact["style"])
        assert "style_full" in compact

    def test_ranking_present(self):
        r = infer_from_metrics(_coldwave_metrics())
        assert len(r["ranking"]) == len(PACKAGES)
        assert r["ranking"][0]["id"] == r["package_id"]

    def test_invalid_metrics(self):
        r = infer_from_metrics("not-a-dict")  # type: ignore[arg-type]
        assert "error" in r


class TestMetricsFromAnalysis:
    def test_flattens_bands(self):
        spectrum = {
            "spectral_centroid_hz": 2000.0,
            "low_high_ratio": 1.5,
            "bands": [
                {"name": "sub_bass", "energy_pct": 12.0},
                {"name": "bass", "energy_pct": 20.0},
                {"name": "presence", "energy_pct": 8.0},
                {"name": "brilliance", "energy_pct": 4.0},
            ],
        }
        dynamics = {"crest_factor_db": 11.0, "transient_density": 5.0}
        m = metrics_from_analysis(
            bpm=120,
            bpm_confidence=0.9,
            key="D",
            mode="major",
            key_confidence=0.8,
            spectrum=spectrum,
            dynamics=dynamics,
            lufs_integrated=-14.2,
        )
        assert m["sub_bass_pct"] == 12.0
        assert m["bass_pct"] == 20.0
        assert m["presence_pct"] == 8.0
        assert m["key"] == "D"
        assert m["mode"] == "major"
        assert m["crest_factor_db"] == 11.0


class TestInferSunoPromptApi:
    def test_metrics_path_no_file(self):
        r = infer_suno_prompt(metrics=_coldwave_metrics())
        assert r["success"] is True
        assert r["package_id"] == "darksynth_coldwave"

    def test_missing_args(self):
        r = infer_suno_prompt()
        assert "error" in r
        assert r["error_code"] == "INVALID_PARAMETER"

    def test_record_lineage(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        reset_default_store()
        lineage_path = tmp_path / "lineage.json"
        monkeypatch.setenv("OPENDAW_LINEAGE_PATH", str(lineage_path))
        reset_default_store()

        r = infer_suno_prompt(
            metrics=_coldwave_metrics(),
            record_lineage=True,
            label="unit-test prompt",
        )
        assert r["success"] is True
        assert "lineage" in r
        assert r["lineage"]["prompt_node_id"]
        assert lineage_path.exists()

        store = LineageStore(lineage_path)
        nodes = store.list_nodes(kind="prompt")
        assert nodes["total"] >= 1
        analysis = store.list_nodes(kind="analysis")
        assert analysis["total"] >= 1
        reset_default_store()

    def test_file_not_found(self):
        r = infer_suno_prompt(filename="definitely_missing_xyz_prompt_infer.wav")
        assert "error" in r
        assert r["error_code"] == "NOT_FOUND"


class TestNoHype:
    """Acceptance: no hallucinated vendor hype in outputs."""

    def test_packages_have_no_quality_soup(self):
        banned = (
            "studio-grade",
            "modern mastering",
            "crisp production",
            "clean mix",
            "punchy bass",
            "crisp highs",
        )
        for pkg in PACKAGES:
            blob = pkg["style"] + " " + pkg["style_full"]
            for b in banned:
                assert b not in blob, f"{pkg['id']} contains banned hype: {b}"
