// @werkstatt spectral_blur 1 1
// Spectral Blur — STFT-based spectral smearing for ambient textures
// Smears magnitude across frequency bins and/or time frames, creating
// diffuse, pad-like sounds from any input. Phase randomization adds
// diffuse spatial texture. Classic for ambient, drone, sound design.

// @param blur_size   8 1 32 int bins
// @param freq_blur   0.7 0 1 linear
// @param time_blur   0.3 0 1 linear
// @param phase_rand  0.5 0 1 linear
// @param mix         0.5 0 1 linear
// @param output      0 -24 6 linear dB

class SpectralBlurProcessor {
    constructor() {
        this.sampleRate = 44100;
        this.blockSize = 128;
        this.fftSize = 2048;
        this.hopSize = 512;
        this.numBins = this.fftSize / 2;

        // Pre-allocate buffers
        this.fftBuffer = new Float32Array(this.fftSize * 2); // complex
        this.window = new Float32Array(this.fftSize);
        this.inputBuffer = new Float32Array(this.fftSize);
        this.outputBuffer = new Float32Array(this.fftSize);
        this.overlapBuffer = new Float32Array(this.fftSize);

        // Magnitude storage for temporal blur (store last N frames)
        this.temporalFrames = 4;
        this.magnitudeHistory = [];
        for (let i = 0; i < this.temporalFrames; i++) {
            this.magnitudeHistory.push(new Float32Array(this.numBins));
        }
        this.historyIdx = 0;

        // Phase storage
        this.phaseBuffer = new Float32Array(this.numBins);
        this.blurredMag = new Float32Array(this.numBins);

        // Write/read positions
        this.writePos = 0;
        this.readPos = 0;
        this.samplesUntilProcess = 0;

        // Generate Hann window
        for (let i = 0; i < this.fftSize; i++) {
            this.window[i] = 0.5 * (1 - Math.cos(2 * Math.PI * i / (this.fftSize - 1)));
        }
    }

    paramChanged(name, value) {
        // Params arrive as Float32Array, read by name
    }

    // Simple radix-2 FFT (Cooley-Tukey, in-place)
    fft(real, imag, inverse) {
        const n = real.length;
        // Bit reversal
        for (let i = 1, j = 0; i < n; i++) {
            let bit = n >> 1;
            for (; j & bit; bit >>= 1) j ^= bit;
            j ^= bit;
            if (i < j) {
                let t = real[i]; real[i] = real[j]; real[j] = t;
                t = imag[i]; imag[i] = imag[j]; imag[j] = t;
            }
        }
        // Butterfly
        for (let len = 2; len <= n; len <<= 1) {
            const halfLen = len >> 1;
            const angle = (inverse ? 2 : -2) * Math.PI / len;
            const wReal = Math.cos(angle);
            const wImag = Math.sin(angle);
            for (let i = 0; i < n; i += len) {
                let curReal = 1, curImag = 0;
                for (let j = 0; j < halfLen; j++) {
                    const tReal = curReal * real[i + j + halfLen] - curImag * imag[i + j + halfLen];
                    const tImag = curReal * imag[i + j + halfLen] + curImag * real[i + j + halfLen];
                    real[i + j + halfLen] = real[i + j] - tReal;
                    imag[i + j + halfLen] = imag[i + j] - tImag;
                    real[i + j] += tReal;
                    imag[i + j] += tImag;
                    const newReal = curReal * wReal - curImag * wImag;
                    curImag = curReal * wImag + curImag * wReal;
                    curReal = newReal;
                }
            }
        }
        if (inverse) {
            for (let i = 0; i < n; i++) {
                real[i] /= n;
                imag[i] /= n;
            }
        }
    }

