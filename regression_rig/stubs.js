// Injected before the app's own script on every page load (Playwright init script).
// Stand-ins for the three things automation can't click: the screen picker,
// the native save dialog, and permission denial. Everything else is the real app.
(() => {
  if (window.__dr) return;
  const dr = window.__dr = {
    cfg: { screenMode: 'ok', screenId: 1, screenW: 1280, screenH: 720, screenAudio: false, gumMode: 'ok', saveMode: 'ok' },
    log: { gum: [], gdm: [], save: [] },
    handles: [],
    streams: [],
    saveDone: 0,
  };
  try {
    const saved = sessionStorage.getItem('__dr_cfg');
    if (saved) Object.assign(dr.cfg, JSON.parse(saved));
  } catch (e) {}

  // Worker-driven tick so the stand-in sources keep animating when the tab is
  // hidden (a real screen capture isn't throttled by tab visibility either).
  const ticks = new Map(); let tickSeq = 0, tickWorker = null;
  function onTick(fn) {
    if (!tickWorker) {
      try {
        const url = URL.createObjectURL(new Blob(['setInterval(()=>postMessage(0),33)'], { type: 'text/javascript' }));
        tickWorker = new Worker(url);
        tickWorker.onmessage = () => { for (const f of ticks.values()) { try { f(); } catch (e) {} } };
      } catch (e) {
        tickWorker = { fallback: setInterval(() => { for (const f of ticks.values()) f(); }, 33) };
      }
    }
    const k = ++tickSeq; ticks.set(k, fn); return k;
  }
  function offTick(k) { ticks.delete(k); }

  const BITS = 16, COLS = 40;
  const COLORS = ['#203050', '#205030', '#503020', '#402050'];

  function makeScreen(cfg) {
    const c = document.createElement('canvas');
    c.width = cfg.screenW; c.height = cfg.screenH;
    const g = c.getContext('2d');
    const t0 = performance.now();
    const id = cfg.screenId;
    function draw() {
      const ds = Math.floor((performance.now() - t0) / 100);
      g.fillStyle = COLORS[id % 4]; g.fillRect(0, 0, c.width, c.height);
      const bw = c.width / COLS, bh = c.height / 15;
      for (let i = 0; i < BITS; i++) { g.fillStyle = ((ds >> (BITS - 1 - i)) & 1) ? '#fff' : '#000'; g.fillRect(i * bw, 0, bw + 1, bh); }
      for (let i = 0; i < 4; i++) { g.fillStyle = ((id >> (3 - i)) & 1) ? '#fff' : '#000'; g.fillRect((17 + i) * bw, 0, bw + 1, bh); }
      g.fillStyle = '#fff'; g.fillRect(22 * bw, 0, bw + 1, bh);
      g.fillStyle = '#000'; g.fillRect(23 * bw, 0, bw + 1, bh);
      g.fillStyle = '#fff'; g.font = Math.round(c.height / 8) + 'px sans-serif';
      g.fillText('SCREEN ' + id + '  t=' + (ds / 10).toFixed(1), c.width * 0.08, c.height * 0.5);
      const x = (ds * 13) % Math.max(1, c.width - 60);
      g.fillStyle = '#ffcc00'; g.fillRect(x, c.height * 0.7, 60, 40);
    }
    const baseDraw = draw;
    const drawAll = () => {
      baseDraw();
      if (cfg.noise) {
        const count = cfg.noise === true ? 400 : (cfg.noise | 0);
        for (let i = 0; i < count; i++) {
          g.fillStyle = 'rgb(' + ((Math.random() * 256) | 0) + ',' + ((Math.random() * 256) | 0) + ',' + ((Math.random() * 256) | 0) + ')';
          g.fillRect(Math.random() * c.width, c.height * 0.15 + Math.random() * c.height * 0.5, 40, 40);
        }
      }
    };
    drawAll();
    const iv = onTick(drawAll);
    const stream = c.captureStream(30);
    let actx = null;
    if (cfg.screenAudio) {
      actx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = actx.createOscillator(); osc.frequency.value = 660;
      const gain = actx.createGain(); gain.gain.value = 0.2;
      const dest = actx.createMediaStreamDestination();
      osc.connect(gain); gain.connect(dest); osc.start();
      for (const t of dest.stream.getAudioTracks()) stream.addTrack(t);
    }
    const vt = stream.getVideoTracks()[0];
    const watch = setInterval(() => {
      if (vt.readyState === 'ended') { offTick(iv); clearInterval(watch); if (actx) actx.close().catch(() => {}); }
    }, 500);
    stream.__drId = id;
    dr.streams.push(stream);
    return stream;
  }

  // Asymmetric stand-in camera: left half red, right half green, centred
  // magenta disc — lets mirror / crop / stretch be measured from pixels.
  function makeCamera() {
    const c = document.createElement('canvas'); c.width = 640; c.height = 480;
    const g = c.getContext('2d');
    let n = 0;
    const draw = () => {
      n++;
      g.fillStyle = 'rgb(200,0,0)'; g.fillRect(0, 0, 320, 480);
      g.fillStyle = 'rgb(0,160,0)'; g.fillRect(320, 0, 320, 480);
      g.fillStyle = 'rgb(255,0,255)'; g.beginPath(); g.arc(320, 240, 100, 0, Math.PI * 2); g.fill();
      g.fillStyle = (n % 30 < 15) ? '#fff' : '#ddd'; g.fillRect(20, 20, 30, 30);
    };
    draw();
    const iv = onTick(draw);
    const stream = c.captureStream(30);
    const vt = stream.getVideoTracks()[0];
    const watch = setInterval(() => { if (vt.readyState === 'ended') { offTick(iv); clearInterval(watch); } }, 500);
    return stream;
  }

  const md = navigator.mediaDevices;
  if (md) {
    const realGUM = md.getUserMedia ? md.getUserMedia.bind(md) : null;
    const realGDM = md.getDisplayMedia ? md.getDisplayMedia.bind(md) : null;
    md.getUserMedia = async (c) => {
      dr.log.gum.push({ t: Date.now(), c: JSON.stringify(c), mode: dr.cfg.gumMode });
      if (dr.cfg.gumMode === 'deny') throw new DOMException('Permission denied', 'NotAllowedError');
      if (dr.cfg.camMode === 'canvas' && c && c.video && !c.audio) return makeCamera();
      return realGUM(c);
    };
    md.getDisplayMedia = async (c) => {
      dr.log.gdm.push({ t: Date.now(), c: JSON.stringify(c), mode: dr.cfg.screenMode });
      if (dr.cfg.screenMode === 'cancel') throw new DOMException('Permission denied', 'NotAllowedError');
      if (dr.cfg.screenMode === 'fail') throw new DOMException('Could not start video source', 'NotReadableError');
      if (dr.cfg.screenMode === 'real') return realGDM(c);
      return makeScreen(dr.cfg);
    };
  }

  if ('showSaveFilePicker' in window) {
    window.showSaveFilePicker = async (opts) => {
      const name = (opts && opts.suggestedName) || 'unnamed';
      dr.log.save.push({ t: Date.now(), name, mode: dr.cfg.saveMode });
      // Real Chrome refuses to open a file picker unless the page is handling a
      // recent user gesture; mirror that so gesture-less save paths show up.
      if (dr.cfg.activation !== 'off' && navigator.userActivation && !navigator.userActivation.isActive) {
        dr.log.save[dr.log.save.length - 1].blocked = true;
        throw new DOMException("Failed to execute 'showSaveFilePicker' on 'Window': Must be handling a user gesture to show a file picker.", 'SecurityError');
      }
      if (dr.cfg.saveDelay) await new Promise((r) => setTimeout(r, dr.cfg.saveDelay));
      if (dr.cfg.saveMode === 'cancel') throw new DOMException('The user aborted a request.', 'AbortError');
      const root = await navigator.storage.getDirectory();
      const h = await root.getFileHandle(Date.now() + '_' + dr.log.save.length + '_' + name, { create: true });
      const origCW = h.createWritable.bind(h);
      h.createWritable = async (...a) => {
        const w = await origCW(...a);
        const origClose = w.close.bind(w);
        w.close = async () => { await origClose(); dr.saveDone++; };
        return w;
      };
      dr.handles.push(h);
      return h;
    };
  }

  dr.setCfg = (o) => { Object.assign(dr.cfg, o); try { sessionStorage.setItem('__dr_cfg', JSON.stringify(dr.cfg)); } catch (e) {} };

  // Push the most recent stand-in save to the test server so it lands on disk.
  dr.exportLast = async (tag) => {
    const h = dr.handles[dr.handles.length - 1];
    if (!h) return { ok: false, why: 'no handle' };
    const f = await h.getFile();
    const r = await fetch('/out/' + tag, { method: 'PUT', body: f });
    return { ok: r.ok, size: f.size };
  };

  function lum(d) { return 0.299 * d[0] + 0.587 * d[1] + 0.114 * d[2]; }
  function decode(g, W, H) {
    const bw = W / COLS, y = H / 30;
    const at = (i) => lum(g.getImageData(Math.floor((i + 0.5) * bw), Math.floor(y), 1, 1).data);
    const white = at(22), black = at(23);
    const valid = white > 150 && black < 100;
    const mid = (white + black) / 2;
    let ds = 0, id = 0;
    for (let i = 0; i < BITS; i++) ds = (ds << 1) | (at(i) > mid ? 1 : 0);
    for (let i = 0; i < 4; i++) id = (id << 1) | (at(17 + i) > mid ? 1 : 0);
    return { valid, ds: valid ? ds : null, id: valid ? id : null };
  }
  function points(g, W, H, pts) {
    return (pts || []).map(([fx, fy]) => Array.from(g.getImageData(Math.min(W - 1, Math.floor(fx * W)), Math.min(H - 1, Math.floor(fy * H)), 1, 1).data).slice(0, 3));
  }

  // Bounding box of magenta pixels (the stand-in camera's disc) on a 2d context.
  function magentaBox(g, W, H) {
    const d = g.getImageData(0, 0, W, H).data;
    let x0 = W, y0 = H, x1 = -1, y1 = -1, n = 0;
    for (let y = 0; y < H; y += 2) for (let x = 0; x < W; x += 2) {
      const i = (y * W + x) * 4;
      if (d[i] > 180 && d[i + 1] < 90 && d[i + 2] > 180) { n++; if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
    }
    return n ? { x0, y0, x1, y1, w: x1 - x0, h: y1 - y0, n } : null;
  }
  dr.previewMagenta = () => {
    const src = document.getElementById('previewCanvas');
    const c = document.createElement('canvas'); c.width = src.width; c.height = src.height;
    const g = c.getContext('2d', { willReadFrequently: true });
    g.drawImage(src, 0, 0);
    return magentaBox(g, c.width, c.height);
  };

  // Read the app's live preview canvas.
  dr.readPreview = (pts) => {
    const src = document.getElementById('previewCanvas');
    if (!src || !src.width) return { valid: false, w: 0, h: 0 };
    const c = document.createElement('canvas'); c.width = src.width; c.height = src.height;
    const g = c.getContext('2d', { willReadFrequently: true });
    g.drawImage(src, 0, 0);
    const out = decode(g, c.width, c.height);
    out.w = c.width; out.h = c.height; out.pts = points(g, c.width, c.height, pts);
    return out;
  };

  // Load a saved file and look inside it: duration, seekability, and the
  // barcode (which fake screen, at what moment) at a list of playback times.
  dr.probe = async (url, opts) => {
    opts = opts || {};
    const blob = await (await fetch(url)).blob();
    const v = document.createElement('video');
    v.muted = true; v.preload = 'auto';
    v.src = URL.createObjectURL(blob);
    await new Promise((res, rej) => {
      v.onloadedmetadata = res;
      v.onerror = () => rej(new Error('video error: ' + (v.error && (v.error.message || v.error.code))));
      setTimeout(() => rej(new Error('metadata timeout')), 20000);
    });
    const out = { size: blob.size, duration: v.duration, w: v.videoWidth, h: v.videoHeight, samples: [] };
    out.seekableEnd = v.seekable.length ? v.seekable.end(v.seekable.length - 1) : null;
    let times = opts.times;
    if (!times) {
      times = [];
      const step = opts.step || 1;
      if (isFinite(v.duration)) for (let t = 0.2; t < v.duration - 0.1; t += step) times.push(Math.round(t * 100) / 100);
    }
    const c = document.createElement('canvas'); c.width = v.videoWidth || 2; c.height = v.videoHeight || 2;
    const g = c.getContext('2d', { willReadFrequently: true });
    for (const t of times) {
      const t0 = performance.now();
      let seeked = true;
      await new Promise((res) => {
        const to = setTimeout(() => { seeked = false; res(); }, 8000);
        v.onseeked = () => { clearTimeout(to); res(); };
        v.currentTime = t;
      });
      await new Promise((r) => setTimeout(r, 40));
      g.drawImage(v, 0, 0);
      const s = decode(g, c.width, c.height);
      s.t = t; s.at = v.currentTime; s.seekMs = Math.round(performance.now() - t0); s.seeked = seeked;
      s.pts = points(g, c.width, c.height, opts.points);
      out.samples.push(s);
    }
    URL.revokeObjectURL(v.src);
    return out;
  };

  dr.audioInfo = async (url) => {
    const buf = await (await fetch(url)).arrayBuffer();
    const ac = new (window.AudioContext || window.webkitAudioContext)();
    try {
      const ab = await ac.decodeAudioData(buf);
      const d = ab.getChannelData(0);
      let sum = 0; for (let i = 0; i < d.length; i += 7) sum += d[i] * d[i];
      const per = [];
      const sr = ab.sampleRate;
      for (let s = 0; s + sr <= d.length; s += sr) {
        let q = 0; for (let i = s; i < s + sr; i += 7) q += d[i] * d[i];
        per.push(Math.round(Math.sqrt(q / (sr / 7)) * 10000) / 10000);
      }
      return { has: true, duration: ab.duration, channels: ab.numberOfChannels, rms: Math.sqrt(sum / (d.length / 7)), per };
    } catch (e) {
      return { has: false, err: String(e && e.message || e) };
    } finally { ac.close().catch(() => {}); }
  };
})();
