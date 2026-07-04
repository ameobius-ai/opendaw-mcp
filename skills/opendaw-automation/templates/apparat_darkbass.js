// @apparat darkbass 1 1
// @label Dark Bass
// @param waveform 2 0 3 int
// @param cutoff 200 50 8000 exp Hz
// @param resonance 0.7 0.1 8 linear
// @param attack 0.005 0.001 0.5 exp s
// @param decay 0.3 0.01 4 exp s
// @param sustain 0.7 0 1 linear
// @param release 0.4 0.01 4 exp s
// @param subOsc 0.5 0 1 linear
// @param detune 0.1 0 0.5 linear
// @param volume 0.6 0 1 linear

class Processor {
    // CRITICAL: do NOT add a constructor that destructures args.
    // Host calls new ProcessorClass() with ZERO arguments.
    // If you need sampleRate, use the global `sampleRate` (set by worklet-env.ts).
    voices = []
    phase = new Float32Array(8)
    subPhase = new Float32Array(8)
    env = new Float32Array(8)
    active = new Int32Array(8)
    voicePitch = new Float32Array(8)
    voiceAge = new Int32Array(8)

    waveform = 2
    cutoff = 200
    resonance = 0.7
    attack = 0.005
    decay = 0.3
    sustain = 0.7
    release = 0.4
    subOsc = 0.5
    detune = 0.1
    volume = 0.6

    // filter state per voice
    f1lo = new Float32Array(8)
    f1hi = new Float32Array(8)

    paramChanged(label, value) {
        this[label] = value
    }

    noteOn(pitch, velocity, cent, id) {
        let idx = -1
        for (let i = 0; i < 8; i++) {
            if (this.active[i] === 0) { idx = i; break }
        }
        if (idx < 0) {
            let oldest = 0
            for (let i = 1; i < 8; i++) {
                if (this.voiceAge[i] > this.voiceAge[oldest]) oldest = i
            }
            idx = oldest
        }
        this.active[idx] = id || (pitch + 1)
        this.voicePitch[idx] = pitch + cent / 100
        this.env[idx] = 0
        this.voiceAge[idx] = 0
        this.phase[idx] = 0
        this.subPhase[idx] = 0
    }

    noteOff(id) {
        if (!id) {
            for (let i = 0; i < 8; i++) this.active[i] = 0
            return
        }
        for (let i = 0; i < 8; i++) {
            if (this.active[i] === id) {
                this.env[i] = 0
                this.active[i] = 0
            }
        }
    }

    reset() {
        for (let i = 0; i < 8; i++) {
            this.active[i] = 0
            this.env[i] = 0
            this.phase[i] = 0
            this.subPhase[i] = 0
        }
    }

    osc(phase, wave) {
        const p = phase % 1
        switch (wave) {
            case 0: return Math.sin(p * 6.283185)
            case 1: return p < 0.5 ? 1 - p * 4 : p * 4 - 3
            case 2: return 2 * p - 1
            case 3: return p < 0.5 ? 1 : -1
            default: return 2 * p - 1
        }
    }

    process(output, block) {
        const outL = output[0]
        const outR = output[1]
        const sr = sampleRate
        const dt = 1 / sr
        const detuneAmt = this.detune * 0.01
        const subLevel = this.subOsc
        const vol = this.volume

        // ADSR rates
        const aRate = 1 / (Math.max(0.001, this.attack) * sr)
        const dRate = 1 / (Math.max(0.001, this.decay) * sr)
        const sLevel = this.sustain
        const rRate = 1 / (Math.max(0.001, this.release) * sr)

        // filter coeff
        const fc = Math.min(0.49, this.cutoff / sr)
        const res = this.resonance
        const lpCoeff = 1 - Math.exp(-2 * Math.PI * fc)
        const hpCoeff = 1 - Math.exp(-2 * Math.PI * fc * 0.5)

        for (let i = block.s0; i < block.s1; i++) {
            let sumL = 0
            let sumR = 0

            for (let v = 0; v < 8; v++) {
                if (this.active[v] === 0) continue

                this.voiceAge[v]++

                // ADSR
                const isActive = this.active[v] > 0
                if (isActive) {
                    if (this.env[v] < 1) {
                        this.env[v] = Math.min(1, this.env[v] + aRate)
                    } else if (this.env[v] > sLevel) {
                        this.env[v] = Math.max(sLevel, this.env[v] - dRate)
                    }
                }

                // frequency
                const freq = 440 * Math.pow(2, (this.voicePitch[v] - 69) / 12)
                const phaseInc = freq * dt + detuneAmt * freq * dt * 0.1

                // main oscillator
                const main = this.osc(this.phase[v], this.waveform)
                this.phase[v] += phaseInc

                // sub oscillator (one octave down, square)
                const subFreq = freq * 0.5
                const subInc = subFreq * dt
                const sub = (this.subPhase[v] % 1) < 0.5 ? 1 : -1
                this.subPhase[v] += subInc

                // mix
                const mixed = main * (1 - subLevel * 0.3) + sub * subLevel * 0.7

                // per-voice lowpass
                this.f1lo[v] = this.f1lo[v] * (1 - lpCoeff) + mixed * lpCoeff
                this.f1hi[v] = this.f1hi[v] * (1 - hpCoeff) + mixed * hpCoeff
                const filtered = this.f1lo[v] + res * (this.f1lo[v] - this.f1hi[v])

                // envelope
                const env = this.env[v]
                const out = filtered * env * vol

                sumL += out
                sumR += out

                // release after noteOff
                if (!isActive && this.env[v] > 0) {
                    this.env[v] = Math.max(0, this.env[v] - rRate)
                    if (this.env[v] <= 0) this.active[v] = 0
                }
            }

            // hard clip
            outL[i] = sumL > 1 ? 1 : (sumL < -1 ? -1 : sumL)
            outR[i] = sumR > 1 ? 1 : (sumR < -1 ? -1 : sumR)
        }
    }
}
