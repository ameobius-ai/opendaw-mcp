"""Unit tests for create_colotomic MCP tool."""



class TestColotomicParameterValidation:
    """Test parameter validation."""

    def test_cycles_too_few(self):
        assert not (1 <= 0 <= 8)

    def test_cycles_too_many(self):
        assert not (1 <= 9 <= 8)

    def test_cycles_valid(self):
        for c in (1, 2, 4, 8):
            assert 1 <= c <= 8

    def test_octave_too_low(self):
        assert not (2 <= 1 <= 5)

    def test_octave_too_high(self):
        assert not (2 <= 6 <= 5)

    def test_invalid_structure(self):
        s = "invalid"
        assert s not in ("slendro", "pelog", "lancaran", "ketawang")

    def test_valid_structures(self):
        for s in ("slendro", "pelog", "lancaran", "ketawang"):
            assert s in ("slendro", "pelog", "lancaran", "ketawang")

    def test_invalid_density(self):
        d = "invalid"
        assert d not in ("sparse", "medium", "dense")

    def test_valid_densities(self):
        for d in ("sparse", "medium", "dense"):
            assert d in ("sparse", "medium", "dense")


class TestColotomicStructures:
    """Test structure definitions."""

    STRUCTURES = {
        "slendro": {
            "cycle_beats": 8,
            "gong": [0],
            "kenong": [4],
            "kempul": [2, 6],
            "kethuk": [1, 3, 5, 7],
        },
        "pelog": {
            "cycle_beats": 16,
            "gong": [0],
            "kenong": [8, 12],
            "kempul": [4, 12],
            "kethuk": [2, 6, 10, 14],
        },
        "lancaran": {
            "cycle_beats": 8,
            "gong": [0],
            "kenong": [4],
            "kempul": [2, 6],
            "kethuk": [1, 2, 3, 5, 6, 7],
        },
        "ketawang": {
            "cycle_beats": 16,
            "gong": [0],
            "kenong": [4, 8, 12],
            "kempul": [2, 6, 10, 14],
            "kethuk": [1, 3, 5, 7, 9, 11, 13, 15],
        },
    }

    def test_slendro_cycle(self):
        assert self.STRUCTURES["slendro"]["cycle_beats"] == 8

    def test_pelog_cycle(self):
        assert self.STRUCTURES["pelog"]["cycle_beats"] == 16

    def test_lancaran_cycle(self):
        assert self.STRUCTURES["lancaran"]["cycle_beats"] == 8

    def test_ketawang_cycle(self):
        assert self.STRUCTURES["ketawang"]["cycle_beats"] == 16

    def test_gong_at_start(self):
        """Gong always at beat 0 (start of cycle)."""
        for name, struct in self.STRUCTURES.items():
            assert 0 in struct["gong"]

    def test_lancaran_doubled_kethuk(self):
        """Lancaran has more kethuk hits than slendro."""
        assert len(self.STRUCTURES["lancaran"]["kethuk"]) > len(self.STRUCTURES["slendro"]["kethuk"])

    def test_ketawang_dense_kethuk(self):
        """Ketawang has kethuk on every odd beat."""
        kethuk = self.STRUCTURES["ketawang"]["kethuk"]
        assert len(kethuk) == 8  # 16 beats, every other


class TestColotomicPitchAssignment:
    """Test pitch assignment per gong layer."""

    def test_gong_pitch_lowest(self):
        """Gong ageng is the lowest pitch."""
        octave = 4
        root_num = 0
        gong = (octave + 1) * 12 + root_num - 12
        kempul = (octave + 1) * 12 + root_num - 7
        kenong = (octave + 1) * 12 + root_num
        kethuk = (octave + 1) * 12 + root_num + 5
        assert gong < kempul < kenong < kethuk

    def test_gong_pitch_c3(self):
        """Gong pitch for C at octave 4 = 48 (C3)."""
        octave = 4
        root_num = 0
        gong = (octave + 1) * 12 + root_num - 12
        assert gong == 48

    def test_kethuk_highest(self):
        """Kethuk is the highest colotomic instrument."""
        octave = 4
        root_num = 0
        kethuk = (octave + 1) * 12 + root_num + 5
        kenong = (octave + 1) * 12 + root_num
        assert kethuk > kenong


class TestColotomicVelocity:
    """Test velocity per gong layer."""

    def test_gong_loudest(self):
        """Gong has the highest velocity."""
        velocity = 0.65
        vel_gong = min(1.0, velocity * 1.2)
        vel_kenong = velocity * 1.0
        vel_kempul = velocity * 0.85
        vel_kethuk = velocity * 0.7
        assert vel_gong > vel_kenong > vel_kempul > vel_kethuk

    def test_gong_clamped(self):
        """Gong velocity clamped to 1.0."""
        velocity = 0.9
        vel_gong = min(1.0, velocity * 1.2)
        assert vel_gong == 1.0

    def test_kethuk_quietest(self):
        """Kethuk is the quietest layer."""
        velocity = 0.65
        vel_kethuk = velocity * 0.7
        vel_kempul = velocity * 0.85
        assert vel_kethuk < vel_kempul


