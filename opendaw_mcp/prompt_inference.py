"""Prompt inference: songsee/analyze metrics → Suno style package.

Pure analysis path — no DAW bridge. Maps BPM/key/spectrum/dynamics to
KB style packages (darksynth_coldwave, folk_horror, cloud_bedroom) plus
generic tag fallbacks when confidence is low.

Used by MCP tool `infer_suno_prompt` (P4 / t_7d93062d).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from opendaw_mcp.errors import enrich_error

# ---------------------------------------------------------------------------
# KB package fingerprints (synced with creative-studio/kb/suno/packages/*)
# Spectral/tempo priors are soft — not genre locks for mix advice.
# ---------------------------------------------------------------------------

KB_PACKAGES_DIR_CANDIDATES = (
    Path(os.environ.get("OPENDAW_KB_DIR", "")).expanduser() if os.environ.get("OPENDAW_KB_DIR") else None,
    Path(__file__).resolve().parents[3] / "kb",  # agent-daw/../kb if layout matches
    Path(__file__).resolve().parents[2].parent / "kb",
)

PACKAGES: list[dict[str, Any]] = [
    {
        "id": "darksynth_coldwave",
        "label": "Darksynth / Coldwave",
        "package_file": "suno/packages/darksynth_coldwave.md",
        "bpm_lo": 100,
        "bpm_hi": 125,
        "bpm_anchor": 110,
        "preferred_mode": "minor",
        "style": (
            "[deep husky baritone], darksynth, coldwave, overdriven-bass, "
            "gated-snare, {bpm} BPM, mono-low-end, no-scream"
        ),
        "style_full": (
            "[Vocal: male, deep husky timbre, relaxed but intense delivery, clear diction, "
            "precise rhythm, modern rap-adjacent tone], darksynth, coldwave, overdriven-bass, "
            "palm-mute-guitar, analog-arps, gated-snare, {bpm} BPM, intimate close-mic dry vocal "
            "combined with wide cold reverb wash, focused mono low-end, no screaming, no shouting, "
            "no vocal acrobatics"
        ),
        "negatives": (
            "no screaming, no shouting, no high-pitched vocals, no aggressive belting, "
            "no vocal acrobatics, bright pop, trap hi-hats, festival drop"
        ),
        # Soft spectral priors (energy %)
        "centroid_lo": 800,
        "centroid_hi": 2800,
        "low_high_ratio_lo": 1.2,
        "sub_bass_bias": "high",  # dark/low-end forward
        "presence_bias": "low",
        "transient_bias": "mid",
        "crest_lo": 9,
        "crest_hi": 16,
    },
    {
        "id": "folk_horror",
        "label": "Folk Horror",
        "package_file": "suno/packages/folk_horror.md",
        "bpm_lo": 75,
        "bpm_hi": 105,
        "bpm_anchor": 90,
        "preferred_mode": "minor",
        "style": (
            "[gravelly storytelling male], folk-horror, dark-folk, acoustic-drone, "
            "tape-sat, {bpm} BPM, dry-vocal, no-scream"
        ),
        "style_full": (
            "[Vocal: male, gravelly weathered timbre, conversational storytelling cadence, "
            "intimate microphone presence, dry and present], folk horror, dark folk, acoustic guitar, "
            "low drone strings, tape saturation, wooden room ambience, {bpm} BPM, intimate close-mic "
            "dry vocal combined with distant church-like reverb tails, lo-fi 4-track texture, "
            "no screaming, no shouting, no pop gloss, no vocal acrobatics"
        ),
        "negatives": (
            "no screaming, no shouting, no arena rock vocal, no soaring vocal, "
            "no polished radio-ready gloss, no vocal acrobatics, uplifting, festival, happy folk"
        ),
        "centroid_lo": 900,
        "centroid_hi": 2600,
        "low_high_ratio_lo": 0.8,
        "sub_bass_bias": "mid",
        "presence_bias": "mid",
        "transient_bias": "low",
        "crest_lo": 11,
        "crest_hi": 20,
    },
    {
        "id": "cloud_bedroom",
        "label": "Cloud / Bedroom",
        "package_file": "suno/packages/cloud_bedroom.md",
        "bpm_lo": 68,
        "bpm_hi": 100,
        "bpm_anchor": 82,
        "preferred_mode": None,  # either ok
        "style": (
            "[half-sung monotone male, subtle autotune], cloud-rap, lo-fi, soft-808, "
            "dusty-drums, {bpm} BPM, bedroom-haze, no-scream"
        ),
        "style_full": (
            "[Vocal: male, half-sung half-rapped, monotone delivery with occasional melodic lifts, "
            "Auto-Tune subtle, introspective tone], cloud rap, lo-fi hip hop, dusty snare, soft 808, "
            "tape saturation, bedroom pop night atmosphere, {bpm} BPM, intimate close-mic dry vocal "
            "combined with hazy wide pad wash, sidechain pump light, no screaming, no aggressive rap belt, "
            "no festival drop, no vocal acrobatics"
        ),
        "negatives": (
            "no screaming, no aggressive rap belt, no stadium crowd ambience, no festival drop, "
            "no high-energy rock vocal, no vocal acrobatics, hype, club anthem, dancefloor"
        ),
        "centroid_lo": 700,
        "centroid_hi": 2200,
        "low_high_ratio_lo": 1.5,
        "sub_bass_bias": "high",
        "presence_bias": "low",
        "transient_bias": "mid",
        "crest_lo": 7,
        "crest_hi": 14,
    },
]

_HINT_ALIASES: dict[str, str] = {
    "coldwave": "darksynth_coldwave",
    "darksynth": "darksynth_coldwave",
    "darksynth_coldwave": "darksynth_coldwave",
    "post-punk": "darksynth_coldwave",
    "postpunk": "darksynth_coldwave",
    "synthwave": "darksynth_coldwave",
    "folk": "folk_horror",
    "folk_horror": "folk_horror",
    "folk-horror": "folk_horror",
    "dark folk": "folk_horror",
    "dark-folk": "folk_horror",
    "acoustic": "folk_horror",
    "cloud": "cloud_bedroom",
    "cloud_bedroom": "cloud_bedroom",
    "bedroom": "cloud_bedroom",
    "lofi": "cloud_bedroom",
    "lo-fi": "cloud_bedroom",
    "cloud rap": "cloud_bedroom",
    "trap": "cloud_bedroom",
    "hiphop": "cloud_bedroom",
    "hip-hop": "cloud_bedroom",
    "hip hop": "cloud_bedroom",
}


def resolve_kb_root() -> Path | None:
    for cand in KB_PACKAGES_DIR_CANDIDATES:
        if cand is None:
            continue
        p = Path(cand)
        if (p / "suno" / "packages").is_dir():
            return p
    return None


def _band_pct(bands: list[dict] | None, name: str) -> float | None:
    if not bands:
        return None
    for b in bands:
        if b.get("name") == name:
            v = b.get("energy_pct")
            return float(v) if v is not None else None
    return None


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _score_package(pkg: dict[str, Any], metrics: dict[str, Any]) -> tuple[float, list[str]]:
    """Return (score 0-1, reasons). Higher = better match."""
    reasons: list[str] = []
    score = 0.0
    weight_sum = 0.0

    bpm = metrics.get("bpm")
    if bpm is not None:
        weight = 0.30
        weight_sum += weight
        lo, hi, anchor = pkg["bpm_lo"], pkg["bpm_hi"], pkg["bpm_anchor"]
        if lo <= bpm <= hi:
            # closer to anchor → higher
            span = max(1.0, (hi - lo) / 2.0)
            dist = abs(float(bpm) - anchor) / span
            part = _clamp01(1.0 - 0.35 * dist)
            score += weight * part
            reasons.append(f"bpm {bpm} in [{lo},{hi}]")
        else:
            # soft falloff outside range
            if bpm < lo:
                dist = (lo - bpm) / max(20.0, lo * 0.3)
            else:
                dist = (bpm - hi) / max(20.0, hi * 0.3)
            part = _clamp01(0.55 - 0.55 * dist)
            score += weight * part
            if part > 0.2:
                reasons.append(f"bpm {bpm} near package range")

    mode = (metrics.get("mode") or "").lower()
    pref = pkg.get("preferred_mode")
    if pref and mode:
        weight = 0.12
        weight_sum += weight
        if mode == pref:
            score += weight
            reasons.append(f"mode {mode}")
        else:
            score += weight * 0.25

    centroid = metrics.get("spectral_centroid_hz")
    if centroid is not None and centroid > 0:
        weight = 0.18
        weight_sum += weight
        clo, chi = pkg["centroid_lo"], pkg["centroid_hi"]
        if clo <= centroid <= chi:
            score += weight
            reasons.append(f"centroid {centroid:.0f}Hz in package band")
        else:
            # distance penalty
            if centroid < clo:
                dist = (clo - centroid) / max(clo, 1)
            else:
                dist = (centroid - chi) / max(chi, 1)
            score += weight * _clamp01(1.0 - dist)

    lh = metrics.get("low_high_ratio")
    # 0.0 with no other spectral energy is "missing", not "thin"
    if lh is not None and float(lh) > 0.0:
        weight = 0.15
        weight_sum += weight
        thr = pkg.get("low_high_ratio_lo", 1.0)
        if lh >= thr:
            # more bass-forward = better for coldwave/cloud
            part = _clamp01(0.55 + 0.15 * min(lh / max(thr, 0.1), 3.0))
            score += weight * part
            reasons.append(f"low/high {lh:.2f}")
        else:
            # folk can be less bass-forward
            if pkg["id"] == "folk_horror":
                score += weight * 0.7
            else:
                score += weight * _clamp01(lh / thr) * 0.5

    sub = metrics.get("sub_bass_pct")
    bass = metrics.get("bass_pct")
    low_sum = None
    if sub is not None or bass is not None:
        low_sum = (sub or 0.0) + (bass or 0.0)
    if low_sum is not None:
        weight = 0.12
        weight_sum += weight
        bias = pkg.get("sub_bass_bias")
        if bias == "high":
            part = _clamp01((low_sum - 20.0) / 40.0)
            score += weight * part
            if part > 0.5:
                reasons.append(f"low-end {low_sum:.1f}%")
        elif bias == "mid":
            part = 1.0 - abs(low_sum - 30.0) / 40.0
            score += weight * _clamp01(part)
        else:
            score += weight * 0.5

    presence = metrics.get("presence_pct")
    brilliance = metrics.get("brilliance_pct")
    air = None
    if presence is not None or brilliance is not None:
        air = (presence or 0.0) + (brilliance or 0.0)
    if air is not None:
        weight = 0.08
        weight_sum += weight
        bias = pkg.get("presence_bias")
        if bias == "low":
            # dark packages prefer less presence/air
            part = _clamp01(1.0 - air / 35.0)
            score += weight * part
        else:
            part = _clamp01(air / 25.0)
            score += weight * part

    crest = metrics.get("crest_factor_db")
    if crest is not None:
        weight = 0.05
        weight_sum += weight
        clo, chi = pkg.get("crest_lo", 8), pkg.get("crest_hi", 18)
        if clo <= crest <= chi:
            score += weight
        else:
            score += weight * 0.3

    # normalize if some metrics missing
    if weight_sum <= 0:
        return 0.0, reasons
    norm = score / weight_sum
    return round(_clamp01(norm), 4), reasons


def _resolve_hint(genre_hint: str | None) -> str | None:
    if not genre_hint:
        return None
    raw = genre_hint.strip().lower()
    key = raw.replace("_", " ").replace("-", " ")
    # try direct / alias (hyphen/underscore/space variants)
    candidates = {
        raw,
        key,
        key.replace(" ", "_"),
        key.replace(" ", "-"),
        key.replace(" ", ""),
        raw.replace("-", "_"),
        raw.replace("_", "-"),
    }
    for c in candidates:
        if c in _HINT_ALIASES:
            return _HINT_ALIASES[c]
    for alias, pid in _HINT_ALIASES.items():
        alias_n = alias.replace("_", " ").replace("-", " ")
        if alias_n in key or key in alias_n:
            return pid
    # id match
    compact = key.replace(" ", "_")
    for pkg in PACKAGES:
        if pkg["id"] == compact or pkg["id"].replace("_", " ") in key:
            return pkg["id"]
    return None


def _format_style(template: str, bpm: float | int | None, key: str | None, mode: str | None) -> str:
    bpm_s = str(int(round(float(bpm)))) if bpm is not None else "120"
    try:
        return template.format(bpm=bpm_s, key=key or "A", mode=mode or "minor")
    except (KeyError, ValueError):
        return template.replace("{bpm}", bpm_s)


def _generic_style(metrics: dict[str, Any]) -> tuple[str, str, float]:
    """Fallback when no package scores well — still no vendor hype."""
    bpm = metrics.get("bpm")
    key = metrics.get("key") or "A"
    mode = metrics.get("mode") or "minor"
    bpm_s = str(int(round(float(bpm)))) if bpm is not None else "120"
    centroid = metrics.get("spectral_centroid_hz") or 0
    lh = metrics.get("low_high_ratio") or 1.0
    tags: list[str] = []

    if centroid and centroid < 1500:
        tags.append("dark atmospheric")
    elif centroid and centroid > 4000:
        tags.append("bright modern")
    else:
        tags.append("balanced modern production")

    if lh >= 2.0:
        tags.append("heavy low-end")
    elif lh <= 0.5:
        tags.append("thin high-forward")

    crest = metrics.get("crest_factor_db")
    if crest is not None and crest > 14:
        tags.append("dynamic mix")
    elif crest is not None and crest < 8:
        tags.append("compressed loud")

    style = (
        f"{', '.join(tags)}, {key} {mode}, {bpm_s} BPM, professional studio recording"
    )
    negatives = "no screaming, no vocal acrobatics, no festival drop"
    return style, negatives, 0.35


def metrics_from_analysis(
    *,
    bpm: float | None = None,
    bpm_confidence: float | None = None,
    key: str | None = None,
    mode: str | None = None,
    key_confidence: float | None = None,
    spectrum: dict | None = None,
    dynamics: dict | None = None,
    lufs_integrated: float | None = None,
    true_peak_db: float | None = None,
    duration_seconds: float | None = None,
) -> dict[str, Any]:
    """Flatten analysis tool outputs into a metrics dict for scoring."""
    spectrum = spectrum or {}
    dynamics = dynamics or {}
    bands = spectrum.get("bands") or []
    m: dict[str, Any] = {
        "bpm": bpm,
        "bpm_confidence": bpm_confidence,
        "key": key,
        "mode": mode,
        "key_confidence": key_confidence,
        "spectral_centroid_hz": spectrum.get("spectral_centroid_hz"),
        "spectral_rolloff_95_hz": spectrum.get("spectral_rolloff_95_hz")
        or spectrum.get("spectral_rolloff_hz"),
        "low_high_ratio": spectrum.get("low_high_ratio"),
        "sub_bass_pct": _band_pct(bands, "sub_bass"),
        "bass_pct": _band_pct(bands, "bass"),
        "low_mids_pct": _band_pct(bands, "low_mids"),
        "mids_pct": _band_pct(bands, "mids"),
        "high_mids_pct": _band_pct(bands, "high_mids"),
        "presence_pct": _band_pct(bands, "presence"),
        "brilliance_pct": _band_pct(bands, "brilliance"),
        "crest_factor_db": dynamics.get("crest_factor_db"),
        "loudness_range_db": dynamics.get("loudness_range_db"),
        "transient_density": dynamics.get("transient_density"),
        "lufs_integrated": lufs_integrated,
        "true_peak_db": true_peak_db,
        "duration_seconds": duration_seconds,
        "bands": bands,
    }
    return m


def infer_from_metrics(
    metrics: dict[str, Any],
    *,
    genre_hint: str | None = None,
    compact: bool = True,
) -> dict[str, Any]:
    """Map analysis metrics → Suno style package.

    Pure function — unit-testable with fixture metrics.
    Does not hallucinate vendor hype; low-confidence fields are labeled.
    """
    if not isinstance(metrics, dict):
        return enrich_error({
            "error": "metrics must be a dict",
            "error_code": "INVALID_PARAMETER",
        })

    hint_id = _resolve_hint(genre_hint)
    scored: list[tuple[float, dict, list[str]]] = []
    for pkg in PACKAGES:
        s, reasons = _score_package(pkg, metrics)
        if hint_id and pkg["id"] == hint_id:
            s = _clamp01(s * 0.55 + 0.45)  # strong boost, not hard lock
            reasons = reasons + [f"genre_hint={genre_hint}"]
        scored.append((s, pkg, reasons))
    scored.sort(key=lambda x: x[0], reverse=True)

    best_score, best_pkg, best_reasons = scored[0]
    second = scored[1][0] if len(scored) > 1 else 0.0
    margin = best_score - second

    bpm = metrics.get("bpm")
    key = metrics.get("key")
    mode = metrics.get("mode")

    # Sparse metrics (no bpm / no spectrum energy) → force generic unless hint
    has_bpm = bpm is not None
    has_spectrum = bool(
        (metrics.get("spectral_centroid_hz") or 0) > 0
        or (metrics.get("low_high_ratio") or 0) > 0
        or metrics.get("sub_bass_pct") is not None
        or metrics.get("bass_pct") is not None
    )
    sparse_metrics = not has_bpm and not has_spectrum

    # Confidence: package score + separation from runner-up + analysis confidences
    conf_parts = [best_score]
    if margin > 0:
        conf_parts.append(_clamp01(0.5 + margin))
    bc = metrics.get("bpm_confidence")
    kc = metrics.get("key_confidence")
    if bc is not None and has_bpm:
        conf_parts.append(float(bc) * 0.5 + 0.5)
    if kc is not None and key:
        conf_parts.append(float(kc) * 0.5 + 0.5)
    confidence = round(sum(conf_parts) / len(conf_parts), 3)
    if sparse_metrics:
        confidence = min(confidence, 0.3)

    low_confidence = sparse_metrics or confidence < 0.45 or best_score < 0.40
    used_generic = False

    if low_confidence and not hint_id:
        style, negatives, conf_floor = _generic_style(metrics)
        confidence = min(confidence, conf_floor)
        package_id = None
        package_label = None
        package_file = None
        used_generic = True
        reasons = ["low package confidence → generic tags"]
        style_full = style
    else:
        tmpl = best_pkg["style"] if compact else best_pkg["style_full"]
        style = _format_style(tmpl, bpm, key, mode)
        style_full = _format_style(best_pkg["style_full"], bpm, key, mode)
        negatives = best_pkg["negatives"]
        package_id = best_pkg["id"]
        package_label = best_pkg["label"]
        package_file = best_pkg["package_file"]
        reasons = best_reasons
        if hint_id and best_pkg["id"] != hint_id:
            # hint pointed elsewhere but another package scored higher after soft boost
            reasons = reasons + [f"hint {hint_id} not top after metrics"]

    # Key string for response
    key_str = None
    if key:
        key_str = f"{key} {mode}" if mode else str(key)

    # Label uncertain fields
    uncertain: list[str] = []
    if bc is not None and float(bc) < 0.4:
        uncertain.append("bpm")
    if kc is not None and float(kc) < 0.4:
        uncertain.append("key")
    if metrics.get("spectral_centroid_hz") in (None, 0, 0.0):
        uncertain.append("spectrum")

    ranking = [
        {
            "id": pkg["id"],
            "score": round(s, 4),
            "label": pkg["label"],
        }
        for s, pkg, _ in scored
    ]

    kb_root = resolve_kb_root()
    package_path = None
    if package_file and kb_root:
        package_path = str(kb_root / package_file)

    result: dict[str, Any] = {
        "success": True,
        "bpm": bpm,
        "key": key_str,
        "key_root": key,
        "mode": mode,
        "style": style,
        "style_full": style_full,
        "negatives": negatives,
        "confidence": confidence,
        "low_confidence": bool(low_confidence and used_generic) or confidence < 0.45,
        "package_id": package_id,
        "package_label": package_label,
        "package_file": package_file,
        "package_path": package_path,
        "used_generic": used_generic,
        "match_reasons": reasons,
        "uncertain_fields": uncertain,
        "ranking": ranking,
        "analysis": {
            "bpm": bpm,
            "bpm_confidence": bc,
            "key": key,
            "mode": mode,
            "key_confidence": kc,
            "spectral_centroid_hz": metrics.get("spectral_centroid_hz"),
            "low_high_ratio": metrics.get("low_high_ratio"),
            "sub_bass_pct": metrics.get("sub_bass_pct"),
            "bass_pct": metrics.get("bass_pct"),
            "presence_pct": metrics.get("presence_pct"),
            "brilliance_pct": metrics.get("brilliance_pct"),
            "crest_factor_db": metrics.get("crest_factor_db"),
            "transient_density": metrics.get("transient_density"),
            "lufs_integrated": metrics.get("lufs_integrated"),
            "true_peak_db": metrics.get("true_peak_db"),
            "duration_seconds": metrics.get("duration_seconds"),
        },
    }
    return result


def analyze_file_metrics(filename: str) -> dict[str, Any]:
    """Load WAV and run pure-python analysis → metrics dict.

    No DAW bridge. Uses opendaw_mcp.utils helpers.
    """
    from opendaw_mcp.utils import (
        _analyze_dynamics,
        _analyze_spectrum,
        _compute_lufs,
        _detect_bpm,
        _detect_key,
        _load_wav_for_analysis,
    )

    try:
        channels, sr, fpath = _load_wav_for_analysis(filename)
    except FileNotFoundError as e:
        return {
            "error": str(e),
            "error_code": "NOT_FOUND",
            "hint": "Pass exports-relative name or absolute WAV path",
        }

    if not channels or not channels[0]:
        return {
            "error": "Empty or silent audio",
            "error_code": "INVALID_PARAMETER",
            "hint": "File has no samples",
        }

    # Silence guard: max abs == 0
    peak = 0.0
    for ch in channels:
        for s in ch[: min(len(ch), sr * 2)]:  # first 2s sample
            a = abs(s)
            if a > peak:
                peak = a
    if peak <= 0.0:
        # full scan if first 2s silent
        peak = max((abs(s) for ch in channels for s in ch), default=0.0)
    if peak <= 0.0:
        return {
            "error": "Silent audio (all zeros)",
            "error_code": "INVALID_PARAMETER",
            "hint": "Re-export or pick another file",
        }

    bpm_data: dict[str, Any] = {}
    key_data: dict[str, Any] = {}
    spectrum: dict[str, Any] = {}
    dynamics: dict[str, Any] = {}
    lufs_data: dict[str, Any] = {}

    try:
        bpm_data = _detect_bpm(channels, sr)
    except Exception:
        bpm_data = {"bpm": None, "confidence": 0.0}
    try:
        key_data = _detect_key(channels, sr)
    except Exception:
        key_data = {"key": None, "mode": None, "confidence": 0.0}
    try:
        spectrum = _analyze_spectrum(channels, sr)
    except Exception:
        spectrum = {}
    try:
        dynamics = _analyze_dynamics(channels, sr)
    except Exception:
        dynamics = {}
    try:
        lufs_data = _compute_lufs(channels, sr)
    except Exception:
        lufs_data = {}

    duration = None
    try:
        duration = round(len(channels[0]) / float(sr), 2)
    except Exception:
        pass

    metrics = metrics_from_analysis(
        bpm=bpm_data.get("bpm"),
        bpm_confidence=bpm_data.get("confidence"),
        key=key_data.get("key"),
        mode=key_data.get("mode"),
        key_confidence=key_data.get("confidence"),
        spectrum=spectrum,
        dynamics=dynamics,
        lufs_integrated=lufs_data.get("lufs_integrated"),
        true_peak_db=lufs_data.get("true_peak_db"),
        duration_seconds=duration,
    )
    metrics["file"] = fpath
    return metrics


def infer_suno_prompt(
    filename: str | None = None,
    *,
    genre_hint: str | None = None,
    compact: bool = True,
    metrics: dict[str, Any] | None = None,
    record_lineage: bool = False,
    parent_id: str | None = None,
    label: str | None = None,
) -> dict[str, Any]:
    """End-to-end: file or metrics → style package (+ optional lineage).

    Pure analysis path when metrics given — no file I/O.
    """
    if metrics is None:
        if not filename:
            return enrich_error({
                "error": "filename or metrics required",
                "error_code": "INVALID_PARAMETER",
            })
        metrics = analyze_file_metrics(filename)
        if "error" in metrics:
            return enrich_error(metrics)

    result = infer_from_metrics(metrics, genre_hint=genre_hint, compact=compact)
    if "error" in result:
        return enrich_error(result)

    result["file"] = metrics.get("file") or filename

    if record_lineage:
        try:
            from opendaw_mcp.lineage import get_store

            store = get_store()
            # Ensure parent exists or omit
            pid = parent_id or None
            if pid:
                if store.get_node(pid) is None:
                    result["lineage_warning"] = f"unknown parent_id {pid}; recording as root"
                    pid = None

            analysis_node = store.record(
                kind="analysis",
                path=result.get("file"),
                parent_id=pid,
                op="analyze",
                metrics={
                    k: result["analysis"].get(k)
                    for k in (
                        "lufs_integrated",
                        "true_peak_db",
                        "sub_bass_pct",
                        "presence_pct",
                        "bpm",
                    )
                    if result["analysis"].get(k) is not None
                },
                provenance={"source": "opendaw", "tool": "infer_suno_prompt"},
                label=label or "prompt-inference analysis",
            )
            if "error" in analysis_node:
                result["lineage_error"] = analysis_node
            else:
                prompt_node = store.record(
                    kind="prompt",
                    path=None,
                    parent_id=analysis_node["node"]["id"],
                    op="prompt_infer",
                    params={
                        "package_id": result.get("package_id"),
                        "genre_hint": genre_hint,
                        "compact": compact,
                    },
                    metrics={"confidence": result.get("confidence")},
                    provenance={
                        "source": "opendaw",
                        "style": result.get("style"),
                        "negatives": result.get("negatives"),
                        "package_id": result.get("package_id"),
                    },
                    label=label or "inferred suno prompt",
                )
                result["lineage"] = {
                    "analysis_node_id": analysis_node["node"]["id"],
                    "prompt_node_id": prompt_node.get("node", {}).get("id"),
                    "edge_op": "prompt_infer",
                }
                if "error" in prompt_node:
                    result["lineage_error"] = prompt_node
        except Exception as e:
            result["lineage_error"] = str(e)

    return result
