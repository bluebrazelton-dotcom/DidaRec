"""DidaRec #20 regression rig: drives the real app in a real browser engine.

Read-only against the repo (served over http://localhost). All output lands
in this scratch folder: out_<browser>/ (saved recordings), results_<browser>.json.
"""
import json, os, shutil, sys, threading, time, traceback
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("DIDAREC_APP") or os.path.dirname(HERE)
STUBS = os.path.join(HERE, "stubs.js")


def make_server(outdir, port):
    class H(SimpleHTTPRequestHandler):
        def translate_path(self, path):
            p = path.split("?", 1)[0].split("#", 1)[0]
            if p.startswith("/out/"):
                return os.path.join(outdir, p[5:].replace("/", os.sep))
            if p.startswith("/app/"):
                return os.path.join(REPO, p[5:].replace("/", os.sep))
            return os.path.join(outdir, "__none__")

        def do_PUT(self):
            if not self.path.startswith("/out/"):
                self.send_response(403); self.end_headers(); return
            n = int(self.headers.get("Content-Length", "0"))
            dest = os.path.join(outdir, self.path[5:])
            with open(dest, "wb") as f:
                left = n
                while left > 0:
                    b = self.rfile.read(min(left, 1 << 20))
                    if not b:
                        break
                    f.write(b); left -= len(b)
            self.send_response(200); self.end_headers()

        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def log_message(self, *a):
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


