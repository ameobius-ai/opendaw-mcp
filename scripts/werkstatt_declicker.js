// @werkstatt declicker 1 1
// @label De-Clicker (Click & Crackle Removal)
// Restoration tool: detects and removes clicks, pops, digital glitches from audio
// iZotope RX De-click / CEDAR Declick — median filter detection + cubic Hermite interpolation

// @param sensitivity  0.5  0  1    linear   // detection sensitivity: 0=conservative (big clicks only), 1=aggressive (subtle too)
// @param click_len    0.3  0  1    linear   // max click length to repair: 0=8 samples, 1=128 samples
// @param median_size  0.4  0  1    linear   // median filter window: 0=5, 1=15 (odd, larger=smoother detection)
// @param interp       0.7  0  1    linear   // interpolation quality: 0=linear, 1=cubic Hermite
// @param overlap      0.3  0  1    linear   // extra samples to repair beyond detected click edges
// @param mix          1    0  1    linear   // dry/wet mix
// @param output       0    -12 6  linear dB

class Processor {
  p = {sensitivity: 0.5, click_len: 0.3, median_size: 0.4, interp: 0.7, overlap: 0.3, mix: 1, output: 0}
  sr = 44100
  outGain = 1

  // Delay buffer for look-back context (per-channel)
  DELAY = 256
  delayBufs = null    // array of Float32Array, one per channel

  // Config (updated from params)
  medSize = 7
  medHalf = 3
  maxClickLen = 48
  overlapSamps = 12

  constructor() {
    if (this.sampleRate) this.sr = this.sampleRate
    this._updateConfig()
  }

  _updateConfig() {
    // Median filter size: 5 to 15, always odd
    const ms = Math.round(5 + this.p.median_size * 10)
    this.medSize = ms % 2 === 0 ? ms + 1 : ms
    this.medHalf = Math.floor(this.medSize / 2)
    // Max click length: 8 to 128 samples
    this.maxClickLen = Math.round(8 + this.p.click_len * 120)
    // Overlap: 0 to 32 extra samples
    this.overlapSamps = Math.round(this.p.overlap * 32)
  }

  paramChanged(name, value) {
    this.p[name] = value
    if (name === "output") {
      this.outGain = Math.pow(10, value / 20)
    }
    if (name === "click_len" || name === "median_size" || name === "overlap") {
      this._updateConfig()
    }
  }

  // Insertion sort for median (small windows — n ≤ 15)
  _median(arr, size) {
    const tmp = new Float32Array(size)
    for (let i = 0; i < size; i++) tmp[i] = arr[i]
    for (let i = 1; i < size; i++) {
      const key = tmp[i]
      let j = i - 1
      while (j >= 0 && tmp[j] > key) { tmp[j + 1] = tmp[j]; j-- }
      tmp[j + 1] = key
    }
    return tmp[Math.floor(size / 2)]
  }

  // Cubic Hermite (Catmull-Rom) interpolation
  // t in [0,1] between p1 and p2, with p0/p3 as neighbors
  _hermite(t, p0, p1, p2, p3) {
    const t2 = t * t
    const t3 = t2 * t
    const m1 = 0.5 * (p2 - p0)    // tangent at p1
    const m2 = 0.5 * (p3 - p1)    // tangent at p2
    const h00 = 2 * t3 - 3 * t2 + 1
    const h10 = t3 - 2 * t2 + t
    const h01 = -2 * t3 + 3 * t2
    const h11 = t3 - t2
    return h00 * p1 + h10 * m1 + h01 * p2 + h11 * m2
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

    // Detection threshold: 0.08 (conservative) to 0.01 (aggressive)
    const threshBase = 0.08 - this.p.sensitivity * 0.07
    const useCubic = this.p.interp > 0.3

    this._updateConfig()

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

      // Update delay buffer with last D samples
      for (let i = 0; i < D; i++) delayBuf[i] = combined[n + i]

      // First pass: median-filtered reference + click detection
      const repaired = new Float32Array(n)
      const isClick = new Uint8Array(n)

      // Sliding local energy for adaptive threshold
      let energySum = 0
      const energyWin = 64

      for (let i = 0; i < n; i++) {
        const idx = D + i

        // Update local energy (sliding window)
        energySum += Math.abs(combined[idx])
        if (i >= energyWin) energySum -= Math.abs(combined[idx - energyWin])
        const localAvg = energySum / Math.min(energyWin, i + 1)

        // Collect median window
        const winArr = new Float32Array(this.medSize)
        let validCount = 0
        for (let w = -this.medHalf; w <= this.medHalf; w++) {
          const wi = idx + w
          if (wi >= 0 && wi < D + n) {
            winArr[validCount++] = combined[wi]
          }
        }

        if (validCount < 3) {
          repaired[i] = combined[idx]
          continue
        }

        const med = this._median(winArr, validCount)

        // Detection: deviation from median vs adaptive threshold
        const deviation = Math.abs(combined[idx] - med)
        const threshold = threshBase * (1 + localAvg * 10)

        if (deviation > threshold && localAvg > 1e-6) {
          isClick[i] = 1
        }

        repaired[i] = combined[idx]
      }

      // Second pass: interpolate click regions
      let i = 0
      while (i < n) {
        if (isClick[i]) {
          // Find click extent
          let clickEnd = i
          while (clickEnd < n && isClick[clickEnd]) clickEnd++
          const clickWidth = clickEnd - i

          if (clickWidth <= this.maxClickLen) {
            // Expand with overlap for smooth transition
            const ovS = this.overlapSamps
            const interpStart = Math.max(0, i - ovS)
            const interpEnd = Math.min(n - 1, clickEnd + ovS)

            // Anchor points: clean samples before and after click
            const beforeIdx = D + interpStart - 1
            const afterIdx = D + interpEnd + 1

            const p0 = (beforeIdx - 1 >= 0) ? combined[beforeIdx - 1] : 0
            const p1 = (beforeIdx >= 0) ? combined[beforeIdx] : 0
            const p2 = (afterIdx < D + n) ? combined[afterIdx] : 0
            const p3 = (afterIdx + 1 < D + n) ? combined[afterIdx + 1] : 0

            const interpLen = interpEnd - interpStart + 1
            for (let j = 0; j < interpLen; j++) {
              const t = interpLen > 1 ? j / (interpLen - 1) : 0
              if (useCubic) {
                repaired[interpStart + j] = this._hermite(t, p0, p1, p2, p3)
              } else {
                repaired[interpStart + j] = this._linear(t, p1, p2)
              }
            }
          }
          // else: click too long — leave as-is to avoid artifacts

          i = clickEnd
        } else {
          i++
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
  }
}
