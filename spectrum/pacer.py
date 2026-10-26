"""Keeping time: frame pacing for the live view and the video/FX timeline."""

import time

FPS = 25.0  # the demo runs at Spectrum-ish speed: 25 frames a second


class Pacer:
    """Sleeps just enough to keep a fixed frame rate, with catch-up."""

    def __init__(self, fps=FPS, speed=1.0):
        self.fps = fps
        self.speed = speed
        self.period = 1.0 / fps
        self.next_frame = time.perf_counter()
        self.start = self.next_frame
        self.frames = 0
        self.backlog = 0

    def tick(self):
        """Wait for the next slot.  Returns (frame_index, time_in_seconds)."""
        now = time.perf_counter()
        if self.next_frame > now:
            time.sleep(self.next_frame - now)
        self.next_frame += self.period
        now = time.perf_counter()
        if self.next_frame < now - self.period * 2:
            # Fell behind badly (slow terminal, loaded machine): resync instead
            # of trying to run at double speed forever.
            self.next_frame = now + self.period
        t = (now - self.start) * self.speed
        self.frames += 1
        return self.frames, t

    def elapsed(self):
        return (time.perf_counter() - self.start) * self.speed


class Clock:
    """Fake clock for offline rendering: ``t = frame / fps``."""

    def __init__(self, fps=FPS):
        self.fps = fps
        self.frame = 0

    def advance(self):
        self.frame += 1
        return self.time()

    def time(self):
        return self.frame / self.fps
