# Changelog

## v1.357.0 (2026-07-06)

- **`add_genre_effects`** — Genre-specific effect chains in one call. 15 genres with character-appropriate routing: house (sidechain + Dattorro + widener + maximizer), techno (pumping comp + delay + waveshaper), dnb (aggressive comp + reverb + reese), metal (heavy waveshaper + comp + loud maximizer), ambient (long reverb, no compression), lofi (gentle), etc. Each chain targets specific tracks (bass/drums/vocals/output). Saves 5-10 individual calls. 20 unit tests. 522 MCP tools.

## v1.356.0 (2026-07-06)

- **`auto_master`** — Adaptive mastering meta-tool. Chains analyze_mix → add_mastering_chain → auto_gain in one call. 6 platform targets (Spotify/Apple/YouTube/Tidal/SoundCloud/Club), 4 styles (balanced/warm/loud/transparent), true peak ceiling. 18 unit tests. 521 MCP tools. One call replaces 3-5 mastering tool calls.
- **Promo materials updated** — dev.to article and HN Show post rewritten with 520 tools/130 DSP, produce_full_track demo, hardware compressor table, 35+ genres.

## v1.355.0 (2026-07-06)

- **`werkstatt_true_peak_limiter.js`** — True peak limiter with inter-sample peak detection (4x oversampling). Lookahead delay line, fast attack, adjustable release, hard clip safety. -1 dBTP ceiling for streaming compliance (Spotify/Apple/YouTube). 130 DSP scripts. Essential for mastering — prevents codec distortion on streaming platforms.

## v1.354.0 (2026-07-06)

- **`create_descant`** — Descant counter-melody generator. 5 types: soaring (long sustained rising notes, anthemic), weaving (interlocking phrases filling melody gaps), pedal_tone (sustained high 5th/tonic), call_response (short answering phrases), ornamental (fast decorative runs, baroque). 3 scales, octave 5+, 2-8 bars. Seeded PRNG. 26 unit tests. 520 MCP tools. Secondary melody above the main tune — choral, worship, folk, ballads.
- **`one_call_production.py`** — Example demonstrating arrange_full_song + produce_full_track.
- **Sound-design skill** — Added 7 new DSP entries (thermal/fet/ssl/nyquist/bx/psycho compressor table).

## v1.353.0 (2026-07-06)

- **`produce_full_track`** — Ultimate meta-tool: produces a complete track in one call. Chains 6 steps: set_bpm → arrange_full_song → create_drum_pattern → create_bassline → apply_mix_preset → render_full (optional). One call replaces 15-20 individual tool calls. Agent specifies structure, key, genre, tempo — everything else automatic. 20+ genres, render optional. 22 unit tests. 519 MCP tools. The one-call production pipeline.

## v1.352.0 (2026-07-06)

- **`werkstatt_ssl_bus_comp.js`** — SSL G-series bus compressor. VCA-based with RMS detection (256-sample window), stepped ratios (2:1/4:1/10:1), stepped attack (0.1-30ms), auto-release mode (program-dependent, heavy compression → faster release), makeup gain. 129 DSP scripts. The "glue" compressor for mix bus — subtle but transformative.

## v1.351.0 (2026-07-06)

- **`arrange_full_song`** — Meta-tool: arranges a complete song from structural sections in one call. Parses "intro:4,prechorus:2,chorus:4,verse:8,bridge:4,outro:4" format. Calls section generators (create_intro, create_prechorus, create_arpeggio for chorus/verse, create_bridge, create_interlude, create_transition, create_outro, create_coda) with automatic start_beat tracking. Creates song structure markers. 9 valid sections, type variants for each. 27 unit tests. 518 MCP tools. Eliminates 8+ separate calls with manual beat offset calculation — one call builds the whole song skeleton.

## v1.350.0 (2026-07-06)

- **`werkstatt_psycho_bass.js`** — Psychoacoustic bass enhancer (MaxxBass/RBass style). Generates harmonics of sub-bass frequencies via polynomial nonlinearity (x²→x⁵). Ear/brain reconstructs missing fundamental from harmonics. Crossover 60-300Hz, 2-5 harmonics, intensity control. 128 DSP scripts. Makes bass audible on laptop/phone speakers without subwoofer.

## v1.349.0 (2026-07-06)

- **`create_prechorus`** — Pre-chorus section generator. 5 types: build (crescendo ii-IV-V-V, velocity and density increase), pedal (sustained V chord, melodic build over dominant), stall (rhythmic stasis on ii-V, repetition), lift (melodic ascent climbing scale degrees), suspending (sus4→sus2→resolve repeated, delays tonic). 3 scales, 2-4 bars. Seeded PRNG. 29 unit tests. 517 MCP tools. Tension builder before chorus — amplifies verse energy toward chorus impact.

## v1.348.0 (2026-07-06)

- **`create_transition`** — Transition section generator. 5 types: key_shift (modulation via pivot chord, up/down 1-7 semitones), tempo_ramp (accel/ritardando via duration scaling), texture_build (sparse→dense, voices added), texture_thin (dense→sparse, voices removed), drop (full→silence→re-entry). 3 scales, 2-8 bars. Direction + interval params. Seeded PRNG. 32 unit tests. 516 MCP tools. Active movement between sections — unlike interlude (passive connective tissue).

## v1.347.0 (2026-07-06)

- **`werkstatt_fet_comp.js`** — FET compressor (Urei 1176 style). Lightning-fast 0.02-4ms attack, program-dependent release (faster after loud peaks), 4 ratio modes (4:1/8:1/12:1/20:1 all-buttons-in), soft knee, output transformer saturation. 7 params. 127 DSP scripts. Drums, vocals, bass, aggressive rock compression.

## v1.346.0 (2026-07-06)

- **`werkstatt_thermal_comp.js`** — Optical compressor (LA-2A style). Photoresistor gain reduction with slow program-dependent attack/release, tube saturation on output for warmth. 5 params: peak_reduce, gain, tube, speed, mix. 126 DSP scripts. Vocals, bass, glue compression.

## v1.345.0 (2026-07-06)

- **`werkstatt_nyquist_comp.js`** — Parallel/New York compression. Dry signal blended with heavily compressed parallel path. Peak envelope detector, adjustable threshold/ratio/attack/release, makeup gain on compressed path. 125 DSP scripts. Increases perceived loudness and detail without killing transients — drums, vocals, mix bus.

## v1.344.0 (2026-07-06)

- **`werkstatt_bx_saturator.js`** — BX-style multi-band saturator. 3-band crossover (200Hz/2kHz) with independent saturation per band: tube-style 2nd harmonic on lows, tape-style 3rd harmonic on mids, transformer-style odd harmonics on highs. Blend control, output trim. 124 DSP scripts. Mixing/mastering harmonic enhancement.

## v1.343.0 (2026-07-06)

- **`werkstatt_tank_reverb.js`** — Spring tank reverb (Accutronics Type 9). 4 dispersive delay lines, allpass dispersion for metallic "boing" character, damping lowpass, drive saturation into tank, stereo spread, predelay, DC blocker. 5 params: decay, damp, spread, drive, mix. 123 DSP scripts. Surf rock, dub, reggae, guitar amp reverb.

## v1.342.0 (2026-07-06)

- **`create_coda`** — Coda section generator. 5 types: theme (final statement, fermata on last note), vamp (I-IV-V-I repeat with velocity fade), codetta (2-bar tag, scale run into tonic fermata), postlude (instrumental winding down after vocals), fanfare (ascending arpeggios + tutti hits, triumphant). 3 scales, 2-8 bars. Seeded PRNG. 34 unit tests. 515 MCP tools. Formal closing — concludes rather than fades.

## v1.341.0 (2026-07-06)

- **`create_interlude`** — Interlude section generator. 5 types: instrumental (solo melodic break over sparse bass), atmospheric (sustained I-IV-V-I pad chords), breakdown (single root → add fifth → add stabs, layer build), reprise (callback motif at different octave), contrapuntal (2-3 independent lines, contrary motion). 3 scales, 2-4 bars. Seeded PRNG. 31 unit tests. 514 MCP tools. Connective tissue between sections — shorter and more textural than bridge.

## v1.340.0 (2026-07-06)

- **`create_bridge`** — Bridge section generator. 5 types: breakdown (sparse bass + stabs, tension through absence), modulation (key shift up m3, same rhythm new centre), solo (dense melodic line over I-IV-V-I chords, 8th notes), atmospheric (sustained chromatic tones, no clear harmony), surprise (staccato bursts at odd positions, rhythmic displacement). 3 scales, 2-8 bars. Seeded PRNG. 32 unit tests. 513 MCP tools. Completes the section framing trio: intro → body → bridge → outro.

## v1.339.0 (2026-07-06)

- **`create_outro`** — Outro section generator. 5 types: fade (gradual thinning, velocity decreases), ritardando (slowing, durations increase, fermata), recap (return to opening, descending swell), pedal (V-I resolution, sustained tonic, octave finality), cadential (running notes to fermata chord, Beethoven close). 3 scales, 2-8 bars. Seeded PRNG. 35 unit tests. 512 MCP tools. Pairs with create_intro for full song framing.

## v1.338.0 (2026-07-06)

- **Render fix** — Root cause of render_full 600s timeout found and fixed. bridge.evaluate default timeout=30s killed renders at 30s, not 600s. Added timeout=1200000 (20 min) to all 6 render evaluate calls. Also removed project.copy() from 4 render functions — OfflineEngineRenderer.start() manages loopArea internally, worker gets snapshot via toArrayBuffer(). Deep copy of 364MB audio was #1 bottleneck. E2E confirmed: 6 stems × 272.8s rendered in 234s → 100MB WAV, has_audio=true.
- **`create_intro`** — Intro section generator. 5 types: ambient (sustained pad swell, root+fifth), drum (rhythmic build kick→snare→hats), melodic (emerging arpeggio I-vi-IV-V, sparse→dense), minimalist (Reich/Glass layered repetition), cinematic (drone+riser+impact, chromatic ascent). 3 scales, 2-8 bars. Seeded PRNG. 46 unit tests. 511 MCP tools.
- **`werkstatt_analog_delay.js`** — BBD bucket-brigade delay with clock aliasing. Analog warmth via sample-rate reduction, feedback saturation. 122 DSP scripts.
- **`werkstatt_distortion_pedal.js`** — DS-1/Rat style distortion with active tone stack. Character control (scoop vs hump). 123 DSP scripts.

## v1.337.0 (2026-07-06)

- **`werkstatt_cassette_sim.js`** — Cassette Tape Simulator. Full tape machine modeling: wow (0.5-2Hz slow speed variation) + flutter (13-33Hz fast flutter) via delay-line interpolation pitch modulation, asymmetric tape saturation (tanh soft clipping), 80Hz head bump resonance, high-frequency loss from tape head gap, pink tape hiss with age control, DC blocker. RC-20/SketchCassette aesthetic. 8 parameters. node --check ✅. **120 DSP scripts**.
- **CI sync** — 28 missing Werkstatt scripts added to CI validation list (73 → 101 scripts checked).
- **`create_cadence`** — Harmonic phrase conclusion generator. 5 types: authentic (V-I, strongest closure, leading tone resolves), plagal (IV-I, Amen cadence, warm soft closure), half (I-V, no closure, musical comma, expectation), deceptive (V-vi, surprise redirect, dramatic detour), phrygian (bII-i, Neapolitan resolution, dark exotic, minor key only). 3 scales. Chromatic pitch helper for non-diatonic chords. Seeded PRNG. 33 unit tests. 510 MCP tools. Bach to Miles Davis.
- **Skills sync** — composition-patterns SKILL.md decision tree updated with 7 new tools (riff, hook, lick, turnaround, solo, drum_solo, etude), description 178+ → 509 tools. dsp-script-authoring SKILL.md: 26 → 122 example scripts.
- **Example** — create_melodic_vocabulary.py: riff+hook+lick+turnaround+etude pipeline demo.

## v1.336.0 (2026-07-06)

- **`create_etude`** — Technical study piece generator. 5 types: scale (ascending/descending scalar runs, 16th notes, direction changes), arpeggio (broken chord patterns root-3rd-5th-7th, inversions, octave spanning, I-IV-V-I), interval (parallel thirds, two voices, eighth notes, direction shifts), rhythm (syncopation, tied notes, rests, 4 varied patterns cycling), chromatic (chromatic runs with direction changes, chromatic thirds). 5 scales including harmonic_minor. Seeded PRNG. 39 unit tests. 509 MCP tools. Czerny to Chopin.

## v1.335.0 (2026-07-06)

- **`create_hook`** — Melodic earworm phrase generator. 5 styles: pop (stepwise singable, I-V-vi-IV contour, repeated rhythmic motif, climax leap), rock (pentatonic with bluesy bends, power-note climaxes, root-fifth-root-octave motif), dance (rhythmic ostinato, syncopated off-beat stabs, octave jumps, 1-bar loop), rnb (melismatic neo-soul, chromatic turns, blue-note inflections b3/b7, syncopated 16ths), country (diatonic story-melody, 3rd/6th emphasis, pentatonic-adjacent, root resolution). 5 scales. Chromatic pitch helper. Seeded PRNG. 39 unit tests. 508 MCP tools.

## v1.334.0 (2026-07-06)

- **`create_lick`** — Short melodic vocabulary phrase generator. 5 styles: bebop (enclosures, chromatic passing, chord-tone targeting, 8th-note linear flow), blues (pentatonic + blue notes b3/b5/b7, bends, call-response micro-phrases), funk (staccato 16th syncopation, octave jumps, ghost notes, accent pattern), rock (pentatonic position, bending aesthetic, climax note), jazz_minor (diminished arpeggio + chromatic descent over minor ii-V-i, altered scale). 5 scales. Chromatic pitch helper. Seeded PRNG. 38 unit tests. 507 MCP tools.

## v1.333.0 (2026-07-06)

- **`create_turnaround`** — 2-bar resolution phrase generator. 5 styles: jazz (I-vi-ii-V with chromatic approach tones, guide tones, 7ths), blues (I-IV-IVdim-I walkup, shuffle feel, dominant 7ths, pentatonic), gospel (ii-V-I with chromatic approach, plagal Amen cadence, melisma), rock (bVII-IV-I mixolydian descent, power chords, octave accents, passing tones), pop (I-V-vi-IV axis progression, diatonic stepwise melody). 4 scales (major/minor/mixolydian/dorian). Chromatic pitch helper for non-diatonic chords. Seeded PRNG. 42 unit tests. 506 MCP tools.
- **O(n) base64 + redeclare fix** — User fixed `let binary` → `const binary = chunks.join("")` redeclaration causing JS SyntaxError in render. Combined with O(n) chunked encoding (32KB), large WAV render now works without crash. Render timeout raised to 600s.

## v1.332.0 (2026-07-06)

- **`create_riff`** — Genre-specific riff generator. 5 styles: rock (power chord roots+fifths, bluesy bends, syncopated rests, octave accents), funk (16th syncopation, ghost notes, staccato stabs, accent map), metal (galloping rhythm 16-16-8, palm-mute, tritone b5 intervals), blues (shuffle feel long-short 8ths, pentatonic bending, call-response), hip_hop (sparse loop aesthetic, melodic minor pentatonic, space between notes). 5 scales (minor_pentatonic/major_pentatonic/blues/minor/phrygian). Seeded PRNG. 25 unit tests. 505 MCP tools.

## v1.331.0 (2026-07-06)

- **`create_drum_solo`** — Genre-specific drum solo generator with rudimental vocabulary. 5 styles: rock (double kick 16ths, crash accents, tom descent fills, intensity build), jazz (swing ride pattern, comping, press rolls, hi-hat feathering), funk (ghost-note 16ths, hi-hat splashes, syncopated kick, pocket fills), latin (cascara, mambo bell, timbale fills, 2-3 clave), marching (paradiddles, flams, drags, open rolls, DCI vocabulary). Rudiment helpers: paradiddle (RLRR LRLL), flam (grace+main), drag (2 grace+main), open roll. Seeded PRNG. 29 unit tests. 504 MCP tools.

