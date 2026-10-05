"""Checklist sections 1-9, 17, 18 (everything that doesn't need crash/review/captions)."""
import json, os, re, sys, time
from harness import run, summarize

GUARD = "At least one of Screen or Webcam"
BG = {1: (32, 48, 80), 2: (32, 80, 48), 3: (80, 48, 32)}
RED, GREEN = (200, 0, 0), (0, 160, 0)


def near(p, q, tol=70):
    return p is not None and all(abs(a - b) <= tol for a, b in zip(p, q))


def secs(t):
    h, m, s = t.split(":")
    return int(h) * 3600 + int(m) * 60 + int(s)


def opts(r, sel):
    return r.ev("s => [...document.querySelectorAll(s + ' option')].map(o => [o.value ? 1 : 0, o.textContent])", sel)


def calls(r):
    return r.ev("[__dr.log.gum.length, __dr.log.gdm.length]")


def s1_load(r):
    r.start(); r.wait(1500)
    c = calls(r); u = r.ui()
    r.check("1.1", c == [0, 0] and not u["err"], "fresh profile, 1.5s after load: getUserMedia calls=%d, getDisplayMedia calls=%d, no banner (no media request means nothing can prompt)" % (c[0], c[1]))
    r.reload(); r.wait(1000)
    c = calls(r)
    r.check("1.2", c == [0, 0], "after reload: getUserMedia=%d getDisplayMedia=%d" % (c[0], c[1]))
    u = r.ui()
    r.check("1.3", u["sources"] == {"screen": True, "camera": False, "mic": False} and not u["camActive"] and not u["micActive"] and not u["hasScreen"] and u["btnRecord"]["dis"],
            "sources=%s; Webcam lit=%s, Mic lit=%s; Screen intent on but button dark until a screen is selected (lit=%s, per v1.21.3); Record disabled=%s"
            % (json.dumps(u["sources"]), u["camActive"], u["micActive"], u["screenActive"], u["btnRecord"]["dis"]))
    # 1.4: at load a dark Screen click opens the picker (v1.22.2); the guard is reachable from the lit state.
    r.cfg(screenMode="ok", screenId=1)
    r.page.click("#toggleScreen"); r.wait(1200)
    c = calls(r); u = r.ui()
    opened = c[1] == 1 and u["hasScreen"] and GUARD not in (u["err"] or "")
    r.page.click("#toggleScreen"); r.wait(400)
    u2 = r.ui()
    r.check("1.4", opened and u2["sources"]["screen"] and (u2["err"] or "").startswith(GUARD),
            "As written this is superseded by v1.22.2: untouched-state click opened the picker (getDisplayMedia calls=%d, no guard text). From the lit state, clicking Screen off -> reverted ON with banner: '%s'" % (c[1], u2["err"]))


def s1_camera(r):
    r.start()
    before = opts(r, "#cameraSelect")
    r.page.click("#toggleCamera")
    r.page.wait_for_function("!!state.cameraStream")
    r.wait(800)
    g = r.ev("__dr.log.gum.map(x => x.c)")
    after = opts(r, "#cameraSelect"); u = r.ui()
    r.check("1.5", len(g) == 1 and '"video"' in g[0] and u["hasCam"] and any(v for v, _ in after),
            "one getUserMedia call (%s); live camera stream held; dropdown before=%s after=%s" % (g[0][:80], [t for _, t in before], [t for _, t in after]))
    r.page.click("#toggleScreen"); r.wait(1200)
    u = r.ui(); pv = r.ev("__dr.readPreview([[0.5,0.5],[0.1,0.1],[0.9,0.9]])")
    lit = [sum(p) for p in pv["pts"]]
    r.check("1.6", (not u["sources"]["screen"]) and (not u["placeholder"]) and max(lit) > 60 and not u["btnRecord"]["dis"],
            "camera-only: sources=%s, placeholder hidden=%s, canvas %dx%d pixel sums at centre/corners=%s (non-black), Record enabled=%s" % (json.dumps(u["sources"]), not u["placeholder"], pv["w"], pv["h"], lit, not u["btnRecord"]["dis"]))
    r.page.click("#toggleCamera"); r.wait(600)
    u = r.ui()
    r.check("1.7", u["sources"]["screen"] and u["placeholder"] and (u["err"] or "").startswith(GUARD),
            "Webcam off from camera-only -> Screen back on=%s, placeholder shown=%s, banner='%s'" % (u["sources"]["screen"], u["placeholder"], u["err"]))


def s1_camonly_record(r):
    r.start()
    r.page.click("#toggleCamera"); r.page.wait_for_function("!!state.cameraStream")
    r.page.click("#toggleScreen"); r.wait(800)
    u = r.ui()
    direct = (not u["btnRecord"]["dis"]) and (not u["btnSelect"]["vis"])
    r.record(5)
    r.page.click("#btnPause"); r.wait(500)
    u2 = r.ui()
    r.check("5.2", u2["paused"] and not u2["btnChange"], "camera-only recording paused: Change screen visible=%s" % u2["btnChange"])
    r.page.click("#btnPause"); r.wait(1500)
    r.stop_save("1_8_camonly.webm")
    pr = r.probe("1_8_camonly.webm", step=1, points=[[0.03, 0.03], [0.97, 0.03], [0.03, 0.97], [0.97, 0.97], [0.5, 0.5]])
    mins = [min(sum(p) for p in s["pts"]) for s in pr["samples"]]
    r.check("1.8", direct and pr["w"] == 1280 and pr["h"] == 720 and pr["duration"] and pr["duration"] > 4 and min(mins) > 40,
            "Record enabled with no Select Screen step=%s; file %dx%d, %.1fs, seekable; darkest of 4 corners+centre across %d frames=%d (camera fills the canvas, no small-rectangle artifact)" % (direct, pr["w"], pr["h"], pr["duration"], len(mins), min(mins)))


