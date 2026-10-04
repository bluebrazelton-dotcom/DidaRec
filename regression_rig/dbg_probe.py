"""Print (file time -> content time) for saved files: python dbg_probe.py <cr|ff> <file> [file...]"""
import sys
from harness import Rig

kind = sys.argv[1]
r = Rig(kind, 8801 if kind == "cr" else 8802)
try:
    r.launch()
    for tag in sys.argv[2:]:
        pr = r.probe(tag, step=0.2)
        ds = [(s["t"], s["ds"]) for s in pr["samples"]]
        print(tag, "duration", pr["duration"], "size", pr["size"], "n", len(ds))
        print("  first", ds[:4], "last", ds[-4:])
        v = [(t, d) for t, d in ds if d is not None]
        if len(v) > 1:
            print("  content span %.1fs over file span %.1fs" % ((v[-1][1] - v[0][1]) / 10.0, v[-1][0] - v[0][0]))
            jumps = [(a[0], b[1] - a[1]) for a, b in zip(v, v[1:]) if b[1] - a[1] > 4]
            print("  jumps (file t, content tenths):", jumps)
finally:
    r.shutdown()
