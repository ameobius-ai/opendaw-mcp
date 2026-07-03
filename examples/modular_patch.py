"""Example: Build a modular patch in openDAW.

Creates a Modular audio effect with a Gain → Delay chain,
demonstrating the modular system's patch cable routing.
"""
import asyncio
import json
from server import bridge


async def main():
    await bridge.start()

    # 1. Create an instrument track
    result = await bridge.evaluate('''() => {
        const p = window.DAW;
        try {
            p.editing.modify(() => {
                const cap = window.DAW_CaptureAudioBox.create(p.boxGraph, window.DAW_UUID.generate());
                const au = window.DAW_AudioUnitBox.create(p.boxGraph, window.DAW_UUID.generate(), (box) => {
                    box.type.setValue(window.DAW_AudioUnitType.Instrument);
                    box.collection.refer(p.rootBox.audioUnits);
                    box.output.refer(p.primaryAudioBusBox.input);
                    box.capture.refer(cap);
                    box.index.setValue(0);
                    box.volume.setValue(0.767835);
                });
                window.DAW_InstrumentFactories.Vaporisateur.create(
                    p.boxGraph, au.input, "Modular Demo", window.DAW_IconSymbol.Piano
                );
                p.api.createNoteTrack(au);
            });
            return {ok: true};
        } catch(e) { return {error: e.message}; }
    }''')
    print(f"1. Created instrument: {json.dumps(result)}")

    # 2. Add Modular effect
    result = await bridge.evaluate('''() => {
        const p = window.DAW;
        try {
            const au = p.rootBoxAdapter.audioUnits.adapters()[0];
            p.editing.modify(() => {
                p.api.insertEffect(au.box.audioEffects, window.DAW_EffectFactories.Modular);
            });
            return {ok: true};
        } catch(e) { return {error: e.message}; }
    }''')
    print(f"2. Added Modular effect: {json.dumps(result)}")

    # 3. Add Gain and Delay modules
    result = await bridge.evaluate('''() => {
        const p = window.DAW;
        try {
            const getMod = () => {
                const au = p.rootBoxAdapter.audioUnits.adapters()[0];
                return au.audioEffects.adapters()
                    .find(e => e.box instanceof window.DAW_ModularDeviceBox).modular();
            };
            
            // Add Gain module (VCA)
            p.editing.modify(() => {
                window.DAW_ModuleGainBox.create(p.boxGraph, window.DAW_UUID.generate(), (box) => {
                    box.attributes.collection.refer(getMod().box.modules);
                    box.attributes.label.setValue("VCA");
                    box.attributes.x.setValue(0);
                    box.attributes.y.setValue(64);
                });
            });
            
            // Add Delay module
            p.editing.modify(() => {
                window.DAW_ModuleDelayBox.create(p.boxGraph, window.DAW_UUID.generate(), (box) => {
                    box.attributes.collection.refer(getMod().box.modules);
                    box.attributes.label.setValue("Delay");
                    box.attributes.x.setValue(128);
                    box.attributes.y.setValue(64);
                });
            });
            
            return {ok: true, module_count: getMod().modules.length};
        } catch(e) { return {error: e.message}; }
    }''')
    print(f"3. Added Gain + Delay modules: {json.dumps(result)}")

    # 4. Patch: AudioInput → Gain → Delay → AudioOutput
    result = await bridge.evaluate('''() => {
        const p = window.DAW;
        try {
            const getMod = () => {
                const au = p.rootBoxAdapter.audioUnits.adapters()[0];
                return au.audioEffects.adapters()
                    .find(e => e.box instanceof window.DAW_ModularDeviceBox).modular();
            };
            const mod = getMod();
            const inMod = mod.modules.find(m => m.box.name === "ModularAudioInputBox");
            const gainMod = mod.modules.find(m => m.box.name === "ModuleGainBox");
            const delayMod = mod.modules.find(m => m.box.name === "ModuleDelayBox");
            const outMod = mod.modules.find(m => m.box.name === "ModularAudioOutputBox");
            
            // Connect: Input → Gain
            p.editing.modify(() => {
                window.DAW_ModuleConnectionBox.create(p.boxGraph, window.DAW_UUID.generate(), (box) => {
                    box.collection.refer(mod.box.connections);
                    box.source.refer(inMod.outputs[0].field);
                    box.target.refer(gainMod.inputs[0].field);
                });
            });
            
            // Connect: Gain → Delay
            p.editing.modify(() => {
                window.DAW_ModuleConnectionBox.create(p.boxGraph, window.DAW_UUID.generate(), (box) => {
                    box.collection.refer(getMod().box.connections);
                    box.source.refer(gainMod.outputs[0].field);
                    box.target.refer(delayMod.inputs[0].field);
                });
            });
            
            // Connect: Delay → Output
            p.editing.modify(() => {
                window.DAW_ModuleConnectionBox.create(p.boxGraph, window.DAW_UUID.generate(), (box) => {
                    box.collection.refer(getMod().box.connections);
                    box.source.refer(delayMod.outputs[0].field);
                    box.target.refer(outMod.inputs[0].field);
                });
            });
            
            return {ok: true, connections: getMod().connections.length};
        } catch(e) { return {error: e.message}; }
    }''')
    print(f"4. Patched Input→Gain→Delay→Output: {json.dumps(result)}")

    # 5. Set parameters: Gain = -3dB, Delay = 500ms
    result = await bridge.evaluate('''() => {
        const p = window.DAW;
        try {
            const mod = p.rootBoxAdapter.audioUnits.adapters()[0]
                .audioEffects.adapters()
                .find(e => e.box instanceof window.DAW_ModularDeviceBox).modular();
            const gainMod = mod.modules.find(m => m.box.name === "ModuleGainBox");
            const delayMod = mod.modules.find(m => m.box.name === "ModuleDelayBox");
            
            p.editing.modify(() => { gainMod.box.gain.setValue(-3.0); });
            p.editing.modify(() => { delayMod.box.time.setValue(500.0); });
            
            return {
                gain_db: gainMod.box.gain.getValue(),
                delay_ms: delayMod.box.time.getValue()
            };
        } catch(e) { return {error: e.message}; }
    }''')
    print(f"5. Set params: {json.dumps(result)}")

    # 6. Final state
    result = await bridge.evaluate('''() => {
        const p = window.DAW;
        try {
            const mod = p.rootBoxAdapter.audioUnits.adapters()[0]
                .audioEffects.adapters()
                .find(e => e.box instanceof window.DAW_ModularDeviceBox).modular();
            return {
                modules: mod.modules.map(m => ({
                    type: m.box.name,
                    label: m.attributes.label.getValue(),
                    inputs: m.inputs.map(c => c.name),
                    outputs: m.outputs.map(c => c.name)
                })),
                connections: mod.connections.map(c => 
                    c.source.box.name + "." + c.source.fieldName + " → " +
                    c.target.box.name + "." + c.target.fieldName
                )
            };
        } catch(e) { return {error: e.message}; }
    }''')
    print(f"\n6. Final patch state:\n{json.dumps(result, indent=2)}")

    await bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())
