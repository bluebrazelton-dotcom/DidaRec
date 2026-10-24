"""Screenshots for the guide's chapter-marks section (v1.41): the Mark chapter
button while recording, and the offer box after a save.

    python chapter_shot.py cr
"""
import os, sys
from harness import run, HERE

OUT = os.path.join(os.path.dirname(HERE), "guide-img")


def chapter_shots(r):
    os.makedirs(OUT, exist_ok=True)
    r.start("chapshot")
    r.page.set_viewport_size({"width": 1280, "height": 1000})
    r.cfg(demo=True, camMode="canvas", screenAudio=True)
    r.page.click("#toggleMic"); r.page.wait_for_function("!!state.heldMicStream")
    r.page.click("#toggleCamera"); r.wait(600)
    r.select_screen(1)
    if r.ui()["err"]:
        r.page.click("#errorBanner .error-banner-close")
    r.record(4)
    r.page.click("#btnMarkChapter"); r.wait(900)
    r.page.mouse.move(4, 4); r.wait(300)
    box = r.page.locator("#controlsBar").bounding_box()
    r.page.screenshot(path=os.path.join(OUT, "08-mark-chapter.png"),
                      clip={"x": 0, "y": max(0, box["y"] - 70), "width": 1280, "height": box["height"] + 110})
    print("shot 08-mark-chapter.png", flush=True)
    r.wait(2500)
    r.page.keyboard.press("m"); r.wait(2500)
    r.page.click("#btnStop")
    r.page.wait_for_function("document.getElementById('chapterOffer').classList.contains('visible')", timeout=60000)
    r.wait(600)
    r.page.mouse.move(4, 4); r.wait(300)
    ob = r.page.locator("#chapterOffer").bounding_box()
    r.page.screenshot(path=os.path.join(OUT, "09-chapter-offer.png"),
                      clip={"x": max(0, ob["x"] - 12), "y": max(0, ob["y"] - 12), "width": min(1280, ob["width"] + 24), "height": ob["height"] + 24})
    print("shot 09-chapter-offer.png", flush=True)


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "cr", [chapter_shots], 8796)
