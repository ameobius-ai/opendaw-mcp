"""Example: Spectral analysis of audio files.

Demonstrates analyze_spectrum — frequency band analysis for mix decisions.
Use after analyze_track to understand tonal balance before EQ decisions.
"""

import asyncio
from opendaw_mcp.server import mcp_opendaw_analyze_spectrum


async def main():
    # Analyze a track's spectral balance
    print("=== Spectral Analysis ===")
    result = await mcp_opendaw_analyze_spectrum("my_track.wav")
    print(result[:1000])

    # The result includes:
    # - 7 ISO frequency bands with RMS, peak, energy %
    # - spectral_centroid_hz: brightness indicator
    # - low_high_ratio: tonal balance
    # - mix_suggestions: actionable EQ advice
    #
    # Workflow:
    # 1. analyze_track("my_track.wav") → bpm, key, lufs
    # 2. analyze_spectrum("my_track.wav") → frequency balance
    # 3. Use mix_suggestions to guide EQ decisions


if __name__ == "__main__":
    asyncio.run(main())
