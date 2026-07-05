// @werkstatt waveguide_string 1 1
// @label Waveguide String
// @param frequency 220 20 2000 exp
// @param decay 0.5 0 1 linear
// @param brightness 0.5 0 1 linear
// @param pick_position 0.3 0 0.5 linear
// @param inharmonicity 0 0 1 linear
// @param mix 0.85 0 1 linear
// @param output 0 -24 6 linear dB

class Processor {
    frequency = 220
    decay = 0.5
    brightness = 0.5
    pick_position = 0.3
    inharmonicity = 0
    mix = 0.85
    output = 0

    // bidirectional delay lines
    delayFwdL = null   // left-going wave
    delayBwdL = null   // right-going wave
    delayFwdR = null
    delayBwdR = null
    idxL = 0
    idxR = 0
    // bridge filter state (one-pole lowpass at termination)
    bridgeFiltL = 0
    bridgeFiltR = 0
    // nut filter state (allpass for inharmonicity)
    nutStateL = 0
    nutStateR = 0
    delayLen = 0
    cached = false

    paramChanged(label, value) {
        this[label] = value
        this.cached = false
    }

    _init(sr) {
        const f = Math.max(20, this.frequency)
        // waveguide delay = (sr / freq - 1) / 2 per direction
        // total round-trip = sr/freq, split between two delay lines
        const totalDelay = Math.max(2, Math.floor(sr / f))
        this.delayLen = Math.max(1, Math.floor(totalDelay / 2))
        this.delayFwdL = new Float32Array(this.delayLen)
        this.delayBwdL = new Float32Array(this.delayLen)
        this.delayFwdR = new Float32Array(this.delayLen)
        this.delayBwdR = new Float32Array(this.delayLen)
        this.idxL = 0
        this.idxR = 0
        this.bridgeFiltL = 0
        this.bridgeFiltR = 0
        this.nutStateL = 0
        this.nutStateR = 0
        this.cached = true
    }

    processAudio(inputs, outputs, parameters) {
        const sr = this.sampleRate || 44100
        if (!this.cached) this._init(sr)

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

        // decay → termination reflection gain
        const reflGain = this.decay * 0.99
        // brightness → bridge filter coefficient (1=pass all, 0=max lowpass)
        const bridgeCoeff = 0.5 + this.brightness * 0.5
        // inharmonicity → allpass coefficient at nut (0=pure reflection, 1=dispersive)
        const nutCoeff = this.inharmonicity * 0.95
        // pick position → excitation split between forward/backward waves
        const pickFwd = Math.cos(this.pick_position * Math.PI)
        const pickBwd = Math.sin(this.pick_position * Math.PI)

        const dF = this.delayFwdL
        const dB = this.delayBwdL
        const dFR = this.delayFwdR
        const dBR = this.delayBwdR
        const dLen = this.delayLen

        for (let i = 0; i < len; i++) {
            const sL = inL[i]
            const sR = inR[i]

            // --- Left channel waveguide ---
            // Read current positions
            const fwdL = dF[this.idxL]
            const bwdL = dB[this.idxL]

            // Bridge: lowpass filter + reflection (right-going → left-going with damping)
            const bridgeOutL = bridgeCoeff * bwdL + (1 - bridgeCoeff) * this.bridgeFiltL
            this.bridgeFiltL = bridgeOutL
            const reflectedL = bridgeOutL * reflGain

            // Nut: allpass dispersion + reflection (left-going → right-going)
            // simple first-order allpass for inharmonicity
            const nutInL = fwdL
            const nutOutL = nutCoeff * nutInL + this.nutStateL
            this.nutStateL = nutInL - nutCoeff * nutOutL
            const nutReflL = nutOutL * reflGain

            // Excitation: input splits into both waves at pick position
            const exciteL = sL * 0.5
            const newFwdL = nutReflL + exciteL * pickFwd
            const newBwdL = reflectedL + exciteL * pickBwd

            // Write back
            dF[this.idxL] = newFwdL
            dB[this.idxL] = newBwdL

            // Output = sum of both waves at current position
            const waveOutL = (fwdL + bwdL) * 0.5

            // Advance index
            this.idxL = (this.idxL + 1) % dLen

            // --- Right channel waveguide ---
            const fwdR = dFR[this.idxR]
            const bwdR = dBR[this.idxR]

            const bridgeOutR = bridgeCoeff * bwdR + (1 - bridgeCoeff) * this.bridgeFiltR
            this.bridgeFiltR = bridgeOutR
            const reflectedR = bridgeOutR * reflGain

            const nutInR = fwdR
            const nutOutR = nutCoeff * nutInR + this.nutStateR
            this.nutStateR = nutInR - nutCoeff * nutOutR
            const nutReflR = nutOutR * reflGain

            const exciteR = sR * 0.5
            dFR[this.idxR] = nutReflR + exciteR * pickFwd
            dBR[this.idxR] = reflectedR + exciteR * pickBwd

            const waveOutR = (fwdR + bwdR) * 0.5
            this.idxR = (this.idxR + 1) % dLen

            outL[i] = (sL * dry + waveOutL * wet) * outGain
            outR[i] = (sR * dry + waveOutR * wet) * outGain
        }
    }
}
