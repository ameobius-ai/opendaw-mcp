// @werkstatt bx_saturator 1 1
// @label BX Saturator
// Multi-band saturation (BX style: 3-band crossover with independent saturation per band)
// Low band: tube-style even harmonic warmth (2nd harmonic emphasis)
// Mid band: tape-style soft clipping (3rd harmonic for presence)
// High band: transformer-style harmonic shimmer (odd harmonics for air)
// Blend control mixes saturated and dry signal
// @param drive 0.3 0 1 linear
// @param low_sat 0.4 0 1 linear
// @param mid_sat 0.3 0 1 linear
// @param high_sat 0.2 0 1 linear
// @param blend 0.5 0 1 linear
// @param output 0.0 -24 6 linear

class BxSaturator {
    constructor(sampleRate, blockSize) {
        this.sampleRate = sampleRate;
        this.blockSize = blockSize;

        // Crossover frequencies
        const lowCutoff = 200;   // Hz
        const midCutoff = 2000;  // Hz

        // Low band: 2nd-order Linkwitz-Riley lowpass
        this.lpLow = this.makeLR4(lowCutoff, "low", sampleRate);
        // High band: 2nd-order Linkwitz-Riley highpass
        this.hpHigh = this.makeLR4(midCutoff, "high", sampleRate);
        // Mid band = input - low - high (computed per sample)

        // Saturation state per band
        this.lowState = 0;
        this.midState = 0;
        this.highState = 0;

        // DC blocker
        this.dcIn = 0;
        this.dcOut = 0;
    }

    makeLR4(freq, type, sr) {
        const w0 = 2 * Math.PI * freq / sr;
        const cosW = Math.cos(w0);
        const sinW = Math.sin(w0);
        // 2nd-order Butterworth (cascaded for LR4)
        const Q = 0.707;
        const alpha = sinW / (2 * Q);

        let b0, b1, b2, a0, a1, a2;

        if (type === "low") {
            b0 = (1 - cosW) / 2;
            b1 = 1 - cosW;
            b2 = (1 - cosW) / 2;
            a0 = 1 + alpha;
            a1 = -2 * cosW;
            a2 = 1 - alpha;
        } else {
            b0 = (1 + cosW) / 2;
            b1 = -(1 + cosW);
            b2 = (1 + cosW) / 2;
            a0 = 1 + alpha;
            a1 = -2 * cosW;
            a2 = 1 - alpha;
        }

        // Normalize
        return {
            b0: b0 / a0, b1: b1 / a0, b2: b2 / a0,
            a1: a1 / a0, a2: a2 / a0,
            x1: 0, x2: 0, y1: 0, y2: 0
        };
    }

    biquad(input, f) {
        const out = f.b0 * input + f.b1 * f.x1 + f.b2 * f.x2 - f.a1 * f.y1 - f.a2 * f.y2;
        f.x2 = f.x1;
        f.x1 = input;
        f.y2 = f.y1;
        f.y1 = out;
        return out;
    }

    // Tube-style even harmonic saturation (2nd harmonic emphasis)
    tubeSat(x, drive) {
        const d = x * (1 + drive * 4);
        return d - 0.15 * d * d * Math.sign(d) * (1 - drive * 0.5);
    }

    // Tape-style soft clipping (3rd harmonic)
    tapeSat(x, drive) {
        const d = x * (1 + drive * 3);
        return Math.tanh(d) * (1 - 0.1 * drive);
    }

    // Transformer-style odd harmonic saturation (air/shimmer)
    transformerSat(x, drive) {
        const d = x * (1 + drive * 5);
        return d - 0.2 * d * d * d * (1 - drive * 0.3);
    }

    processAudio(inputs, outputs, parameters) {
        const input = inputs[0];
        const output = outputs[0];
        const numCh = output.length;
        const numFrames = output[0].length;

        const drive = parameters.drive[0] || 0.3;
        const lowSat = parameters.low_sat[0] || 0.4;
        const midSat = parameters.mid_sat[0] || 0.3;
        const highSat = parameters.high_sat[0] || 0.2;
        const blend = parameters.blend[0] || 0.5;

        const outGainRaw = parameters.output[0] || 0;
        const outGainDb = outGainRaw * 30 - 24;
        const outGain = Math.pow(10, outGainDb / 20);

        for (let i = 0; i < numFrames; i++) {
            let inSample = 0;
            if (numCh > 0 && input[0]) inSample = input[0][i];
            if (numCh > 1 && input[1]) inSample = (inSample + input[1][i]) * 0.5;

            // Crossover
            const lowBand = this.biquad(inSample, this.lpLow);
            const highBand = this.biquad(inSample, this.hpHigh);
            const midBand = inSample - lowBand - highBand;

            // Saturation per band
            const lowSatOut = this.tubeSat(lowBand, lowSat * drive);
            const midSatOut = this.tapeSat(midBand, midSat * drive);
            const highSatOut = this.transformerSat(highBand, highSat * drive);

            // Recombine
            const saturated = lowSatOut + midSatOut + highSatOut;

            // Blend dry + saturated
            const mixed = inSample * (1 - blend) + saturated * blend;

            // DC blocker
            const dcOut = mixed - this.dcIn + 0.995 * this.dcOut;
            this.dcIn = mixed;
            this.dcOut = dcOut;

            // Output gain
            const finalSample = dcOut * outGain;

            for (let c = 0; c < numCh; c++) {
                output[c][i] = finalSample;
            }
        }
    }

    paramChanged(name, value) {
    }
}