def s2_devices(r):
    r.start()
    mic0 = opts(r, "#micSelect"); cam0 = opts(r, "#cameraSelect")
    r.page.click("#toggleMic")
    r.page.wait_for_function("!!state.heldMicStream")
    r.wait(800)
    g = r.ev("__dr.log.gum.map(x => x.c)")
    mic1 = opts(r, "#micSelect")
    r.check("2.1", [t for _, t in mic0] == ["Default microphone"] and len(g) == 1 and '"audio"' in g[0] and sum(v for v, _ in mic1) >= 1,
            "pre-grant options=%s; toggle ON -> %d getUserMedia call; options after=%s" % ([t for _, t in mic0], len(g), [t for _, t in mic1]))
    live = r.ev("state.heldMicStream.getAudioTracks().map(t => [t.readyState, t.label])")
    r.check("2.2", live and live[0][0] == "live" and not r.ui()["rec"],
            "before any recording the held mic track is %s ('%s'); with real names available the dropdown lists them (the 'Microphone: name' Default slot only applies when names can't be listed). OS mic-in-use indicator itself not observable by automation." % (live[0][0], live[0][1]))
    r.check("6.4", "noiseSuppression\":true" in g[0], "optional/ear-only item: constraint check only - mic requested with %s" % g[0][:120])
    r.select_screen(1)
    n0 = calls(r)[0]
    t0 = time.time()
    r.page.click("#btnRecord"); r.page.wait_for_function("state.recording === true")
    dt = time.time() - t0
    same = r.ev("state.micStream === state.heldMicStream")
    n1 = calls(r)[0]
    r.page.wait_for_function("state.chunkIndex > 0", timeout=30000); r.wait(4000)
    r.stop_save("2_3_mic.webm")
    au = r.audio("2_3_mic.webm")
    r.check("2.3", n1 == n0 and same and au["has"] and au["per"] and au["per"][0] > 0.005,
            "Record clicked -> recording in %.2fs with %d new getUserMedia calls; recording uses the held stream=%s; audio RMS in first second=%.4f (non-silent from the start)" % (dt, n1 - n0, same, au["per"][0] if au.get("per") else -1))
    real = [i for i, (v, _) in enumerate(mic1) if v]
    if len(real) >= 2:
        val = r.ev("i => document.querySelectorAll('#micSelect option')[i].value", real[-1])
        r.page.select_option("#micSelect", val); r.wait(1200)
        g2 = r.ev("__dr.log.gum.map(x => x.c)")
        held = r.ev("[state.heldMicDeviceId, state.heldMicStream && state.heldMicStream.getAudioTracks()[0].label, state.heldMicStream && state.heldMicStream.getAudioTracks()[0].readyState]")
        r.select_screen(1); r.record(3)
        used = r.ev("[state.micStream === state.heldMicStream, state.micStream.getAudioTracks()[0].label]")
        r.stop_save("2_4_mic2.webm")
        r.check("2.4", held[0] == val and val[:8] in g2[-1] and used[0],
                "picked '%s' -> re-acquired (getUserMedia with exact deviceId), held track now '%s' (%s); next recording used it: %s" % (mic1[real[-1]][1], held[1], held[2], used[1]))
    else:
        r.rec("2.4", "SKIP", "this engine's fake-device set exposes only %d selectable mic(s); needs 2 real mics - left for the owner" % len(real))
    # 2.10 proxy
    n0 = calls(r)[0]
    r.ev("navigator.mediaDevices.dispatchEvent(new Event('devicechange'))"); r.wait(800)
    n1 = calls(r)[0]; mic2 = opts(r, "#micSelect")
    r.check("2.10", n1 == n0 and len(mic2) >= len(mic1), "optional item, proxy only: synthetic devicechange event -> dropdown re-enumerated (%d options), %d new permission requests. Real plug/unplug not exercised." % (len(mic2), n1 - n0))
    # 2.6 camera
    r.page.click("#toggleCamera"); r.page.wait_for_function("!!state.cameraStream"); r.wait(800)
    cam1 = opts(r, "#cameraSelect")
    r.check("2.6", [t for _, t in cam0] == ["Default camera"] and sum(v for v, _ in cam1) >= 1,
            "pre-grant=%s; after Webcam toggle=%s" % ([t for _, t in cam0], [t for _, t in cam1]))


def s2_deny(r):
    r.start()
    r.cfg(gumMode="deny")
    r.page.click("#toggleMic"); r.wait(800)
    u = r.ui()
    r.check("2.5", (not u["micActive"]) and (not u["sources"]["mic"]) and "declined" in (u["err"] or ""),
            "denied at toggle-ON -> Mic toggle back OFF=%s, banner='%s'" % (not u["micActive"], u["err"]))
    # 2.9: stale 'anonymized' verdict must not stick once names are available
    r.cfg(gumMode="ok")
    r.ev("() => { localStorage.setItem('micEnumAnonymized','1'); localStorage.setItem('camEnumAnonymized','1'); }")
    r.reload()
    m0 = opts(r, "#micSelect")
    r.page.click("#toggleMic"); r.page.wait_for_function("!!state.heldMicStream"); r.wait(800)
    m1 = opts(r, "#micSelect"); flag = r.ev("localStorage.getItem('micEnumAnonymized')")
    r.check("2.9", sum(v for v, _ in m1) >= 1 and flag is None and not any("Chosen in the browser" in t for _, t in m1),
            "with the anonymized verdict pre-set, load showed %s; after Mic ON over http://localhost real names populated %s and the verdict flag cleared (=%s)" % ([t for _, t in m0], [t for _, t in m1], flag))


