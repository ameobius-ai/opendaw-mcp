#!/usr/bin/env python3
"""Tests for validate_scripts.py and autofix_params.py.

Run: venv/bin/python -m pytest tests/test_validation.py -v
"""
import os
import sys
import tempfile
import pytest

# Add parent dir to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from validate_scripts import validate_script
from autofix_params import fix_param_line, fix_script, KNOWN_RANGES


# ─── Fixtures ──────────────────────────────────────────────

VALID_SCRIPT = """\
// @werkstatt test_effect 1 1
// @label Test Effect
// @param threshold 0.5 0 1 linear
// @param freq 0.4 0 1 exp Hz
// @param gain 0 -18 18 linear dB

class Processor {
  constructor(sampleRate, blockSize) {
    this.sr = sampleRate || 48000
  }
  processAudio(inputs, outputs, parameters) {}
}
"""

MALFORMED_SCRIPT = """\
// @werkstatt bad_effect 1 1
// @label Bad Effect
// @param threshold 0.5 linear
// @param ratio 0.3 linear
// @param attack 0.3 linear

class Processor {
  processAudio(inputs, outputs, parameters) {}
}
"""

TYPE_FIRST_SCRIPT = """\
// @werkstatt type_first 1 1
// @param attack linear 0.001 0.1 0.005
// @param release linear 0.01 1.0 0.1

class Processor {
  processAudio(inputs, outputs, parameters) {}
}
"""


# ─── validate_scripts tests ────────────────────────────────

class TestValidateScript:
    def _write(self, content):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False)
        f.write(content)
        f.close()
        return f.name

    def test_valid_script_passes(self):
        path = self._write(VALID_SCRIPT)
        ok, errors = validate_script(path)
        assert ok
        assert errors == []
        os.unlink(path)

    def test_malformed_script_fails(self):
        path = self._write(MALFORMED_SCRIPT)
        ok, errors = validate_script(path)
        assert not ok
        assert len(errors) == 3  # threshold, ratio, attack
        os.unlink(path)

    def test_missing_file(self):
        ok, errors = validate_script("/nonexistent/path.js")
        assert not ok
        assert "not found" in errors[0]

    def test_no_params_is_valid(self):
        script = """\
// @werkstatt no_params 1 1
// @label No Params

class Processor {
  processAudio(inputs, outputs, parameters) {}
}
"""
        path = self._write(script)
        ok, errors = validate_script(path)
        assert ok
        os.unlink(path)

    def test_negative_ranges_valid(self):
        script = """\
// @werkstatt neg_test 1 1
// @param bias 0 -0.5 0.5 linear
// @param output 0 -24 6 linear dB

class Processor {
  processAudio(inputs, outputs, parameters) {}
}
"""
        path = self._write(script)
        ok, errors = validate_script(path)
        assert ok
        os.unlink(path)


# ─── autofix_params tests ──────────────────────────────────

class TestFixParamLine:
    def test_missing_range_gets_defaults(self):
        line = "// @param threshold 0.5 linear"
        fixed, was_fixed = fix_param_line(line)
        assert was_fixed
        assert "0 1" in fixed  # KNOWN_RANGES["threshold"] = ("0", "1")
        assert "linear" in fixed

    def test_missing_range_known_param(self):
        line = "// @param output 0.0 linear"
        fixed, was_fixed = fix_param_line(line)
        assert was_fixed
        assert "-24 6" in fixed  # KNOWN_RANGES["output"]

    def test_type_first_gets_reordered(self):
        line = "// @param attack linear 0.001 0.1 0.005"
        fixed, was_fixed = fix_param_line(line)
        assert was_fixed
        # Should become: // @param attack 0.001 0.1 0.005 linear
        assert "linear" not in fixed.split("// @param")[1].split()[1]

    def test_valid_line_not_changed(self):
        line = "// @param threshold 0.5 0 1 linear"
        fixed, was_fixed = fix_param_line(line)
        assert not was_fixed
        assert fixed == line


class TestFixScript:
    def _write(self, content):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False)
        f.write(content)
        f.close()
        return f.name

    def test_fixes_malformed_script(self):
        path = self._write(MALFORMED_SCRIPT)
        fixed, total = fix_script(path)
        assert fixed == 3
        assert total == 3
        os.unlink(path)

    def test_no_fixes_on_valid_script(self):
        path = self._write(VALID_SCRIPT)
        fixed, total = fix_script(path)
        assert fixed == 0
        assert total == 3
        os.unlink(path)

    def test_fixes_type_first_script(self):
        path = self._write(TYPE_FIRST_SCRIPT)
        fixed, total = fix_script(path)
        assert fixed == 2
        assert total == 2
        os.unlink(path)


# ─── Integration: fix → validate ───────────────────────────

class TestIntegration:
    def _write(self, content):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False)
        f.write(content)
        f.close()
        return f.name

    def test_fix_makes_script_valid(self):
        path = self._write(MALFORMED_SCRIPT)
        # Before fix: invalid
        ok_before, _ = validate_script(path)
        assert not ok_before

        # Fix it
        fix_script(path)

        # After fix: valid
        ok_after, errors = validate_script(path)
        assert ok_after, f"Still invalid after fix: {errors}"
        os.unlink(path)
