"""AutoGen integration example for opendaw-mcp.

Demonstrates using opendaw-mcp tools with a Microsoft AutoGen agent
to create a full track from a natural language prompt.

Requirements:
    pip install opendaw-mcp autogen-agentchat
    openDAW Vite dev server running on localhost:5174

Usage:
    python examples/autogen_integration.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main():
    from opendaw_mcp.autogen_tools import get_autogen_tools, cleanup

    # Get all tools (or filter by category)
    tools = get_autogen_tools()
    print(f"Loaded {len(tools)} AutoGen tools")

    # Get specific categories
    production_tools = get_autogen_tools(
        categories=["transport", "tracks", "effects", "notes", "orchestration", "export"]
    )
    print(f"Production tools: {len(production_tools)}")

    # ─── Direct tool usage (without agent) ───────────────────
    # This shows the tools work. For full agent usage, connect to your LLM.

    # Set BPM
    set_bpm = next(t for t in tools if t.name == "opendaw_set_bpm")
    result = set_bpm.func(bpm=124)
    print(f"Set BPM: {result}")

    # Create a drum pattern
    drums = next(t for t in tools if t.name == "opendaw_create_drum_pattern")
    result = drums.func(
        pattern="x...x...x...x...|o.......o.....o.|..x...x...x...x.",
        unit_index=0
    )
    print(f"Drums: {result}")

    # Create a synth track
    synth = next(t for t in tools if t.name == "opendaw_create_synth_track")
    result = synth.func(name="Bass")
    print(f"Synth: {result}")

    # Add a chord progression
    chords = next(t for t in tools if t.name == "opendaw_create_chord_progression")
    result = chords.func(
        chords=["Fm", "Cm", "Gm", "Fm"],
        unit_index=1,
        track_index=0,
        duration=1920
    )
    print(f"Chords: {result}")

    # Render
    render = next(t for t in tools if t.name == "opendaw_render_full")
    result = render.func(output_path="autogen_demo.wav")
    print(f"Render: {result}")

    # ─── With AutoGen agent (uncomment when LLM is configured) ──
    # from autogen import AssistantAgent, UserProxyAgent
    #
    # llm_config = {
    #     "model": "gpt-4o-mini",
    #     "api_key": os.environ.get("OPENAI_API_KEY"),
    # }
    #
    # assistant = AssistantAgent(
    #     "producer",
    #     llm_config=llm_config,
    #     tools=tools,
    #     system_message=(
    #         "You are a music producer agent. Use the opendaw tools to "
    #         "create, mix, and render music. Always set BPM first, then "
    #         "create tracks, add effects, and render to WAV."
    #     ),
    # )
    #
    # user = UserProxyAgent("user", human_input_mode="NEVER")
    # user.initiate_chat(
    #     assistant,
    #     message="Create a dark techno track at 130 BPM with a driving kick, "
    #             "hypnotic bass, and reverb on the lead. Render to WAV."
    # )

    await cleanup()
    print("\nDone! Check autogen_demo.wav")


if __name__ == "__main__":
    asyncio.run(main())
