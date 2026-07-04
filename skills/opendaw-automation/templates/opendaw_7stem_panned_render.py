#!/usr/bin/env python3
"""
openDAW 7-stem headless render with NATIVE panning + per-stem effects + persistent context fix.
All audio processing (levels, pan, EQ, effects) happens INSIDE openDAW. No ffmpeg.

VERIFIED effects in OFFLINE render (July 2026, code-audited + Glass.wav tested):
  - DattorroReverb: ✅ WORKS (plate reverb on vocals, wet in dB)
  - Waveshaper: ✅ WORKS (hardclip on bass: inputGain > 0dB needed. tanh on other = sand on sax, avoid)
  - Compressor: ✅ WORKS (sidechain drums→bass: p.boxGraph.registerEdge. ProcessPhase bug = first block only, inaudible)
  - Revamp on MASTER output: ✅ WORKS (highShelf/highBell EQ)
  - Delay: ✅ WORKS (needs proper sync fraction + wet/dry)
  - Tidal: ✅ WORKS (audio loop unconditional)

Stems config includes 'pan' key: -1.0 (full left) to +1.0 (full right), 0.0 = center.
Stems config optionally includes 'effects' array with types: DattorroReverb, Waveshaper, Compressor.

Sidechain: add {'type': 'Compressor', 'params': {..., 'sidechain': 'drums'}} to bass effects.
The script connects the named source AU's output to the compressor's sideChain input
AFTER all stems are loaded, using p.boxGraph.registerEdge.

Prerequisites:
  - Vite running on localhost:5174 (npx vite --port 5174 --host)
  - opendaw-mcp venv: ~/projects/creative-studio/agent-daw/opendaw-mcp/venv/
  - Stems in headless-daw/public/stems_<name>/
  - Storage quota fix: launch_persistent_context with fresh tempfile profile each run

Usage: edit CONFIG section, then: python3 this_script.py
"""
import asyncio
from playwright.async_api import async_playwright
import os, json

download_done = asyncio.Event()

