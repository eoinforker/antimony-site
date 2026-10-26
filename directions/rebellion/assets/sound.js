// Procedural sound for the plaza: rain, gutters, the can, the screen, the drone, sirens, thunder, the swell.
// Nothing is sampled; every sound is synthesised here. Quiet, filtered, spacious.

export class Sound {
  constructor() { this.on = false; this.ctx = null; this.spraying = 0; }

  start() {
    if (this.ctx) { this.ctx.resume(); return; }
    const C = this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    const sr = C.sampleRate;
    this.master = C.createGain(); this.master.gain.value = 0;
    const comp = C.createDynamicsCompressor(); comp.threshold.value = -20; comp.ratio.value = 3; comp.attack.value = 0.01; comp.release.value = 0.3;
    this.master.connect(comp).connect(C.destination);
    // a long, dark space
    this.verb = C.createConvolver();
    const ir = C.createBuffer(2, sr * 4, sr);
    for (let ch = 0; ch < 2; ch++) { const d = ir.getChannelData(ch); for (let i = 0; i < d.length; i++) { const t = i / sr; d[i] = (Math.random() * 2 - 1) * Math.pow(1 - t / 4, 3) * Math.exp(-t * 0.9); } }
    this.verb.buffer = ir;
    const vlp = C.createBiquadFilter(); vlp.type = 'lowpass'; vlp.frequency.value = 2600;
    this.wet = C.createGain(); this.wet.gain.value = 0.5;
    this.verb.connect(vlp).connect(this.wet).connect(this.master);

    // noise beds
    const mk = (fn, secs = 4) => { const b = C.createBuffer(2, sr * secs, sr); for (let ch = 0; ch < 2; ch++) fn(b.getChannelData(ch)); return b; };
    this.white = mk(d => { for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1; });
    this.pink = mk(d => { let b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0; for (let i = 0; i < d.length; i++) { const w = Math.random() * 2 - 1; b0 = 0.99886 * b0 + w * 0.0555179; b1 = 0.99332 * b1 + w * 0.0750759; b2 = 0.969 * b2 + w * 0.153852; b3 = 0.8665 * b3 + w * 0.3104856; b4 = 0.55 * b4 + w * 0.5329522; b5 = -0.7616 * b5 - w * 0.016898; d[i] = (b0 + b1 + b2 + b3 + b4 + b5 + b6 + w * 0.5362) * 0.11; b6 = w * 0.115926; } });
    this.brown = mk(d => { let l = 0; for (let i = 0; i < d.length; i++) { l = (l + 0.02 * (Math.random() * 2 - 1)) / 1.02; d[i] = l * 3.5; } });
    this.crackleBuf = mk(d => { let h = 0, c = 0; for (let i = 0; i < d.length; i++) { if (c-- <= 0) { c = 8 + Math.random() * 60; h = Math.random() < 0.15 ? (Math.random() * 2 - 1) : 0; } d[i] = h * (Math.random() < 0.6 ? 1 : -0.5); } }, 2);

    const loop = (buf, rate = 1) => { const s = C.createBufferSource(); s.buffer = buf; s.loop = true; s.playbackRate.value = rate; s.start(0, Math.random() * 2); return s; };
    const filt = (type, f, q = 0.7) => { const b = C.createBiquadFilter(); b.type = type; b.frequency.value = f; b.Q.value = q; return b; };
    const gain = v => { const g = C.createGain(); g.gain.value = v; return g; };
    this.filt = filt; this.gain = gain;

    // heavy rain: a body, a hiss and a near patter
    loop(this.pink).connect(filt('lowpass', 1500)).connect(filt('highpass', 160)).connect(gain(0.5)).connect(this.master);
    loop(this.white, 0.9).connect(filt('highpass', 2600)).connect(filt('lowpass', 8000)).connect(gain(0.045)).connect(this.master);
    const near = loop(this.pink, 1.3); near.connect(filt('bandpass', 3200, 0.6)).connect(gain(0.07)).connect(this.verb);
    // gutters: a hollow running throat, slowly moving
    const gut = filt('bandpass', 520, 2.2), gutG = gain(0.09), gp = C.createStereoPanner(); gp.pan.value = -0.55;
    loop(this.brown, 1.1).connect(gut).connect(gutG).connect(gp).connect(this.master); gutG.connect(this.verb);
    const lfo = C.createOscillator(); lfo.frequency.value = 0.17; const lg = gain(110); lfo.connect(lg).connect(gut.frequency); lfo.start();
    // screen hum: mains at fifty hertz and its harmonics, with a thin buzz
    this.hum = gain(0);
    [[50, 0.5], [100, 0.32], [150, 0.14], [250, 0.05]].forEach(([f, a]) => { const o = C.createOscillator(); o.frequency.value = f; const g = gain(a); o.connect(g).connect(this.hum); o.start(); });
    const bz = C.createOscillator(); bz.type = 'sawtooth'; bz.frequency.value = 100; bz.connect(filt('bandpass', 1400, 5)).connect(gain(0.05)).connect(this.hum); bz.start();
    this.humPan = C.createStereoPanner();
    this.hum.connect(filt('lowpass', 1100)).connect(this.humPan).connect(this.master);
    // the drone: two beating rotor tones and a breathy wash, panned and doppler shifted
    this.droneG = gain(0); this.dronePan = C.createStereoPanner();
    const amNode = gain(0.6); amNode.connect(this.droneG);
    this.rotors = [92, 97.5, 184].map((f, i) => { const o = C.createOscillator(); o.type = i === 2 ? 'triangle' : 'sawtooth'; o.frequency.value = f; o.connect(gain(i === 2 ? 0.2 : 0.35)).connect(amNode); o.start(); return o; });
    const am = C.createOscillator(); am.frequency.value = 23; const amg = gain(0.4); am.connect(amg).connect(amNode.gain); am.start();
    loop(this.pink, 0.7).connect(filt('bandpass', 380, 1.2)).connect(gain(0.5)).connect(amNode);
    this.droneLP = filt('lowpass', 700);
    this.droneG.connect(this.droneLP).connect(this.dronePan).connect(this.master); this.dronePan.connect(this.verb);
    // the can: hiss follows the finger
    this.sprayG = gain(0);
    loop(this.white, 1).connect(filt('highpass', 2800)).connect(filt('peaking', 6800, 0.8)).connect(filt('lowpass', 11000)).connect(this.sprayG).connect(this.master);
    this.sprayG.connect(this.verb);

    this.drops(); this.nextSiren = C.currentTime + 6 + Math.random() * 10;
    this.tick = setInterval(() => this.schedule(), 200);
  }

