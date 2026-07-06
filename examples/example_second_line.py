"""Example: New Orleans second line percussion patterns.

Demonstrates all 5 styles of create_second_line:
- traditional: street parade groove (Charleston hi-hat)
- brass_band: modern brass band (8th-note hats, tom rolls)
- mardi_gras_indian: tribal call-and-response (tom-driven)
- jazz_funeral: dirge → celebration dynamic shift
- bounce: NOLA hip-hop (Triggerman double-time bass, 16th hats)
"""

import asyncio
from opendaw_mcp.server import mcp_opendaw_create_second_line


async def main():
    # 1. Traditional street parade — the original second line
    print("=== Traditional Street Parade ===")
    result = await mcp_opendaw_create_second_line(
        bars=8, style="traditional", velocity=0.8
    )
    print(result[:500])

    # 2. Modern brass band — denser, funkier
    print("\n=== Brass Band ===")
    result = await mcp_opendaw_create_second_line(
        bars=8, style="brass_band", velocity=0.85
    )
    print(result[:500])

    # 3. Mardi Gras Indian — tribal, tom-driven
    print("\n=== Mardi Gras Indian ===")
    result = await mcp_opendaw_create_second_line(
        bars=8, style="mardi_gras_indian", velocity=0.75
    )
    print(result[:500])

    # 4. Jazz funeral — dirge to celebration
    print("\n=== Jazz Funeral (Dirge → Celebration) ===")
    result = await mcp_opendaw_create_second_line(
        bars=8, style="jazz_funeral", velocity=0.7
    )
    print(result[:500])

    # 5. Bounce — NOLA hip-hop Triggerman
    print("\n=== Bounce (Triggerman) ===")
    result = await mcp_opendaw_create_second_line(
        bars=8, style="bounce", velocity=0.9
    )
    print(result[:500])


if __name__ == "__main__":
    asyncio.run(main())
