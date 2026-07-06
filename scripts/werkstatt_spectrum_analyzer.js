// @werkstatt spectrum_analyzer 1 1
// @label Spectrum Analyzer (FFT)
// Real-time FFT spectrum analysis with octave-band readout
// Reports peak frequency, spectral centroid, spectral rolloff, low/mid/high band levels
// Read-only meter — no audio modification
// @param peak_freq 0.0 linear     // Peak frequency in Hz (read-only)
// @param centroid 0.0 linear      // Spectral centroid in Hz (brightness, read-only)
// @param rolloff 0.0 linear       // Spectral rolloff 85% in Hz (read-only)
// @param low_level 0.0 linear     // Low band level 20-250Hz (0-1, read-only)
// @param mid_level 0.0 linear     // Mid band level 250-4000Hz (0-1, read-only)
// @param high_level 0.0 linear    // High band level 4000-20000Hz (0-1, read-only)
// @param crest 0.0 linear         // Crest factor (peak/rms ratio, read-only)
// @param mix 0.0 linear           // Not used (meter only)

class SpectrumAnalyzer {
    constructor(sampleRate, blockSize) {
        this.sampleRate = sampleRate;
        this.blockSize = blockSize;

        // FFT size (power of 2, 2048 = ~43ms at 48kHz)
        this.fftSize = 2048;
        this.halfSize = this.fftSize / 2;

        // Hann window
        this.window = new Float32Array(this.fftSize);
        for (let i = 0; i < this.fftSize; i++) {
            this.window[i] = 0.5 * (1 - Math.cos(2 * Math.PI * i / (this.fftSize - 1)));
        }

        // Input buffer
        this.buffer = new Float32Array(this.fftSize);
        this.bufferPos = 0;

        // FFT workspace (real + imaginary)
        this.real = new Float32Array(this.fftSize);
        this.imag = new Float32Array(this.fftSize);

        // Results
        this.magnitude = new Float32Array(this.halfSize);
        this.peakFreq = 0;
        this.centroid = 0;
        this.rolloff = 0;
        this.lowLevel = 0;
        this.midLevel = 0;
        this.highLevel = 0;

        // Crest factor tracking
        this.peakAmplitude = 0;
        this.rmsSum = 0;
        this.rmsCount = 0;

        // Frequency band boundaries (Hz)
        this.lowMin = 20;
        this.lowMax = 250;
        this.midMin = 250;
        this.midMax = 4000;
        this.highMin = 4000;
        this.highMax = 20000;

        // Analysis interval (every N blocks)
        this.analysisCounter = 0;
        this.analysisInterval = Math.max(1, Math.floor(this.fftSize / blockSize));
    }

    // In-place FFT (Cooley-Tukey radix-2)
    fft(real, imag, n) {
        // Bit reversal
        let j = 0;
        for (let i = 1; i < n; i++) {
            let bit = n >> 1;
            while (j & bit) {
                j ^= bit;
                bit >>= 1;
            }
            j ^= bit;
            if (i < j) {
                const tr = real[i]; real[i] = real[j]; real[j] = tr;
                const ti = imag[i]; imag[i] = imag[j]; imag[j] = ti;
            }
        }

        // Butterfly
        for (let len = 2; len <= n; len <<= 1) {
            const halfLen = len >> 1;
            const angleStep = -2 * Math.PI / len;
            for (let i = 0; i < n; i += len) {
                for (let k = 0; k < halfLen; k++) {
                    const angle = angleStep * k;
                    const cosA = Math.cos(angle);
                    const sinA = Math.sin(angle);
                    const tr = real[i + k + halfLen] * cosA - imag[i + k + halfLen] * sinA;
                    const ti = imag[i + k + halfLen] * cosA + real[i + k + halfLen] * sinA;
                    real[i + k + halfLen] = real[i + k] - tr;
                    imag[i + k + halfLen] = imag[i + k] - ti;
                    real[i + k] += tr;
                    imag[i + k] += ti;
                }
            }
        }
    }

