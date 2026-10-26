"""The demo soundtrack, written as step patterns.

The tune is in A minor at 124 BPM, four bars per chord cycle (Am - F - C - G),
which is about as Spectrum-demo as a chord progression gets.  Patterns are
one token per sixteenth note and ``|`` marks the bar lines, so the strings
below read nearly like sheet music.
"""

from . import score, synth

BPM = 124

# ------------------------------------------------------------------ patchset
INSTRUMENTS = {
    "lead": dict(
        name="lead", wave="pulse25", a=0.004, d=0.11, s=0.62, r=0.10,
        vib=0.28, vib_rate=5.4, vib_delay=0.18, gain=0.20, pan=-0.12,
    ),
    "bass": dict(
        name="bass", wave="pulse25",
        layers=((1.0, -4.0, 1.0), (0.5, 0.0, 0.35)),
        a=0.002, d=0.07, s=0.48, r=0.06, gain=0.235, pan=0.0,
    ),
    "arp": dict(
        name="arp", wave="pulse12", a=0.001, d=0.05, s=0.22, r=0.05,
        gain=0.13, pan=0.30,
    ),
    "pad": dict(
        name="pad", wave="saw",
        layers=((1.0, -8.0, 0.55), (1.0, 0.0, 0.6), (1.0, 8.0, 0.55),
                (0.5, 0.0, 0.25)),
        a=0.16, d=0.5, s=0.8, r=0.7, gain=0.115, pan=0.0,
    ),
    "bell": dict(
        name="bell", wave="bell", a=0.002, d=0.55, s=0.22, r=0.8,
        vib=0.12, vib_rate=4.2, vib_delay=0.3, gain=0.26, pan=0.35,
    ),
    "organ": dict(
        name="organ", wave="organ", a=0.02, d=0.2, s=0.7, r=0.25,
        gain=0.13, pan=-0.25,
    ),
}

_INST_CACHE = {}


def instrument_factory(name):
    inst = _INST_CACHE.get(name)
    if inst is None:
        if name == "drums":
            inst = synth.Instrument("drums-one-shot", gain=0.0)
        else:
            inst = score.make_instrument(INSTRUMENTS[name])
        _INST_CACHE[name] = inst
    return inst


# -------------------------------------------------------------------- patterns
PATTERNS = {
    # ---- pad: one chord per bar, root + fifth through the pad's own layers
    "pad_main": (
        "a3:16 | f3:16 | c3:16 | g3:16"
    ),
    # ---- arpeggios: sixteenths straight out of a tracker
    "arp_main": (
        "a4 c5 e5 c5 a4 c5 e5 c5 a4 c5 e5 c5 a4 c5 e5 c5 |"
        "f4 a4 c5 a4 f4 a4 c5 a4 f4 a4 c5 a4 f4 a4 c5 a4 |"
        "c5 e5 g5 e5 c5 e5 g5 e5 c5 e5 g5 e5 c5 e5 g5 e5 |"
        "g4 b4 d5 b4 g4 b4 d5 b4 g4 b4 d5 b4 g4 b4 d5 b4"
    ),
    "arp_break": (
        "a5:4 c6:4 e6:4 c6:4 a5:4 c6:4 e6:4 c6:4 |"
        "f5:4 a5:4 c6:4 a5:4 f5:4 a5:4 c6:4 a5:4 |"
        "c6:4 e6:4 g6:4 e6:4 c6:4 e6:4 g6:4 e6:4 |"
        "g5:4 b5:4 d6:4 b5:4 g5:4 b5:4 d6:4 b5:4"
    ),
    # ---- bass: driving eighth notes, root - root - fifth
    "bass_main": (
        "a2 . a2 . e3 . a2 . a2 . a2 . g2 . a2 . |"
        "f2 . f2 . c3 . f2 . f2 . f2 . e2 . f2 . |"
        "c2 . c2 . g2 . c2 . c2 . c2 . b1 . c2 . |"
        "g2 . g2 . d3 . g2 . g2 . g2 . f2 . g2 ."
    ),
    # ---- lead phrases: chord tones on the beat, one bar each
    "lead_main": (
        "e5:4 . . . a5:4 . . . c6:4 . . . b5:4 . . . |"
        "a5:4 . . . f5:4 . . . g5:4 . . . a5:4 . . . |"
        "g5:4 . . . e5:4 . . . c5:4 . . . e5:4 . . . |"
        "d5:4 . . . g5:4 . . . f5:2 . d5:2 . b4:4 . . ."
    ),
    "lead_climax": (
        "a5:4 . . . c6:4 . . . e6:4 . . . d6:4 . . . |"
        "c6:4 . . . a5:4 . . . g5:4 . . . f5:4 . . . |"
        "e5:4 . . . g5:4 . . . c6:4 . . . b5:4 . . . |"
        "d6:4 . . . b5:4 . . . g5:4 . . . d5:4 . . ."
    ),
    "lead_outro": (
        "a5:8 . . . . . . . e5:4 . . . a4:4 . . . |"
        "f5:8 . . . . . . . c5:4 . . . a4:4 . . . |"
        "e5:8 . . . . . . . g5:4 . . . c5:4 . . . |"
        "d5:8 . . . . . . . b4:4 . . . g4:4 . . ."
    ),
    # ---- drums: one token per sixteenth
    "drums_main": (
        "k . h . s . h . k . h . s . h ."
    ),
    "drums_busy": (
        "k . h k s . h . k . h k s . h k"
    ),
    "drums_hats": (
        ". . h . . . h . . . h . . . h ."
    ),
    "drums_fill4": (
        "k . h . s . h . k . h . s . h . |"
        "k . h k s . h . k . h k s . h k |"
        "k . h . s . h . k . h . s . h . |"
        "k h k h s h s h k h s s c c c c"
    ),
    "drums_break": (
        "z . . . . . . . . . . . . . . . |"
        ". . . . . . . . . . . . . . . . |"
        ". . . . . . . . . . . . . . . . |"
        ". . . . . . . . . . . . . . . ."
    ),
    "crash_in": (
        "c . . . . . . . . . . . . . . ."
    ),
}


