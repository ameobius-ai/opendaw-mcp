# Changelog

## v1.136.0 (2026-07-05)

- **`create_jazz_arrangement` orchestration tool (329 MCP tools)** — eighth multi-track genre arrangement. Jazz with ii-V-I harmony and swing feel across 4 tracks: drums (swing ride spang-a-lang — ride on every beat + swung 8th at 0.66, ghost snare comping, feathered bass drum), bass (walking bass — quarter notes through ii-V-I using chord tones root/third/fifth/seventh, min7 on ii and V, maj7 on I, smooth voice leading), piano (comping — shell voicings root+third+seventh, syncopated off-beat stabs with space between), horn (bluesy head — melodic line following ii-V-I changes, blue notes, swing 8th phrasing at 0.66). ii-V-I is the fundamental jazz chord change — every other genre uses different harmony. Swing 8ths (triplet feel at 0.66) is the rhythmic signature separating jazz from all straight-time genres. F default (classic jazz key for horns). 50-220 BPM, default 120 (medium swing). 4-32 bars. Third organic 4-track arrangement. 72 orchestration tools. 329 MCP tools
- **1681 unit tests** (+21)

## v1.135.0 (2026-07-05)

- **`create_rock_arrangement` orchestration tool (328 MCP tools)** — seventh multi-track genre arrangement. Classic rock with blues-based I-IV-V harmony across 4 tracks: drums (rock beat — kick on 1&3, snare on 2&4, crash on downbeat, tom fill at bar transition), bass (root-fifth walking bassline locking with kick drum, octave walks between changes), guitar (power chords — root+fifth, no third, ambiguous major/minor, with palm-muted downstrokes), keys (major triad pads — root+major third+fifth, sustained, adding the third that guitar omits). Blues form: I-I-IV-I-V-IV-I-V (8-bar compressed). E default (most common rock guitar key — open strings). 80-180 BPM, default 120. 4-16 bars. Second organic 4-track arrangement. 71 orchestration tools. 328 MCP tools
- **1660 unit tests** (+20)

## v1.134.0 (2026-07-05)

