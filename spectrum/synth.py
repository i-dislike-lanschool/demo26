"""A tiny chiptune synthesizer: wavetables, envelopes, drums, echo.

Everything here is plain Python.  At 22 kHz with half a dozen voices the CPU
cost is a few percent of one core, which is what makes a dependency-free
audio engine practical at all.

The signal path is deliberately simple, like the hardware it imitates:

    voices (pulse / saw / triangle / noise)  ->  stereo mix
    -> ping-pong-ish echo  ->  soft clip  ->  int16

Notes come from :mod:`spectrum.score`, which turns the song data into a sorted
list of sample-accurate events.
"""

import math
import random

SR = 22050  # sample rate for live playback; WAV export can use more

WAVE_SIZE = 512
WAVE_MASK = WAVE_SIZE - 1


def _build_tables():
    tau = 2.0 * math.pi
    sine = [math.sin(tau * i / WAVE_SIZE) for i in range(WAVE_SIZE)]
    tables = {"sine": tuple(sine)}

    def pulse(duty):
        n = int(duty * WAVE_SIZE)
        return tuple((1.0 if i < n else -1.0) for i in range(WAVE_SIZE))

    tables["pulse50"] = pulse(0.5)
    tables["pulse25"] = pulse(0.25)
    tables["pulse12"] = pulse(0.125)
    tables["pulse75"] = pulse(0.75)
    tables["saw"] = tuple(-1.0 + 2.0 * i / WAVE_SIZE for i in range(WAVE_SIZE))
    tables["tri"] = tuple(
        (4.0 / WAVE_SIZE) * abs(i - WAVE_SIZE / 2) - 1.0 for i in range(WAVE_SIZE)
    )

    # Two-inharmonic-partial bell, and a hollow "organ" (odd harmonics).
    bell = []
    organ = []
    for i in range(WAVE_SIZE):
        p = tau * i / WAVE_SIZE
        bell.append(0.62 * math.sin(p) + 0.26 * math.sin(2.76 * p)
                    + 0.16 * math.sin(5.4 * p) + 0.08 * math.sin(8.9 * p))
        organ.append(0.62 * math.sin(p) + 0.25 * math.sin(3 * p)
                     + 0.10 * math.sin(5 * p) + 0.05 * math.sin(7 * p))
    tables["bell"] = tuple(v * 0.8 for v in bell)
    tables["organ"] = tuple(v * 0.8 for v in organ)

    # Noise is a fixed table read at odd steps: repeatable, cheap, crunchy.
    rnd = random.Random(0xC0DE)
    tables["noise"] = tuple(rnd.uniform(-1.0, 1.0) for _ in range(WAVE_SIZE))
    return tables


TABLES = _build_tables()


def midi_to_freq(m):
    return 440.0 * (2.0 ** ((m - 69) / 12.0))


class Instrument:
    """A patch: one or more detuned layers plus an envelope."""

    __slots__ = (
        "name", "layers", "a", "d", "s", "r", "vib", "vib_rate", "vib_delay",
        "arp", "arp_rate", "gain", "pan", "slide", "wave",
    )

    def __init__(self, name, wave="pulse50", layers=None, a=0.004, d=0.06,
                 s=0.7, r=0.09, vib=0.0, vib_rate=5.5, vib_delay=0.15,
                 arp=None, arp_rate=14.0, gain=0.22, pan=0.0, slide=0.0):
        self.name = name
        self.wave = wave
        if layers is None:
            layers = ((1.0, 0.0, 1.0),)  # (ratio, detune cents, gain)
        self.layers = layers
        self.a = max(0.0008, a)
        self.d = max(0.0001, d)
        self.s = max(0.0, min(1.0, s))
        self.r = max(0.01, r)
        self.vib = vib
        self.vib_rate = vib_rate
        self.vib_delay = vib_delay
        self.arp = arp
        self.arp_rate = arp_rate
        self.gain = gain
        self.pan = pan
        self.slide = slide


