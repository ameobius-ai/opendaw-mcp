"""Example: create_markov_melody — Markov chain melody generation.

Next interval depends on previous interval via transition probability
matrix. Captures interval-to-interval tendencies — stylistic memory.
"""

import asyncio

from server import mcp_opendaw_create_markov_melody


async def main():
    # Smooth minor melody: default matrix favors stepwise motion
    result = await mcp_opendaw_create_markov_melody(
        root="A",
        scale="minor",
        bars=8,
        octave=4,
        order=1,
        duration=0.5,
        velocity=0.7,
        seed=42,
    )
    print("Smooth minor:", result)

    # Higher order: order 2 captures 2-interval patterns
    result = await mcp_opendaw_create_markov_melody(
        root="D",
        scale="dorian",
        bars=4,
        order=2,
        duration=0.25,
        seed=99,
    )
    print("Dorian order 2:", result)

    # Custom weights: favor ascending steps
    custom_weights = '{"1": {"1": 0.4, "2": 0.3, "-1": 0.2, "3": 0.1}, "-1": {"1": 0.3, "-1": 0.3, "2": 0.2, "-2": 0.2}}'
    result = await mcp_opendaw_create_markov_melody(
        root="C",
        scale="major",
        bars=4,
        interval_weights=custom_weights,
        seed=7,
    )
    print("Custom weights:", result)


if __name__ == "__main__":
    asyncio.run(main())
