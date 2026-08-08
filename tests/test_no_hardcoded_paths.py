"""Regression: package modules must not contain machine-specific absolute paths.

Guards the "No hardcoded paths" PR-template rule for the opendaw_mcp package
(CI previously grepped only server.py, so /home/... in prompt_inference.py
evaded it — see issue #41).
"""
import re
from pathlib import Path

import opendaw_mcp

PKG_DIR = Path(opendaw_mcp.__file__).resolve().parent


def test_no_hardcoded_home_paths_in_package():
    offenders = []
    for py in sorted(PKG_DIR.glob("*.py")):
        for lineno, line in enumerate(
            py.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if re.search(r"/home/", line):
                offenders.append(f"{py.name}:{lineno}")
    assert not offenders, f"hardcoded /home/ paths found: {offenders}"


def test_kb_candidates_are_not_machine_specific():
    from opendaw_mcp.prompt_inference import KB_PACKAGES_DIR_CANDIDATES

    for cand in KB_PACKAGES_DIR_CANDIDATES:
        if cand is None:
            continue
        assert "/home/" not in str(cand), cand
