#!/usr/bin/env python3
"""Auto-fix malformed @param declarations in Werkstatt scripts.

Three patterns of breakage:
  1. type-then-values: // @param attack linear 0.001 0.1 0.005
     → fix: move type after values
  2. missing min/max:  // @param threshold 0.5 linear
     → fix: add 0 1 as min/max (infer from comment if possible)
  3. mixed: some params in same file may be valid

Usage:
  venv/bin/python autofix_params.py --all          # fix all scripts
  venv/bin/python autofix_params.py --check ssl    # fix by name match
  venv/bin/python autofix_params.py file1.js file2.js
"""
import os
import re
import sys
import glob

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "scripts")

NUM = r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?'

# Valid: // @param name default min max [type] [unit]
VALID = re.compile(
    rf'^//\s*@param\s+(\w+)\s+({NUM})\s+({NUM})\s+({NUM})(?:\s+(\w+))?(?:\s+(.+))?$'
)

# Pattern 1: type-then-values: // @param name TYPE min max default
# e.g. // @param attack linear 0.001 0.1 0.005
PATTERN_TYPE_FIRST = re.compile(
    r'^(//\s*@param\s+(\w+)\s+)(\w+)\s+(' + NUM + r')\s+(' + NUM + r')\s+(' + NUM + r')(?:\s+(.+))?$'
)

# Pattern 2: missing min/max: // @param name default TYPE  // comment
# e.g. // @param threshold 0.5 linear
PATTERN_MISSING_RANGE = re.compile(
    r'^(//\s*@param\s+(\w+)\s+)(' + NUM + r')\s+(\w+)(?:\s{2,}//.*)?$'
)

# Known ranges for specific param names (from comments and common sense)
KNOWN_RANGES = {
    "output": ("-24", "6"),
    "threshold": ("0", "1"),
    "ratio": ("0", "1"),
    "attack": ("0", "1"),
    "release": ("0", "1"),
    "makeup": ("0", "1"),
    "mix": ("0", "1"),
    "drive": ("0", "1"),
    "tube": ("0", "1"),
    "gain": ("0", "1"),
    "speed": ("0", "1"),
    "damp": ("0", "1"),
    "decay": ("0", "1"),
    "spread": ("0", "1"),
    "feedback": ("-0.95", "0.95"),
    "stereo": ("0", "1"),
    "depth": ("0", "1"),
    "auto_release": ("0", "1"),
    "frequency": ("0", "1"),
    "harmonics": ("0", "1"),
    "intensity": ("0", "1"),
    "peak_reduce": ("0", "1"),
    "low_sat": ("0", "1"),
    "mid_sat": ("0", "1"),
    "high_sat": ("0", "1"),
    "blend": ("0", "1"),
    "resonance": ("0", "1"),
    "presence": ("0", "1"),
    "cab_type": ("0", "1"),
    "room_size": ("0", "1"),
    "damping": ("0", "1"),
    "predelay": ("0", "1"),
    "width": ("0", "1"),
    "bias": ("-0.5", "0.5"),
    "warmth": ("0", "1"),
    "miller": ("0", "1"),
    "rate": ("0.1", "8"),
    "stages": ("2", "12"),
    "base_freq": ("100", "8000"),
    # Read-only meters
    "correlation": ("-1", "1"),
    "peak_freq": ("0", "20000"),
    "centroid": ("0", "20000"),
    "rolloff": ("0", "20000"),
    "low_level": ("0", "1"),
    "mid_level": ("0", "1"),
    "high_level": ("0", "1"),
    "crest": ("0", "20"),
    "mono_compat": ("0", "1"),
    "balance": ("-1", "1"),
    "peak_corr": ("-1", "1"),
    "min_freq": ("100", "2000"),
    "max_freq": ("500", "8000"),
    "q": ("0.5", "4.0"),
    "freq": ("80", "300"),
}


def fix_param_line(line):
    """Try to fix a single @param line. Returns (fixed_line, was_fixed)."""
    # Already valid?
    if VALID.match(line):
        return line, False

    result = PATTERN_TYPE_FIRST.match(line)
    if result:
        prefix = result.group(1)   # // @param name 
        name = result.group(2)
        ptype = result.group(3)    # linear/exp/int/bool
        # Could be min max default OR default min max
        v1, v2, v3 = result.group(4), result.group(5), result.group(6)
        rest = result.group(7) or ""
        # Heuristic: if last value has decimal and first is small, it's min/max/default
        # For "linear 0.001 0.1 0.005" → min=0.001 max=0.1 default=0.005
        # For "linear 0 0 1" → default=0 min=0 max=1
        # For "exp 0 -24 6" → default=0 min=-24 max=6
        # Pattern: TYPE min max default (4 tokens after name)
        # OR: TYPE default min max (if first value is between 0-1 and others span wider)
        # Simplest: treat as TYPE default min max (openDAW standard order after name)
        # But the values after TYPE are: default min max
        # Actually looking at cabinet_sim: // @param cab_type linear 0 0 1
        # and valve_preamp: // @param gain linear 1 0 2
        # These are: TYPE default min max
        fixed = f"{prefix}{v1} {v2} {v3} {ptype}"
        if rest:
            fixed += f"  {rest}"
        return fixed, True

    result = PATTERN_MISSING_RANGE.match(line)
    if result:
        prefix = result.group(1)   # // @param name 
        name = result.group(2)
        default = result.group(3)
        ptype = result.group(4)    # linear/exp/bool
        comment = ""
        # Extract comment if present
        m = re.search(r'(//\s*//.*)$', line)
        if m:
            comment = "  " + m.group(1)
        
        lo, hi = KNOWN_RANGES.get(name, ("0", "1"))
        fixed = f"{prefix}{default} {lo} {hi} {ptype}{comment}"
        return fixed, True

    return line, False


def fix_script(path):
    """Fix all @param lines in a script. Returns (num_fixed, total_params)."""
    with open(path, "r") as f:
        lines = f.readlines()
    
    in_header = False
    fixed_count = 0
    total_params = 0
    
    for i, line in enumerate(lines):
        stripped = line.rstrip("\n")
        if "@werkstatt" in stripped or "@apparat" in stripped or "@spielwerk" in stripped:
            in_header = True
            continue
        if not in_header:
            continue
        if stripped.strip() and not stripped.strip().startswith("//"):
            break
        if "@param" not in stripped:
            continue
        
        total_params += 1
        fixed, was_fixed = fix_param_line(stripped)
        if was_fixed:
            lines[i] = fixed + "\n"
            fixed_count += 1
    
    if fixed_count > 0:
        with open(path, "w") as f:
            f.writelines(lines)
    
    return fixed_count, total_params


def main():
    if len(sys.argv) < 2:
        print("Usage: autofix_params.py --all | --check <name> | file1.js ...")
        sys.exit(1)

    if sys.argv[1] == "--all":
        scripts = sorted(glob.glob(os.path.join(SCRIPTS_DIR, "werkstatt_*.js")))
    elif sys.argv[1] == "--check":
        name = sys.argv[2]
        scripts = sorted(glob.glob(os.path.join(SCRIPTS_DIR, f"*{name}*.js")))
    else:
        scripts = sys.argv[1:]

    total_fixed = 0
    total_files = 0

    for path in scripts:
        fixed, total = fix_script(path)
        if fixed > 0:
            total_files += 1
            total_fixed += fixed
            print(f"  ✅ {os.path.basename(path)}: fixed {fixed}/{total} params")

    print(f"\nFixed {total_fixed} params in {total_files} files")


if __name__ == "__main__":
    main()
