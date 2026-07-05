// @werkstatt bitcrusher 1 1
// @label Bitcrusher
// @param bits 8 1 16 linear
// @param rate 0.5 0 1 linear
// @param drive 1 0 2 linear
// @param offset 0 -1 1 linear
// @param mix 0.8 0 1 linear

class Processor {
  p = {bits: 8, rate: 0.5, drive: 1, offset: 0, mix: 0.8}
  holdCounter = 0
  heldL = 0
  heldR = 0
  phase = 0

  paramChanged(name, value) {
    this.p[name] = value
  }

  processAudio(inputs, outputs) {
    const inp = inputs[0]
    const out = outputs[0]
    if (!inp || !out) return
    const bits = Math.max(1, this.p.bits)
    const levels = Math.pow(2, bits) - 1
    const rateRed = this.p.rate
    const holdEvery = rateRed <= 0 ? 1 : Math.max(1, Math.floor(1 / (1 - rateRed + 0.001)))
    const drive = this.p.drive
    const dc = this.p.offset
    const mix = this.p.mix

    for (let ch = 0; ch < out.length; ch++) {
      const ic = inp[ch] || inp[0]
      const oc = out[ch]
      if (!ic || !oc) continue
      let held = ch === 0 ? this.heldL : this.heldR
      let counter = this.holdCounter

      for (let i = 0; i < ic.length; i++) {
        if (counter === 0) {
          let s = ic[i] * drive + dc
          // quantize
          s = Math.round(s * levels) / levels
          held = s
        }
        counter++
        if (counter >= holdEvery) counter = 0
        // dry/wet
        oc[i] = ic[i] * (1 - mix) + held * mix
      }

      if (ch === 0) {
        this.heldL = held
        this.holdCounter = counter
      } else {
        this.heldR = held
      }
    }
  }
}