## v1.330.0 (2026-07-06)

- **`create_solo`** — Genre-specific melodic solo generator. 5 styles: bebop (chromatic approach tones, enclosures, bebop scale passing, chord-tone targeting on strong beats), blues (minor pentatonic + blue notes, 12-bar progression, riff repetition + variation), rock (pentatonic positions, repeated riffs, register climaxes), jazz_swing (swung 8ths 0.66/0.34, guide-tone lines, arpeggio patterns), fusion (wide intervals, chromatic passing, rhythmic displacement, modal). 6 scales (major/minor/dorian/mixolydian/blues/pentatonic_minor). Seeded mulberry32 PRNG for reproducibility. 27 unit tests. 503 MCP tools.

## v1.329.0 (2026-07-06)

- **2 new DSP scripts**: `werkstatt_plate_reverb.js` (EMT 140 / Valhalla Plate style algorithmic plate reverb: 4 allpass diffusers → FDN with damping lowpass + LFO shimmer, stereo cross-feed width, pre-delay, low-cut, diffusion control, 8 params), `werkstatt_ensemble.js` (Roland Juno-60 style ensemble chorus: 3 detuned delay lines at prime-ratio LFO rates 0.5/0.83/1.37Hz, L/C/R panning, depth/rate/voices/detune/width — the signature lush Juno chorus sound). 119 DSP scripts total.

## v1.328.0 (2026-07-06)

- **3 new DSP scripts**: `werkstatt_sidechain_comp.js` (sidechain compressor with pump effect, 8 params: threshold/ratio/attack/release/makeup/mix/srcSelect/listenDuck, envelope follower, gain smoothing, kick→bass ducking), `werkstatt_ott.js` (Xfer-style OTT multiband upward/downward compressor, 3-band LR crossover at 200/2000Hz, per-band upward+downward compression, depth/time/per-band+master gain, the signature EDM sound), `werkstatt_soft_clipper.js` (soft clipper with tanh+cubic curves, ceiling/drive/curve/mix/out, drum bus/mix bus/808 loudness). 117 DSP scripts total.

## v1.327.0 (2026-07-06)

- **`create_future_bass_arrangement`** — Future bass: 150 BPM melodic electronic. 4 tracks: punchy drums with pitching snare roll (ascending velocity crescendo), sub-bass following I-V-vi-IV chord roots, big supersaw chords (maj7/add9/min7 wide voicings, 2 bars per chord), vocal-chop style lead (major scale melodic fragments, starts bar 5). C major default. Flume, San Holo, Illenium, ODESZA. 22 unit tests. 502 MCP tools.

## v1.326.0 (2026-07-06)

- **`create_phonk_arrangement`** — Drift phonk: 130 BPM Memphis rap-inspired. 3 tracks: Memphis drums (punchy kick 1&3, clap 2&4, 16th hats with rolls), sliding 808 bass (chromatic slides, sustained resonance, octave drops), cowbell lead (minor pentatonic repetitive riff, 1-bar cycle, 3 octaves above bass). F minor default. Kordhell, MC Slvr, LXST CXNTURY. 23 unit tests. 501 MCP tools.

## v1.325.0 (2026-07-06) — 500 MILESTONE

- **`create_neurofunk_arrangement`** — Neurofunk DnB: 174 BPM dark technical DnB. 4 tracks: complex chopped breakbeat (extra kick placements, ghost note clusters/snare rolls at phrase ends), deep sustained sub-bass (syncopated gaps), Reese bass (detuned saw with chromatic slides and minor third jumps, rhythmic stabs), dark minor chord stabs (root+b3+tritone+b7). F minor default. Noisia, Spor, Phace. 22 unit tests. **500 MCP tools milestone.**

## v1.324.0 (2026-07-06)

- **`create_ambient_arrangement`** — Ambient: 70 BPM atmospheric soundscape. 4 tracks: sustained pad (open voicings: root/fifth/octave/third, 8 bars per chord), sparse drifting melody (2-4 bar notes, starts bar 9), subliminal drums (kick every 8 bars, shaker every 4), sub-bass drone (root only, 8 bars per note). I-vi-IV-V harmony. C major default. Brian Eno, Stars of the Lid, Aphex Twin SAW. 21 unit tests. 499 MCP tools.

## v1.323.0 (2026-07-06)

- **`create_downtempo_arrangement`** — Downtempo/trip-hop: 85 BPM Bristol sound. 5 tracks: boom-bap drums (heavy swing, ghost notes, vinyl aesthetic), deep sub-bass (sustained melodic, octave 1), minor 7th/9th chords (sparse every 2 bars, Rhodes-style), sparse melancholic melody (starts bar 5, wide intervals), sustained atmosphere pad (root+fifth, cinematic). D minor default. Massive Attack, Portishead, DJ Shadow. 24 unit tests. 498 MCP tools.

## v1.322.1 (2026-07-06)

- **3 new DSP scripts**: `werkstatt_cabinet_sim.js` (guitar cabinet speaker sim: 4x12/open-back/tweed, resonance, speaker rolloff, cone soft clip), `werkstatt_valve_preamp.js` (12AX7 triode preamp: asymmetric waveshaper, even-order harmonics, Miller capacitance, output transformer), `werkstatt_synthetic_ir_reverb.js` (synthetic IR reverb: algorithmic impulse response generation, exponential decay × filtered noise, early reflections, truncated convolution). 114 DSP scripts total.

## v1.322.0 (2026-07-06)

- **`create_psytrance_arrangement`** — Psytrance: 145 BPM hypnotic Goa/psychedelic. 4 tracks: 909 drums (kick 4-on-floor, snare 2&4, 16th hats, shaker, snare rolls at phrase ends), rolling 16th bassline (kick-aligned with offbeat gallop), hypnotic 16th lead motif (filter sweep velocity curve), sustained sci-fi atmosphere pad (minor 3rd + minor 7th). F minor default. Astrix, Vini Vici, Infected Mushroom. 23 unit tests. 497 MCP tools.

## v1.321.0 (2026-07-06)

- **`create_acid_arrangement`** — Acid house: 125 BPM TB-303 squelch bassline. 3 tracks: 909 drums (4-on-floor kick, clap 2&4, open hat offbeats, 16th closed hats, ride), TB-303 bass (16th note pattern with chromatic movement, accent pattern simulating filter sweeps, 2-bar cycle), sparse hypnotic lead stab every 4 bars. A minor default. Phuture, DJ Pierre, 808 State. 22 unit tests. 496 MCP tools.

## v1.320.0 (2026-07-06)

- **`create_garage_arrangement`** — UK garage: 130 BPM 2-step swing. 4 tracks: 2-step kick (alternating syncopated patterns), snare on 2&4, swung 16th hats (+0.08 swing), rim ghost notes, melodic bassline with octave jumps and syncopation, minor 7th chord stabs on offbeats, vocal-chop lead (short rhythmic phrases with gaps). G minor default. MJ Cole, Disclosure, Burial. 21 unit tests. 495 MCP tools.

## v1.319.0 (2026-07-06)

- **`create_hardstyle_arrangement`** — Hardstyle: 150 BPM Dutch festival hard dance. 4 tracks: hard kick on every beat + snare 2&4 + closed hats offbeat + open hat, reverse bass (offbeat boom-BM pattern), screechy sawtooth lead (wide intervals, octave jumps, high octave), stab chords on 1&3 (i-VI-III-VII). F minor default. Headhunterz, Brennan Heart, Wildstylez. 21 unit tests. 494 MCP tools.

## v1.318.0 (2026-07-06)

- **`create_ternary_form`** — Ternary form (ABA): outer A sections with contrasting B middle. 5 B-section contrast types: trio (subdominant, smoother rhythm, minuet & trio), dominant (V key, more active, Beethoven scherzo), relative (relative minor/major, Schubert impromptu), episode (same key, different material, Chopin nocturne), development (fragmentation of A material). Optional A' ornamentation with passing tones and trill-like neighbors. Da capo aria, minuet & trio, Chopin nocturnes, pop/jazz ABA. 33 unit tests. 493 MCP tools.

## v1.317.0 (2026-07-06)

- **`create_sonata_form`** — Sonata form: exposition (theme 1 in tonic + transition + theme 2 in dominant/relative), development (fragmentation, sequence, modulation through iii/vi/ii/IV, dominant pedal retransition), recapitulation (both themes in tonic). The structural foundation of classical symphonies, sonatas, quartets from Haydn through Mahler. Major key modulates to dominant, minor to relative major. Development features rising sequences and crescendo. 27 unit tests. 492 MCP tools.

## v1.316.0 (2026-07-06)

- **`create_binary_form`** — Binary form: two contrasting sections (A|B) with optional repeats (AABB). 5 modulation types: dominant (B in V), relative (B in relative minor/major), subdominant (B in IV), parallel (same key, different material), no_modulation. A section: stepwise melody around tonic, I-V-I bass. B section: wider intervals, modulated, returns to tonic. Baroque dance suites (Bach), folk tunes, early jazz. 22 unit tests. 491 MCP tools.

## v1.315.0 (2026-07-06)

- **`create_call_and_response`** — Two phrases in musical dialogue: leader (call) followed by response. 5 response types: echo (exact repeat), transpose (interval shift), variation (rhythmic variation), complementary (contrasting phrase using inversion-like degrees), fill (short approach+target). 14 scales. Adjustable gap, pairs, response_interval. Root of blues, gospel, African music, jazz, work songs, hip-hop. Call on track_index, response on track_index+1. 23 unit tests. 490 MCP tools.

## v1.314.0 (2026-07-06)

- **`create_comparsa`** — Cuban comparsa: carnival procession percussion. 7 instruments (conga low 54/high 63/open 64, claves 75, cowbell 56, maracas 70, guiro 73). 5 styles: habanera (classic 3-2 clave, cowbell 8ths), santiago (2-3 rumba-influenced, guiro scrapes), matanzas (rumba columbia, sparse, no claves, quinto improvisation), conga_line (marching, bass every beat), comparsa_moderna (16th maracas, salsa-influenced). Ancestor of salsa. 15th world rhythm tradition. Cuba. 25 unit tests. 489 MCP tools.

## v1.313.0 (2026-07-06)

- **`create_konokol`** — Indian Carnatic konokol (solkattu): vocal percussion as MIDI. 6 tala structures: adi_tala (8-beat cycle, most common), roopaka_tala (6-beat 3/4), khanda_chapu (5-beat asymmetric), mishra_chapu (7-beat lyrical), triputa_tala (7-beat variant), jhampa_tala (10-beat). Syllable-to-pitch mapping (ta/ka→hat 42, dhi/nam→snare 38, mi→tom 43, thom/ghu→bass 36, khatam→tom 45). Subdivision emphasis — first syllable of each group = full velocity, others 0.65×. 14th world rhythm tradition. India. 26 unit tests. 488 MCP tools.

## v1.312.0 (2026-07-06)

- **`create_edm_arrangement`** — Festival/mainstage EDM across 4 tracks: 4-on-the-floor kick + claps on 2+4 + 16th closed hats + open hats on offbeats, offbeat sub bass, supersaw chord stabs on beats 1+3, arpeggiated lead hook. Snare roll buildup crescendo at end of phrases. i-VI-III-VII progression (Fm-Db-Ab-Eb). F minor default (most common EDM key). 128 BPM. 23rd multi-track arrangement. 22 unit tests. 487 MCP tools.

## v1.311.0 (2026-07-06)

- **`create_gospel_arrangement`** — Gospel music across 4 tracks: gospel shuffle drums (kick on 1+3, snare on 2+4 with ghost notes, triplet shuffle hats), walking bass (root→3rd→5th→7th approach), Hammond B3 organ (chord stabs on 1+3, sustained on 2+4), SATB choir (sustained with dynamic swell). I-IV-V-I progression. Ab major default (flat keys traditional for gospel). 22nd multi-track arrangement. 25 unit tests. 486 MCP tools.

## v1.310.0 (2026-07-06)

- **`create_rondo`** — Rondo form: recurring theme (A) alternating with contrasting episodes (B, C). 5 form types: simple (ABA, 3 sections), classical (ABACA, 5 sections), seven_part (ABACABA, 7 sections), pop_rock (ABABCB — verse/chorus/bridge structure), jazz (ABAC — head/solo/head/contrast). Each section has distinct melodic pattern (A=tonic stepwise, B=dominant wider intervals, C=distant contrast) and bass pattern (I-V, V-I, IV-I). Adjustable bars_per_section. 14 scales. Mozart/Beethoven classical rondo, pop/rock song structure, jazz standard form. 32 unit tests. 485 MCP tools.

## v1.309.0 (2026-07-06)

- **`create_soli`** — Ensemble unison passage with octave doublings. All voices play the same melodic line in rhythmic unison at different octaves. 2-5 voices, adjustable octave spread (1-4). 14 scales (major through whole_tone). Scale degree input (0=root, 2=2nd, -1=7th below). Jazz big band soli (Basie/Ellington), orchestral tutti, rock/metal unison riffs. Outer voices full velocity, inner voices slightly reduced (0.85×). Unlike fugue (polyphonic imitation) or canon (delayed entry) — soli is simultaneous and homorhythmic. 32 unit tests. 484 MCP tools.

## v1.308.0 (2026-07-06)

- **`create_reggae_percussion`** — Jamaican reggae drum patterns across 6 styles: one_drop (roots reggae, kick+snare on beat 3 "the drop"), rockers (kick 1+3, snare 2+4), steppers (four-on-the-floor, dub/roots), ska (fast upbeat, Skatalites), rocksteady (laid-back, behind-beat hats), dancehall (syncopated, programmed). GM percussion pitches. Swing parameter for ska. 13th world rhythm tradition. 37 unit tests. 483 MCP tools.

## v1.307.0 (2026-07-06)

- **`create_chaconne`** — Chaconne: repeating bass + chord progression + developing variations. Unlike ground bass (bass only) or passacaglia (bass + melodic variations), chaconne repeats both bass AND chords as fixed harmonic framework, with variation melody on top. 5 variation styles: baroque (descending stepwise with grace notes accumulating), romantic (wide intervals, rubato-like timing), jazz (syncopated, chromatic passing tones, descending chromatic runs), minimalist (repeating cells with phase shift), contemporary (dissonant clusters, pointillistic). Bass on track_index, chords on track_index+1, variation on track_index+2. Chord parsing supports major/minor/dim/aug/maj7/m7/7/sus4/sus2/m7b5. 37 unit tests. 482 MCP tools.

## v1.306.0 (2026-07-06)

- **`create_ground_bass`** — Ground bass (basso ostinato): repeating bass pattern with developing melody above. 5 melody styles: baroque (descending stepwise, Purcell/Bach), modal (sparse sustained, Miles Davis), minimalist (phase-shifted cells, Reich/Glass), film_tension (dissonant crescendo), folk (pentatonic variation). Bass on track_index, melody on track_index+1. Fixed __init__.py exports for analysis functions. 23 unit tests. 481 MCP tools.

## v1.305.0 (2026-07-06)

- **`analyze_mix`** — Complete mix diagnosis in one call. Combines track (BPM/key/LUFS) + spectrum (7-band) + stereo (width/phase) + dynamics (crest/LRA/transients) into a single prioritized report. Mix suggestions sorted by severity (HIGH/MEDIUM/LOW/INFO). Master check with platform LUFS targets (Spotify -14, Apple -16, YouTube -14). One call replaces four — agent gets complete mix picture for EQ, compression, stereo, and mastering decisions.

## v1.304.0 (2026-07-06)

