"""Turn the score into values the visuals can dance to.

This is not signal analysis: the demo knows the notes it is playing, so the
"spectrum" it shows is built straight from the score.  It is deterministic
(which matters for rendering video) and it costs nothing.

A :class:`MusicSync` is fed the current time once per frame and keeps decaying
pulses for the kick, snare and hats plus a band meter for the melody.
"""

import math

BANDS = 16
BAND_LO = 45.0    # Hz
BAND_HI = 6000.0  # Hz

DECAY = {
    "kick": 7.0,
    "snare": 9.0,
    "hat": 16.0,
    "flash": 5.0,
    "band": 4.0,
}


def band_of(freq):
    if freq <= 0:
        return 0
    frac = math.log(freq / BAND_LO) / math.log(BAND_HI / BAND_LO)
    return max(0, min(BANDS - 1, int(frac * BANDS)))


class MusicSync:
    def __init__(self, score, loop=True):
        self.score = score
        self.loop = loop
        self.total = score.total_time
        self.beat = score.beat
        self.notes = score.notes
        self.drums = score.drums
        self.bands = [0.0] * BANDS
        self.kick = 0.0
        self.snare = 0.0
        self.hat = 0.0
        self.flash = 0.0
        self.bass = 0.0
        self.song_t = 0.0
        self.note_i = 0
        self.drum_i = 0
        self._last = None

    # ------------------------------------------------------------------ util
    def _reset(self):
        self.note_i = 0
        self.drum_i = 0
        self.bands = [0.0] * BANDS
        self.kick = self.snare = self.hat = self.flash = self.bass = 0.0

    def _apply_note(self, ev):
        b = band_of(ev.freq)
        value = min(1.0, ev.amp * 0.95)
        if ev.freq < 220:
            self.bass = max(self.bass, value)
        self.bands[b] = max(self.bands[b], value)
        self.flash = max(self.flash, value * 0.8)

    def _apply_drum(self, ev):
        kind = ev.inst
        if kind == "k":
            self.kick = max(self.kick, min(1.0, ev.amp))
            self.bands[0] = max(self.bands[0], ev.amp * 0.9)
            self.bands[1] = max(self.bands[1], ev.amp * 0.8)
        elif kind == "s":
            self.snare = max(self.snare, min(1.0, ev.amp))
            self.bands[9] = max(self.bands[9], ev.amp * 0.7)
        elif kind in ("h", "o"):
            self.hat = max(self.hat, min(1.0, ev.amp))
            self.bands[14] = max(self.bands[14], ev.amp * 0.6)
            self.bands[15] = max(self.bands[15], ev.amp * 0.5)
        elif kind == "c":
            self.snare = max(self.snare, ev.amp * 0.9)
        elif kind == "z":
            self.flash = max(self.flash, ev.amp)
            self.bands[12] = max(self.bands[12], ev.amp)

    # ------------------------------------------------------------------ main
    def advance(self, t):
        """Feed the current demo time; returns self so calls can be chained."""
        if not self.loop:
            song_t = min(t, self.total)
        else:
            song_t = t % self.total
        if self._last is None:
            dt = 0.0
        else:
            dt = song_t - self._last
            if dt < -self.total * 0.5:
                # the song wrapped around: fire the downbeat again
                self._reset()
                dt = 0.04
            elif dt < 0:
                dt = 0.0
        if self.loop and self._last is not None and song_t < self._last:
            self._reset()
        self._last = song_t
        self.song_t = song_t

        notes = self.notes
        while self.note_i < len(notes) and notes[self.note_i].time <= song_t:
            self._apply_note(notes[self.note_i])
            self.note_i += 1
        drums = self.drums
        while self.drum_i < len(drums) and drums[self.drum_i].time <= song_t:
            self._apply_drum(drums[self.drum_i])
            self.drum_i += 1

        if dt > 0.0:
            dk = math.exp(-dt * DECAY["kick"])
            self.kick *= dk
            self.snare *= math.exp(-dt * DECAY["snare"])
            self.hat *= math.exp(-dt * DECAY["hat"])
            self.flash *= math.exp(-dt * DECAY["flash"])
            self.bass *= math.exp(-dt * 3.0)
            db = math.exp(-dt * DECAY["band"])
            bands = self.bands
            for i in range(BANDS):
                bands[i] *= db
        return self

    # ------------------------------------------------------------- readouts
    def beat_phase(self):
        p = (self.song_t / self.beat) % 1.0
        return p

    def bar_phase(self):
        p = (self.song_t / (self.beat * 4.0)) % 1.0
        return p

    def bar(self):
        return int(self.song_t / (self.beat * 4.0))

    def level(self):
        """Rough loudness of the moment, 0..1."""
        return min(1.0, 0.35 * self.bass + 0.35 * self.kick + 0.3 * self.flash)
