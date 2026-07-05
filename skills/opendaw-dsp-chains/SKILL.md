---
name: opendaw-dsp-chains
description: "DSP signal chain recipes for openDAW Werkstatt effects. Production-ready chains: vocal, guitar, drum bus, synth bass, lofi, mastering, ambient, acid, cinematic. Which DSP scripts to combine, in what order, with what parameters. 62 DSP scripts, 11+ chains."
tags: [opendaw, dsp, chains, production, werkstatt, sound-design, mixing]
---

# openDAW DSP Signal Chains

Production-ready signal chains combining Werkstatt DSP scripts. Each chain is a recipe: which scripts, what order, what parameters. Not theory — concrete `set_script_device_code` + `set_script_param` calls.

## Когда использовать

- Юзер просит "сделай вокальную цепь", "гитарный тракт", "chain для баса"
- Нужно скомбинировать несколько DSP эффектов на один трек
- Юзер хочет конкретный жанровый звук (lofi, acid, ambient, rock)
- Нужно mastering chain из DSP скриптов

## Базовый паттерн

```python
# 1. Создать трек
await mcp_opendaw_create_synth_track("Vocal", "vaporisateur")

# 2. Добавить Werkstatt effects (каждый — отдельный device)
await mcp_opendaw_add_effect(0, "werkstatt")  # device 0
await mcp_opendaw_add_effect(0, "werkstatt")  # device 1
await mcp_opendaw_add_effect(0, "werkstatt")  # device 2

# 3. Загрузить DSP код в каждый
await mcp_opendaw_set_script_device_code("werkstatt", 0, 0, eq_code)
await mcp_opendaw_set_script_device_code("werkstatt", 0, 1, comp_code)
await mcp_opendaw_set_script_device_code("werkstatt", 0, 2, sat_code)

# 4. Настроить параметры
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "band1_gain", -3)
await mcp_opendaw_set_script_param("werkstatt", 0, 1, "threshold", 0.5)
```

## Chains

### 1. Vocal Chain

```
Input → paraeq → compressor → deesser → exciter → limiter → Output
```

```python
# EQ: cut 200Hz mud, boost 3kHz presence
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "band1_freq", 200)  # cut
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "band1_gain", -4)
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "band2_freq", 3000)  # boost
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "band2_gain", 3)

# Compressor: gentle, transparent
await mcp_opendaw_set_script_param("werkstatt", 0, 1, "threshold", 0.5)
await mcp_opendaw_set_script_param("werkstatt", 0, 1, "ratio", 3)
await mcp_opendaw_set_script_param("werkstatt", 0, 1, "attack", 0.01)
await mcp_opendaw_set_script_param("werkstatt", 0, 1, "release", 0.1)

# De-esser: tame sibilance
await mcp_opendaw_set_script_param("werkstatt", 0, 2, "freq", 6000)
await mcp_opendaw_set_script_param("werkstatt", 0, 2, "threshold", 0.4)

# Exciter: air
await mcp_opendaw_set_script_param("werkstatt", 0, 3, "freq", 8000)
await mcp_opendaw_set_script_param("werkstatt", 0, 3, "harmonics", 0.3)

# Limiter: catch peaks
await mcp_opendaw_set_script_param("werkstatt", 0, 4, "ceiling", 0.95)
```

### 2. Guitar Chain

```
Input → waveshaper → moog_ladder → chorus → stereo_delay → Output
```

```python
# Waveshaper: tube-like overdrive (tanh curve)
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "curve", 0)  # tanh
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "drive", 0.6)
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "bias", 0.1)
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "mix", 0.8)

# Moog ladder: tone shaping
await mcp_opendaw_set_script_param("werkstatt", 0, 1, "cutoff", 2500)
await mcp_opendaw_set_script_param("werkstatt", 0, 1, "resonance", 0.3)
await mcp_opendaw_set_script_param("werkstatt", 0, 1, "mode", 0)  # LP
await mcp_opendaw_set_script_param("werkstatt", 0, 1, "warmth", 0.4)

# Chorus: width
await mcp_opendaw_set_script_param("werkstatt", 0, 2, "rate", 0.5)
await mcp_opendaw_set_script_param("werkstatt", 0, 2, "depth", 0.3)

# Delay: slapback
await mcp_opendaw_set_script_param("werkstatt", 0, 3, "time", 0.15)
await mcp_opendaw_set_script_param("werkstatt", 0, 3, "feedback", 0.2)
await mcp_opendaw_set_script_param("werkstatt", 0, 3, "mix", 0.3)
```

