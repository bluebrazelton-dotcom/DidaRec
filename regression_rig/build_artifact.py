"""Build the short-list page from merged.json + the original checklist's item texts."""
import json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ORIG = os.path.join(HERE, "original_checklist.html")
OUT = os.path.join(HERE, "didarec_short_list.html")

subprocess.run([sys.executable, os.path.join(HERE, "merge.py")], capture_output=True)
merged = json.load(open(os.path.join(HERE, "merged.json"), encoding="utf-8"))
src = open(ORIG, encoding="utf-8").read()


def js(s):
    return json.loads('"' + s + '"')


sections = []
for m in re.finditer(r'\{n:(\d+), title:"((?:[^"\\]|\\.)*)"', src):
    sections.append({"n": int(m.group(1)), "title": js(m.group(2)), "items": []})
for m in re.finditer(r'\{id:"([^"]+)", b:"(\w+)", src:"((?:[^"\\]|\\.)*)",(?: opt:true,)? t:"((?:[^"\\]|\\.)*)"\}', src):
    iid = m.group(1)
    sec = next(s for s in sections if s["n"] == int(iid.split(".")[0]))
    sec["items"].append({"id": iid, "b": m.group(2), "opt": "opt:true" in m.group(0), "t": js(m.group(4))})
n_items = sum(len(s["items"]) for s in sections)
assert n_items == 120, n_items

# ---- what stays with the owner -------------------------------------------------
YOURS = [
    {"id": "Y1", "b": ["ff", "cr"], "title": "One real recording, judged by ear",
     "do": "Mic on, share a window, record about a minute while talking. Pause once for a few seconds, resume, keep talking, then Stop & save and play it back.",
     "look": "Your voice sounds like you (not thin or phone-like). Lips and sound line up. No click or gap where you paused. While the Mic toggle is on, Windows shows the mic-in-use indicator.",
     "covers": ["2.2", "2.7", "3.2", "4.3"]},
    {"id": "Y2", "b": ["ff", "cr"], "title": "Stop sharing from the browser's own bar",
     "do": "Start a recording, then end the share with the browser's \"Stop sharing\" control instead of the app's Stop button. Extra credit: do it after a paused Change screen.",
     "look": "The recording stops and you end up with a saved file. In Chrome a \"Recording stopped - ready to save\" banner appears and its Save recording button opens the save dialog (v1.27; you passed this on the local file on 2026-10-04, so this is a repeat on the hosted page).",
     "covers": ["5.7"]},
    {"id": "Y3", "b": ["cr"], "title": "Chrome system audio",
     "do": "Share a tab or window with \"Also share audio\" ticked while something plays; record 15 seconds and save. Then: start a recording with mic off and no shared audio, pause, Change screen to a source with audio ticked.",
     "look": "First file contains the computer sound. Second case shows the gentle \"started without audio\" note and keeps recording.",
     "covers": ["17.1", "5.6"]},
    {"id": "Y4", "b": ["ff", "cr"], "title": "Change screen to a differently shaped window",
     "do": "Record a full screen, pause, Change screen to a small or tall window, resume for a few seconds, save, and watch.",
     "look": "The stretched picture is acceptable to you. This is a judgment call only you can make; the mechanics passed.",
     "covers": ["5.8"]},
    {"id": "Y5", "b": ["ff", "cr"], "title": "Recording with the tab in the background",
     "do": "Record something that moves (a video or a clock). Switch to another tab or minimise the browser for a minute, come back, save, and scrub through the hidden stretch.",
     "look": "The picture keeps moving through the hidden minute instead of freezing while the sound continues.",
     "covers": ["8.1", "8.2"]},
    {"id": "Y6", "b": ["ff", "cr"], "title": "Real permission prompts",
     "do": "Clear site data, load the app, toggle Webcam and Mic on. In Chrome opened from a file (double-clicked index.html), toggle Mic off and on a few times.",
     "look": "No prompt on load. One prompt per device, then real device names. In file-Chrome only the first toggle-on asks; later ones don't nag.",
     "covers": ["1.5", "2.8"]},
    {"id": "Y7", "b": ["ff"], "title": "Switch microphones in Firefox",
     "do": "Only if you have two mics: Mic on, pick the other one in the dropdown, record a few seconds.",
     "look": "The recording uses the newly chosen mic. Chrome was machine-checked; the test Firefox only had one fake mic. Optional extra: plug or unplug a device and see the dropdown update without a prompt.",
     "covers": ["2.4", "2.10"]},
    {"id": "Y8", "b": ["ff"], "title": "Cancel Firefox's own Save-As dialog",
     "do": "With \"Always ask you where to save files\" on: record 10 seconds, Stop & save, cancel the Save-As dialog, click \"It didn't arrive\", reload.",
     "look": "The recovery banner comes back and Recover & save gives you the file. The in-app half of this was machine-checked; the native dialog needs a person.",
     "covers": ["12.3"]},
    {"id": "Y9", "b": ["ff", "cr"], "title": "Drag a video into the caption editor",
     "do": "Open the caption editor and drag a .webm in from File Explorer. Add one caption and play across it.",
     "look": "The video opens, and the caption is drawn on the picture at the right moment.",
     "covers": ["16.2", "16.3"]},
    {"id": "Y10", "b": ["ff", "cr"], "title": "One real crash",
     "do": "Record 15 seconds, end the browser from Task Manager, reopen, Continue recording for 10 more seconds, save, and watch across the join.",
     "look": "Banner appears; the saved file plays through the join without a multi-second freeze or silence. Tab-kill and browser-close were machine-checked; a hard process kill and your eyes on the seam were not.",
     "covers": ["10.1", "11.2"]},
    {"id": "Y11", "b": ["ff"], "title": "Optional: watch memory while Firefox saves a long recording",
     "do": "Record 20 to 30 minutes at Best quality in your own Firefox. Open Task Manager, then Stop & save and watch Firefox's memory until the download bar appears. Afterwards click \"It's there - all set\", then try Record again straight away.",
     "look": "Memory stays roughly flat rather than climbing by a gigabyte or more. If Record has to wait, the status line says it is clearing out the last recording; note roughly how long the wait is. Both are findings below.",
     "covers": ["14.1", "14.3", "14.4"]},
]
MISSING = {("14.4", "ff"): "Not run: after the long save was confirmed, Record was still waiting on the previous recording's cleanup past the script's 20 s limit, with the v1.28 explanation showing (see findings). Chrome ran it and passed.",
           ("14.5", "ff"): "Optional; not run."}
