// @spielwerk harmonizer 1 1
// @label Harmonizer
// @param interval1 7 -24 24 linear
// @param interval2 12 -24 24 linear
// @param interval3 0 -24 24 linear
// @param vel1 0.8 0 1 linear
// @param vel2 0.7 0 1 linear
// @param vel3 0.6 0 1 linear
// @param mode 0 0 1 linear
// @param key_root 0 0 11 linear
// @param scale 0 0 13 linear

class Processor {
    interval1 = 7
    interval2 = 12
    interval3 = 0
    vel1 = 0.8
    vel2 = 0.7
    vel3 = 0.6
    mode = 0
    key_root = 0
    scale = 0

    SCALES = [
        [0, 2, 4, 5, 7, 9, 11],       // 0: major
        [0, 2, 3, 5, 7, 8, 10],       // 1: minor
        [0, 2, 3, 5, 7, 9, 11],       // 2: dorian
        [0, 1, 3, 5, 7, 8, 10],       // 3: phrygian
        [0, 2, 4, 6, 7, 9, 11],       // 4: lydian
        [0, 2, 4, 5, 7, 8, 10],       // 5: mixolydian
        [0, 1, 3, 5, 6, 8, 10],       // 6: locrian
        [0, 2, 3, 5, 7, 10],          // 7: minor pentatonic
        [0, 2, 4, 7, 9],              // 8: major pentatonic
        [0, 2, 3, 5, 6, 8, 9, 11],    // 9: harmonic minor
        [0, 2, 3, 5, 7, 9, 11],       // 10: melodic minor
        [0, 2, 3, 5, 7, 8, 11],       // 11: hungarian minor
        [0, 2, 4, 5, 7, 8, 11],       // 12: double harmonic
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11], // 13: chromatic
    ]

    paramChanged(name, value) {
        if (name === "interval1") this.interval1 = Math.round(value)
        if (name === "interval2") this.interval2 = Math.round(value)
        if (name === "interval3") this.interval3 = Math.round(value)
        if (name === "vel1") this.vel1 = value
        if (name === "vel2") this.vel2 = value
        if (name === "vel3") this.vel3 = value
        if (name === "mode") this.mode = Math.round(value)
        if (name === "key_root") this.key_root = Math.round(value)
        if (name === "scale") this.scale = Math.round(value)
    }

    // diatonic transpose: move N scale degrees up/down
    _diatonicShift(pitch, degrees) {
        const intervals = this.SCALES[this.scale]
        const root = this.key_root
        const len = intervals.length

        let rel = pitch - root
        let octave = Math.floor(rel / 12)
        let pc = ((rel % 12) + 12) % 12

        // find current position in scale
        let idx = -1
        for (let i = 0; i < len; i++) {
            if (intervals[i] === pc) { idx = i; break }
        }
        if (idx === -1) {
            // not in scale — snap to nearest then shift
            let bestDist = 12
            for (let i = 0; i < len; i++) {
                const d = Math.abs(intervals[i] - pc)
                if (d < bestDist) { bestDist = d; idx = i }
            }
        }

        // shift by degrees
        let newIdx = idx + degrees
        let newOctave = octave + Math.floor(newIdx / len)
        let wrappedIdx = ((newIdx % len) + len) % len
        return root + newOctave * 12 + intervals[wrappedIdx]
    }

    _shiftPitch(pitch, interval) {
        if (interval === 0) return pitch
        if (this.mode === 1) {
            // diatonic: interval = scale degrees
            // convert semitone interval to approximate scale degree count
            const degreeShift = Math.round(interval / 2)
            return this._diatonicShift(pitch, degreeShift)
        }
        return pitch + interval
    }

    _clamp(pitch) {
        return Math.max(0, Math.min(127, pitch))
    }

    *process(block, events) {
        for (const ev of events) {
            // always pass original
            yield ev

            // voice 1
            if (this.interval1 !== 0 && this.vel1 > 0) {
                const p = this._clamp(this._shiftPitch(ev.pitch, this.interval1))
                yield {
                    position: ev.position,
                    duration: ev.duration,
                    pitch: p,
                    velocity: Math.max(0, Math.min(1, ev.velocity * this.vel1)),
                    cent: ev.cent || 0,
                    gate: ev.gate,
                    id: ev.id + "_h1"
                }
            }

            // voice 2
            if (this.interval2 !== 0 && this.vel2 > 0) {
                const p = this._clamp(this._shiftPitch(ev.pitch, this.interval2))
                yield {
                    position: ev.position,
                    duration: ev.duration,
                    pitch: p,
                    velocity: Math.max(0, Math.min(1, ev.velocity * this.vel2)),
                    cent: ev.cent || 0,
                    gate: ev.gate,
                    id: ev.id + "_h2"
                }
            }

            // voice 3
            if (this.interval3 !== 0 && this.vel3 > 0) {
                const p = this._clamp(this._shiftPitch(ev.pitch, this.interval3))
                yield {
                    position: ev.position,
                    duration: ev.duration,
                    pitch: p,
                    velocity: Math.max(0, Math.min(1, ev.velocity * this.vel3)),
                    cent: ev.cent || 0,
                    gate: ev.gate,
                    id: ev.id + "_h3"
                }
            }
        }
    }

    reset() {}
}
