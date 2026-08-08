#!/usr/bin/env python3
"""
Repo consistency checker.

Verifies that documented metrics in key doc surfaces match actual
filesystem counts. Reads the ground-truth marker from README.md and
checks that each tracked surface is in sync. Also verifies that the
package version stays in sync across pyproject.toml and server.json
(registry manifest + OCI tag).

Usage:
    python scripts/check_repo_consistency.py [--repo-root PATH]

Exit code 0 = all surfaces in sync.
Exit code 1 = one or more surfaces out of sync (prints diff).
"""
import ast
import os
import re
import sys


def repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------------------
# Actual counts from the filesystem
# ---------------------------------------------------------------------------

def count_mcp_tools(root: str) -> int:
    server_py = os.path.join(root, "server.py")
    tree = ast.parse(open(server_py).read())
    return sum(
        1 for n in ast.walk(tree)
        if isinstance(n, ast.AsyncFunctionDef) and n.name.startswith("mcp_opendaw_")
    )


def count_skills(root: str) -> int:
    skills_dir = os.path.join(root, "skills")
    return sum(
        1 for d in os.listdir(skills_dir)
        if os.path.isdir(os.path.join(skills_dir, d))
        and os.path.isfile(os.path.join(skills_dir, d, "SKILL.md"))
    )


def count_dsp_scripts(root: str) -> int:
    scripts_dir = os.path.join(root, "scripts")
    return sum(
        1 for f in os.listdir(scripts_dir)
        if f.endswith(".js")
        and (f.startswith("werkstatt_") or f.startswith("apparat_") or f.startswith("spielwerk_"))
    )


def count_examples(root: str) -> int:
    examples_dir = os.path.join(root, "examples")
    return sum(1 for f in os.listdir(examples_dir) if f.endswith(".py"))


# ---------------------------------------------------------------------------
# Read / check documented values
# ---------------------------------------------------------------------------

METRICS_RE = re.compile(
    r"<!-- REPO-METRICS: tools=(\d+) skills=(\d+) dsp=(\d+) examples=(\d+) -->"
)


def read_metrics_marker(readme_path: str) -> dict[str, int]:
    content = open(readme_path).read()
    m = METRICS_RE.search(content)
    if not m:
        raise ValueError(
            "REPO-METRICS marker not found in README.md — "
            "add: <!-- REPO-METRICS: tools=N skills=N dsp=N examples=N -->"
        )
    return {
        "tools": int(m.group(1)),
        "skills": int(m.group(2)),
        "dsp": int(m.group(3)),
        "examples": int(m.group(4)),
    }


def surface_check(label: str, path: str, pattern: str, expected: int) -> str | None:
    """Return an error string if the surface is out of sync, else None."""
    try:
        content = open(path).read()
    except FileNotFoundError:
        return f"  {label}: file not found: {path}"
    m = re.search(pattern, content, re.MULTILINE)
    if not m:
        return f"  {label}: marker pattern not found in {os.path.basename(path)}"
    found = int(m.group(1))
    if found != expected:
        return f"  {label}: documented={found}, expected={expected}"
    return None


# ---------------------------------------------------------------------------
# Version sync (pyproject.toml vs server.json registry manifest)
# ---------------------------------------------------------------------------

def read_pyproject_version(root: str) -> str | None:
    path = os.path.join(root, "pyproject.toml")
    try:
        content = open(path).read()
    except FileNotFoundError:
        return None
    m = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    return m.group(1) if m else None


def read_server_json_versions(root: str) -> tuple[str | None, str | None]:
    """Return (server.json "version", OCI identifier tag). (None, None) if unreadable."""
    import json as _json

    path = os.path.join(root, "server.json")
    try:
        data = _json.loads(open(path).read())
    except (FileNotFoundError, ValueError):
        return None, None
    version = data.get("version")
    oci_tag = None
    for pkg in data.get("packages", []):
        ident = str(pkg.get("identifier", ""))
        if ":" in ident:
            oci_tag = ident.rsplit(":", 1)[1]
    return version, oci_tag


