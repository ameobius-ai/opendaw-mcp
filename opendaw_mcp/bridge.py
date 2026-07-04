"""
Playwright bridge to a headless openDAW instance.

Manages browser lifecycle, page navigation, and JS evaluation in the
DAW's V8 context where the project model lives.
"""

import logging
import os

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

DAW_URL = os.environ.get("OPENDAW_URL", "http://localhost:5174")


class HeadlessDawBridge:
    """Playwright bridge to headless openDAW."""

    def __init__(self):
        self.page = None
        self.playwright = None
        self.browser = None

    async def start(self):
        env = dict(os.environ)
        node_dir = os.environ.get("NODE_BIN_DIR", "")
        if node_dir:
            env["PATH"] = node_dir + ":" + env.get("PATH", "")
        self.playwright = await async_playwright().start()
        launch_opts = dict(
            headless=True,
            args=[
                "--use-fake-ui-for-media-stream",
                "--autoplay-policy=no-user-gesture-required",
            ],
        )
        # Allow system chromium via env var
        chrome_path = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "")
        if chrome_path and os.path.exists(chrome_path):
            launch_opts["executable_path"] = chrome_path
        self.browser = await self.playwright.chromium.launch(**launch_opts)
        self.page = await self.browser.new_page()
        await self.page.goto(DAW_URL, timeout=15000)
        await self.page.wait_for_function("typeof window.DAW !== 'undefined'", timeout=30000)
        await self.page.wait_for_function(
            "typeof window.DAW_InstrumentFactories !== 'undefined'", timeout=30000
        )
        # Inject helper functions into DAW context — eliminates boilerplate in every tool
        await self.page.evaluate(
            """() => {
            if (window.DAW_HELPERS) return;  // already injected
            const p = window.DAW;
            window.DAW_HELPERS = {
                // Get AU adapter by index (sorted by index field)
                au: (i) => {
                    const aus = p.rootBoxAdapter.audioUnits.adapters();
                    if (i >= aus.length) throw new Error('No AU at ' + i);
                    return aus[i];
                },
                // Get track adapter by AU index + track index
                track: (auIdx, trackIdx) => {
                    const au = window.DAW_HELPERS.au(auIdx);
                    const tracks = au.tracks.collection.adapters();
                    if (trackIdx >= tracks.length) throw new Error('No track ' + trackIdx + ' on AU ' + auIdx);
                    return tracks[trackIdx];
                },
                // Get region adapter by AU/track/region index
                region: (auIdx, trackIdx, regIdx) => {
                    const track = window.DAW_HELPERS.track(auIdx, trackIdx);
                    const regions = track.regions.collection.asArray();
                    if (regIdx >= regions.length) throw new Error('No region ' + regIdx);
                    return regions[regIdx];
                },
                // Get AU box by index (sorted by index field) — for box-level access
                auBox: (i) => {
                    const aus = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({box}) => box)
                        .sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
                    if (i >= aus.length) throw new Error('No AU at ' + i);
                    return aus[i];
                },
                // Get all AU boxes sorted
                allAUBoxes: () => [...p.rootBox.audioUnits.pointerHub.incoming()].map(({box}) => box)
                    .sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0)),
                // Get effect boxes for an AU (sorted by index)
                effectBoxes: (au) => [...au.audioEffects.pointerHub.incoming()].map(({box}) => box)
                    .sort((a, b) => a.index.getValue() - b.index.getValue()),
                // Get MIDI effect boxes for an AU (sorted by index)
                midiEffectBoxes: (au) => [...au.midiEffects.pointerHub.incoming()].map(({box}) => box)
                    .sort((a, b) => a.index.getValue() - b.index.getValue()),
                // Get track boxes for an AU (sorted by index)
                trackBoxes: (au) => [...au.tracks.pointerHub.incoming()].map(({box}) => box)
                    .sort((a, b) => a.index.getValue() - b.index.getValue()),
                // Get region boxes for a track (unsorted, insertion order)
                regionBoxes: (track) => [...track.regions.pointerHub.incoming()].map(({box}) => box),
                // Get event boxes from a collection (note events, signature events)
                eventBoxes: (coll) => [...coll.events.pointerHub.incoming()].map(({box}) => box),
                // Get input device boxes for an AU (instruments, effects)
                inputBoxes: (au) => [...au.input.pointerHub.incoming()].map(({box}) => box),
                // Get marker boxes from a marker track
                markerBoxes: (mt) => [...mt.markers.pointerHub.incoming()].map(({box}) => box),
                // Get aux send boxes for an AU (sorted by index)
                sendBoxes: (au) => [...au.auxSends.pointerHub.incoming()].map(({box}) => box)
                    .sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0)),
                // Get all audio bus boxes
                busBoxes: () => [...p.rootBox.audioBusses.pointerHub.incoming()].map(({box}) => box),
                // Get sample boxes from a Playfield instrument
                sampleBoxes: (pf) => [...pf.samples.pointerHub.incoming()].map(({box}) => box),
                // Get note track boxes for an AU (type === 1, sorted by index)
                noteTrackBoxes: (au) => [...au.tracks.pointerHub.incoming()].map(({box}) => box)
                    .sort((a, b) => a.index.getValue() - b.index.getValue())
                    .filter(box => box.type?.getValue?.() === 1),
                // Get clip boxes from a track
                clipBoxes: (track) => [...track.clips.pointerHub.incoming()].map(({box}) => box),
                // Get all clips from rootBox
                rootClipBoxes: () => [...p.rootBox.clips.pointerHub.incoming()].map(({box}) => box),
                // Get script device parameters
                scriptParams: (device) => [...device.parameters.pointerHub.incoming()].map(({box}) => box),
                // Get script device samples
                scriptSamples: (device) => [...device.samples.pointerHub.incoming()].map(({box}) => box),
                // Get effect boxes from a chain field (audio or midi)
                chainBoxes: (field) => [...field.pointerHub.incoming()].map(({box}) => box),
                // Get all AU adapters sorted
                allAUs: () => p.rootBoxAdapter.audioUnits.adapters(),
                // Find instrument AU (first non-output, non-bus)
                instrumentAU: () => {
                    const aus = p.rootBoxAdapter.audioUnits.adapters();
                    const inst = aus.find(a => a.isInstrument);
                    if (!inst) throw new Error('No instrument AU found');
                    return inst;
                },
                // Safe evaluate — wraps in editing.modify
                modify: (fn) => p.editing.modify(fn),
                // Project shortcuts
                project: p,
                api: p.api,
                boxGraph: p.boxGraph,
                editing: p.editing,
                tempoMap: p.tempoMap,
                audioUnitFreeze: p.audioUnitFreeze,
                rootBoxAdapter: p.rootBoxAdapter,
                rootBox: p.rootBox,
                timelineBox: p.timelineBox,
                engine: p.engine,
                primaryAudioUnitBox: p.primaryAudioUnitBox,
                primaryAudioBusBox: p.primaryAudioBusBox,
                uuid: window.DAW_UUID,
                ppqn: window.DAW_PPQN,
            };
        }"""
        )
        logging.info("DAW engine ready!")

    async def evaluate(self, script, timeout=30000):
        """Execute JS in the DAW context. All errors caught and returned."""
        if self.page is None:
            await self.start()
        wrapped = f"""async () => {{ try {{ return await ({script})(); }} catch (e) {{ return {{ __error: e.message, __stack: e.stack }}; }} }}"""
        self.page.set_default_timeout(timeout)
        result = await self.page.evaluate(wrapped)
        if isinstance(result, dict) and "__error" in result:
            return {"error": result["__error"], "stack": result.get("__stack", "")}
        return result

    async def stop(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self.playwright = None
        self.page = None
        self.browser = None
