// @werkstatt nyquist_comp 1 1
// @label Nyquist Comp
// Parallel/New York compression
// Blends dry signal with a heavily compressed parallel path
// Increases perceived loudness and detail without killing transients
// @param threshold 0.4 linear   // threshold for compressed path (-60 to 0 dB)
// @param ratio 0.7 linear       // compression ratio (1:1 to 20:1)
// @param attack 0.1 linear      // attack time (0.1 to 50 ms)
// @param release 0.3 linear     // release time (50 to 500 ms)
// @param blend 0.5 linear       // parallel blend (0=dry only, 1=full compressed)
// @param makeup 0.5 linear      // makeup gain on compressed path (-12 to +24 dB)

class NyquistComp {
    constructor(sampleRate, blockSize) {
        this.sampleRate = sampleRate;
        this.blockSize = blockSize;

        // Envelope detector for compressed path
        this.env = 0;

        // Peak detector for gain reduction smoothing
        this.gainReduction = 0;

        // DC blocker on output
        this.dcIn = 0;
        this.dcOut = 0;
    }

    processAudio(inputs, outputs, parameters) {
        const input = inputs[0];
        const output = outputs[0];
        const numCh = output.length;
        const numFrames = output[0].length;

        // Map parameters
        const thresholdRaw = parameters.threshold[0] || 0.4;
        const ratioRaw = parameters.ratio[0] || 0.7;
        const attackRaw = parameters.attack[0] || 0.1;
        const releaseRaw = parameters.release[0] || 0.3;
        const blend = parameters.blend[0] || 0.5;
        const makeupRaw = parameters.makeup[0] || 0.5;

        // Threshold: -60 to 0 dB
        const thresholdDb = -60 + thresholdRaw * 60;
        const thresholdLinear = Math.pow(10, thresholdDb / 20);

        // Ratio: 1:1 to 20:1
        const ratio = 1 + ratioRaw * 19;

        // Attack: 0.1 to 50 ms
        const attackMs = 0.1 + attackRaw * 49.9;
        const attackCoeff = Math.exp(-1 / (this.sampleRate * attackMs * 0.001));

        // Release: 50 to 500 ms
        const releaseMs = 50 + releaseRaw * 450;
        const releaseCoeff = Math.exp(-1 / (this.sampleRate * releaseMs * 0.001));

        // Makeup: -12 to +24 dB
        const makeupDb = -12 + makeupRaw * 36;
        const makeupGain = Math.pow(10, makeupDb / 20);

        for (let i = 0; i < numFrames; i++) {
            let inSample = 0;
            if (numCh > 0 && input[0]) inSample = input[0][i];
            if (numCh > 1 && input[1]) inSample = (inSample + input[1][i]) * 0.5;

            // Envelope detection (peak detector)
            const absInput = Math.abs(inSample);
            if (absInput > this.env) {
                this.env = attackCoeff * this.env + (1 - attackCoeff) * absInput;
            } else {
                this.env = releaseCoeff * this.env + (1 - releaseCoeff) * absInput;
            }

            // Gain computation
            let gainReductionLinear = 1;
            if (this.env > thresholdLinear) {
                const envDb = 20 * Math.log10(Math.max(this.env, 1e-10));
                const overDb = envDb - thresholdDb;
                const reducedDb = overDb / ratio;
                gainReductionLinear = Math.pow(10, -(overDb - reducedDb) / 20);
            }

            // Smooth gain reduction
            this.gainReduction = this.gainReduction * 0.99 + gainReductionLinear * 0.01;

            // Compressed path
            const compressed = inSample * this.gainReduction * makeupGain;

            // Parallel blend: dry + compressed
            const mixed = inSample * (1 - blend) + compressed * blend;

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
