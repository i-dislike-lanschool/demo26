"""The show: which effect runs when, transitions, and the render call."""

from .canvas import Canvas
from .music_sync import MusicSync

FADE = 0.45  # seconds of black between scenes


def default_effects():
    from .effects.loader import Loader
    from .effects.logo import Logo
    from .effects.plasma import Plasma
    from .effects.mode7 import Mode7
    from .effects.tunnel import Tunnel
    from .effects.scroller import Scroller
    from .effects.vector import VectorTorus
    from .effects.road import NeonRoad
    from .effects.copper import Copper
    from .effects.fire import Fire
    from .effects.finale import Finale

    return [
        Loader(), Logo(), Plasma(), Mode7(), Tunnel(), Scroller(),
        VectorTorus(), NeonRoad(), Copper(), Fire(), Finale(),
    ]


class Stage:
    """Holds the timeline and turns a time value into a finished RGB frame."""

    def __init__(self, score, width=192, height=108, effects=None):
        self.width = width
        self.height = height
        self.score = score
        self.sync = MusicSync(score)
        self.cv = Canvas(width, height)
        self.effects = list(effects) if effects is not None else default_effects()
        self.bar = score.beat * 4.0
        self.segments = []
        t = 0.0
        for effect in self.effects:
            effect.setup(self.cv)
            dur = max(0.5, effect.bars * self.bar)
            self.segments.append((t, dur, effect))
            t += dur
        self.total = t
        self.current = None
        self._fade_cache = {}

    # ------------------------------------------------------------------ main
    def locate(self, t):
        """Which effect is on screen at time ``t`` (looping)."""
        t %= self.total
        for start, dur, effect in self.segments:
            if start <= t < start + dur:
                return effect, t - start, dur
        start, dur, effect = self.segments[-1]
        return effect, dur, dur

    def fade_for(self, local, dur):
        f = 1.0
        if local < FADE:
            f = local / FADE
        elif local > dur - FADE:
            f = (dur - local) / FADE
        if f < 0.0:
            f = 0.0
        elif f > 1.0:
            f = 1.0
        return f

    def _faded(self, pal, factor):
        key = (id(pal), round(factor, 2))
        cached = self._fade_cache.get(key)
        if cached is not None:
            return cached
        out = tuple(tuple(int(v * factor) for v in rgb) for rgb in pal)
        if len(self._fade_cache) < 256:
            self._fade_cache[key] = out
        return out

    def render(self, t):
        """Render one frame at demo time ``t``; returns RGB bytes."""
        effect, local, dur = self.locate(t)
        music = self.sync.advance(t)
        self.current = effect
        cv = self.cv
        cv.clear(0)
        effect.render(cv, local, music)
        pal = effect.palette(local, music)
        fade = self.fade_for(local, dur)
        if fade < 0.999:
            pal = self._faded(pal, fade)
        return cv.to_rgb(pal)

    def render_png(self, t):
        from . import png

        rgb = self.render(t)
        return png.encode_rgb(self.width, self.height, rgb)


def render_frames(score, fps, seconds, progress=None):
    """Yield (frame_index, time, rgb) for offline rendering."""
    stage = Stage(score)
    n = int(seconds * fps)
    for i in range(n):
        t = i / fps
        yield i, t, stage.render(t)
        if progress is not None:
            progress(i + 1, n)
