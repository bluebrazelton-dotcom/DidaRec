"""Checklist section 16 (caption editor)."""
import json, os, sys, time
from harness import run

GOOD_VTT = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nFirst\n\n00:00:03.000 --> 00:00:04.000\nSecond\n\n00:00:05.000 --> 00:00:06.000\nThird\n"
BAD_VTT = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nFirst\n\n00:00:04.000 --> 00:00:03.000\nBackwards\n\n00:00:05.000 --> 00:00:06.000\nThird\n"
GOOD_SRT = "1\n00:00:01,000 --> 00:00:02,000\nAlpha\n\n2\n00:00:03,000 --> 00:00:04,000\nBeta\n"


def cap(r):
    return r.ev("""() => { const v = document.getElementById('captionVideo'); const rows = [...document.querySelectorAll('#captionCueList .caption-cue-row')];
      const tt = v.textTracks && v.textTracks[0];
      return { status: document.getElementById('captionStatus').textContent, rows: rows.length,
        cues: captionEditorState.cues.map(c => [Math.round(c.start * 1000) / 1000, Math.round(c.end * 1000) / 1000, c.text]),
        starts: rows.map(x => x.querySelectorAll('.caption-time-input')[0].value), ends: rows.map(x => x.querySelectorAll('.caption-time-input')[1].value),
        texts: rows.map(x => x.querySelector('textarea').value), active: rows.findIndex(x => x.classList.contains('active')),
        t: v.currentTime, paused: v.paused, dur: v.duration, src: (v.currentSrc || '').slice(-12), controls: v.controls,
        trackMode: tt ? tt.mode : null, trackCues: tt && tt.cues ? [...tt.cues].map(c => [c.startTime, c.endTime, c.text]) : null,
        activeCues: tt && tt.activeCues ? [...tt.activeCues].map(c => c.text) : null,
        draftBanner: document.getElementById('captionDraftBanner').classList.contains('visible'),
        importBanner: document.getElementById('captionImportConfirmBanner').classList.contains('visible'),
        statusBarShown: getComputedStyle(document.getElementById('statusBar')).display !== 'none', mainStatus: document.getElementById('statusText').textContent }; }""")


def vseek(r, t):
    r.ev("""t => new Promise(res => { const v = document.getElementById('captionVideo'); v.onseeked = () => res(); v.currentTime = t; setTimeout(res, 5000); })""", t)
    r.wait(350)


def open_video(r, path, name):
    r.page.set_input_files("#captionVideoInput", path)
    r.page.wait_for_function("n => document.getElementById('captionStatus').textContent === 'Opened ' + n + '.' && document.getElementById('captionVideo').readyState >= 1", arg=name)
    r.wait(300)


