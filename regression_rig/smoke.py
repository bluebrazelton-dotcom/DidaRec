import json, sys
from harness import run, summarize


def smoke(r):
    r.start()
    u = r.ui()
    print("load ui:", json.dumps(u)[:600])
    print("gum/gdm calls on load:", r.ev("[__dr.log.gum.length, __dr.log.gdm.length]"))
    print("ua:", r.ev("navigator.userAgent"))
    r.page.click("#toggleMic")
    r.wait(1500)
    r.select_screen(1)
    print("after select:", json.dumps(r.ui())[:400])
    print("preview:", r.ev("__dr.readPreview()"))
    r.record(6)
    print("recording ui:", json.dumps(r.ui())[:300])
    path = r.stop_save("smoke.webm")
    print("saved:", path, "ui:", json.dumps(r.ui())[:300])
    pr = r.probe("smoke.webm", step=0.5)
    print("probe:", summarize(pr))
    print("audio:", r.audio("smoke.webm"))
    print("console:", r.console[-8:])


if __name__ == "__main__":
    kind = sys.argv[1]
    run(kind, [smoke], 8791 if kind == "cr" else 8792)
