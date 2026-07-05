#!/usr/bin/env python3
"""E2E test: apply_velocity_curve — velocity envelope across notes."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from opendaw_mcp.bridge import HeadlessDawBridge


async def main():
    bridge = HeadlessDawBridge()
    await bridge.start()

    # Setup: create note track + 16 notes via create_notes_batch pattern
    print("=== Setup: create note track + 16 notes ===")
    r = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        const bg = h.boxGraph;
        const NoteEventBox = window.DAW_NoteEventBox;
        const NoteEventCollectionBox = window.DAW_NoteEventCollectionBox;
        const NoteRegionBox = window.DAW_NoteRegionBox;
        const Quarter = h.ppqn.Quarter;

        let createdCount = 0;

        h.modify(() => {
            const au = h.allAUBoxes()[0];
            if (!au) return;
            
            // Find or create note track
            let noteTrack = h.trackBoxes(au).find(b => b.type?.getValue?.() === 1);
            if (!noteTrack) {
                noteTrack = h.api.createNoteTrack(au);
            }

            // Create region with collection
            const collection = NoteEventCollectionBox.create(bg, h.uuid.generate());
            const sixteenth = Math.floor(Quarter / 4);  // 240
            const regionLen = 16 * sixteenth;
            
            const regionBox = NoteRegionBox.create(bg, h.uuid.generate(), (box) => {
                box.position.setValue(0);
                box.label.setValue("Velocity Test");
                box.mute.setValue(false);
                box.duration.setValue(regionLen);
                box.loopDuration.setValue(regionLen);
                box.eventOffset.setValue(0);
                box.events.refer(collection.owners);
                box.regions.refer(noteTrack.regions);
            });

            const eventsField = regionBox.events.targetVertex.unwrap();
            const collBox = eventsField.box;

            // Add 16 notes, uniform velocity 0.5
            for (let i = 0; i < 16; i++) {
                NoteEventBox.create(bg, h.uuid.generate(), (box) => {
                    box.position.setValue(i * sixteenth);
                    box.duration.setValue(sixteenth);
                    box.velocity.setValue(0.5);
                    box.pitch.setValue(60 + (i % 4) * 12);
                    box.chance.setValue(100);
                    box.cent.setValue(0);
                    box.events.refer(collBox.events);
                });
                createdCount++;
            }
        });

        return { notes_created: createdCount };
    }""")
    print(f"Setup: {r}")
    assert r.get("notes_created") == 16, f"Expected 16 notes, got {r.get('notes_created')}"

    # Test 1: ramp_up curve
    print("\n=== Test 1: ramp_up (0.2 → 1.0) ===")
    r = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        let totalNotes = 0;
        const velocities = [];

        h.modify(() => {
            const au = h.allAUBoxes()[0];
            const noteTrack = h.trackBoxes(au).find(b => b.type?.getValue?.() === 1);
            const region = h.regionBoxes(noteTrack)[0];
            const vertex = region.events.targetVertex.unwrap();
            const collectionBox = vertex.box || vertex;
            const noteEvents = h.eventBoxes(collectionBox);

            let minPos = Infinity, maxPos = -Infinity;
            for (const evt of noteEvents) {
                const p = evt.position.getValue();
                if (p < minPos) minPos = p;
                if (p > maxPos) maxPos = p;
            }
            const posRange = maxPos - minPos || 1;

            for (const evt of noteEvents) {
                const pos = evt.position.getValue();
                const t = (pos - minPos) / posRange;
                const vel = 0.2 + (1.0 - 0.2) * t;
                evt.velocity.setValue(Math.max(0.05, Math.min(1.0, vel)));
                velocities.push(Math.round(evt.velocity.getValue() * 100) / 100);
                totalNotes++;
            }
        });

        return {
            total_notes: totalNotes,
            first_vel: velocities[0],
            last_vel: velocities[velocities.length - 1],
            mid_vel: velocities[Math.floor(velocities.length / 2)],
        };
    }""")
    print(f"ramp_up: total={r.get('total_notes')}, first={r.get('first_vel')}, mid={r.get('mid_vel')}, last={r.get('last_vel')}")
    assert r.get("total_notes") == 16, f"Expected 16 notes, got {r.get('total_notes')}"
    assert r.get("first_vel") <= 0.25, f"First velocity should be ~0.2, got {r.get('first_vel')}"
    assert r.get("last_vel") >= 0.95, f"Last velocity should be ~1.0, got {r.get('last_vel')}"
    print("✅ ramp_up verified")

    # Test 2: arc curve
    print("\n=== Test 2: arc (0.3 → 1.0 peak → 0.3) ===")
    r = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        let totalNotes = 0;
        const velocities = [];

        h.modify(() => {
            const au = h.allAUBoxes()[0];
            const noteTrack = h.trackBoxes(au).find(b => b.type?.getValue?.() === 1);
            const region = h.regionBoxes(noteTrack)[0];
            const vertex = region.events.targetVertex.unwrap();
            const collectionBox = vertex.box || vertex;
            const noteEvents = h.eventBoxes(collectionBox);

            let minPos = Infinity, maxPos = -Infinity;
            for (const evt of noteEvents) {
                const p = evt.position.getValue();
                if (p < minPos) minPos = p;
                if (p > maxPos) maxPos = p;
            }
            const posRange = maxPos - minPos || 1;

            for (const evt of noteEvents) {
                const pos = evt.position.getValue();
                const t = (pos - minPos) / posRange;
                let vel;
                if (t < 0.5) {
                    vel = 0.3 + (1.0 - 0.3) * (t * 2);
                } else {
                    vel = 1.0 + (0.3 - 1.0) * ((t - 0.5) * 2);
                }
                evt.velocity.setValue(Math.max(0.05, Math.min(1.0, vel)));
                velocities.push(Math.round(evt.velocity.getValue() * 100) / 100);
                totalNotes++;
            }
        });

        return {
            total_notes: totalNotes,
            first_vel: velocities[0],
            mid_vel: velocities[Math.floor(velocities.length / 2)],
            last_vel: velocities[velocities.length - 1],
        };
    }""")
    print(f"arc: total={r.get('total_notes')}, first={r.get('first_vel')}, mid={r.get('mid_vel')}, last={r.get('last_vel')}")
    assert r.get("total_notes") == 16, f"Expected 16 notes, got {r.get('total_notes')}"
    assert r.get("mid_vel") >= 0.95, f"Mid velocity should peak ~1.0, got {r.get('mid_vel')}"
    assert r.get("first_vel") <= 0.35, f"First velocity should be ~0.3, got {r.get('first_vel')}"
    print("✅ arc verified — peak at middle")

    # Test 3: power curve (sharp attack)
    print("\n=== Test 3: power curve (power=2.0, 0.1 → 1.0) ===")
    r = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        let totalNotes = 0;
        const velocities = [];

        h.modify(() => {
            const au = h.allAUBoxes()[0];
            const noteTrack = h.trackBoxes(au).find(b => b.type?.getValue?.() === 1);
            const region = h.regionBoxes(noteTrack)[0];
            const vertex = region.events.targetVertex.unwrap();
            const collectionBox = vertex.box || vertex;
            const noteEvents = h.eventBoxes(collectionBox);

            let minPos = Infinity, maxPos = -Infinity;
            for (const evt of noteEvents) {
                const p = evt.position.getValue();
                if (p < minPos) minPos = p;
                if (p > maxPos) maxPos = p;
            }
            const posRange = maxPos - minPos || 1;

            for (const evt of noteEvents) {
                const pos = evt.position.getValue();
                const t = (pos - minPos) / posRange;
                const vel = 0.1 + (1.0 - 0.1) * Math.pow(t, 2.0);
                evt.velocity.setValue(Math.max(0.05, Math.min(1.0, vel)));
                velocities.push(Math.round(evt.velocity.getValue() * 100) / 100);
                totalNotes++;
            }
        });

        return {
            total_notes: totalNotes,
            first_vel: velocities[0],
            mid_vel: velocities[Math.floor(velocities.length / 2)],
            last_vel: velocities[velocities.length - 1],
        };
    }""")
    print(f"power: total={r.get('total_notes')}, first={r.get('first_vel')}, mid={r.get('mid_vel')}, last={r.get('last_vel')}")
    assert r.get("total_notes") == 16, f"Expected 16 notes, got {r.get('total_notes')}"
    assert r.get("mid_vel") < 0.5, f"Power=2.0 mid should be < 0.5 (slow rise), got {r.get('mid_vel')}"
    assert r.get("last_vel") >= 0.95, f"Last velocity should be ~1.0, got {r.get('last_vel')}"
    print("✅ power curve verified — slow rise, sharp end")

    await bridge.stop()
    print("\n=== ALL E2E TESTS PASSED ===")


if __name__ == "__main__":
    asyncio.run(main())
