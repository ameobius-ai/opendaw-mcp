// @werkstatt vinyl 1 1
// @label Vinyl Simulator
// @param age 0.3 0 1 linear
// @param dust 0.5 0 1 linear
// @param wear 0.2 0 1 linear
// @param wow 0.15 0 0.5 linear
// @param flutter 0.05 0 0.5 linear
// @param noise 0.3 0 1 linear
// @param mix 0.7 0 1 linear
// @param output 0 -24 6 linear

class Processor {
    age = 0.3
    dust = 0.5
    wear = 0.2
    wow = 0.15
    flutter = 0.05
    noise = 0.3
    mix = 0.7
    output = 0

    // LCG random
    _rng = 12345
    _rand() {
        this._rng = (this._rng * 1103515245 + 12345) & 0x7fffffff
        return this._rng / 0x7fffffff
    }

    // crackle state
    _crackleEnv = 0
    _nextPopAt = 0
    _popCounter = 0

    // wow/flutter state (sinusoidal)
    _wowPhase = 0
    _flutterPhase = 0
    _wowFreq = 0.8   // Hz
    _flutterFreq = 6.5  // Hz

    // pitch shift via fractional delay buffer
    _bufSize = 8192
    _bufL = null
    _bufR = null
    _writePos = 0
    _init = false

    paramChanged(label, value) {
        this[label] = value
    }

    _initBuffers() {
        this._bufL = new Float32Array(this._bufSize)
        this._bufR = new Float32Array(this._bufSize)
        this._init = true
    }

    processAudio(inputs, outputs, parameters) {
        const sr = this.sampleRate || 44100
        if (!this._init) this._initBuffers(sr)

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

        // dust/crackle rate: more dust → more pops
        const popRate = this.dust * 150  // pops per second
        const popInterval = sr / Math.max(1, popRate)
        if (this._nextPopAt === 0) this._nextPopAt = this._rand() * popInterval

        // age affects crackle brightness and density
        const crackleDecay = sr * (0.003 + this.age * 0.01)  // 3-13ms
        const crackleAmp = 0.15 + this.dust * 0.5

        // wear: high-freq rolloff (warmer = less wear, more wear = duller)
        // simple one-pole LP for wear
        const wearCoeff = 1 - this.wear * 0.3
        let wearZ1L = 0, wearZ1R = 0

        // noise: continuous surface hiss
        const noiseAmp = this.noise * 0.04

        // wow/flutter coefficients
        const wowInc = 2 * Math.PI * this._wowFreq / sr
        const flutterInc = 2 * Math.PI * this._flutterFreq / sr
        const wowDepth = this.wow * 0.002  // 0-2ms delay modulation
        const flutterDepth = this.flutter * 0.0004  // 0-0.4ms
        const baseDelay = 64  // samples base delay for pitch modulation

        for (let i = 0; i < len; i++) {
            // --- pitch modulation via fractional delay ---
            this._wowPhase += wowInc
            this._flutterPhase += flutterInc
            const modSamples = baseDelay
                + Math.sin(this._wowPhase) * wowDepth * sr
                + Math.sin(this._flutterPhase) * flutterDepth * sr

            // write input to buffer
            this._bufL[this._writePos] = inL[i]
            this._bufR[this._writePos] = inR[i]

            // fractional read for pitch wobble
            const readPos = this._writePos - modSamples + this._bufSize
            const idx = Math.floor(readPos) % this._bufSize
            const frac = readPos - Math.floor(readPos)
            const idx2 = (idx + 1) % this._bufSize
            const pitchedL = this._bufL[idx] * (1 - frac) + this._bufL[idx2] * frac
            const pitchedR = this._bufR[idx] * (1 - frac) + this._bufR[idx2] * frac

            this._writePos = (this._writePos + 1) % this._bufSize

            // --- crackle/pops ---
            this._popCounter++
            if (this._popCounter >= this._nextPopAt) {
                this._crackleEnv = crackleAmp * (0.5 + this._rand() * 0.5)
                this._popCounter = 0
                this._nextPopAt = popInterval * (0.3 + this._rand() * 1.4)
            }
            // exponential decay of crackle envelope
            const crackleDecayRate = 1 - 1 / crackleDecay
            this._crackleEnv *= crackleDecayRate
            // crackle noise burst
            const crackleL = this._crackleEnv * (this._rand() * 2 - 1)
            const crackleR = this._crackleEnv * (this._rand() * 2 - 1)

            // --- surface noise (filtered random) ---
            // simple one-pole HP for hiss character
            const rawNoiseL = (this._rand() * 2 - 1) * noiseAmp
            const rawNoiseR = (this._rand() * 2 - 1) * noiseAmp
            const noiseOutL = rawNoiseL * 0.7
            const noiseOutR = rawNoiseR * 0.7

            // --- wear: one-pole LP on pitched signal ---
            wearZ1L = wearZ1L * wearCoeff + pitchedL * (1 - wearCoeff)
            wearZ1R = wearZ1R * wearCoeff + pitchedR * (1 - wearCoeff)
            const wornL = pitchedL * (1 - this.wear * 0.5) + wearZ1L * this.wear * 0.5
            const wornR = pitchedR * (1 - this.wear * 0.5) + wearZ1R * this.wear * 0.5

            // --- sum everything ---
            const wetL = wornL + crackleL + noiseOutL
            const wetR = wornR + crackleR + noiseOutR

            outL[i] = (inL[i] * dry + wetL * wet) * outGain
            outR[i] = (inR[i] * dry + wetR * wet) * outGain
        }
    }
}
