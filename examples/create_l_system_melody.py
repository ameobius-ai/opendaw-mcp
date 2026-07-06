"""Example: L-system melody generation with presets and custom rules.

This example demonstrates create_l_system_melody — a deterministic rewriting
system that generates self-similar, fractal melodies through recursive
production rules.
"""

import asyncio
import json

from opendaw_mcp.server import mcp_opendaw_create_l_system_melody


async def main():
    # 1. Fibonacci word — golden ratio self-similarity
    # A -> AB, B -> A. Produces: A, AB, ABA, ABAAB, ABAABABA...
    # Symbol A = +1 scale step, B = -1 scale step
    # The melody steps up and down with self-similar structure
    print("=== Fibonacci L-system ===")
    result = await mcp_opendaw_create_l_system_melody(
        root="D",
        scale="minor",
        bars=4,
        octave=4,
        preset="fibonacci",
        iterations=6,
        duration=0.25,
        velocity=0.7,
    )
    print(result)

    # 2. Koch snowflake — angular, jagged contour
    # A -> A+A-A-A+A. Symbol A = +1, + = +2, - = -2
    # Produces angular melodic shapes reminiscent of the Koch curve
    print("\n=== Koch snowflake L-system ===")
    result = await mcp_opendaw_create_l_system_melody(
        root="A",
        scale="harmonic_minor",
        bars=4,
        octave=4,
        preset="koch",
        iterations=4,
        duration=0.25,
        velocity=0.65,
    )
    print(result)

    # 3. Dragon curve — complex jagged pattern
    # A -> A+B, B -> A-B. Includes +3/-3 jumps
    print("\n=== Dragon curve L-system ===")
    result = await mcp_opendaw_create_l_system_melody(
        root="E",
        scale="phrygian",
        bars=4,
        octave=3,
        preset="dragon",
        iterations=5,
        duration=0.25,
        velocity=0.7,
    )
    print(result)

    # 4. Cantor set — gaps and self-similar structure
    # A -> ABA, B -> BBB. Symbol A = +2, B = 0 (repeat)
    # Produces melodies with self-similar gaps
    print("\n=== Cantor set L-system ===")
    result = await mcp_opendaw_create_l_system_melody(
        root="G",
        scale="major",
        bars=4,
        octave=4,
        preset="cantor",
        iterations=4,
        duration=0.25,
        velocity=0.6,
    )
    print(result)

    # 5. Sierpinski triangle — binary pattern
    # A -> BA, B -> BA. Both produce BA, creating a binary pattern
    print("\n=== Sierpinski L-system ===")
    result = await mcp_opendaw_create_l_system_melody(
        root="C",
        scale="pentatonic_minor",
        bars=4,
        octave=5,
        preset="sierpinski",
        iterations=5,
        duration=0.25,
        velocity=0.7,
    )
    print(result)

    # 6. Custom L-system — algae growth pattern
    # X -> XY, Y -> X. Custom symbol map: X = +2, Y = -1
    print("\n=== Custom L-system (algae) ===")
    result = await mcp_opendaw_create_l_system_melody(
        root="F",
        scale="dorian",
        bars=4,
        octave=4,
        axiom="X",
        rules=json.dumps({"X": "XY", "Y": "X"}),
        symbol_map=json.dumps({"X": 2, "Y": -1}),
        iterations=7,
        duration=0.25,
        velocity=0.7,
    )
    print(result)

    # 7. Custom L-system with rest symbol
    # A -> AB, B -> ARB. R = rest (skip note, advance position)
    print("\n=== Custom L-system with rests ===")
    result = await mcp_opendaw_create_l_system_melody(
        root="A",
        scale="blues",
        bars=4,
        octave=4,
        axiom="A",
        rules=json.dumps({"A": "AB", "B": "ARB"}),
        symbol_map=json.dumps({"A": 1, "B": -2}),
        rest_symbol="R",
        iterations=5,
        duration=0.25,
        velocity=0.7,
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