    processAudio(inputs, outputs, parameters) {
        const input = inputs[0];
        const output = outputs[0];
        if (!input || !input[0]) return;

        const blurSize = Math.max(1, Math.round(parameters[0] || 8));
        const freqBlur = parameters[1] || 0.7;
        const timeBlur = parameters[2] || 0.3;
        const phaseRand = parameters[3] || 0.5;
        const mix = parameters[4] || 0.5;
        const outputGain = Math.pow(10, (parameters[5] || 0) / 20);

        const numChannels = Math.min(input.length, output.length);
        const blockSize = input[0].length;

        for (let s = 0; s < blockSize; s++) {
            // Write input to circular buffer
            this.inputBuffer[this.writePos] = input[0][s];
            this.writePos = (this.writePos + 1) % this.fftSize;

            // Check if we have enough samples to process a frame
            this.samplesUntilProcess--;
            if (this.samplesUntilProcess <= 0) {
                this.samplesUntilProcess = this.hopSize;
                this.processFrame(blurSize, freqBlur, timeBlur, phaseRand);
            }

            // Read from overlap buffer
            const wet = this.overlapBuffer[this.readPos];
            this.overlapBuffer[this.readPos] = 0; // clear after read
            this.readPos = (this.readPos + 1) % this.fftSize;

            const dry = input[0][s];
            const sample = (dry * (1 - mix) + wet * mix) * outputGain;

            for (let ch = 0; ch < numChannels; ch++) {
                output[ch][s] = sample;
            }
        }
    }

    processFrame(blurSize, freqBlur, timeBlur, phaseRand) {
        // Read hopSize samples from input buffer (windowed)
        const real = new Float32Array(this.fftSize);
        const imag = new Float32Array(this.fftSize);

        for (let i = 0; i < this.fftSize; i++) {
            const idx = (this.readPos + i) % this.fftSize;
            real[i] = this.inputBuffer[idx] * this.window[i];
        }

        // Forward FFT
        this.fft(real, imag, false);

        // Extract magnitude and phase
        const mag = new Float32Array(this.numBins);
        const phase = new Float32Array(this.numBins);
        for (let i = 0; i < this.numBins; i++) {
            mag[i] = Math.sqrt(real[i] * real[i] + imag[i] * imag[i]);
            phase[i] = Math.atan2(imag[i], real[i]);
        }

        // Frequency blur: average magnitude with neighbors
        if (freqBlur > 0) {
            for (let i = 0; i < this.numBins; i++) {
                let sum = 0, count = 0;
                for (let j = -blurSize; j <= blurSize; j++) {
                    const idx = i + j;
                    if (idx >= 0 && idx < this.numBins) {
                        sum += mag[idx];
                        count++;
                    }
                }
                const blurred = sum / count;
                this.blurredMag[i] = mag[i] * (1 - freqBlur) + blurred * freqBlur;
            }
        } else {
            for (let i = 0; i < this.numBins; i++) this.blurredMag[i] = mag[i];
        }

        // Temporal blur: average with previous frames
        if (timeBlur > 0) {
            const currentFrame = this.magnitudeHistory[this.historyIdx];
            for (let i = 0; i < this.numBins; i++) {
                currentFrame[i] = this.blurredMag[i];
            }

            for (let i = 0; i < this.numBins; i++) {
                let sum = 0;
                for (let f = 0; f < this.temporalFrames; f++) {
                    sum += this.magnitudeHistory[f][i];
                }
                const avg = sum / this.temporalFrames;
                this.blurredMag[i] = this.blurredMag[i] * (1 - timeBlur) + avg * timeBlur;
            }
            this.historyIdx = (this.historyIdx + 1) % this.temporalFrames;
        }

        // Phase randomization
        if (phaseRand > 0) {
            for (let i = 0; i < this.numBins; i++) {
                // Pseudo-random based on bin index and frame count
                const r = Math.sin(i * 12.9898 + this.writePos * 0.01) * 43758.5453;
                const randPhase = (r - Math.floor(r)) * 2 * Math.PI;
                phase[i] = phase[i] * (1 - phaseRand) + randPhase * phaseRand;
            }
        }

        // Reconstruct complex spectrum
        for (let i = 0; i < this.numBins; i++) {
            real[i] = this.blurredMag[i] * Math.cos(phase[i]);
            imag[i] = this.blurredMag[i] * Math.sin(phase[i]);
            // Mirror for full spectrum
            real[this.fftSize - i] = real[i];
            imag[this.fftSize - i] = -imag[i];
        }

        // Inverse FFT
        this.fft(real, imag, true);

        // Overlap-add to output buffer
        for (let i = 0; i < this.fftSize; i++) {
            const idx = (this.readPos + i) % this.fftSize;
            this.overlapBuffer[idx] += real[i] * this.window[i];
        }
    }
}

const processor = new SpectralBlurProcessor();

function paramChanged(name, value) {
    processor.paramChanged(name, value);
}

function processAudio(inputs, outputs, parameters) {
    processor.processAudio(inputs, outputs, parameters);
}
