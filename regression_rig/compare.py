"""Compare the current run against a saved baseline: python compare.py results_2026-10-04 [cr|ff]
Run merge.py first. Prints every item whose status changed, and anything not passing now."""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
base = json.load(open(os.path.join(HERE, sys.argv[1], "merged.json"), encoding="utf-8"))
cur = json.load(open(os.path.join(HERE, "merged.json"), encoding="utf-8"))
kinds = [sys.argv[2]] if len(sys.argv) > 2 else ["cr", "ff"]


def st(d, k, b):
    v = (d.get(k) or {}).get(b)
    return v["status"] if v else "-"


for b in kinds:
    changed, regress, missing, notpass = [], [], [], []
    for k in sorted(set(base) | set(cur)):
        if k.startswith("ERR:"):
            if st(cur, k, b) != "-":
                notpass.append((k, st(cur, k, b), cur[k][b]["evidence"][:400]))
            continue
        a, c = st(base, k, b), st(cur, k, b)
        if a != c:
            (missing if c == "-" else changed).append((k, a, c))
            if a == "PASS" and c not in ("PASS", "-"):
                regress.append(k)
        if c in ("FAIL", "ERROR"):
            notpass.append((k, c, cur[k][b]["evidence"][:400]))
    n_pass = sum(1 for k in cur if st(cur, k, b) == "PASS")
    print("== %s: %d PASS now" % (b, n_pass))
    print("  changed:", [(k, a + "->" + c) for k, a, c in changed] or "none")
    print("  REGRESSIONS (was PASS, now not):", regress or "none")
    print("  not run this time:", [k for k, _, _ in missing] or "none")
    for k, c, e in notpass:
        print("  %s %s: %s" % (k, c, e.encode("ascii", "replace").decode()))
