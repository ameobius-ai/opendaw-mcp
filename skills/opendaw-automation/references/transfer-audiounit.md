# TransferAudioUnits MCP Tool

## API
`TransferAudioUnits.transfer(audioUnitBoxes, ProjectSkeleton, options)` → `ReadonlyArray<AudioUnitBox>`

### ProjectSkeleton
```js
{
  boxGraph: p.boxGraph,
  mandatoryBoxes: {
    primaryAudioBusBox: primaryBus,  // AudioBusBox on Output unit's input
    rootBox: p.rootBox
  }
}
```

### Finding primaryAudioBusBox
```js
const outputAU = units.find(u => u.type.getValue() === "output");
const primaryBus = [...outputAU.input.pointerHub.incoming()].map(({box}) => box)[0];
```

### TransferOptions
- `insertIndex?: int` — mixer position (-1 = auto by AudioUnitOrdering)
- `deleteSource?: boolean` — true = move, false = copy
- `includeAux?: boolean` — include aux sends
- `includeBus?: boolean` — include bus routing
- `excludeTimeline?: boolean` — exclude tracks/regions

## Key Behaviors
- Output unit filtered from sources (project singleton)
- AuxSendBox excluded by default (TransferUtils.shouldExclude)
- Preserved resources (AudioFileBox, SoundfontFileBox) shared, not duplicated
- New AUs auto-ordered by AudioUnitOrdering (Instruments → Buses → Output)
- Full dependency tracking: instrument, effects, MIDI effects, tracks, regions, notes, automation

## AudioUnitType (string enum)
```typescript
enum AudioUnitType {
    Instrument = "instrument",
    Bus = "bus",
    Aux = "aux",
    Output = "output"
}
```
**Pitfall:** `type.getValue()` returns string ("instrument"), not number. Compare with `=== "output"`, not `=== 2`.

## MCP Tool
`transfer_audiounit(unit_index, delete_source=False, insert_index=-1)`

## E2E Test Result
- Source: AU 0 (Vaporisateur + Delay + note track with notes)
- Transfer: copy (delete_source=false)
- Result: new AU at index 1, type "instrument", effects=["Delay"], tracks=2
- Total AUs: 3 (2 instruments + 1 output)
- Source preserved ✅

## DAW Global
`DAW_TransferAudioUnits` added to headless-daw/src/main.ts globals.

## vs duplicate_audiounit
`transfer_audiounit` uses box-graph serialization (TransferAudioUnits) — more complete than `duplicate_audiounit` (Python orchestration via existing MCP tools). Prefer transfer_audiounit for deep copies.