def s3_basic(r):
    r.start()
    r.page.click("#toggleMic"); r.page.wait_for_function("!!state.heldMicStream")
    r.select_screen(1)
    r.record(10)
    samples = []
    r.cfg(saveDelay=2500)

    def trig():
        r.page.click("#btnCaptionEditor"); r.wait(300)
        samples.append(r.ui())
        r.page.click("#btnStop")
        samples.append(r.ui()); r.wait(1500); samples.append(r.ui())

    path = r.save_via("3_1_basic.webm", trig, resolve=None)
    name1 = r.last_name
    stale, a, b = samples
    if r.kind == "cr":
        sv = r.ev("__dr.log.save")
        r.check("3.1", len(sv) == 1 and os.path.getsize(path) > 10000, "Chrome flow: File System Access save dialog requested once (suggested '%s'); %d bytes written" % (sv[0]["name"], os.path.getsize(path)))
    else:
        r.page.wait_for_selector("#downloadConfirm.visible", timeout=15000)
        r.check("3.1", os.path.getsize(path) > 10000 and r.ui()["dlConfirm"], "Firefox flow: file downloaded automatically ('%s', %d bytes) and the 'Downloaded - did it arrive?' bar appeared" % (name1, os.path.getsize(path)))
    r.check("3.5", a["timer"] == b["timer"], "timer at Stop click=%s, 1.5s later=%s (frozen)" % (a["timer"], b["timer"]))
    r.check("3.6", "caption editor" in (stale["err"] or "") and a["err"] == "" and os.path.getsize(path) > 10000,
            "stale banner before stop='%s'; immediately after Stop click banner='%s'; save completed" % (stale["err"], a["err"]))
    r.check("16.13", "Finish or stop the current recording" in (stale["err"] or "") and stale["rec"] and not stale["captions"] and stale["controls"] and a["err"] == "",
            "Caption editor clicked mid-recording -> refused ('%s'), editor not opened, still recording=%s; Stop & save then cleared the banner at once and saved" % (stale["err"], stale["rec"]))
    pr = r.probe("3_1_basic.webm", step=0.5); au = r.audio("3_1_basic.webm"); sm = summarize(pr)
    okplay = sm["valid"] == sm["n"] and sm["n"] > 10 and au["has"] and abs(au["duration"] - pr["duration"]) < 0.6
    if r.kind == "cr":
        r.check("3.2", okplay, "file plays: %.1fs video, all %d sampled frames decode in order; audio present %.1fs (durations agree within %.2fs). Lip-sync by ear not judged." % (pr["duration"], sm["n"], au["duration"], abs(au["duration"] - pr["duration"])))
    else:
        t0 = time.time()
        r.page.click("#downloadConfirm button.btn-save")
        r.page.wait_for_function("document.getElementById('statusText').textContent.trim() === 'All set'")
        dt = time.time() - t0
        u = r.ui()
        r.reload(); r.wait(800)
        u2 = r.ui()
        r.check("3.3", dt < 1.5 and not u["dlConfirm"] and not u2["recovery"] and okplay, "'All set' shown %.2fs after the click, bar cleared; after reload recovery banner visible=%s; file plays (%.1fs, audio present)" % (dt, u2["recovery"], pr["duration"]))
        r.page.click("#toggleMic"); r.page.wait_for_function("!!state.heldMicStream")
    r.cfg(saveDelay=0)
    # 3.4: second recording in the same minute
    r.select_screen(1); r.record(2)
    r.stop_save("3_4_second.webm")
    name2 = r.last_name
    pat = r"^recording-\d{4}-\d{2}-\d{2}_\d{6}\.webm$"
    r.check("3.4", name1 != name2 and re.match(pat, name1) and re.match(pat, name2), "names: %s / %s" % (name1, name2))


def s4_pause(r):
    r.start()
    r.page.click("#toggleMic"); r.page.wait_for_function("!!state.heldMicStream")
    r.select_screen(1)
    errs = []; chunks = []

    def snap():
        u = r.ui(); errs.append(u["err"]); chunks.append(u["chunks"]); return u

    r.record(4); snap()
    r.page.click("#btnPause"); r.wait(300)
    u1 = snap(); p1 = r.ev("__dr.readPreview()")
    r.wait(2000)
    u2 = snap(); p2 = r.ev("__dr.readPreview()")
    r.page.click("#btnPause"); r.wait(2500)
    u3 = snap()
    ok41 = u1["status"] == "Paused" and u1["timer"] == u2["timer"] and u3["status"] == "Recording" and 1 <= secs(u3["timer"]) - secs(u2["timer"]) <= 4
    r.check("4.1", ok41, "Pause: status '%s', timer %s -> %s over 2s (stopped). Resume: status '%s', timer %s (continues from where it stopped). Preview during pause: barcode time %s -> %s (%s)."
            % (u1["status"], u1["timer"], u2["timer"], u3["status"], u3["timer"], p1["ds"], p2["ds"], "frozen" if p1["ds"] == p2["ds"] else "still live on screen - the recorder is paused, the preview canvas is not"))
    r.page.click("#btnPause"); r.wait(14500)
    u4 = snap()
    r.check("4.2", u4["paused"] and u4["err"] == "", "paused 14.5s: banner='%s' (no write-stall warning)" % u4["err"])
    r.page.click("#btnPause"); r.wait(4000); u5 = snap()
    r.page.click("#btnPause"); r.wait(1500); r.page.click("#btnPause"); r.wait(3000); u6 = snap()
    r.stop_save("4_pause.webm")
    u7 = r.ui()
    pr = r.probe("4_pause.webm", step=0.5); au = r.audio("4_pause.webm"); sm = summarize(pr)
    exp = secs(u7["timer"])
    ds = [x for x in sm["ds"] if x is not None]
    mono = all(b >= a for a, b in zip(ds, ds[1:]))
    jumps = [b - a for a, b in zip(ds, ds[1:]) if b - a > 12]
    ok43 = sm["valid"] == sm["n"] and mono and abs(pr["duration"] - exp) <= 2.5 and len(jumps) == 3 and au["has"] and abs(au["duration"] - pr["duration"]) < 1.0
    r.check("4.3", ok43, "3 pauses (2s, 14.5s, 1.5s). File duration %.1fs vs timer %ss (pauses excluded, not truncated); %d/%d sampled frames valid and in order; exactly %d content jumps at the pause points (%s tenths) - no black gap or stuck frame; audio %.1fs. Audible glitch at the joins not judged by ear."
            % (pr["duration"], exp, sm["valid"], sm["n"], len(jumps), jumps, au["duration"]))
    r.check("4.4", ok43 and sm["maxSeekMs"] < 3000 and pr["seekableEnd"] and abs(pr["seekableEnd"] - pr["duration"]) < 0.5,
            "multi-pause file seeks end-to-end: %d random-access seeks, slowest %dms, seekable range ends at %.1fs" % (sm["n"], sm["maxSeekMs"], pr["seekableEnd"] or -1))
    cn = [int(c.split()[0]) for c in chunks if c]
    r.check("9.1", all(e == "" for e in errs) and cn == sorted(cn) and cn[-1] > cn[0],
            "full record/pause/resume/stop/save cycle incl. a 14.5s pause: chunk counter %s (climbing), banner empty at all %d checkpoints" % (cn, len(errs)))


