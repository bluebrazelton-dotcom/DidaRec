"""Fine-grained look at a stretch of a saved file: python dbg_seam.py <cr|ff> <file> <from_s> <to_s>
Prints, every 0.05 s, which fake screen is showing, its time code, and three pixel samples."""
import sys
from harness import Rig

kind, tag, a, b = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
r = Rig(kind, 8813 if kind == "cr" else 8814)
try:
    r.launch()
    times = [round(a + i * 0.05, 2) for i in range(int((b - a) / 0.05) + 1)]
    pr = r.probe(tag, times=times, points=[[0.5, 0.5], [0.1, 0.9], [0.56, 0.03]])
    print(tag, "duration", pr["duration"])
    run = None
    for s in pr["samples"]:
        key = (s["valid"], s["id"])
        if key != run:
            print("  t=%.2f (landed %.3f) valid=%s id=%s ds=%s pts=%s" % (s["t"], s["at"], s["valid"], s["id"], s["ds"], s["pts"]))
            run = key
    bad = [s["t"] for s in pr["samples"] if not s["valid"]]
    print("  invalid samples:", bad)
finally:
    r.shutdown()
