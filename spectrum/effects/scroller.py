"""Copper bars, a logo and a sine-wave scrolltext -- the heart of the genre.

Palette layout: 0..127 dark cycling hue stripes for the backdrop,
128..191 the copper ramp for the raster bars, 192..239 chrome for the
logo, 240..251 paper white for the scrolltext, 252..255 accents.
"""

from .base import Effect, SIN8, chrome_text, sine_scroller
from .. import palettes

MESSAGE = (
    "NEON SKY /// ПРИВЕТ ИЗ 1991-ГО, ТОЛЬКО ТЕПЕРЬ НА ПИТОНЕ ... "
    "192 НА 108 ПИКСЕЛЕЙ, НИ ОДНОЙ БИБЛИОТЕКИ, НИ ОДНОГО NPM ... "
    "КОД, МУЗЫКА И КАРТИНКА - ВСЁ В ОДНОМ РЕПОЗИТОРИИ ... "
    "ЕСЛИ ТЫ ЭТО ЧИТАЕШЬ, ЗНАЧИТ КАССЕТА ЗАГРУЗИЛАСЬ ... "
    "GREETZ TO ALL OLD-SKOOL SCENERS /// СПАСИБО, ЧТО ПОМНИТЕ ... "
)

SUB = (
    "PURE PYTHON 3   *   NO DEPENDENCIES   *   NO GPU   *   JUST MATH "
    "AND A BYTEARRAY   *   "
)

BAR = 128
CHROME = 192
PAPER = 240


def _palette():
    dark = [tuple(v // 5 for v in rgb) for rgb in palettes.ramp_hue(128)]
    copper = palettes.ramp_copper(64)
    chrome = palettes.gradient(
        [(30, 34, 48), (90, 100, 122), (190, 200, 220), (255, 255, 255),
         (150, 160, 185), (70, 78, 98)], 48)
    paper = palettes.gradient([(140, 130, 120), (255, 252, 246)], 12)
    accent = [(255, 70, 70), (255, 140, 100), (120, 130, 145), (60, 68, 82)]
    return tuple(list(dark) + list(copper) + list(chrome)
                 + list(paper) + list(accent))


PAL = _palette()


class Scroller(Effect):
    name = "scroller"
    title = "SCROLLTEXT"
    bars = 8

    def setup(self, cv):
        w, h = cv.w, cv.h
        self.rasters = []
        for i in range(4):
            self.rasters.append((h * (0.18 + 0.21 * i), 1.0 + i * 0.5))

    def render(self, cv, t, m):
        w, h = cv.w, cv.h
        buf = cv.buf
        # slow dark stripes in the background, like a cycling palette
        scroll = int(t * 22.0)
        for y in range(h):
            idx = (y * 2 + scroll) & 127
            buf[y * w:(y + 1) * w] = bytes((idx,)) * w

        # copper bars with a gradient across their thickness
        kick = m.kick
        cycle = int(t * 40.0)
        for i, (yc, ph) in enumerate(self.rasters):
            amp = 5.0 + kick * 4.0
            thick = 4 + int(kick * 3) + (i % 2) * 2
            top = (i * 17 + cycle) & 63
            band = bytes(BAR + ((top + (k * 40) // max(1, thick)) & 63)
                         for k in range(thick))
            for x in range(w):
                off = int((SIN8[(x * 13 + int(ph * 60) + int(t * 90)) & 255]
                           - 128) * (amp / 128.0))
                y0 = int(yc + off)
                if y0 < 0 or y0 + thick >= h:
                    continue
                buf[y0 * w + x:(y0 + thick) * w + x:w] = band

        # logo, small and chrome-y at the top
        chrome_text(cv, 69, 6, "NEON SKY", 1,
                    tuple(range(CHROME + 6, CHROME + 48, 5)), shadow=0)
        if int(t * 2.2) % 2 == 0:
            cv.text_center(16, "A PYTHON DEMO", 252)

        # the main scrolltext, warped into a sine wave
        sine_scroller(cv, MESSAGE, t, int(h * 0.56), 7.0, 70.0, 34.0,
                      colors=(PAPER + 11, PAPER + 9, PAPER + 7, PAPER + 5,
                              PAPER + 3, PAPER + 1), scale=2)

        # a second, quieter line going the other way
        sine_scroller(cv, SUB[::-1], -t * 0.6, int(h * 0.90), 1.5, 40.0, 26.0,
                      colors=(CHROME + 18, CHROME + 24, CHROME + 30,
                              CHROME + 36), scale=1, shadow=False)

    def palette(self, t, m=None):
        return PAL
