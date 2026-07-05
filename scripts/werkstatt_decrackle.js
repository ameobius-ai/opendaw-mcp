// @werkstatt decrackle 1 1
// @label De-Crackle (Continuous Crackle Removal)
// Restoration tool: removes continuous crackle from vinyl, tape, and old recordings
// iZotope RX De-crackle / CEDAR Decrackle — adaptive crackle modeling + interpolation

// @param strength    0.5  0  1    linear   // crackle removal strength: 0=light, 1=aggressive
// @param sensitivity 0.5  0  1    linear   // detection sensitivity: 0=only loud crackles, 1=subtle too
// @param freq_est    0.4  0  1    linear   // crackle frequency estimation: 0=few/sec, 1=many/sec
// @param smooth      0.5  0  1    linear   // interpolation smoothing: 0=sharp, 1=smooth transitions
// @param adaptive    0.7  0  1    linear   // adaptive threshold: 0=fixed, 1=tracks crackle density
// @param mix         1    0  1    linear   // dry/wet mix
// @param output      0    -12 6  linear dB

class Processor {
  p = {strength: 0.5, sensitivity: 0.5, freq_est: 0.4, smooth: 0.5, adaptive: 0.7, mix: 1, output: 0}
  sr = 44100
  outGain = 1

  // Per-channel state
  DELAY = 128
  delayBufs = null

  // Adaptive crackle model
  crackleEnergy = 0     // running estimate of crackle energy
  signalEnergy = 0      // running estimate of signal energy
  crackleRate = 0       // estimated crackles per second
  threshold = 0         // current adaptive threshold

  // Smoothing state
  prevRepaired = 0      // previous output sample for smoothing

  constructor() {
    if (this.sampleRate) this.sr = this.sampleRate
  }

  paramChanged(name, value) {
    this.p[name] = value
    if (name === "output") {
      this.outGain = Math.pow(10, value / 20)
    }
  }

  // Cubic Hermite interpolation
  _hermite(t, p0, p1, p2, p3) {
    const t2 = t * t
    const t3 = t2 * t
    const m1 = 0.5 * (p2 - p0)
    const m2 = 0.5 * (p3 - p1)
    return (2*t3 - 3*t2 + 1) * p1 + (t3 - 2*t2 + t) * m1
      + (-2*t3 + 3*t2) * p2 + (t3 - t2) * m2
  }

  _linear(t, p1, p2) {
    return p1 * (1 - t) + p2 * t
  }

