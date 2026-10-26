"""Rotating vector torus over a starfield -- wireframe, dots and depth."""

import math

from .base import Effect, Starfield
from .. import palettes


class VectorTorus(Effect):
    name = "vector"
    title = "VECTOR"
    bars = 8

    def setup(self, cv):
        self.w = cv.w
        self.h = cv.h
        self.cx = (cv.w - 1) * 0.5
        self.cy = (cv.h - 1) * 0.5
        self.stars = Starfield(90, seed=23, width=cv.w, height=cv.h)
        rings, tube = 22, 12
        self.rings = rings
        self.tube = tube
        pts = []
        for i in range(rings):
            u = i / rings * 2.0 * math.pi
            cu, su = math.cos(u), math.sin(u)
            for j in range(tube):
                v = j / tube * 2.0 * math.pi
                r = 1.0 + 0.42 * math.cos(v)
                pts.append((r * cu, 0.42 * math.sin(v), r * su))
        self.pts = pts
        self.proj = [(0.0, 0.0, 0.0)] * len(pts)
        self._pal = palettes.ramp_ice(256)

    def render(self, cv, t, m):
        w, h = cv.w, cv.h
        buf = cv.buf
        # starfield gives the torus something to sit in front of
        self.stars.render(cv, t * 0.4, 0.7, tuple(range(6, 30)))

        ax = t * 0.85
        ay = t * 0.55 + m.bass * 0.35
        az = t * 0.22
        ca, sa = math.cos(ax), math.sin(ax)
        cb, sb = math.cos(ay), math.sin(ay)
        cc, sc = math.cos(az), math.sin(az)
        scale = h * 0.56
        cx, cy = self.cx, self.cy
        proj = self.proj
        pulse = 1.0 + m.kick * 0.10
        for k, (x, y, z) in enumerate(self.pts):
            x *= pulse
            y *= pulse
            z *= pulse
            # rotate X, then Y, then Z
            y1 = y * ca - z * sa
            z1 = y * sa + z * ca
            x1 = x * cb + z1 * sb
            z2 = -x * sb + z1 * cb
            x2 = x1 * cc - y1 * sc
            y2 = x1 * sc + y1 * cc
            persp = 2.9 / (z2 + 4.6)
            proj[k] = (cx + x2 * persp * scale, cy + y2 * persp * scale,
                       (z2 + 1.42) * 0.35)

        rings, tube = self.rings, self.tube
        light = (int(t * 40.0)) & 255
        idx_shift = int(m.kick * 30)
        for i in range(rings):
            base = i * tube
            nxt = ((i + 1) % rings) * tube
            for j in range(tube):
                a = proj[base + j]
                b = proj[base + (j + 1) % tube]
                c = proj[nxt + j]
                cold = int(150 - 90 * a[2]) + idx_shift
                colour = (cold + light) & 255
                self._line(buf, w, h, a[0], a[1], b[0], b[1], colour)
                self._line(buf, w, h, a[0], a[1], c[0], c[1], colour)
        # sparkle the vertices
        for p in proj:
            x = int(p[0])
            y = int(p[1])
            if 0 <= x < w and 0 <= y < h:
                buf[y * w + x] = (240 + idx_shift) & 255

    @staticmethod
    def _line(buf, w, h, x0, y0, x1, y1, c):
        x0 = int(x0)
        y0 = int(y0)
        x1 = int(x1)
        y1 = int(y1)
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            if 0 <= x0 < w and 0 <= y0 < h:
                buf[y0 * w + x0] = c
            if x0 == x1 and y0 == y1:
                break
            e2 = err * 2
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def palette(self, t, m=None):
        return palettes.rotate(self._pal, int(t * 24.0))
