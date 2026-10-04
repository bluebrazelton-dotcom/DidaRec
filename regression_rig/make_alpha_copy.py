"""Scratch copy of the app with ONE change: the compositor canvas context is created opaque."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
src = os.path.join(os.path.dirname(HERE), "index.html")
dst_dir = os.path.join(HERE, "app_alpha_false")
os.makedirs(dst_dir, exist_ok=True)
with open(src, "rb") as f:
    data = f.read()
old = b"const ctx = canvas.getContext('2d');"
new = b"const ctx = canvas.getContext('2d', { alpha: false });"
assert data.count(old) == 1, data.count(old)
with open(os.path.join(dst_dir, "index.html"), "wb") as f:
    f.write(data.replace(old, new))
print("written", os.path.join(dst_dir, "index.html"), len(data), "->", len(data.replace(old, new)))
