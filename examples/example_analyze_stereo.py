"""Example: Stereo analysis of audio files.

Demonstrates analyze_stereo — stereo field analysis for mix decisions.
Use after analyze_track and analyze_spectrum for complete mix diagnosis:
- analyze_track: BPM, key, LUFS
- analyze_spectrum: frequency balance (7 bands)
- analyze_stereo: stereo width, L/R balance, phase, mono compatibility
"""

import asyncio
from opendaw_mcp.server import mcp_opendaw_analyze_stereo


async def main():
    print("=== Stereo Analysis ===")
    result = await mcp_opendaw_analyze_stereo("my_track.wav")
    print(result[:1000])

    # The result includes:
    # - stereo_width: Side/Mid RMS ratio (0=mono, 0.5+=wide)
    # - lr_balance: L/R energy difference (-1 to +1)
    # - phase_correlation: -1 to +1 (+1 = mono safe)
    # - mono_compatible: True/False
    # - regions: per-band width (low/mid/high)
    # - mix_suggestions: actionable stereo advice


if __name__ == "__main__":
    asyncio.run(main())