class Voice:
    """One sounding note."""

    __slots__ = ("inst", "freq", "dur", "age", "amp", "pan", "phases",
                 "tables", "incs", "gains", "alive", "vib_phase", "arp_step")

    def __init__(self, inst, freq, dur, amp=1.0, pan=None, phase=0.0):
        self.inst = inst
        self.freq = freq
        self.dur = max(0.02, dur)
        self.age = 0.0
        self.amp = amp
        self.pan = inst.pan if pan is None else pan
        self.tables = [TABLES[inst.wave] if isinstance(inst.wave, str) else inst.wave
                       for _ in inst.layers]
        self.incs = [0.0] * len(inst.layers)
        self.gains = [l[2] for l in inst.layers]
        self.phases = [phase * WAVE_SIZE for _ in inst.layers]
        self.vib_phase = 0.0
        self.arp_step = -1
        self.alive = True
        self._set_freq(freq, 44100)

    def _set_freq(self, freq, sr):
        for k, (ratio, detune, _g) in enumerate(self.inst.layers):
            f = freq * ratio * (2.0 ** (detune / 1200.0))
            self.incs[k] = f * WAVE_SIZE / sr

    def add_to(self, lb, rb, start, n, sr, gain_mul=1.0):
        """Mix the voice into the float buffers.  Returns False when finished."""
        inst = self.inst
        a, d, s, r = inst.a, inst.d, inst.s, inst.r
        dur = self.dur
        amp = self.amp * inst.gain * gain_mul
        if amp <= 0.0:
            return False
        sp = (self.pan + 1.0) * 0.5
        if sp < 0.0:
            sp = 0.0
        elif sp > 1.0:
            sp = 1.0
        gl = amp * (1.0 - sp * 0.85)
        gr = amp * (0.15 + sp * 0.85)
        tables = self.tables
        gains = self.gains
        layers = inst.layers
        phases = self.phases
        incs = self.incs
        nlay = len(tables)
        dt = 1.0 / sr
        vib = inst.vib
        vib_rate = inst.vib_rate
        vib_delay = inst.vib_delay
        arp = inst.arp
        arp_rate = inst.arp_rate
        age = self.age
        base = self.freq
        slide = inst.slide
        arp_count = len(arp) if arp else 0
        arp_step = self.arp_step
        k = start
        end = start + n
        last = age + (n - 1) * dt
        while k < end:
            tt = age
            if tt < dur:
                if tt < a:
                    env = tt / a
                elif tt < a + d:
                    env = 1.0 - (1.0 - s) * ((tt - a) / d)
                else:
                    env = s
            else:
                rt = tt - dur
                if rt > r:
                    self.alive = False
                    break
                env = s * (1.0 - rt / r)
                if env < 0.0:
                    env = 0.0
            if vib and tt > vib_delay:
                depth = vib * min(1.0, (tt - vib_delay) / 0.25)
                mod = depth * math.sin(vib_rate * 6.283185307179586 * tt)
                freq = base * (2.0 ** (mod / 12.0))
            else:
                freq = base
            if arp:
                step = int(tt * arp_rate) % arp_count
                if step != arp_step:
                    arp_step = step
                    freq *= 2.0 ** (arp[step] / 12.0)
                    self._set_freq(freq, sr)
                    incs = self.incs
            elif slide:
                freq = base * (2.0 ** (slide * tt / 12.0))
                if (k - start) % 64 == 0:
                    self._set_freq(freq, sr)
                    incs = self.incs
            val = 0.0
            for li in range(nlay):
                p = phases[li] + incs[li]
                if p >= WAVE_SIZE:
                    p -= WAVE_SIZE * int(p / WAVE_SIZE)
                phases[li] = p
                val += tables[li][int(p)] * gains[li]
            val *= env
            lb[k] += val * gl
            rb[k] += val * gr
            age += dt
            k += 1
        self.age = age
        self.arp_step = arp_step
        if age > dur + r:
            self.alive = False
        del layers
        return self.alive


