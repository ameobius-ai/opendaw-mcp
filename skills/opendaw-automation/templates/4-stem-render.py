#!/usr/bin/env python3
"""
4-stem openDAW render template — anchor + minus + vocal + vocal_doubled.

Workflow:
1. Copy stems to headless-daw/public/stems/ (Vite serves at /stems/)
2. Start Vite: cd headless-daw && npx vite --host (port 5174)
3. Run: python3 templates/4-stem-render.py
4. Output: /tmp/render_output.wav (32-bit float, 48kHz, stereo)

Single-variable iteration: change ONE level per render, user analyzes, repeat.
"""

import asyncio
from playwright.async_api import async_playwright
import os

# ─── Mix Parameters (edit these for each iteration) ──────────────────────────
STEMS = [
    {"url": "/stems/anchor.wav",       "name": "anchor",  "level": -4.0},  # bass foundation
    {"url": "/stems/minus_synced.wav", "name": "minus",   "level": -3.0},  # instrumental minus
    {"url": "/stems/vocal_synced.wav", "name": "vocal",   "level": -2.0},  # primary vocal
    {"url": "/stems/vocal_synced.wav", "name": "vocal_2", "level": -5.0},  # doubled vocal (quieter)
]
OUTPUT_LEVEL = -3.0   # output AU headroom in dB
OUTPUT_PATH = "/tmp/render_output.wav"
# ─────────────────────────────────────────────────────────────────────────────

JS_TEMPLATE = r'''async () => {
    try {
        const p = window.DAW;
        const UUID = window.DAW_UUID;
        const AudioFileBox = window.DAW_AudioFileBox;
        const ctx = window.DAW_audioContext;
        const core = await import('/node_modules/.vite/deps/@opendaw_studio-core.js');
        const OER = core.OfflineEngineRenderer;
        const AW = core.AudioWorklets;
        const Option = window.DAW_Option;
        const WavFile = window.DAW_WavFile;
        const sm = window.DAW_sampleManager;
        const boxes = await import('/node_modules/.vite/deps/@opendaw_studio-boxes.js');
        const TapeDeviceBox = boxes.TapeDeviceBox;

        AW.install('/node_modules/@opendaw/studio-core/dist/processors.js');
        OER.install('/node_modules/@opendaw/studio-core/dist/offline-engine.js?worker_file&type=module');
        const TrackType = { Audio: 2 };

        const stems = STEM_DATA;

        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({box}) => box);
        const outputAu = units.find(u => u.type?.getValue?.() === 'output');
        p.editing.modify(() => { outputAu.volume.setValue(OUTPUT_LVL); });

        for (const s of stems) {
            const resp = await fetch(s.url);
            const buf = await resp.arrayBuffer();
            const ab = await ctx.decodeAudioData(buf);
            const fileUuid = UUID.generate();
            const idStr = UUID.toString(fileUuid);
            window.DAW_localAudioBuffers.set(idStr, ab);
            window.DAW_fileNameToAudioBuffer.set(idStr, ab);

            const factory = {
                create: (boxGraph, host, name, icon, _att) => TapeDeviceBox.create(boxGraph, UUID.generate(), box => {
                    box.label.setValue(name);
                    box.host.refer(host);
                }),
                defaultIcon: 'tape',
                defaultName: s.name,
                trackType: TrackType.Audio
            };

            let auBox, trackBox;
            p.editing.modify(() => {
                const result = p.api.createInstrument(factory, { name: s.name });
                auBox = result.audioUnitBox;
                trackBox = result.trackBox;
                auBox.volume.setValue(s.level);

                const afb = AudioFileBox.create(p.boxGraph, fileUuid, (box) => {
                    box.fileName.setValue(idStr);
                    box.startInSeconds.setValue(0);
                    box.endInSeconds.setValue(ab.duration);
                });
                p.api.createNotStretchedRegion({
                    boxGraph: p.boxGraph, targetTrack: trackBox,
                    audioFileBox: afb,
                    sample: { name: idStr, duration: ab.duration, bpm: 0 },
                    position: 0, name: s.name
                });
            });

            const handler = sm.getOrCreate(fileUuid);
            await new Promise((resolve, reject) => {
                handler.subscribe(state => {
                    if (state.type === 'loaded') resolve();
                    else if (state.type === 'error') reject(state.reason);
                });
            });
            console.log(`Loaded ${s.name}: ${ab.duration}s, level=${s.level}dB`);
        }

        const projectCopy = p.copy();
        window.DAW_setRenderBoxGraph(projectCopy.boxGraph);

        const copyUnits = [...projectCopy.rootBox.audioUnits.pointerHub.incoming()].map(({box}) => box);
        const copyOutput = copyUnits.find(u => u.type?.getValue?.() === 'output');
        if (copyOutput) projectCopy.editing.modify(() => { copyOutput.volume.setValue(OUTPUT_LVL); });

        const abortController = new AbortController();
        const progress = { setValue: (v) => { if (v > 0 && v < 1 && v % 0.1 < 0.01) console.log('progress:', v.toFixed(2)); } };

        console.log('Starting render...');
        const audioData = await Promise.race([
            OER.start(projectCopy, Option.None, progress, abortController.signal),
            new Promise((_, reject) => setTimeout(() => { abortController.abort(); reject(new Error('TIMEOUT')); }, 180000))
        ]);

        let maxS = 0, nonZero = 0;
        if (audioData.frames && Array.isArray(audioData.frames)) {
            const c0 = audioData.frames[0];
            for (let i = 0; i < c0.length; i++) {
                const a = Math.abs(c0[i]);
                if (a > maxS) maxS = a;
                if (a > 0.0001) nonZero++;
            }
        }

        console.log(`maxS=${maxS} nonZero=${nonZero} frames=${audioData.numberOfFrames}`);
        if (maxS < 0.001) return { ok: false, error: 'silence', frames: audioData.numberOfFrames };
        if (maxS > 1.0) console.log('WARNING: clipping detected (maxS > 1.0)');

        const wavArrayBuffer = WavFile.encodeFloats(audioData);
        const blob = new Blob([wavArrayBuffer], { type: 'audio/wav' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'render_output.wav';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        return { ok: true, maxS, nonZero, dur: audioData.numberOfFrames / audioData.sampleRate, frames: audioData.numberOfFrames };
    } catch(e) {
        return { ok: false, error: e.message, stack: (e.stack||'').substring(0, 800) };
    }
}'''