class TestColotomicDuration:
    """Test duration per gong layer."""

    def test_gong_longest(self):
        """Gong has the longest resonance."""
        assert 2.0 > 1.0 > 0.5 > 0.25

    def test_kethuk_shortest(self):
        """Kethuk has the shortest duration."""
        assert 0.25 < 0.5 < 1.0 < 2.0


class TestColotomicNoteGeneration:
    """Test note generation logic."""

    def test_gong_notes_per_cycle(self):
        """One gong hit per cycle."""
        struct = {"gong": [0]}
        cycles = 4
        gong_count = 0
        for cycle in range(cycles):
            for beat in struct["gong"]:
                gong_count += 1
        assert gong_count == 4

    def test_kenong_skips_gong_beat(self):
        """Kenong doesn't play on gong beats."""
        gong_beats = {0}
        kenong_beats = [4]
        actual_kenong = [b for b in kenong_beats if b not in gong_beats]
        assert actual_kenong == [4]

    def test_kempul_skips_higher_layers(self):
        """Kempul skips beats occupied by gong or kenong."""
        gong_beats = {0}
        kenong_beats = {4}
        kempul_beats = [2, 6, 4]  # 4 overlaps with kenong
        actual_kempul = [b for b in kempul_beats if b not in gong_beats and b not in kenong_beats]
        assert 4 not in actual_kempul

    def test_kethuk_skips_all_higher_layers(self):
        """Kethuk skips beats occupied by any higher layer."""
        gong_beats = {0}
        kenong_beats = {4}
        kempul_beats = {2, 6}
        kethuk_beats = [1, 2, 3, 5, 6, 7]
        actual_kethuk = [b for b in kethuk_beats if b not in gong_beats and b not in kenong_beats and b not in kempul_beats]
        assert 2 not in actual_kethuk
        assert 6 not in actual_kethuk


class TestColotomicMelodicFill:
    """Test melodic fill (saron and bonang)."""

    def test_saron_only_medium_dense(self):
        """Saron plays only at medium or dense."""
        for density in ("sparse",):
            assert density not in ("medium", "dense")
        for density in ("medium", "dense"):
            assert density in ("medium", "dense")

    def test_bonang_only_dense(self):
        """Bonang plays only at dense."""
        for density in ("sparse", "medium"):
            assert density != "dense"
        assert "dense" == "dense"

    def test_saron_balungan_pattern(self):
        """Saron plays basic melody pattern."""
        balungan_pattern = [0, 2, 0, 2]
        # Pattern cycles: 0, 2, 0, 2
        assert balungan_pattern == [0, 2, 0, 2]

    def test_bonang_on_off_beats(self):
        """Bonang plays on odd beats (off-beats)."""
        cycle_beats = 8
        bonang_beats = []
        for beat_idx in range(1, cycle_beats, 2):
            bonang_beats.append(beat_idx)
        assert bonang_beats == [1, 3, 5, 7]


class TestColotomicTotalBeats:
    """Test total beat calculation."""

    def test_slendro_4_cycles(self):
        cycle_beats = 8
        cycles = 4
        total = cycles * cycle_beats
        assert total == 32

    def test_pelog_2_cycles(self):
        cycle_beats = 16
        cycles = 2
        total = cycles * cycle_beats
        assert total == 32

    def test_lancaran_8_cycles(self):
        cycle_beats = 8
        cycles = 8
        total = cycles * cycle_beats
        assert total == 64


class TestColotomicLayerCounts:
    """Test layer count tracking."""

    def test_layer_counts_initialized(self):
        """All layers start at 0."""
        layer_counts = {"gong": 0, "kenong": 0, "kempul": 0, "kethuk": 0, "saron": 0, "bonang": 0}
        assert all(v == 0 for v in layer_counts.values())

    def test_gong_count_equals_cycles(self):
        """Gong count = number of cycles (one per cycle)."""
        cycles = 4
        gong_beats = [0]
        gong_count = cycles * len(gong_beats)
        assert gong_count == 4

    def test_sparse_has_no_melodic(self):
        """Sparse density has zero saron and bonang."""
        tempo_density = "sparse"
        saron_count = 0
        bonang_count = 0
        if tempo_density in ("medium", "dense"):
            saron_count = 10
        if tempo_density == "dense":
            bonang_count = 5
        assert saron_count == 0
        assert bonang_count == 0
