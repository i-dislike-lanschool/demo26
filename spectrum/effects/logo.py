"""Title screen: the logo writes itself onto a starfield."""

import math

from .base import Effect, Starfield, chrome_text
from .. import palettes

TITLE = "NEON SKY"
CHROME = (255, 252, 248, 244, 240, 236, 232, 228)


def _palette():
    # 0..63    deep space, for stars and the horizon glow
    # 64..199  reserved for background bands
    # 200..255 chrome for the logo
    space = palettes.gradient(
        [(0, 0, 0), (2, 2, 10), (6, 6, 26), (10, 8, 44), (16, 10, 60)], 64
    )
    mid = palettes.gradient(
        [(20, 6, 40), (40, 10, 70), (70, 20, 100), (110, 40, 130)], 136
    )
    chrome = palettes.gradient(
        [(60, 120, 190), (140, 210, 250), (255, 255, 255), (255, 250, 210),
         (255, 200, 120), (220, 140, 60), (120, 60, 40), (255, 255, 255)],
        56,
    )
    return tuple(space) + tuple(mid) + tuple(chrome)


PAL = _palette()


class Logo(Effect):
    name = "logo"
    title = "NEON SKY"
    bars = 4

    def setup(self, cv):
        self.stars = Starfield(110, seed=5, width=cv.w, height=cv.h)
        self.shown = 0
        self.flash = [0.0] * len(TITLE)
        self.last_t = 0.0

    def render(self, cv, t, m):
        w, h = cv.w, cv.h
        self.stars.render(cv, t, 0.55 + m.kick * 1.6,
                          tuple(range(10, 58)), warp=m.kick * 0.7)

        # horizon glow rising with the music
        hz = int(h * 0.70)
        bump = int(m.bass * 10)
        base = 44 + bump
        span = max(1, h - hz)
        for y in range(hz, h):
            idx = base - ((y - hz) * 26) // span
            cv.buf[y * w:(y + 1) * w] = bytes((idx if idx > 0 else 0,)) * w

        # the logo types itself in, one letter at a time
        dt = t - self.last_t
        self.last_t = t
        want = min(len(TITLE), int(t / 0.22) + 1)
        if want > self.shown:
            for i in range(self.shown, want):
                self.flash[i] = 1.0
            self.shown = want
        for i in range(len(self.flash)):
            self.flash[i] = max(0.0, self.flash[i] - dt * 2.4)

        text = TITLE[: self.shown]
        x = (w - (len(text) * 21 - 1)) // 2 if text else w // 2
        y = 30
        # shadow, then the chrome letters
        chrome_text(cv, x + 2, y + 2, text, 4, (0, 0, 0, 0, 0, 0, 0, 0))
        chrome_text(cv, x, y, text, 4, CHROME)
        for i, f in enumerate(self.flash[: self.shown]):
            if f > 0.15:
                chrome_text(cv, x + i * 21, y, TITLE[i], 4,
                            (255, 255, 255, 250, 245, 240, 235, 230))

        if t > 1.4:
            cv.text_center(70, "A DEMO IN PURE PYTHON", 235, shadow=0)
        if t > 2.0:
            cv.text_center(84, "192X108 * 25 FPS * STDLIB ONLY", 220, shadow=0)
        if t > 2.6:
            cv.text_center(98, "ARENA DEMO 26", 205 + int(m.flash * 40), shadow=0)

        # a thin sine wave, tying the logo to the beat
        amp = 2.0 + m.kick * 4.0
        phase = t * 4.0
        for x in range(w):
            yy = int(h * 0.63 + amp * math.sin(x * 0.09 + phase))
            if 0 <= yy < h:
                cv.buf[yy * w + x] = 240
                if 0 <= yy + 1 < h and m.kick > 0.3:
                    cv.buf[(yy + 1) * w + x] = 200

    def palette(self, t, m=None):
        return PAL
