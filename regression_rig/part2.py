"""Checklist sections 10-13 and 15 (crash recovery, continue/stitch, cancel-save, seeking, review pane) + 18.4."""
import json, os, re, sys, time
from harness import run, summarize

RECOVER = "#recoveryBanner button.btn-save"
CONTINUE = "#recoveryBanner button.btn-record"


def mic_on(r):
    r.page.click("#toggleMic"); r.page.wait_for_function("!!state.heldMicStream")


def seq_of(pr):
    ids = [s["id"] for s in pr["samples"] if s["valid"]]
    return [ids[0]] + [b for a, b in zip(ids, ids[1:]) if b != a] if ids else []


def span(pr, sid):
    """(first file-time, last file-time, first ds, last ds) of the frames showing fake screen `sid`."""
    xs = [s for s in pr["samples"] if s["valid"] and s["id"] == sid]
    if not xs:
        return None
    return (xs[0]["t"], xs[-1]["t"], xs[0]["ds"], xs[-1]["ds"])


def longest_freeze(pr, step):
    ds = [s["ds"] for s in pr["samples"] if s["valid"]]
    best = run_ = 1
    for a, b in zip(ds, ds[1:]):
        run_ = run_ + 1 if a == b else 1
        best = max(best, run_)
    return round((best - 1) * step, 2)


def seam_blanks(pr):
    """(count of undecodable samples, longest consecutive run). Each take starts with one
    black frame, so a stitched file can show a single blank sample at a seam; the checklist
    accepts a single-frame glitch there but not a multi-second freeze."""
    n = best = run_ = 0
    for s in pr["samples"]:
        if s["valid"]:
            run_ = 0
        else:
            n += 1; run_ += 1; best = max(best, run_)
    return n, best


