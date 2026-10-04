"""Is the first frame of a recording (and of a second take) black?  python dbg_first.py <cr|ff>
Records a plain clip, a camera-only clip, and a crash+continue pair, then prints the first
frames of each and the frames around the seam."""
import sys
from harness import run
from part2 import mic_on, CONTINUE

PTS = [[0.5, 0.5], [0.1, 0.9], [0.56, 0.03]]


def first(r):
    tag0 = sys.argv[2] if len(sys.argv) > 2 else "x"
    r.start("first_%s" % tag0)
    mic_on(r); r.select_screen(1); r.record(5)
    r.stop_save("first_plain.webm")
    pr = r.probe("first_plain.webm", times=[0, 0.034, 0.067, 0.1, 0.2], points=PTS)
    print("plain      :", [(s["at"], s["valid"], s["pts"][0]) for s in pr["samples"]], flush=True)
    # mic off
    r.page.click("#toggleMic"); r.wait(300)
    r.select_screen(1); r.record(5); r.stop_save("first_micoff.webm")
    pr = r.probe("first_micoff.webm", times=[0, 0.034, 0.067, 0.1, 0.2], points=PTS)
    print("mic off    :", [(s["at"], s["valid"], s["pts"][0]) for s in pr["samples"]], flush=True)
    # camera-only
    r.page.click("#toggleCamera"); r.page.wait_for_function("!!state.cameraStream")
    r.page.click("#toggleScreen"); r.wait(800)
    r.record(4); r.stop_save("first_camonly.webm")
    pr = r.probe("first_camonly.webm", times=[0, 0.034, 0.067, 0.1, 0.2], points=PTS)
    print("camera-only:", [(s["at"], [sum(p) for p in s["pts"]]) for s in pr["samples"]], flush=True)
    # two takes via crash + continue
    r.start("first2_%s" % tag0)
    mic_on(r); r.select_screen(1); r.record(6)
    r.kill_tab(); r.wait(600); r.page.click(CONTINUE)
    mic_on(r); r.select_screen(2); r.record(6)
    r.stop_save("first_seam.webm")
    pr = r.probe("first_seam.webm", step=0.034, points=PTS)   # every frame of the whole file
    bad = [s["t"] for s in pr["samples"] if not s["valid"]]
    ids = [s["id"] for s in pr["samples"]]
    join = next((s["t"] for s in pr["samples"] if s["valid"] and s["id"] == 2), None)
    k = next((i for i, s in enumerate(pr["samples"]) if s["valid"] and s["id"] == 2), 0)
    around = "".join(str(i) if i else "_" for i in ids[max(0, k - 12):k + 12])
    print("seam       : %d samples every 34 ms over the whole %.1fs file; join at %.2fs; blank samples: %s | ids around the join: %s" % (len(ids), pr["duration"], join or -1, bad, around), flush=True)


if __name__ == "__main__":
    kind = sys.argv[1]
    run(kind, [first], 8815 if kind == "cr" else 8816)