def s5_change(r):
    r.start()
    r.page.click("#toggleMic"); r.page.wait_for_function("!!state.heldMicStream")
    r.select_screen(1)
    r.page.click("#errorBanner .error-banner-close")
    r.record(4)
    a = r.ui()
    r.page.click("#btnPause"); r.wait(400)
    b = r.ui()
    order = r.ev("[...document.querySelectorAll('.action-btns button')].filter(e => getComputedStyle(e).display !== 'none').map(e => e.textContent.trim())")
    # 5.4 cancel
    r.cfg(screenMode="cancel"); r.page.click("#btnChangeScreen"); r.wait(700)
    c = r.ui(); sid = r.ev("state.screenStream.__drId"); live = r.ev("state.screenStream.getVideoTracks()[0].readyState")
    r.check("5.4", c["err"] == "" and c["paused"] and c["rec"] and sid == 1 and live == "live" and c["btnChange"],
            "picker cancelled: banner='%s', still paused=%s, old screen (id %s) track %s, Change screen still offered" % (c["err"], c["paused"], sid, live))
    # 5.5 failure
    r.cfg(screenMode="fail"); r.page.click("#btnChangeScreen"); r.wait(700)
    d = r.ui(); sid = r.ev("state.screenStream.__drId")
    r.check("5.5", (d["err"] or "").startswith("Couldn't switch screens") and d["paused"] and d["rec"] and sid == 1,
            "capture failed: banner='%s'; still paused=%s, recording alive=%s, old screen kept" % (d["err"], d["paused"], d["rec"]))
    # 5.3 real swap, with a 3s 'hunt' while paused
    r.cfg(screenMode="ok", screenId=2, screenW=1280, screenH=720); r.page.click("#btnChangeScreen")
    r.page.wait_for_function("state.screenStream.__drId === 2"); r.wait(3000)
    r.page.click("#btnPause"); r.wait(300)
    e = r.ui()
    r.check("5.1", (not a["btnChange"]) and b["btnChange"] and order == ["Caption editor", "Resume", "Change screen", "Stop & save", "Stop & review"] and not e["btnChange"],
            "recording: visible=%s; paused: visible=%s, button order=%s; after Resume: visible=%s" % (a["btnChange"], b["btnChange"], order, e["btnChange"]))
    r.wait(4000)
    # 5.7 the OLD screen's track ending must not stop the recording
    r.ev("__dr.streams[0].getVideoTracks()[0].dispatchEvent(new Event('ended'))"); r.wait(1200)
    f = r.ui()
    # 5.8 swap to a differently-shaped source
    r.page.click("#btnPause"); r.wait(300)
    r.cfg(screenMode="ok", screenId=3, screenW=800, screenH=600); r.page.click("#btnChangeScreen")
    r.page.wait_for_function("state.screenStream.__drId === 3"); r.wait(500)
    r.page.click("#btnPause"); r.wait(4000)
    g = r.ui()
    # genuine "Stop sharing" on the CURRENT screen: the stop arrives with no click on the page
    if r.kind == "ff":
        # This Firefox build does not deliver a scripted 'ended' event to track listeners, so the stop can't be staged.
        r.stop_save("5_change.webm")
        h = dict(r.ui()); h["rec"] = False
        ff_note = True
        r.results.pop("5.7b", None)
    else:
        ff_note = False
        # Fire the event from a page timer 7s out and do not touch the page meanwhile: the
        # automation's own calls count as a user gesture, and a real 'Stop sharing' click does not.
        n0 = r.ev("__dr.saveDone")
        r.ev("setTimeout(() => { window.__actAtEnd = navigator.userActivation.isActive; state.screenStream.getVideoTracks()[0].dispatchEvent(new Event('ended')); }, 7000)")
        r.wait(14000)
        act = r.ev("window.__actAtEnd")
        saved = r.ev("__dr.saveDone") > n0
        h = r.ui()
        msg = h["err"]; rec_banner = None
        if saved:
            r.ev("t => __dr.exportLast(t)", "5_change.webm")
            r.check("5.7b", True, "extra: capture ended by the browser with no click on the page (page had an active user gesture at that moment: %s). Automatic save completed normally" % act)
        elif h.get("saveNeedsClick"):
            # REVIEW #29 (v1.27): the app offers a "Save recording" button; its click is a real gesture.
            p = r.stop_save("5_change.webm", button="#saveNeedsClick button.btn-save")
            h2 = r.ui()
            r.check("5.7b", bool(p) and not msg and not h2["err"] and not h2.get("saveNeedsClick"),
                    "extra: capture ended by the browser with no click on the page (page had an active user gesture at that moment: %s). The app showed the 'Recording stopped - ready to save' banner (error shown: '%s'); clicking Save recording produced the file (%s); afterwards banner showing: %s, error: '%s'"
                    % (act, msg, bool(p), h2.get("saveNeedsClick"), h2["err"]))
        else:
            r.reload(); r.wait(800)
            rec_banner = r.ui()["recovery"]
            r.stop_save("5_change.webm", button="#recoveryBanner button.btn-save")
            r.check("5.7b", False, "extra: capture ended by the browser with no click on the page (page had an active user gesture at that moment: %s). Automatic save did NOT complete - the app showed: '%s'. Nothing was lost: after a reload the recovery banner offered the recording (%s) and Recover & save produced the file. Cause: Chrome only opens a save dialog during a user gesture, and this stop has none. (The save dialog here is a stand-in that mirrors that Chrome rule.)" % (act, msg, rec_banner))
    pr = r.probe("5_change.webm", step=0.5); sm = summarize(pr)
    ids = [s["id"] for s in pr["samples"] if s["valid"]]
    seq = [ids[0]] + [b_ for a_, b_ in zip(ids, ids[1:]) if b_ != a_]
    r.check("5.3", seq == [1, 2, 3] and sm["valid"] == sm["n"], "saved file shows screen 1 then screen 2 (then 3) with no frames from the paused picker hunt: screen sequence %s, %d/%d frames valid, duration %.1fs" % (seq, sm["valid"], sm["n"], pr["duration"]))
    if ff_note:
        r.rec("5.7", "HUMAN", "cannot be staged in this Firefox build (scripted 'ended' events are not delivered to the track's listeners, so neither half of the check means anything here). Needs the real 'Stop sharing' control.")
    else:
        r.check("5.7", f["rec"] and not f["paused"] and g["rec"] and not h["rec"],
                "old screen's track 'ended' after the swap -> recording kept going (recording=%s). 'ended' on the CURRENT screen -> recording stopped (recording=%s). Simulated track events; the real browser 'Stop sharing' bar was not clicked. See 5.7b for what happens to the save." % (f["rec"], h["rec"]))
    last = [s for s in pr["samples"] if s["valid"] and s["id"] == 3]
    r.check("5.8", pr["w"] == 1280 and pr["h"] == 720 and len(last) >= 3,
            "swap from 1280x720 to an 800x600 source: output stays %dx%d, %d frames from the new source decode correctly (stretched to the first screen's shape, not corrupted). Whether the stretch looks acceptable is the owner's eye." % (pr["w"], pr["h"], len(last)))


