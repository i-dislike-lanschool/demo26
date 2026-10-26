"""A fake ZX Spectrum tape loading screen, stripes and all."""

from .base import Effect
from .. import palettes, font

BORDER = 7
PAL = tuple(palettes.SPECCY[i % 16] for i in range(256))

# Spectrum colours by number, for the border stripes
BLACK, BLUE, RED, MAGENTA, GREEN, CYAN, YELLOW, WHITE = range(8)
BRIGHT = 8


class Loader(Effect):
    name = "loader"
    title = "LOADING"
    bars = 2

    def setup(self, cv):
        self.w = cv.w
        self.h = cv.h
        self.duration = 7.7

    def render(self, cv, t, m):
        w, h = cv.w, cv.h
        buf = cv.buf
        duration = self.duration
        progress = min(1.0, t / (duration * 0.82))

        # the border: flashing bands like data going to the tape
        phase = int(t * 12.0) % 4
        colours = (RED, YELLOW, CYAN, GREEN)
        border_colour = colours[phase]
        buf[:] = bytes((border_colour | BRIGHT,)) * cv.size

        # paper area
        x0, y0 = BORDER, BORDER
        x1, y1 = w - BORDER - 1, h - BORDER - 1
        black = bytes((BLACK,)) * (x1 - x0 + 1)
        for y in range(y0, y1 + 1):
            buf[y * w + x0:y * w + x1 + 1] = black

        # header text
        cv.text(x0 + 6, y0 + 5, "NEON SKY", WHITE | BRIGHT)
        cv.text(x0 + 6, y0 + 15, "A PYTHON DEMO", CYAN | BRIGHT)

        # tape counter, flickering like a real one
        dots = "." * (1 + int(t * 3) % 3)
        cv.text(x0 + 6, y0 + 32, "LOADING" + dots, YELLOW | BRIGHT)

        # progress bar
        bx = x0 + 6
        by = y0 + 44
        bw = w - 2 * BORDER - 26
        cv.fill_rect(bx, by, bx + bw, by + 7, BLUE)
        filled = int(bw * progress)
        for i in range(0, filled, 3):
            colour = (WHITE if (i // 3) % 2 == 0 else CYAN) | BRIGHT
            cv.fill_rect(bx + i, by + 1, bx + min(i + 1, filled), by + 6, colour)
        # percent, right aligned
        pct = "%d%%" % int(progress * 100)
        cv.text(bx + bw + 3, by, pct, WHITE | BRIGHT)

        # name of the file being loaded, like "PROGRAM: NEON.SKY"
        if int(t * 2) % 2 == 0:
            cv.text(x0 + 6, y0 + 58, "PROGRAM: NEON.SKY", GREEN | BRIGHT)
        cv.text(x0 + 6, y0 + 68, "CODE * MUSIC * PIXELS", MAGENTA | BRIGHT)
        cv.text(x0 + 6, y1 - 8, "PRESS Q TO QUIT ANY TIME", WHITE)

        # tiny loading dots around the border frame, moving
        for i in range(0, w, 6):
            if (i // 6 + int(t * 20)) % 4 == 0:
                cv.put(i, 2, WHITE | BRIGHT)
                cv.put(i, h - 3, WHITE | BRIGHT)

    def palette(self, t, m=None):
        return PAL
