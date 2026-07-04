#!/usr/bin/env python3
"""Audit server.py for str-typed params used in JS arithmetic (f-string interpolation).

After ANY type annotation change, run this to verify zero str params remain
in JS arithmetic contexts. Exit code 0 = clean, 1 = found issues.

Usage:
    python3 scripts/audit_str_params.py [path/to/server.py]
"""
import ast
import re
import sys

def audit(filepath: str) -> list[tuple[str, str]]:
    """Return list of (param_name, pattern) for str params found in JS arithmetic."""
    with open(filepath) as f:
        source = f.read()

    tree = ast.parse(source)

    # Collect all str-typed params in mcp_opendaw_* functions
    str_params = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name.startswith("mcp_opendaw_"):
            for arg in node.args.args:
                if arg.annotation and isinstance(arg.annotation, ast.Name) and arg.annotation.id == "str":
                    str_params.add(arg.arg)

    # Check if any str param appears in JS arithmetic context inside f-strings
    suspicious = []
    for p in str_params:
        patterns = [
            rf"\{{{p}\}} \* ",
            rf"\{{{p}\}} / ",
            rf"\{{{p}\}} \+ ",
            rf"\{{{p}\}} - ",
            rf"Math\.\w+\(\{{{p}\}}",
        ]
        for pat in patterns:
            if re.search(pat, source):
                suspicious.append((p, pat.replace("\\", "")))
                break  # one hit per param is enough

    return suspicious


def main():
    filepath = sys.argv[1] if len(sys.argv) > 1 else "server.py"
    issues = audit(filepath)

    if not issues:
        print(f"✅ Clean — 0 str params in JS arithmetic ({filepath})")
        sys.exit(0)
    else:
        print(f"❌ Found {len(issues)} str params in JS arithmetic:")
        for name, pat in issues:
            print(f"  {name} (pattern: {pat})")
        sys.exit(1)


if __name__ == "__main__":
    main()
