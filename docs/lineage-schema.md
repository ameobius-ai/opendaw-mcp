# Lineage / Provenance Schema (v1)

Agent-native memory for `suno → stems → eq → bounce → export`.
Inspired by theDAW LEARN genealogy — file-backed, no UI, no torch.

## File

Default path:

```
$OPENDAW_EXPORT_DIR/lineage/lineage.json
```

Override with `OPENDAW_LINEAGE_PATH`.

## Schema

```json
{
  "version": 1,
  "updated_at": "2026-07-17T22:00:00Z",
  "nodes": {
    "n_abc123": {
      "id": "n_abc123",
      "kind": "audio|render|stem|mix_pass|export|prompt|external|analysis",
      "path": "exports/track_v3.wav",
      "label": "optional human label",
      "created_at": "2026-07-17T22:00:00Z",
      "metrics": {
        "lufs_integrated": -14.02,
        "true_peak_db": -1.05,
        "sub_pct": 12.3,
        "presence_pct": 4.9,
        "air_pct": 2.7
      },
      "provenance": {
        "source": "suno|opendaw|stem-split|post_master|external",
        "model": "chirp-v5-5",
        "prompt": "...",
        "style": "coldwave darksynth",
        "seed": 42,
        "chain_hash": "a1b2c3d4e5f67890",
        "params": {}
      }
    }
  },
  "edges": [
    {
      "id": "e_def456",
      "parent_id": "n_parent",
      "child_id": "n_child",
      "op": "stem_split|eq|master|bounce|export|cover|remix|import|other",
      "params": { "eq": "LS-2.5@100 + HS+4@3k" },
      "created_at": "2026-07-17T22:01:00Z"
    }
  ]
}
```

## MCP tools

| Tool | Purpose |
|------|---------|
| `record_lineage` | Create node (+ optional parent edge) |
| `trace_lineage` | Ancestors from node → roots |
| `list_descendants` | Children from node → leaves |
| `list_lineage_nodes` | Recent nodes filter by kind |
| `record_mix_pass` | Wrapper: `kind=mix_pass` for iterative mix |
| `list_mix_history` | Last-N mix passes + metric diffs |
| `diff_mix_passes` | Numeric delta between two nodes |

## Ops

`import`, `generate`, `stem_split`, `eq`, `compress`, `saturate`, `reverb`,
`delay`, `master`, `bounce`, `export`, `cover`, `remix`, `inpaint`, `extend`,
`analyze`, `prompt_infer`, `other`

## Agent pattern

```
record(suno wav) → record(stems, parent=suno, op=stem_split)
  → record(mix_pass, parent=stem, op=eq, metrics=...)
  → record(master, parent=mix, op=master)
  → record(export_spotify, parent=master, op=export)
trace_lineage(export_id) → full chain with params + metrics
```

## Design rules

1. **No openDAW core changes** — store lives beside exports.
2. **Idempotent file writes** — atomic tmp → replace.
3. **chain_hash auto** from params when missing.
4. **P2 process history** reuses same edges with `kind=mix_pass`.
5. **P3 smart export** records `op=export` + platform in params.
6. **P4 prompt inference** records `kind=prompt` + `op=prompt_infer`.
