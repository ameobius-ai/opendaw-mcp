#!/usr/bin/env python3
"""E2E test for set_marker_repeat MCP tool via bridge.
Tests: add_marker → set_marker_repeat → verify.
Uses correct API: h.timelineBox?.markerTrack + h.markerBoxes(markerTrack)
"""
import asyncio
import sys
sys.path.insert(0, ".")
from server import HeadlessDawBridge

async def main():
    bridge = HeadlessDawBridge()
    await bridge.start()
    try:
        # Add a marker at beat 4
        r1 = await bridge.evaluate("""() => {
            const h = window.DAW_HELPERS;
            const markerTrack = h.timelineBox?.markerTrack;
            if (!markerTrack) return {error: "No markerTrack on timeline"};
            const MarkerBox = window.DAW_MarkerBox;
            h.modify(() => {
                MarkerBox.create(h.boxGraph, h.uuid.generate(), box => {
                    box.position.setValue(4 * 960);
                    box.label.setValue("Test Repeat");
                    box.hue.setValue(190);
                    box.track.refer(markerTrack.markers);
                });
            });
            return {success: true, marker_count: h.markerBoxes(markerTrack).length};
        }""")
        print(f"add_marker: {r1}")

        # Set repeat count to 3
        r2 = await bridge.evaluate("""() => {
            const h = window.DAW_HELPERS;
            const markerTrack = h.timelineBox?.markerTrack;
            if (!markerTrack) return {error: "No markerTrack"};
            const markers = h.markerBoxes(markerTrack);
            if (markers.length === 0) return {error: "No markers"};
            const box = markers[0].box;
            const old = box.plays ? box.plays.getValue() : "no plays field";
            h.modify(() => {
                box.plays.setValue(3);
            });
            return {
                success: true,
                old_repeat: old,
                new_repeat: box.plays.getValue(),
            };
        }""")
        print(f"set_marker_repeat(3): {r2}")

        # Verify
        r3 = await bridge.evaluate("""() => {
            const h = window.DAW_HELPERS;
            const markerTrack = h.timelineBox?.markerTrack;
            const markers = h.markerBoxes(markerTrack);
            return {
                marker_count: markers.length,
                repeat: markers[0].box.plays.getValue(),
                label: markers[0].box.label.getValue(),
            };
        }""")
        print(f"verify: {r3}")

        # Set to 0 (infinite)
        r4 = await bridge.evaluate("""() => {
            const h = window.DAW_HELPERS;
            const markerTrack = h.timelineBox?.markerTrack;
            const markers = h.markerBoxes(markerTrack);
            h.modify(() => {
                markers[0].box.plays.setValue(0);
            });
            return {repeat: markers[0].box.plays.getValue()};
        }""")
        print(f"set_marker_repeat(0=infinite): {r4}")

        if r2.get("new_repeat") == 3 and r3.get("repeat") == 3 and r4.get("repeat") == 0:
            print("\n✅ set_marker_repeat E2E PASSED")
        else:
            print("\n❌ set_marker_repeat E2E FAILED")
            sys.exit(1)
    finally:
        await bridge.stop()

asyncio.run(main())
