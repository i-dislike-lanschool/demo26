"""A byte-indexed framebuffer with the drawing operations the effects need.

The framebuffer is ``bytearray(w * h)`` of palette indices.  Only when a frame
is finished do the indices get expanded to RGB, which keeps per-pixel work in
pure Python down to one or two byte operations.

Handy detail: keep ``width * height <= 65535`` so ``bytes.translate`` can be
used for the palette lookup.  The default 192x108 is the ZX Spectrum's 256x192
screen in 16:9-ish proportions, and 192x108 is also exactly a 64x36 grid of
3x3 pixel attribute cells -- a Spectrum Mode 7 text screen, colour clash and
all.  That is not a coincidence.
"""

import math

from . import font


class Canvas:
    def __init__(self, width, height):
        self.w = width
        self.h = height
        self.size = width * height
        self.buf = bytearray(self.size)
        self._tables = {}

    # ------------------------------------------------------------------ util
    def row_table(self, offset, modulo):
        """Cached ``(x * offset) % modulo`` lookup -- cheap diagonal patterns."""
        key = (offset, modulo)
        t = self._tables.get(key)
        if t is None:
            t = bytes(((x * offset) % modulo) & 0xFF for x in range(self.w))
            self._tables[key] = t
        return t

    def clear(self, value=0):
        self.buf[:] = bytes((value,)) * self.size

    def blit(self, data):
        if len(data) != self.size:
            raise ValueError("framebuffer size mismatch")
        self.buf[:] = data

    def shift_rows(self, v):
        """Cyclically move every row by ``v`` pixels (scroll the whole screen)."""
        if not v:
            return
        v %= self.w
        buf = self.buf
        stride = self.w
        for y in range(self.h):
            i = y * stride
            row = buf[i:i + stride]
            buf[i:i + stride] = row[-v:] + row[:-v]

    def shift_cols(self, v):
        """Cyclically move every column by ``v`` pixels (vertical scroll)."""
        if not v:
            return
        v %= self.h
        buf = self.buf
        stride = self.w
        for x in range(stride):
            col = buf[x::stride]
            buf[x::stride] = col[-v:] + col[:-v]

    # --------------------------------------------------------------- pixels
    def put(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.buf[y * self.w + x] = c

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.buf[y * self.w + x]
        return 0

    def line(self, x0, y0, x1, y1, c):
        """Bresenham between integer points."""
        buf = self.buf
        w, h = self.w, self.h
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            if 0 <= x < w and 0 <= y < h:
                buf[y * w + x] = c
            if x == x1 and y == y1:
                break
            e2 = err * 2
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def disc(self, cx, cy, r, c):
        buf = self.buf
        w, h = self.w, self.h
        if r < 1:
            self.put(int(cx), int(cy), c)
            return
        r2 = r * r
        y0 = max(0, int(cy - r))
        y1 = min(h - 1, int(cy + r) + 1)
        span_byte = bytes((c,))
        for y in range(y0, y1 + 1):
            dy = y - cy
            span = r2 - dy * dy
            if span < 0:
                continue
            half = math.sqrt(span)
            xa = max(0, int(cx - half))
            xb = min(w - 1, int(cx + half))
            if xb >= xa:
                base = y * w
                buf[base + xa:base + xb + 1] = span_byte * (xb - xa + 1)

    def ring(self, cx, cy, r, c, steps=None):
        """Circle outline, drawn as a polygon to keep it cheap."""
        if r < 0.5:
            return
        steps = steps or max(12, int(r * 6))
        for i in range(steps):
            a = (i / steps) * 2.0 * math.pi
            self.put(int(cx + math.cos(a) * r), int(cy + math.sin(a) * r), c)

    def fill_rect(self, x0, y0, x1, y1, c):
        x0, x1 = max(0, int(x0)), min(self.w - 1, int(x1))
        y0, y1 = max(0, int(y0)), min(self.h - 1, int(y1))
        if x1 < x0 or y1 < y0:
            return
        span = bytes((c,)) * (x1 - x0 + 1)
        w = self.w
        for y in range(y0, y1 + 1):
            base = y * w
            self.buf[base + x0:base + x1 + 1] = span

    # ----------------------------------------------------------------- text
    def text(self, x, y, s, c, scale=1, spacing=1, shadow=None):
        """Draw ``s`` with the bitmap font.  Returns the x after the last glyph."""
        buf = self.buf
        w, h = self.w, self.h
        table = font.FONT
        unknown = table["?"]
        step = font.GLYPH_W * scale + spacing
        for ch in s:
            g = table.get(ch) or table.get(ch.upper()) or unknown
            if shadow is not None:
                for row in range(font.GLYPH_H):
                    bits = g[row]
                    if not bits:
                        continue
                    yy = y + row * scale + scale
                    if 0 <= yy < h:
                        for sy in range(scale):
                            if yy + sy >= h:
                                break
                            base = (yy + sy) * w
                            for col in range(font.GLYPH_W):
                                if bits & (0x80 >> col):
                                    xx = x + col * scale + scale
                                    if 0 <= xx < w:
                                        buf[base + xx] = shadow
            for row in range(font.GLYPH_H):
                bits = g[row]
                if not bits:
                    continue
                for col in range(font.GLYPH_W):
                    if bits & (0x80 >> col):
                        xx = x + col * scale
                        if not (0 <= xx < w):
                            continue
                        for sy in range(scale):
                            yy = y + row * scale + sy
                            if yy >= h:
                                break
                            base = yy * w
                            for sx in range(scale):
                                if xx + sx < w:
                                    buf[base + xx + sx] = c
            x += step
        return x

    def text_center(self, y, s, c, scale=1, spacing=1, shadow=None):
        x = (self.w - font.text_width(s, scale, spacing)) // 2
        return self.text(x, y, s, c, scale, spacing, shadow)

    # ------------------------------------------------------- mode 7 text
    def text_mode7(self, col, row, s, inks, papers, bright, cell_w=3, cell_h=3):
        """Draw text in attribute cells, Spectrum Mode 7 style.

        Every character gets its own 8x8 cell with its own ink and paper, so
        backgrounds collide exactly like the old colour-clash hardware did.
        ``inks`` / ``papers`` are lists of 0..7 colours, one per character
        (indexed modulo their length).
        """
        table = font.FONT
        unknown = table["?"]
        buf = self.buf
        w, h = self.w, self.h
        for i, ch in enumerate(s):
            g = table.get(ch) or table.get(ch.upper()) or unknown
            ink = inks[i % len(inks)] | (8 if bright else 0)
            paper = papers[i % len(papers)] | (8 if bright else 0)
            x0 = (col + i) * font.GLYPH_W * cell_w
            y0 = row * font.GLYPH_H * cell_h
            if x0 >= w:
                continue
            for gy in range(font.GLYPH_H):
                bits = g[gy]
                yy = y0 + gy * cell_h
                if yy >= h:
                    break
                for gx in range(font.GLYPH_W):
                    xx = x0 + gx * cell_w
                    if xx >= w:
                        break
                    color = ink if (bits & (0x80 >> gx)) else paper
                    span = bytes((color,)) * cell_w
                    for sy in range(cell_h):
                        if yy + sy >= h:
                            break
                        base = (yy + sy) * w
                        buf[base + xx:base + xx + cell_w] = span
        del buf

    # ---------------------------------------------------------------- rgb out
    def to_rgb(self, pal256):
        """Expand palette indices to RGB bytes -- three per pixel.

        ``b"".join`` over a pre-split table is the fastest pure-Python way to
        do this (about 0.6 ms for a 192x108 frame); ``bytes.translate`` cannot
        map one byte to three.
        """
        flat = bytes(b for rgb in pal256 for b in rgb)
        triples = [flat[i * 3:i * 3 + 3] for i in range(256)]
        return b"".join([triples[i] for i in self.buf])
