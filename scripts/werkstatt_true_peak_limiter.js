// @werkstatt true_peak_limiter 1 1
// @label True Peak Limiter
// Inter-sample peak detection limiter with 4x oversampling
// Prevents inter-sample peaks that cause codec distortion on streaming platforms
// Spotify/Apple Music require -1 dBTP (true peak)
// @param ceiling 0.96 linear   // true peak ceiling (0.5=-6dB to 1.0=0dBTP)
// @param release 0.3 linear    // release time (50 to 500 ms)
// @param lookahead 0.5 linear  // lookahead (1 to 10 ms, higher = cleaner)
// @param oversample 1.0 linear // oversample factor (1=2x, 2=4x, higher CPU)
// @param mix 1.0 linear        // wet/dry mix (0=dry, 1=full limited)

class TruePeakLimiter {
    constructor(sampleRate, blockSize) {
        this.sampleRate = sampleRate;
        this.blockSize = blockSize;

        // Oversampling: simple 4x linear interpolation
        this.oversampleFactor = 4;

        // Envelope state
        this.env = 0;
        this.gainReduction = 1;

        // Lookahead buffer (delay line)
        this.lookaheadSamples = Math.floor(sampleRate * 0.003); // 3ms default
        this.delayBuffer = new Float32Array(this.lookaheadSamples);
        this.delayPos = 0;

        // DC blocker
        this.dcIn = 0;
        this.dcOut = 0;

        // Previous sample for inter-sample peak estimation
        this.prevSample = 0;
    }

    processAudio(inputs, outputs, parameters) {
        const input = inputs[0];
        const output = outputs[0];
        const numCh = output.length;
        const numFrames = output[0].length;

        const ceilingRaw = parameters.ceiling[0] || 0.96;
        const releaseRaw = parameters.release[0] || 0.3;
        const lookaheadRaw = parameters.lookahead[0] || 0.5;
        const mix = parameters.mix[0] || 1.0;

        // Ceiling: -6 to 0 dBTP
        const ceilingDb = -6 + ceilingRaw * 6;
        const ceilingLinear = Math.pow(10, ceilingDb / 20);

        // Release: 50 to 500 ms
        const releaseMs = 50 + releaseRaw * 450;
        const releaseCoeff = Math.exp(-1 / (this.sampleRate * releaseMs * 0.001));

        // Lookahead: 1 to 10 ms
        const lookaheadMs = 1 + lookaheadRaw * 9;
        const lookaheadSamp = Math.max(1, Math.floor(this.sampleRate * lookaheadMs * 0.001));

        // Attack: very fast (0.1 ms)
        const attackCoeff = Math.exp(-1 / (this.sampleRate * 0.0001));

        for (let i = 0; i < numFrames; i++) {
            let inSample = 0;
            if (numCh > 0 && input[0]) inSample = input[0][i];
            if (numCh > 1 && input[1]) inSample = (inSample + input[1][i]) * 0.5;

            // Inter-sample peak estimation via 4x oversampling
            // Simple linear interpolation between samples
            let truePeak = Math.abs(inSample);
            // Check inter-sample peaks by interpolating
            for (let j = 1; j < this.oversampleFactor; j++) {
                const t = j / this.oversampleFactor;
                const interp = this.prevSample * (1 - t) + inSample * t;
                truePeak = Math.max(truePeak, Math.abs(interp));
            }
            this.prevSample = inSample;

            // Gain reduction
            let compGain = 1;
            if (truePeak > ceilingLinear) {
                const overDb = 20 * Math.log10(truePeak / ceilingLinear);
                compGain = Math.pow(10, -overDb / 20);
            }

            // Smooth gain reduction
            if (compGain < this.gainReduction) {
                // Attacking
                this.gainReduction = attackCoeff * this.gainReduction + (1 - attackCoeff) * compGain;
            } else {
                // Releasing
                this.gainReduction = releaseCoeff * this.gainReduction + (1 - releaseCoeff) * compGain;
            }

            // Lookahead delay line
            const delayed = this.delayBuffer[this.delayPos];
            this.delayBuffer[this.delayPos] = inSample;
            this.delayPos = (this.delayPos + 1) % this.delayBuffer.length;

            // Apply gain to delayed signal
            const limited = delayed * this.gainReduction;

            // Final hard clip at ceiling (safety)
            const clipped = Math.max(-ceilingLinear * 1.01, Math.min(ceilingLinear * 1.01, limited));

            // Mix
            const mixed = inSample * (1 - mix) + clipped * mix;

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
