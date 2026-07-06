// @werkstatt aire 1 1
// @label Aire (Stereo Air Exciter)
// M/S stereo widener + HF harmonic exciter combo
// Adds "air" and width to dull/narrow mixes — brightens highs with harmonics
// while widening the stereo field. Inspired by plugin "air" tools (BX cleansweep, Ozone Exciter)
// @param air 0.5 0 1 linear      // HF harmonic exciter amount (0=off, 1=max air)
// @param width 0.5 0 1 linear    // stereo width (0=mono, 0.5=normal, 1=wide)
// @param freq 0.3 0 1 linear     // crossover frequency for air band (2-12 kHz)
// @param harmonics 0.5 0 1 linear // harmonic type (0=2nd, 0.5=mix, 1=3rd)
// @param mix 1.0 0 1 linear      // wet/dry mix (0=dry, 1=full processed)

class Processor {
    constructor(sampleRate, blockSize) {
        this.sampleRate = sampleRate;
        this.blockSize = blockSize;

        // M/S processing state — simple delay for side width
        this.sideDelay = new Float32Array(32);
        this.sideDelayPos = 0;

        // HF bandpass filter state (for air band extraction)
        this.bpState1 = [0, 0];
        this.bpState2 = [0, 0];

        // DC blocker
        this.dcIn = 0;
        this.dcOut = 0;
    }

    processAudio(inputs, outputs, parameters) {
        const input = inputs[0];
        const output = outputs[0];
        const numCh = output.length;
        const numFrames = output[0].length;

        const airAmt = parameters.air[0] || 0.5;
        const widthRaw = parameters.width[0] || 0.5;
        const freqRaw = parameters.freq[0] || 0.3;
        const harmType = parameters.harmonics[0] || 0.5;
        const mix = parameters.mix[0] || 1.0;

        // Width: 0=mono, 0.5=normal, 1=1.5x wide
        const widthFactor = widthRaw * 3.0 - 0.5; // -0.5 to 2.5

        // Air crossover: 2-12 kHz
        const airFreq = 2000 + freqRaw * 10000;
        const bpCoeff = Math.exp(-2 * Math.PI * airFreq / this.sampleRate);

        for (let i = 0; i < numFrames; i++) {
            let leftIn = 0;
            let rightIn = 0;
            if (numCh > 0 && input[0]) leftIn = input[0][i];
            if (numCh > 1 && input[1]) rightIn = input[1][i];

            // M/S encoding
            const mid = (leftIn + rightIn) * 0.5;
            let side = (leftIn - rightIn) * 0.5;

            // Width control: scale side signal
            side = side * widthFactor;

            // M/S decoding back to L/R
            let leftOut = mid + side;
            let rightOut = mid - side;

            // HF bandpass for air exciter
            this.bpState1[0] = this.bpState1[0] + bpCoeff * (leftOut - this.bpState1[0]);
            const hfL = leftOut - this.bpState1[0]; // highpass = signal - lowpass
            this.bpState2[0] = this.bpState2[0] + bpCoeff * (rightOut - this.bpState2[0]);
            const hfR = rightOut - this.bpState2[0];

            // Harmonic generation: 2nd + 3rd harmonic mix
            const harm2 = hfL * hfL; // 2nd harmonic
            const harm3 = harm2 * hfL; // 3rd harmonic
            const airSignalL = harm2 * (1 - harmType) + harm3 * harmType;

            const harm2R = hfR * hfR;
            const harm3R = harm2R * hfR;
            const airSignalR = harm2R * (1 - harmType) + harm3R * harmType;

            // Add air harmonics to signal
            leftOut = leftOut + airSignalL * airAmt * 0.3;
            rightOut = rightOut + airSignalR * airAmt * 0.3;

            // Mix
            const mixedL = leftIn * (1 - mix) + leftOut * mix;
            const mixedR = rightIn * (1 - mix) + rightOut * mix;

            // Output
            if (numCh > 0) output[0][i] = mixedL;
            if (numCh > 1) output[1][i] = mixedR;
        }
    }

    paramChanged(name, value) {
    }
}
