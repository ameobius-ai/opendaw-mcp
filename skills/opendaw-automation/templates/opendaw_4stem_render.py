#!/usr/bin/env python3
"""
openDAW 4-stem headless render template.
Based on F42 — the working pipeline that produces real audio.

Prerequisites:
  - Vite dev server running on localhost:5174
  - Stems in headless-daw/public/stems/ (anchor.wav, minus_synced.wav, vocal_synced.wav)
  - opendaw-mcp venv: source ~/projects/creative-studio/agent-daw/opendaw-mcp/venv/bin/activate

Usage:
  python3 opendaw_4stem_render.py

Customize:
  - stems[] array: add/remove stems, set levels
  - outputAu.volume: master output level
  - Revamp EQ: highShelf/highBell on output AU for air
  - De-esser (commented out): Revamp highBell on vocal AUs — use 5.5-7k, max -1.5dB

Output:
  32-bit float WAV, 48kHz, stereo. Saved via download to outpath.
"""
import asyncio
from playwright.async_api import async_playwright
import os, json

download_done = asyncio.Event()

# ═══ CONFIG ═══
STEMS = [
    {'url': '/stems/anchor.wav',        'name': 'anchor',  'level': -7.0},
    {'url': '/stems/minus_synced.wav',   'name': 'minus',   'level': -3.0},
    {'url': '/stems/vocal_synced.wav',   'name': 'vocal',   'level': -2.0},
    {'url': '/stems/vocal_synced.wav',   'name': 'vocal_2', 'level': -5.0},  # doubled, quieter
]
OUTPUT_VOLUME = -3.0       # dB, master output
HIGH_SHELF_FREQ = 12000    # Hz, air boost
HIGH_SHELF_GAIN = 4.0      # dB
HIGH_BELL_FREQ = 16000     # Hz, air boost
HIGH_BELL_GAIN = 2.0       # dB
DE_ESSER = False           # Set True to enable de-esser on vocal AUs
DE_ESSER_FREQ = 5500       # Hz (5.5-7k range, DO NOT go below 5k)
DE_ESSER_GAIN = -1.5       # dB (max -1.5, deeper kills vocal)
OUTPATH = '/tmp/serebro_4stem/serebro_4stem_opendaw_F42.wav'
# ═══ END CONFIG ═══

