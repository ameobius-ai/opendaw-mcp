"""CrewAI integration example for opendaw-mcp.

Demonstrates using opendaw-mcp tools with a CrewAI crew
to create a full track from a natural language task.

Requirements:
    pip install opendaw-mcp crewai
    openDAW Vite dev server running on localhost:5174

Usage:
    python examples/crewai_integration.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main():
    from opendaw_mcp.crewai_tools import get_crewai_tools, cleanup

    tools = get_crewai_tools()
    print(f"Loaded {len(tools)} CrewAI tools")

    # Get specific categories
    production_tools = get_crewai_tools(
        categories=["transport", "tracks", "effects", "notes", "orchestration", "export"]
    )
    print(f"Production tools: {len(production_tools)}")

    # ─── Direct tool usage (without crew) ────────────────────
    set_bpm = next(t for t in tools if t.name == "opendaw_set_bpm")
    result = set_bpm._run(bpm=124)
    print(f"Set BPM: {result}")

    drums = next(t for t in tools if t.name == "opendaw_create_drum_pattern")
    result = drums._run(
        pattern="x...x...x...x...|o.......o.....o.|..x...x...x...x.",
        unit_index=0
    )
    print(f"Drums: {result}")

    synth = next(t for t in tools if t.name == "opendaw_create_synth_track")
    result = synth._run(name="Bass")
    print(f"Synth: {result}")

    chords = next(t for t in tools if t.name == "opendaw_create_chord_progression")
    result = chords._run(
        chords=["Fm", "Cm", "Gm", "Fm"],
        unit_index=1,
        track_index=0,
        duration=1920
    )
    print(f"Chords: {result}")

    render = next(t for t in tools if t.name == "opendaw_render_full")
    result = render._run(output_path="crewai_demo.wav")
    print(f"Render: {result}")

    # ─── With CrewAI crew (uncomment when LLM is configured) ──
    # from crewai import Agent, Task, Crew, LLM
    #
    # llm = LLM(model="gpt-4o-mini")
    #
    # producer = Agent(
    #     role="Music Producer",
    #     goal="Create and mix music tracks using opendaw tools",
    #     backstory="Expert producer with 20 years of experience in electronic music",
    #     tools=tools,
    #     llm=llm,
    #     verbose=True,
    # )
    #
    # task = Task(
    #     description="Create a dark techno track at 130 BPM with a driving kick, "
    #                 "hypnotic bass line, and reverb on the lead. Render to WAV.",
    #     agent=producer,
    #     expected_output="A WAV file with the finished techno track",
    # )
    #
    # crew = Crew(agents=[producer], tasks=[task], verbose=True)
    # result = crew.kickoff()
    # print(result)

    await cleanup()
    print("\nDone! Check crewai_demo.wav")


if __name__ == "__main__":
    asyncio.run(main())