async def run():
    import json
    js = JS_TEMPLATE.replace("STEM_DATA", json.dumps(STEMS)).replace("OUTPUT_LVL", str(OUTPUT_LEVEL))

    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True, args=['--enable-features=SharedArrayBuffer'])
        context = await b.new_context(accept_downloads=True)
        page = await context.new_page()
        page.on('console', lambda m: print(f'{m.type}: {m.text}', flush=True) if m.type in ['log', 'error', 'warning'] else None)
        page.on('worker', lambda w: w.on('console', lambda m: print(f'WKR {m.type}: {m.text}', flush=True) if m.type in ['log', 'error', 'warning'] else None))

        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        async def handle_download(download):
            await download.save_as(OUTPUT_PATH)
            print(f'Saved: {OUTPUT_PATH}', flush=True)
        page.on('download', handle_download)

        await page.goto('http://localhost:5174/', timeout=60000)
        await page.wait_for_timeout(8000)

        levels_str = ", ".join(f"{s['name']}={s['level']}" for s in STEMS)
        print(f'Render: {levels_str}, output={OUTPUT_LEVEL}dB', flush=True)
        result = await page.evaluate(js)

        ok = result.get('ok')
        maxS = result.get('maxS')
        print(f'ok={ok} maxS={maxS} dur={result.get("dur")}s', flush=True)

        if not ok:
            print(f'FAILED: {result.get("error")}', flush=True)
            if result.get('stack'):
                print(f'Stack: {result["stack"]}', flush=True)
        else:
            print(f'RENDER OK! maxS={maxS}', flush=True)
            await page.wait_for_timeout(5000)

        await b.close()


if __name__ == '__main__':
    asyncio.run(run())
