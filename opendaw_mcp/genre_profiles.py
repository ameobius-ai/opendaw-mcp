"""
Genre reference profiles for mix analysis.
Based on Phantom's profile system + industry standards.

Each profile defines:
- target_lufs: integrated loudness target
- lufs_range: acceptable range
- spectral_targets: per-band energy % targets
- stereo_width_target: side/mid ratio
- dynamic_range_target: crest factor dB
- spectral_centroid_target: brightness Hz
- characteristics: textual description
"""

from typing import Any

PROFILES: dict[str, dict[str, Any]] = {
    "pop": {
        "target_lufs": -10,
        "lufs_range": (-10, -7),
        "spectral_targets": {
            "sub_bass": (8, 15),
            "bass": (15, 25),
            "low_mids": (10, 18),
            "mids": (20, 30),
            "high_mids": (12, 20),
            "presence": (8, 15),
            "brilliance": (5, 12),
        },
        "stereo_width_target": (0.3, 0.5),
        "dynamic_range_target": (6, 10),
        "spectral_centroid_target": (2500, 4000),
        "characteristics": "Polished, vocal-forward, controlled dynamics, 4kHz presence boost",
        "mix_priorities": ["vocal clarity at 2-4kHz", "controlled low end", "wide but mono-compatible stereo"],
    },
    "rock": {
        "target_lufs": -10,
        "lufs_range": (-10, -8),
        "spectral_targets": {
            "sub_bass": (10, 18),
            "bass": (18, 28),
            "low_mids": (12, 20),
            "mids": (18, 28),
            "high_mids": (12, 20),
            "presence": (8, 15),
            "brilliance": (5, 10),
        },
        "stereo_width_target": (0.4, 0.6),
        "dynamic_range_target": (7, 12),
        "spectral_centroid_target": (2000, 3500),
        "characteristics": "Wide stereo, prominent guitars, punchy drums",
        "mix_priorities": ["guitar presence", "punchy drums", "wide stereo field"],
    },
    "hip_hop": {
        "target_lufs": -10,
        "lufs_range": (-10, -6),
        "spectral_targets": {
            "sub_bass": (15, 25),
            "bass": (20, 30),
            "low_mids": (8, 15),
            "mids": (12, 22),
            "high_mids": (10, 18),
            "presence": (8, 15),
            "brilliance": (5, 12),
        },
        "stereo_width_target": (0.25, 0.45),
        "dynamic_range_target": (5, 9),
        "spectral_centroid_target": (1800, 3000),
        "characteristics": "Heavy low end, crisp highs, compressed dynamics",
        "mix_priorities": ["sub-bass weight", "kick punch", "vocal intelligibility above beat"],
    },
    "electronic": {
        "target_lufs": -9,
        "lufs_range": (-9, -6),
        "spectral_targets": {
            "sub_bass": (15, 22),
            "bass": (18, 25),
            "low_mids": (8, 15),
            "mids": (15, 25),
            "high_mids": (12, 20),
            "presence": (10, 18),
            "brilliance": (8, 15),
        },
        "stereo_width_target": (0.45, 0.7),
        "dynamic_range_target": (5, 8),
        "spectral_centroid_target": (2500, 4500),
        "characteristics": "Wide stereo, sub-bass emphasis, bright top end",
        "mix_priorities": ["sub-bass power", "wide stereo", "crisp transients"],
    },
    "edm": {
        "target_lufs": -8,
        "lufs_range": (-8, -5),
        "spectral_targets": {
            "sub_bass": (18, 25),
            "bass": (18, 25),
            "low_mids": (6, 12),
            "mids": (12, 22),
            "high_mids": (12, 22),
            "presence": (12, 20),
            "brilliance": (10, 18),
        },
        "stereo_width_target": (0.5, 0.8),
        "dynamic_range_target": (4, 7),
        "spectral_centroid_target": (3000, 5000),
        "characteristics": "Loud, sidechain pumping, wide and bright",
        "mix_priorities": ["maximum loudness", "sidechain pump", "supersaw width"],
    },
    "metal": {
        "target_lufs": -8,
        "lufs_range": (-8, -5),
        "spectral_targets": {
            "sub_bass": (10, 18),
            "bass": (15, 22),
            "low_mids": (10, 18),
            "mids": (15, 25),
            "high_mids": (15, 22),
            "presence": (12, 20),
            "brilliance": (8, 15),
        },
        "stereo_width_target": (0.35, 0.55),
        "dynamic_range_target": (5, 9),
        "spectral_centroid_target": (2500, 4000),
        "characteristics": "Dense, scooped mids, aggressive compression",
        "mix_priorities": ["double-kick clarity", "guitar wall", "vocal cut through density"],
    },
    "lo-fi": {
        "target_lufs": -16,
        "lufs_range": (-16, -12),
        "spectral_targets": {
            "sub_bass": (12, 20),
            "bass": (18, 28),
            "low_mids": (15, 25),
            "mids": (15, 22),
            "high_mids": (8, 15),
            "presence": (5, 10),
            "brilliance": (3, 8),
        },
        "stereo_width_target": (0.15, 0.35),
        "dynamic_range_target": (8, 14),
        "spectral_centroid_target": (1000, 2000),
        "characteristics": "Warm, rolled-off highs, narrow stereo, intentionally quiet",
        "mix_priorities": ["warmth", "vinyl/tape texture", "soft transients"],
    },
    "ambient": {
        "target_lufs": -20,
        "lufs_range": (-20, -14),
        "spectral_targets": {
            "sub_bass": (10, 20),
            "bass": (12, 22),
            "low_mids": (12, 20),
            "mids": (18, 28),
            "high_mids": (12, 22),
            "presence": (8, 15),
            "brilliance": (8, 15),
        },
        "stereo_width_target": (0.5, 0.8),
        "dynamic_range_target": (12, 20),
        "spectral_centroid_target": (2000, 4000),
        "characteristics": "Wide, dynamic, gentle spectral curve",
        "mix_priorities": ["space and depth", "long reverb tails", "dynamic range preservation"],
    },
    "cinematic": {
        "target_lufs": -18,
        "lufs_range": (-20, -14),
        "spectral_targets": {
            "sub_bass": (15, 25),
            "bass": (15, 25),
            "low_mids": (10, 18),
            "mids": (15, 25),
            "high_mids": (10, 18),
            "presence": (8, 15),
            "brilliance": (5, 12),
        },
        "stereo_width_target": (0.4, 0.7),
        "dynamic_range_target": (12, 18),
        "spectral_centroid_target": (1500, 3000),
        "characteristics": "Dark, heavy, wide, dramatic dynamic swings",
        "mix_priorities": ["sub-bass impact", "orchestral width", "dramatic dynamics"],
    },
}


def get_profile(genre: str) -> dict[str, Any] | None:
    """Get genre profile by name (case-insensitive, hyphen/space/underscore agnostic)."""
    key = genre.lower()
    candidates = (
        key,
        key.replace("-", "_").replace(" ", "_"),
        key.replace("_", "-"),
    )
    for cand in candidates:
        if cand in PROFILES:
            return PROFILES[cand]
    return None


def list_genres() -> list[str]:
    """List all available genre profiles."""
    return sorted(PROFILES.keys())
