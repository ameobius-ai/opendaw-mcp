#!/usr/bin/env python3
"""
Silent Hill inspired trip-hop. Akira Yamaoka style.
80 BPM, A minor, 48 bars (~2:24)

Fixes v2:
- Vaporisateur drum synthesis (kick/snare/hat) instead of Playfield
- Explicit range:"full" in export config for full-length render
"""

import asyncio, sys, os, base64, json, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["OPENDAW_URL"] = os.environ.get("OPENDAW_URL", "https://localhost:8083")
from opendaw_mcp.bridge import HeadlessDawBridge

random.seed(777)
P = 960  # PPQN — openDAW uses 960, NOT 384!
BAR = 4 * P
TOTAL = 48 * BAR

async def build():
    bridge = HeadlessDawBridge()
    await bridge.start()
    print("✓ Bridge connected\n")

    # ═══ TEMPO ═══
    await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        h.modify(() => h.api.setBpm(80));
    }""")
    print("✓ 80 BPM, A minor\n")

    # ═══ 1. SUB BASS (Vaporisateur #0) ═══
    await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        h.modify(() => h.api.createInstrument(h.factories.Vaporisateur));
    }""")
    await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        const dev = [...h.auBox(0).input.pointerHub.incoming()].map(({box}) => box)[0];
        h.modify(() => {
            dev.cutoff?.setValue(180);
            dev.resonance?.setValue(0.15);
            dev.attack?.setValue(0.008);
            dev.decay?.setValue(0.1);
            dev.sustain?.setValue(0.9);
            dev.release?.setValue(0.25);
        });
    }""")
    print("▌ BASS — sub 180Hz")

    r = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const p = h.project;
        const au = h.auBox(0);
        h.modify(() => p.api.createNoteTrack(au));
        const track = [...au.tracks.pointerHub.incoming()].map(({{box}}) => box)[0];
        const regionOpt = h.modify(() => p.api.createNoteRegion({{
            trackBox: track, position: 0, duration: {TOTAL}, loopDuration: {TOTAL},
        }}));
        const region = regionOpt.unwrap("r");
        const sections = [
            [4, 33, 2], [6, 29, 2], [8, 26, 2], [10, 28, 2],
            [12, 33, 2], [14, 29, 2], [16, 26, 2], [18, 28, 2],
            [20, 33, 2], [22, 29, 2], [24, 26, 2], [26, 28, 2],
            [28, 26, 2], [30, 22, 2], [32, 19, 2], [34, 33, 2],
            [36, 33, 2], [38, 29, 2], [40, 26, 2], [42, 28, 2],
            [44, 33, 4],
        ];
        h.modify(() => {{
            sections.forEach(([bar, root, dur]) => {{
                for (let b = 0; b < dur; b++) {{
                    p.api.createNoteEvent({{
                        owner: region, pitch: root,
                        position: bar * {BAR} + b * {BAR},
                        duration: {BAR},
                        velocity: 72 + Math.floor(Math.random() * 8),
                    }});
                }}
            }});
        }});
        return "bass done";
    }}""")
    print(f"  → {r}")

    await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        const au = h.auBox(0);
        const EF = window.opendaw.EffectFactories;
        h.modify(() => h.api.insertEffect(au.audioEffects, EF.Compressor));
        const comp = h.effectBoxes(au)[0];
        h.modify(() => {
            comp.threshold?.setValue(-18);
            comp.ratio?.setValue(3);
            comp.attack?.setValue(0.006);
            comp.release?.setValue(0.1);
        });
    }""")
    print("  → Compressor -18dB 3:1")

    # ═══ 2. KICK (Vaporisateur #1) — low, tight ═══
    await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        h.modify(() => h.api.createInstrument(h.factories.Vaporisateur));
    }""")
    await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        const dev = [...h.auBox(1).input.pointerHub.incoming()].map(({box}) => box)[0];
        h.modify(() => {
            dev.cutoff?.setValue(120);
            dev.resonance?.setValue(0.3);
            dev.attack?.setValue(0.001);
            dev.decay?.setValue(0.04);
            dev.sustain?.setValue(0.0);
            dev.release?.setValue(0.02);
        });
    }""")
    print("\n▌ KICK — Vaporisateur sub-kick, 120Hz cutoff, instant decay")

    # ═══ 3. SNARE/HAT (Vaporisateur #2) — bright, noise-like ═══
    await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        h.modify(() => h.api.createInstrument(h.factories.Vaporisateur));
    }""")
    await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        const dev = [...h.auBox(2).input.pointerHub.incoming()].map(({box}) => box)[0];
        h.modify(() => {
            dev.cutoff?.setValue(6000);
            dev.resonance?.setValue(0.05);
            dev.attack?.setValue(0.001);
            dev.decay?.setValue(0.03);
            dev.sustain?.setValue(0.0);
            dev.release?.setValue(0.01);
        });
    }""")
    print("▌ SNARE/HAT — Vaporisateur noise, 6kHz cutoff, razor short")

    # Program all drums across kick + snare/hat instruments
    r = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const p = h.project;
        const kickAU = h.auBox(1);
        const snareAU = h.auBox(2);

        h.modify(() => p.api.createNoteTrack(kickAU));
        h.modify(() => p.api.createNoteTrack(snareAU));

        const kickTrack = [...kickAU.tracks.pointerHub.incoming()].map(({{box}}) => box)[0];
        const snareTrack = [...snareAU.tracks.pointerHub.incoming()].map(({{box}}) => box)[0];

        const kickRegion = h.modify(() => p.api.createNoteRegion({{
            trackBox: kickTrack, position: 0, duration: {TOTAL}, loopDuration: {TOTAL},
        }})).unwrap("kr");
        const snareRegion = h.modify(() => p.api.createNoteRegion({{
            trackBox: snareTrack, position: 0, duration: {TOTAL}, loopDuration: {TOTAL},
        }})).unwrap("sr");

        h.modify(() => {{
            for (let bar = 0; bar < 48; bar++) {{
                const isIntro = bar < 4;
                const isOutro = bar >= 44;
                const isBridge = bar >= 28 && bar < 36;
                const kickActive = !isIntro;
                const drumIntensity = isBridge ? 0.6 : (isOutro ? 0.4 : 1.0);

                // KICK: trip-hop syncopation
                if (kickActive) {{
                    const kv = Math.floor(95 * drumIntensity);
                    // Beat 1
                    p.api.createNoteEvent({{owner: kickRegion, pitch: 24, position: bar*{BAR}, duration: Math.floor({P}*0.5), velocity: kv + Math.floor(Math.random()*8-4)}});
                    // Beat 1.5 (syncopated)
                    p.api.createNoteEvent({{owner: kickRegion, pitch: 24, position: bar*{BAR}+Math.floor(1.5*{P}), duration: Math.floor({P}*0.5), velocity: Math.floor(kv*0.85)}});
                    // Beat 3 (even bars only)
                    if (bar % 2 === 0) {{
                        p.api.createNoteEvent({{owner: kickRegion, pitch: 24, position: bar*{BAR}+2*{P}, duration: Math.floor({P}*0.5), velocity: Math.floor(kv*0.75)}});
                    }}
                }}

                // SNARE: backbeat 2 and 4
                if (!isIntro) {{
                    const sv = Math.floor(80 * drumIntensity);
                    p.api.createNoteEvent({{owner: snareRegion, pitch: 45, position: bar*{BAR}+1*{P}, duration: Math.floor({P}*0.4), velocity: sv + Math.floor(Math.random()*8-4)}});
                    p.api.createNoteEvent({{owner: snareRegion, pitch: 45, position: bar*{BAR}+3*{P}, duration: Math.floor({P}*0.4), velocity: sv + Math.floor(Math.random()*8-4)}});
                }}

                // HATS: 8th notes with swing — same snare synth at high pitch
                const hatVel = isIntro ? 15 : Math.floor(50 * drumIntensity);
                for (let beat = 0; beat < 8; beat++) {{
                    const isOff = beat % 2 === 1;
                    const swing = isOff ? Math.floor({P} * 0.12) : 0;
                    const v = hatVel + (isOff ? -12 : 5) + Math.floor(Math.random()*8-4);
                    if (v > 8) {{
                        p.api.createNoteEvent({{
                            owner: snareRegion, pitch: 72,
                            position: bar*{BAR} + Math.floor(beat*{P}/2) + swing,
                            duration: Math.floor({P}*0.1),
                            velocity: Math.max(8, v),
                        }});
                    }}
                }}

                // Industrial clanks: random metallic hits
                if (!isIntro && Math.random() < 0.25) {{
                    const pos = bar*{BAR} + Math.floor(Math.random() * 4 * {P});
                    p.api.createNoteEvent({{
                        owner: snareRegion,
                        pitch: 55 + Math.floor(Math.random()*10),
                        position: pos,
                        duration: Math.floor({P}*0.12),
                        velocity: 35 + Math.floor(Math.random()*25),
                    }});
                }}
            }}
        }});

        return "drums: kick+snare+hat+clanks across 48 bars";
    }}""")
    print(f"\n▌ DRUMS — {r}")

    # Drum FX
    await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        const EF = window.opendaw.EffectFactories;
        // Kick: slight compression
        h.modify(() => h.api.insertEffect(h.auBox(1).audioEffects, EF.Compressor));
        const kComp = h.effectBoxes(h.auBox(1))[0];
        h.modify(() => {
            kComp.threshold?.setValue(-10);
            kComp.ratio?.setValue(2);
        });
        // Snare/hat: crusher for industrial grit + reverb
        h.modify(() => {
            h.api.insertEffect(h.auBox(2).audioEffects, EF.Crusher);
            h.api.insertEffect(h.auBox(2).audioEffects, EF.Reverb);
        });
        const crush = h.effectBoxes(h.auBox(2)).find(f => f.label?.getValue?.() === "Crusher");
        const rev = h.effectBoxes(h.auBox(2)).find(f => f.label?.getValue?.() === "Reverb");
        h.modify(() => {
            if (crush) { crush.bits?.setValue(6); crush.frequency?.setValue(0.4); }
            if (rev) { rev.roomSize?.setValue(0.4); }
        });
    }""")
    print("  → Kick: Comp | Snare/Hat: Crusher 6-bit + Reverb")

    # ═══ 4. ATMOSPHERE PAD (Vaporisateur #3) ═══
    await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        h.modify(() => h.api.createInstrument(h.factories.Vaporisateur));
    }""")
    await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        const dev = [...h.auBox(3).input.pointerHub.incoming()].map(({box}) => box)[0];
        h.modify(() => {
            dev.cutoff?.setValue(800);
            dev.resonance?.setValue(0.05);
            dev.attack?.setValue(2.0);
            dev.decay?.setValue(1.0);
            dev.sustain?.setValue(0.6);
            dev.release?.setValue(4.0);
        });
    }""")
    print("\n▌ PAD — atmosphere, slow swell")

    r = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const p = h.project;
        const au = h.auBox(3);
        h.modify(() => p.api.createNoteTrack(au));
        const track = [...au.tracks.pointerHub.incoming()].map(({{box}}) => box)[0];
        const regionOpt = h.modify(() => p.api.createNoteRegion({{
            trackBox: track, position: 0, duration: {TOTAL}, loopDuration: {TOTAL},
        }}));
        const region = regionOpt.unwrap("r");
        const chords = [
            [0, [45, 48, 52, 57, 60], 4],
            [4, [45, 48, 52, 57, 60], 2], [6, [41, 45, 48, 53, 57], 2],
            [8, [38, 41, 45, 50, 53], 2], [10, [40, 44, 47, 52, 56], 2],
            [12, [45, 48, 52, 57, 60], 2], [14, [41, 45, 48, 53, 57], 2],
            [16, [38, 41, 45, 50, 53], 2], [18, [40, 44, 47, 52, 56], 2],
            [20, [45, 48, 52, 57, 60], 2], [22, [41, 45, 48, 53, 57], 2],
            [24, [38, 41, 45, 50, 53], 2], [26, [40, 44, 47, 52, 56], 2],
            // BRIDGE — darker
            [28, [38, 41, 45, 50, 53], 2], [30, [34, 38, 41, 46, 50], 2],
            [32, [31, 34, 38, 43, 46], 2], [34, [45, 49, 52, 57, 61], 2],
            [36, [45, 48, 52, 57, 60], 2], [38, [41, 45, 48, 53, 57], 2],
            [40, [38, 41, 45, 50, 53], 2], [42, [40, 44, 47, 52, 56], 2],
            [44, [45, 48, 52, 57, 60], 4],
        ];
        h.modify(() => {{
            chords.forEach(([bar, notes, dur]) => {{
                notes.forEach((pitch, i) => {{
                    const offset = i * Math.floor({P} * 0.05);
                    p.api.createNoteEvent({{
                        owner: region, pitch,
                        position: bar * {BAR} + offset,
                        duration: dur * {BAR} - offset,
                        velocity: 30 + Math.floor(Math.random() * 12),
                    }});
                }});
            }});
        }});
        return "pad: 48 bars with bridge shift";
    }}""")
    print(f"  → {r}")

    await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        const au = h.auBox(3);
        const EF = window.opendaw.EffectFactories;
        h.modify(() => {
            h.api.insertEffect(au.audioEffects, EF.DattorroReverb);
            h.api.insertEffect(au.audioEffects, EF.Delay);
        });
        const rev = h.effectBoxes(au).find(f => f.label?.getValue?.() === "Dattorro Reverb");
        const del = h.effectBoxes(au).find(f => f.label?.getValue?.() === "Delay");
        h.modify(() => {
            if (rev) { rev.decay?.setValue(0.8); rev.preDelay?.setValue(0.03); }
            if (del) { del.time?.setValue(0.375); del.feedback?.setValue(0.45); del.mix?.setValue(0.35); }
        });
    }""")
    print("  → Dattorro Reverb + Delay")

    # ═══ 5. LEAD (Vaporisateur #4) ═══
    await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        h.modify(() => h.api.createInstrument(h.factories.Vaporisateur));
    }""")
    await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        const dev = [...h.auBox(4).input.pointerHub.incoming()].map(({box}) => box)[0];
        h.modify(() => {
            dev.cutoff?.setValue(1200);
            dev.resonance?.setValue(0.1);
            dev.attack?.setValue(0.015);
            dev.decay?.setValue(0.25);
            dev.sustain?.setValue(0.3);
            dev.release?.setValue(0.5);
        });
    }""")
    print("\n▌ LEAD — haunting melody")

    r = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const p = h.project;
        const au = h.auBox(4);
        h.modify(() => p.api.createNoteTrack(au));
        const track = [...au.tracks.pointerHub.incoming()].map(({{box}}) => box)[0];
        const regionOpt = h.modify(() => p.api.createNoteRegion({{
            trackBox: track, position: 0, duration: {TOTAL}, loopDuration: {TOTAL},
        }}));
        const region = regionOpt.unwrap("r");
        const phrases = [
            [60, 5.0, 1.0], [62, 6.0, 0.5], [58, 6.5, 0.5], [60, 7.0, 2.0],
            [64, 9.0, 1.0], [62, 10.0, 0.5], [60, 10.5, 1.5],
            [67, 12.0, 0.5], [64, 12.5, 0.5], [62, 13.0, 1.0],
            [60, 14.5, 0.5], [58, 15.0, 1.5],
            [64, 16.0, 0.5], [67, 16.5, 0.5], [69, 17.0, 2.0],
            [69, 21.0, 0.5], [67, 21.5, 0.5], [64, 22.0, 1.0],
            [62, 24.0, 2.0], [60, 26.0, 1.5],
            // Bridge descent
            [50, 29.0, 1.0], [53, 30.0, 0.5], [51, 30.5, 1.5],
            [46, 32.0, 1.0], [43, 33.0, 2.0],
            [57, 34.0, 0.5], [61, 34.5, 0.5], [64, 35.0, 1.0],
            // Chorus 2 peak
            [67, 36.0, 0.5], [69, 36.5, 0.5], [72, 37.0, 2.0],
            [69, 39.0, 1.0], [67, 40.0, 0.5], [64, 40.5, 1.5],
            [67, 42.0, 2.0],
            // Outro dissolve
            [60, 45.0, 2.0], [57, 47.0, 1.0],
        ];
        h.modify(() => {{
            phrases.forEach(([pitch, barPos, beats]) => {{
                p.api.createNoteEvent({{
                    owner: region, pitch,
                    position: Math.floor(barPos * {P}),
                    duration: Math.floor(beats * {P}),
                    velocity: 55 + Math.floor(Math.random() * 25),
                }});
            }});
        }});
        return "lead done";
    }}""")
    print(f"  → {r}")

    await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        const au = h.auBox(4);
        const EF = window.opendaw.EffectFactories;
        h.modify(() => {
            h.api.insertEffect(au.audioEffects, EF.Reverb);
            h.api.insertEffect(au.audioEffects, EF.Delay);
            h.api.insertEffect(au.audioEffects, EF.Waveshaper);
        });
        const rev = h.effectBoxes(au).find(f => f.label?.getValue?.() === "Reverb");
        const del = h.effectBoxes(au).find(f => f.label?.getValue?.() === "Delay");
        h.modify(() => {
            if (rev) { rev.roomSize?.setValue(0.8); }
            if (del) { del.time?.setValue(0.375); del.feedback?.setValue(0.5); del.mix?.setValue(0.45); }
        });
    }""")
    print("  → Reverb + Delay + Waveshaper")

    # ═══ MASTER ═══
    await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        const EF = window.opendaw.EffectFactories;
        const outputAU = h.allAUBoxes().find(au => au.type?.getValue?.() === "output");
        h.modify(() => h.api.insertEffect(outputAU.audioEffects, EF.Maximizer));
        const maxi = h.effectBoxes(outputAU)[0];
        h.modify(() => { maxi.ceiling?.setValue(-0.5); maxi.release?.setValue(0.03); });
    }""")
    print("\n▌ MASTER — Maximizer -0.5dB")

    # ═══ MIX ═══
    await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        h.modify(() => {
            h.auBox(0).volume.setValue(0.78);   // bass
            h.auBox(1).volume.setValue(0.82);   // kick
            h.auBox(2).volume.setValue(0.70);   // snare/hat
            h.auBox(3).volume.setValue(0.40);   // pad
            h.auBox(4).volume.setValue(0.55);   // lead
            h.auBox(3).panning?.setValue?.(-0.15);
            h.auBox(4).panning?.setValue?.(0.15);
        });
    }""")
    print("▌ MIX balanced")

    # ═══ RENDER WITH EXPLICIT RANGE ═══
    print(f"\n{'═'*55}")
    print(f"  RENDERING 48 bars at 80 BPM...")
    print(f"{'═'*55}")

    r = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const p = h.project;
        const OER = window.opendaw.OfflineEngineRenderer;
        const Option = window.opendaw.Option;
        const DOV = window.opendaw.DefaultObservableValue;
        const progress = new DOV(0);
        try {{
            const projectCopy = p.copy();
            // Explicit range: 0 to 48 bars
            const exportConfig = {{range: {{start: 0, end: {TOTAL}}}}};
            const audioData = await OER.start(
                projectCopy,
                Option.wrap(exportConfig),
                progress,
                undefined,
                48000
            );
            const sr = audioData.sampleRate;
            const numCh = audioData.frames.length;
            const numFrames = audioData.frames[0].length;
            const interleaved = new Float32Array(numFrames * numCh);
            for (let i = 0; i < numFrames; i++)
                for (let ch = 0; ch < numCh; ch++)
                    interleaved[i*numCh+ch] = audioData.frames[ch][i];
            const pcm = new Int16Array(interleaved.length);
            for (let i = 0; i < interleaved.length; i++) {{
                const s = Math.max(-1, Math.min(1, interleaved[i]));
                pcm[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
            }}
            const buf = new ArrayBuffer(44 + pcm.buffer.byteLength);
            const v = new DataView(buf);
            const ws = (o, s) => {{ for (let i = 0; i < s.length; i++) v.setUint8(o+i, s.charCodeAt(i)); }};
            ws(0,"RIFF"); v.setUint32(4,36+pcm.buffer.byteLength,true);
            ws(8,"WAVE"); ws(12,"fmt "); v.setUint32(16,16,true);
            v.setUint16(20,1,true); v.setUint16(22,numCh,true);
            v.setUint32(24,sr,true); v.setUint32(28,sr*numCh*2,true);
            v.setUint16(32,numCh*2,true); v.setUint16(34,16,true);
            ws(36,"data"); v.setUint32(40,pcm.buffer.byteLength,true);
            new Uint8Array(buf,44).set(new Uint8Array(pcm.buffer));
            const bytes = new Uint8Array(buf);
            let bin = '';
            const cs = 32768;
            for (let i = 0; i < bytes.length; i += cs) {{
                const ch = bytes.subarray(i, Math.min(i+cs, bytes.length));
                for (let j = 0; j < ch.length; j++) bin += String.fromCharCode(ch[j]);
            }}
            return {{sr, numCh, numFrames, dur: Math.round(numFrames/sr*10)/10, b64: btoa(bin)}};
        }} catch(e) {{ return {{error: e.message, stack: e.stack?.slice(0, 400)}}; }}
    }}""", timeout=600000)

    if isinstance(r, dict) and "b64" in r:
        wav_data = base64.b64decode(r["b64"])
        wav_path = "/home/ameobius/projects/creative-studio/agent-daw/opendaw-mcp/silent_hill_v2.wav"
        with open(wav_path, "wb") as f:
            f.write(wav_data)
        print(f"\n✓ {r['dur']}s — {r['sr']}Hz {r['numCh']}ch — {len(wav_data)//1024}KB")
        import shutil
        try:
            shutil.copy(wav_path, "/mnt/c/Users/nameobius/Desktop/silent_hill_v2.wav")
            print("✓ copied to Desktop")
        except: pass
    elif isinstance(r, dict) and "error" in r:
        print(f"\n✗ {r['error']}")

    await bridge.stop()

if __name__ == "__main__":
    asyncio.run(build())