covers = {}
for y in YOURS:
    for c in y["covers"]:
        covers[c] = y["id"]

FINDINGS = [
    {"sev": "high", "where": "Firefox", "title": "OPEN - Saving a long recording spikes memory far past the file size",
     "body": "Checklist 14.1 and 14.3 expect memory to stay roughly flat while a long recording is prepared and saved. In the test Firefox it does not. Chrome's memory stays flat on the same recordings. Not fixed: it needs your confirmation on real Firefox first (Y11), and under Chrome-first it is fixed only if it is real and risks losing a recording.",
     "points": ["Re-run on v1.28, committed memory across the whole browser process tree: 30-minute recording, 363 MB file, 606 MB to a 2,424 MB peak (+1.8 GB); the save took 139 s.",
                "30-minute crash recovery, 368 MB file: 418 MB to a 2,710 MB peak (+2.3 GB); the save took 132 s.",
                "Chrome on the same run: memory fell by 51 MB while saving a 367 MB file.",
                "Playwright's Firefox 151 with the download captured by the test tool, so check it once on your Firefox 157 with Task Manager open (Y11). The files themselves were complete and seeked correctly."]},
    {"sev": "med", "where": "Firefox", "title": "DOCUMENTED, NOT FIXED - A re-record point in the first seconds of a take can't be cut to",
     "body": "The cut code drops the whole first cluster of a take rather than cutting inside it. Chrome's first cluster is about a second; Firefox's is 7 to 9 seconds. Under Chrome-first this is described in the README rather than engineered around.",
     "points": ["First take: typing 0:07 on a 20 s recording brings up the \"start over - discard everything?\" prompt instead of cutting (item 15.4 fails as written). Typing 0:12 cuts correctly.",
                "Later take: a cut 3.5 s into the second take drops that whole take and lands 3.4 s early (extra check 15.14b).",
                "Past the first cluster, Firefox cuts are accurate to a quarter second."]},
    {"sev": "med", "where": "Firefox", "title": "EXPLAINED in v1.28, WAIT REMAINS - Right after a big save is confirmed, Record waits",
     "body": "After clicking \"It's there - all set\" on a long recording, the app is still deleting the saved recording's stored pieces, and the next recording waits behind that. Since v1.28 the status line says so: \"Clearing out your last recording first - after a long recording this can take a few minutes. Recording will begin when it's done.\" The wait itself is unchanged (your decision: message only).",
     "points": ["Measured in the test Firefox on stored test data: 15 s at 75 MB; not started after 5 minutes at 375 MB. Real Firefox 157 not measured.",
                "In the full re-run, Record had not started 20 s after a real 363 MB save was confirmed, and the message was showing. That stopped the short follow-up clip (14.4) from running in Firefox."]},
    {"sev": "low", "where": "Firefox, under load", "title": "OPEN, NOT REPRODUCED ALONE - Storage stalls were handled at load but not everywhere",
     "body": "When the rig ran five browsers at once, Firefox's storage stalled. The app showed its \"storage isn't responding\" message at load, as designed. But Record then sat on \"Starting...\" with no further message, and once a re-record click did nothing for 30 seconds. Neither happened when Firefox ran alone. No code change.", "points": []},
    {"sev": "note", "where": "Checklist", "title": "OPEN - Three checklist lines no longer match the app",
     "body": "1.4: clicking Screen at load now opens the picker (v1.22.2); the guard message only appears from the lit state, which passed. 4.1: the preview stays live while paused; only the recorder pauses. 1.3: the Screen button is dark at load until a screen is selected (v1.21.3).", "points": []},
    {"sev": "note", "where": "Chrome 154", "title": "FIXED in v1.26 - Chrome stored video frames in a form the app's indexing code skipped",
     "body": "Chrome 154 wrote each video frame as a BlockGroup because the compositor canvas carried a transparency channel; the app's duration, keyframe and cut-point code only reads SimpleBlocks. The canvas is now opaque, so Chrome writes SimpleBlocks again. You accepted this in real Chrome on 2026-10-04.",
     "points": ["Mic-off recordings now report their full length (item 9.4 passes) and cuts land where asked (asked for 0:08, kept 8.1 s).",
                "Seeking a 30-minute Chrome file: eight jumps, slowest 148 ms (580 ms before the fix).",
                "The one-frame black flash at the start of every Chrome take was fixed in the same version."]},
    {"sev": "note", "where": "Chrome", "title": "FIXED in v1.27 - \"Stop sharing\" ended in \"Save failed\" instead of a save dialog",
     "body": "Chrome only opens a save dialog while the page is handling a click, and the browser's own Stop-sharing control gives the page none. The app now shows a \"Recording stopped - ready to save\" banner; its Save recording button opens the dialog. The same banner covers any stop the app triggers itself.",
     "points": ["You confirmed the original failure in real Chrome, then the fix on 2026-10-04: banner appeared, dialog opened, file played to the end.",
                "The rig's check (5.7b) passes on the fixed build and fails on the build before it.",
                "Not covered: a save in several parts whose second dialog opens after a long first write can still be refused."]},
    {"sev": "note", "where": "Chrome", "title": "FIXED in v1.28 - Saving captions gave no visible confirmation",
     "body": "The saved and cancelled notes now also appear in the caption editor's own status line. Items 16.11 and 16.12 require it and pass. You checked both in real Chrome on 2026-10-04.", "points": []},
    {"sev": "note", "where": "Both", "title": "FIXED in v1.28 - \"Kept m:ss\" read one second low on whole-second cuts",
     "body": "Typing 0:07 now reports \"Kept 0:07\" and a cut at 0:20 reports \"Kept 0:20\". You checked this in real Chrome on 2026-10-04.", "points": []},
    {"sev": "note", "where": "README (18.5)", "title": "FIXED - Doc spot-check: two inaccuracies, one omission",
     "body": "The README's Chrome save description, the HTTPS requirement and the missing Mirror webcam entry were corrected on 2026-10-04.", "points": []},
]

