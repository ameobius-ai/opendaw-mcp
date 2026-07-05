// @werkstatt spectral_enhancer 1 1
// Spectral enhancer — high-frequency sheen and "air" boost via STFT.
// Boosts magnitude above a crossover frequency, adds harmonic excitement
// by emphasizing spectral peaks, and applies gentle transient enhancement
// via frame-to-frame magnitude delta detection.
//
// @param crossover 4000 1000 16000 exp — crossover frequency (Hz) above which to enhance
// @param air 2 0 6 linear — boost amount (dB scale factor, 1=neutral, 2=+6dB sheen)
// @param sparkle 0.3 0 1 unipolar — spectral peak emphasis (0=off, 1=max peak sharpening)
// @param transients 0.4 0 1 unipolar — transient enhancement via magnitude delta
// @param width 0 0 1 unipolar — stereo widening applied to enhanced band only
// @param mix 1 0 1 unipolar — dry/wet blend
// @param output 0 -24 6 decibel — output gain

class Processor {
    constructor({sampleRate, blockSize}) {
        this.sampleRate = sampleRate;
        this.blockSize = blockSize;
        this.fftSize = 2048;
        this.hopSize = blockSize;
        this.halfSize = this.fftSize / 2;

        // Input ring buffer (interleaved stereo → mono analysis)
        this.inBufL = new Float32Array(this.fftSize);
        this.inBufR = new Float32Array(this.fftSize);
        this.inPos = 0;

        // Output overlap-add
        this.outBufL = new Float32Array(this.fftSize);
        this.outBufR = new Float32Array(this.fftSize);
        this.outPos = 0;

        // Hann window
        this.window = new Float32Array(this.fftSize);
        for (let i = 0; i < this.fftSize; i++) {
            this.window[i] = 0.5 * (1 - Math.cos(2 * Math.PI * i / (this.fftSize - 1)));
        }

        // Window normalization for overlap-add
        this.winNorm = 0;
        for (let i = 0; i < this.fftSize; i++) this.winNorm += this.window[i] * this.window[i];
        this.winNorm = this.winNorm / this.hopSize;

        // Previous magnitude frames for transient detection
        this.prevMagL = new Float32Array(this.halfSize);
        this.prevMagR = new Float32Array(this.halfSize);

        // FFT buffers
        this.real = new Float32Array(this.fftSize);
        this.imag = new Float32Array(this.fftSize);

        this.p = {
            crossover: 4000, air: 2, sparkle: 0.3,
            transients: 0.4, width: 0, mix: 1, output: 0
        };
    }

    paramChanged(name, value) {
        this.p[name] = value;
    }

    // In-place radix-2 Cooley-Tukey FFT
    _fft(real, imag, inverse) {
        const n = real.length;
        // Bit reversal
        for (let i = 1, j = 0; i < n; i++) {
            let bit = n >> 1;
            for (; j & bit; bit >>= 1) j ^= bit;
            j ^= bit;
            if (i < j) {
                let tr = real[i]; real[i] = real[j]; real[j] = tr;
                let ti = imag[i]; imag[i] = imag[j]; imag[j] = ti;
            }
        }
        // Butterfly
        for (let len = 2; len <= n; len <<= 1) {
            const ang = (inverse ? 2 : -2) * Math.PI / len;
            const wR = Math.cos(ang), wI = Math.sin(ang);
            for (let i = 0; i < n; i += len) {
                let cR = 1, cI = 0;
                for (let j = 0; j < len / 2; j++) {
                    const aR = real[i + j], aI = imag[i + j];
                    const bR = real[i + j + len / 2], bI = imag[i + j + len / 2];
                    const tR = bR * cR - bI * cI;
                    const tI = bR * cI + bI * cR;
                    real[i + j] = aR + tR; imag[i + j] = aI + tI;
                    real[i + j + len / 2] = aR - tR; imag[i + j + len / 2] = aI - tI;
                    const nR = cR * wR - cI * wI;
                    cI = cR * wI + cI * wR;
                    cR = nR;
                }
            }
        }
        if (inverse) {
            for (let i = 0; i < n; i++) { real[i] /= n; imag[i] /= n; }
        }
    }

