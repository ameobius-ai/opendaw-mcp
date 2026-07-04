// @werkstatt spectral_freezer 1 1
// Spectral freeze — captures a spectral snapshot and sustains it indefinitely.
// Useful for ambient pads, drone textures, and "frozen" vocal effects.
//
// @param freeze 0 0 1 bool — capture & hold current spectral frame
// @param smooth 0.5 0 1 unipolar — interpolation between frames (0=instant, 1=slow morph)
// @param spread 0 0 1 unipolar — stereo detune width for the frozen signal
// @param decay 0.7 0 0.999 unipolar — how quickly the frozen signal decays after release
// @param mix 1 0 1 unipolar — dry/wet blend
// @param output 0 -24 6 decibel — output gain

class Processor {
    constructor({sampleRate, blockSize}) {
        this.sampleRate = sampleRate;
        this.blockSize = blockSize;
        this.fftSize = 2048;
        this.hopSize = blockSize;
        this.halfSize = this.fftSize / 2;
        this.overlap = this.fftSize / this.hopSize;

        // Input ring buffer
        this.inBuf = new Float32Array(this.fftSize);
        this.inPos = 0;

        // Output overlap-add buffers
        this.outBuf = new Float32Array(this.fftSize);
        this.outPos = 0;

        // Frozen spectrum (magnitude + phase)
        this.frozenMag = new Float32Array(this.halfSize);
        this.frozenPhase = new Float32Array(this.halfSize);

        // Previous output spectrum for smoothing
        this.prevMag = new Float32Array(this.halfSize);

        // Window (Hann)
        this.window = new Float32Array(this.fftSize);
        for (let i = 0; i < this.fftSize; i++) {
            this.window[i] = 0.5 * (1 - Math.cos(2 * Math.PI * i / (this.fftSize - 1)));
        }

        // Precompute twiddle factors
        this.cosTable = new Float32Array(this.halfSize);
        this.sinTable = new Float32Array(this.halfSize);
        for (let i = 0; i < this.halfSize; i++) {
            const angle = -2 * Math.PI * i / this.fftSize;
            this.cosTable[i] = Math.cos(angle);
            this.sinTable[i] = Math.sin(angle);
        }

        this.wasFreezing = false;
        this.sustainGain = 1.0;
        this.spreadPhase = 0;
    }

    // In-place DFT (simplified — not a full FFT, but adequate for this block size)
    // Uses Goertzel-like approach for real input
    transform(real, imag) {
        const N = real.length;
        const halfN = N / 2;
        const tmpReal = new Float32Array(halfN);
        const tmpImag = new Float32Array(halfN);

        for (let k = 0; k < halfN; k++) {
            let re = 0, im = 0;
            const cosK = this.cosTable[k];
            const sinK = this.sinTable[k];
            let wRe = 1, wIm = 0;
            for (let n = 0; n < N; n++) {
                re += real[n] * wRe;
                im += real[n] * wIm;
                const newRe = wRe * cosK - wIm * sinK;
                const newIm = wRe * sinK + wIm * cosK;
                wRe = newRe;
                wIm = newIm;
            }
            tmpReal[k] = re / N;
            tmpImag[k] = -im / N;
        }

        for (let k = 0; k < halfN; k++) {
            real[k] = tmpReal[k];
            imag[k] = tmpImag[k];
        }
    }

    // Inverse transform via conjugate
    inverse(real, imag, output) {
        const N = output.length;
        const halfN = N / 2;

        // Use conjugate symmetry: X[N-k] = conj(X[k])
        const fullReal = new Float32Array(N);
        const fullImag = new Float32Array(N);

        for (let k = 0; k < halfN; k++) {
            fullReal[k] = real[k];
            fullImag[k] = imag[k];
            if (k > 0) {
                fullReal[N - k] = real[k];
                fullImag[N - k] = -imag[k];
            }
        }

        for (let n = 0; n < N; n++) {
            let re = 0, im = 0;
            for (let k = 0; k < N; k++) {
                const angle = 2 * Math.PI * k * n / N;
                re += fullReal[k] * Math.cos(angle) - fullImag[k] * Math.sin(angle);
                im += fullReal[k] * Math.sin(angle) + fullImag[k] * Math.cos(angle);
            }
            output[n] = re / N;
        }
    }

