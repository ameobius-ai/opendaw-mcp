"""Example: Complete mix diagnosis in one call.

analyze_mix combines track + spectrum + stereo + dynamics into a single
prioritized report with master_check for streaming platforms.

This is the recommended single-call analysis for mix/master decisions.
"""

import asyncio
from opendaw_mcp.server import mcp_opendaw_analyze_mix


async def main():
    print("=== Complete Mix Diagnosis ===")
    result = await mcp_opendaw_analyze_mix("my_track.wav")
    print(result[:2000])

    # Result includes:
    # - track: BPM, key, mode, LUFS, duration
    # - spectrum: 7-band frequency balance
    # - stereo: width, phase, L/R balance
    # - dynamics: crest factor, LRA, transients
    # - master_check: Spotify/Apple/YouTube LUFS targets
    # - mix_suggestions: prioritized (HIGH/MEDIUM/LOW/INFO)


if __name__ == "__main__":
    asyncio.run(main())
