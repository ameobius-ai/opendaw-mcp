"""Example: Voice exchange — imitative counterpoint between two tracks.

This example demonstrates create_voice_exchange — a contrapuntal technique
where melodic material is passed between voices with transformations.
"""

import asyncio

from opendaw_mcp.server import mcp_opendaw_create_voice_exchange


async def main():
    # 1. Simple imitation — repeat the motif a fifth higher, 2 beats later
    print("=== Imitation (fifth higher, 2 beats later) ===")
    result = await mcp_opendaw_create_voice_exchange(
        unit_index=0,
        source_track=0,
        source_region=0,
        target_track=1,
        target_region=0,
        exchange_mode="imitation",
        interval=7,  # perfect fifth
        time_offset=2.0,
        velocity_factor=0.85,
    )
    print(result)

    # 2. Inversion — mirror the motif around its first pitch
    print("\n=== Inversion (mirror intervals) ===")
    result = await mcp_opendaw_create_voice_exchange(
        unit_index=0,
        source_track=0,
        source_region=0,
        target_track=1,
        target_region=0,
        exchange_mode="inversion",
        interval=0,  # no transpose, just mirror
        time_offset=2.0,
        velocity_factor=0.8,
    )
    print(result)

    # 3. Retrograde — play the motif backwards
    print("\n=== Retrograde (reverse time) ===")
    result = await mcp_opendaw_create_voice_exchange(
        unit_index=0,
        source_track=0,
        source_region=0,
        target_track=1,
        target_region=0,
        exchange_mode="retrograde",
        interval=0,
        time_offset=4.0,  # more space for reversed motif
        velocity_factor=0.8,
    )
    print(result)

    # 4. Retrograde-inversion — reversed AND mirrored (Bach fugue style)
    print("\n=== Retrograde-Inversion ===")
    result = await mcp_opendaw_create_voice_exchange(
        unit_index=0,
        source_track=0,
        source_region=0,
        target_track=1,
        target_region=0,
        exchange_mode="retrograde_inversion",
        interval=5,  # fourth up
        time_offset=4.0,
        velocity_factor=0.75,
    )
    print(result)

    # 5. Augmentation — stretch the motif 2x (slow response)
    print("\n=== Augmentation (2x slower) ===")
    result = await mcp_opendaw_create_voice_exchange(
        unit_index=0,
        source_track=0,
        source_region=0,
        target_track=1,
        target_region=0,
        exchange_mode="augmentation",
        interval=12,  # octave
        time_offset=2.0,
        velocity_factor=0.7,
    )
    print(result)

    # 6. Diminution — compress the motif to half speed (fast response)
    print("\n=== Diminution (half duration) ===")
    result = await mcp_opendaw_create_voice_exchange(
        unit_index=0,
        source_track=0,
        source_region=0,
        target_track=1,
        target_region=0,
        exchange_mode="diminution",
        interval=-5,  # fourth down
        time_offset=1.0,
        velocity_factor=0.85,
    )
    print(result)

    # 7. True voice exchange with swap — voices cross
    print("\n=== True Voice Exchange (swap) ===")
    result = await mcp_opendaw_create_voice_exchange(
        unit_index=0,
        source_track=0,
        source_region=0,
        target_track=1,
        target_region=0,
        exchange_mode="imitation",
        interval=7,
        time_offset=2.0,
        swap=True,  # also transpose source up
        velocity_factor=0.85,
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
