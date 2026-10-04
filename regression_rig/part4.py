"""Checklist section 14 (long recordings, streaming-save memory) + the long-file half of 13.1/13.2.
Usage: python part4.py <cr|ff> [main_minutes] [crash_minutes]"""
import json, os, subprocess, sys, threading, time
from harness import run, summarize

MAIN_MIN = float(sys.argv[2]) if len(sys.argv) > 2 else 30
# The crash-recovery recording must be long too. A streamed save uses a roughly fixed
# 55-75 MB of working memory whatever the file size; on a 12-minute (~140 MB) file that
# alone sits on the 50% pass line, on a 30-minute (~350 MB) file it is ~16%.
CRASH_MIN = float(sys.argv[3]) if len(sys.argv) > 3 else 30
RECOVER = "#recoveryBanner button.btn-save"


def tree_mem_mb(fragment):
    """(private MB, working-set MB) summed over the browser process tree launched on the given profile dir.

    Private (committed) memory is what the pass/fail uses: a save that buffered the file would
    have to commit the file's size, whatever Windows is doing with resident pages. Working set
    is reported alongside for reference. On 2026-10-04 the two agreed to within a few MB."""
    ps = ("$all = Get-CimInstance Win32_Process | Select-Object Name, ProcessId, ParentProcessId, WorkingSetSize, PrivatePageCount, CommandLine; "
          "$roots = @($all | Where-Object { $_.CommandLine -like '*" + fragment + "*' -and $_.Name -notlike 'powershell*' -and $_.Name -notlike 'python*' } | ForEach-Object { $_.ProcessId }); "
          "$set = New-Object System.Collections.Generic.HashSet[int]; foreach ($p in $roots) { [void]$set.Add([int]$p) }; "
          "$grew = $true; while ($grew) { $grew = $false; foreach ($p in $all) { if ($set.Contains([int]$p.ParentProcessId) -and -not $set.Contains([int]$p.ProcessId)) { [void]$set.Add([int]$p.ProcessId); $grew = $true } } }; "
          "$ws = 0; $pv = 0; foreach ($p in $all) { if ($set.Contains([int]$p.ProcessId)) { $ws += $p.WorkingSetSize; $pv += $p.PrivatePageCount } }; "
          "'' + [math]::Round($pv / 1MB) + ' ' + [math]::Round($ws / 1MB)")
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=60).stdout.strip()
        pv, ws = out.split()
        return int(pv), int(ws)
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
                self.samples.append((time.time(), m[0], m[1]))   # (time, private MB, working-set MB)
            time.sleep(1.5)

    def stop(self):
        self.on = False; self.th.join(timeout=70)

    def window(self, t0, t1, col=1):
        return [s[col] for s in self.samples if t0 <= s[0] <= t1]

    def rise(self, t0, t1, lead=20):
        """Memory during [t0, t1] against the median of the `lead` seconds before t0, for both measures."""
        out = {}
        for name, col in (("private", 1), ("ws", 2)):
            base = sorted(self.window(t0 - lead, t0, col)); during = self.window(t0, t1, col)
            b = base[len(base) // 2] if base else 0
            peak = max(during or [b])
            out[name] = {"before": b, "peak": peak, "rise": peak - b}
        return out


def mem_text(m, size_mb):
    p, w = m["private"], m["ws"]
    return ("committed memory (whole process tree) %d MB before -> peak %d MB (%+d MB = %.0f%% of the file size; a buffered save would add 100%%+). "
            "For reference, resident memory (working set, drifts with the machine): %d -> %d MB (%+d MB)"
            % (p["before"], p["peak"], p["rise"], 100 * p["rise"] / size_mb, w["before"], w["peak"], w["rise"]))


def long_record(r, minutes):
    r.page.select_option("#qualitySelect", "2500000")
    r.page.click("#toggleMic"); r.page.wait_for_function("!!state.heldMicStream")
    r.cfg(noise=30); r.select_screen(1)
    if r.ui()["err"]:
        r.page.click("#errorBanner .error-banner-close")   # the one-time no-audio hint is not an error
    t0 = time.time()
    r.page.click("#btnRecord"); r.page.wait_for_function("state.recording === true", timeout=600000)
    r.start_wait = time.time() - t0
    end = time.time() + minutes * 60
    errs = set()
    while time.time() < end:
        time.sleep(30)
        u = r.ui()
        if u["err"] and "info" not in u["errClass"].split():
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
        if CRASH_MIN <= 0:
            raise_skip = True
        else:
            raise_skip = False
        # ---- 14.3: long session killed mid-recording, then Recover & save
        errs = long_record(r, CRASH_MIN) if not raise_skip else set()
        if raise_skip:
            return main_phase(r, samp)
        r.kill_tab(); r.wait(3000)
        info = r.ui()["recoveryInfo"]
        time.sleep(22)   # let the reopened page settle so the "before" level is a resting one
        info = r.ui()["recoveryInfo"]
        t0 = time.time()
        r.stop_save("14_3_recovered_long.webm", button=RECOVER, timeout=1200000)
        t1 = time.time(); time.sleep(3)
        mem = samp.rise(t0, t1 + 3)
        size, dur, ok, worst, serr, pr = check_file(r, "14_3_recovered_long.webm")
        size_mb = size / 1048576
        r.check("14.3", ok and dur > CRASH_MIN * 60 * 0.95 and mem["private"]["rise"] < 0.5 * size_mb and not errs,
                "%.0f-min Best-quality session, tab killed, reopened ('%s'), Recover & save took %.0fs: file %.0f MB / %.1f min, plays and seeks (slowest of 8 jumps %dms). During the save: %s"
                % (CRASH_MIN, info, t1 - t0, size_mb, dur / 60, worst, mem_text(mem, size_mb)))
        r.reload(); r.wait(1000)
        main_phase(r, samp)
    finally:
        samp.stop()
        with open(os.path.join(r.out, "14_memory_samples_%d.json" % int(time.time())), "w", newline="\n") as f:
            json.dump(samp.samples, f)


def main_phase(r, samp):
    if True:
        # ---- 14.1 / 14.2: long session, normal Stop & save
        errs = long_record(r, MAIN_MIN)
        start_wait = r.start_wait
        chunks = r.ui()["chunks"]
        time.sleep(6)
        t0 = time.time()

        def trig():
            r.page.click("#btnStop")

        r.save_via("14_1_long.webm", trig, timeout=1800000)
        t1 = time.time(); time.sleep(3)
        mem = samp.rise(t0, t1 + 3)
        size, dur, ok, worst, serr, pr = check_file(r, "14_1_long.webm")
        size_mb = size / 1048576
        r.check("14.1", dur > MAIN_MIN * 60 * 0.95 and mem["private"]["rise"] < 0.5 * size_mb and not errs,
                "%.0f-min Best-quality recording (%s), Stop & save took %.0fs: file %.0f MB. During 'Preparing/Saving': %s. Banners during the run: %s"
                % (MAIN_MIN, chunks, t1 - t0, size_mb, mem_text(mem, size_mb), sorted(errs) or "none"))
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
        r.rec("14.1b", "PASS" if start_wait < 5 else "FAIL", "extra: clicking Record for the long session took %.1fs to start recording" % start_wait)


if __name__ == "__main__":
    kind = sys.argv[1]
    run(kind, [s14_long], 8799 if kind == "cr" else 8800)
