// @werkstatt coldfold 1 1
// @label Cold Fold Distortion
// @param drive 0.5 0 2 linear
// @param fold 0.3 0 1 linear
// @param crush 0 0 1 linear
// @param slew 1.0 0 1 linear
// @param mix 0.8 0 1 linear

class Processor {
    drive = 0.5
    fold = 0.3
    crush = 0
    slew = 1.0
    mix = 0.8
    
    // slew filter state
    slewL = 0; slewR = 0
    // last crushed value
    lastL = 0; lastR = 0
    
    paramChanged(name, value) {
        if (name === "drive") this.drive = value
        if (name === "fold") this.fold = value
        if (name === "crush") this.crush = value
        if (name === "slew") this.slew = value
        if (name === "mix") this.mix = value
    }
    
    process(io, block) {
        const inputL = io.src[0]
        const inputR = io.src[1]
        const outputL = io.out[0]
        const outputR = io.out[1]
        const drive = 1 + this.drive * 3
        const foldAmt = this.fold * 4 + 1 // 1..5
        const crushBits = Math.max(1, Math.floor(16 - this.crush * 15))
        const crushLevels = Math.pow(2, crushBits)
        const crushStep = 2 / crushLevels
        const slewAmt = this.slew
        const mix = this.mix
        
        for (let i = block.s0; i < block.s1; i++) {
            let xL = inputL[i] * drive
            let xR = inputR[i] * drive
            
            // wavefolding — mirrors signal at thresholds
            // tanh-based fold: signal wraps around instead of clipping
            while (xL > 1) xL = 2 - xL
            while (xL < -1) xL = -2 - xL
            while (xR > 1) xR = 2 - xR
            while (xR < -1) xR = -2 - xR
            
            // additional fold iterations for harmonic richness
            const foldIter = Math.floor(foldAmt)
            for (let f = 0; f < foldIter; f++) {
                if (xL > 0.7) xL = 1.4 - xL
                else if (xL < -0.7) xL = -1.4 - xL
                if (xR > 0.7) xR = 1.4 - xR
                else if (xR < -0.7) xR = -1.4 - xR
            }
            
            // bitcrush — quantize to discrete levels
            if (this.crush > 0) {
                xL = Math.round(xL / crushStep) * crushStep
                xR = Math.round(xR / crushStep) * crushStep
            }
            
            // slew limiting — sample rate reduction feel
            const slewCoeff = slewAmt * 0.8
            this.slewL = this.slewL * slewCoeff + xL * (1 - slewCoeff)
            this.slewR = this.slewR * slewCoeff + xR * (1 - slewCoeff)
            xL = slewAmt < 1 ? this.slewL : xL
            xR = slewAmt < 1 ? this.slewR : xR
            
            // hard clip safety
            xL = xL > 1 ? 1 : (xL < -1 ? -1 : xL)
            xR = xR > 1 ? 1 : (xR < -1 ? -1 : xR)
            
            outputL[i] = inputL[i] * (1 - mix) + xL * mix
            outputR[i] = inputR[i] * (1 - mix) + xR * mix
        }
    }
}