### 3. Drum Bus Chain

```
Input → paraeq → transient → compressor → stereowidth → limiter → Output
```

```python
# EQ: clean up lows, add air
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "hp_freq", 30)
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "band1_freq", 60)
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "band1_gain", 2)
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "lp_freq", 18000)

# Transient: punch
await mcp_opendaw_set_script_param("werkstatt", 0, 1, "attack", 0.4)
await mcp_opendaw_set_script_param("werkstatt", 0, 1, "sustain", 0.6)

# Compressor: glue
await mcp_opendaw_set_script_param("werkstatt", 0, 2, "threshold", 0.6)
await mcp_opendaw_set_script_param("werkstatt", 0, 2, "ratio", 2)
await mcp_opendaw_set_script_param("werkstatt", 0, 2, "attack", 0.03)
await mcp_opendaw_set_script_param("werkstatt", 0, 2, "release", 0.15)

# Stereo width
await mcp_opendaw_set_script_param("werkstatt", 0, 3, "width", 1.3)

# Limiter
await mcp_opendaw_set_script_param("werkstatt", 0, 4, "ceiling", 0.9)
```

### 4. Synth Bass Chain

```
Input → moog_ladder → waveshaper → compressor → Output
```

```python
# Moog ladder: acid filter
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "cutoff", 500)
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "resonance", 0.7)
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "drive", 0.2)
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "mode", 0)  # LP

# Waveshaper: harmonic richness
await mcp_opendaw_set_script_param("werkstatt", 0, 1, "curve", 3)  # Chebyshev
await mcp_opendaw_set_script_param("werkstatt", 0, 1, "drive", 1.2)
await mcp_opendaw_set_script_param("werkstatt", 0, 1, "harmonics", 0.5)
await mcp_opendaw_set_script_param("werkstatt", 0, 1, "mix", 0.6)

# Compressor: tight dynamics
await mcp_opendaw_set_script_param("werkstatt", 0, 2, "threshold", 0.4)
await mcp_opendaw_set_script_param("werkstatt", 0, 2, "ratio", 4)
await mcp_opendaw_set_script_param("werkstatt", 0, 2, "attack", 0.005)
await mcp_opendaw_set_script_param("werkstatt", 0, 2, "release", 0.08)
```

### 5. Lofi Character Chain

```
Input → darksat → bitcrusher → vibrato → tape_delay → Output
```

```python
# Tape saturation: warm, grainy
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "drive", 0.5)
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "bias", 0.2)
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "tone", 0.3)  # darker

# Bitcrusher: vintage digital
await mcp_opendaw_set_script_param("werkstatt", 0, 1, "crush", 0.6)
await mcp_opendaw_set_script_param("werkstatt", 0, 1, "slew", 0.3)
await mcp_opendaw_set_script_param("werkstatt", 0, 1, "mix", 0.5)

# Vibrato: wow/flutter
await mcp_opendaw_set_script_param("werkstatt", 0, 2, "rate", 0.8)
await mcp_opendaw_set_script_param("werkstatt", 0, 2, "depth", 0.15)

# Tape delay: slapback
await mcp_opendaw_set_script_param("werkstatt", 0, 3, "time", 0.12)
await mcp_opendaw_set_script_param("werkstatt", 0, 3, "feedback", 0.3)
await mcp_opendaw_set_script_param("werkstatt", 0, 3, "wow", 0.3)
await mcp_opendaw_set_script_param("werkstatt", 0, 3, "flutter", 0.2)
await mcp_opendaw_set_script_param("werkstatt", 0, 3, "saturation", 0.4)
```

### 6. Mastering Chain (DSP-only)

