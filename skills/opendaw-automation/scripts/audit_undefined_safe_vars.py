#!/usr/bin/env python3
"""Audit server.py for undefined safe_ variables.

Scans all mcp_opendaw_ functions for safe_ prefixed variables that are
referenced (typically in f-string JS templates) but never assigned.
These are copy-paste bugs where the sanitization line was forgotten.

Usage:
    python3 scripts/audit_undefined_safe_vars.py [server.py]
Exit code: 0 if clean, 1 if issues found.
"""
import ast
import re
import sys
import os

def audit(filepath):
    with open(filepath) as f:
        source = f.read()

    tree = ast.parse(source)
    issues = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        # Only check mcp_opendaw_ functions
        if not node.name.startswith('mcp_opendaw_'):
            continue

        func_source = ast.get_source_segment(source, node)
        if not func_source:
            continue

        # Find all safe_ variable names used in the function
        safe_vars = set(re.findall(r'\b(safe_\w+)\b', func_source))

        for var in safe_vars:
            # Check if it's assigned in this function scope
            assigned = False
            for child in ast.walk(node):
                if isinstance(child, ast.Assign):
                    for target in child.targets:
                        if isinstance(target, ast.Name) and target.id == var:
                            assigned = True
                elif isinstance(child, ast.AugAssign):
                    if isinstance(child.target, ast.Name) and child.target.id == var:
                        assigned = True
            if not assigned:
                issues.append(f'{node.name}: uses {var} but never assigns it')

    return issues


if __name__ == '__main__':
    # Find server.py
    if len(sys.argv) > 1:
        server_path = sys.argv[1]
    else:
        # Default: relative to this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        server_path = os.path.join(os.path.dirname(script_dir), 'server.py')

    if not os.path.exists(server_path):
        print(f'Error: {server_path} not found')
        sys.exit(2)

    issues = audit(server_path)

    if issues:
        print(f'Found {len(issues)} undefined safe_ variable(s):')
        for i in issues:
            print(f'  {i}')
        sys.exit(1)
    else:
        print('All safe_ variables properly assigned ✅')
        sys.exit(0)
