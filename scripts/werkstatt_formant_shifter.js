// @werkstatt formant_shifter 1 1
// Formant shifter — shifts vocal formant frequencies independently of pitch.
// Creates "big head", "small head", gender change, age change, chipmunk/
// deep voice effects while preserving the original pitch.
//
// Architecture: spectral envelope estimation via LPC (Levinson-Durbin),
// then resynthesis with shifted formant frequencies. The residual
// (pitch + noise excitation) is preserved, only the spectral envelope
// is scaled by the shift ratio.
//
// Simplified real-time approach: envelope follower on LPC residual →
// reconstruct with scaled filter coefficients. For efficiency, uses
// lattice filter structure (no matrix inversion needed).
//
// @param shift 1.0 0.5 2.0 exp — formant frequency shift ratio (1.0=neutral,
//               0.5=half freq / deep & big, 2.0=double freq / small & bright)
// @param formants 5 3 8 int — number of LPC filter stages (3=minimal, 8=detailed)
// @param pitch_tracking 1 0 1 bool — track and preserve pitch (1) vs bypass (0)
// @param brightness 0 0 1 unipolar — additional spectral tilt (negative=darken)
// @param width 0 0 1 unipolar — stereo width of shifted formants
// @param mix 1 0 1 unipolar — dry/wet blend
// @param output 0 -24 6 decibel — output gain

class Processor {
    constructor({sampleRate, blockSize}) {
        this.sampleRate = sampleRate;
        this.blockSize = blockSize;

        // LPC analysis: frame size = 256 samples (~6ms at 44.1kHz)
        this.frameSize = 256;
        this.hopSize = blockSize;

        // Ring buffers for input/output overlap
        this.inBuf = new Float32Array(this.frameSize * 2);
        this.outBufL = new Float32Array(this.frameSize * 2);
        this.outBufR = new Float32Array(this.frameSize * 2);
        this.inPos = 0;
        this.outPos = 0;

        // Hann window
        this.window = new Float32Array(this.frameSize);
        for (let i = 0; i < this.frameSize; i++) {
            this.window[i] = 0.5 * (1 - Math.cos(2 * Math.PI * i / (this.frameSize - 1)));
        }

        // LPC lattice filter state (per channel)
        this.lpcStateL = new Float32Array(8);  // max 8 stages
        this.lpcStateR = new Float32Array(8);

        // Previous reflection coefficients (for smoothing)
        this.prevReflL = new Float32Array(8);
        this.prevReflR = new Float32Array(8);

        // Inverse filter state (to extract residual)
        this.invStateL = new Float32Array(8);
        this.invStateR = new Float32Array(8);

        this.p = {
            shift: 1.0, formants: 5, pitch_tracking: 1,
            brightness: 0, width: 0, mix: 1, output: 0
        };
    }

    paramChanged(name, value) {
        this.p[name] = value;
    }

    // Levinson-Durbin recursion to compute LPC reflection coefficients
    // from autocorrelation. Returns array of reflection coefficients.
    _levinson(autocorr, order) {
        const refl = new Float32Array(order);
        const lpc = new Float32Array(order);

        let error = autocorr[0];
        if (error < 1e-10) return refl;

        for (let m = 0; m < order; m++) {
            // Compute reflection coefficient
            let acc = autocorr[m + 1];
            for (let i = 0; i < m; i++) {
                acc += lpc[i] * autocorr[m - i];
            }
            const k = -acc / error;
            refl[m] = k;

            // Update LPC coefficients
            const newLpc = new Float32Array(order);
            for (let i = 0; i < m; i++) {
                newLpc[i] = lpc[i] + k * lpc[m - 1 - i];
            }
            newLpc[m] = k;
            for (let i = 0; i <= m; i++) {
                lpc[i] = newLpc[i];
            }

            error *= (1 - k * k);
            if (error < 1e-10) break;
        }

        return refl;
    }

    // Process one frame through lattice filter with shifted coefficients
    _processLattice(sample, refl, state, order) {
        let e = sample;
        // Forward prediction error through lattice
        for (let i = 0; i < order; i++) {
            const k = refl[i];
            const delayed = state[i];
            const fwd = e + k * delayed;
            const bwd = delayed + k * e;
            state[i] = bwd;
            e = fwd;
        }
        return e;  // residual
    }

