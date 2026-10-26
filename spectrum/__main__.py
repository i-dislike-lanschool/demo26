"""Command line entry point: ``python -m spectrum <command>``."""

import argparse
import os
import sys
import time

from . import songs, stage
from .pacer import Pacer, FPS


def _cmd_play(args):
    from . import audio as audio_mod
    from .console import ConsoleScreen

    score = songs.build(args.bpm)
    effects = None
    if args.scenes:
        from . import effects as effects_pkg
        effects = effects_pkg.build(args.scenes.split(","))
    st = stage.Stage(score, effects=effects)

    player = None
    if not args.no_audio:
        path, _secs = audio_mod.make_wav()
        player = audio_mod.Player(path)
        if not player.start():
            print("No system audio player found - running silent.\n"
                  "Try `python -m spectrum preview` for sound in the browser.")
            player = None

    screen = ConsoleScreen()
    cols, rows = screen.geometry(st.width, st.height)
    pacer = Pacer(FPS, speed=args.speed)
    screen.start()
    try:
        while True:
            t = pacer.elapsed()
            if t >= st.total:
                pacer = Pacer(FPS, speed=args.speed)  # loop the show
                continue
            rgb = st.render(t)
            screen.show(rgb, st.width, st.height, cols, rows)
            eff, _local, _dur = st.locate(t)
            screen.print_line(
                "\x1b[2K NEON SKY  %5.1fs  %-9s  q=quit  %s" %
                (t, eff.name, "" if player else "(silent)"))
            if _quit_pressed():
                break
            pacer.tick()
    except KeyboardInterrupt:
        pass
    finally:
        screen.close()
        if player is not None:
            player.stop()
    return 0


def _quit_pressed():
    """Non-blocking key check, unix and windows."""
    try:
        if os.name == "nt":
            import msvcrt
            if msvcrt.kbhit():
                return msvcrt.getch() in (b"q", b"Q", b"\x1b")
            return False
        import select
        import termios
        import tty
        if select.select([sys.stdin], [], [], 0)[0]:
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setcbreak(fd)
                ch = sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
            return ch in ("q", "Q", "\x1b")
    except Exception:
        return False
    return False


def _cmd_shot(args):
    from . import png

    score = songs.build(args.bpm)
    st = stage.Stage(score)
    rgb = st.render(args.time)
    if args.scale > 1:
        rgb = png.scale_nearest(st.width, st.height, rgb, args.scale)
        w, h = st.width * args.scale, st.height * args.scale
    else:
        w, h = st.width, st.height
    png.write_rgb(args.out, w, h, rgb)
    print("wrote %s (%dx%d)" % (args.out, w, h))
    return 0


def _cmd_wav(args):
    from . import audio as audio_mod

    path, secs = audio_mod.make_wav(args.out, args.bpm)
    print("wrote %s (%.1f s of chiptune)" % (path, secs))
    return 0


def _cmd_preview(args):
    from .server import serve

    serve(port=args.port, bpm=args.bpm)
    return 0


def _cmd_scenes(_args):
    score = songs.build()
    st = stage.Stage(score)
    print("NEON SKY - %.1f s, %d scenes, song %.1f s" %
          (st.total, len(st.segments), score.total_time))
    for start, dur, eff in st.segments:
        print("  %6.1f .. %6.1f  %-9s %s" % (start, start + dur, eff.name,
                                             eff.title))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="spectrum",
        description="NEON SKY - a ZX-Spectrum-style demo in pure Python.")
    sub = ap.add_subparsers(dest="cmd")

    p = sub.add_parser("play", help="run the demo in the terminal")
    p.add_argument("--speed", type=float, default=1.0)
    p.add_argument("--bpm", type=float, default=None)
    p.add_argument("--scenes", default=None,
                   help="comma separated scene names instead of the show")
    p.add_argument("--no-audio", action="store_true")
    p.set_defaults(fn=_cmd_play)

    p = sub.add_parser("shot", help="render one frame to a PNG")
    p.add_argument("time", type=float)
    p.add_argument("out")
    p.add_argument("--scale", type=int, default=3)
    p.add_argument("--bpm", type=float, default=None)
    p.set_defaults(fn=_cmd_shot)

    p = sub.add_parser("wav", help="render the soundtrack to a WAV file")
    p.add_argument("out", nargs="?", default="neon-sky.wav")
    p.add_argument("--bpm", type=float, default=None)
    p.set_defaults(fn=_cmd_wav)

    p = sub.add_parser("preview", help="serve the demo with music in a browser")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--bpm", type=float, default=None)
    p.set_defaults(fn=_cmd_preview)

    p = sub.add_parser("scenes", help="list the scenes and their timings")
    p.set_defaults(fn=_cmd_scenes)

    args = ap.parse_args(argv)
    if not getattr(args, "fn", None):
        ap.print_help()
        return 0
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
