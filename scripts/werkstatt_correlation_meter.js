// @werkstatt correlation_meter 1 1
// @label Correlation Meter (Stereo Phase)
// Real-time stereo correlation measurement
// Reports correlation coefficient (-1 to +1), width estimate, and mono compatibility
// +1 = mono (perfectly correlated), 0 = wide stereo, -1 = out of phase
// Also reports left/right level balance and peak correlation history
// @param correlation 0.0 linear  // Current correlation (-1 to +1, read-only)
// @param width 0.0 linear        // Stereo width estimate (0=mono, 1=narrow, 2=wide, read-only)
// @param mono_compat 0.0 linear  // Mono compatibility score (0-1, 1=perfect, read-only)
// @param balance 0.0 linear      // L/R balance (-1=full L, 0=center, +1=full R, read-only)
// @param peak_corr 0.0 linear    // Peak negative correlation (worst phase moment, read-only)
// @param mix 0.0 linear          // Not used (meter only, no audio modification)

class CorrelationMeter {
    constructor(sampleRate, blockSize) {
        this.sampleRate = sampleRate;
        this.blockSize = blockSize;

        // Running sums for correlation calculation
        // correlation = sum(L*R) / sqrt(sum(L²) * sum(R²))
        this.sumLR = 0;
        this.sumLL = 0;
        this.sumRR = 0;

        // Window size for averaging (about 1 second)
        this.windowSize = Math.floor(sampleRate * 1.0);
        this.lrBuffer = new Float32Array(this.windowSize);
        this.llBuffer = new Float32Array(this.windowSize);
        this.rrBuffer = new Float32Array(this.windowSize);
        this.bufferPos = 0;
        this.bufferFilled = false;

        // L/R level tracking
        this.leftPeak = 0;
        this.rightPeak = 0;
        this.leftRms = 0;
        this.rightRms = 0;
        this.leftRmsCount = 0;
        this.rightRmsCount = 0;

        // Peak negative correlation tracking
        this.peakNegativeCorr = 1.0;

        // Short-term correlation history (for width estimation)
        this.correlationHistory = new Float32Array(50); // 50 samples of history
        this.historyPos = 0;
    }

    processAudio(inputs, outputs, parameters) {
        const input = inputs[0];
        const output = outputs[0];
        const numCh = output.length;
        const numFrames = output[0].length;

        for (let i = 0; i < numFrames; i++) {
            const left = (input[0] && numCh > 0) ? input[0][i] : 0;
            const right = (input[1] && numCh > 1) ? input[1][i] : 0;

            // Track peaks
            if (Math.abs(left) > this.leftPeak) this.leftPeak = Math.abs(left);
            if (Math.abs(right) > this.rightPeak) this.rightPeak = Math.abs(right);

            // Accumulate RMS
            this.leftRms += left * left;
            this.rightRms += right * right;
            this.leftRmsCount++;

            // Store in circular buffer
            this.lrBuffer[this.bufferPos] = left * right;
            this.llBuffer[this.bufferPos] = left * left;
            this.rrBuffer[this.bufferPos] = right * right;
            this.bufferPos = (this.bufferPos + 1) % this.windowSize;
            if (this.bufferPos === 0) this.bufferFilled = true;

            // Pass through (meter only)
            for (let ch = 0; ch < numCh; ch++) {
                if (input[ch]) output[ch][i] = input[ch][i];
            }
        }

        // Update correlation from windowed buffer
        const effectiveLen = this.bufferFilled ? this.windowSize : this.bufferPos;
        if (effectiveLen > 0) {
            let sumLR = 0, sumLL = 0, sumRR = 0;
            for (let j = 0; j < effectiveLen; j++) {
                sumLR += this.lrBuffer[j];
                sumLL += this.llBuffer[j];
                sumRR += this.rrBuffer[j];
            }

            const denom = Math.sqrt(Math.max(sumLL * sumRR, 1e-12));
            const corr = sumLR / denom;

            // Clamp to -1..+1
            this.currentCorrelation = Math.max(-1, Math.min(1, corr));

            // Track peak negative correlation
            if (this.currentCorrelation < this.peakNegativeCorr) {
                this.peakNegativeCorr = this.currentCorrelation;
            }

            // Store in history for width estimation
            this.correlationHistory[this.historyPos] = this.currentCorrelation;
            this.historyPos = (this.historyPos + 1) % this.correlationHistory.length;
        }
    }

    paramChanged(name, value) {
        // Parameters are read-only outputs
    }

    // Current correlation coefficient (-1 to +1)
    getCorrelation() {
        return this.currentCorrelation || 0;
    }

    // Stereo width estimate (0=mono, 1=narrow, 2=wide)
    getWidth() {
        const c = this.getCorrelation();
        // Width = 1 - correlation (roughly)
        // +1 corr → 0 width (mono), 0 corr → 1 width (stereo), -1 corr → 2 width (out of phase)
        return Math.max(0, 1 - c);
    }

    // Mono compatibility score (0-1, 1=perfect mono compatibility)
    getMonoCompatibility() {
        const c = this.getCorrelation();
        // Map correlation to 0-1 score
        // +1 → 1.0 (perfect), 0 → 0.5 (ok), -1 → 0.0 (terrible)
        return Math.max(0, (c + 1) / 2);
    }

    // L/R balance (-1=full L, 0=center, +1=full R)
    getBalance() {
        if (this.leftRmsCount === 0) return 0;
        const lRms = Math.sqrt(this.leftRms / this.leftRmsCount);
        const rRms = Math.sqrt(this.rightRms / this.leftRmsCount);
        const total = lRms + rRms;
        if (total < 1e-12) return 0;
        return (rRms - lRms) / total;
    }

    // Peak negative correlation (worst phase moment)
    getPeakNegativeCorrelation() {
        return this.peakNegativeCorr;
    }
}
