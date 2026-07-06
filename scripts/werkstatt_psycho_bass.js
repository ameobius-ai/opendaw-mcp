// @werkstatt psycho_bass 1 1
// @label Psycho Bass
// Psychoacoustic bass enhancer (MaxxBass / RBass style)
// Generates harmonics of sub-bass frequencies that small speakers can't reproduce
// The ear/brain reconstructs the missing fundamental from the harmonics
// Result: bass sounds full on laptop/phone speakers even without subwoofer
// @param frequency 0.3 linear   // crossover frequency (60-300 Hz, below this = needs harmonics)
// @param harmonics 0.5 linear   // number of harmonics to generate (2-5)
// @param intensity 0.5 linear   // harmonic intensity (0=subtle, 1=heavy)
// @param mix 0.5 linear         // wet/dry blend (0=original, 1=full harmonics)

class PsychoBass {
    constructor(sampleRate, blockSize) {
        this.sampleRate = sampleRate;
        this.blockSize = blockSize;

        // Lowpass filter to extract sub-bass
        this.lpState = [0, 0];

        // Highpass on output to avoid doubling the fundamental
        this.hpState = [0, 0];

        // DC blocker
        this.dcIn = 0;
        this.dcOut = 0;
    }

    processAudio(inputs, outputs, parameters) {
        const input = inputs[0];
        const output = outputs[0];
        const numCh = output.length;
        const numFrames = output[0].length;

        const freqRaw = parameters.frequency[0] || 0.3;
        const harmRaw = parameters.harmonics[0] || 0.5;
        const intensity = parameters.intensity[0] || 0.5;
        const mix = parameters.mix[0] || 0.5;

        // Crossover: 60-300 Hz
        const crossover = 60 + freqRaw * 240;
        const lpCoeff = Math.exp(-2 * Math.PI * crossover / this.sampleRate);
        const hpCoeff = Math.exp(-2 * Math.PI * crossover / this.sampleRate);

        // Number of harmonics: 2-5
        const numHarm = 2 + Math.floor(harmRaw * 3.99);

        // Harmonic amplitudes (decreasing)
        const harmAmps = [];
        for (let h = 2; h <= numHarm + 1; h++) {
            harmAmps.push(1.0 / h);
        }

        for (let i = 0; i < numFrames; i++) {
            let inSample = 0;
            if (numCh > 0 && input[0]) inSample = input[0][i];
            if (numCh > 1 && input[1]) inSample = (inSample + input[1][i]) * 0.5;

            // Extract sub-bass via lowpass
            this.lpState[0] = this.lpState[0] + lpCoeff * (inSample - this.lpState[0]);
            const subBass = this.lpState[0];

            // Generate harmonics via nonlinear processing
            // The key insight: a nonlinear function of a sinusoid generates harmonics
            // We use a polynomial that generates 2nd, 3rd, 4th, 5th harmonics
            let harmonicSignal = 0;
            const driven = subBass * (1 + intensity * 4);

            // Polynomial nonlinearity generates harmonics
            // x² → 2nd harmonic, x³ → 3rd harmonic, etc.
            const x2 = driven * driven;
            const x3 = x2 * driven;
            const x4 = x3 * driven;
            const x5 = x4 * driven;

            let harmSum = 0;
            if (numHarm >= 2) harmSum += harmAmps[0] * x2 * 0.5;
            if (numHarm >= 3) harmSum += harmAmps[1] * x3 * 0.33;
            if (numHarm >= 4) harmSum += harmAmps[2] * x4 * 0.25;
            if (numHarm >= 5) harmSum += harmAmps[3] * x5 * 0.2;

            harmonicSignal = harmSum * intensity;

            // Highpass the harmonic signal to remove any fundamental leakage
            this.hpState[0] = this.hpState[0] + (1 - hpCoeff) * (harmonicSignal - this.hpState[0]);
            const harmonicsHP = this.hpState[0];

            // Mix: original + generated harmonics
            const mixed = inSample * (1 - mix) + (inSample + harmonicsHP) * mix;

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
