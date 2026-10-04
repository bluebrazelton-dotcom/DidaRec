"""Checklist section 14 (long recordings, streaming-save memory) + the long-file half of 13.1/13.2.
Usage: python part4.py <cr|ff> [main_minutes] [crash_minutes]"""
import json, os, subprocess, sys, threading, time
from harness import run, summarize

MAIN_MIN = float(sys.argv[2]) if len(sys.argv) > 2 else 30
CRASH_MIN = float(sys.argv[3]) if len(sys.argv) > 3 else 12
RECOVER = "#recoveryBanner button.btn-save"


def tree_mem_mb(fragment):
    """Working-set total (MB) of the browser process tree launched on the given profile dir."""
    ps = ("$all = Get-CimInstance Win32_Process | Select-Object Name, ProcessId, ParentProcessId, WorkingSetSize, CommandLine; "
          "$roots = @($all | Where-Object { $_.CommandLine -like '*" + fragment + "*' -and $_.Name -notlike 'powershell*' -and $_.Name -notlike 'python*' } | ForEach-Object { $_.ProcessId }); "
          "$set = New-Object System.Collections.Generic.HashSet[int]; foreach ($p in $roots) { [void]$set.Add([int]$p) }; "
          "$grew = $true; while ($grew) { $grew = $false; foreach ($p in $all) { if ($set.Contains([int]$p.ParentProcessId) -and -not $set.Contains([int]$p.ProcessId)) { [void]$set.Add([int]$p.ProcessId); $grew = $true } } }; "
          "$sum = 0; foreach ($p in $all) { if ($set.Contains([int]$p.ProcessId)) { $sum += $p.WorkingSetSize } }; [math]::Round($sum / 1MB)")
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=60).stdout.strip()
        return int(out)
    except Exception:
        return None


class Sampler:
    def __init__(self, fragment):
        self.fragment = fragment; self.samples = []; self.on = False

    def start(self):
        self.on = True
        self.th = threading.Thread(target=self._loop, daemon=True); self.th.start()

    def _loop(self):
        while self.on:
            m = tree_mem_mb(self.fragment)
            if m is not None:
                self.samples.append((time.time(), m))
            time.sleep(1.5)

    def stop(self):
        self.on = False; self.th.join(timeout=70)

    def window(self, t0, t1):
        return [m for t, m in self.samples if t0 <= t <= t1]


def long_record(r, minutes):
    r.page.select_option("#qualitySelect", "2500000")
    r.page.click("#toggleMic"); r.page.wait_for_function("!!state.heldMicStream")
    r.cfg(noise=30); r.select_screen(1)
    r.page.click("#btnRecord"); r.page.wait_for_function("state.recording === true")
    end = time.time() + minutes * 60
    errs = set()
    while time.time() < end:
        time.sleep(30)
        u = r.ui()
        if u["err"]:
            errs.add(u["err"])
        if not u["rec"]:
            raise RuntimeError("recording stopped by itself: " + json.dumps(u)[:400])
    return errs


def check_file(r, tag):
    size = os.path.getsize(os.path.join(r.out, tag))
    pr = r.probe(tag, times=None, step=1e9)   # metadata only
    dur = pr["duration"]
    times = [round(dur * f, 1) for f in (0.5, 0.05, 0.95, 0.25, 0.75, 0.1, 0.9, 0.4)] if dur and dur != float("inf") else [1.0]
    pr = r.probe(tag, times=times)
    base = None; ok = True; errs = []
    for s in pr["samples"]:
        if not s["valid"] or not s["seeked"]:
            ok = False; continue
        off = s["ds"] / 10.0 - s["at"]
        base = off if base is None else base
        errs.append(round(off - base, 1))
        if abs(off - base) > 1.5:
            ok = False
    worst = max(s["seekMs"] for s in pr["samples"])
    return size, dur, ok, worst, errs, pr


