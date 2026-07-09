// @werkstatt valve_preamp 1 1
// Valve/tube preamplifier simulator
// Models the warm, harmonic-rich character of a tube preamp stage
// (12AX7 triode in Class A bias)
//
// Tube preamps produce:
// - Even-order harmonic distortion (2nd, 4th harmonics) — the "warmth"
// - Soft asymmetrical clipping (positive and negative halves differ)
// - Dynamic compression at high input levels
// - Subtle high-frequency rolloff (Miller capacitance)
// - Low-end weight from output transformer coupling
//
// Implementation:
// 1. Input gain stage
// 2. Asymmetric waveshaper (models triode grid conduction)
// 3. Miller capacitance lowpass (high-freq rolloff)
// 4. DC offset compensation
// 5. Output transformer coloration (low-end bump, slight phase)
//
// Parameters:
//   gain      0-2    input drive amount (0=clean, 1=breakup, 2=crunch)
//   bias     -0.5..0.5  tube bias point (asymmetry control)
//   warmth    0-1    harmonic content (even-order amount)
//   miller    0-1    high-freq rolloff amount (Miller capacitance)
//   mix       0-1    dry/wet mix
//   output   -24..6 dB output gain

// @param gain 1 0 2 linear
// @param bias 0 -0.5 0.5 linear
// @param warmth 0.6 0 1 linear
// @param miller 0.4 0 1 linear
// @param mix 1 0 1 linear
// @param output 0 -24 6 exp

class ValvePreamp {
    constructor(sampleRate, blockSize) {
        this.sampleRate = sampleRate;
        this.blockSize = blockSize;
        // Miller capacitance lowpass state
        this.millerState = 0.0;
        // DC blocker
        this.dcPrevIn = 0.0;
        this.dcPrevOut = 0.0;
        // Output transformer low-end state
        this.transformerState = 0.0;
        // Previous sample for 2nd harmonic generation
        this.prevSample = 0.0;
    }

    paramChanged(name, value) {
        // Coefficients computed in processAudio for real-time control
    }

    processAudio(inputs, outputs, parameters) {
        const gain = parameters[0];
        const bias = parameters[1];
        const warmth = parameters[2];
        const miller = parameters[3];
        const mix = parameters[4];
        const output = parameters[5];

        const input = inputs[0];
        const outputBuf = outputs[0];
        const n = input.length;

        // Miller capacitance cutoff: higher miller = lower cutoff
        const millerFreq = 20000 - miller * 12000; // 20kHz → 8kHz
        const millerCoeff = Math.exp(-2 * Math.PI * millerFreq / this.sampleRate);

        // Output transformer low-end: gentle boost around 80-100 Hz
        const transformerFreq = 90;
        const transformerCoeff = Math.exp(-2 * Math.PI * transformerFreq / this.sampleRate);

        // Output gain
        const outGain = Math.pow(10, output / 20);

        for (let i = 0; i < n; i++) {
            let sample = input[i];

            // 1. Input gain stage
            let driven = sample * gain;

            // 2. Asymmetric waveshaper (triode model)
            // Positive half: softer clip (grid conduction)
            // Negative half: harder clip (cutoff)
            let biased = driven + bias;
            let shaped;
            if (biased > 0) {
                // Positive: tanh-like soft clip
                shaped = biased / (1 + biased * warmth * 0.5);
            } else {
                // Negative: asymmetric — harder
                shaped = biased / (1 + Math.abs(biased) * warmth * 0.8);
            }
            // Remove bias offset
            shaped -= bias * 0.3;

            // 3. Miller capacitance lowpass
            this.millerState = this.millerState + millerCoeff * (shaped - this.millerState);
            let milled = this.millerState;

            // 4. 2nd harmonic generation (even-order warmth)
            // Add a fraction of the difference between current and previous sample
            // This creates even harmonics naturally
            let harmonic = (milled - this.prevSample) * warmth * 0.15;
            let withHarm = milled + harmonic;
            this.prevSample = milled;

            // 5. DC blocker
            let dcOut = withHarm - this.dcPrevIn + 0.995 * this.dcPrevOut;
            this.dcPrevIn = withHarm;
            this.dcPrevOut = dcOut;

            // 6. Output transformer coloration (low-end bump)
            this.transformerState = this.transformerState +
                transformerCoeff * (dcOut - this.transformerState);
            let transformed = dcOut + this.transformerState * 0.3;

            // 7. Output gain + dry/wet
            let wet = transformed * outGain;
            outputBuf[i] = sample * (1 - mix) + wet * mix;
        }
    }
}

registerProcessor('valve_preamp', ValvePreamp);
