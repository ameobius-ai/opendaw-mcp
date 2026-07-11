/**
 * Minimal openDAW test host — creates Project programmatically, no dashboard/UI.
 *
 * Based on naomiaro/opendaw-test projectSetup.ts pattern:
 *   Workers.install → AudioWorklets.install → OfflineEngineRenderer.install
 *   → AudioContext → Project.new → engine.isReady
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

// Vite worker/url imports — resolved at build time
import WorkersUrl from "@opendaw/studio-core/workers-main.js?worker&url"
import WorkletsUrl from "@opendaw/studio-core/processors.js?url"
import OfflineEngineUrl from "@opendaw/studio-core/offline-engine.js?worker&url"

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Boot
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const statusEl = document.getElementById("status")!

function setStatus(msg: string) {
  statusEl.textContent = msg
  console.log(`[test-host] ${msg}`)
}

async function boot() {
  setStatus("Booting...")

  assert(crossOriginIsolated, "window must be crossOriginIsolated")
  console.log("[test-host] crossOriginIsolated:", crossOriginIsolated)
  console.log("[test-host] SharedArrayBuffer:", typeof SharedArrayBuffer !== "undefined")

  AnimationFrame.start(window)

  setStatus("Installing workers...")
  await Workers.install(WorkersUrl)
  AudioWorklets.install(WorkletsUrl)
  OfflineEngineRenderer.install(OfflineEngineUrl)

  setStatus("Creating AudioContext...")
  const audioContext = new AudioContext({ latencyHint: 0 })

  setStatus("Installing audio worklets...")
  await AudioWorklets.createFor(audioContext)

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
  setStatus(`ERROR: ${err.message}`)
  console.error("[test-host] boot failed:", err)
})
