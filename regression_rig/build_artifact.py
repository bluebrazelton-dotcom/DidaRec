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
     "look": "The recording stops and you end up with a saved file. In Chrome, note whether the save dialog opens or you get a \"Save failed ... use Recovery\" message (see finding 3).",
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
]
covers = {}
for y in YOURS:
    for c in y["covers"]:
        covers[c] = y["id"]

FINDINGS = [
    {"sev": "high", "where": "Chrome 154", "title": "Chrome now stores video frames in a form the app's indexing code skips",
     "body": "Chrome 154 writes each video frame as a BlockGroup (it is carrying a transparency channel from the canvas) instead of a SimpleBlock. The app's duration, keyframe and cut-point code only reads SimpleBlocks. With the mic on, audio blocks mask most of it. With no audio at all, it shows.",
     "points": ["Mic off: the saved file's stated length is short, so the end of the recording is cut off on playback. Measured: 6.1 s recorded, file plays 3.4 s (item 9.4).",
                "Mic off: a re-record cut lands seconds early and the status line disagrees with the file. Asked for 0:08, status said \"Kept 0:06\", file kept 3.3 s (extra check 15.3b).",
                "Mic on: cuts fall back to whole-cluster precision, landing 0.5-0.8 s early. Still inside the checklist's one-second rule, but not the frame-level precision v1.22 was built for.",
                "Every cluster after the first is treated as having no keyframe, so the saved file carries almost no seek index. LONGRUN",
                "Tried on a scratch copy, not in your repo: creating the compositor canvas as opaque (one line, getContext('2d', { alpha: false })) makes Chrome write SimpleBlocks again; length and keyframe flags came out right. That is a candidate fix, not a tested one.",
                "Your project notes never mention BlockGroups, so this probably arrived with a Chrome update after August. I can't date it."]},
    {"sev": "high", "where": "Firefox", "title": "A re-record point in the first seconds of a take can't be cut to",
     "body": "The cut code drops the whole first cluster of a take rather than cutting inside it. Chrome's first cluster is about a second; Firefox's was 7 to 9 seconds in these runs.",
     "points": ["First take: typing 0:07 on a 20 s recording brought up the \"start over - discard everything?\" prompt instead of cutting (item 15.4 fails as written). Typing 0:12 cut correctly.",
                "Later take: a cut 3.5 s into the second take dropped that whole take and landed 3.2 s early (extra check 15.14b).",
                "Past the first cluster, Firefox cuts were accurate: 12.4 s, 63.3 s and a re-cut all landed within a quarter second."]},
    {"sev": "med", "where": "Chrome", "title": "\"Stop sharing\" probably ends in \"Save failed\" instead of a save dialog",
     "body": "Chrome only opens a save dialog while the page is handling a click. When the browser's own Stop-sharing control ends the capture, there is no click on the page. With a stand-in dialog that enforces the same rule, the app showed: \"Save failed: ... Must be handling a user gesture to show a file picker. Your recording is safe - refresh and use Recovery.\" The recording was recoverable after a reload.",
     "points": ["Needs one confirmation in real Chrome (Y2). The same would apply to any stop the app triggers itself, such as storage running full."]},
    {"sev": "low", "where": "Chrome", "title": "Saving captions gives no visible confirmation",
     "body": "After a successful caption save, and after a cancelled one, the app writes its note to the recorder's status bar, which is hidden while the caption editor is open. Firefox shows its note inside the editor. Items 16.11 and 16.12 otherwise pass.", "points": []},
    {"sev": "low", "where": "Both", "title": "\"Kept m:ss\" reads one second low on whole-second cuts",
     "body": "The status rounds down, and a cut never keeps anything past the requested time. Typing 0:07 reports \"Kept 0:06\"; a cut at 0:20 reports \"Kept 0:19\". Cosmetic.", "points": []},
    {"sev": "low", "where": "Firefox, under load", "title": "Storage stalls were handled at load but not everywhere",
     "body": "When my rig ran five browsers at once, Firefox's storage stalled. The app showed its \"storage isn't responding\" message at load, as designed. But Record then sat on \"Starting...\" with no further message, and once a re-record click did nothing for 30 seconds. Neither happened when Firefox ran alone.", "points": []},
    {"sev": "note", "where": "Checklist", "title": "Three checklist lines no longer match the app",
     "body": "1.4: clicking Screen at load now opens the picker (v1.22.2); the guard message only appears from the lit state, which passed. 4.1: the preview stays live while paused; only the recorder pauses. 1.3: the Screen button is dark at load until a screen is selected (v1.21.3).", "points": []},
    {"sev": "note", "where": "README (18.5)", "title": "Doc spot-check: two inaccuracies, one omission",
     "body": "The Chrome paragraph says you pick the destination up front and the recording streams to it as it's captured; in fact the dialog opens at Stop and the file is written then. Requirements say HTTPS is required, while your own setup notes run it from a double-clicked file. Mirror webcam isn't in the feature list.", "points": []},
]

LIMITS = [
    "Chrome was your installed Chrome 154, driven by Playwright. Firefox was Playwright's own build, version 151, not your 157 and below the README's 153 floor.",
    "Camera and mic were the browsers' fake devices. The screen picker was replaced by a generated moving test pattern with a time code in it, which is how the content of every saved file could be verified frame by frame.",
    "Chrome's save dialog was replaced by a stand-in that writes through the same file API. Firefox downloads were real.",
    "Runs were headless except the background-tab check. Nothing was judged by ear or eye.",
    "Nothing in the screen-recorder repo was changed. Scripts and test recordings are in a scratch folder.",
]

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
                ev = "Not machine-checked." if row["y"] else "Not run."
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
    parts = []
    for b, name in (("cr", "Chrome"), ("ff", "Firefox")):
        r = (merged.get("14.2") or {}).get(b)
        if r:
            parts.append("%s 14.2: %s" % (name, r["status"]))
    seek_note = "Long-file result: " + "; ".join(parts) + " (see section 14 below)."
else:
    seek_note = "Whether that slows seeking in a long file is what the 30-minute run (section 14, still running) will show."
for f in FINDINGS:
    f["points"] = [p.replace("LONGRUN", seek_note) for p in f["points"]]

data = {"sections": out_sections, "yours": YOURS, "findings": FINDINGS, "limits": LIMITS, "extras": extras, "tally": tally,
        "longDone": long_done, "built": __import__("time").strftime("%Y-%m-%d %H:%M")}
tpl = open(os.path.join(HERE, "page_template.html"), encoding="utf-8").read()
html = tpl.replace("/*DATA*/null", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
with open(OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write(html)
print("built", OUT, len(html), "bytes; tally", tally, "extras", len(extras), "long_done", long_done)
