"""Example: create_soli — ensemble unison passage.

A soli is a section where all instruments play the same melodic line
in rhythmic unison at different octaves. Common in jazz big band,
orchestral tutti, and rock unison riffs.
"""
import asyncio
import sys
sys.path.insert(0, ".")
from server import mcp_opendaw_create_soli


async def main():
    result = await mcp_opendaw_create_soli(
        melody_pattern="0 2 4 2 0 -1 0 3",
        rhythm_pattern="0.5 0.5 0.5 0.5 0.5 0.5 0.5 0.5",
        key_root="C",
        scale_name="major",
        voices=3,
        octave_spread=2,
        velocity=0.7,
        unit_index=0,
        track_index=0,
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
