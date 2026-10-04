"""Scratch copy of the app with ONE change: startCompositing paints a frame immediately
instead of leaving the freshly resized (black) canvas until the first clock tick.
Point the rig at it with DIDAREC_APP=<this folder>\\app_firstframe."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
src = os.path.join(os.path.dirname(HERE), "index.html")
dst_dir = os.path.join(HERE, "app_firstframe")
os.makedirs(dst_dir, exist_ok=True)
with open(src, "rb") as f:
    data = f.read()
old = b"  state.drawFrame = drawOneFrame;   // sentinel + entry point for the clock\n  startDrawClock();\n"
new = b"  state.drawFrame = drawOneFrame;   // sentinel + entry point for the clock\n  drawOneFrame();\n  startDrawClock();\n"
assert data.count(old) == 1, data.count(old)
with open(os.path.join(dst_dir, "index.html"), "wb") as f:
    f.write(data.replace(old, new))
print("written", os.path.join(dst_dir, "index.html"))
