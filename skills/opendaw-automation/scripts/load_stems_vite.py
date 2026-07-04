#!/usr/bin/env python3
"""
Load audio stems into openDAW via Vite public dir + fetch().
Bypasses the 200KB base64 cap in the MCP server.

Setup:
  1. Copy stems to headless-daw/public/stems/
  2. Start Vite: npx vite dev --port 5174
  3. Run: python3 load_stems_vite.py

What works:
  - fetch() + decodeAudioData() for any file size
  - Creating audio tracks via p.api.createAudioTrack(au)
  - Setting volume/panning on audio units
  - Adding effects (Compressor, StereoTool, etc.)
  - Offline export via AudioOfflineRenderer

What DOES NOT work (as of June 2026):
  - AudioRegionBox placement (box.regions.refer() fails — see references/api-investigation-2026-06.md)
  - Creating new AudioUnitBox (p.api.createAudioUnit doesn't exist)
  - sampleManager.default.load() (default is undefined)

Usage:
  from load_stems_vite import OpenDawSession
  session = OpenDawSession()
  await session.start()
  await session.load_audio('/stems/bass.wav', 'bass')
  await session.create_track_with_region('bass', vol=0, pan=0)  # region placement may fail
  await session.close()
"""
import asyncio
import json
import base64
from playwright.async_api import async_playwright

DAW_URL = "http://localhost:5174"


