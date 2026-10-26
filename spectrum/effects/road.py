"""Night drive: stars, a sliced sun and an endless neon grid.

Every colour the scene needs is packed into one 256 entry palette, so the
per-pixel work is just picking an index.
"""

from .base import Effect, Starfield
from .. import palettes

SKY = 0        # 0..63   sky gradient
SUN = 64       # 64..127 sun
FLOOR = 128    # 128..191 floor
GRID = 192     # 192..223 grid lines
STAR = 224     # 224..255 stars and accents


def _palette():
    """Each scene range gets its own gradient, packed end to end."""
    sky = palettes.gradient(
        [(0, 0, 0), (3, 0, 14), (8, 0, 30), (18, 0, 48), (34, 0, 62),
         (60, 4, 74), (100, 10, 82), (150, 22, 84), (215, 44, 78),
         (255, 96, 64)], 64)
    sun = palettes.gradient(
        [(255, 246, 160), (255, 220, 80), (255, 170, 40), (255, 110, 40),
         (240, 50, 60), (200, 24, 70), (150, 12, 60)], 64)
    floor = palettes.gradient(
        [(6, 0, 20), (14, 2, 38), (26, 4, 60), (44, 8, 84), (72, 14, 110),
         (110, 26, 140), (170, 50, 170), (255, 110, 210)], 64)
    grid = palettes.gradient(
        [(60, 0, 90), (120, 10, 150), (200, 40, 210), (255, 90, 240),
         (0, 90, 120), (0, 170, 200), (0, 230, 245), (160, 255, 255)], 32)
    star = palettes.gradient(
        [(30, 50, 80), (90, 140, 200), (170, 220, 255), (255, 255, 255)], 32)
    return tuple(sky + sun + floor + grid + star)


PAL256 = _palette()


class NeonRoad(Effect):
    name = "road"
    title = "NEON ROAD"
    bars = 8

    def setup(self, cv):
        w, h = cv.w, cv.h
        self.horizon = int(h * 0.42)
        self.stars = Starfield(70, seed=11, width=w, height=h)
        self.cx = (w - 1) * 0.5
        self.sky_rows = []
        hz = max(1, self.horizon)
        for y in range(hz):
            self.sky_rows.append(SKY + (y * 63) // hz)
        self.sun_r = int(h * 0.19)
        self.sun_cy = self.horizon - int(h * 0.02)

    def render(self, cv, t, m):
        w, h = cv.w, cv.h
        buf = cv.buf
        horizon = self.horizon
        # ------------------------------------------------------------- sky
        for y in range(horizon):
            buf[y * w:(y + 1) * w] = bytes((self.sky_rows[y],)) * w

        # ------------------------------------------------------------- sun
        cx, cy, r = self.cx, self.sun_cy, self.sun_r
        k = 0
        for y in range(max(0, int(cy - r)), min(horizon, int(cy + r) + 1)):
            dy = y - cy
            half = (r * r - dy * dy)
            if half <= 0:
                continue
            half = half ** 0.5
            # cut the sun into slices that thin out towards the top
            phase = (y - int(t * 8.0)) % 9
            if phase < 1 + max(0, int((y - (cy - r * 0.45)) // 3)):
                continue
            x0 = int(cx - half)
            x1 = int(cx + half)
            col = SUN + int(((y - (cy - r)) * 63) / max(1.0, 2 * r))
            a0, a1 = max(0, x0), min(w, x1 + 1)
            if a1 > a0:
                buf[y * w + a0:y * w + a1] = bytes((col,)) * (a1 - a0)
            k += 1

        # ----------------------------------------------------------- stars
        self.stars.render(cv, t, 0.9 + m.kick * 1.4,
                          tuple(range(STAR, STAR + 32)), warp=m.kick * 0.8,
                          cx=cx, cy=cy)

        # ----------------------------------------------------------- floor
        speed = 55.0 + m.kick * 30.0
        spin = int(t * speed)
        kick_add = int(m.kick * 24)
        cxi = int(cx)
        # one table per row: the perspective only depends on the row
        for y in range(horizon + 1, h):
            d = y - horizon
            s = (240 // d) + 1
            phase = ((150 // d) * 8 + spin) % 48
            hband = phase < 9
            base = y * w
            floor_idx = FLOOR + min(63, 6 + (220 // d) + kick_add)
            line_idx = GRID + 26 + (kick_add >> 2)
            if hband:
                band = GRID + 2 + min(3, kick_add >> 3)
                for x in range(w):
                    buf[base + x] = line_idx if ((((x - cxi) * s) >> 3) & 31) < 3 else band
            else:
                for x in range(w):
                    buf[base + x] = line_idx if ((((x - cxi) * s) >> 3) & 31) < 2 else floor_idx

        # -------------------------------------------------- horizon glow
        if horizon < h:
            glow = STAR + 12 + int(m.kick * 20)
            buf[horizon * w:(horizon + 1) * w] = bytes((glow,)) * w
            if horizon - 1 >= 0:
                buf[(horizon - 1) * w:(horizon) * w] = bytes((STAR + 6,)) * w

    def palette(self, t, m=None):
        return PAL256
