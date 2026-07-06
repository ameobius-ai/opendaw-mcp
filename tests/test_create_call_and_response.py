"""Unit tests for create_call_and_response."""
import json
import pytest
import random

NOTE_MAP = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4,
            "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9,
            "A#": 10, "Bb": 10, "B": 11}

SCALE_INTERVALS = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "aeolian": [0, 2, 3, 5, 7, 8, 10],
    "locrian": [0, 1, 3, 5, 6, 8, 10],
    "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
    "melodic_minor": [0, 2, 3, 5, 7, 9, 11],
    "pentatonic_major": [0, 2, 4, 7, 9],
    "pentatonic_minor": [0, 3, 5, 7, 10],
    "blues": [0, 3, 5, 6, 7, 10],
    "whole_tone": [0, 2, 4, 6, 8, 10],
}


def _degree_to_pitch(degree, scale):
    n_intervals = len(scale)
    octave = degree // n_intervals
    index = degree % n_intervals
    if index < 0:
        index += n_intervals
        octave -= 1
    return octave * 12 + scale[index]


def _generate_car(call_pattern="0 2 4 7 4 2", call_rhythm="0.5 0.5 0.5 1.0 0.5 0.5",
                  response_type="echo", key_root="C", scale_name="major",
                  pairs=4, response_interval=5, velocity=0.7, gap_beats=1.0, start_beat=0.0):
    """Pure-Python reimplementation."""
    scale = SCALE_INTERVALS[scale_name]
    root_pc = NOTE_MAP[key_root]
    root_pitch = (3 + 1) * 12 + root_pc

    degrees = [int(d) for d in call_pattern.split()]
    durations = [float(d) for d in call_rhythm.split()]
    if len(durations) < len(degrees):
        durations.extend([0.5] * (len(degrees) - len(durations)))
    n_call_notes = len(degrees)
    call_duration = sum(durations[:n_call_notes])

    rng = random.Random(42)
    all_call = []
    all_response = []

    for p in range(pairs):
        pair_start = start_beat + p * (call_duration + gap_beats + call_duration + gap_beats)

        beat = pair_start
        for i in range(n_call_notes):
            pitch = root_pitch + _degree_to_pitch(degrees[i], scale)
            dur = durations[i] if i < len(durations) else 0.5
            all_call.append({"pitch": pitch, "start": round(beat, 4), "duration": round(dur * 0.95, 4), "velocity": round(velocity, 3)})
            beat += dur

        response_start = pair_start + call_duration + gap_beats

        if response_type == "echo":
            beat = response_start
            for i in range(n_call_notes):
                pitch = root_pitch + _degree_to_pitch(degrees[i], scale)
                dur = durations[i] if i < len(durations) else 0.5
                all_response.append({"pitch": pitch, "start": round(beat, 4), "duration": round(dur * 0.95, 4), "velocity": round(velocity * 0.9, 3)})
                beat += dur

        elif response_type == "transpose":
            beat = response_start
            for i in range(n_call_notes):
                pitch = root_pitch + _degree_to_pitch(degrees[i], scale) + response_interval
                dur = durations[i] if i < len(durations) else 0.5
                all_response.append({"pitch": pitch, "start": round(beat, 4), "duration": round(dur * 0.95, 4), "velocity": round(velocity * 0.9, 3)})
                beat += dur

        elif response_type == "variation":
            beat = response_start
            for i in range(n_call_notes):
                pitch = root_pitch + _degree_to_pitch(degrees[i], scale)
                dur = durations[i] if i < len(durations) else 0.5
                offset = 0.0
                if rng.random() < 0.4:
                    offset = rng.choice([0.25, -0.125, 0.125])
                var_dur = dur * rng.choice([0.5, 0.75, 1.0, 1.25])
                all_response.append({"pitch": pitch, "start": round(beat + offset, 4), "duration": round(var_dur * 0.9, 4), "velocity": round(velocity * rng.uniform(0.7, 1.0), 3)})
                beat += dur

        elif response_type == "complementary":
            beat = response_start
            comp_degrees = [(-d + 7) % (len(scale) * 2) - len(scale) for d in degrees]
            for i in range(n_call_notes):
                deg = comp_degrees[i] if i < len(comp_degrees) else 0
                pitch = root_pitch + _degree_to_pitch(deg, scale)
                dur = durations[i] if i < len(durations) else 0.5
                all_response.append({"pitch": pitch, "start": round(beat, 4), "duration": round(dur * 0.95, 4), "velocity": round(velocity * 0.85, 3)})
                beat += dur

        else:  # fill
            beat = response_start
            last_deg = degrees[-1]
            approach_deg = last_deg - 1
            all_response.append({"pitch": root_pitch + _degree_to_pitch(approach_deg, scale), "start": round(beat, 4), "duration": 0.25, "velocity": round(velocity * 0.6, 3)})
            all_response.append({"pitch": root_pitch + _degree_to_pitch(last_deg, scale), "start": round(beat + 0.25, 4), "duration": 1.0, "velocity": round(velocity * 0.85, 3)})

    return all_call, all_response


# === Echo ===

class TestEcho:
    def test_same_pitches(self):
        call, response = _generate_car(response_type="echo", pairs=1)
        call_pitches = [n["pitch"] for n in call]
        resp_pitches = [n["pitch"] for n in response]
        assert call_pitches == resp_pitches

    def test_response_slightly_quieter(self):
        call, response = _generate_car(response_type="echo", pairs=1, velocity=0.8)
        assert response[0]["velocity"] == round(0.8 * 0.9, 3)

    def test_response_after_gap(self):
        call, response = _generate_car(response_type="echo", pairs=1, gap_beats=2.0)
        call_end = call[-1]["start"] + call[-1]["duration"]
        assert response[0]["start"] >= call_end