  setOn(v) {
    this.on = v;
    if (v) this.start();
    if (!this.ctx) return;
    const t = this.ctx.currentTime;
    this.master.gain.cancelScheduledValues(t);
    this.master.gain.setTargetAtTime(v ? 0.75 : 0, t, v ? 0.6 : 0.15);
    if (!v) setTimeout(() => { if (!this.on && this.ctx) this.ctx.suspend(); }, 900); else this.ctx.resume();
  }
  pause(p) { if (!this.ctx) return; if (p) this.ctx.suspend(); else if (this.on) this.ctx.resume(); }

  // single drops on near surfaces, scheduled ahead
  drops() {
    const C = this.ctx;
    this.dropAt = C.currentTime;
  }
  schedule() {
    const C = this.ctx; if (!C || C.state !== 'running') return;
    const ahead = C.currentTime + 0.4;
    while (this.dropAt < ahead) {
      this.dropAt += 0.012 + Math.random() * 0.05;
      const s = C.createBufferSource(); s.buffer = this.white;
      const f = this.filt('bandpass', 1400 + Math.random() * 4200, 3 + Math.random() * 6);
      const g = this.gain(0), p = C.createStereoPanner(); p.pan.value = Math.random() * 2 - 1;
      const a = 0.012 + Math.random() * Math.random() * 0.05;
      g.gain.setValueAtTime(0, this.dropAt); g.gain.linearRampToValueAtTime(a, this.dropAt + 0.002); g.gain.exponentialRampToValueAtTime(0.0001, this.dropAt + 0.03 + Math.random() * 0.04);
      s.connect(f).connect(g).connect(p).connect(this.master);
      s.start(this.dropAt, Math.random() * 3, 0.1);
      // a gutter trickle now and then
      if (Math.random() < 0.06) {
        const o = C.createOscillator(); o.frequency.setValueAtTime(600 + Math.random() * 900, this.dropAt); o.frequency.exponentialRampToValueAtTime(300 + Math.random() * 300, this.dropAt + 0.06);
        const og = this.gain(0); og.gain.setValueAtTime(0.0001, this.dropAt); og.gain.exponentialRampToValueAtTime(0.012, this.dropAt + 0.005); og.gain.exponentialRampToValueAtTime(0.0001, this.dropAt + 0.09);
        o.connect(og).connect(this.verb); o.start(this.dropAt); o.stop(this.dropAt + 0.12);
      }
    }
    if (C.currentTime > this.nextSiren) { this.siren(); this.nextSiren = C.currentTime + 30 + Math.random() * 40; }
  }

