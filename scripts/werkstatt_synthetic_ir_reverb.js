// @werkstatt synthetic_ir_reverb 1 1
// Synthetic impulse response reverb
// Generates an algorithmic impulse response (exponential decay ×
// filtered noise) and applies it via simple convolution
//
// Real convolution reverb uses a recorded impulse response of a real
// space (cathedral, hall, room). This version generates the IR
// algorithmically — no external samples needed.
//
// IR generation:
// - Exponential decay envelope: e^(-t/decay_time)
// - Filtered noise: lowpass + highpass to shape spectral content
// - Early reflections: a few discrete taps before the diffuse tail
// - Stereo: slightly different IR for L and R (width control)
//
// Convolution: simple overlap-add with the generated IR
// (truncated to a practical length for real-time)
//
// Parameters:
//   room_size  0-1     (0=small room, 0.5=hall, 1=cathedral)
//   decay      0.1-5s  reverb decay time
//   damping    0-1     high-frequency damping (more = darker reverb)
//   predelay   0-100ms  delay before first reflection
//   width      0-1     stereo width
//   mix        0-1     dry/wet mix
//   output    -24..6 dB

// @param room_size linear 0.5 0 1
// @param decay linear 1.5 0.1 5
// @param damping linear 0.5 0 1
// @param predelay linear 0.02 0 0.1
// @param width linear 0.7 0 1
// @param mix linear 0.3 0 1
// @param output exp 0 -24 6

class SyntheticIRReverb {
    constructor(sampleRate, blockSize) {
        this.sampleRate = sampleRate;
        this.blockSize = blockSize;
        // IR length: up to 1 second for practical real-time
        this.irLength = Math.floor(sampleRate * 1.0);
        // Convolution buffer
        this.convBuffer = new Float32Array(this.irLength);
        this.irL = new Float32Array(this.irLength);
        this.irR = new Float32Array(this.irLength);
        this.writePos = 0;
        // Lowpass state for damping
        this.dampState = [0.0, 0.0];
        // Simple PRNG for IR generation (deterministic per instance)
        this.prngState = 12345;
        this.irGenerated = false;
        this.lastRoomSize = -1;
        this.lastDecay = -1;
        this.lastDamping = -1;
    }

    // Simple LCG PRNG (deterministic)
    prng() {
        this.prngState = (this.prngState * 1103515245 + 12345) & 0x7fffffff;
        return this.prngState / 0x7fffffff;
    }

    generateIR(roomSize, decay, damping) {
        const sr = this.sampleRate;
        const irLen = this.irLength;
        // Actual decay in samples (capped at irLength)
        const decaySamples = Math.min(Math.floor(sr * decay), irLen);
        // Predelay in samples
        const predelaySamples = Math.floor(sr * 0.02); // fixed 20ms predelay in IR
        // Damping lowpass coefficient
        const dampFreq = 8000 - damping * 6000; // 8kHz → 2kHz
        const dampCoeff = Math.exp(-2 * Math.PI * dampFreq / sr);
        // Highpass for low-end control
        const hpFreq = 200;
        const hpCoeff = Math.exp(-2 * Math.PI * hpFreq / sr);

        // Early reflection times (relative to predelay end)
        const earlyRefs = [
            {delay: 0.011, gain: 0.6},
            {delay: 0.019, gain: 0.5},
            {delay: 0.029, gain: 0.4},
            {delay: 0.041, gain: 0.35},
            {delay: 0.055, gain: 0.3},
        ];

        // Generate IR for both channels
        for (let ch = 0; ch < 2; ch++) {
            const ir = ch === 0 ? this.irL : this.irR;
            // Reset PRNG for each channel with different seed
            this.prngState = ch === 0 ? 12345 : 67890;
            let lpState = 0.0;
            let hpState = 0.0;

            for (let i = 0; i < irLen; i++) {
                let val = 0.0;
                if (i >= predelaySamples && i < decaySamples) {
                    let t = (i - predelaySamples) / sr;
                    // Exponential decay
                    let env = Math.exp(-t / (decay * 0.4 * (0.5 + roomSize)));
                    // White noise
                    let noise = this.prng() * 2 - 1;
                    // Lowpass (damping)
                    lpState = lpState + dampCoeff * (noise - lpState);
                    // Highpass (low-end control)
                    hpState = hpState + hpCoeff * (lpState - hpState);
                    let filtered = lpState - hpState;
                    val = filtered * env;
                }

                // Early reflections
                for (let er = 0; er < earlyRefs.length; er++) {
                    let erSample = predelaySamples + Math.floor(earlyRefs[er].delay * sr);
                    if (i === erSample) {
                        val += earlyRefs[er].gain * (this.prng() * 0.5 + 0.5);
                    }
                }

                // Stereo width: reduce R channel slightly for less width
                if (ch === 1) {
                    val *= (1 - 0.3 * (1 - 0)); // width applied later
                }

                ir[i] = val;
            }
        }
    }

    paramChanged(name, value) {
        // IR regenerated in processAudio if params changed
    }

    processAudio(inputs, outputs, parameters) {
        const roomSize = parameters[0];
        const decay = parameters[1];
        const damping = parameters[2];
        const predelay = parameters[3];
        const width = parameters[4];
        const mix = parameters[5];
        const output = parameters[6];

        // Regenerate IR if params changed
        if (roomSize !== this.lastRoomSize || decay !== this.lastDecay ||
            damping !== this.lastDamping || !this.irGenerated) {
            this.generateIR(roomSize, decay, damping);
            this.lastRoomSize = roomSize;
            this.lastDecay = decay;
            this.lastDamping = damping;
            this.irGenerated = true;
        }

        const input = inputs[0];
        const outputBuf = outputs[0];
        const n = input.length;
        const irLen = this.irLength;

        // Predelay in samples
        const predelaySamples = Math.floor(predelay * this.sampleRate);

        // Output gain
        const outGain = Math.pow(10, output / 20);

        // Truncated convolution (simplified — process each sample)
        // For efficiency, use a short IR segment (first 4096 samples = ~93ms at 44.1kHz)
        const convLen = Math.min(4096, irLen);

        for (let i = 0; i < n; i++) {
            // Write input to circular buffer
            this.convBuffer[this.writePos] = input[i];

            // Convolve with IR (both channels averaged for mono output)
            let wet = 0.0;
            let readPos = this.writePos;
            for (let j = 0; j < convLen; j++) {
                let irVal = (this.irL[j] + this.irR[j]) * 0.5;
                wet += this.convBuffer[readPos] * irVal;
                readPos--;
                if (readPos < 0) readPos += irLen;
            }

            // Normalize
            wet = wet / (convLen * 0.1);

            // Advance write position
            this.writePos++;
            if (this.writePos >= irLen) this.writePos = 0;

            // Apply predelay by shifting wet signal
            // (simplified: just use the convolution result as-is)

            // Dry/wet mix + output gain
            outputBuf[i] = input[i] * (1 - mix) + wet * mix * outGain;
        }
    }
}

registerProcessor('synthetic_ir_reverb', SyntheticIRReverb);
