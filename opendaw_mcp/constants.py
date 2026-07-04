"""
Module-level lookup tables for opendaw-mcp.

Extracted from server.py for testability and maintainability.
These map human-readable parameter names to the integer indices
used by the openDAW DAW engine.
"""

# Tidal device rate settings (LFO / sequencer sync rates)
TIDAL_RATE_MAP: dict[str, int] = {
    "1/1": 0, "1/2": 1, "1/3": 2, "1/4": 3, "3/16": 4, "1/6": 5, "1/8": 6,
    "3/32": 7, "1/12": 8, "1/16": 9, "3/64": 10, "1/24": 11, "1/32": 12,
    "1/48": 13, "1/64": 14, "1/96": 15, "1/128": 16,
}

# Delay device sync settings
DELAY_SYNC_MAP: dict[str, int] = {
    "off": 0, "1/128": 1, "1/96": 2, "1/64": 3, "1/48": 4, "1/32": 5,
    "1/24": 6, "3/64": 7, "1/16": 8, "1/12": 9, "3/32": 10, "1/8": 11,
    "1/6": 12, "3/16": 13, "1/4": 14, "5/16": 15, "1/3": 16, "3/8": 17,
    "7/16": 18, "1/2": 19, "1/1": 20,
}

# Waveshaper function expressions (JS code evaluated in the DAW context)
WAVESHAPER_FUNCS: dict[str, str] = {
    "hardclip": "min(1, max(-1, x))",
    "cubicSoft": "x - (x*x*x) / 3.0",
    "tanh": "tanh(x)",
    "sigmoid": "2.0 / (1.0 + exp(-x)) - 1.0",
    "arctan": "atan(x) / (PI/2)",
    "asymmetric": "x > 0 ? tanh(x*1.5) : tanh(x*0.7)",
}

# Revamp EQ sections (order matters — matches the DAW's internal section order)
REVAMP_SECTIONS: tuple[str, ...] = (
    "highPass", "lowShelf", "lowBell", "midBell",
    "highBell", "highShelf", "lowPass",
)
