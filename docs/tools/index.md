# Tool Reference

556 MCP tools for headless openDAW control. All tools use the `mcp_opendaw_` prefix.

## Categories

| Category | Tools | Page |
|----------|-------|------|
| Project & Transport | 32 | [→](project-transport.md) |
| Tracks & Audio Units | 21 | [→](tracks.md) |
| Instruments & Synths | 4 | [→](instruments.md) |
| Effects & MIDI Effects | 32 | [→](effects.md) |
| Notes & Regions | 48 | [→](notes-regions.md) |
| Clips & Markers | 22 | [→](clips-markers.md) |
| Mixer & Sends | 17 | [→](mixer.md) |
| Automation | 12 | [→](automation.md) |
| Export & Rendering | 17 | [→](export.md) |
| Scriptable Devices | 5 | [→](scriptable.md) |
| Drums & Modular | 12 | [→](drums-modular.md) |
| Stems & Presets | 4 | [→](stems-presets.md) |
| Orchestration & Misc | 26 | [→](orchestration.md) |

## Calling convention

All tools are async and return a JSON dict. Example:

```python
result = await server.mcp_opendaw_set_bpm(bpm=124)
# {"success": true, "bpm": 124}
```

## DAW_HELPERS

17 typed helpers injected into the bridge context for box enumeration.
See [Architecture → DAW_HELPERS](../architecture.md#daw_helpers) for the full list.