```
Input → paraeq → multiband_comp → exciter → stereowidth → limiter → Output
```

```python
# EQ: final balance
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "band1_freq", 100)
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "band1_gain", -1)
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "band2_freq", 2500)
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "band2_gain", 1)
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "band3_freq", 10000)
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "band3_gain", 2)

# Multiband: 3-band control
await mcp_opendaw_set_script_param("werkstatt", 0, 1, "crossover1", 250)
await mcp_opendaw_set_script_param("werkstatt", 0, 1, "crossover2", 2500)
await mcp_opendaw_set_script_param("werkstatt", 0, 1, "low_threshold", 0.6)
await mcp_opendaw_set_script_param("werkstatt", 0, 1, "mid_threshold", 0.5)
await mcp_opendaw_set_script_param("werkstatt", 0, 1, "high_threshold", 0.5)

# Exciter: sparkle
await mcp_opendaw_set_script_param("werkstatt", 0, 2, "freq", 6000)
await mcp_opendaw_set_script_param("werkstatt", 0, 2, "harmonics", 0.2)
await mcp_opendaw_set_script_param("werkstatt", 0, 2, "drive", 0.3)

# Stereo width
await mcp_opendaw_set_script_param("werkstatt", 0, 3, "width", 1.2)
await mcp_opendaw_set_script_param("werkstatt", 0, 3, "lowTrim", 0.8)

# Limiter: loudness
await mcp_opendaw_set_script_param("werkstatt", 0, 4, "ceiling", 0.95)
await mcp_opendaw_set_script_param("werkstatt", 0, 4, "release", 0.05)
```

### 7. Acid House Chain

```
Input → moog_ladder → overdrive → stereo_delay → Output
```

```python
# Moog ladder: squelchy
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "cutoff", 600)
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "resonance", 0.9)
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "drive", 0.4)

# Overdrive: grit
await mcp_opendaw_set_script_param("werkstatt", 0, 1, "drive", 0.5)
await mcp_opendaw_set_script_param("werkstatt", 0, 1, "mix", 0.7)

# Delay: dotted eighth
await mcp_opendaw_set_script_param("werkstatt", 0, 2, "time", 0.375)
await mcp_opendaw_set_script_param("werkstatt", 0, 2, "feedback", 0.35)
await mcp_opendaw_set_script_param("werkstatt", 0, 2, "mix", 0.25)
```

### 8. Ambient Pad Chain

```
Input → reverb → chorus → stereo_delay → auto_pan → Output
```

```python
# Reverb: large space
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "room", 0.8)
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "decay", 0.7)
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "damp", 0.4)
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "mix", 0.6)

# Chorus: detune
await mcp_opendaw_set_script_param("werkstatt", 0, 1, "rate", 0.3)
await mcp_opendaw_set_script_param("werkstatt", 0, 1, "depth", 0.5)

# Delay: long, atmospheric
await mcp_opendaw_set_script_param("werkstatt", 0, 2, "time", 0.5)
await mcp_opendaw_set_script_param("werkstatt", 0, 2, "feedback", 0.5)
await mcp_opendaw_set_script_param("werkstatt", 0, 2, "mix", 0.4)

# Auto-pan: movement
await mcp_opendaw_set_script_param("werkstatt", 0, 3, "rate", 0.2)
await mcp_opendaw_set_script_param("werkstatt", 0, 3, "depth", 0.5)
```

### 9. Vocoder / Vocal FX Chain

```
Input → vocoder → formant_filter → reverb → Output
```

```python
# Vocoder: 16-band
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "bands", 16)
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "carrier", 1)  # saw
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "mix", 0.8)

# Formant: vowel shift
await mcp_opendaw_set_script_param("werkstatt", 0, 1, "formant1", 700)
await mcp_opendaw_set_script_param("werkstatt", 0, 1, "formant2", 1200)
await mcp_opendaw_set_script_param("werkstatt", 0, 1, "formant3", 2600)

# Reverb: space
await mcp_opendaw_set_script_param("werkstatt", 0, 2, "decay", 0.5)
await mcp_opendaw_set_script_param("werkstatt", 0, 2, "mix", 0.4)
```

