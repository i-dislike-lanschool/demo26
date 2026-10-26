"""Texture-mapped tunnel.

The geometry (angle and 1/radius for every pixel) never changes, so it is
computed once in ``setup``.  Per frame the whole effect is then two byte adds
and one lookup per pixel: rotate the texture by shifting the angle, zoom by
shifting the depth.
"""

import math

from .base import Effect, TAU
from .. import palettes


class Tunnel(Effect):
    name = "tunnel"
    title = "TUNNEL"
    bars = 8

    def setup(self, cv):
        w, h = cv.w, cv.h
        n = w * h
        self.ang = [0] * n     # angle, left-shifted by 8 for texture indexing
        self.dep = bytearray(n)
        self.shade = bytearray(n)
        cx, cy = (w - 1) * 0.5, (h - 1) * 0.5
        norm = 1.0 / h
        i = 0
        for y in range(h):
            dy = (y - cy) * norm
            for x in range(w):
                dx = (x - cx) * norm
                r = math.hypot(dx, dy)
                a = math.atan2(dy, dx) * (1.0 / TAU) + 0.5
                self.ang[i] = (int(a * 256.0) & 255) << 8
                if r < 0.004:
                    r = 0.004
                self.dep[i] = int(7.0 / r) & 255
                # near the rim the wall is close and bright, in the middle
                # it vanishes into the dark
                sh = int(190.0 * min(1.0, r * 1.65))
                self.shade[i] = sh
                i += 1

        # A plaid wall: sums of two sine waves in (u, v) texture space.
        tex = bytearray(65536)
        S = palettes.__dict__  # not used; keep the table local below
        sin8 = [int(127.5 + 127.5 * math.sin(TAU * k / 256.0)) for k in range(256)]
        for v in range(256):
            base = v << 8
            sv = sin8[(v * 2) & 255]
            for u in range(256):
                a = sin8[(u + v) & 255]
                b = sin8[(u * 3 - sv + v) & 255]
                val = (a + b) >> 1
                if (u & 63) < 3:
                    val = 255 - val  # bright spokes every quarter turn
                tex[base + u] = val
        self.tex = tex
        self._pal = palettes.ramp_copper(256)

    def render(self, cv, t, m):
        ang = self.ang
        dep = self.dep
        shade = self.shade
        tex = self.tex
        buf = cv.buf
        rot = int(t * 16.0) * 256
        zoom = int(t * 70.0 + m.kick * 10.0)
        n = cv.size
        for i in range(n):
            buf[i] = (tex[(((ang[i] + rot) & 0xFF00)
                          | ((dep[i] + zoom) & 0xFF))] + shade[i]) & 255

    def palette(self, t, m=None):
        spin = int(t * 30.0)
        return palettes.rotate(self._pal, spin)
