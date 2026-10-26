"""Copper bars: fat wavy rasters with a vertical gradient, the Amiga way."""

from .base import Effect, SIN8
from .. import palettes

NBARS = 6
BAR_ENTRIES = 36                 # palette entries per bar ramp
BG = 256 - NBARS * BAR_ENTRIES   # background occupies the top of the palette


def _palette():
    out = []
    # a few dark indigo entries for the backdrop
    out += palettes.gradient([(2, 0, 10), (6, 2, 26), (12, 4, 40), (6, 2, 26),
                              (2, 0, 10)], BG)
    hues = [(255, 120, 40), (255, 220, 90), (90, 220, 255),
            (255, 90, 160), (140, 255, 140), (255, 255, 255)]
    for rgb in hues:
        dark = tuple(v // 6 for v in rgb)
        mid = tuple(v // 2 for v in rgb)
        hot = tuple(min(255, v + 90) for v in rgb)
        half = BAR_ENTRIES // 2
        up = palettes.gradient([dark, mid, rgb, hot], half)
        down = palettes.gradient([hot, rgb, mid, dark], BAR_ENTRIES - half)
        out += up + down
    while len(out) < 256:
        out.append((0, 0, 0))
    return tuple(out[:256])


PAL = _palette()


class Copper(Effect):
    name = "copper"
    title = "COPPER"
    bars = 8

    def setup(self, cv):
        w, h = cv.w, cv.h
        self.rasters = [
            dict(y=0.14, phase=0.0, speed=1.0, thick=13, hue=0),
            dict(y=0.30, phase=1.7, speed=-0.7, thick=9, hue=1),
            dict(y=0.46, phase=3.1, speed=1.4, thick=15, hue=2),
            dict(y=0.62, phase=0.8, speed=-1.1, thick=9, hue=3),
            dict(y=0.78, phase=2.4, speed=0.9, thick=13, hue=4),
            dict(y=0.87, phase=4.2, speed=-1.6, thick=7, hue=5),
        ]
        self.sparks = [(x * 37 % w, x * 61 % h, (x % 5) + 1)
                       for x in range(26)]
        # per-bar gradient rows, as bytes, ready to stamp into the buffer
        self.band_cache = {}

    def _band(self, i, thick):
        key = (i, thick)
        band = self.band_cache.get(key)
        if band is None:
            base = BG + i * BAR_ENTRIES
            rows = []
            for k in range(thick):
                # sample the bar ramp so any thickness fits the gradient
                idx = base + (k * (BAR_ENTRIES - 1)) // max(1, thick - 1)
                rows.append(idx)
            band = bytes(rows)
            self.band_cache[key] = band
        return band

    def render(self, cv, t, m):
        w, h = cv.w, cv.h
        buf = cv.buf
        kick = m.kick
        # dark backdrop with a slow crawling scanline shimmer
        scroll = int(t * 10.0)
        for y in range(h):
            idx = ((y + scroll) >> 2) % BG
            buf[y * w:(y + 1) * w] = bytes((idx,)) * w

        # stars twinkling behind the bars
        for (x, y, speed) in self.sparks:
            yy = int((y + t * speed * 6.0) % h)
            if (int(t * speed * 3.0) + x) % 17 < 3:
                buf[yy * w + x] = 255

        for i, bar in enumerate(self.rasters):
            amp = (9.0 + kick * 10.0) * (0.7 + 0.15 * i)
            phase = int(bar["phase"] * 40 + t * 60.0 * bar["speed"])
            base_y = bar["y"] * h
            thick = bar["thick"] + int(kick * 5)
            band = self._band(i, thick)
            core = BG + i * BAR_ENTRIES + BAR_ENTRIES // 2  # hottest row
            for x in range(w):
                off = (SIN8[(x * 9 + phase) & 255] - 128) * (amp / 128.0)
                y0 = int(base_y + off) - thick // 2
                if y0 < 0 or y0 + thick >= h:
                    continue
                buf[y0 * w + x:(y0 + thick) * w + x:w] = band
                buf[(y0 + thick // 2) * w + x] = core

        # a bouncing line of dots on the beat
        dots = int(4 + kick * 8)
        for i in range(dots):
            x = int((w - 1) * i / max(1, dots - 1))
            y = int(h * 0.5 + _wave(x * 0.13 + t * 3.0) * h * 0.3)
            if 0 <= y < h:
                buf[y * w + x] = 255

    def palette(self, t, m=None):
        return PAL


def _wave(phase):
    """A -1..1 sine without importing math in the inner loop."""
    return (SIN8[int(phase * 40.0) & 255] - 127.5) / 127.5
