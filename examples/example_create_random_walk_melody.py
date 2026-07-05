"""Example: create_random_walk_melody — stochastic melody generation.

Random walk through a scale: each note depends on the previous one,
producing smooth, coherent, yet unpredictable melodies.
"""

import asyncio

from server import mcp_opendaw_create_random_walk_melody


async def main():
    # Ambient wander: smooth stepwise motion in A minor
    result = await mcp_opendaw_create_random_walk_melody(
        root="A",
        scale="minor",
        bars=8,
        max_step=2,
        direction_bias=0.0,
        duration=0.5,
        duration_variation="slight",
        velocity_variation="human",
        boundary_behavior="reflect",
        seed=42,
    )
    print("Ambient wander:", result)

    # Rising tension: bias upward, larger steps
    result = await mcp_opendaw_create_random_walk_melody(
        root="D",
        scale="phrygian",
        bars=4,
        max_step=4,
        direction_bias=0.6,
        duration=0.25,
        velocity=0.8,
        boundary_behavior="reflect",
        seed=99,
    )
    print("Rising tension:", result)

    # Eno-style generative: sparse, slow, gentle
    result = await mcp_opendaw_create_random_walk_melody(
        root="C",
        scale="major",
        bars=16,
        max_step=1,
        duration=1.0,
        duration_variation="dotted",
        rest_probability=0.3,
        velocity=0.5,
        velocity_variation="slight",
        seed=7,
    )
    print("Eno generative:", result)


if __name__ == "__main__":
    asyncio.run(main())
