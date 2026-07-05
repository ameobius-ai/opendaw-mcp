// @spielwerk scale_quantizer 1 1
// @label Scale Quantizer
// @param scale 0 0 13 linear
// @param root 0 0 11 linear
// @param direction 0 0 1 linear

class Processor {
    scale = 0
    root = 0
    direction = 0

    // 14 scales: intervals as semitone offsets from root
    SCALES = [
        [0, 2, 4, 5, 7, 9, 11],       // 0: major (ionian)
        [0, 2, 3, 5, 7, 8, 10],       // 1: minor (aeolian)
        [0, 2, 3, 5, 7, 9, 11],       // 2: dorian
        [0, 1, 3, 5, 7, 8, 10],       // 3: phrygian
        [0, 2, 4, 6, 7, 9, 11],       // 4: lydian
        [0, 2, 4, 5, 7, 8, 10],       // 5: mixolydian
        [0, 1, 3, 5, 6, 8, 10],       // 6: locrian
        [0, 2, 3, 5, 7, 10],          // 7: minor pentatonic
        [0, 2, 4, 7, 9],              // 8: major pentatonic
        [0, 2, 3, 5, 6, 8, 9, 11],    // 9: harmonic minor
        [0, 2, 3, 5, 7, 9, 11],       // 10: melodic minor (ascending)
        [0, 2, 3, 5, 7, 8, 11],       // 11: hungarian minor
        [0, 2, 4, 5, 7, 8, 11],       // 12: double harmonic
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11], // 13: chromatic (pass-through)
    ]

    SCALE_NAMES = [
        "major", "minor", "dorian", "phrygian", "lydian",
        "mixolydian", "locrian", "minor_pentatonic", "major_pentatonic",
        "harmonic_minor", "melodic_minor", "hungarian_minor",
        "double_harmonic", "chromatic"
    ]

    paramChanged(name, value) {
        if (name === "scale") this.scale = Math.round(value)
        if (name === "root") this.root = Math.round(value)
        if (name === "direction") this.direction = Math.round(value)
    }

    // snap a MIDI pitch to the nearest pitch in the scale
    _quantize(pitch) {
        if (this.scale === 13) return pitch // chromatic = pass-through

        const intervals = this.SCALES[this.scale]
        const root = this.root

        // pitch relative to root
        let rel = pitch - root
        // normalize to 0-11
        let octave = Math.floor(rel / 12)
        let pc = ((rel % 12) + 12) % 12

        // find nearest scale degree
        let bestDist = 12
        let bestPc = pc
        for (const interval of intervals) {
            // distance in both directions
            const distUp = (interval - pc + 12) % 12
            const distDown = (pc - interval + 12) % 12
            const dist = Math.min(distUp, distDown)
            if (dist < bestDist) {
                bestDist = dist
                bestPc = interval
            }
        }

        // direction: 0 = nearest (default), 1 = always snap up
        if (this.direction === 1) {
            // always snap up: if pitch is below the scale degree, move up
            const distUp = (bestPc - pc + 12) % 12
            const distDown = (pc - bestPc + 12) % 12
            if (distDown < distUp) {
                // snap down was closer but we force up
                bestPc = intervals.find(i => i > pc) ?? intervals[0] + 12
            }
        }

        return root + octave * 12 + bestPc
    }

    *process(block, events) {
        for (const ev of events) {
            const newPitch = this._quantize(ev.pitch)
            yield {
                position: ev.position,
                duration: ev.duration,
                pitch: newPitch,
                velocity: ev.velocity,
                cent: ev.cent || 0,
                gate: ev.gate,
                id: ev.id
            }
        }
    }

    reset() {}
}
