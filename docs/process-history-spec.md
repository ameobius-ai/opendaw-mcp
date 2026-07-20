# Process history — last-N mix passes (P2)

Depends on lineage (P1). Reuse `kind=mix_pass` edges.

**Status: implemented in 1.391.0**

## Goal

Agent iterative mix without "what was 3 steps ago?":

```
pass_n metrics vs pass_n-1
  sub_pct / presence_pct / air_pct / lufs / true_peak_db
```

## Tools

1. `record_mix_pass(parent_id, path, params_json, metrics_json, label)`
   wrapper → `record_lineage(kind=mix_pass, op=eq|master|..., ...)`

2. `list_mix_history(root_id|node_id, limit=8)`
   last N mix_pass descendants / chain with metric diffs

3. `diff_mix_passes(node_a, node_b)`
   numeric delta on metrics keys

## Metric keys (canonical)

- `lufs_integrated`
- `true_peak_db`
- `sub_pct`
- `presence_pct`
- `air_pct`
- `crest`

## Acceptance

- unit tests with synthetic chain of 5 mix_pass nodes
- diff shows presence_pct +0.4 after HS boost
- no openDAW core changes

## Kanban

`t_30120c46`
