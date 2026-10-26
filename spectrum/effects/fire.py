"""The obligatory fire effect, burning in half resolution and scaled up.

Classic doom-fire propagation: every pixel inherits the heat of the pixels
below it, cooled by a small random amount, so tongues of flame crawl upwards.
The random cooling comes from a precomputed table to keep the loop cheap.
"""

import math
import random

from .base import Effect
from .. import palettes

FIRE = palettes.ramp_fire(256)
FIRE_HOT = tuple(FIRE)  # alias kept for clarity at the call sites

_RND = random.Random(1234)
_COOL = bytes(_RND.randrange(4) for _ in range(4096))  # white-noise cooling


class Fire(Effect):
    name = "fire"
    title = "FIRE"
    bars = 8

    def setup(self, cv):
        w, h = cv.w, cv.h
        self.fw = max(8, w // 2)
        self.fh = max(8, h // 2)
        self.heat = bytearray(self.fw * self.fh)
        self.frame = 0
        self.sparks = [(x * 53 % w, x * 29 % h, 1 + x % 4) for x in range(30)]

    def render(self, cv, t, m):
        fw, fh = self.fw, self.fh
        heat = self.heat
        rnd_frame = self.frame * 97
        # ------------------------------------------------- seed the bottom
        bottom = (fh - 1) * fw
        for x in range(fw):
            v = 255
            if _COOL[(x * 5 + rnd_frame) & 4095] == 3:
                v = 150 + _COOL[(x * 11 + rnd_frame) & 4095] * 20
            heat[bottom + x] = v
        heat[bottom - fw:bottom] = heat[bottom:bottom + fw]

        # ------------------------------------------------------ propagate
        cool = 4 if m.flash > 0.6 else 5
        wind = 1 if math.sin(t * 0.9) > 0.3 else 0
        for y in range(fh - 3, -1, -1):
            row = (y + 1) * fw          # the row below
            dst = y * fw
            slot = (rnd_frame + y * 131) & 4095
            for x in range(fw):
                xl = x - 1 if x > 0 else fw - 1
                xr = x + 1 if x < fw - 1 else 0
                xw = x + wind if x < fw - 1 else x
                v = (heat[row + xl] + heat[row + xw] + heat[row + xr]) // 3
                v -= cool + _COOL[(slot + x * 3) & 4095]
                heat[dst + x] = 0 if v < 0 else v

        # --------------------------------------------------- upscale x2
        buf = cv.buf
        w, h = cv.w, cv.h
        for y in range(min(h, fh * 2)):
            src = (y >> 1) * fw
            dst = y * w
            row = heat[src:src + fw]
            out = bytearray(w)
            for x in range(fw):
                v = row[x]
                out[x * 2] = v
                out[x * 2 + 1] = v
            buf[dst:dst + w] = out

        # embers drifting up through the dark
        for (sx, sy, sp) in self.sparks:
            yy = int((sy - t * sp * 9.0) % h)
            xx = sx + int(3 * math.sin(t * sp + sy))
            if 0 <= xx < w and heat[(yy >> 1) * fw + (xx >> 1)] < 40:
                buf[yy * w + xx] = 250

        self.frame += 1

    def palette(self, t, m=None):
        return FIRE
