"""Merge all results_<browser>*.json into one table. python merge.py [--full]"""
import glob, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load(kind):
    out = {}
    files = sorted(glob.glob(os.path.join(HERE, "results_%s*.json" % kind)), key=os.path.getmtime)
    for f in files:
        if "dbg" in os.path.basename(f):
            continue
        for k, v in json.load(open(f, encoding="utf-8")).items():
            if k not in out or v["at"] >= out[k]["at"]:
                out[k] = v
    return out


def key(k):
    m = re.match(r"(\d+)\.(\d+)(.*)", k)
    return (int(m.group(1)), int(m.group(2)), m.group(3)) if m else (999, 0, k)


cr, ff = load("cr"), load("ff")
keys = sorted(set(cr) | set(ff), key=key)
merged = {k: {"cr": cr.get(k), "ff": ff.get(k)} for k in keys}
with open(os.path.join(HERE, "merged.json"), "w", encoding="utf-8", newline="\n") as f:
    json.dump(merged, f, indent=1, ensure_ascii=False)
full = "--full" in sys.argv
counts = {}
for k in keys:
    a = cr.get(k, {}).get("status", "-"); b = ff.get(k, {}).get("status", "-")
    counts[a] = counts.get(a, 0) + 1; counts[b] = counts.get(b, 0) + 1
    if full or a not in ("PASS", "-") or b not in ("PASS", "-"):
        print("%-7s cr=%-5s ff=%-5s" % (k, a, b))
        if a not in ("PASS", "-"):
            print("    cr:", cr[k]["evidence"][:600].encode("ascii", "replace").decode())
        if b not in ("PASS", "-"):
            print("    ff:", ff[k]["evidence"][:600].encode("ascii", "replace").decode())
print("items:", len(keys), "counts:", counts)