  siren() {
    const C = this.ctx, t = C.currentTime, dur = 9 + Math.random() * 5;
    const o = C.createOscillator(); o.type = 'triangle';
    const hi = 930 + Math.random() * 40, lo = hi * 0.75;
    for (let k = 0, tt = t; tt < t + dur; k++, tt += 0.62) o.frequency.setValueAtTime(k % 2 ? lo : hi, tt);
    o.detune.setValueAtTime(40, t); o.detune.linearRampToValueAtTime(-60, t + dur);
    const g = this.gain(0); g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(0.03, t + dur * 0.4); g.gain.linearRampToValueAtTime(0, t + dur);
    const p = C.createStereoPanner(); p.pan.setValueAtTime(Math.random() < 0.5 ? -0.8 : 0.8, t); p.pan.linearRampToValueAtTime((Math.random() - 0.5) * 0.6, t + dur);
    o.connect(this.filt('lowpass', 1100)).connect(g).connect(p); p.connect(this.verb); p.connect(this.gain(0.25)).connect(this.master);
    o.start(t); o.stop(t + dur + 0.1);
  }

  thunder(delay, near) {
    const C = this.ctx; if (!C || !this.on) return;
    const t = C.currentTime + delay, len = 5 + Math.random() * 3;
    const s = C.createBufferSource(); s.buffer = this.brown; s.loop = true;
    const f = this.filt('lowpass', near ? 900 : 420); f.frequency.setValueAtTime(near ? 900 : 420, t); f.frequency.exponentialRampToValueAtTime(90, t + len);
    const g = this.gain(0);
    g.gain.setValueAtTime(0, t);
    let tt = t; const peak = near ? 0.55 : 0.3;
    g.gain.linearRampToValueAtTime(peak, t + 0.08);
    for (let i = 0; i < 6; i++) { tt += 0.3 + Math.random() * 0.7; g.gain.linearRampToValueAtTime(peak * (0.25 + Math.random() * 0.6) * (1 - i / 7), tt); }
    g.gain.linearRampToValueAtTime(0, t + len);
    s.connect(f).connect(g); g.connect(this.master); g.connect(this.verb);
    s.start(t, Math.random() * 2); s.stop(t + len + 0.2);
    if (near) { // the first tear of it
      const c = C.createBufferSource(); c.buffer = this.crackleBuf;
      const cg = this.gain(0); cg.gain.setValueAtTime(0.25, t); cg.gain.exponentialRampToValueAtTime(0.001, t + 0.9);
      c.connect(this.filt('lowpass', 2400)).connect(cg).connect(this.verb); c.start(t); c.stop(t + 1);
    }
  }

  crackle(dur = 0.4, amt = 1) {
    const C = this.ctx; if (!C || !this.on) return;
    const t = C.currentTime;
    const s = C.createBufferSource(); s.buffer = this.crackleBuf; s.playbackRate.value = 0.7 + Math.random() * 0.6;
    const g = this.gain(0); g.gain.setValueAtTime(0.07 * amt, t); g.gain.setTargetAtTime(0, t + dur * 0.6, dur * 0.3);
    s.connect(this.filt('bandpass', 2200, 0.8)).connect(g).connect(this.humPan); g.connect(this.verb);
    s.start(t, Math.random()); s.stop(t + dur + 0.3);
  }

