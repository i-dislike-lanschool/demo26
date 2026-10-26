"""16-bit PCM WAV writing, stdlib only."""

import array
import struct
import sys


def to_pcm16(samples):
    """Clamp floats in [-1, 1] to signed 16 bit little endian."""
    out = array.array("h")
    for s in samples:
        v = int(s * 32767.0)
        if v > 32767:
            v = 32767
        elif v < -32768:
            v = -32768
        out.append(v)
    if sys.byteorder == "big":
        out.byteswap()
    return out.tobytes()


def encode_wav(samples, rate, channels=1):
    """Float samples (interleaved for channels > 1) to WAV file bytes."""
    data = to_pcm16(samples)
    bits = 16
    byte_rate = rate * channels * bits // 8
    block_align = channels * bits // 8
    header = b"RIFF"
    header += struct.pack("<I", 36 + len(data))
    header += b"WAVEfmt "
    header += struct.pack("<IHHIIHH", 16, 1, channels, rate,
                          byte_rate, block_align, bits)
    header += b"data" + struct.pack("<I", len(data))
    return header + data


def encode_pcm(pcm, rate, channels=1):
    """Wrap ready little-endian int16 PCM bytes in a WAV header."""
    bits = 16
    byte_rate = rate * channels * bits // 8
    block_align = channels * bits // 8
    header = b"RIFF"
    header += struct.pack("<I", 36 + len(pcm))
    header += b"WAVEfmt "
    header += struct.pack("<IHHIIHH", 16, 1, channels, rate,
                          byte_rate, block_align, bits)
    header += b"data" + struct.pack("<I", len(pcm))
    return header + pcm


def write_pcm(path, pcm, rate, channels=1):
    body = encode_pcm(pcm, rate, channels)
    with open(path, "wb") as fh:
        fh.write(body)
    return len(body)


def write_wav(path, samples, rate, channels=1):
    """Write float samples (interleaved for channels > 1) to a WAV file."""
    body = encode_wav(samples, rate, channels)
    with open(path, "wb") as fh:
        fh.write(body)
    return len(body)
