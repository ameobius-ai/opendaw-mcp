"""LangChain integration example for opendaw-mcp.

Demonstrates using opendaw-mcp tools with a LangChain agent
to create a full track from a natural language prompt.

Requirements:
    pip install opendaw-mcp langchain langchain-openai
    openDAW Vite dev server running on localhost:5174

Usage:
    python examples/langchain_integration.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main():
    from opendaw_mcp.langchain_tools import OpendawToolkit

    toolkit = OpendawToolkit(daw_url="http://localhost:5174")

    # Get all tools (or filter by category)
    tools = toolkit.get_tools()
    print(f"Loaded {len(tools)} LangChain tools")

    # Get specific categories only
    production_tools = toolkit.get_tools(
        categories=["transport", "tracks", "effects", "notes", "orchestration", "export"]
    )
    print(f"Production tools: {len(production_tools)}")

    # ─── Direct tool usage (without agent) ───────────────────
    # This shows the tools work. For full agent usage, connect to your LLM.

    # Set BPM
    set_bpm = next(t for t in tools if t.name == "opendaw_set_bpm")
    result = set_bpm.invoke({"bpm": 124})
    print(f"Set BPM: {result}")

    # Create a drum pattern
    drums = next(t for t in tools if t.name == "opendaw_create_drum_pattern")
    result = drums.invoke({
        "pattern": "x...x...x...x...|o.......o.....o.|..x...x...x...x.",
        "unit_index": 0
    })
    print(f"Drums: {result}")

    # Create a synth track
    synth = next(t for t in tools if t.name == "opendaw_create_synth_track")
    result = synth.invoke({"name": "Bass"})
    print(f"Synth: {result}")

    # Add a chord progression
    chords = next(t for t in tools if t.name == "opendaw_create_chord_progression")
    result = chords.invoke({
        "chords": ["Fm", "Cm", "Gm", "Fm"],
        "unit_index": 1,
        "track_index": 0,
        "duration": 1920
    })
    print(f"Chords: {result}")

    # Render
    render = next(t for t in tools if t.name == "opendaw_render_full")
    result = render.invoke({"output_path": "langchain_demo.wav"})
    print(f"Render: {result}")

    # ─── With LangChain agent (uncomment when LLM is configured) ──
    # from langchain_openai import ChatOpenAI
    # from langchain.agents import create_react_agent, AgentExecutor
    #
    # llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    # agent = create_react_agent(llm, tools, prompt)
    # executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    #
    # response = executor.invoke({
    #     "input": "Create a dark techno track at 130 BPM with a driving kick, "
    #              "hypnotic bass line, and reverb on the lead. Render to WAV."
    # })
    # print(response["output"])

    await toolkit.server.bridge.stop()
    print("\nDone! Check langchain_demo.wav")


if __name__ == "__main__":
    asyncio.run(main())