  rattle() {
    const C = this.ctx; if (!C || !this.on) return;
    const t0 = C.currentTime;
    for (let i = 0; i < 7; i++) {
      const t = t0 + i * 0.085 + Math.random() * 0.015;
      const s = C.createBufferSource(); s.buffer = this.white;
      const g = this.gain(0); g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.06, t + 0.003); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.05);
      const p = C.createStereoPanner(); p.pan.value = 0.15 + (i % 2 ? 0.1 : -0.1);
      s.connect(this.filt('bandpass', 3000 + Math.random() * 900, 7)).connect(g).connect(p).connect(this.master);
      s.start(t, Math.random() * 3, 0.08);
      const o = C.createOscillator(); o.frequency.value = 2500 + Math.random() * 500; const og = this.gain(0);
      og.gain.setValueAtTime(0.0001, t); og.gain.exponentialRampToValueAtTime(0.012, t + 0.002); og.gain.exponentialRampToValueAtTime(0.0001, t + 0.04);
      o.connect(og).connect(p); o.start(t); o.stop(t + 0.06);
    }
  }

  spray(on, speed = 0) {
    if (!this.ctx) return;
    const t = this.ctx.currentTime;
    const v = on ? 0.12 + Math.min(0.06, speed * 0.00004) : 0;
    this.sprayG.gain.setTargetAtTime(v, t, on ? 0.03 : 0.08);
  }

  swell(up) {
    const C = this.ctx; if (!C || !this.on) return;
    const t = C.currentTime, len = up ? 9 : 5;
    const out = this.gain(0);
    out.gain.setValueAtTime(0, t); out.gain.linearRampToValueAtTime(up ? 0.5 : 0.3, t + (up ? 2.4 : 1.2)); out.gain.setTargetAtTime(0, t + (up ? 4 : 2), up ? 1.8 : 1);
    const lp = this.filt('lowpass', 240);
    const base = up ? 41.2 : 36.7;
    [1, 1.5, 2, 3].forEach((m, i) => { const o = C.createOscillator(); o.type = i ? 'sine' : 'triangle'; o.frequency.value = base * m; o.detune.value = (Math.random() - 0.5) * 8; const g = this.gain([0.6, 0.3, 0.22, 0.08][i]); o.connect(g).connect(lp); o.start(t); o.stop(t + len); });
    lp.connect(out); out.connect(this.master); out.connect(this.verb);
    // a filtered rise of air before it lands
    const n = C.createBufferSource(); n.buffer = this.pink; n.loop = true;
    const bp = this.filt('bandpass', 200, 1.4); bp.frequency.setValueAtTime(up ? 180 : 900, t); bp.frequency.exponentialRampToValueAtTime(up ? 1400 : 160, t + 2.4);
    const ng = this.gain(0); ng.gain.setValueAtTime(0, t); ng.gain.linearRampToValueAtTime(0.1, t + 2.2); ng.gain.linearRampToValueAtTime(0, t + 3);
    n.connect(bp).connect(ng).connect(this.verb); n.start(t); n.stop(t + 3.2);
  }

  // per frame: the hum and the drone follow the camera
  update(s) {
    if (!this.ctx || this.ctx.state !== 'running') return;
    const t = this.ctx.currentTime;
    this.hum.gain.setTargetAtTime(0.012 + 0.03 * s.screenFacing + (s.glitch ? 0.02 : 0), t, 0.2);
    this.humPan.pan.setTargetAtTime(s.screenPan, t, 0.2);
    this.droneG.gain.setTargetAtTime(0.09 / (1 + s.droneDist * s.droneDist / 900), t, 0.2);
    this.dronePan.pan.setTargetAtTime(Math.max(-1, Math.min(1, s.dronePan)), t, 0.1);
    this.droneLP.frequency.setTargetAtTime(380 + 2400 / (1 + s.droneDist / 20), t, 0.2);
    const dop = Math.max(-80, Math.min(80, -s.droneRadial * 9));
    this.rotors.forEach(o => o.detune.setTargetAtTime(dop, t, 0.2));
  }
}
