#!/usr/bin/env python3
"""
Add MCP tool annotations to server.py based on tool name patterns.

Read-only tools (get_, list_, read_, detect_, analyze_, evaluate_):
  annotations=ToolAnnotations(readOnlyHint=True)

Destructive tools (delete_, clear_, reset_):
  annotations=ToolAnnotations(destructiveHint=True)
"""
import re
import sys

READ_ONLY = ['get_', 'list_', 'read_', 'detect_', 'analyze_', 'evaluate_']
DESTRUCTIVE = ['delete_', 'clear_', 'reset_']

def classify(name: str) -> str | None:
    # remove mcp_opendaw_ prefix
    short = name.replace('mcp_opendaw_', '')
    if any(short.startswith(p.rstrip('_')) for p in READ_ONLY):
        return 'read_only'
    if any(short.startswith(p.rstrip('_')) for p in DESTRUCTIVE):
        return 'destructive'
    return None

def main():
    with open('server.py', 'r') as f:
        src = f.read()

    # Find all @mcp.tool() decorators followed by async def mcp_opendaw_*
    pattern = r'(@mcp\.tool\(\))\n(async def (mcp_opendaw_\w+))'

    read_only_count = 0
    destructive_count = 0

    def replace_decorator(match):
        nonlocal read_only_count, destructive_count
        decorator = match.group(1)
        func_def = match.group(2)
        func_name = match.group(3)

        category = classify(func_name)
        if category == 'read_only':
            new_decorator = '@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))'
            read_only_count += 1
        elif category == 'destructive':
            new_decorator = '@mcp.tool(annotations=ToolAnnotations(destructiveHint=True))'
            destructive_count += 1
        else:
            return match.group(0)  # no change

        return f'{new_decorator}\n{func_def}'

    new_src = re.sub(pattern, replace_decorator, src)

    # Check if ToolAnnotations is already imported
    if 'ToolAnnotations' not in new_src and read_only_count + destructive_count > 0:
        # Add import after existing mcp imports
        new_src = new_src.replace(
            'from mcp.server.fastmcp import FastMCP',
            'from mcp.server.fastmcp import FastMCP\nfrom mcp.types import ToolAnnotations'
        )

    with open('server.py', 'w') as f:
        f.write(new_src)

    print(f'Annotated: {read_only_count} read-only, {destructive_count} destructive')
    print(f'Total: {read_only_count + destructive_count} tools annotated')

if __name__ == '__main__':
    main()
