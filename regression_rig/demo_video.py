"""Scripted demo video of DidaRec (silent, captioned), made with the rig.

    python demo_video.py cr

The rig drives the real app in its demo look (a lecture slide for the shared
screen, a drawn presenter for the webcam) while Playwright records the page.
A drawn pointer, click ripples and a caption bar are overlaid on the page (not
on the recorded canvas). Chrome's own share picker and save dialog are
stand-ins, so captions say so where they would appear.

Writes demo/didarec-demo.webm and demo/didarec-demo.vtt (the captions, with
the times they were shown), plus demo/didarec-demo-poster.png.
"""
import os, shutil, subprocess, sys, time
from harness import run, HERE

OUT = os.path.join(os.path.dirname(HERE), "demo")

OVERLAY = r"""
(() => {
  if (window.__demo) return;
  const cur = document.createElement('div');
  cur.id = '__demoCursor';
  cur.style.cssText = 'position:fixed;left:0;top:0;width:22px;height:22px;z-index:99999;pointer-events:none;transform:translate(-3px,-2px);transition:left .05s linear, top .05s linear;';
  cur.innerHTML = "<svg viewBox='0 0 24 24' width='22' height='22'><path d='M4 2 L20 12 L12 13.5 L8 21 Z' fill='#EFE6D3' stroke='#1F2B3D' stroke-width='1.6' stroke-linejoin='round'/></svg>";
  document.body.appendChild(cur);
  const cap = document.createElement('div');
  cap.id = '__demoCaption';
  cap.style.cssText = "position:fixed;left:0;right:0;bottom:0;height:88px;padding:0 6%;display:flex;align-items:center;justify-content:center;background:#1F2B3D;color:#EFE6D3;font:600 23px/1.3 'Roboto','Segoe UI',Arial,sans-serif;text-align:center;z-index:99998;pointer-events:none;border-top:2px solid #4A5D7C;";
  document.body.appendChild(cap);
  window.__demo = {
    move(x, y) { cur.style.left = x + 'px'; cur.style.top = y + 'px'; },
    ripple(x, y) {
      const r = document.createElement('div');
      r.style.cssText = 'position:fixed;left:' + (x - 18) + 'px;top:' + (y - 18) + 'px;width:36px;height:36px;border-radius:50%;border:3px solid #9CCDEE;z-index:99997;pointer-events:none;opacity:.9;transition:transform .45s ease-out, opacity .45s ease-out;';
      document.body.appendChild(r);
      requestAnimationFrame(() => { r.style.transform = 'scale(2.2)'; r.style.opacity = '0'; });
      setTimeout(() => r.remove(), 500);
    },
    caption(t) { cap.textContent = t || ''; },
  };
})();
"""


