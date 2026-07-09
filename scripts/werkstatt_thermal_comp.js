// @werkstatt thermal_comp 1 1
// @label Thermal Comp
// Optical compressor (LA-2A style)
// Photoresistor gain reduction element with slow, program-dependent attack/release
// Tube-style saturation on output for warmth
// @param peak_reduce 0.5 0 1 linear
// @param gain 0.5 0 1 linear
// @param tube 0.3 0 1 linear
// @param speed 0.5 0 1 linear
// @param mix 1.0 0 1 linear

class ThermalComp {
    constructor(sampleRate, blockSize) {
        this.sampleRate = sampleRate;
        this.blockSize = blockSize;

        // Opto element state (photoresistor has memory, slow response)
        this.optoLevel = 0;
        this.smoothGain = 1;

        // Tube saturation state
        this.tubeState = 0;

        // DC blocker
        this.dcIn = 0;
        this.dcOut = 0;
    }

    processAudio(inputs, outputs, parameters) {
        const input = inputs[0];
        const output = outputs[0];
        const numCh = output.length;
        const numFrames = output[0].length;

        const peakReduceRaw = parameters.peak_reduce[0] || 0.5;
        const gainRaw = parameters.gain[0] || 0.5;
        const tubeRaw = parameters.tube[0] || 0.3;
        const speedRaw = parameters.speed[0] || 0.5;
        const mix = parameters.mix[0] || 1.0;

        // Input gain: 0 to +30 dB
        const inputGainDb = gainRaw * 30;
        const inputGain = Math.pow(10, inputGainDb / 20);

        // Peak reduction: maps to threshold -40 to 0 dB
        const thresholdDb = -40 + (1 - peakReduceRaw) * 40;
        const thresholdLinear = Math.pow(10, thresholdDb / 20);

        // Opto speed: attack 10-100ms, release 100-2000ms
        const attackMs = 100 - speedRaw * 90;  // 10ms (fast) to 100ms (slow)
        const releaseMs = 2000 - speedRaw * 1900; // 100ms (fast) to 2000ms (slow)
        const attackCoeff = Math.exp(-1 / (this.sampleRate * attackMs * 0.001));
        const releaseCoeff = Math.exp(-1 / (this.sampleRate * releaseMs * 0.001));

        // Tube saturation amount
        const tubeAmount = tubeRaw * 2;

        for (let i = 0; i < numFrames; i++) {
            let inSample = 0;
            if (numCh > 0 && input[0]) inSample = input[0][i];
            if (numCh > 1 && input[1]) inSample = (inSample + input[1][i]) * 0.5;

            // Apply input gain
            const gained = inSample * inputGain;

            // Opto element: detects level, photoresistor response is slow
            // The LED brightness is proportional to signal level
            const absLevel = Math.abs(gained);
            // Opto attack: fast on transients but not instant
            // Opto release: very slow, program-dependent
            if (absLevel > this.optoLevel) {
                this.optoLevel = attackCoeff * this.optoLevel + (1 - attackCoeff) * absLevel;
            } else {
                this.optoLevel = releaseCoeff * this.optoLevel + (1 - releaseCoeff) * absLevel;
            }

            // Gain reduction: opto compresses above threshold
            // The photoresistor resistance decreases with light, reducing gain
            let compGain = 1;
            if (this.optoLevel > thresholdLinear) {
                const overDb = 20 * Math.log10(this.optoLevel / thresholdLinear);
                // LA-2A has a soft knee, roughly 4:1 ratio with gentle curve
                const reducedDb = overDb * 0.25;  // ~4:1
                compGain = Math.pow(10, -(overDb - reducedDb) / 20);
            }

            // Smooth gain transitions (opto element is inherently smooth)
            this.smoothGain = this.smoothGain * 0.999 + compGain * 0.001;

            // Apply compression
            const compressed = gained * this.smoothGain;

            // Tube saturation on output (2nd harmonic emphasis)
            const tubeDrive = compressed * (1 + tubeAmount);
            const tubeOut = tubeDrive - 0.1 * tubeAmount * tubeDrive * tubeDrive * Math.sign(tubeDrive);
            const tubeNormalized = tubeOut / (1 + tubeAmount * 0.3);

            // Mix dry + wet
            const mixed = inSample * (1 - mix) + tubeNormalized * mix;

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