- **`create_afrobeat_arrangement` orchestration tool (327 MCP tools)** — sixth multi-track genre arrangement. First non-electronic genre. Fela Kuti-style afrobeat across 4 tracks: drums (layered polyrhythm — syncopated kick + continuous shaker + clave accents + triplet perc, 12/8 feel in 4/4 time), bass (repetitive ostinato — root/octave/fifth/fourth 16th-note pattern, driving and hypnotic, locks with kick), horns (brass section call-and-response — sustained minor triads as calls, syncopated stabs as responses, minor key intervals root/min3/fourth/fifth/min7/octave), guitar (off-beat "chanka" stabs — two-note voicings root+fifth and min3+fifth, percussive and tight). First arrangement with 4 tracks. F minor default (Fela's key). 95-135 BPM, default 120. 8-32 bars. 70 orchestration tools. 327 MCP tools
- **1640 unit tests** (+25)

## v1.133.0 (2026-07-05)

- **`create_dubstep_arrangement` orchestration tool (326 MCP tools)** — fifth multi-track genre arrangement. Dubstep across 3 tracks: drums (half-time at 140 BPM — kick on 1, snare on 3, feels like 70 BPM, with perc fills and ghost notes), bass (wobble bass — sustained root with rapid octave/fifth stabs simulating LFO-driven cutoff modulation, the "wub-wub"), lead (minor arpeggio — root/min3/fifth/min7/octave, dark and atmospheric, continuous 16th notes). Half-time is the fundamental difference from all other arrangements: house/techno/trap are straight time, dubstep swings at half speed. G minor default. 130-155 BPM, default 140. 4-16 bars. 69 orchestration tools. 326 MCP tools
- **1615 unit tests** (+21)

## v1.132.0 (2026-07-05)

- **`create_techno_arrangement` orchestration tool (325 MCP tools)** — fourth multi-track genre arrangement. Berlin/Detroit techno across 3 tracks: drums (relentless four-on-floor with industrial closed hats, open hat accents, claps on 2+4), bass (sustained sub-bass drone with root→fifth shifts — not rhythmic but continuous, the hypnotic foundation), stabs (Detroit percussive atonal stabs on off-beats — single notes, not chords, minor intervals root/min3/fifth/min7/octave). Key difference from house: sub-bass drone instead of off-beat bass, percussive stabs instead of chord stabs. C minor default. Tempo-aware 120-150 BPM, default 130. Minimum 8 bars (techno needs longer forms). 68 orchestration tools. 325 MCP tools
- **1594 unit tests** (+20)

## v1.131.0 (2026-07-05)

- **`create_trap_arrangement` orchestration tool (324 MCP tools)** — third multi-track genre arrangement. Complete trap section across 3 tracks: drums (trap hi-hat rolls with triplet bursts, syncopated kick, snare on 3, ghost roll), bass (808 sub-bass slides — long sustained root with slides to fourth/fifth, negative pitch offsets, octave 1 sub-bass territory), melody (bell plucks in minor key — root/minor3/fifth/minor7 with echo). 808 slides are the signature — long glides between root notes creating dark low-end. Melody 3 octaves above bass. F# minor default (most common trap key). Tempo-aware 120-170 BPM, default 140. 4-32 bars. 67 orchestration tools. 324 MCP tools
- **1517 unit tests** (+20)

## v1.130.0 (2026-07-05)

- **`create_house_arrangement` orchestration tool (323 MCP tools)** — second multi-track genre arrangement. Complete house music section across 3 tracks: drums (four-on-the-floor kick, open hats on off-beats, clap on 2+4), bass (off-beat sustained between kicks — the "untz-untz" groove), stabs (minor triad on beats 1+3 with off-beant variant). Kick and bass perfectly interleaved — never overlap. Stabs 2 octaves above bass. Tempo-aware 110-140 BPM, default 124. 4-32 bars. 66 orchestration tools. 323 MCP tools
- **1497 unit tests** (+18)

## v1.129.0 (2026-07-05)

- **`create_dnb_arrangement` orchestration tool (322 MCP tools)** — first multi-track genre arrangement. Generates a complete DnB section across 3 tracks in one call: drums (Amen-style breakbeat with syncopated kicks, ghost notes), bass (Reese-style with sustained notes + syncopated stabs + octave jump), pad (sustained minor triad, 2 bars per chord). Elements lock rhythmically — bass sustains when drums break, stabs when drums roll. Pad 2 octaves above bass. Tempo-aware (140-200 BPM, default 174). Configurable track indices. 4-32 bars. 65 orchestration tools. 322 MCP tools
- **1479 unit tests** (+17)

## v1.128.0 (2026-07-05)

- **`werkstatt_decrackle.js` DSP script (98 DSP, 79 Werkstatt)** — de-crackle: removes continuous crackle from vinyl, tape, and old recordings. Adaptive crackle modeling: tracks crackle energy and signal energy separately, adaptive threshold rises with signal level and falls with crackle density. Crackle rate estimation (10-200 crackles/sec). Crackle detection: short spikes above adaptive threshold but below signal level. Extent finding (1-8 samples) + interpolation (Hermite/linear blend via smooth param). Strength blend controls removal amount. iZotope RX De-crackle / CEDAR Decrackle style — fourth restoration processor. 7 params (strength/sensitivity/freq_est/smooth/adaptive/mix/output). 98 DSP scripts, 79 Werkstatt
- **1462 unit tests** (+22)

## v1.127.0 (2026-07-05)

- **`create_electronic_bass` orchestration tool (321 MCP tools)** — genre-specific electronic basslines. Bass as a rhythmic engine that locks with kick drum — fundamentally different from melodic basslines. 6 variants: house_offbeat (sustained notes between kicks, "untz-untz" feel), techno_sub (one long root per bar, Berlin minimal), dnb_reese (sustained on 1 + syncopated stabs, Noisia), dubstep_wobble (quarters on 1+3, wub pattern on 2+4 with fifth movement, Skrillex), acid_303 (16th root/octave alternation with fifth drops, TB-303 squelch, Phuture), garage_2step (bass on 1 and 2.66 with ghost, MJ Cole/Disclosure). Pitch offsets: root/0, fifth/7, octave/12. 1-bar cycle. 64 orchestration tools. 321 MCP tools
- **1440 unit tests** (+18)

## v1.126.0 (2026-07-05)

- **`create_trap_rolls` orchestration tool (320 MCP tools)** — trap hi-hat roll patterns: the evolving density technique that defines modern trap. Hi-hat patterns that start sparse and build through triplet bursts, 32nd-note runs, and stutter patterns. 5 variants: modern (16ths with triplet rolls at bar transitions, Travis Scott/Drake), migos (triplet bursts on off-beats, Migos "Bad and Boujee"), bubble (continuous 16ths with 32nd doubles, Young Thug/Future), skrrt (stuttering bursts mimicking screeching tires, Playboi Carti/21 Savage), evolving (density builds 8th→16th→triplet across 4 bars, Metro Boomin). Triplet subdivisions (0.16/0.33/0.66/0.83). 2-bar cycle. 63 orchestration tools. 320 MCP tools
- **1422 unit tests** (+18)

## v1.125.0 (2026-07-05)

- **`create_breakbeat` orchestration tool (319 MCP tools)** — breakbeat: the syncopated skeleton of jungle, DnB, big beat, and breakbeat hardcore. Broken drum patterns where kick/snare don't sit on clean quarters. 5 variants: amen (G.C. Coleman, The Winstons 1969 — the most sampled 6-second loop in history), dnb (chopped Amen-style with 16th hats and ghost snares, Andy C/Noisia), big_beat (mid-tempo fat breaks with kick+snare syncopation, Fatboy Slim/Prodigy), 2_step (UK garage skipping feel, shifted kick, MJ Cole/Disclosure), funky_drummer (Clyde Stubblefield, James Brown 1970 — the most funk-sampled break, Public Enemy/NWA). All patterns syncopated (at least one off-grid kick/snare). 2-bar cycle. 62 orchestration tools. 319 MCP tools
- **1404 unit tests** (+21)

## v1.124.0 (2026-07-05)

- **`create_four_on_floor` orchestration tool (318 MCP tools)** — four-on-the-floor: the foundational beat of house, techno, and disco. Kick on every quarter note (beats 1-2-3-4) — the pulse that defined dance music from 70s disco through Chicago house to Berlin techno. 5 variants: classic_house (open hats on off-beats, clap on 2+4, Frankie Knuckles/TR-909), deep_house (shuffled hats, rimshot, Larry Heard), techno (16th hats, industrial clap, Jeff Mills), disco (tambourine 16ths, Moroder/Donna Summer), tech_house (swung hats, perc stabs, Solardo/Fisher). 1-bar cycle. 61 orchestration tools. 318 MCP tools
- **1383 unit tests** (+20)

## v1.123.0 (2026-07-05)

- **`werkstatt_declicker.js` DSP script (97 DSP, 78 Werkstatt)** — de-clicker: restoration tool that detects and removes clicks, pops, and digital glitches from audio. Time-domain median-filter detection: sliding window (5-15 samples, insertion sort) computes local median, deviation from median vs adaptive threshold (local energy-based) flags clicks. Two-pass processing: detect click regions, then interpolate with cubic Hermite (Catmull-Rom) or linear fallback. Click length limit (8-128 samples) prevents over-repairing legitimate transients. Overlap expansion (0-32 samples) smooths transition edges. Delay buffer (256 samples) for look-back context. iZotope RX De-click / CEDAR Declick style — third restoration processor. 7 params (sensitivity/click_len/median_size/interp/overlap/mix/output). 97 DSP scripts, 78 Werkstatt
- **1386 unit tests** (+23)

## v1.122.0 (2026-07-05)

- **`werkstatt_dereverb.js` DSP script (96 DSP, 77 Werkstatt)** — de-reverb: restoration tool that removes room reverb tails from recordings. Per-band (4-16 logarithmic bands) dual envelope follower: fast envelope tracks direct signal, slow envelope tracks reverb tail. Transient detection via fast/slow ratio threshold — when fast > slow × sensitivity, it's a direct signal (preserve). When fast < slow, it's a tail (suppress). Tail dominance = how much the tail dominates, determines gain reduction (0 to -24 dB). Decay estimation (100ms-2s) controls slow envelope time constant. Direct signal preservation parameter. iZotope RX De-reverb / Accusonus ERA style — second restoration processor. 7 params (reduction/decay_est/sensitivity/bands/preserve/mix/output). 96 DSP scripts, 77 Werkstatt
- **1397 unit tests** (+24)

## v1.121.0 (2026-07-05)

- **Complete DSP documentation rewrite** — docs/dsp-scripts.md now lists all 95 scripts (76 Werkstatt + 9 Apparat + 10 Spielwerk) organized by category. Previously listed only ~30 scripts with wrong section headers ("40 Werkstatt"). Every script now has its name, label, and description. Categories: dynamics (10), saturation (8), EQ (5), filter (8), modulation (8), reverb (5), delay (5), pitch (5), time (3), stereo/spatial (4), spectral/fx (8), restoration (1), physical modeling (1), vocoder (1), phase vocoder (2), utility (4), vocal (1), instruments (9), MIDI effects (10). 65% of the library was previously invisible in docs.

## v1.120.0 (2026-07-05)

- **`create_boom_bap` orchestration tool (317 MCP tools)** — boom-bap hip-hop drum pattern: the foundational beat of hip-hop. "boom" = kick, "bap" = snare. 5 variants: classic (90s, Nas/Illmatic), old_school (80s, Run-DMC), trap (rolling hats, Migos), lofi (laid-back, J Dilla), drill (UK, Central Cee). Kick + snare + hi-hat + ghost strokes. 2-bar cycle. From Run-DMC to Kendrick Lamar. 60 orchestration tools. 317 MCP tools
- **1373 unit tests** (+20)

## v1.119.0 (2026-07-05)

- **`werkstatt_spectral_denoise.js` DSP script (95 DSP, 76 Werkstatt)** — spectral denoiser: restoration tool using noise floor subtraction. Two-phase: (1) noise learning — accumulates noise magnitude spectrum from input during 0.5-10s learning period, (2) denoising — per-bin spectral subtraction (Berouti & Schwartz 1979) with oversubtraction factor (1-4x), spectral floor (prevents musical noise), half-wave rectification, gain smoothing. Reduction 0 to -30 dB. iZotope RX Spectral De-noise / CEDAR DNS style — first restoration processor in the library. 7 params (reduction/learn_time/oversub/floor/smoothing/mix/output). 95 DSP scripts, 76 Werkstatt
- **1353 unit tests** (+22)

## v1.118.0 (2026-07-05)

- **`create_dembow` orchestration tool (316 MCP tools)** — reggaeton/dancehall dembow rhythm: the 3-3-2 syncopated gallop that drives virtually all reggaeton and Latin dancehall. From Bobby Dixon's "Dembow" riddim (1990 Jamaica) to Daddy Yankee "Gasolina" to Bad Bunny. 5 variants: classic (full gallop), dancehall (sparser), trap_latino (syncopated kick), perreo (ghost hits, underground), urbano (reggaeton+trap fusion). Kick + snare + ghost strokes. 1-bar cycle. 59 orchestration tools. 316 MCP tools
- **1331 unit tests** (+17)

## v1.117.0 (2026-07-05)

- **`werkstatt_matching_eq.js` DSP script (94 DSP, 75 Werkstatt)** — matching EQ: adaptive spectral balance corrector. Accumulates long-term average spectrum (LTAS) of input, compares to reference target (pink noise = -3 dB/octave, white = flat, brown = -6 dB/octave, interpolated), computes per-bin correction gain = (target/actual)^matchAmt. Smoothing window (1-31 bins) for broadband vs detailed correction. Adaptation speed controls how fast gain curve approaches target. Additional tilt for subjective brightness. Gain clamped 0.1x-10x. iZotope Ozone EQ Match / FabFilter Pro-Q spectrum grab — the EQ that decides for you. 7 params (target/match_amt/smooth/adapt_rate/tilt/mix/output). 94 DSP scripts, 75 Werkstatt
- **1314 unit tests** (+22)

## v1.116.0 (2026-07-05)

- **`werkstatt_time_stretch.js` DSP script (93 DSP, 74 Werkstatt)** — phase vocoder time stretch: high-quality time stretching that preserves pitch. Same STFT + phase unwrapping framework as phase_vocoder but stretches duration without changing frequency. Synthesis hop = analysis hop × stretch ratio (0.25x–4x). Transient detection via energy jump (2x threshold) + transient preservation blends input phase during attacks to reduce smearing. Identity phase locking. Élastique-grade quality — complements granular_stretch (texture) and paulstretch (ambient) with the third time-stretch algorithm. 5 params (stretch/lock_phase/transient/mix/output). 93 DSP scripts, 74 Werkstatt
- **1292 unit tests** (+23)

## v1.115.0 (2026-07-05)

- **`werkstatt_phase_vocoder.js` DSP script (92 DSP, 73 Werkstatt)** — phase vocoder pitch shifter: high-quality FFT-based pitch shifting with phase unwrapping. STFT (2048-point FFT, 512 hop, Hann window) → per-bin magnitude/phase → phase deviation from expected advance → true frequency (phase derivative) → accumulated output phase with synthesis hop = analysis hop × ratio → inverse FFT + overlap-add. Identity phase locking reduces phasiness artifacts. Formant control shifts/preserves/boosts spectral envelope. ±12 semitones range. Élastique / Melodyne quality — preserves phase coherence across frames, no transient smearing of time-domain pitch shifters. 5 params (pitch/formant/lock_phase/mix/output). 92 DSP scripts, 73 Werkstatt
- **1269 unit tests** (+20)

## v1.114.0 (2026-07-05)

- **`create_cascara` orchestration tool (315 MCP tools)** — Afro-Cuban cáscara pattern: timbale shell rhythm that fills space around clave and tumbao. Completes the Afro-Cuban rhythm section trilogy (clave + tumbao + cáscara). 4 variants: son_3_2 (forward), son_2_3 (reverse), guaguanco (ghost strokes on downbeats for density), mambo (syncopated accents + fill on bar 2). Two stroke heights: high (rim/edge, accented) + low (shell body, unaccented) + ghost (very soft). High/low alternation creates call-and-response within the pattern. 58 orchestration tools. 315 MCP tools
- **1249 unit tests** (+19)

## v1.113.0 (2026-07-05)

- **`werkstatt_auto_tune.js` DSP script (91 DSP, 72 Werkstatt)** — auto-tune pitch correction: autocorrelation pitch detection (60-1200 Hz range, parabolic interpolation for sub-sample accuracy) → snap-to-scale correction (7 scales: chromatic/major/minor/dorian/mixolydian/pentatonic minor/blues, 12 root notes) → time-domain pitch shifting via ring buffer with linear interpolation. Retune speed controls hard (robot, T-Pain) vs soft (natural) correction. Strength parameter blends between dry and fully corrected. Detune offset in cents. Cher "Believe" / Antares Auto-Tune style. 7 params (key/scale/retune/strength/detune/mix/output). 91 DSP scripts, 72 Werkstatt
- **1230 unit tests** (+19)

## v1.112.0 (2026-07-05)

- **`apparat_bowed_string.js` DSP script (90 DSP, 9 Apparat)** — bowed string physical modeling: digital waveguide with bow friction. Stribeck stick-slip curve models Helmholtz motion (bow sticks, slips, sticks). Two delay lines split at bow position (nut side + bridge side). String velocity = right wave - left wave at bow point. One-pole damping filter in waveguide loop (brightness control). 3 biquad resonators for violin body (280/450/650 Hz). Vibrato with rate/depth. noteOn seeds waveguide with noise. 9 params (bow_pressure/bow_speed/bow_position/freq/brightness/body_resonance/vibrato_rate/vibrato_depth/volume). 90 DSP scripts, 9 Apparat
- **1211 unit tests** (+19)

## v1.111.0 (2026-07-05)

- **`werkstatt_spectral_compressor.js` DSP script (89 DSP, 71 Werkstatt)** — spectral compressor: STFT-based per-bin dynamics processing. Cooley-Tukey radix-2 FFT (1024-point, 512 hop, Hann window), per-bin envelope follower with independent attack/release, per-bin compression curve, tilt parameter shifts threshold across frequency spectrum (compress lows more or highs more), gain smoothing prevents artifacts, overlap-add reconstruction. No crossover artifacts — each frequency bin compressed independently. Flux Syrah / FabFilter Pro-MB style. 8 params (threshold/ratio/attack/release/smoothing/tilt/mix/output). 89 DSP scripts, 71 Werkstatt
- **1192 unit tests** (+21)

## v1.110.0 (2026-07-05)

- **`create_tumbao` orchestration tool (314 MCP tools)** — Afro-Cuban tumbao (conga) pattern: the rhythmic foundation of salsa alongside clave. 4 variants: salsa (standard), salsa_slap (with slap on beat 2), rumba (guaguancó, more open tones), bolero (sparse, less anticipatory). 3 stroke types mapped to 3 conga pitches: tone (closed, low), open (resonant, mid), slap (sharp, high). Open tone on &4 anticipates downbeat — the tumbao signature. 57 orchestration tools. 314 MCP tools
- **1171 unit tests** (+14)

## v1.109.0 (2026-07-05)

- **`werkstatt_harmonic_tremolo.js` DSP script (88 DSP, 70 Werkstatt)** — harmonic tremolo: Fender '60s effect. LR4 Linkwitz-Riley crossover splits signal into low/high bands, dual LFO modulates each band's gain in antiphase. Unlike regular tremolo (amplitude up/down), harmonic tremolo rocks between bass and treble — spectral modulation, not amplitude. Shape blends sine→square for choppy vintage feel. Phase offset controls antiphase depth. 7 params (rate/depth/crossover/shape/phase_offset/mix/output). Khruangbin, Magic Sam, Fender Vibrolux style. 88 DSP scripts, 70 Werkstatt
- **1157 unit tests** (+20)

## v1.108.0 (2026-07-05)

- **`werkstatt_binaural.js` DSP script (87 DSP, 69 Werkstatt)** — binaural spatial panner: 3D sound positioning via HRTF approximation. Woodworth formula for ITD (interaural time difference), frequency-dependent ILD (head shadow effect, HF attenuated on shadowed ear), pinna elevation spectral notches (2 peaking biquads, notch frequency shifts with elevation), distance attenuation (inverse distance law + air absorption HF rolloff), room reverb with LCG decorrelation. 7 params (azimuth/elevation/distance/head_size/room/mix/output). 87 DSP scripts, 69 Werkstatt
- **1137 unit tests** (+20)

## v1.107.0 (2026-07-05)

- **`werkstatt_expander.js` DSP script (86 DSP, 68 Werkstatt)** — downward expander: compressor complement, attenuates signals below threshold. Ratio controls expansion strength (1:1→20:1), range caps max attenuation (0→-60 dB), soft knee for smooth transition, stereo linked detection, attack/release smoothing. At ratio=∞ becomes a gate. Used for noise reduction, drum transient enhancement, spill cleanup. 8 params (threshold/ratio/attack/release/range/mix/knee/output). 86 DSP scripts, 68 Werkstatt
- **1117 unit tests** (+76)

## v1.106.0 (2026-07-05)

- **`create_euclidean_rhythm` orchestration tool (313 MCP tools)** — Euclidean rhythm generator: Björklund's algorithm distributes k onsets across n steps maximally evenly. Generates most of the world's classic rhythms: E(3,8)=tresillo, E(5,8)=cinquillo, E(7,16)=samba, E(7,12)=bembé, E(4,9)=Aksak, E(3,7)=Persian. Rotation shifts pattern clockwise. Accents on first onset per bar. Returns pattern as binary string and E(k,n) notation. 313 MCP tools, 56 orchestration
- **1041 unit tests** (+13)

## v1.105.0 (2026-07-05)

- **`werkstatt_grain_delay.js` DSP script (85 DSP, 67 Werkstatt)** — grain delay: Hann-windowed grains read from delay buffer with independent pitch shift (0.25x-4x), scatter (randomized read position jitter), reverse playback probability, equal-power pan, damped feedback. Grain rate controls spawn density, grain size controls window length. Grain cap at 80 for stability. Output Portal / GRM Tools / Sugar Bytes Effectrix style. 10 params (delay/grain_size/grain_rate/pitch/scatter/pan/reverse/feedback/mix/output). 85 DSP scripts, 67 Werkstatt
- **1028 unit tests** (+15), E2E 8/8

## v1.104.0 (2026-07-05)

- **`werkstatt_vinyl.js` DSP script (84 DSP, 66 Werkstatt)** — vinyl record simulator: crackle/pops via LCG-triggered exponential envelopes with randomized intervals, continuous surface noise, wow/flutter pitch wobble via fractional delay buffer (0.8Hz wow + 6.5Hz flutter), wear high-frequency rolloff via one-pole LP. 8 params (age/dust/wear/wow/flutter/noise/mix/output). Lo-fi hip-hop, ambient texture, vintage aesthetic. 84 DSP scripts, 66 Werkstatt
- **1013 unit tests** (+15), E2E 8/8

## v1.103.0 (2026-07-05)

- **`create_clave` orchestration tool (312 MCP tools)** — Afro-Cuban clave pattern: 5-note rhythmic skeleton across 2 bars that defines the feel. 6 clave types: son 3-2, son 2-3, rumba 3-2, rumba 2-3, bossa nova, 6/8. Clave direction (3-2 forward vs 2-3 reverse) determines where downbeats fall. All other rhythms align to the clave. Cycle repeats for bars > 2. 312 MCP tools, 55 orchestration
- **998 unit tests** (+12)

## v1.102.0 (2026-07-05)

- **`werkstatt_multiband_saturator.js` DSP script (83 DSP, 65 Werkstatt)** — multiband saturator: LR4 Linkwitz-Riley crossover splits into 3 bands, each with independent drive and saturation character (tape=tanh warm, tube=asymmetric soft clip even harmonics, transistor=hard cubic odd harmonics). Per-band drive 1..10x gain into saturation curve. Band summation + dry/wet mix. FabFilter Saturn / iZotope Trash style. 10 params (crossover1/crossover2/low_drive/mid_drive/high_drive/low_char/mid_char/high_char/output/mix). 83 DSP scripts, 65 Werkstatt
- **986 unit tests** (+15), E2E 8/8

## v1.101.0 (2026-07-05)

- **`werkstatt_modal_resonator.js` DSP script (82 DSP, 64 Werkstatt)** — modal synthesis resonator bank: parallel bandpass biquad filters tuned to modal frequency ratios of real materials (marimba bar, bell, circular plate, string, wine glass). 5 material presets with published frequency ratios. Inharmonicity parameter stretches upper modes quadratically (B coefficient). Per-mode Q derived from T60 decay time. Brightness controls high-mode amplitude rolloff. Stereo processing with independent biquad state per channel. 7 params (material/fundamental/decay/brightness/inharmonicity/mix/output). 82 DSP scripts, 64 Werkstatt
- **971 unit tests** (+15), E2E 8/8

## v1.100.0 (2026-07-05)

- **`spielwerk_chorder.js` DSP script (81 DSP, 10 Spielwerk)** — chord voicer MIDI effect: 13 chord shapes (major/minor/maj7/min7/dom7/dim/dim7/half-dim/aug/sus2/sus4/add9/m6), 5 voicing modes (close/drop-2/drop-3/open/spread), 4 inversions via rotation, octave shift, spread spacing, strum delay between voices, per-voice velocity attenuation. 7 params (chord/voicing/inversion/octave/spread/strum/velScale). 81 DSP scripts, 10 Spielwerk MIDI effects
- **956 unit tests** (+15), E2E 8/8

## v1.99.0 (2026-07-05)

- **`create_cross_rhythm` orchestration tool (311 MCP tools)** — cross-rhythm: multiple voices with independent period lengths creating shifting alignment. Unlike polyrhythm (divides one bar into n+m parts), cross-rhythm gives each voice its own period in beats — voices cycle independently, only realigning at LCM of all periods. 2-6 voices, velocity attenuation per voice, alignment interval (LCM) reported. African cross-rhythms, Steve Reich, Talking Heads, minimalism. 311 MCP tools
- **941 unit tests** (+10), 54 orchestration tools

## v1.98.0 (2026-07-05)

- **`werkstatt_svf.js` DSP script** — Chamberlin state variable filter: simultaneous LP/BP/HP outputs with seamless morph parameter (LP→BP→HP continuous blend). Output mode: 0=morph, 1=notch, 2=allpass. Self-oscillation at high resonance (capped at 0.99 to prevent runaway), soft-clip tanh protection. 7 params (cutoff/resonance/morph/output_mode/drive/mix/output). Korg MS-20 / Oberheim SEM style. 80 DSP scripts
- **931 unit tests** (+14), E2E 8/8

## v1.97.0 (2026-07-05)

- **`werkstatt_tilt_eq.js` DSP script** — single-knob spectral tilt EQ: low shelf (cut below pivot) + high shelf (boost above pivot) with one tilt parameter. Positive tilt = brighten, negative = darken. Pivot frequency configurable, steepness controls shelf slope. Biquad-based (RBJ cookbook), coefficient caching, 5 params (tilt/pivot/steepness/mix/output). Ozone / FabFilter / Airwindows Tilt style. 79 DSP scripts
- **917 unit tests** (+14), E2E 8/8

## v1.96.0 (2026-07-05)

- **`werkstatt_bass_enhancer.js` DSP script** — psychoacoustic bass enhancer (MaxxBass / Renaissance Bass style): isolates bass band via LPF, full-wave rectification generates sub-harmonic content, LPF smoothing extracts sub fundamental, HPF removes DC. Brain perceives lower fundamental even on small speakers/headphones. Envelope follower with attack/release, harmonic saturation via tanh for bass presence, band replacement (HPF dry + enhanced bass). 8 params (freq/sub_level/direct_level/harmonics/attack/release/mix/output). 78 DSP scripts
- **903 unit tests** (+14), E2E 8/8

## v1.95.0 (2026-07-05)

- **`werkstatt_freq_shifter.js` DSP script** — SSB frequency shifter: single-sideband modulation via Hilbert transform (allpass pair for 90° phase difference) + complex carrier oscillator. Shifts all frequencies by fixed Hz amount (not ratio like pitch_shift), breaking harmonic relationships for that classic Buchla/banana synth inharmonic sound. Upper/lower sideband selection via direction param, feedback for spiraling shifts. 5 params (shift/direction/feedback/mix/output). 77 DSP scripts
- **889 unit tests** (+13), E2E 8/8

## v1.94.0 (2026-07-05)

- **`werkstatt_reverse_delay.js` DSP script** — reverse delay: reads delay buffer in reverse direction for each repetition, with fade ramps at window boundaries to prevent clicks. Feedback feeds reversed sample back into buffer (creating cascading reverse repeats). Damping lowpass on feedback path, equal-power pan, 8 params (time/feedback/levels/pan/fade/damping/mix/output). The Edge / U2 style reverse delay. 76 DSP scripts
- **876 unit tests** (+14), E2E 8/8

## v1.93.0 (2026-07-05)

- **`werkstatt_gated_reverb.js` DSP script** — 80s gated reverb: Schroeder plate reverb + envelope-followed gate on dry input. Gate detects amplitude on dry signal (not reverb output), opens above threshold, holds, then exponentially closes — cutting the reverb tail for that signature Phil Collins / 80s snare sound. 9 params (decay/predelay/damping/width/threshold/hold/release/mix/output). 75 DSP scripts
- **862 unit tests** (+13), E2E 8/8

## v1.92.0 (2026-07-05)

- **`werkstatt_multiband_imager.js` DSP script** — 3-band stereo imager: LR4 Linkwitz-Riley crossover splits signal into low/mid/high, each band gets independent M/S width control. Low band defaults to mono (standard mastering practice), high band defaults wide. Bypass_low for dry low band, link mode couples low+mid width. 9 params (crossover1/crossover2/low_width/mid_width/high_width/bypass_low/link/mix/output). iZotope Ozone Imager / Waves S1 style. 74 DSP scripts
- **849 unit tests** (+13), E2E 8/8

## v1.91.0 (2026-07-05)

- **`werkstatt_tape_stop.js` DSP script** — exponential tape stop: speed decays exponentially to zero with corresponding pitch drop. State machine (playing→stopping→stopped), trigger/restart control, configurable decay curve (1=linear, 2=classic tape, 8=hard stop), wow/flutter during slowdown, circular buffer with fractional read. 9 params (stop_time/trigger/restart/curve/wow/flutter/flutter_rate/mix/output). 73 DSP scripts
- **836 unit tests** (+14), E2E 8/8

## v1.90.0 (2026-07-05)

- **`spielwerk_prob_gate.js` DSP script** — subtractive probability gate (Spielwerk MIDI effect): LCG-based note dropping with per-note probability, 3 modes (uniform/position-based/pitch-based), hold momentum (passed notes boost next), forced pass zones (min/max pitch always pass), velocity boost for survivors, seedable for reproducibility. 8 params (chance/variation/seed/mode/min_pitch/max_pitch/velocity_boost/hold). 72 DSP scripts, 9 Spielwerk MIDI effects
- **822 unit tests** (+15), E2E 8/8

## v1.89.0 (2026-07-05)

- **`werkstatt_fuzz.js` DSP script** — hard clipping fuzz (Big Muff Pi style): high-gain hard clip with foldback squash, full-wave rectified octave-up content, Muff tone stack (LP/HP blend), noise gate, asymmetrical bias for even harmonics, dry blend. 8 params (sustain/tone/octave/gate/bias/level/dry/output). 71 DSP scripts
- **807 unit tests** (+13), E2E 8/8

## v1.88.0 (2026-07-05)

- **`create_phase` orchestration tool** — Steve Reich-style phase shifting: 2-4 voices play the same melodic pattern, but drifting voices gradually shift in time creating evolving phase relationships. 3 drift directions (forward/backward/diverge), phase_rate, phase_amount with reset, per-voice velocity decay. Unlike create_canon (fixed offset) or create_isorhythm (repeating cycles), phasing creates continuous temporal drift. 310 MCP tools
- **794 unit tests** (+10), E2E 8/8

## v1.87.0 (2026-07-05)

- **`werkstatt_octaver.js` DSP script** — sub-octave generator (Boss OC-2 style): zero-crossing flip-flop divides input frequency by 2 (-1 oct) and 4 (-2 oct), envelope follower tracks amplitude for natural decay, hysteresis on zero-crossing detection, one-pole lowpass smoothing on square wave edges. 7 params (oct1/oct2/direct/smooth/track/trigger/output). 70 DSP scripts
- **841 unit tests** (+13), E2E 8/8

## v1.86.0 (2026-07-05)

- **`werkstatt_autowah.js` DSP script** — envelope-followed filter (autowah): filter frequency driven by input envelope, not LFO or static cutoff. 3 filter modes (bandpass/peaking/lowpass), sensitivity, attack/release, direction (up/down sweep), cutoff smoothing. 69 DSP scripts
- **828 unit tests** (+13), E2E 8/8

## v1.85.0 (2026-07-05)

- **`werkstatt_dimension_chorus.js` DSP script** — Roland Dimension D-style chorus: 2 detuned delay lines with independent LFO rates (triangle wave), no feedback, mono-sum input, brightness filter, stereo width control. 68 DSP scripts
- **818 unit tests** (+13), E2E 8/8

## v1.84.0 (2026-07-05)

- **`werkstatt_multitap_delay.js` DSP script** — multitap delay: 4 independent taps from single delay buffer, each with time/level/pan/feedback. Equal-power stereo pan per tap, feedback damping, spread modulation. 67 DSP scripts
- **805 unit tests** (+13), E2E 8/8

## v1.83.0 (2026-07-05)

- **`create_stutter` orchestration tool** — stutter edit: rapid rhythmic repetitions with evolving rate and dynamics. 5 patterns (accelerate, decelerate, ping_pong, constant, random), 5 accent patterns, 5 velocity ramps, gate, pitch jitter. 309 MCP tools
- **792 unit tests** (+10), E2E 8/8

## v1.82.0 (2026-07-05)

- **`spielwerk_harmonizer.js` DSP script** — MIDI harmonizer: 3 voices at fixed intervals or diatonic, per-voice velocity, 14 scales. Forces notes into scale. 66 DSP scripts
- **782 unit tests** (+11), E2E 8/8

## v1.81.0 (2026-07-05)

- **`werkstatt_dynamic_eq.js` DSP script** — dynamic EQ: 3 bands, peaking biquad + envelope follower, per-band threshold/range. 65 DSP scripts
- **771 unit tests** (+9), E2E 8/8
- ruff clean, CI green

## v1.80.0 (2026-07-05)

- **`spielwerk_scale_quantizer.js` DSP script** — MIDI scale quantizer: 14 scales, 12 roots, snap direction. Forces notes into scale. 64 DSP scripts
- **762 unit tests** (+10), E2E 7/7
- ruff clean, CI green

## v1.79.0 (2026-07-05)

- **`apparat_supersaw.js` DSP script** — JP-8000 supersaw: 7 detuned saws, per-voice stereo pan, resonant lowpass. 9 params. 63 DSP scripts
- **752 unit tests** (+10), E2E 8/8
- ruff clean, CI green

## v1.78.0 (2026-07-05)

- **`werkstatt_convolution_reverb.js` DSP script** — convolution reverb with generated stereo IR. Time-domain direct convolution: early reflections (7 taps) + decaying noise tail through lowpass. 8 params: room_size, decay, damping, predelay, early_late, width, mix, output. 62 DSP scripts
- **742 unit tests** (+10), E2E 8/8
- ruff clean, CI green

## v1.77.0 (2026-07-05)

- **`create_motif_development` orchestration tool** — through-composed melodic development: 2-8 note motif → continuous evolving line. 11 stages: statement/sequence/fragment/invert/octave/expand/compress/cadence. Beethoven 5th approach. 51 orchestration tools
- **308 MCP tools** (51 orchestration)
- **732 unit tests** (+10), E2E 8/8
- ruff clean, CI green

## v1.76.0 (2026-07-05)

- **`werkstatt_rotary_speaker.js` DSP script** — Leslie rotary: dual horn+rotor, Doppler pitch mod, amplitude mod, crossover, acceleration. Hammond organ, guitar, soul vocals
- **61 DSP scripts** (48 Werkstatt + 7 Apparat + 6 Spielwerk)
- **722 unit tests** (+10), E2E 8/8
- ruff clean, CI green

## v1.75.0 (2026-07-05)

- **`create_variations` orchestration tool** — thematic variation generator: reads source notes, writes N variations to new regions. 9 transforms (transpose/invert/reverse/augment/diminish/fragment/octave). Bach Goldberg, Beethoven Diabelli, jazz reharmonization. Generative (non-destructive). 50 orchestration tools
- **307 MCP tools** (50 orchestration)
- **712 unit tests** (+10), E2E 9/9
- ruff clean, CI green

## v1.74.0 (2026-07-05)

- **`opendaw-dsp-chains` agent skill** — 10 production-ready DSP signal chain recipes (vocal, guitar, drum bus, synth bass, lofi, mastering, acid, ambient, vocoder, distortion). Exact scripts + order + params. 11 skills total
- ruff clean, CI green

## v1.73.0 (2026-07-05)

- **`werkstatt_moog_ladder.js` DSP script** — Moog ladder 24dB/oct filter, 4 cascaded stages, feedback resonance, tanh nonlinearity, 3 modes (LP/HP/BP), drive, warmth
- **60 DSP scripts** (47 Werkstatt + 7 Apparat + 6 Spielwerk)
- **702 unit tests** (+10), E2E 8/8
- ruff clean, CI green

## v1.72.0 (2026-07-05)

- **`werkstatt_waveshaper.js` DSP script** — custom-curve waveshaper: tanh/cubic/atan/Chebyshev, drive 0-3, bias, harmonics, tone, output, mix. 4 shaping curves in one unit
- **59 DSP scripts** (46 Werkstatt + 7 Apparat + 6 Spielwerk)
- **692 unit tests** (+10), E2E 8/8
- ruff clean, CI green

## v1.71.0 (2026-07-05)

- **`create_two_hand_piano` orchestration tool** — two-hand piano arrangement. Left hand: block/arpeggio up/down/updown/Alberti bass/bass+chord. Right hand: chord tones/arpeggio/melody. Separate bass/chord/melody octaves, adjustable arpeggio rate. Piano ballads, jazz comping, classical accompaniment, lofi piano
- **306 MCP tools** (49 orchestration)
- **625 unit tests** (+10), E2E 8/8
- ruff clean, CI green

## v1.70.0 (2026-07-05)

- **`create_fugue` orchestration tool** — polyphonic fugue with subject, tonal/real answer, countersubject, stretto. Voice alternation, velocity decay. 2-5 voices, 2-32 note subject. Bach WTC/Art of Fugue style
- **305 MCP tools** (48 orchestration)
- **615 unit tests** (+10), E2E 8/8
- ruff clean, CI green

## v1.69.0 (2026-07-05)

- **`werkstatt_spectral_gate.js` DSP script** — multiband spectral gate. 4-16 log-spaced bandpass bank, per-band envelope followers, threshold gating, spectral tilt. 10 params: bands, threshold, reduction, attack, release, min_freq, max_freq, tilt, mix, output
- **58 DSP scripts** (45 Werkstatt + 7 Apparat + 6 Spielwerk)
- **605 unit tests** (+10), E2E 8/8
- ruff clean, CI green

## v1.68.0 (2026-07-05)

- **`werkstatt_looper.js` DSP script** — live looper with overdub. Records into circular buffer, variable speed (0.25x-4x), 3 play modes (auto/play/overdub), reverse mode, crossfade at loop boundaries. 10 params: loop_length, feedback, overdub, play_mode, speed, reverse_mode, monitor, fade_edges, mix, output
- **57 DSP scripts** (44 Werkstatt + 7 Apparat + 6 Spielwerk)
- **595 unit tests** (+10), E2E 8/8
- ruff clean, CI green

## v1.67.0 (2026-07-05)

- **`create_chorale` orchestration tool** — 4-voice SATB chorale generator with voice-leading rules. Parses chord progression, assigns soprano/alto/tenor/bass with smooth voice movement, parallel fifth/octave detection, voice range clamping. Supports maj/min/m7/maj7/dom7/sus2/sus4/dim/aug. Classic Bach chorale style
- **304 MCP tools** (47 orchestration)
- **585 unit tests** (+10), E2E 8/8
- ruff clean, CI green

## v1.66.0 (2026-07-05)

- **`werkstatt_scratch.js` DSP script** — DJ vinyl scratch with turntable physics. Triangle LFO back-and-forth, pullback yank, friction-based inertia, wow/flutter, crackle. 10 params: depth, rate, pullback, friction, wow, flutter, flutter_rate, crackle, mix, output
- **56 DSP scripts** (43 Werkstatt + 7 Apparat + 6 Spielwerk)
- **575 unit tests** (+10), E2E 8/8
- ruff clean, CI green

## v1.65.0 (2026-07-05)

- **`werkstatt_reverse.js` DSP script** — real-time reverse playback effect with chunked circular buffer. Reverses audio in configurable chunks (0.05-5 sec) with variable speed (0.25x-4x). Three trigger modes: continuous, single, gate. Three stereo modes: normal, ping-pong, wide. Feedback for layered reverse textures. Crossfade smoothing. Classic for backwards cymbals, vocal reverses, psychedelic transitions. 10 params: chunk_size, feedback, speed, smooth, dry_gain, wet_gain, mix, stereo_mode, trigger_mode, output
- **55 DSP scripts** (42 Werkstatt + 7 Apparat + 6 Spielwerk)
- **565 unit tests** (+10), E2E 8/8
- ruff clean, CI green

## v1.64.0 (2026-07-05)

- **`werkstatt_vocoder.js` DSP script** — channel vocoder with 8-24 log-spaced bandpass filter bank. Maps modulator (vocal/input) spectral envelope onto a carrier oscillator (saw/square/noise). Per-band envelope followers with adjustable response time and threshold gating. Emphasis control boosts high bands for intelligibility. Output highpass removes rumble. Classic for robotic voice effects, synth vocal textures, Daft Punk-style sounds. 10 params: bands, carrier_wave, carrier_freq, mod_response, mod_threshold, band_q, emphasis, highpass, mix, output
- **54 DSP scripts** (41 Werkstatt + 7 Apparat + 6 Spielwerk)
- **555 unit tests** (+10), E2E 8/8
- ruff clean, CI green

## v1.63.0 (2026-07-05)

- **`werkstatt_multiband_comp.js` DSP script** — 3-band multiband compressor with Linkwitz-Riley 4th order crossovers (24dB/oct). Independent threshold/ratio/attack/release/makeup gain per band (low/mid/high). Crossover frequencies 50-8000 Hz (exponential). Envelope followers per band with peak detection. Classic mastering tool — controls dynamics separately in low/mid/high frequency ranges. 18 params: 2 crossovers + 5 per band × 3 + mix
- **53 DSP scripts** (40 Werkstatt + 7 Apparat + 6 Spielwerk)
- **555 unit tests** (+10), E2E 8/8
- ruff clean, CI green

## v1.62.0 (2026-07-05)

- **`werkstatt_harmonizer.js` DSP script** — dual-voice harmonizer with independent pitch shift (±12 semitones + ±50 cents), per-voice gain, detune LFO for chorus-like wobble, and delay-based pitch shifting. Creates choir/harmony effects from any input — two shifted voices with micro-detune. Distinct from pitch_shift (single voice) — harmonizer creates multiple harmonized copies. Classic for vocal harmonies, guitar harmonizers, synth thickening. 9 params: 2× shift_semi/cent/gain, detune, delay, mix
- **52 DSP scripts** (39 Werkstatt + 7 Apparat + 6 Spielwerk)
- **546 unit tests** (+10), E2E 8/8
- ruff clean, CI green

## v1.61.0 (2026-07-05)

- **`create_passacaglia` orchestration tool (303 MCP tools)** — repeating bass ostinato with evolving harmonies above. Baroque form (Bach BWV 582) adapted to modern contexts. 3 variation styles: block (sustained chords), arpeggiated (broken), melodic (stepwise counter-melody). Bass pattern as MIDI pitches + custom rhythm, chord cycling, 3/4 and 4/4 time. Distinct from ostinato (single pattern), pedal_point (single note), bordun (drone chord)
- **46 orchestration tools** total
- **536 unit tests** (+10 passacaglia), E2E 8/8
- ruff clean, CI green

## v1.60.0 (2026-07-05)

- **`werkstatt_formant_filter.js` DSP script** — 3-band parallel formant filter simulating vocal tract resonances. 5 vowel presets (/a/, /i/, /u/, /o/) with smooth interpolation, or manual F1/F2/F3 control. Bandwidth and resonance parameters shape the vocal character. Biquad bandpass filters in parallel. Classic for vocoder-like vocal coloring, talk-box effects, and synth voice synthesis. 9 params: 3 formant freqs, 3 bandwidths, vowel, resonance, mix
- **51 DSP scripts** (38 Werkstatt + 7 Apparat + 6 Spielwerk)
- **354 unit tests** (+10), E2E 8/8
- ruff clean, CI green

## v1.59.0 (2026-07-05)

- **`werkstatt_comb_filter.js` DSP script** — standalone comb filter with delay-line feedback. Positive/negative polarity selects comb vs inverse comb characteristic. Damping LP in feedback path controls high-frequency decay. Freq 10-8000 Hz (delay time = 1/freq), feedback ±0.99. Classic building block of flangers/chorus, but standalone gives distinctive notched/peaked spectral combing. 5 params: freq, feedback, damping, mix, polarity
- **50 DSP scripts** (37 Werkstatt + 7 Apparat + 6 Spielwerk)
- **344 unit tests** (+10), E2E 8/8
- ruff clean, CI green

## v1.58.0 (2026-07-05)

- **`werkstatt_auto_pan.js` DSP script** — auto-pan with LFO-driven stereo positioning. Waveform morph (sine→triangle→square), rate (0.1-20 Hz), depth, phase offset (0-360°), width, and offset. Equal-power pan law. Distinct from stereowidth (which expands existing stereo) — auto-pan moves the signal between channels. Classic for guitars, synths, percussion. 6 params: rate, depth, shape, phase, width, offset
- **49 DSP scripts** (36 Werkstatt + 7 Apparat + 6 Spielwerk)
- **334 unit tests** (+10), E2E 8/8
- ruff clean, CI green

## v1.57.0 (2026-07-05)

- **`werkstatt_graphic_eq.js` DSP script** — 10-band graphic EQ with ISO frequency bands (32, 64, 125, 250, 500, 1k, 2k, 4k, 8k, 16k Hz), each ±12 dB gain, plus master output ±6 dB. Biquad peaking filters (Q=1.41, ⅔ octave) in series. Distinct from parametric EQ (fixed bands vs movable). Classic rack-mount EQ for tone shaping, mixing, and live sound. 11 params: 10 bands + master
- **48 DSP scripts** (35 Werkstatt + 7 Apparat + 6 Spielwerk)
- **324 unit tests** (+10 for graphic EQ), E2E 8/8
- **Example script**: `werkstatt_graphic_eq.py` — mix bus, smile curve, vocal clarity presets
- ruff clean, CI green

## v1.56.0 (2026-07-05)

- **`werkstatt_tape_delay.js` DSP script** — tape delay with wow (0.5 Hz slow pitch drift) and flutter (15 Hz fast pitch wobble) modulating the delay time, plus saturation in the feedback path for graceful repeat degradation. Fractional delay read for smooth modulation. 6 params: time, feedback, wow, flutter, saturation, mix. Classic for dub, guitar slapback, ambient wash. Completes delay family: stereo ✅ tape ✅
- **47 DSP scripts** (34 Werkstatt + 7 Apparat + 6 Spielwerk)
- **E2E verified**: compiled via ScriptCompiler, 6 params, time/feedback/wow/flutter set
- **Example script**: `werkstatt_tape_delay.py` — dub, slapback, ambient wash presets
- ruff clean, CI green

## v1.55.0 (2026-07-05)

- **`werkstatt_tube_saturator.js` DSP script** — tube/valve saturator with asymmetrical transfer curve (even harmonic dominance), warmth control (even/odd blend), bias, post-saturation tone filter, output gain. 6 params: drive, warmth, bias, tone, output, mix. Distinct from tape (darksat) and soft-clip (overdrive). Completes saturation family: tape ✅ overdrive ✅ wavefold ✅ bitcrusher ✅ tube ✅
- **46 DSP scripts** (33 Werkstatt + 7 Apparat + 6 Spielwerk)
- **E2E verified**: compiled via ScriptCompiler, 6 params, drive/warmth/bias/tone set
- **Example script**: `werkstatt_tube_saturator.py` — gentle warmth, aggressive crunch, vintage vocal
- ruff clean, CI green

## v1.54.0 (2026-07-05)

- **`werkstatt_spring_reverb.js` DSP script** — spring reverb with dispersive delay lines, transient-driven "boing" chirp response, and 4 detuned springs. Parameters: decay, damp, tension (delay time), boing (transient sensitivity), mix. Classic for surf rock, dub, guitar amps. Completes reverb family: algorithmic ✅ shimmer ✅ spring ✅
- **45 DSP scripts** (32 Werkstatt + 7 Apparat + 6 Spielwerk)
- **E2E verified**: compiled via ScriptCompiler, 5 params, decay/tension/boing/damp set
- **Example script**: `werkstatt_spring_reverb.py` — surf rock, dub, tight amp presets
- ruff clean, CI green

## v1.53.0 (2026-07-05)

- **`create_isorhythm` orchestration tool (302 MCP tools)** — repeating rhythm (talea) × repeating pitch (color) as independent cycles. When lengths differ, patterns phase-shift until realigning at LCM. Medieval motets (Machaut), Messiaen, Boulez. Distinct from ostinato (which repeats rhythm+pitch together)
- **E2E verified**: equal lengths (24 notes), phase shift 4×5 (LCM=20), single talea, complex rhythm, bad velocity/repeats/pitch/talea — 8/8 tests passed
- **+10 unit tests** for isorhythm talea/color independence, phase cycling, position, duration → 282 total
- **Example script**: `create_isorhythm.py` — classic, phase shift, minimalist
- **45 orchestration tools** total
- ruff clean, CI green

## v1.52.0 (2026-07-05)

- **`create_hocket` orchestration tool (301 MCP tools)** — melodic line split between 2-4 voices. Hocket (Latin "hoquet" = hiccup) divides a single melody so each voice plays only part of it, creating interlocking texture. Three split modes: alternate (round-robin), pairs (2 per voice), phrase (4 per voice). Medieval Notre Dame polyphony, African mbira, Balinese gamelan, Steve Reich
- **E2E verified**: alternate 2v (8 notes), 3 voices (12 notes), pairs, phrase, bad voices/split_mode/velocity/pitch — 8/8 tests passed
- **+10 unit tests** for hocket voice assignment, note preservation, position spacing → 272 total
- **Example script**: `create_hocket.py` — alternate, pairs, phrase patterns
- **44 orchestration tools** total
- ruff clean, CI green

## v1.51.0 (2026-07-05)

- **`create_bordun` orchestration tool (300 MCP tools)** — continuously sustained drone chord as a textural layer. Unlike pedal_point (single anchored note), bordun is a sustained chord — open fifths, octaves, or drone chords. Found in Scottish bagpipes, Indian tanpura, hurdy-gurdy, ambient drone, folk. Configurable intervals (1-8), retrigger mode (every N bars), 3/4 time support
- **E2E verified**: open fifth (2 notes), octave+fifth (3 notes), retrigger (4 notes), single drone, 3/4 time, bad root/octave/velocity — 8/8 tests passed
- **+10 unit tests** for bordun note generation, pitch mapping, retrigger, duration → 262 total
- **Example script**: `create_bordun.py` — open fifth, octave+fifth, minor triad, single drone
- **43 orchestration tools** total
- ruff clean, CI green

## v1.50.0 (2026-07-05)

- **`werkstatt_bitcrusher.js` DSP script** — standalone bitcrusher with bit-depth quantization (1-16 bits) and sample-rate reduction. Drive, DC offset, dry/wet mix. Dedicated bitcrusher separate from coldfold's combined wavefold+crush. Lo-fi, chiptune, industrial, vaporwave
- **44 DSP scripts** (31 Werkstatt + 7 Apparat + 6 Spielwerk)
- **E2E verified**: compiled via ScriptCompiler, 5 params (bits/rate/drive/offset/mix), param values set
- **Example script**: `werkstatt_bitcrusher.py` — lo-fi and extreme degradation presets
- ruff clean, CI green

## v1.49.0 (2026-07-05)

- **`create_hemiola` orchestration tool (299 MCP tools)** — 3:2 rhythmic displacement creating cross-rhythm illusion. Fundamental to West African, Afro-Cuban, jazz, and minimalist music. Brahms, Bernstein, Glass. Two patterns: "3:2" (classic) and "2:3" (inverse). Superimposes primary and secondary groups over same time span
- **E2E verified**: 3:2 pattern (5 notes), 2:3 pattern (5 notes), bars=2, bad pattern/bars/velocity/pitch/duration — 8/8 tests passed
- **+10 unit tests** for hemiola note count, ratio, timing, velocity → 242 total
- **Example script**: `create_hemiola.py` — 3:2 and 2:3 patterns
- **42 orchestration tools** total
- ruff clean, CI green

## v1.48.0 (2026-07-05)

- **`apparat_wavetable.js` DSP script** — wavetable synthesizer with 8 interpolated wavetables, scan position + LFO, unison detune (1-7 voices), ADSR. Completes Apparat synthesis methods: subtractive ✅ FM ✅ ring mod ✅ Karplus-Strong ✅ wavetable ✅
- **43 DSP scripts** (30 Werkstatt + 7 Apparat + 6 Spielwerk)
- **E2E verified**: compiled via ScriptCompiler, 10 params, pos/unison/pos_lfo_depth set
- **+10 unit tests** (TestWavetableDSP: header, params, tables, scan, unison, ADSR) → 232 total
- **Example script**: `apparat_wavetable.py`

## v1.47.0 (2026-07-05)

- **`werkstatt_vibrato.js` DSP script** — pitch vibrato via modulated delay line. Rate (0.1-20 Hz exp), depth (0.5-20 ms), shape (sine→triangle morph), stereo phase offset. Completes modulation family: chorus ✅ flanger ✅ phaser ✅ tremolo ✅ vibrato ✅
- **43 DSP scripts** (30 Werkstatt + 7 Apparat + 6 Spielwerk)
- **E2E verified**: compiled via ScriptCompiler, 4 params, rate/depth/shape/stereo set
- **+10 unit tests** (TestVibratoDSP: header, params, LFO, depth, shape, stereo) → 222 total
- **Example script**: `werkstatt_vibrato.py`

## v1.46.0 (2026-07-05)

- **`create_appoggiatura` orchestration tool (298 MCP tools)** — expressive leaning grace note: approach → main. The fourth and final essential baroque ornament (trill ✅, mordent ✅, turn ✅, appoggiatura ✅). Plays a neighbor note FIRST (usually 2/3 of duration), then resolves into main. Creates harmonic tension → release. Adjustable ratio (0.5-0.9), approach from above or below, slight accent on approach. Bach cello suites, Mozart operas, Chopin nocturnes. Completes the full ornaments set
- **E2E verified**: appoggiatura above (2 notes), below, equal split, same pitch, bad pitch/ratio/velocity/duration — 8/8 tests passed
- **+10 unit tests** for appoggiatura note order, timing, velocity, direction (374 total)
- **Example script**: `create_appoggiatura.py` — above + below appoggiatura
- **298 MCP tools** (260 low-level + 41 orchestration + 3 melodic)
- ruff clean, CI green
- **Ornaments set complete**: trill + mordent + turn + appoggiatura

## v1.45.0 (2026-07-05)

- **`create_turn` orchestration tool (297 MCP tools)** — circular ornament (gruppetto): main → upper → main → lower → main. Third of four essential baroque ornaments (trill ✅, mordent ✅, turn ✅, appoggiatura ❌). Upper/lower direction, adjustable interval. Mozart piano concertos, Beethoven sonatas, Bach partitas. One call replaces 5 manual note creations. Completes ornaments set: trill + mordent + turn
- **E2E verified**: upper turn (5 notes), lower turn, half-step, bad direction/interval/pitch/velocity/duration — 8/8 tests passed
- **+10 unit tests** for turn note order, timing, velocity, clamping (364 total)
- **Example script**: `create_turn.py` — upper + lower turn
- **297 MCP tools** (259 low-level + 40 orchestration + 3 melodic)
- ruff clean, CI green

## v1.44.0 (2026-07-05)

- **`create_mordent` orchestration tool (296 MCP tools)** — classical baroque ornament: main note → neighbor → main. One of the four essential ornaments (trill, mordent, turn, appoggiatura). Upper mordent flicks up, lower flicks down. Adjustable interval (1-7 semitones), timing split (40%/20%/40%). Bach two-part inventions, Mozart sonatas. One call replaces 3 manual note creations. Completes the ornaments set alongside create_trill
- **E2E verified**: upper mordent (3 notes), lower mordent, half-step, bad direction/interval/pitch/velocity, clamped neighbor — 8/8 tests passed
- **+10 unit tests** for mordent neighbor direction, timing split, velocity, clamping (354 total)
- **Example script**: `create_mordent.py` — upper + lower mordent
- **296 MCP tools** (258 low-level + 39 orchestration + 3 melodic)
- ruff clean, CI green

## v1.43.0 (2026-07-05)

- **`create_comping` orchestration tool (295 MCP tools)** — rhythmic chordal accompaniment: the most common accompaniment style in modern music. Play chords in a rhythmic pattern rather than sustained blocks. Jazz piano comping, funk guitar chops, reggae skanks, country boom-chick, neo-soul. Rhythm grid (x=play, -=rest, .=ghost), syncopation, chord JSON parsing, multi-chord progression. One call replaces 20-80 manual note creations. Unlike create_chord_progression (sustained blocks) or create_stab (house stabs), comping gives each chord a rhythmic identity
- **E2E verified**: jazz comping (64 notes, 4 chords), funk with ghosts, reggae skank 16 steps, syncopation, bad JSON/rhythm/velocity/chord type — 8/8 tests passed
- **+10 unit tests** for comping note generation, ghost velocity, rhythm parsing, syncopation (344 total)
- **Example script**: `create_comping.py` — jazz ii-V-I with syncopation
- **295 MCP tools** (257 low-level + 38 orchestration + 3 melodic)
- ruff clean, CI green

## v1.42.0 (2026-07-05)

- **`augment_notes` transformation tool (294 MCP tools)** — augmentation/diminution: the fourth classical motivic transformation. Multiplies note durations by a factor (0.25-4.0). Combined with transpose, reverse, and invert, completes the set of four fundamental transformations used by Bach, Beethoven, and every composition teacher. Two modes: "scale" (multiply both duration AND position — phrase slows down/speeds up) and "stretch" (multiply only duration, positions unchanged). Think Beethoven 5th: opening motif returns augmented (twice as slow) in recapitulation. Essential for: motivic development, fugue subjects, theme variations, rhythmic transformation
- **E2E verified**: augmentation x2 (5 notes), diminution x0.5 (8 notes), stretch mode, factor=1.0 no-op, bad factor/mode rejection, non-existent AU — 8/8 tests passed
- **+10 unit tests** for factor validation, duration math, mode logic (334 total)
- **Example script**: `augment_notes.py` — augmentation + diminution on C major scale
- **294 MCP tools** (256 low-level + 37 orchestration + 3 melodic)
- ruff clean, CI green

## v1.41.0 (2026-07-05)

- **`create_canon` orchestration tool (293 MCP tools)** — strict melodic imitation with delayed voice entries. The foundation of contrapuntal music: Pachelbel's Canon, "Row Row Row Your Boat", Bach fugue subjects, film score layering. Unlike create_counterpoint (generates a new line), a canon copies the SAME melody into each voice — just shifted in time and pitch. 2-6 voices, per-voice transposition, velocity decay, up/down entry order. One call replaces 16-48 manual note creations. Essential for: rounds, fugues, film scores, call-and-response layering, minimalism
- **+10 unit tests** for canon voice generation + transposition + direction + clamping (324 total)
- **293 MCP tools** (255 low-level + 35 orchestration + 3 melodic)

## v1.40.0 (2026-07-05)

- **`create_pedal_point` orchestration tool (292 MCP tools)** — sustained bass note under changing chords. The foundational technique in film scoring (Hans Zimmer drones), organ preludes (Bach), and rock ballads. Retrigger or sustained pedal mode. Full chord name parsing (maj/min/m7/maj7/dom7/sus2/sus4/dim/aug + implicit major). Adjustable time signatures (3/4, 4/4, 6/8). One call replaces 13-34 manual note creations. Essential for: film scoring, organ music, rock ballads, ambient drones, harmonic tension
- **+10 unit tests** for pedal point generation + chord parsing (314 total)
- **292 MCP tools** (254 low-level + 35 orchestration + 3 melodic)

## v1.35.0 (2026-07-05)

- **`create_bass_drop` orchestration tool (287 MCP tools)** — descending pitch sweep into sustained sub bass for dubstep/EDM/trap. Two phases: sweep (16th-note resolution pitch glide) + hold (sustained landing note). 3 curves (linear/exp/log), adjustable sweep (0.25-8 beats) and hold (0-16 beats). Complement to `create_riser` — riser builds up, bass drop lands. One call replaces 10-65 manual note creations. Essential for: dubstep drops, EDM build-and-drop, trap bass falls, impact transitions
- **E2E verified**: default drop (33 notes, 32 sweep + 1 hold), sweep-only (64 notes), short aggressive (9 notes), error handling
- **287 MCP tools** (254 low-level + 30 orchestration + 3 melodic)
- ruff clean, CI green

## v1.34.0 (2026-07-05)

- **`create_break` orchestration tool (286 MCP tools)** — classic drum break patterns for jungle/DnB/hip-hop/breakbeat. 6 presets: Amen Break, Think Break, Ashanti, Funky Drummer, When the Levee, Synthetic. 1-8 bars with variation modes (none/fill/humanize/drop) and swing. One call replaces 15-120 manual note creations. Essential for: breakbeat-based genres, sampling workflows, drum programming
- **E2E verified**: Amen (14 notes), Think 2-bar fill (26 notes), Funky Drummer humanized (22 notes), Amen 2-bar drop (25 notes), Synthetic with swing (14 notes), error handling
- **286 MCP tools** (254 low-level + 29 orchestration + 3 melodic)
- ruff clean, CI green

## v1.33.0 (2026-07-05)

- **`create_stab` orchestration tool (285 MCP tools)** — rhythmic chord stabs for house/disco/funk. Grid pattern with 'x' (stab), '-' (rest), '.' (ghost). Cycles through chord progressions. Adjustable octave, velocity, stab duration, pattern length. Ghost stabs use 45% velocity and shorter duration. One call replaces 20-60 manual note creations. Essential for: house off-beat stabs, funk syncopated punches, garage/shuffle patterns
- **E2E verified**: house Cm7 off-beat (16 notes, 4 stabs), funky F7/Cm7 with ghost notes (28 notes, 7 hits), all-rests error, invalid rhythm error
- **285 MCP tools** (254 low-level + 28 orchestration + 3 melodic)
- ruff clean, CI green

## v1.32.0 (2026-07-05)

- **`create_riser` orchestration tool (284 MCP tools)** — ascending pitch sweep for build-up transitions. 3 curves (linear, exp, log). Adjustable pitch range (MIDI 0-127), step count (8-128), length (0.25-16 beats). Velocity ramps up proportionally. One call replaces 10-50 manual note creations. Essential for: build-ups before drops, section transitions, tension creation
- **E2E verified**: 32 notes, pitch 36→84, exp curve ascending, linear curve 16 notes, error handling
- **284 MCP tools** (254 low-level + 27 orchestration + 3 melodic)
- ruff clean, CI green

## v1.31.0 (2026-07-05)

- **`werkstatt_stereowidth.js`** — M/S stereo width processor. 5 params: width (0=mono, 0.5=neutral, 1.5=wide), lowTrim (mono bass below crossover), lowFreq (50-500Hz crossover), mix, output. M/S encode → width scaling on side → low-freq trim → M/S decode. Essential for mastering: wide highs, mono bass
- **41 DSP scripts** (29 Werkstatt + 6 Apparat + 6 Spielwerk)
- **E2E verified**: compiled, 5 params, width 0.5→1.2, lowTrim 0→0.7

## v1.30.0 (2026-07-05)

- **`apparat_pluck.js`** — Karplus-Strong plucked string synth. 7 params: decay (string decay rate), damping (lowpass strength), brightness (noise burst spectral content), attack, release, detune, volume. Noise burst excites delay line, averaging filter creates natural string decay. Unique physical modeling sound unavailable in other Apparat scripts
- **40 DSP scripts** (28 Werkstatt + 6 Apparat + 6 Spielwerk)
- **E2E verified**: compiled via ScriptCompiler, 7 params, brightness 0.7→0.9, code header readback OK

## v1.29.0 (2026-07-05)

- **`werkstatt_transient.js`** — transient shaper with dual envelope followers. 4 params: attack (±12 dB transient boost/cut), sustain (±12 dB sustain boost/cut), mix, output. Fast envelope (~5ms) detects transients, slow envelope (~80ms) detects sustain, independent gain on each component. No threshold needed — works on any material. Essential for drum mixing
- **39 DSP scripts** (28 Werkstatt + 5 Apparat + 6 Spielwerk)
- **E2E verified**: compiled, 4 params, attack 0.5→0.8, sustain 0.5→0.3

## v1.28.0 (2026-07-05)

- **`werkstatt_deesser.js`** — dynamic de-esser, band-split architecture. 7 params: freq (2-12kHz crossover), threshold (-40..0 dB), ratio (1:1..10:1), attack, release, mix, output. 2nd-order Linkwitz-Riley HPF isolates sibilance, envelope-followed gain reduction on high band only. Completes vocal chain: EQ → compressor → de-esser → exciter → limiter
- **38 DSP scripts** (27 Werkstatt + 5 Apparat + 6 Spielwerk)
- **E2E verified**: compiled, 7 params, threshold 0.5→0.65, freq 0.4→0.8

## v1.27.0 (2026-07-05)

- **`werkstatt_exciter.js`** — harmonic exciter, band-split architecture. 5 params: freq (800Hz-12kHz crossover), harmonics, drive, mix, output. Cascaded one-pole HPF + cubic nonlinearity, parallel wet/dry. Completes mastering chain: EQ → compressor → exciter → limiter
- **37 DSP scripts** (26 Werkstatt + 5 Apparat + 6 Spielwerk)
- **E2E verified**: compiled, 5 params, freq 0.3→0.75, harmonics 0.5→0.85

## v1.26.0 (2026-07-05)

- **`werkstatt_limiter.js`** — brickwall limiter w/ lookahead + TPDF dither. 5 params: ceiling, release, lookahead, dither, mix. Instant attack, smooth release, circular buffer
- **`werkstatt_exciter.js`** — harmonic exciter, band-split architecture. 5 params: freq (800Hz-12kHz crossover), harmonics, drive, mix, output. Cascaded one-pole HPF + cubic nonlinearity, parallel wet/dry. Completes mastering chain: EQ → compressor → exciter → limiter
- **37 DSP scripts** (26 Werkstatt + 5 Apparat + 6 Spielwerk)
- **E2E verified**: compiled, 5 params, freq 0.3→0.75, harmonics 0.5→0.85

## v1.25.1 (2026-07-05)

- **+31 unit tests** for music_theory functions — parse_melody_pattern (11), scale_to_pitches (6), chord_to_pitches (8), GENRE_PRESETS (6)
- **272 unit tests** total (was 241), all passing
- ruff clean, CI green

## v1.25.0 (2026-07-05)

- **`werkstatt_paraeq.js`** — 3-band parametric EQ + HP/LP. 12 params: 3 × (freq, gain, Q) + hp_freq + lp_freq + mix. Biquad (RBJ cookbook), signal chain HP→B1→B2→B3→LP
- **35 DSP scripts** (24 Werkstatt + 5 Apparat + 6 Spielwerk)
- **E2E verified**: compiled, 12 params, band1_gain 0→6, band2_q 1→3.5

## v1.24.0 (2026-07-05)

- **`werkstatt_compressor.js`** — soft-knee peak compressor. 7 params: threshold, ratio, attack, release, makeup, mix, knee. Peak detection, one-pole envelope, stereo-linked
- **Integration test fix** — skips when Playwright chromium unavailable instead of failing
- **34 DSP scripts** (23 Werkstatt + 5 Apparat + 6 Spielwerk)
- **E2E verified**: compiled, 7 params, threshold/ratio set, code readback OK

## v1.23.3 (2026-07-05)

- **`werkstatt_multifilter.js`** — multi-mode SVF filter (LP/HP/BP/Notch). 5 params: mode, cutoff, resonance, drive, mix. Chamberlin topology
- **33 DSP scripts** (22 Werkstatt + 5 Apparat + 6 Spielwerk)
- **E2E verified**: compiled, 5 params, mode switching, resonance cranked

## v1.23.2 (2026-07-05)

- **`werkstatt_overdrive.js`** — asymmetric soft-clip overdrive. 5 params: drive, tone, level, bias, dry. Even harmonics for warmth, dry blend for parallel
- **32 DSP scripts** (21 Werkstatt + 5 Apparat + 6 Spielwerk)
- **E2E verified**: compiled, 5 params, set_param works

## v1.23.1 (2026-07-05)

- **`werkstatt_stereo_delay.js`** — stereo delay with ping-pong, feedback, tone filter. 6 params. Fills delay gap in DSP library
- **31 DSP scripts** (20 Werkstatt + 5 Apparat + 6 Spielwerk)
- **E2E verified**: compiled, 6 params, set_param works

## v1.23.0 (2026-07-05)

- **`apply_articulation`** — staccato/legato/tenuto/accent for existing notes. Duration reshaping for phrasing. Accent boosts velocity on downbeats
- **13 unit tests** — 228→241 total
- **E2E verified**: staccato (240→120), legato (240→228), accent (beats=0.9, off-beats=0.5)
- **55 examples** (added apply_articulation.py)
- **283 MCP tools**, **26 orchestration tools**

## v1.22.0 (2026-07-05)

- **`apply_velocity_curve`** — deterministic velocity envelope across notes (ramp_up/ramp_down/arc/trough/power). Unlike humanize (random), applies mathematical curve shape — build-ups, fade-ins, crescendo rolls, expressive phrasing. Power exponent for exponential curves
- **15 unit tests** — 213→228 total
- **E2E verified**: ramp_up (0.2→1.0, 16 notes), arc (peak=0.95), power=2.0 (slow rise)
- **54 examples** (added apply_velocity_curve.py)
- **282 MCP tools**, **25 orchestration tools**

## v1.21.0 (2026-07-05)

- **`apply_sidechain`** — new orchestration tool: sidechain ducking via volume automation. Classic pumping/breathing effect for house/techno/EDM. Adjustable depth, attack, release, kick interval
- **`create_ghost_notes`** — new orchestration tool: ghost notes (quiet grace notes) for funk/R&B/neo-soul/hip-hop drumming. Seeded reproducibility, avoids occupied positions
- **12 unit tests** for sidechain ducking curve and ghost note placement logic — 201→212 total
- **E2E test** for sidechain (272 events, 16 kicks, error handling) and ghost_notes (4 added, error handling)
- **53 examples** (added apply_sidechain.py, create_ghost_notes.py)
- **281 MCP tools**, **24 orchestration tools**, ruff clean, CI green

## v1.20.0 (2026-07-05)

- **`create_call_response`** — new orchestration tool: call-and-response patterns (antecedent/consequent phrases). Foundation of blues, jazz, hip-hop, electronic. Alternates call → response with adjustable repeats
- **`create_walking_bass`** — new orchestration tool: walking bass lines over chord progressions. Beat 1=chord root, beat 2=chord tone, beat 3=passing tone, beat 4=approach note. Jazz/blues/swing
- **11 unit tests** for call_response (interleave, timing, velocity) and walking_bass (beat positions, approach notes, bass range) — 190→201 total
- **E2E test** for call_response (blues ×4, 1 repeat, error handling) and walking_bass (ii-V-I, 2 bars/chord, error handling)
- **51 examples** (added create_call_response.py, create_walking_bass.py)
- **279 MCP tools**, **22 orchestration tools**, ruff clean, CI green

## v1.19.1 (2026-07-05)

- **`create_scale_run`** — new orchestration tool: ascending/descending scale sequences for fills and transitions. 14 scales, 1-4 octaves, adjustable step duration
- **8 unit tests** for scale run generation (ascending/descending, multi-octave, blues/chromatic/pentatonic) — 182→190 total
- **E2E test** for scale_run (C minor up 1 oct, A blues down 2 oct, error handling)
- **49 examples** (added create_scale_run.py)
- **277 MCP tools**, **20 orchestration tools**, ruff clean, CI green

## v1.19.0 (2026-07-05)

- **`apply_swing`** — new orchestration tool: pure swing feel for existing notes, deterministic, no randomness. 16th/8th grid, 0-1 depth. 0.58 = classic hip-hop/lofi swing
- **`create_polyrhythm`** — new orchestration tool: polyrhythms with two streams of different subdivision counts (3:4, 2:3, 5:7, 7:8). Jazz, electronic, progressive, math rock
- **12 unit tests** for swing offset logic and polyrhythm generation (170→182 total)
- **E2E test** for apply_swing (0.5/0.0/8th grid) and create_polyrhythm (3:4, 2:3, error handling)
- Bugfix: swing=0.0 no longer increments shift counter
- **276 MCP tools**, **19 orchestration tools**, ruff clean, CI green

## v1.18.1 (2026-07-05)

- **3 new Werkstatt DSP scripts**: `werkstatt_flanger.js` (stereo flanger with LFO delay + feedback), `werkstatt_noisegate.js` (noise gate with threshold/hold/release/range), `werkstatt_tremolo.js` (tremolo with sine→square shape)
- E2E verified: all 3 compile, params created, set_param works
- **30 DSP scripts** total (19 Werkstatt + 5 Apparat + 6 Spielwerk)

## v1.18.0 (2026-07-05)

- **`create_drum_fill`** — new orchestration tool: drum fills/transitions with 5 types (build, break, roll, crash, tom). Adjustable density and bar length. One call replaces 10-30 note creations.
- **`create_ostinato`** — new orchestration tool: repeating melodic/rhythmic pattern as foundation layer. Scale-based, 1-16 repeats. Common in minimalism, electronic, and film music.
- **`create_crescendo`** — new orchestration tool: apply crescendo/decrescendo to existing notes. Linear, exponential, or logarithmic velocity curves.
- **E2E verified**: drum_fill (build 7 notes, roll 45 notes), ostinato (C minor 1-5-3-5 ×4 = 16 notes), crescendo (exp 0.2→0.9, 23 notes modified)
- **17 orchestration tools** total, **274 MCP tools**, ruff clean, CI green

## v1.17.0 (2026-07-05)

- **`create_counterpoint`** — new orchestration tool: generate counter-melody in contrary motion. Mirrors melody around center pitch. Auto-creates target track.
- **`humanize_notes`** — new orchestration tool: velocity/timing/duration variation + swing. Seeded mulberry32 PRNG for reproducibility.
- **`create_harmony`** — new orchestration tool: generate harmony from existing notes. 8 intervals (diatonic thirds/fifths/sixths + chromatic). Up/down direction.
- **`reverse_notes`** — melodic variation: retrograde (reverse note order in region)
- **`invert_notes`** — melodic variation: mirror inversion around axis pitch (newPitch = 2*axis - oldPitch)
- **`suno-prompt-engineering` skill** — concentrated Suno prompt engineering guide from 20+ KB files
- **7 new examples**: create_melody, create_bassline, create_arpeggio, humanize_notes, create_harmony, create_counterpoint, reverse_invert_notes
- **TOOL_CATALOG**: all 27 DSP scripts documented (was 7)
- **KB index sync**: 31→33 entries (all files covered)
- **bridge.py**: `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` env var for system chromium
- **271 MCP tools**, **43 examples**, **9 skills**, ruff clean, CI green

## v1.16.1 (2026-07-05)

- **`create_melody`** — new orchestration tool: generate melodies from scale + rhythmic pattern using scale degrees (1-7). Supports 14 scales, rests (0), sustains (-), octave shifts (+). One call replaces 10-30 `create_note` calls.
- **`create_bassline`** — new orchestration tool: generate basslines from root + rhythmic pattern. Low octave default (C2=36), high velocity (0.9), octave up/down (+/_). One call replaces 8-20 `create_note` calls.
- **`create_arpeggio`** — new orchestration tool: generate arpeggios from chord name with 6 patterns (up/down/updown/downup/random/chord) and 6 rates (32/16/8/4/16t/32t). One call replaces 8-32 `create_note` calls.
- **`humanize_notes`** — new orchestration tool: add human-like velocity, timing, duration variation and swing to existing notes. Seeded mulberry32 PRNG for reproducibility. Makes programmed MIDI feel less robotic.
- **`create_harmony`** — new orchestration tool: generate harmony parts from existing notes. Diatonic (thirds/fifths/sixths) and chromatic (octave/fifth/fourth/major-minor third) intervals. Up/down direction. Auto-creates target track.
- **`create_counterpoint`** — new orchestration tool: generate counter-melody in contrary motion. Mirrors melody around center pitch. Adjustable interval. Auto-creates target track.
- **`reverse_notes`** — new melodic variation tool: reverse note order in a region (retrograde). Positions mirrored, durations/velocities preserved.
- **`invert_notes`** — new melodic variation tool: invert melody around a pitch axis (mirror reflection). newPitch = 2*axis - oldPitch.
- **`opendaw_mcp/music_theory.py`** — shared music theory module: `NOTE_TO_PITCH`, `CHORD_INTERVALS`, `SCALE_INTERVALS`, `GENRE_PRESETS`, `chord_to_pitches()`, `scale_to_pitches()`
- **DRY refactor**: `create_chord_progression` and `create_genre_track` now import from `music_theory` instead of duplicating dicts inline
- **2 new genres**: `coldwave` (110 BPM, dark bass) and `hiphop` (90 BPM, boom bap) — `create_genre_track` now supports 8 genres
- **14 scale types**: major, minor, harmonic minor, melodic minor, dorian, phrygian, lydian, mixolydian, locrian, pentatonic major/minor, blues, chromatic
- **38 new unit tests** (test_music_theory.py) — 150 total
- ruff clean, 271 MCP tools, no regressions

## v1.16.0 (2026-07-05)

- **Modular architecture** — infrastructure extracted from 13K-line `server.py` into `opendaw_mcp/` package:
  - `constants.py` — lookup tables (TIDAL_RATE_MAP, DELAY_SYNC_MAP, WAVESHAPER_FUNCS, REVAMP_SECTIONS)
  - `bridge.py` — `HeadlessDawBridge` class (Playwright bridge, DAW_HELPERS injection)
  - `utils.py` — pure-Python helpers (`_parse_wav`, `_compute_lufs`, `_ok`, `_err`, `_safe_filename`, `_safe_path`, `_clamp_script_param`)
  - `__init__.py` — public API, all symbols re-exported for backward compat
- **`OpendawServer` facade** — class providing `bridge` + all `mcp_opendaw_*` tools as methods. Framework wrappers (LangChain, AutoGen, CrewAI) now work via this single interface.
- **server.py: 13244 → 12955 lines** (infrastructure moved to package modules)
- **0 regressions** — 93 unit tests pass, ruff clean, all framework wrappers functional, 263 MCP tools intact

## v1.15.2 (2026-07-04)

- **CrewAI toolkit** — `opendaw_mcp/crewai_tools.py` wraps 27 tools for CrewAI. Custom `OpendawCrewAITool` class, category filtering, shared server instance.
- **GitHub Discussions seeded** — 5 discussions: release announcement, 3 FAQ (bridge, GPU, MCP clients), genre showcase
- **33 examples total** (added `crewai_integration.py`)

## v1.15.1 (2026-07-04)

- **AutoGen toolkit** — `opendaw_mcp/autogen_tools.py` wraps 27 tools for Microsoft AutoGen. Category filtering, shared server instance.
- **Framework integration docs page** — LangChain + AutoGen + MCP direct + Hermes, with comparison table
- **32 examples total** (added `autogen_integration.py`)

## v1.15.0 (2026-07-04)

- **LangChain toolkit** — `opendaw_mcp/langchain_tools.py` wraps 30+ tools as LangChain `StructuredTool` objects. Category filtering, auto bridge start. Use with any LangChain agent.
- **Docs site** — mkdocs-material at https://ameobius.github.io/opendaw-mcp/ — 21 pages, dark mode, search, auto-deploy via GitHub Actions
- **PR template** — structured checklist for contributors
- **PyPI metadata** — Documentation, Issues, Changelog URLs pointing to docs site
- **dev.to article** — "Controlling a DAW with AI Agents via MCP" (in `promotion/`)
- **32 examples total** (added `langchain_integration.py`, `autogen_integration.py`)

## v1.14.4 (2026-07-04)

- **Final 2 genre examples (E2E verified)**: `genre_lofi.py` (82 BPM, swung drums, jazzy ii-V-I, warm) and `genre_trap.py` (145 BPM, fast hi-hat rolls, gliding 808, dark minor). **All 8 genres from the skill now covered with E2E examples.** 30 examples total.

## v1.14.3 (2026-07-04)

- **3 more genre examples (E2E verified)**: `genre_hiphop.py` (85 BPM, boom bap, 808 Ab minor), `genre_dnb.py` (174 BPM, Amen break, reese+sub F minor), `genre_house.py` (124 BPM, 4-on-floor, off-beat chord stabs). 28 examples total, 6 genres covered.

## v1.14.2 (2026-07-04)

- **2 new genre examples (E2E verified)**: `genre_coldwave.py` (100 BPM, Am-Fmaj7-Cmaj-Gdom7, 4 tracks, Dattorro+Waveshaper) and `genre_ambient.py` (70 BPM, Cmaj7-Amin7-Fmaj7-Gmaj7, pad+bell+texture, long reverbs). 25 examples total.
- Fixed return key names in genre examples (`notes_created` / `total_notes` / `lanes`)

## v1.14.1 (2026-07-04)

- **`opendaw-genres` skill** — 8 genre templates with concrete parameters: techno, coldwave, hip-hop, ambient, DnB, house, lofi, trap. BPM, track layout, drum patterns, bass lines, chord progressions, effect chains, pan, LUFS targets. 8 skills total.

## v1.14.0 (2026-07-04)

- **2 new agent skills**: `suno-to-opendaw` (6-stage Suno→stems→openDAW→mix→master→export pipeline) and `dsp-script-authoring` (custom Werkstatt/Apparat/Spielwerk DSP script writing guide). 7 skills total.
- `set_marker_repeat` MCP tool — marker repeat count control (0=infinite)
- **263 MCP tools** (254 low-level + 8 orchestration)

## v1.13.0 (2026-07-04)

- **Preset Management**: 2 new MCP tools for openDAW preset format (.opb). `save_effect_preset` encodes any audio effect chain into a shareable .opb bundle. `load_effect_preset` decodes .opb and applies it to a project.
- 5 Werkstatt presets published to upstream (PR #284): Dark Saturation, Plate Reverb, Cold Fold Distortion, Stereo Phaser, Stereo Chorus.

## v1.12.1 (2026-07-04)

- **Stem Splitter**: 2 new MCP tools for SOTA open-source source separation. `split_stems` runs 7 modes locally on GPU (ensemble, scnet, bs6, polarformer, dereverb, drumsep, denoise). Optional auto-import into DAW.

## v1.12.0 (2026-07-04)

- **Agent Skills**: 8 structured skill files in `skills/` directory — adaptive mix→master, suno-to-opendaw, dsp-script-authoring, opendaw-genres, opendaw-automation, track architecture, sound design, effect routing. Decision points for genre-adaptive workflows. Agent-agnostic.
- **26 DSP scripts total** (15 Werkstatt + 5 Apparat + 6 Spielwerk)

## v1.11.9 (2026-07-04)

- **CodeRabbit fixes**: reverb stereo width (separate L/R comb banks, M/S width on reverb tail), paulstretch cursor split (independent read/write cursors, proper frame emission gating)

## v1.11.8 (2026-07-04)

- **New Werkstatt script**: ring modulator with envelope-followed frequency modulation — workaround for MIDI input limitation in Werkstatt audio effects

## v1.11.7 (2026-07-04)

- **Suno→openDAW pipeline example**: import AI-generated track, add mastering chain (tape sat + lookahead comp), reverb send bus, MIDI arp layer, render + stems + LUFS

## v1.11.6 (2026-07-04)

- **4 new Spielwerk MIDI effect scripts**: chord memory, strummer, velocity scaler, MIDI delay
- **1 new Python example**: Suno→openDAW pipeline

## v1.11.5 (2026-07-04)

- **7 new DSP scripts**: DC remover + stereo width, allpass filter, 2-operator FM synth, chord memory, strummer, velocity scaler, MIDI delay
- **Coldfold fix**: removed unused `range` variable (CodeRabbit review)

## v1.11.4 (2026-07-04)

- **1 new Apparat script**: ring modulator synth with ADSR and sub-oscillator

## v1.11.3 (2026-07-04)

- **1 new Werkstatt script**: real-time pitch shifter via delay-line sweep
- **Ruff lint fixes**: removed unused imports/variables

## v1.11.2 (2026-07-04)

- **10 DSP bug fixes** synced from upstream PR #283 CodeRabbit review: darksat DC blocker, chorus delay buffer, coldfold slew scaling, lookahead gain reduction, reverb comb filter indices, shimmer per-channel pitch shifter, phaser stable allpass topology, subcrusher bidirectional glide, arpeggiator block boundaries
- **2 new Werkstatt scripts**: ADSR trim + granular time-stretch

## v1.11.1 (2026-07-04)

- **Scriptable device mapping info** — `list_script_params` now returns full `@param` mapping metadata (min, max, mapping type, unit)
- **Range validation** — `set_script_param` validates values against `@param` declarations: bool snaps, int rounds+clamps, linear/exp clamps
- **+15 unit tests** (93 total) — TestScriptParamClamping
- **+6 integration E2E tests** — bridge startup, globals, track ops, scriptable compile, param clamping, latency benchmark (avg 4ms round-trip)
- **5 new Werkstatt DSP scripts** — reverb, chorus, phaser, lookahead compressor, shimmer delay

## v1.11.0 (2026-07-04)

- **`apply_mix_preset`** — 8th orchestration tool: batch volume/pan/mute/solo across all tracks. Named presets (lofi, house, balanced, wide) or custom JSON

## v1.10.0–v1.10.2 (2026-07-04)

- **7 orchestration tools** — high-level composers for agents: `create_notes_batch`, `create_drum_pattern`, `create_chord_progression`, `add_mastering_chain`, `create_genre_track`, `create_song_structure`, `automation_sweep`
- **Official ScriptCompiler migration** — `set_script_device_code` now uses the real ScriptCompiler from `@opendaw/studio-adapters`
- **Stems export fix** — `useInstrumentOutput` changed from True→False. Stems now route through channel strip
- **`export_dry_stem`** — new tool for freeze/flatten/re-amp workflows
- **Device-specific parameter tools** — Waveshaper equations, Crusher bits/crush, Revamp EQ sections, Tidal LFO rate, Delay sync
- **+23 new unit tests** (54 total)

## v1.9.x (2026-07-03)

- **DRY refactoring: 17 DAW_HELPERS** — ~295 replacements, 0 raw enumeration patterns
- **CLI commands** — `--version`, `--list-tools`, `--help`
- **93 unit tests** — pytest covering helpers, WAV parsing, LUFS computation
- **Security hardening** — path traversal fixes, case-sensitive extension stripping
- **PEP 561** — `py.typed` marker for type checker support
- **Social preview banner** — custom OpenGraph image

---

For the full changelog including v1.0–v1.8, see the [GitHub releases page](https://github.com/ameobius/opendaw-mcp/releases).
