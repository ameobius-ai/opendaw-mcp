// @werkstatt karplus_strong 1 1
// @label Karplus-Strong String
// @param frequency 220 20 2000 exp
// @param decay 0.5 0 1 linear
// @param brightness 0.5 0 1 linear
// @param pluck_damping 0 0 1 linear
// @param stretch 1 0.5 2 linear
// @param mix 0.8 0 1 linear
// @param output 0 -24 6 linear dB

class Processor {
    frequency = 220
    decay = 0.5
    brightness = 0.5
    pluck_damping = 0
    stretch = 1
    mix = 0.8
    output = 0

    // delay line state per channel
    delayL = null
    delayR = null
    idxL = 0
    idxR = 0
    lastFiltL = 0
    lastFiltR = 0
    delayLen = 0
    cached = false

    paramChanged(label, value) {
        this[label] = value
        this.cached = false
    }

    _initDelay(sr) {
        const f = Math.max(20, this.frequency)
        // delay length = sampleRate / freq * stretch
        // stretch > 1 = longer (lower/inharmonic), stretch < 1 = shorter (sharper)
        this.delayLen = Math.max(2, Math.floor(sr / f * this.stretch))
        this.delayL = new Float32Array(this.delayLen)
        this.delayR = new Float32Array(this.delayLen)
        this.idxL = 0
        this.idxR = 0
        this.lastFiltL = 0
        this.lastFiltR = 0
        this.cached = true
    }

    processAudio(inputs, outputs, parameters) {
        const sr = this.sampleRate || 44100
        if (!this.cached) this._initDelay(sr)

        const input = inputs[0]
        const output = outputs[0]
        const len = output[0].length
        const inL = input[0] || new Float32Array(len)
        const inR = input[1] || inL
        const outL = output[0]
        const outR = output[1] || output[0]

        const wet = this.mix
        const dry = 1 - this.mix
        const outGain = Math.pow(10, this.output / 20)

        // decay → feedback gain (0.995 stability clamp prevents infinite ring)
        const decayGain = this.decay * 0.995
        // pluck damping reduces excitation gain (0 = full pluck, 1 = muted/soft)
        const exciteGain = 1 - this.pluck_damping
        // brightness: 1 = no filtering (bright), 0 = max lowpass (dark)
        const bright = this.brightness
        const oneMinusBright = 1 - this.brightness

        const dL = this.delayL
        const dR = this.delayR
        const dLen = this.delayLen

        for (let i = 0; i < len; i++) {
            const sL = inL[i]
            const sR = inR[i]

            // --- Karplus-Strong core (left) ---
            // 1. read current delay line position
            const curL = dL[this.idxL]
            // 2. read next position for averaging lowpass
            const nextL = dL[(this.idxL + 1) % dLen]
            // 3. one-pole lowpass: brightness controls cutoff
            //    filtered = bright * next + (1-bright) * lastFiltered
            const filtL = bright * nextL + oneMinusBright * this.lastFiltL
            // 4. write back: input excitation + filtered feedback
            dL[this.idxL] = sL * exciteGain + filtL * decayGain
            this.lastFiltL = filtL
            // 5. advance index
            this.idxL = (this.idxL + 1) % dLen

            // --- Karplus-Strong core (right) ---
            const curR = dR[this.idxR]
            const nextR = dR[(this.idxR + 1) % dLen]
            const filtR = bright * nextR + oneMinusBright * this.lastFiltR
            dR[this.idxR] = sR * exciteGain + filtR * decayGain
            this.lastFiltR = filtR
            this.idxR = (this.idxR + 1) % dLen

            // wet/dry mix
            outL[i] = (sL * dry + curL * wet) * outGain
            outR[i] = (sR * dry + curR * wet) * outGain
        }
    }
}
