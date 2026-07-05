// @werkstatt multiband_saturator 1 1
// @label Multiband Saturator
// @param crossover1 200 80 800 exp
// @param crossover2 2500 1000 8000 exp
// @param low_drive 0.4 0 1 linear
// @param mid_drive 0.3 0 1 linear
// @param high_drive 0.2 0 1 linear
// @param low_char 0 0 2 int
// @param mid_char 1 0 2 int
// @param high_char 2 0 2 int
// @param output 0 -24 6 linear
// @param mix 1 0 1 linear

class Processor {
    crossover1 = 200
    crossover2 = 2500
    low_drive = 0.4
    mid_drive = 0.3
    high_drive = 0.2
    low_char = 0
    mid_char = 1
    high_char = 2
    output = 0
    mix = 1

    // LR4 crossover state: 4 cascaded one-pole LP for each band
    // each band needs LP and HP state for L and R
    // low band: LP from input
    // high band: HP from input (input - LP)
    // mid band: LP(high) - LP(low) ... actually use cascaded approach

    // We use 3 cascaded LP filters (2nd order each, 4th order total = LR4)
    // lpA: lowpass at crossover1 → low band
    // lpB: lowpass at crossover2 on (input - low) → mid band
    // high = input - low - mid

    // state arrays: [stage][channel] = {z1, z2}
    lpA = [{z1:0,z2:0,z3:0,z4:0}, {z1:0,z2:0,z3:0,z4:0}]  // crossover1 LP
    lpB = [{z1:0,z2:0,z3:0,z4:0}, {z1:0,z2:0,z3:0,z4:0}]  // crossover2 LP
    lpBh = [{z1:0,z2:0,z3:0,z4:0}, {z1:0,z2:0,z3:0,z4:0}] // crossover2 LP on high-mid

    cached = false
    g1 = 0  // crossover1 coefficient
    g2 = 0  // crossover2 coefficient

    paramChanged(label, value) {
        this[label] = value
        this.cached = false
    }

    _updateCoeffs(sr) {
        // one-pole LP coefficient for LR4 (4 cascaded)
        // use bilinear transform for 1st-order LP
        const wc1 = 2 * Math.PI * this.crossover1 / sr
        const wc2 = 2 * Math.PI * this.crossover2 / sr
        // tanh prewarping
        this.g1 = Math.tan(wc1 / 2) / (1 + Math.tan(wc1 / 2))
        this.g2 = Math.tan(wc2 / 2) / (1 + Math.tan(wc2 / 2))
        this.cached = true
    }

    _lp4(state, x, g) {
        // 4 cascaded one-pole lowpass
        let s = x
        s = g * s + (1 - g) * state.z1; state.z1 = s
        s = g * s + (1 - g) * state.z2; state.z2 = s
        s = g * s + (1 - g) * state.z3; state.z3 = s
        s = g * s + (1 - g) * state.z4; state.z4 = s
        return s
    }

    _saturate(sample, drive, character) {
        // drive: 0..1 → 1..10x gain
        const d = 1 + drive * 9
        const x = sample * d

        if (character === 0) {
            // tape: soft tanh, warm even-ish harmonics
            return Math.tanh(x) / Math.tanh(d)
        } else if (character === 1) {
            // tube: asymmetric soft clip, even harmonics
            // positive half softer than negative
            const pos = x > 0 ? 1 - 1 / (1 + x * 2) : -1 + 1 / (1 - x * 1.5)
            return pos * 0.8
        } else {
            // transistor: hard-ish clip, odd harmonics
            // cubic + harder shoulder
            const c = x - x * x * x * 0.25
            return Math.tanh(c * 1.5) / Math.tanh(d * 1.5)
        }
    }

    processAudio(inputs, outputs, parameters) {
        const sr = this.sampleRate || 44100
        if (!this.cached) this._updateCoeffs(sr)

        const input = inputs[0]
        const output = outputs[0]
        const len = output[0].length
        const inL = input[0] || new Float32Array(len)
        const inR = input[1] || inL
        const outL = output[0]
        const outR = output[1] || output[0]

        const outGain = Math.pow(10, this.output / 20)
        const wet = this.mix
        const dry = 1 - this.mix

        for (let i = 0; i < len; i++) {
            const sL = inL[i]
            const sR = inR[i]

            // split into 3 bands
            // low = LP4(input, crossover1)
            // mid = LP4(input - low, crossover2) — LP of the highpassed remainder
            // high = (input - low) - mid

            const lowL = this._lp4(this.lpA[0], sL, this.g1)
            const lowR = this._lp4(this.lpA[1], sR, this.g1)

            const hpL1 = sL - lowL
            const hpR1 = sR - lowR

            const midL = this._lp4(this.lpB[0], hpL1, this.g2)
            const midR = this._lp4(this.lpB[1], hpR1, this.g2)

            const highL = hpL1 - midL
            const highR = hpR1 - midR

            // saturate each band
            const satLowL = this._saturate(lowL, this.low_drive, Math.round(this.low_char))
            const satLowR = this._saturate(lowR, this.low_drive, Math.round(this.low_char))
            const satMidL = this._saturate(midL, this.mid_drive, Math.round(this.mid_char))
            const satMidR = this._saturate(midR, this.mid_drive, Math.round(this.mid_char))
            const satHighL = this._saturate(highL, this.high_drive, Math.round(this.high_char))
            const satHighR = this._saturate(highR, this.high_drive, Math.round(this.high_char))

            // sum bands back
            const wetL = satLowL + satMidL + satHighL
            const wetR = satLowR + satMidR + satHighR

            outL[i] = (sL * dry + wetL * wet) * outGain
            outR[i] = (sR * dry + wetR * wet) * outGain
        }
    }
}
