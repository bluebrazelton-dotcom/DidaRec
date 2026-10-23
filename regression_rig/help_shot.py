"""Screenshot of the in-app help panel open while recording (v1.39), for the guide and the owner's look.

    python help_shot.py cr
"""
import os, sys
from harness import run, HERE

OUT = os.path.join(os.path.dirname(HERE), "guide-img")


def help_shot(r):
    os.makedirs(OUT, exist_ok=True)
    r.start("help")
    r.page.set_viewport_size({"width": 1280, "height": 860})
    r.cfg(demo=True, camMode="canvas")
    r.page.click("#toggleMic"); r.page.wait_for_function("!!state.heldMicStream")
    r.select_screen(1)
    if r.ui()["err"]:
        r.page.click("#errorBanner .error-banner-close")
    r.record(5)
    r.page.click("#btnHelp")
    r.page.wait_for_function("document.getElementById('helpFrame').contentDocument && document.getElementById('helpFrame').contentDocument.body && document.getElementById('helpFrame').contentDocument.body.classList.contains('embedded')", timeout=15000)
    r.wait(1200)
    r.page.mouse.move(4, 4); r.wait(300)
    r.page.screenshot(path=os.path.join(OUT, "07-help-panel.png"))
    print("shot 07-help-panel.png", flush=True)


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "cr", [help_shot], 8798)