    processAudio(inputs, outputs, parameters) {
        const input = inputs[0];
        const output = outputs[0];
        const numCh = output.length;
        const numFrames = output[0].length;

        for (let i = 0; i < numFrames; i++) {
            // Mono sum for analysis
            let sample = 0;
            for (let ch = 0; ch < numCh; ch++) {
                if (input[ch]) sample += input[ch][i];
            }
            sample /= Math.max(numCh, 1);

            // Track peak and RMS for crest factor
            const absSample = Math.abs(sample);
            if (absSample > this.peakAmplitude) this.peakAmplitude = absSample;
            this.rmsSum += sample * sample;
            this.rmsCount++;

            // Store in circular buffer
            this.buffer[this.bufferPos] = sample;
            this.bufferPos = (this.bufferPos + 1) % this.fftSize;

            // Pass through (meter only)
            for (let ch = 0; ch < numCh; ch++) {
                if (input[ch]) output[ch][i] = input[ch][i];
            }
        }

        // Analyze periodically
        this.analysisCounter++;
        if (this.analysisCounter >= this.analysisInterval) {
            this.analysisCounter = 0;
            this.analyze();
        }
    }

    analyze() {
        // Copy buffer with window
        for (let i = 0; i < this.fftSize; i++) {
            const idx = (this.bufferPos + i) % this.fftSize;
            this.real[i] = this.buffer[idx] * this.window[i];
            this.imag[i] = 0;
        }

        // Run FFT
        this.fft(this.real, this.imag, this.fftSize);

        // Compute magnitude spectrum
        let totalMagnitude = 0;
        let lowSum = 0, midSum = 0, highSum = 0;
        let lowCount = 0, midCount = 0, highCount = 0;
        let weightedSum = 0;
        let peakMag = 0;
        let peakBin = 0;

        for (let k = 0; k < this.halfSize; k++) {
            const mag = Math.sqrt(this.real[k] * this.real[k] + this.imag[k] * this.imag[k]);
            this.magnitude[k] = mag;
            totalMagnitude += mag;

            const freq = k * this.sampleRate / this.fftSize;

            // Spectral centroid weighting
            weightedSum += freq * mag;

            // Track peak
            if (mag > peakMag) {
                peakMag = mag;
                peakBin = k;
            }

            // Band levels
            if (freq >= this.lowMin && freq < this.lowMax) {
                lowSum += mag;
                lowCount++;
            } else if (freq >= this.midMin && freq < this.midMax) {
                midSum += mag;
                midCount++;
            } else if (freq >= this.highMin && freq < this.highMax) {
                highSum += mag;
                highCount++;
            }
        }

        // Peak frequency
        this.peakFreq = peakBin * this.sampleRate / this.fftSize;

        // Spectral centroid (brightness)
        this.centroid = totalMagnitude > 0 ? weightedSum / totalMagnitude : 0;

        // Spectral rolloff (85% of energy)
        let energy85 = totalMagnitude * 0.85;
        let cumulative = 0;
        let rolloffBin = this.halfSize - 1;
        for (let k = 0; k < this.halfSize; k++) {
            cumulative += this.magnitude[k];
            if (cumulative >= energy85) {
                rolloffBin = k;
                break;
            }
        }
        this.rolloff = rolloffBin * this.sampleRate / this.fftSize;

        // Band levels (normalized 0-1)
        this.lowLevel = lowCount > 0 ? (lowSum / lowCount) / 100 : 0;
        this.midLevel = midCount > 0 ? (midSum / midCount) / 100 : 0;
        this.highLevel = highCount > 0 ? (highSum / highCount) / 100 : 0;
    }

    paramChanged(name, value) {
        // Read-only
    }

    getPeakFrequency() { return this.peakFreq; }
    getCentroid() { return this.centroid; }
    getRolloff() { return this.rolloff; }
    getLowLevel() { return Math.min(1, this.lowLevel); }
    getMidLevel() { return Math.min(1, this.midLevel); }
    getHighLevel() { return Math.min(1, this.highLevel); }

    getCrestFactor() {
        if (this.rmsCount === 0) return 0;
        const rms = Math.sqrt(this.rmsSum / this.rmsCount);
        if (rms < 1e-12) return 0;
        return this.peakAmplitude / rms;
    }
}
