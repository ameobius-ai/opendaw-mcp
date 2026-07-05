// @werkstatt phaser 1 1
// @param rate linear 0.5 0.1 8 LFO rate (Hz)
// @param depth linear 0.7 0 1 LFO depth (modulation amount)
// @param stages int 4 2 12 allpass stages (2=gentle, 4=classic, 6=deep, 12=extreme)
// @param base_freq exp 800 100 8000 base center frequency (Hz)
// @param feedback linear 0.3 -0.95 0.95 resonance feedback
// @param mix linear 0.5 0 1 dry/wet mix
// @param stereo linear 0.5 0 1 stereo phase offset (0=mono, 1=180° offset)

// Phaser — cascaded first-order allpass filters with LFO-swept center frequency.
// Classic 4-stage phaser sound (Small Stone, Phase 90).
// Allpass chain creates phase notches that sweep up/down via sine LFO.

class Phaser {
    constructor(sampleRate, blockSize) {
        this.sampleRate = sampleRate;
        this.blockSize = blockSize;

        // LFO state
        this.lfoPhaseL = 0;
        this.lfoPhaseR = 0;

        // Allpass states (per channel, per stage)
        this.maxStages = 12;
        this.apStateL = new Float32Array(this.maxStages + 1); // +1 for feedback path
        this.apStateR = new Float32Array(this.maxStages + 1);

        // Feedback state
        this.fbL = 0;
        this.fbR = 0;
    }

    // First-order allpass: H(z) = (a - z^-1) / (1 - a*z^-1)
    // Phase shift approaches 180° at high frequencies, 0° at DC
    // Center frequency controlled by coefficient a
    allpass(input, state, a) {
        const output = a * input + state[0];
        state[0] = input - a * output;
        return output;
    }

    processAudio(inputs, outputs, parameters) {
        const input = inputs[0];
        const output = outputs[0];

        const rate = parameters.rate;
        const depth = parameters.depth;
        const stages = Math.max(2, Math.min(12, Math.round(parameters.stages)));
        const baseFreq = parameters.base_freq;
        const feedback = Math.max(-0.95, Math.min(0.95, parameters.feedback));
        const mix = parameters.mix;
        const stereo = parameters.stereo;

        const numCh = Math.min(input.length, output.length);
        const len = output[0].length;

        const lfoInc = (2 * Math.PI * rate) / this.sampleRate;

        for (let s = 0; s < len; s++) {
            // LFO values (-1..1)
            const lfoL = Math.sin(this.lfoPhaseL);
            const lfoR = Math.sin(this.lfoPhaseR);

            // Advance LFO
            this.lfoPhaseL += lfoInc;
            this.lfoPhaseR += lfoInc + lfoInc * stereo * 0.5;
            if (this.lfoPhaseL > 2 * Math.PI) this.lfoPhaseL -= 2 * Math.PI;
            if (this.lfoPhaseR > 2 * Math.PI) this.lfoPhaseR -= 2 * Math.PI;

            // Sweep frequency: base ± depth * base * lfo
            const sweepL = baseFreq * (1 + depth * 0.8 * lfoL);
            const sweepR = baseFreq * (1 + depth * 0.8 * lfoR);

            // Convert frequency to allpass coefficient
            // a = (1 - sin(wT)) / (1 + sin(wT)) where wT = 2*pi*f/sr
            const wTL = (2 * Math.PI * Math.max(20, Math.min(20000, sweepL))) / this.sampleRate;
            const wTR = (2 * Math.PI * Math.max(20, Math.min(20000, sweepR))) / this.sampleRate;
            const sinWTL = Math.sin(wTL);
            const sinWTR = Math.sin(wTR);
            const aL = (1 - sinWTL) / (1 + sinWTL);
            const aR = (1 - sinWTR) / (1 + sinWTR);

            // Process left channel
            if (numCh >= 1) {
                const dryL = input[0][s];
                let wetL = dryL + this.fbL * feedback;

                // Cascade through allpass stages
                for (let st = 0; st < stages; st++) {
                    wetL = this.allpass(wetL, this.apStateL, st, aL);
                }

                // Store feedback
                this.fbL = wetL;

                // Output: dry/wet mix
                output[0][s] = dryL * (1 - mix) + wetL * mix;
            }

            // Process right channel
            if (numCh >= 2) {
                const dryR = input[1][s];
                let wetR = dryR + this.fbR * feedback;

                for (let st = 0; st < stages; st++) {
                    wetR = this.allpass(wetR, this.apStateR, st, aR);
                }

                this.fbR = wetR;

                output[1][s] = dryR * (1 - mix) + wetR * mix;
            } else if (numCh === 1 && output.length >= 2) {
                // Mono input → stereo output: copy left to right
                output[1][s] = output[0][s];
            }
        }
    }
}

const phaser = new Phaser(sampleRate, blockSize);
phaser.processAudio(inputs, outputs, parameters);