  processAudio(inputs, outputs) {
    const input = inputs[0]
    const output = outputs[0]
    if (!input || !output) return

    const n = output[0].length
    const og = this.outGain
    const mix = this.p.mix
    const D = this.DELAY

    // Detection threshold base
    const sensBase = 0.06 - this.p.sensitivity * 0.05  // 0.06 to 0.01
    const smoothAmt = this.p.smooth
    const strengthAmt = this.p.strength
    const adaptAmt = this.p.adaptive

    // Crackle rate estimate (crackles per second)
    const estRate = 10 + this.p.freq_est * 190  // 10 to 200 crackles/sec
    const samplesPerCrackle = this.sr / estRate

    // Ensure per-channel delay buffers
    if (!this.delayBufs || this.delayBufs.length < output.length) {
      this.delayBufs = []
      for (let i = 0; i < output.length; i++) {
        this.delayBufs.push(new Float32Array(D))
      }
    }

    for (let ch = 0; ch < output.length; ch++) {
      const inCh = input[ch] || input[0]
      const outCh = output[ch]
      const delayBuf = this.delayBufs[ch]

      // Combined buffer: [delay (look-back)] + [current block]
      const combined = new Float32Array(D + n)
      for (let i = 0; i < D; i++) combined[i] = delayBuf[i]
      for (let i = 0; i < n; i++) combined[D + i] = inCh[i]

      // Update delay buffer
      for (let i = 0; i < D; i++) delayBuf[i] = combined[n + i]

      // Repaired output
      const repaired = new Float32Array(n)

      // Sliding local energy for adaptive threshold
      let localEnergy = 0
      const energyWin = 256

      for (let i = 0; i < n; i++) {
        const idx = D + i

        // Update local energy
        localEnergy += combined[idx] * combined[idx]
        if (i >= energyWin) localEnergy -= combined[idx - energyWin] * combined[idx - energyWin]
        const localRMS = Math.sqrt(localEnergy / Math.min(energyWin, i + 1))

        // Adaptive threshold: base + local energy + crackle energy
        // Track crackle energy separately from signal
        const absVal = Math.abs(combined[idx])
        const isLikelyCrackle = absVal > this.threshold && absVal < this.threshold * 4

        // Update crackle energy estimate (only when crackle detected)
        if (isLikelyCrackle) {
          this.crackleEnergy = this.crackleEnergy * 0.99 + absVal * 0.01
        }

        // Update signal energy
        this.signalEnergy = this.signalEnergy * 0.999 + localRMS * localRMS * 0.001

        // Adaptive threshold: rises with signal energy, falls with crackle density
        const signalFloor = Math.sqrt(this.signalEnergy) * (0.5 + sensBase * 10)
        this.threshold = signalFloor * (1 - adaptAmt) + (this.crackleEnergy * 2 + signalFloor) * adaptAmt

        // Crackle detection: short spike above threshold but below "real signal" level
        const isCrackle = absVal > this.threshold && absVal < signalFloor * 8

        if (isCrackle && strengthAmt > 0.01) {
          // Find crackle extent (crackles are short: 1-8 samples typically)
          let crackEnd = i
          let maxDev = absVal
          while (crackEnd < n - 1 && crackEnd < i + 8) {
            const nextAbs = Math.abs(combined[D + crackEnd + 1])
            if (nextAbs > this.threshold * 0.5) {
              maxDev = Math.max(maxDev, nextAbs)
              crackEnd++
            } else {
              break
            }
          }

          // Interpolate across crackle region
          const beforeIdx = D + i - 1
          const afterIdx = D + crackEnd + 1

          const p0 = (beforeIdx - 1 >= 0) ? combined[beforeIdx - 1] : 0
          const p1 = (beforeIdx >= 0) ? combined[beforeIdx] : 0
          const p2 = (afterIdx < D + n) ? combined[afterIdx] : 0
          const p3 = (afterIdx + 1 < D + n) ? combined[afterIdx + 1] : 0

          const crackLen = crackEnd - i + 1
          for (let j = 0; j < crackLen; j++) {
            const t = crackLen > 1 ? j / (crackLen - 1) : 0
            // Blend between hermite and linear based on smooth param
            const hermVal = this._hermite(t, p0, p1, p2, p3)
            const linVal = this._linear(t, p1, p2)
            repaired[i + j] = hermVal * smoothAmt + linVal * (1 - smoothAmt)
          }

          // Apply strength: blend original with repaired
          for (let j = 0; j < crackLen; j++) {
            const origIdx = D + i + j
            repaired[i + j] = combined[origIdx] * (1 - strengthAmt) + repaired[i + j] * strengthAmt
          }

          i = crackEnd  // skip past crackle
        } else {
          repaired[i] = combined[idx]
        }
      }

      // Output with dry/wet
      for (let j = 0; j < n; j++) {
        const dry = inCh[j]
        const wet = repaired[j]
        outCh[j] = (dry * (1 - mix) + wet * mix) * og
      }
    }
  }

  reset() {
    if (this.delayBufs) {
      for (let i = 0; i < this.delayBufs.length; i++) {
        this.delayBufs[i].fill(0)
      }
    }
    this.crackleEnergy = 0
    this.signalEnergy = 0
    this.crackleRate = 0
    this.threshold = 0
    this.prevRepaired = 0
  }
}