class OpenDawSession:
    """Playwright session for openDAW automation."""
    
    def __init__(self, headless=True):
        self.headless = headless
        self.pw = None
        self.browser = None
        self.page = None
        self.logs = []
    
    async def start(self):
        self.pw = await async_playwright().start()
        # CRITICAL: --disable-web-security BREAKS SharedArrayBuffer.
        # COOP/COEP headers from vite.config.ts handle cross-origin isolation.
        # Using --disable-web-security sets crossOriginIsolated=false → SAB undefined → DAW panics.
        # Fix (verified June 2026): ONLY --enable-features=SharedArrayBuffer.
        self.browser = await self.pw.chromium.launch(
            headless=self.headless,
            args=['--enable-features=SharedArrayBuffer']
        )
        self.page = await self.browser.new_page()
        self.page.on('console', lambda msg: self.logs.append(f'[{msg.type}] {msg.text}'))
        self.page.on('pageerror', lambda err: self.logs.append(f'[ERROR] {err}'))
        
        await self.page.goto(DAW_URL, timeout=15000)
        await self.page.wait_for_function('typeof window.DAW !== "undefined"', timeout=60000)
        await self.page.wait_for_function('typeof window.DAW_EffectFactories !== "undefined"', timeout=10000)
    
    async def eval_js(self, js):
        """Evaluate JS in DAW context. Returns dict or None."""
        try:
            return await self.page.evaluate(js)
        except Exception as e:
            return {"error": str(e)}
    
    async def set_bpm(self, bpm):
        return await self.eval_js(f"() => {{ window.DAW.editing.modify(() => window.DAW.api.setBpm({bpm})); return window.DAW.timelineBox?.bpm?.getValue?.(); }}")
    
    async def load_audio(self, url_path, name):
        """Load audio file via fetch + decodeAudioData. Returns sample ID or error."""
        result = await self.eval_js(f"""async () => {{
            try {{
                const resp = await fetch('{url_path}');
                if (!resp.ok) return {{ error: 'HTTP ' + resp.status }};
                const buf = await resp.arrayBuffer();
                const ctx = window.DAW_audioContext;
                const audioBuffer = await ctx.decodeAudioData(buf);
                const id = window.DAW_UUID.generate();
                window.DAW_localAudioBuffers.set(id, audioBuffer);
                return {{ id, name: '{name}', duration: audioBuffer.duration, sr: audioBuffer.sampleRate, ch: audioBuffer.numberOfChannels }};
            }} catch(e) {{
                return {{ error: e.message }};
            }}
        }}""")
        return result
    
    async def get_units(self):
        """List all audio units."""
        return await self.eval_js("""() => {
            const p = window.DAW;
            return [...p.rootBox.audioUnits.pointerHub.incoming()].map(({box}, i) => ({
                index: i,
                name: box.name?.getValue?.() || 'unnamed',
                volume: box.volume?.getValue?.() ?? 0,
                panning: box.panning?.getValue?.() ?? 0,
                numTracks: [...box.tracks.pointerHub.incoming()].length,
                effects: [...box.audioEffects.pointerHub.incoming()].map(({box: efx}) => efx.constructor?.name || 'Unknown'),
            }));
        }""")
    
    async def set_unit_volume(self, unit_index, vol_db):
        return await self.eval_js(f"""() => {{
            const p = window.DAW;
            const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box);
            if ({unit_index} >= units.length) return {{ error: 'No unit at index {unit_index}' }};
            p.editing.modify(() => units[{unit_index}].volume.setValue({vol_db}));
            return {{ vol: units[{unit_index}].volume?.getValue?.() }};
        }}""")
    
    async def set_unit_panning(self, unit_index, pan):
        return await self.eval_js(f"""() => {{
            const p = window.DAW;
            const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box);
            if ({unit_index} >= units.length) return {{ error: 'No unit at index {unit_index}' }};
            p.editing.modify(() => units[{unit_index}].panning.setValue({pan}));
            return {{ pan: units[{unit_index}].panning?.getValue?.() }};
        }}""")
    
    async def create_track(self, unit_index=0):
        """Create audio track on unit. Returns track info."""
        return await self.eval_js(f"""() => {{
            const p = window.DAW;
            const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box);
            const au = units[{unit_index}];
            if (!au) return {{ error: 'No unit at index {unit_index}' }};
            let trackBox;
            p.editing.modify(() => {{ trackBox = p.api.createAudioTrack(au); }});
            return {{ success: !!trackBox, type: trackBox?.type?.getValue?.() }};
        }}""")
    
    async def add_effect(self, unit_index, effect_name):
        """Add audio effect to unit's effect chain."""
        valid = {"Compressor","Crusher","DattorroReverb","Delay","Fold","Gate","Maximizer","NeuralAmp","Reverb","Revamp","StereoTool","Tidal","Vocoder","Waveshaper","Werkstatt"}
        if effect_name not in valid:
            return {"error": f"Unknown effect: {effect_name}. Valid: {sorted(valid)}"}
        return await self.eval_js(f"""() => {{
            const p = window.DAW;
            const ef = window.DAW_EffectFactories;
            const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box);
            const au = units[{unit_index}];
            if (!au) return {{ error: 'No unit at index {unit_index}' }};
            let effectBox;
            p.editing.modify(() => {{ effectBox = p.api.insertEffect(au.audioEffects, ef.AudioNamed['{effect_name}']); }});
            return {{ success: !!effectBox, effect: '{effect_name}' }};
        }}""")
    
    async def export_mix(self, sample_rate=48000):
        """Offline render and return as base64 WAV."""
        result = await self.eval_js(f"""async () => {{
            try {{
                const p = window.DAW;
                const Renderer = window.DAW_AudioOfflineRenderer;
                const WavFile = window.DAW_WavFile;
                const Option = window.DAW_Option;
                const audioBuffer = await Renderer.start(p, Option.None, (v)=>{{}}, undefined, {{ sample_rate: {sample_rate} }});
                const wavArrayBuffer = WavFile.encodeFloats(audioBuffer);
                const bytes = new Uint8Array(wavArrayBuffer);
                const chunks = [];
                const chunkSize = 65536;
                for (let i = 0; i < bytes.length; i += chunkSize) {{
                    const chunk = bytes.slice(i, i + chunkSize);
                    chunks.push(String.fromCharCode.apply(null, chunk));
                }}
                return {{ b64: chunks.join(''), size: bytes.length, duration: audioBuffer.duration, sr: audioBuffer.sampleRate, ch: audioBuffer.numberOfChannels }};
            }} catch(e) {{
                return {{ error: e.message }};
            }}
        }}""")
        if isinstance(result, dict) and result.get('b64'):
            wav_bytes = base64.b64decode(result['b64'])
            return wav_bytes, result
        return None, result
    
    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.pw:
            await self.pw.stop()
