// @spielwerk powerchord 1 1
// @label Power Chord
// @param interval 7 0 24 int
// @param interval2 12 0 24 int
// @param velScale 0.85 0.1 1 linear
// @param detune 3 0 50 int

class Processor {
    heldNotes = new Map()

    process(block, events) {
        const interval = this.interval || 7
        const interval2 = this.interval2 || 12
        const velScale = this.velScale || 0.85
        const detune = (this.detune || 3) / 100
        const out = []

        for (const ev of events) {
            if (ev.gate) {
                this.heldNotes.set(ev.pitch, {id: ev.id, velocity: ev.velocity})

                // root note (pass through)
                out.push({
                    position: ev.position,
                    duration: ev.duration,
                    pitch: ev.pitch,
                    velocity: ev.velocity,
                    cent: ev.cent || 0
                })

                // first interval (e.g. perfect fifth)
                if (interval > 0 && ev.pitch + interval <= 127) {
                    out.push({
                        position: ev.position + 8,
                        duration: ev.duration,
                        pitch: ev.pitch + interval,
                        velocity: ev.velocity * velScale,
                        cent: (ev.cent || 0) + detune
                    })
                }

                // second interval (e.g. octave)
                if (interval2 > 0 && ev.pitch + interval2 <= 127) {
                    out.push({
                        position: ev.position + 16,
                        duration: ev.duration,
                        pitch: ev.pitch + interval2,
                        velocity: ev.velocity * velScale * 0.9,
                        cent: (ev.cent || 0) - detune
                    })
                }
            } else {
                this.heldNotes.delete(ev.pitch)
            }
        }

        return out
    }

    paramChanged(label, value) {
        this[label] = value
    }

    reset() {
        this.heldNotes.clear()
    }
}