# ═══ CONFIG — edit these values for your mix ═══
STEMS = [
    {'url': '/stems_glass/anchor.wav',      'name': 'anchor',    'level': -10.0, 'pan': 0.0},
    {'url': '/stems_glass/drums.wav',       'name': 'drums',     'level': -1.0,  'pan': 0.0},
    {'url': '/stems_glass/bass.wav',        'name': 'bass',      'level': -3.0,  'pan': 0.0, 'effects': [
        {'type': 'Waveshaper', 'params': {'equation': 'hardclip', 'inputGain': 6.0, 'outputGain': 0.0, 'mix': 0.6}},
        {'type': 'Compressor', 'params': {'threshold': -20, 'ratio': 4, 'attack': 5, 'release': 80, 'sidechain': 'drums'}},
    ]},
    {'url': '/stems_glass/vocals_pf.wav',   'name': 'vocal_L',   'level': -5.0,  'pan': -0.7, 'effects': [
        {'type': 'DattorroReverb', 'params': {'preDelay': 20, 'bandwidth': 0.8, 'decay': 0.7, 'damping': 0.2, 'wet': -10, 'dry': 0}},
    ]},
    {'url': '/stems_glass/vocals_bs6.wav',  'name': 'vocal_R',   'level': -5.0,  'pan': 0.7, 'effects': [
        {'type': 'DattorroReverb', 'params': {'preDelay': 20, 'bandwidth': 0.8, 'decay': 0.7, 'damping': 0.2, 'wet': -10, 'dry': 0}},
    ]},
    {'url': '/stems_glass/other.wav',       'name': 'other_L',   'level': -4.0,  'pan': -0.85},
    {'url': '/stems_glass/other.wav',       'name': 'other_R',   'level': -4.0,  'pan': 0.85},
]
OUTPUT_VOLUME = -3.0
HIGH_SHELF_FREQ = 12000
HIGH_SHELF_GAIN = 10.0
HIGH_BELL_FREQ = 16000
HIGH_BELL_GAIN = 3.0
OUTPATH = '/mnt/c/Users/admin/Downloads/Glass/Glass_opendaw.wav'
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
        const hsFreq = HS_FREQ, hsGain = HS_GAIN;
        const hbFreq = HB_FREQ, hbGain = HB_GAIN;
        const outVol = OUT_VOL;

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
                if (s.pan !== undefined && s.pan !== 0) {
                    auBox.panning.setValue(s.pan);
                }

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

            // Apply per-stem effects AFTER sampleManager loading completes
            if (s.effects && s.effects.length > 0) {
                p.editing.modify(() => {
                    for (const fx of s.effects) {
                        if (fx.type === 'DattorroReverb') {
                            const rev = p.api.insertEffect(auBox.audioEffects, ef.AudioNamed.DattorroReverb);
                            const pr = fx.params;
                            if (pr.preDelay !== undefined) rev.preDelay.setValue(pr.preDelay);
                            if (pr.bandwidth !== undefined) rev.bandwidth.setValue(pr.bandwidth);
                            if (pr.decay !== undefined) rev.decay.setValue(pr.decay);
                            if (pr.damping !== undefined) rev.damping.setValue(pr.damping);
                            if (pr.wet !== undefined) rev.wet.setValue(pr.wet);
                            if (pr.dry !== undefined) rev.dry.setValue(pr.dry);
                        }
                        else if (fx.type === 'Waveshaper') {
                            const ws = p.api.insertEffect(auBox.audioEffects, ef.AudioNamed.Waveshaper);
                            const pr = fx.params;
                            if (pr.equation !== undefined) ws.equation.setValue(pr.equation);
                            if (pr.inputGain !== undefined) ws.inputGain.setValue(pr.inputGain);
                            if (pr.outputGain !== undefined) ws.outputGain.setValue(pr.outputGain);
                            if (pr.mix !== undefined) ws.mix.setValue(pr.mix);
                        }
                        else if (fx.type === 'Compressor') {
                            const comp = p.api.insertEffect(auBox.audioEffects, ef.AudioNamed.Compressor);
                            const pr = fx.params;
                            if (pr.threshold !== undefined) comp.threshold.setValue(pr.threshold);
                            if (pr.ratio !== undefined) comp.ratio.setValue(pr.ratio);
                            if (pr.attack !== undefined) comp.attack.setValue(pr.attack);
                            if (pr.release !== undefined) comp.release.setValue(pr.release);
                            // sidechain: store for later connection
                            if (pr.sidechain) {
                                window._sidechain_targets = window._sidechain_targets || [];
                                window._sidechain_targets.push({compressorBox: comp, sourceName: pr.sidechain});
                            }
                        }
                    }
                });
            }
        }

        // Connect sidechains after all stems loaded
        const scTargets = window._sidechain_targets || [];
        for (const sc of scTargets) {
            const allUnits = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({box}) => box);
            const sourceAu = allUnits.find(u => {
                try { return u.label?.getValue?.() === sc.sourceName; } catch(e) { return false; }
            });
            if (sourceAu) {
                p.editing.modify(() => {
                    try {
                        p.boxGraph.registerEdge(sourceAu.audioEffects.output, sc.compressorBox.sideChain);
                    } catch(e) {
                        console.log('sidechain connect error: ' + e.message);
                    }
                });
                console.log('sidechain: ' + sc.sourceName + ' -> compressor');
            }
        }

        const projectCopy = p.copy();
        const copyUnits = [...projectCopy.rootBox.audioUnits.pointerHub.incoming()].map(({box}) => box);
        const copyOutput = copyUnits.find(u => u.type?.getValue?.() === 'output');
        if (copyOutput) projectCopy.editing.modify(() => { copyOutput.volume.setValue(outVol); });

        const abortController = new AbortController();
        const progress = { setValue: (v) => {} };

        const audioData = await Promise.race([
            OER.start(projectCopy, Option.None, progress, abortController.signal),
            new Promise((_, reject) => setTimeout(() => { abortController.abort(); reject(new Error('TIMEOUT')); }, 300000))
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
        return { ok: false, error: String(e), message: e.message, stack: (e.stack||'').substring(0, 1200) };
    }
}'''


async def run():
    js = (JS
          .replace('STEMS_JSON', json.dumps(STEMS))
          .replace('HS_FREQ', str(HIGH_SHELF_FREQ))
          .replace('HS_GAIN', str(HIGH_SHELF_GAIN))
          .replace('HB_FREQ', str(HIGH_BELL_FREQ))
          .replace('HB_GAIN', str(HIGH_BELL_GAIN))
          .replace('OUT_VOL', str(OUTPUT_VOLUME)))

    async with async_playwright() as p:
        # Fresh user-data-dir each run to avoid IndexedDB quota buildup
        import tempfile, shutil
        tmp_profile = tempfile.mkdtemp(prefix='opendaw_profile_')
        context = await p.chromium.launch_persistent_context(
            tmp_profile,
            headless=True,
            args=[
                '--enable-features=SharedArrayBuffer',
                '--unlimited-storage',
                '--disable-site-isolation-trials',
                '--disk-cache-size=1',
                '--media-cache-size=1',
                '--disable-application-cache',
            ],
            accept_downloads=True,
        )
        page = context.pages[0] if context.pages else await context.new_page()

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

        result = await page.evaluate(js)

        ok = result.get('ok') if result else None
        maxS = result.get('maxS') if result else None
        print(f'ok={ok} maxS={maxS} nonZero={result.get("nonZero") if result else None} dur={result.get("dur") if result else None}', flush=True)

        if not ok:
            print(f'FAILED: {result.get("error") if result else "result is None"}', flush=True)
            if result and result.get('stack'):
                print(f'Stack: {result["stack"]}', flush=True)
            if result and result.get('message'):
                print(f'Message: {result["message"]}', flush=True)

        if ok:
            try:
                await asyncio.wait_for(download_done.wait(), timeout=120)
            except asyncio.TimeoutError:
                print('Download timeout!', flush=True)

        await page.wait_for_timeout(3000)
        try:
            await context.close()
        except Exception:
            pass
        try:
            shutil.rmtree(tmp_profile, ignore_errors=True)
        except Exception:
            pass

asyncio.run(run())