- **`analyze_dynamics`** — Dynamics analysis: crest factor (peak/RMS), loudness range (LRA 95-10 percentile), dynamic range, transient density (spikes/sec), 10-segment RMS contour, segment variation. Auto compression suggestions (heavily compressed, very dynamic, flat, percussive, smooth, level changes). Pure Python 300ms RMS windows. Completes the analysis trilogy: track + spectrum + stereo + dynamics.

## v1.303.0 (2026-07-06)

- **`analyze_stereo`** — Stereo field analysis: width (Side/Mid RMS ratio), L/R balance, phase correlation (-1 to +1), mono compatibility, phase issues %, per-region width (low/mid/high). Auto mix suggestions (narrow, wide, phase issues, L/R imbalance, wide bass). Pure Python one-pole filters for band splitting. Complements analyze_spectrum for complete mix diagnosis.

## v1.302.0 (2026-07-06)

- **`analyze_spectrum`** — Spectral analysis across 7 ISO frequency bands (sub_bass/bass/low_mids/mids/high_mids/presence/brilliance). Per band: RMS, peak dB, energy %. Global: spectral centroid (brightness), spectral spread (variance), spectral rolloff (95%), low/high ratio (tonal balance), spectral crest (tonal vs noisy). Auto mix suggestions (bass-heavy, dark, bright, muddy, harsh). Pure Python STFT, 8192-point Hann window.

## v1.301.0 (2026-07-06)

- **`create_second_line`** — New Orleans second line percussion: street parade groove, the root of funk/R&B. 5 instruments: bass drum (syncopated "street beat"), snare (backbeat + ghost notes), hi-hat (Charleston or 8ths), tom (fills), cymbal (phrase accents). 5 styles: traditional (parade, Charleston hi-hat), brass_band (modern, 8th-note hats + tom rolls), mardi_gras_indian (tribal, call-and-response tom/snare), jazz_funeral (dirge→celebration dynamic shift), bounce (NOLA hip-hop, double-time "Triggerman" bass + 16th hats). North American tradition.

## v1.300.0 (2026-07-06)

