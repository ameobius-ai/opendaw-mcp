<!-- mcp-name: io.github.AMEOBIUS/opendaw-mcp -->
# openDAW MCP

[![CI](https://github.com/AMEOBIUS/opendaw-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/AMEOBIUS/opendaw-mcp/actions/workflows/ci.yml)
[![Docs](https://github.com/AMEOBIUS/opendaw-mcp/actions/workflows/docs.yml/badge.svg)](https://ameobius.github.io/opendaw-mcp/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![PyPI](https://img.shields.io/pypi/v/opendaw-mcp.svg)](https://pypi.org/project/opendaw-mcp/)
[![MCP Tools](https://img.shields.io/badge/MCP%20Tools-289-brightgreen)](TOOL_CATALOG.md)
[![Skills](https://img.shields.io/badge/Agent%20Skills-10-blue)](skills/)
[![DSP Scripts](https://img.shields.io/badge/DSP%20Scripts-41-orange)](scripts/)
[![Tests](https://img.shields.io/badge/Tests-283%20unit%20%2B%2017%20E2E-brightgreen)](tests/)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](pyproject.toml)
[![Lint](https://img.shields.io/badge/Lint-ruff%20✓-brightgreen)](pyproject.toml)
[![MCP Registry](https://img.shields.io/badge/MCP%20Registry-Published-blue)](https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.AMEOBIUS/opendaw-mcp)
[![Smithery](https://img.shields.io/badge/Smithery-Published-purple)](https://smithery.ai/server/@macar228228/opendaw-mcp)
[![Glama](https://glama.ai/mcp/servers/AMEOBIUS/opendaw-mcp/badges/score.svg)](https://glama.ai/mcp/servers/AMEOBIUS/opendaw-mcp)
[![LangChain + AutoGen + CrewAI](https://img.shields.io/badge/LangChain%20%2B%20AutoGen%20%2B%20CrewAI-Ready-blue)](opendaw_mcp/)

**289 MCP tools for agent-native control of [openDAW](https://github.com/andremichelle/openDAW) — a browser-based digital audio workstation.**

This project wraps openDAW's internal box system and project API behind a [Model Context Protocol](https://modelcontextprotocol.io) server, allowing AI agents (Claude, GPT, Hermes, etc.) to create and manipulate music projects programmatically — tracks, instruments, effects, MIDI, automation, audio regions, rendering, and more.

> ⭐ **Star this repo** if it's useful — it helps others discover it!

### Quick numbers

| | |
|---|---|
| **286** MCP tools | **58** Python examples (8 genre templates) |
| **36** DSP scripts | **10** agent skills |
| **3** framework wrappers | **272** unit + **13** E2E tests |
| **7** stem separation modes | **0** ruff errors |

### 30-second demo

```python
from opendaw_mcp.server import OpendawServer

server = OpendawServer()
await server.bridge.start()

# Full drum beat in one call (kick|snare|hihat, 16 steps each)
await server.mcp_opendaw_create_drum_pattern(
    pattern="x...x...x...x...|o.......o.....o.|..x...x...x...x.", unit_index=0
)

# Synth + reverb
await server.mcp_opendaw_create_synth_track(name="Lead")
await server.mcp_opendaw_add_effect(unit_index=1, effect_type="Dattorro")

# Render to WAV
await server.mcp_opendaw_render_full(output_path="beat.wav")
```

## Why opendaw-mcp?

**The only MCP server that gives an AI agent full DAW control — not just file conversion or playback.**

| Feature | opendaw-mcp | Other audio MCPs |
|---------|-------------|-------------------|
| Full DAW control (289 tools) | ✅ | ❌ (1-10 tools) |
| Scriptable DSP (write custom JS effects) | ✅ | ❌ |
| SOTA stem separation (7 models, GPU local) | ✅ | ❌ |
| Suno → DAW E2E pipeline | ✅ | ❌ |
| Genre templates (8 genres) | ✅ | ❌ |
| Agent skills with decision points | ✅ (10 skills) | ❌ |
| Offline render with LUFS targeting | ✅ | ❌ |
| Preset save/load (.opb) | ✅ | ❌ |
| dawproject interchange (Ableton/Bitwig) | ✅ | ❌ |

**Unique workflow:** Suno generates → SOTA stem split → openDAW import → mix/master → export. No other tool does this.

## How It Works

```text
AI Agent ──MCP──▶ Python Server ──Playwright──▶ Headless Chromium ──▶ openDAW (Vite dev server)
```

The MCP server launches a headless Chromium instance loaded with openDAW, then communicates via `page.evaluate()` calls into the DAW's V8 context. Every tool performs real operations on the live project — no stubs, no mocks.

## Features

- **Track & Region CRUD** — create/delete/move audio, note, and automation tracks with regions
- **Instrument Control** — Vaporisateur ( polysynth), Nano, Tape, Soundfont, Playfield (drum machine), MIDI output
- **Effects** — Delay, Reverb, Compressor, Equalizer, Saturation, Waveshaper, Stereo, Vocoder, NeuralAmp, Maximizer
- **MIDI Effects** — Arpeggio, Pitch, Velocity, Zeitgeist, Spielwerk (scriptable)
- **Scriptable Devices** — Apparat (instrument), Werkstatt (audio effect), Spielwerk (MIDI effect) with JS code compilation, full `@param` mapping metadata, and range-validated parameter setting
- **Automation** — event creation, interpolation modes, tempo/signature changes
- **Audio Operations** — region fades, gain, time/pitch stretch, warp markers, play modes
- **Mixing** — send/return routing, buses, volume, solo/mute, mixer state inspection
- **Rendering** — offline stem export with LUFS targeting, full mix render
- **Clips** — session view clip CRUD, clone, consolidate, playback settings
- **Groove** — groove shuffle amount and duration control
- **Presets** — export/import audio unit presets, effect chain presets
- **Transfer** — move regions and audio units between projects
- **Project Info** — tempo map conversion (PPQN↔seconds), duration, validation, sample listing
- **Notes** — pitch range, overlapping detection, advanced properties (chance, cent, playCount, playCurve)
- **Modular System** — voltage modules (Gain, Delay, Multiplier, AudioInput, AudioOutput), patch cable connections
- **Piano Mode** — global transpose, keyboard type, note scale, time range
- **Project & Bus Metadata** — creation date, signature, AU/track count, bus labels and colors
- **Debugging & Control** — screenshots, condition polling, raw JS evaluation

## Agent Skills

The `skills/` directory contains structured skill files for AI agents (Hermes, Claude, etc.) that describe how to use the 289 MCP tools effectively. Each skill covers a specific domain and includes decision points so the agent can adapt to any genre or workflow.

| Skill | Domain | Description |
|-------|--------|-------------|
| `adaptive-mix-mastering` | Mix → Master pipeline | Universal pipeline with decision points: genre detection, stem strategy, effect chain selection, LUFS targeting, mastering approach. Adapts to coldwave, techno, hip-hop, ambient, rock, pop. Includes `references/decision-tree.md`. |
| `suno-to-opendaw` | Suno → openDAW E2E | Killer workflow: Suno AI generation → SOTA stem separation (7 modes) → openDAW import → arrange → mix → master → export. 6-stage pipeline from prompt to finished track. Unique value prop — no other MCP server offers this. |
| `dsp-script-authoring` | Custom DSP writing | How to author custom Werkstatt/Apparat/Spielwerk DSP scripts. Processor API, @param/@sample declarations, DSP patterns (filters, saturation, reverb, LFO, envelope), validation workflow, 8 critical pitfalls. For writing new DSP, not using existing. |
| `opendaw-automation` | API reference | 289 MCP tools full reference, bridge architecture, pitfalls, DSP script library (33 scripts), CodeRabbit review patterns. The base skill — others cross-reference it. |
| `opendaw-track-architecture` | Track structure | Tracks, regions, clips, notes, tempo, time signature, markers, groove, song form. 50+ tools for building the skeleton of a track. |
| `opendaw-sound-design` | Instruments + DSP | Built-in instruments (Vaporisateur, Playfield, Nano, Tape, Soundfont) + 33 scriptable DSP scripts (Werkstatt/Apparat/Spielwerk) with full API reference and choosing guide. |
| `opendaw-genres` | Genre templates | Concrete parameters per genre — BPM, track layout, drum patterns, bass lines, chords, effect chains, pan, LUFS targets. 8 genres: techno, coldwave, hip-hop, ambient, DnB, house, lofi, trap. Not theory — actual tool calls and values. |
| `opendaw-effect-routing` | Effects + routing | Effect chains, sends/returns, sidechain, buses, mixing, mastering chain, render/export. How to route audio and deliver final output. |
| `opendaw-composition-patterns` | Composition | When and how to use 26 orchestration tools. Decision tree by musical goal, genre-specific recipes, parameter guidelines, pitfalls. Hip-hop/house/jazz/DnB/ambient/expressive MIDI workflows. |

### Using skills with Hermes

```bash
# Skills are auto-discovered from ~/.hermes/profiles/*/skills/
# Copy to your profile:
cp -r skills/adaptive-mix-mastering ~/.hermes/profiles/your-profile/skills/creative/
```

### Using skills with other agents

The SKILL.md files are standard markdown with YAML frontmatter. Any agent that supports skill loading can use them. The decision points and tool references are agent-agnostic.

## Suno Integration

opendaw-mcp connects with [Suno](https://suno.com) for AI music generation. The flagship `suno_generate_to_opendaw.py` example demonstrates the full pipeline: Suno generation → download → openDAW import → mastering → render.

**Getting Suno API access:** Join the [Suno Discord](https://discord.gg/kRpauM54vn) to get chirp API access. Without it, generation won't work — this is required for all Suno-based workflows.

**Pipeline examples:**
- `suno_generate_to_opendaw.py` — Suno generation → openDAW mastering (flagship)
- `suno_to_opendaw.py` — Import existing Suno track → enhance with DSP
- `suno_stems_to_opendaw.py` — Stem split → per-stem mix → render

## Quick Start

📚 **Full documentation: https://ameobius.github.io/opendaw-mcp/**

### Prerequisites

- Python 3.11+
- Node.js 20+ (for openDAW dev server)
- Chromium (Playwright will install it)

### Install

**From PyPI:**

```bash
pip install opendaw-mcp
playwright install chromium
```

**From source:**

```bash
git clone https://github.com/ameobius/opendaw-mcp.git
cd opendaw-mcp
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### Set Up openDAW

Clone and build openDAW separately:

```bash
git clone https://github.com/andremichelle/openDAW.git
cd openDAW
npm install
npm run build   # or: npx turbo run build
```

Create a headless host page (see `headless-daw/` for reference implementation).

### Run

```bash
# Terminal 1: Start openDAW dev server
cd openDAW
npm run dev     # typically serves on http://localhost:5174

# Terminal 2: Start MCP server (stdio transport, default)
cd opendaw-mcp
source venv/bin/activate
python server.py
```

### SSE Transport

For remote deployments and registry introspection (e.g. [Glama](https://glama.ai)):

```bash
MCP_TRANSPORT=sse FASTMCP_HOST=0.0.0.0 FASTMCP_PORT=8080 python server.py
```

### CLI

```bash
python server.py --help        # show usage and env vars
python server.py --version     # print version and tool count
python server.py --list-tools  # list all 258 registered MCP tools
```

### Docker

```bash
# Pull pre-built image from GitHub Container Registry
docker pull ghcr.io/ameobius/opendaw-mcp:1.14.1
docker run -p 8080:8080 ghcr.io/ameobius/opendaw-mcp:1.14.1
# MCP server available at http://localhost:8080/sse

# Or build from source
docker build -t opendaw-mcp .
docker run -p 8080:8080 opendaw-mcp
```

The Docker image bundles openDAW (built from source), Vite dev server, Chromium, and the MCP server. The entrypoint starts Vite, waits for it to be ready, then launches the MCP server in SSE mode.

### Claude Desktop / MCP Client Config

Add to your MCP client config (e.g. `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "opendaw": {
      "command": "python",
      "args": ["path/to/opendaw-mcp/server.py"],
      "env": {
        "OPENDAW_HOST_DIR": "path/to/headless-daw",
        "OPENDAW_URL": "http://localhost:5174",
        "OPENDAW_EXPORT_DIR": "path/to/exports"
      }
    }
  }
}
```

See `mcp.json` in the repo for a reference config.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENDAW_HOST_DIR` | `../headless-daw` | Path to the headless openDAW host directory |
| `OPENDAW_URL` | `http://localhost:5174` | URL of the running openDAW instance |
| `OPENDAW_EXPORT_DIR` | `../exports` | Directory for rendered audio exports |
| `NODE_BIN_DIR` | *(from PATH)* | Path to Node.js binary directory (if not on PATH) |
| `MCP_TRANSPORT` | `stdio` | Transport protocol: `stdio` or `sse` |
| `FASTMCP_HOST` | `127.0.0.1` | SSE server bind host |
| `FASTMCP_PORT` | `8000` | SSE server bind port |

## Architecture

### HeadlessDawBridge

The `HeadlessDawBridge` class manages the Playwright lifecycle:

1. Launches headless Chromium with audio autoplay enabled
2. Navigates to the openDAW URL
3. Waits for `window.DAW` and factory globals to load
4. Injects `DAW_HELPERS` — JS utility functions that eliminate boilerplate across tools

### DAW_HELPERS

JavaScript helpers injected into the DAW context:

- `au(i)` — get audio unit adapter by index
- `track(auIdx, trackIdx)` — get track adapter
- `region(au, track, reg)` — get region adapter
- `instrumentAU()` — get the first instrument audio unit
- `modify(fn)` — wrapper around `editing.modify()` for box mutations
- `allAUs()` — list all audio unit adapters

### Tool Structure

Each MCP tool follows the pattern:

```python
@mcp.tool()
async def tool_name(param: str) -> str:
    """Description."""
    async def _run():
        result = await bridge.page.evaluate("""...JS...""")
        return json.dumps(result)
    return await bridge.run(_run)
```

The bridge is a singleton — state persists within a single Python process. All box mutations go through `editing.modify()` as required by openDAW's transactional model.

### Input Sanitization

All string parameters that are interpolated into JavaScript template literals are sanitized before evaluation — quotes, backslashes, and braces are stripped to prevent JS injection. Numeric parameters use proper `int`/`float` type annotations for FastMCP type coercion.

## DSP Scripts

The `scripts/` directory contains 30 example DSP scripts (19 Werkstatt + 5 Apparat + 6 Spielwerk):

| Script | Device | Description |
|--------|--------|-------------|
| `werkstatt_darksat.js` | Werkstatt | Tape saturation with drive, bias, tone, mix, output gain |
| `werkstatt_coldfold.js` | Werkstatt | Wavefolding + bitcrush + slew rate reduction |
| `werkstatt_paulstretch.js` | Werkstatt | Extreme time-stretch via FFT/ISTFT overlap-add |
| `werkstatt_envfollower.js` | Werkstatt | Envelope follower with sidechain ducking |
| `werkstatt_chorus.js` | Werkstatt | Stereo chorus with LFO-modulated delay lines |
| `werkstatt_reverb.js` | Werkstatt | Algorithmic reverb with comb + allpass filters |
| `werkstatt_shimmer.js` | Werkstatt | Pitch-shimmer reverb with granular pitch shift |
| `werkstatt_spectral_freezer.js` | Werkstatt | Spectral freeze — captures & sustains a spectral frame for drone/ambient textures |
| `werkstatt_phaser.js` | Werkstatt | Phaser with LFO-swept allpass filter chain |
| `werkstatt_subcrusher.js` | Werkstatt | Sub-bass enhancement with glide and distortion |
| `werkstatt_lookahead.js` | Werkstatt | Lookahead limiter with gain reduction metering |
| `werkstatt_adsr_trim.js` | Werkstatt | ADSR envelope trim for sustained samples (#241) |
| `werkstatt_flanger.js` | Werkstatt | Stereo flanger with LFO-modulated delay line and feedback |
| `werkstatt_noisegate.js` | Werkstatt | Noise gate with threshold, attack/hold/release, range control |
| `werkstatt_tremolo.js` | Werkstatt | Tremolo with sine→square shape interpolation and phase offset |
| `werkstatt_granular_stretch.js` | Werkstatt | Granular time-stretch with Hann window + pitch shift (#201) |
| `werkstatt_pitch_shift.js` | Werkstatt | Real-time pitch shifter via delay-line sweep with crossfade (#188) |
| `werkstatt_dcremover.js` | Werkstatt | DC offset remover + M/S stereo width tool (#91) |
| `werkstatt_allpass.js` | Werkstatt | Allpass filter with invert + cascade stages (#133) |
| `werkstatt_ringmod_env.js` | Werkstatt | Ring modulator with envelope-followed frequency modulation (#277) |
| `apparat_darkbass.js` | Apparat | Bass synth with sub oscillator and filter envelope |
| `apparat_coldlead.js` | Apparat | Lead synth with detune and vibrato |
| `apparat_subcrusher.js` | Apparat | Sub-bass synth with glide and distortion |
| `apparat_ringmod.js` | Apparat | Ring modulator synth with ADSR and sub-oscillator (#277) |
| `apparat_fm.js` | Apparat | 2-operator FM synth with carrier/modulator ratio and ADSR (#138) |
| `spielwerk_powerchord.js` | Spielwerk | MIDI effect that generates power chord harmonies |
| `spielwerk_arpeggiator.js` | Spielwerk | MIDI arpeggiator with swing and octave range |
| `spielwerk_chordmemory.js` | Spielwerk | Chord memory — holds last chord shape (major/minor/7/dim/aug) |
| `spielwerk_strum.js` | Spielwerk | Strummer with up/down/random direction and spread |
| `spielwerk_velocity.js` | Spielwerk | Velocity scaler with curve, offset, and min/max clamp |
| `spielwerk_mididelay.js` | Spielwerk | MIDI delay with feedback, transpose per repeat, and decay |

## Examples

The `examples/` directory contains 46 Python scripts demonstrating the full workflow:

| Example | Description |
|---------|-------------|
| `create_beat.py` | Drum beat with Playfield |
| `create_chord_progression.py` | Chord progression with Vaporisateur |
| `mix_workflow.py` | Mixing: levels, effects, sends |
| `render_stems.py` | Stem export with LUFS targeting |
| `automation_sweep.py` | Filter cutoff automation |
| `modular_patch.py` | Modular system with patch cables |
| `full_production_pipeline.py` | Complete track: synth + drums + DSP + automation + render |
| `full_production_pipeline_v2.py` | Enhanced pipeline with orchestration tools |
| `scriptable_devices_demo.py` | All 3 scriptable device types: Apparat synth + Werkstatt DSP + Spielwerk MIDI |
| `device_specific_params.py` | Effect parameters: Compressor, Reverb, Delay, etc. |
| `instrument_automation.py` | Automating instrument parameters over time |
| `mastering_pipeline.py` | Mastering chain: EQ, compression, limiting |
| `metronome_settings.py` | Metronome configuration and tempo changes |
| `orchestration_demo.py` | High-level orchestration tools in action |
| `song_structure_demo.py` | Song structure with markers and sections |
| `render_convert.py` | Render and convert audio formats |
| `dawproject_export.py` | Export to Bitwig .dawproject format |
| `warp_marker_tempo_match.py` | Warp markers for tempo-matched audio regions |
| `suno_to_opendaw.py` | Suno→openDAW pipeline: import AI track, add mastering chain, reverb send, arp layer, render+stems |
| `suno_stems_to_opendaw.py` | Full E2E: stem split (7 SOTA modes, local GPU) → import stems → per-stem mix (vol/pan/effects) → MIDI arp layer → render+export |
| `suno_generate_to_opendaw.py` | **Flagship**: Suno generation (chirp_generate) → download → openDAW load → mastering (DarkSat+Lookahead) → LUFS check → render |
| `preset_management.py` | Save/load Werkstatt effect presets (.opb) — compile DSP script, tweak params, export preset, import back |
| `genre_techno.py` | Genre template: techno skeleton (130 BPM, 4-on-floor drums, rolling bass, Vaporisateur+Playfield, Compressor+Waveshaper chain) |
| `genre_coldwave.py` | Genre template: coldwave skeleton (100 BPM, sparse drums, Am-Fmaj7-Cmaj-Gdom7 progression, 4 tracks, Dattorro reverb, Waveshaper hardclip) |
| `genre_ambient.py` | Genre template: ambient skeleton (70 BPM, no drums, Cmaj7-Amin7-Fmaj7-Gmaj7, pad+bell+texture, long reverbs decay 0.85-0.95) |
| `genre_hiphop.py` | Genre template: hip-hop skeleton (85 BPM, boom bap drums, 808 bass Ab minor, dark pentatonic melody, Compressor+Waveshaper) |
| `genre_dnb.py` | Genre template: DnB skeleton (174 BPM, Amen break, reese+sub bass F minor, aggressive Comp 8:1, Waveshaper) |
| `genre_house.py` | Genre template: house skeleton (124 BPM, 4-on-floor, off-beat chord stabs Fmin9-Cmin9-Gmin9-Dmin9, rolling bass, Delay+Reverb) |
| `genre_lofi.py` | Genre template: lofi skeleton (82 BPM, swung drums, jazzy Dmin7-Gdom7-Cmaj7-Fmaj7 ii-V-I, warm bass, short reverb) |
| `genre_trap.py` | Genre template: trap skeleton (145 BPM, fast hi-hat rolls, gliding 808 bass, dark minor melody) |
| `create_melody.py` | Melody from scale degrees + rhythmic pattern (14 scales, rests, sustains, octave shifts) |
| `create_bassline.py` | Bassline from root + rhythmic pattern (low octave, high velocity, scale degrees) |
| `create_arpeggio.py` | Arpeggios from chord names — 6 patterns (up/down/updown/downup/random/chord), 6 rates |
| `humanize_notes.py` | Humanize MIDI: velocity/timing/duration variation + swing (seeded PRNG, reproducible) |
| `create_harmony.py` | Generate harmony parts — diatonic (3rds/5ths/6ths) + chromatic intervals, up/down |
| `create_counterpoint.py` | Counter-melody in contrary motion — mirrors melody around center pitch |
| `reverse_invert_notes.py` | Melodic variation: retrograde (reverse) + mirror inversion around axis |
| `create_drum_fill.py` | Drum fills/transitions: 5 types (build, break, roll, crash, tom), adjustable density |
| `create_ostinato.py` | Repeating melodic pattern as foundation layer (minimalism, electronic, film) |
| `create_crescendo.py` | Crescendo/decrescendo on existing notes: linear, exponential, logarithmic curves |
| `custom_dsp_script.py` | DSP authoring: custom Werkstatt analog saturation script (tanh + DC blocker + tone filter), compile via ScriptCompiler, set params, verify |
| `langchain_integration.py` | LangChain toolkit: use opendaw-mcp tools as LangChain Tool objects with any LLM agent |
| `autogen_integration.py` | AutoGen toolkit: use opendaw-mcp tools with Microsoft AutoGen agents |
| `crewai_integration.py` | CrewAI toolkit: use opendaw-mcp tools with CrewAI crews |
| `screenshot_demo.py` | Create a full house track with drums/bass/chords/effects, take a screenshot of the DAW UI, render to WAV |

## Agent Framework Integration

### LangChain

```python
from opendaw_mcp.langchain_tools import OpendawToolkit

toolkit = OpendawToolkit()
tools = toolkit.get_tools()  # or filter: get_tools(categories=["transport", "orchestration"])

# Use with any LangChain agent
from langchain.agents import create_react_agent, AgentExecutor
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini")
agent = create_react_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

executor.invoke({"input": "Create a dark techno track at 130 BPM and render it"})
```

See [`examples/langchain_integration.py`](examples/langchain_integration.py) for a full demo.

### AutoGen

```python
from opendaw_mcp.autogen_tools import get_autogen_tools

tools = get_autogen_tools()  # or filter: get_autogen_tools(categories=["transport", "orchestration"])

from autogen import AssistantAgent, UserProxyAgent

assistant = AssistantAgent("producer", llm_config=llm_config, tools=tools,
    system_message="You are a music producer. Use opendaw tools to create, mix, and render music.")
user = UserProxyAgent("user", human_input_mode="NEVER")
user.initiate_chat(assistant, message="Create a dark techno track at 130 BPM and render it")
```

See [`examples/autogen_integration.py`](examples/autogen_integration.py) for a full demo.

### CrewAI

```python
from opendaw_mcp.crewai_tools import get_crewai_tools

tools = get_crewai_tools()

from crewai import Agent, Task, Crew, LLM

llm = LLM(model="gpt-4o-mini")
producer = Agent(role="Music Producer", goal="Create and mix tracks", backstory="Expert producer", tools=tools, llm=llm)
task = Task(description="Create a dark techno track at 130 BPM and render it", agent=producer, expected_output="WAV file")
crew = Crew(agents=[producer], tasks=[task])
result = crew.kickoff()
```

See [`examples/crewai_integration.py`](examples/crewai_integration.py) for a full demo.

## Tool Catalog

See [`TOOL_CATALOG.md`](TOOL_CATALOG.md) for the complete list of 289 tools with parameters and descriptions.

### Orchestration Tools

High-level composers that combine multiple low-level operations into a single call — designed for agents to reduce token usage and round-trips:

| Tool | Replaces | Example |
|------|----------|---------|
| `create_notes_batch` | 10-50 × `create_note` | `'[{"pitch":60,"start":0,"duration":0.5},...]'` |
| `create_drum_pattern` | 10-20 × `create_note` | `'{"kick":"x...x...","hihat":"....o..."}'` |
| `create_chord_progression` | 15-50 × `create_note` | `'[["C","min7"],["F","dom7"]]'` |
| `add_mastering_chain` | 3 × `add_effect` + 10 × `set_param` | `style="warm", target_lufs=-14` |
| `create_genre_track` | 20-40 low-level calls | `genre="lofi"` → synth + drums + bass + chords |

## Mastering

The MCP server includes a full mastering chain for streaming-ready output:

1. **Render** — `render_full` (full mixdown) or `export_stems` (per-track stems)
2. **Measure LUFS** — `measure_lufs` (ITU-R BS.1770-4 K-weighting, gated mean squares)
3. **Auto-gain** — `auto_gain` (iterative: render → measure → adjust Maximizer threshold + output volume → re-render, converges ±1 LUFS)

```python
# Render full mix
await server.mcp_opendaw_render_full("my_mix", 48000)

# Measure loudness
lufs = json.loads(await server.mcp_opendaw_measure_lufs("my_mix"))
# → {"lufs_integrated": -18.3, "true_peak_db": -3.71, ...}

# Auto-gain to Spotify target (-14 LUFS)
result = json.loads(await server.mcp_opendaw_auto_gain("-14", "mastered", 48000, "3"))
# → converges to -13.7 LUFS in 3 iterations
```

Platform targets: Spotify/YouTube -14 LUFS, Apple Music -16 LUFS, Tidal -14 LUFS.

## Limitations

- **Headless only** — some UI-dependent features (file dialogs, popup-based model loading) are not available
- **Single process** — bridge state doesn't persist across Python process restarts
- **Upstream coupling** — tools depend on openDAW's internal box system, which can change between versions
- **AU rename** — requires adapter context not available in headless mode

## Acknowledgments

- [andremichelle](https://github.com/andremichelle) — creator of openDAW, an incredible browser-based DAW
- [Model Context Protocol](https://modelcontextprotocol.io) — the protocol that makes agent-native tools possible

## License

Apache-2.0 — see [LICENSE](LICENSE)

## Changelog

### v1.37.0 (2026-07-05)

- **`create_trill` orchestration tool (289 MCP tools)** — rapid two-note alternation ornament. 5 rates (32nd/16th/8th/32t/16t triplet). Upper note accent (baroque style), start on upper or lower. Works for classical trills, jazz shakes, metal tremolo picking, electronic LFO patterns. One call replaces 4-64 manual note creations. Essential for: baroque ornaments, jazz phrasing, tremolo effects, ornamentation
- **E2E verified**: default 16th (16 notes), 32nd (64 notes), 8th (4 notes), triplet 16th (24 notes), start_with_upper, no_accent, error handling — 8/8 tests passed
- **+11 unit tests** for trill pattern generation (283 total)
- **Example script**: `create_trill.py` — 5 trills across genres (baroque, fast, slow, jazz shake, minor 3rd)
- **289 MCP tools** (254 low-level + 32 orchestration + 3 melodic)
- ruff clean, CI green

### v1.36.0 (2026-07-05)

- **`create_chop` orchestration tool (288 MCP tools)** — slice source pitches into segments and rearrange. 5 modes: reverse (Dilla flip), stutter (glitch repeat), shuffle (Madlib random), ping-pong (ABBA), gate (chopped break). Octave shift for bass chops, velocity variation for human feel, inner-pitch reverse for nested chops. One call replaces 8-48 manual note creations. Essential for: hip-hop sampling, glitch-hop, bass music, sample flip workflows
- **E2E verified**: reverse (4 notes), stutter x3 (12 notes), shuffle (5 notes), ping-pong (8 notes), gate (3 notes), octave shift, error handling — 8/8 tests passed
- **+13 unit tests** for chop pattern generation (285 total)
- **Example script**: `create_chop.py` — 6 chops across 48 beats (reverse, stutter, shuffle, ping-pong, gate, bass chop)
- **288 MCP tools** (254 low-level + 31 orchestration + 3 melodic)
- ruff clean, CI green

### v1.35.0 (2026-07-05)

- **`create_bass_drop` orchestration tool (287 MCP tools)** — descending pitch sweep into sustained sub bass for dubstep/EDM/trap. Two phases: sweep (16th-note resolution pitch glide) + hold (sustained landing note). 3 curves (linear/exp/log), adjustable sweep (0.25-8 beats) and hold (0-16 beats). Complement to `create_riser` — riser builds up, bass drop lands. One call replaces 10-65 manual note creations. Essential for: dubstep drops, EDM build-and-drop, trap bass falls, impact transitions
- **E2E verified**: default drop (33 notes, 32 sweep + 1 hold), sweep-only (64 notes), short aggressive (9 notes), error handling
- **287 MCP tools** (254 low-level + 30 orchestration + 3 melodic)
- ruff clean, CI green

### v1.34.0 (2026-07-05)

- **`create_break` orchestration tool (287 MCP tools)** — classic drum break patterns for jungle/DnB/hip-hop/breakbeat. 6 presets: Amen Break, Think Break, Ashanti, Funky Drummer, When the Levee, Synthetic. 1-8 bars with variation modes (none/fill/humanize/drop) and swing. One call replaces 15-120 manual note creations. Essential for: breakbeat-based genres, sampling workflows, drum programming
- **E2E verified**: Amen (14 notes), Think 2-bar fill (26 notes), Funky Drummer humanized (22 notes), Amen 2-bar drop (25 notes), Synthetic with swing (14 notes), error handling
- **287 MCP tools** (254 low-level + 30 orchestration + 3 melodic)
- ruff clean, CI green

### v1.33.0 (2026-07-05)

- **`create_stab` orchestration tool (287 MCP tools)** — rhythmic chord stabs for house/disco/funk. Grid pattern with 'x' (stab), '-' (rest), '.' (ghost). Cycles through chord progressions. Adjustable octave, velocity, stab duration, pattern length. Ghost stabs use 45% velocity and shorter duration. One call replaces 20-60 manual note creations. Essential for: house off-beat stabs, funk syncopated punches, garage/shuffle patterns
- **E2E verified**: house Cm7 off-beat (16 notes, 4 stabs), funky F7/Cm7 with ghost notes (28 notes, 7 hits), all-rests error, invalid rhythm error
- **287 MCP tools** (254 low-level + 30 orchestration + 3 melodic)
- ruff clean, CI green

### v1.32.0 (2026-07-05)

- **`create_riser` orchestration tool (284 MCP tools)** — ascending pitch sweep for build-up transitions. 3 curves (linear, exp, log). Adjustable pitch range (MIDI 0-127), step count (8-128), length (0.25-16 beats). Velocity ramps up proportionally. One call replaces 10-50 manual note creations. Essential for: build-ups before drops, section transitions, tension creation
- **E2E verified**: 32 notes, pitch 36→84, exp curve ascending, linear curve 16 notes, error handling
- **287 MCP tools** (254 low-level + 30 orchestration + 3 melodic)
- ruff clean, CI green

### v1.31.0 (2026-07-05)

- **`werkstatt_stereowidth.js`** — M/S stereo width processor. 5 params: width (0=mono, 0.5=neutral, 1.5=wide), lowTrim (mono bass below crossover), lowFreq (50-500Hz crossover), mix, output. M/S encode → width scaling on side → low-freq trim → M/S decode. Essential for mastering: wide highs, mono bass
- **41 DSP scripts** (29 Werkstatt + 6 Apparat + 6 Spielwerk)
- **E2E verified**: compiled via ScriptCompiler, 5 params, width 0.5→1.2, lowTrim 0→0.7
- ruff clean, CI green

### v1.30.0 (2026-07-05)

- **`apparat_pluck.js`** — Karplus-Strong plucked string synth. 7 params: decay (string decay rate), damping (lowpass strength), brightness (noise burst spectral content), attack, release, detune, volume. Noise burst excites delay line, averaging filter creates natural string decay. Unique physical modeling sound unavailable in other Apparat scripts
- **40 DSP scripts** (28 Werkstatt + 6 Apparat + 6 Spielwerk)
- **E2E verified**: compiled via ScriptCompiler, 7 params, brightness 0.7→0.9, code header readback OK
- ruff clean, CI green

### v1.29.0 (2026-07-05)

- **`werkstatt_transient.js`** — transient shaper with dual envelope followers. 4 params: attack (±12 dB transient boost/cut), sustain (±12 dB sustain boost/cut), mix, output. Fast envelope (~5ms) detects transients, slow envelope (~80ms) detects sustain, independent gain on each component. No threshold needed — works on any material. Essential for drum mixing
- **39 DSP scripts** (28 Werkstatt + 5 Apparat + 6 Spielwerk)
- **E2E verified**: compiled via ScriptCompiler, 4 params, attack 0.5→0.8, sustain 0.5→0.3
- ruff clean, CI green

### v1.28.0 (2026-07-05)

- **`werkstatt_deesser.js`** — dynamic de-esser, band-split architecture. 7 params: freq (2-12kHz crossover), threshold (-40..0 dB), ratio (1:1..10:1), attack, release, mix, output. 2nd-order Linkwitz-Riley HPF isolates sibilance, envelope-followed gain reduction on high band only. Completes vocal chain: EQ → compressor → de-esser → exciter → limiter
- **38 DSP scripts** (27 Werkstatt + 5 Apparat + 6 Spielwerk)
- **E2E verified**: compiled via ScriptCompiler, 7 params, threshold 0.5→0.65, freq 0.4→0.8
- ruff clean, CI green

### v1.27.0 (2026-07-05)

- **`werkstatt_exciter.js`** — harmonic exciter with band-split architecture. 5 params: freq (crossover 800Hz-12kHz), harmonics (0-1), drive (0-1), mix (0-1), output (±24 dB). Cascaded one-pole HPF isolates highs, cubic nonlinearity adds odd harmonics, parallel wet/dry. Completes mastering chain: EQ → compressor → exciter → limiter
- **37 DSP scripts** (26 Werkstatt + 5 Apparat + 6 Spielwerk)
- **E2E verified**: compiled via ScriptCompiler, 5 params, freq 0.3→0.75, harmonics 0.5→0.85
- ruff clean, CI green

### v1.26.0 (2026-07-05)

- **`werkstatt_limiter.js`** — brickwall limiter with lookahead buffer + TPDF dither. 5 params: ceiling (0-1), release (10-500 ms), lookahead (0.1-5 ms), dither (TPDF on/off), mix. Instant attack, smooth release, circular lookahead buffer. Completes dynamics chain: compressor → limiter. Essential for mastering
- **`werkstatt_exciter.js`** — harmonic exciter with band-split architecture. 5 params: freq (crossover 800Hz-12kHz), harmonics (0-1), drive (0-1), mix (0-1), output (±24 dB). Cascaded one-pole HPF isolates highs, cubic nonlinearity adds odd harmonics, parallel wet/dry. Completes mastering chain: EQ → compressor → exciter → limiter
- **37 DSP scripts** (26 Werkstatt + 5 Apparat + 6 Spielwerk)
- **E2E verified**: compiled via ScriptCompiler, 5 params, freq 0.3→0.75, harmonics 0.5→0.85, code header readback OK
- ruff clean, CI green

### v1.25.1 (2026-07-05)

- **+31 unit tests** for music_theory functions — `parse_melody_pattern` (11 tests: ascending, rests, timing, velocity, scales, octaves, sharps, empty pattern), `scale_to_pitches` (6 tests: major, minor, length extension, octave, dorian, phrygian), `chord_to_pitches` (8 tests: triads, sevenths, diminished, sus4, octave, sharps), `GENRE_PRESETS` (6 tests: known genres, bpm/drums fields, bpm ranges)
- **316 unit tests** total (was 241), all passing
- ruff clean, CI green

### v1.25.0 (2026-07-05)

- **`werkstatt_paraeq.js`** — 3-band parametric EQ + HP/LP filters. 12 params: 3 × (freq, gain ±18 dB, Q 0.1-6) + hp_freq + lp_freq + mix. Biquad filters (RBJ Audio EQ Cookbook). Signal chain: HP → Band1 → Band2 → Band3 → LP. Closes critical EQ gap — parametric EQ is fundamental to mixing, was the most requested missing DSP category
- **35 DSP scripts** (24 Werkstatt + 5 Apparat + 6 Spielwerk)
- **E2E verified**: compiled via ScriptCompiler, 12 params with correct defaults, band1_gain 0→6 dB, band2_q 1→3.5, code header readback OK
- ruff clean, CI green

### v1.24.0 (2026-07-05)

- **`werkstatt_compressor.js`** — soft-knee peak compressor. 7 params: threshold (0→-60 dB), ratio (1:1→20:1), attack (0.1→100 ms log), release (50→500 ms log), makeup (0→+24 dB), mix (dry/wet), knee (0→12 dB soft knee). Peak detection, one-pole envelope smoother, stereo-linked. Closes the biggest DSP gap — compressor is fundamental to mixing
- **Integration test fix** — `test_integration.py` now skips when Playwright chromium is unavailable instead of failing. Checks both DAW reachability and browser availability
- **34 DSP scripts** (23 Werkstatt + 5 Apparat + 6 Spielwerk)
- **E2E verified**: compiled via ScriptCompiler, 7 params with correct defaults, threshold 0.5→0.75, ratio 0.4→0.85, code header readback OK
- ruff clean, CI green

### v1.23.3 (2026-07-05)

- **`werkstatt_multifilter.js`** — multi-mode SVF filter (Chamberlin topology). 4 modes: lowpass, highpass, bandpass, notch. 5 params: mode, cutoff (20-20kHz), resonance, drive, mix. Closes critical gap — standalone multi-mode filter was missing while allpass/dcremover existed
- **34 DSP scripts** (23 Werkstatt + 5 Apparat + 6 Spielwerk)
- **E2E verified**: compiled via ScriptCompiler, 5 params with correct defaults, mode switching (LP→HP), resonance cranked (0.3→0.8)
- ruff clean, CI green

### v1.23.2 (2026-07-05)

- **`werkstatt_overdrive.js`** — asymmetric soft-clip overdrive (tube-like). 5 params: drive, tone, level, bias, dry. Asymmetric clipping = even harmonics = warmth. Pre-HP filter removes mud, post-LP tone control, dry blend for parallel overdrive
- **32 DSP scripts** (21 Werkstatt + 5 Apparat + 6 Spielwerk)
- **E2E verified**: compiled via ScriptCompiler, 5 params with correct defaults, set_param works (drive 0.4→0.8, dry 0→0.3)
- ruff clean, CI green

### v1.23.1 (2026-07-05)

- **`werkstatt_stereo_delay.js`** — stereo delay with ping-pong, feedback, tone filter. 6 params: time_l, time_r, feedback, tone, mix, pingpong. Fill gap — delay was missing from DSP library while reverb/chorus/flanger/phaser all present
- **31 DSP scripts** (20 Werkstatt + 5 Apparat + 6 Spielwerk)
- **E2E verified**: compiled via ScriptCompiler, 6 params created with correct defaults, set_param works (feedback 0.35→0.6, pingpong 0→1.0)
- ruff clean, CI green

### v1.23.0 (2026-07-05)

- **`apply_articulation`** — staccato/legato/tenuto/accent for existing notes. Duration reshaping for phrasing character (staccato=short, legato=connected, tenuto=full slot, accent=velocity boost on downbeats). Deterministic, not random
- **13 unit tests** for articulation math (staccato ratio, legato overlap, tenuto slot fill, accent boost) — 228→241 total
- **E2E verified**: staccato (240→120, 8 notes), legato (240→228, 95% fill), accent (beats boosted to 0.9, off-beats stay 0.5)
- **58 examples** (added apply_articulation.py)
- **283 MCP tools**, **26 orchestration tools**, ruff clean, CI green

### v1.22.0 (2026-07-05)

- **`apply_velocity_curve`** — deterministic velocity envelope across notes (ramp_up/ramp_down/arc/trough/power). Unlike humanize (random), this applies a mathematical curve shape — build-ups, fade-ins, crescendo rolls, expressive phrasing. Power exponent for exponential curves
- **15 unit tests** for velocity curve interpolation (ramp, arc, trough, power) — 213→228 total
- **E2E verified**: ramp_up (0.2→1.0, 16 notes), arc (peak at middle=0.95), power=2.0 (slow rise, mid=0.36)
- **54 examples** (added apply_velocity_curve.py)
- **282 MCP tools**, **25 orchestration tools**, ruff clean, CI green

### v1.21.0 (2026-07-05)

- **`apply_sidechain`** — sidechain ducking via volume automation. Classic pumping/breathing effect for house/techno/EDM. Adjustable depth, attack, release, kick interval
- **`create_ghost_notes`** — ghost notes (quiet grace notes) for funk/R&B/neo-soul/hip-hop drumming. Seeded reproducibility, avoids occupied positions
- **12 unit tests** for sidechain ducking curve and ghost note placement logic — 201→212 total
- **E2E verified**: sidechain (272 events, 16 kicks, error handling), ghost_notes (4 added, error handling)
- **53 examples** (added apply_sidechain.py, create_ghost_notes.py)
- **281 MCP tools**, **24 orchestration tools**, ruff clean, CI green

### v1.20.0 (2026-07-05)

- **`create_call_response`** — call-and-response patterns (antecedent/consequent phrases). Foundation of blues, jazz, hip-hop, electronic. Alternates call → response with adjustable repeats
- **`create_walking_bass`** — walking bass lines over chord progressions. Beat 1=chord root, beat 2=chord tone, beat 3=passing tone, beat 4=approach note. Jazz/blues/swing
- **11 unit tests** for call_response (interleave, timing, velocity) and walking_bass (beat positions, approach notes, bass range) — 190→201 total
- **E2E verified**: call_response (blues ×4, error handling), walking_bass (ii-V-I, 12-bar blues, 2 bars/chord, error handling)
- **51 examples** (added create_call_response.py, create_walking_bass.py)
- **279 MCP tools**, **22 orchestration tools**, ruff clean, CI green

### v1.19.1 (2026-07-05)

- **`create_scale_run`** — ascending/descending scale sequences for fills, transitions, build-ups. 14 scales, 1-4 octaves
- **8 unit tests** for scale run generation (major/minor/blues/chromatic/pentatonic, multi-octave, direction)
- **E2E verified**: C minor up 1 oct (8 notes), A blues down 2 oct (13 notes), error handling
- **277 MCP tools**, **20 orchestration tools**, ruff clean, CI green

### v1.19.0 (2026-07-05)

- **`apply_swing`** — pure swing feel for existing notes, deterministic, no randomness. 16th/8th grid, 0-1 depth. 0.58 = classic hip-hop/lofi swing
- **`create_polyrhythm`** — polyrhythms: two streams with different subdivision counts (3:4, 2:3, 5:7, 7:8). Jazz, electronic, progressive, math rock
- **12 unit tests** for swing offset logic and polyrhythm generation (170→182 total)
- **E2E test** for apply_swing (0.5/0.0/8th grid) and create_polyrhythm (3:4, 2:3, error handling)
- **30 DSP scripts** (added flanger, noisegate, tremolo)
- **281 MCP tools**, **24 orchestration tools**, ruff clean, CI green

### v1.18.0 (2026-07-05)

- **`create_drum_fill`** — drum fills/transitions: 5 types (build, break, roll, crash, tom), adjustable density and bar length
- **`create_ostinato`** — repeating melodic/rhythmic pattern as foundation layer, scale-based, 1-16 repeats
- **`create_crescendo`** — crescendo/decrescendo on existing notes, 3 curves (linear, exp, log)
- E2E verified: drum_fill (build+roll), ostinato (C minor ×4), crescendo (exp 0.2→0.9)
- **276 MCP tools**, **19 orchestration tools**, ruff clean, CI green

### v1.17.0 (2026-07-05)

- **`create_counterpoint`** — new orchestration tool: generate counter-melody in contrary motion. Mirrors melody around center pitch. Auto-creates target track.
- **`humanize_notes`** — new orchestration tool: velocity/timing/duration variation + swing. Seeded mulberry32 PRNG for reproducibility.
- **`create_harmony`** — new orchestration tool: generate harmony from existing notes. 8 intervals (diatonic thirds/fifths/sixths + chromatic). Up/down direction.
- **`reverse_notes`** — melodic variation: retrograde (reverse note order in region)
- **`invert_notes`** — melodic variation: mirror inversion around axis pitch (newPitch = 2*axis - oldPitch)
- **`suno-prompt-engineering` skill** — concentrated Suno prompt engineering guide from 20+ KB files
- **7 new examples**: create_melody, create_bassline, create_arpeggio, humanize_notes, create_harmony, create_counterpoint, reverse_invert_notes
- **TOOL_CATALOG**: all 27 DSP scripts documented (was 7)
- **KB index sync**: 31→33 entries (all files covered)
- **bridge.py**: `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` env var for system chromium
- **271 MCP tools**, **43 examples**, **9 skills**, ruff clean, CI green

### v1.16.1 (2026-07-05)

- **`create_melody`** — new orchestration tool: generate melodies from scale + rhythmic pattern using scale degrees (1-7). Supports 14 scales, rests, sustains, octave shifts. One call replaces 10-30 `create_note` calls.
- **`create_bassline`** — new orchestration tool: generate basslines from root + rhythmic pattern. Low octave default (C2=36), high velocity (0.9), octave up/down (+/_). One call replaces 8-20 `create_note` calls.
- **`create_arpeggio`** — new orchestration tool: generate arpeggios from chord name with 6 patterns (up/down/updown/downup/random/chord) and 6 rates. One call replaces 8-32 `create_note` calls.
- **`opendaw_mcp/music_theory.py`** — shared music theory module: `NOTE_TO_PITCH`, `CHORD_INTERVALS`, `SCALE_INTERVALS`, `GENRE_PRESETS`, `chord_to_pitches()`, `scale_to_pitches()`
- **DRY refactor**: `create_chord_progression` and `create_genre_track` now import from `music_theory` instead of duplicating dicts inline
- **2 new genres**: `coldwave` (110 BPM, dark bass, Dm-Fmaj-Gmin-Amin) and `hiphop` (90 BPM, boom bap, Cm7-Ebmaj7-Gmin7-Bbmaj7) — `create_genre_track` now supports 8 genres
- **Scales**: 14 scale types (major, minor, harmonic minor, melodic minor, dorian, phrygian, lydian, mixolydian, locrian, pentatonic major/minor, blues, chromatic)
- **38 new unit tests** (test_music_theory.py) — 150 total
- ruff clean, 264 MCP tools intact, no regressions

### v1.16.0 (2026-07-05)

- **Modular architecture** — infrastructure extracted from 13K-line `server.py` into `opendaw_mcp/` package:
  - `constants.py` — lookup tables (TIDAL_RATE_MAP, DELAY_SYNC_MAP, WAVESHAPER_FUNCS, REVAMP_SECTIONS)
  - `bridge.py` — `HeadlessDawBridge` class (Playwright bridge, DAW_HELPERS injection)
  - `utils.py` — pure-Python helpers (`_parse_wav`, `_compute_lufs`, `_ok`, `_err`, `_safe_filename`, `_safe_path`, `_clamp_script_param`)
  - `__init__.py` — public API, all symbols re-exported for backward compat
- **`OpendawServer` facade** — class providing `bridge` + all `mcp_opendaw_*` tools as methods. Framework wrappers (LangChain, AutoGen, CrewAI) now work via this single interface.
- **server.py: 13244 → 12955 lines** (infrastructure moved to package modules)
- **0 regressions** — 316 unit tests pass, ruff clean, all framework wrappers functional, 283 MCP tools intact

### v1.15.2 (2026-07-04)

- **CrewAI toolkit** — `opendaw_mcp/crewai_tools.py` wraps 27 tools for CrewAI. Custom `OpendawCrewAITool` class, category filtering, shared server instance.
- **GitHub Discussions seeded** — 5 discussions: release announcement, 3 FAQ (bridge, GPU, MCP clients), genre showcase
- **33 examples total** (added `crewai_integration.py`)

### v1.15.1 (2026-07-04)

- **AutoGen toolkit** — `opendaw_mcp/autogen_tools.py` wraps 27 tools for Microsoft AutoGen. Category filtering, shared server instance.
- **Framework integration docs page** — LangChain + AutoGen + MCP direct + Hermes, with comparison table
- **32 examples total** (added `autogen_integration.py`)

### v1.15.0 (2026-07-04)

- **LangChain toolkit** — `opendaw_mcp/langchain_tools.py` wraps 30+ tools as LangChain `StructuredTool` objects. Category filtering, auto bridge start. Use with any LangChain agent.
- **AutoGen toolkit** — `opendaw_mcp/autogen_tools.py` wraps 27 tools for Microsoft AutoGen. Category filtering, shared server instance.
- **Docs site** — mkdocs-material at https://ameobius.github.io/opendaw-mcp/ — 21 pages, dark mode, search, auto-deploy via GitHub Actions
- **PR template** — structured checklist for contributors
- **PyPI metadata** — Documentation, Issues, Changelog URLs pointing to docs site
- **dev.to article** — "Controlling a DAW with AI Agents via MCP" (in `promotion/`)
- **32 examples total** (added `langchain_integration.py`, `autogen_integration.py`)

### v1.14.4 (2026-07-04)

- **Final 2 genre examples (E2E verified)**: `genre_lofi.py` (82 BPM, swung drums, jazzy ii-V-I, warm) and `genre_trap.py` (145 BPM, fast hi-hat rolls, gliding 808, dark minor). **All 8 genres from the skill now covered with E2E examples.** 30 examples total.

### v1.14.3 (2026-07-04)

- **3 more genre examples (E2E verified)**: `genre_hiphop.py` (85 BPM, boom bap, 808 Ab minor), `genre_dnb.py` (174 BPM, Amen break, reese+sub F minor), `genre_house.py` (124 BPM, 4-on-floor, off-beat chord stabs Fmin9-Cmin9-Gmin9-Dmin9). **28 examples total, 6 genres covered.**

### v1.14.2 (2026-07-04)

- **2 new genre examples (E2E verified)**: `genre_coldwave.py` (100 BPM, Am-Fmaj7-Cmaj-Gdom7, 4 tracks, Dattorro+Waveshaper) and `genre_ambient.py` (70 BPM, Cmaj7-Amin7-Fmaj7-Gmaj7, pad+bell+texture, long reverbs). **25 examples total.**
- Fixed return key names in genre examples (`notes_created` / `total_notes` / `lanes`)

### v1.14.1 (2026-07-04)

- **`opendaw-genres` skill** — 8 genre templates with concrete parameters: techno, coldwave, hip-hop, ambient, DnB, house, lofi, trap. BPM, track layout, drum patterns, bass lines, chord progressions, effect chains, pan, LUFS targets. Not theory — actual tool calls and values. **10 skills total.**

### v1.14.0 (2026-07-04)

- **2 new agent skills**: `suno-to-opendaw` (6-stage Suno→stems→openDAW→mix→master→export pipeline) and `dsp-script-authoring` (custom Werkstatt/Apparat/Spielwerk DSP script writing guide with patterns, validation, pitfalls). **7 skills total.**
- `set_marker_repeat` MCP tool (v1.13.1) — marker repeat count control (0=infinite)
- **283 MCP tools** (254 low-level + 26 orchestration)

### v1.13.0 (2026-07-04)

- **Preset Management**: 2 new MCP tools for openDAW preset format (.opb). `save_effect_preset` encodes any audio effect chain into a shareable .opb bundle via PresetEncoder.encodeEffects. `load_effect_preset` decodes .opb and applies it to a project. Enables agent-driven preset creation and reuse.
- 5 Werkstatt presets published to upstream (PR #284): Dark Saturation, Plate Reverb, Cold Fold Distortion, Stereo Phaser, Stereo Chorus.
- **283 MCP tools** (254 low-level + 26 orchestration)

### v1.12.1 (2026-07-04)

- **Stem Splitter**: 2 new MCP tools for SOTA open-source source separation. `split_stems` runs 7 modes locally on GPU (ensemble, scnet, bs6, polarformer, dereverb, drumsep, denoise). Optional auto-import into DAW. Uses BS-Roformer, HTDemucs FT, SCNet XL, MelBand Roformer models.
- `list_split_modes` — list all separation modes with SDR scores
- **283 MCP tools** (254 low-level + 26 orchestration)

### v1.12.0 (2026-07-04)

- **Agent Skills**: 10 structured skill files in `skills/` directory — adaptive mix→master, suno-to-opendaw (Suno→stems→mix→master E2E), dsp-script-authoring (custom DSP), opendaw-genres (8 genre templates), opendaw-automation (283 tools, 146 ref files), track architecture, sound design, effect routing, composition patterns. Decision points for genre-adaptive workflows. Agent-agnostic.
- **41 DSP scripts total** (29 Werkstatt + 6 Apparat + 6 Spielwerk)

### v1.11.9 (2026-07-04)

- **CodeRabbit fixes**: reverb stereo width (separate L/R comb banks with decorrelated delay times, M/S width on reverb tail), paulstretch cursor split (independent read/write cursors, proper frame emission gating)
- **41 DSP scripts total** (29 Werkstatt + 6 Apparat + 6 Spielwerk)

### v1.11.8 (2026-07-04)

- **New Werkstatt script**: ring modulator with envelope-followed frequency modulation (#277) — workaround for MIDI input limitation in Werkstatt audio effects
- **41 DSP scripts total** (29 Werkstatt + 6 Apparat + 6 Spielwerk)

### v1.11.7 (2026-07-04)

- **Suno→openDAW pipeline example**: import AI-generated track, add mastering chain (tape sat + lookahead comp), reverb send bus, MIDI arp layer, render + stems + LUFS

### v1.11.6 (2026-07-04)

- **4 new Spielwerk MIDI effect scripts**: chord memory, strummer, velocity scaler, MIDI delay
- **1 new Python example**: Suno→openDAW pipeline (import AI track, mastering chain, reverb send, arp layer, render+stems)
- **41 DSP scripts total** (29 Werkstatt + 6 Apparat + 6 Spielwerk)

### v1.11.5 (2026-07-04)

- **7 new DSP scripts**: DC remover + stereo width (#91), allpass filter (#133), 2-operator FM synth (#138), chord memory, strummer, velocity scaler, MIDI delay
- **Coldfold fix**: removed unused `range` variable (CodeRabbit review)
- **41 DSP scripts total** (29 Werkstatt + 6 Apparat + 6 Spielwerk)

### v1.11.4 (2026-07-04)

- **1 new Apparat script**: ring modulator synth with ADSR and sub-oscillator (#277)
- **18 DSP scripts total** (12 Werkstatt + 4 Apparat + 2 Spielwerk)

### v1.11.3 (2026-07-04)

- **1 new Werkstatt script**: real-time pitch shifter via delay-line sweep (#188)
- **Ruff lint fixes**: removed unused imports/variables in examples and midi_parser
- **17 DSP scripts total** (12 Werkstatt + 3 Apparat + 2 Spielwerk)

### v1.11.2 (2026-07-04)

- **10 DSP bug fixes** synced from upstream PR #283 CodeRabbit review:
  - darksat: undefined `outR` variable fix, DC blocker signal path corrected
  - chorus: delay buffer 2× for depth modulation, safe modulo for negative indices
  - coldfold: slew parameter `/100` scaling removed (was disabling the parameter)
  - lookahead: gain reduction now applied to delayed signal (true lookahead)
  - reverb: comb filter indices advancing, per-comb damping state, M/S stereo width decode
  - shimmer: per-channel pitch shifter state (eliminates stereo crosstalk)
  - phaser: stable 1st-order allpass topology (2nd-order was unstable)
  - subcrusher: bidirectional glide (was diverging on upward glides)
  - arpeggiator: swing notes no longer dropped at block boundaries
- **14 DSP scripts total** (9 Werkstatt + 3 Apparat + 2 Spielwerk) — all CodeRabbit issues addressed
- **2 new Werkstatt scripts**: ADSR trim (sustained sample trimming, #241) + granular time-stretch (Hann window overlap + pitch shift, #201)
- **1 new Werkstatt script**: real-time pitch shifter via delay-line sweep (#188)
- **1 new Apparat script**: ring modulator synth with ADSR and sub-oscillator (#277)
- **18 DSP scripts total** (12 Werkstatt + 4 Apparat + 2 Spielwerk)

### v1.11.1 (2026-07-04)

- **Scriptable device mapping info** — `list_script_params` now returns full `@param` mapping metadata (min, max, mapping type, unit) via `ScriptDeclaration.parseParams()`
- **Range validation** — `set_script_param` now validates values against `@param` declarations: bool snaps to 0/1, int rounds+clamps, linear/exp clamps to [min, max]. Returns `clamped` flag and `range` info
- **`_clamp_script_param`** Python helper mirrors JS-side clamping logic
- **+15 unit tests** (93 total) — TestScriptParamClamping: linear/exp/int/bool/unipolar clamping, rounding, snapping
- **+6 integration E2E tests** — bridge startup, globals, track ops, scriptable compile, param clamping, latency benchmark (avg 4ms round-trip)
- **5 new Werkstatt DSP scripts** — reverb (Schroeder plate), chorus (stereo dual-LFO), phaser (allpass cascade), lookahead compressor (soft knee), shimmer delay (granular pitch shift). Total: 12 scripts
- **`DAW_ScriptDeclaration`** added to headless-daw globals

### v1.11.0 (2026-07-04)

- **`apply_mix_preset`** — 8th orchestration tool: batch volume/pan/mute/solo across all tracks. Named presets (lofi, house, balanced, wide) or custom JSON
- **258 MCP tools** (252 low-level + 8 orchestration)

### v1.10.2 (2026-07-04)

- **24 new unit tests** for orchestration tools (78 total) — curve interpolation, chord theory, drum pattern parsing, song structure parsing
- **TOOL_CATALOG fully synchronized** — 0 discrepancies with server.py

### v1.10.1 (2026-07-04)

- **258 MCP tools** (253 low-level + 7 orchestration)
- **`create_song_structure`** — arrangement markers (intro/verse/chorus/bridge/outro) from JSON section list
- **`automation_sweep`** — smooth automation ramps with linear/exp/log curves. Replaces 10-30 `create_automation_event` calls
- **PyPI v1.10.1 published** — `pip install opendaw-mcp`
- **Both orchestration tools tested end-to-end** via Playwright bridge
- **54 tests, ruff clean, CI green**

### v1.10.0 (2026-07-04)

- **7 orchestration tools** — high-level composers for agents:
  - `create_notes_batch` — batch MIDI note creation (JSON array, one round-trip)
  - `create_drum_pattern` — step-sequencer notation (`x...x...` → drum beat)
  - `create_chord_progression` — chord names → auto-voiced notes (`[["C","min7"]]`)
  - `add_mastering_chain` — EQ + Compressor + Maximizer with style presets
  - `create_genre_track` — full genre starting point (house/techno/lofi/dnb/trap/ambient)
  - `create_song_structure` — arrangement markers from JSON
  - `automation_sweep` — smooth parameter ramps with linear/exp/log curves
- **258 total tools** (250 low-level + 7 orchestration + 1 internal)
- **`set_metronome`** — dedicated metronome control (enabled, gain, beat_subdivision)
- **Module-level lookup tables** — TIDAL_RATE_MAP, DELAY_SYNC_MAP, WAVESHAPER_FUNCS, REVAMP_SECTIONS extracted for testability
- **+23 new unit tests** (54 total) — fraction maps, waveshaper funcs, revamp sections, safe_filename edge cases
- **Official ScriptCompiler migration** — `set_script_device_code` now uses the real `ScriptCompiler` from `@opendaw/studio-adapters` instead of custom @param/@sample parser. Benefits: declaration caching (WeakMap), proper sample file cleanup, label parsing, correct worklet wrapping
- **Stems export fix** — `useInstrumentOutput` changed from True→False. Stems now route through channel strip (effects, sends, volume/pan) as documented by naomiaro/opendaw-test
- **`export_dry_stem`** — new tool for freeze/flatten/re-amp workflows: captures raw instrument output before effects
- **`set_waveshaper_equation`** — 6 transfer functions (hardclip/cubicSoft/tanh/sigmoid/arctan/asymmetric)
- **`set_crusher_crush`** — sample-rate reduction with documented crush inversion semantics
- **`set_revamp_filter`** — 7 EQ sections (highpass/lowshelf/lowbell/midbell/highbell/highshelf/lowpass) with enabled/freq/gain/q/order
- **`set_tidal_rate`** — musical fraction string → Tidal LFO rate index (17 entries)
- **`set_delay_sync`** — musical fraction string → Delay synced time index (21 entries, includes "off")
- **Effect lookup case-insensitive** — `add_effect("werkstatt")` now works alongside `Werkstatt`
- **naomiaro/opendaw-test research** — 543 commits, 17 SDK doc chapters used as authoritative reference for effect parameters and box field names
- **54 tests, ruff clean, CI green**

### v1.9.6 (2026-07-03)

- **`measure_lufs` refactored** — 223 lines → 20 lines. Extracted `_parse_wav()` and `_compute_lufs()` helpers
- **DRY: K-weighting coefficients** — duplicated if/else branches (48kHz vs else) were identical, merged into single computation
- **9 new unit tests** — WAV parsing (float32/mono/stereo/PCM16/invalid/no-data) + LUFS computation (silence/full-scale/low-level/stereo)
- **Social preview banner** — custom OpenGraph image for GitHub link previews
- **awesome-mcp PR updated** — title and body synced to 255 tools
- **GitHub topics** — 18 topics for discoverability
- **31 total tests, ruff clean, CI green**

### v1.9.5 (2026-07-03)

- **CLI commands** — `--version`, `--list-tools`, `--help` with full env var reference
- **31 unit tests** — pytest covering `_ok`, `_err`, `_wrap_eval`, `_unwrap_eval`, `_safe_filename`, `_safe_path`, `_parse_wav`, `_compute_lufs`
- **3 bug fixes found by tests:**
  - `_ok()` — `{"success": False}` in data overwrote the `True` flag (security fix)
  - `_safe_filename()` — case-sensitive extension stripping (`.MP3` not stripped)
  - `_safe_filename()` — Windows backslash path traversal not handled on Linux
- **CI enhanced** — now runs pytest (54 tests) alongside syntax/AST/smoke/ruff checks
- **PEP 561** — `py.typed` marker for type checker support
- **Mastering pipeline example** — full chain: render → measure LUFS → auto-gain → stems → MP3
- **25 examples total** — all syntax-validated
- **255 total tools** (added `export_dry_stem` for freeze/flatten workflows)

### v1.9.4 (2026-07-03)

- **Removed 2 duplicate tools** (245 → 243)
  - `delete_signature_event` — superseded by `delete_signature_change` (richer: position match + index, returns updated event list)
  - `list_aux_sends` — superseded by `list_sends` (richer: target_bus_name, send_level_db, routing, send_pan via box-level access)
- **TOOL_CATALOG.md regenerated from AST** — all 255 tools with descriptions, 32 categories
- **server.json Docker tag fixed** — was stale `1.0.0`, now matches release version
- **255 total tools**

### v1.9.3 (2026-07-03)

- **DRY refactoring complete: 17 DAW_HELPERS, ~295 replacements, 0 raw enumeration patterns**
  - New helpers: `markerBoxes`, `sendBoxes`, `busBoxes`, `sampleBoxes`, `noteTrackBoxes`, `clipBoxes`, `rootClipBoxes`, `scriptParams`, `scriptSamples`, `chainBoxes`
  - All `pointerHub.incoming()` enumeration patterns replaced across 245 tools
  - CONTRIBUTING.md updated with full 17-helper reference table
  - 6 DRY commits, 0 regressions, CI green

### v1.9.2 (2026-07-03)

- **DRY refactoring: 113+ tools migrated to `h.allAUBoxes()` / `h.auBox()` helpers**
  - Replaced 133 occurrences of raw `[...rootBox.audioUnits.pointerHub.incoming()].map(({box}) => box).sort(...)` boilerplate with `h.allAUBoxes()` across 113+ MCP tools
  - Box-level helpers eliminate ~3000 lines of duplicated AU enumeration code
  - E2E verified: allAUBoxes returns sorted array, auBox(i) returns box by index, count matches raw, box identity matches
- **Security hardening**
  - Transport action enum validation (`play`, `stop`, `toggle`) — prevents JS injection
  - `duplicate_effect` chain_type enum validation (`audio`, `midi`)
  - `_safe_filename()` + `_safe_path()` helpers — `os.path.basename()` sanitization + path traversal protection on 6 render/export locations
  - `_unwrap_eval` bare except → `json.JSONDecodeError`
- **245 total tools** (no tool count change — refactoring only)

### v1.9.1 (2026-07-03)

- **2 new generic tools: Boolean & Integer effect parameter setters**
  - `set_effect_parameter_bool(unit_index, effect_index, parameter_name, value)` — Generic boolean field setter. Covers Compressor (lookahead, automakeup, autoattack, autorelease), Gate (inverse), Maximizer (lookahead), StereoTool (invertL, invertR, swap), NeuralAmp (mono)
  - `set_effect_parameter_int(unit_index, effect_index, parameter_name, value)` — Generic integer field setter. Covers Vocoder (bandCount), StereoTool (panningMixing), Fold (overSampling), Crusher (bits), Delay (version). Device-specific tools are preferred when available.
- **245 total tools**

### v1.9.0 (2026-07-03)

- **6 new tools: Device-Specific Parameters & NeuralAmp Model Loading**
  - `set_neuralamp_model(unit_index, effect_index, model_json, label, pack_id)` — Load NAM/Tone3000 model JSON directly into a NeuralAmp effect, bypassing the popup-based Select Flow. Creates NeuralAmpModelBox and links it via pointer
  - `set_vocoder_modulator_source(unit_index, effect_index, source)` — Set Vocoder modulator source: noise-white, noise-pink, noise-brown, self, or external
  - `set_vocoder_band_count(unit_index, effect_index, band_count)` — Set Vocoder filter band count (8-32)
  - `set_stereo_tool_panning(unit_index, effect_index, panning_mixing)` — Set StereoTool panning law (linear, equal-power)
  - `set_fold_oversampling(unit_index, effect_index, oversampling)` — Set Fold wavefolder oversampling (0=off, 1=2x, 2=4x)
  - `set_crusher_bits(unit_index, effect_index, bits)` — Set Crusher bit depth (1-16)
- **255 total tools**

### v1.8.2 (2026-07-03)

- **2 new tools: Audio Region Time Base & Waveform Offset**
  - `set_audio_region_time_base(unit_index, track_index, region_index, time_base)` — Switch duration interpretation between 'musical' (PPQN, tempo-following) and 'seconds' (fixed wall-clock)
  - `set_audio_region_waveform_offset(unit_index, track_index, region_index, offset)` — Set waveform display offset for visual alignment
- **PR #280 closed** — andremichelle confirmed it's our bundler setup issue, not upstream. Closing as requested.
- **237 total tools**

### v1.8.1 (2026-07-03)

- **3 new tools: Warp Marker CRUD** — `create_warp_marker`, `delete_warp_marker`, `update_warp_marker`
  - `create_warp_marker(unit_index, track_index, region_index, position_beats, seconds)` — Add warp marker to stretched audio regions
  - `delete_warp_marker(unit_index, track_index, region_index, marker_index)` — Delete non-anchor warp marker
  - `update_warp_marker(unit_index, track_index, region_index, marker_index, position_beats, seconds)` — Update warp marker position/seconds (-1 = unchanged)
  - Enables agent-driven tempo matching: programmatically pin audio regions to musical positions
- **235 total tools**

### v1.8.0 (2026-07-03)

- **3 new tools: MP3/FLAC Audio Conversion** — `convert_audio`, `render_full_format`, `export_stems_format`
  - `convert_audio(filename, format, bitrate, quality)` — WAV→MP3/FLAC via system ffmpeg
  - `render_full_format(filename, format, bitrate)` — render + convert in one step
  - `export_stems_format(filename_prefix, format, bitrate)` — stems + convert each
  - Uses system ffmpeg (4.4.2), not browser WASM — more reliable in headless mode
  - E2E: WAV 1.01MB → MP3 0.11MB (ratio 0.106) → FLAC 0.19MB (ratio 0.194) ✅
- **Bugfix: operator precedence in 14 division+nullish coalescing expressions**
  - `X / Quarter ?? 0` → `(X ?? 0) / Quarter` — prevents NaN→null for position/duration fields
- **Improvement: `get_track_info` now includes `exclude_piano_mode` field**
- **232 total tools**

### v1.7.4 (2026-07-03)

- **3 new tools: Engine Sleep/Wake + Loading Check** — `engine_sleep`, `engine_wake`, `query_loading_complete`
  - `engine_sleep()` — suspend audio processing to save CPU during non-audio operations
  - `engine_wake()` — resume audio processing
  - `query_loading_complete()` — check if all audio samples are loaded and ready
  - E2E: sleep ✅, wake ✅, loading (loaded=false, is_ready=true) ✅
- **Improvement: `get_effect_chain` + `get_midi_effect_chain`** — now return short type names (`Delay` instead of `DelayDeviceBox`), plus `class`, `minimized` fields

### v1.7.3 (2026-07-03)

- **2 new tools: Instrument Automation** — `add_instrument_automation`, `list_automatable_fields`
  - Automate any instrument parameter: Vaporisateur cutoff/volume/ADSR, Tape flutter/wow, Playfield sample mute
  - Per-sample targeting via `sample_index` for Playfield
  - `list_automatable_fields` introspects Pointers.Automation support (18/23 on Vaporisateur)
  - Addresses upstream #269 (playfield mute automation) via MCP
  - E2E: Vaporisateur cutoff automated (3 events) ✅, 18 automatable fields ✅

### v1.7.2 (2026-07-03)

- **3 new tools: Effect Duplication + Instrument Automation** — `duplicate_effect`, `add_instrument_automation`, `list_automatable_fields`
  - `duplicate_effect` — duplicate single effect in-place with all params copied (audio or MIDI chain)
  - `add_instrument_automation` — automate any instrument parameter (Vaporisateur cutoff/volume, Tape flutter, Playfield sample mute, etc). Supports per-sample targeting via sample_index
  - `list_automatable_fields` — introspect which fields support Pointers.Automation (18/23 on Vaporisateur)
  - Addresses upstream issue #273 (Ctrl+D for audio effects) and #269 (playfield mute automation) via MCP
  - E2E tested: Delay duplicated with params ✅, Vaporisateur cutoff automated (3 events) ✅, 18 automatable fields detected ✅
- **Bugfix: `transport(action)` now respects action parameter** — was always toggling, now correctly handles "play", "stop", "toggle"
- **Cleanup: removed unused `region_type` param** from `set_region_duration` and `set_region_mute`

### v1.7.1 (2026-07-03)

- **4 new tools: Engine Control** — `engine_panic()`, `get_engine_status()`, `schedule_clip_play(clip_ids)`, `schedule_clip_stop(track_ids)`
  - Panic button for stuck audio, real-time engine monitoring (CPU load, position, BPM, playing state), session view clip triggering
  - E2E tested: get_engine_status ✅, engine_panic ✅

### v1.7.0 (2026-07-03)

- **2 new tools: DawProject Interop** — `export_dawproject(filename)`, `import_dawproject(filename)`
  - Export/import projects in .dawproject format (Bitwig, Ableton, rePitch compatible)
  - ZIP containing project.xml, metadata.xml, and audio samples
  - Enables cross-DAW workflow: create in openDAW → export to Bitwig, or import Bitwig project → render in openDAW
  - DawProject + DawProjectImport exposed as globals in headless-daw
  - E2E tested: export (2442 bytes, valid ZIP) → import (7 boxes, round-trip OK)

### v1.6.2 (2026-07-03)

- **2 new tools: Studio Settings** — `get_studio_settings()`, `set_studio_setting(category, key, value)`
  - Read/write StudioPreferences: engine, visibility, editing, debug, storage, time-display, pointer
  - Control auto-create-output-maximizer, overlapping-regions-behaviour, enable-beta-features, auto-delete-orphaned-samples, note-audition-while-editing, and more
  - StudioPreferences exposed as `DAW_StudioPreferences` global in headless-daw

### v1.6.1 (2026-07-03)

- **4 new tools from DAW globals research** — `set_unit_minimized`, `list_aux_sends`, `capture_realtime`, `get_sample_info`
  - Mixer minimize, aux send listing, realtime audio capture, sample metadata

### v1.6.0 (2026-07-03)

- **DAW_HELPERS refactoring** — all 180 tools with `const p = window.DAW` migrated to `const h = window.DAW_HELPERS` pattern
  - Eliminated boilerplate: AU list enumeration, sort, editing.modify wrapping
  - Fixed 19+ pre-existing bugs: `setPosition` (api→engine), 8x missing `.sort()` on AU lists, 9x `Quarter=960` hardcode → `h.ppqn.Quarter`, 2x Python/JS scope leaks
  - DAW_HELPERS provides: `h.au(i)`, `h.track()`, `h.region()`, `h.modify()`, `h.allAUs()`, `h.ppqn`, `h.uuid`, `h.rootBox`, `h.api`, `h.editing`, `h.boxGraph`, `h.tempoMap`, `h.rootBoxAdapter`, `h.project`
- E2E verified: 23/23 tests passing

### v1.5.2 (2026-07-02)

- Sanitization: all string parameters sanitized against JS injection
- Documentation: README badges, Docker, SSE, examples, mastering
- CI: GitHub Actions with AST tool count verification

### v1.5.0 (2026-07-01)

- Modular system: 6 MCP tools for patchable modular synthesizer
- PianoMode: 6 MCP tools for piano roll view control
- Freeze/unfreeze: pre-render AU to save CPU
- Preset save/load: export/import AU as base64 preset
- Transfer regions/AUs: deep-copy with dependency tracking
