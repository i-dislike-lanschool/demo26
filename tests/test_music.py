"""Tests for the score, the synth and the music analysis."""

import unittest

from spectrum import music_sync, songs, synth, wav


class TestScore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.score = songs.build()

    def test_basics(self):
        self.assertGreater(self.score.total_time, 60)
        self.assertGreater(len(self.score.notes), 100)
        self.assertGreater(len(self.score.drums), 50)

    def test_events_sorted(self):
        times = [ev.time for ev in self.score.events]
        self.assertEqual(times, sorted(times))

    def test_sections(self):
        self.assertTrue(self.score.sections)
        self.assertTrue(self.score.section_at(0))

    def test_parse_note(self):
        from spectrum.score import parse_note
        from spectrum.synth import midi_to_freq
        midi, steps = parse_note("a4:4")
        self.assertEqual(midi, 69)
        self.assertEqual(steps, 4)
        self.assertAlmostEqual(midi_to_freq(69), 440.0, places=1)


class TestSynth(unittest.TestCase):
    def test_render(self):
        score = songs.build()
        mixer = synth.Mixer(score)
        import array
        n = int(2.0 * synth.SR)
        out = mixer.fill(n)
        self.assertEqual(len(out), n * 2 * 2)  # stereo, int16
        pcm = array.array("h")
        pcm.frombytes(bytes(out))
        peak = max(abs(v) / 32768.0 for v in pcm)
        self.assertLessEqual(peak, 1.0)
        self.assertGreater(peak, 0.05)

    def test_wav_header(self):
        data = wav.encode_wav([0.0, 0.5, -0.5, 0.0], 22050, 1)
        self.assertEqual(data[0:4], b"RIFF")
        self.assertEqual(data[8:12], b"WAVE")


class TestMusicSync(unittest.TestCase):
    def test_advance(self):
        score = songs.build()
        sync = music_sync.MusicSync(score)
        st = sync.advance(5.0)
        for attr in ("kick", "snare", "hat", "flash", "bass"):
            self.assertTrue(hasattr(st, attr), attr)
        self.assertEqual(len(st.bands), music_sync.BANDS)
        self.assertGreaterEqual(sync.level(), 0.0)
        self.assertTrue(0.0 <= sync.beat_phase() < 1.0)


if __name__ == "__main__":
    unittest.main()
