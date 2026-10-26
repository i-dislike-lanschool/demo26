"""Tests for the framebuffer and the PNG writer."""

import struct
import unittest
import zlib

from spectrum import canvas, palettes, png


class TestCanvas(unittest.TestCase):
    def setUp(self):
        self.cv = canvas.Canvas(16, 10)

    def test_clear_and_put(self):
        self.cv.clear(7)
        self.assertEqual(set(self.cv.buf), {7})
        self.cv.put(3, 4, 9)
        self.assertEqual(self.cv.get(3, 4), 9)

    def test_line_and_rect(self):
        self.cv.clear(0)
        self.cv.line(0, 0, 15, 9, 5)
        self.cv.fill_rect(2, 2, 4, 4, 6)
        self.assertEqual(self.cv.get(3, 3), 6)
        self.assertIn(5, self.cv.buf)

    def test_text(self):
        self.cv.clear(0)
        self.cv.text(0, 0, "HI", 1)
        self.assertGreater(sum(1 for v in self.cv.buf if v), 10)

    def test_to_rgb_length_and_mapping(self):
        pal = palettes.ramp_gray(256)
        self.cv.clear(0)
        self.cv.put(0, 0, 200)
        rgb = self.cv.to_rgb(pal)
        self.assertEqual(len(rgb), 16 * 10 * 3)
        self.assertEqual(tuple(rgb[0:3]), pal[200])


class TestPng(unittest.TestCase):
    def test_roundtrip(self):
        w, h = 5, 4
        rgb = bytes((x * 7 + y) % 256 for y in range(h) for x in range(w)
                    for _ in range(3))
        data = png.encode_rgb(w, h, rgb)
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        # parse IHDR
        self.assertEqual(data[12:16], b"IHDR")
        iw, ih, depth, ctype = struct.unpack(">IIBB", data[16:26])
        self.assertEqual((iw, ih, depth, ctype), (w, h, 8, 2))
        # decode IDAT and compare pixels
        idat = b""
        pos = 8
        while pos < len(data):
            ln = struct.unpack(">I", data[pos:pos + 4])[0]
            tag = data[pos + 4:pos + 8]
            if tag == b"IDAT":
                idat += data[pos + 8:pos + 8 + ln]
            pos += 12 + ln
        raw = zlib.decompress(idat)
        stride = w * 3
        for y in range(h):
            row = raw[y * (stride + 1):(y + 1) * (stride + 1)]
            self.assertEqual(row[0], 0)  # filter: none
            self.assertEqual(bytes(row[1:]), rgb[y * stride:(y + 1) * stride])

    def test_scale_nearest(self):
        rgb = bytes(range(12))  # 2x2 rgb
        big = png.scale_nearest(2, 2, rgb, 3)
        self.assertEqual(len(big), 6 * 6 * 3)
        self.assertEqual(big[0:3], rgb[0:3])
        self.assertEqual(big[3:6], rgb[0:3])


if __name__ == "__main__":
    unittest.main()
