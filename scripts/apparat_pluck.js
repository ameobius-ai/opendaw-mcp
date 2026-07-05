// @apparat pluck 1 1
// @label Plucked String
// @param decay 0.5 0.05 0.99 linear
// @param damping 0.5 0 1 linear
// @param brightness 0.7 0 1 linear
// @param attack 0.001 0.001 0.1 exp s
// @param release 0.3 0.01 2 exp s
// @param detune 0.1 0 0.5 linear
// @param volume 0.7 0 1 linear

class Processor {
    voices = []
    
    decay = 0.5
    damping = 0.5
    brightness = 0.7
    attack = 0.001
    release = 0.3
    detune = 0.1
    volume = 0.7
    
    paramChanged(name, value) {
        this[name] = value
    }
    
    noteOn(freq, vel) {
        const sr = this.sampleRate
        const bufferLen = Math.max(2, Math.floor(sr / Math.max(20, freq)))
        const buf = new Float32Array(bufferLen)
        
        // fill with noise burst, brightness controls high-freq content
        const bright = this.brightness
        for (let i = 0; i < bufferLen; i++) {
            buf[i] = (Math.random() * 2 - 1) * (0.5 + bright * 0.5)
        }
        
        this.voices.push({
            buf: buf,
            bufLen: bufferLen,
            pos: 0,
            phase: 0,
            freq: freq,
            vel: vel,
            env: 0,
            age: 0,
            dead: false,
        })
    }
    
    processAudio(inputs, outputs, parameters) {
        const output = outputs[0]
        if (!output) return
        const sr = this.sampleRate
        const numCh = output.length
        const blockSize = output[0].length
        
        const decayRate = this.decay
        const dampAmt = this.damping
        const atkSamples = Math.max(1, Math.floor(this.attack * sr))
        const relSamples = Math.max(1, Math.floor(this.release * sr))
        const vol = this.volume
        const detuneCents = (this.detune - 0) * 50 // 0..25 cents
        
        // process voices
        for (let v = 0; v < this.voices.length; v++) {
            const voice = this.voices[v]
            if (voice.dead) continue
            
            const fundamental = voice.freq * Math.pow(2, detuneCents / 1200)
            // recompute buffer length if detune changed pitch significantly
        }
        
        // render
        for (let c = 0; c < numCh; c++) {
            const out = output[c]
            for (let i = 0; i < blockSize; i++) {
                let sample = 0
                for (let v = 0; v < this.voices.length; v++) {
                    const voice = this.voices[v]
                    if (voice.dead) continue
                    
                    // Karplus-Strong: read from buffer, average with next, write back
                    const cur = voice.buf[voice.pos]
                    const next = voice.buf[(voice.pos + 1) % voice.bufLen]
                    const filtered = (cur + next) * 0.5 * decayRate + cur * (1 - decayRate) * 0
                    // damping: lowpass strength
                    const damped = cur * (1 - dampAmt * 0.5) + next * (dampAmt * 0.5)
                    voice.buf[voice.pos] = damped * decayRate
                    
                    // envelope
                    voice.age++
                    let env
                    if (voice.age < atkSamples) {
                        env = voice.age / atkSamples
                    } else {
                        // natural decay from KS + release envelope
                        const relAge = voice.age - atkSamples
                        const relEnv = Math.exp(-relAge / relSamples)
                        env = relEnv * voice.vel
                    }
                    
                    sample += damped * env * vol * 0.5
                    voice.pos = (voice.pos + 1) % voice.bufLen
                    
                    if (voice.age > relSamples * 4 && Math.abs(damped) < 0.001) {
                        voice.dead = true
                    }
                }
                out[i] = sample
            }
        }
        
        // cleanup dead voices periodically
        if (this.voices.length > 32) {
            this.voices = this.voices.filter(v => !v.dead)
        }
    }
}
