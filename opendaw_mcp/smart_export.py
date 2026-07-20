"""Smart export — platform bounce over file-only post-master path.

One call: platform LUFS + true-peak ceiling + optional lineage edge.
No DAW bridge required (dry-run and file path both pure Python).

Kanban: t_20bc5cb3 / docs/smart-export-spec.md
"""

from __future__ import annotations

import math
import os
import struct
from pathlib import Path
from typing import Any

from opendaw_mcp.utils import _compute_lufs, _parse_wav, _safe_filename

# Spec table (docs/smart-export-spec.md). Club is -9 / -0.3 (export), not auto_master's -8.
PLATFORM_PRESETS: dict[str, dict[str, float]] = {
    "spotify": {"target_lufs": -14.0, "ceiling_dbtp": -1.0},
    "apple": {"target_lufs": -16.0, "ceiling_dbtp": -1.0},
    "youtube": {"target_lufs": -14.0, "ceiling_dbtp": -1.0},
    "tidal": {"target_lufs": -14.0, "ceiling_dbtp": -1.0},
    "soundcloud": {"target_lufs": -14.0, "ceiling_dbtp": -1.0},
    "club": {"target_lufs": -9.0, "ceiling_dbtp": -0.3},
}

VALID_PLATFORMS = frozenset(PLATFORM_PRESETS.keys())

# Allow tiny float noise when verifying ceiling compliance
_TP_EPS = 0.05


def _export_dir() -> Path:
    return Path(
        os.environ.get(
            "OPENDAW_EXPORT_DIR",
            str(Path(__file__).resolve().parent.parent / "exports"),
        )
    ).expanduser().resolve()


def resolve_input_path(filename: str) -> Path:
    """Resolve WAV in OPENDAW_EXPORT_DIR or as absolute/relative path."""
    if not filename or not str(filename).strip():
        raise FileNotFoundError("filename required")
    name = str(filename).strip()
    candidates: list[Path] = []
    p = Path(name).expanduser()
    if p.is_absolute():
        candidates.append(p)
    else:
        export = _export_dir()
        base = name if name.lower().endswith(".wav") else f"{name}.wav"
        candidates.append(export / base)
        candidates.append(export / name)
        candidates.append(Path.cwd() / name)
        candidates.append(Path.cwd() / base)
        candidates.append(p)
    for c in candidates:
        try:
            rp = c.resolve()
        except OSError:
            continue
        if rp.is_file():
            return rp
    raise FileNotFoundError(f"File not found: {filename}")


def get_platform_preset(platform: str) -> dict[str, float]:
    key = (platform or "").strip().lower()
    if key not in PLATFORM_PRESETS:
        raise ValueError(
            f"Invalid platform: {platform}. Valid: {sorted(VALID_PLATFORMS)}"
        )
    return dict(PLATFORM_PRESETS[key])


def measure_file(path: Path | str) -> dict[str, Any]:
    raw = Path(path).read_bytes()
    wav = _parse_wav(raw)
    metrics = _compute_lufs(wav["channels"], wav["sample_rate"])
    return {
        **metrics,
        "sample_rate": wav["sample_rate"],
        "channels": wav["n_channels"],
        "n_frames": wav["n_frames"],
        "duration_seconds": round(wav["n_frames"] / wav["sample_rate"], 3),
        "audio_format": wav["audio_format"],
        "bits_per_sample": wav["bits_per_sample"],
        "_wav": wav,
    }


def _soft_clip_channels(channels: list[list[float]], ceiling_lin: float) -> list[list[float]]:
    """Soft clip toward ceiling, then hard clamp. ceiling_lin in linear (0-1)."""
    if ceiling_lin <= 0:
        ceiling_lin = 1e-6
    out: list[list[float]] = []
    for ch in channels:
        row: list[float] = []
        for s in ch:
            a = abs(s)
            if a <= ceiling_lin:
                row.append(s)
            else:
                # tanh soft overshoot then clamp
                sign = 1.0 if s >= 0 else -1.0
                over = a / ceiling_lin
                soft = ceiling_lin * math.tanh(over)
                if soft > ceiling_lin:
                    soft = ceiling_lin
                row.append(sign * soft)
        out.append(row)
    return out


def _apply_gain(channels: list[list[float]], gain_lin: float) -> list[list[float]]:
    return [[s * gain_lin for s in ch] for ch in channels]