    processAudio(inputs, outputs) {
        const input = inputs[0];
        const output = outputs[0];
        if (!input || !output) return;

        const numCh = Math.min(input.length, output.length);
        const og = Math.pow(10, this.p.output / 20);
        const binFreq = this.sampleRate / this.fftSize;
        const crossBin = Math.max(1, Math.min(this.halfSize - 1, Math.round(this.p.crossover / binFreq)));
        const airGain = this.p.air;
        const sparkAmt = this.p.sparkle;
        const transAmt = this.p.transients;
        const widthAmt = this.p.width;
        const mixAmt = this.p.mix;

        for (let ch = 0; ch < numCh; ch++) {
            const inCh = input[ch] || input[0];
            const outCh = output[ch];
            const inBuf = ch === 0 ? this.inBufL : this.inBufR;
            const outBuf = ch === 0 ? this.outBufL : this.outBufR;
            const prevMag = ch === 0 ? this.prevMagL : this.prevMagR;

            // Write input to ring buffer
            for (let i = 0; i < inCh.length; i++) {
                inBuf[this.inPos] = inCh[i];
                this.inPos = (this.inPos + 1) % this.fftSize;
            }

            // Read windowed frame
            for (let i = 0; i < this.fftSize; i++) {
                const idx = (this.inPos + i) % this.fftSize;
                this.real[i] = inBuf[idx] * this.window[i];
                this.imag[i] = 0;
            }

            // Forward FFT
            this._fft(this.real, this.imag, false);

            // Process spectrum
            for (let k = 1; k < this.halfSize; k++) {
                let mag = Math.sqrt(this.real[k] * this.real[k] + this.imag[k] * this.imag[k]);
                let phase = Math.atan2(this.imag[k], this.real[k]);

                // Air boost above crossover
                if (k >= crossBin) {
                    // Smooth transition: ramp from 1.0 to airGain over ~500 Hz
                    const ramp = Math.min(1, (k - crossBin) / Math.max(1, Math.round(500 / binFreq)));
                    mag *= 1 + ramp * (airGain - 1);
                }

                // Spectral peak emphasis (sparkle)
                if (sparkAmt > 0 && k > 1 && k < this.halfSize - 1) {
                    const leftMag = Math.sqrt(this.real[k-1] * this.real[k-1] + this.imag[k-1] * this.imag[k-1]);
                    const rightMag = Math.sqrt(this.real[k+1] * this.real[k+1] + this.imag[k+1] * this.imag[k+1]);
                    const localAvg = (leftMag + rightMag) * 0.5;
                    if (localAvg > 0.00001 && mag > localAvg) {
                        const peakRatio = mag / localAvg;
                        mag *= 1 + sparkAmt * Math.min(1, (peakRatio - 1) * 0.5);
                    }
                }

                // Transient enhancement via magnitude delta
                if (transAmt > 0) {
                    const delta = mag - prevMag[k];
                    if (delta > 0) {
                        mag += delta * transAmt * 0.5;
                    }
                    prevMag[k] = mag;
                }

                this.real[k] = mag * Math.cos(phase);
                this.imag[k] = mag * Math.sin(phase);
            }

            // Stereo widening: rotate side channel (applied on R channel only)
            if (widthAmt > 0 && ch === 1 && numCh >= 2) {
                for (let k = crossBin; k < this.halfSize; k++) {
                    // Scale R bins slightly out of phase for width
                    const phase = Math.atan2(this.imag[k], this.real[k]);
                    const mag = Math.sqrt(this.real[k] * this.real[k] + this.imag[k] * this.imag[k]);
                    const newPhase = phase + widthAmt * 0.3;
                    this.real[k] = mag * Math.cos(newPhase);
                    this.imag[k] = mag * Math.sin(newPhase);
                }
            }

            // Inverse FFT
            this._fft(this.real, this.imag, true);

            // Overlap-add to output buffer
            for (let i = 0; i < this.fftSize; i++) {
                outBuf[(this.outPos + i) % this.fftSize] += this.real[i] * this.window[i] / this.winNorm;
            }
        }

        // Read output
        for (let ch = 0; ch < numCh; ch++) {
            const outCh = output[ch];
            const outBuf = ch === 0 ? this.outBufL : this.outBufR;
            const inCh = input[ch] || input[0];
            for (let i = 0; i < outCh.length; i++) {
                const wet = outBuf[this.outPos];
                const dry = inCh[i];
                outCh[i] = (dry + (wet - dry) * mixAmt) * og;
            }
        }

        // Advance output position and clear read samples
        const advance = output[0] ? output[0].length : this.blockSize;
        for (let ch = 0; ch < numCh; ch++) {
            const outBuf = ch === 0 ? this.outBufL : this.outBufR;
            for (let i = 0; i < advance; i++) {
                outBuf[(this.outPos + i) % this.fftSize] = 0;
            }
        }
        this.outPos = (this.outPos + advance) % this.fftSize;
    }
}
