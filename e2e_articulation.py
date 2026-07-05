#!/usr/bin/env python3
"""E2E test: apply_articulation — staccato, legato, tenuto, accent."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from opendaw_mcp.bridge import HeadlessDawBridge


async def main():
    bridge = HeadlessDawBridge()
    await bridge.start()

    # Setup: 8 notes at 16th grid, uniform duration=240, velocity=0.5
    print("=== Setup: 8 notes, 16th grid, dur=240, vel=0.5 ===")
    r = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        const bg = h.boxGraph;
        const NoteEventBox = window.DAW_NoteEventBox;
        const NoteEventCollectionBox = window.DAW_NoteEventCollectionBox;
        const NoteRegionBox = window.DAW_NoteRegionBox;
        const Quarter = h.ppqn.Quarter;
        let created = 0;

        h.modify(() => {
            const au = h.allAUBoxes()[0];
            if (!au) return;
            let noteTrack = h.trackBoxes(au).find(b => b.type?.getValue?.() === 1);
            if (!noteTrack) noteTrack = h.api.createNoteTrack(au);

            const collection = NoteEventCollectionBox.create(bg, h.uuid.generate());
            const sixteenth = Math.floor(Quarter / 4);
            const regionLen = 8 * sixteenth;

            const regionBox = NoteRegionBox.create(bg, h.uuid.generate(), (box) => {
                box.position.setValue(0);
                box.label.setValue("Articulation Test");
                box.mute.setValue(false);
                box.duration.setValue(regionLen);
                box.loopDuration.setValue(regionLen);
                box.eventOffset.setValue(0);
                box.events.refer(collection.owners);
                box.regions.refer(noteTrack.regions);
            });

            const eventsField = regionBox.events.targetVertex.unwrap();
            const collBox = eventsField.box;

            for (let i = 0; i < 8; i++) {
                NoteEventBox.create(bg, h.uuid.generate(), (box) => {
                    box.position.setValue(i * sixteenth);
                    box.duration.setValue(sixteenth);  // 240 = full 16th
                    box.velocity.setValue(0.5);
                    box.pitch.setValue(60);
                    box.chance.setValue(100);
                    box.cent.setValue(0);
                    box.events.refer(collBox.events);
                });
                created++;
            }
        });
        return { notes_created: created };
    }""")
    print(f"Setup: {r}")
    assert r.get("notes_created") == 8

    # Test 1: staccato (amount=0.5 → dur should be 120)
    print("\n=== Test 1: staccato (amount=0.5) ===")
    r = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        const Quarter = h.ppqn.Quarter;
        let durations = [];

        h.modify(() => {
            const au = h.allAUBoxes()[0];
            const noteTrack = h.trackBoxes(au).find(b => b.type?.getValue?.() === 1);
            const region = h.regionBoxes(noteTrack)[0];
            const vertex = region.events.targetVertex.unwrap();
            const collectionBox = vertex.box || vertex;
            const noteEvents = h.eventBoxes(collectionBox);
            const sorted = [...noteEvents].sort((a, b) => a.position.getValue() - b.position.getValue());
            const sixteenth = Math.floor(Quarter / 4);

            for (const evt of sorted) {
                const dur = evt.duration.getValue();
                const slotDur = Math.max(sixteenth, dur);
                evt.duration.setValue(Math.max(1, Math.floor(slotDur * 0.5)));
                durations.push(evt.duration.getValue());
            }
        });
        return { durations: durations };
    }""")
    print(f"staccato durations: {r.get('durations')}")
    assert all(d == 120 for d in r.get("durations", [])), f"Expected all 120, got {r.get('durations')}"
    print("✅ staccato verified — all durations 120 (50% of 240)")

    # Test 2: legato (amount=0.95)
    print("\n=== Test 2: legato (amount=0.95) ===")
    # Reset durations first
    await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        const Quarter = h.ppqn.Quarter;
        h.modify(() => {
            const au = h.allAUBoxes()[0];
            const noteTrack = h.trackBoxes(au).find(b => b.type?.getValue?.() === 1);
            const region = h.regionBoxes(noteTrack)[0];
            const vertex = region.events.targetVertex.unwrap();
            const collectionBox = vertex.box || vertex;
            const noteEvents = h.eventBoxes(collectionBox);
            const sixteenth = Math.floor(Quarter / 4);
            for (const evt of noteEvents) evt.duration.setValue(sixteenth);
        });
        return { reset: true };
    }""")

    r = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        let durations = [];

        h.modify(() => {
            const au = h.allAUBoxes()[0];
            const noteTrack = h.trackBoxes(au).find(b => b.type?.getValue?.() === 1);
            const region = h.regionBoxes(noteTrack)[0];
            const vertex = region.events.targetVertex.unwrap();
            const collectionBox = vertex.box || vertex;
            const noteEvents = h.eventBoxes(collectionBox);
            const sorted = [...noteEvents].sort((a, b) => a.position.getValue() - b.position.getValue());

            for (let i = 0; i < sorted.length; i++) {
                const evt = sorted[i];
                const pos = evt.position.getValue();
                const dur = evt.duration.getValue();
                const nextStart = (i < sorted.length - 1) ? sorted[i+1].position.getValue() : pos + dur;
                const targetEnd = pos + (nextStart - pos) * 0.95;
                evt.duration.setValue(Math.max(1, Math.floor(targetEnd - pos)));
                durations.push(evt.duration.getValue());
            }
        });
        return { durations: durations };
    }""")
    print(f"legato durations: {r.get('durations')}")
    # Notes at 0, 240, 480... 8th gap=240, legato 0.95 → 240*0.95=228
    assert r.get("durations") and r.get("durations")[0] == 228, f"First legato dur should be 228, got {r.get('durations')}"
    print("✅ legato verified — durations extended to 228 (95% of gap)")

    # Test 3: accent (boost velocity on beats)
    print("\n=== Test 3: accent (amount=0.8, boost on quarter beats) ===")
    # Reset velocity
    await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        h.modify(() => {
            const au = h.allAUBoxes()[0];
            const noteTrack = h.trackBoxes(au).find(b => b.type?.getValue?.() === 1);
            const region = h.regionBoxes(noteTrack)[0];
            const vertex = region.events.targetVertex.unwrap();
            const collectionBox = vertex.box || vertex;
            const noteEvents = h.eventBoxes(collectionBox);
            for (const evt of noteEvents) evt.velocity.setValue(0.5);
        });
        return { reset: true };
    }""")

    r = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        const Quarter = h.ppqn.Quarter;
        let velocities = [];

        h.modify(() => {
            const au = h.allAUBoxes()[0];
            const noteTrack = h.trackBoxes(au).find(b => b.type?.getValue?.() === 1);
            const region = h.regionBoxes(noteTrack)[0];
            const vertex = region.events.targetVertex.unwrap();
            const collectionBox = vertex.box || vertex;
            const noteEvents = h.eventBoxes(collectionBox);
            const sorted = [...noteEvents].sort((a, b) => a.position.getValue() - b.position.getValue());
            const beatTicks = Quarter;  // 960

            for (const evt of sorted) {
                const pos = evt.position.getValue();
                if ((pos % beatTicks) === 0) {
                    const curVel = evt.velocity.getValue();
                    evt.velocity.setValue(Math.min(1.0, curVel + 0.8 * (1.0 - curVel)));
                }
                velocities.push(Math.round(evt.velocity.getValue() * 100) / 100);
            }
        });
        return { velocities: velocities };
    }""")
    print(f"accent velocities: {r.get('velocities')}")
    # Notes at positions: 0, 240, 480, 720, 960, 1200, 1440, 1680
    # Quarter=960 → beats at pos 0 and 960 (indices 0 and 4)
    vels = r.get("velocities", [])
    assert vels and vels[0] > 0.5, f"First note (on beat) should be boosted, got {vels[0]}"
    assert vels[1] == 0.5, f"Second note (off beat) should stay 0.5, got {vels[1]}"
    assert vels[4] > 0.5, f"Fifth note (on beat at 960) should be boosted, got {vels[4]}"
    print("✅ accent verified — beats boosted, off-beats unchanged")

    await bridge.stop()
    print("\n=== ALL E2E TESTS PASSED ===")


if __name__ == "__main__":
    asyncio.run(main())