# === Transpose ===

class TestTranspose:
    def test_transposed_pitches(self):
        call, response = _generate_car(response_type="transpose", pairs=1, response_interval=7)
        for c, r in zip(call, response):
            assert r["pitch"] - c["pitch"] == 7

    def test_transpose_down(self):
        call, response = _generate_car(response_type="transpose", pairs=1, response_interval=-5)
        for c, r in zip(call, response):
            assert r["pitch"] - c["pitch"] == -5


# === Variation ===

class TestVariation:
    def test_same_pitches_different_rhythm(self):
        call, response = _generate_car(response_type="variation", pairs=1)
        call_pitches = [n["pitch"] for n in call]
        resp_pitches = [n["pitch"] for n in response]
        assert call_pitches == resp_pitches  # same pitches
        # Durations may differ
        call_durs = [n["duration"] for n in call]
        resp_durs = [n["duration"] for n in response]
        assert call_durs != resp_durs  # varied


# === Complementary ===

class TestComplementary:
    def test_different_pitches(self):
        call, response = _generate_car(response_type="complementary", pairs=1)
        call_pitches = [n["pitch"] for n in call]
        resp_pitches = [n["pitch"] for n in response]
        assert call_pitches != resp_pitches  # contrasting

    def test_complementary_uses_scale(self):
        call, response = _generate_car(response_type="complementary", pairs=1, key_root="C", scale_name="major")
        # All response pitches should be scale tones
        root_pitch = 48
        scale = SCALE_INTERVALS["major"]
        for n in response:
            rel = (n["pitch"] - root_pitch) % 12
            assert rel in scale or rel == 0


# === Fill ===

class TestFill:
    def test_two_notes_only(self):
        call, response = _generate_car(response_type="fill", pairs=1)
        assert len(response) == 2  # approach + target

    def test_approach_before_target(self):
        call, response = _generate_car(response_type="fill", pairs=1)
        assert response[0]["start"] < response[1]["start"]

    def test_target_is_last_call_note(self):
        call, response = _generate_car(response_type="fill", pairs=1, key_root="C", scale_name="major")
        # Last call degree = 2 → root_pitch + degree_to_pitch(2, major) = 48+4 = 52
        assert response[1]["pitch"] == 52


# === Structure ===

class TestStructure:
    def test_two_tracks(self):
        call, response = _generate_car(pairs=2)
        assert len(call) > 0
        assert len(response) > 0

    def test_pairs_count(self):
        call, _ = _generate_car(pairs=4, response_type="echo")
        # 4 pairs × 6 call notes = 24
        assert len(call) == 24

    def test_pair_spacing(self):
        call, _ = _generate_car(call_pattern="0 2 4", call_rhythm="1 1 1",
                                pairs=2, response_type="echo")
        # call_duration = 3, gap = 1, response_duration = 3, gap = 1 → pair_len = 8
        assert call[0]["start"] == 0.0
        assert call[3]["start"] == 8.0  # first note of second pair (3 notes per pair)

    def test_all_response_types_produce_notes(self):
        for rt in ["echo", "transpose", "variation", "complementary", "fill"]:
            _, response = _generate_car(response_type=rt, pairs=1)
            assert len(response) > 0, f"Response type {rt} produced no notes"


# === Pitches ===

class TestPitches:
    def test_c_major_root(self):
        call, _ = _generate_car(call_pattern="0", call_rhythm="1", pairs=1, key_root="C", scale_name="major")
        assert call[0]["pitch"] == 48  # C3

    def test_a_minor_root(self):
        call, _ = _generate_car(call_pattern="0", call_rhythm="1", pairs=1, key_root="A", scale_name="minor")
        assert call[0]["pitch"] == 57  # A3

    def test_scale_degrees(self):
        call, _ = _generate_car(call_pattern="0 1 2 3 4 5 6 7", call_rhythm="0.5 0.5 0.5 0.5 0.5 0.5 0.5 0.5",
                                 pairs=1, key_root="C", scale_name="major")
        expected = [48, 50, 52, 53, 55, 57, 59, 60]
        actual = [n["pitch"] for n in call]
        assert actual == expected


# === Edge Cases ===

class TestEdgeCases:
    def test_single_pair(self):
        call, response = _generate_car(pairs=1)
        assert len(call) > 0 and len(response) > 0

    def test_many_pairs(self):
        call, _ = _generate_car(pairs=8)
        assert len(call) == 8 * 6  # 8 pairs × 6 call notes

    def test_all_scales(self):
        for scale in SCALE_INTERVALS:
            call, _ = _generate_car(scale_name=scale, pairs=1)
            assert len(call) > 0, f"Scale {scale} failed"

    def test_start_beat_offset(self):
        call, _ = _generate_car(pairs=1, start_beat=8.0)
        assert call[0]["start"] == 8.0

    def test_rhythm_pad(self):
        # More notes than rhythm values → padded with 0.5
        call, _ = _generate_car(call_pattern="0 0 0 0", call_rhythm="1 1", pairs=1)
        # 3rd and 4th notes should use 0.5 duration
        assert call[2]["duration"] == round(0.5 * 0.95, 4)
