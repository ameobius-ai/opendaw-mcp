#!/usr/bin/env python3
"""
Extract all MCP tool functions from a server.cpython-313.pyc file.
Produces a JSON file with: function name, args, docstring, JS f-string (reconstructed),
and other string constants. Used for disaster recovery when server.py is lost.

Usage:
    python3 scripts/extract_pyc.py [path/to/server.cpython-313.pyc] [output.json]

Default: reads __pycache__/server.cpython-313.pyc, writes /tmp/pyc_extraction_complete.json
"""
import marshal, struct, types, dis, json, sys, re

FORMAT_OPS = {'FORMAT_SIMPLE', 'FORMAT_WITH_KIND', 'FORMAT_VALUE'}

def get_code(co, name):
    for c in co.co_consts:
        if isinstance(c, types.CodeType) and c.co_name == name:
            return c
    return None

def reconstruct_fstring(instructions, bs_idx):
    bs_inst = instructions[bs_idx]
    num_parts = bs_inst.argval
    parts = []
    j = bs_idx - 1
    count = 0
    while j >= 0 and count < num_parts:
        inst = instructions[j]
        if inst.opname == 'LOAD_CONST' and isinstance(inst.argval, str):
            parts.insert(0, inst.argval)
            count += 1; j -= 1
        elif inst.opname in FORMAT_OPS:
            if j > 0 and instructions[j-1].opname in ('LOAD_FAST','LOAD_GLOBAL','LOAD_DEREF','LOAD_NAME'):
                var_name = instructions[j-1].argval
                if inst.opname == 'FORMAT_WITH_KIND' and j > 2:
                    spec_inst = instructions[j-2]
                    if spec_inst.opname == 'LOAD_CONST' and isinstance(spec_inst.argval, str):
                        parts.insert(0, '{' + var_name + ':' + spec_inst.argval + '}')
                        j -= 3; count += 1; continue
                parts.insert(0, '{' + var_name + '}')
                j -= 2; count += 1
            else:
                j -= 1
        else:
            j -= 1
    return ''.join(parts)

def get_all_fstrings(fcode):
    instructions = list(dis.get_instructions(fcode))
    results = []
    for i, inst in enumerate(instructions):
        if inst.opname == 'BUILD_STRING' and inst.argval >= 1:
            results.append(reconstruct_fstring(instructions, i))
    for c in fcode.co_consts:
        if isinstance(c, str) and len(c) > 100 and ('window.DAW' in c or '() =>' in c):
            if c not in results:
                results.append(c)
    return results

def escape_js_fstring(js, arg_names):
    """Double all { } that are NOT {arg_name} interpolations."""
    arg_set = set(arg_names)
    result = []
    i = 0
    while i < len(js):
        if js[i] == '{':
            depth = 1; k = i + 1
            while k < len(js) and depth > 0:
                if js[k] == '{': depth += 1
                elif js[k] == '}': depth -= 1
                k += 1
            if depth == 0:
                block = js[i:k]
                arg_pattern = '|'.join(re.escape(a) for a in arg_set)
                parts = re.split(r'\{(' + arg_pattern + r')\}', block)
                for p in parts:
                    if p in arg_set:
                        result.append('{' + p + '}')
                    else:
                        result.append(p.replace('{','{{').replace('}','}}'))
                i = k; continue
            result.append('{{'); i += 1
        elif js[i] == '}':
            result.append('}}'); i += 1
        else:
            result.append(js[i]); i += 1
    return ''.join(result)

def main():
    pyc_path = sys.argv[1] if len(sys.argv) > 1 else '__pycache__/server.cpython-313.pyc'
    out_path = sys.argv[2] if len(sys.argv) > 2 else '/tmp/pyc_extraction_complete.json'

    with open(pyc_path, 'rb') as f:
        f.read(16)
        code = marshal.load(f)

    func_names = [n for n in code.co_names if n.startswith('mcp_opendaw_')]
    all_funcs = {}

    for fname in func_names:
        fcode = get_code(code, fname)
        if not fcode: continue
        fstrings = get_all_fstrings(fcode)
        strings = [s for s in fcode.co_consts if isinstance(s, str)]
        docstring = strings[0] if strings else None
        js_code = max(fstrings, key=len) if fstrings else ''
        escaped_js = escape_js_fstring(js_code, list(fcode.co_varnames[:fcode.co_argcount])) if js_code else ''
        all_funcs[fname] = {
            'args': list(fcode.co_varnames[:fcode.co_argcount]),
            'doc': docstring,
            'js': js_code,
            'escaped_js': escaped_js,
            'js_len': len(js_code),
            'other_strings': [s for s in strings if s != docstring and s != js_code],
        }

    # Helpers and bridge class
    helpers = {}
    for hname in ['_export_offline', '_export_realtime', '_find_script_device_js', '_ok', '_err', '_wrap_eval', 'cleanup']:
        hc = get_code(code, hname)
        if hc:
            helpers[hname] = {
                'args': list(hc.co_varnames[:hc.co_argcount]),
                'strings': [s for s in hc.co_consts if isinstance(s, str)],
                'fstrings': get_all_fstrings(hc),
            }

    bridge_code = get_code(code, 'HeadlessDawBridge')
    bridge_methods = {}
    if bridge_code:
        for c in bridge_code.co_consts:
            if isinstance(c, types.CodeType):
                bridge_methods[c.co_name] = {
                    'args': list(c.co_varnames[:c.co_argcount]),
                    'strings': [s for s in c.co_consts if isinstance(s, str)],
                    'fstrings': get_all_fstrings(c),
                }

    data = {
        'module_strings': [c for c in code.co_consts if isinstance(c, str)],
        'module_names': list(code.co_names),
        'functions': all_funcs,
        'helpers': helpers,
        'bridge_methods': bridge_methods,
    }

    with open(out_path, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    has_js = sum(1 for v in all_funcs.values() if v['js_len'] > 50)
    print(f'Functions: {len(all_funcs)} ({has_js} with JS)')
    print(f'Helpers: {len(helpers)}, Bridge methods: {len(bridge_methods)}')
    print(f'Total JS chars: {sum(v["js_len"] for v in all_funcs.values())}')
    print(f'Saved to {out_path}')

if __name__ == '__main__':
    main()