def _track(inst, pat, vol=1.0, oct=0, pan=None, chord=None):
    t = {"inst": inst, "pat": pat, "vol": vol, "oct": oct}
    if pan is not None:
        t["pan"] = pan
    if chord is not None:
        t["chord"] = chord
    return t


SONG = {
    "title": "NEON SKY",
    "bpm": BPM,
    "patterns": PATTERNS,
    "arrangement": [
        {"name": "intro", "bars": 2, "tracks": [
            _track("pad", "pad_main", 0.85),
            _track("arp", "arp_main", 0.55),
        ]},
        {"name": "intro+", "bars": 2, "tracks": [
            _track("pad", "pad_main", 0.85),
            _track("arp", "arp_main", 0.7),
            _track("drums", "drums_hats", 0.28),
        ]},
        {"name": "verse", "bars": 8, "tracks": [
            _track("bass", "bass_main", 0.95),
            _track("drums", "drums_main", 0.55),
            _track("arp", "arp_main", 0.5),
            _track("lead", "lead_main", 0.95),
        ]},
        {"name": "chorus", "bars": 8, "tracks": [
            _track("bass", "bass_main", 0.95),
            _track("drums", "drums_busy", 0.6),
            _track("arp", "arp_main", 0.55),
            _track("lead", "lead_climax", 1.0),
            _track("pad", "pad_main", 0.5),
        ]},
        {"name": "break", "bars": 4, "tracks": [
            _track("pad", "pad_main", 0.95),
            _track("bell", "arp_break", 0.8),
            _track("organ", "pad_main", 0.55, chord=(0, 7)),
            _track("drums", "drums_break", 0.5),
        ]},
        {"name": "finale", "bars": 8, "tracks": [
            _track("bass", "bass_main", 1.0),
            _track("drums", "drums_fill4", 0.6),
            _track("arp", "arp_main", 0.6),
            _track("lead", "lead_climax", 1.0),
            _track("pad", "pad_main", 0.45),
        ]},
        {"name": "outro", "bars": 4, "tracks": [
            _track("pad", "pad_main", 1.0),
            _track("bell", "arp_break", 0.65),
            _track("lead", "lead_outro", 0.9),
            _track("organ", "pad_main", 0.6, chord=(0, 7)),
        ]},
    ],
}


def build(bpm=None):
    song = dict(SONG)
    if bpm:
        song["bpm"] = bpm
    return score.compile_song(song, instrument_factory)
