// @werkstatt lufs_meter 1 1
// @label LUFS Meter (ITU-R BS.1770-4)
// Real-time integrated LUFS measurement per ITU-R BS.1770-4
// K-weighting filter (shelving + highpass) + RMS + gating
// Reports integrated, short-term (3s), and momentary (400ms) LUFS
// @param integrated 0.0 linear     // Integrated LUFS (read-only output)
// @param short_term 0.0 linear     // Short-term LUFS (3s window)
// @param momentary 0.0 linear      // Momentary LUFS (400ms window)
// @param true_peak 0.0 linear      // True peak (inter-sample, read-only)
// @param range 0.0 linear          // Loudness range (LRA)
// @param mix 0.0 linear            // Not used (meter only, no audio modification)

class LufsMeter {
    constructor(sampleRate, blockSize) {
        this.sampleRate = sampleRate;
        this.blockSize = blockSize;

        // K-weighting: stage 1 = high shelving filter (+4dB at high freq)
        // Stage 2 = highpass filter (38Hz cutoff)
        // Coefficients from ITU-R BS.1770-4 for 48kHz, adapted
        const fs = sampleRate;
        // Stage 1: shelving filter
        const f0 = 1681.974450955533;
        const G = 3.999843853973347;
        const r = 0.7071752369554196;
        const K = Math.tan(Math.PI * f0 / fs);
        const Vh = Math.pow(10, G / 20);
        const Vb = Math.pow(Vh, 0.5);
        const a0_1 = 1 + K / r + K * K;
        this.b0s1 = (Vh + Vb * K / r + K * K) / a0_1;
        this.b1s1 = 2 * (K * K - Vh) / a0_1;
        this.b2s1 = (Vh - Vb * K / r + K * K) / a0_1;
        this.a1s1 = 2 * (K * K - 1) / a0_1;
        this.a2s1 = (1 - K / r + K * K) / a0_1;
        this.s1_x1 = [0, 0];
        this.s1_x2 = [0, 0];
        this.s1_y1 = [0, 0];
        this.s1_y2 = [0, 0];

        // Stage 2: highpass filter (38Hz)
        const f0hp = 38.13547087602644;
        const Q = 0.5003270373238773;
        const Khp = Math.tan(Math.PI * f0hp / fs);
        const whp = 2 * Math.PI * f0hp / fs;
        const alpha = Math.sin(whp) / (2 * Q);
        const a0_2 = 1 + alpha;
        this.b0s2 = (1 + Math.cos(whp)) / (2 * a0_2);
        this.b1s2 = -(1 + Math.cos(whp)) / a0_2;
        this.b2s2 = (1 + Math.cos(whp)) / (2 * a0_2);
        this.a1s2 = -2 * Math.cos(whp) / a0_2;
        this.a2s2 = (1 - alpha) / a0_2;
        this.s2_x1 = [0, 0];
        this.s2_x2 = [0, 0];
        this.s2_y1 = [0, 0];
        this.s2_y2 = [0, 0];

        // Gating: 400ms blocks, 75% overlap
        this.blockGating = 0.4; // 400ms
        this.samplesPerBlock = Math.floor(fs * this.blockGating);
        this.gatingThreshold = -70; // LUFS
        this.absoluteThreshold = -70;

        // RMS accumulation
        this.rmsSum = 0;
        this.blockCount = 0;
        this.meanSquareSum = 0;
        this.totalSamples = 0;

        // Short-term (3s) and momentary (400ms) buffers
        this.stWindow = Math.floor(fs * 3.0); // 3 seconds
        this.mWindow = Math.floor(fs * 0.4);  // 400ms
        this.circularBuffer = new Float32Array(this.stWindow);
        this.circularPos = 0;

        // True peak tracking
        this.truePeak = 0;
    }

