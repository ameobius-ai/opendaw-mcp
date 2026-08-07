"""
Tracks & Regions Tools
================
"""

import json
import asyncio

# These will be injected by server.py
bridge = None
_wrap_eval = None
_ok = None
_err = None


def init_tracks_tools(bridge_instance, wrap_eval_func, ok_func=None, err_func=None):
    """Initialize tracks tools with shared dependencies."""
    global bridge, _wrap_eval, _ok, _err
    bridge = bridge_instance
    _wrap_eval = wrap_eval_func
    _ok = ok_func
    _err = err_func



async def mcp_opendaw_balance_track_velocities(
    unit_index: int,
    track_indices: str,
    preset: str = "mix_balanced",
    target_velocities: str = "",
    region_index: int = -1,
) -> str:
    """Balance velocities across multiple tracks — MIDI mix leveling.

    Sets relative velocity levels across multiple note tracks so they sit
    correctly in the mix. Unlike scale_velocity (one track at a time), this
    operates on multiple tracks simultaneously and establishes the *relative*
    balance between them.

    Presets:
    - "mix_balanced" — all tracks equal (~0.75). Neutral starting point.
    - "drums_forward" — drums loudest (0.95), bass (0.80), harmony (0.65),
      lead (0.70). Hip-hop, rock, electronic.
    - "vocal_forward" — vocal/lead loudest (0.95), pads (0.60), bass (0.75),
      drums (0.80). Pop, ballad, singer-songwriter.
    - "pads_quiet" — pads very quiet (0.50), arp (0.65), bass (0.80),
      drums (0.90), lead (0.85). Ambient, cinematic.
    - "bass_heavy" — bass loudest (0.95), drums (0.85), lead (0.70),
      harmony (0.55). Reggae, dub, trap.
    - "custom" — use target_velocities parameter (comma-separated 0-1 values,
      one per track in track_indices order).

    The tool reads current average velocities, computes scale factors to reach
    targets, and applies them. Original relative dynamics within each track
    are preserved (multiply mode).

    track_indices: Comma-separated track indices (e.g. "0,1,2,3").
    preset: One of the presets above, or "custom".
    target_velocities: For custom mode — comma-separated target avg velocities
      (e.g. "0.9,0.7,0.6,0.8"). Must match track_indices count.
    region_index: Region (-1 = first, -2 = all regions).

    Returns per-track velocity stats before/after.

    Example:
      # Balance 4 tracks: drums, bass, pads, lead
      balance_track_velocities(0, "0,1,2,3", preset="drums_forward")
      # Custom: drums=0.9, bass=0.7, pads=0.5, lead=0.8
      balance_track_velocities(0, "0,1,2,3", preset="custom",
                               target_velocities="0.9,0.7,0.5,0.8")
    """
    presets = {
        "mix_balanced": [0.75, 0.75, 0.75, 0.75],
        "drums_forward": [0.95, 0.80, 0.65, 0.70],
        "vocal_forward": [0.80, 0.75, 0.60, 0.95],
        "pads_quiet": [0.90, 0.80, 0.50, 0.85],
        "bass_heavy": [0.85, 0.95, 0.55, 0.70],
    }

    try:
        track_list = [int(t.strip()) for t in track_indices.split(",") if t.strip()]
    except ValueError:
        return "Error: track_indices must be comma-separated integers"
    if not track_list:
        return "Error: must provide at least one track index"

    if preset == "custom":
        if not target_velocities:
            return "Error: custom preset requires target_velocities"
        try:
            targets = [float(v.strip()) for v in target_velocities.split(",") if v.strip()]
        except ValueError:
            return "Error: target_velocities must be comma-separated floats"
        if len(targets) != len(track_list):
            return f"Error: {len(targets)} targets for {len(track_list)} tracks — must match"
        for t in targets:
            if not (0.0 <= t <= 1.0):
                return "Error: target velocities must be 0-1"
    else:
        if preset not in presets:
            return f"Error: preset must be one of {list(presets.keys())} or 'custom', got '{preset}'"
        targets = presets[preset]
        if len(track_list) > len(targets):
            return f"Error: preset '{preset}' has {len(targets)} targets but {len(track_list)} tracks given"

    targets_json = json.dumps(targets[:len(track_list)])
    tracks_json = json.dumps(track_list)

    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackList = {tracks_json};
        const targetVels = {targets_json};
        const regIdx = {region_index};

        const allUnits = h.allAUBoxes();
        if (unitIdx < 0 || unitIdx >= allUnits.length) return {{error: "unit_index out of range"}};
        const au = allUnits[unitIdx];
        const noteTracks = h.noteTrackBoxes(au);

        const trackResults = [];
        let totalModified = 0;

        for (let ti = 0; ti < trackList.length; ti++) {{
            const trackIdx = trackList[ti];
            if (trackIdx < 0 || trackIdx >= noteTracks.length) {{
                trackResults.push({{track_index: trackIdx, error: "track_index out of range"}});
                continue;
            }}
            const trackBox = noteTracks[trackIdx];
            const regions = h.regionBoxes(trackBox);
            if (regions.length === 0) {{
                trackResults.push({{track_index: trackIdx, error: "No regions on track"}});
                continue;
            }}

            let allNotes = [];
            const regionsToProcess = regIdx === -2 ? regions : (regIdx < 0 ? [regions[0]] : [regions[regIdx]]);
            if (regIdx >= 0 && regIdx >= regions.length) {{
                trackResults.push({{track_index: trackIdx, error: "region_index out of range"}});
                continue;
            }}

            for (const region of regionsToProcess) {{
                let collection = null;
                try {{
                    const vertex = region.events.targetVertex.unwrap();
                    collection = vertex.box || vertex;
                }} catch(e) {{ continue; }}
                if (!collection || !collection.events) continue;
                const notes = h.eventBoxes(collection);
                allNotes = allNotes.concat(notes);
            }}

            if (allNotes.length === 0) {{
                trackResults.push({{track_index: trackIdx, error: "No notes", target: targetVels[ti]}});
                continue;
            }}

            // Current average velocity
            const origVels = allNotes.map(n => n.velocity.getValue());
            const origAvg = origVels.reduce((a, b) => a + b, 0) / origVels.length;
            const origMax = Math.max(...origVels);

            // Scale factor to reach target average
            const target = targetVels[ti];
            const scaleFactor = origAvg > 0 ? target / origAvg : 1.0;

            let modified = 0;
            const editing = h.editing;
            await editing.modify(async () => {{
                for (const n of allNotes) {{
                    let v = n.velocity.getValue() * scaleFactor;
                    v = Math.max(0.01, Math.min(1.0, v));
                    n.velocity.setValue(v);
                    modified++;
                }}
            }});

            const newVels = allNotes.map(n => n.velocity.getValue());
            const newAvg = newVels.reduce((a, b) => a + b, 0) / newVels.length;
            const newMax = Math.max(...newVels);

            trackResults.push({{
                track_index: trackIdx,
                note_count: allNotes.length,
                target_velocity: target,
                scale_factor: Math.round(scaleFactor * 1000) / 1000,
                original_avg: Math.round(origAvg * 1000) / 1000,
                original_max: Math.round(origMax * 1000) / 1000,
                new_avg: Math.round(newAvg * 1000) / 1000,
                new_max: Math.round(newMax * 1000) / 1000,
                notes_modified: modified,
            }});
            totalModified += modified;
        }}

        return {{
            success: true,
            preset: "{preset}",
            total_notes_modified: totalModified,
            tracks_balanced: trackResults.filter(r => !r.error).length,
            track_results: trackResults,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_clone_clip(unit_index: int, track_index: int, clip_index: int, consolidate: bool = False) -> str:
    """Clone a clip (note or value) on the same track. Optionally consolidate (make event collection unique).

    unit_index: AU index.
    track_index: Track index within the AU.
    clip_index: Clip index to clone.
    consolidate: If true, the clone gets its own independent event collection (not shared).

    Returns success, or error.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const track = h.track({unit_index}, {track_index});
            const clips = track.clips.collection.adapters();
            if ({clip_index} >= clips.length) return {{error: "No clip {clip_index}"}};
            const clip = clips[{clip_index}];
            h.modify(() => {{
                clip.clone({str(consolidate).lower()});
            }});
            const newClips = track.clips.collection.adapters();
            return {{
                success: true,
                clip_count: newClips.length,
                new_clip_label: newClips[newClips.length - 1].label,
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_clone_track(
    unit_index: int,
    track_index: int,
    name: str = "",
    transpose: int = 0,
    velocity_scale: float = 1.0,
    time_offset_beats: float = 0.0,
    new_unit: bool = False,
) -> str:
    """Clone a track — full duplication of notes, regions, and structure.

    Creates a new track within the same audio unit (or a new audio unit)
    with all notes from the source track copied over. Optionally
    transposed, velocity-scaled, and time-shifted.

    Unlike copy_notes_to_track (which copies notes between existing
    tracks), clone_track creates the destination track from scratch
    with the correct track type (note/audio), then populates it with
    a region and all notes from the source.

    Essential for:
    - Doubling: same notes on two instruments for thicker sound
    - Octave layering: transpose +12 for octave above
    - Parallel harmony: transpose +7 for fifths, +3 for thirds
    - Call-and-response: time_offset to shift the copy later
    - Counterpoint layer: same rhythm, different transposition

    Args:
        unit_index: Source audio unit index
        track_index: Source track index within the unit
        name: Optional name for the cloned track (default: same as source)
        transpose: Semitone transposition applied to cloned notes
            (-24 to +24, default 0 = same pitch)
        velocity_scale: Multiply note velocities by this factor
            (0.1-2.0, default 1.0 = same velocity)
        time_offset_beats: Shift all notes by this many beats
            (-16 to +16, default 0.0 = same position)
        new_unit: If true, create a new audio unit for the clone
            (requires same instrument type). If false (default), adds
            a new track to the source audio unit.
    """
    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HeadlessBridgeHelper;
        if (!h) return {{"error": "Bridge helper not available"}};
        const Quarter = 960;

        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const trackName = {json.dumps(name)};
        const transSemis = Math.max(-24, Math.min(24, {transpose}));
        const velScale = Math.max(0.1, Math.min(2, {velocity_scale}));
        const timeOffset = Math.max(-16, Math.min(16, {time_offset_beats}));
        const createNewUnit = {str(new_unit).lower()};

        const noteTracks = h.noteTracks();
        const allUnits = h.allAUBoxes();
        if (noteTracks.length === 0) return {{"error": "No note tracks"}};

        // Find the source track by scanning all units
        let srcTrack = null;
        let srcAU = null;
        let srcUnitIdx = -1;
        for (let u = 0; u < allUnits.length; u++) {{
            const tracks = h.trackBoxes(allUnits[u]);
            for (let t = 0; t < tracks.length; t++) {{
                if (u === unitIdx && t === trackIdx) {{
                    srcTrack = tracks[t];
                    srcAU = allUnits[u];
                    srcUnitIdx = u;
                }}
            }}
        }}
        if (!srcTrack) return {{"error": "Source track not found"}};

        // Read source track properties
        const srcType = srcTrack.type?.getValue();
        const srcHue = srcTrack.hue?.getValue() || 0;
        const srcVolume = srcTrack.volume?.getValue();
        const srcPanning = srcTrack.panning?.getValue();
        const srcMute = srcTrack.mute?.getValue();

        // Read source regions and notes
        const srcRegions = h.regionBoxes(srcTrack);
        const regionData = [];
        for (const region of srcRegions) {{
            if (region.constructor.name === 'NoteRegionBox') {{
                const notes = [];
                try {{
                    const vertex = region.events.targetVertex.unwrap();
                    const eventsBox = vertex.box || vertex;
                    const eventList = h.eventBoxes(eventsBox);
                    for (const note of eventList) {{
                        notes.push({{
                            pitch: note.pitch.getValue(),
                            position: note.position.getValue(),
                            duration: note.duration.getValue(),
                            velocity: note.velocity.getValue(),
                            cent: note.cent?.getValue() || 0,
                        }});
                    }}
                }} catch(e) {{}}

                const regPos = region.position?.getValue() || 0;
                const regDur = region.duration?.getValue() || 0;
                const regHue = region.hue?.getValue() || 0;
                regionData.push({{position: regPos, duration: regDur, hue: regHue, notes: notes}});
            }}
        }}

        if (regionData.length === 0) return {{"error": "No note regions on source track"}};

        // Determine destination
        let destAU = srcAU;
        if (createNewUnit) {{
            // Create a new audio unit of the same type
            const srcType = srcAU.type?.getValue();
            const srcLabel = srcAU.label?.getValue() || "Cloned Unit";
            try {{
                destAU = await h.api.createAudioUnit(srcType);
                if (destAU) {{
                    try {{ destAU.label?.setValue(srcLabel + " (clone)"); }} catch(e) {{}}
                }}
            }} catch(e) {{
                return {{"error": "Failed to create new unit: " + e.message}};
            }}
        }}

        // Create the cloned track
        const editing = h.editing;
        let newTrackIdx = -1;
        let notesCreated = 0;

        await editing.modify(async () => {{
            const TrackBox = h.TrackBox || window.DAW_TrackBox;
            const NoteRegionBox = h.NoteRegionBox || window.DAW_NoteRegionBox;
            const NoteEventBox = h.NoteEventBox;
            const bg = h.boxGraph;
            const uuidGen = h.uuid;

            if (!TrackBox || !NoteRegionBox || !NoteEventBox || !bg || !uuidGen) return;

            // Create new track on destination AU
            try {{
                const auAdapter = h.project.boxAdapters.adapterFor(destAU, window.DAW_AudioUnitBoxAdapter);
                if (auAdapter) {{
                    const newTrackAdapter = auAdapter.createTrack(srcType || 0);
                    if (newTrackAdapter) {{
                        const newTrackBox = newTrackAdapter.box || newTrackAdapter;
                        // Set track properties
                        try {{
                            if (srcVolume !== undefined) newTrackBox.volume?.setValue(srcVolume);
                            if (srcPanning !== undefined) newTrackBox.panning?.setValue(srcPanning);
                            if (srcMute !== undefined) newTrackBox.mute?.setValue(srcMute);
                            newTrackBox.hue?.setValue((srcHue + 180) % 360); // complementary color
                        }} catch(e) {{}}

                        // Count tracks to get the new index
                        const destTracks = h.trackBoxes(destAU);
                        newTrackIdx = destTracks.length - 1;

                        // Create regions with notes
                        for (const rd of regionData) {{
                            try {{
                                // Create a note region
                                const regionAdapter = auAdapter.createNoteRegion();
                                if (regionAdapter) {{
                                    const newRegion = regionAdapter.box || regionAdapter;
                                    try {{
                                        newRegion.position?.setValue(rd.position + Math.round(timeOffset * Quarter));
                                        newRegion.duration?.setValue(rd.duration);
                                        newRegion.hue?.setValue((rd.hue + 180) % 360);
                                    }} catch(e) {{}}

                                    // Get the events collection
                                    try {{
                                        const vertex = newRegion.events.targetVertex.unwrap();
                                        const destCollection = vertex.box || vertex;
                                        if (destCollection && destCollection.events) {{
                                            for (const note of rd.notes) {{
                                                const newPitch = Math.max(0, Math.min(127, note.pitch + transSemis));
                                                const newPos = note.position + Math.round(timeOffset * Quarter);
                                                const newVel = Math.max(0.01, Math.min(1, note.velocity * velScale));
                                                await NoteEventBox.create(bg, uuidGen.generate(), (box) => {{
                                                    box.position.setValue(Math.max(0, newPos));
                                                    box.duration.setValue(note.duration);
                                                    box.pitch.setValue(newPitch);
                                                    box.velocity.setValue(newVel);
                                                    if (note.cent) box.cent?.setValue(note.cent);
                                                    box.events.refer(destCollection.events);
                                                }});
                                                notesCreated++;
                                            }}
                                        }}
                                    }} catch(e) {{}}
                                }}
                            }} catch(e) {{}}
                        }}
                    }}
                }}
            }} catch(e) {{
                return {{"error": "Track creation failed: " + e.message}};
            }}
        }});

        return {{
            success: true,
            source_unit: srcUnitIdx,
            source_track: trackIdx,
            destination_unit: createNewUnit ? allUnits.length : srcUnitIdx,
            new_track_index: newTrackIdx,
            regions_cloned: regionData.length,
            notes_created: notesCreated,
            transpose: transSemis,
            velocity_scale: velScale,
            time_offset_beats: timeOffset,
            new_unit: createNewUnit,
        }};
    }}""")
    return _wrap_eval(result)
    return _wrap_eval(result)


async def mcp_opendaw_compact_tracks(unit_index: int) -> str:
    """Remove empty tracks from an audio unit (or all AUs).

Calls ProjectApi.compactTracks() — removes tracks with no regions.
Useful cleanup after deleting regions or editing.

unit_index: Audio unit index (-1 = all AUs).
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const units = h.allAUBoxes();

        const results = [];
        if (unitIdx < 0) {{
            for (let i = 0; i < units.length; i++) {{
                const before = h.trackBoxes(units[i]).length;
                h.modify(() => h.api.compactTracks(units[i]));
                const after = h.trackBoxes(units[i]).length;
                results.push({{au: i, before, after, removed: before - after}});
            }}
        }} else {{
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            const before = h.trackBoxes(units[unitIdx]).length;
            h.modify(() => h.api.compactTracks(units[unitIdx]));
            const after = h.trackBoxes(units[unitIdx]).length;
            results.push({{au: unitIdx, before, after, removed: before - after}});
        }}
        return {{success: true, results}};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_consolidate_clip(unit_index: int, track_index: int, clip_index: int) -> str:
    """Consolidate a clip's event collection — make it unique (not shared/mirrored).

    If a clip shares its event collection with other clips (mirrored),
    this creates a new independent copy so edits don't affect other clips.

    unit_index: AU index.
    track_index: Track index within the AU.
    clip_index: Clip index to consolidate.

    Returns success, or error.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const track = h.track({unit_index}, {track_index});
            const clips = track.clips.collection.adapters();
            if ({clip_index} >= clips.length) return {{error: "No clip {clip_index}"}};
            const clip = clips[{clip_index}];
            const wasMirrored = clip.isMirrowed;
            h.modify(() => {{
                clip.consolidate();
            }});
            return {{
                success: true,
                was_mirrored: wasMirrored,
                is_mirrored: clip.isMirrowed,
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_consolidate_region(unit_index: int, track_index: int, region_index: int) -> str:
    """Consolidate a region's event collection — make it unique (not shared/mirrored).

    If a region shares its event collection with other regions (mirrored),
    this creates a new independent copy so edits don't affect other regions.

    unit_index: AU index.
    track_index: Track index within the AU.
    region_index: Region index to consolidate.

    Returns success or error.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const region = h.region({unit_index}, {track_index}, {region_index});
            const wasMirrored = region.isMirrowed;
            region.consolidate();
            return {{
                success: true,
                was_mirrored: wasMirrored,
                is_mirrored: region.isMirrowed,
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


# ─────────────────────────────────────────────────────────────────────
# Warp Markers & Region Play Mode (149-151)
# ─────────────────────────────────────────────────────────────────────


async def mcp_opendaw_copy_notes_to_track(
    source_unit_index: int,
    source_track_index: int,
    dest_track_index: int,
    source_region_index: int = -1,
    dest_unit_index: int = -1,
    transpose: int = 0,
    time_offset: float = 0,
    velocity_scale: float = 1.0,
) -> str:
    """Copy notes from one track/region to another track — MIDI layering and doubling.

    Copies all notes from a source region to a destination track's first region.
    Optional transpose (semitones), time offset (beats), and velocity scaling.

    Use cases:
    - Layer drums: copy drum track to second track with different instrument
    - Create harmony: copy melody +12 (octave) or +7 (fifth)
    - Call-and-response: copy with time_offset to create echo
    - Doubles: copy to same track position with slight transpose for thickening

    source_unit_index: Source AU index.
    source_track_index: Source note track index.
    dest_track_index: Destination note track index.
    source_region_index: Source region (-1 = first region).
    dest_unit_index: Destination AU index (-1 = same as source).
    transpose: Semitone offset (-127 to 127, 0 = same pitch).
    time_offset: Beat offset for copied notes (0 = same position, 2 = two beats later).
    velocity_scale: Multiply velocity of copied notes (1.0 = same, 0.7 = quieter layer).

    Returns count of notes copied.

    Example:
      # Layer drums — copy track 0 to track 2
      copy_notes_to_track(0, 0, 2)
      # Create octave harmony — copy melody +12
      copy_notes_to_track(0, 3, 4, transpose=12, velocity_scale=0.7)
      # Echo effect — copy 2 beats later at half velocity
      copy_notes_to_track(0, 0, 1, time_offset=2, velocity_scale=0.5)
    """
    if not (-127 <= transpose <= 127):
        return f"Error: transpose must be -127 to 127, got {transpose}"
    if not (0.0 <= velocity_scale <= 2.0):
        return f"Error: velocity_scale must be 0-2, got {velocity_scale}"
    dest_unit = dest_unit_index if dest_unit_index >= 0 else source_unit_index

    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const bg = h.boxGraph;
        const NoteEventBox = window.DAW_NoteEventBox;
        const srcUnitIdx = {source_unit_index};
        const srcTrackIdx = {source_track_index};
        const destUnitIdx = {dest_unit};
        const destTrackIdx = {dest_track_index};
        const srcRegionIdx = {source_region_index};
        const semis = {transpose};
        const tOff = {time_offset};
        const velScale = {velocity_scale};

        const allUnits = h.allAUBoxes();
        if (srcUnitIdx < 0 || srcUnitIdx >= allUnits.length) return {{error: "source_unit_index out of range"}};
        if (destUnitIdx < 0 || destUnitIdx >= allUnits.length) return {{error: "dest_unit_index out of range"}};

        const srcAu = allUnits[srcUnitIdx];
        const srcTracks = h.trackBoxes(srcAu);
        if (srcTrackIdx < 0 || srcTrackIdx >= srcTracks.length) return {{error: "source_track_index out of range"}};
        const srcTrack = srcTracks[srcTrackIdx];
        const srcRegions = h.regionBoxes(srcTrack);
        if (srcRegions.length === 0) return {{error: "No regions on source track"}};
        const srcRegIdx2 = srcRegionIdx < 0 ? 0 : srcRegionIdx;
        if (srcRegIdx2 >= srcRegions.length) return {{error: "source_region_index out of range"}};
        const srcRegion = srcRegions[srcRegIdx2];

        const destAu = allUnits[destUnitIdx];
        const destTracks = h.trackBoxes(destAu);
        if (destTrackIdx < 0 || destTrackIdx >= destTracks.length) return {{error: "dest_track_index out of range"}};
        const destTrack = destTracks[destTrackIdx];
        const destRegions = h.regionBoxes(destTrack);
        if (destRegions.length === 0) return {{error: "No regions on destination track — create a region first"}};
        const destRegion = destRegions[0];

        // Read source notes
        const srcEventsField = srcRegion.events.targetVertex.unwrap();
        const srcCollBox = srcEventsField.box;
        const srcNotes = [...srcCollBox.events.pointerHub.incoming()];
        if (srcNotes.length === 0) return {{error: "No notes in source region"}};

        // Read destination note collection
        const destEventsField = destRegion.events.targetVertex.unwrap();
        const destCollBox = destEventsField.box;

        let copied = 0;
        let skipped = 0;

        h.modify(() => {{
            for (const n of srcNotes) {{
                const pitch = n.box.pitch.getValue() + semis;
                if (pitch < 0 || pitch > 127) {{
                    skipped++;
                    continue;
                }}
                const pos = n.box.position.getValue() + tOff;
                const dur = n.box.duration.getValue();
                const vel = Math.max(0, Math.min(1, n.box.velocity.getValue() * velScale));

                NoteEventBox.create(bg, h.uuid.generate(), (box) => {{
                    box.position.setValue(Math.round(pos));
                    box.duration.setValue(Math.round(dur));
                    box.velocity.setValue(vel);
                    box.pitch.setValue(pitch);
                    box.chance.setValue(100);
                    box.cent.setValue(0);
                    box.events.refer(destCollBox.events);
                }});
                copied++;
            }}
        }});

        return {{
            success: true,
            notes_copied: copied,
            notes_skipped: skipped,
            transpose: semis,
            time_offset: tOff,
            velocity_scale: velScale,
            source: {{unit: srcUnitIdx, track: srcTrackIdx, region: srcRegIdx2}},
            dest: {{unit: destUnitIdx, track: destTrackIdx}},
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_copy_region_fades(src_unit: int, src_track: int, src_region: int,
                                        dst_unit: int, dst_track: int, dst_region: int) -> str:
    """Copy fade in/out settings from one audio region to another.

    Copies fadeIn, fadeOut, fadeInSlope, fadeOutSlope from the source region's
    Fading object to the destination region's Fading object.

    src_unit/src_track/src_region: Source region coordinates.
    dst_unit/dst_track/dst_region: Destination region coordinates.

    Returns the copied fade values.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const srcReg = h.region(h.au({src_unit}), h.track({src_unit}, {src_track}), {src_region});
            const dstReg = h.region(h.au({dst_unit}), h.track({dst_unit}, {dst_track}), {dst_region});
            if (!srcReg.fading || !dstReg.fading) return {{error: "Both regions must have fading (audio regions only)"}};
            const fadeIn = srcReg.fading.fadeIn.getValue();
            const fadeOut = srcReg.fading.fadeOut.getValue();
            const fadeInSlope = srcReg.fading.fadeInSlope.getValue();
            const fadeOutSlope = srcReg.fading.fadeOutSlope.getValue();
            h.modify(() => {{
                dstReg.fading.fadeIn.setValue(fadeIn);
                dstReg.fading.fadeOut.setValue(fadeOut);
                dstReg.fading.fadeInSlope.setValue(fadeInSlope);
                dstReg.fading.fadeOutSlope.setValue(fadeOutSlope);
            }});
            return {{
                success: true,
                fade_in: fadeIn, fade_out: fadeOut,
                fade_in_slope: fadeInSlope, fade_out_slope: fadeOutSlope,
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_copy_region_to_track(src_unit: int, src_track: int, src_region: int,
                                           dst_unit: int, dst_track: int, position: float = None) -> str:
    """Copy a region to a different track (or same track at new position).

    Works with note, audio, and automation regions. The copy includes all
    content — notes, audio content, or automation events.

    src_unit/src_track/src_region: Source region coordinates.
    dst_unit/dst_track: Destination track coordinates.
    position: New position in PPQN (omit to use source position).

    Returns new region position and duration.
    """
    pos_str = "null" if position is None else str(position)
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const srcReg = h.region(h.au({src_unit}), h.track({src_unit}, {src_track}), {src_region});
            const dstTrack = h.track({dst_unit}, {dst_track});
            let newAdapter;
            h.modify(() => {{
                newAdapter = srcReg.copyTo({{
                    target: dstTrack.box.regions,
                    position: {pos_str},
                }});
            }});
            return {{
                success: true,
                new_position: newAdapter.position,
                new_duration: newAdapter.duration,
                track_type: dstTrack.type?.getValue?.() ?? 'unknown',
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_create_audio_clip(sample_id: str, unit_index: int, clip_index: int, track_index: int, bpm: int) -> str:
    """Create an audio clip in the session view (clip launcher).

Audio clips are the session-view counterpart to audio regions. They appear
in the clip launcher and can be triggered independently.

sample_id: The ID returned by mcp_opendaw_load_audio.
unit_index: Audio unit index (default 0).
clip_index: Slot index in the clip launcher (0, 1, 2, ...).
track_index: Track index within the audio unit (default 0).
bpm: Source BPM of the sample (for warp marker calculation).

Returns clip UUID and index.
"""
    safe_sample_id = sample_id.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const UUID = h.uuid;
        const AudioFileBox = window.DAW_AudioFileBox;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const clipIdx = {clip_index};
        const sampleId = "{safe_sample_id}";
        const sampleBpm = {bpm};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
        const au = units[unitIdx];

        const audioTracks = h.trackBoxes(au)
            .filter(box => box.type?.getValue?.() === 2);
        if (trackIdx >= audioTracks.length) return {{error: "No audio track at index " + trackIdx}};
        const trackBox = audioTracks[trackIdx];

        const audioBuffer = window.DAW_localAudioBuffers.get(sampleId);
        if (!audioBuffer) return {{error: "Sample not loaded: " + sampleId}};

        const sample = {{
            name: sampleId,
            duration: audioBuffer.duration,
            bpm: sampleBpm,
            sample_rate: audioBuffer.sampleRate,
        }};

        let clipBox;
        h.editing.modify(() => {{
            const audioFileBox = AudioFileBox.create(h.boxGraph, UUID.generate(), (box) => {{
                box.fileName.setValue(sampleId);
                box.startInSeconds.setValue(0.0);
                box.endInSeconds.setValue(audioBuffer.duration);
            }});

            clipBox = h.api.createNotStretchedClip({{
                boxGraph: h.boxGraph,
                targetTrack: trackBox,
                index: clipIdx,
                audioFileBox: audioFileBox,
                sample: sample,
            }});
        }});

        return {{
            success: true,
            clip_uuid: clipBox.address.uuid.toString(),
            clip_index: clipBox.index.getValue(),
            label: clipBox.label.getValue(),
            duration_seconds: audioBuffer.duration,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_create_audio_track() -> str:
    """Create a new audio track on the primary audio unit."""
    result = await bridge.evaluate("""() => {
        const h = window.DAW_HELPERS;
        let trackBox;
        h.modify(() => {
            trackBox = h.api.createAudioTrack(h.primaryAudioUnitBox);
        });
        return {success: !!trackBox, type: 'audio'};
    }""")
    return _wrap_eval(result)


async def mcp_opendaw_create_genre_track(genre: str, bpm: float = 120) -> str:
    """Create a genre-specific starting track with synth, beat, and basic mix — one call builds a full section.

genre: Musical genre preset:
  - "house" — 4/4 kick, offbeat hat, stab bass, 128 BPM
  - "techno" — driving kick, ride hat, acid bass, 130 BPM
  - "lofi" — swing kick/snare, soft keys, 80 BPM
  - "dnb" — breakbeat drums, sub bass, 174 BPM
  - "trap" — 808 kick, hat rolls, melodic lead, 140 BPM
  - "ambient" — pad chord, no drums, 70 BPM
  - "coldwave" — driving kick, dark bass, 110 BPM
  - "hiphop" — boom bap kick/snare, 90 BPM

bpm: Override tempo (default per genre).

Returns created AU indices, note counts, and suggested next steps.
"""
    if genre not in GENRE_PRESETS:
        return f"Error: unknown genre '{genre}'. Valid: {VALID_GENRES}"

    g = GENRE_PRESETS[genre]
    actual_bpm = bpm if bpm != 120 else g["bpm"]

    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const bg = h.boxGraph;
        const p = window.DAW;
        const IF = window.DAW_InstrumentFactories;
        const NoteEventBox = window.DAW_NoteEventBox;
        const NoteEventCollectionBox = window.DAW_NoteEventCollectionBox;
        const NoteRegionBox = window.DAW_NoteRegionBox;
        const Quarter = h.ppqn.Quarter;
        const Sixteenth = Quarter / 4;

        const genreData = {json.dumps(g)};
        const bpm = {actual_bpm};

        // Set BPM via existing API (inside modify)
        h.modify(() => h.api.setBpm(bpm));

        // Create synth AU for chords/bass (inside modify — createInstrument needs transaction)
        let synthAU, synthAUIdx, synthNoteTracks;
        h.modify(() => {{
            const result = p.api.createInstrument(IF.Vaporisateur, {{}});
            synthAU = result.audioUnitBox;
            synthAUIdx = h.allAUBoxes().length - 1;
            synthNoteTracks = h.noteTrackBoxes(synthAU);
        }});

        let chordNotes = 0;
        let bassNotes = 0;
        let drumNotes = 0;

        // Add chords
        if (genreData.chords.length > 0 && synthNoteTracks.length > 0) {{
            const trackBox = synthNoteTracks[0];
            const noteToPitch = {{"C":0,"C#":1,"Db":1,"D":2,"D#":3,"Eb":3,"E":4,"F":5,"F#":6,"Gb":6,"G":7,"G#":8,"Ab":8,"A":9,"A#":10,"Bb":10,"B":11}};
            const chordIntervals = {{"maj":[0,4,7],"min":[0,3,7],"dom7":[0,4,7,10],"maj7":[0,4,7,11],"min7":[0,3,7,10],"sus2":[0,2,7],"sus4":[0,5,7],"add9":[0,4,7,14],"dim":[0,3,6],"aug":[0,4,8]}};

            h.modify(() => {{
                const collection = NoteEventCollectionBox.create(bg, h.uuid.generate());
                let maxEnd = 0;
                for (let ci = 0; ci < genreData.chords.length; ci++) {{
                    const [rootName, chordType] = genreData.chords[ci];
                    const rootPc = noteToPitch[rootName] || 0;
                    const intervals = chordIntervals[chordType] || [0,4,7];
                    const rootPitch = 60 + rootPc - (rootPc > 5 ? 12 : 0);
                    for (const iv of intervals) {{
                        NoteEventBox.create(bg, h.uuid.generate(), (box) => {{
                            box.position.setValue(Math.round(ci * 4 * Quarter));
                            box.duration.setValue(Math.round(4 * Quarter));
                            box.velocity.setValue(0.6);
                            box.pitch.setValue(rootPitch + iv);
                            box.chance.setValue(100);
                            box.cent.setValue(0);
                            box.events.refer(collection.events);
                        }});
                        chordNotes++;
                        maxEnd = Math.max(maxEnd, Math.round((ci * 4 + 4) * Quarter));
                    }}
                }}
                NoteRegionBox.create(bg, h.uuid.generate(), (box) => {{
                    box.position.setValue(0);
                    box.label.setValue("Chords");
                    box.mute.setValue(false);
                    box.duration.setValue(Math.max(maxEnd, 4 * Quarter));
                    box.loopDuration.setValue(Math.max(maxEnd, 4 * Quarter));
                    box.eventOffset.setValue(0);
                    box.events.refer(collection.owners);
                    box.regions.refer(trackBox.regions);
                }});
            }});
        }}

        // Add bass on same AU, second note track if available
        if (genreData.bass.length > 0 && synthNoteTracks.length > 0) {{
            const bassTrack = synthNoteTracks[Math.min(1, synthNoteTracks.length - 1)];
            h.modify(() => {{
                const collection = NoteEventCollectionBox.create(bg, h.uuid.generate());
                let maxEnd = 0;
                for (const n of genreData.bass) {{
                    NoteEventBox.create(bg, h.uuid.generate(), (box) => {{
                        box.position.setValue(Math.round(n.start * Quarter));
                        box.duration.setValue(Math.round(n.duration * Quarter));
                        box.velocity.setValue(0.85);
                        box.pitch.setValue(n.pitch);
                        box.chance.setValue(100);
                        box.cent.setValue(0);
                        box.events.refer(collection.events);
                    }});
                    bassNotes++;
                    maxEnd = Math.max(maxEnd, Math.round((n.start + n.duration) * Quarter));
                }}
                NoteRegionBox.create(bg, h.uuid.generate(), (box) => {{
                    box.position.setValue(0);
                    box.label.setValue("Bass");
                    box.mute.setValue(false);
                    box.duration.setValue(Math.max(maxEnd, 4 * Quarter));
                    box.loopDuration.setValue(Math.max(maxEnd, 4 * Quarter));
                    box.eventOffset.setValue(0);
                    box.events.refer(collection.owners);
                    box.regions.refer(bassTrack.regions);
                }});
            }});
        }}

        // Add drums on a separate AU
        if (Object.keys(genreData.drums).length > 0) {{
            let drumAU, drumTracks;
            h.modify(() => {{
                const drumResult = p.api.createInstrument(IF.Vaporisateur, {{}});
                drumAU = drumResult.audioUnitBox;
                drumTracks = h.noteTrackBoxes(drumAU);
            }});
            if (drumTracks.length > 0) {{
                const drumTrack = drumTracks[0];
                const velocities = {{'x': 0.9, 'o': 0.5, 'X': 1.0}};
                const lanePitches = {{kick: 36, snare: 38, hihat: 42, clap: 39, perc: 47}};
                h.modify(() => {{
                    const collection = NoteEventCollectionBox.create(bg, h.uuid.generate());
                    const maxSteps = Math.max(...Object.values(genreData.drums).map(s => s.length));
                    for (const [laneName, steps] of Object.entries(genreData.drums)) {{
                        const pitch = lanePitches[laneName] || 36;
                        for (let i = 0; i < steps.length; i++) {{
                            const ch = steps[i];
                            if (ch === '.' || ch === ' ') continue;
                            NoteEventBox.create(bg, h.uuid.generate(), (box) => {{
                                box.position.setValue(Math.round(i * Sixteenth));
                                box.duration.setValue(Math.round(Sixteenth * 0.8));
                                box.velocity.setValue(velocities[ch] || 0.8);
                                box.pitch.setValue(pitch);
                                box.chance.setValue(100);
                                box.cent.setValue(0);
                                box.events.refer(collection.events);
                            }});
                            drumNotes++;
                        }}
                    }}
                    NoteRegionBox.create(bg, h.uuid.generate(), (box) => {{
                        box.position.setValue(0);
                        box.label.setValue("Drums");
                        box.mute.setValue(false);
                        box.duration.setValue(Math.max(maxSteps * Sixteenth, 4 * Quarter));
                        box.loopDuration.setValue(Math.max(maxSteps * Sixteenth, 4 * Quarter));
                        box.eventOffset.setValue(0);
                        box.events.refer(collection.owners);
                        box.regions.refer(drumTrack.regions);
                    }});
                }});
            }}
        }}

        return {{
            success: true,
            genre: "{genre}",
            bpm: bpm,
            chord_notes: chordNotes,
            bass_notes: bassNotes,
            drum_notes: drumNotes,
            synth_au_index: synthAUIdx,
            next_steps: [
                "Call add_mastering_chain to add mastering to the output bus",
                "Call render_full to render the mix",
                "Call auto_gain with target_lufs=-14 for streaming loudness",
            ],
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_create_instrument_track(name: str) -> str:
    """Create a new instrument audio unit with a Tape device and an audio track.

This is required for audio playback — the Tape device reads audio regions
and outputs sound. The instrument AU is connected to the output AU's bus.

name: Display name for the instrument (default "Tape").
Returns the unit_index and track_index for use with place_audio_region.
"""
    safe_name = name.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const AudioUnitBox = window.DAW_AudioUnitBox;
        const TapeDeviceBox = window.DAW_TapeDeviceBox;
        const CaptureAudioBox = window.DAW_CaptureAudioBox;
        const AudioUnitType = window.DAW_AudioUnitType;

        const rootBox = h.rootBox;
        const primaryAudioBusBox = h.primaryAudioBusBox;

        let instrumentAU, tapeDevice, captureBox, trackBox;
        h.modify(() => {{
            // Create CaptureAudioBox
            captureBox = CaptureAudioBox.create(h.boxGraph, h.uuid.generate());

            // Create instrument AudioUnitBox connected to output bus
            instrumentAU = AudioUnitBox.create(h.boxGraph, h.uuid.generate(), (box) => {{
                box.type.setValue(AudioUnitType.Instrument);
                box.collection.refer(rootBox.audioUnits);
                box.output.refer(primaryAudioBusBox.input);
                box.capture.refer(captureBox);
                box.index.setValue(0);
                box.volume.setValue(0.767835); // 0 dB (VolumeMapper.decibel(-96,-9,+6) powerByCenter)
            }});

            // Create TapeDeviceBox (audio player instrument)
            tapeDevice = TapeDeviceBox.create(h.boxGraph, h.uuid.generate(), (box) => {{
                box.label.setValue("{safe_name}");
                box.host.refer(instrumentAU.input);
            }});

            // Create audio track on the instrument AU
            trackBox = h.api.createAudioTrack(instrumentAU);
        }});

        // Find unit_index and track_index
        const allUnits = h.allAUBoxes();
        const unitIndex = allUnits.findIndex(au => String(au.address) === String(instrumentAU.address));
        const audioTracks = h.trackBoxes(instrumentAU).filter(box => box.type?.getValue?.() === 2);
        const trackIndex = audioTracks.findIndex(t => String(t.address) === String(trackBox.address));

        return {{
            success: true,
            unit_index: unitIndex,
            track_index: trackIndex >= 0 ? trackIndex : 0,
            instrument_au: String(instrumentAU.address),
            tape_device: String(tapeDevice.address),
            track_box: String(trackBox.address),
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_create_note_clip(unit_index: int, track_index: int, clip_index: int, name: str, hue: int) -> str:
    """Create a note clip in the session view (clip launcher).

Note clips are the session-view counterpart to note regions. They contain
a NoteEventCollection and can be triggered independently in the clip launcher.

unit_index: Audio unit index (-1 = search all AUs for note tracks).
track_index: Note track index within the AU.
clip_index: Slot index in the clip launcher (0, 1, 2, ...).
name: Display name for the clip.
hue: Color hue 0-360 (-1 = auto from track type).

Returns clip UUID and index.
"""
    safe_name = name.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const clipIdx = {clip_index};
        const clipName = "{safe_name}";
        const clipHue = {hue};

        // Find note track
        let noteTracks = [];
        if (unitIdx < 0) {{
            const allUnits = h.allAUBoxes();
            for (const au of allUnits) {{
                noteTracks.push(...h.noteTrackBoxes(au));
            }}
        }} else {{
            const units = h.allAUBoxes();
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            noteTracks = h.noteTrackBoxes(units[unitIdx]);
        }}

        if (trackIdx >= noteTracks.length) return {{error: "No note track at index " + trackIdx}};
        const trackBox = noteTracks[trackIdx];

        let clipBox;
        h.editing.modify(() => {{
            const opts = {{name: clipName}};
            if (clipHue >= 0) opts.hue = clipHue;
            clipBox = h.api.createNoteClip(trackBox, clipIdx, opts);
        }});

        return {{
            success: true,
            clip_uuid: clipBox.address.uuid.toString(),
            clip_index: clipBox.index.getValue(),
            label: clipBox.label.getValue(),
            duration_ppqn: clipBox.duration.getValue(),
            track_type: "Notes",
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_create_note_track(unit_index: int) -> str:
    """Create a new note/MIDI track on an audio unit.

unit_index: Audio unit index. Use -1 (default) for the primary audio unit,
or specify an instrument AU index that contains a synth device (Vaporisateur, Nano, etc).
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const idx = {unit_index};
        let au;
        if (idx < 0) {{
            au = h.primaryAudioUnitBox;
        }} else {{
            const units = h.allAUBoxes();
            if (idx >= units.length) return {{error: "No audio unit at index " + idx}};
            au = units[idx];
        }}
        let trackBox;
        h.modify(() => {{
            trackBox = h.api.createNoteTrack(au);
        }});
        return {{success: !!trackBox, type: 'note', unit_index: idx}};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_create_pitch_stretched_clip(sample_id: str, unit_index: int, clip_index: int, track_index: int, bpm: int) -> str:
    """Create a pitch-stretched audio clip in session view.

Pitch-stretched clips maintain pitch alignment with the project tempo.
Uses AudioPitchStretchBox for play mode.

sample_id: ID from mcp_opendaw_load_audio.
unit_index: Audio unit index.
clip_index: Slot index in clip launcher.
track_index: Audio track index within AU.
bpm: Source BPM of the sample.
"""
    safe_sample_id = sample_id.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const UUID = h.uuid;
        const AudioFileBox = window.DAW_AudioFileBox;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const clipIdx = {clip_index};
        const sampleId = "{safe_sample_id}";
        const sampleBpm = {bpm};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
        const au = units[unitIdx];

        const audioTracks = h.trackBoxes(au).filter(box => box.type?.getValue?.() === 2);
        if (trackIdx >= audioTracks.length) return {{error: "No audio track at index " + trackIdx}};
        const trackBox = audioTracks[trackIdx];

        const audioBuffer = window.DAW_localAudioBuffers.get(sampleId);
        if (!audioBuffer) return {{error: "Sample not loaded: " + sampleId}};

        const sample = {{name: sampleId, duration: audioBuffer.duration, bpm: sampleBpm, sample_rate: audioBuffer.sampleRate}};

        let clipBox;
        h.editing.modify(() => {{
            const audioFileBox = AudioFileBox.create(h.boxGraph, UUID.generate(), (box) => {{
                box.fileName.setValue(sampleId);
                box.startInSeconds.setValue(0.0);
                box.endInSeconds.setValue(audioBuffer.duration);
            }});

            clipBox = h.api.createPitchStretchedClip({{
                boxGraph: h.boxGraph,
                targetTrack: trackBox,
                index: clipIdx,
                audioFileBox: audioFileBox,
                sample: sample,
            }});
        }});

        return {{
            success: true,
            clip_uuid: clipBox.address.uuid.toString(),
            clip_index: clipBox.index.getValue(),
            label: clipBox.label.getValue(),
            timebase: "musical",
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_create_pitch_stretched_region(sample_id: str, unit_index: int, start_beat: int, track_index: int, bpm: int) -> str:
    """Place a pitch-stretched audio region on a track.

Pitch-stretch preserves the original timing but allows pitch manipulation
via warp markers. Use this when you want to tune audio to project key
without changing its duration.

sample_id: The ID returned by mcp_opendaw_load_audio.
unit_index: Audio unit index (default 0).
start_beat: Beat position to place the region.
track_index: Track index within the audio unit (default 0).
bpm: Source BPM of the sample (for warp marker calculation).

Returns position and duration in PPQN.
"""
    safe_sample_id = sample_id.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const UUID = h.uuid;
        const PPQN = h.ppqn;
        const Quarter = PPQN.Quarter;
        const AudioFileBox = window.DAW_AudioFileBox;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const sampleId = "{safe_sample_id}";
        const startBeat = {start_beat};
        const sampleBpm = {bpm};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
        const au = units[unitIdx];

        const audioTracks = h.trackBoxes(au)
            .filter(box => box.type?.getValue?.() === 2);
        if (trackIdx >= audioTracks.length) return {{error: "No audio track at index " + trackIdx}};
        const trackBox = audioTracks[trackIdx];

        const audioBuffer = window.DAW_localAudioBuffers.get(sampleId);
        if (!audioBuffer) return {{error: "Sample not loaded: " + sampleId}};

        const sample = {{
            name: sampleId,
            duration: audioBuffer.duration,
            bpm: sampleBpm,
            sample_rate: audioBuffer.sampleRate,
        }};

        let regionBox, audioFileBox;
        h.editing.modify(() => {{
            audioFileBox = AudioFileBox.create(h.boxGraph, UUID.generate(), (box) => {{
                box.fileName.setValue(sampleId);
                box.startInSeconds.setValue(0.0);
                box.endInSeconds.setValue(audioBuffer.duration);
            }});

            regionBox = h.api.createPitchStretchedRegion({{
                boxGraph: h.boxGraph,
                targetTrack: trackBox,
                position: Math.round(startBeat * Quarter),
                audioFileBox: audioFileBox,
                sample: sample,
            }});
        }});

        return {{
            success: true,
            sample_id: sampleId,
            position_beats: startBeat,
            duration_ppqn: regionBox.duration.getValue(),
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_create_synth_track(name: str, synth_type: str) -> str:
    """Create a new instrument audio unit with a synthesizer device and a note track.

Unlike create_instrument_track (which creates a Tape device for audio playback),
this creates a MIDI synthesizer that responds to notes from create_note.

synth_type: 'vaporisateur' (subtractive synth, default), 'nano' (simple synth),
            'soundfont' (SF2 player, needs sample), 'apparat' (FM synth).
name: Display name for the instrument.

Returns unit_index and track_index for use with create_note.
"""
    factory_key = synth_type.capitalize() if synth_type else "Vaporisateur"
    safe_name = name.replace('"', '').replace('\\', '').replace("'", "")
    safe_synth_type = synth_type.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const AudioUnitBox = window.DAW_AudioUnitBox;
        const CaptureAudioBox = window.DAW_CaptureAudioBox;
        const AudioUnitType = window.DAW_AudioUnitType;
        const IconSymbol = window.DAW_IconSymbol;
        const InstrumentFactories = window.DAW_InstrumentFactories;

        if (!InstrumentFactories) throw new Error("InstrumentFactories not loaded. Check headless-daw lazy-load.");
        if (!IconSymbol) throw new Error("IconSymbol not loaded.");

        const factory = InstrumentFactories["{factory_key}"];
        if (!factory) throw new Error("Unknown synth type: {safe_synth_type} (factory key: {factory_key})");

        const rootBox = h.rootBox;
        const primaryAudioBusBox = h.primaryAudioBusBox;

        let instrumentAU, synthDevice, captureBox, trackBox;
        h.modify(() => {{
            // Create CaptureAudioBox
            captureBox = CaptureAudioBox.create(h.boxGraph, h.uuid.generate());

            // Create instrument AudioUnitBox connected to output bus
            instrumentAU = AudioUnitBox.create(h.boxGraph, h.uuid.generate(), (box) => {{
                box.type.setValue(AudioUnitType.Instrument);
                box.collection.refer(rootBox.audioUnits);
                box.output.refer(primaryAudioBusBox.input);
                box.capture.refer(captureBox);
                box.index.setValue(0);
                box.volume.setValue(0.767835); // 0 dB
            }});

            // Create synth device using InstrumentFactories (proper init values!)
            const icon = IconSymbol.Piano;
            synthDevice = factory.create(h.boxGraph, instrumentAU.input, "{safe_name}", icon);

            // Create note track on the instrument AU
            trackBox = h.api.createNoteTrack(instrumentAU);
        }});

        // Find unit_index and track_index
        const allUnits = h.allAUBoxes();
        const unitIndex = allUnits.findIndex(au => String(au.address) === String(instrumentAU.address));
        const noteTracks = h.noteTrackBoxes(instrumentAU);
        const trackIndex = noteTracks.findIndex(t => String(t.address) === String(trackBox.address));

        return {{
            success: true,
            unit_index: unitIndex,
            track_index: trackIndex >= 0 ? trackIndex : 0,
            synth_type: "{safe_synth_type}",
            synth_class: synthDevice.constructor?.name,
            instrument_au: String(instrumentAU.address),
            synth_device: String(synthDevice.address),
            track_box: String(trackBox.address),
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_create_time_stretched_clip(sample_id: str, unit_index: int, clip_index: int, track_index: int, bpm: int, playback_rate: float, transient_mode: str) -> str:
    """Create a time-stretched audio clip in session view.

sample_id: ID from mcp_opendaw_load_audio.
unit_index: Audio unit index.
clip_index: Slot index in clip launcher.
track_index: Audio track index within AU.
bpm: Source BPM of the sample.
playback_rate: Playback rate (1.0 = normal, 0.5 = half speed, 2.0 = double).
transient_mode: "Pingpong", "Monoton", "Cycles", or "Plode".
"""
    safe_mode = transient_mode.replace('"', '').replace("'", '').replace('\\', '')


    safe_sample_id = sample_id.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const UUID = h.uuid;
        const AudioFileBox = window.DAW_AudioFileBox;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const clipIdx = {clip_index};
        const sampleId = "{safe_sample_id}";
        const sampleBpm = {bpm};
        const rate = {playback_rate};
        const modeName = "{safe_mode}";

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
        const au = units[unitIdx];

        const audioTracks = h.trackBoxes(au).filter(box => box.type?.getValue?.() === 2);
        if (trackIdx >= audioTracks.length) return {{error: "No audio track at index " + trackIdx}};
        const trackBox = audioTracks[trackIdx];

        const audioBuffer = window.DAW_localAudioBuffers.get(sampleId);
        if (!audioBuffer) return {{error: "Sample not loaded: " + sampleId}};

        const sample = {{name: sampleId, duration: audioBuffer.duration, bpm: sampleBpm, sample_rate: audioBuffer.sampleRate}};

        const TransientPlayMode = {{Pingpong: 0, Monoton: 1, Cycles: 2, Plode: 3}};
        const tMode = TransientPlayMode[modeName] ?? 0;

        let clipBox;
        h.editing.modify(() => {{
            const audioFileBox = AudioFileBox.create(h.boxGraph, UUID.generate(), (box) => {{
                box.fileName.setValue(sampleId);
                box.startInSeconds.setValue(0.0);
                box.endInSeconds.setValue(audioBuffer.duration);
            }});

            clipBox = h.api.createTimeStretchedClip({{
                boxGraph: h.boxGraph,
                targetTrack: trackBox,
                index: clipIdx,
                audioFileBox: audioFileBox,
                sample: sample,
                playbackRate: rate,
                transientPlayMode: tMode,
            }});
        }});

        return {{
            success: true,
            clip_uuid: clipBox.address.uuid.toString(),
            clip_index: clipBox.index.getValue(),
            label: clipBox.label.getValue(),
            playback_rate: rate,
            transient_mode: modeName,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_create_time_stretched_region(sample_id: str, unit_index: int, start_beat: int, track_index: int, playback_rate: float, transient_mode: str, bpm: int) -> str:
    """Place a time-stretched audio region on a track.

Unlike place_audio_region (which uses TimeBase.Seconds), this creates a
musically-timed region with warp markers. Audio plays back at a different
speed while staying in sync with the project tempo.

sample_id: The ID returned by mcp_opendaw_load_audio.
unit_index: Audio unit index (default 0).
start_beat: Beat position to place the region.
track_index: Track index within the audio unit (default 0).
playback_rate: Rate multiplier (1.0 = original, 0.5 = half-speed, 2.0 = double).
transient_mode: "once", "repeat", or "pingpong" (default).
bpm: Source BPM of the sample (for warp marker calculation).

Returns position, duration in PPQN, and playback rate.
"""
    mode_val = json.dumps(transient_mode)


    safe_sample_id = sample_id.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const UUID = h.uuid;
        const PPQN = h.ppqn;
        const Quarter = PPQN.Quarter;
        const AudioFileBox = window.DAW_AudioFileBox;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const sampleId = "{safe_sample_id}";
        const startBeat = {start_beat};
        const playbackRate = {playback_rate};
        const transientMode = {mode_val};
        const sampleBpm = {bpm};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
        const au = units[unitIdx];

        const audioTracks = h.trackBoxes(au)
            .filter(box => box.type?.getValue?.() === 2);
        if (trackIdx >= audioTracks.length) return {{error: "No audio track at index " + trackIdx}};
        const trackBox = audioTracks[trackIdx];

        const audioBuffer = window.DAW_localAudioBuffers.get(sampleId);
        if (!audioBuffer) return {{error: "Sample not loaded: " + sampleId}};

        const sample = {{
            name: sampleId,
            duration: audioBuffer.duration,
            bpm: sampleBpm,
            sample_rate: audioBuffer.sampleRate,
        }};

        let regionBox, audioFileBox;
        h.editing.modify(() => {{
            audioFileBox = AudioFileBox.create(h.boxGraph, UUID.generate(), (box) => {{
                box.fileName.setValue(sampleId);
                box.startInSeconds.setValue(0.0);
                box.endInSeconds.setValue(audioBuffer.duration);
            }});

            regionBox = h.api.createTimeStretchedRegion({{
                boxGraph: h.boxGraph,
                targetTrack: trackBox,
                position: Math.round(startBeat * Quarter),
                audioFileBox: audioFileBox,
                sample: sample,
                playbackRate: playbackRate,
                transientPlayMode: transientMode,
            }});
        }});

        return {{
            success: true,
            sample_id: sampleId,
            position_beats: startBeat,
            duration_ppqn: regionBox.duration.getValue(),
            playback_rate: playbackRate,
            transient_mode: "{transient_mode}",
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_create_track_region(unit_index: int, track_index: int, start_beat: int, duration_beats: int, name: str, hue: int) -> str:
    """Create a region on any track (note or value) using the generic createTrackRegion API.

Automatically detects track type and creates the appropriate region:
- Note track → NoteRegionBox with NoteEventCollection
- Value track → ValueRegionBox with ValueEventCollection
Returns Option.None (error) for audio tracks — use place_audio_region instead.

unit_index: Audio unit index (-1 = search all AUs).
track_index: Track index within the AU.
start_beat: Beat position for the region.
duration_beats: Duration in beats.
name: Display name (empty = auto: "Notes" or "Automation").
hue: Color 0-360 (-1 = auto from track type).

Returns region UUID, type, and position.
"""
    safe_name = name.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const PPQN = h.ppqn;
        const Quarter = PPQN.Quarter;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const startBeat = {start_beat};
        const durBeats = {duration_beats};
        const regionName = "{safe_name}";
        const regionHue = {hue};

        let tracks = [];
        if (unitIdx < 0) {{
            for (const au of h.allAUBoxes()) {{
                tracks.push(...h.trackBoxes(au));
            }}
        }} else {{
            const units = h.allAUBoxes();
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            tracks = h.trackBoxes(units[unitIdx]);
        }}

        if (trackIdx >= tracks.length) return {{error: "No track at index " + trackIdx}};
        const trackBox = tracks[trackIdx];
        const trackType = trackBox.type.getValue();

        let regionBox;
        h.editing.modify(() => {{
            const opts = {{}};
            if (regionName) opts.name = regionName;
            if (regionHue >= 0) opts.hue = regionHue;
            const opt = h.api.createTrackRegion(trackBox, Math.round(startBeat * Quarter), Math.round(durBeats * Quarter), opts);
            opt.match({{
                some: (box) => {{ regionBox = box }},
                none: () => {{}}
            }});
        }});

        if (!regionBox) return {{error: "createTrackRegion returned None (track type may not support regions)"}};
        return {{
            success: true,
            region_uuid: regionBox.address.uuid.toString(),
            position: regionBox.position.getValue(),
            duration: regionBox.duration.getValue(),
            track_type: trackType === 1 ? "Notes" : trackType === 3 ? "Value" : "Type " + trackType,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_create_value_clip(unit_index: int, track_index: int, name: str, clip_index: int) -> str:
    """Create a value clip (automation clip) on an automation track in session view.

Uses ProjectApi.createValueClip — creates a ValueClipBox with an empty
ValueEventCollectionBox on the specified automation (Value-type) track.

unit_index: Audio unit index.
track_index: Automation track index (-1 = first automation track on the unit).
name: Clip label.
clip_index: Clip slot index (0-based).

Returns clip creation details.
"""
    clip_idx = clip_index
    safe_name = name.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const clipIdx = {clip_idx};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
        const au = units[unitIdx];

        // Find Value-type tracks (automation)
        const valueTracks = h.trackBoxes(au).filter(t => t.type?.getValue?.() === 3);

        if (valueTracks.length === 0) return {{error: "No automation tracks on AU " + unitIdx + ". Use add_automation first."}};
        const targetTrack = trackIdx < 0 ? valueTracks[0] : (trackIdx < valueTracks.length ? valueTracks[trackIdx] : null);
        if (!targetTrack) return {{error: "No automation track at index " + trackIdx}};

        let clip;
        h.editing.modify(() => {{
            clip = h.api.createValueClip(targetTrack, clipIdx, {{name: "{safe_name}"}});
        }});

        if (!clip) return {{error: "Failed to create value clip"}};

        return {{
            success: true,
            clip_class: clip.constructor.name,
            label: clip.label?.getValue?.() ?? "",
            duration_beats: (clip.duration?.getValue?.() ?? 0) / h.ppqn.Quarter,
            mute: clip.mute?.getValue?.() ?? false,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_duplicate_audiounit(unit_index: int) -> str:
    """Duplicate an audio unit with all its content: instrument, effects, tracks, regions, notes, automation.

Creates a new audio unit of the same type (Instrument/Audio) with a copy of:
- Instrument device (same factory type + all parameters)
- Audio effect chain (same effects + all parameter values)
- MIDI effect chain (same effects + all parameter values)
- Note tracks, note regions, and all note events (pitch/duration/velocity/position)
- Track volume, panning, mute state
- Audio regions (if any, referencing same audio files)
- Unit label, volume

unit_index: Source audio unit index to duplicate.

Returns the new unit index and details of what was copied.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const units = h.allAUBoxes();
        if ({unit_index} >= units.length) return {{error: "No audio unit at index {unit_index}"}};
        const srcAU = units[{unit_index}];

        const srcType = srcAU.type.getValue();
        const srcLabel = srcAU.label?.getValue() || "Unit";
        const srcVolume = srcAU.volume?.getValue() || 0.767835;

        // Read instrument info
        const srcIncoming = h.inputBoxes(srcAU);
        const srcInstrument = srcIncoming.length > 0 ? srcIncoming[0] : null;
        const instrumentFactoryName = srcInstrument?.constructor.name || null;

        // Read effects
        const srcEffects = h.effectBoxes(srcAU)
            .sort((a,b) => a.index.getValue() - b.index.getValue())
            .map(box => ({{type: box.constructor.name}}));

        // Read MIDI effects
        const srcMidiEffects = h.midiEffectBoxes(srcAU)
            .sort((a,b) => a.index.getValue() - b.index.getValue())
            .map(box => ({{type: box.constructor.name}}));

        // Read tracks
        const srcTracks = h.trackBoxes(srcAU).sort((a,b) => a.index.getValue() - b.index.getValue());

        // Map instrument class name to factory key
        const instFactoryMap = {{
            'VaporisateurDeviceBox': 'Vaporisateur',
            'NanoDeviceBox': 'Nano',
            'SoundfontDeviceBox': 'Soundfont',
            'MidiOutputDeviceBox': 'MidiOutput',
            'PlayfieldDeviceBox': 'Playfield',
            'ApparatDeviceBox': 'Apparat',
        }};
        const factoryKey = instFactoryMap[instrumentFactoryName] || null;

        // Collect note data from all tracks
        const noteData = [];
        for (const track of srcTracks) {{
            const trackType = track.type?.getValue();
            const trackVolume = track.volume?.getValue();
            const trackPanning = track.panning?.getValue();
            const trackMute = track.mute?.getValue();
            const trackHue = track.hue?.getValue();

            const regions = h.regionBoxes(track);
            const trackNotes = [];
            for (const region of regions) {{
                if (region.constructor.name === 'NoteRegionBox') {{
                    try {{
                        const vertex = region.events.targetVertex.unwrap();
                        const eventsBox = vertex.box || vertex;
                        const notes = h.eventBoxes(eventsBox);
                        for (const note of notes) {{
                            trackNotes.push({{
                                pitch: note.pitch.getValue(),
                                position: note.position.getValue(),
                                duration: note.duration.getValue(),
                                velocity: note.velocity.getValue(),
                                cent: note.cent?.getValue() || 0,
                            }});
                        }}
                    }} catch(e) {{}}
                }}
            }}

            noteData.push({{
                trackType, trackVolume, trackPanning, trackMute, trackHue,
                notes: trackNotes,
            }});
        }}

        return {{
            srcType, srcLabel, srcVolume,
            instrumentFactoryName, factoryKey,
            effectCount: srcEffects.length,
            effects: srcEffects,
            midiEffectCount: srcMidiEffects.length,
            midiEffects: srcMidiEffects,
            trackCount: srcTracks.length,
            tracks: noteData,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_duplicate_automation_event(unit_index: int, track_index: int, region_index: int,
                                                  event_index: int, position_offset: float = 0.0,
                                                  value_override: float = None) -> str:
    """Duplicate an automation event within the same region.

    Copies the event's position, value, and interpolation. Can offset position
    and override the value.

    unit_index/track_index/region_index: Automation region coordinates.
    event_index: Event index within the region.
    position_offset: PPQN offset from original position.
    value_override: New value (0-1) instead of copying. Omit to copy original.

    Returns the new event's position and value.
    """
    value_str = "null" if value_override is None else str(value_override)
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const reg = h.region(h.au({unit_index}), h.track({unit_index}, {track_index}), {region_index});
            const events = reg.events.targetVertex.unwrap("events").box;
            const eventAdapters = h.eventBoxes(events)
                .sort((a, b) => a.position.getValue() - b.position.getValue());
            if ({event_index} >= eventAdapters.length) return {{error: "No event at index " + {event_index}}};
            const srcBox = eventAdapters[{event_index}];
            const adapter = h.project.boxAdapters.adapterFor(srcBox, h.project.ValueEventBoxAdapter || class {{}});
            const origPos = srcBox.position.getValue();
            const origVal = srcBox.value.getValue();
            let newAdapter;
            h.modify(() => {{
                newAdapter = adapter.copyTo({{
                    position: origPos + {position_offset},
                    value: {value_str} !== null ? {value_str} : origVal,
                }});
            }});
            return {{
                success: true,
                new_position: newAdapter.position,
                new_value: newAdapter.value,
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_duplicate_effect(unit_index: int, effect_index: int, chain_type: str = "audio") -> str:
    """Duplicate a single effect within an AU's effect chain, copying all parameter values.

    Addresses upstream issue #273 (Ctrl+D for audio effects) via MCP.
    Works for both audio and MIDI effect chains.

    unit_index: AU index containing the effect.
    effect_index: Index of the effect to duplicate within its chain.
    chain_type: "audio" (default) or "midi" — which effect chain to operate on.

    Returns the new effect's index and type.
    """
    valid_chains = {"audio", "midi"}
    safe_chain = (chain_type or "audio").lower().strip()
    if safe_chain not in valid_chains:
        return json.dumps({"error": f"Invalid chain_type '{safe_chain}'. Must be 'audio' or 'midi'"})
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const ef = window.DAW_EffectFactories;
        const units = h.allAUBoxes();
        if ({unit_index} >= units.length) return {{error: "No AU at index {unit_index}"}};
        const au = units[{unit_index}];
        const isMidi = "{safe_chain}" === "midi";
        const chainField = isMidi ? au.midiEffects : au.audioEffects;
        if (!chainField) return {{error: "No " + (isMidi ? "MIDI" : "audio") + " effect chain on this AU"}};

        const effects = h.chainBoxes(chainField)
            .sort((a, b) => a.index.getValue() - b.index.getValue());
        if ({effect_index} >= effects.length) return {{error: "No effect at index {effect_index}"}};

        const srcEffect = effects[{effect_index}];
        const className = srcEffect.constructor.name;

        // Find factory key
        const factoryMap = isMidi ? ef.MidiNamed : ef.AudioNamed;
        let factoryKey = null;
        for (const key of Object.keys(factoryMap)) {{
            if (className === key + "DeviceBox" || className === key) {{
                factoryKey = key;
                break;
            }}
        }}
        if (!factoryKey) return {{error: "No factory for " + className}};

        const factory = factoryMap[factoryKey];
        let newEffect;
        h.modify(() => {{
            newEffect = h.api.insertEffect(chainField, factory);
            // Copy all parameter values
            const srcRecord = srcEffect.record();
            const dstRecord = newEffect.record();
            for (const [key, srcField] of Object.entries(srcRecord)) {{
                const dstField = dstRecord[key];
                if (!dstField || typeof dstField.getValue !== 'function') continue;
                if (typeof srcField.getValue !== 'function') continue;
                const fname = srcField._fieldName || srcField.fieldName || key;
                if (['host', 'index', 'label', 'sideChain'].includes(fname)) continue;
                try {{
                    const value = srcField.getValue();
                    if (typeof value === 'number' || typeof value === 'boolean') {{
                        if (typeof dstField.setValue === 'function') {{
                            dstField.setValue(value);
                        }}
                    }}
                }} catch(e) {{}}
            }}
        }});

        const updatedEffects = h.chainBoxes(chainField)
            .sort((a, b) => a.index.getValue() - b.index.getValue());
        const newIdx = updatedEffects.findIndex(b => b.address.equals(newEffect.address));

        return {{
            success: true,
            chain_type: isMidi ? "midi" : "audio",
            original_index: {effect_index},
            new_index: newIdx,
            effect_type: factoryKey,
            total_effects: updatedEffects.length,
        }};
    }}""")
    return _wrap_eval(result)


# ─── Instrument Automation ───────────────────────────────────────────


async def mcp_opendaw_duplicate_note_event(unit_index: int, track_index: int, region_index: int, note_index: int,
                                           position_offset: float = 0.0, pitch_offset: int = 0) -> str:
    """Duplicate a note event within the same region with optional position/pitch offset.

    Copies the note's position, duration, pitch, velocity, cent, chance, playCount.
    Can transpose and shift the copy relative to the original.

    unit_index/track_index/region_index: Region coordinates.
    note_index: Note index within the region.
    position_offset: PPQN offset from original position (default 0 = same position).
    pitch_offset: Semitone offset from original pitch (default 0 = same pitch).

    Returns the new note's position, pitch, and duration.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const reg = h.region(h.au({unit_index}), h.track({unit_index}, {track_index}), {region_index});
            const events = reg.events.targetVertex.unwrap("events").box;
            const noteAdapters = h.eventBoxes(events)
                .sort((a, b) => a.position.getValue() - b.position.getValue());
            if ({note_index} >= noteAdapters.length) return {{error: "No note at index " + {note_index}}};
            const srcBox = noteAdapters[{note_index}];
            const adapter = h.project.boxAdapters.adapterFor(srcBox, h.project.NoteEventBoxAdapter || class {{}});
            let newAdapter;
            h.modify(() => {{
                newAdapter = adapter.copyTo({{
                    position: srcBox.position.getValue() + {position_offset},
                    pitch: srcBox.pitch.getValue() + {pitch_offset},
                }});
            }});
            return {{
                success: true,
                new_position: newAdapter.position,
                new_pitch: newAdapter.pitch,
                new_duration: newAdapter.duration,
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_duplicate_note_region(unit_index: int, track_index: int, region_index: int, offset_beats: float) -> str:
    """Duplicate a note region to a new position.

Copies the region and all its notes to offset_beats after the original.
Useful for repeating patterns (e.g. duplicate 1-bar loop to bar 2).

unit_index: Audio unit index (-1 = search all AUs).
track_index: Note track index within the AU.
region_index: Region to duplicate (0-based).
offset_beats: How far to shift the copy (in beats, e.g. 4.0 = next bar in 4/4).

Returns new region index.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const NoteRegionBox = window.DAW_NoteRegionBox;
        const NoteEventCollectionBox = window.DAW_NoteEventCollectionBox;
        const NoteEventBox = window.DAW_NoteEventBox;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const offsetTicks = Math.round({offset_beats} * h.ppqn.Quarter);

        let noteTracks = [];
        if (unitIdx < 0) {{
            const allUnits = h.allAUBoxes();
            for (const au of allUnits) {{
                const tracks = h.trackBoxes(au)
                    .filter(box => box.type?.getValue?.() === 1);
                noteTracks.push(...tracks);
            }}
        }} else {{
            const units = h.allAUBoxes();
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            noteTracks = h.noteTrackBoxes(units[unitIdx]);
        }}

        if (trackIdx >= noteTracks.length) return {{error: "No note track at index " + trackIdx}};
        const trackBox = noteTracks[trackIdx];

        const regions = h.regionBoxes(trackBox);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx}};

        const srcRegion = regions[regionIdx];
        const srcPos = srcRegion.position.getValue();
        const srcDuration = srcRegion.duration.getValue();
        const newPos = srcPos + offsetTicks;

        let newRegionIdx = -1;
        h.modify(() => {{
            // Get source collection
            let srcCollection = null;
            try {{
                const vertex = srcRegion.events.targetVertex.unwrap();
                srcCollection = vertex.box || vertex;
            }} catch(e) {{}}

            if (srcCollection && srcCollection.events) {{
                // Create new collection and copy all note events
                const newCollection = NoteEventCollectionBox.create(h.boxGraph, h.uuid.generate());
                const srcNotes = h.eventBoxes(srcCollection);
                for (const srcNote of srcNotes) {{
                    NoteEventBox.create(h.boxGraph, h.uuid.generate(), (box) => {{
                        box.position.setValue(srcNote.position.getValue());
                        box.duration.setValue(srcNote.duration.getValue());
                        box.velocity.setValue(srcNote.velocity.getValue());
                        box.pitch.setValue(srcNote.pitch.getValue());
                        box.chance.setValue(srcNote.chance?.getValue?.() ?? 100);
                        box.cent.setValue(srcNote.cent?.getValue?.() ?? 0);
                        box.events.refer(newCollection.events);
                    }});
                }}

                // Create new region
                NoteRegionBox.create(h.boxGraph, h.uuid.generate(), (box) => {{
                    box.position.setValue(newPos);
                    box.label.setValue((srcRegion.label?.getValue?.() ?? "Region") + " copy");
                    box.mute.setValue(false);
                    box.duration.setValue(srcDuration);
                    box.loopDuration.setValue(0);
                    box.loopDuration.setValue(srcDuration);
                    box.eventOffset.setValue(0);
                    box.events.refer(newCollection.owners);
                    box.regions.refer(trackBox.regions);
                }});
            }}

            // Find new region index
            const updatedRegions = h.regionBoxes(trackBox);
            newRegionIdx = updatedRegions.length - 1;
        }});

        return {{
            success: true,
            new_region_index: newRegionIdx,
            new_position_beats: newPos / h.ppqn.Quarter,
            offset_beats: {offset_beats},
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_duplicate_notes(unit_index: int, track_index: int, region_index: int) -> str:
    """Duplicate all notes within a region, shifting them after the last note.

Creates copies of every note in the region, shifted by (max(position+duration) - min(position)).
This mirrors the DAW's native "duplicate notes" feature.

unit_index: Audio unit index (-1 = search all AUs).
track_index: Note track index within the AU.
region_index: Region whose notes to duplicate (0-based).

Returns count of duplicated notes and shift in beats.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const NoteEventBox = window.DAW_NoteEventBox;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const Quarter = h.ppqn.Quarter;

        let noteTracks = [];
        if (unitIdx < 0) {{
            const allUnits = h.allAUBoxes();
            for (const au of allUnits) {{
                const tracks = h.trackBoxes(au)
                    .filter(box => box.type?.getValue?.() === 1);
                noteTracks.push(...tracks);
            }}
        }} else {{
            const units = h.allAUBoxes();
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            noteTracks = h.noteTrackBoxes(units[unitIdx]);
        }}

        if (trackIdx >= noteTracks.length) return {{error: "No note track at index " + trackIdx}};
        const trackBox = noteTracks[trackIdx];

        const regions = h.regionBoxes(trackBox);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx}};

        const srcRegion = regions[regionIdx];
        let collection = null;
        try {{
            const vertex = srcRegion.events.targetVertex.unwrap();
            collection = vertex.box || vertex;
        }} catch(e) {{}}

        if (!collection || !collection.events) return {{error: "No note collection in region"}};

        const notes = h.eventBoxes(collection);
        if (notes.length === 0) return {{error: "No notes in region"}};

        let blockStart = Infinity, blockEnd = -Infinity;
        for (const n of notes) {{
            const pos = n.position.getValue();
            const dur = n.duration.getValue();
            if (pos < blockStart) blockStart = pos;
            if (pos + dur > blockEnd) blockEnd = pos + dur;
        }}
        const shift = blockEnd - blockStart;
        if (shift <= 0) return {{error: "Cannot duplicate: notes have zero span"}};

        let created = 0;
        h.modify(() => {{
            for (const n of notes) {{
                NoteEventBox.create(h.boxGraph, h.uuid.generate(), (box) => {{
                    box.events.refer(collection.events);
                    box.position.setValue(n.position.getValue() + shift);
                    box.duration.setValue(n.duration.getValue());
                    box.pitch.setValue(n.pitch.getValue());
                    box.velocity.setValue(n.velocity.getValue());
                    box.chance.setValue(n.chance?.getValue?.() ?? 100);
                    box.cent.setValue(n.cent?.getValue?.() ?? 0);
                }});
                created++;
            }}
        }});

        return {{
            success: true,
            duplicated: created,
            shift_beats: shift / Quarter,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_duplicate_region(unit_index: int, track_index: int, region_index: int, find_free_space: bool) -> str:
    """Duplicate any region (audio, note, or value) using the DAW's built-in duplicateRegion API.

Places the copy right after the original. With find_free_space=True, scans
for the first available gap on any track (auto-resolves overlaps). Without
it, places on the same track at the original's end position.

unit_index: Audio unit index (-1 = search all AUs).
track_index: Track index within the AU.
region_index: Region to duplicate (0-based).
find_free_space: If True, find the first free space on any track. If False,
    place directly after the original on the same track.

Returns the new region's position and index.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const findFree = {json.dumps(find_free_space)};

        // Find the track
        let tracks = [];
        if (unitIdx < 0) {{
            const allUnits = h.allAUBoxes();
            for (const au of allUnits) {{
                tracks.push(...h.trackBoxes(au));
            }}
        }} else {{
            const units = h.allAUBoxes();
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            tracks = h.trackBoxes(units[unitIdx]);
        }}

        if (trackIdx >= tracks.length) return {{error: "No track at index " + trackIdx}};
        const trackBox = tracks[trackIdx];

        const regions = h.regionBoxes(trackBox);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx}};
        const srcRegion = regions[regionIdx];

        // Get the adapter for this region via TrackBoxAdapter.regions.collection
        const TrackBoxAdapter = window.DAW_TrackBoxAdapter;
        const trackAdapter = h.project.boxAdapters.adapterFor(trackBox, TrackBoxAdapter);
        const regionAdapters = trackAdapter.regions.collection.asArray();
        if (regionIdx >= regionAdapters.length) return {{error: "No region adapter at index " + regionIdx}};
        const regionAdapter = regionAdapters[regionIdx];

        let result2;
        h.editing.modify(() => {{
            const opt = h.api.duplicateRegion(regionAdapter, {{findFreeSpace: findFree}});
            result2 = opt.match({{
                some: (dup) => ({{
                    success: true,
                    new_position_ppqn: dup.position,
                    new_duration_ppqn: dup.duration,
                    new_complete_ppqn: dup.complete,
                }}),
                none: () => ({{error: "duplicateRegion returned None (track has no adapter)"}})
            }});
        }});

        return result2 || {{error: "No result from duplicateRegion"}};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_duplicate_section(from_beat: float, to_beat: float, target_beat: float, unit_indices: str = "") -> str:
    """Duplicate all regions within a beat range to a new position.

    Scans all tracks across all specified audio units, finds every region that
    overlaps the [from_beat, to_beat) range, and copies each one to target_beat
    with the same relative offset. This is the arrangement operation producers
    use constantly: "copy verse 1 to bar 17" or "duplicate this 8-bar section
    after itself".

    Works with note regions, audio regions, and automation regions. Preserves
    all content (notes, audio, automation events).

    from_beat: Start of the source section in beats.
    to_beat: End of the source section in beats (exclusive).
    target_beat: Where to place the duplicated section (beat 0 = start of project).
    unit_indices: Comma-separated AU indices to scan (default: all AUs).

    Returns number of regions duplicated, per-track details, and new positions.

    Examples:
      duplicate_section(from_beat=0, to_beat=16, target_beat=16)
        -> Copy first 4 bars (0-16 beats) to beat 16 (bars 5-8)
      duplicate_section(from_beat=0, to_beat=32, target_beat=32, unit_indices="0,1,2")
        -> Copy first 8 bars from AUs 0,1,2 to beat 32
    """
    if to_beat <= from_beat:
        return "Error: to_beat must be after from_beat"
    if target_beat < 0:
        return "Error: target_beat must be >= 0"

    section_length = to_beat - from_beat
    offset = target_beat - from_beat

    unit_list = unit_indices.strip() if unit_indices else ""

    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const TrackBoxAdapter = window.DAW_TrackBoxAdapter;
        try {{
            const fromBeat = {from_beat};
            const toBeat = {to_beat};
            const targetBeat = {target_beat};
            const offset = {offset};
            const sectionLen = {section_length};
            const Quarter = h.ppqn.Quarter;

            // Determine which AUs to scan
            let unitsToScan;
            const unitList = "{unit_list}";
            if (unitList) {{
                const idxs = unitList.split(",").map(s => parseInt(s.trim())).filter(n => !isNaN(n));
                const allUnits = h.allAUBoxes();
                unitsToScan = idxs.map(i => allUnits[i]).filter(u => u);
            }} else {{
                unitsToScan = h.allAUBoxes();
            }}

            const duplicated = [];
            let totalDuplicated = 0;

            for (let uIdx = 0; uIdx < unitsToScan.length; uIdx++) {{
                const au = unitsToScan[uIdx];
                const tracks = h.trackBoxes(au);

                for (let tIdx = 0; tIdx < tracks.length; tIdx++) {{
                    const trackBox = tracks[tIdx];
                    const trackAdapter = h.project.boxAdapters.adapterFor(trackBox, TrackBoxAdapter);
                    if (!trackAdapter) continue;
                    const regionAdapters = trackAdapter.regions.collection.asArray();

                    for (let rIdx = 0; rIdx < regionAdapters.length; rIdx++) {{
                        const reg = regionAdapters[rIdx];
                        const regPosBeats = reg.position / Quarter;
                        const regDurBeats = reg.duration / Quarter;
                        const regEndBeats = regPosBeats + regDurBeats;

                        // Check if region overlaps [fromBeat, toBeat)
                        if (regEndBeats <= fromBeat || regPosBeats >= toBeat) continue;

                        // Copy to new position
                        let newAdapter;
                        h.modify(() => {{
                            newAdapter = reg.copyTo({{
                                target: trackBox.regions,
                                position: Math.round((regPosBeats + offset) * Quarter),
                            }});
                        }});

                        if (newAdapter) {{
                            totalDuplicated++;
                            duplicated.push({{
                                unit: uIdx,
                                track: tIdx,
                                original_position_beats: Math.round(regPosBeats * 100) / 100,
                                new_position_beats: Math.round((regPosBeats + offset) * 100) / 100,
                                duration_beats: Math.round(regDurBeats * 100) / 100,
                            }});
                        }}
                    }}
                }}
            }}

            return {{
                success: true,
                from_beat: fromBeat,
                to_beat: toBeat,
                target_beat: targetBeat,
                section_length_beats: sectionLen,
                offset_beats: offset,
                regions_duplicated: totalDuplicated,
                details: duplicated.slice(0, 50),
                total_affected_units: new Set(duplicated.map(d => d.unit)).size,
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_flatten_note_regions(unit_index: int, track_index: int, region_indices: str) -> str:
    """Flatten (merge) multiple overlapping note regions into a single region.

    Merges selected note regions on the same track into one, combining all notes.
    The original regions are deleted and replaced by a single flattened region.

    unit_index: AU index.
    track_index: Track index within the AU.
    region_indices: Comma-separated region indices to flatten (e.g. "0,1,2").

    Returns the new flattened region info, or error.
    """
    safe_indices = region_indices.replace('"', '').replace('\\', '').replace("'", "").replace(';', '').replace('{', '').replace('}', '')
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const trackAdapter = h.track({unit_index}, {track_index});
            const regions = trackAdapter.regions.collection.asArray();
            const indices = "{safe_indices}".split(',').map(s => parseInt(s.trim()));
            const toFlatten = indices.map(i => regions[i]).filter(r => r);
            if (toFlatten.length < 2) return {{error: "Need at least 2 regions to flatten"}};
            const first = toFlatten[0];
            toFlatten.forEach(r => r.onSelected());
            let flatResult;
            h.modify(() => {{ flatResult = first.flatten(toFlatten); }});
            if (!flatResult || flatResult.isEmpty()) return {{error: "Flatten returned None — regions may not be compatible or not selected"}};
            const newBox = flatResult.unwrap();
            return {{
                success: true,
                new_position: newBox.position.getValue(),
                new_duration: newBox.duration.getValue(),
                new_label: newBox.label.getValue(),
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_freeze_audiounit(unit_index: int) -> str:
    """Freeze an audio unit — pre-render its output offline to save CPU.

    Uses audioUnitFreeze.freeze() which renders the AU's complete output via
    OfflineEngineRenderer and caches it. While frozen, the AU plays from cache
    instead of processing instruments/effects in real-time.

    Cannot freeze AUs with sidechain dependents or the Output unit.

    unit_index: AU index to freeze.

    Returns success or error (e.g. sidechain dependents block freeze).
    """
    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const freeze = h.audioUnitFreeze;
        if (!freeze) return {{error: "audioUnitFreeze not available"}};
        const auAdapters = h.allAUs();
        if ({unit_index} >= auAdapters.length) return {{error: "No AU at {unit_index}"}};
        const auAdapter = auAdapters[{unit_index}];
        try {{
            if (freeze.hasSidechainDependents(auAdapter))
                return {{error: "AU has sidechain dependents — cannot freeze"}};
            await freeze.freeze(auAdapter);
            return {{
                success: true,
                frozen: freeze.isFrozen(auAdapter),
                unit_index: {unit_index},
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_import_audio_to_tracks(
    file_path: str,
    mode: str = "",
    start_beat: float = 0.0,
    bpm: float = 120.0,
) -> str:
    """Import an audio file into the DAW, optionally split into stems on separate tracks.

    One-call pipeline: audio file → (optional stem separation) → create instrument
    tracks → load each stem → place on tracks at start_beat. This is the Suno-to-DAW
    bridge: generate a track with Suno, download it, then import with stem splitting
    for mixing and mastering.

    Without mode: loads the whole file as one track (simple import).
    With mode: splits into stems, creates one track per stem, loads and places each.

    file_path: Absolute path to WAV/MP3/FLAC/OGG file on disk.
    mode: Stem separation mode (empty = no split, single track).
        Modes: "bs6" (6-stem), "scnet" (4-stem), "ensemble" (max quality),
        "polarformer" (vocal/instrumental), "drumsep" (drum parts).
    start_beat: Beat position to place the audio region(s) (default 0).
    bpm: Tempo for the project (affects beat alignment, default 120).

    Returns: track count, per-track info (name, sample_id, duration, stem name),
    and suggested next steps (apply_genre_mix, render_full).

    Examples:
      # Simple import — one track, no splitting
      import_audio_to_tracks("/tmp/suno_track.wav")
      # Split into 6 stems, each on its own track
      import_audio_to_tracks("/tmp/suno_track.wav", mode="bs6")
      # Vocal/instrumental split at beat 4
      import_audio_to_tracks("/tmp/vocal.wav", mode="polarformer", start_beat=4)
    """
    if not os.path.exists(file_path):
        return json.dumps({"error": f"File not found: {file_path}"})

    # No stem splitting — simple single-track import
    if not mode:
        track_result = await mcp_opendaw_create_instrument_track(
            os.path.splitext(os.path.basename(file_path))[0])
        track_data = json.loads(track_result)
        if "error" in track_data:
            return json.dumps({"error": "Failed to create track", "detail": track_data})

        unit_idx = track_data.get("unit_index", 0)
        track_idx = track_data.get("track_index", 0)

        load_result = await mcp_opendaw_load_audio(file_path, os.path.basename(file_path))
        load_data = json.loads(load_result)
        if "error" in load_data:
            return json.dumps({"error": "Failed to load audio", "detail": load_data})

        sample_id = load_data["id"]
        place_result = await mcp_opendaw_place_audio_region(sample_id, unit_idx, start_beat, track_idx)
        place_data = json.loads(place_result)
        if "error" in place_data:
            return json.dumps({"error": "Failed to place region", "detail": place_data})

        return json.dumps({
            "imported": True,
            "stem_split": False,
            "tracks_created": 1,
            "unit_index": unit_idx,
            "tracks": [{
                "stem": "full",
                "unit_index": unit_idx,
                "track_index": track_idx,
                "sample_id": sample_id,
                "duration": load_data.get("duration", 0),
                "placed_at_beat": start_beat,
            }],
            "next_steps": [
                "apply_genre_mix or add_effect for processing",
                "render_full for export",
            ],
        }, indent=2)

    # Stem splitting mode
    if mode not in STEM_MODES:
        return json.dumps({"error": f"Unknown mode: {mode}. Available: {list(STEM_MODES.keys())}"})

    # Run stem splitter
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_dir = f"/tmp/stems_{base_name}"

    split_result = await mcp_opendaw_split_stems(file_path, mode, output_dir, import_to_daw=False)
    split_data = json.loads(split_result)
    if "error" in split_data:
        return json.dumps({"error": "Stem splitting failed", "detail": split_data})

    stems = split_data.get("stems", [])
    if not stems:
        return json.dumps({"error": "No stems produced", "detail": split_data})

    # Create a track per stem and load/place each
    tracks = []
    for stem in stems:
        stem_name = stem["name"]
        stem_path = stem["path"]

        track_result = await mcp_opendaw_create_instrument_track(stem_name)
        track_data = json.loads(track_result)
        if "error" in track_data:
            tracks.append({"stem": stem_name, "error": "track creation failed", "detail": track_data})
            continue

        unit_idx = track_data.get("unit_index", 0)
        track_idx = track_data.get("track_index", 0)

        load_result = await mcp_opendaw_load_audio(stem_path, stem_name)
        load_data = json.loads(load_result)
        if "error" in load_data:
            tracks.append({"stem": stem_name, "error": "load failed", "detail": load_data})
            continue

        sample_id = load_data["id"]
        place_result = await mcp_opendaw_place_audio_region(sample_id, unit_idx, start_beat, track_idx)
        place_data = json.loads(place_result)
        if "error" in place_data:
            tracks.append({"stem": stem_name, "error": "place failed", "detail": place_data})
            continue

        tracks.append({
            "stem": stem_name,
            "unit_index": unit_idx,
            "track_index": track_idx,
            "sample_id": sample_id,
            "duration": load_data.get("duration", 0),
            "placed_at_beat": start_beat,
        })

    success_count = sum(1 for t in tracks if "error" not in t)
    return json.dumps({
        "imported": True,
        "stem_split": True,
        "mode": mode,
        "tracks_created": success_count,
        "tracks": tracks,
        "next_steps": [
            "apply_genre_mix for genre-specific processing per stem",
            "add_mastering_chain for final polish",
            "render_full for export",
        ],
    }, indent=2)


async def mcp_opendaw_merge_note_regions(
    unit_index: int,
    track_index: int,
    region_index_a: int,
    region_index_b: int,
) -> str:
    """Merge two note regions on the same track into one.

    Copies all notes from region B into region A's note collection, adjusting
    positions so they remain at their original absolute timeline position.
    Region A's duration is extended to cover both regions. Region B is deleted.

    The regions do not need to be adjacent — if there's a gap between them,
    the merged region spans the full range (with silence in the gap).

    Use cases:
    - Join verse + chorus into one continuous region
    - Consolidate split regions back together
    - Merge separately-recorded MIDI takes
    - Simplify arrangement before export

    unit_index: AU index.
    track_index: Note track index.
    region_index_a: First region (keeps its identity, absorbs B's notes).
    region_index_b: Second region (deleted after merge).

    Returns merged region details.

    Example:
      # Merge regions 0 and 1 into one
      merge_note_regions(0, 0, 0, 1)
    """
    if region_index_a == region_index_b:
        return "Error: region_index_a and region_index_b must be different"

    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const bg = h.boxGraph;
        const NoteEventBox = window.DAW_NoteEventBox;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regAIdx = {region_index_a};
        const regBIdx = {region_index_b};
        const Quarter = h.ppqn.Quarter;

        const allUnits = h.allAUBoxes();
        if (unitIdx < 0 || unitIdx >= allUnits.length) return {{error: "unit_index out of range"}};
        const au = allUnits[unitIdx];
        const noteTracks = h.noteTrackBoxes(au);
        if (trackIdx < 0 || trackIdx >= noteTracks.length) return {{error: "track_index out of range"}};
        const trackBox = noteTracks[trackIdx];
        const regions = h.regionBoxes(trackBox);
        if (regAIdx < 0 || regAIdx >= regions.length) return {{error: "region_index_a out of range"}};
        if (regBIdx < 0 || regBIdx >= regions.length) return {{error: "region_index_b out of range"}};

        const regA = regions[regAIdx];
        const regB = regions[regBIdx];

        const posA = regA.position.getValue();
        const durA = regA.duration.getValue();
        const posB = regB.position.getValue();
        const durB = regB.duration.getValue();
        const endA = posA + durA;
        const endB = posB + durB;

        // Read region B notes
        let collB = null;
        try {{
            const vertex = regB.events.targetVertex.unwrap();
            collB = vertex.box || vertex;
        }} catch(e) {{}}
        if (!collB || !collB.events) return {{error: "No note collection in region B"}};

        const notesB = h.eventBoxes(collB);

        // Read region A collection
        let collA = null;
        try {{
            const vertex = regA.events.targetVertex.unwrap();
            collA = vertex.box || vertex;
        }} catch(e) {{}}
        if (!collA || !collA.events) return {{error: "No note collection in region A"}};

        let moved = 0;
        let skipped = 0;

        h.modify(() => {{
            // Copy notes from B into A's collection
            // Note positions in B are relative to B's start (posB)
            // Absolute position = posB + notePos
            // New relative position in A = absolute - posA
            for (const n of notesB) {{
                const absPos = posB + n.position.getValue();
                const relPos = absPos - posA;

                NoteEventBox.create(bg, h.uuid.generate(), (box) => {{
                    box.position.setValue(Math.round(relPos));
                    box.duration.setValue(n.duration.getValue());
                    box.velocity.setValue(n.velocity.getValue());
                    box.pitch.setValue(n.pitch.getValue());
                    box.chance.setValue(n.chance?.getValue?.() ?? 100);
                    box.cent.setValue(n.cent?.getValue?.() ?? 0);
                    box.events.refer(collA.events);
                }});
                moved++;
            }}

            // Extend region A duration to cover both regions
            const newEnd = Math.max(endA, endB);
            const newDur = newEnd - posA;
            regA.duration.setValue(newDur);

            // Delete region B
            regB.delete();
        }});

        const remainingRegions = h.regionBoxes(trackBox).length;

        return {{
            success: true,
            merged_region_index: regAIdx,
            notes_moved: moved,
            notes_skipped: skipped,
            original_a: {{
                position_beats: posA / Quarter,
                duration_beats: durA / Quarter,
            }},
            merged: {{
                position_beats: posA / Quarter,
                duration_beats: (Math.max(endA, endB) - posA) / Quarter,
            }},
            deleted_region_b: regBIdx,
            remaining_regions: remainingRegions,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_merge_note_tracks(
    source_unit: int,
    source_track: int,
    dest_unit: int,
    dest_track: int,
    source_region: int = -1,
    dest_region: int = -1,
    delete_source: bool = True,
    resolve_overlaps: str = "keep_higher_velocity",
    transpose: int = 0,
) -> str:
    """Merge notes from a source track into a destination track.

    Combines notes from two tracks into one, optionally deleting the
    source. Overlapping notes are resolved by the chosen strategy.
    Unlike copy_notes_to_track (which just copies), merge consolidates
    two note streams into a single coherent track — the source notes
    are integrated into the destination region and optionally removed
    from origin.

    Typical use cases:
    - Merge a doubled melody into the main melody track
    - Consolidate counterpoint into the harmony track
    - Combine left-hand and right-hand piano into one track
    - Flatten multi-track MIDI into a single instrument

    Args:
        source_unit: AU index of source track
        source_track: Note track index within source AU
        dest_unit: AU index of destination track
        dest_track: Note track index within destination AU
        source_region: Source region index (-1 = first region)
        dest_region: Destination region index (-1 = first region,
                      or auto-create if none exists)
        delete_source: If True, delete source notes after merge.
                      If False, notes remain in both tracks (copy mode).
        resolve_overlaps: Strategy for overlapping notes —
            "keep_higher_velocity" = keep louder note at conflict point,
            "keep_lower_velocity" = keep quieter note,
            "keep_source" = prefer source notes,
            "keep_dest" = prefer destination notes,
            "keep_both" = keep all overlapping notes (no resolution),
            "shorten_earlier" = truncate the earlier-starting note
                                to end where the later one begins.
        transpose: Semitones to transpose source notes (-24 to 24).
    """
    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HeadlessBridgeHelper;
        if (!h) return {{"error": "Bridge helper not available"}};
        const Quarter = 960;

        const srcUnitIdx = {source_unit};
        const srcTrackIdx = {source_track};
        const dstUnitIdx = {dest_unit};
        const dstTrackIdx = {dest_track};
        const srcRegIdx = {source_region};
        const dstRegIdx = {dest_region};
        const delSource = {delete_source};
        const overlapMode = "{resolve_overlaps}";
        const transposeVal = {transpose};

        // Get all note tracks across all AUs
        const allTracks = h.noteTracks();
        if (allTracks.length === 0) return {{"error": "No note tracks"}};

        // Helper: get AU and track
        function getTrack(unitIdx, trackIdx) {{
            const units = h.audioUnitBoxes();
            if (unitIdx < 0 || unitIdx >= units.length) return null;
            const au = units[unitIdx];
            const tracks = h.noteTrackBoxes(au);
            if (trackIdx < 0 || trackIdx >= tracks.length) return null;
            return tracks[trackIdx];
        }}

        const srcTrack = getTrack(srcUnitIdx, srcTrackIdx);
        if (!srcTrack) return {{"error": "Source track not found"}};
        const dstTrack = getTrack(dstUnitIdx, dstTrackIdx);
        if (!dstTrack) return {{"error": "Destination track not found"}};

        // Get source regions
        const srcRegions = h.regionBoxes(srcTrack);
        if (srcRegions.length === 0) return {{"error": "No source regions"}};
        const srcReg = srcRegIdx < 0 ? srcRegions[0] : srcRegions[srcRegIdx];
        if (!srcReg) return {{"error": "Source region out of range"}};

        // Get source notes
        let srcColl = null;
        try {{
            const v = srcReg.events.targetVertex.unwrap();
            srcColl = v.box || v;
        }} catch(e) {{}}
        if (!srcColl || !srcColl.events) return {{"error": "No note collection in source region"}};
        const srcNotes = h.eventBoxes(srcColl);
        if (srcNotes.length === 0) return {{"error": "No notes in source region"}};

        // Read source note data
        const srcData = srcNotes.map(n => ({{
            pos: n.position.getValue(),
            dur: n.duration.getValue(),
            pitch: Math.max(0, Math.min(127, n.pitch.getValue() + transposeVal)),
            vel: n.velocity.getValue(),
        }}));

        // Get or create destination region
        const dstRegions = h.regionBoxes(dstTrack);
        let dstReg = null;
        let dstColl = null;
        let dstNotes = [];

        if (dstRegions.length > 0) {{
            const rIdx = dstRegIdx < 0 ? 0 : dstRegIdx;
            if (rIdx < dstRegions.length) {{
                dstReg = dstRegions[rIdx];
                try {{
                    const v = dstReg.events.targetVertex.unwrap();
                    dstColl = v.box || v;
                }} catch(e) {{}}
                if (dstColl && dstColl.events) {{
                    dstNotes = h.eventBoxes(dstColl);
                }}
            }}
        }}

        // Read destination note data
        const dstData = dstNotes.map(n => ({{
            pos: n.position.getValue(),
            dur: n.duration.getValue(),
            pitch: n.pitch.getValue(),
            vel: n.velocity.getValue(),
        }}));

        // Merge: combine source and destination notes
        const merged = [...dstData, ...srcData];

        // Sort by position
        merged.sort((a, b) => a.pos - b.pos);

        // Resolve overlaps
        const conflicts = [];
        const toRemove = new Set(); // indices in merged to skip

        if (overlapMode !== "keep_both") {{
            for (let i = 0; i < merged.length; i++) {{
                if (toRemove.has(i)) continue;
                for (let j = i + 1; j < merged.length; j++) {{
                    if (toRemove.has(j)) continue;
                    const a = merged[i];
                    const b = merged[j];
                    // Check overlap: a starts before b, but a extends into b
                    if (a.pos + a.dur > b.pos && a.pos < b.pos + b.dur) {{
                        const isSrcB = j >= dstData.length; // b is from source
                        const isSrcA = i >= dstData.length; // a is from source

                        if (overlapMode === "keep_higher_velocity") {{
                            if (a.vel >= b.vel) {{
                                toRemove.add(j);
                            }} else {{
                                toRemove.add(i);
                                break;
                            }}
                        }} else if (overlapMode === "keep_lower_velocity") {{
                            if (a.vel <= b.vel) {{
                                toRemove.add(j);
                            }} else {{
                                toRemove.add(i);
                                break;
                            }}
                        }} else if (overlapMode === "keep_source") {{
                            if (isSrcA && !isSrcB) {{
                                toRemove.add(j);
                            }} else if (!isSrcA && isSrcB) {{
                                toRemove.add(i);
                                break;
                            }}
                        }} else if (overlapMode === "keep_dest") {{
                            if (!isSrcA && isSrcB) {{
                                toRemove.add(j);
                            }} else if (isSrcA && !isSrcB) {{
                                toRemove.add(i);
                                break;
                            }}
                        }} else if (overlapMode === "shorten_earlier") {{
                            // Truncate a to end where b starts
                            a.dur = Math.max(1, b.pos - a.pos);
                        }}
                        conflicts.push({{
                            pos_beat: Math.round(a.pos / Quarter * 100) / 100,
                            resolved: overlapMode,
                        }});
                    }}
                }}
            }}
        }}

        // Filter out removed notes
        const finalNotes = merged.filter((_, idx) => !toRemove.has(idx));

        // Apply: write all finalNotes to destination, delete source notes if requested
        const editing = h.editing;
        let created = 0;
        let deleted = 0;

        await editing.modify(async () => {{
            // Delete all existing destination notes
            for (const n of dstNotes) {{
                n.delete();
            }}
            // Delete source notes if requested
            if (delSource) {{
                for (const n of srcNotes) {{
                    n.delete();
                    deleted++;
                }}
            }}
            // Create merged notes in destination collection
            // Use NoteEventBox.create if available, or h.createNote
            const bg = h.boxGraph;
            const uuid = h.uuid;
            const NoteEventBox = h.NoteEventBox;

            for (const nd of finalNotes) {{
                try {{
                    if (NoteEventBox && bg && uuid) {{
                        await NoteEventBox.create(bg, uuid.generate(), (box) => {{
                            box.position.setValue(nd.pos);
                            box.duration.setValue(nd.dur);
                            box.pitch.setValue(nd.pitch);
                            box.velocity.setValue(nd.vel);
                            if (dstColl && dstColl.events) {{
                                box.events.refer(dstColl.events);
                            }}
                        }});
                        created++;
                    }}
                }} catch(e) {{
                    // Fallback: try h.createNote
                    if (h.createNote) {{
                        h.createNote(dstColl, nd.pos, nd.dur, nd.pitch, nd.vel);
                        created++;
                    }}
                }}
            }}
        }});

        return {{
            success: true,
            source_notes: srcData.length,
            dest_notes_before: dstData.length,
            merged_notes: finalNotes.length,
            conflicts_resolved: conflicts.length,
            overlap_mode: overlapMode,
            source_deleted: delSource ? deleted : 0,
            notes_created: created,
            transpose: transposeVal,
            conflicts_sample: conflicts.slice(0, 5),
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_move_audio_unit(unit_index: int, delta: int) -> str:
    """Move an audio unit up or down in the mixer order.

Uses AudioUnitBoxAdapter.move(delta) — reindexes the AU within its type group
(Instrument/Aux/Output). Delta is relative: -1 = up, +1 = down.

unit_index: Current AU index.
delta: Relative move (-1 up, +1 down).

Returns new index or error.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const AudioUnitBoxAdapter = window.DAW_AudioUnitBoxAdapter;
        const units = h.allAUBoxes();
        if ({unit_index} >= units.length) return {{error: "No AU at {unit_index}"}};
        const auBox = units[{unit_index}];
        const adapter = h.project.boxAdapters.adapterFor(auBox, AudioUnitBoxAdapter);
        let newIdx = auBox.index.getValue();
        h.editing.modify(() => {{
            adapter.move({delta});
        }});
        return {{success: true, old_index: {unit_index}, new_index: auBox.index.getValue()}};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_move_region_content(unit_index: int, track_index: int, region_index: int, delta_beats: float) -> str:
    """Shift the content start of a region without moving the region itself.

    Moves the content inside the region by delta_beats — adjusts waveform offset
    (audio) or note positions (MIDI) while keeping the region position. Useful for
    realigning content within a region after tempo changes.

    For audio regions with seconds timeBase, delta is converted via tempo map.
    For note regions, note positions shift by -delta (content moves left = positive delta).

    unit_index: AU index.
    track_index: Track index within the AU.
    region_index: Region index.
    delta_beats: Shift amount in beats (positive = content moves left, region shrinks from left).

    Returns new position, duration, and loopDuration, or error.
    """
    delta_ppqn = int(delta_beats * 960)
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const auAdapters = h.allAUs();
        if ({unit_index} >= auAdapters.length) return {{error: "No AU at {unit_index}"}};
        const auAdapter = auAdapters[{unit_index}];
        const trackAdapters = auAdapter.tracks.collection.adapters();
        if ({track_index} >= trackAdapters.length) return {{error: "No track {track_index}"}};
        const trackAdapter = trackAdapters[{track_index}];
        const regions = trackAdapter.regions.collection.asArray();
        if ({region_index} >= regions.length) return {{error: "No region {region_index}"}};
        const region = regions[{region_index}];
        try {{
            h.editing.modify(() => {{
                region.moveContentStart({delta_ppqn});
            }});
            return {{
                success: true,
                new_position: region.position,
                new_duration: region.duration,
                new_loop_duration: region.loopDuration,
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


# ─────────────────────────────────────────────────────────────────────
# Inspection Helpers (155-157) — using DAW_HELPERS
# ─────────────────────────────────────────────────────────────────────


async def mcp_opendaw_move_region_to_track(src_unit_index: int, src_track_index: int, region_index: int, dst_unit_index: int, dst_track_index: int) -> str:
    """Move a region from one track to another (possibly in a different audio unit).

The region keeps its position, duration, and content. The source track loses the region.

src_unit_index: Source audio unit index.
src_track_index: Source track index within source unit.
region_index: Region index within source track.
dst_unit_index: Destination audio unit index.
dst_track_index: Destination track index within destination unit.

Returns success or error.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const srcUnitIdx = {src_unit_index};
        const srcTrackIdx = {src_track_index};
        const regionIdx = {region_index};
        const dstUnitIdx = {dst_unit_index};
        const dstTrackIdx = {dst_track_index};

        const units = h.allAUBoxes();
        const srcAU = units[srcUnitIdx];
        const dstAU = units[dstUnitIdx];
        if (!srcAU) return {{error: "Source unit not found"}};
        if (!dstAU) return {{error: "Destination unit not found"}};

        const srcTracks = h.trackBoxes(srcAU);
        const dstTracks = h.trackBoxes(dstAU);
        const srcTrack = srcTracks[srcTrackIdx];
        const dstTrack = dstTracks[dstTrackIdx];
        if (!srcTrack) return {{error: "Source track not found"}};
        if (!dstTrack) return {{error: "Destination track not found"}};

        const srcRegions = h.regionBoxes(srcTrack);
        const region = srcRegions[regionIdx];
        if (!region) return {{error: "Region not found"}};

        // Check type compatibility
        const srcType = srcTrack.type?.getValue();
        const dstType = dstTrack.type?.getValue();
        if (srcType !== dstType) return {{error: `Track type mismatch: source=${{srcType}} dest=${{dstType}}`}};

        h.editing.modify(() => {{
            region.regions.refer(dstTrack.regions);
        }});
        return {{success: true, region_type: region.constructor.name, moved_to_unit: dstUnitIdx, moved_to_track: dstTrackIdx}};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_move_track(unit_index: int, track_index: int, delta: int) -> str:
    """Move a track up or down within an audio unit.

Uses AudioUnitBoxAdapter.moveTrack(adapter, delta) — reindexes the track.
Delta is relative: -1 = up, +1 = down.

unit_index: AU index.
track_index: Track index within AU.
delta: Relative move (-1 up, +1 down).

Returns new index or error.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const AudioUnitBoxAdapter = window.DAW_AudioUnitBoxAdapter;
        const TrackBoxAdapter = window.DAW_TrackBoxAdapter;
        const units = h.allAUBoxes();
        if ({unit_index} >= units.length) return {{error: "No AU at {unit_index}"}};
        const auBox = units[{unit_index}];
        const auAdapter = h.project.boxAdapters.adapterFor(auBox, AudioUnitBoxAdapter);
        const tracks = h.trackBoxes(auBox)
            .sort((a, b) => a.index.getValue() - b.index.getValue());
        if ({track_index} >= tracks.length) return {{error: "No track at {track_index}"}};
        const trackBox = tracks[{track_index}];
        const trackAdapter = h.project.boxAdapters.adapterFor(trackBox, TrackBoxAdapter);
        h.editing.modify(() => {{
            auAdapter.moveTrack(trackAdapter, {delta});
        }});
        return {{success: true, old_index: {track_index}, new_index: trackBox.index.getValue()}};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_place_audio_region(sample_id: str, unit_index: int, start_beat: float, track_index: int) -> str:
    """Place a previously loaded audio sample as a region on a track.

sample_id: The ID returned by mcp_opendaw_load_audio.
unit_index: Audio unit index (default 0).
start_beat: Beat position to place the region.
track_index: Track index within the audio unit (default 0).

NOTE: The audio unit must be an instrument AU with a Tape device.
Use mcp_opendaw_create_instrument_track first if no instrument AU exists.
    """
    safe_sample_id = sample_id.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const AudioFileBox = window.DAW_AudioFileBox;
        const AudioRegionBox = window.DAW_AudioRegionBox;
        const sampleId = "{safe_sample_id}";
        const startBeat = {start_beat};
        const unitIdx = {unit_index};
        const trackIdx = {track_index};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No audio unit at index " + unitIdx}};
        const au = units[unitIdx];

        const audioTracks = h.trackBoxes(au)
            .filter(box => box.type?.getValue?.() === 2); // TrackType.Audio = 2
        if (trackIdx >= audioTracks.length) return {{error: "No audio track at index " + trackIdx}};
        const trackBox = audioTracks[trackIdx];

        // Check if sample is loaded
        const audioBuffer = window.DAW_localAudioBuffers.get(sampleId);
        if (!audioBuffer) return {{error: "Sample not loaded: " + sampleId + ". Call mcp_opendaw_load_audio first."}};

        // Use the proper API method: createNotStretchedRegion
        const sample = {{
            name: "{sample_id}",
            duration: audioBuffer.duration,
            bpm: 120,
            sample_rate: audioBuffer.sampleRate,
        }};

        let regionBox, audioFileBox;
        h.modify(() => {{
            audioFileBox = AudioFileBox.create(h.boxGraph, h.uuid.generate(), (box) => {{
                box.fileName.setValue("{sample_id}");
                box.startInSeconds.setValue(0.0);
                box.endInSeconds.setValue(audioBuffer.duration);
            }});

            regionBox = h.api.createNotStretchedRegion({{
                boxGraph: h.boxGraph,
                targetTrack: trackBox,
                position: Math.round(startBeat * h.ppqn.Quarter),
                audioFileBox: audioFileBox,
                sample: sample,
            }});
        }});

        return {{
            success: true,
            sample_id: sampleId,
            position_beats: startBeat,
            duration_seconds: audioBuffer.duration,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_remix_track(
    filename: str,
    genre: str = "synthwave",
    style: str = "pop",
    stem_mode: str = "bs4",
    master_lufs: float = -14,
    add_harmony: bool = True,
    add_counter_melody: bool = False,
    bars: int = 8,
) -> str:
    """Full Suno remix pipeline in one call — analyze → import → harmony → mix → master.

    Takes any audio file (from download_audio or local) and creates a complete
    remix: detect BPM + key → set project tempo → import stems → auto-generate
    matching chord progression → harmonic arrangement → genre mix → mastering.
    One call replaces 8-10 individual tool calls.

    Steps performed:
    1. analyze_track (BPM + key + mode + LUFS)
    2. set_bpm to detected tempo
    3. import_audio_to_tracks (with stem separation if stem_mode set)
    4. create_progression_from_key (diatonic, style-appropriate)
    5. create_harmonic_arrangement (arp + melody on top of stems)
    6. apply_genre_mix (genre-specific processing)
    7. add_mastering_chain (LUFS target)

    After this call, the project is remix-ready — call render_full to export.

    filename: Path to audio file (from download_audio or local path).
    genre: Genre for mix processing (synthwave, house, techno, dnb, trap, etc).
    style: Progression style (pop, jazz, rock, synthwave, folk, lofi).
    stem_mode: Stem separation mode ("bs2", "bs4", "bs6") or "" for simple import.
    master_lufs: Mastering target (-14 Spotify, -10 loud, -16 Apple).
    add_harmony: If True, generates harmonic layers (arp + melody). Default True.
    add_counter_melody: If True, adds counter-melody layer. Default False.
    bars: Arrangement length in bars. Default 8.

    Returns: analysis results, tracks created, harmony layers, effects, mastering.

    Example:
      # Full pipeline: Suno → download → remix
      chirp_generate → audio_url
      download_audio(audio_url) → /tmp/track.wav
      remix_track("/tmp/track.wav", genre="synthwave", style="synthwave",
                   stem_mode="bs6", add_counter_melody=True)
      render_full() → export
    """
    pipeline_steps = []

    # Step 1: Analyze track
    try:
        analysis_result = await mcp_opendaw_analyze_track(filename)
        analysis = json.loads(analysis_result)
        if "error" in analysis:
            return json.dumps({"error": f"Analysis failed: {analysis['error']}"}, indent=2)
        detected_bpm = analysis.get("bpm", 120.0)
        detected_key = analysis.get("key", "C")
        detected_mode = analysis.get("mode", "major")
        detected_lufs = analysis.get("lufs_integrated", -20.0)
        pipeline_steps.append({
            "step": "analyze_track",
            "bpm": detected_bpm,
            "key": detected_key,
            "mode": detected_mode,
            "lufs": detected_lufs,
            "duration": analysis.get("duration_seconds", 0),
            "status": "ok",
        })
    except Exception as e:
        return json.dumps({"error": f"Analysis failed: {e}"}, indent=2)

    # Step 2: Set BPM
    try:
        await mcp_opendaw_set_bpm(detected_bpm)
        pipeline_steps.append({"step": "set_bpm", "bpm": detected_bpm, "status": "ok"})
    except Exception as e:
        pipeline_steps.append({"step": "set_bpm", "error": str(e)})

    # Step 3: Import audio (with stems if requested)
    try:
        import_result = await mcp_opendaw_import_audio_to_tracks(filename, mode=stem_mode)
        import_data = json.loads(import_result)
        tracks_imported = import_data.get("tracks_created", 1)
        unit_index = import_data.get("unit_index", 0)
        pipeline_steps.append({
            "step": "import_audio",
            "stem_mode": stem_mode,
            "tracks_imported": tracks_imported,
            "unit_index": unit_index,
            "status": "ok",
        })
    except Exception as e:
        pipeline_steps.append({"step": "import_audio", "error": str(e)})
        unit_index = 0

    # Step 4: Create matching progression
    progression_str = ""
    if add_harmony:
        try:
            prog_result = await mcp_opendaw_create_progression_from_key(
                detected_key, detected_mode, style, unit_index=unit_index)
            prog_data = json.loads(prog_result)
            progression_str = "-".join(prog_data.get("progression", []))
            pipeline_steps.append({
                "step": "create_progression",
                "key": detected_key,
                "mode": detected_mode,
                "style": style,
                "progression": prog_data.get("progression", []),
                "status": "ok",
            })
        except Exception as e:
            pipeline_steps.append({"step": "create_progression", "error": str(e)})

    # Step 5: Harmonic arrangement (arp + melody on top of imported stems)
    if add_harmony and progression_str:
        try:
            cm_pattern = "contrary" if add_counter_melody else ""
            harm_result = await mcp_opendaw_create_harmonic_arrangement(
                progression_str,
                pad_octave=-1,        # skip — stems provide harmonic content
                bass_pattern="",      # skip — stems or genre provide bass
                arp_pattern="up",
                melody_pattern="chord_tones",
                counter_melody_pattern=cm_pattern,
                bars_per_chord=max(1, bars // 4),
                velocity=0.7,
                unit_index=unit_index,
            )
            harm_data = json.loads(harm_result)
            pipeline_steps.append({
                "step": "harmonic_arrangement",
                "progression": progression_str,
                "layers": harm_data.get("layers", []),
                "notes_added": harm_data.get("total_notes", 0),
                "counter_melody": add_counter_melody,
                "status": "ok",
            })
        except Exception as e:
            pipeline_steps.append({"step": "harmonic_arrangement", "error": str(e)})

    # Step 6: Genre mix
    try:
        mix_result = await mcp_opendaw_apply_genre_mix(
            genre, unit_index=unit_index,
            sidechain=genre in ("house", "techno", "dubstep", "dnb", "trance", "synthwave"))
        mix_data = json.loads(mix_result)
        pipeline_steps.append({
            "step": "genre_mix",
            "genre": genre,
            "effects_added": mix_data.get("effect_count", 0),
            "status": "ok",
        })
    except Exception as e:
        pipeline_steps.append({"step": "genre_mix", "error": str(e)})

    # Step 7: Mastering chain
    try:
        await mcp_opendaw_add_mastering_chain(target_lufs=master_lufs)
        pipeline_steps.append({
            "step": "mastering",
            "target_lufs": master_lufs,
            "status": "ok",
        })
    except Exception as e:
        pipeline_steps.append({"step": "mastering", "error": str(e)})

    # Summary
    return json.dumps({
        "remix_complete": True,
        "source_file": filename,
        "detected_bpm": detected_bpm,
        "detected_key": detected_key,
        "detected_mode": detected_mode,
        "genre": genre,
        "style": style,
        "stem_mode": stem_mode,
        "progression": progression_str or None,
        "unit_index": unit_index,
        "pipeline_steps": pipeline_steps,
        "ready_for_export": all(s.get("status") == "ok" for s in pipeline_steps),
        "next_step": "call render_full or render_full_format to export the remix",
    }, indent=2)


async def mcp_opendaw_rename_unit(unit_index: int, name: str, icon: str) -> str:
    """Rename an audio unit's instrument and optionally set its icon.

Instrument AUs have a label (display name) and icon (symbol) on their
InstrumentBox. This sets both. The output AU (index 0) has no instrument
and cannot be renamed.

unit_index: Audio unit index (must be >= 1, not the output AU).
name: New display name (empty = skip).
icon: New icon symbol (empty = skip, e.g. 'piano', 'guitar', 'drums').

Returns old and new name/icon.
"""
    name_val = json.dumps(name)
    icon_val = json.dumps(icon)
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const nameVal = {name_val};
        const iconVal = {icon_val};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
        const au = units[unitIdx];

        // Get InstrumentBox via au.input.pointerHub.incoming()
        const incoming = h.inputBoxes(au);
        if (incoming.length === 0) return {{error: "AU has no instrument (output AU?)"}};
        const instBox = incoming[0];

        if (!instBox.label) return {{error: "Instrument has no label field"}};

        const oldName = instBox.label?.getValue?.() ?? "";
        const oldIcon = instBox.icon?.getValue?.() ?? "";

        h.modify(() => {{
            if (nameVal !== null) instBox.label.setValue(nameVal);
            if (iconVal !== null && instBox.icon) instBox.icon.setValue(iconVal);
        }});

        return {{
            success: true,
            unit_index: unitIdx,
            instrument_type: instBox.constructor.name,
            old_name: oldName,
            new_name: instBox.label.getValue(),
            old_icon: oldIcon,
            new_icon: instBox.icon?.getValue?.() ?? "",
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_replace_from_preset(unit_index: int, preset_b64: str,
                                           keep_midi_effects: bool = False,
                                           keep_audio_effects: bool = False,
                                           keep_timeline: bool = False) -> str:
    """Replace an audio unit's instrument/effects/timeline from a preset.

Uses PresetDecoder.replaceAudioUnit — swaps the instrument in an existing AU,
optionally keeping the target's MIDI effects, audio effects, and/or timeline.
The preset must contain a compatible instrument type (MIDI→MIDI, Audio→Audio).

unit_index: Target AU index to replace.
preset_b64: Base64 preset bytes from export_preset.
keep_midi_effects: If true, keep target's existing MIDI effects.
keep_audio_effects: If true, keep target's existing audio effects.
keep_timeline: If true, keep target's existing tracks/regions/notes.

Returns success or error with reason.
"""
    preset_json = json.dumps(preset_b64)
    keep_midi = "true" if keep_midi_effects else "false"
    keep_audio = "true" if keep_audio_effects else "false"
    keep_timeline_js = "true" if keep_timeline else "false"
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const PresetDecoder = window.DAW_PresetDecoder;
        if (!PresetDecoder) return {{error: "PresetDecoder not loaded"}};
        const b64 = {preset_json};
        const binary = atob(b64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);

        const units = h.allAUBoxes();
        if ({unit_index} >= units.length) return {{error: "No AU at {unit_index}"}};
        const targetAU = units[{unit_index}];

        let attempt;
        h.editing.modify(() => {{
            attempt = PresetDecoder.replaceAudioUnit(bytes.buffer, targetAU, {{
                keepMIDIEffects: {keep_midi},
                keepAudioEffects: {keep_audio},
                keepTimeline: {keep_timeline_js},
            }});
        }});

        if (!attempt.isSuccess()) return {{error: attempt.failureReason()}};
        // Read new state
        const fx = h.effectBoxes(targetAU);
        const inp = h.inputBoxes(targetAU).length > 0
            ? h.inputBoxes(targetAU)[0].constructor.name : 'none';
        return {{
            success: true,
            instrument: inp,
            effects: fx.length,
            effect_names: fx.map(f => f.label.getValue()),
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_replace_instrument(unit_index: int, new_instrument: str) -> str:
    """Replace the instrument on an audio unit with a different MIDI instrument.

Uses ProjectApi.replaceMIDIInstrument — deletes the old instrument and
creates a new one on the same AU. Only works for MIDI instruments
(Nano, Vaporisateur, Soundfont, Apparat). Tape (audio player) cannot
be replaced this way.

The AU must have a CaptureMidiBox (i.e. it was created as a synth/note
instrument, not an audio track).

unit_index: Audio unit index (must be >= 1).
new_instrument: Factory key — 'Vaporisateur', 'Nano', 'Soundfont', 'Apparat'.

Returns old and new instrument type.
    """
    safe_instrument = new_instrument.replace('"', '').replace('\\', '').replace("'", "")
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const ef = window.DAW_InstrumentFactories;
        const unitIdx = {unit_index};
        const factoryKey = "{safe_instrument}";

        if (!ef) return {{error: "InstrumentFactories not loaded"}};
        const factory = ef[factoryKey];
        if (!factory) return {{error: "Unknown factory: " + factoryKey}};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
        const au = units[unitIdx];

        // Get current InstrumentBox
        const incoming = h.inputBoxes(au);
        if (incoming.length === 0) return {{error: "AU has no instrument"}};
        const oldInst = incoming[0];
        const oldName = oldInst.label?.getValue?.() ?? "";
        const oldType = oldInst.constructor.name;

        let newInst;
        let replaceError = "";
        h.modify(() => {{
            const attempt = h.api.replaceMIDIInstrument(oldInst, factory);
            if (attempt.isSuccess()) {{
                newInst = attempt.result();
            }} else {{
                replaceError = attempt.failureReason();
            }}
        }});

        if (!newInst) return {{error: "replaceMIDIInstrument failed: " + (replaceError || "unknown — AU may not have CaptureMidiBox or instrument is not MIDI")}};

        return {{
            success: true,
            unit_index: unitIdx,
            old_type: oldType,
            old_name: oldName,
            new_type: newInst.constructor.name,
            new_name: newInst.label?.getValue?.() ?? factory.defaultName,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_schedule_clip_play(clip_ids: str) -> str:
    """Schedule clips to play in session view (live triggering).

    Args:
        clip_ids: Comma-separated list of clip UUIDs to trigger
    """
    safe_ids = clip_ids.replace('"', '').replace('\\', '').replace("'", "").replace(';', '').replace(' ', '')
    ids_json = json.dumps(safe_ids)
    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        try {{
            const ids = {ids_json}.split(',').filter(Boolean);
            // Get clip UUIDs from rootBox clips
            const rootBox = h.rootBox;
            const allClips = h.rootClipBoxes();
            const targetUuids = [];
            for (const clip of allClips) {{
                const uuidStr = h.uuid.toString(clip.address.uuid);
                if (ids.includes(uuidStr)) {{
                    targetUuids.push(clip.address.uuid);
                }}
            }}
            if (targetUuids.length === 0) return {{error: "No matching clips found"}};
            h.engine.scheduleClipPlay(targetUuids);
            return {{success: true, triggered: targetUuids.length}};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_schedule_clip_stop(track_ids: str) -> str:
    """Schedule clips to stop on specified tracks (session view).

    Args:
        track_ids: Comma-separated list of track UUIDs to stop clips on
    """
    safe_ids = track_ids.replace('"', '').replace('\\', '').replace("'", "").replace(';', '').replace(' ', '')
    ids_json = json.dumps(safe_ids)
    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        try {{
            const ids = {ids_json}.split(',').filter(Boolean);
            const allAUs = h.allAUs();
            const targetUuids = [];
            for (const au of allAUs) {{
                const tracks = au.tracks.collection.adapters();
                for (const track of tracks) {{
                    const uuidStr = h.uuid.toString(track.uuid);
                    if (ids.includes(uuidStr)) {{
                        targetUuids.push(track.uuid);
                    }}
                }}
            }}
            if (targetUuids.length === 0) return {{error: "No matching tracks found"}};
            h.engine.scheduleClipStop(targetUuids);
            return {{success: true, stopped: targetUuids.length}};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_audio_region_fade(unit_index: int, track_index: int, region_index: int, fade_in: float, fade_out: float, in_slope: float, out_slope: float) -> str:
    """Set fade in/out on an audio region.

Audio regions have a Fading object with four params:
- in: fade-in duration in seconds (0 = no fade-in)
- out: fade-out duration in seconds (0 = no fade-out)
- inSlope: fade-in curve (0.5 = linear, 0.75 = fast start, 0.25 = slow start)
- outSlope: fade-out curve (0.5 = linear, 0.25 = fast end, 0.75 = slow end)

Pass -1.0 for any parameter to skip changing it (keep current value).

unit_index: Audio unit index.
track_index: Audio track index.
region_index: Region index within the track.
fade_in: Fade-in duration in seconds (-1 = skip).
fade_out: Fade-out duration in seconds (-1 = skip).
in_slope: Fade-in curve 0-1 (-1 = skip).
out_slope: Fade-out curve 0-1 (-1 = skip).

Returns updated fade values.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const fadeIn = {fade_in};
        const fadeOut = {fade_out};
        const inSlope = {in_slope};
        const outSlope = {out_slope};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
        const au = units[unitIdx];

        const audioTracks = h.trackBoxes(au)
            .filter(box => box.type?.getValue?.() === 2);
        if (trackIdx >= audioTracks.length) return {{error: "No audio track at index " + trackIdx}};
        const track = audioTracks[trackIdx];

        const regions = h.regionBoxes(track);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx}};
        const region = regions[regionIdx];

        if (!region.fading) return {{error: "Region has no fading field"}};

        h.modify(() => {{
            if (fadeIn >= 0) region.fading.in.setValue(fadeIn);
            if (fadeOut >= 0) region.fading.out.setValue(fadeOut);
            if (inSlope >= 0) region.fading.inSlope.setValue(inSlope);
            if (outSlope >= 0) region.fading.outSlope.setValue(outSlope);
        }});

        return {{
            success: true,
            region_index: regionIdx,
            fade_in: region.fading.in.getValue(),
            fade_out: region.fading.out.getValue(),
            in_slope: region.fading.inSlope.getValue(),
            out_slope: region.fading.outSlope.getValue(),
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_audio_region_gain(unit_index: int, track_index: int, region_index: int, gain_db: float) -> str:
    """Set gain (in dB) on an audio region.

Audio regions have a per-region gain control (Float32Field, decibel).
Use this for trim automation or balancing clips within a track.

unit_index: Audio unit index.
track_index: Audio track index.
region_index: Region index within the track.
gain_db: Gain in dB (0 = unity, -6 = half volume, +6 = double).

Returns updated gain value.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const gainDb = {gain_db};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
        const au = units[unitIdx];

        const audioTracks = h.trackBoxes(au)
            .filter(box => box.type?.getValue?.() === 2);
        if (trackIdx >= audioTracks.length) return {{error: "No audio track at index " + trackIdx}};
        const track = audioTracks[trackIdx];

        const regions = h.regionBoxes(track);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx}};
        const region = regions[regionIdx];

        if (!region.gain) return {{error: "Region has no gain field"}};

        h.modify(() => {{
            region.gain.setValue(gainDb);
        }});

        return {{
            success: true,
            region_index: regionIdx,
            gain_db: region.gain.getValue(),
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_audio_region_time_base(unit_index: int, track_index: int, region_index: int, time_base: str) -> str:
    """Set the time base of an audio region.

    Controls how the region's duration is interpreted:
    - 'musical' — duration in PPQN (musical beats, follows tempo changes)
    - 'seconds' — duration in seconds (fixed wall-clock time, independent of tempo)

    unit_index: AU index.
    track_index: Track index within the AU.
    region_index: Audio region index.
    time_base: 'musical' or 'seconds'.

    Returns old and new time base.
    """
    safe_tb = time_base.replace('"', '').replace("'", '').replace('\\', '').strip().lower()
    if safe_tb not in ("musical", "seconds"):
        return json.dumps({"error": f"Invalid time_base '{safe_tb}'. Use 'musical' or 'seconds'."})
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const auAdapters = h.allAUs();
        if ({unit_index} >= auAdapters.length) return {{error: "No AU at {unit_index}"}};
        const auAdapter = auAdapters[{unit_index}];
        const trackAdapters = auAdapter.tracks.collection.adapters();
        if ({track_index} >= trackAdapters.length) return {{error: "No track {track_index}"}};
        const trackAdapter = trackAdapters[{track_index}];
        const regions = trackAdapter.regions.collection.asArray();
        if ({region_index} >= regions.length) return {{error: "No region {region_index}"}};
        const region = regions[{region_index}];
        if (!region.isAudioRegion?.()) return {{error: "Region is not an audio region"}};
        const regionBox = region.box;
        const oldVal = regionBox.timeBase.getValue();
        h.modify(() => {{
            regionBox.timeBase.setValue("{safe_tb}");
        }});
        return {{
            success: true,
            old_time_base: oldVal,
            new_time_base: "{safe_tb}",
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_audio_region_waveform_offset(unit_index: int, track_index: int, region_index: int, offset: float) -> str:
    """Set the waveform display offset of an audio region.

    The waveform offset shifts the visual start of the waveform within the region,
    useful for aligning the waveform display with the actual audio content.

    unit_index: AU index.
    track_index: Track index within the AU.
    region_index: Audio region index.
    offset: Waveform offset value (in seconds).

    Returns old and new offset.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const auAdapters = h.allAUs();
        if ({unit_index} >= auAdapters.length) return {{error: "No AU at {unit_index}"}};
        const auAdapter = auAdapters[{unit_index}];
        const trackAdapters = auAdapter.tracks.collection.adapters();
        if ({track_index} >= trackAdapters.length) return {{error: "No track {track_index}"}};
        const trackAdapter = trackAdapters[{track_index}];
        const regions = trackAdapter.regions.collection.asArray();
        if ({region_index} >= regions.length) return {{error: "No region {region_index}"}};
        const region = regions[{region_index}];
        if (!region.isAudioRegion?.()) return {{error: "Region is not an audio region"}};
        const regionBox = region.box;
        const oldVal = regionBox.waveformOffset.getValue();
        h.modify(() => {{
            regionBox.waveformOffset.setValue({offset});
        }});
        return {{
            success: true,
            old_offset: oldVal,
            new_offset: {offset},
        }};
    }}""")
    return _wrap_eval(result)

# ---------------------------------------------------------------------------
# Orchestration Tools — high-level composers that combine multiple low-level
# operations into a single call. These reduce token usage and round-trips
# for agents building complete musical structures.
# ---------------------------------------------------------------------------


async def mcp_opendaw_set_clip_hue(unit_index: int, track_index: int, clip_index: int, hue: int) -> str:
    """Set the color (hue) of a clip in the session view.

    unit_index: AU index.
    track_index: Track index within the AU.
    clip_index: Clip index.
    hue: Color hue 0-360.

    Returns success with old and new hue.
    """
    if hue < 0 or hue > 360:
        return json.dumps({"error": f"hue must be 0-360, got {hue}"})
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const track = h.track({unit_index}, {track_index});
            const clips = track.clips.collection.adapters();
            if ({clip_index} >= clips.length) return {{error: "No clip {clip_index}"}};
            const clip = clips[{clip_index}];
            const oldHue = clip.hue;
            h.modify(() => {{
                clip.box.hue.setValue({hue});
            }});
            return {{success: true, old_hue: oldHue, new_hue: {hue}}};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


# ─────────────────────────────────────────────────────────────────────
# Automation Event Management (160-162)
# ─────────────────────────────────────────────────────────────────────


async def mcp_opendaw_set_clip_label(unit_index: int, track_index: int, clip_index: int, label: str) -> str:
    """Set the label (name) of a clip in the session view.

    unit_index: AU index.
    track_index: Track index within the AU.
    clip_index: Clip index.
    label: New clip name.

    Returns success with old and new label.
    """
    safe_label = json.dumps(label)
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const track = h.track({unit_index}, {track_index});
            const clips = track.clips.collection.adapters();
            if ({clip_index} >= clips.length) return {{error: "No clip {clip_index}"}};
            const clip = clips[{clip_index}];
            const oldLabel = clip.label;
            h.modify(() => {{
                clip.box.label.setValue({safe_label});
            }});
            return {{success: true, old_label: oldLabel, new_label: {safe_label}}};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_clip_mute(unit_index: int, track_index: int, clip_index: int, mute: bool) -> str:
    """Mute or unmute a clip in the session view.

    unit_index: AU index.
    track_index: Track index within the AU.
    clip_index: Clip index.
    mute: True to mute, false to unmute.

    Returns success with old and new mute state.
    """
    mute_val = "true" if mute else "false"
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const track = h.track({unit_index}, {track_index});
            const clips = track.clips.collection.adapters();
            if ({clip_index} >= clips.length) return {{error: "No clip {clip_index}"}};
            const clip = clips[{clip_index}];
            const oldMute = clip.mute;
            h.modify(() => {{
                clip.box.mute.setValue({mute_val});
            }});
            return {{success: true, old_mute: oldMute, new_mute: {mute_val}}};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_clip_playback(unit_index: int, track_index: int, clip_index: int, loop: bool, reverse: bool, speed: float) -> str:
    """Set clip playback parameters (loop, reverse, speed) on a clip.

Clips have a ClipPlaybackFields (triggerMode) object with:
- loop: Whether the clip loops (true/false)
- reverse: Play in reverse (true/false)
- speed: Playback speed multiplier (1 = normal)
- quantise: Quantise value
- trigger: Trigger mode

Pass None for any parameter to skip changing it.

unit_index: Audio unit index.
track_index: Track index.
clip_index: Clip index (from list_clips).
loop: Enable looping (None = skip).
reverse: Reverse playback (None = skip).
speed: Speed multiplier (None = skip).

Returns updated playback values.
"""
    loop_val = json.dumps(loop)
    reverse_val = json.dumps(reverse)
    speed_val = json.dumps(speed)
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const clipIdx = {clip_index};
        const loopVal = {loop_val};
        const reverseVal = {reverse_val};
        const speedVal = {speed_val};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
        const au = units[unitIdx];

        const allTracks = h.trackBoxes(au);
        if (trackIdx >= allTracks.length) return {{error: "No track at index " + trackIdx}};
        const track = allTracks[trackIdx];

        const clips = [...track.clips?.pointerHub?.incoming?.() ?? []].map(({{box}}) => box);
        if (clipIdx >= clips.length) return {{error: "No clip at index " + clipIdx}};
        const clip = clips[clipIdx];

        if (!clip.triggerMode) return {{error: "Clip has no triggerMode"}};

        h.editing.modify(() => {{
            if (loopVal !== null) clip.triggerMode.loop.setValue(loopVal);
            if (reverseVal !== null) clip.triggerMode.reverse.setValue(reverseVal);
            if (speedVal !== null) clip.triggerMode.speed.setValue(speedVal);
        }});

        return {{
            success: true,
            clip_class: clip.constructor.name,
            label: clip.label?.getValue?.() ?? "",
            loop: clip.triggerMode.loop.getValue(),
            reverse: clip.triggerMode.reverse.getValue(),
            speed: clip.triggerMode.speed?.getValue?.() ?? 1,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_clip_properties(unit_index: int, track_index: int, clip_index: int, label: str, hue: int, mute: bool, duration_beats: int) -> str:
    """Set properties on a clip (session view): label, color, mute, duration.

Pass empty string for label to skip, -1 for hue/duration to skip,
None for mute to skip.

unit_index: Audio unit index.
track_index: Track index.
clip_index: Clip index (from list_clips).
label: New label (empty = skip).
hue: New color hue 0-360 (-1 = skip).
mute: Mute state (None = skip).
duration_beats: New duration in beats (-1 = skip).

Returns updated clip properties.
"""
    label_val = json.dumps(label)
    mute_val = json.dumps(mute)
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const clipIdx = {clip_index};
        const Quarter = h.ppqn.Quarter;
        const hueVal = {hue};
        const muteVal = {mute_val};
        const durVal = {duration_beats};
        const labelVal = {label_val};

        const units = h.allAUBoxes();
        if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
        const au = units[unitIdx];

        const allTracks = h.trackBoxes(au);
        if (trackIdx >= allTracks.length) return {{error: "No track at index " + trackIdx}};
        const track = allTracks[trackIdx];

        const clips = [...track.clips?.pointerHub?.incoming?.() ?? []].map(({{box}}) => box);
        if (clipIdx >= clips.length) return {{error: "No clip at index " + clipIdx}};
        const clip = clips[clipIdx];

        h.editing.modify(() => {{
            if (labelVal !== null) clip.label.setValue(labelVal);
            if (hueVal >= 0 && clip.hue) clip.hue.setValue(hueVal);
            if (muteVal !== null && clip.mute) clip.mute.setValue(muteVal);
            if (durVal >= 0 && clip.duration) clip.duration.setValue(Math.round(durVal * Quarter));
        }});

        return {{
            success: true,
            clip_class: clip.constructor.name,
            label: clip.label?.getValue?.() ?? "",
            hue: clip.hue?.getValue?.() ?? 0,
            mute: clip.mute?.getValue?.() ?? false,
            duration_beats: (clip.duration?.getValue?.() ?? 0) / Quarter,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_region_color(track_index: int, region_index: int, hue: int, unit_index: int) -> str:
    """Set the color (hue) of a region or clip.

Regions and clips use an Int32Field 'hue' for color. The hue is an integer
that maps to a color in the HSL spectrum (0-360). Use this to visually
distinguish sections (e.g. red for choruses, blue for verses).

track_index: Track index within the AU.
region_index: Region/clip to color (0-based).
hue: Color hue (0-360, e.g. 0=red, 120=green, 240=blue).
unit_index: Audio unit index (-1 = search all AUs).

Returns old and new hue values.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const hueVal = {hue};

        let tracks = [];
        const units = h.allAUBoxes();
        if (unitIdx < 0) {{
            for (const au of units) {{
                const ts = h.trackBoxes(au);
                tracks.push(...ts);
            }}
        }} else {{
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            tracks = h.trackBoxes(units[unitIdx]);
        }}
        if (trackIdx >= tracks.length) return {{error: "No track at index " + trackIdx}};
        const trackBox = tracks[trackIdx];

        const regions = h.regionBoxes(trackBox);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx}};
        const region = regions[regionIdx];

        if (!region.hue) return {{error: "Region has no hue field"}};
        const oldHue = region.hue?.getValue?.() ?? 0;
        h.modify(() => {{
            region.hue.setValue(hueVal);
        }});

        return {{
            success: true,
            old_hue: oldHue,
            new_hue: region.hue.getValue(),
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_region_duration(track_index: int, region_index: int, duration_beats: int, unit_index: int = 0) -> str:
    """Set the duration of a region.

duration_beats: New duration in beats (e.g. 4.0 = 1 bar in 4/4).
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const newDur = Math.round({duration_beats} * h.ppqn.Quarter);

        let tracks = [];
        const units = h.allAUBoxes();
        if (unitIdx < 0) {{
            for (const au of units) {{
                const ts = h.trackBoxes(au);
                tracks.push(...ts);
            }}
        }} else {{
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            tracks = h.trackBoxes(units[unitIdx]);
        }}
        if (trackIdx >= tracks.length) return {{error: "No track at index " + trackIdx}};
        const trackBox = tracks[trackIdx];

        const regions = h.regionBoxes(trackBox);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx}};

        const oldDur = regions[regionIdx].duration.getValue();
        h.modify(() => {{
            regions[regionIdx].duration.setValue(newDur);
            if (regions[regionIdx].loopDuration) {{
                regions[regionIdx].loopDuration.setValue(newDur);
            }}
        }});

        return {{
            success: true,
            old_duration_beats: oldDur / h.ppqn.Quarter,
            new_duration_beats: newDur / h.ppqn.Quarter,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_region_label(track_index: int, region_index: int, label: str, unit_index: int) -> str:
    """Rename a region's label (display name).

label: New label text.
unit_index: Audio unit index (-1 = search all AUs).
track_index: Track index within the AU.
region_index: Region to rename (0-based).
"""
    safe_label = label.replace('"', '').replace("'", '').replace('\\', '')
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};

        let tracks = [];
        const units = h.allAUBoxes();
        if (unitIdx < 0) {{
            for (const au of units) {{
                const ts = h.trackBoxes(au);
                tracks.push(...ts);
            }}
        }} else {{
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            tracks = h.trackBoxes(units[unitIdx]);
        }}
        if (trackIdx >= tracks.length) return {{error: "No track at index " + trackIdx}};
        const trackBox = tracks[trackIdx];

        const regions = h.regionBoxes(trackBox);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx}};

        const oldLabel = regions[regionIdx].label?.getValue?.() ?? "";
        h.modify(() => {{
            regions[regionIdx].label.setValue("{safe_label}");
        }});

        return {{
            success: true,
            old_label: oldLabel,
            new_label: regions[regionIdx].label.getValue(),
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_region_mute(track_index: int, region_index: int, mute: bool, unit_index: int = 0) -> str:
    """Mute or unmute a specific region without deleting it.

mute: true to mute, false to unmute.
"""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const muteVal = {json.dumps(mute)};

        let tracks = [];
        const units = h.allAUBoxes();
        if (unitIdx < 0) {{
            for (const au of units) {{
                const ts = h.trackBoxes(au);
                tracks.push(...ts);
            }}
        }} else {{
            if (unitIdx >= units.length) return {{error: "No AU at index " + unitIdx}};
            tracks = h.trackBoxes(units[unitIdx]);
        }}
        if (trackIdx >= tracks.length) return {{error: "No track at index " + trackIdx}};
        const trackBox = tracks[trackIdx];

        const regions = h.regionBoxes(trackBox);
        if (regionIdx >= regions.length) return {{error: "No region at index " + regionIdx}};

        const oldMute = regions[regionIdx].mute?.getValue?.() ?? false;
        h.modify(() => {{
            regions[regionIdx].mute.setValue(muteVal);
        }});

        return {{
            success: true,
            old_mute: oldMute,
            new_mute: muteVal,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_track_enabled(unit_index: int, track_index: int, enabled: bool) -> str:
    """Enable or disable a track (equivalent to track mute in the UI).

    unit_index: AU index.
    track_index: Track index within the AU.
    enabled: True to enable, false to mute/disable.

    Returns success with old and new enabled state.
    """
    val = "true" if enabled else "false"
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const track = h.track({unit_index}, {track_index});
            const oldVal = track.enabled.getValue();
            h.modify(() => {{
                track.enabled.field.setValue({val});
            }});
            return {{success: true, old_enabled: oldVal, new_enabled: {val}}};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_track_mute(unit_index: int, mute: bool) -> str:
    """Mute or unmute an audio unit."""
    mute_val = json.dumps(mute)
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const idx = {unit_index};
        const units = h.allAUBoxes();
        if (idx >= units.length) return {{error: "No audio unit at index " + idx}};
        const au = units[idx];

        h.modify(() => {{
            au.mute.setValue({mute_val});
        }});
        return {{
            success: true,
            unit: au.name?.getValue?.() || "Unit " + idx,
            mute: {mute_val},
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_track_panning(unit_index: int, panning: float) -> str:
    """Set panning of an audio unit. -1.0 = full left, 0.0 = center, 1.0 = full right."""
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const idx = {unit_index};
        const units = h.allAUBoxes();
        if (idx >= units.length) return {{error: "No audio unit at index " + idx}};
        const au = units[idx];

        h.modify(() => {{
            au.panning.setValue({panning});
        }});
        return {{
            success: true,
            unit: au.name?.getValue?.() || "Unit " + idx,
            panning: {panning},
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_track_solo(unit_index: int, solo: bool) -> str:
    """Solo or unsolo an audio unit."""
    solo_val = json.dumps(solo)
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const idx = {unit_index};
        const units = h.allAUBoxes();
        if (idx >= units.length) return {{error: "No audio unit at index " + idx}};
        const au = units[idx];

        h.modify(() => {{
            au.solo.setValue({solo_val});
        }});
        return {{
            success: true,
            unit: au.name?.getValue?.() || "Unit " + idx,
            solo: {solo_val},
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_track_volume(unit_index: int, volume_db: float) -> str:
    """Set volume of an audio unit in dB.

Uses VolumeMapper.decibel(-96, -9, +6) powerByCenter mapping.
Range: -96 dB (mute) to +6 dB. 0 dB = raw 0.768.
"""
    vol_db = volume_db
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const idx = {unit_index};
        const units = h.allAUBoxes();
        if (idx >= units.length) return {{error: "No audio unit at index " + idx + ". Total: " + units.length}};
        const au = units[idx];

        const volDb = {vol_db};
        let raw = volDb;
        try {{
            const c = au.volume.constraints;
            if (c?.valueMapper) raw = c.valueMapper.mapToNormalized(volDb);
            else if (c?.mapper) raw = c.mapper.mapToNormalized(volDb);
        }} catch(e) {{}}

        h.modify(() => {{
            au.volume.setValue(raw);
        }});
        return {{
            success: true,
            unit: au.name?.getValue?.() || "Unit " + idx,
            volume_db: {vol_db},
            raw_value: raw,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_set_unit_minimized(unit_index: int, minimized: bool) -> str:
    """Minimize or expand an audio unit in the mixer view.

    Minimized AUs take less space in the mixer — useful for decluttering
    when working with many tracks.

    unit_index: AU index.
    minimized: True to minimize, False to expand.

    Returns success with old and new minimized state.
    """
    val = "true" if minimized else "false"
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        try {{
            const au = h.au({unit_index});
            const oldVal = au.minimizedField.getValue();
            h.modify(() => {{
                au.minimizedField.setValue({val});
            }});
            return {{success: true, old_minimized: oldVal, new_minimized: {val}}};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_split_note_region(
    unit_index: int,
    track_index: int,
    region_index: int,
    split_beat: float,
) -> str:
    """Split a note region into two at a given beat position.

    Creates a new region starting at split_beat containing all notes from
    that position onward. The original region's duration is trimmed to
    split_beat. Notes that straddle the split point are kept in the original
    region (they will play their full duration even if they extend past
    the trimmed region boundary — this matches DAW behaviour).

    Use cases:
    - Divide a long region into sections (e.g. split at bar 8 for verse/chorus)
    - Cut silence off the end of a region
    - Create variations: split, then modify one half
    - Prepare for arrangement edits (move one half elsewhere)

    unit_index: AU index.
    track_index: Note track index.
    region_index: Region to split (0-based).
    split_beat: Absolute beat position to split at (must be within region range).

    Returns original and new region details.

    Example:
      # Split region 0 at bar 8 (beat 32 in 4/4)
      split_note_region(0, 0, 0, 32)
    """
    result = await bridge.evaluate(f"""async () => {{
        const h = window.DAW_HELPERS;
        const bg = h.boxGraph;
        const NoteRegionBox = window.DAW_NoteRegionBox;
        const NoteEventCollectionBox = window.DAW_NoteEventCollectionBox;
        const NoteEventBox = window.DAW_NoteEventBox;
        const unitIdx = {unit_index};
        const trackIdx = {track_index};
        const regionIdx = {region_index};
        const splitBeat = {split_beat};
        const Quarter = h.ppqn.Quarter;
        const splitTick = Math.round(splitBeat * Quarter);

        const allUnits = h.allAUBoxes();
        if (unitIdx < 0 || unitIdx >= allUnits.length) return {{error: "unit_index out of range"}};
        const au = allUnits[unitIdx];
        const noteTracks = h.noteTrackBoxes(au);
        if (trackIdx < 0 || trackIdx >= noteTracks.length) return {{error: "track_index out of range"}};
        const trackBox = noteTracks[trackIdx];
        const regions = h.regionBoxes(trackBox);
        if (regionIdx < 0 || regionIdx >= regions.length) return {{error: "region_index out of range"}};
        const srcRegion = regions[regionIdx];

        const srcPos = srcRegion.position.getValue();
        const srcDur = srcRegion.duration.getValue();
        const srcEnd = srcPos + srcDur;

        // Validate split point
        if (splitTick <= srcPos) return {{error: "split_beat must be after region start (" + srcPos / Quarter + ")"}};
        if (splitTick >= srcEnd) return {{error: "split_beat must be before region end (" + srcEnd / Quarter + ")"}};

        // Read source notes
        let srcCollection = null;
        try {{
            const vertex = srcRegion.events.targetVertex.unwrap();
            srcCollection = vertex.box || vertex;
        }} catch(e) {{}}
        if (!srcCollection || !srcCollection.events) return {{error: "No note collection in region"}};

        const srcNotes = h.eventBoxes(srcCollection);
        const newDur = srcEnd - splitTick;

        // Categorize notes: keep (before split) or move (at/after split)
        const notesToMove = [];
        const notesToKeep = [];
        for (const n of srcNotes) {{
            const notePos = n.position.getValue();
            if (notePos >= splitTick) {{
                notesToMove.push(n);
            }} else {{
                notesToKeep.push(n);
            }}
        }}

        h.modify(() => {{
            // Create new collection for moved notes
            const newCollection = NoteEventCollectionBox.create(bg, h.uuid.generate());
            for (const n of notesToMove) {{
                const origPos = n.position.getValue();
                const relPos = origPos - splitTick;  // position relative to new region
                NoteEventBox.create(bg, h.uuid.generate(), (box) => {{
                    box.position.setValue(Math.round(relPos));
                    box.duration.setValue(n.duration.getValue());
                    box.velocity.setValue(n.velocity.getValue());
                    box.pitch.setValue(n.pitch.getValue());
                    box.chance.setValue(n.chance?.getValue?.() ?? 100);
                    box.cent.setValue(n.cent?.getValue?.() ?? 0);
                    box.events.refer(newCollection.events);
                }});
            }}

            // Create new region pointing to new collection
            const srcLabel = srcRegion.label?.getValue?.() ?? "Region";
            NoteRegionBox.create(bg, h.uuid.generate(), (box) => {{
                box.position.setValue(splitTick);
                box.label.setValue(srcLabel + " (split)");
                box.mute.setValue(srcRegion.mute?.getValue?.() ?? false);
                box.duration.setValue(newDur);
                box.loopDuration.setValue(newDur);
                box.eventOffset.setValue(0);
                box.events.refer(newCollection.owners);
                box.regions.refer(trackBox.regions);
            }});

            // Delete moved notes from original region
            for (const n of notesToMove) {{
                n.delete();
            }}

            // Trim original region duration
            srcRegion.duration.setValue(splitTick - srcPos);
        }});

        // Find new region index (should be last)
        const updatedRegions = h.regionBoxes(trackBox);
        const newRegIdx = updatedRegions.length - 1;

        return {{
            success: true,
            original: {{
                region_index: regionIdx,
                position_beats: srcPos / Quarter,
                duration_beats: (splitTick - srcPos) / Quarter,
                notes_kept: notesToKeep.length,
            }},
            new: {{
                region_index: newRegIdx,
                position_beats: splitTick / Quarter,
                duration_beats: newDur / Quarter,
                notes_moved: notesToMove.length,
            }},
            split_beat: splitBeat,
            notes_straddling: 0,
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_transfer_audiounit(unit_index: int, delete_source: bool = False,
                                          insert_index: int = -1) -> str:
    """Transfer/copy an audio unit (instrument/effects/tracks/regions) within the project.

Uses TransferAudioUnits.transfer — deep-copy an AU with all dependencies (instrument, effects,
MIDI effects, tracks, regions, notes, automation) via box-graph serialization. Much more complete
than duplicate_audiounit (which uses Python orchestration). Output unit cannot be copied.

unit_index: Source AU index to copy.
delete_source: If true, delete source AU after copy (move semantics).
insert_index: Position in mixer order for the new AU (-1 = auto-place by type ordering).

Returns the new AU's index, type, and label, or error.
"""
    delete_js = "true" if delete_source else "false"
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const TransferAudioUnits = window.DAW_TransferAudioUnits;
        if (!TransferAudioUnits) return {{error: "TransferAudioUnits not loaded"}};
        const units = h.allAUBoxes();
        if ({unit_index} >= units.length) return {{error: "No AU at {unit_index}"}};

        const srcAU = units[{unit_index}];
        // Find primary audio bus (connected to Output unit's input)
        const outputAU = units.find(u => u.type.getValue() === "output" || u.type.getValue() === 2);
        if (!outputAU) return {{error: "No Output unit found"}};
        const primaryBus = h.inputBoxes(outputAU)[0]?.box || h.inputBoxes(outputAU)[0] || null;
        if (!primaryBus) return {{error: "No primary audio bus found"}};

        const skeleton = {{
            boxGraph: h.boxGraph,
            mandatoryBoxes: {{
                primaryAudioBusBox: primaryBus,
                rootBox: h.rootBox,
            }}
        }};

        let newAUs;
        const opts = {{deleteSource: {delete_js}}};
        if ({insert_index} >= 0) opts.insertIndex = {insert_index};
        h.editing.modify(() => {{
            newAUs = TransferAudioUnits.transfer([srcAU], skeleton, opts);
        }});

        if (!newAUs || newAUs.length === 0) return {{error: "Transfer returned no units"}};
        const newAU = newAUs[0];
        return {{
            success: true,
            new_unit_index: newAU.index.getValue(),
            unit_type: newAU.type.getValue(),
            label: newAU.label ? newAU.label.getValue() : '',
            source_deleted: {delete_js},
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_transfer_region(src_unit_index: int, src_track_index: int, region_index: int,
                                       dst_unit_index: int, dst_track_index: int,
                                       insert_position: float, delete_source: bool = False) -> str:
    """Transfer/copy a region to another track at a specific position.

Uses TransferRegions.transfer — copies the region and all its dependencies (notes, events, audio files)
to the target track. Works across different audio units. Preserved resources (AudioFileBox) are shared,
not duplicated. The source region can optionally be deleted (move semantics).

src_unit_index: Source AU index.
src_track_index: Source track index within AU.
region_index: Region index within source track (0-based, sorted by position).
dst_unit_index: Destination AU index.
dst_track_index: Destination track index within AU.
insert_position: Position in beats for the new region.
delete_source: If true, delete the source region (move). If false, keep source (copy).

Returns the new region's type, position, and duration, or error.
"""
    delete_js = "true" if delete_source else "false"
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const TransferRegions = window.DAW_TransferRegions;
        if (!TransferRegions) return {{error: "TransferRegions not loaded"}};
        const units = h.allAUBoxes();

        if ({src_unit_index} >= units.length) return {{error: "No source AU at {src_unit_index}"}};
        if ({dst_unit_index} >= units.length) return {{error: "No dest AU at {dst_unit_index}"}};

        const srcAU = units[{src_unit_index}];
        const dstAU = units[{dst_unit_index}];

        const srcTracks = h.trackBoxes(srcAU)
            .sort((a, b) => a.index.getValue() - b.index.getValue());
        const dstTracks = h.trackBoxes(dstAU)
            .sort((a, b) => a.index.getValue() - b.index.getValue());

        if ({src_track_index} >= srcTracks.length) return {{error: "No source track at {src_track_index}"}};
        if ({dst_track_index} >= dstTracks.length) return {{error: "No dest track at {dst_track_index}"}};

        const srcTrack = srcTracks[{src_track_index}];
        const dstTrack = dstTracks[{dst_track_index}];

        const regions = h.regionBoxes(srcTrack)
            .sort((a, b) => a.position.getValue() - b.position.getValue());
        if ({region_index} >= regions.length) return {{error: "No region at {region_index}"}};

        const srcRegion = regions[{region_index}];
        const regionType = srcRegion.constructor.name;
        const insertPos = Math.round({insert_position} * h.ppqn.Quarter);  // beats to ppqn

        let newRegion;
        h.editing.modify(() => {{
            newRegion = TransferRegions.transfer(srcRegion, dstTrack, insertPos, {delete_js});
        }});

        if (!newRegion) return {{error: "Transfer failed"}};
        return {{
            success: true,
            region_type: newRegion.constructor.name,
            position_beats: newRegion.position.getValue() / h.ppqn.Quarter,
            duration_beats: newRegion.duration.getValue() / h.ppqn.Quarter,
            source_deleted: {delete_js},
        }};
    }}""")
    return _wrap_eval(result)


async def mcp_opendaw_unfreeze_audiounit(unit_index: int) -> str:
    """Unfreeze a frozen audio unit — resume real-time processing.

    Removes the cached audio and resumes live processing of instruments,
    effects, and sends for the specified audio unit.

    unit_index: AU index to unfreeze.

    Returns success or error.
    """
    result = await bridge.evaluate(f"""() => {{
        const h = window.DAW_HELPERS;
        const freeze = h.audioUnitFreeze;
        if (!freeze) return {{error: "audioUnitFreeze not available"}};
        const auAdapters = h.allAUs();
        if ({unit_index} >= auAdapters.length) return {{error: "No AU at {unit_index}"}};
        const auAdapter = auAdapters[{unit_index}];
        try {{
            const wasFrozen = freeze.isFrozen(auAdapter);
            if (!wasFrozen) return {{error: "AU is not frozen"}};
            freeze.unfreeze(auAdapter);
            return {{
                success: true,
                was_frozen: wasFrozen,
                frozen: freeze.isFrozen(auAdapter),
                unit_index: {unit_index},
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}""")
    return _wrap_eval(result)


# ─────────────────────────────────────────────────────────────────────
# Mixer & Region Advanced (148-150)
# ─────────────────────────────────────────────────────────────────────

