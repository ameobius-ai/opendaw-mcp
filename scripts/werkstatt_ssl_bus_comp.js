// @werkstatt ssl_bus_comp 1 1
// @label SSL Bus Comp
// SSL G-series bus compressor (the glue compressor)
// VCA-based with smooth gain reduction, signature mix bus sound
// Known for "gluing" a mix together — subtle but transformative
// @param threshold 0.5 linear  // threshold (-30 to 0 dB)
// @param ratio 0.3 linear      // ratio (2:1, 4:1, 10:1)
// @param attack 0.3 linear     // attack (0.1, 0.3, 1, 3, 10, 30 ms — 1176-style steps)
// @param release 0.3 linear    // release (0.1, 0.3, 1, 3, 10 sec — auto-release mode)
// @param makeup 0.5 linear     // makeup gain (0 to +24 dB)
// @param mix 1.0 linear        // wet/dry mix (0=dry, 1=full compressed)
// @param auto_release 1.0 bool  // auto-release mode (SSL signature feature)

class SslBusComp {
    constructor(sampleRate, blockSize) {
        this.sampleRate = sampleRate;
        this.blockSize = blockSize;

        // RMS detector (SSL uses RMS, not peak)
        this.rmsWindow = new Float32Array(256);
        this.rmsPos = 0;
        this.rmsSum = 0;

        // Gain reduction state
        this.gainReduction = 1;
        this.env = 0;

        // Auto-release state
        this.compressionHistory = 0;

        // DC blocker
        this.dcIn = 0;
        this.dcOut = 0;
    }

    processAudio(inputs, outputs, parameters) {
        const input = inputs[0];
        const output = outputs[0];
        const numCh = output.length;
        const numFrames = output[0].length;

        const thresholdRaw = parameters.threshold[0] || 0.5;
        const ratioRaw = parameters.ratio[0] || 0.3;
        const attackRaw = parameters.attack[0] || 0.3;
        const releaseRaw = parameters.release[0] || 0.3;
        const makeupRaw = parameters.makeup[0] || 0.5;
        const mix = parameters.mix[0] || 1.0;
        const autoRelease = (parameters.auto_release[0] || 1.0) > 0.5;

        // Threshold: -30 to 0 dB
        const thresholdDb = -30 + thresholdRaw * 30;
        const thresholdLinear = Math.pow(10, thresholdDb / 20);

        // Ratio: 2:1, 4:1, 10:1 (SSL has stepped ratios)
        const ratioSteps = [2, 4, 10];
        const ratioIdx = Math.min(Math.floor(ratioRaw * 3), 2);
        const ratio = ratioSteps[ratioIdx];

        // Attack: SSL stepped (0.1, 0.3, 1, 3, 10, 30 ms)
        const attackSteps = [0.1, 0.3, 1, 3, 10, 30];
        const attackIdx = Math.min(Math.floor(attackRaw * 6), 5);
        const attackMs = attackSteps[attackIdx];
        const attackCoeff = Math.exp(-1 / (this.sampleRate * attackMs * 0.001));

        // Release: SSL stepped (0.1, 0.3, 1, 3, 10 sec)
        const releaseSteps = [0.1, 0.3, 1, 3, 10];
        const releaseIdx = Math.min(Math.floor(releaseRaw * 5), 4);
        const releaseMs = releaseSteps[releaseIdx] * 1000; // convert to ms
        const releaseCoeff = Math.exp(-1 / (this.sampleRate * releaseMs * 0.001));

        // Makeup: 0 to +24 dB
        const makeupDb = makeupRaw * 24;
        const makeupGain = Math.pow(10, makeupDb / 20);

        for (let i = 0; i < numFrames; i++) {
            let inSample = 0;
            if (numCh > 0 && input[0]) inSample = input[0][i];
            if (numCh > 1 && input[1]) inSample = (inSample + input[1][i]) * 0.5;

            // RMS detection (256-sample window)
            const oldSample = this.rmsWindow[this.rmsPos];
            const newSquared = inSample * inSample;
            this.rmsSum = this.rmsSum - oldSample * oldSample + newSquared;
            this.rmsWindow[this.rmsPos] = inSample;
            this.rmsPos = (this.rmsPos + 1) % this.rmsWindow.length;

            const rms = Math.sqrt(Math.max(this.rmsSum / this.rmsWindow.length, 1e-10));

            // Gain reduction
            let compGain = 1;
            if (rms > thresholdLinear) {
                const rmsDb = 20 * Math.log10(rms);
                const overDb = rmsDb - thresholdDb;
                const reducedDb = overDb * (1 - 1 / ratio);
                compGain = Math.pow(10, -reducedDb / 20);
            }

            // Auto-release: SSL's auto mode adjusts release based on compression amount
            let actualReleaseCoeff = releaseCoeff;
            if (autoRelease) {
                // Track average compression
                this.compressionHistory = this.compressionHistory * 0.99 + (1 - compGain) * 0.01;
                // Heavy compression → faster release (program-dependent)
                const speedup = 1 + this.compressionHistory * 3;
                actualReleaseCoeff = Math.pow(releaseCoeff, speedup);
            }

            // Envelope follower
            if (compGain < this.env) {
                // Attacking (gain reducing)
                this.env = attackCoeff * this.env + (1 - attackCoeff) * compGain;
            } else {
                // Releasing (gain recovering)
                this.env = actualReleaseCoeff * this.env + (1 - actualReleaseCoeff) * compGain;
            }

            // Apply compression
            const compressed = inSample * this.env * makeupGain;

            // Mix
            const mixed = inSample * (1 - mix) + compressed * mix;

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
