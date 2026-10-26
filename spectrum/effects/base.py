"""Shared bits for the demo effects: tables, helpers, the Effect base class."""

import math
import random

from .. import font, palettes

TAU = 2.0 * math.pi

# Three flavours of the same sine, so a plasma can add three wave lookups and
# get a full 0..255 range out of it without a single division.
SIN01 = tuple(0.5 + 0.5 * math.sin(TAU * i / 256.0) for i in range(256))
SIN8 = tuple(int(v * 255.0) for v in SIN01)
SIN85 = tuple(int(v * 85.0) for v in SIN01)
SIN128 = tuple(int(v * 128.0) for v in SIN01)
COS8 = tuple(SIN8[(i + 64) & 255] for i in range(256))


def clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)


class Effect:
    """One scene.  ``render`` gets local time and the music state."""

    name = "effect"
    title = "EFFECT"
    bars = 8            # length of the scene, in bars of music
    palette_name = ""

    def setup(self, cv):
        """Precompute tables for a given canvas size."""

    def render(self, cv, t, m):
        raise NotImplementedError

    def palette(self, t, m=None):
        """The RGB palette for this frame; effects rotate it over time."""
        return palettes.ramp_hue(256)


# ------------------------------------------------------------------ utilities
def scaled(text, scale, spacing=1):
    return font.text_width(text, scale, spacing)


def draw_glyph(cv, x, y, ch, scale, color):
    """Draw a single character; returns its advance width."""
    table = font.FONT
    g = table.get(ch) or table.get(ch.upper()) or table["?"]
    buf = cv.buf
    w, h = cv.w, cv.h
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
                            buf[base + xx + sx] = color
    return font.GLYPH_W * scale + 1


def chrome_text(cv, x, y, text, scale, ramp, spacing=1, shadow=None):
    """Text where every scanline of the letters takes the next ramp colour.

    The ramp is a list of palette indices; it makes the classic "chrome" logo
    look without needing more than 8 lines of bitmap.
    """
    table = font.FONT
    unknown = table["?"]
    buf = cv.buf
    w, h = cv.w, cv.h
    step = font.GLYPH_W * scale + spacing
    for ch in text:
        g = table.get(ch) or table.get(ch.upper()) or unknown
        for row in range(font.GLYPH_H):
            bits = g[row]
            if not bits:
                continue
            color = ramp[row % len(ramp)]
            for sy in range(scale):
                yy = y + row * scale + sy
                if yy >= h:
                    continue
                if shadow is not None and row == font.GLYPH_H - 1:
                    for col in range(font.GLYPH_W):
                        if bits & (0x80 >> col):
                            xx = x + col * scale
                            if 0 <= xx < w:
                                buf[yy * w + xx] = shadow
                base = yy * w
                for col in range(font.GLYPH_W):
                    if bits & (0x80 >> col):
                        xx = x + col * scale
                        if not (0 <= xx < w):
                            continue
                        for sx in range(scale):
                            if xx + sx < w:
                                buf[base + xx + sx] = color
        x += step
    return x


def sine_scroller(cv, text, t, y_base, amp, wavelength, speed, colors,
                  scale=2, shadow=True):
    """One line of sine-wave scrolling text, the demo-scene way."""
    w, h = cv.w, cv.h
    offs = []
    for x in range(w):
        offs.append(int(amp * math.sin((x / wavelength) * TAU + t * 1.7)
                        + amp * 0.35 * math.sin((x / (wavelength * 0.41)) * TAU
                                                - t * 2.3)))
    width = font.text_width(text, scale, 1)
    span = width + w
    start = int(t * speed) % span
    x0 = w - start
    # draw right to left so a character can never overwrite its neighbour's tail
    for i, ch in enumerate(text):
        gx = x0 + i * (font.GLYPH_W * scale + 1)
        if gx + font.GLYPH_W * scale < 0 or gx >= w:
            continue
        table = font.FONT
        g = table.get(ch) or table.get(ch.upper()) or table["?"]
        color = colors[(i + int(t * 8)) % len(colors)]
        for row in range(font.GLYPH_H):
            bits = g[row]
            if not bits:
                continue
            for col in range(font.GLYPH_W):
                if not (bits & (0x80 >> col)):
                    continue
                xx = gx + col * scale
                for sx in range(scale):
                    px = xx + sx
                    if not (0 <= px < w):
                        continue
                    yy = y_base + offs[px] + row * scale
                    for sy in range(scale):
                        if 0 <= yy + sy < h:
                            cv.buf[(yy + sy) * w + px] = color
        if shadow:
            for row in range(font.GLYPH_H):
                bits = g[row]
                if not bits:
                    continue
                for col in range(font.GLYPH_W):
                    if not (bits & (0x80 >> col)):
                        continue
                    px = gx + col * scale + scale
                    if not (0 <= px < w):
                        continue
                    yy = y_base + offs[px] + row * scale + scale
                    for sy in range(scale):
                        if 0 <= yy + sy < h:
                            cv.buf[(yy + sy) * w + px] = 0


class Starfield:
    """Cheap 3D starfield that also powers the logos' backgrounds."""

    def __init__(self, count=140, seed=7, width=192, height=108, spread=1.0):
        rnd = random.Random(seed)
        self.w = width
        self.h = height
        self.stars = []
        for _ in range(count):
            self.stars.append([
                rnd.uniform(-spread, spread),
                rnd.uniform(-spread, spread),
                rnd.uniform(0.08, 1.0),
                rnd.uniform(0.75, 1.35),   # speed multiplier
            ])

    def render(self, cv, t, speed, ramp, warp=0.0, cx=None, cy=None):
        w, h = cv.w, cv.h
        cx = w * 0.5 if cx is None else cx
        cy = h * 0.5 if cy is None else cy
        scale = h * 0.55
        buf = cv.buf
        n = len(ramp)
        for s in self.stars:
            z = s[2] - speed * s[3] * 0.016
            if z <= 0.02:
                s[2] = 1.0
                s[0] = (s[0] * 1.37 + 0.11) % 2.0 - 1.0
                s[1] = (s[1] * 1.91 + 0.37) % 2.0 - 1.0
                z = 1.0
            s[2] = z
            inv = 1.0 / z
            x = cx + s[0] * inv * scale
            y = cy + s[1] * inv * scale
            if not (0 <= x < w and 0 <= y < h):
                continue
            idx = clamp(int((1.0 - z) * n), 0, n - 1)
            color = ramp[idx]
            xi = int(x)
            yi = int(y)
            buf[yi * w + xi] = color
            if warp > 0.35:
                # stretch the star into a streak when the music kicks
                ln = int(warp * z * 3.0)
                for k in range(1, ln + 1):
                    xx = int(cx + s[0] * (inv + k * 0.02) * scale)
                    yy = int(cy + s[1] * (inv + k * 0.02) * scale)
                    if 0 <= xx < w and 0 <= yy < h:
                        buf[yy * w + xx] = ramp[clamp(idx - k * 2, 0, n - 1)]
