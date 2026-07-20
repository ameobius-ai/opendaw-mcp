# Smart export — platform bounce (P3)

Depends on lineage P1. Wraps existing post-master / auto_master / measure_lufs.

## Goal

One call: `export_for_platform(platform)` → platform-correct bounce + lineage edge.

## Platforms

| platform | LUFS target | TP ceiling | notes |
|----------|-------------|------------|-------|
| spotify  | -14         | -1.0 dBTP  | default |
| apple    | -16         | -1.0 dBTP  | quieter |
| youtube  | -14         | -1.0 dBTP  | |
| tidal    | -14         | -1.0 dBTP  | |
| soundcloud | -14       | -1.0 dBTP  | |
| club     | -9          | -0.3 dBTP  | loud |

## Tool

`export_for_platform(platform, filename, parent_id="")`

Pipeline:
1. if openDAW project live → render_full (optional)
2. apply post-master / auto_master style for platform
3. measure_lufs verify
4. record_lineage(kind=export, op=export, params={platform, target_lufs, ceiling}, metrics=...)

## Acceptance

- dry-run mode without DAW bridge (file-only post-master path) ✓
- fails if TP above ceiling ✓
- records lineage when parent_id given (always records export node; parent attaches edge) ✓

## Implementation (v1.390.0)

- Module: `opendaw_mcp/smart_export.py`
- MCP: `mcp_opendaw_export_for_platform(platform, filename, parent_id="", dry_run=False, output_name="")`
- Tests: `tests/test_smart_export.py` (13)

## Kanban

`t_20bc5cb3`
