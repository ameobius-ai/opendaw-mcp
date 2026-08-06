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

# Chromium launch flags tuned for low-RAM / weak machines. openDAW renders
# audio via OfflineAudioContext, so --mute-audio and --disable-gpu do not
# affect exports.
_LOW_MEM_ARGS = [
    "--no-sandbox",
    "--use-fake-ui-for-media-stream",
    "--autoplay-policy=no-user-gesture-required",
    "--disable-dev-shm-usage",  # write to /tmp instead of /dev/shm (Docker default shm: 64 MB)
    "--disable-gpu",  # headless rendering needs no GPU
    "--mute-audio",  # no realtime audio output in headless mode
    "--disable-extensions",
    "--disable-background-networking",
    "--disable-sync",
    "--disable-translate",
    "--disable-features=Translate,OptimizationHints",
    "--no-first-run",
    "--no-default-browser-check",
    "--js-flags=--max-old-space-size=512",  # cap V8 heap; override via OPENDAW_V8_HEAP_MB
]


def _chromium_args() -> list[str]:
    """Build Chromium launch args, with environment overrides.

    OPENDAW_V8_HEAP_MB — V8 heap cap in MB (default: 512)
    OPENDAW_CHROMIUM_ARGS — extra args, space-separated, appended last
    """
    heap_mb = os.environ.get("OPENDAW_V8_HEAP_MB", "512")
    args = [
        a.replace("--max-old-space-size=512", f"--max-old-space-size={heap_mb}")
        for a in _LOW_MEM_ARGS
    ]
    extra = os.environ.get("OPENDAW_CHROMIUM_ARGS", "").split()
    return args + extra


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
            args=_chromium_args(),
        )
        # Allow system chromium via env var
        chrome_path = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "")
        if chrome_path and os.path.exists(chrome_path):
            launch_opts["executable_path"] = chrome_path
        self.browser = await self.playwright.chromium.launch(**launch_opts)
        self.page = await self.browser.new_page(ignore_https_errors=True)
        await self.page.goto(DAW_URL, timeout=15000)
        # Wait until a Project is reachable via any supported host surface and the
        # box/factory/enum globals used by the helper are present. Two hosts are
        # supported: creative-studio headless-daw (window.DAW + deferred
        # DAW_startEngine) and the repo tests/e2e test_host
        # (window.opendaw.service.project + an auto-started engine). We therefore do
        # not hard-require window.DAW or DAW_startEngine here.
        await self.page.wait_for_function(
            "(typeof window.DAW !== 'undefined'"
            " || (window.opendaw && window.opendaw.service && window.opendaw.service.project)"
            " || typeof window.DAW_project !== 'undefined')"
            " && typeof window.DAW_NoteEventBox !== 'undefined'"
            " && typeof window.DAW_InstrumentFactories !== 'undefined'"
            " && typeof window.DAW_UUID !== 'undefined'"
            " && typeof window.DAW_PPQN !== 'undefined'",
            timeout=30000,
        )
        # Inject helper functions into DAW context — eliminates boilerplate in every tool.
        # The Project is exposed differently per host: creative-studio headless-daw
        # publishes it as window.DAW (+ DAW_* globals, engine deferred via
        # DAW_startEngine), while the repo test_host publishes it as
        # window.opendaw.service.project / window.DAW_project (engine auto-started).
        # Render/export tools use OfflineEngineRenderer, so the live engine is not
        # required here.
        await self.page.evaluate(
            """async () => {
            if (window.DAW_HELPERS) return;  // already injected

            // Locate the Project across supported hosts. Read opendaw.service.project
            // before DAW_project, since this bridge overwrites window.DAW_project with
            // the helper object below.
            const p = window.DAW
                || (window.opendaw && window.opendaw.service && window.opendaw.service.project)
                || window.DAW_project;
            if (!p) throw new Error('openDAW project not available (window.DAW / window.opendaw.service.project / window.DAW_project)');
            const InstrumentFactories = window.DAW_InstrumentFactories;
            const H = {
                // Get AU adapter by index (sorted by index field)
                au: (i) => {
                    const aus = p.rootBoxAdapter.audioUnits.adapters();
                    if (i >= aus.length) throw new Error('No AU at ' + i);
                    return aus[i];
                },
                // Get track adapter by AU index + track index
                track: (auIdx, trackIdx) => {
                    const au = H.au(auIdx);
                    const tracks = au.tracks.collection.adapters();
                    if (trackIdx >= tracks.length) throw new Error('No track ' + trackIdx + ' on AU ' + auIdx);
                    return tracks[trackIdx];
                },
                // Get region adapter by AU/track/region index
                region: (auIdx, trackIdx, regIdx) => {
                    const track = H.track(auIdx, trackIdx);
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
                // Instrument factories for api.createInstrument()
                factories: InstrumentFactories,
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
                // Box factory classes (exposed by headless-daw from studio-boxes)
                NoteEventBox: window.DAW_NoteEventBox,
                NoteRegionBox: window.DAW_NoteRegionBox,
                TrackBox: window.DAW_TrackBox,
                // All note-track boxes across every AU (flat, index-sorted per AU)
                noteTracks: () => H.allAUBoxes().flatMap(au => H.noteTrackBoxes(au)),
                // Alias for allAUBoxes (AU boxes sorted by index)
                audioUnitBoxes: () => H.allAUBoxes(),
                // Audio region boxes for an AU (across all its tracks)
                audioRegionBoxes: (au) => H.trackBoxes(au)
                    .flatMap(t => H.regionBoxes(t))
                    .filter(r => r && r.constructor && r.constructor.name === 'AudioRegionBox'),
                // Create a note event in a collection (positional args)
                createNote: (coll, pos, dur, pitch, vel) =>
                    window.DAW_NoteEventBox.create(p.boxGraph, window.DAW_UUID.generate(), (box) => {
                        box.position.setValue(pos);
                        box.duration.setValue(dur);
                        box.pitch.setValue(pitch);
                        box.velocity.setValue(vel);
                        if (coll && coll.events) box.events.refer(coll.events);
                    }),
                // Create a note event from options ({pitch, position, duration, velocity, cent?, chance?})
                createNoteEvent: (coll, opts) =>
                    window.DAW_NoteEventBox.create(p.boxGraph, window.DAW_UUID.generate(), (box) => {
                        box.position.setValue(opts.position);
                        box.duration.setValue(opts.duration);
                        box.pitch.setValue(opts.pitch);
                        box.velocity.setValue(opts.velocity);
                        if (opts.cent !== undefined && box.cent) box.cent.setValue(opts.cent);
                        if (opts.chance !== undefined && box.chance) box.chance.setValue(opts.chance);
                        if (coll && coll.events) box.events.refer(coll.events);
                    }),
            };

            // headless-daw tool code references the helper under four alias names —
            // point them all at the single rich helper object.
            window.DAW_HELPERS = H;
            window.DAW_HeadlessBridgeHelper = H;
            window.DAW_HeadlessBridge = H;
            window.DAW_project = H;
        }"""
        )
        logging.info("DAW helpers injected — engine deferred (DAW_startEngine on demand)")

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
