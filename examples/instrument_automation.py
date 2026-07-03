#!/usr/bin/env python3
"""Example: Instrument parameter automation.

Demonstrates automating instrument parameters directly (not just effect params):
- Creates a Vaporisateur synth
- Lists automatable fields (shows which support Pointers.Automation)
- Automates cutoff filter sweep (200 Hz → 8000 Hz → 200 Hz over 8 bars)
- Automates volume fade-in (-24 dB → 0 dB over 4 bars)

This addresses upstream issue #269 (playfield mute automation) — the same
mechanism works for any automatable instrument field, including Playfield
sample-level params via the sample_index parameter.
"""

import asyncio
import json

from server import (
    bridge,
    mcp_opendaw_create_synth_track,
    mcp_opendaw_list_automatable_fields,
    mcp_opendaw_add_instrument_automation,
    mcp_opendaw_add_effect,
    mcp_opendaw_get_effect_chain,
    mcp_opendaw_transport,
)


async def main():
    await bridge.start()

    # 1. Create a Vaporisateur synth
    print("Creating Vaporisateur synth...")
    synth = json.loads(await mcp_opendaw_create_synth_track(
        name="AutoSweep", synth_type="vaporisateur"
    ))
    unit_idx = synth["unit_index"]
    print(f"  Unit {unit_idx}: {synth['synth_class']}")

    # 2. List automatable fields
    print("\nAutomatable fields:")
    fields = json.loads(await mcp_opendaw_list_automatable_fields(unit_index=unit_idx))
    for f in fields["fields"]:
        flag = "✓" if f["automatable"] else "✗"
        print(f"  {flag} {f['name']} = {f['value']}")

    # 3. Add a delay effect for character
    print("\nAdding delay effect...")
    await mcp_opendaw_add_effect(unit_index=unit_idx, effect_type="Delay")

    chain = json.loads(await mcp_opendaw_get_effect_chain(unit_index=unit_idx))
    print(f"  Effects: {[(e['type'], e['enabled']) for e in chain['effects']]}")

    # 4. Automate cutoff: filter sweep 200 → 8000 → 200 Hz over 8 bars
    print("\nAutomating cutoff (filter sweep)...")
    cutoff_auto = json.loads(await mcp_opendaw_add_instrument_automation(
        unit_index=unit_idx,
        parameter_name="cutoff",
        points="[[0, 200], [2, 8000], [4, 200], [6, 8000], [8, 200]]"
    ))
    print(f"  {cutoff_auto}")

    # 5. Automate volume: fade in from -24 dB to 0 dB over 4 bars
    print("\nAutomating volume (fade in)...")
    vol_auto = json.loads(await mcp_opendaw_add_instrument_automation(
        unit_index=unit_idx,
        parameter_name="volume",
        points="[[0, -24], [4, 0], [8, -6]]"
    ))
    print(f"  {vol_auto}")

    # 6. Play to hear the result
    print("\nPlaying...")
    await mcp_opendaw_transport(action="play")

    print("\nDone! The synth now has:")
    print("  - A filter cutoff sweep (200 Hz ↔ 8000 Hz) over 8 bars")
    print("  - A volume fade-in (-24 dB → 0 dB → -6 dB) over 8 bars")
    print("  - A delay effect for atmosphere")

    await bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())
