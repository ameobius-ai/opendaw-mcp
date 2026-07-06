"""Example: Fugato — fugal passages with subject, answer, and countersubject.

This example demonstrates create_fugato — a fugal passage with imitative
subject entries, answer, countersubject, and episodic material.
"""

import asyncio
import json

from opendaw_mcp.server import mcp_opendaw_create_fugato


async def main():
    # 1. Simple 2-voice fugato with auto-generated subject
    print("=== 2-voice Fugato (auto subject) ===")
    result = await mcp_opendaw_create_fugato(
        root="D",
        scale="minor",
        bars=8,
        octave=4,
        voices=2,
        answer_interval=7,
        answer_mode="real",
        include_countersubject=True,
        include_episode=True,
        velocity=0.6,
    )
    print(result)

    # 2. 3-voice fugato with custom subject (Bach-style)
    print("\n=== 3-voice Fugato (custom subject) ===")
    subject = json.dumps([[0, 0.5], [2, 0.5], [5, 1.0], [4, 0.5], [2, 0.5], [0, 1.0]])
    result = await mcp_opendaw_create_fugato(
        root="A",
        scale="minor",
        subject_notes=subject,
        bars=8,
        octave=4,
        voices=3,
        answer_interval=7,
        answer_mode="real",
        include_countersubject=True,
        countersubject_interval=-3,
        include_episode=True,
        episode_bars=2,
        velocity=0.65,
    )
    print(result)

    # 3. 4-voice fugato with tonal answer
    print("\n=== 4-voice Fugato (tonal answer) ===")
    result = await mcp_opendaw_create_fugato(
        root="G",
        scale="major",
        bars=12,
        octave=4,
        voices=4,
        answer_interval=7,
        answer_mode="tonal",
        include_countersubject=True,
        include_episode=True,
        episode_bars=2,
        velocity=0.6,
    )
    print(result)

    # 4. 2-voice fugato without countersubject (minimal)
    print("\n=== 2-voice Fugato (minimal, no CS) ===")
    result = await mcp_opendaw_create_fugato(
        root="E",
        scale="dorian",
        bars=6,
        octave=3,
        voices=2,
        answer_interval=5,  # answer at fourth
        answer_mode="real",
        include_countersubject=False,
        include_episode=False,
        velocity=0.65,
    )
    print(result)

    # 5. Episode-heavy fugato
    print("\n=== Episode-heavy Fugato ===")
    result = await mcp_opendaw_create_fugato(
        root="C",
        scale="harmonic_minor",
        bars=16,
        octave=4,
        voices=4,
        answer_interval=7,
        answer_mode="real",
        include_countersubject=True,
        include_episode=True,
        episode_bars=4,
        velocity=0.55,
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
