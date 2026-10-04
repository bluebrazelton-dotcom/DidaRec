"""Scratch copy of the app as last committed (git HEAD), for A/B runs against the working copy.
Point the rig at it with DIDAREC_APP=<this folder>\\app_head."""
import os, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
repo = os.path.dirname(HERE)
dst_dir = os.path.join(HERE, "app_head")
os.makedirs(dst_dir, exist_ok=True)
data = subprocess.run(["git", "-C", repo, "show", "HEAD:index.html"], capture_output=True, check=True).stdout
with open(os.path.join(dst_dir, "index.html"), "wb") as f:
    f.write(data)
print("written", os.path.join(dst_dir, "index.html"), len(data), "bytes;",
      "opaque-canvas fix present:", b"alpha: false" in data, "| first-frame fix present:", b"drawOneFrame();                   // paint now" in data)
