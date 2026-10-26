"""Live audio: render the soundtrack to WAV and try to play it.

The sandbox has no sound hardware guarantees, so playback is best effort:
we look for a command line player (aplay, ffplay, paplay, afplay, mpv...),
and on Windows fall back to ``winsound``.  If nothing is available the demo
still runs, silently, and ``tools/preview.py`` plays the very same WAV in
the browser instead.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import threading

from . import songs, synth, wav

PLAYERS = (
    ("aplay", ["aplay", "-q"]),
    ("ffplay", ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]),
    ("paplay", ["paplay"]),
    ("mpv", ["mpv", "--no-video", "--really-quiet"]),
    ("mplayer", ["mplayer", "-really-quiet"]),
    ("afplay", ["afplay"]),
)


def find_player():
    for _name, cmd in PLAYERS:
        if shutil.which(cmd[0]):
            return cmd
    return None


def make_wav(path=None, bpm=None):
    """Render the whole soundtrack; returns (path, seconds)."""
    score = songs.build(bpm)
    mixer = synth.Mixer(score)
    pcm = mixer.fill(mixer.length)  # interleaved int16 stereo
    if path is None:
        fd, path = tempfile.mkstemp(prefix="neon-sky-", suffix=".wav")
        os.close(fd)
    wav.write_pcm(path, pcm, synth.SR, 2)
    return path, score.total_time


class Player:
    """Starts a system player for a WAV file in a background process."""

    def __init__(self, path):
        self.path = path
        self.proc = None
        self._winsound = None

    def start(self):
        cmd = find_player()
        if cmd is not None:
            self.proc = subprocess.Popen(
                cmd + [self.path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        if sys.platform == "win32":  # pragma: no cover - windows only
            import winsound

            def _play():
                winsound.PlaySound(self.path, winsound.SND_FILENAME)

            self._winsound = threading.Thread(target=_play, daemon=True)
            self._winsound.start()
            return True
        return False

    def stop(self):
        if self.proc is not None:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=2)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            self.proc = None