class DrumVoice:
    """Synthesised percussion: kick, snare, hat, clap, zap."""

    __slots__ = ("kind", "age", "amp", "pan", "phase", "state", "rnd", "dur")

    def __init__(self, kind, amp=1.0, pan=0.0, seed=1):
        self.kind = kind
        self.age = 0.0
        self.amp = amp
        self.pan = pan
        self.phase = 0.0
        self.state = 0.0
        self.rnd = random.Random(seed * 7919 + 13)
        self.dur = {"k": 0.42, "s": 0.24, "h": 0.055, "o": 0.30,
                    "c": 0.18, "z": 0.35}.get(kind, 0.2)

    def add_to(self, lb, rb, start, n, sr, gain_mul=1.0):
        kind = self.kind
        amp = self.amp * gain_mul
        sp = (self.pan + 1.0) * 0.5
        gl = amp * (1.0 - sp * 0.8)
        gr = amp * (0.2 + sp * 0.8)
        dt = 1.0 / sr
        age = self.age
        ph = self.phase
        st = self.state
        noise_table = TABLES["noise"]
        rnd = self.rnd
        tau = 6.283185307179586
        for k in range(start, start + n):
            t = age
            if t > self.dur:
                return False
            if kind == "k":
                f = 44.0 + 118.0 * math.exp(-t * 30.0)
                ph += f * dt
                if ph >= 1.0:
                    ph -= int(ph)
                env = math.exp(-t * 7.5)
                val = math.sin(tau * ph) * env
                if t < 0.006:
                    val += (1.0 - t / 0.006) * 0.35
                val *= 0.95
            elif kind == "s":
                idx = int((rnd.random() * 0.5 + age * 9000.0)) & WAVE_MASK
                nz = noise_table[idx]
                ph += 188.0 * dt
                tone = math.sin(tau * (ph % 1.0)) * 0.35
                env = math.exp(-t * 17.0)
                val = (nz * 0.75 + tone) * env * 0.8
            elif kind == "h" or kind == "o":
                idx = int(rnd.random() * WAVE_SIZE) & WAVE_MASK
                nz = noise_table[idx]
                # one-pole high pass, the classic "psh" of white noise hats
                st += (nz - st) * 0.55
                hp = nz - st
                rate = 55.0 if kind == "h" else 13.0
                val = hp * math.exp(-t * rate) * 0.55
            elif kind == "c":
                idx = int(rnd.random() * WAVE_SIZE) & WAVE_MASK
                nz = noise_table[idx] * (2.2 if (t * 26.0) % 1.0 < 0.3 else 0.8)
                val = nz * math.exp(-t * 22.0) * 0.6
            else:  # "z": a little laser zap for transitions
                ph += (900.0 * math.exp(-t * 9.0) + 60.0) * dt
                if ph >= 1.0:
                    ph -= int(ph)
                val = math.sin(tau * ph) * math.exp(-t * 6.0) * 0.5
            lb[k] += val * gl
            rb[k] += val * gr
            age += dt
        self.age = age
        self.phase = ph
        self.state = st
        return True