JS = r'''async () => {
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
        const ef = window.DAW_EffectFactories;

        AW.install('/node_modules/@opendaw/studio-core/dist/processors.js');
        OER.install('/node_modules/@opendaw/studio-core/dist/offline-engine.js?worker_file&type=module');
        const TrackType = { Audio: 2 };

        const stems = STEMS_JSON;
        const deEsser = DE_ESSER_VAL;
        const hsFreq = HS_FREQ, hsGain = HS_GAIN;
        const hbFreq = HB_FREQ, hbGain = HB_GAIN;
        const outVol = OUT_VOL;
        const deFreq = DE_FREQ, deGain = DE_GAIN;

        // Set output volume + Revamp EQ
        const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({box}) => box);
        const outputAu = units.find(u => u.type?.getValue?.() === 'output');
        p.editing.modify(() => {
            outputAu.volume.setValue(outVol);
            const revamp = p.api.insertEffect(outputAu.audioEffects, ef.AudioNamed.Revamp);
            revamp.highShelf.enabled.setValue(true);
            revamp.highShelf.frequency.setValue(hsFreq);
            revamp.highShelf.gain.setValue(hsGain);
            revamp.highBell.enabled.setValue(true);
            revamp.highBell.frequency.setValue(hbFreq);
            revamp.highBell.gain.setValue(hbGain);
        });
        console.log(`Output: vol=${outVol}dB, HS@${hsFreq}+${hsGain}, HB@${hbFreq}+${hbGain}`);

        for (const s of stems) {
            const resp = await fetch(s.url);
            const buf = await resp.arrayBuffer();
            const ab = await ctx.decodeAudioData(buf);
            const fileUuid = UUID.generate();
            const idStr = UUID.toString(fileUuid);
            window.DAW_localAudioBuffers.set(idStr, ab);
            window.DAW_fileNameToAudioBuffer.set(idStr, ab);

            const factory = {
                create: (boxGraph, host, name, icon, _attachment) => TapeDeviceBox.create(boxGraph, UUID.generate(), box => {
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

            // De-esser on vocal AUs (optional)
            if (deEsser && (s.name === 'vocal' || s.name === 'vocal_2')) {
                p.editing.modify(() => {
                    const revamp = p.api.insertEffect(auBox.audioEffects, ef.AudioNamed.Revamp);
                    revamp.highBell.enabled.setValue(true);
                    revamp.highBell.frequency.setValue(deFreq);
                    revamp.highBell.gain.setValue(deGain);
                    console.log(`De-esser on ${s.name}: @${deFreq} ${deGain}dB`);
                });
            }

            const handler = sm.getOrCreate(fileUuid);
            await new Promise((resolve, reject) => {
                handler.subscribe(state => {
                    if (state.type === 'loaded') resolve();
                    else if (state.type === 'error') reject(state.reason);
                });
            });
            console.log(`Loaded ${s.name}: ${ab.duration}s, level=${s.level}dB`);
        }

        // Copy + render
        const projectCopy = p.copy();
        window.DAW_setRenderBoxGraph(projectCopy.boxGraph);
        const copyUnits = [...projectCopy.rootBox.audioUnits.pointerHub.incoming()].map(({box}) => box);
        const copyOutput = copyUnits.find(u => u.type?.getValue?.() === 'output');
        if (copyOutput) projectCopy.editing.modify(() => { copyOutput.volume.setValue(outVol); });

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
    js = (JS
          .replace('STEMS_JSON', json.dumps(STEMS))
          .replace('DE_ESSER_VAL', 'true' if DE_ESSER else 'false')
          .replace('HS_FREQ', str(HIGH_SHELF_FREQ))
          .replace('HS_GAIN', str(HIGH_SHELF_GAIN))
          .replace('HB_FREQ', str(HIGH_BELL_FREQ))
          .replace('HB_GAIN', str(HIGH_BELL_GAIN))
          .replace('OUT_VOL', str(OUTPUT_VOLUME))
          .replace('DE_FREQ', str(DE_ESSER_FREQ))
          .replace('DE_GAIN', str(DE_ESSER_GAIN)))

    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True, args=['--enable-features=SharedArrayBuffer'])
        context = await b.new_context(accept_downloads=True)
        page = await context.new_page()
        page.on('console', lambda m: print(f'{m.type}: {m.text}', flush=True) if m.type in ['log','error','warning'] else None)
        page.on('worker', lambda w: w.on('console', lambda m: print(f'WKR {m.type}: {m.text}', flush=True) if m.type in ['log','error','warning'] else None))

        os.makedirs(os.path.dirname(OUTPATH), exist_ok=True)
        async def handle_download(download):
            try:
                await download.save_as(OUTPATH)
                print(f'Saved: {OUTPATH}', flush=True)
            except Exception as e:
                print(f'Download error: {e}', flush=True)
            finally:
                download_done.set()
        page.on('download', handle_download)

        await page.goto('http://localhost:5174/', timeout=60000)
        await page.wait_for_timeout(8000)

        print(f'Render: {len(STEMS)} stems, out={OUTPUT_VOLUME}dB...', flush=True)
        result = await page.evaluate(js)

        ok = result.get('ok')
        maxS = result.get('maxS')
        print(f'ok={ok} maxS={maxS} nonZero={result.get("nonZero")} dur={result.get("dur")}', flush=True)

        if not ok:
            print(f'FAILED: {result.get("error")}', flush=True)
            if result.get('stack'):
                print(f'Stack: {result["stack"]}', flush=True)

        if ok:
            try:
                await asyncio.wait_for(download_done.wait(), timeout=120)
            except asyncio.TimeoutError:
                print('Download timeout!', flush=True)

        await page.wait_for_timeout(3000)
        await b.close()

asyncio.run(run())
