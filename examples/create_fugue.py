"""Example: create_fugue — polyphonic fugue with subject and answer.

Generates a fugue with subject, tonal answer, optional countersubject,
and stretto mode for climactic density.

Usage:
    python3 examples/create_fugue.py
"""
import asyncio
from server import mcp_opendaw_create_synth_track, mcp_opendaw_create_fugue


async def main():
    await mcp_opendaw_create_synth_track("FugueSynth", "vaporisateur")

    # Basic 3-voice fugue in C major
    r = await mcp_opendaw_create_fugue(
        subject="60,62,64,65,64,62,60,57",
        voices=3,
        entry_delay_beats=4,
        answer_type="tonal",
    )
    print(f"Fugue: {r}")

    # 4-voice fugue with countersubject and stretto
    r2 = await mcp_opendaw_create_fugue(
        subject="60,62,64,65,64,62,60,57",
        voices=4,
        countersubject="57,60,62,64,62,60,57,55",
        answer_type="real",
        stretto=True,
    )
    print(f"Stretto fugue: {r2}")


if __name__ == "__main__":
    asyncio.run(main())
