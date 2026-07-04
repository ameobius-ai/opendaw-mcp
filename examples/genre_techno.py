"""
Example: Genre Template — Techno Track Skeleton

Demonstrates the opendaw-genres skill: creates a complete techno track skeleton
with BPM, drum pattern, rolling bass, chord stab, and effect chain.

Usage:
    # Start Vite first (in separate terminal):
    #   cd headless-daw && npx vite --port 5174
    #
    # Then:
    source venv/bin/activate
    OPENDAW_URL=http://localhost:5174 python3 examples/genre_techno.py
"""
import asyncio
import sys
sys.path.insert(0, ".")
from server import HeadlessDawBridge


async def main():
    bridge = HeadlessDawBridge()
    await bridge.start()

    try:
        # === 1. Set BPM ===
        await bridge.evaluate("""() => {
            const h = window.DAW_HELPERS;
            h.api.setBpm(130);
            return {bpm: 130};
        }""")
        print("✓ BPM set to 130")

        # === 2. Create drum track (Playfield) ===
        drum_result = await bridge.evaluate("""async () => {
            const h = window.DAW_HELPERS;
            const p = h.api;
            // Create instrument AU
            const inst = p.createAnyInstrument(h.InstrumentFactories.Playfield);
            const au = inst.audioUnit;
            const auIndex = h.allAUs().indexOf(au);
            // Create note track
            const track = p.createNoteTrack(au);
            const trackIndex = au.tracks.size - 1;
            // Create note region (4 bars = 16 beats)
            const region = p.createNoteRegion({
                owner: track,
                position: 0,
                duration: 16,
                unit: h.allAUs().indexOf(au)
            });
            return {
                au_index: auIndex,
                track_index: trackIndex,
                region_index: 0,
                instrument: "Playfield"
            };
        }""")
        print(f"✓ Drum track created: {drum_result}")

        # === 3. Create bass track (Vaporisateur) ===
        bass_result = await bridge.evaluate("""async () => {
            const h = window.DAW_HELPERS;
            const p = h.api;
            const inst = p.createAnyInstrument(h.InstrumentFactories.Vaporisateur);
            const au = inst.audioUnit;
            const auIndex = h.allAUs().indexOf(au);
            const track = p.createNoteTrack(au);
            const region = p.createNoteRegion({
                owner: track,
                position: 0,
                duration: 16,
                unit: auIndex
            });
            return {au_index: auIndex, track_index: 0, region_index: 0};
        }""")
        print(f"✓ Bass track created: {bass_result}")

        # === 4. Add drum pattern (4-on-the-floor) ===
        # Using create_drum_pattern orchestration tool logic
        drum_pattern = {
            "kick":  "x...x...x...x...",
            "clap":  "....x.......x...",
            "hihat": "o.o.o.o.o.o.o.o.",
        }
        drum_pattern_json = str(drum_pattern).replace("'", '"')
        pattern_result = await bridge.evaluate(f"""async () => {{
            const h = window.DAW_HELPERS;
            const p = h.api;
            const aus = h.allAUs();
            if (aus.length < 1) return {{error: "No AUs"}};
            const drumAU = aus[0]; // first AU = drums
            const track = [...drumAU.tracks.values()][0];
            const region = [...track.regions.collection.asArray()][0];
            const notes = [];
            const lanes = {{
                "kick": 36, "clap": 39, "hihat": 42, "snare": 38, "perc": 47
            }};
            const pattern = {drum_pattern_json};
            const ppqn = h.ppqn.Quarter; // 960
            const stepLen = ppqn / 4; // 16th note = 240 ppqn
            for (const [lane, hits] of Object.entries(pattern)) {{
                const pitch = lanes[lane] || 36;
                for (let i = 0; i < hits.length; i++) {{
                    const c = hits[i];
                    if (c === '.') continue;
                    let vel = 0.7;
                    if (c === 'x') vel = 0.9;
                    else if (c === 'o') vel = 0.5;
                    else if (c === 'X') vel = 1.0;
                    notes.push({{
                        position: i * stepLen,
                        duration: stepLen,
                        pitch: pitch,
                        velocity: vel
                    }});
                }}
            }}
            // Add notes to region
            const events = region.events.targetVertex.unwrap().box;
            const NoteEventBox = window.DAW_NoteEventBox;
            h.modify(() => {{
                for (const n of notes) {{
                    p.createNoteEvent({{
                        owner: events,
                        position: n.position,
                        duration: n.duration,
                        velocity: n.velocity,
                        pitch: n.pitch
                    }});
                }}
            }});
            return {{notes_added: notes.length}};
        }}""")
        print(f"✓ Drum pattern added: {pattern_result}")

        # === 5. Add rolling bass (16th notes, A1 = 33) ===
        bass_notes_result = await bridge.evaluate("""async () => {
            const h = window.DAW_HELPERS;
            const p = h.api;
            const aus = h.allAUs();
            if (aus.length < 2) return {error: "No bass AU"};
            const bassAU = aus[1]; // second AU = bass
            const track = [...bassAU.tracks.values()][0];
            const region = [...track.regions.collection.asArray()][0];
            const events = region.events.targetVertex.unwrap().box;
            const ppqn = h.ppqn.Quarter;
            const stepLen = ppqn / 4; // 16th
            const notes = [];
            // 16 bars × 4 beats × 4 sixteenths = 256 notes (but we do 4 bars = 64)
            for (let i = 0; i < 64; i++) {
                notes.push({
                    position: i * stepLen,
                    duration: stepLen,
                    pitch: 33, // A1
                    velocity: 0.7
                });
            }
            h.modify(() => {
                for (const n of notes) {
                    p.createNoteEvent({
                        owner: events,
                        position: n.position,
                        duration: n.duration,
                        velocity: n.velocity,
                        pitch: n.pitch
                    });
                }
            });
            return {bass_notes: notes.length};
        }""")
        print(f"✓ Rolling bass added: {bass_notes_result}")

        # === 6. Add effect chain on drums ===
        drum_fx = await bridge.evaluate("""async () => {
            const h = window.DAW_HELPERS;
            const p = h.api;
            const aus = h.allAUs();
            if (aus.length < 1) return {error: "No drum AU"};
            const drumAU = aus[0];
            // Add Compressor
            const comp = p.insertEffect(drumAU.audioEffects, h.EffectFactories.Compressor);
            // Add Revamp (EQ)
            const eq = p.insertEffect(drumAU.audioEffects, h.EffectFactories.Revamp);
            const fx = [...drumAU.audioEffects.adapters()];
            return {
                effects: fx.length,
                types: fx.map(f => f.box.constructor.name.replace('DeviceBox',''))
            };
        }""")
        print(f"✓ Drum effects: {drum_fx}")

        # === 7. Add Waveshaper on bass ===
        bass_fx = await bridge.evaluate("""async () => {
            const h = window.DAW_HELPERS;
            const p = h.api;
            const aus = h.allAUs();
            if (aus.length < 2) return {error: "No bass AU"};
            const bassAU = aus[1];
            const ws = p.insertEffect(bassAU.audioEffects, h.EffectFactories.Waveshaper);
            const fx = [...bassAU.audioEffects.adapters()];
            return {
                effects: fx.length,
                types: fx.map(f => f.box.constructor.name.replace('DeviceBox',''))
            };
        }""")
        print(f"✓ Bass effects: {bass_fx}")

        # === 8. Set track volumes ===
        volumes = await bridge.evaluate("""async () => {
            const h = window.DAW_HELPERS;
            const aus = h.allAUs();
            const results = [];
            // Drums at -3 dB
            if (aus[0]) {
                aus[0].box.volume.setValue(-3.0);
                results.push({au: 0, volume: aus[0].box.volume.getValue()});
            }
            // Bass at -6 dB
            if (aus[1]) {
                aus[1].box.volume.setValue(-6.0);
                results.push({au: 1, volume: aus[1].box.volume.getValue()});
            }
            return results;
        }""")
        print(f"✓ Track volumes: {volumes}")

        # === 9. Get project state ===
        state = await bridge.evaluate("""() => {
            const h = window.DAW_HELPERS;
            const aus = h.allAUs();
            return {
                bpm: h.timelineBox?.box?.bpm?.getValue() || "unknown",
                au_count: aus.length,
                au_details: aus.map(au => ({
                    name: au.box.label?.getValue() || "unnamed",
                    volume: au.box.volume?.getValue(),
                    effect_count: [...au.audioEffects.adapters()].length
                }))
            };
        }""")
        print(f"\n✅ Techno skeleton created!")
        print(f"   BPM: {state.get('bpm')}")
        print(f"   AUs: {state.get('au_count')}")
        for au in state.get('au_details', []):
            print(f"   - {au['name']}: vol={au['volume']}dB, fx={au['effect_count']}")

    finally:
        await bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())
