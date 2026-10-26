"""Tests for the bitmap font."""

import unittest

from spectrum import font


class TestFont(unittest.TestCase):
    def test_glyph_shape(self):
        for ch, rows in font.FONT.items():
            self.assertEqual(len(rows), font.GLYPH_H, ch)
            for row in rows:
                self.assertTrue(0 <= row <= 0xFF, ch)

    def test_known_glyphs(self):
        # "N" must have its two verticals at the outer columns
        n = font.glyph("N")
        self.assertEqual(n[0] & 0xF8, 0x88)
        # a space is empty
        self.assertEqual(tuple(font.glyph(" ")), (0,) * font.GLYPH_H)

    def test_cyrillic_and_aliases(self):
        for ch in "ПРИВЕТ МИР ЁЙ ♪ ♥ ->":
            self.assertTrue(font.supports(ch), ch)

    def test_text_width(self):
        self.assertEqual(font.text_width("AB"), font.GLYPH_W * 2 + 1)


if __name__ == "__main__":
    unittest.main()