def write_float32_wav(path: Path | str, channels: list[list[float]], sample_rate: int) -> None:
    """Write IEEE float32 stereo/mono WAV (format tag 3)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    n_ch = len(channels)
    n_frames = len(channels[0]) if channels else 0
    for ch in channels:
        if len(ch) != n_frames:
            raise ValueError("channel length mismatch")
    # interleave
    interleaved = []
    for i in range(n_frames):
        for c in range(n_ch):
            interleaved.append(float(channels[c][i]))
    data = struct.pack(f"<{n_frames * n_ch}f", *interleaved)
    byte_rate = sample_rate * n_ch * 4
    block_align = n_ch * 4
    # RIFF size = 4 + (8+fmt) + (8+data) = 4 + 24 + 8 + len(data) for 16-byte fmt? 
    # fmt chunk size 16 for PCM-like float
    fmt_chunk = struct.pack(
        "<HHIIHH",
        3,  # IEEE float
        n_ch,
        sample_rate,
        byte_rate,
        block_align,
        32,
    )
    riff_size = 4 + (8 + len(fmt_chunk)) + (8 + len(data))
    with open(path, "wb") as f:
        f.write(b"RIFF")
        f.write(struct.pack("<I", riff_size))
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write(struct.pack("<I", len(fmt_chunk)))
        f.write(fmt_chunk)
        f.write(b"data")
        f.write(struct.pack("<I", len(data)))
        f.write(data)


def _plan_gain(input_lufs: float, target_lufs: float) -> float:
    """Linear gain to move integrated LUFS toward target."""
    gain_db = target_lufs - input_lufs
    return 10 ** (gain_db / 20.0)


def export_for_platform(
    platform: str,
    filename: str,
    *,
    parent_id: str = "",
    dry_run: bool = False,
    output_name: str = "",
    lineage_store: Any | None = None,
    strict_ceiling: bool = True,
) -> dict[str, Any]:
    """Platform bounce: normalize LUFS, enforce TP ceiling, optional lineage.

    Returns success dict or {error, error_code, hint}.
    """
    try:
        preset = get_platform_preset(platform)
    except ValueError as e:
        return {
            "error": str(e),
            "error_code": "INVALID_PARAMETER",
            "hint": f"Valid platforms: {sorted(VALID_PLATFORMS)}",
        }

    target_lufs = float(preset["target_lufs"])
    ceiling_dbtp = float(preset["ceiling_dbtp"])
    ceiling_lin = 10 ** (ceiling_dbtp / 20.0)
    platform_key = platform.strip().lower()

    try:
        in_path = resolve_input_path(filename)
    except FileNotFoundError as e:
        return {
            "error": str(e),
            "error_code": "NOT_FOUND",
            "hint": "Pass a WAV in OPENDAW_EXPORT_DIR or an absolute path",
        }

    try:
        measured_in = measure_file(in_path)
    except Exception as e:
        return {
            "error": f"Measure failed: {e}",
            "error_code": "INVALID_PARAMETER",
        }

    wav = measured_in.pop("_wav")
    in_metrics = {
        "lufs_integrated": measured_in["lufs_integrated"],
        "true_peak_db": measured_in["true_peak_db"],
        "max_sample": measured_in["max_sample"],
        "duration_seconds": measured_in["duration_seconds"],
    }

    gain_lin = _plan_gain(in_metrics["lufs_integrated"], target_lufs)
    gain_db = 20 * math.log10(gain_lin) if gain_lin > 0 else -120.0

    out_base = _safe_filename(output_name) if output_name else (
        f"{_safe_filename(in_path.stem)}_{platform_key}"
    )
    out_path = _export_dir() / f"{out_base}.wav"

    plan = {
        "platform": platform_key,
        "target_lufs": target_lufs,
        "ceiling_dbtp": ceiling_dbtp,
        "input_path": str(in_path),
        "output_path": str(out_path),
        "output_name": out_base,
        "planned_gain_db": round(gain_db, 3),
        "input_metrics": in_metrics,
        "dry_run": bool(dry_run),
    }

    if dry_run:
        # Estimate post-gain peak (sample-based, same as utils TP)
        est_peak = in_metrics["max_sample"] * gain_lin
        est_tp = 20 * math.log10(est_peak) if est_peak > 0 else -120.0
        would_need_limit = est_tp > ceiling_dbtp + _TP_EPS
        return {
            "success": True,
            "dry_run": True,
            "plan": plan,
            "estimated_true_peak_db_pre_limit": round(est_tp, 2),
            "would_apply_limiter": would_need_limit,
            "note": "dry_run — no file written, no lineage recorded",
        }

    # Process: gain → soft clip to ceiling → re-measure
    channels = _apply_gain(wav["channels"], gain_lin)
    channels = _soft_clip_channels(channels, ceiling_lin)

    # Final LUFS touch-up if still far (after limiting may have dropped LUFS)
    mid_metrics = _compute_lufs(channels, wav["sample_rate"])
    if abs(mid_metrics["lufs_integrated"] - target_lufs) > 0.35:
        touch = _plan_gain(mid_metrics["lufs_integrated"], target_lufs)
        # Don't overshoot ceiling: cap touch so peak stays under ceiling
        peak = mid_metrics["max_sample"]
        max_touch = (ceiling_lin / peak) if peak > 0 else 1.0
        if max_touch > 0:
            touch = min(touch, max_touch)
        channels = _apply_gain(channels, touch)
        channels = _soft_clip_channels(channels, ceiling_lin)

    out_metrics = _compute_lufs(channels, wav["sample_rate"])
    tp = float(out_metrics["true_peak_db"])

    # Hard fail before write when TP exceeds ceiling (acceptance: fails if TP above ceiling)
    if strict_ceiling and tp > ceiling_dbtp + _TP_EPS:
        return {
            "error": (
                f"True peak {tp:.2f} dBTP exceeds ceiling "
                f"{ceiling_dbtp:.1f} dBTP for platform={platform_key}"
            ),
            "error_code": "INVALID_PARAMETER",
            "hint": "Lower input level or use a quieter platform target",
            "metrics": {
                "lufs_integrated": out_metrics["lufs_integrated"],
                "true_peak_db": out_metrics["true_peak_db"],
                "max_sample": out_metrics["max_sample"],
            },
            "plan": plan,
        }

    write_float32_wav(out_path, channels, wav["sample_rate"])

    result: dict[str, Any] = {
        "success": True,
        "dry_run": False,
        "platform": platform_key,
        "target_lufs": target_lufs,
        "ceiling_dbtp": ceiling_dbtp,
        "input_path": str(in_path),
        "output_path": str(out_path),
        "output_name": out_base,
        "gain_db": round(gain_db, 3),
        "input_metrics": in_metrics,
        "metrics": {
            "lufs_integrated": out_metrics["lufs_integrated"],
            "true_peak_db": out_metrics["true_peak_db"],
            "max_sample": out_metrics["max_sample"],
            "crest": round(
                out_metrics["true_peak_db"] - out_metrics["lufs_integrated"], 2
            )
            if out_metrics.get("lufs_integrated") is not None
            else None,
        },
        "ceiling_ok": tp <= ceiling_dbtp + _TP_EPS,
        "lufs_error": round(out_metrics["lufs_integrated"] - target_lufs, 2),
    }

    # Always record export node; parent_id attaches edge when provided
    try:
        from opendaw_mcp.lineage import get_store

        store = lineage_store if lineage_store is not None else get_store()
        params = {
            "platform": platform_key,
            "target_lufs": target_lufs,
            "ceiling_dbtp": ceiling_dbtp,
            "gain_db": round(gain_db, 3),
        }
        metrics = {
            "lufs_integrated": out_metrics["lufs_integrated"],
            "true_peak_db": out_metrics["true_peak_db"],
            "max_sample": out_metrics["max_sample"],
        }
        rec = store.record(
            kind="export",
            path=str(out_path),
            parent_id=parent_id or None,
            op="export",
            params=params,
            metrics=metrics,
            provenance={
                "source": "smart_export",
                "platform": platform_key,
                "input": str(in_path),
            },
            label=f"export:{platform_key}:{out_base}",
        )
        if "error" in rec:
            result["lineage_error"] = rec
        else:
            result["lineage"] = {
                "node_id": rec["node"]["id"],
                "edge_id": rec.get("edge", {}).get("id") if rec.get("edge") else None,
                "parent_id": parent_id or None,
            }
    except Exception as e:
        result["lineage_error"] = str(e)

    return result
