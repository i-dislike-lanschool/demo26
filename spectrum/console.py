"""Render the demo into a text terminal using half-block characters.

Each character cell becomes two vertical samples: the upper half is the
foreground colour of a "▀", the lower half is the background colour.  That
gives twice the vertical resolution of a plain block-per-cell display, so a
192x108 frame looks smooth even in an 80x24 terminal.

Truecolor (16 million colours) is used when the terminal claims support,
otherwise the picture is quantised to the xterm-256 cube, and finally to the
basic 8 colours.  It also works over SSH; it will just look a bit rougher.
"""

import os
import shutil
import sys

RESET = "\x1b[0m"
HOME = "\x1b[H"
HIDE = "\x1b[?25l"
SHOW = "\x1b[?25h"
CLEAR = "\x1b[2J"


def enable_ansi_on_windows():
    if os.name != "nt":
        return
    try:
        import ctypes

        k = ctypes.windll.kernel32
        for handle in (-11, -12):
            h = k.GetStdHandle(handle)
            mode = ctypes.c_uint32()
            if k.GetConsoleMode(h, ctypes.byref(mode)):
                k.SetConsoleMode(h, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL
    except Exception:
        pass


def detect_colour_depth():
    if not sys.stdout.isatty():
        return "none"
    if os.environ.get("NO_COLOR"):
        return "none"
    if os.environ.get("COLORTERM", "").lower() in ("truecolor", "24bit"):
        return "truecolor"
    if os.name == "nt":
        # Windows Terminal speaks truecolor; legacy conhost does 256
        return "truecolor" if os.environ.get("WT_SESSION") else "256"
    term = os.environ.get("TERM", "")
    if "kitty" in term or "alacritty" in term:
        return "truecolor"
    if "256color" in term:
        return "256"
    return "16"


def _box_bounds(sw, sh, dw, dh):
    """Integer source ranges for each destination cell (box sampling)."""
    xs = [(i * sw) // dw for i in range(dw + 1)]
    ys = [(j * sh) // dh for j in range(dh + 1)]
    return xs, ys


def _sample(rgb, w, xs, ys):
    """Average a box of the RGB buffer.  Returns (r, g, b)."""
    x0, x1 = xs
    y0, y1 = ys
    if x1 <= x0:
        x1 = x0 + 1
    if y1 <= y0:
        y1 = y0 + 1
    r = g = b = 0
    n = 0
    for y in range(y0, y1):
        base = (y * w + x0) * 3
        for i in range(x1 - x0):
            r += rgb[base]
            g += rgb[base + 1]
            b += rgb[base + 2]
            base += 3
            n += 1
    return r // n, g // n, b // n


def _quant256(r, g, b):
    """Nearest xterm-256 colour (good enough for a demo)."""
    if abs(r - g) < 12 and abs(g - b) < 12:
        level = (r * 25) // 256
        return 232 + level if level < 24 else 231
    q = lambda v: 0 if v < 48 else (1 if v < 115 else (v - 35) // 40)
    return 16 + 36 * q(r) + 6 * q(g) + q(b)


def _idx16(r, g, b):
    """Index 0..15 of the nearest basic ANSI colour."""
    idx = 0
    if r > 96:
        idx |= 1
    if g > 96:
        idx |= 2
    if b > 96:
        idx |= 4
    if max(r, g, b) > 192:
        idx += 8 if idx < 8 else 0
    return idx


def _fg16(i):
    return "\x1b[%dm" % (30 + (i & 7) + (60 if i >= 8 else 0))


def _bg16(i):
    return "\x1b[%dm" % (40 + (i & 7) + (60 if i >= 8 else 0))


class ConsoleScreen:
    def __init__(self, cols=None, rows=None, depth=None, fullscreen=False):
        enable_ansi_on_windows()
        size = shutil.get_terminal_size((80, 24))
        self.cols = cols or min(size.columns, 118)
        self.rows = rows or max(8, size.lines - 1)
        self.depth = depth or detect_colour_depth()
        self.fullscreen = fullscreen
        self.started = False

    def start(self):
        if self.depth == "none":
            return
        sys.stdout.write(HIDE + (CLEAR if self.fullscreen else ""))
        sys.stdout.flush()
        self.started = True

    def close(self):
        if self.started:
            sys.stdout.write(RESET + SHOW + "\n")
            sys.stdout.flush()
            self.started = False

    def geometry(self, frame_w, frame_h):
        """How many terminal columns / rows to use for a frame of this shape."""
        cols = self.cols
        # Each text row is two square samples, so the pixel grid is cols wide
        # and 2*rows tall.  Fit it inside the frame aspect ratio.
        rows = int(round(cols * frame_h / (2.0 * frame_w)))
        rows = max(4, min(rows, self.rows))
        return cols, rows

    def show(self, rgb, w, h, cols=None, rows=None):
        if self.depth == "none":
            return
        cols = cols or self.cols
        rows = rows or self.rows
        sw, sh = cols, rows * 2
        xs, ys = _box_bounds(w, h, sw, sh)
        out = [HOME]
        depth = self.depth
        for j in range(rows):
            fg_prev = bg_prev = None
            line = []
            for i in range(cols):
                top = _sample(rgb, w, (xs[i], xs[i + 1]), (ys[j * 2], ys[j * 2 + 1]))
                bot = _sample(rgb, w, (xs[i], xs[i + 1]), (ys[j * 2 + 1], ys[j * 2 + 2]))
                if depth == "truecolor":
                    fg = "\x1b[38;2;%d;%d;%dm" % top
                    bg = "\x1b[48;2;%d;%d;%dm" % bot
                elif depth == "256":
                    fg = "\x1b[38;5;%dm" % _quant256(*top)
                    bg = "\x1b[48;5;%dm" % _quant256(*bot)
                else:
                    fg = _fg16(_idx16(*top))
                    bg = _bg16(_idx16(*bot))
                if top == bot:
                    line.append(bg + " ")
                    continue
                if fg != fg_prev:
                    line.append(fg)
                    fg_prev = fg
                if bg != bg_prev:
                    line.append(bg)
                    bg_prev = bg
                line.append("\u2580")  # upper half block
            out.append("".join(line) + RESET)
        sys.stdout.write("\n".join(out))
        sys.stdout.flush()

    def print_line(self, text=""):
        sys.stdout.write(text + "\n")
        sys.stdout.flush()
