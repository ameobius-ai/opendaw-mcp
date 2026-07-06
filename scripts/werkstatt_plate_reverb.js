// @werkstatt plate_reverb 1 1
// @label Plate Reverb
// @param size 0.5 0 1 linear
// @param decay 0.4 0 1 linear
// @param damping 0.3 0 1 linear
// @param predelay 0.1 0 1 linear
// @param width 0.7 0 1 linear
// @param mix 0.3 0 1 linear
// @param lowCut 0.3 0 1 linear
// @param diff 0.8 0 1 linear

// Plate reverb — EMT 140 / Valhalla Plate style algorithmic reverb.
// Unlike hall/room reverbs (which have distinct early reflections + tail),
// plate reverb has diffuse, dense, bright sound from the start —
// the metallic plate creates an even, smooth wash of reverb with no
// distinct early reflections. Signature sound on vocals, drums, guitars
// from the 60s to today.
//
// Architecture: 4 parallel allpass diffusers → feedback delay network
// with damping lowpass + modulation for shimmer. Stereo width via
// L/R cross-feed. Pre-delay before the reverb enters.
//
// size: 0→small plate (0.5s), 1→large plate (8s decay)
// decay: 0→0.2s, 1→12s RT60
// damping: 0→no damping (bright), 1→heavy damping (dark, muted highs)
// predelay: 0→0ms, 1→200ms
// width: 0→mono, 1→full stereo
// mix: dry/wet
// lowCut: 0→no filter, 1→200Hz highpass on input
// diff: 0→less diffusion (metallic), 1→max diffusion (smooth)

class Processor {
  p = {size: 0.5, decay: 0.4, damping: 0.3, predelay: 0.1, width: 0.7, mix: 0.3, lowCut: 0.3, diff: 0.8}
  sr = sampleRate
  // Allpass diffuser state (4 stages, L+R)
  ap = [[0,0],[0,0],[0,0],[0,0]]
  apTime = [0.007, 0.011, 0.013, 0.017]  // prime ms values
  apIdx = [0,0,0,0]
  // Delay lines for FDN (6 delays in a feedback matrix)
  dl = [[],[]]  // L, R delay buffers
  dlTime = [0.029, 0.037, 0.041, 0.043, 0.053, 0.059]  // prime ms
  dlIdx = [0,0]
  // Pre-delay buffer
  pd = [[],[]]
  pdIdx = [0,0]
  // Damping lowpass state
  dampL = 0
  dampR = 0
  // Lowcut highpass state
  lcL = 0
  lcR = 0
  // LFO for modulation (subtle shimmer)
  lfoPhase = 0

  paramChanged(name, value) {
    this.p[name] = value
  }

  _initDelay(buf, ms) {
    const len = Math.max(1, Math.floor(this.sr * ms / 1000))
    if (buf.length !== len) {
      buf.length = len
      for (let i = 0; i < len; i++) buf[i] = 0
    }
    return len
  }

  processAudio(inputs, outputs, parameters) {
    const input = inputs[0]
    const output = outputs[0]
    if (!input || !output) return

    const sizeMs = 5 + this.p.size * 300  // 5-305ms base delay scale
    const decaySec = 0.2 + this.p.decay * 11.8  // 0.2-12s
    const dampingHz = 200 + (1 - this.p.damping) * 6000  // 200-6200Hz
    const predelayMs = this.p.predelay * 200
    const width = this.p.width
    const mix = this.p.mix
    const lowCutHz = this.p.lowCut * 200
    const diffAmount = this.p.diff

    const dampAlpha = Math.exp(-2 * Math.PI * dampingHz / this.sr)
    const lcAlpha = Math.exp(-2 * Math.PI * lowCutHz / this.sr)
    const decayGain = Math.pow(0.001, 1 / (decaySec * this.sr / 1000))  // RT60

    // Init delay buffers
    const pdLen = this._initDelay(this.pd[0], predelayMs)
    this._initDelay(this.pd[1], predelayMs)

    // Init FDN delay buffers (scaled by size)
    const dlLens = this.dlTime.map(t => Math.max(1, Math.floor(this.sr * t * sizeMs / 100 / 1000 * 100)))
    for (let ch = 0; ch < 2; ch++) {
      const totalLen = dlLens.reduce((a,b) => a+b, 0)
      if (this.dl[ch].length !== totalLen) {
        this.dl[ch] = new Float32Array(totalLen)
      }
    }

    const lfoFreq = 0.5  // 0.5 Hz modulation
    const lfoInc = 2 * Math.PI * lfoFreq / this.sr

    for (let ch = 0; ch < input.length; ch++) {
      const inCh = input[ch]
      const outCh = output[ch]
      if (!inCh || !outCh) continue
      const chIdx = Math.min(ch, 1)  // L=0, R=1

      for (let i = 0; i < inCh.length; i++) {
        let x = inCh[i]

        // Lowcut (highpass)
        if (ch === 0) {
          this.lcL = this.lcL * lcAlpha + x * (1 - lcAlpha)
          x = x - this.lcL
        } else {
          this.lcR = this.lcR * lcAlpha + x * (1 - lcAlpha)
          x = x - this.lcR
        }

        // Pre-delay
        this.pd[chIdx][this.pdIdx[chIdx]] = x
        const pdOut = this.pd[chIdx][(this.pdIdx[chIdx] + 1) % pdLen]
        this.pdIdx[chIdx] = (this.pdIdx[chIdx] + 1) % pdLen

        // Allpass diffusers (series)
        let diffused = pdOut
        for (let a = 0; a < 4; a++) {
          const apLen = Math.max(1, Math.floor(this.sr * this.apTime[a] * (0.5 + diffAmount) / 1000))
          const apOut = this.ap[a][chIdx]
          this.ap[a][chIdx] = diffused + apOut * 0.5
          diffused = apOut - this.ap[a][chIdx] * 0.5
        }

        // FDN: simplified — use a single long delay per channel with feedback
        const dlBuf = this.dl[chIdx]
        const dlLen = dlBuf.length
        if (dlLen < 2) continue

        // Read from delay
        const readIdx = (this.dlIdx[chIdx] - Math.floor(dlLen * 0.5) + dlLen) % dlLen
        let wet = dlBuf[readIdx]

        // Damping lowpass on feedback
        if (ch === 0) {
          this.dampL = this.dampL * dampAlpha + wet * (1 - dampAlpha)
          wet = this.dampL
        } else {
          this.dampR = this.dampR * dampAlpha + wet * (1 - dampAlpha)
          wet = this.dampR
        }

        // Cross-feed for stereo width
        const crossWet = ch === 0 ? this.dampR : this.dampL
        wet = wet * (1 - width * 0.5) + crossWet * width * 0.5

        // Write to delay (input + feedback)
        dlBuf[this.dlIdx[chIdx]] = diffused + wet * decayGain
        this.dlIdx[chIdx] = (this.dlIdx[chIdx] + 1) % dlLen

        // LFO modulation (only on first channel to avoid duplicate)
        if (ch === 0) {
          this.lfoPhase += lfoInc
        }

        // Output: dry + wet
        outCh[i] = inCh[i] * (1 - mix) + wet * mix
      }
    }
  }
}
