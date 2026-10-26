"""A tiny HTTP server that plays the demo in a browser, music included.

The sandbox terminal has no speakers, but a browser does: this serves the
rendered frames as PNGs and the generated soundtrack as a WAV, and a page
that keeps them in sync.  Stdlib only, of course.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from . import png, songs, stage, synth
from .pacer import FPS

_PAGE = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>NEON SKY - a Python demo</title>
<style>
  html,body{margin:0;height:100%;background:#000;color:#9ef;
    font:14px/1.5 monospace;display:flex;flex-direction:column;
    align-items:center;justify-content:center;gap:12px}
  canvas{image-rendering:pixelated;image-rendering:crisp-edges;
    border:1px solid #123;background:#000;
    width:min(92vw, calc(92vh * 16 / 9));aspect-ratio:16/9}
  button{font:inherit;background:#123;color:#9ef;border:1px solid #369;
    padding:6px 18px;cursor:pointer}
  button:hover{background:#234}
  #hud{opacity:.75;white-space:pre}
</style>
</head>
<body>
<canvas id="cv"></canvas>
<div><button id="play">PLAY</button> <span id="hud"></span></div>
<script type="module">
const meta = await (await fetch('/meta.json')).json();
const cv = document.getElementById('cv');
cv.width = meta.w; cv.height = meta.h;
const ctx = cv.getContext('2d');
const hud = document.getElementById('hud');
const audio = new Audio('/music.wav');
audio.loop = true;

let t0 = null, playing = false, raf = 0, lastFrame = -1;

function sceneAt(t) {
  for (const s of meta.scenes) if (t >= s.start && t < s.start + s.dur) return s;
  return meta.scenes[meta.scenes.length - 1];
}

async function drawFrame(t) {
  const res = await fetch('/frame.png?t=' + t.toFixed(3), {cache: 'no-store'});
  const bmp = await createImageBitmap(await res.blob());
  ctx.drawImage(bmp, 0, 0);
  bmp.close();
}

let pending = false, lastT = -1;
function loop() {
  const t = (performance.now() / 1000 - t0) % meta.total;
  // keep the soundtrack beat-locked to the picture
  if (audio.duration && Math.abs(audio.currentTime - (t % audio.duration)) > 0.25)
    audio.currentTime = t % audio.duration;
  const s = sceneAt(t);
  hud.textContent = s.name + '  ' + t.toFixed(1) + 's / ' + meta.total.toFixed(1) + 's';
  // ask for a new frame at the demo frame rate, one request at a time
  if (!pending && t - lastT >= 1 / meta.fps - 0.004) {
    lastT = t; pending = true;
    drawFrame(t).finally(() => { pending = false; });
  }
  raf = requestAnimationFrame(loop);
}

document.getElementById('play').onclick = async (e) => {
  if (!playing) {
    t0 = performance.now() / 1000;
    try { await audio.play(); } catch (err) { hud.textContent = '(no audio: ' + err + ')'; }
    playing = true; e.target.textContent = 'STOP';
    loop();
  } else {
    playing = false; e.target.textContent = 'PLAY';
    cancelAnimationFrame(raf); audio.pause();
  }
};

// first frame before anyone presses anything
drawFrame(0.0);
hud.textContent = 'press PLAY';
</script>
</body>
</html>
"""


class DemoServer:
    def __init__(self, bpm=None):
        self.score = songs.build(bpm)
        self.stage = stage.Stage(self.score)
        self._wav = None
        self._lock = threading.Lock()

    def wav_bytes(self):
        with self._lock:
            if self._wav is None:
                mixer = synth.Mixer(self.score)
                from . import wav as wavmod
                self._wav = wavmod.encode_pcm(mixer.fill(mixer.length),
                                              synth.SR, 2)
        return self._wav

    def meta(self):
        return {
            "w": self.stage.width, "h": self.stage.height,
            "fps": FPS, "total": self.stage.total,
            "song": self.score.total_time,
            "scenes": [
                {"name": eff.name, "title": eff.title,
                 "start": round(start, 3), "dur": round(dur, 3)}
                for start, dur, eff in self.stage.segments],
        }


def make_handler(demo):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "NeonSky/1.0"

        def log_message(self, fmt, *a):  # keep the console quiet-ish
            pass

        def _send(self, code, ctype, body):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            url = urlparse(self.path)
            if url.path in ("/", "/index.html"):
                self._send(200, "text/html; charset=utf-8",
                           _PAGE.encode("utf-8"))
            elif url.path == "/meta.json":
                self._send(200, "application/json",
                           json.dumps(demo.meta()).encode())
            elif url.path == "/music.wav":
                self._send(200, "audio/wav", demo.wav_bytes())
            elif url.path == "/frame.png":
                qs = parse_qs(url.query)
                t = float(qs.get("t", ["0"])[0])
                rgb = demo.stage.render(t)
                self._send(200, "image/png",
                           png.encode_rgb(demo.stage.width,
                                          demo.stage.height, rgb))
            else:
                self._send(404, "text/plain", b"not found")

    return Handler


def serve(port=8000, bpm=None, host="0.0.0.0"):
    demo = DemoServer(bpm)
    httpd = ThreadingHTTPServer((host, port), make_handler(demo))
    print("NEON SKY preview on http://%s:%d/  (ctrl-c to stop)" % (host, port))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0
