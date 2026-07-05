"""Example: apply_sidechain — classic pumping/breathing ducking effect."""
import asyncio
import json
import server


async def main():
    await server.bridge.start()

    # 1. Create a synth track (pad/bass to be sidechained)
    result = await server.mcp_opendaw_create_synth_track("Sidechained", "Vaporisateur")
    uid = json.loads(result)["unit_index"]
    print(f"Synth: unit_index={uid}")

    # 2. Apply classic house sidechain — 8 bars, deep pump
    result = await server.mcp_opendaw_apply_sidechain(
        unit_index=uid, bars=8, depth=0.7,
        attack=0.01, release=0.25, kick_interval=1.0,
    )
    data = json.loads(result)
    print(f"House sidechain: {data['total_events']} events, {data['num_kicks']} kicks, depth={data['depth']}")

    # 3. Light techno sidechain — 16 bars, subtle ducking
    result = await server.mcp_opendaw_apply_sidechain(
        unit_index=uid, bars=16, depth=0.4,
        attack=0.02, release=0.4, kick_interval=2.0,
    )
    data = json.loads(result)
    print(f"Techno sidechain: {data['total_events']} events, {data['num_kicks']} kicks, depth={data['depth']}")

    await server.bridge.stop()
    print("\nDone! Classic sidechain ducking applied.")


if __name__ == "__main__":
    asyncio.run(main())
