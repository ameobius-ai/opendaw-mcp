// @werkstatt grain_delay 1 1
// @label Grain Delay
// @param delay 150 10 1000 exp
// @param grain_size 80 10 500 exp
// @param grain_rate 20 1 100 exp
// @param pitch 1 0.25 4 exp
// @param scatter 0.3 0 1 linear
// @param pan 0.5 0 1 linear
// @param reverse 0 0 1 linear
// @param feedback 0.2 0 0.9 linear
// @param mix 0.5 0 1 linear
// @param output 0 -24 6 linear

class Processor {
    delay = 150
    grain_size = 80
    grain_rate = 20
    pitch = 1
    scatter = 0.3
    pan = 0.5
    reverse = 0
    feedback = 0.2
    mix = 0.5
    output = 0

    _rng = 42
    _rand() {
        this._rng = (this._rng * 1103515245 + 12345) & 0x7fffffff
        return this._rng / 0x7fffffff
    }

    _bufSize = 0
    _bufL = null
    _bufR = null
    _writePos = 0
    _grains = []
    _grainCounter = 0
    _init = false
    _sr = 44100

    paramChanged(label, value) {
        this[label] = value
    }

    _initBuffers(sr) {
        this._sr = sr
        this._bufSize = Math.max(256, Math.ceil(sr * 2))
        this._bufL = new Float32Array(this._bufSize)
        this._bufR = new Float32Array(this._bufSize)
        this._writePos = 0
        this._grains = []
        this._init = true
    }

    _wrap(pos) {
        return ((Math.floor(pos) % this._bufSize) + this._bufSize) % this._bufSize
    }

    _spawnGrain() {
        const sr = this._sr
        const delaySamps = this.delay * 0.001 * sr
        const grainSamps = Math.max(4, this.grain_size * 0.001 * sr)

        const jitter = (this._rand() * 2 - 1) * this.scatter * delaySamps * 0.5
        const readStart = this._writePos - delaySamps + jitter

        const panAmt = (this._rand() * 2 - 1) * this.pan
        const isReverse = this._rand() < this.reverse
        const amp = 0.6 + this._rand() * 0.4

        this._grains.push({
            bufPos: this._wrap(readStart),
            readPos: 0,
            grainLen: grainSamps,
            pitch: this.pitch,
            reverse: isReverse,
            panL: Math.cos((panAmt + 1) * Math.PI * 0.25),
            panR: Math.sin((panAmt + 1) * Math.PI * 0.25),
            amp: amp,
        })
    }

    _hann(pos, len) {
        return 0.5 * (1 - Math.cos(2 * Math.PI * pos / len))
    }

    processAudio(inputs, outputs, parameters) {
        const sr = this.sampleRate || 44100
        if (!this._init || this._sr !== sr) this._initBuffers(sr)

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
        const grainInterval = Math.max(1, Math.floor(sr / this.grain_rate))
        const fb = this.feedback
        const delaySamps = Math.floor(this.delay * 0.001 * sr)

        for (let i = 0; i < len; i++) {
            // feedback from delay position
            const fbPos = this._wrap(this._writePos - delaySamps)
            const fbL = this._bufL[fbPos] * fb
            const fbR = this._bufR[fbPos] * fb

            // write input + feedback to buffer
            this._bufL[this._writePos] = inL[i] + fbL
            this._bufR[this._writePos] = inR[i] + fbR

            // spawn grains at regular interval
            this._grainCounter++
            if (this._grainCounter >= grainInterval) {
                this._spawnGrain()
                this._grainCounter = 0
            }

            // sum active grains
            let wetL = 0, wetR = 0
            for (let g = this._grains.length - 1; g >= 0; g--) {
                const grain = this._grains[g]
                if (grain.readPos >= grain.grainLen) {
                    this._grains.splice(g, 1)
                    continue
                }

                const win = this._hann(grain.readPos, grain.grainLen)
                const readOffset = grain.reverse
                    ? (grain.grainLen - grain.readPos)
                    : grain.readPos
                const bufReadPos = grain.bufPos + readOffset * grain.pitch
                const idx = this._wrap(bufReadPos)
                const idx2 = (idx + 1) % this._bufSize
                const frac = bufReadPos - Math.floor(bufReadPos)
                const sL = this._bufL[idx] * (1 - frac) + this._bufL[idx2] * frac
                const sR = this._bufR[idx] * (1 - frac) + this._bufR[idx2] * frac

                wetL += sL * win * grain.amp * grain.panL
                wetR += sR * win * grain.amp * grain.panR

                grain.readPos += 1
            }

            outL[i] = (inL[i] * dry + wetL * wet) * outGain
            outR[i] = (inR[i] * dry + wetR * wet) * outGain

            this._writePos = (this._writePos + 1) % this._bufSize
        }

        if (this._grains.length > 80) {
            this._grains = this._grains.slice(-80)
        }
    }
}
