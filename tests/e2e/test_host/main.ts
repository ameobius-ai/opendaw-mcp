/**
 * Minimal openDAW test host — creates Project programmatically, no dashboard/UI.
 *
 * Boot order (each step depends on the previous one):
 *   Workers.install → AudioWorklets.install → AudioContext
 *   → AudioWorklets.createFor → WasmEngine.install → WasmEngine.ensureReady
 *   → Project.new → startAudioWorklet → engine.isReady
 *
 * Exposes window.opendaw.service + window.DAW_* globals compatible with
 * opendaw_mcp/bridge.py DAW_HELPERS and server.py tool functions.
 */

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Imports — all @opendaw packages needed by server.py
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

import { assert, UUID, Progress, Option, ArrayMultimap } from "@opendaw/lib-std"
import { PPQN, AudioData, WavFile } from "@opendaw/lib-dsp"
import { AnimationFrame } from "@opendaw/lib-dom"
import { UUID as UUID_box } from "@opendaw/lib-box"
import { ControlEvent, ControlType, MidiFile, MidiTrack } from "@opendaw/lib-midi"

import {
  AudioWorklets,
  GlobalSampleLoaderManager,
  GlobalSoundfontLoaderManager,
  Project,
  Workers,
  SampleProvider,
  SoundfontProvider,
  SampleService,
  OfflineEngineRenderer,
  EffectFactories,
  StudioPreferences,
} from "@opendaw/studio-core"
import type { SoundfontService } from "@opendaw/studio-core"

import { WasmEngine } from "@opendaw/studio-core-wasm"

import {
  SampleMetaData,
  SoundfontMetaData,
  InstrumentFactories,
  EngineAddresses,
  ExportConfiguration,
  PresetDecoder,
  PresetEncoder,
  PresetHeader,
  ProjectSkeleton,
  TrackBoxAdapter,
  AudioUnitBoxAdapter,
  TrackType,
  TransferAudioUnits,
  TransferRegions,
  ScriptCompiler,
  ScriptDeclaration,
} from "@opendaw/studio-adapters"

import {
  AudioUnitType,
  IconSymbol,
  Pointers,
} from "@opendaw/studio-enums"

import {
  AudioUnitBox,
  AudioBusBox,
  AudioFileBox,
  AudioRegionBox,
  AuxSendBox,
  CaptureAudioBox,
  MarkerBox,
  ModularDeviceBox,
  ModuleConnectionBox,
  NeuralAmpModelBox,
  NoteEventBox,
  NoteEventCollectionBox,
  NoteRegionBox,
  SignatureEventBox,
  TapeDeviceBox,
  TrackBox,
  ValueEventBox,
  ValueEventCollectionBox,
  WarpMarkerBox,
} from "@opendaw/studio-boxes"

// Vite worker/url imports — resolved at build time.
//
// Every specifier here must be a file npm actually ships. A subpath in a
// package's export map is NOT evidence of that: #44 was caused by importing
// "@opendaw/studio-core/offline-engine.js", which studio-core advertises in
// both `exports` and `files` yet publishes at no version in our ^0.1.4 range.
// Vite fails such an import during transform, which aborts the entire module:
// boot() never runs, no DAW_* global is assigned, and the bridge can only
// report a 30 s timeout. Verify a file exists in the published tarball before
// importing it.
//
// The wasm artifacts below were checked against studio-core-wasm@0.0.8:
// dist/wasm-processor.js, dist/wasm-offline-worker.js and dist/wasm/ are all
// present.
import WorkersUrl from "@opendaw/studio-core/workers-main.js?worker&url"
import WorkletsUrl from "@opendaw/studio-core/processors.js?url"
import WasmProcessorUrl from "@opendaw/studio-core-wasm/wasm-processor.js?url"
import WasmOfflineWorkerUrl from "@opendaw/studio-core-wasm/wasm-offline-worker.js?url"

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Boot
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const statusEl = document.getElementById("status")!

// The base URL serving the wasm binaries. Must match the /wasm-engine route in
// vite.config.ts, which serves node_modules/@opendaw/studio-core-wasm/dist/wasm.
const WASM_ENGINE_URL = "/wasm-engine"