    processAudio(inputs, outputs, parameters) {
        const input = inputs[0];
        const output = outputs[0];

        if (!input || input.length === 0) return;

        const freeze = parameters.freeze[0] >= 0.5;
        const smooth = parameters.smooth[0];
        const spread = parameters.spread[0];
        const decay = parameters.decay[0];
        const mix = parameters.mix[0];
        const outputGain = Math.pow(10, parameters.output[0] / 20);

        const numChannels = Math.min(input.length, output.length);

        for (let ch = 0; ch < numChannels; ch++) {
            const inCh = input[ch];
            const outCh = output[ch];

            // Push input into ring buffer
            for (let i = 0; i < this.blockSize; i++) {
                this.inBuf[this.inPos] = inCh[i];
                this.inPos = (this.inPos + 1) % this.fftSize;
            }

            // Check if we have a full frame to process
            if (this.inPos % this.hopSize !== 0) continue;

            // Read frame from ring buffer with windowing
            const frameReal = new Float32Array(this.fftSize);
            const frameImag = new Float32Array(this.fftSize);

            let readPos = (this.inPos - this.fftSize + this.fftSize) % this.fftSize;
            for (let i = 0; i < this.fftSize; i++) {
                frameReal[i] = this.inBuf[readPos] * this.window[i];
                readPos = (readPos + 1) % this.fftSize;
            }

            // Forward transform
            this.transform(frameReal, frameImag);

            // Compute magnitude
            const mag = new Float32Array(this.halfSize);
            for (let k = 0; k < this.halfSize; k++) {
                mag[k] = Math.sqrt(frameReal[k] * frameReal[k] + frameImag[k] * frameImag[k]);
            }

            if (freeze) {
                if (!this.wasFreezing) {
                    // Capture snapshot
                    for (let k = 0; k < this.halfSize; k++) {
                        this.frozenMag[k] = mag[k];
                        this.frozenPhase[k] = Math.atan2(frameImag[k], frameReal[k]);
                        this.prevMag[k] = mag[k];
                    }
                    this.wasFreezing = true;
                    this.sustainGain = 1.0;
                }

                // Sustain frozen spectrum with slow phase rotation for movement
                this.spreadPhase += spread * 0.001;
                for (let k = 0; k < this.halfSize; k++) {
                    // Smooth between previous and frozen
                    const targetMag = this.frozenMag[k];
                    this.prevMag[k] = this.prevMag[k] * smooth + targetMag * (1 - smooth);

                    // Slowly rotate phase for shimmer
                    const phaseOffset = this.spreadPhase * (1 + k * 0.001);
                    const phase = this.frozenPhase[k] + phaseOffset;

                    frameReal[k] = this.prevMag[k] * this.sustainGain * Math.cos(phase);
                    frameImag[k] = this.prevMag[k] * this.sustainGain * Math.sin(phase);
                }

                this.sustainGain *= decay;
            } else {
                this.wasFreezing = false;
                // Pass-through with smoothing
                for (let k = 0; k < this.halfSize; k++) {
                    this.prevMag[k] = this.prevMag[k] * smooth + mag[k] * (1 - smooth);
                    frameReal[k] = frameReal[k];
                    frameImag[k] = frameImag[k];
                }
            }
        }

        // Inverse transform back to time domain
        const timeFrame = new Float32Array(this.fftSize);
        this.inverse(frameReal, frameImag, timeFrame);

        // Apply window again (synthesis)
        for (let i = 0; i < this.fftSize; i++) {
            timeFrame[i] *= this.window[i];
        }

        // Overlap-add into output buffer
        for (let i = 0; i < this.fftSize; i++) {
            this.outBuf[(this.outPos + i) % this.fftSize] += timeFrame[i];
        }

        // Read output
        for (let i = 0; i < this.blockSize; i++) {
            const dry = input[0] ? input[0][i] : 0;
            const wet = this.outBuf[this.outPos] * outputGain;
            for (let ch = 0; ch < numChannels; ch++) {
                outCh[i] = dry * (1 - mix) + wet * mix;
            }
            this.outBuf[this.outPos] = 0;
            this.outPos = (this.outPos + 1) % this.fftSize;
        }
    }

    paramChanged(name, value) {
        // React to parameter changes if needed
    }
}
