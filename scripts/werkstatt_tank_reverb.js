// @werkstatt tank_reverb 1 1
// @label Tank Reverb
// Spring tank reverb with impulse-response modeling
// Models the Accutronics Type 9 tank (long decay, 3-spring)
// Distinctive metallic "boing" on transients, diffuse sustain
// @param decay 0.4 exp       // tank decay (0.1=short, 0.9=long, maps to feedback)
// @param damp 0.5 linear     // high-frequency damping (0=bright, 1=muffled)
// @param spread 0.5 linear   // stereo spread of reflections
// @param drive 0.3 linear    // input drive into the tank (saturation)
// @param mix 0.3 linear      // wet/dry mix (0=dry, 1=full wet)

class TankReverb {
    constructor(sampleRate, blockSize) {
        this.sampleRate = sampleRate;
        this.blockSize = blockSize;

        // 4 dispersive delay lines simulating spring reflections
        // Accutronics Type 9: 3 springs with slightly different lengths
        const springDelays = [0.027, 0.033, 0.041, 0.019]; // 27, 33, 41, 19 ms
        this.numLines = 4;
        this.delayBufs = [];
        this.delayPos = [];
        this.delayLens = [];

        for (let i = 0; i < this.numLines; i++) {
            const len = Math.floor(springDelays[i] * sampleRate);
            this.delayLens.push(len);
            this.delayBufs.push(new Float32Array(len));
            this.delayPos.push(0);
        }

        // Allpass dispersion chain (creates the metallic character)
        this.apState = [];
        for (let i = 0; i < this.numLines; i++) {
            this.apState.push([0, 0, 0, 0, 0, 0]);
        }

        // Feedback states
        this.fb = [0, 0, 0, 0];

        // Damping lowpass per line
        this.dampState = [0, 0, 0, 0];

        // Drive saturation state
        this.driveState = 0;

        // DC blocker
        this.dcIn = 0;
        this.dcOut = 0;

        // Stereo spread: separate L/R accumulation
        this.spreadL = [1.0, 0.6, 0.3, 0.8];
        this.spreadR = [0.8, 0.3, 0.6, 1.0];

        // Predelay
        this.preDelayLen = Math.floor(0.004 * sampleRate);
        this.preDelayBuf = new Float32Array(this.preDelayLen);
        this.preDelayPos = 0;
    }

    allpass(input, states) {
        const coeff = 0.6;
        let out = input;
        for (let i = 0; i < states.length; i++) {
            const tmp = out;
            out = states[i] + out * coeff;
            states[i] = tmp - out * coeff;
        }
        return out;
    }

    processAudio(inputs, outputs, parameters) {
        const input = inputs[0];
        const output = outputs[0];
        const numCh = output.length;
        const numFrames = output[0].length;

        const decay = parameters.decay[0] || 0.4;
        const damp = parameters.damp[0] || 0.5;
        const spread = parameters.spread[0] || 0.5;
        const drive = parameters.drive[0] || 0.3;
        const mix = parameters.mix[0] || 0.3;

        const fbGain = decay * 0.82;
        const dampCoeff = 0.1 + (1.0 - damp) * 0.7;
        const driveAmount = 1.0 + drive * 3.0;

        for (let i = 0; i < numFrames; i++) {
            // Input
            let inSample = 0;
            if (numCh > 0 && input[0]) inSample = input[0][i];
            if (numCh > 1 && input[1]) inSample = (inSample + input[1][i]) * 0.5;

            // Predelay
            const dry = this.preDelayBuf[this.preDelayPos];
            this.preDelayBuf[this.preDelayPos] = inSample;
            this.preDelayPos = (this.preDelayPos + 1) % this.preDelayLen;

            // Drive saturation (soft clip into tank)
            const driven = Math.tanh(inSample * driveAmount) * 0.8;

            // Process each spring line
            let wetL = 0;
            let wetR = 0;

            for (let s = 0; s < this.numLines; s++) {
                const buf = this.delayBufs[s];
                const pos = this.delayPos[s];
                const len = this.delayLens[s];

                // Read delayed
                const readPos = (pos - len + buf.length) % buf.length;
                const delayed = buf[readPos];

                // Allpass dispersion (metallic character)
                const dispersed = this.allpass(delayed, this.apState[s]);

                // Damping lowpass
                this.dampState[s] = this.dampState[s] + dampCoeff * (dispersed - this.dampState[s]);
                const damped = this.dampState[s];

                // Feedback
                this.fb[s] = damped * fbGain;

                // Write input + feedback
                buf[pos] = driven + this.fb[s];
                this.delayPos[s] = (pos + 1) % buf.length;

                // Accumulate stereo with spread
                wetL += damped * this.spreadL[s];
                wetR += damped * this.spreadR[s];
            }

            wetL /= this.numLines;
            wetR /= this.numLines;

            // Apply spread amount
            const spreadAmt = spread;
            const wetL_final = wetL * (0.5 + spreadAmt * 0.5);
            const wetR_final = wetR * (0.5 + spreadAmt * 0.5);

            // DC blocker
            const dcL = wetL_final - this.dcIn + 0.995 * this.dcOut;
            this.dcIn = wetL_final;
            this.dcOut = dcL;

            // Mix
            const outL = dry * (1 - mix) + dcL * mix;
            const outR = dry * (1 - mix) + wetR_final * mix;

            if (numCh > 0) output[0][i] = outL;
            if (numCh > 1) output[1][i] = outR;
        }
    }

    paramChanged(name, value) {
    }
}