function setStatus(msg: string) {
  statusEl.textContent = msg
  console.log(`[test-host] ${msg}`)
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Boot failure reporting
//
// Failures used to end up in the status line and nowhere else. Nothing reads
// that line, so bridge.py could only observe that the DAW_* globals never
// appeared and report a 30 s timeout — which names the symptom and hides the
// cause. Record the real error where the bridge can read it. See issue #57.
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

type BootError = {
  message: string
  stack: string | null
  phase: string
  at: string
}

function recordBootError(phase: string, err: unknown) {
  const w = window as any
  const record: BootError = {
    message: err instanceof Error ? err.message : String(err),
    stack: err instanceof Error ? err.stack ?? null : null,
    phase,
    at: new Date().toISOString(),
  }
  // Keep the first failure. Anything after it is usually a consequence, and
  // overwriting would hide the one that actually matters.
  if (!w.DAW_BOOT_ERROR) {
    w.DAW_BOOT_ERROR = record
  }
  console.error(`[test-host] ${phase} failed:`, err)
}

// A throw at module scope, or a rejection nobody awaited, never reaches
// boot()'s catch — without these it would leave no trace at all.
window.addEventListener("error", (event) => {
  recordBootError("window.onerror", event.error ?? event.message)
})
window.addEventListener("unhandledrejection", (event) => {
  recordBootError("unhandledrejection", event.reason)
})

async function boot() {
  setStatus("Booting...")

  assert(crossOriginIsolated, "window must be crossOriginIsolated")
  console.log("[test-host] crossOriginIsolated:", crossOriginIsolated)
  console.log("[test-host] SharedArrayBuffer:", typeof SharedArrayBuffer !== "undefined")

  AnimationFrame.start(window)

  setStatus("Installing workers...")
  await Workers.install(WorkersUrl)
  AudioWorklets.install(WorkletsUrl)

  setStatus("Creating AudioContext...")
  const audioContext = new AudioContext({ latencyHint: 0 })

  setStatus("Installing audio worklets...")
  await AudioWorklets.createFor(audioContext)

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // WASM engine
  //
  // studio-core ships no built-in engine. EngineWorklet resolves
  // EngineVariant.current() at construction time, and the provider it looks up
  // is registered by WasmEngine.install. studio-core cannot import
  // studio-core-wasm — that package depends on studio-core — so the engine is
  // injected, and its artifacts arrive as host-served URLs.
  //
  // Skipping this is exactly what left the host broken after #56: boot() got as
  // far as startAudioWorklet() and panicked with "No engine installed
  // (WasmEngine.install must run before an engine boots)".
  //
  // install() also wires the offline render path for us — internally it calls
  // OfflineEngineRenderer.install(offlineWorkerUrl, {wasmUrl}) — so mixdown,
  // stems, freeze and benchmarks go through this same call.
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  setStatus("Installing WASM engine...")
  WasmEngine.install({
    processorUrl: WasmProcessorUrl,
    offlineWorkerUrl: WasmOfflineWorkerUrl,
    wasmUrl: WASM_ENGINE_URL,
  })

  // ensureReady compiles the wasm modules and registers the processor module.
  // It reports failure by returning false rather than throwing, and there is no
  // fallback engine — so treat false as fatal here. Carrying on would surface
  // later as a panic from deep inside the EngineVariant provider
  // ("WasmEngine.ensureReady must succeed before an engine boots"), far from
  // the actual reason.
  setStatus("Compiling WASM engine modules...")
  if (!(await WasmEngine.ensureReady(audioContext))) {
    throw new Error(
      "WasmEngine.ensureReady() returned false: the wasm engine artifacts could " +
        `not be compiled or fetched. Check that ${WASM_ENGINE_URL} serves ` +
        "@opendaw/studio-core-wasm/dist/wasm (see the wasm-engine-assets plugin " +
        "in vite.config.ts) and look for a preceding \"WASM engine unavailable\" " +
        "warning with the underlying error.",
    )
  }

  const sampleProvider: SampleProvider = {
    fetch: async (_uuid: UUID.Bytes, _progress: Progress.Handler): Promise<[AudioData, SampleMetaData]> => {
      throw new Error("No samples in test host")
    },
  }
  const sampleManager = new GlobalSampleLoaderManager(sampleProvider)

  const soundfontProvider: SoundfontProvider = {
    fetch: async (_uuid: UUID.Bytes, _progress: Progress.Handler): Promise<[ArrayBuffer, SoundfontMetaData]> => {
      throw new Error("No soundfonts in test host")
    },
  }
  const soundfontManager = new GlobalSoundfontLoaderManager(soundfontProvider)

  const sampleService = new SampleService(audioContext)

  const soundfontService = new Proxy({} as SoundfontService, {
    get(_target, prop) {
      throw new Error(`SoundfontService.${String(prop)} accessed but disabled in test host`)
    },
  }) as SoundfontService

  setStatus("Creating project...")
  localStorage.removeItem("engine-preferences")

  const audioWorklets = AudioWorklets.get(audioContext)
  const project = Project.new({
    audioContext,
    sampleManager,
    soundfontManager,
    audioWorklets,
    sampleService,
    soundfontService,
  })

  setStatus("Starting engine...")
  project.startAudioWorklet()
  await project.engine.isReady()

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // Shim service + globals
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  const service = {
    hasProfile: true,
    project,
    newProject: () => console.warn("[test-host] newProject() — already have project"),
  }

  const w = window as any

  // Primary API for bridge.py
  w.opendaw = {
    service,
    InstrumentFactories,
    EffectFactories,
    EngineAddresses,
    ExportConfiguration,
  }

  // Globals expected by server.py tool functions
  w.DAW_IconSymbol = IconSymbol
  w.DAW_EffectFactories = EffectFactories
  w.DAW_InstrumentFactories = InstrumentFactories
  w.DAW_AudioUnitBox = AudioUnitBox
  w.DAW_AudioBusBox = AudioBusBox
  w.DAW_AudioFileBox = AudioFileBox
  w.DAW_AudioRegionBox = AudioRegionBox
  w.DAW_AudioUnitType = AudioUnitType
  w.DAW_AuxSendBox = AuxSendBox
  w.DAW_CaptureAudioBox = CaptureAudioBox
  w.DAW_MarkerBox = MarkerBox
  w.DAW_ModularDeviceBox = ModularDeviceBox
  w.DAW_ModuleConnectionBox = ModuleConnectionBox
  w.DAW_NeuralAmpModelBox = NeuralAmpModelBox
  w.DAW_NoteEventBox = NoteEventBox
  w.DAW_NoteEventCollectionBox = NoteEventCollectionBox
  w.DAW_NoteRegionBox = NoteRegionBox
  w.DAW_SignatureEventBox = SignatureEventBox
  w.DAW_TapeDeviceBox = TapeDeviceBox
  w.DAW_TrackBox = TrackBox
  w.DAW_TrackBoxAdapter = TrackBoxAdapter
  w.DAW_AudioUnitBoxAdapter = AudioUnitBoxAdapter
  w.DAW_TrackType = TrackType
  w.DAW_ValueEventBox = ValueEventBox
  w.DAW_ValueEventCollectionBox = ValueEventCollectionBox
  w.DAW_WarpMarkerBox = WarpMarkerBox
  w.DAW_Pointers = Pointers
  w.DAW_UUID = UUID
  w.DAW_Option = Option
  w.DAW_PPQN = PPQN
  w.DAW_ArrayMultimap = ArrayMultimap
  w.DAW_ControlEvent = ControlEvent
  w.DAW_ControlType = ControlType
  w.DAW_MidiFile = MidiFile
  w.DAW_MidiTrack = MidiTrack
  w.DAW_WavFile = WavFile
  w.DAW_PresetDecoder = PresetDecoder
  w.DAW_PresetEncoder = PresetEncoder
  w.DAW_PresetHeader = PresetHeader
  w.DAW_ProjectSkeleton = ProjectSkeleton
  w.DAW_ScriptCompiler = ScriptCompiler
  w.DAW_ScriptDeclaration = ScriptDeclaration
  w.DAW_StudioPreferences = StudioPreferences
  w.DAW_TransferAudioUnits = TransferAudioUnits
  w.DAW_TransferRegions = TransferRegions
  w.DAW_OfflineEngineRenderer = OfflineEngineRenderer
  w.DAW_WasmEngine = WasmEngine

  // Offline rendering is wired by WasmEngine.install (it calls
  // OfflineEngineRenderer.install internally), so it is available whenever the
  // engine booted at all.
  w.DAW_offlineEngineAvailable = true

  // Runtime state globals
  w.DAW_project = project
  w.DAW_audioContext = audioContext
  w.DAW_sampleManager = sampleManager
  w.DAW_engineStarted = true
  w.DAW_localAudioBuffers = new Map()

  setStatus("Ready")
  console.log("[test-host] window.opendaw.service ready")
}

boot().catch((err) => {
  recordBootError("boot", err)
  setStatus(`ERROR: ${err instanceof Error ? err.message : String(err)}`)
})
