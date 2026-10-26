"""Classic plasma: three interfering sine fields plus a radial wave."""

from .base import Effect, SIN85
from .. import palettes


class Plasma(Effect):
    name = "plasma"
    title = "PLASMA"
    bars = 8

    def setup(self, cv):
        w, h = cv.w, cv.h
        self.wx = [
            tuple((x * 3) & 255 for x in range(w)),
            tuple((x * 5) & 255 for x in range(w)),
            tuple((x * 9) & 255 for x in range(w)),
        ]
        self.wy = [
            tuple((y * 4) & 255 for y in range(h)),
            tuple((y * 2) & 255 for y in range(h)),
            tuple((y * 6) & 255 for y in range(h)),
        ]
        cx, cy = w * 0.5, h * 0.5
        self.rdx = tuple(int((x - cx) * (x - cx) * 0.10) for x in range(w))
        self.rdy = tuple(int((y - cy) * (y - cy) * 0.10) for y in range(h))
        self._pal = palettes.ramp_hue(256)
        self._pal2 = palettes.ramp_fire(256)

    def render(self, cv, t, m):
        w, h = cv.w, cv.h
        buf = cv.buf
        S = SIN85
        wx0, wx1, wx2 = self.wx
        wy0, wy1, wy2 = self.wy
        rdx, rdy = self.rdx, self.rdy
        tt = int(t * 34.0)
        t2 = tt + int(m.kick * 12.0)
        tr = int(t * 55.0) + int(m.bass * 20.0)
        for y in range(h):
            a = wy0[y] + tt
            b = wy1[y] - t2
            c = wy2[y] + tt * 2
            rr = rdy[y] - tr
            base = y * w
            for x in range(w):
                v = (S[(wx0[x] + a) & 255]
                     + S[(wx1[x] - b) & 255]
                     + S[(wx2[x] + c) & 255]
                     + (S[(rdx[x] + rr) & 255] >> 2))
                buf[base + x] = v & 255

    def palette(self, t, m=None):
        kick = m.kick if m else 0.0
        shift = int(t * 26.0 + kick * 40.0)
        pal = palettes.rotate(self._pal, shift)
        if kick > 0.55:
            # flash brighter on the beat without rebuilding the ramp
            f = (kick - 0.55) * 0.9
            pal = tuple(
                (min(255, int(r + (255 - r) * f)),
                 min(255, int(g + (255 - g) * f)),
                 min(255, int(b + (255 - b) * f)))
                for r, g, b in pal
            )
        return pal