LIMITS = [
    "These results are a full re-run on v1.28 (pushed 2026-10-04), one browser at a time. Chrome: 117 checks passed, none failed. Firefox: 105 passed; the 4 failures and the one unfinished scenario are the open Firefox items above.",
    "Chrome was your installed Chrome 154, driven by Playwright. Firefox was Playwright's own build, version 151, not your 157 and below the README's 153 floor.",
    "Camera and mic were the browsers' fake devices. The screen picker was replaced by a generated moving test pattern with a time code in it, which is how the content of every saved file could be verified frame by frame.",
    "Chrome's save dialog was replaced by a stand-in that writes through the same file API and enforces Chrome's click rule. Firefox downloads were real.",
    "Runs were headless, and a hidden tab could not be staged, so background-tab recording is on your list. Nothing was judged by ear or eye.",
    "The test rig is in the repo's regression_rig folder.",
]

LEDE_EXTRA = " Chrome comes first: do the Chrome column in full, then Firefox as a smoke pass (Y1, Y8, Y10). Y11 is optional. Findings fixed since the first pass are marked FIXED below."
BASELINE = "Build under test: v1.28 (ef7224e), full re-run."

out_sections = []
tally = {"auto": 0, "problem": 0, "yours": 0, "skipped": 0}
for s in sections:
    items = []
    for it in s["items"]:
        row = {"id": it["id"], "t": it["t"], "opt": it["opt"], "y": covers.get(it["id"])}
        for b in ("ff", "cr"):
            if it["b"] not in ("both", b):
                row[b] = None
                continue
            res = (merged.get(it["id"]) or {}).get(b)
            if res is None:
                st = "yours" if row["y"] else "skipped"
                ev = MISSING.get((it["id"], b)) or ("Not machine-checked." if row["y"] else "Not run.")
            else:
                st = {"PASS": "auto", "FAIL": "problem", "HUMAN": "yours", "SKIP": "skipped", "ERROR": "problem"}[res["status"]]
                ev = res["evidence"]
                if st == "skipped" and row["y"]:
                    st = "yours"
            row[b] = {"s": st, "e": ev}
            tally[st] += 1
        items.append(row)
    out_sections.append({"n": s["n"], "title": s["title"], "items": items})