### 10. Distortion / Metal Chain

```
Input → waveshaper → moog_ladder → compressor → bitcrusher → Output
```

```python
# Waveshaper: cubic (aggressive)
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "curve", 1)  # cubic
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "drive", 2.5)
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "bias", 0)

# Moog ladder: tone cut
await mcp_opendaw_set_script_param("werkstatt", 0, 1, "cutoff", 3000)
await mcp_opendaw_set_script_param("werkstatt", 0, 1, "resonance", 0.4)
await mcp_opendaw_set_script_param("werkstatt", 0, 1, "mode", 0)  # LP

# Compressor: tight
await mcp_opendaw_set_script_param("werkstatt", 0, 2, "ratio", 6)
await mcp_opendaw_set_script_param("werkstatt", 0, 2, "attack", 0.002)

# Bitcrusher: digital grit
await mcp_opendaw_set_script_param("werkstatt", 0, 3, "crush", 0.3)
await mcp_opendaw_set_script_param("werkstatt", 0, 3, "mix", 0.3)
```

### 11. Cinematic Drum Room Chain

```
Input → paraeq → transient → convolution_reverb → stereowidth → Output
```

```python
# ParaEQ: remove boxiness
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "band2_freq", 350)
await mcp_opendaw_set_script_param("werkstatt", 0, 0, "band2_gain", -3)

# Transient: punch up attack
await mcp_opendaw_set_script_param("werkstatt", 0, 1, "attack", 1.5)
await mcp_opendaw_set_script_param("werkstatt", 0, 1, "sustain", 0.7)

# Convolution reverb: large room ambience
await mcp_opendaw_set_script_param("werkstatt", 0, 2, "room_size", 0.8)
await mcp_opendaw_set_script_param("werkstatt", 0, 2, "decay", 0.6)
await mcp_opendaw_set_script_param("werkstatt", 0, 2, "damping", 0.3)
await mcp_opendaw_set_script_param("werkstatt", 0, 2, "predelay", 0.03)
await mcp_opendaw_set_script_param("werkstatt", 0, 2, "early_late", 0.4)
await mcp_opendaw_set_script_param("werkstatt", 0, 2, "width", 0.8)
await mcp_opendaw_set_script_param("werkstatt", 0, 2, "mix", 0.35)

# Stereo width: widen the room
await mcp_opendaw_set_script_param("werkstatt", 0, 3, "width", 1.2)
await mcp_opendaw_set_script_param("werkstatt", 0, 3, "lowTrim", 0.5)
```

## Pitfalls

- **Order matters**: EQ before compression = different sound than compression before EQ. Generally: corrective EQ → dynamics → saturation → time effects (reverb/delay)
- **Don't chain 2 saturations**: waveshaper + tube_saturator + darksat = mush. Pick one saturation type per chain
- **Reverb always last**: reverb before compression kills the space
- **Limiter always last**: it's the ceiling, nothing after it
- **Too many effects = latency**: each Werkstatt adds processing. 5-6 max per chain
- **Moog ladder self-oscillation**: resonance > 0.9 can scream. Use with caution on bright sources
- **Vocoder needs carrier input**: the carrier oscillator is internal, but modulator needs to be the track signal

## DSP Script Index

| Family | Scripts |
|--------|---------|
| Saturation | darksat, waveshaper, tube_saturator, overdrive, coldfold |
| Dynamics | compressor, lookahead, limiter, exciter, deesser, transient, noisegate, multiband_comp |
| Filter | multifilter, moog_ladder, allpass, comb, formant |
| Modulation | chorus, flanger, phaser, tremolo, vibrato, auto_pan |
| Reverb | reverb, spring_reverb, shimmer, convolution_reverb |
| Delay | stereo_delay, tape_delay |
| EQ | paraeq, graphic_eq, dynamic_eq |
| Pitch | pitch_shift, ringmod_env, harmonizer |
| Time | granular_stretch, paulstretch |
| Stereo | stereowidth, auto_pan |
| Spectral/FX | spectral_gate, vocoder, reverse, scratch, looper |
