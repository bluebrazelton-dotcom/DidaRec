# DidaRec — Next Session, Start Here

Close-out snapshot, 2026-10-04 (post-#20 machine pass).
Supersedes the 2026-08-06 snapshot. This session: the owner-run #20 pass had
stalled, so the 120-item checklist was run by a new Playwright rig
(`regression_rig/`, committed on main, NOT pushed). 208 browser checks
passed; the pass found real defects, logged as REVIEW #27–#33. **The build is
not final.** `index.html` then got two one-line fixes (v1.26, 191a3b6: opaque
canvas + first frame painted at once), rig-verified. Later the same day:
**v1.27 (#29) and v1.28 (#31 message, #32)**, both rig-verified and
owner-checked in real Chrome on the local file, committed on main, NOT
pushed — the hosted page is still v1.26. Harness now **181 / 1287**
(prefixes end at FO).
Browsers have moved: Chrome 154, Firefox 157 (baseline was FF 153).
**Direction change this session: Chrome-first** (see Ground rules); README
updated to recommend Chrome/Edge.

## #20 machine pass (newest): what it found

- **#27 Chrome 154 video = BlockGroups.** The canvas's alpha channel makes
  Chrome write frames as BlockGroup + BlockAdditions; the block walkers only
  read SimpleBlocks. Mic-off recordings: Duration short (end cut off on
  playback), seams overlap, cuts land seconds early. With audio: masked, but
  cuts fall back to Rule A.
  **FIXED v1.26** (`getContext('2d', { alpha: false })`), plus the black
  first frame on every Chrome take. Owner acceptance PASSED 2026-10-04.
- **#28 First-cluster cuts are never refined** (`computeCutPlan` k===0).
  Firefox's first cluster is 7–9 s: typed 0:07 → "start over" prompt.
- **#29 Chrome: gesture-less stop can't open the save dialog** ("Stop
  sharing", auto-stops) → "Save failed … use Recovery".
  **FIXED v1.27** ("Recording stopped — ready to save" banner; the Save
  recording click runs the same save). Owner check PASSED 2026-10-04 in
  real Chrome on the local file.
- **#30 Firefox save memory spike** (+1.1 to +1.8 GB on 100–400 MB files,
  test build 151). Needs owner confirmation on real Firefox (Y11).
- **#31 Firefox: Record stuck on "Starting…"** behind cleanup after a large
  confirmed save. **EXPLAINED v1.28** (status-line message); the wait itself
  remains — owner decision: message only. Rig Firefox, synthetic data: 15 s
  at 75 MB, over 5 min at 375 MB (`regression_rig/cleanup_wait.py`).
- **#32** small UX items: caption-export notes in the editor and the "Kept"
  label **FIXED v1.28**, owner check PASSED; storage-stall item documented
  only. **#33** README part done; checklist wording still open.
- v1.27/v1.28 rig results: `regression_rig/results_2026-10-04_v1.28/`
  (Chrome part 1 is from the v1.27 build; parts 2–3 and the Firefox
  cleanup-wait run are v1.28; `s15_review_c` errored once in a full part-2
  run on v1.27 and passed alone and in the next full run — cause not found).
- Evidence: `regression_rig/results_2026-10-04/` (per-item JSON, built
  results page, memory samples). Results page artifact:
  claude.ai/artifact/WdEhAyUEdwEMdU84xPiWrs (owner's 11-task short list).

## v1.25 (newest): first audio-less share hint (#26 hint half)

- One-time hint when a screen capture lands with no audio track. Fires
  in selectScreen only (FC pins swaps silent); once ever via
  localStorage 'audioHintShown' (try/catch idiom, FF pins throwing
  localStorage can't break selection); branches on the
  showSaveFilePicker proxy — Chrome wording (tick "Also share audio")
  vs Firefox wording (loopback input as the mic). Calm .info modifier
  on the dismissable banner via showInfoBanner; showError strips .info
  on EVERY call (single choke point — FD/FE pin the lifecycle).
- **Harness: 173 scenarios / 1234 assertions** (prefixes end at FG).
  The showError mock now WRAPS the real function (was a replacement) —
  real banner classList logic under test for the first time.
- **v1.25 owner acceptance PASSED 2026-08-06, both browsers** — all
  five checklist items. #26's hint half CLOSED.
- #26's docs half SHIPPED 2026-08-06 as the README's "System audio on
  Firefox" section — **#26 fully CLOSED**.

## Where things stand

- **v1.24 SHIPPED (#23): pause → change screens → resume.** A "Change
  screen" button between Pause and Stop, visible only while a
  screen-capturing recording is paused (never camera-only — EQ).
  `changeScreenPaused()` acquires the NEW capture FIRST; cancel
  (silent) or failure (one gentle note) is a proven no-op — old screen
  intact, still paused, still resumable (ES/ET). Zero recording-
  pipeline/save-flow changes: EY's end-to-end differential shows a
  paused-swap session's saved bytes === a no-swap session's.
- **#23 CLOSED same day** — owner acceptance PASSED 2026-08-04, both
  browsers (canvas stretch judged acceptable; deliberate swaps never
  tripped a stop). Item 6's no-audio note is Chrome-only in practice:
  Firefox ignores getDisplayMedia audio entirely (upstream Bugzilla
  1541425), so the note's trigger can't occur there — expected. The
  finding spawned **#26** (Firefox system-audio loopback guidance).
- Working pattern held: Sonnet drafted in scratch + pre-verified on
  copies with the real harness; orchestrator review verified the
  ended-listener extraction byte-for-byte, hand-checked the
  audioContext lifecycle, and found 1 hygiene gap (stale
  audioMixDest/screenAudioSourceNodes between recordings — unreachable
  as a bug, but fixed by amendment: both teardown sites now clear them
  atomically with audioContext); owner approved draft+amendment before
  any repo write.
- **Harness: 165 scenarios / 1197 assertions** (`node test.cjs`;
  prefixes end at EY). Harness-side additions: AudioContext source-node
  mock records connect/disconnect; `makeEndedCapableTrack` does real
  listener bookkeeping and models worst-case stop()-fires-'ended';
  screenVideo/cameraVideo exposed read-only via __api.

## Permanent design knowledge (new ● + carried forward)

- ● **The recorder records the COMPOSITOR CANVAS, not the screen
  stream** — that's why #23 was pipeline-free: swapping
  screenVideo.srcObject mid-pause is invisible to MediaRecorder, chunk
  writes, and saves. The draw clock keeps painting while paused.
- ● **A recording's audio track set is FIXED at start** (v1.21.2 opus
  rule): no mix at start → no audio can ever be added mid-recording.
  Swap audio reconnection goes through the SAME live destination node
  (state.audioMixDest); mix teardown is atomic (context + dest + source
  nodes together, both teardown sites).
- ● **The screen 'ended' listener is a tracked (track, handler) pair**
  (wire/unwireScreenEndedListener) — deliberate swap stops can't trip
  it even on a browser that fires 'ended' on script stop(); genuine
  "Stop sharing" still stops the recording. Never re-inline it.
- ● The seam-offset formula has FOUR lockstep sites: concatenateWebM /
  scanSegmentsForStitch / computeCutPlan / computeRedoLastTakePlan
  (EK's oracle pins #4 against #3; DS assertNoOverlap enforces).
- ● The dark Screen button has FOUR click meanings (EI); camera-only
  reachability pinned by AH. changeScreenPaused is deliberately a
  SEPARATE entry point — don't fold it into toggleSource/selectScreen.
- ● Both browsers write UNKNOWN-SIZE clusters (Chrome 1-byte 0xFF, FF
  8-byte all-ones — N/O/AL); refineCutToBlock refuses known-size
  clusters (AX) and falls back to Rule A.
- ● FF153: audio codec in mimeType + no audio track = silent zero-chunk
  recorder (DX pins the fix). FF has no vp9; first blob can be ~7.5s
  late; clusters ~7.5s vs Chrome ~1s; storage can wedge (watchdogs).
- Watch for **Firefox 154** (~days away): may fix the upstream opus
  bug; v1.21.2's fix and the watchdogs stay regardless.
- ● **Chrome 154 writes video frames as BlockGroups (0xA0 → 0xA1 Block +
  0x75A1 BlockAdditions) when the canvas has alpha; audio stays SimpleBlock.**
  Anything that walks blocks must handle both or the canvas must be opaque
  (#27). Chrome video-only clusters are keyframe-spaced (~3.4 s), not ~1 s.
- ● **Chrome's save dialog needs a user gesture.** Any stop the user didn't
  click in the page (Stop sharing, write failure, watchdog) cannot call
  showSaveFilePicker (#29). The rig's stand-in dialog enforces this.
  Handled since v1.27 by the Save recording banner (saveDialogNeedsClick /
  offerSaveClick); any new save entry point must start from a click.

## Load-bearing invariants (do not break)

- Seam offsets = previous segment's CONTENT END, four lockstep sites.
  refineCutToBlock's keptEndMs floors at the cluster timestamp (DZ).
- applyReviewCutPlan is the ONE cut-application path; 'noop'/'startOver'
  stay with each CALLER; its T is read only on the cutAtByte>0 branch.
- changeScreenPaused ORDERING: new capture succeeds BEFORE anything old
  is touched (unwire listener → disconnect audio → stop tracks →
  reassign → rewire → reconnect). ES/ET pin the no-op guarantees; EU
  pins the listener guard; EV pins same-destination reconnection.
- Refinement is an ENHANCEMENT (EF/EH pin fallbacks); never surface a
  refinement error.
- claimFinalize() mutual exclusion; finalizeStarted survives resetUI,
  resets only in startRecording; salvage paths force stopMode='save'.
- Undo re-record arms the FULL pane chain (DO/EE/EK).
- confirmDownloadArrived: mark-completed-first, background delete.
- The review-pane preview is the ONE legitimate concatenateWebM caller.
- New reviewState fields go into resetState(). New state fields go into
  the harness resetState Object.assign AND (if mix-related) the atomic
  teardown sites.

## Gotchas (unchanged ones compressed)

- New vm module state must be `var`; timing consts go in ORIG_TIMINGS
  AND resetState's timer-clearing block; mirror the DY capture/restore
  pattern for any navigator mock a scenario swaps.
- PowerShell Get-Content/Set-Content mangles this repo's BOM-less LF
  files — Edit tools or bash/sed only. Git's CRLF warnings are benign.
- Grep tool can render `//` as `\` (display artifact) — Read before
  believing a "syntax error".
- AL/AM/AN pin literal timestamp/Duration strings; AG lit-guard; EI
  four Screen-click meanings.
- Real-browser behavior is invisible to the harness. `regression_rig/` now
  covers most of it (see its README): run one Chrome and one Firefox at a
  time, never more — parallel load stalls Firefox storage and fails checks
  for reasons unrelated to the app. The rig's Firefox is Playwright's build
  (151), not the installed one; ear/eye judgments, native pickers and hidden
  tabs still need the owner. Owner acceptance still gates UI-flow features.

## Queue

- ~~v1.25 owner acceptance~~ PASSED 2026-08-06; **#26 fully CLOSED**
  (hint half accepted; docs half shipped as the README's "System audio
  on Firefox" section).
- ~~#19 README half~~ SHIPPED 2026-08-06: full README rewrite —
  Firefox-first + save-flow difference, feature list (take controls,
  Change screen, captions save-first-then-open), loopback walkthrough,
  live Pages URL (repo renamed: bluebrazelton-dotcom/DidaRec),
  Firefox 153+ floor (owner's tested version — earlier untested).
  Docs-only; no version bump; harness untouched at 173/1234.
- **#19 remainder: faculty-facing usage guide** (REVIEW deliverable 2)
  — plain-language what-to-click instructions for non-technical
  faculty: recording basics, pause/resume, crash recovery + Continue
  Recording, per-browser saving, captions workflow, file:// Chrome
  device-name caveat. Placement decision owed (README section vs.
  separate file vs. in-app help).
- **#20 — machine pass DONE 2026-10-04; owner remainder = 11 tasks, AFTER
  fixes.** Order:
  1. DONE for #29 (Y2 confirmed 2026-10-04). Y11 (#30, Firefox memory) still
     open and optional under Chrome-first.
  2. Fix session(s): DONE — #27 (v1.26), #29 (v1.27), #31 message and
     #32 (v1.28). Under Chrome-first, #28 is documented
     in the README rather than fixed, and #30 is fixed only if Y11 confirms
     it AND it risks losing a recording. Docs #33: README part done
     2026-10-04; checklist wording still open.
  3. Re-run the rig on the fixed build (parts 1–3 ≈ 25 min per browser;
     part 4 ≈ 45 min).
  4. Owner runs the remaining short-list tasks once, on the final build:
     the Chrome column in full; Firefox as a smoke pass (Y1, Y8, Y10).
  5. Then #19's faculty guide.
- Unpushed: main is ahead of origin by the v1.27 and v1.28 commits (fix,
  rig, docs). Push when the owner says so, then repeat the two real-Chrome
  checks on the hosted page if wanted. Older note: the rig commit
  includes `original_checklist.html`, previously kept out of the repo —
  decide before pushing.
- Roadmap remainder (REVIEW feature map): chapter hotkeys + sidecar
  export, mediabunny remux (Cues/MP4) — all unscheduled,
  owner-priority-driven. (Stale "caption VTT/SRT import" entry removed
  2026-08-06 — import/export shipped with the v1.18 editor.)

## Ground rules (unchanged)

Zero dependencies, single `index.html`, ONE `<script>` block. WebM only.
Don't touch the recording pipeline's byte behavior or the streamed save
flows (differentials enforce).
**Chrome-first (owner decision 2026-10-04, reverses "Firefox first"):**
Chrome/Edge is the recommended browser and gates releases and owner
acceptance. Firefox is supported with known limits: a Firefox bug that loses
a recording still gets fixed; Firefox-only limits (system audio, first-cluster
cuts #28, download save flow) get documented, not engineered around.
Acceptance order: Chrome first, then a Firefox smoke pass.
Faculty tone. Delegate
drafting to Sonnet agents; orchestrator reviews EVERYTHING before it
ships. File Edit Rule: agents draft in scratch; orchestrator presents in
full, waits for approval. End with a working page; bump BUILD_LOG and
REVIEW when done.
