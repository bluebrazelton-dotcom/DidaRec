# Regression rig

Drives the real app in real browser engines (Playwright) and checks the #20
regression checklist item by item. Built 2026-10-04. Read-only against
`index.html`; all output lands in this folder.

Needs: Python with `playwright` installed, Chrome installed, and Playwright's
Firefox build (`python -m playwright install firefox`).

## Run

Run from this folder. One browser per command; `cr` = installed Chrome,
`ff` = Playwright's Firefox.

    python part1.py cr        # sections 1-9, 17, 18
    python part2.py cr        # sections 10-13, 15 (crash, stitch, cancel-save, seek, review pane)
    python part3.py cr        # section 16 (caption editor)
    python part4.py cr        # section 14 (30-min crash recovery, then 30-min recording; ~75 min)
    python merge.py           # non-pass summary across both browsers -> merged.json
    python build_artifact.py  # results page -> didarec_short_list.html

Name scenarios to run a subset: `python part2.py ff s15_review_a s15_review_b`.
(`s15_review_b` reads state left by `s15_review_a`; run them together.)

Run ONE browser at a time, with nothing else heavy on the machine. Under load,
timing-sensitive checks fail for reasons that have nothing to do with the app
(recovery banner read before it fills in, audio shorter than video, a stale
frame, Firefox storage stalls). If a check fails, re-run its scenario alone
before believing it.

The memory checks (14.1, 14.3) judge committed memory across the whole browser
process tree: the rise during the save must stay under 50% of the file size.
Chrome's streamed save uses a roughly fixed 55-75 MB of working memory whatever
the file size (measured 2026-10-04: +74 MB on a 139 MB file, +56 MB on a 347 MB
file), so the recording has to be long for the percentage to mean anything —
keep both phases at 30 minutes. A 12-minute recovery file sits right on the
line and will flip between pass and fail. Firefox's download save measured
+1.1 to +2.1 GB on 100-400 MB files (REVIEW #30).

Before reading any change as an app change, run the same check against the last
commit as a control: `python make_head_copy.py`, set `DIDAREC_APP` to
`app_head`, re-run.

`python compare.py results_2026-10-04` (after `merge.py`) lists what changed
against a saved baseline.

## What stands in for what

- `stubs.js` is injected before the app's script. It replaces the screen picker
  with a generated test pattern carrying a time code (so saved files can be
  verified frame by frame), and in Chrome replaces the native save dialog with
  one that writes through the same file API and enforces Chrome's
  user-gesture rule.
- Camera and mic are the browsers' fake devices.
- Firefox is Playwright's patched build, not the installed Firefox.
- Nothing is judged by ear or eye, and a hidden/background tab can't be staged.

## Other scripts

- `cleanup_wait.py ff [chunks]` (REVIEW #31) stores a large session directly,
  confirms it as a finished download, clicks Record at once and times the wait
  and the status line. Default 1500 chunks x 256 KB; 300 chunks takes about two
  minutes. Run alone.

- `dbg3.py cr [mic] [--headed]` dumps the stored cluster structure of a
  recording (how the Chrome BlockGroup finding was diagnosed).
- `make_alpha_copy.py` writes a scratch copy of the app with an opaque canvas
  context into `app_alpha_false/`; point the rig at it with the `DIDAREC_APP`
  environment variable.
- `dbg_probe.py cr <file>` prints file time against content time for a saved
  recording in `out_cr/`.
