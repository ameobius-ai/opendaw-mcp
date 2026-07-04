# Upstream Issue Coverage — DSP Scripts vs Open Issues

Our Werkstatt/Apparat/Spielwerk DSP scripts address several open feature requests in `andremichelle/openDAW`. This mapping is useful for PR communication (PR #283) and demonstrates that scriptable devices can satisfy community requests without core engine changes.

## Coverage map

| Issue | Title | Our script | How it covers |
|-------|-------|-----------|---------------|
| #195 | chorus effect | `werkstatt_chorus.js` | Stereo chorus with dual LFO 90° apart, rate/depth/center/feedback/mix controls |
| #133 | allpass filter | `werkstatt_allpass.js` + `werkstatt_phaser.js` | Dedicated allpass filter with freq/stages/invert/feedback + phaser with 2-8 stage allpass cascade, LFO sweeps 200-8000 Hz |
| #91 | Stereo Tool / DC remove button | `werkstatt_dcremover.js` + `werkstatt_darksat.js` | Dedicated DC offset remover with M/S stereo width + balance. Also DC blocker built into darksat |
| #209 | Paulstretch Effect | `werkstatt_paulstretch.js` | Full Paul Nasca algorithm: FFT phase randomization + overlap-add, up to 100x stretch |
| #139 | Parameter Modulation Controllers | `werkstatt_envfollower.js` | Envelope follower with attack/release/depth/threshold/invert — ducking or boosting |
| #241 | Envelope on soundfont player | `werkstatt_adsr_trim.js` | ADSR state machine that gates sustained samples — trims long Soundfont tails |
| #201 | Classic time stretch | `werkstatt_granular_stretch.js` | Granular time-stretch with Hann window overlap, configurable grain size and overlap ratio |
| #188 | Real-time Audio Pitch shifter | `werkstatt_pitch_shift.js` | Delay-line pitch shifter with crossfading read taps, ±24 semitones + cents fine tune |
| #277 | Werkstatt MIDI input | `apparat_ringmod.js` | Apparat instrument with MIDI-triggered ADSR + ring modulation. Werkstatt (audio effect) cannot receive MIDI — Apparat (instrument) can. Partial coverage: gives the MIDI-ADSR ring mod from the issue, but on Apparat not Werkstatt |
| #138 | FM (PM) Style Synthesizer | `apparat_fm.js` | 2-operator FM synth: carrier phase modulated by modulator, ratio/mod_depth/waveform controls, ADSR. Not full Sytrus routing matrix, but demonstrates FM concept as Apparat script |

## NOT covered (requires core engine / UI work)

| Issue | Title | Why not scriptable |
|-------|-------|--------------------|
| #203 | Analyser Device | Needs UI (oscilloscope/spectrum/spectrogram canvas) — not a DSP effect |
| #141 | Instrument/FX Layer device | Architecture change (rack/layer routing), not a single DSP script |
| #211 | Sidechain input for Werkstatt | Werkstatt `process(io, block)` already has `io.src` — but true sidechain routing needs engine support for routing a second audio source into the effect |
| #207 | Custom device inputs | Engine-level routing change (X-Y graph, button/pulse input types) |
| #102 | Volume Envelope Device | Possible as Werkstatt script (volume automation based on position), but issue asks for drawable envelope UI like Bitwig Segments |
| #90 | Mid-Side EQ | Needs switchable M/S mode UI with waveform display — not a simple DSP script |
| #149 | Separate envelopes for volume and filter in Vaporisateur | Requires changes to the built-in Vaporisateur device (separate envelope generators), not a scriptable device |
| #154 | Automation generation | UI feature (random LFO/function generation panel) — our MCP `automation_sweep` tool covers part of this programmatically, but the issue asks for in-DAW UI buttons |
| #89 | Multitarget midi/automation | Architecture change — one clip playing multiple instruments / automating multiple values. Engine routing, not a script |
| #174 | Playfield-like controls for Tape Device | Requires UI changes to the Tape device (start/end/reverse controls like Playfield). Our MCP `set_clip_playback` covers reverse/speed programmatically, but the issue asks for native Tape UI controls |
| #271 | New automation clip default node | UX behavior change in automation clip creation — engine/UI, not scriptable |
| #273 | Ctrl+D for audio effects | UI feature (duplicate effect via keyboard shortcut). Our MCP `mcp_opendaw_duplicate_effect` covers this programmatically |
| #270 | Automating enable/disable of effects | Requires automation target support for effect bypass parameter — engine change. Our MCP `set_effect_enabled` covers toggle but not automation of it |
| #269 | Playfield automating mute does not work | Bug in Playfield mute automation — engine fix needed |
| #275 | Automation node placement behaviour | UX bug in automation node placement — engine/UI fix |
| #274 | Automation node placement bug | UX bug in automation node placement — engine/UI fix |
| #272 | Up the contrast for the loop button | UI/theme tweak — not scriptable |
| #212 | Automationtrack automatic naming | UX feature — engine auto-naming for automation tracks |
| #245 | Podcast Recording | Large feature request — recording workflow, not a DSP script |
| #261 | WASM Audio Engine | Architecture migration — WASM audio engine, not scriptable |
| #262 | Audio (Video) Chat Extension | UX feature — not scriptable |
| #255 | Implement dough-samples to default openDAW samples | Content/sample library change — not scriptable |
| #249 | File evaluation and choosing | UX feature — file browser improvement, not scriptable |
| #243 | Make the manual accessible outside desktop computers | Documentation/UX — not scriptable |
| #234 | Evaluate WebClap | Feature evaluation — not a DSP script |
| #263 | Provide windows building instructions | Documentation — not scriptable |

## Strategy

- **andremichelle closes AI-generated issues** — do NOT open new issues referencing our scripts
- PR #283 (DSP examples) is the safe channel — mention issue coverage in PR description
- Comment on existing issues to link our scripts — this is OK, it's contributing to existing discussions not opening AI issues
- Scripts demonstrate that scriptable devices can satisfy feature requests without engine changes — this is the value proposition for the PR
- **All addressable issues are now covered** — the remaining open issues require core engine/UI work (see NOT covered table above). Future DSP scripts should target new issues as they're opened by the community
- **Issue triage workflow**: when checking for new addressable issues, fetch `gh issue list --state open --label "feature request"`, then check each issue body. If it asks for a DSP effect/synth/MIDI processing that can run in a Werkstatt/Apparat/Spielwerk script → addressable. If it asks for UI controls, routing changes, device architecture, or automation target support → NOT addressable via scripts
