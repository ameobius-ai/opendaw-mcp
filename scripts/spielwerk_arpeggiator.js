// @spielwerk arpeggiator 1 1
// @label Arpeggiator
// @param rate 240 60 1920 int
// @param mode 0 0 3 int
// @param octaves 2 1 4 int
// @param gate 0.8 0.1 1 linear
// @param velDecay 0.7 0.3 1 linear

class Processor {
    heldNotes = []
    stepCounter = 0
    nextStepPos = 0  // ppqn position for next step
    lastFrom = -1

    process(block, events) {
        const rate = this.rate || 240
        const mode = this.mode || 0
        const octaves = this.octaves || 2
        const gateLen = this.gate || 0.8
        const velDecay = this.velDecay || 0.7
        const out = []

        // update held notes
        for (const ev of events) {
            if (ev.gate) {
                if (!this.heldNotes.find(n => n.pitch === ev.pitch)) {
                    this.heldNotes.push({pitch: ev.pitch, velocity: ev.velocity})
                }
            } else {
                this.heldNotes = this.heldNotes.filter(n => n.pitch !== ev.pitch)
            }
        }

        if (this.heldNotes.length === 0) {
            this.stepCounter = 0
            this.nextStepPos = block.to
            return out
        }

        // reset step position on transport jump
        if (this.lastFrom < 0 || block.from < this.lastFrom) {
            this.nextStepPos = block.from
            this.stepCounter = 0
        }
        this.lastFrom = block.from

        // sort held notes by pitch
        const sorted = [...this.heldNotes].sort((a, b) => a.pitch - b.pitch)

        // build arpeggiated sequence across octaves
        const seq = []
        for (let oct = 0; oct < octaves; oct++) {
            for (const n of sorted) {
                const p = n.pitch + oct * 12
                if (p <= 127) {
                    seq.push({pitch: p, velocity: n.velocity})
                }
            }
        }
        if (seq.length === 0) return out

        // apply mode
        let indices = []
        if (mode === 0) {
            for (let i = 0; i < seq.length; i++) indices.push(i)
        } else if (mode === 1) {
            for (let i = seq.length - 1; i >= 0; i--) indices.push(i)
        } else if (mode === 2) {
            for (let i = 0; i < seq.length; i++) indices.push(i)
            for (let i = seq.length - 2; i > 0; i--) indices.push(i)
        } else {
            for (let i = 0; i < seq.length * 2; i++) {
                indices.push(Math.floor(Math.random() * seq.length))
            }
        }

        const dur = Math.max(30, Math.floor(rate * gateLen))

        // generate notes within this block range
        while (this.nextStepPos < block.to) {
            if (this.nextStepPos >= block.from) {
                const idx = indices[this.stepCounter % indices.length]
                const note = seq[idx]
                out.push({
                    position: this.nextStepPos,
                    duration: dur,
                    pitch: note.pitch,
                    velocity: note.velocity * Math.pow(velDecay, this.stepCounter % seq.length),
                    cent: 0
                })
            }
            this.stepCounter++
            this.nextStepPos += rate
        }

        return out
    }

    paramChanged(label, value) {
        this[label] = value
    }

    reset() {
        this.heldNotes = []
        this.stepCounter = 0
        this.nextStepPos = 0
        this.lastFrom = -1
    }
}
