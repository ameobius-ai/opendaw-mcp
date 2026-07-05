// @spielwerk chorder 1 1
// @label Chorder
// @param chord 0 0 12 int
// @param voicing 0 0 4 int
// @param inversion 0 0 3 int
// @param octave 0 -3 3 int
// @param spread 0 0 24 int
// @param strum 0 0 64 int
// @param velScale 0.85 0.1 1 linear

class Processor {
    chord = 0
    voicing = 0
    inversion = 0
    octave = 0
    spread = 0
    strum = 0
    velScale = 0.85

    // chord shapes: root, 3rd, 5th, 7th, 9th
    shapes = [
        [0, 4, 7],          // 0: major
        [0, 3, 7],          // 1: minor
        [0, 4, 7, 11],      // 2: maj7
        [0, 3, 7, 10],      // 3: min7
        [0, 4, 7, 10],      // 4: dom7
        [0, 3, 6],          // 5: dim
        [0, 3, 6, 9],       // 6: dim7
        [0, 3, 6, 10],      // 7: half-dim (m7b5)
        [0, 4, 8],          // 8: aug
        [0, 2, 7],          // 9: sus2
        [0, 5, 7],          // 10: sus4
        [0, 4, 7, 14],      // 11: add9
        [0, 3, 7, 9],       // 12: m6
    ]

    paramChanged(label, value) {
        this[label] = value
    }

    voiceChord(shape) {
        const inv = Math.round(this.inversion)
        let notes = shape.map(i => i)

        // rotate for inversion
        for (let n = 0; n < inv && notes.length > 1; n++) {
            const bottom = notes.shift()
            notes.push(bottom + 12)
        }

        // voicing mode
        const mode = Math.round(this.voicing)
        if (mode === 1 && notes.length >= 3) {
            // drop-2: drop 2nd-from-top voice down an octave
            const idx = notes.length - 2
            notes[idx] -= 12
        } else if (mode === 2 && notes.length >= 4) {
            // drop-3: drop 3rd-from-top voice down an octave
            const idx = notes.length - 3
            notes[idx] -= 12
        } else if (mode === 3) {
            // open: spread voices across octaves
            notes = notes.map((n, i) => n + Math.floor(i / 2) * 12)
        } else if (mode === 4) {
            // spread: interleave octaves
            notes = notes.map((n, i) => i % 2 === 1 ? n + 12 : n)
        }

        // spread param: add extra octave spacing
        const sp = Math.round(this.spread)
        if (sp > 0) {
            notes = notes.map((n, i) => n + i * sp)
        }

        return notes
    }

    *process(block, events) {
        const shape = this.shapes[Math.round(this.chord)] || this.shapes[0]
        const octShift = Math.round(this.octave) * 12
        const strumAmt = Math.round(this.strum)
        const voices = this.voiceChord(shape)

        for (const ev of events) {
            if (ev.gate) {
                for (let i = 0; i < voices.length; i++) {
                    const p = ev.pitch + octShift + voices[i]
                    if (p >= 0 && p <= 127) {
                        yield {
                            position: ev.position + i * strumAmt,
                            duration: ev.duration,
                            pitch: p,
                            velocity: ev.velocity * this.velScale * (1 - i * 0.04),
                            cent: ev.cent || 0
                        }
                    }
                }
            }
        }
    }

    reset() {}
}
