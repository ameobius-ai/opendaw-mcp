#!/usr/bin/env python3
"""
openDAW headless stack smoke test.
Run with the opendaw-mcp venv python:
  /path/to/opendaw-mcp/venv/bin/python scripts/smoke_test.py

Requires: Vite dev server running on :5174, Playwright chromium installed.
"""
import asyncio
import sys
from playwright.async_api import async_playwright

PASS = 0
FAIL = 0

def check(label, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✓ {label}")
    else:
        FAIL += 1
        print(f"  ✗ {label} — {detail}")

async def main():
    global PASS, FAIL
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(
        headless=True,
        args=["--disable-web-security", "--enable-features=SharedArrayBuffer"]
    )
    page = await browser.new_page()
    errors = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)

    print("Connecting to http://localhost:5174 ...")
    try:
        await page.goto("http://localhost:5174", timeout=15000)
    except Exception as e:
        print(f"FATAL: Cannot connect to Vite — {e}")
        sys.exit(1)

    try:
        await page.wait_for_function("typeof window.DAW !== 'undefined'", timeout=30000)
    except Exception:
        print("FATAL: window.DAW never appeared (engine boot failed)")
        sys.exit(1)

    print("\n=== Core Objects ===")
    core = await page.evaluate("""() => ({
        engine: typeof window.DAW.engine,
        api: typeof window.DAW.api,
        editing: typeof window.DAW.editing,
        boxGraph: typeof window.DAW.boxGraph,
        mixer: typeof window.DAW.mixer,
        effects: typeof window.DAW_EffectFactories,
        primaryAU: typeof window.DAW.primaryAudioUnitBox,
    })""")
    for k, v in core.items():
        check(k, v == "object", f"got {v}")

    print("\n=== Engine Getters ===")
    eng = await page.evaluate("""() => ({
        sampleRate: window.DAW.engine.sampleRate,
        isPlaying: typeof window.DAW.engine.isPlaying,
        position: typeof window.DAW.engine.position,
    })""")
    check("sampleRate=44100", eng["sampleRate"] == 44100, f"got {eng['sampleRate']}")
    check("isPlaying accessible", eng["isPlaying"] == "object")

    print("\n=== setBpm ===")
    bpm = await page.evaluate("""() => { try {
        window.DAW.editing.modify(() => window.DAW.api.setBpm(140));
        return {ok: true};
    } catch(e) { return {error: e.message}; } }""")
    check("setBpm(140)", bpm.get("ok"), bpm.get("error", ""))

    print("\n=== createAudioTrack ===")
    track = await page.evaluate("""() => { try {
        let t; window.DAW.editing.modify(() => {
            t = window.DAW.api.createAudioTrack(window.DAW.primaryAudioUnitBox);
        }); return {ok: !!t};
    } catch(e) { return {error: e.message}; } }""")
    check("createAudioTrack", track.get("ok"), track.get("error", ""))

    print("\n=== insertEffect (Compressor) ===")
    fx = await page.evaluate("""() => { try {
        let b; window.DAW.editing.modify(() => {
            b = window.DAW.api.insertEffect(
                window.DAW.primaryAudioUnitBox.audioEffects,
                window.DAW_EffectFactories.AudioNamed.Compressor
            );
        }); return {ok: !!b};
    } catch(e) { return {error: e.message}; } }""")
    check("insertEffect(Compressor)", fx.get("ok"), fx.get("error", ""))

    print("\n=== Volume ===")
    vol = await page.evaluate("""() => { try {
        window.DAW.editing.modify(() => {
            window.DAW.primaryAudioUnitBox.volume.setValue(-6.0);
        }); return {ok: true};
    } catch(e) { return {error: e.message}; } }""")
    check("volume.setValue(-6)", vol.get("ok"), vol.get("error", ""))

    print("\n=== Play/Stop ===")
    ps = await page.evaluate("""async () => { try {
        window.DAW.engine.play();
        await new Promise(r => setTimeout(r, 200));
        window.DAW.engine.stop();
        return {ok: true};
    } catch(e) { return {error: e.message}; } }""")
    check("play+stop", ps.get("ok"), ps.get("error", ""))

    print("\n=== Effects Catalog ===")
    catalog = await page.evaluate("""() => ({
        audio: Object.keys(window.DAW_EffectFactories.AudioNamed).length,
        midi: Object.keys(window.DAW_EffectFactories.MidiNamed).length,
    })""")
    check(f"AudioNamed={catalog['audio']} effects", catalog["audio"] >= 15)
    check(f"MidiNamed={catalog['midi']} effects", catalog["midi"] >= 5)

    await browser.close()
    await pw.stop()

    print(f"\n{'='*40}")
    print(f"  {PASS} passed, {FAIL} failed")
    if errors:
        print(f"  Console errors: {errors[:3]}")
    sys.exit(1 if FAIL else 0)

asyncio.run(main())
