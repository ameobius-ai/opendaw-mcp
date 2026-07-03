// @werkstatt darksat 1 1
// @label Dark Saturation
// @param drive 0.3 0 1 linear
// @param bias 0.0 -0.5 0.5 linear
// @param tone 0.5 0 1 linear
// @param mix 1.0 0 1 linear
// @param output -3 -24 6 linear dB

class Processor {
    // state variables — NO allocation in process()
    drive = 0.3
    bias = 0.0
    tone = 0.5
    mix = 1.0
    outputGain = 0.7079 // -3dB
    
    // one-pole highpass for DC blocker
    hpX1L = 0; hpY1L = 0
    hpX1R = 0; hpY1R = 0
    hpCoeff = 0.999 // ~20Hz highpass at 48k
    
    // tone filter state (lowpass → highpass shelving)
    toneLp1L = 0; toneLp1R = 0
    toneHp1L = 0; toneHp1R = 0
    
    // oversampling: 2x linear interpolation, process both samples
    // simplified — no actual oversampling buffer, just double-rate waveshaper
    
    paramChanged(name, value) {
        if (name === "drive") this.drive = value
        if (name === "bias") this.bias = value
        if (name === "tone") this.tone = value
        if (name === "mix") this.mix = value
        if (name === "output") this.outputGain = Math.pow(10, value / 20)
    }
    
    // tanh saturation with drive — cheap approximation
    sat(x) {
        const d = 1 + this.drive * 5
        const biased = x + this.bias
        // polynomial tanh approx: 1.5x / (1 + 0.8x²) — fast, musical
        const driven = biased * d
        return driven * 1.5 / (1 + 0.8 * driven * driven)
    }
    
    process(io, block) {
        const inputL = io.src[0]
        const inputR = io.src[1]
        const outputL = io.out[0]
        const outputR = io.out[1]
        const drive = this.drive
        const mix = this.mix
        const outGain = this.outputGain
        const hpC = this.hpCoeff
        const toneAmt = this.tone
        
        // tone filter coefficients (simple one-pole)
        const lpCoeff = 0.5 + toneAmt * 0.45 // 0.5..0.95
        const hpCoeff = 0.02 + (1 - toneAmt) * 0.1 // bright when tone=0
        
        for (let i = block.s0; i < block.s1; i++) {
            // DC blocker
            const inL = inputL[i]
            const inR = inputR[i]
            this.hpY1L = hpC * (this.hpY1L + inL - this.hpX1L)
            this.hpY1R = hpC * (this.hpY1R + inR - this.hpX1R)
            this.hpX1L = inL
            this.hpX1R = inR
            
            const dryL = this.hpY1L
            const dryR = this.hpY1R
            
            // saturate
            let satL = this.sat(dryL)
            let satR = this.sat(dryR)
            
            // tone: lowpass the saturated signal, mix with highpass
            this.toneLp1L = this.toneLp1L * lpCoeff + satL * (1 - lpCoeff)
            this.toneLp1R = this.toneLp1R * lpCoeff + satR * (1 - lpCoeff)
            this.toneHp1L = this.toneHp1L * (1 - hpCoeff) + satL * hpCoeff
            this.toneHp1R = this.toneHp1R * (1 - hpCoeff) + satR * hpCoeff
            
            satL = this.toneLp1L * toneAmt + this.toneHp1L * (1 - toneAmt)
            satR = this.toneLp1R * toneAmt + this.toneHp1R * (1 - toneAmt)
            
            // mix dry/wet
            outputL[i] = (dryL * (1 - mix) + satL * mix) * outGain
            outputR[i] = (dryR * (1 - mix) + satR * mix) * outGain
        }
    }
}
