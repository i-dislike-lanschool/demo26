"""Colour ramps and palettes used by the demo.

A palette is just a tuple of 256 ``(r, g, b)`` triples, ready to be indexed by
a framebuffer byte.  The 8-bit demos this one imitates could not do real
colour, so most of the ramps here are built from a handful of hues that are
"flickered" or cycled instead of blended.
"""

import math

# ZX Spectrum-ish colours: black, blue, red, magenta, green, cyan, yellow,
# white.  Twice, once normal and once dim, like the real machine's bright bit.
SPECCY = (
    (0, 0, 0),
    (0, 0, 205),
    (205, 0, 0),
    (205, 0, 205),
    (0, 205, 0),
    (0, 205, 205),
    (205, 205, 0),
    (205, 205, 205),
    (0, 0, 0),
    (0, 0, 255),
    (255, 0, 0),
    (255, 0, 255),
    (0, 255, 0),
    (0, 255, 255),
    (255, 255, 0),
    (255, 255, 255),
)


def _clamp(v):
    return 0 if v < 0 else (255 if v > 255 else int(v))


def gradient(stops, size=256):
    """Sample a smooth multi-stop gradient into ``size`` RGB triples."""
    out = []
    n = len(stops) - 1
    for i in range(size):
        p = (i / (size - 1)) * n if size > 1 else 0.0
        a = min(int(p), n - 1)
        f = p - a
        c0, c1 = stops[a], stops[a + 1]
        out.append(tuple(_clamp(c0[k] + (c1[k] - c0[k]) * f) for k in range(3)))
    return tuple(out)


def hsv_rgb(h, s, v):
    """h in [0, 1) turns, s and v in [0, 1]."""
    h = h % 1.0
    i = int(h * 6.0)
    f = h * 6.0 - i
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))
    return {
        0: (v, t, p), 1: (q, v, p), 2: (p, v, t),
        3: (p, q, v), 4: (t, p, v), 5: (v, p, q),
    }[i % 6]


def ramp_hue(size, shift=0.0, sat=0.9, val=1.0):
    """Full rainbow ramp, optionally rotated by ``shift`` turns."""
    return tuple(
        tuple(_clamp(c * 255.0) for c in hsv_rgb(i / size + shift, sat, val))
        for i in range(size)
    )


def ramp_fire(size=256):
    """Black -> red -> orange -> yellow -> white."""
    return gradient(
        [
            (0, 0, 0), (40, 0, 0), (140, 0, 0), (230, 60, 0),
            (255, 150, 0), (255, 240, 90), (255, 255, 235),
        ],
        size,
    )


def ramp_ice(size=256):
    """Deep blue -> cyan -> white."""
    return gradient(
        [
            (0, 0, 20), (0, 10, 90), (0, 60, 170), (0, 150, 225),
            (70, 230, 245), (230, 255, 255),
        ],
        size,
    )


def ramp_copper(size=256):
    """Amber / copper, the colour of every 90s tracker skin."""
    return gradient(
        [
            (10, 4, 0), (70, 20, 4), (150, 55, 8), (215, 105, 15),
            (250, 165, 45), (255, 225, 150), (255, 250, 230),
        ],
        size,
    )


def ramp_speccy_fade(size=256):
    """The 8 Spectrum hues, fading into the dark, on repeat."""
    out = []
    hues = SPECCY[1:8]
    for i in range(size):
        c = hues[min(6, (i * 8) // size)]
        k = (i % (size // 8)) / max(1, (size // 8) - 1)
        out.append(tuple(_clamp(v * (0.25 + 0.75 * k)) for v in c))
    return tuple(out)


def ramp_gray(size=256):
    return tuple((i, i, i) for i in range(size))


def rotate(pal, n):
    """Return ``pal`` rotated by ``n`` entries -- palette cycling, the classic."""
    n %= len(pal)
    return pal[n:] + pal[:n]


def palette_blend(a, b, f):
    """Mix two 256-entry palettes, ``f`` = 0 gives ``a``, 1 gives ``b``."""
    f = 0.0 if f < 0 else (1.0 if f > 1 else f)
    return tuple(
        tuple(_clamp(a[i][k] + (b[i][k] - a[i][k]) * f) for k in range(3))
        for i in range(min(len(a), len(b)))
    )


def zoom(pal, size_out=256):
    """Stretch a shorter palette over the whole 0..255 range."""
    n = len(pal)
    return tuple(pal[(i * n) // size_out] for i in range(size_out))


NAMED = {
    "fire": ramp_fire,
    "ice": ramp_ice,
    "copper": ramp_copper,
    "speccy": ramp_speccy_fade,
    "rainbow": lambda size=256: ramp_hue(size),
    "gray": ramp_gray,
}


def by_name(name, size=256):
    if name == "rainbow":
        return ramp_hue(size)
    return NAMED.get(name, ramp_hue)(size)


# Pre-built ones the effects use directly.
FIRE = ramp_fire(256)
ICE = ramp_ice(256)
COPPER = ramp_copper(256)
SPECTRUM_FADE = ramp_speccy_fade(256)
GRAY = ramp_gray(256)


def vignette_map(w, h, strength=0.55):
    """Precompute a per-pixel brightness multiplier (0..1) for a screen."""
    cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
    inv = math.hypot(cx, cy)
    out = bytearray(w * h)
    k = 0
    for y in range(h):
        dy = (y - cy) / inv
        for x in range(w):
            dx = (x - cx) / inv
            d = math.sqrt(dx * dx + dy * dy)
            v = 1.0 - strength * d * d
            out[k] = 0 if v < 0.0 else int(1 + 254 * (v if v < 1.0 else 1.0))
            k += 1
    return out
