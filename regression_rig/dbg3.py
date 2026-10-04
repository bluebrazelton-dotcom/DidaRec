"""Chrome video-only recording: what is actually inside the stored clusters?  python dbg3.py <cr|ff> [mic]"""
import json, sys
from harness import run

DUMP = """async () => {
  const parts = []; let bytes = 0; const chunkSizes = [];
  await forEachSessionChunk(state.sessionId, (data) => { parts.push(new Uint8Array(data.slice(0))); bytes += data.byteLength; chunkSizes.push(data.byteLength); });
  const buf = new Uint8Array(bytes); let o = 0; for (const p of parts) { buf.set(p, o); o += p.length; }
  const sc = createWebmStreamScanner(); sc.push(buf); const ok = sc.finish(); const res = sc.result();
  const view = new DataView(buf.buffer);
  const out = [];
  for (const c of res.clusters) {
    const ids = {}; let n = 0, minRel = null, maxRel = null, firstNonSimple = null;
    const cId = ebmlReadId(view, c.start); const cSize = ebmlReadSize(view, c.start + cId.length);
    let pos = c.start + cId.length + cSize.length; let stoppedAt = null;
    while (pos < c.end) {
      const id = ebmlReadId(view, pos); if (!id) { stoppedAt = 'badid@' + (pos - c.start); break; }
      const size = ebmlReadSize(view, pos + id.length); if (!size || size.isUnknown) { stoppedAt = 'badsize@' + (pos - c.start) + ' id=' + id.value.toString(16); break; }
      const ds = pos + id.length + size.length, de = ds + size.value;
      const key = id.value.toString(16); ids[key] = (ids[key] || 0) + 1;
      if (id.value === 0xA0 && !window.__bgDump) {
        const kids = []; let p = ds;
        while (p < de && kids.length < 8) { const k = ebmlReadId(view, p); if (!k) break; const s = ebmlReadSize(view, p + k.length); if (!s) break; kids.push([k.value.toString(16), s.value]); p += k.length + s.length + s.value; }
        window.__bgDump = kids;
      }
      if (id.value === EBML_IDS.SIMPLEBLOCK) { const tn = ebmlReadSize(view, ds); const rel = view.getInt16(ds + tn.length, false); n++; if (minRel === null || rel < minRel) minRel = rel; if (maxRel === null || rel > maxRel) maxRel = rel; }
      if (de > c.end) { stoppedAt = 'overrun@' + (pos - c.start) + ' id=' + key + ' need=' + (de - c.end); break; }
      pos = de;
    }
    out.push({ ts: c.timestamp, bytes: c.end - c.start, unknownSize: cSize.isUnknown, ids, simpleBlocks: n, minRel, maxRel, stoppedAt });
  }
  return { ok, bytes, chunkSizes, lastMax: res.lastClusterMaxBlockTime, maxTs: res.maxClusterTs, clusters: out, firstBlockGroupChildren: window.__bgDump || null, ctxAlpha: (ctx.getContextAttributes ? ctx.getContextAttributes().alpha : null), keyframes: res.clusters.map(c => c.keyframe) };
}"""


def dump(r):
    mic = "mic" in sys.argv
    print("gpu/canvas info:", r.ev("(() => { const c = document.createElement('canvas'); const gl = c.getContext('webgl'); const e = gl && gl.getExtension('WEBGL_debug_renderer_info'); return [navigator.userAgent.slice(-60), e ? gl.getParameter(e.UNMASKED_RENDERER_WEBGL) : 'no webgl']; })()") if False else "")
    r.start()
    print("renderer:", r.ev("(() => { const c = document.createElement('canvas'); const gl = c.getContext('webgl'); const e = gl && gl.getExtension('WEBGL_debug_renderer_info'); return [navigator.userAgent.slice(-70), e ? gl.getParameter(e.UNMASKED_RENDERER_WEBGL) : 'no webgl']; })()"))
    if mic:
        r.page.click("#toggleMic"); r.page.wait_for_function("!!state.heldMicStream")
    r.select_screen(1)
    r.record(8)
    u = r.ui()
    wall = r.ev("(Date.now() - state.startTime) / 1000")
    if r.kind == "cr":
        r.cfg(saveMode="cancel"); r.page.click("#btnStop"); r.wait(2500)
    else:
        with r.page.expect_download() as di:
            r.page.click("#btnStop")
        r.wait(1500)
    d = r.ev(DUMP)
    print("mic=%s wall at stop=%.1fs timer=%s" % (mic, wall, u["timer"]))
    print("ok=%s bytes=%d chunkSizes=%s lastMax=%s maxTs=%s" % (d["ok"], d["bytes"], d["chunkSizes"], d["lastMax"], d["maxTs"]))
    print("first BlockGroup children [id, size]:", d["firstBlockGroupChildren"], "| canvas ctx alpha:", d["ctxAlpha"], "| cluster keyframe flags:", d["keyframes"])
    for c in d["clusters"][:4]:
        print("  ", json.dumps(c))


if __name__ == "__main__":
    kind = sys.argv[1]
    run(kind, [dump], 8805 if kind == "cr" else 8806, headless="--headed" not in sys.argv)
