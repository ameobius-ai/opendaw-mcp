# Quick Start

## Prerequisites

- Python 3.11+
- Node.js 20+ (for the openDAW dev server)
- Chromium (Playwright auto-installs)

## Install

=== "pip"

    ```bash
    pip install opendaw-mcp
    ```

=== "Docker"

    ```bash
    docker run -p 3000:3000 ghcr.io/ameobius/opendaw-mcp:1.14.4
    ```

=== "From source"

    ```bash
    git clone https://github.com/ameobius/opendaw-mcp.git
    cd opendaw-mcp
    python -m venv venv && source venv/bin/activate
    pip install -e .
    ```

## Set up the DAW bridge

The MCP server needs a running openDAW instance. The fastest way:

```bash
# Clone openDAW and run the dev server
git clone https://github.com/andremichelle/openDAW.git
cd openDAW/headless-daw
npm install
npx vite --port 5174
```

The DAW will be available at `http://localhost:5174` with COOP/COEP headers
(required for `crossOriginIsolated` and AudioWorklet support).

## Configure

Set the DAW URL (defaults to `http://localhost:5174`):

```bash
export OPENDAW_URL=http://localhost:5174
```

## First track

```python
import asyncio
from opendaw_mcp.server import OpendawServer

async def main():
    server = OpendawServer()
    await server.bridge.start()

    # Set tempo
    await server.mcp_opendaw_set_bpm(bpm=124)

    # Create a synth track
    result = await server.mcp_opendaw_create_synth_track(name="Bass")
    au_index = result["unit_index"]

    # Add notes
    await server.mcp_opendaw_create_notes_batch(
        notes=[
            {"pitch": 36, "position": 0,   "duration": 480},
            {"pitch": 36, "position": 480, "duration": 480},
            {"pitch": 43, "position": 960, "duration": 960},
        ],
        unit_index=au_index,
        track_index=0
    )

    # Add a delay effect
    await server.mcp_opendaw_add_effect(unit_index=au_index, effect_type="Delay")

    # Render to WAV
    await server.mcp_opendaw_render_full(output_path="first_track.wav")

    await server.bridge.stop()

asyncio.run(main())
```

## Using with Claude / MCP clients

Add to your MCP client config:

```json
{
  "mcpServers": {
    "opendaw": {
      "command": "opendaw-mcp",
      "env": {
        "OPENDAW_URL": "http://localhost:5174"
      }
    }
  }
}
```

Once connected, your LLM agent can use all 263 tools directly.

## Using with Hermes Agent

```yaml
# ~/.hermes/config.yaml
mcp:
  opendaw:
    command: opendaw-mcp
    env:
      OPENDAW_URL: http://localhost:5174
```

## Verify it works

```bash
python -c "
import asyncio
from opendaw_mcp.server import OpendawServer

async def test():
    s = OpendawServer()
    await s.bridge.start()
    info = await s.mcp_opendaw_get_project_info()
    print(info)
    await s.bridge.stop()

asyncio.run(test())
"
```

You should see project info with default BPM (120), track count, and AU count.

## Next steps

- [Architecture](architecture.md) — how the bridge works
- [Tool Reference](tools/index.md) — all 263 tools by category
- [Examples](examples.md) — 30 working examples including 8 genre templates
- [DSP Scripts](dsp-scripts.md) — custom audio processing in JavaScript