class Mixer:
    """Plays a list of score events, forever, with echo and soft clipping.

    ``fill(n)`` returns ``n`` frames of interleaved int16 stereo.  Scheduling is
    sample accurate and loops back to the top of the song when it runs out.
    """

    def __init__(self, score, sr=SR, echo=True, master=0.85, tail=1.2):
        self.score = score
        self.sr = sr
        self.events = [(int(ev.time * sr), ev) for ev in score.events]  # already sorted
        self.total = score.total_time + tail
        self.length = int(self.total * sr)
        self.master = master
        self.echo = echo
        self.voices = []
        self.position = 0          # samples rendered since start
        self.loops = 0
        self.ev_pos = 0
        beat = score.beat
        self.delay = int(beat * 0.75 * sr)
        self.feedback = 0.34
        self.dline_l = [0.0] * self.delay
        self.dline_r = [0.0] * self.delay
        self.dpos = 0
        self._rng = random.Random(99)
        self._frames_done = 0

    # ------------------------------------------------------------------ util
    def song_time(self):
        return self.position / self.sr

    def _trigger(self, ev):
        kind = ev.kind
        if kind == "note":
            voice = Voice(ev.inst, ev.freq, ev.dur, ev.amp, ev.pan,
                          phase=self._rng.random())
            self.voices.append(voice)
        elif kind == "drum":
            self.voices.append(
                DrumVoice(ev.inst, ev.amp, ev.pan, seed=self._frames_done & 0xFFF)
            )

    # ------------------------------------------------------------------ main
    def fill(self, frames):
        out = bytearray(frames * 4)
        filled = 0
        while filled < frames:
            # how far can we go before the next event or the song end?
            limit = min(frames - filled, self.length - self.position)
            if self.ev_pos < len(self.events):
                ev_sample, ev = self.events[self.ev_pos]
                limit = min(limit, ev_sample - self.position)
            if limit <= 0:
                if (self.ev_pos < len(self.events)
                        and self.events[self.ev_pos][0] <= self.position):
                    self._trigger(self.events[self.ev_pos][1])
                    self.ev_pos += 1
                    continue
                # end of song: loop
                self.position = 0
                self.ev_pos = 0
                self.voices = []
                self.loops += 1
                continue
            step = min(limit, 1024)
            lb = [0.0] * step
            rb = [0.0] * step
            alive = []
            for voice in self.voices:
                if voice.add_to(lb, rb, 0, step, self.sr):
                    alive.append(voice)
            self.voices = alive if alive else []
            # echo + soft clip + int16
            if self.echo:
                dl, dr = self.dline_l, self.dline_r
                base = int(self.position)
                fade_start = self.length - int(0.7 * self.sr)
                m = self.master
                fb = self.feedback
                dpos = self.dpos
                delay = self.delay
                o = filled * 4
                for i in range(step):
                    l = lb[i]
                    r = rb[i]
                    el = dl[dpos]
                    er = dr[dpos]
                    dl[dpos] = (l + el * fb) * 0.62
                    dr[dpos] = (r + er * fb) * 0.62
                    dpos += 1
                    if dpos >= delay:
                        dpos = 0
                    l = l + el * 0.45
                    r = r + er * 0.45
                    # fade the loop out just before it wraps around
                    g = m
                    if base + i > fade_start:
                        g *= max(0.0, (self.length - base - i) / (0.7 * self.sr))
                    l *= g
                    r *= g
                    if l > 0.94:
                        l = 0.94 + (l - 0.94) * 0.25
                    elif l < -0.94:
                        l = -0.94 + (l + 0.94) * 0.25
                    if r > 0.94:
                        r = 0.94 + (r - 0.94) * 0.25
                    elif r < -0.94:
                        r = -0.94 + (r + 0.94) * 0.25
                    out[o] = int(l * 32767.0) & 0xFF
                    out[o + 1] = (int(l * 32767.0) >> 8) & 0xFF
                    out[o + 2] = int(r * 32767.0) & 0xFF
                    out[o + 3] = (int(r * 32767.0) >> 8) & 0xFF
                    o += 4
                self.dpos = dpos
            else:
                o = filled * 4
                m = self.master
                for i in range(step):
                    l = lb[i] * m
                    r = rb[i] * m
                    if l > 0.94:
                        l = 0.94 + (l - 0.94) * 0.25
                    elif l < -0.94:
                        l = -0.94 + (l + 0.94) * 0.25
                    if r > 0.94:
                        r = 0.94 + (r - 0.94) * 0.25
                    elif r < -0.94:
                        r = -0.94 + (r + 0.94) * 0.25
                    out[o] = int(l * 32767.0) & 0xFF
                    out[o + 1] = (int(l * 32767.0) >> 8) & 0xFF
                    out[o + 2] = int(r * 32767.0) & 0xFF
                    out[o + 3] = (int(r * 32767.0) >> 8) & 0xFF
                    o += 4
            self.position += step
            self._frames_done += step
            filled += step
        return bytes(out)

    # --------------------------------------------------------------- offline
    def render_seconds(self, seconds, dtype="int16"):
        """Render ``seconds`` of audio into a float list (interleaved stereo)."""
        n = int(seconds * self.sr)
        data = self.fill(n)
        vals = []
        for i in range(0, len(data), 2):
            vals.append(int.from_bytes(data[i:i + 2], "little", signed=True) / 32768.0)
        return vals
