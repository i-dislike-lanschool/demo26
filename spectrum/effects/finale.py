"""Rolling credits, then THE END."""

import math

from .base import Effect, Starfield, chrome_text
from .. import palettes

CREDITS = [
    "NEON SKY",
    "",
    "A DEMO IN PURE PYTHON",
    "",
    "CODE .... THE AGENT",
    "MUSIC ... CHIPTUNE ENGINE",
    "PIXELS .. 192 X 108",
    "SOUND ... 22050 HZ, ONE CORE",
    "",
    "NO LIBRARIES",
    "NO GPU",
    "NO PACKAGE MANAGER",
    "JUST THE STDLIB",
    "",
    "GREETINGS TO EVERYONE",
    "WHO STILL REMEMBERS",
    "LOADING FROM TAPE",
    "",
    "",
]


def _palette():
    base = palettes.gradient(
        [(0, 0, 0), (4, 2, 16), (14, 6, 34), (30, 10, 52), (60, 20, 70)], 128
    )
    gold = palettes.gradient(
        [(120, 60, 20), (220, 140, 50), (255, 210, 120), (255, 250, 220),
         (255, 255, 255)], 128
    )
    return tuple(base) + tuple(gold)


PAL = _palette()


class Finale(Effect):
    name = "finale"
    title = "THE END"
    bars = 8

    def setup(self, cv):
        self.stars = Starfield(120, seed=31, width=cv.w, height=cv.h)
        self.h = cv.h
        self.scroll_len = len(CREDITS) * 10
        self.scroll_time = 11.0

    def render(self, cv, t, m):
        w, h = cv.w, cv.h
        self.stars.render(cv, t * 0.7, 0.5 + m.kick, tuple(range(10, 60)))

        if t < self.scroll_time:
            y = h + 6 - t * (self.scroll_len + h) / self.scroll_time
            for i, line in enumerate(CREDITS):
                yy = int(y + i * 10)
                if yy < -8 or yy > h:
                    continue
                if not line:
                    continue
                if i == 0:
                    chrome_text(cv, (w - (len(line) * 21 - 1)) // 2, yy, line, 4,
                                (250, 245, 240, 235, 228, 220, 210, 200))
                else:
                    bright = 128 + 40 + (i % 3) * 12
                    cv.text_center(yy, line, bright, shadow=0)
        else:
            k = t - self.scroll_time
            # the last chord hits, everything glows
            glow = 128 + int(60 + 60 * math.sin(k * 3.0))
            title = "THE END"
            x = (w - (len(title) * 21 - 1)) // 2
            chrome_text(cv, x + 1, 39, title, 4, (0, 0, 0, 0, 0, 0, 0, 0))
            chrome_text(cv, x, 38, title, 4,
                        (250, 245, 240, 236, 232, 228, 224, 220))
            cv.text_center(78, "THANKS FOR WATCHING", 128 + 70)
            if int(t * 2) % 2 == 0:
                cv.text_center(92, "PRESS Q TO QUIT", 128 + 30)

        # a thin ember line at the bottom, pulsing with the kick
        amp = 2.0 + m.kick * 3.0
        yy0 = int(h * 0.93)
        for x in range(w):
            yy = int(yy0 + amp * math.sin(x * 0.06 + t * 2.0))
            if 0 <= yy < h:
                cv.buf[yy * w + x] = 200
                if yy + 1 < h:
                    cv.buf[(yy + 1) * w + x] = 150

    def palette(self, t, m=None):
        return PAL
