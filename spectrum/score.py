"""Tracker-ish song format: step patterns in text, arranged into sections.

A pattern is just words, one per sixteenth-note step::

    "a2:2 . a3:2 . f2:2 . c3:2 ."

* ``a2``      -- start a note (octave 2), it lasts until the next note
* ``a2:6``    -- ...or exactly 6 steps
* ``.``       -- a rest
* ``-``       -- a tie, nothing new starts (purely for readability)
* ``|``       -- a bar line, ignored
* ``k s h o c z`` -- drum hits: kick, snare, hat, open hat, clap, zap

Sections then say which patterns play in which bars, so the arrangement reads
like a table instead of a wall of numbers.
"""

import math

from . import synth

NOTE_OFFSET = {
    "c": 0, "c#": 1, "db": 1, "d": 2, "d#": 3, "eb": 3, "e": 4, "f": 5,
    "f#": 6, "gb": 6, "g": 7, "g#": 8, "ab": 8, "a": 9, "a#": 10, "bb": 10,
    "b": 11,
}
DRUM_TOKENS = {"k", "s", "h", "o", "c", "z"}


class Event:
    """One thing that happens at a moment in the song."""

    __slots__ = ("time", "kind", "freq", "dur", "amp", "pan", "inst", "name")

    def __init__(self, time, kind, inst, amp=1.0, pan=0.0, freq=0.0, dur=0.1,
                 name=""):
        self.time = time
        self.kind = kind      # "note" or "drum"
        self.inst = inst
        self.amp = amp
        self.pan = pan
        self.freq = freq
        self.dur = dur
        self.name = name

    def __repr__(self):
        return "<Event %.3f %s %s %.1f>" % (
            self.time, self.kind, self.name or type(self.inst).__name__, self.freq
        )


def parse_note(token):
    """``"a2"`` or ``"c#4:6"`` -> (midi, steps or None)."""
    length = None
    if ":" in token:
        token, _, ln = token.partition(":")
        try:
            length = int(ln)
        except ValueError:
            raise ValueError("bad note length in %r" % token)
    t = token.lower()
    if len(t) < 2:
        raise ValueError("bad note name %r" % token)
    name = t[:-1]
    try:
        octave = int(t[-1])
    except ValueError:
        raise ValueError("bad octave in %r" % token)
    if name not in NOTE_OFFSET:
        raise ValueError("bad note name %r" % token)
    midi = 12 * (octave + 1) + NOTE_OFFSET[name]
    return midi, length


def tokens(pattern):
    return [w for w in pattern.replace("|", " ").split() if w and w != "-"]


class Score:
    def __init__(self, title, bpm, events, bars, beat, sections, notes, drums):
        self.title = title
        self.bpm = bpm
        self.events = events
        self.bars = bars
        self.beat = beat
        self.step = beat / 4.0
        self.total_time = bars * 4 * beat
        self.sections = sections      # list of (name, start_time, duration)
        self.notes = notes            # notes only, for the visuals
        self.drums = drums

    def section_at(self, t):
        t %= self.total_time
        for name, start, dur in self.sections:
            if start <= t < start + dur:
                return name
        return self.sections[-1][0]

    def bar_at(self, t):
        return int((t % self.total_time) // (4 * self.beat))


def compile_song(song, instrument_factory):
    """Turn a song dict (see ``music/songs.py``) into a :class:`Score`."""
    bpm = float(song["bpm"])
    beat = 60.0 / bpm
    step = beat / 4.0
    patterns = song["patterns"]
    arrangement = song["arrangement"]
    events = []
    notes = []
    drums = []
    sections = []

    bar_cursor = 0
    for section in arrangement:
        name = section["name"]
        bars = int(section["bars"])
        start_time = bar_cursor * 4 * beat
        sections.append((name, start_time, bars * 4 * beat))
        transpose = section.get("transpose", 0)
        for track in section["tracks"]:
            inst_name = track["inst"]
            inst = instrument_factory(inst_name)
            pat = patterns[track["pat"]]
            toks = tokens(pat)
            if not toks:
                continue
            vol = track.get("vol", 1.0)
            octave = track.get("oct", 0)
            pan = track.get("pan", inst.pan)
            chord = track.get("chord")
            total_steps = bars * 16
            i = 0
            while i < total_steps:
                tkn = toks[i % len(toks)]
                # how long does this token sound?  until the next note starts
                if tkn == "." or tkn in DRUM_TOKENS:
                    i += 1
                    continue
                midi, explicit = parse_note(tkn)
                if explicit is None:
                    # ring on until the next note token, rests included
                    ln = 1
                    while ln < total_steps - i and toks[(i + ln) % len(toks)] == ".":
                        ln += 1
                else:
                    ln = explicit
                length = max(1, min(ln, total_steps - i))
                start = start_time + i * step
                dur = length * step
                midi2 = midi + 12 * octave + transpose
                base_name = tkn.split(":")[0]
                ev = Event(start, "note", inst, amp=vol, pan=pan,
                           freq=synth.midi_to_freq(midi2), dur=dur, name=base_name)
                events.append(ev)
                notes.append(ev)
                if chord:
                    for semi in chord:
                        ev2 = Event(start, "note", inst, amp=vol * 0.75, pan=pan,
                                    freq=synth.midi_to_freq(midi2 + semi),
                                    dur=dur, name=base_name)
                        events.append(ev2)
                        notes.append(ev2)
                i += length
        # drums are separate: each token is a hit on that step
        for track in section["tracks"]:
            if track["inst"] != "drums":
                continue
            pat = patterns[track["pat"]]
            toks = tokens(pat)
            vol = track.get("vol", 1.0)
            for i in range(bars * 16):
                tkn = toks[i % len(toks)]
                if tkn not in DRUM_TOKENS:
                    continue
                start = start_time + i * step
                ev = Event(start, "drum", tkn, amp=vol, pan=track.get("pan", 0.0))
                ev.freq = 0.0
                events.append(ev)
                drums.append(ev)
        bar_cursor += bars

    events.sort(key=lambda e: e.time)
    notes.sort(key=lambda e: e.time)
    drums.sort(key=lambda e: e.time)
    total = bar_cursor * 4 * beat
    score = Score(song.get("title", "untitled"), bpm, events, bar_cursor, beat,
                  sections, notes, drums)
    score.total_time = total
    return score


def make_instrument(params):
    """Build a synth.Instrument from a plain dict."""
    p = dict(params)
    name = p.pop("name", "?")
    layers = p.pop("layers", None)
    arp = p.pop("arp", None)
    return synth.Instrument(name, layers=layers, arp=arp, **p)
