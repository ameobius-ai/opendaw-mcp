# Tool Reference

Auto-generated from `server.py`. **547 MCP tools.**

| Category | Count |
|---|---|
| Create / Modify | 303 |
| Destructive | 15 |
| Other | 141 |
| Read-only | 74 |
| Render / Export | 14 |

## Create / Modify

| Tool | Annotation | Parameters | Description |
|---|---|---|---|
| `mcp_opendaw_add_anticipation` |  | `unit_index`, `track_index`, `region_index`, `scale`, `root`, `anticipation_offset`, `anticipation_fraction`, `anticipation_velocity`, `direction`, `min_duration_beats`, `cross_track` | Add anticipation notes before strong-beat notes. |
| `mcp_opendaw_add_automation` |  | `unit_index`, `effect_index`, `parameter_name`, `points` | Add parameter automation to an effect on an audio unit. |
| `mcp_opendaw_add_bass_chain` |  | `unit_index`, `style`, `drive_amount` | Add a ready-made bass processing chain to an audio unit — EQ → Compressor (+ optional Waveshaper drive). |
| `mcp_opendaw_add_chord_tension` |  | `unit_index`, `track_index`, `region_index`, `chord_position`, `extension`, `octave`, `velocity` | Add a tension/extension note to an existing chord — jazz harmony. |
| `mcp_opendaw_add_drum_chain` |  | `unit_index`, `style`, `reverb_amount` | Add a ready-made drum processing chain to an audio unit — Gate → EQ → Compressor (+ optional Reverb). |
| `mcp_opendaw_add_effect` |  | `unit_index`, `effect_type` | Add an audio effect to an audio unit's effect chain. |
| `mcp_opendaw_add_genre_effects` |  | `genre`, `unit_index`, `vocal_unit_index` | Add genre-appropriate effects to tracks automatically. |
| `mcp_opendaw_add_instrument_automation` |  | `unit_index`, `parameter_name`, `points`, `sample_index` | Automate a parameter on the instrument connected to an audio unit. |
| `mcp_opendaw_add_instrument_chain` |  | `unit_index`, `style`, `reverb_amount`, `delay_amount` | Add a ready-made instrument processing chain — EQ → Compressor → Reverb (+ optional Delay). |
| `mcp_opendaw_add_marker` |  | `position_beats`, `label` | Add a timeline marker at a position. |
| `mcp_opendaw_add_mastering_chain` |  | `target_lufs`, `style` | Add a ready-made mastering chain to the output bus — EQ + compressor + maximizer in one call. |
| `mcp_opendaw_add_midi_effect` |  | `unit_index`, `effect_type` | Add a MIDI effect to an audio unit's MIDI effect chain. |
| `mcp_opendaw_add_modular_module` |  | `au_index`, `effect_index`, `module_type`, `label`, `x`, `y` | Add a module to a Modular device. |
| `mcp_opendaw_add_neighbor_tones` |  | `unit_index`, `track_index`, `region_index`, `scale`, `root`, `direction`, `neighbor_fraction`, `neighbor_offset`, `neighbor_velocity`, `min_duration_beats`, `cross_track` | Add upper/lower neighbor tones to embellish existing notes. |
| `mcp_opendaw_add_passing_tones` |  | `unit_index`, `track_index`, `region_index`, `scale`, `root`, `max_interval`, `velocity`, `duration_fraction`, `direction`, `cross_track` | Add passing tones between existing notes for smoother melodic lines. |
| `mcp_opendaw_add_signature_change` |  | `position_beats`, `numerator`, `denominator` | Add a time signature change at a specific position in the track. |
| `mcp_opendaw_add_suspension` |  | `unit_index`, `track_index`, `region_index`, `scale`, `root`, `resolution`, `suspension_offset`, `preparation_beats`, `suspension_velocity`, `resolution_velocity`, `cross_track` | Add suspension-resolutions to existing notes. |
| `mcp_opendaw_add_tempo_change` |  | `position_beats`, `bpm`, `interpolation` | Add a tempo (BPM) change at a specific position in the track. |
| `mcp_opendaw_add_vocal_chain` |  | `unit_index`, `style`, `reverb_amount`, `delay_amount` | Add a ready-made vocal processing chain to an audio unit — EQ + compressor + reverb (+ optional delay). |
| `mcp_opendaw_apply_articulation` |  | `unit_index`, `track_index`, `region_index`, `articulation`, `amount` | Apply articulation to existing notes — staccato, legato, tenuto, accent. |
| `mcp_opendaw_apply_contour` |  | `unit_index`, `track_index`, `region_index`, `contour`, `range_semitones`, `snap_to_scale`, `root`, `preserve_first`, `preserve_last` | Apply a melodic contour shape to existing notes. |
| `mcp_opendaw_apply_full_mix` |  | `genre`, `unit_index`, `num_tracks`, `master_lufs` | Apply a complete mix in one call — genre-aware processing chains on every track + mastering. |
| `mcp_opendaw_apply_genre_humanization` |  | `genre`, `unit_index`, `drum_track`, `bass_track`, `harmony_track`, `melody_track`, `has_4th_track` | Apply genre-aware humanization to arrangement tracks — makes programmed MIDI feel alive. |
| `mcp_opendaw_apply_genre_mix` |  | `genre`, `unit_index`, `num_tracks`, `sidechain` | Apply genre-specific mixing effects to tracks after creating an arrangement. |
| `mcp_opendaw_apply_mix_preset` |  | `preset` | Apply a mix preset to all audio units in one call — volume, pan, mute, solo. |
| `mcp_opendaw_apply_rhythm_pattern` |  | `unit_index`, `track_index`, `region_index`, `rhythm_string`, `onset_grid`, `grid`, `velocity_mode`, `duration_mode` | Apply a rhythmic pattern to existing notes — reposition onsets to match a target grid. |
| `mcp_opendaw_apply_sidechain` |  | `unit_index`, `track_index`, `bars`, `start_beat`, `depth`, `attack`, `release`, `kick_interval` | Apply sidechain ducking via volume automation — the classic pumping/breathing effect. |
| `mcp_opendaw_apply_swing` |  | `unit_index`, `track_index`, `swing_amount`, `grid` | Apply swing feel to existing notes without changing velocity or duration. |
| `mcp_opendaw_apply_velocity_curve` |  | `unit_index`, `track_index`, `region_index`, `curve_type`, `start_velocity`, `end_velocity`, `power` | Apply a velocity envelope across notes — ramp, arc, trough, or custom power curve. |
| `mcp_opendaw_apply_velocity_lfo` |  | `unit_index`, `track_index`, `rate`, `depth`, `shape`, `phase`, `center`, `region_index` | Apply periodic velocity modulation — velocity LFO along note positions. |
| `mcp_opendaw_apply_velocity_pattern` |  | `unit_index`, `track_index`, `pattern`, `region_index`, `mode`, `base_velocity` | Apply a cyclic velocity pattern to existing notes in a region. |
| `mcp_opendaw_create_acid_arrangement` |  | `key_root`, `bpm`, `bars`, `velocity`, `unit_index`, `track_index`, `start_beat` | Create an acid house arrangement — TB-303 squelch bassline. |
| `mcp_opendaw_create_additive_rhythm` |  | `grouping`, `unit`, `repeats`, `pitch`, `scale`, `root`, `octave`, `accent_mode`, `accent_velocity`, `normal_velocity`, `decay`, `unit_index`, `track_index`, `start_beat` | Create an additive rhythm — unequal groupings within a bar. |
| `mcp_opendaw_create_afrobeat_arrangement` |  | `bpm`, `bars`, `root`, `octave`, `unit_index`, `drum_track`, `bass_track`, `horn_track`, `guitar_track`, `start_beat`, `velocity` | Create a full afrobeat arrangement — polyrhythmic drums + bass + horns + guitar across 4 tracks. |
| `mcp_opendaw_create_ambient_arrangement` |  | `key_root`, `bpm`, `bars`, `velocity`, `unit_index`, `track_index`, `start_beat` | Create an ambient arrangement — 70 BPM atmospheric soundscape. |
| `mcp_opendaw_create_appoggiatura` |  | `main_pitch`, `approach_pitch`, `duration_beats`, `appoggiatura_ratio`, `velocity`, `unit_index`, `track_index`, `start_beat` | Create an appoggiatura — leaning grace note that resolves to the main note. |
| `mcp_opendaw_create_arabic_percussion` |  | `bars`, `rhythm`, `velocity`, `unit_index`, `track_index`, `start_beat`, `darbuka_pitch`, `daf_pitch`, `zills_pitch` | Create an Arabic/Middle Eastern percussion ensemble — darbuka, daf, and zills. |
| `mcp_opendaw_create_arpeggiated_progression` |  | `progression`, `pattern`, `bars_per_chord`, `octave`, `velocity`, `step_duration`, `unit_index`, `track_index`, `start_beat` | Create an arpeggiated chord progression — synthwave/trance arp engine. |
| `mcp_opendaw_create_arpeggio` |  | `chord`, `pattern`, `rate`, `octave`, `steps`, `unit_index`, `track_index`, `start_beat`, `velocity` | Create an arpeggio from a chord name — one call instead of 8-32 create_note calls. |
| `mcp_opendaw_create_arrangement_variation` |  | `genre`, `section_name`, `bpm`, `root`, `bars`, `start_beat`, `velocity`, `drum_density`, `bass_octave_shift`, `melody_transform`, `include_drums`, `include_bass`, `include_harmony`, `include_melody`, `unit_index`, `drum_track`, `bass_track`, `harmony_track`, `melody_track` | Create a musically varied section — not a repeat, a real variation. |
| `mcp_opendaw_create_audio_bus` |  | `name` | Create a new audio bus (aux bus) with its own audio unit and track. |
| `mcp_opendaw_create_audio_clip` |  | `sample_id`, `unit_index`, `clip_index`, `track_index`, `bpm` | Create an audio clip in the session view (clip launcher). |
| `mcp_opendaw_create_audio_track` |  | — | Create a new audio track on the primary audio unit. |
| `mcp_opendaw_create_automation_event` |  | `unit_index`, `track_index`, `position_beats`, `value`, `interpolation`, `curve_slope` | Create a single automation event at a specific position on a value track. |
| `mcp_opendaw_create_balkan_meter` |  | `meter`, `cycles`, `variation`, `velocity`, `unit_index`, `track_index`, `start_beat`, `kick_pitch`, `snare_pitch`, `hh_pitch`, `tapan_pitch` | Create a Balkan additive meter pattern — asymmetric time signatures with unequal beat groupings. |
| `mcp_opendaw_create_bariolage` |  | `root`, `scale`, `bars`, `octave`, `pedal_pitch`, `moving_pattern`, `subdivision`, `velocity`, `pedal_velocity`, `accent_pedal`, `unit_index`, `track_index`, `start_beat` | Create a bariolage — rapid alternation between a fixed pedal pitch and moving notes. |
| `mcp_opendaw_create_bass_drop` |  | `start_pitch`, `end_pitch`, `sweep_beats`, `hold_beats`, `sweep_curve`, `unit_index`, `track_index`, `start_beat`, `velocity` | Create a bass drop — descending pitch sweep into sustained sub bass. |
| `mcp_opendaw_create_bass_from_progression` |  | `progression`, `pattern`, `bars_per_chord`, `octave`, `velocity`, `unit_index`, `track_index`, `start_beat` | Create a bass line from a chord progression string. |
| `mcp_opendaw_create_bassline` |  | `root`, `pattern`, `unit_index`, `track_index`, `start_beat`, `octave`, `velocity`, `scale` | Create a bassline from root note + rhythmic pattern — one call instead of 8-20 create_note calls. |
| `mcp_opendaw_create_binary_form` |  | `key_root`, `scale_name`, `bars_per_section`, `repeat`, `modulation`, `velocity`, `unit_index`, `track_index`, `start_beat` | Create binary form — two contrasting sections (A\|B) with optional repeats. |
| `mcp_opendaw_create_blues_arrangement` |  | `bpm`, `bars`, `root`, `octave`, `unit_index`, `drum_track`, `bass_track`, `chord_track`, `lead_track`, `start_beat`, `velocity` | Create a full blues arrangement — shuffle drums + walking bass + dominant 7th chords + blues scale lead. |
| `mcp_opendaw_create_boom_bap` |  | `boom_bap_type`, `bars`, `unit_index`, `track_index`, `start_beat`, `kick_pitch`, `snare_pitch`, `hat_pitch`, `velocity` | Create a boom-bap hip-hop drum pattern — the foundational beat of hip-hop. |
| `mcp_opendaw_create_bordun` |  | `root`, `octave`, `intervals`, `bars`, `beats_per_bar`, `velocity`, `retrigger_bars`, `unit_index`, `track_index`, `start_beat` | Create a bordun — continuously sustained drone chord as a textural layer. |
| `mcp_opendaw_create_break` |  | `break_type`, `bars`, `variation`, `unit_index`, `track_index`, `start_beat`, `swing` | Create a classic drum break — the foundation of jungle, DnB, hip-hop, breakbeat. |
| `mcp_opendaw_create_breakbeat` |  | `breakbeat_type`, `bars`, `unit_index`, `track_index`, `start_beat`, `kick_pitch`, `snare_pitch`, `hat_pitch`, `ghost_pitch`, `velocity` | Create a breakbeat pattern — the syncopated skeleton of jungle, DnB, big beat, and breakbeat hardcore. |
| `mcp_opendaw_create_breakbeat_arrangement` |  | `key_root`, `bpm`, `bars`, `velocity`, `unit_index`, `track_index`, `start_beat` | Create a breakbeat/big beat arrangement — 130 BPM broken-beat energy. |
| `mcp_opendaw_create_bridge` |  | `bridge_type`, `key_root`, `scale_type`, `octave`, `bars`, `velocity`, `unit_index`, `track_index`, `start_beat`, `seed` | Create a bridge section — the contrast that breaks repetition. |
| `mcp_opendaw_create_buildup` |  | `unit_index`, `track_index`, `start_beat`, `length_beats`, `style`, `velocity` | Create a complete build-up — riser + snare roll in one call. |
| `mcp_opendaw_create_cadence` |  | `cadence_type`, `key_root`, `scale_type`, `octave`, `velocity`, `unit_index`, `track_index`, `start_beat`, `seed` | Create a cadence — a harmonic conclusion that ends a phrase or section. |
| `mcp_opendaw_create_cadenza` |  | `root`, `scale`, `duration_beats`, `octave`, `style`, `virtuosic`, `breath_marks`, `velocity`, `unit_index`, `track_index`, `start_beat` | Create a cadenza — an unmeasured virtuosic solo passage with rubato. |
| `mcp_opendaw_create_call_and_response` |  | `call_pattern`, `call_rhythm`, `response_type`, `key_root`, `scale_name`, `pairs`, `response_interval`, `velocity`, `gap_beats`, `unit_index`, `track_index`, `start_beat` | Create call-and-response — two phrases in musical dialogue. |
| `mcp_opendaw_create_call_response` |  | `scale`, `root`, `call_pattern`, `response_pattern`, `unit_index`, `track_index`, `start_beat`, `octave`, `velocity`, `step_duration`, `repeats` | Create a call-and-response pattern — antecedent/consequent phrase structure. |
| `mcp_opendaw_create_canon` |  | `melody`, `voices`, `entry_delay_beats`, `transposition`, `velocity_decay`, `direction`, `unit_index`, `track_index`, `start_beat`, `velocity` | Create a canon — strict melodic imitation with delayed voice entries. |
| `mcp_opendaw_create_cascara` |  | `cascara_type`, `bars`, `unit_index`, `track_index`, `start_beat`, `high_pitch`, `low_pitch`, `velocity` | Create an Afro-Cuban cáscara pattern — the timbale shell rhythm that fills space around the clave. |
| `mcp_opendaw_create_chaconne` |  | `bass_pattern`, `bass_rhythm`, `chord_pattern`, `variation_style`, `repeats`, `velocity`, `unit_index`, `track_index`, `start_beat` | Create a chaconne — repeating bass + chord progression + developing variations. |
| `mcp_opendaw_create_chop` |  | `pitches`, `chop_mode`, `segment_beats`, `stutter_count`, `octave_shift`, `velocity_variation`, `reverse_pitch_in_segment`, `unit_index`, `track_index`, `start_beat`, `velocity`, `seed` | Create a chop — slice source pitches into segments and rearrange them. |
| `mcp_opendaw_create_chorale` |  | `chord_pattern`, `beats_per_chord`, `beats_per_bar`, `key_root`, `key_mode`, `soprano_velocity`, `alto_velocity`, `tenor_velocity`, `bass_velocity`, `note_duration`, `voice_spread`, `unit_index`, `track_index`, `start_beat` | Create a 4-voice SATB chorale with voice-leading rules. |
| `mcp_opendaw_create_chord_pads` |  | `progression`, `bars_per_chord`, `octave`, `velocity`, `unit_index`, `track_index`, `start_beat`, `note_duration` | Create chord pads from a human-readable progression string. |
| `mcp_opendaw_create_chord_progression` |  | `chords`, `unit_index`, `track_index`, `start_beat`, `chord_duration` | Create a chord progression from chord names — one call instead of 15-50 note creations. |
| `mcp_opendaw_create_chorus` |  | `chorus_type`, `key_root`, `scale_type`, `octave`, `bars`, `velocity`, `unit_index`, `track_index`, `start_beat`, `seed` | Create a chorus — the emotional peak, the hook, the memorable part. |
| `mcp_opendaw_create_clave` |  | `clave_type`, `bars`, `unit_index`, `track_index`, `start_beat`, `pitch`, `velocity`, `duration` | Create an Afro-Cuban clave pattern — the 5-note rhythmic skeleton that defines the feel. |
| `mcp_opendaw_create_coda` |  | `coda_type`, `key_root`, `scale_type`, `octave`, `bars`, `velocity`, `unit_index`, `track_index`, `start_beat`, `seed` | Create a coda — the definitive ending after the main material is done. |
| `mcp_opendaw_create_colotomic` |  | `root`, `scale`, `cycles`, `octave`, `structure`, `tempo_density`, `velocity`, `unit_index`, `track_index`, `start_beat` | Create a colotomic structure — interlocking gong layers marking cyclic time. |
| `mcp_opendaw_create_comparsa` |  | `style`, `bars`, `tempo_bpm`, `velocity`, `unit_index`, `track_index`, `start_beat` | Create Cuban comparsa — carnival procession percussion. |
| `mcp_opendaw_create_comping` |  | `chords`, `rhythm`, `unit_index`, `track_index`, `start_beat`, `chord_octave`, `velocity`, `note_spacing`, `syncopation` | Create comping — rhythmic chordal accompaniment. |
| `mcp_opendaw_create_counter_melody` |  | `counter_type`, `key_root`, `scale_type`, `octave`, `bars`, `velocity`, `unit_index`, `track_index`, `start_beat`, `seed` | Create a counter-melody — a secondary melody that complements the main one. |
| `mcp_opendaw_create_counter_melody_from_progression` |  | `progression`, `pattern`, `bars_per_chord`, `octave`, `velocity`, `unit_index`, `track_index`, `start_beat` | Create a counter-melody (second melodic line) from a chord progression. |
| `mcp_opendaw_create_counterpoint` |  | `unit_index`, `track_index`, `region_index`, `interval`, `new_unit_index`, `new_track_index`, `velocity` | Generate a counter-melody in contrary motion to existing notes. |
| `mcp_opendaw_create_country_arrangement` |  | `bpm`, `bars`, `root`, `octave`, `unit_index`, `drum_track`, `bass_track`, `chord_track`, `lead_track`, `start_beat`, `velocity` | Create a full country arrangement — boom-chick guitar + root-five bass + major pentatonic fiddle lead. |
| `mcp_opendaw_create_crescendo` |  | `unit_index`, `track_index`, `region_index`, `start_velocity`, `end_velocity`, `curve` | Apply a crescendo or decrescendo to existing notes in a region. |
| `mcp_opendaw_create_cross_rhythm` |  | `voices`, `bars`, `unit_index`, `track_index`, `start_beat`, `duration`, `base_velocity` | Create a cross-rhythm — multiple voices with independent period lengths creating shifting alignment. |
| `mcp_opendaw_create_dembow` |  | `dembow_type`, `bars`, `unit_index`, `track_index`, `start_beat`, `kick_pitch`, `snare_pitch`, `velocity` | Create a dembow rhythm — the foundational beat of reggaeton and Latin dancehall. |
| `mcp_opendaw_create_descant` |  | `descant_type`, `key_root`, `scale_type`, `octave`, `bars`, `velocity`, `unit_index`, `track_index`, `start_beat`, `seed` | Create a descant — a secondary melody sung/played above the main melody. |
| `mcp_opendaw_create_disco_arrangement` |  | `bpm`, `bars`, `root`, `octave`, `unit_index`, `drum_track`, `bass_track`, `string_track`, `guitar_track`, `start_beat`, `velocity` | Create a full disco arrangement — four-on-floor + octave bass + string sustains + wah guitar across 4 tracks. |
| `mcp_opendaw_create_djembe_ensemble` |  | `bars`, `style`, `velocity`, `unit_index`, `track_index`, `start_beat`, `kenkeni_pitch`, `sangban_pitch`, `dundunba_pitch`, `djembe1_pitch`, `djembe2_pitch`, `bell_pitch` | Create a West African djembe/dunun ensemble — cyclical ostinato with call-and-response. |
| `mcp_opendaw_create_dnb_arrangement` |  | `bpm`, `bars`, `root`, `octave`, `unit_index`, `drum_track`, `bass_track`, `pad_track`, `start_beat`, `velocity` | Create a full drum & bass arrangement — drums + bass + pad across 3 tracks in one call. |
| `mcp_opendaw_create_downtempo_arrangement` |  | `key_root`, `bpm`, `bars`, `velocity`, `unit_index`, `track_index`, `start_beat` | Create a downtempo/trip-hop arrangement — 85 BPM Bristol sound. |
| `mcp_opendaw_create_drum_fill` |  | `unit_index`, `fill_type`, `bars`, `start_beat`, `density` | Create a drum fill or transition pattern — one call replaces 10-30 note creations. |
| `mcp_opendaw_create_drum_pattern` |  | `pattern`, `unit_index` | Create a drum beat from compact step-sequencer notation — one call replaces 10-20 note creations. |
| `mcp_opendaw_create_drum_solo` |  | `solo_type`, `bars`, `velocity`, `unit_index`, `track_index`, `start_beat`, `seed` | Create a genre-specific drum solo with rudimental vocabulary. |
| `mcp_opendaw_create_dubstep_arrangement` |  | `bpm`, `bars`, `root`, `octave`, `unit_index`, `drum_track`, `bass_track`, `lead_track`, `start_beat`, `velocity` | Create a full dubstep arrangement — half-time drums + wobble bass + lead arp across 3 tracks. |
| `mcp_opendaw_create_edm_arrangement` |  | `bpm`, `bars`, `root`, `octave`, `unit_index`, `drum_track`, `bass_track`, `synth_track`, `lead_track`, `start_beat`, `velocity` | Create a full EDM arrangement — festival/mainstage 4-on-floor + supersaw + pluck + lead. |
| `mcp_opendaw_create_electronic_bass` |  | `bass_type`, `bars`, `unit_index`, `track_index`, `start_beat`, `root`, `octave`, `velocity` | Create an electronic bassline pattern — genre-specific bass for dance music. |
| `mcp_opendaw_create_etude` |  | `etude_type`, `key_root`, `scale_type`, `bars`, `octave`, `velocity`, `unit_index`, `track_index`, `start_beat`, `seed` | Create an etude — a technical study piece targeting a specific skill. |
| `mcp_opendaw_create_euclidean_rhythm` |  | `onsets`, `steps`, `rotation`, `bars`, `unit_index`, `track_index`, `start_beat`, `pitch`, `velocity`, `duration` | Create a Euclidean rhythm — distributes k onsets across n steps as evenly as possible. |
| `mcp_opendaw_create_filter_sweep` |  | `unit_index`, `direction`, `start_beat`, `duration_beats`, `start_cutoff`, `end_cutoff`, `resonance`, `resonance_boost`, `curve`, `steps` | Create a filter sweep on a Vaporisateur instrument's cutoff parameter with smart defaults. |
| `mcp_opendaw_create_flamenco_compas` |  | `palo`, `cycles`, `velocity`, `unit_index`, `track_index`, `start_beat`, `palmas_secas_pitch`, `palmas_sordas_pitch`, `cajon_pitch`, `golpe_pitch` | Create a Flamenco compás — the cyclical rhythmic foundation of Flamenco. |
| `mcp_opendaw_create_four_on_floor` |  | `floor_type`, `bars`, `unit_index`, `track_index`, `start_beat`, `kick_pitch`, `hat_pitch`, `open_hat_pitch`, `clap_pitch`, `perc_pitch`, `velocity` | Create a four-on-the-floor pattern — the foundational beat of house, techno, and disco. |
| `mcp_opendaw_create_fugato` |  | `root`, `scale`, `subject_notes`, `bars`, `octave`, `voices`, `answer_interval`, `answer_mode`, `include_countersubject`, `countersubject_interval`, `include_episode`, `episode_bars`, `velocity`, `unit_index`, `track_index`, `start_beat` | Create a fugato — a fugal passage with subject entries and imitation. |
| `mcp_opendaw_create_fugue` |  | `subject`, `voices`, `entry_delay_beats`, `answer_type`, `countersubject`, `key_root`, `key_mode`, `note_duration`, `velocity`, `velocity_decay`, `stretto`, `unit_index`, `track_index`, `start_beat` | Create a fugue — polyphonic composition with subject, answer, and countersubject. |
| `mcp_opendaw_create_full_genre_pipeline` |  | `genre`, `bpm`, `bars`, `root`, `master_lufs`, `progression`, `add_counter_melody`, `add_track_chains` | Create a complete genre track from zero to render-ready in one call. |
| `mcp_opendaw_create_funk_arrangement` |  | `bpm`, `bars`, `root`, `octave`, `unit_index`, `drum_track`, `bass_track`, `guitar_track`, `horn_track`, `start_beat`, `velocity` | Create a full funk arrangement — funky drummer + slap bass + scratch guitar + horn stabs across 4 tracks. |
| `mcp_opendaw_create_future_bass_arrangement` |  | `bpm`, `bars`, `root`, `octave`, `unit_index`, `drum_track`, `bass_track`, `chord_track`, `lead_track`, `start_beat`, `velocity` | Create a full future bass arrangement — 4 tracks: drums + bass + chords + lead. |
| `mcp_opendaw_create_garage_arrangement` |  | `key_root`, `bpm`, `bars`, `velocity`, `unit_index`, `track_index`, `start_beat` | Create a UK garage arrangement — 130 BPM 2-step swing. |
| `mcp_opendaw_create_genre_sections` |  | `genre`, `bpm`, `root`, `section_lengths`, `unit_index`, `drum_track`, `bass_track`, `harmony_track`, `melody_track` | Create a multi-section electronic track from loop-based arrangements — intro → buildup → drop → breakdown → outro. |
| `mcp_opendaw_create_genre_track` |  | `genre`, `bpm` | Create a genre-specific starting track with synth, beat, and basic mix — one call builds a full section. |
| `mcp_opendaw_create_ghost_notes` |  | `unit_index`, `track_index`, `region_index`, `density`, `velocity`, `seed` | Add ghost notes (quiet grace notes) to existing drum/MIDI patterns. |
| `mcp_opendaw_create_glissando` |  | `start_pitch`, `end_pitch`, `scale_type`, `duration_beats`, `rate`, `velocity`, `velocity_curve`, `unit_index`, `track_index`, `start_beat` | Create a glissando — smooth scale run between two pitches. |
| `mcp_opendaw_create_gospel_arrangement` |  | `bpm`, `bars`, `root`, `octave`, `unit_index`, `drum_track`, `bass_track`, `organ_track`, `choir_track`, `start_beat`, `velocity` | Create a full gospel arrangement — shuffle drums + walking bass + Hammond organ + choir. |
| `mcp_opendaw_create_ground_bass` |  | `bass_pattern`, `bass_rhythm`, `repeats`, `melody_style`, `unit_index`, `track_index`, `start_beat`, `velocity` | Create a ground bass — a repeating ostinato bass line with optional melody. |
| `mcp_opendaw_create_hardstyle_arrangement` |  | `key_root`, `bpm`, `bars`, `velocity`, `unit_index`, `track_index`, `start_beat` | Create a hardstyle arrangement — 150 BPM festival hard dance. |
| `mcp_opendaw_create_harmonic_arrangement` |  | `progression`, `pad_octave`, `arp_pattern`, `arp_octave`, `arp_step`, `bass_pattern`, `bass_octave`, `melody_pattern`, `melody_octave`, `counter_melody_pattern`, `counter_melody_octave`, `bars_per_chord`, `velocity`, `unit_index`, `start_beat` | Create all five harmonic layers from one progression string in one call. |
| `mcp_opendaw_create_harmony` |  | `unit_index`, `track_index`, `region_index`, `interval`, `direction`, `new_unit_index`, `new_track_index`, `velocity` | Generate harmony parts from existing notes — thirds, fifths, sixths, octaves. |
| `mcp_opendaw_create_harmony_line` |  | `source_unit`, `source_track`, `source_region`, `target_unit`, `target_track`, `target_region`, `interval`, `root_note`, `scale`, `direction`, `velocity_scale` | Create a harmony line from an existing melody using diatonic intervals. |
| `mcp_opendaw_create_hemiola` |  | `pattern`, `bars`, `unit_index`, `track_index`, `start_beat`, `primary_pitch`, `secondary_pitch`, `primary_velocity`, `secondary_velocity`, `duration` | Create a hemiola — 3:2 rhythmic displacement creating cross-rhythm illusion. |
| `mcp_opendaw_create_hocket` |  | `melody`, `voices`, `split_mode`, `unit_index`, `track_index`, `start_beat`, `note_duration`, `velocity` | Create a hocket — single melodic line split between voices/tracks. |
| `mcp_opendaw_create_hook` |  | `hook_type`, `key_root`, `scale_type`, `bars`, `octave`, `velocity`, `unit_index`, `track_index`, `start_beat`, `seed` | Create a melodic hook — an earworm phrase that lodges in memory. |
| `mcp_opendaw_create_house_arrangement` |  | `bpm`, `bars`, `root`, `octave`, `unit_index`, `drum_track`, `bass_track`, `stab_track`, `start_beat`, `velocity` | Create a full house music arrangement — drums + bass + stabs across 3 tracks in one call. |
| `mcp_opendaw_create_impact` |  | `unit_index`, `track_index`, `start_beat`, `impact_type`, `pitch`, `length_beats`, `velocity` | Create an impact — single hit transition element for drops and section changes. |
| `mcp_opendaw_create_industrial_arrangement` |  | `key_root`, `bpm`, `bars`, `velocity`, `unit_index`, `track_index`, `start_beat` | Create an industrial arrangement — 135 BPM dark mechanical aggression. |
| `mcp_opendaw_create_instrument_track` |  | `name` | Create a new instrument audio unit with a Tape device and an audio track. |
| `mcp_opendaw_create_interlude` |  | `interlude_type`, `key_root`, `scale_type`, `octave`, `bars`, `velocity`, `unit_index`, `track_index`, `start_beat`, `seed` | Create an interlude — a short connective passage between song sections. |
| `mcp_opendaw_create_intro` |  | `intro_type`, `key_root`, `scale_type`, `octave`, `bars`, `velocity`, `unit_index`, `track_index`, `start_beat`, `seed` | Create an intro section — the opening that sets the mood before the main body. |
| `mcp_opendaw_create_irish_trad` |  | `tune_type`, `bars`, `velocity`, `unit_index`, `track_index`, `start_beat`, `bodhran_pitch`, `feet_pitch`, `hh_pitch` | Create an Irish traditional music accompaniment — bodhrán + feet for session tunes. |
| `mcp_opendaw_create_isorhythm` |  | `talea`, `color`, `repeats`, `velocity`, `unit_index`, `track_index`, `start_beat` | Create an isorhythm — repeating rhythm (talea) × repeating pitch series (color). |
| `mcp_opendaw_create_jazz_arrangement` |  | `bpm`, `bars`, `root`, `octave`, `unit_index`, `drum_track`, `bass_track`, `piano_track`, `horn_track`, `start_beat`, `velocity` | Create a full jazz arrangement — swing drums + walking bass + comping piano + horn across 4 tracks. |
| `mcp_opendaw_create_jpop_arrangement` |  | `key_root`, `bpm`, `bars`, `velocity`, `unit_index`, `track_index`, `start_beat` | Create a J-pop arrangement — 140 BPM melodic energy pop. |
| `mcp_opendaw_create_konokol` |  | `style`, `cycles`, `tempo_bpm`, `velocity`, `unit_index`, `track_index`, `start_beat` | Create Indian Carnatic konokol (solkattu) — vocal percussion as MIDI. |
| `mcp_opendaw_create_korean_percussion` |  | `bars`, `style`, `velocity`, `unit_index`, `track_index`, `start_beat`, `janggu_chwe_pitch`, `janggu_kyong_pitch`, `buk_pitch`, `kkwaenggwari_pitch`, `jing_pitch` | Create a Korean traditional percussion ensemble — nongak (farmers' music). |
| `mcp_opendaw_create_kpop_arrangement` |  | `key_root`, `bpm`, `bars`, `velocity`, `unit_index`, `track_index`, `start_beat` | Create a K-pop arrangement — 128 BPM high-energy commercial pop. |
| `mcp_opendaw_create_l_system_melody` |  | `root`, `scale`, `bars`, `octave`, `preset`, `axiom`, `rules`, `symbol_map`, `iterations`, `duration`, `velocity`, `rest_symbol`, `unit_index`, `track_index`, `start_beat` | Create a melody using an L-system (Lindenmayer system) — a deterministic rewriting system. |
| `mcp_opendaw_create_lick` |  | `lick_type`, `key_root`, `scale_type`, `octave`, `velocity`, `unit_index`, `track_index`, `start_beat`, `seed` | Create a short melodic lick — a 1-2 bar phrase that fits a chord context. |
| `mcp_opendaw_create_liquid_dnb_arrangement` |  | `bpm`, `bars`, `root`, `octave`, `unit_index`, `drum_track`, `bass_track`, `pad_track`, `melody_track`, `start_beat`, `velocity` | Create a full liquid drum & bass arrangement across 4 tracks. |
| `mcp_opendaw_create_lofi_arrangement` |  | `bpm`, `bars`, `root`, `octave`, `unit_index`, `drum_track`, `bass_track`, `chord_track`, `melody_track`, `start_beat`, `velocity` | Create a full lofi hip-hop arrangement — boom-bap drums + jazzy chords + mellow bass + sleepy melody. |
| `mcp_opendaw_create_markov_melody` |  | `root`, `scale`, `bars`, `octave`, `order`, `interval_weights`, `duration`, `velocity`, `seed`, `unit_index`, `track_index`, `start_beat` | Create a melody using a Markov chain over scale-degree intervals. |
| `mcp_opendaw_create_melodic_polyrhythm` |  | `unit_index`, `track_index`, `numerator`, `denominator`, `bars`, `pitches`, `velocity`, `velocity_pattern`, `start_beat`, `direction`, `scale`, `root` | Create a polyrhythm — N notes evenly spaced across M beats. |
| `mcp_opendaw_create_melody` |  | `scale`, `root`, `pattern`, `unit_index`, `track_index`, `start_beat`, `octave`, `velocity` | Create a melody from a scale and rhythmic pattern — one call instead of 10-30 create_note calls. |
| `mcp_opendaw_create_melody_from_progression` |  | `progression`, `pattern`, `bars_per_chord`, `octave`, `velocity`, `unit_index`, `track_index`, `start_beat` | Create a lead melody from a chord progression string. |
| `mcp_opendaw_create_metal_arrangement` |  | `bpm`, `bars`, `root`, `octave`, `unit_index`, `drum_track`, `bass_track`, `chord_track`, `lead_track`, `start_beat`, `velocity` | Create a full metal arrangement — double kick drums + palm-muted riffs + power chords + shred lead. |
| `mcp_opendaw_create_metric_modulation` |  | `position_beats`, `old_note`, `new_note`, `old_bpm`, `ratio`, `add_time_signature` | Create a metric modulation — tempo change that preserves a note-value equivalence. |
| `mcp_opendaw_create_midi_echo` |  | `unit_index`, `track_index`, `region_index`, `repeats`, `delay_beats`, `velocity_decay`, `pitch_shift`, `dest_track`, `feedback_mode` | Create MIDI echo — repeat notes with decaying velocity and optional pitch shift. |
| `mcp_opendaw_create_modulated_song` |  | `sections`, `arp_pattern`, `bass_pattern`, `melody_pattern`, `counter_melody_pattern`, `unit_index`, `velocity`, `drum_genre`, `bpm` | Build a multi-section song with key modulation between sections — one call. |
| `mcp_opendaw_create_montuno` |  | `root`, `scale`, `bars`, `octave`, `chord_prog`, `pattern`, `rhythm`, `velocity`, `accent_beats`, `unit_index`, `track_index`, `start_beat` | Create a montuno — a repeating Latin/jazz piano ostinato pattern. |
| `mcp_opendaw_create_mordent` |  | `main_pitch`, `direction`, `interval`, `duration_beats`, `velocity`, `unit_index`, `track_index`, `start_beat` | Create a mordent — main note → neighbor → back. A classical ornament. |
| `mcp_opendaw_create_motif_development` |  | `motif`, `scale`, `root`, `octave`, `steps`, `step_duration`, `velocity`, `unit_index`, `track_index`, `start_beat` | Develop a motif into a through-composed melodic line that evolves. |
| `mcp_opendaw_create_motif_variations` |  | `source_unit`, `source_track`, `source_region`, `start_note`, `note_count`, `target_unit`, `target_track`, `target_region`, `variation_type`, `sequence_shift`, `augmentation_factor`, `fragment_count` | Extract a motif from existing notes and create a variation in a new region. |
| `mcp_opendaw_create_mute_automation` |  | `unit_index`, `events` | Create timed mute/unmute automation events on an audio unit. |
| `mcp_opendaw_create_neurofunk_arrangement` |  | `bpm`, `bars`, `root`, `octave`, `unit_index`, `drum_track`, `bass_track`, `reese_track`, `stabs_track`, `start_beat`, `velocity` | Create a full neurofunk DnB arrangement — 4 tracks: drums + sub-bass + Reese + stabs. |
| `mcp_opendaw_create_note` |  | `track_index`, `pitch`, `start_beat`, `duration_beats`, `velocity`, `unit_index` | Create a MIDI note on a note track. |
| `mcp_opendaw_create_note_clip` |  | `unit_index`, `track_index`, `clip_index`, `name`, `hue` | Create a note clip in the session view (clip launcher). |
| `mcp_opendaw_create_note_track` |  | `unit_index` | Create a new note/MIDI track on an audio unit. |
| `mcp_opendaw_create_notes_batch` |  | `notes`, `unit_index`, `track_index` | Create multiple MIDI notes in a single call — batch creation for melodies, chords, arpeggios. |
| `mcp_opendaw_create_ostinato` |  | `scale`, `root`, `pattern`, `unit_index`, `track_index`, `start_beat`, `repeats`, `octave`, `velocity` | Create an ostinato — a repeating melodic/rhythmic pattern as a foundation layer. |
| `mcp_opendaw_create_outro` |  | `outro_type`, `key_root`, `scale_type`, `octave`, `bars`, `velocity`, `unit_index`, `track_index`, `start_beat`, `seed` | Create an outro section — the closing that resolves the song. |
| `mcp_opendaw_create_pan_sweep` |  | `unit_index`, `start_beat`, `duration_beats`, `start_pan`, `end_pan`, `curve`, `steps` | Create a panning automation sweep — move signal from left to right (or vice versa) over time. |
| `mcp_opendaw_create_passacaglia` |  | `bass_pattern`, `bass_rhythm`, `bass_repeats`, `chord_pattern`, `chord_octave`, `variation_style`, `beats_per_bar`, `bass_velocity`, `chord_velocity`, `unit_index`, `track_index`, `start_beat` | Create a passacaglia — repeating bass ostinato with evolving harmonies above. |
| `mcp_opendaw_create_pedal_point` |  | `pedal_pitch`, `chord_pattern`, `bars_per_chord`, `beats_per_bar`, `pedal_velocity`, `chord_velocity`, `chord_octave`, `retrigger_pedal`, `unit_index`, `track_index`, `start_beat` | Create a pedal point — sustained bass tone under changing chords. |
| `mcp_opendaw_create_phase` |  | `pattern`, `voices`, `phase_rate`, `phase_direction`, `phase_amount`, `step_duration`, `repeats`, `unit_index`, `track_index`, `start_beat`, `velocity`, `velocity_decay` | Create a Steve Reich-style phase shifting pattern. |
| `mcp_opendaw_create_phase_shift` |  | `unit_index`, `track_index`, `region_index`, `shift_per_bar`, `bars`, `direction`, `cross_track`, `velocity_scale` | Create a phase-shifted copy of a region — Steve Reich phasing. |
| `mcp_opendaw_create_phonk_arrangement` |  | `bpm`, `bars`, `root`, `octave`, `unit_index`, `drum_track`, `bass_track`, `cowbell_track`, `start_beat`, `velocity` | Create a full drift phonk arrangement — 3 tracks: drums + 808 + cowbell lead. |
| `mcp_opendaw_create_pitch_stretched_clip` |  | `sample_id`, `unit_index`, `clip_index`, `track_index`, `bpm` | Create a pitch-stretched audio clip in session view. |
| `mcp_opendaw_create_pitch_stretched_region` |  | `sample_id`, `unit_index`, `start_beat`, `track_index`, `bpm` | Place a pitch-stretched audio region on a track. |
| `mcp_opendaw_create_playfield_sample` |  | `midi_note`, `sample_name`, `duration_seconds`, `unit_index` | Add a drum pad to a Playfield drum machine. |
| `mcp_opendaw_create_polyrhythm` |  | `primary_count`, `secondary_count`, `bars`, `unit_index`, `track_index`, `start_beat`, `primary_pitch`, `secondary_pitch`, `primary_velocity`, `secondary_velocity`, `duration` | Create a polyrhythm — two rhythmic streams with different subdivision counts playing simultaneously. |
| `mcp_opendaw_create_pop_arrangement` |  | `bpm`, `bars`, `root`, `octave`, `unit_index`, `drum_track`, `bass_track`, `chord_track`, `melody_track`, `start_beat`, `velocity` | Create a full pop arrangement with verse-chorus-bridge song structure across 4 tracks. |
| `mcp_opendaw_create_prechorus` |  | `prechorus_type`, `key_root`, `scale_type`, `octave`, `bars`, `velocity`, `unit_index`, `track_index`, `start_beat`, `seed` | Create a pre-chorus — the tension builder before the chorus hits. |
| `mcp_opendaw_create_progression_from_key` |  | `key`, `mode`, `style`, `unit_index`, `track_index`, `start_beat`, `chord_duration` | Auto-generate a diatonic chord progression from a detected key — no manual chord typing. |
| `mcp_opendaw_create_psytrance_arrangement` |  | `key_root`, `bpm`, `bars`, `velocity`, `unit_index`, `track_index`, `start_beat` | Create a psytrance arrangement — 145 BPM hypnotic Goa/psychedelic. |
| `mcp_opendaw_create_random_walk_melody` |  | `root`, `scale`, `bars`, `octave`, `max_step`, `direction_bias`, `duration`, `duration_variation`, `rest_probability`, `velocity`, `velocity_variation`, `boundary_behavior`, `seed`, `unit_index`, `track_index`, `start_beat` | Create a melody using a random walk through a scale — stochastic generation. |
| `mcp_opendaw_create_ratchet` |  | `unit_index`, `track_index`, `pitch`, `start_beat`, `length_beats`, `subdivisions`, `max_subdivisions`, `velocity`, `velocity_decay`, `pitch_drift`, `region_index` | Create a ratchet — repeated notes with changing subdivision rate. |
| `mcp_opendaw_create_reggae_arrangement` |  | `bpm`, `bars`, `root`, `octave`, `unit_index`, `drum_track`, `bass_track`, `guitar_track`, `keys_track`, `start_beat`, `velocity` | Create a full reggae arrangement — one-drop drums + melodic bass + skank guitar + organ across 4 tracks. |
| `mcp_opendaw_create_reggae_percussion` |  | `style`, `bars`, `tempo_bpm`, `velocity`, `swing`, `unit_index`, `track_index`, `start_beat` | Create Jamaican reggae percussion patterns across 6 styles. |
| `mcp_opendaw_create_riff` |  | `riff_type`, `key_root`, `scale_type`, `bars`, `octave`, `velocity`, `unit_index`, `track_index`, `start_beat`, `seed` | Create a genre-specific riff — catchy repeated melodic fragment. |
| `mcp_opendaw_create_riser` |  | `unit_index`, `track_index`, `start_beat`, `length_beats`, `start_pitch`, `end_pitch`, `steps`, `curve`, `velocity` | Create a riser — ascending pitch sweep for build-up transitions. |
| `mcp_opendaw_create_rnb_arrangement` |  | `bpm`, `bars`, `root`, `octave`, `unit_index`, `drum_track`, `bass_track`, `chord_track`, `lead_track`, `start_beat`, `velocity` | Create a full modern R&B arrangement — trap-influenced drums + deep sub bass + extended chords + vocal-style lead. |
| `mcp_opendaw_create_rock_arrangement` |  | `bpm`, `bars`, `root`, `octave`, `unit_index`, `drum_track`, `bass_track`, `guitar_track`, `keys_track`, `start_beat`, `velocity` | Create a full rock arrangement — rock beat drums + bass + power chords + riff across 4 tracks. |
| `mcp_opendaw_create_rondo` |  | `key_root`, `scale_name`, `form_type`, `bars_per_section`, `tempo_bpm`, `velocity`, `unit_index`, `track_index`, `start_beat` | Create a rondo — recurring theme alternating with contrasting episodes. |
| `mcp_opendaw_create_samba_pattern` |  | `bars`, `style`, `velocity`, `unit_index`, `track_index`, `start_beat`, `surdo_pitch`, `caixa_pitch`, `tamborim_pitch`, `chocalho_pitch`, `repique_pitch` | Create a Brazilian samba percussion ensemble pattern — multi-instrument layered groove. |
| `mcp_opendaw_create_scale_run` |  | `scale`, `root`, `direction`, `octaves`, `unit_index`, `track_index`, `start_beat`, `step_duration`, `velocity`, `octave` | Create a scale run — ascending or descending scale sequence for fills and transitions. |
| `mcp_opendaw_create_second_line` |  | `bars`, `style`, `velocity`, `unit_index`, `track_index`, `start_beat`, `bass_pitch`, `snare_pitch`, `hi_hat_pitch`, `tom_pitch`, `cymbal_pitch` | Create a New Orleans second line percussion ensemble — street parade groove. |
| `mcp_opendaw_create_section_transition` |  | `transition_type`, `start_beat`, `duration_beats`, `unit_indices` | Create a complete section transition in one call — combines multiple automation tools. |
| `mcp_opendaw_create_send` |  | `src_unit`, `name`, `send_level_db`, `routing` | Create a parallel FX send bus from an audio unit. |
| `mcp_opendaw_create_sequence` |  | `pattern`, `transposition`, `repeats`, `direction`, `segment_beats`, `velocity_decay`, `unit_index`, `track_index`, `start_beat`, `velocity` | Create a melodic sequence — repeat a pattern at transposed pitch levels. |
| `mcp_opendaw_create_soli` |  | `melody_pattern`, `rhythm_pattern`, `key_root`, `scale_name`, `voices`, `octave_spread`, `velocity`, `unit_index`, `track_index`, `start_beat` | Create a soli — ensemble unison passage with octave doublings. |
| `mcp_opendaw_create_solo` |  | `solo_type`, `key_root`, `scale_type`, `bars`, `octave`, `velocity`, `unit_index`, `track_index`, `start_beat`, `seed` | Create a genre-specific melodic solo over a chord progression. |
| `mcp_opendaw_create_solo_automation` |  | `solo_track`, `total_tracks`, `start_beat`, `end_beat`, `unit_indices` | Mute all tracks except the solo track for a beat range, then restore. |
| `mcp_opendaw_create_sonata_form` |  | `key_root`, `scale_name`, `exposition_bars`, `development_bars`, `recap_bars`, `velocity`, `unit_index`, `track_index`, `start_beat` | Create sonata form — exposition, development, recapitulation. |
| `mcp_opendaw_create_song_structure` |  | `sections`, `unit_index` | Create song structure markers for arrangement (intro/verse/chorus/bridge/outro). |
| `mcp_opendaw_create_song_with_variations` |  | `genre`, `sections`, `bpm`, `root`, `unit_index`, `drum_track`, `bass_track`, `harmony_track`, `melody_track`, `apply_mix`, `apply_humanize`, `apply_master` | Build a complete song with real musical variations between sections — one call. |
| `mcp_opendaw_create_songo_pattern` |  | `bars`, `variation`, `velocity`, `unit_index`, `track_index`, `start_beat`, `kick_pitch`, `snare_pitch`, `hh_pitch`, `tom_pitch` | Create a songo drum pattern — the Cuban drum-kit fusion that revolutionized Latin music. |
| `mcp_opendaw_create_soul_arrangement` |  | `bpm`, `bars`, `root`, `octave`, `unit_index`, `drum_track`, `bass_track`, `keys_track`, `horns_track`, `start_beat`, `velocity` | Create a full soul arrangement — gospel drums + melodic bass + Rhodes chords + horn stabs across 4 tracks. |
| `mcp_opendaw_create_stab` |  | `chords`, `rhythm`, `unit_index`, `track_index`, `start_beat`, `octave`, `velocity`, `length_beats`, `stab_duration` | Create rhythmic stabs — short chord jabs that define house, disco, funk. |
| `mcp_opendaw_create_stutter` |  | `pitches`, `rate`, `pattern`, `repeat_count`, `accent_pattern`, `velocity_ramp`, `gate`, `pitch_jitter`, `unit_index`, `track_index`, `start_beat`, `velocity`, `seed` | Create a stutter edit — rapid rhythmic repetitions with evolving rate and dynamics. |
| `mcp_opendaw_create_synth_track` |  | `name`, `synth_type` | Create a new instrument audio unit with a synthesizer device and a note track. |
| `mcp_opendaw_create_synthwave_arrangement` |  | `bpm`, `bars`, `root`, `octave`, `unit_index`, `drum_track`, `bass_track`, `pad_track`, `lead_track`, `start_beat`, `velocity` | Create a full synthwave arrangement — retro drums + arpeggiated bass + dreamy pads + nostalgic lead across 4 tracks. |
| `mcp_opendaw_create_taiko_ensemble` |  | `bars`, `style`, `velocity`, `unit_index`, `track_index`, `start_beat`, `odaiko_pitch`, `chu_daiko_pitch`, `shime_pitch`, `atarigane_pitch` | Create a Japanese taiko ensemble — kumi-daiko group drumming with dramatic dynamics. |
| `mcp_opendaw_create_tala` |  | `tala_name`, `cycles`, `laya`, `velocity`, `unit_index`, `track_index`, `start_beat` | Create an Indian classical tala — cyclic rhythmic structure with vibhag sections and tali/khali markings. |
| `mcp_opendaw_create_techno_arrangement` |  | `bpm`, `bars`, `root`, `octave`, `unit_index`, `drum_track`, `bass_track`, `stab_track`, `start_beat`, `velocity` | Create a full techno arrangement — drums + sub-bass drone + percussive stabs across 3 tracks. |
| `mcp_opendaw_create_tempo_ramp` |  | `start_beat`, `end_beat`, `start_bpm`, `end_bpm`, `curve`, `steps` | Create a smooth tempo ramp (ritardando or accelerando) across a beat range. |
| `mcp_opendaw_create_ternary_form` |  | `key_root`, `scale_name`, `a_bars`, `b_bars`, `a_prime_ornamented`, `b_contrast`, `velocity`, `unit_index`, `track_index`, `start_beat` | Create ternary form — ABA with contrasting middle section. |
| `mcp_opendaw_create_time_stretched_clip` |  | `sample_id`, `unit_index`, `clip_index`, `track_index`, `bpm`, `playback_rate`, `transient_mode` | Create a time-stretched audio clip in session view. |
| `mcp_opendaw_create_time_stretched_region` |  | `sample_id`, `unit_index`, `start_beat`, `track_index`, `playback_rate`, `transient_mode`, `bpm` | Place a time-stretched audio region on a track. |
| `mcp_opendaw_create_track_region` |  | `unit_index`, `track_index`, `start_beat`, `duration_beats`, `name`, `hue` | Create a region on any track (note or value) using the generic createTrackRegion API. |
| `mcp_opendaw_create_trade_solos` |  | `key_root`, `scale_type`, `octave`, `bars`, `trade_length`, `velocity`, `unit_index`, `track_index_a`, `track_index_b`, `start_beat`, `seed` | Create trade solos — two instruments trading phrases back and forth. |
| `mcp_opendaw_create_trance_arrangement` |  | `bpm`, `bars`, `root`, `octave`, `unit_index`, `drum_track`, `bass_track`, `arp_track`, `lead_track`, `start_beat`, `velocity` | Create a full trance arrangement — driving drums + rolling bass + supersaw arp + pluck lead across 4 tracks. |
| `mcp_opendaw_create_transition` |  | `transition_type`, `key_root`, `scale_type`, `octave`, `bars`, `velocity`, `direction`, `interval`, `unit_index`, `track_index`, `start_beat`, `seed` | Create a transition — a passage that moves between two sections. |
| `mcp_opendaw_create_trap_arrangement` |  | `bpm`, `bars`, `root`, `octave`, `unit_index`, `drum_track`, `bass_track`, `melody_track`, `start_beat`, `velocity` | Create a full trap arrangement — drums + 808 bass + bell melody across 3 tracks in one call. |
| `mcp_opendaw_create_trap_rolls` |  | `roll_type`, `bars`, `unit_index`, `track_index`, `start_beat`, `kick_pitch`, `snare_pitch`, `hat_pitch`, `velocity` | Create trap hi-hat roll patterns — the evolving density technique that defines modern trap. |
| `mcp_opendaw_create_trill` |  | `lower_pitch`, `upper_pitch`, `rate`, `duration_beats`, `accent_upper`, `start_with_upper`, `velocity`, `unit_index`, `track_index`, `start_beat` | Create a trill — rapid alternation between two notes. |
| `mcp_opendaw_create_tumbao` |  | `tumbao_type`, `bars`, `unit_index`, `track_index`, `start_beat`, `low_pitch`, `open_pitch`, `slap_pitch`, `velocity` | Create an Afro-Cuban tumbao (conga) pattern — the rhythmic foundation of salsa. |
| `mcp_opendaw_create_tuplet_group` |  | `root`, `scale`, `tuplet_number`, `span_beats`, `base_division`, `repeats`, `octave`, `pitch_mode`, `rest_positions`, `velocity`, `accent_first`, `unit_index`, `track_index`, `start_beat` | Create a tuplet group — irrational rhythm subdivision within a time span. |
| `mcp_opendaw_create_turn` |  | `main_pitch`, `direction`, `interval`, `duration_beats`, `velocity`, `unit_index`, `track_index`, `start_beat` | Create a turn — circular ornament: main → neighbor → main → other neighbor → main. |
| `mcp_opendaw_create_turnaround` |  | `turnaround_type`, `key_root`, `scale_type`, `octave`, `velocity`, `unit_index`, `track_index`, `start_beat`, `seed` | Create a turnaround — a 2-bar phrase that resolves a section back to tonic. |
| `mcp_opendaw_create_two_hand_piano` |  | `chords`, `left_hand`, `right_hand`, `melody_pitches`, `bass_octave`, `chord_octave`, `melody_octave`, `chord_duration`, `arpeggio_rate`, `unit_index`, `track_index`, `start_beat`, `velocity` | Create a two-hand piano arrangement — left hand accompaniment + right hand melody. |
| `mcp_opendaw_create_value_clip` |  | `unit_index`, `track_index`, `name`, `clip_index` | Create a value clip (automation clip) on an automation track in session view. |
| `mcp_opendaw_create_variations` |  | `source_unit`, `source_track`, `source_region`, `variations`, `target_unit`, `target_track`, `start_beat`, `spacing_beats` | Create thematic variations from an existing note region. |
| `mcp_opendaw_create_verse` |  | `verse_type`, `key_root`, `scale_type`, `octave`, `bars`, `velocity`, `unit_index`, `track_index`, `start_beat`, `seed` | Create a verse — the storytelling section of a song. |
| `mcp_opendaw_create_voice_exchange` |  | `unit_index`, `source_track`, `source_region`, `target_track`, `target_region`, `exchange_mode`, `interval`, `transpose`, `time_offset`, `duration_factor`, `velocity_factor`, `swap` | Create a voice exchange — imitative counterpoint where motifs pass between voices. |
| `mcp_opendaw_create_voice_led_progression` |  | `progression`, `bars_per_chord`, `octave`, `velocity`, `unit_index`, `track_index`, `start_beat`, `note_duration`, `voice_range` | Create chord pads with smooth voice leading — minimal movement between chords. |
| `mcp_opendaw_create_volume_fade` |  | `unit_index`, `direction`, `start_beat`, `duration_beats`, `start_volume_db`, `end_volume_db`, `curve`, `steps` | Create a volume fade automation on an audio unit — fade in or fade out. |
| `mcp_opendaw_create_walking_bass` |  | `chords`, `unit_index`, `track_index`, `start_beat`, `octave`, `velocity`, `bars_per_chord` | Create a walking bass line over a chord progression. |
| `mcp_opendaw_create_warp_marker` |  | `unit_index`, `track_index`, `region_index`, `position_beats`, `seconds` | Add a warp marker to a time-stretched or pitch-stretched audio region. |
| `mcp_opendaw_import_audio_to_tracks` |  | `file_path`, `mode`, `start_beat`, `bpm` | Import an audio file into the DAW, optionally split into stems on separate tracks. |
| `mcp_opendaw_import_dawproject` |  | `filename` | Import a .dawproject file into the current session. |
| `mcp_opendaw_import_midi` |  | `file_path`, `unit_index`, `track_index`, `offset_beats` | Import a MIDI file and create note events on a note track. |
| `mcp_opendaw_import_preset` |  | `preset_b64` | Import a preset (base64-encoded binary) as a new audio unit. |
| `mcp_opendaw_load_audio` |  | `file_path`, `name` | Load an audio file (WAV/MP3/FLAC/OGG) into the DAW project. |
| `mcp_opendaw_load_effect_preset` |  | `filepath`, `unit_index` | Load a .opb preset file into the DAW and apply it to an audio unit. |
| `mcp_opendaw_load_project` |  | `filename` | Load a previously saved project from a .odaw file. |
| `mcp_opendaw_place_audio_region` |  | `sample_id`, `unit_index`, `start_beat`, `track_index` | Place a previously loaded audio sample as a region on a track. |
| `mcp_opendaw_set_articulation` |  | `unit_index`, `track_index`, `region_index`, `articulation`, `staccato_ratio`, `micro_gap` | Set articulation for notes — legato, staccato, or tenuto. |
| `mcp_opendaw_set_audio_region_fade` |  | `unit_index`, `track_index`, `region_index`, `fade_in`, `fade_out`, `in_slope`, `out_slope` | Set fade in/out on an audio region. |
| `mcp_opendaw_set_audio_region_gain` |  | `unit_index`, `track_index`, `region_index`, `gain_db` | Set gain (in dB) on an audio region. |
| `mcp_opendaw_set_audio_region_time_base` |  | `unit_index`, `track_index`, `region_index`, `time_base` | Set the time base of an audio region. |
| `mcp_opendaw_set_audio_region_waveform_offset` |  | `unit_index`, `track_index`, `region_index`, `offset` | Set the waveform display offset of an audio region. |
| `mcp_opendaw_set_automation_interpolation` |  | `unit_index`, `track_index`, `region_index`, `event_index`, `interpolation`, `curve_slope` | Set the interpolation type of an existing automation event. |
| `mcp_opendaw_set_bpm` |  | `bpm` | Set the project tempo in BPM. |
| `mcp_opendaw_set_bus_color` |  | `bus_index`, `hue` | Set the color (hue 0-360) of an audio bus. |
| `mcp_opendaw_set_bus_enabled` |  | `bus_index`, `enabled` | Enable or mute an audio bus (FX bus A/B comparison). |
| `mcp_opendaw_set_bus_label` |  | `bus_index`, `label` | Set the label (name) of an audio bus. |
| `mcp_opendaw_set_clip_hue` |  | `unit_index`, `track_index`, `clip_index`, `hue` | Set the color (hue) of a clip in the session view. |
| `mcp_opendaw_set_clip_label` |  | `unit_index`, `track_index`, `clip_index`, `label` | Set the label (name) of a clip in the session view. |
| `mcp_opendaw_set_clip_mute` |  | `unit_index`, `track_index`, `clip_index`, `mute` | Mute or unmute a clip in the session view. |
| `mcp_opendaw_set_clip_playback` |  | `unit_index`, `track_index`, `clip_index`, `loop`, `reverse`, `speed` | Set clip playback parameters (loop, reverse, speed) on a clip. |
| `mcp_opendaw_set_clip_properties` |  | `unit_index`, `track_index`, `clip_index`, `label`, `hue`, `mute`, `duration_beats` | Set properties on a clip (session view): label, color, mute, duration. |
| `mcp_opendaw_set_crusher_bits` |  | `unit_index`, `effect_index`, `bits` | Set the bit depth on a Crusher (bitcrusher) effect. |
| `mcp_opendaw_set_crusher_crush` |  | `unit_index`, `effect_index`, `crush` | Set the sample-rate reduction (crush) on a Crusher effect. |
| `mcp_opendaw_set_delay_sync` |  | `unit_index`, `effect_index`, `fraction` | Set the synced delay time on a Delay effect using a musical fraction string. |
| `mcp_opendaw_set_device_label` |  | `unit_index`, `effect_index`, `label`, `is_midi_effect` | Rename an effect or MIDI effect device. |
| `mcp_opendaw_set_effect_enabled` |  | `unit_index`, `effect_index`, `enabled` | Enable or bypass an specific effect on an audio unit. |
| `mcp_opendaw_set_effect_parameter` |  | `unit_index`, `effect_index`, `parameter_name`, `value` | Set a parameter on an audio effect. |
| `mcp_opendaw_set_effect_parameter_bool` |  | `unit_index`, `effect_index`, `parameter_name`, `value` | Set a boolean parameter on an audio effect. |
| `mcp_opendaw_set_effect_parameter_int` |  | `unit_index`, `effect_index`, `parameter_name`, `value` | Set an integer parameter on an audio effect. |
| `mcp_opendaw_set_effect_parameter_string` |  | `unit_index`, `effect_index`, `parameter_name`, `string_value` | Set a string parameter on an audio effect (e.g. Waveshaper equation). |
| `mcp_opendaw_set_fold_oversampling` |  | `unit_index`, `effect_index`, `oversampling` | Set the oversampling level on a Fold (wavefolding) effect. |
| `mcp_opendaw_set_groove_shuffle` |  | `amount` | Set the groove/shuffle (swing) amount for the project. |
| `mcp_opendaw_set_instrument_param` |  | `unit_index`, `param_name`, `value`, `param_index` | Set a parameter on the instrument connected to an audio unit. |
| `mcp_opendaw_set_loop_region` |  | `from_beat`, `to_beat`, `enabled` | Set the playback loop region. |
| `mcp_opendaw_set_marker_label` |  | `marker_index`, `label` | Rename a timeline marker. |
| `mcp_opendaw_set_marker_position` |  | `marker_index`, `position_beats` | Move a timeline marker to a new position. |
| `mcp_opendaw_set_marker_repeat` |  | `marker_index`, `repeat_count` | Set the repeat count on a timeline marker. |
| `mcp_opendaw_set_metronome` |  | `enabled`, `gain`, `beat_subdivision` | Configure the metronome settings. |
| `mcp_opendaw_set_midi_effect_param` |  | `unit_index`, `effect_index`, `param_name`, `value`, `param_index` | Set a parameter on a MIDI effect. |
| `mcp_opendaw_set_modular_module_param` |  | `au_index`, `effect_index`, `module_index`, `param_name`, `value` | Set a parameter on a module in a Modular device. |
| `mcp_opendaw_set_neuralamp_model` |  | `unit_index`, `effect_index`, `model_json`, `label`, `pack_id` | Load a Neural Amp Modeler (NAM/Tone3000) model JSON into a NeuralAmp effect. |
| `mcp_opendaw_set_note_advanced` |  | `unit_index`, `track_index`, `region_index`, `note_index`, `chance`, `cent`, `play_count`, `play_curve` | Set advanced note properties — chance, cent, playCount, playCurve. |
| `mcp_opendaw_set_note_cents` |  | `unit_index`, `track_index`, `region_index`, `cents`, `mode`, `target_pitch`, `beat_positions`, `note_indices`, `direction`, `scale`, `root_note` | Set detune (cents) on notes — deterministic microtonal pitch control. |
| `mcp_opendaw_set_note_properties` |  | `note_index`, `unit_index`, `track_index`, `region_index`, `position_beats`, `duration_beats`, `pitch`, `velocity`, `cent`, `chance` | Edit properties of a single note within a region. |
| `mcp_opendaw_set_piano_keyboard` |  | `keyboard_type` | Set the piano roll keyboard type. |
| `mcp_opendaw_set_piano_note_labels` |  | `show` | Toggle note labels (C, C#, D, etc.) in the piano roll. |
| `mcp_opendaw_set_piano_note_scale` |  | `scale` | Set the piano roll note scale (vertical zoom). |
| `mcp_opendaw_set_piano_time_range` |  | `quarters` | Set the piano roll time range (horizontal view width in quarter notes). |
| `mcp_opendaw_set_playfield_sample_enabled` |  | `sample_index`, `enabled`, `unit_index` | Enable/disable a drum pad on a Playfield drum machine. |
| `mcp_opendaw_set_position` |  | `position` | Set the playback position in beats. |
| `mcp_opendaw_set_region_color` |  | `track_index`, `region_index`, `hue`, `unit_index` | Set the color (hue) of a region or clip. |
| `mcp_opendaw_set_region_duration` |  | `track_index`, `region_index`, `duration_beats`, `unit_index` | Set the duration of a region. |
| `mcp_opendaw_set_region_label` |  | `track_index`, `region_index`, `label`, `unit_index` | Rename a region's label (display name). |
| `mcp_opendaw_set_region_loop` |  | `track_index`, `region_index`, `loop_beats`, `loop_offset_beats`, `event_offset_beats`, `unit_index` | Set loop parameters for a note region. |
| `mcp_opendaw_set_region_mute` |  | `track_index`, `region_index`, `mute`, `unit_index` | Mute or unmute a specific region without deleting it. |
| `mcp_opendaw_set_region_position` |  | `track_index`, `region_index`, `position_beats`, `unit_index`, `region_type` | Move a region to a new position on the timeline. |
| `mcp_opendaw_set_revamp_filter` |  | `unit_index`, `effect_index`, `section`, `enabled`, `frequency`, `gain`, `q`, `order` | Configure a filter section on a Revamp (parametric EQ) effect. |
| `mcp_opendaw_set_script_device_code` |  | `device_type`, `unit_index`, `device_index`, `code` | Set the user JavaScript code on a scriptable device (Apparat/Werkstatt/Spielwerk). |
| `mcp_opendaw_set_script_param` |  | `device_type`, `unit_index`, `device_index`, `param_label`, `value` | Set a parameter value on a scriptable device by label. |
| `mcp_opendaw_set_send_level` |  | `src_unit`, `send_index`, `level_db` | Set the send level for an existing aux send. |
| `mcp_opendaw_set_send_pan` |  | `unit_index`, `send_index`, `pan` | Set the stereo pan for an aux send (-1.0 = full left, 0.0 = center, 1.0 = full right). |
| `mcp_opendaw_set_send_routing` |  | `unit_index`, `send_index`, `routing` | Set the routing mode for an aux send (pre-fader or post-fader). |
| `mcp_opendaw_set_stereo_tool_panning` |  | `unit_index`, `effect_index`, `panning_mixing` | Set the panning mixing mode on a StereoTool effect. |
| `mcp_opendaw_set_studio_setting` |  | `category`, `key`, `value` | Set a studio preference setting. |
| `mcp_opendaw_set_tidal_rate` |  | `unit_index`, `effect_index`, `rate` | Set the LFO rate on a Tidal effect using a musical fraction string. |
| `mcp_opendaw_set_time_signature` |  | `numerator`, `denominator` | Set the project time signature (e.g. 4/4, 3/4, 6/8, 7/8). |
| `mcp_opendaw_set_time_stretch_cents` |  | `unit_index`, `track_index`, `region_index`, `cents` | Set the pitch shift (in cents) on a time-stretched audio region. |
| `mcp_opendaw_set_track_enabled` |  | `unit_index`, `track_index`, `enabled` | Enable or disable a track (equivalent to track mute in the UI). |
| `mcp_opendaw_set_track_mute` |  | `unit_index`, `mute` | Mute or unmute an audio unit. |
| `mcp_opendaw_set_track_panning` |  | `unit_index`, `panning` | Set panning of an audio unit. -1.0 = full left, 0.0 = center, 1.0 = full right. |
| `mcp_opendaw_set_track_solo` |  | `unit_index`, `solo` | Solo or unsolo an audio unit. |
| `mcp_opendaw_set_track_volume` |  | `unit_index`, `volume_db` | Set volume of an audio unit in dB. |
| `mcp_opendaw_set_transpose` |  | `semitones` | Set global transpose for the piano roll view (does not affect audio playback). |
| `mcp_opendaw_set_tuning` |  | `frequency` | Set the A4 base frequency (concert pitch tuning). |
| `mcp_opendaw_set_unit_minimized` |  | `unit_index`, `minimized` | Minimize or expand an audio unit in the mixer view. |
| `mcp_opendaw_set_vaporisateur_osc_param` |  | `osc_index`, `param_name`, `value`, `unit_index` | Set a parameter on a Vaporisateur oscillator. |
| `mcp_opendaw_set_vocoder_band_count` |  | `unit_index`, `effect_index`, `band_count` | Set the band count on a Vocoder effect (number of filter bands, typically 8-32). |
| `mcp_opendaw_set_vocoder_modulator_source` |  | `unit_index`, `effect_index`, `source` | Set the modulator source on a Vocoder effect. |
| `mcp_opendaw_set_waveshaper_equation` |  | `unit_index`, `effect_index`, `equation` | Set the transfer function equation on a Waveshaper effect. |

## Destructive

| Tool | Annotation | Parameters | Description |
|---|---|---|---|
| `mcp_opendaw_clear_region_notes` | `destructive` | `unit_index`, `track_index`, `region_index` | Clear all notes from a region while keeping the region on the timeline. |
| `mcp_opendaw_delete_audio_region` | `destructive` | `unit_index`, `track_index`, `region_index` | Delete an audio region from the timeline. |
| `mcp_opendaw_delete_audio_unit` | `destructive` | `unit_index` | Delete an entire audio unit with all its tracks, effects, and sends. |
| `mcp_opendaw_delete_automation_event` | `destructive` | `unit_index`, `track_index`, `event_index` | Delete a single automation event (ValueEventBox) from an automation track. |
| `mcp_opendaw_delete_clip` | `destructive` | `unit_index`, `track_index`, `clip_index` | Delete a clip from a track (session view). |
| `mcp_opendaw_delete_marker` | `destructive` | `marker_index` | Delete a timeline marker by index. |
| `mcp_opendaw_delete_note` | `destructive` | `note_index`, `unit_index`, `track_index`, `region_index` | Delete a single note from a region. |
| `mcp_opendaw_delete_note_region` | `destructive` | `unit_index`, `track_index`, `region_index` | Delete a note region from the timeline. |
| `mcp_opendaw_delete_region` | `destructive` | `track_index`, `region_index`, `unit_index`, `region_type` | Delete a region from a track. |
| `mcp_opendaw_delete_section` | `destructive` | `from_beat`, `to_beat`, `unit_indices` | Delete all regions within a beat range across all tracks. |
| `mcp_opendaw_delete_signature_change` | `destructive` | `position_beats`, `index` | Delete a time signature change from the timeline. |
| `mcp_opendaw_delete_track` | `destructive` | `unit_index`, `track_index` | Delete a track from an audio unit. Removes all regions, clips, and notes on that track. |
| `mcp_opendaw_delete_warp_marker` | `destructive` | `unit_index`, `track_index`, `region_index`, `marker_index` | Delete a warp marker from a time-stretched or pitch-stretched audio region. |
| `mcp_opendaw_reset_playfield_params` | `destructive` | `unit_index`, `sample_index` | Reset all parameters of a Playfield drum sample to defaults. |
| `mcp_opendaw_reset_project` | `destructive` | — | Reset the project to a fresh state — removes all audio units, tracks, regions, effects. |

## Other

| Tool | Annotation | Parameters | Description |
|---|---|---|---|
| `mcp_opendaw_accent_beats` |  | `unit_index`, `track_index`, `accent_pattern`, `strong_velocity`, `medium_velocity`, `weak_velocity`, `region_index` | Apply beat-aware velocity accents to notes based on their position. |
| `mcp_opendaw_arrange_full_song` |  | `structure`, `key_root`, `scale_type`, `octave`, `velocity`, `intro_type`, `prechorus_type`, `bridge_type`, `outro_type`, `interlude_type`, `transition_type`, `coda_type`, `seed` | Arrange a complete song from structural sections in one call. |
| `mcp_opendaw_augment_notes` |  | `factor`, `unit_index`, `track_index`, `region_index`, `mode` | Augment or diminish note durations — the fourth classical transformation. |
| `mcp_opendaw_auto_gain` |  | `target_lufs`, `filename`, `sample_rate`, `max_iterations` | Auto-adjust output volume to hit a target LUFS. |
| `mcp_opendaw_auto_master` |  | `target_lufs`, `platform`, `style`, `ceiling_dbtp` | Adaptive mastering — analyze, correct, and master in one call. |
| `mcp_opendaw_automation_sweep` |  | `unit_index`, `parameter_name`, `start_beat`, `end_beat`, `start_value`, `end_value`, `steps`, `curve` | Create a smooth automation sweep (ramp) between two values over a beat range. |
| `mcp_opendaw_balance_track_velocities` |  | `unit_index`, `track_indices`, `preset`, `target_velocities`, `region_index` | Balance velocities across multiple tracks — MIDI mix leveling. |
| `mcp_opendaw_batch_diagnostic` |  | `filenames`, `genre` | Run full diagnostic on multiple stems in one call — problems + phase + profile comparison. |
| `mcp_opendaw_capture_realtime` |  | `duration_seconds`, `filename` | Capture realtime audio output from the DAW engine. |
| `mcp_opendaw_change_base_signature` |  | `nominator`, `denominator` | Change the base time signature of the project. |
| `mcp_opendaw_classify_drum_pattern` |  | `unit_index`, `track_index`, `region_index` | Classify a drum pattern from MIDI notes in a region. |
| `mcp_opendaw_clone_clip` |  | `unit_index`, `track_index`, `clip_index`, `consolidate` | Clone a clip (note or value) on the same track. Optionally consolidate (make event collection unique). |
| `mcp_opendaw_clone_effect_chain` |  | `src_unit`, `dst_unit` | Copy all effects from one audio unit to another, including parameter values. |
| `mcp_opendaw_clone_track` |  | `unit_index`, `track_index`, `name`, `transpose`, `velocity_scale`, `time_offset_beats`, `new_unit` | Clone a track — full duplication of notes, regions, and structure. |
| `mcp_opendaw_compact_tracks` |  | `unit_index` | Remove empty tracks from an audio unit (or all AUs). |
| `mcp_opendaw_compare_to_profile` |  | `filename`, `genre` | Compare your mix against a professional genre reference profile. |
| `mcp_opendaw_compare_to_reference` |  | `filename`, `reference` | A/B compare your mix against a reference track across all dimensions. |
| `mcp_opendaw_connect_modular_modules` |  | `au_index`, `effect_index`, `source_module_index`, `source_output_name`, `target_module_index`, `target_input_name` | Connect two modules in a Modular device (create a patch cable). |
| `mcp_opendaw_connect_sidechain` |  | `source_unit_index`, `target_unit_index`, `effect_index` | Connect one audio unit's output as sidechain source to a Compressor/Gate on another unit. |
| `mcp_opendaw_consolidate_clip` |  | `unit_index`, `track_index`, `clip_index` | Consolidate a clip's event collection — make it unique (not shared/mirrored). |
| `mcp_opendaw_consolidate_note` |  | `unit_index`, `track_index`, `region_index`, `note_index` | Consolidate a repeated note (playCount > 1) into individual separate notes. |
| `mcp_opendaw_consolidate_region` |  | `unit_index`, `track_index`, `region_index` | Consolidate a region's event collection — make it unique (not shared/mirrored). |
| `mcp_opendaw_constrain_note_range` |  | `unit_index`, `track_index`, `region_index`, `min_pitch`, `max_pitch`, `mode` | Constrain notes to a pitch range — clamp or octave-wrap out-of-range notes. |
| `mcp_opendaw_convert_audio` |  | `filename`, `format`, `bitrate`, `quality` | Convert an exported WAV file to MP3 or FLAC using system ffmpeg. |
| `mcp_opendaw_copy_notes_to_track` |  | `source_unit_index`, `source_track_index`, `dest_track_index`, `source_region_index`, `dest_unit_index`, `transpose`, `time_offset`, `velocity_scale` | Copy notes from one track/region to another track — MIDI layering and doubling. |
| `mcp_opendaw_copy_playfield_sample` |  | `unit_index`, `sample_index`, `target_index` | Copy a Playfield (drum machine) sample to a new index slot. |
| `mcp_opendaw_copy_region_fades` |  | `src_unit`, `src_track`, `src_region`, `dst_unit`, `dst_track`, `dst_region` | Copy fade in/out settings from one audio region to another. |
| `mcp_opendaw_copy_region_to_track` |  | `src_unit`, `src_track`, `src_region`, `dst_unit`, `dst_track`, `position` | Copy a region to a different track (or same track at new position). |
| `mcp_opendaw_diatonic_transpose_notes` |  | `unit_index`, `track_index`, `region_index`, `steps`, `root_note`, `scale` | Transpose notes by scale steps (diatonic) instead of semitones (chromatic). |
| `mcp_opendaw_displace_rhythm` |  | `unit_index`, `track_index`, `region_index`, `offset`, `mode` | Displace all notes in a region by a fixed rhythmic offset — laid-back, |
| `mcp_opendaw_double_melody` |  | `unit_index`, `track_index`, `interval`, `region_index`, `diatonic`, `root`, `scale`, `velocity_scale`, `dest_track_index`, `dest_unit_index`, `time_offset` | Double a melody at a parallel interval — thickening and harmonization. |
| `mcp_opendaw_download_audio` |  | `url`, `filename`, `output_dir` | Download an audio file from a URL (e.g. Suno CDN) to local disk. |
| `mcp_opendaw_duplicate_audiounit` |  | `unit_index` | Duplicate an audio unit with all its content: instrument, effects, tracks, regions, notes, automation. |
| `mcp_opendaw_duplicate_automation_event` |  | `unit_index`, `track_index`, `region_index`, `event_index`, `position_offset`, `value_override` | Duplicate an automation event within the same region. |
| `mcp_opendaw_duplicate_effect` |  | `unit_index`, `effect_index`, `chain_type` | Duplicate a single effect within an AU's effect chain, copying all parameter values. |
| `mcp_opendaw_duplicate_note_event` |  | `unit_index`, `track_index`, `region_index`, `note_index`, `position_offset`, `pitch_offset` | Duplicate a note event within the same region with optional position/pitch offset. |
| `mcp_opendaw_duplicate_note_region` |  | `unit_index`, `track_index`, `region_index`, `offset_beats` | Duplicate a note region to a new position. |
| `mcp_opendaw_duplicate_notes` |  | `unit_index`, `track_index`, `region_index` | Duplicate all notes within a region, shifting them after the last note. |
| `mcp_opendaw_duplicate_region` |  | `unit_index`, `track_index`, `region_index`, `find_free_space` | Duplicate any region (audio, note, or value) using the DAW's built-in duplicateRegion API. |
| `mcp_opendaw_duplicate_section` |  | `from_beat`, `to_beat`, `target_beat`, `unit_indices` | Duplicate all regions within a beat range to a new position. |
| `mcp_opendaw_engine_panic` |  | — | Send a panic signal to the engine — stops all notes immediately. |
| `mcp_opendaw_engine_sleep` |  | — | Put the audio engine to sleep — suspends audio processing to save CPU. |
| `mcp_opendaw_engine_wake` |  | — | Wake the audio engine from sleep — resumes audio processing. |
| `mcp_opendaw_expand_intervals` |  | `unit_index`, `track_index`, `region_index`, `factor`, `anchor`, `snap_to_scale`, `root` | Expand or compress melodic intervals by a factor. |
| `mcp_opendaw_explode_chords` |  | `unit_index`, `track_index`, `region_index`, `num_voices`, `direction`, `target_units`, `velocity_balance` | Explode chords into separate voice tracks. |
| `mcp_opendaw_extract_motifs` |  | `unit_index`, `track_index`, `region_index`, `min_motif_length`, `max_motif_length`, `min_repetitions`, `max_results` | Extract repeating melodic motifs from a MIDI region. |
| `mcp_opendaw_extract_rhythm` |  | `unit_index`, `track_index`, `region_index`, `grid` | Extract rhythmic pattern from notes — onset grid, syncopation, IOI. |
| `mcp_opendaw_filter_notes` |  | `unit_index`, `track_index`, `region_index`, `min_pitch`, `max_pitch`, `min_velocity`, `max_velocity`, `from_beat`, `to_beat`, `action` | Filter notes by criteria — list, delete, or keep matching notes. |
| `mcp_opendaw_find_overlapping_notes` |  | `unit_index`, `track_index`, `region_index`, `pitch`, `from_beat`, `to_beat` | Find notes that overlap a given pitch and time range within a note region. |
| `mcp_opendaw_flatten_note_regions` |  | `unit_index`, `track_index`, `region_indices` | Flatten (merge) multiple overlapping note regions into a single region. |
| `mcp_opendaw_force_scale_notes` |  | `unit_index`, `track_index`, `region_index`, `root_note`, `scale`, `direction`, `preserve_octave` | Force all notes in a region into a specific scale — harmonic snap. |
| `mcp_opendaw_freeze_audiounit` |  | `unit_index` | Freeze an audio unit — pre-render its output offline to save CPU. |
| `mcp_opendaw_generate_melody` |  | `root`, `scale`, `bars`, `contour`, `rhythm`, `octave`, `velocity`, `rest_probability`, `unit_index`, `track_index`, `start_beat` | Generate a melodic line from a scale using contour-guided random selection. |
| `mcp_opendaw_groove_transfer` |  | `source_unit_index`, `source_track_index`, `source_region_index`, `dest_unit_index`, `dest_track_index`, `dest_region_index`, `groove_length`, `timing_strength`, `velocity_strength`, `grid` | Transfer groove (timing + velocity feel) from a source region to a destination region. |
| `mcp_opendaw_humanize_notes` |  | `unit_index`, `track_index`, `velocity_amount`, `timing_amount`, `duration_amount`, `swing`, `seed` | Add human-like variation to existing notes — velocity, timing, duration, and swing. |
| `mcp_opendaw_humanize_pitch` |  | `unit_index`, `track_index`, `region_index`, `cents_depth`, `bias`, `seed` | Add micro-detune (cents) to notes — intonation humanization. |
| `mcp_opendaw_identify_chords` |  | `unit_index`, `track_index`, `region_index`, `group_tolerance`, `min_notes` | Identify chords from existing notes in a region — harmonic analysis / reverse engineering. |
| `mcp_opendaw_insert_rests` |  | `unit_index`, `track_index`, `region_index`, `rest_positions`, `tolerance_beats`, `mode`, `shorten_neighbors` | Insert rests at specified beat positions by removing notes. |
| `mcp_opendaw_invert_chord_notes` |  | `unit_index`, `track_index`, `region_index`, `chord_position`, `inversion`, `direction` | Invert a chord at a specific position — move bottom N notes up an octave (or top N down). |
| `mcp_opendaw_invert_notes` |  | `unit_index`, `track_index`, `region_index`, `axis` | Invert melody around a pitch axis — mirror reflection. |
| `mcp_opendaw_map_velocity_by_pitch` |  | `unit_index`, `track_index`, `region_index`, `mode`, `intensity`, `min_velocity`, `max_velocity`, `pitch_ref` | Map velocity based on pitch — expressive dynamics from note height. |
| `mcp_opendaw_match_to_reference` |  | `filename`, `reference`, `output_filename`, `match_lufs`, `match_spectrum`, `match_stereo` | Automatically match your mix to a reference track — spectral + loudness alignment. |
| `mcp_opendaw_measure_lufs` |  | `filename` | Measure LUFS (integrated) and true peak of an exported WAV file. |
| `mcp_opendaw_merge_consecutive_notes` |  | `unit_index`, `track_index`, `region_index`, `same_pitch_only`, `max_gap_beats`, `velocity_mode` | Merge consecutive notes of the same pitch into single sustained notes. |
| `mcp_opendaw_merge_note_regions` |  | `unit_index`, `track_index`, `region_index_a`, `region_index_b` | Merge two note regions on the same track into one. |
| `mcp_opendaw_merge_note_tracks` |  | `source_unit`, `source_track`, `dest_unit`, `dest_track`, `source_region`, `dest_region`, `delete_source`, `resolve_overlaps`, `transpose` | Merge notes from a source track into a destination track. |
| `mcp_opendaw_modulate_progression` |  | `progression`, `target_key`, `direction` | Transpose a chord progression to a new key. |
| `mcp_opendaw_move_audio_unit` |  | `unit_index`, `delta` | Move an audio unit up or down in the mixer order. |
| `mcp_opendaw_move_automation_event` |  | `unit_index`, `track_index`, `event_index`, `new_position_beats` | Move an automation event to a new position on the timeline. |
| `mcp_opendaw_move_effect` |  | `unit_index`, `from_index`, `to_index` | Reorder an effect within an audio unit's effect chain. |
| `mcp_opendaw_move_notes` |  | `source_unit`, `source_track`, `source_region`, `dest_unit`, `dest_track`, `time_offset`, `transpose`, `velocity_scale`, `delete_source`, `dest_region` | Move notes from a source region to another track — copy + delete. |
| `mcp_opendaw_move_region_content` |  | `unit_index`, `track_index`, `region_index`, `delta_beats` | Shift the content start of a region without moving the region itself. |
| `mcp_opendaw_move_region_to_track` |  | `src_unit_index`, `src_track_index`, `region_index`, `dst_unit_index`, `dst_track_index` | Move a region from one track to another (possibly in a different audio unit). |
| `mcp_opendaw_move_section` |  | `from_beat`, `to_beat`, `target_beat`, `unit_indices` | Move all regions within a beat range to a new position (non-destructive rearrangement). |
| `mcp_opendaw_move_signature_event` |  | `event_index`, `target_ppqn` | Move a time signature change event to a new PPQN position. |
| `mcp_opendaw_move_track` |  | `unit_index`, `track_index`, `delta` | Move a track up or down within an audio unit. |
| `mcp_opendaw_note_stats` |  | `unit_index`, `track_index`, `region_index` | Get comprehensive statistics for notes in a region. |
| `mcp_opendaw_ppqn_to_parts` |  | `position_ppqn` | Convert a PPQN position to musical parts: bars, beats, semiquavers, ticks. |
| `mcp_opendaw_ppqn_to_seconds` |  | `position_beats` | Convert a position in beats (PPQN units) to seconds using the project's tempo map. |
| `mcp_opendaw_produce_and_master` |  | `structure`, `key_root`, `scale_type`, `octave`, `velocity`, `genre`, `bpm`, `platform`, `master_style`, `render`, `seed` | Produce AND master a complete track in one call. |
| `mcp_opendaw_produce_full_track` |  | `structure`, `key_root`, `scale_type`, `octave`, `velocity`, `genre`, `bpm`, `render`, `seed` | Produce a complete track from structure to render in one call. |
| `mcp_opendaw_quantize_notes` |  | `division`, `unit_index`, `track_index`, `strength` | Quantize note positions to a grid division. |
| `mcp_opendaw_quantize_velocities` |  | `unit_index`, `track_index`, `levels`, `mode`, `min_velocity`, `max_velocity`, `region_index` | Quantize note velocities to discrete stepped levels. |
| `mcp_opendaw_query_loading_complete` |  | — | Check if all audio samples are loaded and ready for playback. |
| `mcp_opendaw_randomize_note_chance` |  | `unit_index`, `track_index`, `region_index`, `min_chance`, `max_chance`, `mode`, `seed` | Randomize note playback probability (chance) — generative variation. |
| `mcp_opendaw_randomize_note_durations` |  | `unit_index`, `track_index`, `region_index`, `variation`, `distribution`, `min_duration_beats`, `max_duration_beats`, `preserve_total`, `seed` | Randomize note durations with controllable distribution. |
| `mcp_opendaw_redo` |  | — | Redo the last undone operation. |
| `mcp_opendaw_reharmonize_progression` |  | `progression`, `technique`, `intensity`, `target_chord` | Reharmonize a chord progression — substitute chords with functionally |
| `mcp_opendaw_remix_track` |  | `filename`, `genre`, `style`, `stem_mode`, `master_lufs`, `add_harmony`, `add_counter_melody`, `bars` | Full Suno remix pipeline in one call — analyze → import → harmony → mix → master. |
| `mcp_opendaw_remove_audio_bus` |  | `bus_index`, `fx_unit_index` | Remove an FX audio bus and its associated audio unit. |
| `mcp_opendaw_remove_effect` |  | `unit_index`, `effect_index` | Remove an audio effect from an audio unit's chain. |
| `mcp_opendaw_remove_midi_effect` |  | `unit_index`, `effect_index` | Remove a MIDI effect from an audio unit's MIDI chain. |
| `mcp_opendaw_remove_modular_module` |  | `au_index`, `effect_index`, `module_index` | Remove a module from a Modular device. |
| `mcp_opendaw_remove_send` |  | `unit_index`, `send_index` | Remove an aux send from an audio unit. |
| `mcp_opendaw_rename_unit` |  | `unit_index`, `name`, `icon` | Rename an audio unit's instrument and optionally set its icon. |
| `mcp_opendaw_reorder_sections` |  | `section_order`, `unit_indices` | Reorder song sections — rearrange blocks on the timeline. |
| `mcp_opendaw_repeat_notes` |  | `unit_index`, `track_index`, `region_index`, `repeats`, `transpose_semitones`, `velocity_decay`, `time_gap_beats`, `direction`, `dest_track_index` | Repeat existing notes in a region N times with per-repeat transformations. |
| `mcp_opendaw_repeat_phrase` |  | `unit_index`, `track_index`, `region_index`, `repetitions`, `transpose_semitones`, `transpose_mode`, `scale`, `root`, `velocity_pattern`, `velocity_start`, `velocity_end`, `time_stretch`, `cross_track` | Repeat a melodic phrase N times with transposition — melodic sequence. |
| `mcp_opendaw_replace_from_preset` |  | `unit_index`, `preset_b64`, `keep_midi_effects`, `keep_audio_effects`, `keep_timeline` | Replace an audio unit's instrument/effects/timeline from a preset. |
| `mcp_opendaw_replace_instrument` |  | `unit_index`, `new_instrument` | Replace the instrument on an audio unit with a different MIDI instrument. |
| `mcp_opendaw_reverse_notes` |  | `unit_index`, `track_index`, `region_index` | Reverse the order of notes in a region — retrograde variation. |
| `mcp_opendaw_rotate_notes` |  | `unit_index`, `track_index`, `region_index`, `rotate_by`, `axis`, `preserve_pitch_contour` | Rotate notes in a region by N positions (cyclic shift). |
| `mcp_opendaw_save_effect_preset` |  | `unit_index`, `effect_index`, `name`, `description`, `output_path` | Save an audio effect chain as a .opb preset file. |
| `mcp_opendaw_save_project` |  | `filename` | Save the current project state to a binary file. |
| `mcp_opendaw_scale_durations` |  | `unit_index`, `track_index`, `mode`, `value`, `region_index`, `min_duration`, `max_duration`, `quantize` | Scale the duration of all notes in a region — MIDI note length control. |
| `mcp_opendaw_scale_velocity` |  | `unit_index`, `track_index`, `mode`, `value`, `region_index`, `min_velocity`, `max_velocity` | Scale the velocity of all notes in a region — MIDI dynamics control. |
| `mcp_opendaw_schedule_clip_play` |  | `clip_ids` | Schedule clips to play in session view (live triggering). |
| `mcp_opendaw_schedule_clip_stop` |  | `track_ids` | Schedule clips to stop on specified tracks (session view). |
| `mcp_opendaw_screenshot_daw` |  | — | Take a screenshot of the openDAW UI. Returns base64-encoded PNG image. |
| `mcp_opendaw_seconds_to_beats` |  | `seconds` | Convert a time in seconds to beats using the project's tempo map. |
| `mcp_opendaw_separate_stems` |  | `input_file`, `model`, `output_dir` | Separate audio into stems using SOTA AI models — SCNet, BS-Roformer, PolarFormer. |
| `mcp_opendaw_serialize` |  | — | Serialize the current project state to JSON. Returns the serialized project data. |
| `mcp_opendaw_shift_mode` |  | `unit_index`, `track_index`, `region_index`, `root_note`, `from_scale`, `to_scale`, `preserve_root` | Transform notes from one scale/mode to another, keeping the tonic. |
| `mcp_opendaw_shuffle_notes` |  | `unit_index`, `track_index`, `region_index`, `mode`, `seed`, `shuffle_amount`, `preserve_first`, `preserve_last`, `group_beats` | Shuffle note data randomly within a region. |
| `mcp_opendaw_split_note_region` |  | `unit_index`, `track_index`, `region_index`, `split_beat` | Split a note region into two at a given beat position. |
| `mcp_opendaw_split_stems` |  | `input_path`, `mode`, `output_dir`, `import_to_daw` | Split an audio file into stems using SOTA open-source separation models. |
| `mcp_opendaw_spread_voicing` |  | `unit_index`, `track_index`, `region_index`, `chord_position`, `mode`, `spread_octaves` | Spread or compact a chord voicing — open vs close harmony. |
| `mcp_opendaw_start_engine` |  | — | Start the audio engine (AudioWorklet) after setting up tracks and regions. |
| `mcp_opendaw_strum_notes` |  | `unit_index`, `track_index`, `region_index`, `direction`, `speed`, `jitter` | Strum simultaneous notes — convert block chords into guitar-style strums. |
| `mcp_opendaw_subdivide_notes` |  | `unit_index`, `track_index`, `region_index`, `subdivisions`, `pitch_pattern`, `velocity_pattern`, `accent_first`, `dest_track_index` | Subdivide each note in a region into N smaller notes. |
| `mcp_opendaw_swap_sections` |  | `section1_start`, `section1_end`, `section2_start`, `section2_end`, `unit_indices` | Swap two sections of the arrangement — exchange their positions on the timeline. |
| `mcp_opendaw_switch_phase` |  | `phase` | Switch the active tool phase for phase-based tool loading. |
| `mcp_opendaw_task_cancel` |  | `task_id` | Request cancellation of a running task. |
| `mcp_opendaw_task_get` |  | `task_id` | Poll the status of a long-running task (render, stems). |
| `mcp_opendaw_task_list` |  | — | List all tasks (most recent first). |
| `mcp_opendaw_task_render_full` |  | `filename`, `sample_rate` | Start async render of the full project mix. |
| `mcp_opendaw_thin_notes` |  | `unit_index`, `track_index`, `region_index`, `strategy`, `interval`, `velocity_threshold`, `random_chance`, `preserve_strong_beats` | Thin out notes in a region — reduce note density for cleaner patterns. |
| `mcp_opendaw_time_warp_notes` |  | `unit_index`, `track_index`, `region_index`, `warp_factor`, `origin` | Warp note positions and durations by a factor — half-time / double-time / custom stretch. |
| `mcp_opendaw_transcribe_audio` |  | `filename`, `bpm`, `unit_index`, `drum_track`, `melody_track` | Transcribe a full audio track — drums + melody — into MIDI notes in one call. |
| `mcp_opendaw_transcribe_drums` |  | `filename`, `bpm`, `sensitivity`, `unit_index`, `track_index` | Transcribe drum onsets from an audio file into MIDI notes on a DAW track. |
| `mcp_opendaw_transcribe_melody` |  | `filename`, `bpm`, `unit_index`, `track_index` | Transcribe monophonic melody from an audio file into MIDI notes on a DAW track. |
| `mcp_opendaw_transfer_audiounit` |  | `unit_index`, `delete_source`, `insert_index` | Transfer/copy an audio unit (instrument/effects/tracks/regions) within the project. |
| `mcp_opendaw_transfer_region` |  | `src_unit_index`, `src_track_index`, `region_index`, `dst_unit_index`, `dst_track_index`, `insert_position`, `delete_source` | Transfer/copy a region to another track at a specific position. |
| `mcp_opendaw_transport` |  | `action` | Control transport: play, stop, or toggle. |
| `mcp_opendaw_transpose_notes` |  | `semitones`, `unit_index`, `track_index`, `region_index` | Transpose all notes by a number of semitones. |
| `mcp_opendaw_undo` |  | — | Undo the last editing operation. |
| `mcp_opendaw_unfreeze_audiounit` |  | `unit_index` | Unfreeze a frozen audio unit — resume real-time processing. |
| `mcp_opendaw_update_automation_event` |  | `unit_index`, `track_index`, `event_index`, `value`, `interpolation`, `curve_slope` | Update an existing automation event's value and/or interpolation. |
| `mcp_opendaw_update_warp_marker` |  | `unit_index`, `track_index`, `region_index`, `marker_index`, `position_beats`, `seconds` | Update a warp marker's position and/or seconds value. |
| `mcp_opendaw_validate_project` |  | — | Check if the project is valid — detects overlapping regions on the same track. |
| `mcp_opendaw_wait_for_condition` |  | `condition_js`, `timeout_ms`, `poll_interval_ms` | Wait for a JavaScript condition to evaluate to true in the DAW context. |

## Read-only

| Tool | Annotation | Parameters | Description |
|---|---|---|---|
| `mcp_opendaw_analyze_dynamics` | `readOnly` | `filename` | Dynamics analysis — crest factor, loudness range, transient density, segment RMS. |
| `mcp_opendaw_analyze_harmonic_rhythm` | `readOnly` | `unit_index`, `track_index`, `region_index`, `group_tolerance`, `min_notes` | Analyze harmonic rhythm — how fast chords change and where. |
| `mcp_opendaw_analyze_melody` | `readOnly` | `unit_index`, `track_index`, `region_index` | Analyze melodic content — contour, intervals, direction, climax. |
| `mcp_opendaw_analyze_mix` | `readOnly` | `filename` | Complete mix diagnosis in one call — combines track + spectrum + stereo + dynamics. |
| `mcp_opendaw_analyze_phase` | `readOnly` | `filename` | Per-band phase analysis — coherence, polarity, inter-channel delay. |
| `mcp_opendaw_analyze_song_structure` | `readOnly` | `unit_index`, `bars_per_segment` | Analyze song structure by segmenting MIDI content into structural parts. |
| `mcp_opendaw_analyze_spectrum` | `readOnly` | `filename` | Spectral analysis of audio across 7 ISO frequency bands. |
| `mcp_opendaw_analyze_stereo` | `readOnly` | `filename` | Stereo analysis of audio — width, L/R balance, mono compatibility, mid/side energy. |
| `mcp_opendaw_analyze_track` | `readOnly` | `filename` | Full audio analysis in one call — BPM + key + LUFS + duration + dynamic range. |
| `mcp_opendaw_detect_bpm` | `readOnly` | `filename` | Detect BPM (tempo) of an exported WAV file using onset detection + autocorrelation. |
| `mcp_opendaw_detect_frequency_masking` | `readOnly` | `filenames` | Detect frequency masking between stems — where instruments compete for the same frequency range. |
| `mcp_opendaw_detect_key` | `readOnly` | `filename` | Detect musical key and mode of a WAV file using chroma features + Krumhansl-Schmuckler key profiles. |
| `mcp_opendaw_detect_problems` | `readOnly` | `filename` | Detect technical audio problems — clipping, DC offset, hum, sibilance, mud, harshness. |
| `mcp_opendaw_detect_scale_from_notes` | `readOnly` | `unit_index`, `track_index`, `region_index` | Detect the musical scale/key from MIDI notes in a region. |
| `mcp_opendaw_evaluate_raw` | `readOnly` | `script` | Execute arbitrary JavaScript in the DAW V8 context and return the result. |
| `mcp_opendaw_get_audio_file_info` | `readOnly` | `unit_index`, `track_index`, `region_index` | Get metadata about the audio file referenced by an audio region. |
| `mcp_opendaw_get_automation_value` | `readOnly` | `unit_index`, `track_index`, `position_beats` | Get the automation value at a specific position on a value (automation) track. |
| `mcp_opendaw_get_bar_interval` | `readOnly` | `position_ppqn` | Get the start and end PPQN of the bar containing the given position. |
| `mcp_opendaw_get_device_chain_detail` | `readOnly` | `unit_index` | Get detailed info about all devices on an AU — instrument, audio effects, MIDI effects. |
| `mcp_opendaw_get_effect_chain` | `readOnly` | `unit_index` | Get the full effect chain for an audio unit. |
| `mcp_opendaw_get_effect_state` | `readOnly` | `unit_index`, `effect_index` | Get full state of an effect: enabled, minimized, sidechain, all parameters. |
| `mcp_opendaw_get_engine_status` | `readOnly` | — | Get real-time engine status: playing state, position, BPM, CPU load, recording state. |
| `mcp_opendaw_get_full_project_state` | `readOnly` | — | Get a complete snapshot of the project — all AUs, tracks, regions, effects, mixer state. |
| `mcp_opendaw_get_midi_effect_chain` | `readOnly` | `unit_index` | Get the MIDI effect chain for an audio unit. |
| `mcp_opendaw_get_mixer_state` | `readOnly` | — | Get the full mixer state — all audio units with volume, panning, mute, solo, and type. |
| `mcp_opendaw_get_neuralamp_model` | `readOnly` | `unit_index`, `effect_index` | Get the NeuralAmp (Tone3000) model JSON for a NeuralAmp effect. |
| `mcp_opendaw_get_note_range` | `readOnly` | `unit_index`, `track_index`, `region_index` | Get the pitch range and max duration of notes in a note region. |
| `mcp_opendaw_get_piano_mode` | `readOnly` | — | Get piano roll view settings. |
| `mcp_opendaw_get_project_duration` | `readOnly` | — | Get the total project duration — the end position of the last region across all tracks. |
| `mcp_opendaw_get_project_info` | `readOnly` | — | Get a quick project overview: BPM, time signature, track/AU/effect counts, total duration. |
| `mcp_opendaw_get_project_metadata` | `readOnly` | — | Get project metadata: creation date, BPM, time signature, AU count, track count. |
| `mcp_opendaw_get_project_state` | `readOnly` | — | Get full project state: BPM, sample rate, playing status, track list, effects chain. |
| `mcp_opendaw_get_region_info` | `readOnly` | `unit_index`, `track_index`, `region_index` | Get detailed info about a single region — position, duration, loop, mute, content. |
| `mcp_opendaw_get_region_play_mode` | `readOnly` | `unit_index`, `track_index`, `region_index` | Get the play mode of an audio region — stretch type, playback rate, cents, transient mode. |
| `mcp_opendaw_get_sample_info` | `readOnly` | `sample_uuid` | Get detailed info about an audio sample by UUID. |
| `mcp_opendaw_get_script_device_code` | `readOnly` | `device_type`, `unit_index`, `device_index` | Read the current user JavaScript code from a scriptable device. |
| `mcp_opendaw_get_signature_events` | `readOnly` | — | List all time signature change events in the project. |
| `mcp_opendaw_get_studio_settings` | `readOnly` | — | Get all studio preferences/settings (engine, visibility, editing, debug, storage, time-display, pointer). |
| `mcp_opendaw_get_tempo_at` | `readOnly` | `position_beats` | Get the BPM at a specific position, accounting for tempo automation. |
| `mcp_opendaw_get_track_info` | `readOnly` | `unit_index`, `track_index` | Get detailed info about a track — type, regions, clips, enabled state, target. |
| `mcp_opendaw_get_unit_freeze_status` | `readOnly` | `unit_index` | Check if an audio unit is frozen and whether it can be frozen. |
| `mcp_opendaw_list_audio_buses` | `readOnly` | — | List all audio buses in the project (primary output + FX buses). |
| `mcp_opendaw_list_audio_regions` | `readOnly` | `unit_index`, `track_index` | List all audio regions with file name, position, and duration. |
| `mcp_opendaw_list_automatable_fields` | `readOnly` | `unit_index`, `sample_index` | List all automatable parameter fields on an instrument (or specific Playfield sample). |
| `mcp_opendaw_list_automation_events` | `readOnly` | `unit_index`, `track_index` | List automation events (ValueEventBox) on a unit's automation tracks. |
| `mcp_opendaw_list_automation_events_detail` | `readOnly` | `unit_index`, `track_index` | List all automation events on a value track with full detail — position, value, interpolation. |
| `mcp_opendaw_list_clips` | `readOnly` | `unit_index`, `track_index` | List clips (session view / clip launcher) on tracks. |
| `mcp_opendaw_list_effect_parameters` | `readOnly` | `unit_index`, `effect_index` | List all parameters of an effect on an audio unit. |
| `mcp_opendaw_list_effects` | `readOnly` | — | List all available audio and MIDI effect types. |
| `mcp_opendaw_list_genre_profiles` | `readOnly` | — | List all available genre reference profiles for mix analysis. |
| `mcp_opendaw_list_instrument_params` | `readOnly` | `unit_index` | List all parameters of the instrument connected to an audio unit. |
| `mcp_opendaw_list_markers` | `readOnly` | — | List all timeline markers with positions and labels. |
| `mcp_opendaw_list_midi_effect_params` | `readOnly` | `unit_index`, `effect_index` | List all parameters of a MIDI effect with current values. |
| `mcp_opendaw_list_midi_effects` | `readOnly` | — | List all available MIDI effect types. |
| `mcp_opendaw_list_midi_output_devices` | `readOnly` | — | List all MIDI output devices registered in the project (hardware MIDI outputs). |
| `mcp_opendaw_list_modular_connections` | `readOnly` | `au_index`, `effect_index` | List all connections (patch cables) in a Modular device. |
| `mcp_opendaw_list_modular_devices` | `readOnly` | — | List all Modular audio effect devices in the project. |
| `mcp_opendaw_list_modular_modules` | `readOnly` | `au_index`, `effect_index` | List all modules in a Modular device. |
| `mcp_opendaw_list_note_regions` | `readOnly` | `unit_index`, `track_index` | List all note regions with position, duration, and note count. |
| `mcp_opendaw_list_notes` | `readOnly` | `unit_index`, `track_index`, `region_index` | List all note events within a region. |
| `mcp_opendaw_list_playfield_samples` | `readOnly` | `unit_index` | List all drum pads (samples) on a Playfield drum machine. |
| `mcp_opendaw_list_samples` | `readOnly` | — | List all audio file samples used in the project. |
| `mcp_opendaw_list_script_params` | `readOnly` | `device_type`, `unit_index`, `device_index` | List @param declarations on a scriptable device with full mapping info. |
| `mcp_opendaw_list_script_samples` | `readOnly` | `device_type`, `unit_index`, `device_index` | List @sample declaration slots on a scriptable device. |
| `mcp_opendaw_list_sends` | `readOnly` | `unit_index` | List all aux sends on an audio unit. |
| `mcp_opendaw_list_signature_changes` | `readOnly` | — | List all time signature changes on the timeline's signature track. |
| `mcp_opendaw_list_split_modes` | `readOnly` | — | List available stem separation modes with descriptions. |
| `mcp_opendaw_list_tempo_changes` | `readOnly` | — | List all tempo (BPM) changes on the timeline's tempo track. |
| `mcp_opendaw_list_tracks` | `readOnly` | — | List all tracks across all audio units with their type, effects, and regions. |
| `mcp_opendaw_list_transient_markers` | `readOnly` | `unit_index`, `track_index`, `region_index` | List transient markers for an audio region's audio file. |
| `mcp_opendaw_list_value_regions` | `readOnly` | `unit_index`, `track_index` | List automation regions (ValueRegionBox) on value/automation tracks. |
| `mcp_opendaw_list_vaporisateur_params` | `readOnly` | `unit_index` | Get full Vaporisateur synthesizer state: oscillators, LFO, noise, main params. |
| `mcp_opendaw_list_warp_markers` | `readOnly` | `unit_index`, `track_index`, `region_index` | List warp markers on a time-stretched or pitch-stretched audio region. |
| `mcp_opendaw_read_meter` |  | `unit_index`, `device_index` | Read parameter values from a Werkstatt meter device (LUFS/correlation/spectrum). |

## Render / Export

| Tool | Annotation | Parameters | Description |
|---|---|---|---|
| `mcp_opendaw_export_dawproject` |  | `filename` | Export the current project as a .dawproject file (Bitwig/Ableton/rePitch compatible format). |
| `mcp_opendaw_export_dry_stem` |  | `unit_index`, `filename`, `sample_rate` | Export a single audio unit as a DRY stem (instrument output, no effects/channel strip). |
| `mcp_opendaw_export_effect_chain` |  | `unit_index`, `effect_type` | Export an effect chain (audio or MIDI) from an AU as a base64 preset. |
| `mcp_opendaw_export_midi` |  | `filename`, `unit_index`, `track_index`, `region_index` | Export a note region's notes as a standard MIDI file (.mid). |
| `mcp_opendaw_export_mix` |  | `filename`, `sample_rate`, `method` | Render the full project mix to a WAV file. |
| `mcp_opendaw_export_preset` |  | `unit_index`, `include_timeline` | Export an audio unit as a preset (base64-encoded binary). |
| `mcp_opendaw_export_single_stem` |  | `unit_index`, `filename`, `sample_rate` | Export a single audio unit as a stem WAV with its effect chain applied. |
| `mcp_opendaw_export_stems` |  | `filename_prefix`, `sample_rate` | Export each audio unit as a separate stem WAV file. |
| `mcp_opendaw_export_stems_format` |  | `filename_prefix`, `sample_rate`, `format`, `bitrate` | Export stems as separate files and convert each to MP3 or FLAC. |
| `mcp_opendaw_render_and_analyze` |  | `filename`, `sample_rate`, `analysis_depth` | Render the current project and run full audio analysis in one call. |
| `mcp_opendaw_render_full` |  | `filename`, `sample_rate` | Render the entire project as a single stereo WAV file (full mixdown). |
| `mcp_opendaw_render_full_format` |  | `filename`, `sample_rate`, `format`, `bitrate` | Render the entire project and convert to MP3 or FLAC in one step. |
| `mcp_opendaw_render_full_song` |  | `filename`, `sample_rate`, `tail_beats` | Render the entire project — auto-detects song length from all regions. |
| `mcp_opendaw_render_range` |  | `start_beat`, `end_beat`, `filename`, `sample_rate` | Render only a portion of the project (e.g. chorus only) for quick A/B comparison. |
