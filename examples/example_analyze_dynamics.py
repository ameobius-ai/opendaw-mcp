"""Example: Dynamics analysis of audio files.

Demonstrates analyze_dynamics — crest factor, loudness range, transient density.
Complete analysis pipeline:
1. analyze_track: BPM, key, LUFS
2. analyze_spectrum: 7-band frequency balance
3. analyze_stereo: stereo width, phase, mono compatibility
4. analyze_dynamics: crest factor, LRA, transients, segment contour
"""

import asyncio
from opendaw_mcp.server import mcp_opendaw_analyze_dynamics


async def main():
    print("=== Dynamics Analysis ===")
    result = await mcp_opendaw_analyze_dynamics("my_track.wav")
    print(result[:1000])

    # Result includes:
    # - crest_factor_db: peak/RMS ratio (high=dynamic, low=compressed)
    # - loudness_range_db: LRA (95-10 percentile)
    # - transient_density: spikes/sec (high=percussive)
    # - segments: 10-segment RMS contour
    # - compression_suggestions: actionable dynamics advice


if __name__ == "__main__":
    asyncio.run(main())
