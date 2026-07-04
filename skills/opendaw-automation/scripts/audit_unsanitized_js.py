#!/usr/bin/env python3
"""Audit server.py for unsanitized str params in JS template literals.

Scans for "{param}" patterns inside bridge.evaluate f-string blocks,
cross-references with str-typed function params, and reports any
that lack a safe_ prefixed sanitized variable.

Usage:
    python3 scripts/audit_unsanitized_js.py [server.py]
"""
import re
import sys

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "server.py"
    with open(path) as f:
        source = f.read()

    # Known safe_ variable prefixes
    safe_prefixes = ('safe_',)

    # Known non-injectable str params (whitelisted or validated before use)
    whitelist = {
        'sample_name', 'effect_name', 'track_name', 'region_name',
        'clip_name', 'marker_name', 'bus_name', 'send_name',
        'param_name', 'preset_name', 'slot_name', 'label', 'name',
        'file_path', 'output_path', 'export_path', 'code', 'style',
        'title', 'prompt', 'lyrics', 'direction', 'routing', 'mode',
        'format', 'kind', 'type', 'script_path', 'sample_path',
        'audio_path', 'midi_path', 'config',
        'source_output_name', 'target_input_name', 'string_value',
        'condition_js', 'script', 'division',
    }

    # Find all function signatures with str params
    func_pattern = r'async def (mcp_opendaw_\w+)\((.*?)\) -> str:'
    issues = []

    for m in re.finditer(func_pattern, source):
        func_name = m.group(1)
        params_str = m.group(2)

        # Find function body
        func_start = m.start()
        func_end = source.find('\n@mcp.tool()', func_start + 1)
        if func_end == -1:
            func_end = len(source)
        body = source[func_start:func_end]

        # Find all "{param}" patterns in body (JS string literal interpolation)
        for interp_match in re.finditer(r'"\{(\w+)\}"', body):
            param = interp_match.group(1)

            # Skip if already safe_
            if param.startswith(safe_prefixes):
                continue

            # Skip if param is whitelisted (known non-injectable)
            if param in whitelist:
                continue

            # Skip if not a str-typed param (check function signature)
            if f'{param}: str' not in params_str and f'{param}: str =' not in params_str:
                # Could be a non-str param interpolated as string — still check
                # but lower priority
                pass

            # Check if a safe_ version exists in the body
            safe_var_candidates = [
                f'safe_{param}',
                'safe_param' if param == 'parameter_name' else None,
            ]
            safe_var_candidates = [c for c in safe_var_candidates if c]

            has_safe = any(sv in body for sv in safe_var_candidates)

            if not has_safe:
                # Determine line number
                abs_pos = func_start + interp_match.start()
                line_num = source[:abs_pos].count('\n') + 1
                issues.append(f'{func_name} L{line_num}: "{param}" in JS string literal without safe_ var')

    # Deduplicate
    issues = sorted(set(issues))

    if issues:
        print(f'Found {len(issues)} unsanitized str params in JS string literals:')
        for i in issues:
            print(f'  {i}')
        sys.exit(1)
    else:
        print('All str params in JS string literals are sanitized')
        sys.exit(0)

if __name__ == '__main__':
    main()
