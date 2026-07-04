# Send/Return Routing Investigation (July 2 session 4)

## Goal
Create parallel FX buses (reverb/delay on separate AU) via aux sends, controllable from MCP.

## What works
- `AuxSendBox.create(boxGraph, UUID, (box) => { ... })` — creates send box
- `AudioBusBox.create(boxGraph, UUID, (box) => { ... })` — creates FX bus
- `box.audioUnit.refer(srcAU.auxSends)` — connects send to source AU
- `box.sendGain.setValue(dB)` — send level in dB (field stores dB, NOT 0..1)
- `box.routing.setValue(0|1)` — 0=Pre-fader, 1=Post-fader (AudioSendRouting enum)
- Both `AuxSendBox` and `AudioBusBox` added to headless-daw main.ts lazy-load

## Topology issue (BLOCKER)

**Symptom**: after `create_send(src=1, dst=2)`, export_mix returns max_sample=0.0000 (silence).

**Root cause**: `dstAU.output.refer(fxBus.input)` redirects dst AU's output from primary bus to FX bus. This breaks the main signal path — dst AU (ReverbBus with Vaporisateur) no longer reaches primary output. And since Vaporisateur on dst AU has no notes, FX bus gets silence.

**Wrong approach (current code)**:
```
srcAU (Lead) → primaryBus (main out)    ← dry path OK
srcAU.auxSends → AuxSendBox → fxBus.input    ← send path
dstAU (ReverbBus) → fxBus.input    ← BROKEN: redirected from primaryBus
fxBus.output → primaryBus.input    ← FX bus to main out
```
Problem: dstAU was on primaryBus, now on fxBus. But fxBus only gets signal from the aux send, not from dstAU's own instrument. dstAU's Vaporisateur has no notes → silence on fxBus → silence everywhere.

**Correct approach (NOT YET IMPLEMENTED)**:
Don't redirect dstAU.output. Instead:
1. Create fxBus (AudioBusBox) with output → primaryBus.input
2. Create AuxSendBox: srcAU.auxSends → fxBus.input (send taps srcAU post-fader)
3. dstAU stays on primaryBus (unchanged)
4. Add Reverb effect on... where? The FX bus itself doesn't have an effect chain.

**Alternative**: openDAW's send/return model may work differently than traditional DAWs:
- In openDAW, sends go AU → AudioBusBox (not AU → AU)
- AudioBusBox has no effect chain field — effects live on AudioUnitBox
- Need to study how openDAW UI creates "FX channel" with effects + send return

**Next step**: Study `packages/app/studio/src/ui/` for mixer/send bus creation UI. Look at how `Mixer.ts` or `AudioBusBoxAdapter` handles incoming sends + effect chains on buses.

## AuxSendBox schema
```typescript
fields: {
    1: pointer "audio-unit" → Pointers.AuxSend (mandatory)
    2: pointer "target-bus" → Pointers.AudioOutput (mandatory)
    3: int32 "index" (index constraint)
    4: int32 "routing" (AudioSendRouting.Pre=0 | Post=1, default Post)
    5: float32 "send-gain" (decibel constraint, dB)
    6: float32 "send-pan" (bipolar constraint)
}
```

## AudioBusBox schema
```typescript
fields: {
    1: pointer "collection" → Pointers.AudioBusses (mandatory)
    2: pointer "output" → Pointers.AudioOutput (mandatory)
    3: field "input" → accepts Pointers.AudioOutput (NOT exclusive — multiple incoming OK)
    4: boolean "enabled" (default true)
    5: string "icon"
    6: string "label"
    7: string "color" (default "red")
    8: boolean "minimized"
}
```

Note: AudioBusBox has NO `audio-effects` field — effects only live on AudioUnitBox. This means the traditional "FX channel with reverb" pattern needs a different approach in openDAW.

## DawProjectImporter pattern (reference)
```typescript
const auxSendBox = AuxSendBox.create(boxGraph, UUID.generate(), box => {
    box.audioUnit.refer(audioUnitBox.auxSends)
    box.targetBus.refer(targetBusBox.input)  // targetBusBox is AudioBusBox, not AudioUnitBox
    box.routing.setValue(AudioSendRouting.Post)
    box.sendGain.setValue(gainToDb(volume))
})
```
The importer connects `targetBus` to an `AudioBusBox.input`, NOT to an `AudioUnitBox.input`. This confirms sends go AU → AudioBusBox, not AU → AU.