def audio_gap(au):
    per = au.get("per") or []
    if len(per) < 3:
        return None
    med = sorted(per)[len(per) // 2]
    return [i for i, v in enumerate(per) if v < 0.2 * med]


def quality(r, tag, step=0.25):
    pr = r.probe(tag, step=step); au = r.audio(tag); sm = summarize(pr)
    return pr, au, sm


def review_open(r):
    r.page.click("#btnStopReview")
    r.page.wait_for_function("document.getElementById('reviewPane').classList.contains('visible') && document.getElementById('reviewVideo').readyState >= 1", timeout=60000)
    r.wait(400)


def review_seek(r, t):
    r.ev("""t => new Promise(res => { const v = document.getElementById('reviewVideo'); v.onseeked = () => res(); v.currentTime = t; setTimeout(res, 5000); })""", t)
    r.wait(400)


def cut_done(r):
    r.page.wait_for_function("!document.getElementById('reviewPane').classList.contains('visible')", timeout=30000)
    r.wait(300)


def kept_secs(status):
    m = re.match(r"Kept (\d+):(\d\d)", status or "")
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def kept_ok(status, target):
    """Status shows whole seconds, rounded down; the cut never keeps content past the target."""
    k = kept_secs(status)
    return k is not None and int(target - 1.0) <= k <= target


def try_cut(r, how, t):
    """Attempt a re-record cut at t seconds by scrubbing or typing. Returns dict(landed, status, prompt)."""
    if how == "typed":
        m, s = divmod(int(t), 60)
        r.page.fill("#reviewTimeInput", "%d:%02d" % (m, s)); r.page.click("#btnRerecordAtTime")
    else:
        review_seek(r, t); r.page.click("#btnReRecordHere")
    for _ in range(60):   # a cut can take a moment (it reads the cluster it lands in)
        r.wait(250)
        if r.ev("!document.getElementById('reviewPane').classList.contains('visible') || document.getElementById('reviewDiscardConfirm').classList.contains('visible') || document.getElementById('reviewStatus').textContent !== ''"):
            break
    r.wait(300)
    u = r.ui()
    if not u["review"]:
        return {"landed": True, "status": u["status"], "prompt": None, "prior": u["prior"]}
    conf = r.ev("[document.getElementById('reviewDiscardConfirm').classList.contains('visible'), document.getElementById('reviewDiscardConfirmMsg').textContent]")
    if conf[0]:
        r.page.click("#reviewDiscardConfirm button.btn-record"); r.wait(300)
    return {"landed": False, "status": u["reviewStatus"], "prompt": conf[1] if conf[0] else None, "prior": u["prior"]}


def s10_crash(r):
    r.start("crash10")
    mic_on(r); r.select_screen(1)
    r.record(16)
    r.kill_tab(); r.wait(800)
    u = r.ui()
    r.check("10.1", u["recovery"] and "chunks" in u["recoveryInfo"], "recorded ~16s screen+mic, tab killed with no unload handling, app reopened at the same origin -> recovery banner: '%s'" % u["recoveryInfo"])
    # 12.5 first: cancel during the crash-recovery save, then retry
    if r.kind == "cr":
        r.cfg(saveMode="cancel"); r.page.click(RECOVER); r.wait(1200)
        c = r.ui(); r.cfg(saveMode="ok")
        cancel_ok = c["recovery"] and "stays in the list" in (c["err"] or "")
        cancel_txt = "save dialog cancelled -> banner still up, '%s'" % c["err"]
        r.stop_save("10_recovered.webm", button=RECOVER)
    else:
        r.stop_save("10_recovered_try1.webm", button=RECOVER, resolve="keep")
        c = r.ui()
        cancel_ok = c["recovery"] and "kept safe" in (c["err"] or "")
        cancel_txt = "download declined via 'It didn't arrive' -> banner still up, '%s'" % c["err"]
        r.stop_save("10_recovered.webm", button=RECOVER)
    pr, au, sm = quality(r, "10_recovered.webm", 0.5)
    ok = sm["valid"] == sm["n"] and pr["duration"] > 13 and au["has"]
    r.check("10.2", ok, "Recover & save -> %.1fs file, %d/%d frames valid up to the crash point, audio present" % (pr["duration"], sm["valid"], sm["n"]))
    r.check("12.5", cancel_ok and ok, "during a crash-recovery save: %s; retry saved a playable %.1fs file" % (cancel_txt, pr["duration"]))
    seek_ok = pr["seekableEnd"] and abs(pr["seekableEnd"] - pr["duration"]) < 0.5 and sm["maxSeekMs"] < 3000
    r.reload(); r.wait(600)
    after = r.ui()["recovery"]
    # whole-browser close mid-recording
    mic_on(r); r.select_screen(1); r.record(8)
    r.kill_browser(); r.wait(800)
    u2 = r.ui()
    r.stop_save("10_browser_kill.webm", button=RECOVER)
    pr2 = r.probe("10_browser_kill.webm", step=1)
    r.rec("10.2b", "PASS" if (u2["recovery"] and pr2["duration"] > 6 and not after) else "FAIL",
          "extra: after the confirmed recovery save a reload shows no banner (%s); whole browser closed mid-recording and relaunched on the same profile -> banner=%s, recovered %.1fs" % (not after, u2["recovery"], pr2["duration"]))
    r._seek_crash = (seek_ok, pr["duration"], sm["maxSeekMs"])


def s11_continue(r):
    r.start("cont11")
    mic_on(r); r.select_screen(1); r.record(11)
    r.kill_tab(); r.wait(800)
    r.page.click(CONTINUE); r.wait(400)
    st = r.ui()["status"]
    mic_on(r); r.select_screen(2); r.record(11)
    r.stop_save("11_two_segments.webm")
    pr, au, sm = quality(r, "11_two_segments.webm")
    sq = seq_of(pr); fz = longest_freeze(pr, 0.25); gaps = audio_gap(au)
    r.check("11.1", "1 prior segment" in st and pr["duration"] > 19, "crash -> Continue recording ('%s') -> second take -> Stop & save produced one %.1fs file" % (st, pr["duration"]))
    blank, blank_run = seam_blanks(pr)
    r.check("11.2", sq == [1, 2] and blank <= 1 and blank_run <= 1 and fz <= 0.75 and not gaps and abs(au["duration"] - pr["duration"]) < 1.0,
            "one continuous file: screen sequence %s, %d/%d frames valid at 0.25s steps (%d blank sample(s), never two in a row - the checklist allows a single-frame glitch at the seam), longest repeated frame %.2fs, no silent second in the audio (%.1fs audio vs %.1fs video). Seam judged by measurement, not by eye/ear." % (sq, sm["valid"], sm["n"], blank, fz, au["duration"], pr["duration"]))
    seek_st = pr["seekableEnd"] and abs(pr["seekableEnd"] - pr["duration"]) < 0.5 and sm["maxSeekMs"] < 3000
    # three segments via two crashes
    r.start("cont11b")
    mic_on(r); r.select_screen(1); r.record(8)
    r.kill_tab(); r.wait(600); r.page.click(CONTINUE)
    mic_on(r); r.select_screen(2); r.record(8)
    r.kill_tab(); r.wait(800)
    info = r.ui()["recoveryInfo"]
    r.page.click(CONTINUE); r.wait(300)
    st2 = r.ui()["status"]
    mic_on(r); r.select_screen(3); r.record(8)
    r.stop_save("11_three_segments.webm")
    pr3, au3, sm3 = quality(r, "11_three_segments.webm")
    sq3 = seq_of(pr3); fz3 = longest_freeze(pr3, 0.25)
    r.check("11.3", "across 2 segments" in info and "2 prior segments" in st2, "second crash: banner '%s'; Continue -> '%s'" % (info, st2))
    blank3, blank3_run = seam_blanks(pr3)
    r.check("11.4", sq3 == [1, 2, 3] and blank3 <= 2 and blank3_run <= 1 and fz3 <= 0.75 and not audio_gap(au3) and pr3["duration"] > 21,
            "three segments in order %s in one %.1fs file; %d/%d frames valid (%d blank sample(s), never two in a row), longest repeated frame %.2fs, no silent second" % (sq3, pr3["duration"], sm3["valid"], sm3["n"], blank3, fz3))
    r.reload(); r.wait(500)
    clean = not r.ui()["recovery"]
    # 12.4: cancel-save on a stitched chain keeps every segment
    r.start("cont11c")
    mic_on(r); r.select_screen(1); r.record(7)
    r.kill_tab(); r.wait(600); r.page.click(CONTINUE)
    mic_on(r); r.select_screen(2); r.record(7)
    if r.kind == "cr":
        r.cfg(saveMode="cancel"); r.page.click("#btnStop"); r.wait(2500)
        msg = r.ui()["err"]; r.cfg(saveMode="ok")
    else:
        r.stop_save("12_4_declined.webm", resolve="keep")
        msg = r.ui()["err"]
    r.reload(); r.wait(800)
    info4 = r.ui()["recoveryInfo"]; up = r.ui()["recovery"]
    r.stop_save("12_4_stitched_recovered.webm", button=RECOVER)
    pr4 = r.probe("12_4_stitched_recovered.webm", step=0.5)
    r.check("12.4", up and "across 2 segments" in info4 and seq_of(pr4) == [1, 2] and pr4["duration"] > 12,
            "stitched 2-segment recording, save cancelled/declined ('%s') -> reload banner '%s' -> Recover & save gave a %.1fs file with both segments %s" % (msg, info4, pr4["duration"], seq_of(pr4)))
    sc = getattr(r, "_seek_crash", None)
    r.check("13.3", seek_st and (sc is None or sc[0]),
            "stitched file: seekable to the end, slowest of %d seeks %dms; crash-recovered file: %s" % (sm["n"], sm["maxSeekMs"], ("seekable to %.1fs, slowest seek %dms" % (sc[1], sc[2])) if sc else "see 10.2"))
    r.rec("11.4b", "PASS" if clean else "FAIL", "extra: after the 3-segment save, reload shows no recovery banner=%s" % clean)


def s12_cancel(r):
    r.start("cancel12")
    mic_on(r); r.select_screen(1); r.record(11)
    if r.kind == "cr":
        r.cfg(saveMode="cancel"); r.page.click("#btnStop"); r.wait(2500)
        u = r.ui(); r.cfg(saveMode="ok")
        said = u["err"]
    else:
        r.stop_save("12_declined.webm", resolve="keep")
        u = r.ui(); said = u["err"]
    r.check("12.1", bool(said) and ("still here" in said or "kept safe" in said), "save %s -> '%s'" % ("dialog cancelled" if r.kind == "cr" else "download not confirmed ('It didn't arrive')", said))
    r.reload(); r.wait(800)
    u2 = r.ui()
    r.stop_save("12_recovered.webm", button=RECOVER)
    pr = r.probe("12_recovered.webm", step=0.5); sm = summarize(pr)
    r.reload(); r.wait(600)
    u3 = r.ui()
    r.check("12.2", u2["recovery"] and sm["valid"] == sm["n"] and pr["duration"] > 9 and not u3["recovery"],
            "reload -> recovery banner back ('%s'); Recover & save -> %.1fs playable file; after that confirmed save, reload shows no banner (%s)" % (u2["recoveryInfo"], pr["duration"], not u3["recovery"]))
    if r.kind == "ff":
        r.check("12.3", u2["recovery"] and pr["duration"] > 9 and not u3["recovery"],
                "bar path verified: 'It didn't arrive - keep my recording' -> reload -> banner -> Recover & save playable -> 'It's there - all set' -> no banner. NOT exercised: Firefox's own Save-As dialog being cancelled (needs 'Always ask where to save' and a human click).")
    r.rec("12.6", "SKIP", "optional; only if a stitch failure happens naturally - not triggered in any run here (no confirm()/alert() dialog appeared in any scenario: %d seen)" % len(r.dialogs()))


def s13_seek(r):
    r.start()
    mic_on(r); r.select_screen(1); r.record(15)
    r.stop_save("13_short.webm")
    pr = r.probe("13_short.webm", times=[14.0, 2.0, 9.5, 0.3, 12.2, 5.0, 13.9, 1.0, 7.7])
    ok = True; worst = 0; errs = []
    base = None
    for s in pr["samples"]:
        worst = max(worst, s["seekMs"])
        if not s["valid"] or not s["seeked"]:
            ok = False; continue
        off = s["ds"] / 10.0 - s["at"]
        base = off if base is None else base
        errs.append(round(off - base, 2))
        if abs(off - base) > 0.4:
            ok = False
    r.check("13.1", pr["duration"] is not None and pr["duration"] != float("inf") and pr["duration"] > 14 and pr["seekableEnd"] and abs(pr["seekableEnd"] - pr["duration"]) < 0.5,
            "short clip: player reports total length %.1fs up front (seekable to %.1fs). The longer file is covered by the long-recording run (14.2)." % (pr["duration"], pr["seekableEnd"] or -1))
    r.check("13.2", ok and worst < 2000, "9 jumps forward and backward (14.0, 2.0, 9.5, 0.3 ...): every landing shows the frame that belongs at that time (content-vs-time error %s s), slowest jump %dms" % (errs, worst))


def cut_and_take(r, tag, new_sid, take=5):
    """After a cut landed (armed idle state): record a new take on another fake screen and save."""
    mic_on_if_needed(r)
    r.select_screen(new_sid); r.record(take)
    r.stop_save(tag)
    return quality(r, tag)


def mic_on_if_needed(r):
    if not r.ev("!!state.heldMicStream"):
        if r.ev("state.sources.mic"):
            r.page.wait_for_function("!!state.heldMicStream")
        else:
            mic_on(r)


def s15_review_a(r):
    r.start("rev15a")
    mic_on(r); r.select_screen(1)
    r.record(30)
    saves0 = r.save_count()
    r.ev("""() => { window.__lbl = []; const a = document.getElementById('btnStopReview'), b = document.getElementById('btnStop');
      const mo = new MutationObserver(() => window.__lbl.push([a.textContent, b.textContent])); mo.observe(a, {childList:true, characterData:true, subtree:true}); mo.observe(b, {childList:true, characterData:true, subtree:true}); }""")
    review_open(r)
    u = r.ui(); lbl = r.ev("window.__lbl")
    vd = r.ev("document.getElementById('reviewVideo').duration")
    review_seek(r, 12.0)
    at = r.ev("document.getElementById('reviewVideo').currentTime")
    played = r.ev("""() => new Promise(res => { const v = document.getElementById('reviewVideo'); v.muted = true; const t0 = v.currentTime; v.play().then(() => setTimeout(() => { v.pause(); res(v.currentTime - t0); }, 1200)).catch(e => res(-1)); })""")
    redo_vis = r.ev("getComputedStyle(document.getElementById('btnRedoLastTake')).display !== 'none'")
    ok151 = u["review"] and not u["controls"] and r.save_count() == saves0 and abs(vd - 30) < 4 and abs(at - 12.0) < 0.3 and played > 0.5
    during = [x for x in lbl if x[0] == "Preparing review..."]
    r.check("15.2", bool(during) and all(x[1] == "Stop & save" for x in during) and r.ev("document.getElementById('btnStopReview').textContent") == "Stop & review" and r.ev("document.getElementById('btnStop').textContent") == "Stop & save",
            "label changes observed: %s; afterwards both read 'Stop & review' / 'Stop & save'" % lbl)
    # 15.7 no-op at the very end
    review_seek(r, vd)
    r.page.click("#btnReRecordHere"); r.wait(400)
    u7 = r.ui()
    r.check("15.7", "already the end" in u7["reviewStatus"] and u7["review"], "playhead at the end -> '%s'; still in the pane" % u7["reviewStatus"])
    # 15.4 invalid typed time
    r.page.fill("#reviewTimeInput", "banana"); r.page.click("#btnRerecordAtTime"); r.wait(300)
    ub = r.ui()
    bad_ok = "doesn't look like a time" in ub["reviewStatus"] and ub["review"] and ub["prior"] == 0
    # 15.8 (keep reviewing branch) via typed 0:00
    r.page.fill("#reviewTimeInput", "0:00"); r.page.click("#btnRerecordAtTime"); r.wait(300)
    conf = r.ev("[document.getElementById('reviewDiscardConfirm').classList.contains('visible'), document.getElementById('reviewDiscardConfirmMsg').textContent]")
    r.page.click("#reviewDiscardConfirm button.btn-record"); r.wait(300)
    kept = r.ui(); conf2 = r.ev("document.getElementById('reviewDiscardConfirm').classList.contains('visible')")
    zero_ok = conf[0] and "very beginning" in conf[1] and kept["review"] and not conf2
    # 15.10 cancel stays in the pane (Chrome dialog)
    if r.kind == "cr":
        r.cfg(saveMode="cancel"); r.page.click("#reviewPane .btn-save-as-is"); r.wait(800)
        uc = r.ui(); r.cfg(saveMode="ok")
        r.check("15.10", uc["review"] and "Save cancelled" in uc["reviewStatus"], "Save as is, dialog cancelled -> still in the pane, '%s' (a successful Save as is follows in 15.9)" % uc["reviewStatus"])
    # 15.3 scrubbed cut at 12.4s
    review_seek(r, 12.4)
    btn = r.ev("document.getElementById('btnReRecordHere').textContent")
    r.page.click("#btnReRecordHere"); cut_done(r)
    uc = r.ui()
    # 18.4 layout in the armed state
    lay = r.ev("""() => { const vis = e => getComputedStyle(e).display !== 'none'; const bs = [...document.querySelectorAll('.action-btns button')].filter(vis);
      const tops = [...new Set(bs.map(b => Math.round(b.getBoundingClientRect().top)))]; const ab = document.querySelector('.action-btns').getBoundingClientRect(); const u = document.getElementById('btnUndoReRecord').getBoundingClientRect();
      return { tops, undoTop: Math.round(u.top), rowBottom: Math.round(Math.max(...bs.map(b => b.getBoundingClientRect().bottom))), n: bs.length, vw: innerWidth }; }""")
    r.check("18.4", uc["btnUndo"] and len(lay["tops"]) == 1 and lay["undoTop"] >= lay["rowBottom"], "armed state at %dpx wide: %d recorder buttons share one line (tops %s); Undo re-record starts at y=%d, below that row (bottom %d). Layout measured, not eyeballed." % (lay["vw"], lay["n"], lay["tops"], lay["undoTop"], lay["rowBottom"]))
    pr, au, sm = cut_and_take(r, "15_3_scrub_cut.webm", 2)
    s1 = span(pr, 1); s2 = span(pr, 2)
    kept_s = (s1[3] - s1[2]) / 10.0 + 0.25 if s1 else -1
    fz = longest_freeze(pr, 0.25)
    ok153 = btn == "Re-record from 0:12" and uc["status"].startswith("Kept 0:12") and seq_of(pr) == [1, 2] and abs(s2[0] - 12.4) <= 1.0 and fz <= 0.75 and not audio_gap(au)
    r.check("15.3", ok153, "scrubbed to 12.4s: button '%s', status '%s'. Saved file: original content runs to %.2fs then the new take starts (target 12.4s, within 1s); one stitched file %s, %.1fs, longest repeated frame %.2fs, no silent second" % (btn, uc["status"][:12], s2[0] if s2 else -1, seq_of(pr), pr["duration"], fz))
    r.check("15.1", ok151, "Stop & review after ~30s: recorder controls hidden=%s, review pane shown=%s, no save dialog/download (%d new), preview duration %.1fs, seek to 12.0s landed at %.2fs, played %.1fs in 1.2s. From a paused recording: see 15.1b." % (not u["controls"], u["review"], r.save_count() - saves0 if r.kind == "ff" else 0, vd, at, played))
    r._rev = {"bad_ok": bad_ok, "bad_txt": ub["reviewStatus"], "zero_ok": zero_ok, "zero_txt": conf[1], "redo_single": redo_vis}


def s15_review_b(r):
    # typed cut, undo, redo last take, back to recorder
    r.start("rev15b")
    mic_on(r); r.select_screen(1); r.record(20)
    review_open(r)
    rv = getattr(r, "_rev", {})
    first = try_cut(r, "typed", 7)
    early_note = ""
    target = 7.0
    if not first["landed"]:
        early_note = " BUT typed 0:07 on this 20s recording did NOT cut: the app answered with the start-over prompt ('%s') - a time inside the recording's first cluster cannot be cut to. Retried at 0:12:" % (first["prompt"] or first["status"])
        target = 12.0
        first2 = try_cut(r, "typed", 12)
        st = first2["status"]
    else:
        st = first["status"]
    pr, au, sm = cut_and_take(r, "15_4_typed_cut.webm", 2)
    s2 = span(pr, 2)
    r.check("15.4", first["landed"] and kept_ok(st, target) and seq_of(pr) == [1, 2] and abs(s2[0] - target) <= 1.0 and rv.get("bad_ok", False) and rv.get("zero_ok", False),
            "%s typed %d:%02d -> '%s'; in the saved file the new take starts at %.2fs (target %.1fs). 'banana' -> '%s' and nothing changed. 0:00 -> start-over confirmation shown=%s"
            % (early_note, int(target) // 60, int(target) % 60, st[:12], s2[0], target, rv.get("bad_txt"), rv.get("zero_ok")))
    # 15.6 undo after a cut restores the full chain
    r.select_screen(1); r.record(20)
    review_open(r)
    review_seek(r, 12.0); r.page.click("#btnReRecordHere"); cut_done(r)
    a = r.ui()
    r.page.click("#btnUndoReRecord"); r.wait(700)
    b = r.ui()
    pr, au, sm = cut_and_take(r, "15_6_undo.webm", 2)
    s1 = span(pr, 1); s2 = span(pr, 2)
    r.check("15.6", a["btnUndo"] and not b["btnUndo"] and "1 prior segment" in b["status"] and seq_of(pr) == [1, 2] and s2[0] > 18.5,
            "cut at 0:12 ('%s') then Undo re-record -> '%s'; saved file has the FULL original (%.1fs of it) followed by the new take - no cut applied" % (a["status"][:10], b["status"], s2[0]))
    # 15.12 back to recorder, then 15.5 redo last take on a 2-segment recording
    r.select_screen(1); r.record(10)
    review_open(r)
    r.page.click("#reviewPane .btn-back-recorder"); r.wait(500)
    back = r.ui()
    r.select_screen(2); r.record(8)
    review_open(r)
    redo_vis = r.ev("getComputedStyle(document.getElementById('btnRedoLastTake')).display !== 'none' && !document.getElementById('btnRedoLastTake').disabled")
    pvd = r.ev("document.getElementById('reviewVideo').duration")
    r.page.click("#btnRedoLastTake"); cut_done(r)
    c = r.ui()
    pr, au, sm = cut_and_take(r, "15_5_redo.webm", 3)
    sq = seq_of(pr); s3 = span(pr, 3); fz = longest_freeze(pr, 0.25)
    r.check("15.12", "prior segment(s) preserved" in back["status"] and not back["review"] and sq[0] == 1, "Back to recorder -> '%s'; the later save includes the previously reviewed content (file starts with it)" % back["status"])
    r.check("15.5", redo_vis and rv.get("redo_single") is False and c["prior"] == 1 and sq == [1, 3] and fz <= 0.75 and abs(pvd - 18) < 4,
            "2 segments: Redo last take offered=%s (hidden with 1 segment=%s); click -> '%s', newest take dropped whole; saved file = first take then the redo %s (take 2 absent), new take starts at %.2fs, longest repeated frame %.2fs" % (redo_vis, rv.get("redo_single") is False, c["status"][:12], sq, s3[0], fz))


def s15_review_c(r):
    # multi-segment cut inside an earlier segment; re-cut of a cut
    r.start("rev15c")
    mic_on(r); r.select_screen(1); r.record(10)
    r.kill_tab(); r.wait(600); r.page.click(CONTINUE)
    mic_on(r); r.select_screen(2); r.record(10)
    review_open(r)
    vd = r.ev("document.getElementById('reviewVideo').duration")
    review_seek(r, 9.0); p1 = r.ev("document.getElementById('reviewVideo').currentTime")
    review_seek(r, 13.0); p2 = r.ev("document.getElementById('reviewVideo').currentTime")
    c = try_cut(r, "scrub", 5.0)
    note = ""; target = 5.0
    if not c["landed"]:
        note = " A cut at 0:05 was refused with the start-over prompt (inside the first cluster); used 0:09 instead."
        target = 9.0
        c = try_cut(r, "scrub", 9.0)
    pr, au, sm = cut_and_take(r, "15_14_multiseg_cut.webm", 3)
    sq = seq_of(pr); s3 = span(pr, 3)
    r.check("15.14", abs(vd - 20) < 4 and abs(p1 - 9) < 0.3 and abs(p2 - 13) < 0.3 and c["prior"] == 1 and sq == [1, 3] and abs(s3[0] - target) <= 1.0,
            "crash+continue chain reviewed: preview %.1fs seeks on both sides of the seam; cut at %.0fs inside the EARLIER segment -> later segment dropped (prior segments=%d); saved file = %s with the kept part ending at %.2fs.%s" % (vd, target, c["prior"], sq, s3[0], note))
    # extra: a cut a few seconds INTO THE SECOND segment of a chain
    r.start("rev15c2")
    mic_on(r); r.select_screen(1); r.record(10)
    r.kill_tab(); r.wait(600); r.page.click(CONTINUE)
    mic_on(r); r.select_screen(2); r.record(12)
    review_open(r)
    seam = r.ev("(() => { const s = reviewState.scans; return (Math.max(s[0].lastClusterMaxBlockTime, s[0].maxClusterTs)) / 1000; })()")
    tgt = round(seam + 3.5, 1)
    c2 = try_cut(r, "scrub", tgt)
    pr, au, sm = cut_and_take(r, "15_14b_cut_in_second_segment.webm", 3)
    s3 = span(pr, 3); sq = seq_of(pr)
    off = s3[0] - tgt
    r.rec("15.14b", "PASS" if (c2["landed"] and abs(off) <= 1.0 and sq == [1, 2, 3]) else "FAIL",
          "extra (same precision rule as 15.3): 2-segment chain, seam at %.1fs, cut requested at %.1fs (3.5s into the second take) -> status '%s'; saved file sequence %s, new take starts at %.2fs (%.1fs from the requested point)" % (seam, tgt, (c2["status"] or "")[:12], sq, s3[0], off))
    # 15.15 re-cut of a cut
    r.start("rev15d")
    mic_on(r); r.select_screen(1); r.record(30)
    review_open(r); review_seek(r, 20.0); r.page.click("#btnReRecordHere"); cut_done(r)
    a = r.ui()["status"]
    mic_on_if_needed(r); r.select_screen(2); r.record(6)
    review_open(r); review_seek(r, 10.0); r.page.click("#btnReRecordHere"); cut_done(r)
    b = r.ui()["status"]
    pr, au, sm = cut_and_take(r, "15_15_recut.webm", 3)
    sq = seq_of(pr); s3 = span(pr, 3)
    r.check("15.15", kept_ok(a, 20) and kept_ok(b, 10) and sq == [1, 3] and abs(s3[0] - 10.0) <= 1.0 and abs(pr["duration"] - 15) < 3,
            "cut at 0:20 ('%s'), new take, review again, cut EARLIER at 0:10 ('%s'): saved file = %s, original ends at %.2fs, total %.1fs" % (a[:10], b[:10], sq, s3[0], pr["duration"]))


def s15_review_d(r):
    # save as is, discard, start over confirm, crash mid-review, review from paused
    r.start("rev15e")
    mic_on(r); r.select_screen(1); r.record(8)
    r.page.click("#btnPause"); r.wait(1500)
    review_open(r)
    up = r.ui()
    r.rec("15.1b", "PASS" if up["review"] and not up["controls"] else "FAIL", "Stop & review clicked while PAUSED -> review pane shown=%s, preview duration %.1fs" % (up["review"], r.ev("document.getElementById('reviewVideo').duration")))
    r.stop_save("15_9_save_as_is.webm", button="#reviewPane .btn-save-as-is")
    u = r.ui()
    pr = r.probe("15_9_save_as_is.webm", step=0.5); sm = summarize(pr)
    r.reload(); r.wait(600)
    r.check("15.9", sm["valid"] == sm["n"] and pr["duration"] > 6 and not u["review"] and not r.ui()["recovery"], "Save as is (single segment) -> normal save flow, %.1fs playable file; back at the recorder; reload shows no recovery banner" % pr["duration"])
    if r.kind == "ff":
        mic_on(r); r.select_screen(1); r.record(6); review_open(r)
        r.stop_save("15_10_ff_declined.webm", button="#reviewPane .btn-save-as-is", resolve="keep")
        r.reload(); r.wait(700)
        back = r.ui()["recovery"]
        r.check("15.10", back, "Firefox has no save dialog to cancel; equivalent path: Save as is downloads, 'It didn't arrive - keep my recording' -> recording still recoverable after reload=%s (pane closes on download by design)" % back)
        r.page.click("#recoveryBanner button.btn-stop"); r.wait(600)
    # 15.11 discard with in-pane confirmation
    mic_on(r); r.select_screen(1); r.record(6); review_open(r)
    d0 = len(r.dialogs())
    r.page.click("#reviewPane .caption-editor-toolbar button.btn-stop"); r.wait(300)
    conf = r.ev("[document.getElementById('reviewDiscardConfirm').classList.contains('visible'), document.getElementById('reviewPane').contains(document.getElementById('reviewDiscardConfirm'))]")
    r.page.click("#reviewDiscardConfirm button.btn-stop"); r.wait(800)
    u = r.ui()
    r.reload(); r.wait(600)
    r.check("15.11", conf == [True, True] and len(r.dialogs()) == d0 and not u["review"] and u["status"] == "Ready" and not r.ui()["recovery"],
            "Discard recording -> confirmation rendered inside the pane (browser popups: %d); confirm -> pane closed, status '%s'; reload: no recovery banner" % (len(r.dialogs()) - d0, u["status"]))
    # 15.8 start over (confirm branch), via scrub to 0
    mic_on(r); r.select_screen(1); r.record(6); review_open(r)
    review_seek(r, 0)
    r.page.click("#btnReRecordHere"); r.wait(300)
    conf = r.ev("[document.getElementById('reviewDiscardConfirm').classList.contains('visible'), document.getElementById('reviewDiscardConfirmMsg').textContent]")
    r.page.click("#reviewDiscardConfirm button.btn-stop"); r.wait(800)
    u = r.ui()
    r.reload(); r.wait(600)
    rv = getattr(r, "_rev", {})
    r.check("15.8", conf[0] and "very beginning" in conf[1] and not u["review"] and u["status"] == "Ready" and u["prior"] == 0 and not r.ui()["recovery"] and rv.get("zero_ok", True),
            "Re-record from 0:00 -> banner '%s'; 'Keep reviewing' left everything as it was (%s); confirming -> clean idle ('%s'), no recovery banner after reload" % (conf[1][:70], rv.get("zero_ok"), u["status"]))
    # 15.13 crash mid-review
    mic_on(r); r.select_screen(1); r.record(8); review_open(r)
    r.kill_tab(); r.wait(800)
    u = r.ui()
    r.stop_save("15_13_recovered.webm", button=RECOVER)
    pr = r.probe("15_13_recovered.webm", step=1)
    r.check("15.13", u["recovery"] and pr["duration"] > 6, "tab killed with the review pane open -> recovery banner on reopen ('%s'), recovered file %.1fs" % (u["recoveryInfo"], pr["duration"]))


def s15_precision_end(r):
    r.start("rev15f")
    mic_on(r); r.select_screen(1); r.record(70)
    review_open(r)
    review_seek(r, 63.3)
    btn = r.ev("document.getElementById('btnReRecordHere').textContent")
    r.page.click("#btnReRecordHere"); cut_done(r)
    st = r.ui()["status"]
    pr, au, sm = cut_and_take(r, "15_16_late_cut.webm", 2)
    s2 = span(pr, 2)
    r.check("15.16", kept_ok(st, 63.3) and abs(s2[0] - 63.3) <= 1.0 and seq_of(pr) == [1, 2],
            "~70s recording, scrubbed to 63.3s ('%s'): status '%s'; in the saved file the new take starts at %.2fs (within 1s of the target)" % (btn, st[:10], s2[0]))


def s15_cut_micoff(r):
    """Same precision rule as 15.3/15.16, but on a recording with no audio at all."""
    r.start("rev15g")
    r.select_screen(1); r.record(14)
    review_open(r)
    c = try_cut(r, "scrub", 8.0)
    if c["landed"]:
        r.select_screen(2); r.record(4); r.stop_save("15_3b_micoff_cut.webm")
        pr = r.probe("15_3b_micoff_cut.webm", step=0.25)
        s1 = span(pr, 1); s2 = span(pr, 2)
        kept = (s1[3] - s1[2]) / 10.0 + 0.3 if s1 else 0
        r.rec("15.3b", "PASS" if abs(kept - 8.0) <= 1.0 else "FAIL",
              "extra: mic OFF (no audio), 14s recording, cut requested at 0:08 -> status '%s'; the saved file keeps about %.1fs of the original before the new take (%.1fs from the requested point; the checklist's rule is 'within a second')" % (c["status"][:12], kept, kept - 8.0))
    else:
        r.rec("15.3b", "FAIL", "extra: mic OFF (no audio), 14s recording, cut requested at 0:08 -> no cut; app answered '%s'" % (c["prompt"] or c["status"]))


ALL = [s15_cut_micoff, s10_crash, s11_continue, s12_cancel, s13_seek, s15_review_a, s15_review_b, s15_review_c, s15_review_d, s15_precision_end]

if __name__ == "__main__":
    kind = sys.argv[1]
    names = sys.argv[2:]
    sc = [f for f in ALL if not names or f.__name__ in names]
    run(kind, sc, 8793 if kind == "cr" else 8794)
