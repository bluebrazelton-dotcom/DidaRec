"""REVIEW #31: Record clicked while the previous download's background cleanup is still deleting.

Stores a large session directly (no recording needed), puts it behind the
"did it arrive?" bar, clicks "It's there - all set", then clicks Record at once
and watches the status line until the recording starts.

    python cleanup_wait.py ff            # default 1500 chunks x 256 KB (~375 MB)
    python cleanup_wait.py ff 600        # fewer chunks

Run alone. Control: DIDAREC_APP=app_head (see README).
"""
import sys, time
from harness import run

N = 1500
KB = 256
MSG = "Clearing out your last recording"


def s31_cleanup_wait(r):
    r.start()
    t0 = time.time()
    sid = r.ev("""async ([n, kb]) => {
      const id = await createSession('video/webm');
      const buf = new Uint8Array(kb * 1024);
      for (let i = 0; i < n; i++) await addChunk(id, i, new Blob([buf]));
      return id; }""", [N, KB])
    seeded = time.time() - t0
    r.select_screen(1)
    r.ev("id => offerDownloadConfirm([id], 1)", sid)
    r.page.wait_for_selector("#downloadConfirm.visible")
    r.page.click("#downloadConfirm button.btn-save")
    t1 = time.time()
    r.page.click("#btnRecord")
    seen = []; started = None
    while time.time() - t1 < 900:
        s = r.ev("() => [document.getElementById('statusText').textContent, document.getElementById('btnRecord').textContent, state.recording]")
        if not seen or seen[-1][1] != s[0]:
            seen.append((round(time.time() - t1, 1), s[0], s[1]))
        if s[2]:
            started = time.time() - t1
            break
        r.wait(250)
    explained = any(MSG in t for _, t, _ in seen)
    waited = started if started is not None else 900.0
    # A wait under 2 s needs no explanation; a longer one must have been explained.
    r.check("31", started is not None and (waited < 2.0 or explained),
            "stored %d chunks x %d KB (%.0f MB) in %.0fs; 'all set' then Record at once: recording started after %s; wait explained on the status line: %s; status line over time: %s"
            % (N, KB, N * KB / 1024.0, seeded, ("%.1fs" % started) if started is not None else "NOT within 900s", explained, seen[:8]))
    if started is not None:
        r.wait(1500)
        r.stop_save("31_after.webm")


if __name__ == "__main__":
    kind = sys.argv[1]
    nums = [a for a in sys.argv[2:] if a.isdigit()]
    if nums:
        N = int(nums[0])
    run(kind, [s31_cleanup_wait], 8793 if kind == "cr" else 8794, headless="--headed" not in sys.argv)
