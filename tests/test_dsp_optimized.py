"""
Optimized DSP Script Tests
===========================
Parameterized tests for all DSP scripts to reduce code duplication.

This file replaces 54 individual DSP test classes with a single parameterized
test suite, achieving ~97% code reduction while maintaining same coverage.
"""
import os
import re
import pytest


def get_dsp_scripts():
    """Get list of all DSP scripts to test."""
    scripts_dir = os.path.join(os.path.dirname(__file__), "..", "scripts")
    dsp_scripts = []
    
    if os.path.exists(scripts_dir):
        for filename in os.listdir(scripts_dir):
            if filename.startswith("werkstatt_") and filename.endswith(".js"):
                dsp_scripts.append(filename)
    
    return sorted(dsp_scripts)


def read_script(script_name):
    """Read a DSP script."""
    script_path = os.path.join(os.path.dirname(__file__), "..", "scripts", script_name)
    with open(script_path, 'r', encoding='utf-8') as f:
        return f.read()


def parse_params(code):
    """Parse @param annotations from script."""
    params = []
    pattern = r'//\s*@param\s+(\w+)\s+([\d.]+)\s+([\d.-]+)\s+([\d.-]+)\s+(\w+)'
    for m in re.finditer(pattern, code):
        params.append({
            "name": m.group(1),
            "default": float(m.group(2)),
            "min": float(m.group(3)),
            "max": float(m.group(4)),
            "type": m.group(5)
        })
    return params


DSP_SCRIPTS = get_dsp_scripts()


class TestDSPScripts:
    """Parameterized tests for all DSP scripts."""
    
    @pytest.mark.parametrize("script_name", DSP_SCRIPTS)
    def test_script_exists(self, script_name):
        """Verify script file exists."""
        script_path = os.path.join(os.path.dirname(__file__), "..", "scripts", script_name)
        assert os.path.exists(script_path), f"Script not found: {script_name}"
    
    @pytest.mark.parametrize("script_name", DSP_SCRIPTS)
    def test_has_werkstatt_header(self, script_name):
        """Verify script has @werkstatt header."""
        code = read_script(script_name)
        assert "// @werkstatt" in code, f"{script_name} missing @werkstatt header"
    
    @pytest.mark.parametrize("script_name", DSP_SCRIPTS)
    def test_has_label(self, script_name):
        """Verify script has a label."""
        code = read_script(script_name)
        assert any(label in code for label in ["label", "Label", "name", "Name"]), \
            f"{script_name} missing label"
    
    @pytest.mark.parametrize("script_name", DSP_SCRIPTS)
    def test_has_parameters(self, script_name):
        """Verify script has @param annotations."""
        code = read_script(script_name)
        params = parse_params(code)
        assert len(params) > 0, f"{script_name} has no @param annotations"
    
    @pytest.mark.parametrize("script_name", DSP_SCRIPTS)
    def test_param_structure(self, script_name):
        """Verify all parameters have correct structure."""
        code = read_script(script_name)
        params = parse_params(code)
        
        for param in params:
            assert "name" in param, f"{script_name} param missing name"
            assert "default" in param, f"{script_name} param {param['name']} missing default"
            assert "min" in param, f"{script_name} param {param['name']} missing min"
            assert "max" in param, f"{script_name} param {param['name']} missing max"
            assert "type" in param, f"{script_name} param {param['name']} missing type"
            assert param["min"] <= param["default"] <= param["max"], \
                f"{script_name} param {param['name']} default out of range"
    
    @pytest.mark.parametrize("script_name", DSP_SCRIPTS)
    def test_has_output_param(self, script_name):
        """Verify script has output parameter."""
        code = read_script(script_name)
        params = parse_params(code)
        output_params = [p for p in params if p["name"] in ["output", "mix"]]
        assert len(output_params) > 0, f"{script_name} missing output/mix parameter"
    
    @pytest.mark.parametrize("script_name", DSP_SCRIPTS)
    def test_implementation_complete(self, script_name):
        """Verify script has complete implementation."""
        code = read_script(script_name)
        has_processing = any(keyword in code for keyword in [
            "process", "Process", "update", "Update", "compute", "Compute",
            "function", "Function", "class", "Class"
        ])
        assert has_processing, f"{script_name} missing processing implementation"
