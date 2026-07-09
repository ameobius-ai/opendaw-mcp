#!/usr/bin/env python3
"""Pre-flight validator for Werkstatt DSP scripts.

Checks @param declarations in JS script headers before loading them
into openDAW. Catches malformed params that cause silent render failures.

Usage:
  venv/bin/python validate_scripts.py [script.js ...]
  venv/bin/python validate_scripts.py --all          # check all scripts
  venv/bin/python validate_scripts.py --check ssl_bus_comp  # by name

Exit codes:
  0 = all valid
  1 = one or more invalid
"""
import os
import re
import sys
import glob

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "scripts")

# Expected @param format:
# // @param <name> <default> <min> <max> [type] [unit]
# min and max MUST be numeric (int or float, possibly negative)
# Malformed examples (will fail):
#   // @param threshold 0.5 linear          — "linear" is not a number
#   // @param threshold 0.5 0 1             — valid (type is optional)
# Valid examples:
#   // @param freq 0.4 0 1 linear Hz
#   // @param gain 0 -18 18 linear dB
#   // @param mix 1 0 1 linear

NUM = r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?'

PARAM_PATTERN = re.compile(
    r'^//\s*@param\s+(\w+)\s+'   # name
    rf'({NUM})\s+'                # default (numeric)
    rf'({NUM})\s+'                # min (numeric, required)
    rf'({NUM})'                   # max (numeric, required)
    r'(?:\s+(\w+))?'              # type (optional, word)
    r'(?:\s+(.+))?'               # unit (optional, rest of line)
    r'$'
)

# Also catch truncated params (3 fields, no min/max)
PARAM_TRUNCATED = re.compile(
    r'^//\s*@param\s+(\w+)\s+(\S+)\s+(\S+)\s*$'
)


def validate_script(path):
    """Check a single Werkstatt script. Returns (ok, errors)."""
    errors = []
    name = os.path.basename(path)

    if not os.path.exists(path):
        return False, [f"{name}: file not found"]

    with open(path, "r") as f:
        lines = f.readlines()

    in_header = False
    for i, line in enumerate(lines, 1):
        line = line.rstrip("\n")
        if "@werkstatt" in line or "@apparat" in line or "@spielwerk" in line:
            in_header = True
            continue
        if not in_header:
            continue
        # Stop at class declaration or first non-comment
        if line.strip() and not line.strip().startswith("//"):
            break

        if "@param" not in line:
            continue

        # Try full match
        match = PARAM_PATTERN.match(line)
        if match:
            continue  # valid

        # Failed — extract param name for better error
        name_match = re.match(r'^//\s*@param\s+(\w+)', line)
        param_name = name_match.group(1) if name_match else "unknown"
        errors.append(
            f"  line {i}: @{param_name} — missing or non-numeric min/max\n"
            f"    got: {line.strip()}\n"
            f"    expected: // @param {param_name} <default> <min> <max> [type] [unit]\n"
            f"    example: // @param {param_name} 0.5 0 1 linear"
        )

    return len(errors) == 0, errors


def main():
    if len(sys.argv) < 2:
        print("Usage: validate_scripts.py [script.js ...] | --all | --check <name>")
        sys.exit(1)

    if sys.argv[1] == "--all":
        scripts = sorted(glob.glob(os.path.join(SCRIPTS_DIR, "werkstatt_*.js")))
        scripts += sorted(glob.glob(os.path.join(SCRIPTS_DIR, "apparat_*.js")))
        scripts += sorted(glob.glob(os.path.join(SCRIPTS_DIR, "spielwerk_*.js")))
    elif sys.argv[1] == "--check":
        name = sys.argv[2]
        scripts = sorted(glob.glob(os.path.join(SCRIPTS_DIR, f"*{name}*.js")))
        if not scripts:
            print(f"No scripts matching '{name}'")
            sys.exit(1)
    else:
        scripts = sys.argv[1:]

    total = 0
    valid = 0
    invalid = 0

    for path in scripts:
        total += 1
        ok, errors = validate_script(path)
        if ok:
            valid += 1
        else:
            invalid += 1
            print(f"\n❌ {os.path.basename(path)}:")
            for e in errors:
                print(e)

    print(f"\n{'='*50}")
    print(f"Checked: {total}  Valid: {valid}  Invalid: {invalid}")

    if invalid > 0:
        print(f"\n⚠️  {invalid} script(s) have malformed @param declarations.")
        print("These will cause 'Malformed @param' errors when loaded into openDAW.")
        print("Fix: add min/max values to each @param line.")
        sys.exit(1)
    else:
        print("All scripts valid ✅")
        sys.exit(0)


if __name__ == "__main__":
    main()