def version_sync_errors(root: str) -> list[str]:
    """Errors when the release version drifts between pyproject.toml and server.json."""
    errors: list[str] = []
    py_ver = read_pyproject_version(root)
    sj_ver, sj_oci = read_server_json_versions(root)
    if py_ver and sj_ver and py_ver != sj_ver:
        errors.append(
            f"  version drift: pyproject.toml={py_ver}, server.json version={sj_ver}"
        )
    if py_ver and sj_oci and py_ver != sj_oci:
        errors.append(
            f"  version drift: pyproject.toml={py_ver}, server.json OCI tag={sj_oci}"
        )
    return errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Check repo documentation consistency")
    parser.add_argument("--repo-root", default=repo_root(), help="Path to repo root")
    args = parser.parse_args()
    root = args.repo_root

    errors: list[str] = []

    # --- Actual counts ---
    actual = {
        "tools": count_mcp_tools(root),
        "skills": count_skills(root),
        "dsp": count_dsp_scripts(root),
        "examples": count_examples(root),
    }

    print(
        f"Actual: tools={actual['tools']} skills={actual['skills']} "
        f"dsp={actual['dsp']} examples={actual['examples']}"
    )

    # --- Ground-truth marker ---
    readme = os.path.join(root, "README.md")
    try:
        doc = read_metrics_marker(readme)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    # Marker vs actual
    for key in ("tools", "skills", "dsp", "examples"):
        if doc[key] != actual[key]:
            errors.append(
                f"  README REPO-METRICS marker: {key}={doc[key]}, actual={actual[key]}"
            )

    t = doc["tools"]
    s = doc["skills"]
    d = doc["dsp"]
    e = doc["examples"]

    # --- Surface checks (tools count) ---
    surfaces_tools = [
        ("README badge:MCP-Tools",    readme,                              r"MCP%20Tools-(\d+)-brightgreen"),
        ("TOOL_CATALOG header",       os.path.join(root, "TOOL_CATALOG.md"), r"^(\d+) MCP tools"),
        ("docs/index.md headline",    os.path.join(root, "docs", "index.md"), r"\*\*(\d+)\*\* MCP tools"),
        ("docs/index.md quick-num",   os.path.join(root, "docs", "index.md"), r"- \*\*(\d+)\*\* MCP tools"),
        ("docs/tools/index.md",       os.path.join(root, "docs", "tools", "index.md"), r"^(\d+) MCP tools"),
        ("ARCHITECTURE.md",           os.path.join(root, "ARCHITECTURE.md"), r"\*\*(\d+) tools\*\*"),
    ]
    for label, path, pat in surfaces_tools:
        err = surface_check(label, path, pat, t)
        if err:
            errors.append(err)

    # --- Surface checks (skills count) ---
    surfaces_skills = [
        ("README badge:Agent-Skills", readme, r"Agent%20Skills-(\d+)-blue"),
    ]
    for label, path, pat in surfaces_skills:
        err = surface_check(label, path, pat, s)
        if err:
            errors.append(err)

    # --- Surface checks (dsp count) ---
    surfaces_dsp = [
        ("README badge:DSP-Scripts", readme, r"DSP%20Scripts-(\d+)-orange"),
    ]
    for label, path, pat in surfaces_dsp:
        err = surface_check(label, path, pat, d)
        if err:
            errors.append(err)

    # --- Surface checks (examples count) ---
    surfaces_examples = [
        ("README badge:Examples", readme, r"Examples-(\d+)-blue"),
    ]
    for label, path, pat in surfaces_examples:
        err = surface_check(label, path, pat, e)
        if err:
            errors.append(err)

    # --- Version sync (pyproject.toml vs server.json) ---
    errors.extend(version_sync_errors(root))

    # --- Result ---
    if errors:
        print("\nCONSISTENCY CHECK FAILED — surfaces out of sync:")
        for err in errors:
            print(err)
        print(
            "\nTo fix: update the REPO-METRICS marker in README.md, "
            "then sync all flagged surfaces."
        )
        sys.exit(1)

    print("Consistency check passed — all surfaces in sync.")


if __name__ == "__main__":
    main()
