// @werkstatt haas_stereo_widener 1 1
// Haas stereo widener — creates pseudo-stereo via short delay on one channel
// Based on the Haas (precedence) effect: delays < 30ms are perceived as spatial,
// not as echo. Classic technique for widening mono sources.

// @param delay linear 5 1 30   // Delay in ms (1-30, default 5). <10ms = subtle widen, 15-25ms = dramatic
// @param width linear 0.8 0 1   // Width amount (0=mono, 0.5=original, 1=full Haas). Mix between dry mono and Haas stereo
// @param channel int 1 0 1      // Which channel gets the delay (0=left, 1=right). Flips the stereo image
// @param feedback linear 0 0 0.3 // Feedback into delay line (0-0.3). Subtle regeneration, 0=clean
// @param mix linear 1 0 1       // Dry/wet mix (0=original, 1=full Haas effect)

class HaasProcessor {
    constructor() {
        this.delaySamples = 0;
        this.delayBuffer = new Float32Array(2048);
        this.writePos = 0;
        this.readPos = 0;
        this.feedbackSample = 0;
    }

    paramChanged(name, value) {
        if (name === 'delay') {
            this.delaySamples = Math.max(1, Math.round(value * 0.001 * this.sampleRate));
        }
    }

    processAudio(inputs, outputs, parameters) {
        const input = inputs[0];
        const output = outputs[0];
        if (!input || !output) return;
        if (input.length < 2 || output.length < 2) return;

        const delayMs = parameters['delay'][0];
        const width = parameters['width'][0];
        const channel = Math.round(parameters['channel'][0]);
        const feedback = parameters['feedback'][0];
        const mix = parameters['mix'][0];

        const targetDelay = Math.max(1, Math.round(delayMs * 0.001 * this.sampleRate));
        if (targetDelay !== this.delaySamples) {
            this.delaySamples = targetDelay;
        }

        const bufLen = this.delayBuffer.length;
        const numFrames = input[0].length;

        for (let i = 0; i < numFrames; i++) {
            const leftIn = input[0][i];
            const rightIn = input[1] ? input[1][i] : leftIn;

            // Mono sum for Haas source
            const mono = (leftIn + rightIn) * 0.5;

            // Write to delay buffer
            this.delayBuffer[this.writePos] = mono + this.feedbackSample * feedback;
            this.writePos = (this.writePos + 1) % bufLen;

            // Read delayed sample
            this.readPos = (this.writePos - this.delaySamples + bufLen) % bufLen;
            const delayed = this.delayBuffer[this.readPos];
            this.feedbackSample = delayed;

            // Build Haas stereo image
            // One channel = dry mono, other = delayed mono
            let haasLeft, haasRight;
            if (channel === 0) {
                haasLeft = delayed;   // left gets delay
                haasRight = mono;     // right is dry
            } else {
                haasLeft = mono;      // left is dry
                haasRight = delayed;  // right gets delay
            }

            // Width control: blend between mono and Haas stereo
            // width=0 → full mono (both = mono), width=1 → full Haas
            const outLeft = mono * (1 - width) + haasLeft * width;
            const outRight = mono * (1 - width) + haasRight * width;

            // Dry/wet mix
            output[0][i] = leftIn * (1 - mix) + outLeft * mix;
            output[1][i] = rightIn * (1 - mix) + outRight * mix;
        }
    }
}