def s5_noaudio(r):
    if r.kind != "cr":
        return
    r.start()
    r.select_screen(1, audio=False)
    r.record(3)
    r.page.click("#btnPause"); r.wait(300)
    r.cfg(screenMode="ok", screenId=2, screenAudio=True); r.page.click("#btnChangeScreen")
    r.page.wait_for_function("state.screenStream.__drId === 2"); r.wait(500)
    u = r.ui()
    r.page.click("#btnPause"); r.wait(3000)
    v = r.ui()
    r.stop_save("5_6_noaudio.webm")
    au = r.audio("5_6_noaudio.webm"); pr = r.probe("5_6_noaudio.webm", step=1)
    r.check("5.6", "started without audio" in (u["err"] or "") and "info" not in u["errClass"] and v["rec"] and not au["has"] and pr["duration"] > 4,
            "no-audio recording swapped to a source carrying an audio track -> note '%s'; recording continued, saved file plays (%.1fs) with no audio track. Stand-in audio source; real system audio not exercised." % (u["err"], pr["duration"]))


def s6_quality(r):
    r.start()
    labels = r.ev("[...document.querySelectorAll('#qualitySelect option')].map(o => o.textContent + (o.selected ? '*' : ''))")
    sizes = {}
    dis = None
    for val, tag in (("800000", "6_small.webm"), ("2500000", "6_best.webm")):
        r.page.select_option("#qualitySelect", val)
        r.cfg(noise=30); r.select_screen(1)
        r.record(20)
        dis = r.ev("document.getElementById('qualitySelect').disabled")
        p = r.stop_save(tag)
        sizes[val] = os.path.getsize(p)
    ratio = sizes["2500000"] / max(1, sizes["800000"])
    r.check("6.1", labels == ["Smaller file", "Balanced*", "Best quality"] and ratio > 1.4,
            "options=%s; ~20s of the same busy content: Smaller=%d KB, Best=%d KB (%.1fx)" % (labels, sizes["800000"] // 1024, sizes["2500000"] // 1024, ratio))
    r.check("6.2", dis is True, "quality selector disabled while recording=%s" % dis)
    r.reload()
    v = r.ev("document.getElementById('qualitySelect').value")
    r.check("6.3", v == "2500000", "after reload the selector still reads %s (Best quality)" % v)


def canvas_xy(r, fx, fy):
    b = r.page.locator("#previewCanvas").bounding_box()
    return b["x"] + fx * b["width"], b["y"] + fy * b["height"]


def drag(r, f0, f1):
    x0, y0 = canvas_xy(r, *f0); x1, y1 = canvas_xy(r, *f1)
    r.page.mouse.move(x0, y0); r.wait(80)
    cur = r.ev("document.getElementById('previewCanvas').style.cursor")
    r.page.mouse.down(); r.page.mouse.move((x0 + x1) / 2, (y0 + y1) / 2, steps=5); r.page.mouse.move(x1, y1, steps=5); r.page.mouse.up(); r.wait(250)
    return cur


def pip(r):
    return r.ev("(() => { const q = getPipRect(); return { x: q.x / canvas.width, y: q.y / canvas.height, w: q.w / canvas.width, h: q.h / canvas.height, xFrac: pipState.xFrac, yFrac: pipState.yFrac, widthFrac: pipState.widthFrac, shape: pipState.shape, mirror: pipState.mirror, saved: localStorage.getItem('pipLayout') }; })()")


def s7_pip(r):
    r.start()
    r.cfg(camMode="canvas")
    r.select_screen(1)
    r.page.click("#toggleCamera"); r.page.wait_for_function("!!state.cameraStream"); r.wait(800)
    q = pip(r)
    L = [q["x"] + q["w"] * 0.2, q["y"] + q["h"] * 0.85]; R = [q["x"] + q["w"] * 0.8, q["y"] + q["h"] * 0.85]
    pv = r.ev("p => __dr.readPreview(p)", [L, R])
    r.check("7.1", near(pv["pts"][0], RED) and near(pv["pts"][1], GREEN) and not r.ui()["rec"], "Webcam ON with a screen selected, no recording: camera overlay live at default corner (pixels %s / %s = camera's left/right halves)" % (pv["pts"][0], pv["pts"][1]))
    # 7.2 drag
    cur = drag(r, [q["x"] + q["w"] / 2, q["y"] + q["h"] / 2], [0.30, 0.35])
    q2 = pip(r)
    L = [q2["x"] + q2["w"] * 0.2, q2["y"] + q2["h"] * 0.85]; R = [q2["x"] + q2["w"] * 0.8, q2["y"] + q2["h"] * 0.85]
    OLD = [q["x"] + q["w"] * 0.5, q["y"] + q["h"] * 0.85]
    pv = r.ev("p => __dr.readPreview(p)", [L, R, OLD])
    moved = abs(q2["x"] + q2["w"] / 2 - 0.30) < 0.03 and abs(q2["y"] + q2["h"] / 2 - 0.35) < 0.03
    ok72 = cur == "grab" and moved and near(pv["pts"][0], RED) and near(pv["pts"][1], GREEN) and near(pv["pts"][2], BG[1]) and q2["saved"] and abs(json.loads(q2["saved"])["xFrac"] - q2["xFrac"]) < 1e-6
    # 7.3 resize via the grip
    def grip(qq):
        return [qq["x"] + qq["w"] - 0.004, qq["y"] + qq["h"] - 0.006]
    cur2 = drag(r, grip(q2), [0.99, 0.6]); big = pip(r)["widthFrac"]
    cur3 = drag(r, grip(pip(r)), [0.0, 0.5]); small = pip(r)["widthFrac"]
    drag(r, grip(pip(r)), [pip(r)["x"] + 0.25, 0.6]); q3 = pip(r)
    hs = max(20, round(q3["w"] * 1280 * 0.1))
    G = [q3["x"] + q3["w"] - (hs * 0.325) / 1280, q3["y"] + q3["h"] - (hs * 0.325) / 720]
    L = [q3["x"] + q3["w"] * 0.2, q3["y"] + q3["h"] * 0.5]; R = [q3["x"] + q3["w"] * 0.8, q3["y"] + q3["h"] * 0.5]
    gp = r.ev("p => __dr.readPreview(p)", [G])["pts"][0]
    r.record(4)
    dis_rec = r.ev("[document.getElementById('pipShapeSelect').disabled, document.getElementById('mirrorToggle').disabled]")
    r.stop_save("7_pip.webm")
    pr = r.probe("7_pip.webm", times=[1.0, 2.0, 3.0], points=[L, R, G, OLD])
    pts = pr["samples"][1]["pts"]
    in_out = near(pts[0], RED) and near(pts[1], GREEN) and near(pts[3], BG[1])
    r.check("7.2", ok72 and in_out, "hover cursor='%s'; dragged to centre (%.2f, %.2f) and it stayed there; old corner back to screen content; layout saved; recorded file shows the camera at the new spot (pixels %s / %s)" % (cur, q2["x"] + q2["w"] / 2, q2["y"] + q2["h"] / 2, pts[0], pts[1]))
    r.check("7.3", cur2 == "nwse-resize" and abs(big - 0.5) < 0.002 and abs(small - 0.08) < 0.002 and sum(gp) > sum(pts[2]) + 120 and near(pts[2], GREEN),
            "grip cursor='%s'; dragged wide -> width %.0f%% of canvas (clamped at 50%%); dragged narrow -> %.0f%% (clamped at 8%%); grip pixel in preview=%s (bright), same spot in the recorded file=%s (plain camera - grip not recorded)" % (cur2, big * 100, small * 100, gp, pts[2]))
    r.check("3.7", in_out and abs(q3["widthFrac"] - 0.25) < 0.02, "screen+webcam recording: overlay present in the saved file at the position/size set beforehand (width %.0f%% of frame; left/right pixels %s / %s match the preview)" % (q3["widthFrac"] * 100, pts[0], pts[1]))
    # 7.5 shapes
    r.select_screen(1); r.wait(600)
    res = {}
    for shape in ("square", "circle", "rectangle"):
        r.page.select_option("#pipShapeSelect", shape); r.wait(500)
        qq = pip(r); mb = r.ev("__dr.previewMagenta()")
        corner = r.ev("p => __dr.readPreview(p)", [[qq["x"] + qq["w"] * 0.03, qq["y"] + qq["h"] * 0.03]])["pts"][0]
        cx = (mb["x0"] + mb["x1"]) / 2 / 1280; cy = (mb["y0"] + mb["y1"]) / 2 / 720
        res[shape] = {"aspect": round(mb["w"] / max(1, mb["h"]), 2), "pipAspectPx": round(qq["w"] * 1280 / (qq["h"] * 720), 2), "off": [round(cx - (qq["x"] + qq["w"] / 2), 3), round(cy - (qq["y"] + qq["h"] / 2), 3)], "corner": corner}
    ok75 = all(abs(v["aspect"] - 1) < 0.08 and abs(v["off"][0]) < 0.01 and abs(v["off"][1]) < 0.012 for v in res.values()) and abs(res["square"]["pipAspectPx"] - 1) < 0.03 and near(res["circle"]["corner"], BG[1]) and not near(res["square"]["corner"], BG[1])
    r.check("7.5", ok75 and dis_rec[0] is True, "camera's test disc stays round and centred in every shape (width/height: %s; centre offset: %s); square box is 1:1; circle's corner shows screen content (%s); shape selector disabled while recording=%s"
            % ({k: v["aspect"] for k, v in res.items()}, {k: v["off"] for k, v in res.items()}, res["circle"]["corner"], dis_rec[0]))
    # 7.6 mirror
    r.page.select_option("#pipShapeSelect", "rectangle"); r.wait(300)
    qq = pip(r)
    L = [qq["x"] + qq["w"] * 0.2, qq["y"] + qq["h"] * 0.5]; R = [qq["x"] + qq["w"] * 0.8, qq["y"] + qq["h"] * 0.5]
    r.page.check("#mirrorToggle"); r.wait(500)
    pm = r.ev("p => __dr.readPreview(p)", [L, R])["pts"]
    r.record(3); r.stop_save("7_mirror.webm")
    po = r.probe("7_mirror.webm", times=[1.5], points=[L, R])["samples"][0]["pts"]
    r.reload()
    q4 = pip(r); chk = r.ev("document.getElementById('mirrorToggle').checked"); shp = r.ev("document.getElementById('pipShapeSelect').value")
    r.cfg(camMode="canvas")
    r.page.click("#toggleCamera"); r.page.wait_for_function("!!state.cameraStream")
    r.page.click("#toggleScreen"); r.wait(900)
    co = r.ev("p => __dr.readPreview(p)", [[0.2, 0.8], [0.8, 0.8]])["pts"]
    r.check("7.6", near(pm[0], GREEN) and near(pm[1], RED) and near(po[0], GREEN) and near(po[1], RED) and chk and near(co[0], GREEN) and near(co[1], RED) and dis_rec[1] is True,
            "Mirror ON: preview left/right = %s / %s (flipped), recorded file = %s / %s (flipped too); still ticked after reload=%s; camera-only view also flipped (%s / %s); checkbox disabled while recording=%s" % (pm[0], pm[1], po[0], po[1], chk, co[0], co[1], dis_rec[1]))
    # 7.4 persistence + different-resolution screen
    r.page.click("#toggleScreen"); r.wait(300)
    r.select_screen(2, w=1600, h=900); r.wait(600)
    q5 = pip(r); cw = r.ev("[canvas.width, canvas.height]")
    pv = r.ev("p => __dr.readPreview(p)", [[q5["x"] + q5["w"] * 0.5, q5["y"] + q5["h"] * 0.85]])["pts"][0]
    same = abs(q4["xFrac"] - q3["xFrac"]) < 1e-6 and abs(q4["widthFrac"] - q3["widthFrac"]) < 1e-6 and abs(q5["xFrac"] - q3["xFrac"]) < 1e-6
    r.check("7.4", same and shp == "rectangle" and cw == [1600, 900], "after reload: position/size fractions identical (x %.3f, y %.3f, width %.3f), shape='%s'; on a 1600x900 screen the same fractions apply (canvas %s) and the overlay draws there" % (q4["xFrac"], q4["yFrac"], q4["widthFrac"], shp, cw))


def s8_background(r):
    r.start()
    r.page.click("#toggleMic"); r.page.wait_for_function("!!state.heldMicStream")
    r.select_screen(1)
    r.record(5)
    other = r.ctx.new_page(); other.goto(r.base + "/out/blank.html"); other.bring_to_front()
    r.wait(1500)
    hidden = r.ev("[document.hidden, document.visibilityState, !!state.drawWorker]")
    if not hidden[0]:
        other.close()
        r.stop_save("8_bg_unused.webm")
        r.rec("8.1", "HUMAN", "this automated (headless) browser never reports the tab as hidden (document.hidden=%s), so a genuine background-tab run can't be staged here" % hidden[0])
        r.rec("8.2", "HUMAN", "see 8.1")
        return
    t_hide = r.ev("__dr.readPreview().ds")
    time.sleep(40)
    other.close(); r.page.bring_to_front(); r.wait(3000)
    r.stop_save("8_bg.webm")
    pr = r.probe("8_bg.webm", step=1); sm = summarize(pr)
    ds = [x for x in sm["ds"] if x is not None]
    stuck = max([0] + [sum(1 for _ in g) for g in [[1 for b_ in ds[i:i + 6] if b_ == ds[i]] for i in range(len(ds))]])
    r.check("8.1", hidden[0], "recording kept running ~40s with the tab hidden behind another tab (document.hidden=%s, worker draw clock active=%s)" % (hidden[0], hidden[2]))
    r.check("8.2", sm["valid"] == sm["n"] and stuck <= 2 and pr["duration"] > 40, "file %.1fs; frames sampled every 1s through the hidden stretch keep advancing (longest run of an identical frame: %d samples) - not a frozen picture" % (pr["duration"], stuck))


def s9_resilience(r):
    r.start()
    r.select_screen(1)
    r.record(6)
    mt = r.ev("state.mediaRecorder.mimeType")
    w1 = r.ev("(Date.now() - state.startTime) / 1000")
    r.stop_save("9_4_screen_noaudio.webm")
    pr = r.probe("9_4_screen_noaudio.webm", step=1); au = r.audio("9_4_screen_noaudio.webm"); sm = summarize(pr)
    r.cfg(camMode="canvas")
    r.page.click("#toggleCamera"); r.page.wait_for_function("!!state.cameraStream")
    r.select_screen(1); r.record(5)
    w2 = r.ev("(Date.now() - state.startTime) / 1000")
    r.stop_save("9_4_screen_cam_noaudio.webm")
    pr2 = r.probe("9_4_screen_cam_noaudio.webm", step=1); sm2 = summarize(pr2)
    full = abs(pr["duration"] - w1) < 1.0 and abs(pr2["duration"] - w2) < 1.0
    r.check("9.4", sm["valid"] == sm["n"] and not au["has"] and sm2["valid"] == sm2["n"] and "opus" not in mt and full,
            "mic OFF: recorder mimeType '%s' (no audio codec requested); recording starts and completes, files are valid with no audio track. Length check: screen-only recorded %.1fs -> file plays %.1fs; screen+webcam recorded %.1fs -> file plays %.1fs%s"
            % (mt, w1, pr["duration"], w2, pr2["duration"], "" if full else "  <-- the saved file's stated length is short: the end of the recording is cut off on playback"))
    # 9.3: recorder dies silently mid-recording -> Stop & save must still act
    r.select_screen(1); r.record(6)
    r.ev("() => { const m = state.mediaRecorder; m.onstop = null; m.stop(); }"); r.wait(1500)
    msgs = []

    def trig():
        r.page.click("#btnStop"); r.wait(200); msgs.append(r.ui()["err"])

    p = r.save_via("9_3_salvage.webm", trig)
    pr3 = r.probe("9_3_salvage.webm", step=1)
    r.check("9.3", "saving what was captured" in (msgs[0] or "") and pr3["duration"] > 4,
            "recorder killed behind the app's back mid-recording; Stop & save -> '%s' and a playable %.1fs file was saved (never a dead click)" % (msgs[0], pr3["duration"]))
    r.rec("9.2", "SKIP", "optional; depends on Firefox's broken recorder state, which can't be produced on demand (unit harness covers the abort logic)")


def s17_hint(r):
    r.start()
    r.select_screen(1, audio=False); r.wait(300)
    u = r.ui()
    r.check("17.2", bool(u["err"]) and "info" in u["errClass"].split(), "first audio-less screen -> banner shown with class '%s' (calm info style)" % u["errClass"])
    if r.kind == "cr":
        r.check("17.3", "Also share audio" in u["err"], "wording: '%s'" % u["err"])
    else:
        r.check("17.4", "loopback" in u["err"] and "Stereo Mix" in u["err"] and "VB-Audio Cable" in u["err"] and "microphone" in u["err"], "wording: '%s'" % u["err"])
    r.page.click("#errorBanner .error-banner-close"); r.wait(200)
    u2 = r.ui()
    r.check("17.6", u2["err"] == "" and "visible" not in u2["errClass"], "x clicked -> banner hidden (class '%s')" % u2["errClass"])
    r.select_screen(2, audio=False); r.wait(300)
    u3 = r.ui()
    r.record(2)
    r.page.click("#btnCaptionEditor"); r.wait(300)
    u4 = r.ui()
    r.check("17.7", bool(u4["err"]) and "info" not in u4["errClass"].split() and "visible" in u4["errClass"].split(), "after the hint, a genuine error ('%s') shows with class '%s' (normal error style)" % (u4["err"][:50], u4["errClass"]))
    r.page.click("#errorBanner .error-banner-close"); r.wait(200)
    u5 = r.ui()
    r.check("18.3", u5["err"] == "" and "visible" not in u5["errClass"].split(), "error banner x clicked -> dismissed")
    r.stop_save("17_tmp.webm")
    r.ev("localStorage.clear()"); r.reload()
    r.select_screen(1, audio=False); r.wait(300)
    u6 = r.ui()
    r.check("17.5", u3["err"] == "" and bool(u6["err"]) and "info" in u6["errClass"], "second audio-less selection: banner='%s' (silent); after clearing site storage it shows again: %s" % (u3["err"], bool(u6["err"])))
    if r.kind == "cr":
        r.ev("localStorage.clear()"); r.reload()
        r.select_screen(1, audio=True); r.wait(300)
        a = r.ui(); flag0 = r.ev("localStorage.getItem('audioHintShown')")
        r.record(4)
        r.page.click("#btnPause"); r.wait(300)
        r.cfg(screenMode="ok", screenId=2, screenAudio=False); r.page.click("#btnChangeScreen")
        r.page.wait_for_function("state.screenStream.__drId === 2"); r.wait(400)
        b = r.ui(); flag1 = r.ev("localStorage.getItem('audioHintShown')")
        r.page.click("#btnPause"); r.wait(2000)
        r.stop_save("17_1_sysaudio.webm")
        au = r.audio("17_1_sysaudio.webm")
        r.check("17.8", a["err"] == "" and flag0 is None and b["err"] == "" and flag1 is None, "hint still unused (flag=%s); paused swap to an audio-less source -> no hint from the swap path (banner='%s', flag=%s)" % (flag0, b["err"], flag1))
        r.check("17.1", au["has"] and au["per"] and au["per"][0] > 0.01, "PROXY ONLY: a screen stream carrying an audio track (stand-in tone, mic off) lands in the saved file (audio RMS %.3f in first second). Chrome's real 'Also share audio' checkbox and real system sound need the owner." % (au["per"][0] if au.get("per") else 0))


def s18_misc(r):
    r.start()
    # (1) dark + webcam off -> picker
    r.cfg(screenMode="ok", screenId=1); r.page.click("#toggleScreen"); r.wait(1000)
    a = r.ui(); c1 = calls(r)[1]
    m1 = c1 == 1 and a["hasScreen"] and a["screenActive"] and GUARD not in (a["err"] or "")
    # (2) lit, nothing else on -> off, guard reverts
    r.page.click("#toggleScreen"); r.wait(300)
    b = r.ui()
    m2 = b["sources"]["screen"] and (b["err"] or "").startswith(GUARD)
    # (4) capturing + webcam on -> simply disables the screen source
    r.page.click("#toggleCamera"); r.page.wait_for_function("!!state.cameraStream"); r.wait(300)
    r.page.click("#toggleScreen"); r.wait(500)
    d = r.ui()
    m4 = (not d["sources"]["screen"]) and (not d["hasScreen"]) and d["err"] == "" and not d["btnSelect"]["vis"]
    # back to: screen intent on, dark, webcam on -> (3) camera-only entrance
    r.page.click("#toggleScreen"); r.wait(300)
    e = r.ui()
    r.page.click("#toggleScreen"); r.wait(500)
    f = r.ui(); c3 = calls(r)[1]
    m3 = e["sources"]["screen"] and not e["hasScreen"] and (not f["sources"]["screen"]) and c3 == c1 and not f["btnRecord"]["dis"]
    r.check("18.1", m1 and m2 and m3 and m4, "(1) dark+webcam off -> picker opened, no guard text: %s; (2) lit, only source -> reverted with guard banner: %s; (3) dark+webcam on -> camera-only, no picker: %s; (4) capturing+webcam on -> screen source simply off: %s" % (m1, m2, m3, m4))
    # 18.2 cancelled re-selection
    r.start()
    r.select_screen(1)
    r.select_screen(2, mode="cancel")
    u = r.ui()
    r.check("18.2", u["btnSelect"]["text"] == "Select Screen" and not u["btnSelect"]["sel"] and u["btnRecord"]["dis"] and u["placeholder"] and not u["screenActive"],
            "cancelled re-selection: button reads '%s' (selected style=%s), Record disabled=%s, placeholder shown=%s, Screen toggle lit=%s; banner='%s'" % (u["btnSelect"]["text"], u["btnSelect"]["sel"], u["btnRecord"]["dis"], u["placeholder"], u["screenActive"], u["err"]))


ALL = [s1_load, s1_camera, s1_camonly_record, s2_devices, s2_deny, s3_basic, s4_pause, s5_change, s5_noaudio, s6_quality, s7_pip, s8_background, s9_resilience, s17_hint, s18_misc]

if __name__ == "__main__":
    kind = sys.argv[1]
    headed = "--headed" in sys.argv
    names = [a for a in sys.argv[2:] if not a.startswith("--")]
    sc = [f for f in ALL if not names or f.__name__ in names]
    run(kind, sc, 8791 if kind == "cr" else 8792, headless=not headed)
