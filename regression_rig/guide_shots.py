"""Screenshots for the faculty guide (guide.html), taken from the real app.

    python guide_shots.py cr

Uses the stand-in screen and camera in their "demo" look (a lecture slide and a
simple presenter picture instead of the test pattern). Writes PNGs to
../guide-img/. Retake after any change to the recorder's layout.
"""
import os, sys
from harness import run, HERE

OUT = os.path.join(os.path.dirname(HERE), "guide-img")
VTT = "WEBVTT\n\n00:00:01.000 --> 00:00:04.000\nWelcome back. Today we look at how plants make food.\n\n00:00:04.500 --> 00:00:08.000\nIt starts with sunlight, water and air.\n"


def shot(r, name, selector="main"):
    r.page.mouse.move(4, 4); r.wait(350)
    box = r.page.locator(selector).bounding_box()
    vp = r.page.viewport_size
    clip = {"x": 0, "y": max(0, box["y"] - 12), "width": vp["width"], "height": min(box["height"] + 24, vp["height"] - max(0, box["y"] - 12))}
    r.page.screenshot(path=os.path.join(OUT, name), clip=clip)
    print("shot", name, flush=True)


def guide_shots(r):
    os.makedirs(OUT, exist_ok=True)
    r.start("guide")
    r.page.set_viewport_size({"width": 1100, "height": 900})
    r.cfg(demo=True, camMode="canvas")
    r.wait(300)
    shot(r, "01-start.png")

    r.page.click("#toggleMic"); r.page.wait_for_function("!!state.heldMicStream")
    r.select_screen(1)
    if r.ui()["err"]:
        r.page.click("#errorBanner .error-banner-close")
    r.page.click("#toggleCamera"); r.page.wait_for_function("!!state.cameraStream"); r.wait(900)
    r.record(6)
    shot(r, "02-recording.png")
    r.page.click("#btnPause"); r.wait(500)
    shot(r, "03-paused.png")
    r.page.click("#btnPause"); r.wait(5000)

    # review screen
    r.page.click("#btnStopReview")
    r.page.wait_for_function("document.getElementById('reviewPane').classList.contains('visible') && document.getElementById('reviewVideo').readyState >= 1", timeout=60000)
    r.ev("""() => new Promise(res => { const v = document.getElementById('reviewVideo'); v.onseeked = () => res(); v.currentTime = 7; setTimeout(res, 4000); })""")
    r.wait(2500)   # let the player's own loading spinner clear before the picture is taken
    shot(r, "04-review.png")
    path = r.stop_save("lecture.webm", button="#reviewPane .btn-save-as-is")

    # interrupted recording -> banner on reopening
    r.select_screen(1); r.record(8)
    r.kill_tab(); r.wait(900)
    r.page.set_viewport_size({"width": 1100, "height": 900}); r.wait(300)
    shot(r, "05-recovery.png")
    r.page.click("#recoveryBanner button.btn-stop"); r.wait(600)

    # caption editor with a saved video and two captions
    with open(os.path.join(r.out, "lecture.vtt"), "w", newline="\n", encoding="utf-8") as f:
        f.write(VTT)
    r.page.click("#btnCaptionEditor"); r.wait(400)
    r.page.set_input_files("#captionVideoInput", path)
    r.page.wait_for_function("document.getElementById('captionVideo').readyState >= 1", timeout=30000); r.wait(400)
    r.page.set_input_files("#captionImportInput", os.path.join(r.out, "lecture.vtt")); r.wait(700)
    r.ev("""() => new Promise(res => { const v = document.getElementById('captionVideo'); v.onseeked = () => res(); v.currentTime = 2; setTimeout(res, 4000); })""")
    r.wait(600)
    shot(r, "06-captions.png")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "cr", [guide_shots], 8795)
