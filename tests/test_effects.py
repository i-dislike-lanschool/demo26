"""Every effect must render a frame and provide a full 256 colour palette."""

import unittest

from spectrum import effects, songs, stage


class TestEffects(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.score = songs.build()
        cls.st = stage.Stage(cls.score)
        cls.sync = cls.st.sync

    def test_every_effect_renders(self):
        for start, dur, eff in self.st.segments:
            for frac in (0.1, 0.5, 0.9):
                t = start + dur * frac
                rgb = self.st.render(t)
                self.assertEqual(len(rgb), self.st.width * self.st.height * 3,
                                 eff.name)

    def test_palettes_are_full(self):
        for start, dur, eff in self.st.segments:
            pal = eff.palette(dur * 0.5, self.sync.advance(start + dur * 0.5))
            self.assertEqual(len(pal), 256, eff.name)
            for rgb in pal:
                self.assertEqual(len(rgb), 3, eff.name)
                for v in rgb:
                    self.assertTrue(0 <= v <= 255, (eff.name, rgb))

    def test_registry(self):
        self.assertEqual(len(effects.ALL), 11)
        self.assertEqual(set(effects.BY_NAME), {e.name for e in effects.ALL})
        built = effects.build(["plasma", "fire"])
        self.assertEqual([e.name for e in built], ["plasma", "fire"])

    def test_locate_loops(self):
        eff, local, dur = self.st.locate(self.st.total + 1.0)
        self.assertEqual(eff.name, self.st.segments[0][2].name)
        self.assertGreaterEqual(local, 0.0)


if __name__ == "__main__":
    unittest.main()
