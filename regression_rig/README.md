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
    python part4.py cr 30 12  # section 14 (30-min recording + 12-min crash recovery)
    python merge.py           # non-pass summary across both browsers -> merged.json
    python build_artifact.py  # results page -> didarec_short_list.html

Name scenarios to run a subset: `python part2.py ff s15_review_a s15_review_b`.
(`s15_review_b` reads state left by `s15_review_a`; run them together.)

Do not run more than one Chrome and one Firefox at a time. With more, Firefox's
storage stalls and checks fail for reasons that have nothing to do with the app.

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

- `dbg3.py cr [mic] [--headed]` dumps the stored cluster structure of a
  recording (how the Chrome BlockGroup finding was diagnosed).
- `make_alpha_copy.py` writes a scratch copy of the app with an opaque canvas
  context into `app_alpha_false/`; point the rig at it with the `DIDAREC_APP`
  environment variable.
- `dbg_probe.py cr <file>` prints file time against content time for a saved
  recording in `out_cr/`.