extras = []
for k, v in merged.items():
    if re.match(r"^\d+\.\d+[a-zA-Z]+$", k):
        extras.append({"id": k, "cr": v.get("cr") and {"s": v["cr"]["status"], "e": v["cr"]["evidence"]}, "ff": v.get("ff") and {"s": v["ff"]["status"], "e": v["ff"]["evidence"]}})

long_done = bool(merged.get("14.1"))
seek_note = ""
if long_done:
    seek_note = "In practice it did not hurt: eight jumps across a 30-minute Chrome file each landed correctly, slowest 580 ms."
else:
    seek_note = "Whether that slows seeking in a long file is what the 30-minute run (section 14, still running) will show."
for f in FINDINGS:
    f["points"] = [p.replace("LONGRUN", seek_note) for p in f["points"]]

data = {"sections": out_sections, "yours": YOURS, "findings": FINDINGS, "limits": LIMITS, "extras": extras, "tally": tally,
        "longDone": long_done, "ledeExtra": LEDE_EXTRA, "baseline": BASELINE, "built": __import__("time").strftime("%Y-%m-%d %H:%M")}
tpl = open(os.path.join(HERE, "page_template.html"), encoding="utf-8").read()
html = tpl.replace("/*DATA*/null", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
with open(OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write(html)
print("built", OUT, len(html), "bytes; tally", tally, "extras", len(extras), "long_done", long_done)
