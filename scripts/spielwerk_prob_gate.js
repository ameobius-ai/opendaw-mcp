// @spielwerk prob_gate 1 1
// @label Probability Gate
// Subtractive MIDI effect — passes notes through with per-note probability.
// Creates generative patterns from static sequences by randomly dropping notes.
// Brian Eno "oblique strategies", generative ambient, stochastic composition.

// @param chance     0.7  0  1   linear   // global pass probability (0=silence, 1=pass all)
// @param variation  0    0  1   linear   // per-step chance variation (0=static, 1=full random spread)
// @param seed       42   1  9999 linear   // random seed for reproducibility
// @param mode       0    0  2   linear   // 0=uniform, 1=position-based (downbeat more likely), 2=pitch-based (high notes more likely)
// @param min_pitch  0    0  127 linear   // notes below this pitch always pass
// @param max_pitch  127  0  127 linear   // notes above this pitch always pass
// @param velocity_boost 0.1 0 0.5 linear // velocity boost for surviving notes (compensate for dropped notes)
// @param hold       0    0  1   linear   // 0=independent per-note, 1=if a note passes, next likely passes too (momentum)

class Processor {
    chance = 0.7
    variation = 0
    seed = 42
    mode = 0
    min_pitch = 0
    max_pitch = 127
    velocity_boost = 0.1
    hold = 0

    // LCG random state
    _rng = 0
    _lastPassed = true

    paramChanged(label, value) {
        if (label === "chance") this.chance = value
        else if (label === "variation") this.variation = value
        else if (label === "seed") this.seed = Math.round(value)
        else if (label === "mode") this.mode = Math.round(value)
        else if (label === "min_pitch") this.min_pitch = Math.round(value)
        else if (label === "max_pitch") this.max_pitch = Math.round(value)
        else if (label === "velocity_boost") this.velocity_boost = value
        else if (label === "hold") this.hold = value
    }

    _nextRand() {
        // LCG: seed * 1103515245 + 12345 mod 2^31
        this._rng = (this._rng * 1103515245 + 12345) & 0x7FFFFFFF
        return this._rng / 0x7FFFFFFF  // 0..1
    }

    *process(block, events) {
        // Reset RNG at block start if seed changed
        if (this._rng === 0) this._rng = this.seed

        for (const ev of events) {
            // Forced pass zones
            if (ev.pitch <= this.min_pitch || ev.pitch >= this.max_pitch) {
                yield {
                    position: ev.position,
                    duration: ev.duration,
                    pitch: ev.pitch,
                    velocity: Math.min(1, ev.velocity + this.velocity_boost * 0.5),
                    cent: ev.cent || 0
                }
                continue
            }

            // Base chance with variation
            let noteChance = this.chance
            if (this.variation > 0) {
                const r = this._nextRand()
                noteChance = this.chance + (r - 0.5) * this.variation
                noteChance = Math.max(0, Math.min(1, noteChance))
            }

            // Mode-specific probability adjustment
            if (this.mode === 1) {
                // Position-based: notes near bar start more likely to pass
                const barPos = ev.position % block.ppqn
                const posNorm = 1 - (barPos / block.ppqn)
                noteChance = noteChance * (0.5 + 0.5 * posNorm)
            } else if (this.mode === 2) {
                // Pitch-based: higher notes more likely to pass (sparkle)
                const pitchNorm = ev.pitch / 127
                noteChance = noteChance * (0.4 + 0.6 * pitchNorm)
            }

            // Hold/momentum: if last note passed, boost this one
            if (this.hold > 0 && this._lastPassed) {
                noteChance = noteChance + this.hold * (1 - noteChance) * 0.5
                noteChance = Math.min(1, noteChance)
            }

            // Roll the dice
            const roll = this._nextRand()
            const passed = roll < noteChance
            this._lastPassed = passed

            if (passed) {
                // Boost velocity slightly to compensate for dropped notes
                const boost = 1 + this.velocity_boost * (1 - this.chance)
                yield {
                    position: ev.position,
                    duration: ev.duration,
                    pitch: ev.pitch,
                    velocity: Math.max(0.01, Math.min(1, ev.velocity * boost)),
                    cent: ev.cent || 0
                }
            }
            // If not passed: note is dropped (not yielded)
        }
    }

    reset() {
        this._rng = this.seed
        this._lastPassed = true
    }
}