class Rig:
    def __init__(self, kind, port, headless=True):
        self.kind = kind  # 'cr' or 'ff'
        self.port = port
        self.headless = headless
        self.out = os.path.join(HERE, "out_" + kind)
        self.profiles = os.path.join(HERE, "profiles_" + kind)
        os.makedirs(self.out, exist_ok=True)
        os.makedirs(self.profiles, exist_ok=True)
        with open(os.path.join(self.out, "blank.html"), "w", newline="\n") as f:
            f.write("<!doctype html><meta charset=utf-8><title>probe</title>")
        self.srv = make_server(self.out, port)
        self.base = "http://localhost:%d" % port
        self.app = self.base + "/app/index.html"
        self.pw = sync_playwright().start()
        self.ctx = None
        self.page = None
        self.results = {}
        part = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        self.results_path = os.path.join(HERE, "results_%s%s.json" % (kind, "" if part == "part1" else "_" + part))
        if os.path.exists(self.results_path):
            with open(self.results_path, encoding="utf-8") as f:
                self.results = json.load(f)
        self.console = []
        self.downloads = []
        self._n = 0
        self.version = None

    # ---------- browser lifecycle ----------
    def launch(self, profile=None, fresh=True):
        self.close()
        if profile is None:
            self._n += 1
            profile = "p%03d_%d" % (self._n, int(time.time()))
        pdir = os.path.join(self.profiles, profile)
        if fresh and os.path.exists(pdir):
            shutil.rmtree(pdir, ignore_errors=True)
        self.profile = profile
        if self.kind == "cr":
            self.ctx = self.pw.chromium.launch_persistent_context(
                pdir, channel="chrome", headless=self.headless, accept_downloads=True,
                args=["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream",
                      "--autoplay-policy=no-user-gesture-required"],
                viewport={"width": 1400, "height": 1000})
        else:
            self.ctx = self.pw.firefox.launch_persistent_context(
                pdir, headless=self.headless, accept_downloads=True,
                firefox_user_prefs={
                    "media.navigator.streams.fake": True,
                    "media.navigator.permission.disabled": True,
                    "media.autoplay.default": 0,
                    "media.autoplay.blocking_policy": 0,
                },
                viewport={"width": 1400, "height": 1000})
        self.ctx.add_init_script(path=STUBS)
        self.ctx.set_default_timeout(20000)
        self.page = self.ctx.pages[0] if self.ctx.pages else self.ctx.new_page()
        self._wire(self.page)
        if self.version is None:
            try:
                self.version = self.ctx.browser.version if self.ctx.browser else None
            except Exception:
                self.version = None
        return self.page

    def _wire(self, page):
        page.on("console", lambda m: self.console.append((time.time(), m.type, m.text[:300])))
        page.on("pageerror", lambda e: self.console.append((time.time(), "pageerror", str(e)[:300])))
        page.on("dialog", lambda d: (self.console.append((time.time(), "dialog", d.type + ": " + d.message[:200])), d.dismiss()))
        page.on("download", lambda d: self.downloads.append(d.suggested_filename))

    def dialogs(self):
        return [c for c in self.console if c[1] == "dialog"]

    def save_count(self):
        """How many saves have been initiated on this page (dialog requests in Chrome, downloads in Firefox)."""
        if self.kind == "cr":
            return self.ev("__dr.log.save.length")
        return len(self.downloads)

    def open(self):
        self.page.goto(self.app)
        self.page.wait_for_function("typeof state !== 'undefined' && !!window.__dr")
        self.page.wait_for_timeout(400)
        if self.version is None:
            self.version = self.page.evaluate("navigator.userAgent")
        return self.page

    def start(self, profile=None, fresh=True):
        self.launch(profile, fresh)
        return self.open()

    def kill_tab(self):
        """Ctrl+W equivalent: tab dies without any unload handlers, context survives."""
        old = self.page
        self.page = self.ctx.new_page()
        self._wire(self.page)
        old.close(run_before_unload=False)
        return self.open()

    def kill_browser(self):
        """Whole-browser death, then reopen the same profile."""
        prof = self.profile
        self.close()
        time.sleep(1.0)
        return self.start(prof, fresh=False)

    def reload(self):
        self.page.reload()
        self.page.wait_for_function("typeof state !== 'undefined' && !!window.__dr")
        self.page.wait_for_timeout(400)

    def close(self):
        if self.ctx:
            try:
                self.ctx.close()
            except Exception:
                pass
        self.ctx = None
        self.page = None

    def shutdown(self):
        self.close()
        try:
            self.pw.stop()
        except Exception:
            pass
        self.srv.shutdown()

    # ---------- app helpers ----------
    def ev(self, js, arg=None):
        return self.page.evaluate(js, arg)

    def cfg(self, **kw):
        self.ev("o => __dr.setCfg(o)", kw)

    def wait(self, ms):
        self.page.wait_for_timeout(ms)

    def ui(self):
        return self.ev("""() => {
          const vis = (id) => { const e = document.getElementById(id); if (!e) return null; const cs = getComputedStyle(e); return cs.display !== 'none' && cs.visibility !== 'hidden'; };
          const txt = (id) => { const e = document.getElementById(id); return e ? e.textContent.trim() : null; };
          const eb = document.getElementById('errorBanner');
          return {
            status: txt('statusText'), timer: txt('timer'), chunks: (c => (+c > 0 ? c + ' saved' : ''))((document.getElementById('chunkCount').dataset || {}).count || '0'),
            err: vis('errorBanner') ? txt('errorBannerMsg') : '', errClass: eb.className,
            recovery: vis('recoveryBanner'), recoveryInfo: txt('recoveryInfo'),
            dlConfirm: vis('downloadConfirm'), stitchFallback: vis('stitchFallback'), saveNeedsClick: vis('saveNeedsClick'),
            placeholder: vis('placeholder'),
            screenActive: document.getElementById('toggleScreen').classList.contains('active'),
            camActive: document.getElementById('toggleCamera').classList.contains('active'),
            micActive: document.getElementById('toggleMic').classList.contains('active'),
            btnSelect: { vis: vis('btnSelectScreen'), text: txt('btnSelectScreen'), sel: document.getElementById('btnSelectScreen').classList.contains('selected') },
            btnRecord: { vis: vis('btnRecord'), dis: document.getElementById('btnRecord').disabled, text: txt('btnRecord') },
            btnPause: { vis: vis('btnPause'), text: txt('btnPause') },
            btnChange: vis('btnChangeScreen'), btnStop: { vis: vis('btnStop'), text: txt('btnStop') },
            btnStopReview: { vis: vis('btnStopReview'), text: txt('btnStopReview') },
            btnUndo: vis('btnUndoReRecord'), controls: vis('controlsBar'),
            review: vis('reviewPane'), reviewStatus: txt('reviewStatus'), captions: vis('captionEditor'), captionStatus: txt('captionStatus'),
            rec: state.recording, paused: state.paused, prior: state.priorSegments.length,
            hasScreen: !!state.screenStream, hasCam: !!state.cameraStream, sources: Object.assign({}, state.sources),
          };
        }""")

    def select_screen(self, sid=1, audio=False, w=1280, h=720, mode="ok"):
        self.cfg(screenMode=mode, screenId=sid, screenAudio=audio, screenW=w, screenH=h)
        self.page.click("#btnSelectScreen")
        if mode == "ok":
            self.page.wait_for_function("document.getElementById('btnSelectScreen').textContent.trim() === 'Change Screen'")
        else:
            self.wait(500)

    def record(self, seconds, wait_chunk=True):
        self.page.click("#btnRecord")
        self.page.wait_for_function("state.recording === true")
        if wait_chunk:
            # Firefox can take ~7.5s to deliver its first chunk
            self.page.wait_for_function("state.chunkIndex > 0", timeout=30000)
        self.wait(int(seconds * 1000))

    def stop_save(self, tag, button="#btnStop", resolve="arrived", timeout=120000):
        """Click a save-triggering button and capture the file.
        Chrome: the stand-in picker writes to OPFS, then it's exported to out/.
        Firefox: the real download is captured to out/.
        Returns the file path (or None if nothing was produced)."""
        return self.save_via(tag, lambda: self.page.click(button), resolve, timeout)

    def save_via(self, tag, trigger, resolve="arrived", timeout=120000):
        path = os.path.join(self.out, tag)
        if self.kind == "cr":
            n0 = self.ev("__dr.saveDone")
            trigger()
            self.page.wait_for_function("n => __dr.saveDone > n", arg=n0, timeout=timeout)
            self.wait(400)
            r = self.ev("t => __dr.exportLast(t)", tag)
            self.last_name = self.ev("__dr.log.save[__dr.log.save.length - 1].name")
            return path if r.get("ok") else None
        with self.page.expect_download(timeout=timeout) as di:
            trigger()
        di.value.save_as(path)
        self.last_name = di.value.suggested_filename
        if resolve:
            self.page.wait_for_selector("#downloadConfirm.visible", timeout=15000)
            if resolve == "arrived":
                self.page.click("#downloadConfirm button.btn-save")
            elif resolve == "keep":
                self.page.click("#downloadConfirm button.btn-record")
            self.wait(300)
        return path

    def probe(self, tag, **opts):
        p = self.ctx.new_page()
        try:
            p.goto(self.base + "/out/blank.html")
            p.wait_for_function("!!window.__dr")
            return p.evaluate("([u, o]) => __dr.probe(u, o)", ["/out/" + tag, opts])
        finally:
            p.close()

    def audio(self, tag):
        p = self.ctx.new_page()
        try:
            p.goto(self.base + "/out/blank.html")
            p.wait_for_function("!!window.__dr")
            return p.evaluate("u => __dr.audioInfo(u)", "/out/" + tag)
        finally:
            p.close()

    # ---------- results ----------
    def rec(self, item, status, evidence):
        self.results[item] = {"status": status, "evidence": evidence, "at": time.strftime("%Y-%m-%d %H:%M:%S")}
        with open(self.results_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(self.results, f, indent=1, ensure_ascii=False)
        lim = 2500 if status in ("FAIL", "ERROR") else 230
        print(("[%s] %-6s %-5s %s" % (self.kind, item, status, evidence[:lim])).encode("ascii", "replace").decode(), flush=True)

    def check(self, item, cond, evidence):
        self.rec(item, "PASS" if cond else "FAIL", evidence)
        return bool(cond)


def summarize(pr):
    """Compact view of a probe result."""
    s = pr["samples"]
    ok = [x for x in s if x["valid"]]
    return {"dur": None if pr["duration"] is None else round(pr["duration"], 2) if pr["duration"] != float("inf") else "inf",
            "size": pr["size"], "wh": [pr["w"], pr["h"]], "n": len(s), "valid": len(ok),
            "ids": sorted(set(x["id"] for x in ok)),
            "ds": [x["ds"] for x in s], "maxSeekMs": max([x["seekMs"] for x in s] or [0])}


def run(kind, scenarios, port, headless=True):
    rig = Rig(kind, port, headless)
    try:
        for fn in scenarios:
            t0 = time.time()
            rig.results.pop("ERR:" + fn.__name__, None)
            try:
                fn(rig)
            except Exception as e:
                tb = traceback.format_exc()
                where = [l.strip() for l in tb.splitlines() if "didarec_auto" in l]
                state = ""
                try:
                    state = json.dumps(rig.ui())[:900]
                except Exception as e2:
                    state = "ui unavailable: " + str(e2)[:100]
                rig.rec("ERR:" + fn.__name__, "ERROR", (str(e)[:200] + " | " + " <- ".join(where[-3:]) + " | ui=" + state + " | console=" + json.dumps(rig.console[-6:]))[:2500])
            finally:
                rig.close()
            print("[%s] -- %s done in %.0fs" % (kind, fn.__name__, time.time() - t0), flush=True)
    finally:
        rig.shutdown()
    return rig
