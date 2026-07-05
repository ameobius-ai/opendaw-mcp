// @werkstatt modal_resonator 1 1
// @label Modal Resonator
// @param material 1 0 4 int
// @param fundamental 220 40 2000 exp
// @param decay 0.5 0.05 2 linear
// @param brightness 0.6 0 1 linear
// @param inharmonicity 0 0 1 linear
// @param mix 0.8 0 1 linear
// @param output 0 -24 6 linear

class Processor {
    material = 1
    fundamental = 220
    decay = 0.5
    brightness = 0.6
    inharmonicity = 0
    mix = 0.8
    output = 0

    // modal frequency ratios per material
    materials = [
        [1.0, 3.0, 5.41, 8.93],              // 0: marimba bar (Deutch)
        [0.5, 1.0, 1.2, 1.5, 2.0, 2.5, 2.6, 3.0], // 1: bell (inharmonic)
        [1.0, 1.46, 1.85, 2.31, 2.93],       // 2: circular plate
        [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0], // 3: string (harmonic)
        [1.0, 2.76, 5.05, 7.6],              // 4: wine glass
    ]

    // biquad state per mode per channel
    modes = []  // array of {freq, q, amp, x1, x2, y1, y2, x1r, x2r, y1r, y2r}
    cached = false

    paramChanged(label, value) {
        this[label] = value
        this.cached = false
    }

    _buildModes(sr) {
        const matIdx = Math.round(this.material)
        const ratios = this.materials[matIdx] || this.materials[1]
        const modes = []
        const inhar = this.inharmonicity
        const decayS = this.decay
        const bright = this.brightness

        for (let i = 0; i < ratios.length; i++) {
            const ratio = ratios[i]
            // inharmonicity stretches upper modes (B = inharmonicity coefficient)
            const stretch = 1 + inhar * i * i * 0.01
            const freq = this.fundamental * ratio * stretch
            if (freq > sr * 0.45) continue

            // decay: lower modes ring longer, higher modes decay faster
            // decay param controls base T60, brightness scales high-mode decay
            const baseT60 = decayS * 3.0
            const modeT60 = baseT60 / (1 + i * (1.5 - bright))
            const q = Math.max(1, modeT60 * freq * 1.5)

            // amplitude: brightness controls high-mode rolloff
            const amp = Math.pow(bright, i) * (1 - i * 0.05)

            modes.push({
                freq, q, amp,
                x1: 0, x2: 0, y1: 0, y2: 0,
                x1r: 0, x2r: 0, y1r: 0, y2r: 0,
            })
        }
        return modes
    }

    _biquadBP(m, sample, sr) {
        // RBJ cookbook bandpass (constant 0 dB peak gain)
        const w0 = 2 * Math.PI * m.freq / sr
        const cosW = Math.cos(w0)
        const sinW = Math.sin(w0)
        const alpha = sinW / (2 * m.q)

        const b0 = alpha
        const b1 = 0
        const b2 = -alpha
        const a0 = 1 + alpha
        const a1 = -2 * cosW
        const a2 = 1 - alpha

        // normalize
        const nb0 = b0 / a0
        const nb2 = b2 / a0
        const na1 = a1 / a0
        const na2 = a2 / a0

        // direct form I
        const x0 = sample
        const y0 = nb0 * x0 + nb2 * m.x2 - na1 * m.y1 - na2 * m.y2
        m.x2 = m.x1
        m.x1 = x0
        m.y2 = m.y1
        m.y1 = y0
        return y0
    }

    _biquadBPR(m, sample, sr) {
        const w0 = 2 * Math.PI * m.freq / sr
        const cosW = Math.cos(w0)
        const sinW = Math.sin(w0)
        const alpha = sinW / (2 * m.q)

        const b0 = alpha
        const b2 = -alpha
        const a0 = 1 + alpha
        const a1 = -2 * cosW
        const a2 = 1 - alpha

        const nb0 = b0 / a0
        const nb2 = b2 / a0
        const na1 = a1 / a0
        const na2 = a2 / a0

        const x0 = sample
        const y0 = nb0 * x0 + nb2 * m.x2r - na1 * m.y1r - na2 * m.y2r
        m.x2r = m.x1r
        m.x1r = x0
        m.y2r = m.y1r
        m.y1r = y0
        return y0
    }

    processAudio(inputs, outputs, parameters) {
        const sr = this.sampleRate || 44100
        if (!this.cached) {
            this.modes = this._buildModes(sr)
            this.cached = true
        }
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

        for (let i = 0; i < len; i++) {
            const sL = inL[i]
            const sR = inR[i]
            let resL = 0
            let resR = 0

            for (let m = 0; m < this.modes.length; m++) {
                const mode = this.modes[m]
                resL += this._biquadBP(mode, sL, sr) * mode.amp
                resR += this._biquadBPR(mode, sR, sr) * mode.amp
            }

            outL[i] = (sL * dry + resL * wet) * outGain
            outR[i] = (sR * dry + resR * wet) * outGain
        }
    }
}
