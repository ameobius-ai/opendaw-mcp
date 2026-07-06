"""Example: create_call_and_response — musical dialogue.

Call-and-response is the most fundamental musical conversation:
a leader phrase (call) followed by a response phrase.
This example creates 4 pairs with echo response in C major.
"""
import asyncio
import sys
sys.path.insert(0, ".")
from server import mcp_opendaw_create_call_and_response


async def main():
    result = await mcp_opendaw_create_call_and_response(
        call_pattern="0 2 4 7 4 2",
        call_rhythm="0.5 0.5 0.5 1.0 0.5 0.5",
        response_type="echo",
        key_root="C",
        scale_name="major",
        pairs=4,
        gap_beats=1.0,
        unit_index=0,
        track_index=0,
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
