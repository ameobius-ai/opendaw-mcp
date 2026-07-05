// @werkstatt reverse 1 1
// @label Reverse
// @param chunk_size 0.5 0.05 5 linear sec
// @param feedback 0 0 0.9 linear
// @param speed 1 0.25 4 linear x
// @param smooth 0 0 0.1 linear sec
// @param dry_gain 0 0 1 linear
// @param wet_gain 1 0 1 linear
// @param mix 1 0 1 linear
// @param stereo_mode 0 0 2 linear type
// @param trigger_mode 0 0 2 linear type
// @param output 0 -12 12 linear dB

class Processor {
  p = {chunk_size: 0.5, feedback: 0, speed: 1, smooth: 0,
       dry_gain: 0, wet_gain: 1, mix: 1, stereo_mode: 0,
       trigger_mode: 0, output: 0}
  sr = 44100
  bs = 128

  // Circular buffer for chunks
  bufL = null
  bufR = null
  bufSize = 0
  writePos = 0
  readPos = 0

  // Chunk state
  chunkLen = 0
  chunkSamples = 0
  chunkProgress = 0
  fadeIncr = 0

  // Feedback state
  fbL = 0
  fbR = 0

  // Envelope for smoothing
  envState = 0

  constructor() {
    if (this.sampleRate) this.sr = this.sampleRate
    if (this.blockSize) this.bs = this.blockSize
    this.bufSize = Math.ceil(this.sr * 10) // 10 seconds max
    this.bufL = new Float32Array(this.bufSize)
    this.bufR = new Float32Array(this.bufSize)
    this.chunkSamples = Math.floor(this.p.chunk_size * this.sr)
  }

  paramChanged(name, value) {
    this.p[name] = value
    if (name === "chunk_size") {
      this.chunkSamples = Math.floor(value * this.sr)
    }
  }

  // Write one sample to circular buffer
  _write(xL, xR) {
    this.bufL[this.writePos] = xL
    this.bufR[this.writePos] = xR
    this.writePos = (this.writePos + 1) % this.bufSize
  }

  // Read from a position that's chunkSamples behind write position
  // But in reverse order — read backwards from writePos-1
  _readReverse(offset) {
    const pos = (this.writePos - 1 - offset + this.bufSize * 10) % this.bufSize
    return [this.bufL[pos], this.bufR[pos]]
  }

  processAudio(inputs, outputs) {
    const inp = inputs[0]
    const out = outputs[0]
    if (!inp || !out) return

    const sr = this.sr
    const stereo = out.length > 1
    const mix = this.p.mix
    const dryGain = this.p.dry_gain
    const wetGain = this.p.wet_gain
    const outGain = Math.pow(10, this.p.output / 20)
    const fbAmt = this.p.feedback
    const speed = this.p.speed
    const smooth = this.p.smooth
    const stereoMode = this.p.stereo_mode
    const triggerMode = this.p.trigger_mode

    const cs = this.chunkSamples
    const fadeSamples = Math.max(0, Math.floor(smooth * sr))
    const readSpeed = speed

    for (let i = 0; i < out[0].length; i++) {
      const inL = inp[0] ? inp[0][i] : 0
      const inR = stereo && inp.length > 1 && inp[1] ? inp[1][i] : inL

      // Add feedback
      const writeL = inL + this.fbL * fbAmt
      const writeR = inR + this.fbR * fbAmt

      // Write to buffer
      this._write(writeL, writeR)

      // Read reversed
      const readOff = Math.floor(this.chunkProgress)
      let [revL, revR] = this._readReverse(readOff)

      // Crossfade for smooth transitions
      if (fadeSamples > 0) {
        const fadePos = this.chunkProgress % 1
        // Fade in at start, fade out at end of chunk
        let env = 1
        const fadeStart = Math.min(fadePos * cs / fadeSamples, 1)
        const fadeEnd = Math.min((1 - fadePos) * cs / fadeSamples, 1)
        env = Math.min(fadeStart, fadeEnd)
        env = Math.max(0, Math.min(1, env))
        revL *= env
        revR *= env
      }

      // Stereo mode processing
      if (stereoMode === 1) {
        // Ping-pong: L gets reversed R, R gets reversed L
        const tmp = revL
        revL = revR
        revR = tmp
      } else if (stereoMode === 2) {
        // Wide: L-R reversed
        const mid = (revL + revR) * 0.5
        const side = (revL - revR) * 0.5
        revL = mid + side
        revR = mid - side
      }

      // Advance read position
      this.chunkProgress += readSpeed

      // When we've read through the whole chunk, reset
      if (this.chunkProgress >= cs) {
        if (triggerMode === 0) {
          // Continuous: immediately start next chunk
          this.chunkProgress = 0
        } else if (triggerMode === 1) {
          // Single: freeze at end
          this.chunkProgress = cs - 1
        } else {
          // Gate: reset only if input is loud enough
          if (Math.abs(inL) + Math.abs(inR) > 0.01) {
            this.chunkProgress = 0
          }
        }
      }

      // Update feedback
      this.fbL = revL
      this.fbR = revR

      // Output
      const dryL = inL * dryGain
      const dryR = inR * dryGain
      const wetL = revL * wetGain * outGain
      const wetR = revR * wetGain * outGain

      out[0][i] = dryL * (1 - mix) + wetL * mix
      if (stereo) {
        out[1][i] = dryR * (1 - mix) + wetR * mix
      }
    }
  }
}
