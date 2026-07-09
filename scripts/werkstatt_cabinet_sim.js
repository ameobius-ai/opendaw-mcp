// @werkstatt cabinet_sim 1 1
// Guitar cabinet speaker simulator
// Simulates the frequency response of a guitar speaker cabinet
// (4x12 closed-back, 1x12 open-back, etc.)
//
// Speaker cabinets have a characteristic sound:
// - Limited high-frequency response (rolls off above ~5-6 kHz)
// - Resonance peak around 80-120 Hz (cab resonance)
// - Midrange coloration (cone breakup, box resonance)
// - Slight compression at high volumes
//
// Implementation: speaker EQ (lowpass + peak) + box resonance +
// cone distortion (soft clip) + slight phase smear
//
// Parameters:
//   cab_type   0.0-1.0  (0=closed-back 4x12, 0.5=1x12 open-back, 1.0=tweed combo)
//   resonance  0.0-1.0  cabinet resonance amount (low-end bump)
//   presence   0.0-1.0  high-frequency presence control
//   drive      0.0-1.0  speaker cone excursion (soft distortion at high drive)
//   mix        0.0-1.0  dry/wet mix
//   output    -24..6 dB output gain

// @param cab_type 0 0 1 linear
// @param resonance 0.5 0 1 linear
// @param presence 0.3 0 1 linear
// @param drive 0.3 0 1 linear
// @param mix 0.8 0 1 linear
// @param output 0 -24 6 exp

class CabinetSim {
    constructor(sampleRate, blockSize) {
        this.sampleRate = sampleRate;
        this.blockSize = blockSize;
        // State for lowpass (speaker high-freq rolloff)
        this.lpState = [0.0, 0.0];
        // State for resonance peak (cab box resonance)
        this.resState = [0.0, 0.0];
        // State for midrange bandpass (cone coloration)
        this.midState = [0.0, 0.0];
        // DC blocker
        this.dcState = 0.0;
        this.dcR = 0.995;
    }

    paramChanged(name, value) {
        // Precompute filter coefficients when params change
        if (name === "cab_type" || name === "presence" || name === "resonance") {
            // Speaker cutoff: closed-back 4x12 ~ 5kHz, open-back ~ 4kHz, tweed ~ 3.5kHz
            this.lpFreq = 3500 + (1 - this.cabType) * 1500;
            this.lpCoeff = Math.exp(-2 * Math.PI * this.lpFreq / this.sampleRate);

            // Resonance frequency: 4x12 ~ 100Hz, 1x12 ~ 85Hz, tweed ~ 70Hz
            this.resFreq = 70 + (1 - this.cabType) * 30;
            this.resCoeff = Math.exp(-2 * Math.PI * this.resFreq / this.sampleRate);
            this.resGain = 1 + this.resonance * 1.5;

            // Presence: controls high-mid shelf
            this.presFreq = 2500 + this.presence * 1500;
            this.presCoeff = Math.exp(-2 * Math.PI * this.presFreq / this.sampleRate);
        }
    }

    processAudio(inputs, outputs, parameters) {
        const cabType = parameters[0]; // cab_type
        const resonance = parameters[1]; // resonance
        const presence = parameters[2]; // presence
        const drive = parameters[3]; // drive
        const mix = parameters[4]; // mix
        const output = parameters[5]; // output

        const input = inputs[0];
        const outputBuf = outputs[0];
        const n = input.length;

        // Recompute coefficients if needed
        const lpFreq = 3500 + (1 - cabType) * 1500;
        const lpCoeff = Math.exp(-2 * Math.PI * lpFreq / this.sampleRate);
        const resFreq = 70 + (1 - cabType) * 30;
        const resCoeff = Math.exp(-2 * Math.PI * resFreq / this.sampleRate);
        const resGain = 1 + resonance * 1.5;
        const presFreq = 2500 + presence * 1500;
        const presCoeff = Math.exp(-2 * Math.PI * presFreq / this.sampleRate);
        const presGain = 0.7 + presence * 0.6;

        // Output gain
        const outGain = Math.pow(10, output / 20);

        // Drive amount for soft clip
        const drv = 0.5 + drive * 2.0;

        for (let i = 0; i < n; i++) {
            let sample = input[i];

            // DC blocker
            let dcOut = sample - this.dcState;
            this.dcState = sample + this.dcR * this.dcState;
            sample = dcOut;

            // 1. Speaker lowpass (high-freq rolloff) — one-pole
            this.lpState[0] = this.lpState[0] + lpCoeff * (sample - this.lpState[0]);
            let lp = this.lpState[0];

            // 2. Cabinet resonance — peak filter around resFreq
            // Simple resonant one-pole with feedback
            let resInput = lp * resGain;
            this.resState[0] = this.resState[0] + resCoeff * (resInput - this.resState[0]);
            let res = this.resState[0] * resGain;

            // 3. Presence boost — high-mid shelf
            this.midState[0] = this.midState[0] + presCoeff * (lp - this.midState[0]);
            let pres = (lp - this.midState[0]) * presGain;

            // Combine: lowpass + resonance + presence
            let processed = lp + res * 0.5 + pres * 0.3;

            // 4. Speaker cone soft clip (drive)
            if (drv > 0.5) {
                processed = processed * drv;
                processed = processed / (1 + Math.abs(processed)); // soft clip
                processed = processed / drv * (drv / (drv + 0.5));
            }

            // 5. Dry/wet mix
            let wet = processed * outGain;
            let dry = input[i];
            outputBuf[i] = dry * (1 - mix) + wet * mix;
        }
    }
}

// Register the processor
registerProcessor('cabinet_sim', CabinetSim);