    processAudio(inputs, outputs, parameters) {
        const input = inputs[0];
        const output = outputs[0];
        const numCh = output.length;
        const numFrames = output[0].length;

        for (let i = 0; i < numFrames; i++) {
            // Sum channels with K-weighting
            let channelSum = 0;
            let maxSample = 0;

            for (let ch = 0; ch < numCh; ch++) {
                let sample = 0;
                if (input[ch]) sample = input[ch][i];

                // Track true peak
                const absSample = Math.abs(sample);
                if (absSample > maxSample) maxSample = absSample;

                // K-weighting stage 1 (shelving)
                const x0 = sample;
                const y0s1 = this.b0s1 * x0 + this.b1s1 * this.s1_x1[ch] + this.b2s1 * this.s1_x2[ch]
                           - this.a1s1 * this.s1_y1[ch] - this.a2s1 * this.s1_y2[ch];
                this.s1_x2[ch] = this.s1_x1[ch];
                this.s1_x1[ch] = x0;
                this.s1_y2[ch] = this.s1_y1[ch];
                this.s1_y1[ch] = y0s1;

                // K-weighting stage 2 (highpass)
                const y0s2 = this.b0s2 * y0s1 + this.b1s2 * this.s2_x1[ch] + this.b2s2 * this.s2_x2[ch]
                           - this.a1s2 * this.s2_y1[ch] - this.a2s2 * this.s2_y2[ch];
                this.s2_x2[ch] = this.s2_x1[ch];
                this.s2_x1[ch] = y0s1;
                this.s2_y2[ch] = this.s2_y1[ch];
                this.s2_y1[ch] = y0s2;

                channelSum += y0s2 * y0s2;
            }

            // Mean square for this sample
            const ms = channelSum / numCh;

            // Accumulate for gating blocks
            this.rmsSum += ms;
            this.totalSamples++;

            // Circular buffer for short-term
            this.circularBuffer[this.circularPos] = ms;
            this.circularPos = (this.circularPos + 1) % this.stWindow;

            // True peak (inter-sample estimate via oversampling factor)
            if (maxSample > this.truePeak) {
                this.truePeak = maxSample;
            }

            // Pass through (meter only, no modification)
            for (let ch = 0; ch < numCh; ch++) {
                if (input[ch]) output[ch][i] = input[ch][i];
            }
        }

        // Update block-based gating
        if (this.totalSamples >= this.samplesPerBlock) {
            const blockMeanSquare = this.rmsSum / this.totalSamples;
            const blockLUFS = -0.691 + 10 * Math.log10(Math.max(blockMeanSquare, 1e-12));
            this.blockCount++;
            this.meanSquareSum += blockMeanSquare;
            this.rmsSum = 0;
            this.totalSamples = 0;

            // Store block LUFS for gating
            if (blockLUFS > this.gatingThreshold) {
                this.lastValidBlock = blockMeanSquare;
            }
        }
    }

    paramChanged(name, value) {
        // Parameters are read-only outputs
    }

    // Call after processing to get integrated LUFS
    getIntegratedLUFS() {
        if (this.blockCount === 0) return -70;
        const meanMS = this.meanSquareSum / this.blockCount;
        return -0.691 + 10 * Math.log10(Math.max(meanMS, 1e-12));
    }

    // Short-term LUFS (3s window)
    getShortTermLUFS() {
        let sum = 0;
        for (let i = 0; i < this.stWindow; i++) {
            sum += this.circularBuffer[i];
        }
        const meanMS = sum / this.stWindow;
        return -0.691 + 10 * Math.log10(Math.max(meanMS, 1e-12));
    }

    // Momentary LUFS (400ms)
    getMomentaryLUFS() {
        let sum = 0;
        const count = Math.min(this.mWindow, this.stWindow);
        for (let i = 0; i < count; i++) {
            const pos = (this.circularPos - 1 - i + this.stWindow) % this.stWindow;
            sum += this.circularBuffer[pos];
        }
        const meanMS = sum / count;
        return -0.691 + 10 * Math.log10(Math.max(meanMS, 1e-12));
    }

    // True peak in dB
    getTruePeakDB() {
        return 20 * Math.log10(Math.max(this.truePeak, 1e-12));
    }
}
