#!/usr/bin/env python3
"""
Generate docs/tools-reference.md from server.py AST.

Extracts: tool name, category (from prefix), docstring, parameters,
annotations (readOnly/destructive), and groups by category.
"""
import ast
import re
import sys
from pathlib import Path


def extract_tools(server_path: str) -> list[dict]:
    """Parse server.py and extract all MCP tool definitions."""
    tree = ast.parse(Path(server_path).read_text())
    src_lines = Path(server_path).read_text().splitlines()

    tools = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.AsyncFunctionDef) and node.name.startswith('mcp_opendaw_')):
            continue

        name = node.name
        doc = ast.get_docstring(node) or ""
        # extract summary (first line of docstring)
        summary = doc.split('\n')[0].strip() if doc else ""

        # extract args (skip self)
        args = []
        for arg in node.args.args:
            if arg.arg == 'self':
                continue
            # try to get annotation
            ann = ""
            if arg.annotation and isinstance(arg.annotation, ast.Name):
                ann = arg.annotation.id
            elif arg.annotation and isinstance(arg.annotation, ast.Constant):
                ann = str(arg.annotation.value)
            args.append({"name": arg.arg, "type": ann})

        # check annotation from decorator
        annotation = ""
        for dec in node.decorator_list:
            if isinstance(dec, ast.Call) and hasattr(dec, 'keywords'):
                for kw in dec.keywords:
                    if kw.arg == 'annotations' and isinstance(kw.value, ast.Call):
                        func = kw.value.func
                        if isinstance(func, ast.Name) and func.id == 'ToolAnnotations':
                            for kw2 in kw.value.keywords:
                                if kw2.arg == 'readOnlyHint' and isinstance(kw2.value, ast.Constant):
                                    if kw2.value.value:
                                        annotation = "readOnly"
                                elif kw2.arg == 'destructiveHint' and isinstance(kw2.value, ast.Constant):
                                    if kw2.value.value:
                                        annotation = "destructive"

        # categorize by prefix
        short = name.replace('mcp_opendaw_', '')
        if any(short.startswith(p) for p in ['get_', 'list_', 'read_', 'detect_', 'analyze_', 'evaluate_']):
            category = "Read-only"
        elif any(short.startswith(p) for p in ['create_', 'add_', 'set_', 'apply_', 'load_', 'place_', 'import_']):
            category = "Create / Modify"
        elif any(short.startswith(p) for p in ['delete_', 'clear_', 'reset_']):
            category = "Destructive"
        elif any(short.startswith(p) for p in ['render_', 'export_']):
            category = "Render / Export"
        else:
            category = "Other"

        tools.append({
            "name": name,
            "summary": summary,
            "args": args,
            "annotation": annotation,
            "category": category,
        })

    return sorted(tools, key=lambda t: (t['category'], t['name']))


def generate_md(tools: list[dict]) -> str:
    """Generate markdown reference."""
    lines = [
        "# Tool Reference",
        "",
        f"Auto-generated from `server.py`. **{len(tools)} MCP tools.**",
        "",
        "| Category | Count |",
        "|---|---|",
    ]

    cats = {}
    for t in tools:
        cats.setdefault(t['category'], []).append(t)
    for cat in sorted(cats.keys()):
        lines.append(f"| {cat} | {len(cats[cat])} |")
    lines.append("")

    for cat in sorted(cats.keys()):
        lines.append(f"## {cat}")
        lines.append("")
        lines.append("| Tool | Annotation | Parameters | Description |")
        lines.append("|---|---|---|---|")
        for t in cats[cat]:
            ann = f"`{t['annotation']}`" if t['annotation'] else ""
            args = ", ".join(f"`{a['name']}`" for a in t['args']) if t['args'] else "—"
            desc = t['summary'].replace('|', '\\|')[:120]
            lines.append(f"| `{t['name']}` | {ann} | {args} | {desc} |")
        lines.append("")

    return '\n'.join(lines)


def main():
    tools = extract_tools('server.py')
    md = generate_md(tools)

    out = Path('docs/tools/reference.md')
    out.parent.mkdir(parents=True, exist_ok=True)

    # check if content changed
    if out.exists() and out.read_text() == md:
        print("No changes — tool reference up to date.")
        return

    out.write_text(md)
    print(f"Generated {out}: {len(tools)} tools in {len(set(t['category'] for t in tools))} categories")


if __name__ == '__main__':
    main()