def s14_long(r):
    prof = "long14_%s" % r.kind
    r.start(prof)
    samp = Sampler(prof); samp.start()
    try:
        # ---- 14.3: long session killed mid-recording, then Recover & save
        errs = long_record(r, CRASH_MIN)
        r.kill_tab(); r.wait(3000)
        info = r.ui()["recoveryInfo"]
        time.sleep(8)
        t0 = time.time(); base = samp.window(t0 - 8, t0)
        r.stop_save("14_3_recovered_long.webm", button=RECOVER, timeout=1200000)
        t1 = time.time(); time.sleep(3)
        during = samp.window(t0, t1 + 3)
        size, dur, ok, worst, serr, pr = check_file(r, "14_3_recovered_long.webm")
        b = sum(base) / max(1, len(base)); peak = max(during or [b]); rise = peak - b
        r.check("14.3", ok and dur > CRASH_MIN * 60 * 0.95 and rise < 0.5 * size / 1048576 and not errs,
                "%.0f-min Best-quality session, tab killed, reopened ('%s'), Recover & save took %.0fs: file %.0f MB / %.1f min, plays and seeks (slowest of 8 jumps %dms). Browser memory (whole process tree): %.0f MB before -> peak %.0f MB during the save (+%.0f MB, i.e. %.0f%% of the file size)"
                % (CRASH_MIN, info, t1 - t0, size / 1048576, dur / 60, worst, b, peak, rise, 100 * rise / (size / 1048576)))
        # ---- 14.1 / 14.2: long session, normal Stop & save
        r.reload(); r.wait(1000)
        errs = long_record(r, MAIN_MIN)
        chunks = r.ui()["chunks"]
        time.sleep(6)
        t0 = time.time(); base = samp.window(t0 - 8, t0)
        seen = []

        def trig():
            r.page.click("#btnStop")

        r.save_via("14_1_long.webm", trig, timeout=1800000)
        t1 = time.time(); time.sleep(3)
        during = samp.window(t0, t1 + 3)
        size, dur, ok, worst, serr, pr = check_file(r, "14_1_long.webm")
        b = sum(base) / max(1, len(base)); peak = max(during or [b]); rise = peak - b
        r.check("14.1", dur > MAIN_MIN * 60 * 0.95 and rise < 0.5 * size / 1048576 and not errs,
                "%.0f-min Best-quality recording (%s), Stop & save took %.0fs: file %.0f MB. Browser memory (whole process tree): %.0f MB while recording -> peak %.0f MB during 'Preparing/Saving' (+%.0f MB = %.0f%% of the file size; a buffered save would add 100%%+). Banners during the run: %s"
                % (MAIN_MIN, chunks, t1 - t0, size / 1048576, b, peak, rise, 100 * rise / (size / 1048576), sorted(errs) or "none"))
        r.check("14.2", ok and worst < 5000 and pr["seekableEnd"] and abs(pr["seekableEnd"] - dur) < 1,
                "long file: player shows the full %.1f min up front; 8 jumps across the whole length (50%%, 5%%, 95%%, 25%% ...) each land on the right frame (content-vs-time drift %s s), slowest %dms" % (dur / 60, serr, worst))
        r.rec("13.1L", "PASS" if (dur and dur != float("inf")) else "FAIL", "longer-file half of 13.1/13.2: %.1f-min file reports its total length and seeks (see 14.2)" % (dur / 60))
        # ---- 14.4 short sanity clip afterwards
        if r.kind == "cr":
            r.wait(500)
        r.cfg(noise=0); r.select_screen(1); r.record(15); r.stop_save("14_4_sanity.webm")
        p = r.probe("14_4_sanity.webm", step=1); sm = summarize(p)
        r.check("14.4", sm["valid"] == sm["n"] and p["duration"] > 14, "15s clip right after the long sessions: %.1fs, %d/%d frames valid" % (p["duration"], sm["valid"], sm["n"]))
        r.rec("14.5", "SKIP", "optional; an hour-plus multi-segment chain was not run")
    finally:
        samp.stop()
        with open(os.path.join(r.out, "14_memory_samples.json"), "w", newline="\n") as f:
            json.dump(samp.samples, f)


if __name__ == "__main__":
    kind = sys.argv[1]
    run(kind, [s14_long], 8799 if kind == "cr" else 8800)
