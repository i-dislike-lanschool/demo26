"""Minimal PNG writer (8-bit RGB) -- stdlib only, no Pillow needed."""

import struct
import zlib


def _chunk(tag, data):
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def encode_rgb(w, h, rgb, level=6):
    """Encode raw RGB bytes (``w * h * 3``) as a PNG file in memory."""
    stride = w * 3
    raw = bytearray()
    for y in range(h):
        raw.append(0)  # filter type: none
        raw += rgb[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)  # 8-bit truecolour
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(bytes(raw), level))
        + _chunk(b"IEND", b"")
    )


def write_rgb(path, w, h, rgb, level=6):
    data = encode_rgb(w, h, rgb, level)
    with open(path, "wb") as fh:
        fh.write(data)
    return len(data)


def scale_nearest(w, h, rgb, factor):
    """Upscale by an integer factor (nearest neighbour), for previews."""
    out = bytearray()
    stride = w * 3
    for y in range(h):
        row = rgb[y * stride:(y + 1) * stride]
        big = bytearray(w * 3 * factor)
        for x in range(w):
            px = row[x * 3:x * 3 + 3] * factor
            big[x * 3 * factor:(x + 1) * 3 * factor] = px
        for _ in range(factor):
            out += big
    return bytes(out)
