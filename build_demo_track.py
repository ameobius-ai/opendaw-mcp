#!/usr/bin/env python3
"""
Demo track built entirely through opendaw-mcp.
Dark lo-fi ambient, 72 BPM, A minor.
"""

import asyncio
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["OPENDAW_URL"] = os.environ.get("OPENDAW_URL", "https://localhost:8083")

from opendaw_mcp.bridge import HeadlessDawBridge


async def build_track():
    bridge = HeadlessDawBridge()
    await bridge.start()
    print("✓ Bridge connected")

    P = 384  # PPQN per quarter note

    # ─── BPM ───
    await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        h.modify(() => h.api.setBpm(72));
    }""")
    print("✓ BPM = 72")

    # ─── 1. BASS SYNTH (Vaporisateur) ───
    await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        h.modify(() => h.api.createInstrument(h.factories.Vaporisateur));
    }""")
    print("✓ Vaporisateur bass")

    # Create note track + region + bass notes
    r = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const p = h.project;
        const au = h.auBox(0);
        
        h.modify(() => p.api.createNoteTrack(au));
        const trackBox = [...au.tracks.pointerHub.incoming()].map(({{box}}) => box)[0];
        
        const regionOpt = h.modify(() => p.api.createNoteRegion({{
            trackBox, position: 0, duration: 8*4*{P}, loopDuration: 8*4*{P},
        }}));
        const region = regionOpt.unwrap("region");
        
        // A minor bassline: A1 A1 E2 A1 G2 E2
        const noteData = [
            [33, 0, 4], [33, 4, 4], [40, 8, 4], [33, 12, 4],
            [33, 16, 4], [33, 20, 4], [43, 24, 4], [40, 28, 4],
        ];
        
        h.modify(() => {{
            noteData.forEach(([pitch, bar, dur]) => {{
                p.api.createNoteEvent({{
                    owner: region,
                    pitch: pitch,
                    position: bar * {P},
                    duration: dur * {P},
                    velocity: 75,
                }});
            }});
        }});
        
        return "bass done";
    }}""")
    print(f"✓ Bassline: {r}")

    # ─── 2. DRUMS (Playfield) ───
    await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        h.modify(() => h.api.createInstrument(h.factories.Playfield));
    }""")
    print("✓ Playfield drums")

    r = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const p = h.project;
        const drumsAU = h.auBox(1);
        
        h.modify(() => p.api.createNoteTrack(drumsAU));
        const trackBox = [...drumsAU.tracks.pointerHub.incoming()].map(({{box}}) => box)[0];
        
        const regionOpt = h.modify(() => p.api.createNoteRegion({{
            trackBox, position: 0, duration: 8*4*{P}, loopDuration: 8*4*{P},
        }}));
        const region = regionOpt.unwrap("region");
        
        h.modify(() => {{
            for (let bar = 0; bar < 8; bar++) {{
                for (let beat = 0; beat < 4; beat++) {{
                    const kickPos = (bar * 4 + beat) * {P};
                    p.api.createNoteEvent({{
                        owner: region,
                        pitch: 36,
                        position: kickPos,
                        duration: Math.floor({P} / 2),
                        velocity: 95,
                    }});
                    const hatPos = kickPos + Math.floor({P} / 2);
                    p.api.createNoteEvent({{
                        owner: region,
                        pitch: 42,
                        position: hatPos,
                        duration: Math.floor({P} / 4),
                        velocity: 45,
                    }});
                }}
            }}
        }});
        
        return "drums done";
    }}""")
    print(f"✓ Drum pattern: {r}")

    # ─── 3. PAD (second Vaporisateur) ───
    await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        h.modify(() => h.api.createInstrument(h.factories.Vaporisateur));
    }""")
    print("✓ Vaporisateur pad")

    r = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const p = h.project;
        const padAU = h.auBox(2);
        
        h.modify(() => p.api.createNoteTrack(padAU));
        const trackBox = [...padAU.tracks.pointerHub.incoming()].map(({{box}}) => box)[0];
        
        const regionOpt = h.modify(() => p.api.createNoteRegion({{
            trackBox, position: 0, duration: 8*4*{P}, loopDuration: 8*4*{P},
        }}));
        const region = regionOpt.unwrap("region");
        
        // Am - Am - Em - Am, 2 bars each
        const chords = [
            [0,  [57, 60, 64]],   // Am
            [2,  [57, 60, 64]],   // Am
            [4,  [52, 55, 59]],   // Em
            [6,  [57, 60, 64]],   // Am
        ];
        
        h.modify(() => {{
            chords.forEach(([bar, notes]) => {{
                notes.forEach(pitch => {{
                    p.api.createNoteEvent({{
                        owner: region,
                        pitch: pitch,
                        position: bar * 4 * {P},
                        duration: 2 * 4 * {P},
                        velocity: 40,
                    }});
                }});
            }});
        }});
        
        return "pad done";
    }}""")
    print(f"✓ Pad chords: {r}")

    # ─── 4. MIX ───
    r = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        h.modify(() => {
            h.auBox(0).volume.setValue(0.7);   // bass -3dB
            h.auBox(1).volume.setValue(0.85);  // drums
            h.auBox(2).volume.setValue(0.5);   // pad -6dB
        });
        return "mix set";
    }""")
    print(f"✓ {r}")

    # ─── 5. SYNTH PARAMETERS ───
    r = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        const p = h.project;
        
        const bassDevice = [...h.auBox(0).input.pointerHub.incoming()].map(({box}) => box)[0];
        h.modify(() => {
            if (bassDevice.cutoff) bassDevice.cutoff.setValue(400);
            if (bassDevice.resonance) bassDevice.resonance.setValue(0.3);
            if (bassDevice.attack) bassDevice.attack.setValue(0.05);
            if (bassDevice.release) bassDevice.release.setValue(0.8);
        });
        
        const padDevice = [...h.auBox(2).input.pointerHub.incoming()].map(({box}) => box)[0];
        h.modify(() => {
            if (padDevice.cutoff) padDevice.cutoff.setValue(3000);
            if (padDevice.resonance) padDevice.resonance.setValue(0.05);
            if (padDevice.attack) padDevice.attack.setValue(0.8);
            if (padDevice.release) padDevice.release.setValue(2.0);
        });
        
        return "synth params set";
    }""")
    print(f"✓ {r}")

    # ─── 6. SUMMARY ───
    r = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        const aus = h.allAUBoxes();
        return {
            genre: "Dark Lo-Fi Ambient",
            bpm: 72,
            key: "A minor",
            duration: "8 bars",
            audioUnits: aus.map((au, i) => ({
                index: i,
                type: au.type?.getValue?.(),
                volume: Math.round((au.volume?.getValue?.() ?? 0) * 100) / 100,
                tracks: [...au.tracks.pointerHub.incoming()].length,
            })),
        };
    }""")

    print(f"\n{'='*50}")
    print("TRACK BUILT THROUGH OPENDAW-MCP")
    print(f"{'='*50}")
    print(json.dumps(r, indent=2))

    await bridge.stop()
    print("\n✓ Done — track lives in the DAW session")


if __name__ == "__main__":
    asyncio.run(build_track())