- **`create_korean_percussion`** — Korean traditional percussion: nongak (farmers' music) and samul nori. 5 instruments: janggu (hourglass drum with two heads: chwe/low + kyeong/high), buk (barrel drum), kkwaenggwari (small gong, lead), jing (large gong). 5 styles: nongak (rural), samul_nori (modern stage), binari (ritual/shaman), utdari_pungnyu (court), yeongnam_folk (Gyeongsang). Four instruments = weather elements (rain/clouds/thunder/wind). Korean tradition.

## v1.299.0 (2026-07-06)

- **`create_taiko_ensemble`** — Japanese taiko ensemble: kumi-daiko group drumming with dramatic dynamics. 4 instruments: odaiko (thunderous bass), chu-daiko (mid-range workhorse), shime-daiko (high timekeeper), atarigane (metal gong). 5 styles: miyake (steady + dramatic odaiko), yatai (festival, joyful), edo (march-like, sparse odaiko), hachijo (soloistic, long rolls, ma/silence), omega (modern Kodo-style, maximum density). Dynamic contrast from near silence to thunder. Japanese tradition.

## v1.298.0 (2026-07-06)

- **`create_irish_trad`** — Irish traditional music accompaniment: bodhrán + feet stomp for session tunes. 6 tune types: reel (4/4 straight 8ths), jig (6/8 triplet feel), hornpipe (4/4 swung/dotted), slip jig (9/8 ethereal), polka (2/4 fast), slide (12/8 Sliabh Luachra). Bodhrán on accented beats, brush hi-hat on every beat, feet stomp on every other bar. Hornpipe is the only swung type (swing=0.6). Ireland / Celtic tradition.

## v1.297.0 (2026-07-06)

- **`create_balkan_meter`** — Balkan additive meter: asymmetric time signatures (7/8, 9/8, 11/16, 13/8) with unequal beat groupings (2+2+3, 2+2+2+3, etc.). 6 meters: 7_8 (standard), 9_8 (horo), 11_16 (krivo), 13_8 (elenino), 7_8_sand (reversed 3+2+2), 9_8_ska (2+3+2+2). 3 variations: classic (tapan), modern (fusion, ghost snares), wedding (tapan rolls). Accents at group starts create the "limping" feel. Bulgarian, Macedonian, Greek, Serbian tradition.

## v1.296.0 (2026-07-06)

- **`create_flamenco_compas`** — Flamenco compás: the 12-beat cyclical rhythmic foundation of Flamenco. 6 palos: bulerias (fast festive, accents 12/3/6/8/10), solea (slow solemn, mother of Flamenco), alegrias (joyful from Cádiz), seguiriyas (tragic, asymmetric 3+2+3+2+2 grouping), tangos (simple 4/4), rumba (syncopated 4/4, Gypsy Kings). 4 instruments: palmas secas (sharp claps on accents), palmas sordas (muffled claps on non-accents), cajón (box drum on bass beats), golpe (table tap at cycle end). Andalusian / Spanish tradition.

## v1.295.0 (2026-07-06)

- **`create_arabic_percussion`** — Arabic/Middle Eastern percussion ensemble: darbuka (dum/tek/ka strokes), daf (frame drum), zills (finger cymbals). 6 rhythms: maqsum (the mother rhythm), baladi (urban Egyptian double-dum), saidi (Upper Egyptian), ayoub (Sufi trance 2/4), malfouf (fast running 2/4), chiftetelli (slow 8/4 belly dance). Dum = low center stroke, tek = high rim, ka = left-hand rim. Stroke-to-pitch offset: dum lowers, tek/ka raise pitch. Arabic, Turkish, Persian traditions.

## v1.294.0 (2026-07-06)

- **`create_djembe_ensemble`** — West African djembe/dunun ensemble: cyclical ostinato with call-and-response. 6 instruments: kenkeni (high dunun), sangban (mid dunun), dundunba (low dunun), bell (timeline), djembe2 (accompaniment), djembe1 (lead/improvisation). 4 traditional rhythms: danza (Malian welcoming), kuku (Guinean celebration), djole (Sierra Leonean), doundounba (dance of the strong men). Unlike samba (parade) or songo (drum kit), West African drumming is cyclical ostinato under improvised lead. Mali, Guinea, Senegal tradition.

## v1.293.0 (2026-07-06)

- **`create_samba_pattern`** — Brazilian samba percussion ensemble: multi-instrument layered groove with 5 independent drums (surdo, caixa, tamborim, chocalho, repique). Unlike songo (drum kit), samba is a bateria ensemble — each instrument has its own pattern, layered independently. 4 styles: batucada (carnival), samba_enredo (parade), pagode (backyard informal), samba_funk (fusion). Surdo = bass heartbeat, caixa = 16th snare glue, tamborim = syncopated conversation, chocalho = 16th shaker wash, repique = lead drum with calls/fills. Brazilian music tradition.

## v1.292.0 (2026-07-06)

- **`create_songo_pattern`** — Cuban songo drum-kit pattern: the fusion that revolutionized Latin music (Los Van Van, Changuito, 1970s). 4 variations: classic (original songo), modern (timba-era with ghost notes + tom fills), fusion (jazz-influenced ride pattern), songo_funk (funk-inflected backbeat). 4 drum-kit voices: kick (syncopated bombo), snare (rim + open + ghost), hi-hat (continuous 8ths with accents), tom (tonal fills). 2-bar cycle in 4/4. Unlike clave (timeline), tumbao (congas), or cascara (timbale shell), songo is a complete drum-kit groove. Afro-Cuban / Latin jazz.

## v1.291.0 (2026-07-06)

- **`create_tala`** — Indian classical tala: cyclic rhythmic structure with vibhag sections (unequal-length groupings), tali (clap) and khali (wave) markings, and theka (tabla bols sequence). 6 talas: teental (16), ektal (12), jhaptal (10), rupak (7), dadra (6), kehartwa (8). 3 laya tempos: vilambit, madhya, drut. Bol-to-pitch mapping: bayan strokes (Dha/Dhin) in lower register, dayan strokes (Ti/Na/Ta/Tin) in higher register. Velocity: tali beats emphasized, khali beats soft. Second non-European tradition after gamelan colotomic. Indian classical music.

## v1.290.0 (2026-07-06)

### Added
- `create_colotomic` — Gamelan colotomic structure: interlocking gong layers (gong ageng, kenong, kempul, kethuk) marking cyclic time. 4 structures: slendro (8-beat), pelog (16-beat), lancaran (doubled kethuk), ketawang (16-beat dense). 3 densities: sparse (gongs only), medium (+saron balungan), dense (+bonang elaboration). Hierarchical nested temporal grid. Unlike polyrhythm (conflicting meters), colotomic is hierarchical nesting. Indonesian gamelan, Javanese, Balinese.

## v1.289.0 (2026-07-06)

### Added
- `create_fugato` — Fugal passage with subject entries and imitation. Subject stated, answered at interval (real or tonal), optional countersubject (inverted contour), optional episode (sequenced material between entries). 2-4 voices. Custom or auto-generated subject. Voice 3 enters octave lower, voice 4 as answer. Unlike create_voice_exchange (transforms existing notes), generates entire fugal texture from scratch. Bach, Handel, Shostakovich fugato passages.

## v1.288.0 (2026-07-06)

### Added
- `create_cadenza` — Unmeasured virtuosic solo passage with rubato. Irregular rhythm, accelerando, fermatas, dramatic pauses. 6 segment types: flourish (rapid runs with accelerando), leap (wide jumps), trill (oscillation), fermata (held note + pause), cascade (descending arpeggio with diminuendo), climb (ascending with crescendo). 4 styles: classical, romantic, jazz, modern. Virtuosic mode. Breath marks. Seeded PRNG for reproducibility. Unlike all other tools (quantized grid), cadenzas use speech-like unmeasured rhythm.

## v1.287.0 (2026-07-06)

### Added
- `create_tuplet_group` — Irrational rhythm subdivision: N notes in a time span normally occupied by M notes. Triplets (3:2), quintuplets (5:4), septuplets (7:4), up to 16 notes. 5 pitch modes (scale_asc/desc, chord, repeated, alternating). Rest positions. Accent on first note. Repeats. Unlike polyrhythm (multiple voices), tuplets subdivide a single voice. Chopin, Ligeti, Ferneyhough.

## v1.286.0 (2026-07-06)

### Added
- `create_bariolage` — Baroque string crossing technique: rapid alternation between fixed pedal pitch and moving notes. 5 moving patterns (scale_asc, scale_desc, scale_wave, arpeggio, chromatic). 3 subdivisions (8th/16th/32nd). Creates two-voice illusion from single voice — pedal as drone anchor, moving notes as melodic interest. Bach, Vivaldi, Handel bariolage passages.

## v1.285.0 (2026-07-06)

### Added
- `create_voice_exchange` — Imitative counterpoint: pass motifs between voices with 6 transformation modes (imitation, inversion, retrograde, retrograde-inversion, augmentation, diminution). Optional swap mode for true voice crossing. Time offset for response entry. Foundation of fugue, canon, and Renaissance polyphony. Unlike clone_track (exact copy), transforms material as it passes between voices.

## v1.284.0 (2026-07-06)

### Added
- `create_montuno` — Latin/jazz piano montuno ostinato. 2-bar or 4-bar repeating figure with syncopated chord stabs and melodic passages. 4 patterns: 2-3 clave, 3-2 clave, guajira (dotted rhythm), charanga (flowing passages). 3 rhythms (8th/16th/quarter). Custom chord progression or auto I-vi-IV-V. Accent beats with velocity boost. Unlike arpeggiator (mechanical cycling), combines harmonic movement + syncopated rhythm + call-and-response phrasing.

## v1.283.0 (2026-07-06)

### Added
- `create_l_system_melody` — L-system (Lindenmayer system) melody generation. Deterministic rewriting system with recursive production rules. 5 presets: fibonacci (golden ratio self-similarity), cantor (Cantor set gaps), dragon (dragon curve), koch (Koch snowflake), sierpinski (Sierpinski triangle). Custom axiom/rules/symbol_map via JSON. Self-similar fractal melodic structure. Fully deterministic — same input always produces same melody. Completes stochastic trio (random walk + Markov + L-system).

## v1.282.0 (2026-07-06)

### Added
- `create_markov_melody` — Markov chain melody generation. Next interval depends on previous interval(s) via transition probability matrix. Order 1 or 2. Default matrix favors smooth motion with regression to mean (leaps followed by steps back). Custom weights as JSON. Unlike random_walk (zero-order), captures interval-to-interval tendencies — stylistic memory.

## v1.281.0 (2026-07-06)

### Added
- `create_random_walk_melody` — stochastic melody via random walk through a scale. Each note depends on the previous (stepwise motion). max_step (1-7), direction_bias (-1 to +1), boundary behavior (reflect/wrap/clamp), duration/velocity variation, rest probability, seeded PRNG (mulberry32). Brian Eno generative, Xenakis stochastic, ambient, IDM. Unlike generate_melody (contour-guided), produces melodic continuity through stepwise dependency.

## v1.280.0 (2026-07-06)

### Added
- `set_note_cents` — deterministic microtonal pitch control. Set specific cent offsets on targeted notes: all/pitch/beats/indices/alternating/gradient/scale_degree modes. Piano honky-tonk, quarter-tone, just intonation, Arabic maqam, synth drift, MIDI chorus. Unlike humanize_pitch (random), deterministic and pattern-based. -100 to +100 cents.

## v1.279.0 (2026-07-06)

### Added
- `shift_mode` — modal transformation: shift notes from one scale/mode to another, preserving tonic. Finds differing scale degrees and shifts only those notes. minor→dorian (+1 on degree 6), minor→phrygian (-1 on degree 2), major→mixolydian (-1 on degree 7). 14 scales. Unlike force_scale_notes (snaps nearest), preserves contour.

## v1.278.0 (2026-07-06)

### Added
- `create_additive_rhythm` — unequal groupings within a bar. Plus-separated group sizes ("3+2+2", "5+3") create irregular accent patterns. 4 note values, 5 pitch modes, group_start/group_end accents, velocity decay. Messiaen, Stravinsky, Bartók, math rock, prog metal.

## v1.277.0 (2026-07-06)

### Added
- `create_metric_modulation` — metric modulation with note-value equivalence. Tempo change preserving specific note duration: new_bpm = old_bpm × (new_note_value / old_note_value). 12 note values (whole through thirty_second), direct ratio mode "N:M", optional time signature change. Elliott Carter, Copland, Adams, Dream Theater, Tool. Unlike add_tempo_change (arbitrary BPM), preserves rhythmic continuity.

## v1.276.0 (2026-07-06)

### Added
- `create_phase_shift` — phase-shifted copy with gradual drift (Steve Reich phasing). Copies source phrase, each bar shifts by cumulative offset. forward/backward direction. shift_per_bar (1/32 to 1/2 note), 2-16 bars. Minimalism, techno loop phasing, ambient drift, IDM.

## v1.275.0 (2026-07-06)

### Added
- `create_melodic_polyrhythm` — melodic polyrhythm: N notes evenly spaced across M beats. 3:4=triplet, 5:4=quintuplet, 7:4=septuplet. Scale-based pitch generation (12 scales, up/down/alternate) or custom pitches. 4 velocity patterns (constant/accent/fade/wave). 1-8 bars. Jazz cross-rhythm, prog-rock, African cross-pulse, contemporary classical.

## v1.274.0 (2026-07-06)

### Added
- `clone_track` — full track duplication. Creates new track with all regions and notes copied. Optional transpose (-24..+24), velocity_scale (0.1-2.0), time_offset_beats (-16..+16), new_unit (separate AU). Complementary hue for visual distinction. Doubling, octave layering, parallel harmony, call-and-response, counterpoint layers.

## v1.273.0 (2026-07-06)

### Added
- `repeat_phrase` — repeat a melodic phrase N times with transposition. Copies all notes from source region, transposed by fixed interval (diatonic or chromatic). 5 velocity patterns (constant/crescendo/decrescendo/fade_out/build). Optional time_stretch per repetition. Optional cross_track. Bach fugues, jazz ii-V-I chains, pop chorus lifts, film score ostinato builds.

## v1.272.0 (2026-07-06)

### Added
- `add_anticipation` — anticipation notes before strong-beat notes. Creates forward rhythmic motion by arriving early on weak beat. 12 scales, 4 directions (auto/upper/lower/approach). anticipation_offset + anticipation_fraction control timing. Fourth and final non-chord tone technique (passing ✅, suspension ✅, neighbor ✅, anticipation ✅). Jazz syncopation, pop vocal anticipations, salsa montuno, funk guitar stabs.

## v1.271.0 (2026-07-06)

### Added
- `add_neighbor_tones` — upper/lower neighbor tone embellishment. Splits note into first_part → neighbor (scale step away) → return. 12 scales, 3 directions (upper/lower/alternating), neighbor_fraction + neighbor_offset control timing. Third of 4 non-chord tone techniques (passing ✅, suspension ✅, neighbor ✅).

## v1.270.0 (2026-07-06)

### Added
- `add_suspension` — Add suspension-resolutions to existing notes on strong beats. Creates preparation → suspension → resolution structure (classic 4-3, 9-8, 7-6 suspensions). 10 scales, 3 resolution modes (down/up/both). suspension_offset controls interval, preparation_beats controls prep duration. Optional cross_track. Bach chorales, jazz ballads, film scores.

## v1.269.0 (2026-07-06)

### Added
- `add_passing_tones` — Add diatonic passing tones between existing notes for smoother melodic lines. Only fills gaps where interval > 2 semitones and gap >= 1/8 note. 12 scales, 4 directions (auto/ascending/descending/nearest). velocity and duration_fraction control passing tone character. Optional cross_track preserves original melody. Fundamental counterpoint: Bach inventions, jazz walking lines, pop melismas.

## v1.268.0 (2026-07-06)

### Added
- `explode_chords` — Explode chords into separate voice tracks. Detects chord groups by position tolerance, assigns notes to voices by pitch. 3 directions: down (bass first), up (top first), outward (middle to outer). 4 velocity balance modes: natural, equal, top_heavy, fade. 2-8 voices. Target AU indices or source track. Fundamental orchestration: chord progression into individual instrumental parts.

## v1.267.0 (2026-07-06)

### Added
- `apply_contour` — Apply a melodic contour shape to existing notes. 6 contours: ascending, descending, arch, inverted_arch, wave, escalating. Redistributes pitches to follow the contour while keeping timing unchanged. range_semitones controls span (1-48), optional scale snapping (12 scales), preserve_first/last anchors. Complement to analyze_melody (which extracts contour). Melodic transformation, motivic reshaping.

## v1.266.0 (2026-07-06)

### Added
- `merge_note_tracks` — Merge notes from a source track into a destination track. 6 overlap resolution strategies: keep_higher_velocity, keep_lower_velocity, keep_source, keep_dest, keep_both, shorten_earlier. Optional transpose, delete_source flag. Consolidate doubled melodies, flatten multi-track MIDI, combine counterpoint into harmony track.

## v1.265.0 (2026-07-06)

### Added
- `shuffle_notes` — Random permutation of notes within a region. 4 modes: pitches (keep rhythm, shuffle melody), rhythm (keep pitches, shuffle timing), full (shuffle all attributes), within_groups (shuffle within beat groups). Seeded mulberry32 PRNG for reproducibility. shuffle_amount 0-1 controls fraction shuffled. preserve_first/last anchors. Generative melodic/rhythmic variation from existing note material.

## v1.264.0 (2026-07-06)

### Added
- `insert_rests` — Insert rests at specified beat positions. 3 modes: delete (remove notes at positions), truncate (cut overlapping notes at rest point), shorten (halve duration). Tolerance matching, shorten_neighbors for cleaner separation. Positional space creation, syncopation, breathing room in dense patterns.

## v1.263.0 (2026-07-06)

### Added
- `expand_intervals` — Expand or compress melodic intervals by a factor (0.25-4.0). 3 anchors: first (expand forward), last (expand backward), center (symmetric around mean). Optional scale snapping (9 scales: major, minor, dorian, phrygian, lydian, mixolydian, locrian, harmonic_minor, melodic_minor). factor=2 doubles intervals (seconds→thirds), factor=0.5 halves. Motivic development, melodic transformation.

## v1.262.0 (2026-07-06)

### Added
- `randomize_note_durations` — Randomize note durations with 5 distribution modes (uniform, increasing, decreasing, bimodal, jitter). Variation 0-1, min/max duration clamps, preserve_total scales to match original phrase length. Seeded PRNG for reproducibility. Generative duration variation, rhythmic humanization.

## v1.261.0 (2026-07-06)

### Added
- `rotate_notes` — Rotate notes cyclically (cyclic shift / permutation). 3 axes: position (reassign note order), pitch (shift pitches), both (true permutation). Rotation normalized modulo n. preserve_pitch_contour maintains original interval sequence. Serialism (Berg, Webern), jazz melodic rotation, pattern transformation.

## v1.260.0 (2026-07-06)

### Added
- `merge_consecutive_notes` — Merge consecutive notes of the same pitch into sustained notes. same_pitch_only mode, max_gap_beats threshold (0=touching only, 0.25=16th gap), 4 velocity modes (first/last/max/avg). Cleans up repeated hits, converts staccato to sustained, simplifies busy passages.

## v1.259.0 (2026-07-06)

### Added
- `subdivide_notes` — Subdivide each note into N smaller parts (2-16). Pitch patterns (same, scale_up/down, octave_up/down, chromatic_up/down) and velocity patterns (decrescendo, crescendo, accent_first/last, alternating). Diminution, rhythmic fragmentation, passagework creation. Same-track replaces originals; cross-track preserves source.

## v1.258.0 (2026-07-06)

### Added
- `repeat_notes` — Repeat existing notes in a region N times (1-16 cycles) with per-repeat transformations: cumulative pitch transpose (direction up/down), velocity decay multiplier, and time gap between cycles. Unlike create_midi_echo (feedback decay), this preserves note structure and applies uniform transform per cycle. Ideal for sequences, ostinato patterns, motivic development. Cross-track destination support.

## v1.257.0 (2026-07-06)

### Added
- `add_chord_tension` — Add jazz extension note to existing chord. 7 extensions: 9 (warmth), b9 (dark), #9 (Hendrix), 11 (suspended), #11 (Lydian), 13 (rich), b13 (dramatic). Calculates pitch from chord root. Triad → Cmaj9, G7 → G7b13. Complements invert_chord_notes and spread_voicing.

## v1.256.0 (2026-07-06)

### Added
- `randomize_note_chance` — Randomize note playback probability (chance 0-100%). 5 distribution modes: uniform (even random), decreasing (fade-out probability), increasing (emerge from silence), sparse (mostly min, some max), binary (coin flip). Seeded PRNG. Core generative MIDI tool — patterns that evolve per iteration.

## v1.255.0 (2026-07-06)

### Added
- `spread_voicing` — Chord voicing spread/compact. 4 modes: open (widen spacing, spread_octaves 1-3), close (collapse to one octave), drop2 (jazz piano comping — 2nd highest down octave), drop3 (wider jazz — 3rd highest down octave). Complements invert_chord_notes.

## v1.254.0 (2026-07-06)

### Added
- `reorder_sections` — Full song structure rearrangement. Takes JSON array of section boundaries in new order, rearranges note content back-to-back. Turn verse-chorus-verse into chorus-verse-verse. Complements swap_sections (two-section exchange).

## v1.253.0 (2026-07-06)

### Added
- `humanize_pitch` — Micro-detune (cents) intonation humanization. Adds per-note cent offsets to simulate natural pitch drift. cents_depth 0-50, bias -20 to +20, seeded PRNG. Complements humanize_notes (which handles velocity/timing/duration).

## v1.252.0 (2026-07-06)

### Added
- `invert_chord_notes` — Chord inversion at a specific beat position. 1st-6th inversion, direction up (bottom notes up octave) or down (drop voicing — top notes down). Returns original + new pitches, root name.

## v1.251.0 (2026-07-06)

### Added
- `swap_sections` — Swap two sections on the timeline — exchange positions. Song structure experimentation: chorus↔verse, bridge↔solo. Handles different-length sections, preserves content. Collect-delete-recreate pattern.

## v1.250.0 (2026-07-06)

### Added
- `create_ratchet` — Ratchet (accelerando repeat) — repeated notes with changing subdivision rate. 4 modes (accelerate/decelerate/constant/exponential), max 2-64 notes/beat, velocity_decay, pitch_drift. Bach cadences, electronic build-ups, drum fills.

## v1.249.0 (2026-07-06)

### Added
- `apply_velocity_lfo` — Periodic velocity modulation (velocity LFO). 5 waveforms (sine/triangle/saw/square/random), rate (cycles per beat), depth, phase, center velocity. Creates pumping, breathing, wave-like dynamics synced to beat positions.

## v1.248.0 (2026-07-06)

### Added
- `move_notes` — Move notes from source region to another track (copy + delete source). Transpose, time_offset, velocity_scale, delete_source flag. Cross-AU support.

## v1.247.0 (2026-07-06)

### Added
- `quantize_velocities` — Snap note velocities to discrete stepped levels (MPC 16-level mode, uniform velocity, stepped dynamics). 2-128 levels, 4 modes (snap/floor/ceil/round_random), min/max velocity range, level distribution histogram.

## v1.246.0 (2026-07-06)

### Added
- `create_midi_echo` — Create MIDI echo — repeat notes with decaying velocity and optional pitch shift. 4 feedback modes: linear (geometric decay 0.6^r), exponential (faster decay 0.6^(r²)), constant (same velocity, stutter feel), reverse (decreasing velocity). pitch_shift per repeat creates cascading octave echoes. dest_track for separate echo track. 1-8 repeats, configurable delay. Use for guitar delay throws, synth echo fills, creative repetitions.

## v1.245.0 (2026-07-06)

### Added
- `balance_track_velocities` — Balance velocities across multiple tracks simultaneously. 5 presets: mix_balanced (equal 0.75), drums_forward (drums 0.95/bass 0.80/harmony 0.65/lead 0.70), vocal_forward (lead 0.95/pads 0.60), pads_quiet (pads 0.50/lead 0.85), bass_heavy (bass 0.95). Custom mode with comma-separated target velocities. Preserves relative dynamics within each track via multiply scaling. Returns per-track stats before/after.

## v1.244.0 (2026-07-06)

### Added
- `map_velocity_by_pitch` — Map velocity based on pitch position. 4 modes: higher_quieter (high notes softer, natural for piano/orchestra/drums), lower_quieter (highs cut through, lead synths), bell_curve (loudest in middle register, vocal range), inverse_bell (experimental). Intensity 0-1 controls strength. pitch_ref sets neutral pitch (default C4=60). Returns per-octave velocity stats before/after. Use for naturalising flat MIDI velocities.

## v1.243.0 (2026-07-06)

### Added
- `analyze_harmonic_rhythm` — Analyse how fast chords change and where. Identifies chords from MIDI notes (same logic as identify_chords), computes chord timeline (position + duration per chord), harmonic rhythm rate (fast <2 beats / medium 2-4 / slow >4), chords per bar, stable sections (4+ bars same chord), active sections (sub-beat changes), modulation detection (6+ distinct roots). Complements identify_chords by focusing on temporal pattern of harmony.

## v1.242.0 (2026-07-06)

### Added
- `detect_scale_from_notes` — Detect musical scale/key from MIDI notes in a region. 15 scales tested via Pearson correlation against pitch class histogram (180 root×scale combinations). Returns best match + 5 alternatives + confidence rating + chromatic coverage. Works on MIDI directly (no audio file needed), unlike detect_key which analyses WAV. Use before force_scale_notes, diatonic_transpose, generate_melody.

## v1.241.0 (2026-07-06)

### Added
- `apply_rhythm_pattern` — Apply rhythmic pattern to notes (inverse of extract_rhythm). Rhythm string or onset grid input, pattern cycling, round-robin note assignment, 4 velocity modes (preserve/accent/flat/pattern), 3 duration modes (preserve/staccato/legato). Closes rhythm analysis→modification loop.
- Fixed `extract_rhythm` grid resolution bug — grid_map values were inverted (16th gave quarter-note resolution instead of 16th). Now correctly maps 16th=240 ticks, 8th=480, 32nd=120, quarter=960.

## v1.240.0 (2026-07-06)

### Added
- `extract_rhythm` — Rhythmic pattern extraction from notes. Returns onset grid (binary array), rhythm string (x=onset, .=rest), syncopation score (0-1, based on weak beat hits), swing factor (odd-position ratio), inter-onset intervals (IOI mean/min/max), density (onsets/total positions), strong/weak beat hit counts. 4 grid resolutions: 16th, 8th, 32nd, quarter. 13 unit tests including onset grid, syncopation, swing, IOI stats. Updated composition-patterns skill with all 7 new tools (accent_beats, filter_notes, split_note_region, merge_note_regions, note_stats, analyze_melody, extract_rhythm). **415 MCP tools**, 3050 unit tests

## v1.239.0 (2026-07-06)

### Added
- `analyze_melody` — Full melodic contour analysis. Returns contour profile (up/down/static per interval), interval histogram (sorted by size), step vs leap ratio (≤2 semitone = step), direction change count, climax (highest pitch + position 0-1 on timeline), nadir (lowest), contour shape classification (ascending/descending/arch/v_shape/wave/static), phrase grouping by rests (gaps > 1 beat), melodic range (semitones), average interval size. 15 unit tests including interval calc, step/leap, direction changes, climax position, contour shapes, phrase grouping. **414 MCP tools**, 3037 unit tests

## v1.238.0 (2026-07-06)

### Added
- `accent_beats` — Beat-aware velocity accents by position. 6 patterns: 4/4 (downbeat strong), backbeat (beats 2+4 strong), 3/4 waltz, 6/8 compound, off_beat (syncopated, reggae skank), four_on_floor (every beat strong). Interpolates velocity for notes between beats (16th notes blend toward weak). Unlike apply_velocity_pattern (cycles by note index), this uses absolute beat position to determine accent level. strong/medium/weak velocity levels configurable. 14 unit tests including pattern weights, beat index calc, interpolation, clamping, region offset independence. **413 MCP tools**, 3022 unit tests

## v1.237.0 (2026-07-06)

### Added
- `note_stats` — Comprehensive note statistics for a region. Returns: note count, pitch range (min/max/span + note names), velocity statistics (min/max/mean/median/std — std=0 detects robotic uniform velocity), duration statistics (min/max/mean in beats), density (notes per beat), pitch class histogram (12 pitch classes with counts), top 5 most common pitches (with names), time span (first note to last note end). 13 unit tests including velocity std, median (even/odd), density, pitch class histogram, pitch name conversion. **412 MCP tools**, 3008 unit tests

## v1.236.0 (2026-07-06)

### Added
- `filter_notes` — Multi-criteria note filtering with actions. Filters by pitch range (min/max MIDI), velocity range (0-1), time range (beats). -1 = wildcard. Three actions: list (read-only, returns matching notes), delete (remove matching), keep (remove non-matching, inverse filter). AND logic on all criteria. Use cases: cleanup sub-bass rumble, isolate melody register, remove ghost notes, trim to time window. 13 unit tests including combined filters, wildcard semantics, delete/keep logic, absolute beat calculation. **411 MCP tools**, 2995 unit tests

## v1.235.0 (2026-07-06)

### Added
- `merge_note_regions` — Merge two note regions into one. Copies all notes from region B into A's collection, adjusting positions to absolute timeline (absPos = posB + notePos, relPos = absPos - posA). Region A duration extends to cover both regions. Region B deleted. Works with adjacent, gapped, overlapping, and out-of-order regions. 13 unit tests including position recalculation, duration extension (adjacent/gap/overlap), round-trip split+merge, note property preservation. **410 MCP tools**, 2982 unit tests

## v1.234.0 (2026-07-06)

### Added
- `split_note_region` — Split a note region into two at a beat position. Creates a new NoteRegionBox starting at split_beat with all notes at/after that position (positions recalculated relative to new region start). Original region duration trimmed to split point. Notes straddling the split (starting before, extending past) stay in original — matches DAW behaviour. Validates split point is within region range. 13 unit tests including note categorization, relative position recalculation, bar boundary splitting. **409 MCP tools**, 2969 unit tests

## v1.233.0 (2026-07-06)

### Added
- `double_melody` — Parallel interval doubling. Creates a copy of every note shifted by a named musical interval (octave, double_octave, fifth, fourth, third, sixth, unison). Diatonic mode shifts by scale steps — produces correct major/minor third quality depending on scale degree (C→E = major third, D→F = minor third in C major). Same-region mode (dest_track_index=-1) thickens in place; cross-track mode creates a separate layer. velocity_scale (0.8 = classic quieter double), time_offset for delayed doubling. Fills the gap between copy_notes_to_track (chromatic only) and create_harmony_line (diatonic only). 13 unit tests including diatonic quality verification. **408 MCP tools**, 2956 unit tests

## v1.232.0 (2026-07-05)

### Added
- `generate_melody` — Generative melody from scale + contour. Creates melodic lines from scratch — no chord progression needed. 6 contour shapes (ascending, descending, arch, v_shape, wave, random) control melodic direction. 5 rhythm patterns (quarter, eighth, syncopated, mixed, sparse). Weighted random pitch selection guided by contour target height. Rest probability for spacing. 2-octave scale range centered on octave. Reports pitch_range, notes_created. Seed from root+scale+contour+rhythm+bars for reproducibility. 13 unit tests including contour math verification. **407 MCP tools**, 2943 unit tests

## v1.231.0 (2026-07-05)

### Added
- `set_articulation` — Articulation control: legato, staccato, or tenuto. Legato extends each note to the next (minus micro_gap PPQN for separation). Staccato shortens to staccato_ratio of available time (0.5=half, 0.25=very short, 0.75=portato). Tenuto holds full available duration with no gap. Groups notes by position (chords treated as units). Last note keeps original duration. 13 unit tests. **406 MCP tools**, 2930 unit tests

## v1.230.0 (2026-07-05)

### Added
- `constrain_note_range` — Pitch range limiting: clamp or octave-wrap out-of-range notes. "clamp" hard-limits to [min_pitch, max_pitch]. "octave_wrap" shifts by ±12 semitones until in range, preserving pitch class — use for instrument range constraints (guitar E2-E6, violin G3-A7, vocal soprano C4-A5, etc.). Falls back to clamp when range < 12 semitones. Reports notes_adjusted, clamped, wrapped per track. 13 unit tests including pitch class preservation verification. **405 MCP tools**, 2917 unit tests

## v1.229.0 (2026-07-05)

### Added
- `strum_notes` — Guitar-style strumming: converts simultaneous chord notes into time-offset strums. Groups notes by position (tolerance 10 PPQN), sorts by pitch, offsets each by speed × index. 3 directions: down (low→high, default), up (high→low), random (Fisher-Yates shuffle, banjo/ukulele feel). Speed: 0.03125 (1/32, fast shred) to 0.5 (1/2, harp-like). jitter for humanization (±% of speed per string). Reports chord_groups found, notes_strummed per track. 13 unit tests. **404 MCP tools**, 2904 unit tests

## v1.228.0 (2026-07-05)

### Added
- `thin_notes` — Note density reduction: selectively removes notes to clean up cluttered MIDI. 3 strategies: "interval" (keep every Nth note sorted by position, 2=halve, 3=third), "velocity_threshold" (remove notes below velocity threshold — ghost note cleanup after AI transcription), "random" (probabilistic removal for organic variation). preserve_strong_beats option keeps notes on beat 1 and 3 regardless of strategy. Reports original_count, removed, remaining per track. 13 unit tests. **403 MCP tools**, 2891 unit tests

## v1.227.0 (2026-07-05)

### Added
- `displace_rhythm` — Rhythmic displacement: shift all notes by a fixed offset in beats. Two modes: "shift" (add offset, negative=pushed/early, positive=laid-back/late, clamps to 0, auto-extends region) and "circular" (rotate pattern within region bounds, wraps around — creates new patterns from same material). Default offset 0.0625 (1/16 note). Range -4.0 to 4.0 beats. Offset=0 returns no-op. Converts to PPQN internally. Reports per-track notes_modified, offset, mode. 13 unit tests. **402 MCP tools**, 2878 unit tests

## v1.226.0 (2026-07-05)

### Added
- `reharmonize_progression` — Chord substitution / reharmonization. 5 techniques: tritone_sub (G7→Db7, shared guide tones), secondary_dominant (insert V7 of target chord), diatonic_sub (I→vi submediant, shared tones), modal_interchange (borrow from parallel key, F→Fm), passing_dim (diminished passing chord for chromatic bass). Intensity control (light/medium/heavy). target_chord for selective substitution. Returns reharmonized progression string + per-chord mapping with explanations. Same input format as create_chord_pads/modulate_progression. 13 unit tests including music theory verification (tritone guide tones, secondary dominant resolution, modal interchange common tones, passing dim interval requirement, diatonic sub shared tones). **401 MCP tools**, 2865 unit tests

## v1.225.0 (2026-07-05)

### Added
- `create_voice_led_progression` — Chord pads with smooth voice leading. Unlike `create_chord_pads` (root position → large jumps between chords), this re-voices each chord so individual voices move minimally. Algorithm: first chord = root position centered on octave; each subsequent chord: generate all octave-shifted inversions within ±voice_range, pick the voicing with minimal total semitone movement from previous chord. Common tones stay stationary (distance 0 = optimal). Reports per-chord movement, total movement, and average. Same hyphen-separated chord format as create_chord_pads. voice_range constrains voice spread (default 12 = ±1 octave). 13 unit tests including algorithm verification (minimal movement, common tones, range constraints). **400 MCP tools**, 2852 unit tests

## v1.224.0 (2026-07-05)

### Added
- `create_harmony_line` — Diatonic harmony line from existing melody. Reads notes from a source melody, shifts each by N scale steps to create parallel harmony. 5 intervals: third (+2 steps, most common — Lennon-McCartney/Everly Brothers), sixth (+5, jazzier/airy), fifth (+4, power/organum), fourth (+3, suspended/modal), octave (+7, doubling). Direction above/below. Diatonic — harmony notes guaranteed in key. Auto-creates target track/region. Notes not in scale snap to nearest scale note before shifting. velocity_scale for harmony loudness (default 0.8). 12 unit tests. **399 MCP tools**, 2839 unit tests

## v1.223.0 (2026-07-05)

### Added
- `create_metal_arrangement` — Twenty-first multi-track arrangement. Heavy metal — riff-based, not chord-progression-based. Double kick drums (16th kick notes, snare 2+4, crash on bar starts, ride on off-beats), root-following bass (8th notes following riff roots), rhythm guitar (power chords [root+fifth] + palm-muted chugging on low E pedal tone, phrygian dominant scale for exotic metal sound), shred lead (minor pentatonic ascending runs, natural minor descending runs, long sustained bends, phrygian dominant licks). 4-bar riff pattern: pedal chugging + power chord stabs. E root (lowest guitar string), 160 BPM (thrash metal). Distortion effect in genre_mix. Velocity 0.85 (louder than other genres). Registered in all 4 genre registries + genre_mix (distortion + aggressive comp) + genre_humanization (timing 0.02, velocity 0.04 — tightest of all genres). 12 unit tests. **398 MCP tools**, 2827 unit tests, **21 multi-track arrangements**

## v1.222.0 (2026-07-05)

### Added
- `create_country_arrangement` — Twentieth multi-track arrangement. Classic country/Americana across 4 tracks: straight 8th backbeat drums (kick 1+3, snare 2+4, steady 8th hats — straight, not shuffled like blues), root-five bass (root on beat 1, fifth on beat 3 — the classic country pattern), boom-chick guitar (alternating bass note + chord strum on beats 1-2 and 3-4 — Carter Family/Johnny Cash pattern), major pentatonic fiddle lead (root/2/3/5/6 with blue notes b3/b7, sustained notes + scale runs + turnaround licks). 8-bar form: I-I-IV-I-V-I-IV-I. 120 BPM default (country two-step), G root. Triads, not 7ths — country harmony is cleaner than blues. Registered in all 4 genre registries + genre_mix recipe + genre_humanization (timing 0.06, velocity 0.10, swing 0.0). 12 unit tests. **397 MCP tools**, 2815 unit tests, **20 multi-track arrangements**

## v1.221.0 (2026-07-05)

### Added
- `create_motif_variations` — Classical motif transformation from existing MIDI material. Extracts a motif (by start_note index + note_count) from a source region and creates a variation in a target region. 6 classical variation techniques: sequence (repeat shifted by N semitones, 3 repetitions), inversion (mirror intervals around first note), retrograde (play backwards), augmentation (stretch durations ×N), diminution (compress durations ×N), fragmentation (first N notes repeated 4×). Closes the analysis→creation loop: extract_motifs finds patterns, this tool develops them. Auto-creates target track/region if not specified. Uses NoteEventBox.create. 12 unit tests. **396 MCP tools**, 2803 unit tests

## v1.220.0 (2026-07-05)

### Added
- `classify_drum_pattern` — Rhythmic pattern classification from MIDI drum notes. Uses GM drum map (36=kick, 38=snare, 42=closed hat, 46=open hat, 50/47/45=toms, 49=crash, 51=ride). Analyzes per-bar: kick/snare positions, syncopation ratio, triplet feel, hat density, fast hats (32nd), velocity stats. Classifies into 8 patterns: four-on-the-floor (house/techno), boom-bap (hip-hop), trap (fast hats), breakbeat (jungle/DnB), shuffle (blues/jazz), half-time (R&B/ballads), amen (DnB classic), march (military). Confidence scoring, sorted matches, unknown fallback. Fills the rhythmic-analysis gap. 12 unit tests. **395 MCP tools**, 2791 unit tests

## v1.219.0 (2026-07-05)

### Added
- `analyze_song_structure` — Structural analysis of MIDI content. Scans all note tracks bar-by-bar, computes per-bar features (note density, pitch range, average velocity, active track count, energy = density × velocity). Groups consecutive bars with similar density into segments, classifies each as intro/verse/chorus/bridge/outro/breakdown based on position and energy patterns. Highest-energy segment is labeled as chorus. Returns form string (e.g. "intro → verse → chorus → verse → chorus → outro"). Fills the structural-analysis gap — the agent can now understand song form, not just create it. 12 unit tests. **394 MCP tools**, 2779 unit tests

## v1.218.0 (2026-07-05)

### Added
- `extract_motifs` — Melodic motif extraction from MIDI regions. Identifies repeating melodic phrases (3-8 notes) by their interval contour — the pattern of pitch changes between consecutive notes. Same motif transposed to a different key still matches. Contour classification (ascending/descending/arch/V-shape/wave/static/mixed), rhythm pattern matching, significance scoring (repetitions × note_count), deduplication to avoid reporting sub-motifs of larger patterns. Returns occurrences with start positions and pitches. Fills the melodic-analysis gap — identify_chords does harmonic analysis, extract_motifs does melodic analysis. 12 unit tests. **393 MCP tools**, 2767 unit tests

## v1.217.0 (2026-07-05)

### Added
- `create_blues_arrangement` — Nineteenth multi-track arrangement. Classic 12-bar blues across 4 tracks: shuffle drums (kick 1+3, snare 2+4, triplet hi-hats), walking bass (quarter notes, root→fifth→octave→chromatic approach), dominant 7th chord stabs (I7/IV7/V7 — no triads in blues), blues scale lead (root/b3/4/b5/5/b7 with blue notes and turnarounds). 12-bar form: I-I-I-I-IV-IV-I-I-V-IV-I-V. 120 BPM default (Chicago blues), A root. Registered in all 4 genre registries (pipeline, variation, song, render) + genre_mix recipe + genre_humanization (timing 0.12, velocity 0.15, swing 0.58). 12 unit tests. **392 MCP tools**, 2755 unit tests, **19 multi-track arrangements**

## v1.216.0 (2026-07-05)

### Added
- `werkstatt_maximizer.js` — Loudness maximizer with lookahead limiting, ISP (inter-sample peak) detection, TPDF dithering via LFSR, stereo link, and dry/wet mix. Ceiling (-6 to 0 dB), release (5-500ms), lookahead (0-1ms), dither amount, stereo link. 6 params. Complements the existing limiter — maximizer is louder-than-limiter with transparent sound for mastering. **111 DSP scripts** (92 Werkstatt + 9 Apparat + 10 Spielwerk)

## v1.215.0 (2026-07-05)

### Added
- `diatonic_transpose_notes` — Scale-step transpose (diatonic) instead of semitone transpose (chromatic). Moves notes up/down by N steps within the specified scale — C major C→D = +1 step (2 semitones), E→F = +1 step (1 semitone). 13 scales. Skips out-of-scale notes. Octave wrapping. For creating variations that stay in key, sequences, modal interchange, walking bass from scale degrees, counterpoint. 10 unit tests. **391 MCP tools**, 2743 unit tests

## v1.214.0 (2026-07-05)

### Added
- `identify_chords` — Harmonic analysis from existing MIDI notes. Reads notes from a region, groups by temporal overlap (group_tolerance beats), and matches pitch-class sets against 10 chord types (maj/min/dom7/maj7/min7/sus2/sus4/add9/dim/aug). Returns chord name, root, type, time position, alternate names, and note names. Subset matching for chords with extra notes (extensions). Useful for: understanding imported MIDI, analyzing AI-generated progressions, reverse-engineering harmony, verifying generated chords. 9 unit tests. **390 MCP tools**, 2733 unit tests

## v1.213.0 (2026-07-05)

### Added
- `force_scale_notes` — Harmonic snap: force all notes into a specific scale. Finds out-of-scale notes and moves them to nearest in-scale pitch. 13 scales (major/minor/dorian/phrygian/lydian/mixolydian/aeolian/locrian/pentatonic_major/pentatonic_minor/blues/harmonic_minor/melodic_minor). direction: nearest/up/down. preserve_octave: stay in octave (±1-2 semitones) or allow octave jumps. Harmonic equivalent of quantize_notes — snap pitch to scale instead of timing to grid. Useful after audio-to-MIDI transcription, random generation, or importing MIDI from unknown sources. 10 unit tests. **389 MCP tools**, 2724 unit tests

## v1.212.0 (2026-07-05)

### Added
- `time_warp_notes` — Half-time / double-time / custom time stretch for MIDI. Warps note positions AND durations by a factor (0.5 = half-time, 2.0 = double-time) without changing BPM. Unlike scale_durations (only duration), this moves notes in time — a 1-bar pattern becomes 2 bars at half-time. origin: "start" (region start anchor) or "zero" (absolute). Range 0.1-8.0. 9 unit tests. **388 MCP tools**, 2714 unit tests

## v1.211.0 (2026-07-05)

### Added
- `groove_transfer` — Groove feel transfer between regions. Extracts groove template (per-grid-slot timing offsets + velocity ratios) from a source region's notes, then applies to destination region(s). Groove cycles every groove_length beats (4=1 bar of 4/4, 3=waltz, 2=half-bar). timing_strength and velocity_strength (0-1) control how much of the source feel to apply. 16th or 8th grid. This is NOT copying notes — it transfers the *feel*, so a 1-bar drum groove can be applied to a 4-bar programmed pattern. 9 unit tests. **387 MCP tools**, 2705 unit tests

## v1.210.0 (2026-07-05)

### Added
- `scale_durations` — MIDI note duration scaling tool. 5 modes: multiply (scale all durations by factor), add (offset durations), set (uniform duration), quantize (snap to 16th/8th/quarter/half grid), legato (extend each note to just before next note with configurable gap). Returns original + new duration min/max/avg. Clamp via min_duration/max_duration. Companion to scale_velocity — same concept for note lengths. 9 unit tests. **386 MCP tools**, 2696 unit tests

## v1.209.0 (2026-07-05)

### Added
- `copy_notes_to_track` — Copy notes from one track/region to another track. MIDI layering and doubling tool. Optional transpose (semitones), time_offset (beats), velocity_scale for the copied notes. Cross-AU support via dest_unit_index. Use cases: layer drums (copy to second track with different instrument), create harmony (copy melody +12 octave), echo/call-and-response (copy with time_offset), doubles (copy with slight transpose for thickening). Creates notes via NoteEventBox.create in destination region. 9 unit tests. **385 MCP tools**, 2687 unit tests

## v1.208.0 (2026-07-05)

### Added
- `scale_velocity` — MIDI dynamics scaling tool. 5 modes: multiply (scale all velocities by factor), add (offset all velocities), set (uniform velocity), normalize (scale to target max velocity), compress (reduce dynamic range around 0.5 midpoint). Returns original + new velocity min/max/avg stats. Clamp range via min_velocity/max_velocity params. Unlike create_crescendo (gradient), this uniformly scales existing velocities — like gain for MIDI dynamics. 9 unit tests. **384 MCP tools**, 2678 unit tests

## v1.207.0 (2026-07-05)

### Added
- `create_rnb_arrangement` — 18th multi-track genre arrangement. Contemporary R&B (The Weeknd / Frank Ocean / SZA): half-time drums with triplet hi-hat rolls (trap influence), deep sub bass (long sustained root), dark extended chord voicings (min9/maj7/min7 on i-VI-III-VII minor-key progression), vocal-style lead with pentatonic minor + blue notes (b5), wide interval leaps, melismatic fills. 68 BPM, C minor default, 4 tracks. Integrated into all genre registries: create_full_genre_pipeline, create_arrangement_variation, create_song_with_variations, apply_genre_mix (comp+EQ+reverb+delay+sidechain recipe), apply_genre_humanization (timing 0.08, bias 0.02). Also added lofi + soul to all registries where missing. 15 unit tests. **383 MCP tools**, 2669 unit tests

## v1.206.0 (2026-07-05)

### Added
- `transcribe_audio` — composite audio transcription tool. Runs transcribe_drums + transcribe_melody on the same WAV in one call, placing drum notes (kick=36/snare=38/hat=42) on drum_track and pitched melody notes on melody_track. Auto-detects BPM. Completes audio-to-MIDI family: transcribe_drums (216), transcribe_melody (217), transcribe_audio (219 — this). Suno pipeline: download_audio → transcribe_audio → full MIDI on 2 tracks → remix. 6 unit tests. **382 MCP tools**, 2654 unit tests

## v1.205.0 (2026-07-05)

### Added
- `werkstatt_formant_shifter.js` DSP script — LPC-based formant shifter. Shifts vocal formant frequencies independently of pitch using Levinson-Durbin recursion → reflection coefficients → lattice filter structure. Creates gender/age/size morphing effects (big head, small head, chipmunk, deep voice) while preserving original pitch. 7 params: shift (0.5-2.0 ratio), formants (3-8 LPC stages), pitch_tracking, brightness, width, mix, output. Coefficient smoothing prevents clicks. 11 unit tests. **110 DSP scripts** (91 Werkstatt + 9 Apparat + 10 Spielwerk), 2648 unit tests

## v1.204.0 (2026-07-05)

### Added
- `transcribe_melody` — **new capability**, audio-to-MIDI monophonic melody transcription. Converts monophonic instrument recordings (bass, vocal, lead synth, horn) into MIDI notes via autocorrelation pitch detection. Frame-by-frame autocorrelation → fundamental frequency → MIDI pitch (with cents deviation via parabolic interpolation). Groups consecutive similar-pitch frames into sustained notes. Velocity from frame energy. Auto-detects BPM. Together with transcribe_drums (cycle 216), completes audio-to-MIDI pipeline: download_audio → transcribe_drums + transcribe_melody → full MIDI reconstruction. 12 unit tests (sine detection, pitch accuracy 440Hz→69, two notes, velocity range, MIDI range, beat conversion, cents, clarity, tool delegation, auto-BPM). **381 MCP tools**, 2637 unit tests

## v1.203.0 (2026-07-05)

### Added
- `transcribe_drums` — **new capability**, audio-to-MIDI drum transcription. Converts WAV drum recordings into MIDI notes using band-split onset detection (kick <250Hz, snare 250-2500Hz, hat >2500Hz). One-pole IIR filters for band splitting, energy envelope per band, onset detection via local average threshold, velocity from amplitude, beat conversion from BPM. Auto-detects BPM if not provided. Pipeline: download_audio → transcribe_drums → edit/quantize in DAW. 11 unit tests (kick/snare/hat detection, beat conversion, velocity range, MIDI pitches, band counts, auto-BPM). **380 MCP tools**, 2625 unit tests

## v1.202.0 (2026-07-05)

### Added
- `create_soul_arrangement` — 17th multi-track genre arrangement. Motown/Stax/Atlantic soul (Otis Redding, Aretha Franklin, Marvin Gaye): gospel drums (steady kick, backbeat snare, ride with bell), melodic walking bass (root→fifth→octave→walk to next chord), Rhodes chord stabs on I-IV-vi-V gospel changes (maj7/dom7/min9 voicings), Motown horn stabs + pentatonic fills. 72 BPM default, C major, 4 tracks, 2 bars per chord. Integrated into create_full_genre_pipeline (17 genres total). 11 unit tests. **379 MCP tools**, 2614 unit tests

## v1.201.0 (2026-07-05)

### Added
- `werkstatt_spectral_enhancer.js` DSP script — STFT-based spectral enhancer for high-frequency "air" boost and sheen. 7 params: crossover (1-16 kHz exp), air (boost factor above crossover), sparkle (spectral peak emphasis), transients (magnitude delta detection), width (stereo widening on enhanced band), mix, output. Radix-2 Cooley-Tukey FFT (2048-point), Hann window, overlap-add reconstruction. 11 unit tests. **109 DSP scripts**, 2603 unit tests

### Fixed
- README: "303 MCP tools" → "378" (was 75 versions stale)
- README: test count updated (1403→2603)
- pyproject.toml/server.json: description "302" → "378"
- CI workflow: tool threshold 304 → 378
- dsp-scripts.md: counts updated (Werkstatt 89→90, Modulation 8→9, Time 3→4, Spectral/FX 9→10)

## v1.200.0 (2026-07-05)

### Added
- `create_lofi_arrangement` — 16th multi-track genre arrangement. Lofi hip-hop (Nujabes / J Dilla / chillhop): boom-bap drums (laid-back 16th hats, syncopated kick, backbeat snare), mellow bass (root + walk), jazzy 7th chords (ii-V-I, arpeggiated maj7/min7/dom7), sparse sleepy pentatonic melody. 78 BPM default, F major, 4 tracks. Integrated into create_full_genre_pipeline (16 genres total). 11 unit tests (signature, defaults, harmony, drums, tracks, delegation, pipeline integration, BPM validation, arpeggiation, pentatonic). **378 MCP tools**, 1403 unit tests

## v1.199.0 (2026-07-05)

### Added
- `werkstatt_phaser.js` DSP script — cascaded allpass phaser with LFO sweep. 7 params: rate (0.1-8 Hz), depth, stages (2-12 allpass filters), base_freq (100-8000 Hz), feedback (±0.95 resonance), mix (dry/wet), stereo (L/R LFO phase offset). First-order allpass coefficient: a = (1-sin(wT))/(1+sin(wT)). Completes the "big four" modulation effects (chorus ✅, flanger ✅, phaser ✅, tremolo ✅). 11 unit tests. **109 DSP scripts** (90 Werkstatt + 9 Apparat + 10 Spielwerk), 1392 unit tests, ruff F401 fix

## v1.198.0 (2026-07-05)

### Added
- `remix_track` — full Suno remix pipeline in one call: analyze_track → set_bpm → import_audio_to_tracks → create_progression_from_key → create_harmonic_arrangement → apply_genre_mix → add_mastering_chain. 7 steps, one call replaces 8-10 individual tool calls. Defaults: synthwave genre, bs4 stems, -14 LUFS. Parameters: genre, style, stem_mode, master_lufs, add_harmony, add_counter_melody, bars. 6 unit tests (signature, pipeline steps, defaults, delegation, harmony skip, full Suno pipeline). **377 MCP tools**, 1381 unit tests

## v1.197.0 (2026-07-05)

### Added
- `analyze_track` — composite audio analysis in one call: BPM + key + mode + LUFS + true peak + duration + dynamic range + chroma. Runs detect_bpm + detect_key + measure_lufs internally. Eliminates 3 separate calls. 6 unit tests (field validation, component existence, synthetic track, dynamic range math, pipeline). **376 MCP tools**, 1375 unit tests

## v1.196.0 (2026-07-05)

### Added
- `create_progression_from_key` — auto-generate diatonic chord progression from detected key + mode. 6 styles (pop/jazz/rock/synthwave/folk/lofi), 12 templates (major + minor). Delegates to create_chord_progression with auto-computed chord roots from scale degrees. Eliminates manual chord typing — detect_key → create_progression_from_key("A", "minor", "synthwave") → Am-F-C-G automatically. 14 unit tests (diatonic correctness across all 12 keys × 6 styles, progression lengths, style templates). **375 MCP tools**, 1369 unit tests

## v1.195.0 (2026-07-05)

### Added
- `detect_key` — musical key detection using chroma features + Krumhansl-Schmuckler key profiles. Pure Python radix-2 Cooley-Tukey FFT (no numpy/librosa). STFT (4096-point, Hann window, 75% overlap) → 12 pitch class chroma vector → correlation with 24 key profiles (12 roots × major/minor). Returns key, mode, confidence, alternatives (top 3), chroma vector. C major triad → C major ✅, A minor triad → A minor ✅, A4 sine → A ✅. Completes Suno remix pipeline: download → detect_bpm → detect_key → import → generate matching harmony → mix → render. **374 MCP tools**, 1355 unit tests, 16 new (4 FFT + 12 key detection)

## v1.194.0 (2026-07-05)

### Added
- `detect_bpm` — BPM detection using onset detection + autocorrelation. Pure Python (no numpy). Energy envelope (1024-sample windows) → onset peaks → autocorrelation across 60-200 BPM with half/double-time check. 373 MCP tools, 1339 unit tests

## v1.193.0 (2026-07-05)

### Added
- `download_audio` — download audio from URL (Suno CDN, any HTTP source) to local disk. Streaming download (64KB chunks), 60s timeout, filename sanitization, next_step suggestion. Completes Suno integration pipeline: chirp_generate → download_audio → import_audio_to_tracks → mix → master → render. 372 MCP tools total

## v1.192.0 (2026-07-05)

### Added
- `import_audio_to_tracks` — one-call Suno-to-DAW pipeline. Audio file → (optional stem separation) → create instrument tracks → load → place. Without mode = single track. With mode = one track per stem (replaces 12+ manual calls). New example: `suno_stems_pipeline.py`. 371 MCP tools total

### Updated
- `suno-to-opendaw` skill — Stage 3 rewritten with import_audio_to_tracks, E2E example updated, tooling section synced

## v1.191.0 (2026-07-05)

### Added
- `create_solo_automation` — mute all tracks except one for a beat range, then restore. Drum break, bass spotlight, vocal spotlight in one call. Internally calls create_mute_automation for each non-solo track. Replaces N manual mute automation calls. 370 MCP tools total

### Updated
- All 11 agent skills synchronized to 372 tools / 108 DSP / v1.193.0

## v1.190.0 (2026-07-05)

### Added
- `werkstatt_waveguide_string.js` — bidirectional waveguide string synthesis. Two delay lines per channel (forward/backward waves). Bridge termination: one-pole lowpass (brightness). Nut termination: first-order allpass dispersion (inharmonicity for stiff strings). Pick position splits excitation between waves. 7 params. 108 DSP scripts total

## v1.189.0 (2026-07-05)

### Added
- `clear_region_notes` — erase all notes inside a region while keeping the region on the timeline. The "erase and rewrite" operation. Different from delete_note_region (removes entire region) and delete_note (removes single note). Supports all regions on track (region_index=-1). 369 MCP tools total

## v1.188.0 (2026-07-05)

### Added
- `delete_section` — delete all regions in a beat range across all tracks. Completes section CRUD trilogy: duplicate (copy), move (cut-paste), delete (remove). Collect-then-delete pattern avoids index invalidation. One call replaces N delete_region calls. 368 MCP tools total

## v1.187.0 (2026-07-05)

### Added
- `move_section` — move all regions in a beat range to a new position. Cut-and-paste for arrangement restructuring. Scans all tracks across all AUs, collects overlapping regions first (avoids index invalidation), then moves each with offset. Pairs with duplicate_section (copy vs move). 367 MCP tools total

## v1.186.0 (2026-07-05)

### Added
- `apply_velocity_pattern` — cyclic velocity accent pattern on existing notes. JSON array of multipliers cycled across notes in position order. 2 modes: cycle (repeat pattern from start) and stretch (distribute evenly across all notes). Base velocity multiplier. The groove tool — replaces manual per-note velocity editing. 366 MCP tools total

## v1.185.0 (2026-07-05)

### Added
- `duplicate_section` — duplicate all regions in a beat range to a new position. Scans all tracks across all AUs, finds overlapping regions, copies each with offset. One call replaces N duplicate_region calls. Works with note/audio/automation regions. 365 MCP tools total

## v1.184.0 (2026-07-05)

### Added
- `create_tempo_ramp` — smooth tempo ramp (ritardando/accelerando). Creates series of ValueEventBox on tempo track with linear interpolation. 3 curves: linear (even), exp (ease-in), log (ease-out). Configurable steps (default 16). Auto-detects ramp type from BPM direction. 364 MCP tools total

## v1.183.0 (2026-07-05)

### Added
- `werkstatt_karplus_strong.js` — Karplus-Strong physical modeling string synthesis. Delay-line with one-pole lowpass feedback loop. 7 params: frequency (exp 20-2000 Hz), decay, brightness (feedback filtering), pluck_damping (excitation gain), stretch (inharmonic/detuned strings), mix, output. Stereo processing. 107 DSP scripts total

### Fixed
- Ruff: 4 unused variables removed from test_orchestration.py (arp_pattern, bass_pattern, drum_genre, steps)

## v1.182.0 (2026-07-05)

### Added
- `create_section_transition` — composite section transition in one call. 5 presets: drop (breakdown→drop: filter close + mute + filter open + impact), buildup (verse→chorus: filter open + fade in), breakdown (main→breakdown: filter close + fade out + mute), intro (silence→intro: fade in all + filter open), outro (main→outro: fade out all + filter close). Replaces 3-5 individual automation calls. 363 MCP tools total

## v1.181.0 (2026-07-05)

### Added
- `werkstatt_spectral_blur.js` — STFT-based spectral blur DSP. Smears magnitude across frequency bins (freq_blur) and time frames (time_blur), with phase randomization for diffuse texture. Cooley-Tukey FFT, Hann window, overlap-add reconstruction. Classic for ambient, drone, sound design. 106 DSP scripts total

## v1.180.0 (2026-07-05)

### Added
- `create_mute_automation` — timed mute/unmute automation events for section dynamics. Mute drums in breakdowns, unmute for drops, create structural silences. Step interpolation (boolean, no smooth ramp). JSON event array input. 362 MCP tools total

## v1.179.0 (2026-07-05)

### Added
- `create_pan_sweep` — stereo panning automation sweep. L→R, R→L, or partial. Linear curve default (panning is psychoacoustic, exp not needed). For intros, guitar solos, EDM builds, stereo movement. 361 MCP tools total

## v1.178.0 (2026-07-05)

### Added
- `create_volume_fade` — smart volume fade automation on AU volume. Direction-aware (in/out), dB-to-normalized conversion via VolumeMapper powerByCenter(-96, -9, +6), exp curve default. For intros, outros, breakdowns, section transitions. 360 MCP tools total

## v1.177.0 (2026-07-05)

### Added
- `create_filter_sweep` — smart filter sweep on Vaporisateur cutoff. Direction-aware (open/close), exponential curve default (natural for frequency perception), optional resonance boost at midpoint (classic "talking filter" whistle effect). The most common EDM/techno/house transition technique in one call. 359 MCP tools total

## v1.176.0 (2026-07-05)

### Fixed
- Removed 3 unused variables flagged by ruff: `ext_tones` in `create_melody_from_progression` (server.py), `auto_wah_features` and `divisions` in test_utils.py — ruff now fully clean (0 errors, first time in 15+ cycles)

### Changed
- Synced docs/dsp-scripts.md with actual scripts: added 5 missing DSP scripts (de_plosive, mid_side_processor, haas_widener, glue_comp, vowel_morph), updated category counts (Dynamics 11→13, Filter 9→10, Stereo/Spatial 4→6, Restoration 4→5), total 81→86 Werkstatt, 100→105 scripts
- Synced TOOL_CATALOG.md with actual scripts: added 10 missing Werkstatt DSP scripts (moog_ladder, rotary_speaker, waveshaper, envelope_follower, auto_wah, mid_side_processor, haas_widener, glue_comp, de_plosive, vowel_morph), updated counts 71→86 Werkstatt, 90→105 total

## v1.175.0 (2026-07-05)

### Added
- `werkstatt_vowel_morph.js` — formant vowel morph DSP. Morphs between 5 vowels (A, E, I, O, U) via 3 cascaded resonant biquad bandpass filters. Auto-morph LFO for talking/chatter effects. Spectral tilt for darken/brighten. 105 DSP scripts total

## v1.174.0 (2026-07-05)

### Added
- `create_buildup` — combined build-up tool: riser + snare roll in one call. 5 styles: edm (4-stage roll + exp riser C2→C6), trap (triplet roll + C1→C5), techno (3-stage), rock (linear riser + tom), minimal (riser only). Pairs with `create_impact` for complete build-up → drop transition

## v1.173.0 (2026-07-05)

### Added
- `create_impact` — transition hit tool for EDM drops and section changes. 5 types: sub_boom (C1 deep), impact_hit (C3 punch), downlifter (descending glissando), sub_drop (B0 cinematic), punch (C5 snappy). Pairs with `create_riser` for build-up → drop transitions

## v1.172.0 (2026-07-05)

### Added
- `werkstatt_glue_comp.js` — SSL-style bus glue compressor. Auto-makeup gain, VCA warmth (even harmonics), parallel mix. SSL defaults: 2:1 ratio, 10ms attack, 100ms release. 104 DSP scripts total

## v1.171.0 (2026-07-05)

### Added
- `apply_full_mix` — one-call complete mix: genre-aware drum/bass/instrument chains on all tracks + mastering. Replaces 5-6 individual chain calls. 15 genres supported

## v1.170.0 (2026-07-05)

### Added
- `werkstatt_haas_widener.js` — Haas stereo widener DSP. Creates pseudo-stereo via short delay (1-30ms) on one channel, based on the Haas (precedence) effect. Params: delay, width, channel, feedback, mix. 103 DSP scripts total

## v1.169.0 (2026-07-05)

### Added
- `add_instrument_chain` — universal instrument processing chain: EQ → Comp → Reverb (+ optional Delay). 5 presets: clean, warm, bright, ambient, driven. Covers guitars, keys, synth leads, strings, pads
- `create_full_genre_pipeline` now supports `add_track_chains=True` — automatically applies genre-appropriate drum/bass/instrument chains to each track

## v1.168.0 (2026-07-05)

### Added
- `add_drum_chain` — one-call drum processing: Gate → EQ → Compressor (+ optional Reverb). 5 presets: punchy, deep, crisp, roomy, tight
- `add_bass_chain` — one-call bass processing: EQ → Compressor (+ optional Waveshaper drive). 5 presets: deep, round, driven, clean, tight
- Completes the processing chain family: vocal + drum + bass + mastering

## v1.167.0 (2026-07-05)

- **add_vocal_chain** — new one-call vocal processing chain. Adds EQ + Compressor + Reverb (+ optional Delay) to any audio unit. 5 style presets: balanced (pop), warm (R&B/soul), bright (radio pop), intimate (ballad/acoustic), aggressive (rock/rap). Each preset has genre-appropriate EQ curves (low shelf, mid cut, high shelf air) and compressor settings (threshold, ratio, attack, release). `reverb_amount` (0-1) and `delay_amount` (0-1, default off) for spatial control. Parallel to add_mastering_chain but for vocal/melodic tracks. 12 unit tests. 352 MCP tools, 2223 tests.

## v1.166.0 (2026-07-05)

- **werkstatt_mid_side_processor.js** — new mastering DSP. Mid/Side encoder/decoder with independent gain and filtering per channel. M = (L+R)/2 (center: vocals, bass, kick), S = (L-R)/2 (stereo: wide instruments, ambience). Mid highpass removes low-end rumble from center, side lowpass tames harsh stereo content. Width control (0=mono collapse, 1=original, 2=double wide). Biquad filters on both channels. Influenced by Brainworx bx_digital. 19 unit tests. 102 DSP scripts, 2211 tests.

## v1.165.0 (2026-07-05)

- **werkstatt_de_plosive.js** — new restoration DSP. Adaptive highpass filter that detects plosive bursts (P, B, T sounds) in vocals and dynamically engages a biquad highpass only when plosive energy is detected. Clean vocal passes through untouched. Parameters: threshold (detection sensitivity), freq (80-300 Hz cutoff), attack/release (engagement speed), q (resonance), mix. Influenced by iZotope RX De-plosive. 18 unit tests. 101 DSP scripts. 2192 tests.

## v1.164.0 (2026-07-05)

- **create_modulated_song: drum_genre integration** — new `drum_genre` parameter adds genre drum arrangement (drums + bass) for the full song length BEFORE harmonic sections. When set, pads and bass are auto-skipped in harmonic sections (genre provides them). `bpm` parameter controls tempo. All 15 genres supported. Summary now includes `drum_notes`, `harmonic_notes`, and `drums` info. Backward compatible — default `drum_genre=""` = harmony only. 10 new unit tests. 2174 tests.

## v1.163.0 (2026-07-05)

- **create_modulated_song** — new multi-section song builder with key modulation. Builds verse→chorus→bridge→outro in one call, each section with its own chord progression, length, and energy level. Auto-calculates start_beat for each section. Default: 24-bar song (verse Am-F-C-G 8 bars 0.7 → chorus C-G-Am-F 8 bars 1.0 → bridge F-C-Dm-G 4 bars 0.6 → outro Am-F-C-G 4 bars 0.5). Inherits all 5 harmonic layers from create_harmonic_arrangement. Supports up to 12 sections. New example: modulated_song.py. 17 unit tests. 351 MCP tools, 2164 tests.

## v1.162.0 (2026-07-05)

- **modulate_progression** — new music theory tool. Transpose chord progression to a new key while preserving chord qualities and interval relationships. Supports up/down direction, flat/sharp key naming, per-chord mapping with root shifts. Common modulations: relative major/minor (Am↔C), up a fourth (C→F, chorus energy), up a fifth (C→G, triumphant), down a third (C→A, bridge). Returns modulated progression string ready for create_harmonic_arrangement. 16 unit tests. 350 MCP tools, 2147 tests.

## v1.161.0 (2026-07-05)

- **create_full_genre_pipeline: harmonic layers integration** — new `progression` parameter adds arp + melody harmonic layers on top of genre rhythm. Pads and bass skipped (genre arrangement already provides them). `add_counter_melody` flag (default False) optionally adds contrary-motion counter-melody. `bars_per_chord` auto-calculated as `bars // 4`. Pipeline summary now includes `rhythm_notes`, `harmonic_notes`, and `progression` fields. Backward compatible — default `progression=""` = rhythm only. 8 new unit tests. 2131 tests.

## v1.160.0 (2026-07-05)

- **create_harmonic_arrangement: counter-melody integrated** — 5th layer (counter-melody) now built into the one-call harmonic arrangement. New params: `counter_melody_pattern` (contrary/oblique/parallel_third/parallel_sixth/call_response, default ""=skip) and `counter_melody_octave` (default 4). Track auto-routing: counter-melody placed on track 3+layers_before (3 if no arp/melody, 4 if one, 5 if both). Velocity auto-scaled to 0.6x (supportive, below melody 0.75x). Backward compatible — default counter_melody_pattern="" skips. Example `harmonic_quintet.py` updated to one-call. 2123 tests.

## v1.159.0 (2026-07-05)

- **create_counter_melody_from_progression** — new harmonic quintet layer. Second melodic line (counterpoint) from chord progression string. 5 contrapuntal patterns: contrary (opposite root motion), oblique (sustained tone), parallel_third (sweet consonance), parallel_sixth (open cinematic), call_response (gospel/soul antiphonal). Default velocity 0.6 (supportive), track 4 (above melody), octave 4 (below melody). 349 MCP tools, 2118 tests.

## v1.158.0 (2026-07-05)

- **create_harmonic_arrangement: all 4 layers now skippable** — bass_pattern="" skips bass (useful when genre arrangement already has bass), pad_octave=-1 skips pads. Previously pads and bass were always created, causing conflicts when combining with genre arrangements. New example: `liquid_dnb_harmonic.py` shows combined pipeline (genre arrangement + harmonic layers with skipped pads/bass). 119 examples.
- **2102 unit tests** (+3)

## v1.157.0 (2026-07-05)

- **2 new DSP scripts (100 total)** — `werkstatt_envelope_follower.js`: amplitude tracking DSP, attack/release envelope detection with per-sample coefficients, dry/wet mix. Building block for auto-wah, tremolo depth, ducking, sidechain detection. `werkstatt_auto_wah.js`: envelope-driven resonant filter sweep, biquad bandpass with dynamic frequency mapping (min-max Hz based on input level), per-channel state for stereo. Classic funk/disco quack (Mu-Tron III, Cry Baby, Bootsy Collins). 4+6 params. 81 Werkstatt + 9 Apparat + 10 Spielwerk = 100 DSP scripts.
- **2099 unit tests** (+26)

## v1.156.0 (2026-07-05)

- **liquid_dnb genre integration** — added liquid_dnb to apply_genre_mix (smooth comp ratio 4, lush reverb 0.8s on pads, dotted delay on melody, sidechain with gentle threshold -18), apply_genre_humanization (timing 0.05, velocity 0.08, slight behind-beat bias 0.01 — more human than DnB but still tight), and create_full_genre_pipeline (174 BPM, F root, 4 tracks, warm master). Pipeline now supports `create_full_genre_pipeline("liquid_dnb")` end-to-end. 15 genre arrangements fully integrated.
- **2073 unit tests** (+9)

## v1.155.0 (2026-07-05)

- **`create_liquid_dnb_arrangement` orchestration tool (348 MCP tools)** — new genre arrangement: liquid drum & bass. 4-track arrangement (drums + bass + pad + melody) with smooth, melodic character distinct from regular DnB: smooth breakbeat with rimshots (not Amen ghost notes), melodic sub-bass walking root→fifth→octave→third (not Reese stabs), lush extended chords min9/maj9 (not plain minor triads), soulful pentatonic lead with call-response phrases. Default root F, velocity 0.75 (smoother than DnB's 0.85). Influences: LTJ Bukem, Calibre, High Contrast, Hospital Records. 15 multi-track genre arrangements. 74 orchestration tools. 348 MCP tools
- **2064 unit tests** (+14)

## v1.154.0 (2026-07-05)

- **`create_harmonic_arrangement` orchestration tool (347 MCP tools)** — new capability: one-call harmonic quartet. Creates all four harmonic layers (chord pads + arpeggiated progression + bass + melody) from a single "Am-F-C-G" progression string in one call, replacing 4 separate calls. Configurable per-layer: pad_octave, arp_pattern (or "" to skip), arp_octave, arp_step, bass_pattern, bass_octave, melody_pattern (or "" to skip), melody_octave. Velocity auto-scaled per layer (pads=0.9x, bass=1.0x, arp=0.85x, melody=0.75x). Melody auto-routed to track 4 when arp present, track 3 otherwise. Presets: jazz (walking bass + sustained pads, no arp), house (pedal sub-bass + arp bass, no melody). 73 orchestration tools. 347 MCP tools
- **2050 unit tests** (+15)

## v1.153.0 (2026-07-05)

- **`create_melody_from_progression` orchestration tool (346 MCP tools)** — new capability: lead melody from chord progression. Completes the harmonic quartet: create_chord_pads (sustained harmony) + create_arpeggiated_progression (arp movement) + create_bass_from_progression (bass foundation) + this (lead melody). All four take the same "Am-F-C-G" string. Melody hits chord tones on strong beats (1, 3) and uses passing/neighbor tones on weak beats (2, 4) for melodic interest. 5 patterns: chord_tones (4 quarters with chord tones on 1+3, passing on 2+4), sustained (ballad, 1 chord tone per bar), syncopated (8th notes: downbeats=chord tones, upbeats=passing), triadic (8th arpeggios through chord tones with octave variation, folk/country), stepwise (scale steps between chord tones, pop/classical). Approach notes to next chord root on last bar beat 4 (chromatic half-step). 72 orchestration tools. 346 MCP tools
- **2035 unit tests** (+23)

## v1.152.0 (2026-07-05)

- **`create_bass_from_progression` orchestration tool (345 MCP tools)** — new capability: bass line from chord progression. Completes the harmonic trio: create_chord_pads (sustained harmony) + create_arpeggiated_progression (melodic movement) + this (bass foundation). All three take the same "Am-F-C-G" string. 6 patterns: root (beat 1+3 quarter notes), root_fifth (root on 1, fifth on 3 — rock/pop), walking (jazz: root→chord tone→chord tone→chromatic approach to next root), pedal (one sustained root per chord — techno/house sub-bass), octave (8th notes alternating root+octave — disco/funk), root_octave (root on 1, octave up on 3 — pop/rock power). Walking bass uses chromatic approach notes (half-step below/above next chord root). Configurable octave (1=sub-bass, 2=bass, 3=mid), velocity, bars_per_chord. 71 orchestration tools. 345 MCP tools
- **2012 unit tests** (+22)

## v1.151.0 (2026-07-05)

- **`create_arpeggiated_progression` orchestration tool (344 MCP tools)** — new capability: arpeggiated chord progression engine. Takes a progression string ("Am-F-C-G") and generates arpeggiated notes cycling through chord tones, changing chords every bars_per_chord bars. 5 patterns: up (root→3rd→5th→oct — classic synthwave), down (oct→5th→3rd→root), updown (full cycle), random (dreamy, picks from chord tones), bass (root only, driving — synthwave bass engine). Configurable octave (2=bass arp, 4=mid, 5=lead), step_duration (16th/8th/32nd), bars_per_chord. Unlike create_arpeggio (single chord repeated), this cycles through a full progression. Pairs with create_chord_pads (sustained) for the complete harmonic layer: chord_pads (harmony) + arpeggiated_progression (melodic movement from same chords). 70 orchestration tools. 344 MCP tools
- **1990 unit tests** (+16)

## v1.150.0 (2026-07-05)

- **`create_chord_pads` orchestration tool (343 MCP tools)** — new capability: human-readable chord progression pads. Takes a simple hyphen-separated string like "Am-F-C-G" instead of JSON arrays (create_chord_progression takes JSON). 10 chord types: maj, min, dom7, maj7, min7, sus2, sus4, add9, dim, aug. Parses chord names with sharps/flats (F#m, Bbmaj7). Configurable: bars_per_chord (1-16), octave (0-6), velocity, note_duration (default 3.8 beats = almost full bar with articulation gap). Default progression: Am-F-C-G = i-VI-III-VII in A minor (synthwave/trance). Also supports C-G-Am-F (pop I-V-vi-IV), Dm7-G7-Cmaj7-Am7 (jazz ii-V-I-vi). Completes the harmonic layer: create_song_with_variations (rhythm/melody) + create_chord_pads (harmony) + apply_genre_mix + render_full_song = complete production pipeline. 69 orchestration tools. 343 MCP tools
- **1974 unit tests** (+23)

## v1.149.0 (2026-07-05)

- **`render_full_song` orchestration tool (342 MCP tools)** — new capability: auto-detect song length and render entire project. Scans all note and audio regions across all tracks to find the latest ending point, adds configurable tail (default 4 beats for reverb/delay tails), then delegates to render_range. No manual beat counting needed. Closes the pipeline gap: after create_song_with_variations (or any arrangement tool), one call gets the final WAV. Two-phase: Phase 1 bridge evaluate to detect max region end, Phase 2 render_range(0, detected + tail). 68 orchestration tools. 342 MCP tools
- **1951 unit tests** (+14)

## v1.148.0 (2026-07-05)

- **`create_song_with_variations` orchestration tool (341 MCP tools)** — new capability: full song builder with real musical variations. One call builds a complete song where each section has actual musical variation (not just velocity changes). 12 presets: full (all tracks normal), drums_only (sparse drums, rest silent), drums_bass (groove only), full_busy (busy drums 1.5), breakdown (sparse 0.3 + no bass + inverted melody), melody_invert/reverse/octave_up/transposeN (melody transforms), bass_octave_up (+12), bass_sub (-24, sub bass), fade (sparse outro), drop (busy + octave-up bass, climax). Default: 36-bar song — intro(4,0.5,drums_only) → verse1(8,0.8,full) → chorus(8,1.0,full_busy) → verse2(8,0.8,melody_transpose5) → bridge(4,0.6,breakdown) → outro(4,0.4,fade). Each section calls create_arrangement_variation internally. Optional post-processing pipeline: apply_genre_mix → apply_genre_humanization → add_mastering_chain. All 14 genres supported. 67 orchestration tools. 341 MCP tools
- **1937 unit tests** (+27)

## v1.147.0 (2026-07-05)

- **`create_arrangement_variation` orchestration tool (340 MCP tools)** — new capability: musically varied sections with real transformations. Unlike create_genre_sections (which repeats the same loop at different velocities), this tool applies actual musical transformations to each track independently: drum density control (0.3 = sparse/half notes removed, 1.0 = normal, 1.5 = busy/ghost notes boosted), bass octave shift (±1-2 — sub bass to high), melody transforms (invert around middle C, transpose by N semitones, reverse/retrograde, fragment/remove off-beats, octave up/down), and independent track inclusion/exclusion (set include_drums/bass/harmony/melody = False to silence that track). All 14 genres supported (not just 8 electronic). Two-phase design: Phase 1 generates base arrangement, Phase 2 applies per-track transforms via bridge. Build real songs: intro (sparse drums, no bass) → verse1 (normal) → chorus (busy drums, octave-up bass) → verse2 (transposed melody) → bridge (sparse, inverted melody) → outro (no melody, fading). This is the difference between a loop repeated 5× and a song with musical development. 66 orchestration tools. 340 MCP tools
- **1910 unit tests** (+17)

## v1.146.0 (2026-07-05)

- **`create_genre_sections` orchestration tool (339 MCP tools)** — new capability: multi-section electronic track structure. Transforms loop-based arrangements into song structure: intro (drums only, 0.5 energy, velocity 0.39) → buildup (drums+bass, 0.7, velocity 0.546) → drop (ALL tracks, 1.0, velocity 0.78 — the climax) → breakdown (harmony+melody only, no drums/bass, 0.6) → outro (drums+bass fading, 0.4). Each section is a separate arrangement call at different start_beat with energy-scaled velocity, creating dynamic energy progression. 8 electronic genres supported (dnb/house/techno/trance/dubstep/synthwave/trap/disco). Custom section lengths via comma-separated bar counts: default "4,8,8,8,4" = 32 bars, "2,4,8,4,2" = 20 bars, "8,16,16,16,8" = 64 bars epic. Organic genres excluded (jazz/rock/funk/reggae/afrobeat/pop — they have their own structure or don't need electronic song structure). Different from pop_arrangement (which has verse-chorus-bridge internally) — this creates DJ-friendly electronic structure from ANY loop-based arrangement. 82 orchestration tools. 339 MCP tools
- **1893 unit tests** (+19)

## v1.145.0 (2026-07-05)

- **`apply_genre_humanization` orchestration tool (338 MCP tools)** — new capability: genre-aware MIDI humanization. After creating an arrangement, notes are perfectly quantized — robotic. This tool applies genre-appropriate humanization via the existing humanize_notes API: jazz gets loose timing (0.20) + wide velocity variation (0.20) + swing 0.66 (classic jazz feel); electronic genres stay tight (timing 0.02-0.04, no swing); funk gets behind-the-beat bias (0.02); reggae gets laid-back bias (0.03 — more than funk); pop is subtle (0.05); disco is between pop and funk (0.06). Per-track scaling: drums get full humanization (factor 1.0), bass gets half (0.5 — bass should stay tight), harmony gets 0.7, melody gets 0.8. 14 genre recipes matching the 14 arrangement tools. Added to create_full_genre_pipeline as Step 5 (between genre_mix and mastering). Pipeline is now: create tracks → arrangement → genre mix → humanization → mastering → ready. Jazz bass timing = 0.20*0.5 = 0.10 (half of drums), DnB bass timing = 0.03*0.5 = 0.015 (very tight). Only jazz has non-zero swing. 81 orchestration tools. 338 MCP tools
- **1874 unit tests** (+26)

## v1.144.0 (2026-07-05)

- **`create_disco_arrangement` orchestration tool (337 MCP tools)** — fourteenth multi-track genre arrangement. Classic 70s disco across 4 tracks: drums (four-on-floor with 16th OPEN hats — not closed 8ths like house, kick every quarter, clap 2+4, open hat on every 16th off-beat position), bass (SYNCOPATED OCTAVE — the "good times" bass line: root on beat 1, octave jumps on the "and" of beats 2&4, fifth walks, melodic hook with 3+ distinct pitches), strings (sustained chord pads with octave doubling, 3.8-beat sustain, lush orchestral — house uses stabs, disco uses sustained strings), guitar (wah-wah 16th chops — ALL 16 16ths with accent pattern [1.0, 0.4, 0.7, 0.3, ...], root+min7 voicing, funk-influenced "chukka-chukka", very short 0.06 duration). I-vi-IV-V progression (G-Em-C-D in G major) — major-key optimistic, the "feel good" sound. Different from house (minor vamp), pop (I-V-vi-IV), rock (I-IV-V). Disco is the ancestor of house but fundamentally different: house has off-beat bass stabs with closed 8th hats, disco has melodic octave bass with 16th open hats. Disco guitar plays ALL 16 16ths (reggae skank only plays 4 off-beats). No sidechain (organic-electronic hybrid, not pure electronic). Also added disco to apply_genre_mix (bright drum EQ high+3, warm bass, string reverb, no sidechain) and create_full_genre_pipeline (120 BPM, G major, 4 tracks, warm master). 80 orchestration tools. 14 multi-track arrangements. 337 MCP tools
- **1848 unit tests** (+22)

## v1.143.0 (2026-07-05)

- **`create_trance_arrangement` orchestration tool (336 MCP tools)** — thirteenth multi-track genre arrangement. Uplifting trance across 4 tracks: drums (driving four-on-floor — hard kick on every quarter velocity*0.9, clap on 2&4, open hats on off-beats, snare rush buildup with crescendo on last bar of 4-bar phrase), bass (ROLLING off-beat 8ths — sustained 0.4-beat notes on the "and" of every beat, root→octave alternation, the relentless engine), supersaw arp (16th-note chord arpeggio cycling root+third+fifth+octave, wall of sound, 16 notes per bar), pluck lead (staccato off-beat plucks — ALL notes on off-beats 0.5/1.5/2.5/3.5, chord-tone based, answering the supersaw). i-VI-III-VII progression (same chords as synthwave but 138 BPM euphoric vs 110 BPM nostalgic). Rolling off-beat bass is the fundamental difference — house has short off-beat stabs, techno has sustained sub drones, synthwave has 16th-note arpeggios, trance has sustained off-beat 8ths. Snare rush buildup (8 × 16th-note snares with velocity crescendo) is unique. Also added trance to apply_genre_mix (supersaw gets both reverb AND delay, aggressive sidechain ratio 4) and create_full_genre_pipeline (138 BPM, Fm, 4 tracks, loud master, sidechain). 79 orchestration tools. 13 multi-track arrangements. 336 MCP tools
- **1826 unit tests** (+19)

## v1.142.0 (2026-07-05)

- **`create_synthwave_arrangement` orchestration tool (335 MCP tools)** — twelfth multi-track genre arrangement. 80s-inspired synthwave with nostalgic feel across 4 tracks: drums (retro four-on-floor — kick on every quarter softer than house, snare on 2&4, closed hats on all 8ths, 80s drum machine feel), bass (ARPEGGIATED 16th notes — root→octave→fifth→octave, the relentless engine of synthwave, not sustained like reggae or sub-drone like techno), pads (sustained minor chords with octave doubling, full bar dreamy wash, 3.8 beat sustain), lead (nostalgic melody following chord changes, chord-tone based with echo space after each phrase). i-VI-III-VII progression (Am-F-C-G in A minor) — the four chords that define synthwave, same chords as pop's I-V-vi-IV but minor-key and different order. Arpeggiated bass is the fundamental difference from all 12 other arrangements — no other genre uses 16th-note arpeggios as the bass engine. Also added synthwave to apply_genre_mix (lush pad reverb decay 0.6, lead echo delay, sidechain) and create_full_genre_pipeline (110 BPM, A minor, 4 tracks, warm master, sidechain). 78 orchestration tools. 12 multi-track arrangements. 335 MCP tools
- **1807 unit tests** (+26)

## v1.141.0 (2026-07-05)

- **`create_full_genre_pipeline` orchestration tool (334 MCP tools)** — new capability: zero-to-render-ready in one call. Full pipeline: set BPM → create synth+note tracks → create regions → genre arrangement → genre mix (effects per track) → sidechain (electronic only) → mastering chain. One call replaces 5-10 individual tool calls. 11 genre defaults with correct BPM, key, track count, and master style. Pop auto-adjusts bars to 16 if less (needs song structure). Sidechain: electronic genres only (dnb/house/techno/dubstep/pop), organic skip. Master style: loud (dnb/trap/techno/dubstep), warm (house/rock/funk), balanced (afrobeat/pop/reggae), transparent (jazz). Returns pipeline_steps with status per step and ready_for_export flag. 77 orchestration tools. 334 MCP tools
- **1781 unit tests** (+19)

## v1.140.0 (2026-07-05)

- **`apply_genre_mix` orchestration tool (333 MCP tools)** — new capability: genre-aware mixing. Closes the loop: create arrangement → apply genre mix → ready to render. One call replaces 10-20 manual add_effect + set_effect_parameter calls. 11 genre-specific effect chain recipes, each with genre-appropriate: drums compressor (DnB ratio 8 attack 1ms, jazz ratio 2 attack 20ms), bass treatment (DnB Waveshaper saturation, reggae deep EQ, jazz natural), melody/chords (reverb + delay with genre-specific decay times), sidechain (electronic genres only: dnb/house/techno/dubstep/pop, organic genres skip: jazz/rock/funk/reggae/afrobeat). Every recipe starts with drums compressor. Compressor params vary by genre — not one-size-fits-all. 76 orchestration tools. 333 MCP tools
- **1762 unit tests** (+18)

## v1.139.0 (2026-07-05)

- **`create_reggae_arrangement` orchestration tool (332 MCP tools)** — eleventh multi-track genre arrangement. Roots reggae with one-drop feel across 4 tracks: drums (one-drop — kick AND snare TOGETHER on beat 3, no kick on beat 1, 8th-note hi-hat throughout), bass (THE lead instrument — melodic walk root→octave→fifth→root with sustained notes, follows I-IV chord changes), guitar (skank — staccato chops on ALL 4 off-beats per bar, root+min3 minor voicing, very short 0.1 duration), keys (organ bubble — sustained minor triad, Hammond-style, 3.5 beat sustain). One-drop (kick+snare together on 3, empty on 1) is unique among all 11 arrangements — no other genre puts kick and snare together. Bass as lead instrument (melodic, not rhythmic) is unique — in all other genres bass is rhythmic support. I-IV minor vamp. A minor default (classic reggae key). 60-100 BPM, default 80. 4-16 bars. 75 orchestration tools. 332 MCP tools
- **1744 unit tests** (+21)

## v1.138.0 (2026-07-05)

- **`create_funk_arrangement` orchestration tool (331 MCP tools)** — tenth multi-track genre arrangement. James Brown / Parliament-Funkadelic style — vamp-based (one chord, no progression). Across 4 tracks: drums (Funky Drummer — Clyde Stubblefield's most sampled break in history: syncopated kick at 1.25/1.75, strong ghost snare, 16th-note hi-hat with varying dynamics), bass (slap bass — Larry Graham thumb/pluck technique: thumb=root, pluck=octave/fifth/min7, 16th-note density, 16 notes per bar), guitar (scratch "chank" — all 16 16ths played with accent pattern, root+min7 voicing, extremely short 0.08 duration), horns (dominant7 stabs — root+maj3+min7, on the "and" of beats, short and tight). Vamp (one chord groove, no changes) is the fundamental difference from all 9 other arrangements — pop/rock/jazz change chords, funk stays on one. 1-bar cycle (not 2-bar like others). 16th-note syncopation is the rhythmic DNA — every instrument plays 16ths. D default (classic funk key). 85-120 BPM, default 100. 4-16 bars. 74 orchestration tools. 331 MCP tools
- **1723 unit tests** (+23)
- **`multi_track_arrangements.py` example** — demo of all 10 arrangement tools with parameters, output format, and genre comparison table. 114 examples total.

## v1.137.0 (2026-07-05)

- **`create_pop_arrangement` orchestration tool (330 MCP tools)** — ninth multi-track genre arrangement. First with real song structure (verse-chorus-bridge, not loops). Pop across 4 tracks with section-aware patterns: drums (verse=sparse kick+hat → chorus=full kick+snare+hat+crash → bridge=building toms with rising energy → outro=winding down), bass (verse=root notes sparse → chorus=driving root+octave jumps → bridge=walking chord tones building → outro=held roots), chords (I-V-vi-IV "four chords of pop" — verse=light arpeggios root+3+5 → chorus=full block chords sustained → bridge=sus4→resolution → outro=held triads), melody (verse=sparse low register → chorus=anthemic hook high register catchy → bridge=chromatic tension building → outro=winding down). I-V-vi-IV is the most used pop progression — different from rock's I-IV-V and jazz's ii-V-I. Song structure (not repeated loops) is the key difference from all 8 other arrangements. Energy varies by section: verse=0.5, chorus=1.0, bridge=0.7, outro=0.6. C default. 85-145 BPM, default 120. 16-32 bars (min 16 for song structure). 73 orchestration tools. 330 MCP tools
- **1700 unit tests** (+19)

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