def s16_captions(r):
    r.start("cap16")
    r.page.click("#toggleMic"); r.page.wait_for_function("!!state.heldMicStream")
    r.select_screen(1); r.record(10); A = r.stop_save("lecture.webm")
    r.select_screen(2); r.record(6); B = r.stop_save("lectureB.webm")
    for name, text in (("good.vtt", GOOD_VTT), ("bad.vtt", BAD_VTT), ("good.srt", GOOD_SRT)):
        with open(os.path.join(r.out, name), "w", newline="\n", encoding="utf-8") as f:
            f.write(text)
    P = lambda n: os.path.join(r.out, n)
    # leave an interrupted recording behind so a recovery banner is pending (for 16.14)
    r.select_screen(1); r.record(4)
    r.kill_tab(); r.wait(800)
    r.select_screen(1); r.wait(300)
    before = r.ui()

    # ---- 16.16 / 16.18: fresh editor, no video
    r.page.click("#btnCaptionEditor"); r.wait(300)
    u = r.ui()
    r.page.click("#captionEditor .btn-add-caption"); r.wait(200); c1 = cap(r)
    r.page.set_input_files("#captionImportInput", P("good.vtt")); r.wait(400); c2 = cap(r)
    r.check("16.16", "Open your video first" in c1["status"] and c1["rows"] == 0 and "Open your video first" in c2["status"] and c2["rows"] == 0,
            "no video open: Add caption -> '%s' (0 cues); Import captions -> '%s' (0 cues)" % (c1["status"], c2["status"]))
    hint = r.ev("(() => { const e = document.querySelector('#captionEditor .caption-hint'); return [getComputedStyle(e).display !== 'none' && e.getBoundingClientRect().height > 0, e.textContent]; })()")
    r.check("16.18", hint[0] and ".vtt" in hint[1] and "next to your video" in hint[1] and "unchanged" in hint[1], "hint line visible: '%s'" % hint[1])

    # ---- 16.1 open video
    open_video(r, A, "lecture.webm")
    c = cap(r)
    r.check("16.1", u["captions"] and not u["controls"] and c["controls"] and c["dur"] and c["dur"] > 8 and c["dur"] != float("inf"),
            "idle -> Caption editor: recorder controls hidden=%s, editor shown=%s; opened lecture.webm -> '%s', native controls=%s, duration %.1fs" % (not u["controls"], u["captions"], c["status"], c["controls"], c["dur"]))

    # ---- 16.3 add + edit a cue
    vseek(r, 2.0)
    r.page.click("#captionEditor .btn-add-caption"); r.wait(300)
    a = cap(r)
    ta = r.page.locator("#captionCueList .caption-cue-row textarea").first
    ta.fill("Hello world"); r.page.keyboard.press("Tab"); r.wait(900)
    vseek(r, 2.5)
    b = cap(r)
    ok = a["rows"] == 1 and a["texts"] == ["New caption"] and a["active"] == 0 and b["trackMode"] == "showing" and b["activeCues"] == ["Hello world"]
    r.check("16.3", ok, "Add caption at 2.0s -> 1 row, placeholder '%s', selected; typed text + tab away -> the video's caption track is showing and at 2.5s the active caption is %s (rendering on the picture itself not eyeballed)" % (a["texts"], b["activeCues"]))

    # ---- more cues, 16.6 seek on row click
    vseek(r, 5.0); r.page.click("#captionEditor .btn-add-caption"); r.wait(250)
    vseek(r, 7.5); r.page.click("#captionEditor .btn-add-caption"); r.wait(250)
    vseek(r, 0.2)
    row = r.page.locator("#captionCueList .caption-cue-row").nth(1)
    bb = row.bounding_box()
    r.page.mouse.click(bb["x"] + 3, bb["y"] + 3); r.wait(500)
    c = cap(r)
    r.check("16.6", abs(c["t"] - 5.001) < 0.05 and c["paused"], "3 cues; clicked the 2nd row's background -> video at %.3fs (cue starts 5.000), paused=%s" % (c["t"], c["paused"]))

    # ---- 16.7 time-edit validation
    def set_time(row_i, which, val):
        inp = r.page.locator("#captionCueList .caption-cue-row").nth(row_i).locator(".caption-time-input").nth(which)
        inp.fill(val); r.page.keyboard.press("Tab"); r.wait(350)

    set_time(2, 0, "banana"); e1 = r.ui()["err"]; c1 = cap(r)
    r.page.click("#errorBanner .error-banner-close")
    set_time(2, 0, "00:00:01.000"); c2 = cap(r)
    set_time(0, 1, "00:00:00.500"); e3 = r.ui()["err"]; c3 = cap(r)
    r.page.click("#errorBanner .error-banner-close")
    ok = "doesn't look like a time" in e1 and c1["starts"][2] == "00:00:07.500" and c2["starts"][0] == "00:00:01.000" and c2["starts"] == sorted(c2["starts"]) and "end time needs to come after the start time" in e3.lower().replace("the end", "end") and c3["cues"] == c2["cues"]
    r.check("16.7", ok, "'banana' -> '%s', input back to %s; valid earlier time -> row order now %s; end before start -> '%s', cue unchanged" % (e1, c1["starts"][2], c2["starts"], e3))

    # ---- 16.8 playback highlight (make the cues non-overlapping first)
    set_time(0, 1, "00:00:01.800")
    vseek(r, 0.5)
    seq = r.ev("""() => new Promise(res => { const v = document.getElementById('captionVideo'); v.muted = true; const out = []; const list = document.getElementById('captionCueList');
      const iv = setInterval(() => { const rows = [...document.querySelectorAll('#captionCueList .caption-cue-row')]; const i = rows.findIndex(x => x.classList.contains('active'));
        let inView = null; if (i >= 0) { const a = rows[i].getBoundingClientRect(), b = list.getBoundingClientRect(); inView = a.top >= b.top - 2 && a.bottom <= b.bottom + 2; }
        out.push([Math.round(v.currentTime * 10) / 10, i, inView]); if (v.currentTime > 7.6 || out.length > 80) { clearInterval(iv); v.pause(); res(out); } }, 200);
      v.play(); })""")
    order = []
    for t, i, iv in seq:
        if not order or order[-1] != i:
            order.append(i)
    views = [iv for _, i, iv in seq if i >= 0]
    r.check("16.8", [x for x in order if x >= 0] == [0, 1, 2] and all(views), "played 0.5s -> 7.6s: highlighted row went %s (-1 = between cues); highlighted row inside the list's visible area at every sample=%s. Smoothness not judged." % (order, all(views)))

    # ---- 16.4 type while playing
    vseek(r, 2.5)
    r.ev("document.getElementById('captionVideo').play()"); r.wait(250)
    r.page.click("#captionEditor .btn-add-caption"); r.wait(200)
    st = cap(r)
    new_i = st["active"] if st["active"] >= 0 else 2
    new_i = r.ev("captionEditorState.cues.findIndex(c => c.text === 'New caption' && c.start > 2.4 && c.start < 4)")
    ta = r.page.locator("#captionCueList .caption-cue-row").nth(new_i).locator("textarea")
    ta.click(); ta.press("Control+a")
    typed = "typing while it plays on"
    r.page.keyboard.type(typed, delay=140)
    chk = r.ev("""i => { const rows = [...document.querySelectorAll('#captionCueList .caption-cue-row')]; const ta = rows[i].querySelector('textarea');
      return { focused: document.activeElement === ta, value: ta.value, committed: captionEditorState.cues[i].text, active: rows.findIndex(x => x.classList.contains('active')), t: document.getElementById('captionVideo').currentTime, paused: document.getElementById('captionVideo').paused }; }""", new_i)
    r.ev("document.getElementById('captionVideo').pause()")
    r.page.keyboard.press("Tab"); r.wait(400)
    after = cap(r)
    r.check("16.4", chk["focused"] and chk["value"] == typed and chk["committed"] == "New caption" and chk["active"] != new_i and chk["active"] >= 0 and not chk["paused"] and after["texts"][new_i] == typed,
            "added a cue during playback (row %d) and typed %d chars without leaving the box while playback ran to %.1fs: highlight moved on to row %d, the box kept focus=%s and the uncommitted text '%s'; committed normally on tab-away" % (new_i, len(typed), chk["t"], chk["active"], chk["focused"], chk["value"]))

    # ---- 16.14 / 16.15 back to recorder mid-edit, during playback
    vseek(r, 1.0)
    r.ev("(() => { const v = document.getElementById('captionVideo'); v.muted = false; return v.play(); })()"); r.wait(600)
    playing = r.ev("!document.getElementById('captionVideo').paused")
    r.page.click("#captionEditor .btn-back-recorder"); r.wait(300)
    paused = r.ev("document.getElementById('captionVideo').paused")
    now = r.ui()
    r.check("16.15", playing and paused, "video playing=%s when Back to recorder was clicked -> paused=%s immediately" % (playing, paused))
    same = all(now[k] == before[k] for k in ("hasScreen", "recovery", "sources", "controls", "rec", "prior")) and now["btnSelect"]["text"] == before["btnSelect"]["text"] == "Change Screen" and now["recovery"] and not now["btnRecord"]["dis"]
    r.check("16.14", same and not now["captions"], "Back to recorder mid-edit: controls back, selected screen still live (button '%s', Record enabled), pending recovery banner still showing=%s" % (now["btnSelect"]["text"], now["recovery"]))
    r.page.click("#btnCaptionEditor"); r.wait(300)
    kept = cap(r)

    # ---- 16.9 draft restore
    r.wait(1600)
    snap = cap(r)["cues"]
    r.reload(); r.page.click("#btnCaptionEditor"); open_video(r, A, "lecture.webm")
    d1 = cap(r)
    r.page.click("#captionDraftBanner button.btn-record"); r.wait(400)
    d2 = cap(r)
    r.reload(); r.page.click("#btnCaptionEditor"); open_video(r, A, "lecture.webm")
    r.page.click("#captionDraftBanner button.btn-stop"); r.wait(600)
    d3 = cap(r)
    r.reload(); r.page.click("#btnCaptionEditor"); open_video(r, A, "lecture.webm")
    d4 = cap(r)
    r.check("16.9", kept["rows"] == 4 and d1["draftBanner"] and d1["rows"] == 0 and d2["cues"] == snap and len(snap) == 4 and d3["rows"] == 0 and not d4["draftBanner"],
            "edits autosaved; reload + reopen same video -> 'Saved caption edits found' banner=%s; Continue -> %d cues back, identical=%s. Reload, Start fresh -> %d cues; reload again -> banner=%s (draft deleted)" % (d1["draftBanner"], len(d2["cues"]), d2["cues"] == snap, d3["rows"], d4["draftBanner"]))

    # ---- 16.10 import (replace confirmation, partial import) and 16.5 same-file re-pick
    d0 = len(r.dialogs())
    r.page.set_input_files("#captionImportInput", P("good.vtt")); r.wait(500)
    i1 = cap(r)
    r.page.set_input_files("#captionImportInput", P("good.vtt")); r.wait(500)
    i2 = cap(r)
    r.page.click("#captionImportConfirmBanner button.btn-record"); r.wait(400)
    i3 = cap(r)
    r.page.set_input_files("#captionImportInput", P("bad.vtt")); r.wait(500)
    r.page.click("#captionImportConfirmBanner button.btn-record"); r.wait(400)
    i4 = cap(r)
    r.page.set_input_files("#captionImportInput", P("good.srt")); r.wait(500)
    r.page.click("#captionImportConfirmBanner button.btn-record"); r.wait(400)
    i5 = cap(r)
    r.check("16.10", i1["status"] == "Imported 3 captions." and i2["importBanner"] and len(r.dialogs()) == d0 and i3["status"] == "Imported 3 captions." and i4["rows"] == 2 and "left out" in i4["status"] and i5["status"] == "Imported 2 captions.",
            "empty list: '%s'. Non-empty list: in-pane 'Replace current captions?' banner=%s, browser popups=%d; confirm -> '%s'. File with one bad cue -> '%s'. .srt -> '%s'" % (i1["status"], i2["importBanner"], len(r.dialogs()) - d0, i3["status"], i4["status"], i5["status"]))
    src1 = cap(r)["src"]
    open_video(r, A, "lecture.webm"); src2 = cap(r)["src"]; again = cap(r)
    r.check("16.5", i2["importBanner"] and src1 != src2 and again["status"] == "Opened lecture.webm.",
            "same caption file picked twice in a row -> second pick was processed (replace banner appeared); same .webm opened twice in a row -> reloaded ('%s', new player source). Note: sequence used was import/import rather than import/Start fresh/import." % again["status"])
    if again["draftBanner"]:
        r.page.click("#captionDraftBanner button.btn-record"); r.wait(400)
    if cap(r)["rows"] == 0:
        r.page.set_input_files("#captionImportInput", P("good.vtt")); r.wait(500)

    # ---- 16.11 export naming + content
    cur = cap(r)
    r.save_via("export_lecture.vtt", lambda: r.page.click("#captionEditor .btn-save-vtt"), resolve=None); n_vtt = r.last_name
    after_save = cap(r); err_after = r.ui()["err"]
    r.save_via("export_lecture.srt", lambda: r.page.click("#captionEditor .btn-save-srt"), resolve=None); n_srt = r.last_name
    vtt = open(P("export_lecture.vtt"), encoding="utf-8").read(); srt = open(P("export_lecture.srt"), encoding="utf-8").read()
    n = len(cur["cues"])
    okx = n_vtt == "lecture.vtt" and n_srt == "lecture.srt" and vtt.startswith("WEBVTT") and vtt.count("-->") == n and srt.strip().startswith("1") and srt.count("-->") == n and "," in srt.split("-->")[0] and all(t in vtt and t in srt for _, _, t in cur["cues"])
    fb = "editor shows '%s'" % after_save["status"]
    if r.kind == "cr":   # REVIEW #32: the recorder status bar is hidden behind the editor, so the note must be in the editor
        okx = okx and "Captions saved" in (after_save["status"] or "")
    r.check("16.11", okx,"lecture.webm -> suggested '%s' and '%s'; both files well-formed with all %d edited cues (VTT header, SRT numbering and comma milliseconds). Feedback: %s" % (n_vtt, n_srt, n, fb))
    r._cap_feedback = (after_save["mainStatus"], after_save["statusBarShown"], after_save["status"])

    # ---- 16.12 export cancel (Chrome)
    if r.kind == "cr":
        r.cfg(saveMode="cancel"); r.page.click("#captionEditor .btn-save-vtt"); r.wait(700)
        x = cap(r); e = r.ui()["err"]; r.cfg(saveMode="ok")
        r.wait(1200)
        r.reload(); r.page.click("#btnCaptionEditor"); open_video(r, A, "lecture.webm")
        y = cap(r)
        r.check("16.12", e == "" and "Save cancelled" in (x["status"] or "") and y["draftBanner"],
                "save dialog cancelled -> no error banner; editor shows '%s'; draft still restorable after reload=%s" % (x["status"], y["draftBanner"]))
        r.page.click("#captionDraftBanner button.btn-record"); r.wait(300)

    # ---- 16.17 draft banner doesn't leak rows; 16.2 drag-and-drop
    open_video(r, B, "lectureB.webm")
    r.page.click("#captionEditor .btn-add-caption"); r.wait(1700)
    open_video(r, A, "lecture.webm")
    try:   # the draft lookup is asynchronous; give the banner a moment before deciding it isn't coming
        r.page.wait_for_selector("#captionDraftBanner.visible", timeout=3000)
    except Exception:
        pass
    if cap(r)["draftBanner"]:
        r.page.click("#captionDraftBanner button.btn-record"); r.wait(400)
    if cap(r)["rows"] == 0:   # make sure video A really has rows showing before switching to B
        r.page.click("#captionEditor .btn-add-caption"); r.wait(300)
    a_rows = cap(r)["rows"]
    open_video(r, B, "lectureB.webm")
    z = cap(r)
    r.check("16.17", a_rows > 0 and z["draftBanner"] and z["rows"] == 0, "video A showing %d cue rows; opened video B (which has its own draft) -> B's banner shown=%s with %d rows behind it" % (a_rows, z["draftBanner"], z["rows"]))
    r.page.click("#captionDraftBanner button.btn-record"); r.wait(300)
    dropped = r.ev("""async () => { const blob = await (await fetch('/out/lecture.webm')).blob(); const f = new File([blob], 'dropped-lecture.webm', { type: 'video/webm' });
      const dt = new DataTransfer(); dt.items.add(f); const el = document.getElementById('captionEditor');
      el.dispatchEvent(new DragEvent('dragover', { dataTransfer: dt, bubbles: true, cancelable: true }));
      el.dispatchEvent(new DragEvent('drop', { dataTransfer: dt, bubbles: true, cancelable: true }));
      await new Promise(r => setTimeout(r, 1200)); const v = document.getElementById('captionVideo'); return [document.getElementById('captionStatus').textContent, v.readyState, v.duration]; }""")
    r.check("16.2", dropped[0] == "Opened dropped-lecture.webm." and dropped[1] >= 1 and dropped[2] > 8, "PROXY: a synthetic drop event carrying a .webm onto the editor pane -> '%s', video loaded (%.1fs). A real drag from the OS file manager was not performed." % (dropped[0], dropped[2]))


ALL = [s16_captions]

if __name__ == "__main__":
    kind = sys.argv[1]
    run(kind, ALL, 8795 if kind == "cr" else 8796)
