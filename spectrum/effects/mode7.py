"""Mode 7: attribute cells, colour clash, and graphics characters.

Each character cell owns its ink and paper colour, which is exactly how the
Spectrum worked -- and why neighbouring characters tint each other's
backgrounds.  The mosaic is made of 24x24 pixel cells, the word in the middle
is drawn over them with per-letter colours, so the clash is real.
"""

import random

from .base import Effect, draw_glyph
from .. import font, palettes

WORD = "SPECTRUM"
SUB = "COLOUR CLASH FOREVER"


class Mode7(Effect):
    name = "mode7"
    title = "COLOUR CLASH"
    bars = 8

    def setup(self, cv):
        w, h = cv.w, cv.h
        rnd = random.Random(0x5EED)
        self.w = w
        self.h = h
        self.cell = 24
        self.cols = w // self.cell
        self.rows = (h - 12) // self.cell
        # A handful of 8x8 "graphics characters", then expand each to 24x24
        # with three pixel wide blocks, pre-built so drawing is just a translate.
        patterns = []
        for i in range(8):
            rows = []
            for y in range(8):
                if i == 0:
                    bits = 0xAA if y % 2 else 0x55
                elif i == 1:
                    bits = 0x80 >> (y % 8)
                elif i == 2:
                    bits = (0xFF if y < 2 else 0x81) if y in (0, 7) else 0x81
                elif i == 3:
                    bits = rnd.randrange(256)
                elif i == 4:
                    bits = 0xF0 if y < 4 else 0x0F
                elif i == 5:
                    bits = (0x00 if y % 2 else 0x3C)
                elif i == 6:
                    bits = rnd.choice((0x18, 0x3C, 0x7E, 0xFF, 0x42, 0x99))
                else:
                    bits = 0x00
                rows.append(bits)
            templates = []
            for y in range(self.cell):
                bits = rows[y // 3]
                row = bytearray(self.cell)
                for x in range(8):
                    on = 1 if bits & (0x80 >> x) else 0
                    row[x * 3:x * 3 + 3] = bytes((on, on, on))
                templates.append(bytes(row))
            patterns.append(templates)
        self.patterns = patterns
        self.cells = []
        for cy in range(self.rows):
            for cx in range(self.cols):
                self.cells.append([
                    rnd.randrange(len(patterns)),   # pattern
                    rnd.randrange(1, 8),            # ink
                    rnd.randrange(0, 8),            # paper
                    rnd.random(),                   # brightness seed
                ])
        self.cmaps = {}
        self.pal = tuple(palettes.SPECCY[i % 16] for i in range(256))
        self._last_kick = 0.0
        self._bar = -1
        self.ink_seq = [1, 2, 3, 4, 5, 6, 7, 1]
        self.paper_seq = [6, 5, 4, 3, 2, 1, 6, 5]

    def _cmap(self, ink, paper):
        key = (ink, paper)
        cm = self.cmaps.get(key)
        if cm is None:
            cm = bytes((paper if i != 1 else ink) for i in range(256))
            self.cmaps[key] = cm
        return cm

    def render(self, cv, t, m):
        w = self.w
        buf = cv.buf
        cell = self.cell
        rnd = random.Random(int(t * 6) * 7919 + 17)
        # new colours on every beat, so the screen flickers like the real thing
        bar = int(m.song_t / (m.beat * 4.0)) if hasattr(m, "beat") else int(t)
        if bar != self._bar:
            self._bar = bar
            for c in self.cells:
                c[0] = rnd.randrange(len(self.patterns))
                c[1] = rnd.randrange(1, 8)
                c[2] = rnd.randrange(0, 8)
        bright = m.kick > 0.35
        # background mosaic
        for idx, cell_data in enumerate(self.cells):
            cy, cx = divmod(idx, self.cols)
            pattern = self.patterns[cell_data[0]]
            ink = cell_data[1]
            paper = cell_data[2]
            if bright:
                ink |= 8
                paper |= 8
            cmap = self._cmap(ink, paper)
            x0 = cx * cell
            y0 = cy * cell
            for r in range(cell):
                base = (y0 + r) * w + x0
                buf[base:base + cell] = pattern[r].translate(cmap)

        # a dark banner strip behind the subtitle, if there is room
        a = (self.rows * cell) * w
        if a + w <= len(buf):
            buf[a:a + w] = bytes(w)

        # the big word, one attribute cell per letter
        y = 40
        x = (w - (font.GLYPH_W * 3 + 1) * len(WORD) + 1) // 2
        shift = int(t * 3.0) % len(WORD)
        for i, ch in enumerate(WORD):
            ink = self.ink_seq[(i + shift) % len(self.ink_seq)]
            paper = self.paper_seq[(i + shift) % len(self.paper_seq)]
            if ink == paper:
                paper = 0
            if bright:
                ink |= 8
                paper |= 8
            cv.fill_rect(x - 2, y - 3, x + font.GLYPH_W * 3 + 1, y + 26, paper)
            draw_glyph(cv, x, y, ch, 3, ink)
            x += font.GLYPH_W * 3 + 1

        # subtitle in single pixels, one colour per letter
        sx = (w - font.text_width(SUB, 1, 1)) // 2
        yy = y + 34
        for i, ch in enumerate(SUB):
            colour = (2 + i) % 7 + 1
            if bright:
                colour |= 8
            draw_glyph(cv, sx + i * 6, yy, ch, 1, colour)

        # scan of letter colours, so each frame is slightly different
        if int(t * 4) % 3 == 0:
            self.ink_seq = self.ink_seq[1:] + self.ink_seq[:1]

    def palette(self, t, m=None):
        return self.pal