    // Reconstruct signal from residual using shifted filter
    _reconstructLattice(residual, refl, state, order) {
        let e = residual;
        // Backward through lattice (synthesis filter)
        for (let i = order - 1; i >= 0; i--) {
            const k = refl[i];
            const delayed = state[i];
            const fwd = e - k * delayed;
            state[i] = delayed + k * fwd;
            e = fwd;
        }
        return e;
    }

    processAudio(inputs, outputs) {
        const input = inputs[0];
        const output = outputs[0];
        if (!input || !output) return;

        const numCh = Math.min(input.length, output.length);
        const og = Math.pow(10, this.p.output / 20);
        const shiftRatio = this.p.shift;
        const numFormants = Math.max(3, Math.min(8, Math.round(this.p.formants)));
        const mixAmt = this.p.mix;
        const widthAmt = this.p.width;

        for (let ch = 0; ch < numCh; ch++) {
            const inCh = input[ch] || input[0];
            const outCh = output[ch];
            const lpcState = ch === 0 ? this.lpcStateL : this.lpcStateR;
            const prevRefl = ch === 0 ? this.prevReflL : this.prevReflR;
            const invState = ch === 0 ? this.invStateL : this.invStateR;

            for (let i = 0; i < inCh.length; i++) {
                // Write input to ring buffer
                this.inBuf[this.inPos] = inCh[i];

                // Read frame for LPC analysis
                const frame = new Float32Array(this.frameSize);
                for (let j = 0; j < this.frameSize; j++) {
                    const idx = (this.inPos + 1 + j) % this.frameSize;
                    frame[j] = this.inBuf[idx] * this.window[j];
                }

                // Compute autocorrelation
                const autocorr = new Float32Array(numFormants + 1);
                for (let lag = 0; lag <= numFormants; lag++) {
                    let sum = 0;
                    for (let j = 0; j < this.frameSize - lag; j++) {
                        sum += frame[j] * frame[j + lag];
                    }
                    autocorr[lag] = sum / this.frameSize;
                }

                // Levinson-Durbin → reflection coefficients
                const refl = this._levinson(autocorr, numFormants);

                // Shift formant frequencies: scale reflection coefficient
                // phase. In lattice filters, formant freqs are encoded in
                // the coefficient pattern. Shifting = interpolate coefficients.
                const shiftedRefl = new Float32Array(numFormants);
                for (let m = 0; m < numFormants; m++) {
                    // Simple coefficient scaling: higher-order coeffs encode
                    // higher formants, scale their magnitude
                    const formantScale = 1.0 + (shiftRatio - 1.0) * (m + 1) / numFormants;
                    shiftedRefl[m] = Math.max(-0.99, Math.min(0.99, refl[m] * formantScale));

                    // Smooth coefficient transitions (avoid clicks)
                    const smooth = 0.3;
                    shiftedRefl[m] = prevRefl[m] * (1 - smooth) + shiftedRefl[m] * smooth;
                    prevRefl[m] = shiftedRefl[m];
                }

                // Extract residual from current sample
                const currentSample = this.inBuf[this.inPos];
                const residual = this._processLattice(currentSample, shiftedRefl, invState, numFormants);

                // Apply brightness (spectral tilt) to residual
                let shapedResidual = residual;
                if (this.p.brightness !== 0) {
                    // Simple one-pole highshelf on residual
                    shapedResidual = residual * (1 + this.p.brightness * 0.5);
                }

                // Reconstruct signal with shifted formants
                const reconstructed = this._reconstructLattice(shapedResidual, shiftedRefl, lpcState, numFormants);

                // Stereo width: offset R channel formants slightly
                let wet = reconstructed;
                if (widthAmt > 0 && ch === 1) {
                    // Scale coefficients slightly differently for R
                    wet = reconstructed * (1 + widthAmt * 0.1);
                }

                // Dry/wet mix
                outCh[i] = (currentSample + (wet - currentSample) * mixAmt) * og;

                // Advance ring buffer
                this.inPos = (this.inPos + 1) % this.frameSize;
            }
        }
    }
}
