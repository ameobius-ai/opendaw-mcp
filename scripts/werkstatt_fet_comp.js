// @werkstatt fet_comp 1 1
// @label FET Comp
// FET compressor (Urei 1176 style)
// Field-effect transistor gain reduction element with fast attack/release
// Signature: lightning-fast transient grabbing, aggressive character
// @param input 0.5 linear      // input gain (drives threshold + character)
// @param attack 0.3 linear     // attack time (0.02 to 4 ms — very fast)
// @param release 0.5 linear    // release time (50 to 1100 ms)
// @param ratio 0.5 linear      // ratio (4:1 or 12:1 selectable via mode)
// @param mode 0.0 linear       // 0=4:1, 1=8:1, 2=12:1, 3=20:1 (all buttons in)
// @param output 0.5 linear     // output gain (-12 to +24 dB)
// @param mix 1.0 linear        // wet/dry mix (0=dry, 1=full compressed)

class FetComp {
    constructor(sampleRate, blockSize) {
        this.sampleRate = sampleRate;
        this.blockSize = blockSize;

        // FET gain reduction element
        this.env = 0;
        this.gainReduction = 1;

        // 1176-style program-dependent release (faster on loud peaks)
        this.peakHold = 0;

        // DC blocker
        this.dcIn = 0;
        this.dcOut = 0;

        // Transformer saturation on output (1176 output transformer)
        this.transformerState = 0;
    }

    processAudio(inputs, outputs, parameters) {
        const input = inputs[0];
        const output = outputs[0];
        const numCh = output.length;
        const numFrames = output[0].length;

        const inputRaw = parameters.input[0] || 0.5;
        const attackRaw = parameters.attack[0] || 0.3;
        const releaseRaw = parameters.release[0] || 0.5;
        const ratioRaw = parameters.ratio[0] || 0.5;
        const modeRaw = parameters.mode[0] || 0;
        const outputRaw = parameters.output[0] || 0.5;
        const mix = parameters.mix[0] || 1.0;

        // Input gain: 0 to +30 dB
        const inputGainDb = inputRaw * 30;
        const inputGain = Math.pow(10, inputGainDb / 20);

        // 1176 threshold is fixed around -8 dB (depends on input gain)
        // Higher input gain = more compression
        const thresholdDb = -8 - inputRaw * 10;
        const thresholdLinear = Math.pow(10, thresholdDb / 20);

        // Ratio modes: 4:1, 8:1, 12:1, 20:1 (all buttons in)
        const modeIdx = Math.floor(modeRaw * 3.99);
        const ratios = [4, 8, 12, 20];
        const baseRatio = ratios[modeIdx];
        // Blend ratio with the ratio param for fine control
        const ratio = baseRatio * (0.5 + ratioRaw);

        // Attack: 0.02 to 4 ms (1176 is famous for fast attack)
        const attackMs = 0.02 + attackRaw * 3.98;
        const attackCoeff = Math.exp(-1 / (this.sampleRate * attackMs * 0.001));

        // Release: 50 to 1100 ms
        const releaseMs = 50 + releaseRaw * 1050;
        const releaseCoeff = Math.exp(-1 / (this.sampleRate * releaseMs * 0.001));

        // Output gain: -12 to +24 dB
        const outputGainDb = -12 + outputRaw * 36;
        const outputGain = Math.pow(10, outputGainDb / 20);

        for (let i = 0; i < numFrames; i++) {
            let inSample = 0;
            if (numCh > 0 && input[0]) inSample = input[0][i];
            if (numCh > 1 && input[1]) inSample = (inSample + input[1][i]) * 0.5;

            // Apply input gain
            const gained = inSample * inputGain;

            // FET envelope detector (peak, very fast)
            const absInput = Math.abs(gained);

            // 1176 uses peak detection with program-dependent release
            if (absInput > this.env) {
                this.env = attackCoeff * this.env + (1 - attackCoeff) * absInput;
                this.peakHold = 0;
            } else {
                // Program-dependent: faster release after loud peaks
                const progRelease = releaseCoeff + (1 - releaseCoeff) * Math.min(this.peakHold / 100, 0.5);
                this.env = progRelease * this.env + (1 - progRelease) * absInput;
                this.peakHold++;
            }

            // Gain reduction
            let compGain = 1;
            if (this.env > thresholdLinear) {
                const envDb = 20 * Math.log10(Math.max(this.env, 1e-10));
                const overDb = envDb - thresholdDb;
                // 1176 has a soft knee near threshold
                const kneeDb = 4;
                let reducedDb;
                if (overDb < kneeDb) {
                    reducedDb = overDb * (1 - 1/ratio) * (overDb / (2 * kneeDb));
                } else {
                    reducedDb = (overDb - kneeDb/2) * (1 - 1/ratio);
                }
                compGain = Math.pow(10, -reducedDb / 20);
            }

            // Smooth gain (FET responds fast but not instant)
            this.gainReduction = this.gainReduction * 0.5 + compGain * 0.5;

            // Apply compression
            const compressed = gained * this.gainReduction;

            // Output transformer saturation (subtle 3rd harmonic)
            const transformerDrive = compressed * (1 + 0.5);
            const transformerOut = transformerDrive - 0.03 * transformerDrive * transformerDrive * transformerDrive * Math.sign(transformerDrive);
            const transformerNorm = transformerOut / 1.15;

            // Output gain
            const outSample = transformerNorm * outputGain;

            // Mix
            const mixed = inSample * (1 - mix) + outSample * mix;

            // DC blocker
            const dcOut = mixed - this.dcIn + 0.995 * this.dcOut;
            this.dcIn = mixed;
            this.dcOut = dcOut;

            for (let c = 0; c < numCh; c++) {
                output[c][i] = dcOut;
            }
        }
    }

    paramChanged(name, value) {
    }
}
