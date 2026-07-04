"""Screenshot demo for opendaw-mcp — generates a visible DAW state for screenshots/GIFs.

Creates a full track with drums, bass, chords, and effects, then takes a screenshot
of the openDAW UI. Useful for README banners, social media, and docs.

Requirements:
    - openDAW Vite dev server running on localhost:5174
    - The DAW UI must be visible (not fully headless)

Usage:
    python examples/screenshot_demo.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server import OpendawServer


async def main():
    server = OpendawServer()
    await server.bridge.start()

    # ─── Reset to clean state ────────────────────────────────
    await server.mcp_opendaw_reset_project()

    # ─── Set up a house track ────────────────────────────────
    await server.mcp_opendaw_set_bpm(124)
    await server.mcp_opendaw_set_time_signature(4, 4)

    # ─── Drums (Playfield) ───────────────────────────────────
    drums = await server.mcp_opendaw_create_synth_track("Drums")
    drum_au = drums["unit_index"]

    await server.mcp_opendaw_replace_instrument(
        unit_index=drum_au, instrument_type="Playfield"
    )

    # 4-on-floor kick + claps + hats
    await server.mcp_opendaw_create_drum_pattern(
        pattern="x...x...x...x...|....o.......o...|..x...x...x...x.",
        unit_index=drum_au
    )

    # ─── Bass (Vaporisateur) ─────────────────────────────────
    bass = await server.mcp_opendaw_create_synth_track("Bass")
    bass_au = bass["unit_index"]

    await server.mcp_opendaw_set_instrument_param(
        unit_index=bass_au, param_name="filterCutoff", value=0.3
    )
    await server.mcp_opendaw_set_vaporisateur_osc_param(
        unit_index=bass_au, osc_index=0, param="waveform", value=2  # Saw
    )

    # Bass line: F-F-F-F-C-C-G-G (16th notes)
    bass_notes = []
    pattern = [41, 41, 41, 41, 41, 41, 41, 41, 48, 48, 48, 48, 43, 43, 43, 43]
    for i, pitch in enumerate(pattern):
        bass_notes.append({"pitch": pitch, "position": i * 240, "duration": 240, "velocity": 0.9})

    await server.mcp_opendaw_create_notes_batch(
        notes=bass_notes, unit_index=bass_au, track_index=0
    )

    # ─── Chords (Vaporisateur) ───────────────────────────────
    chords = await server.mcp_opendaw_create_synth_track("Chords")
    chord_au = chords["unit_index"]

    await server.mcp_opendaw_set_instrument_param(
        unit_index=chord_au, param_name="filterCutoff", value=0.6
    )
    await server.mcp_opendaw_set_instrument_param(
        unit_index=chord_au, param_name="attack", value=0.3
    )
    await server.mcp_opendaw_set_instrument_param(
        unit_index=chord_au, param_name="release", value=0.5
    )

    # Fm9 - Cm9 - Gm9 - Dm9 (off-beat stabs)
    chord_progressions = [
        ({"chords": ["Fm9", "Cm9", "Gm9", "Dm9"], "duration": 3840}),
    ]
    for prog in chord_progressions:
        await server.mcp_opendaw_create_chord_progression(
            chords=prog["chords"], unit_index=chord_au, track_index=0, duration=prog["duration"]
        )

    # ─── Effects ─────────────────────────────────────────────
    # Reverb on chords
    await server.mcp_opendaw_add_effect(unit_index=chord_au, effect_type="Dattorro")
    await server.mcp_opendaw_set_effect_parameter(
        unit_index=chord_au, effect_index=0, param="decay", value=0.5
    )

    # Delay on bass
    await server.mcp_opendaw_add_effect(unit_index=bass_au, effect_type="Delay")
    await server.mcp_opendaw_set_delay_sync(
        unit_index=bass_au, effect_index=0, sync="1/8"
    )

    # Compressor on drums
    await server.mcp_opendaw_add_effect(unit_index=drum_au, effect_type="Compressor")
    await server.mcp_opendaw_set_effect_parameter(
        unit_index=drum_au, effect_index=0, param="ratio", value=4.0
    )

    # ─── Mix ─────────────────────────────────────────────────
    await server.mcp_opendaw_set_track_volume(unit_index=drum_au, volume_db=-2)
    await server.mcp_opendaw_set_track_volume(unit_index=bass_au, volume_db=-3)
    await server.mcp_opendaw_set_track_volume(unit_index=chord_au, volume_db=-6)
    await server.mcp_opendaw_set_track_panning(unit_index=chord_au, panning=0.2)

    # ─── Song structure markers ──────────────────────────────
    await server.mcp_opendaw_create_song_structure(
        sections=[
            {"name": "Intro", "length": 8},
            {"name": "Verse", "length": 16},
            {"name": "Chorus", "length": 16},
            {"name": "Outro", "length": 8},
        ]
    )

    # ─── Mastering chain ─────────────────────────────────────
    await server.mcp_opendaw_add_mastering_chain(style="balanced")

    # ─── Screenshot ──────────────────────────────────────────
    screenshot = await server.mcp_opendaw_screenshot_daw()
    if screenshot.get("success"):
        img_data = screenshot.get("image", "")
        if img_data:
            output_path = os.path.join(os.path.dirname(__file__), "..", "docs", "assets", "screenshot_demo.png")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            import base64
            with open(output_path, "wb") as f:
                f.write(base64.b64decode(img_data))
            print(f"Screenshot saved: {output_path}")
    else:
        print("Screenshot not available (headless mode)")

    # ─── Render ──────────────────────────────────────────────
    render = await server.mcp_opendaw_render_full(output_path="screenshot_demo.wav")
    if render.get("success"):
        print(f"Rendered: {render.get('file_path', 'screenshot_demo.wav')}")

    # ─── Project info ────────────────────────────────────────
    info = await server.mcp_opendaw_get_project_info()
    print(f"\nProject: {info.get('bpm', '?')} BPM, {info.get('track_count', '?')} tracks, "
          f"{info.get('au_count', '?')} audio units")

    await server.bridge.stop()
    print("\nDone! Track ready for screenshot/GIF capture.")


if __name__ == "__main__":
    asyncio.run(main())