class Demo:
    def __init__(self, r):
        self.r = r
        self.t0 = time.time()
        self.cues = []       # (start, end, text)
        self.open = None
        self.x, self.y = 640, 400

    def t(self):
        return time.time() - self.t0

    def say(self, text):
        now = self.t()
        if self.open:
            s, txt = self.open
            self.cues.append((s, now, txt))
        self.open = (now, text)
        self.r.ev("t => __demo.caption(t)", text)

    def hush(self):
        if self.open:
            s, txt = self.open
            self.cues.append((s, self.t(), txt))
            self.open = None
        self.r.ev("() => __demo.caption('')")

    def glide(self, x, y, ms=600):
        steps = max(8, int(ms / 30))
        for i in range(1, steps + 1):
            cx = self.x + (x - self.x) * i / steps
            cy = self.y + (y - self.y) * i / steps
            self.r.page.mouse.move(cx, cy)
            self.r.ev("([x, y]) => __demo.move(x, y)", [cx, cy])
            self.r.wait(30)
        self.x, self.y = x, y

    def click(self, selector, wait_after=700):
        box = self.r.page.locator(selector).first.bounding_box()
        x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        self.glide(x, y)
        self.r.wait(250)
        self.r.ev("([x, y]) => __demo.ripple(x, y)", [x, y])
        self.r.page.mouse.click(x, y)
        self.r.wait(wait_after)
        if os.environ.get('DEMO_DEBUG'):
            u = self.r.ui()
            print('  click %-34s -> status=%r pause=%r rec=%r paused=%r err=%r' % (selector, u['status'], u['btnPause']['text'], u['rec'], u['paused'], u['err'][:60]), flush=True)

    def vtt(self):
        def ts(s):
            h = int(s // 3600); m = int(s % 3600 // 60); sec = s % 60
            return "%02d:%02d:%06.3f" % (h, m, sec)
        out = ["WEBVTT", ""]
        for i, (s, e, txt) in enumerate(self.cues, 1):
            out += [str(i), ts(s) + " --> " + ts(max(e, s + 0.5)), txt, ""]
        return "\n".join(out)


def demo(r):
    os.makedirs(OUT, exist_ok=True)
    r.start("demo")
    r.cfg(demo=True, camMode="canvas")
    r.ev(OVERLAY)
    d = Demo(r)
    if r.page.video:
        d.video_path = r.page.video.path()
    d.say("DidaRec records your screen, your webcam and your voice — right in the browser. Nothing to install, no account.")
    d.glide(640, 300, 800); r.wait(3200)

    d.say("Turn on your microphone and webcam.")
    d.click("#toggleMic", 600)
    d.click("#toggleCamera", 900)
    r.wait(800)

    r.cfg(screenMode="ok", screenId=1, screenAudio=True, screenW=1280, screenH=720)
    d.say("Select Screen asks your browser what to share — a screen, a window or a tab. (A stand-in here.)")
    d.click("#btnSelectScreen", 1200)
    r.wait(1500)

    d.say("Click Record. DidaRec saves as you go, so a crash can't lose your work.")
    d.click("#btnRecord", 800)
    r.wait(2200)
    r.page.screenshot(path=os.path.join(OUT, "didarec-demo-poster.png"), clip={"x": 0, "y": 0, "width": 1280, "height": 1000 - 88})
    r.wait(2000)

    d.say("Pause whenever you like. Each pause starts a new part you can work on later.")
    d.click("#btnPause", 900)
    r.wait(800)
    d.say("While paused you can change the screen, switch the webcam off, mute the mic — or fill the picture with your webcam.")
    d.click("#toggleFullscreen", 1200)
    d.click("#btnPause", 600)        # Resume recording
    r.wait(3200)
    d.click("#btnPause", 700)        # Pause
    d.click("#toggleFullscreen", 900)
    d.click("#btnPause", 600)        # Resume
    r.wait(2800)

    d.say("Stop & review shows every part. Play one on its own, delete it, or replace it with a new take.")
    d.click("#btnStopReview", 400)
    r.page.wait_for_function("document.getElementById('reviewPane').classList.contains('visible') && document.getElementById('reviewVideo').readyState >= 1", timeout=60000)
    r.wait(1200)
    rows = r.page.locator("#reviewPartsList .review-part-row")
    try:
        box = rows.nth(1).bounding_box()
        d.glide(box["x"] + 60, box["y"] + box["height"] / 2, 700)
    except Exception:
        pass
    r.wait(2600)

    d.say("Save as is writes one video file. Chrome asks where to put it. (A stand-in here.)")
    d.click("#reviewPane .btn-save-as-is", 300)
    try:
        r.page.wait_for_function("n => __dr.saveDone > n", arg=0, timeout=60000)
    except Exception:
        pass
    r.wait(1500)

    d.say("Free and open source. Your video stays on your computer.  bluebrazelton-dotcom.github.io/DidaRec")
    r.wait(4500)
    d.hush()
    r.wait(600)

    vtt = d.vtt()
    with open(os.path.join(OUT, "didarec-demo.vtt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(vtt)
    t_end = d.t()
    r.close()
    src = getattr(d, "video_path", None)
    if not (src and os.path.exists(src)):
        print("no video file produced (set DIDAREC_VIDEO)", flush=True)
        return
    # Playwright starts the recording when the page opens, a few seconds before
    # the overlay (and the caption clock) exist. Cut that head off so the
    # captions line up, and re-encode as VP9 for the web.
    out = os.path.join(OUT, "didarec-demo.webm")
    try:
        dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src]).decode().strip())
        off = max(0.0, dur - t_end)
        subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-ss", "%.3f" % off, "-i", src, "-an",
                               "-c:v", "libvpx-vp9", "-crf", "33", "-b:v", "0", "-row-mt", "1", "-deadline", "good", "-cpu-used", "2",
                               "-pix_fmt", "yuv420p", out])
        print("video %d bytes (raw %.1fs, head cut %.2fs); %d captions; %.1fs" % (os.path.getsize(out), dur, off, len(d.cues), t_end), flush=True)
    except Exception as e:
        shutil.copyfile(src, out)
        print("ffmpeg unavailable (%s): raw video copied; captions are offset" % e, flush=True)


if __name__ == "__main__":
    os.environ.setdefault("DIDAREC_VIDEO", os.path.join(HERE, "out_cr", "video"))
    run(sys.argv[1] if len(sys.argv) > 1 else "cr", [demo], 8799)
