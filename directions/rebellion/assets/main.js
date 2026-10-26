// Antimony, Rebellion: one plaza at night, in the rain. The megacorps own the glass; the paint is ours.
import * as THREE from 'three';
import { EffectComposer } from './vendor/addons/EffectComposer.js';
import { RenderPass } from './vendor/addons/RenderPass.js';
import { UnrealBloomPass } from './vendor/addons/UnrealBloomPass.js';
import { ShaderPass } from './vendor/addons/ShaderPass.js';
import { OutputPass } from './vendor/addons/OutputPass.js';
import { Painter, spray, handWord, wordWidth, stencil, stencilShape, scribble, buff, LiveLayer, rng, canvas as mkCanvas } from './paint.js';
import { Sound } from './sound.js';

const Q = new URLSearchParams(location.search);
const FREEZE = Q.has('t') ? (+Q.get('t')) / 1000 : null;
const PHONE = matchMedia('(pointer: coarse)').matches || Math.min(innerWidth, innerHeight) < 600;
const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches;
const store = { get(k) { try { return sessionStorage.getItem(k); } catch (e) { return null; } }, set(k, v) { try { sessionStorage.setItem(k, v); } catch (e) { } } };
const KEY = 'antimony.rebellion', SKEY = 'antimony.rebellion.sound';
let INTRO = FREEZE !== null ? true : !(store.get(KEY) === '1' || REDUCED);
const INTRO_END = 7.4;

const C = { ink: '#0B0C0C', paper: '#EEEAE0', sky: '#94E6FF', cobalt: '#2448FF' };
const CORP = {
  kolvane: { col: '#EEF2FF', name: 'KOLVANE' },
  novarch: { col: '#D2DAFF', name: 'NOVARCH' },
  tessarine: { col: '#FF2D55', name: 'TESSARINE' },
  ostraven: { col: '#BFD0FF', name: 'OSTRAVEN' },
};
const WORK = {
  orbe: { name: 'Orbe', url: 'https://eoinforker.github.io/orbe-site/', file: 'assets/work/orbe.svg' },
  immiscible: { name: 'immiscible', url: 'https://immiscible.ai', file: 'assets/work/immiscible.svg' },
  idyll: { name: 'Idyll', url: 'https://idyll.day', file: 'assets/work/idyll.svg' },
};
const BREAK = {
  cav: 'M60.75 14.02L78.19 42.8L73.21 60.2L39.25 88.97L21.81 60.2L26.79 42.8Z',
  gem: 'M58.6 21.5L70.58 46.7L67.82 56.3L41.4 81.5L29.42 56.3L32.18 46.7Z',
  seam: 'M67.46 -12L68.96 -12L62.35 21.5L45.15 81.5L33.4 112L31.9 112L37.65 81.5L54.85 21.5Z',
  facet: 'M58.6 21.5L70.58 46.7L67.82 56.3L41.4 81.5Z',
};
const tile100 = () => { const p = new Path2D(); p.roundRect(0, 0, 100, 100, 22); return p; };

// ============================================================ renderer
const el = document.getElementById('scene');
const renderer = new THREE.WebGLRenderer({ canvas: el, antialias: false, powerPreference: 'high-performance', stencil: false });
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.outputColorSpace = THREE.SRGBColorSpace;
let quality = Q.has('q') ? +Q.get('q') : (PHONE ? 0.8 : 1);
const baseDPR = () => Math.min(devicePixelRatio || 1, PHONE ? 1.5 : 1.25);
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(56, innerWidth / innerHeight, 0.3, 2600);
camera.rotation.order = 'YXZ';

// ============================================================ shared uniforms
const V3 = (x = 0, y = 0, z = 0) => new THREE.Vector3(x, y, z);
const U = {
  uTime: { value: 0 }, uFlash: { value: 0 }, uFlashDir: { value: V3(0.3, 0.55, -0.78).normalize() },
  uLPos: { value: Array.from({ length: 8 }, () => V3(0, -999, 0)) }, uLCol: { value: Array.from({ length: 8 }, () => V3()) },
  uSpotPos: { value: V3(0, 40, 0) }, uSpotDir: { value: V3(0, -1, 0) }, uSpotCos: { value: Math.cos(0.075) }, uSpotI: { value: 1.3 },
  uFogCol: { value: V3(0.011, 0.014, 0.024) }, uFogDen: { value: 0.0036 },
  uEnv: { value: null }, uEnvOn: { value: 0 }, uUV: { value: 0.75 }, uDrip: { value: 1 }, uReveal: { value: 1 },
};

const COMMON = /* glsl */`
uniform float uTime; uniform float uFlash; uniform vec3 uFlashDir;
uniform vec3 uLPos[8]; uniform vec3 uLCol[8];
uniform vec3 uSpotPos; uniform vec3 uSpotDir; uniform float uSpotCos; uniform float uSpotI;
uniform vec3 uFogCol; uniform float uFogDen;
float h12(vec2 p){ vec3 p3 = fract(vec3(p.xyx) * .1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
float vnoise(vec2 p){ vec2 i=floor(p), f=fract(p); vec2 u=f*f*(3.-2.*f);
  return mix(mix(h12(i),h12(i+vec2(1,0)),u.x), mix(h12(i+vec2(0,1)),h12(i+vec2(1,1)),u.x), u.y); }
float fbm(vec2 p){ float a=.5, s=0.; for(int i=0;i<5;i++){ s+=a*vnoise(p); p=p*2.03+vec2(1.7,9.2); a*=.5; } return s; }
vec3 skyCol(vec3 d){
  float y = d.y;
  vec3 hor = vec3(0.022,0.027,0.048), zen = vec3(0.003,0.004,0.01);
  vec3 c = mix(hor, zen, smoothstep(-0.05, .55, y));
  vec2 q = d.xz/(abs(y)+.22);
  float cl = fbm(q*0.9 + vec2(uTime*0.012, uTime*0.005));
  float under = 1.-smoothstep(.05,.8,y);
  c += vec3(0.018,0.022,0.04)*smoothstep(.4,.85,cl)*under;
  float fl = uFlash * pow(max(dot(d, uFlashDir),0.), 5.);
  c += vec3(.5,.56,.78) * fl * (0.25 + cl*1.4) + vec3(.03,.035,.055)*uFlash*cl;
  return c;
}
vec3 lights(vec3 p, vec3 n){ vec3 s=vec3(0);
  for(int i=0;i<8;i++){ vec3 d=uLPos[i]-p; float l2=dot(d,d); vec3 L=d*inversesqrt(l2+1e-4);
    s += uLCol[i] * max(dot(n,L)*.75+.25,0.) * 110./(l2+110.); }
  return s; }
float spotCone(vec3 p){ vec3 d=p-uSpotPos; float c=dot(normalize(d),uSpotDir); return smoothstep(uSpotCos, uSpotCos+0.008, c); }
vec3 spot(vec3 p, vec3 n){ vec3 d=p-uSpotPos; float dist=length(d); vec3 L=d/dist;
  return vec3(.82,.9,1.)*uSpotI*spotCone(p)*max(dot(n,-L),0.)*1400./(dist*dist+60.); }
vec3 fogit(vec3 col, vec3 p){ float d=length(p-cameraPosition); float hf = exp(-max(p.y,0.)*0.014);
  float f = 1.-exp(-d*uFogDen*(0.4+hf)); return mix(col, uFogCol*(1.+uFlash*0.9), f); }
`;

const VS_WORLD = /* glsl */`
varying vec2 vUv; varying vec3 vW;
void main(){ vUv=uv; vec4 w=modelMatrix*vec4(position,1.); vW=w.xyz; gl_Position=projectionMatrix*viewMatrix*w; }`;

// ------------------------------------------------------------ the towers' glass, and paint on it
const FS_WALL = /* glsl */`
${COMMON}
uniform vec2 uSize; uniform float uSeed; uniform vec3 uN; uniform vec3 uT; uniform vec3 uTint; uniform float uLit; uniform float uKind; uniform float uPodium; uniform float uLobby; uniform vec3 uEdge;
uniform samplerCube uEnv; uniform float uEnvOn; uniform float uUV; uniform float uDrip; uniform float uReveal;
uniform sampler2D uPaint; uniform sampler2D uDripM; uniform vec4 uPR; uniform float uHasPaint; uniform vec2 uPTex;
uniform sampler2D uLive; uniform vec4 uLR; uniform float uHasLive; uniform vec2 uLTex;
varying vec2 vUv; varying vec3 vW;
vec3 envAt(vec3 R, float lod){ vec3 e = uEnvOn>0.5 ? textureLod(uEnv, R, lod).rgb : skyCol(R); return e + vec3(.45,.5,.68)*uFlash*0.22*smoothstep(-.1,.5,R.y); }
vec3 paintOver(vec3 under, vec4 P, sampler2D tex, vec2 pu, vec2 tx, vec3 N, vec3 T, vec3 V){
  float a = P.a; if (a < 0.004) return under;
  vec3 alb = pow(clamp(P.rgb/a,0.,1.), vec3(2.2));
  float ax = texture(tex, pu+vec2(tx.x,0)).a - texture(tex, pu-vec2(tx.x,0)).a;
  float ay = texture(tex, pu+vec2(0,tx.y)).a - texture(tex, pu-vec2(0,tx.y)).a;
  vec3 n = normalize(N - (T*ax + vec3(0,1,0)*ay)*1.8);
  vec3 R = reflect(-V,n);
  float F = 0.045 + 0.955*pow(1.-max(dot(n,V),0.),5.);
  vec3 dif = alb*(vec3(0.045,0.05,0.075) + lights(vW,n)*1.4 + spot(vW,n) + uFlash*vec3(.3,.34,.48));
  float fl = smoothstep(0.25, 0.42, alb.g - alb.r);
  float wht = smoothstep(0.55, 0.8, min(alb.r, alb.b));
  vec3 glow = alb*fl*uUV*0.6 + vec3(.62,.72,1.)*wht*uUV*0.24;
  vec3 Ls = normalize(uSpotPos - vW);
  vec3 spec = envAt(R, 1.)*F*1.25 + vec3(.9,.95,1.)*pow(max(dot(R,Ls),0.),70.)*spotCone(vW)*uSpotI*1.6;
  return mix(under, dif*(0.3+0.7*uReveal) + glow, a) + spec*a*0.9;
}
void main(){
  vec2 m = vUv*uSize;
  vec3 N=uN, T=uT, B=vec3(0,1,0);
  vec3 V = normalize(cameraPosition - vW);
  vec3 base = uTint; vec3 n = N; float refl = 1.; vec3 inner = vec3(0); float lod = 0.;
  if (uKind < 0.5) {
    float colW = 1.5, flH = 4.0;
    float yy = m.y - uPodium; bool pod = yy < 0.;
    float fy = pod ? m.y/max(uPodium,1.) : fract(yy/flH);
    vec2 cell = vec2(floor(m.x/colW), pod ? -1. : floor(yy/flH));
    float fx = fract(m.x/colW), mx = min(fx,1.-fx)*colW;
    float fin = step(mod(cell.x, 4.), 0.5);
    float mull = 1. - smoothstep(0.03+fin*0.05, 0.055+fin*0.05, mx);
    float span = pod ? 0. : step(fy*flH, 0.9);
    float tr = pod ? 1.-smoothstep(0.03,0.07,abs(m.y-uPodium)) : 1.-smoothstep(0.02, 0.05, abs(fy*flH-0.9));
    float h1 = h12(cell + uSeed), h2 = h12(cell.yx*1.31 + uSeed*1.7);
    n = normalize(N + T*(h1-.5)*0.014 + B*(h2-.5)*0.01);
    float riv = smoothstep(.7,.97, vnoise(vec2(m.x*7., m.y*0.3 - uTime*1.7 + h1*10.)));
    n = normalize(n + T*riv*0.07*(vnoise(vec2(m.x*26., m.y*1.7 - uTime*3.))-.5));
    float floorLit = step(h12(vec2(cell.y, uSeed*3.1)), uLit);
    float paneLit = floorLit * step(0.3, h12(cell*1.3+uSeed));
    inner = vec3(.5,.62,.85)*(0.008+0.03*h1*h1) * paneLit * (0.4 + 0.6*smoothstep(0.95, 0.3, fy));
    if (pod) { inner = vec3(.62,.72,.92)*0.03*(0.3+0.7*fy*fy)*(0.7+0.3*h1)*uLobby; float post = 1.-smoothstep(0.08,0.12, min(fract(m.x/6.),1.-fract(m.x/6.))*6.); inner*=1.-post; base = mix(base, vec3(0.02), post); }
    if (span>0.5){ base = vec3(0.010,0.011,0.014); inner = vec3(0); refl = 0.3; lod = 4.; }
    if (mull>0.01){ base = mix(base, vec3(0.022,0.025,0.03), mull); inner *= 1.-mull; refl = mix(refl, 0.55, mull); lod = mix(lod, 2.5, mull); n = normalize(mix(n, N + T*sign(fx-.5)*0.7*fin, mull)); }
    if (tr>0.01){ base = mix(base, vec3(0.04,0.045,0.055), tr); inner*=1.-tr; lod = mix(lod,2.,tr); }
    // the building's own light: hairline edges up its corners, a band on the plant floors, a strip along the street
    float ed = min(m.x, uSize.x - m.x);
    vec2 fw = fwidth(m);
    float ew = max(0.12, fw.x*1.6), eh = max(0.1, fw.y*1.6);
    inner += uEdge * (1.-smoothstep(ew*0.4, ew, ed)) * step(uPodium, m.y) * 2.2 * min(1., 0.12/ew*1.4);
    float band = (1.-smoothstep(eh*0.5, eh, abs(mod(m.y - uPodium - 28., 56.) - 28.))) * min(1., 0.1/eh*1.4);
    inner += uEdge * band * step(uPodium + 20., m.y) * 0.9;
    inner += uEdge * (1.-smoothstep(0.04, 0.1, abs(m.y - 0.18))) * 0.9 + uEdge * (1.-smoothstep(0.03, 0.08, abs(m.y - uPodium))) * 0.35;
  } else {
    // a construction hoarding: painted ply panels, wet
    float px = fract(m.x/1.22); float seam = 1.-smoothstep(0.004,0.012,min(px,1.-px)*1.22);
    base = vec3(0.014,0.016,0.02)*(0.85+0.3*vnoise(m*vec2(3.,1.)))*(1.-seam*0.6);
    refl = 0.4; lod = 3.5;
    n = normalize(N + T*(vnoise(m*9.)-.5)*0.05);
  }
  vec3 R = reflect(-V, n);
  vec3 env = envAt(R, lod);
  float F = 0.05 + 0.95*pow(1.-max(dot(n,V),0.),5.);
  vec3 col = env*mix(0.12,0.9,F)*refl + inner*(1.-F) + base*(vec3(0.01) + lights(vW,N)*0.5) ;
  // the searchlight on wet glass: a scattered disc and a hard glint
  vec3 Ls = normalize(uSpotPos - vW);
  col += spot(vW,N)*(uKind>0.5 ? 0.25 : 0.05) + vec3(.9,.95,1.)*pow(max(dot(R,Ls),0.),300.)*spotCone(vW)*uSpotI*3.;
  if (uHasPaint > 0.5) {
    vec2 pu = (m - uPR.xy)/(uPR.zw - uPR.xy);
    if (pu.x>0. && pu.y>0. && pu.x<1. && pu.y<1.) {
      vec4 P = texture(uPaint, pu);
      vec4 D = texture(uDripM, pu);
      P *= 1. - D.a*step(uDrip, D.g);
      col = paintOver(col, P, uPaint, pu, uPTex, N, T, V);
    }
  }
  if (uHasLive > 0.5) {
    vec2 lu = (m - uLR.xy)/(uLR.zw - uLR.xy);
    if (lu.x>0. && lu.y>0. && lu.x<1. && lu.y<1.) col = paintOver(col, texture(uLive, lu), uLive, lu, uLTex, N, T, V);
  }
  gl_FragColor = vec4(fogit(col, vW), 1.);
}`;

// ------------------------------------------------------------ the wet plaza
const FS_GROUND = /* glsl */`
${COMMON}
uniform sampler2D uRefl; uniform mat4 uTexMat; uniform float uUV; uniform float uReveal;
uniform sampler2D uGP; uniform vec4 uGR; uniform vec2 uGPTex;
uniform sampler2D uLive; uniform vec4 uLR; uniform float uHasLive; uniform vec2 uLTex;
uniform vec4 uVents[3];
varying vec2 vUv; varying vec3 vW;
vec2 ripple(vec2 p, float t){
  vec2 acc=vec2(0);
  for (int j=-1;j<=1;j++) for(int i=-1;i<=1;i++){
    vec2 c=floor(p)+vec2(float(i),float(j)); float h=h12(c);
    vec2 o=c+vec2(h, h12(c+7.1));
    float ph=fract(t*(0.8+h*0.7)+h*13.);
    vec2 d=p-o; float r=length(d); float rr=r-ph*0.85;
    acc += d/(r+1e-3) * exp(-rr*rr*160.) * (1.-ph) * cos(rr*46.);
  }
  return acc;
}
vec3 paintG(vec3 under, vec4 P, sampler2D tex, vec2 pu, vec2 tx){
  float a = P.a; if (a<0.004) return under;
  vec3 alb = pow(clamp(P.rgb/a,0.,1.), vec3(2.2));
  float fl = smoothstep(0.25, 0.42, alb.g - alb.r);
  vec3 dif = alb*(vec3(0.025,0.03,0.045) + lights(vW,vec3(0,1,0))*1.2 + spot(vW,vec3(0,1,0)) + uFlash*vec3(.25,.28,.4));
  return mix(under, dif*(0.3+0.7*uReveal) + alb*fl*uUV*0.4, a*0.92);
}
void main(){
  vec2 xz=vW.xz; vec3 V=normalize(cameraPosition-vW);
  float d = length(vW - cameraPosition);
  float plaza = 1.-smoothstep(54.,58.,length(xz-vec2(0.,-2.)));
  vec2 tile = xz/vec2(1.2,0.6); vec2 tf=fract(tile);
  float jx = min(tf.x,1.-tf.x)*1.2, jy = min(tf.y,1.-tf.y)*0.6;
  float joint = (1.-smoothstep(0.004,0.02,min(jx,jy)))*plaza*(1.-smoothstep(25.,60.,d));
  float tv = h12(floor(tile));
  float pud = fbm(xz*0.055+3.) + 0.22*fbm(xz*0.35) + 0.08*tv*plaza;
  float puddle = smoothstep(0.44, 0.54, pud);
  vec3 alb = mix(vec3(0.012,0.013,0.016), vec3(0.026,0.027,0.031)*(0.8+0.4*tv), plaza)*(1.-joint*0.6);
  // grates over the steam vents
  float grate = 0.;
  for (int i=0;i<3;i++){ vec2 g = abs(xz-uVents[i].xy); if (max(g.x,g.y) < uVents[i].z){ grate = 1.; float bars = step(0.5, fract(xz.x*5.)); alb = vec3(0.006)*(0.5+bars); } }
  vec2 rp = ripple(xz*2.1, uTime) + ripple(xz*3.4+5., uTime*1.25)*0.6;
  float rfade = 1. - smoothstep(14., 60., d);
  vec3 n = normalize(vec3(rp.x*0.45*rfade*mix(0.5,1.,puddle), 1., rp.y*0.45*rfade*mix(0.5,1.,puddle)));
  n = normalize(n + vec3(vnoise(xz*7.)-.5, 0., vnoise(xz*7.+3.)-.5)*0.12*(1.-puddle)*(1.-grate));
  vec4 pc = uTexMat*vec4(vW,1.); vec2 ruv = pc.xy/pc.w;
  ruv += n.xz*vec2(0.05, 0.08);
  float rough = mix(0.5, 0.03, puddle);
  vec3 refl = vec3(0);
  for (int i=0;i<5;i++){ float k=(float(i)-2.)*0.5; refl += textureLod(uRefl, clamp(ruv+vec2(0., k*rough*0.07), 0.002, .998), rough*5.).rgb; }
  refl *= 0.2;
  float F = 0.025 + 0.975*pow(1.-max(dot(n,V),0.),5.);
  vec3 col = alb*(vec3(0.008,0.01,0.016) + lights(vW,vec3(0,1,0)) + spot(vW,vec3(0,1,0)) + uFlash*vec3(.18,.2,.28));
  vec2 gu = vec2((xz.x-uGR.x)/(uGR.z-uGR.x), (-xz.y-uGR.y)/(uGR.w-uGR.y));
  if (gu.x>0.&&gu.y>0.&&gu.x<1.&&gu.y<1.) col = paintG(col, texture(uGP, gu), uGP, gu, uGPTex);
  if (uHasLive>0.5){ vec2 lu = vec2((xz.x-uLR.x)/(uLR.z-uLR.x), (-xz.y-uLR.y)/(uLR.w-uLR.y)); if (lu.x>0.&&lu.y>0.&&lu.x<1.&&lu.y<1.) col = paintG(col, texture(uLive, lu), uLive, lu, uLTex); }
  col += refl * mix(0.55, 1.15, puddle) * max(F, mix(0.08, 0.3, puddle)) * (1.-grate*0.7);
  #ifdef DBG
  col = refl*2.;
  #endif
  gl_FragColor = vec4(fogit(col, vW), 1.);
}`;

// ------------------------------------------------------------ signs and screens
const FS_SIGN = /* glsl */`
${COMMON}
uniform sampler2D uAtlas; uniform vec4 uA; uniform vec4 uB; uniform float uProg; uniform float uSA; uniform float uTA;
uniform float uSeed; uniform float uGain; uniform float uScreen; uniform float uGlitch; uniform float uUV;
uniform sampler2D uSP; uniform float uHasSP; uniform vec2 uSPTex;
varying vec2 vUv; varying vec3 vW;
vec3 tileAt(vec4 r, vec2 uv){
  vec2 q = uv-.5; if (uSA > uTA) q.x *= uSA/uTA; else q.y *= uTA/uSA; q += .5;
  vec3 bg = texture(uAtlas, r.xy + r.zw*vec2(0.02,0.02)).rgb;
  if (q.x<0.||q.y<0.||q.x>1.||q.y>1.) return bg;
  return texture(uAtlas, r.xy + q*r.zw).rgb;
}
void main(){
  vec2 uv = vUv;
  float t = uTime;
  float gl = uGlitch + (uProg>0.001 && uProg<0.999 ? 0.6 : 0.);
  float band = floor(uv.y*(uScreen>0.5?26.:10.) + floor(t*13.)*0.37);
  float bh = h12(vec2(band, floor(t*17.)+uSeed));
  uv.x += (bh-.5)*0.22*gl*step(0.62,bh);
  float split = 0.012*gl;
  vec3 cA = tileAt(uA, uv), cB = tileAt(uB, uv);
  if (uScreen > 0.5) {
    // the corporate feed: its mark, breathing, with slow cold light moving through it
    float sweep = 0.5+0.5*sin(uv.x*3.1 - t*0.35 + sin(uv.y*2.+t*0.2));
    cA = cA*(0.75+0.35*sweep) + vec3(0.045,0.055,0.11)*pow(sweep,3.)*(1.-length(cA));
    if (gl > 0.01) { cA.r = tileAt(uA, uv+vec2(split,0)).r; cB.b = tileAt(uB, uv-vec2(split,0)).b; }
  }
  float pick = step(h12(vec2(band*1.7+uSeed, floor(t*9.))), uProg*1.12-0.06);
  vec3 col = mix(cA, cB, pick);
  if (uProg>0.001 && uProg<0.999) col *= step(0.3, h12(vec2(floor(t*26.), uSeed)))*0.9+0.1;
  if (gl > 0.2) col += vec3(0.6,0.7,1.)*step(0.985, h12(floor(uv*vec2(60.,30.))+floor(t*20.)))*gl;
  // the surface: LED pitch on screens, a diffuser on lightboxes
  if (uScreen > 0.5) { vec2 g = fract(vUv*vec2(uSA,1.)*72.); col *= 0.86 + 0.18*smoothstep(0.55,0.15,length(g-.5)); col *= 0.94+0.06*sin(vUv.y*900.+t*40.); }
  else col *= 0.9 + 0.12*(1.-length(vUv-.5));
  col *= uGain;
  if (uHasSP > 0.5) {
    vec4 P = texture(uSP, vUv);
    if (P.a > 0.004) {
      vec3 alb = pow(clamp(P.rgb/P.a,0.,1.), vec3(2.2));
      float fl = smoothstep(0.25, 0.42, alb.g - alb.r);
      vec3 N = normalize(cameraPosition - vW);
      float wht = smoothstep(0.55, 0.8, min(alb.r, alb.b));
      vec3 lit = alb*(vec3(0.07,0.08,0.11) + spot(vW, N) + uFlash*0.3) + alb*fl*uUV*0.6 + vec3(.62,.72,1.)*wht*uUV*0.3;
      col = mix(col, lit, P.a);
    }
  }
  gl_FragColor = vec4(fogit(col, vW), 1.);
}`;

// ============================================================ fonts and images
async function fontsReady() {
  try { await Promise.all([document.fonts.load('600 64px "Timeless Serif"'), document.fonts.load('300 64px "Commit Mono"')]); } catch (e) { }
}
function loadSVG(file) {
  return fetch(file).then(r => r.text()).then(t => new Promise(res => {
    // the files animate; take their still, final state
    const still = t.replace(/<style>[\s\S]*?<\/style>/g, '');
    const img = new Image();
    img.onload = () => res(img); img.onerror = () => res(null);
    img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(still);
  })).catch(() => null);
}

// ============================================================ drawn marks
function breakCanvas(size, stone = C.paper) {
  const c = mkCanvas(size, size), x = c.getContext('2d');
  x.scale(size / 100, size / 100);
  x.fillStyle = stone; x.fill(tile100());
  x.globalCompositeOperation = 'destination-out'; x.fill(new Path2D(BREAK.seam)); x.fill(new Path2D(BREAK.cav));
  x.globalCompositeOperation = 'source-over';
  x.fillStyle = C.sky; x.fill(new Path2D(BREAK.gem));
  x.fillStyle = 'rgba(255,255,255,0.28)'; x.fill(new Path2D(BREAK.facet));
  return c;
}
function corpGlyph(x, kind, cx, cy, s, col) {
  x.save(); x.fillStyle = col; x.strokeStyle = col;
  if (kind === 'kolvane') { // three slabs, the middle one pushed out of line
    [[-0.3, 0], [-0.04, 0.15], [0.22, 0]].forEach(([dy, dx]) => x.fillRect(cx - s * 0.32 + dx * s, cy + dy * s - s * 0.08, s * 0.58, s * 0.16));
    x.fillRect(cx - s * 0.32, cy - s * 0.46, s * 0.06, s * 0.06);
  } else if (kind === 'novarch') { // a gate: a heavy arch over a parted base
    x.lineWidth = s * 0.12; x.beginPath(); x.arc(cx, cy + s * 0.1, s * 0.3, Math.PI, 0); x.stroke();
    x.fillRect(cx - s * 0.42, cy + s * 0.2, s * 0.34, s * 0.09); x.fillRect(cx + s * 0.08, cy + s * 0.2, s * 0.34, s * 0.09);
  } else if (kind === 'tessarine') { // a falling wedge cut by a slot
    x.beginPath(); x.moveTo(cx - s * 0.38, cy - s * 0.3); x.lineTo(cx + s * 0.38, cy - s * 0.3); x.lineTo(cx + s * 0.18, cy - s * 0.05); x.lineTo(cx - s * 0.18, cy - s * 0.05); x.fill();
    x.beginPath(); x.moveTo(cx - s * 0.13, cy + 0.02 * s); x.lineTo(cx + s * 0.13, cy + 0.02 * s); x.lineTo(cx, cy + s * 0.34); x.fill();
  } else { // ostraven: a ring broken three ways, a point held in it
    x.lineWidth = s * 0.075;
    for (let k = 0; k < 3; k++) { x.beginPath(); x.arc(cx, cy, s * 0.3, k * Math.PI * 2 / 3 + 0.28 - Math.PI / 2, (k + 1) * Math.PI * 2 / 3 - 0.28 - Math.PI / 2); x.stroke(); }
    x.beginPath(); x.arc(cx, cy, s * 0.06, 0, Math.PI * 2); x.fill();
  }
  x.restore();
}
function tracked(x, text, cx, y, size, track, font) {
  x.font = `${size}px ${font}`;
  const ws = [...text].map(c => x.measureText(c).width), tw = ws.reduce((a, b) => a + b, 0) + track * size * (text.length - 1);
  let px = cx - tw / 2;
  [...text].forEach((c, i) => { x.fillText(c, px, y); px += ws[i] + track * size; });
}

// tiles: 0..3 corps, 4 mark on cobalt, 5 mark on ink, 6 Orbe, 7 immiscible, 8 Idyll
async function buildAtlas() {
  const T = 512, A = mkCanvas(T * 4, T * 3), x = A.getContext('2d', { willReadFrequently: true });
  x.fillStyle = '#050607'; x.fillRect(0, 0, A.width, A.height);
  const at = i => [(i % 4) * T, Math.floor(i / 4) * T];
  ['kolvane', 'novarch', 'tessarine', 'ostraven'].forEach((k, i) => {
    const [ox, oy] = at(i);
    const lit = k === 'novarch';
    const g = x.createRadialGradient(ox + T / 2, oy + T * 0.45, 0, ox + T / 2, oy + T / 2, T * 0.75);
    if (lit) { g.addColorStop(0, '#8E9CC8'); g.addColorStop(0.7, '#3A4566'); g.addColorStop(1, '#1A2033'); }
    else { g.addColorStop(0, '#0b0d14'); g.addColorStop(1, '#040506'); }
    x.fillStyle = g; x.fillRect(ox, oy, T, T);
    corpGlyph(x, k, ox + T / 2, oy + T * 0.43, T * 0.5, lit ? '#06070B' : CORP[k].col);
    x.fillStyle = lit ? '#06070B' : CORP[k].col; x.globalAlpha = 0.9;
    tracked(x, CORP[k].name, ox + T / 2, oy + T * 0.84, 30, 0.55, '300 "Commit Mono", monospace');
    x.globalAlpha = 1;
  });
  const mk = breakCanvas(512);
  { const [ox, oy] = at(4); x.fillStyle = C.cobalt; x.fillRect(ox, oy, T, T); x.drawImage(mk, ox + T * 0.22, oy + T * 0.22, T * 0.56, T * 0.56); }
  { const [ox, oy] = at(5); x.fillStyle = '#06080d'; x.fillRect(ox, oy, T, T);
    const g = x.createRadialGradient(ox + T / 2, oy + T / 2, 0, ox + T / 2, oy + T / 2, T * 0.5); g.addColorStop(0, 'rgba(36,72,255,0.35)'); g.addColorStop(1, 'rgba(36,72,255,0)'); x.fillStyle = g; x.fillRect(ox, oy, T, T);
    x.drawImage(mk, ox + T * 0.24, oy + T * 0.24, T * 0.52, T * 0.52); }
  const imgs = await Promise.all(Object.values(WORK).map(w => loadSVG(w.file)));
  Object.values(WORK).forEach((w, i) => {
    const [ox, oy] = at(6 + i);
    x.fillStyle = '#07080b'; x.fillRect(ox, oy, T, T);
    if (imgs[i]) x.drawImage(imgs[i], ox + T * 0.27, oy + T * 0.14, T * 0.46, T * 0.46);
    x.fillStyle = C.paper; x.textAlign = 'left'; x.textBaseline = 'alphabetic';
    tracked(x, w.name, ox + T / 2, oy + T * 0.83, 54, 0.04, '500 "Timeless Serif", Georgia, serif');
  });
  // vertical blades: 0 KOLVANE, 1 ANTIMONY
  const VA = mkCanvas(512, 1024), v = VA.getContext('2d', { willReadFrequently: true });
  v.fillStyle = '#040506'; v.fillRect(0, 0, 512, 1024);
  corpGlyph(v, 'kolvane', 128, 120, 150, CORP.kolvane.col);
  v.fillStyle = CORP.kolvane.col; v.textAlign = 'center';
  [...'KOLVANE'].forEach((c, i) => { v.font = '300 64px "Commit Mono", monospace'; v.fillText(c, 128, 290 + i * 104); });
  v.fillStyle = '#06080d'; v.fillRect(256, 0, 256, 1024);
  v.drawImage(mk, 256 + 48, 50, 160, 160);
  v.fillStyle = C.paper;
  [...'ANTIMONY'].forEach((c, i) => { v.font = '500 70px "Timeless Serif", Georgia, serif'; v.fillText(c, 384, 300 + i * 92); });
  // the mean colour of each tile, for the light it throws
  const means = [];
  for (let i = 0; i < 9; i++) {
    const [ox, oy] = at(i), d = x.getImageData(ox, oy, T, T).data;
    let r = 0, g = 0, b = 0, n = 0;
    for (let k = 0; k < d.length; k += 64) { r += d[k]; g += d[k + 1]; b += d[k + 2]; n++; }
    means.push(new THREE.Color(`rgb(${Math.round(r / n)},${Math.round(g / n)},${Math.round(b / n)})`));
  }
  const vd = v.getImageData(0, 0, 512, 1024).data; const vm = [0, 1].map(k => { let r = 0, g = 0, b = 0, n = 0; for (let y = 0; y < 1024; y += 4) for (let xx = k * 256; xx < k * 256 + 256; xx += 4) { const o = (y * 512 + xx) * 4; r += vd[o]; g += vd[o + 1]; b += vd[o + 2]; n++; } return new THREE.Color(`rgb(${Math.round(r / n)},${Math.round(g / n)},${Math.round(b / n)})`); });
  const tex = new THREE.CanvasTexture(A); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 8;
  const vtex = new THREE.CanvasTexture(VA); vtex.colorSpace = THREE.SRGBColorSpace; vtex.anisotropy = 8;
  const rect = i => { const m = 3 / T; return new THREE.Vector4((i % 4) / 4 + m / 4, 1 - (Math.floor(i / 4) + 1) / 3 + m / 3, (1 - 2 * m) / 4, (1 - 2 * m) / 3); };
  const vrect = i => new THREE.Vector4(i * 0.5 + 0.004, 0.002, 0.492, 0.996);
  return { tex, vtex, rect, vrect, means, vm };
}

// ============================================================ the world
const TOWERS = [
  { id: 'hero', x: 0, z: -38, w: 48, d: 40, h: 160, ry: 0, tint: [0.012, 0.014, 0.02], lit: 0.32, podium: 10, lobby: 1, seed: 1.3, edge: '#C4CCF2', edgeK: 0.5 },
  { id: 'spire', x: 0, z: -41, w: 30, d: 28, h: 46, y0: 160, ry: 0, tint: [0.012, 0.014, 0.02], lit: 0.1, podium: -1, seed: 2.1, edge: '#C4CCF2', edgeK: 0.5 },
  { id: 'L', x: -45, z: -8, w: 32, d: 40, h: 150, ry: 1.1, tint: [0.013, 0.014, 0.018], lit: 0.4, podium: 9, lobby: 0.7, seed: 3.7, edge: '#EEF2FF', edgeK: 0.45 },
  { id: 'R', x: 45, z: -12, w: 30, d: 38, h: 176, ry: -1.06, tint: [0.012, 0.013, 0.019], lit: 0.28, podium: 9, lobby: 0.6, seed: 5.9, edge: '#FF2D55', edgeK: 0.32 },
  { id: 'BL', x: -38, z: -96, w: 36, d: 36, h: 250, ry: 0.3, tint: [0.012, 0.013, 0.017], lit: 0.25, podium: 12, lobby: 0.5, seed: 7.1, edge: '#BFD0FF', edgeK: 0.4 },
  { id: 'BR', x: 40, z: -104, w: 32, d: 34, h: 228, ry: -0.24, tint: [0.012, 0.014, 0.019], lit: 0.3, podium: 12, lobby: 0.5, seed: 8.3, edge: '#C4CCF2', edgeK: 0.4 },
  { id: 'FL', x: -54, z: 52, w: 30, d: 30, h: 120, ry: 2.1, tint: [0.012, 0.013, 0.017], lit: 0.35, podium: 8, lobby: 0.5, seed: 9.9, edge: '#EEF2FF', edgeK: 0.3 },
  { id: 'FR', x: 54, z: 54, w: 30, d: 30, h: 132, ry: -2.1, tint: [0.012, 0.013, 0.017], lit: 0.3, podium: 8, lobby: 0.5, seed: 11.4, edge: '#BFD0FF', edgeK: 0.3 },
];
const walls = {}; // id.face -> { mesh, mat, w, h, n, t, origin, live }
const blankTex = new THREE.DataTexture(new Uint8Array([0, 0, 0, 0]), 1, 1); blankTex.needsUpdate = true;

function faceFrame(T, face) {
  const a = T.ry + [0, Math.PI / 2, Math.PI, -Math.PI / 2][face];
  const n = V3(Math.sin(a), 0, Math.cos(a)), t = V3(Math.cos(a), 0, -Math.sin(a));
  const half = face % 2 === 0 ? T.d / 2 : T.w / 2, width = face % 2 === 0 ? T.w : T.d;
  const c = V3(T.x, (T.y0 || 0), T.z).addScaledVector(n, half);
  return { a, n, t, width, c };
}
// a point on a face: u from its left edge, v up from its base
function onFace(id, face, u, v, out = 0.15) {
  const T = TOWERS.find(t => t.id === id), F = faceFrame(T, face);
  return { pos: F.c.clone().addScaledVector(F.t, u - F.width / 2).addScaledVector(F.n, out).setY((T.y0 || 0) + v), a: F.a, n: F.n };
}

function buildTowers() {
  for (const T of TOWERS) {
    for (let f = 0; f < 4; f++) {
      const F = faceFrame(T, f);
      const geo = new THREE.PlaneGeometry(F.width, T.h); geo.translate(0, T.h / 2, 0);
      const mat = new THREE.ShaderMaterial({
        uniforms: {
          ...U, uSize: { value: new THREE.Vector2(F.width, T.h) }, uSeed: { value: T.seed + f * 1.37 }, uN: { value: F.n }, uT: { value: F.t },
          uTint: { value: V3(...T.tint) }, uLit: { value: T.lit }, uKind: { value: 0 }, uPodium: { value: T.podium }, uLobby: { value: T.lobby || 0 },
          uEdge: { value: (() => { const c = new THREE.Color(T.edge || '#000000').multiplyScalar(T.edgeK ?? 0.5); return V3(c.r, c.g, c.b); })() },
          uPaint: { value: blankTex }, uDripM: { value: blankTex }, uPR: { value: new THREE.Vector4(0, 0, 1, 1) }, uHasPaint: { value: 0 }, uPTex: { value: new THREE.Vector2(0.001, 0.001) },
          uLive: { value: blankTex }, uLR: { value: new THREE.Vector4(0, 0, 1, 1) }, uHasLive: { value: 0 }, uLTex: { value: new THREE.Vector2(0.001, 0.001) },
        }, vertexShader: VS_WORLD, fragmentShader: FS_WALL,
      });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.copy(F.c); mesh.rotation.y = F.a;
      scene.add(mesh);
      walls[T.id + '.' + f] = { mesh, mat, w: F.width, h: T.h, T, podium: T.podium };
      mesh.userData.wall = walls[T.id + '.' + f];
    }
  }
}

// the far city: boxes in the haze
const FS_FAR = /* glsl */`
${COMMON}
varying vec3 vW; varying vec3 vN; varying float vS;
void main(){
  vec2 m = vec2(abs(vN.x)>0.5 ? vW.z : vW.x, vW.y);
  vec2 cell = floor(m/vec2(1.6,3.8)); vec2 f = fract(m/vec2(1.6,3.8));
  float lit = step(0.86, h12(cell+vS*13.)) * step(0.4, h12(vec2(cell.y, vS)));
  float win = step(0.15,f.x)*step(f.x,0.85)*step(0.25,f.y)*step(f.y,0.8);
  vec3 col = vec3(0.006,0.007,0.01) + vec3(.55,.65,.9)*0.06*lit*win;
  gl_FragColor = vec4(fogit(col, vW), 1.);
}`;
function buildFarCity() {
  const R = rng(51), n = PHONE ? 60 : 110;
  const geo = new THREE.BoxGeometry(1, 1, 1); geo.translate(0, 0.5, 0);
  const seeds = new Float32Array(n);
  const mat = new THREE.ShaderMaterial({
    uniforms: { ...U }, fragmentShader: FS_FAR,
    vertexShader: `attribute float aS; varying vec3 vW; varying vec3 vN; varying float vS;
      void main(){ vS=aS; vec4 w = modelMatrix*instanceMatrix*vec4(position,1.); vW=w.xyz; vN = normalize(mat3(modelMatrix*instanceMatrix)*normal); gl_Position=projectionMatrix*viewMatrix*w; }`,
  });
  const im = new THREE.InstancedMesh(geo, mat, n), M = new THREE.Matrix4(), q = new THREE.Quaternion();
  const tops = [];
  for (let i = 0; i < n; i++) {
    const a = R() * Math.PI * 2, r = 150 + R() * 260;
    const x = Math.sin(a) * r, z = Math.cos(a) * r - 40;
    const w = 18 + R() * 30, d = 18 + R() * 30, h = 50 + Math.pow(R(), 1.6) * 300;
    q.setFromAxisAngle(V3(0, 1, 0), R() * Math.PI);
    M.compose(V3(x, 0, z), q, V3(w, h, d)); im.setMatrixAt(i, M); seeds[i] = R();
    if (h > 160) tops.push([x, h + 1, z]);
  }
  geo.setAttribute('aS', new THREE.InstancedBufferAttribute(seeds, 1));
  scene.add(im);
  // warning lights on the tallest roofs, slow red
  const pg = new THREE.BufferGeometry(); pg.setAttribute('position', new THREE.Float32BufferAttribute(tops.flat(), 3));
  const ph = new Float32Array(tops.length).map(() => R()); pg.setAttribute('aP', new THREE.BufferAttribute(ph, 1));
  const pts = new THREE.Points(pg, new THREE.ShaderMaterial({
    uniforms: { ...U }, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    vertexShader: `attribute float aP; uniform float uTime; varying float vB; void main(){ vB = pow(0.5+0.5*sin(uTime*1.3+aP*40.),6.); vec4 mv = modelViewMatrix*vec4(position,1.); gl_PointSize = 520./-mv.z; gl_Position = projectionMatrix*mv; }`,
    fragmentShader: `varying float vB; void main(){ float r = length(gl_PointCoord-.5); gl_FragColor = vec4(vec3(1.2,0.06,0.09)*vB*smoothstep(.5,.1,r), 1.); }`,
  }));
  scene.add(pts);
}

let sky;
function buildSky() {
  sky = new THREE.Mesh(new THREE.SphereGeometry(2000, 32, 16), new THREE.ShaderMaterial({
    uniforms: { ...U }, side: THREE.BackSide, depthWrite: false,
    vertexShader: `varying vec3 vD; void main(){ vD = normalize(position); vec4 p = projectionMatrix*viewMatrix*vec4(position+cameraPosition,1.); gl_Position = p.xyww; }`,
    fragmentShader: `${COMMON} varying vec3 vD; void main(){ gl_FragColor = vec4(skyCol(normalize(vD)),1.); }`,
  }));
  sky.renderOrder = -1; sky.frustumCulled = false;
  scene.add(sky);
}

// ------------------------------------------------------------ ground and its reflection
let ground, reflRT, mirrorCam, texMat = new THREE.Matrix4();
const VENTS = [[-6, 16, 0.7], [9, 6, 0.6], [-17, -6, 0.7]];
function buildGround() {
  const s = PHONE ? 0.36 : 0.5;
  reflRT = new THREE.WebGLRenderTarget(Math.round(innerWidth * s), Math.round(innerHeight * s), { type: THREE.HalfFloatType, generateMipmaps: true, minFilter: THREE.LinearMipmapLinearFilter, magFilter: THREE.LinearFilter });
  mirrorCam = camera.clone();
  const mat = new THREE.ShaderMaterial({
    uniforms: {
      ...U, uRefl: { value: reflRT.texture }, uTexMat: { value: texMat },
      uGP: { value: blankTex }, uGR: { value: new THREE.Vector4(0, 0, 1, 1) }, uGPTex: { value: new THREE.Vector2(0.001, 0.001) },
      uLive: { value: blankTex }, uLR: { value: new THREE.Vector4(-60, -60, 60, 60) }, uHasLive: { value: 0 }, uLTex: { value: new THREE.Vector2(0.001, 0.001) },
      uVents: { value: VENTS.map(v => new THREE.Vector4(v[0], v[1], v[2], 0)) },
    }, vertexShader: VS_WORLD, fragmentShader: FS_GROUND, defines: Q.has('dbg') ? { DBG: 1 } : {},
  });
  const geo = new THREE.PlaneGeometry(1400, 1400, 1, 1); geo.rotateX(-Math.PI / 2);
  ground = new THREE.Mesh(geo, mat);
  scene.add(ground);
}
function updateMirror() {
  mirrorCam.projectionMatrix.copy(camera.projectionMatrix);
  mirrorCam.position.set(camera.position.x, -camera.position.y, camera.position.z);
  const dir = V3(0, 0, -1).applyQuaternion(camera.quaternion); dir.y *= -1;
  const up = V3(0, 1, 0).applyQuaternion(camera.quaternion); up.y *= -1;
  mirrorCam.up.copy(up); mirrorCam.lookAt(mirrorCam.position.clone().add(dir));
  mirrorCam.updateMatrixWorld(); mirrorCam.matrixWorldInverse.copy(mirrorCam.matrixWorld).invert();
  texMat.set(0.5, 0, 0, 0.5, 0, 0.5, 0, 0.5, 0, 0, 0.5, 0.5, 0, 0, 0, 1).multiply(mirrorCam.projectionMatrix).multiply(mirrorCam.matrixWorldInverse);
}

// ------------------------------------------------------------ hoarding at street level
let hoarding;
function buildHoarding() {
  const w = 12, h = 2.6, a = 0.3;
  const n = V3(Math.sin(a), 0, Math.cos(a)), t = V3(Math.cos(a), 0, -Math.sin(a));
  const geo = new THREE.PlaneGeometry(w, h); geo.translate(0, h / 2, 0);
  const mat = new THREE.ShaderMaterial({
    uniforms: {
      ...U, uSize: { value: new THREE.Vector2(w, h) }, uSeed: { value: 4.4 }, uN: { value: n }, uT: { value: t },
      uTint: { value: V3(0.02, 0.02, 0.024) }, uLit: { value: 0 }, uKind: { value: 1 }, uPodium: { value: -1 }, uLobby: { value: 0 }, uEdge: { value: V3() },
      uPaint: { value: blankTex }, uDripM: { value: blankTex }, uPR: { value: new THREE.Vector4(0, 0, w, h) }, uHasPaint: { value: 0 }, uPTex: { value: new THREE.Vector2(0.001, 0.001) },
      uLive: { value: blankTex }, uLR: { value: new THREE.Vector4(0, 0, w, h) }, uHasLive: { value: 0 }, uLTex: { value: new THREE.Vector2(0.001, 0.001) },
    }, vertexShader: VS_WORLD, fragmentShader: FS_WALL,
  });
  hoarding = new THREE.Mesh(geo, mat);
  hoarding.position.set(-5.8, 0, 12); hoarding.rotation.y = a;
  scene.add(hoarding);
  walls.hoard = { mesh: hoarding, mat, w, h, podium: -1 };
  hoarding.userData.wall = walls.hoard;
  // a dark frame along its top
  const rail = new THREE.Mesh(new THREE.BoxGeometry(w, 0.08, 0.1), new THREE.MeshBasicMaterial({ color: 0x050607 }));
  rail.position.set(-5.8, h, 12).addScaledVector(n, 0.02); rail.rotation.y = a; scene.add(rail);
}

// ============================================================ the paint: what the rebellion did here
const PXM = PHONE ? 0.5 : 1;
function paintTex(P) {
  const t = new THREE.CanvasTexture(P.c); t.premultiplyAlpha = true; t.anisotropy = 8; t.colorSpace = THREE.NoColorSpace;
  let d = blankTex;
  if (P.p) { d = new THREE.CanvasTexture(P.p); d.anisotropy = 4; }
  return { t, d };
}
function attachPaint(wall, P) {
  const { t, d } = paintTex(P);
  const u = wall.mat.uniforms;
  u.uPaint.value = t; u.uDripM.value = d; u.uHasPaint.value = 1;
  u.uPR.value.set(P.u0, P.v0, P.u1, P.v1); u.uPTex.value.set(1 / P.W, 1 / P.H);
}
const ledgesFor = (podium, top) => { const l = []; for (let v = podium + 0.9; v < top; v += 4) l.push(v); return l; };

function handTag(P, word, u, vBase, h, o) {
  const top = P.y(vBase + h), x = P.x(u), hp = h * P.pxm;
  const W = wordWidth(word, hp, o.gap ?? 0.1);
  const { strokes } = handWord(word, x - W / 2, top, hp, { seed: o.seed, lean: o.lean ?? 0.14, gap: o.gap ?? 0.1, slope: o.slope || 0 });
  const r = hp * (o.weight ?? 0.085);
  if (o.shadow) strokes.forEach((s, i) => spray(P, s.map(([a, b]) => [a + hp * 0.05, b + hp * 0.06]), { col: o.shadow, r: r * 1.06, flow: 0.66, drip: 0.6, dripLen: o.dripLen, seed: o.seed * 31 + i, wobble: 0.22, dripW: 1.1 }));
  strokes.forEach((s, i) => spray(P, s, { col: o.col, r, flow: 0.78, drip: o.drip ?? 1, dripLen: o.dripLen, seed: o.seed * 17 + i, wobble: 0.24 }));
  if (o.shine) strokes.forEach((s, i) => {
    if (i % 3 !== 1 || s.length < 2) return;
    const [a, b] = s, t0 = 0.12, t1 = 0.12 + 0.18;
    const p0 = [a[0] + (b[0] - a[0]) * t0 - r * 0.35, a[1] + (b[1] - a[1]) * t0 - r * 0.3], p1 = [a[0] + (b[0] - a[0]) * t1 - r * 0.35, a[1] + (b[1] - a[1]) * t1 - r * 0.3];
    spray(P, [p0, p1], { col: o.shine, r: r * 0.17, flow: 0.9, drip: 0, dripLen: [0, 0], seed: i + 400, halo: false, wobble: 0.05 });
    spray(P, [[p1[0] + r * 0.2, p1[1] + r * 0.5], [p1[0] + r * 0.24, p1[1] + r * 0.75]], { col: o.shine, r: r * 0.14, flow: 0.9, drip: 0, dripLen: [0, 0], seed: i + 401, halo: false, wobble: 0 });
  });
}

function paintWorld(signs) {
  const R = rng(2077);
  // ---- the hero tower: ANTIMONY SYSTEMS, older paint buffed beneath it
  const hero = walls['hero.0'];
  const PH = new Painter({ u0: 0, v0: 0, u1: 48, v1: 36, pxm: 42 * PXM, ledges: ledgesFor(10, 36) });
  // an earlier visit, buffed out by the owners
  handTag(PH, 'ANTIMONY', 33, 8.6, 2.6, { col: '#76AEC2', seed: 5, drip: 0.6, dripLen: [0.2, 1.0], weight: 0.07 });
  scribble(PH, PH.x(3), PH.y(16.4), PH.pxm * 6, PH.pxm * 1.7, '#8E949C', 11);
  scribble(PH, PH.x(39), PH.y(19.8), PH.pxm * 5, PH.pxm * 1.4, '#A9AFB8', 12);
  buff(PH, PH.x(23.2), PH.y(11.6), PH.pxm * 16.5, PH.pxm * 3.3, 3);
  buff(PH, PH.x(2.2), PH.y(15.2), PH.pxm * 6.2, PH.pxm * 2.6, 4, [30, 32, 36]);
  scribble(PH, PH.x(12.5), PH.y(9.9), PH.pxm * 4, PH.pxm * 1.0, '#9BA1A9', 13);
  // the strike
  const hA = 7.2, wA = wordWidth('ANTIMONY', hA, 0.06);
  const fit = Math.min(1, 41 / wA);
  handTag(PH, 'ANTIMONY', 24, 20.2, hA * fit, { col: C.sky, shadow: C.cobalt, shine: C.paper, seed: 7, gap: 0.04, slope: -0.012, dripLen: [0.4, 2.2], weight: 0.105 });
  handTag(PH, 'SYSTEMS', 25.5, 14.7, 3.4, { col: C.paper, shadow: C.cobalt, seed: 19, gap: 0.1, weight: 0.095, dripLen: [0.3, 1.3], drip: 0.9 });
  stencil(PH, 'SOFTWARE FOR THE PEOPLE WHO MAKE THE WORK', PH.x(24.6), PH.y(12.0), 1.05 * PH.pxm, C.sky, { seed: 31, drips: 0.12, track: 0.06, center: true });
  stencil(PH, 'READ THE TERMS. THEN REWRITE THEM.', PH.x(19), PH.y(4.3), 0.95 * PH.pxm, C.paper, { seed: 41, drips: 0.15 });
  attachPaint(hero, PH);

  // ---- the screen tower
  const L = walls['L.0'];
  const PL = new Painter({ u0: 0, v0: 0, u1: 32, v1: 14, pxm: 40 * PXM, ledges: [9.05] });
  scribble(PL, PL.x(2.5), PL.y(13.2), PL.pxm * 6, PL.pxm * 1.8, '#9096A0', 21);
  buff(PL, PL.x(1.5), PL.y(13.1), PL.pxm * 9.5, PL.pxm * 2.8, 22, [30, 31, 35]);
  stencil(PL, 'YOUR WORK IS NOT THEIR DATASET', PL.x(3), PL.y(10.0), 1.0 * PL.pxm, C.sky, { seed: 23, drips: 0.2 });
  attachPaint(L, PL);

  // ---- the third tower: ANTIMONY down the glass from a rope
  const Rw = walls['R.0'];
  const PR = new Painter({ u0: 0, v0: 0, u1: 30, v1: 86, pxm: 30 * PXM, ledges: ledgesFor(9, 86) });
  const lh = 4.4; let v = 82;
  [...'ANTIMONY'].forEach((ch, i) => {
    v -= lh + 0.9;
    handTag(PR, ch, 8 + (R() - 0.5) * 0.8, v, lh * (0.95 + R() * 0.1), { col: C.sky, seed: 50 + i, lean: 0.06, dripLen: [0.4, 2.6], weight: 0.09, drip: 1.3 });
  });
  stencil(PR, 'NO ONE SHOULD RENT THEIR OWN HANDS', PR.x(3.5), PR.y(11.4), 0.95 * PR.pxm, C.paper, { seed: 61, drips: 0.12 });
  scribble(PR, PR.x(20), PR.y(15.5), PR.pxm * 5, PR.pxm * 1.5, '#9AA0A8', 62);
  attachPaint(Rw, PR);

  // ---- the hoarding at street level
  const PHo = new Painter({ u0: 0, v0: 0, u1: 12, v1: 2.6, pxm: 90 * PXM, drips: true, ledges: [] });
  scribble(PHo, PHo.x(9.6), PHo.y(0.75), PHo.pxm * 1.8, PHo.pxm * 0.42, '#7F858E', 71);
  stencil(PHo, 'THE TOOLS BELONG TO THE PEOPLE WHO USE THEM', PHo.x(0.55), PHo.y(1.72), 0.31 * PHo.pxm, C.paper, { seed: 72, drips: 0.25 });
  stencil(PHo, 'OPT OUT OF BEING OPTIMISED', PHo.x(0.55), PHo.y(1.02), 0.5 * PHo.pxm, C.sky, { seed: 73, drips: 0.3 });
  attachPaint(walls.hoard, PHo);

  // ---- the paving: a road stencil, stretched to be read at a low angle
  const PG = new Painter({ u0: -16, v0: -24, u1: 16, v1: -6, pxm: 50 * PXM, drips: false });
  stencil(PG, 'MAKERS OVER MARGINS', PG.x(3.2), PG.y(-15.4), 0.5 * PG.pxm, C.sky, { seed: 81, stretch: 3.8, track: 0.12, center: true });
  const gt = paintTex(PG).t;
  ground.material.uniforms.uGP.value = gt; ground.material.uniforms.uGR.value.set(PG.u0, PG.v0, PG.u1, PG.v1); ground.material.uniforms.uGPTex.value.set(1 / PG.W, 1 / PG.H);

  // ---- the Break, stencilled over a corporate lightbox
  const box = signs.find(s => s.id === 'Rbox');
  const PB = new Painter({ u0: 0, v0: 0, u1: 1, v1: 1, pxm: 512, drips: false });
  const s = 512 * 0.62, x0 = 512 * 0.17, y0 = 512 * 0.2;
  const stone = new Path2D(); stone.roundRect(0, 0, 100, 100, 22);
  stencilShape(PB, { fill: stone, cut: [new Path2D(BREAK.seam), new Path2D(BREAK.cav)] }, x0, y0, s, C.paper, { seed: 91, flow: 0.55, base: 0.62, board: true });
  stencilShape(PB, { fill: new Path2D(BREAK.gem) }, x0 + 3, y0 + 2, s, C.sky, { seed: 92, flow: 0.7, base: 0.7 });
  stencilShape(PB, { fill: new Path2D(BREAK.facet) }, x0 + 3, y0 + 2, s, '#E4F7FF', { seed: 93, flow: 0.35, base: 0.18 });
  const bt = paintTex(PB).t;
  box.mat.uniforms.uSP.value = bt; box.mat.uniforms.uHasSP.value = 1;
  if (Q.has('shot')) window.__paint = { hero: PH, R: PR, L: PL, hoard: PHo, ground: PG, box: PB };
}

// ============================================================ signs
const signs = [];
let atlas, screen;
function addSign(o) {
  const { pos, a, n } = onFace(o.tower, o.face || 0, o.u, o.v, o.out ?? 0.35);
  const vert = !!o.vertical;
  const mat = new THREE.ShaderMaterial({
    uniforms: {
      ...U, uAtlas: { value: vert ? atlas.vtex : atlas.tex },
      uA: { value: vert ? atlas.vrect(0) : atlas.rect(o.corp) }, uB: { value: vert ? atlas.vrect(0) : atlas.rect(o.corp) },
      uProg: { value: 0 }, uSA: { value: o.w / o.h }, uTA: { value: vert ? 0.5 : 1 }, uSeed: { value: signs.length * 3.7 + 1 },
      uGain: { value: o.gain ?? 2 }, uScreen: { value: o.screen ? 1 : 0 }, uGlitch: { value: 0 },
      uSP: { value: blankTex }, uHasSP: { value: 0 }, uSPTex: { value: new THREE.Vector2(1 / 512, 1 / 512) },
    }, vertexShader: VS_WORLD, fragmentShader: FS_SIGN,
  });
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(o.w, o.h), mat);
  mesh.position.copy(pos); mesh.rotation.y = a;
  scene.add(mesh);
  // a dark housing behind it
  const housing = new THREE.Mesh(new THREE.BoxGeometry(o.w + 0.5, o.h + 0.5, 0.5), new THREE.MeshBasicMaterial({ color: 0x030405 }));
  housing.position.copy(pos).addScaledVector(n, -0.27); housing.rotation.y = a; scene.add(housing);
  // glow in the wet air in front of it
  const halo = new THREE.Mesh(new THREE.PlaneGeometry(o.w * 2.4, o.h * 2.4), new THREE.ShaderMaterial({
    uniforms: { uCol: { value: V3() }, uOp: { value: o.halo ?? 0.16 } }, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    vertexShader: `varying vec2 vUv; void main(){ vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.); }`,
    fragmentShader: `uniform vec3 uCol; uniform float uOp; varying vec2 vUv; void main(){ vec2 q=(vUv-.5)*2.; float r=length(q*vec2(1.,1.)); float a=pow(max(1.-r,0.),2.2); gl_FragColor=vec4(uCol*a*uOp,1.); }`,
  }));
  halo.position.copy(pos).addScaledVector(n, 1.2); halo.rotation.y = a; scene.add(halo);
  const s = {
    ...o, mesh, mat, halo, n, pos, vert,
    corpRect: vert ? atlas.vrect(0) : atlas.rect(o.corp), cur: vert ? 'v0' : o.corp, t0: -1, pending: null,
    colA: vert ? atlas.vm[0] : atlas.means[o.corp], colB: null, light: o.light ?? -1,
  };
  s.colNow = s.colA.clone();
  mesh.userData.sign = s;
  signs.push(s);
  return s;
}
function buildSigns() {
  const K = { kolvane: 0, novarch: 1, tessarine: 2, ostraven: 3 };
  screen = addSign({ id: 'screen', tower: 'hero', u: 24, v: 36.2, w: 22, h: 12.4, corp: K.novarch, screen: true, gain: 1.45, light: 0, rebel: 4, halo: 0.2 });
  addSign({ id: 'heroCrown', tower: 'hero', u: 24, v: 144, w: 18, h: 18, corp: K.novarch, gain: 2.4, rebel: 5 });
  addSign({ id: 'heroPod', tower: 'hero', u: 6.6, v: 5.2, w: 5, h: 5, corp: K.ostraven, gain: 1.7, light: 4, rebel: 4 });
  addSign({ id: 'Lblade', tower: 'L', u: 27, v: 34, w: 5, h: 30, corp: 0, vertical: true, gain: 2.1, light: 2, rebel: 'v1' });
  addSign({ id: 'Lcrown', tower: 'L', u: 16, v: 132, w: 16, h: 16, corp: K.kolvane, gain: 2.4, rebel: 4 });
  addSign({ id: 'Lpod', tower: 'L', u: 22, v: 5.5, w: 5, h: 5, corp: K.kolvane, gain: 1.7, light: 3, rebel: 5 });
  addSign({ id: 'Rbox', tower: 'R', u: 21, v: 22, w: 12, h: 12, corp: K.tessarine, gain: 1.9, light: 5, rebel: 5 });
  addSign({ id: 'Rcrown', tower: 'R', u: 15, v: 158, w: 16, h: 16, corp: K.tessarine, gain: 2.4, rebel: 5 });
  addSign({ id: 'Rpod', tower: 'R', u: 7.5, v: 5.5, w: 5, h: 5, corp: K.ostraven, gain: 1.7, light: 6, rebel: 4 });
  addSign({ id: 'BLcrown', tower: 'BL', u: 18, v: 222, w: 20, h: 20, corp: K.ostraven, gain: 2.6, rebel: 4 });
  addSign({ id: 'BLblade', tower: 'BL', u: 5, v: 80, w: 6, h: 36, corp: 0, vertical: true, gain: 2, rebel: 'v1' });
  addSign({ id: 'BRcrown', tower: 'BR', u: 16, v: 200, w: 18, h: 18, corp: K.novarch, gain: 2.6, rebel: 5 });
  addSign({ id: 'BRmid', tower: 'BR', u: 24, v: 60, w: 12, h: 12, corp: K.tessarine, gain: 2, rebel: 4 });
}
const SPILL = { corp: new THREE.Color(0.26, 0.29, 0.42), rebel: new THREE.Color(0.09, 0.22, 0.52) };
function rectFor(s, key) { return typeof key === 'string' ? atlas.vrect(+key.slice(1)) : atlas.rect(key); }
function meanFor(key) { return typeof key === 'string' ? atlas.vm[+key.slice(1)] : atlas.means[key]; }
function swapSign(s, key, delay) { s.pending = { key, at: REDUCED ? now : now + delay }; }

// ============================================================ rain, sheets, steam, the drone
let rain, sheets = [], steam, drone, cone;
function buildRain() {
  const n = PHONE ? 2600 : 7000, R = rng(7);
  const pos = new Float32Array(n * 6), seed = new Float32Array(n * 8), end = new Float32Array(n * 2);
  for (let i = 0; i < n; i++) {
    const s = [R(), R(), R(), R()];
    for (let k = 0; k < 2; k++) { seed.set(s, (i * 2 + k) * 4); end[i * 2 + k] = k; }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.setAttribute('aSeed', new THREE.BufferAttribute(seed, 4));
  g.setAttribute('aEnd', new THREE.BufferAttribute(end, 1));
  rain = new THREE.LineSegments(g, new THREE.ShaderMaterial({
    uniforms: { ...U }, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    vertexShader: `${COMMON} attribute vec4 aSeed; attribute float aEnd; varying float vE; varying vec3 vW;
      void main(){
        vec3 box = vec3(44., 34., 44.);
        vec3 p = aSeed.xyz*box;
        float sp = 10. + aSeed.w*5.;
        p.y = mod(p.y - uTime*sp, box.y);
        p.xz = mod(p.xz - cameraPosition.xz + box.xz*.5, box.xz) + cameraPosition.xz - box.xz*.5;
        p += vec3(1.6, -sp, 0.5) * aEnd * 0.042;
        vW = p; vE = aEnd;
        gl_Position = projectionMatrix*viewMatrix*vec4(p,1.);
      }`,
    fragmentShader: `${COMMON} varying float vE; varying vec3 vW;
      void main(){
        float d = length(vW-cameraPosition);
        vec3 c = vec3(.05,.06,.085) + lights(vW, normalize(cameraPosition-vW))*0.35 + vec3(.8,.9,1.)*uSpotI*spotCone(vW)*0.5 + vec3(.3,.34,.45)*uFlash;
        float a = mix(0.15, 1., vE) * smoothstep(0.6, 3., d) * (1.-smoothstep(16., 30., d));
        gl_FragColor = vec4(c*a*0.55, 1.);
      }`,
  }));
  rain.frustumCulled = false; scene.add(rain);
  // sheets of rain further out, moving with the wind
  const sheetMat = (w, h, s) => new THREE.ShaderMaterial({
    uniforms: { ...U, uWH: { value: new THREE.Vector2(w, h) }, uS: { value: s } }, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
    vertexShader: VS_WORLD,
    fragmentShader: `${COMMON} uniform vec2 uWH; uniform float uS; varying vec2 vUv; varying vec3 vW;
      void main(){
        vec2 m = vUv*uWH;
        float streak = smoothstep(.62,.95, vnoise(vec2(m.x*2.6 + m.y*0.12, m.y*0.09 + uTime*1.9 + uS)));
        float gust = smoothstep(.3,.8, fbm(vec2(m.x*0.03 - uTime*0.12 + uS, uTime*0.05)));
        float edge = smoothstep(0.,.15,vUv.x)*smoothstep(1.,.85,vUv.x)*smoothstep(0.,.1,vUv.y)*smoothstep(1.,.6,vUv.y);
        vec3 c = (uFogCol*5. + lights(vW, vec3(0,0,1))*0.6 + vec3(.25,.3,.4)*uFlash + vec3(.6,.7,.8)*uSpotI*spotCone(vW)*0.6);
        gl_FragColor = vec4(c*streak*gust*edge*0.16, 1.);
      }`,
  });
  [[0, 14, 6, 70, 40, 1], [-10, 14, -6, 80, 50, 2], [12, 16, 10, 60, 36, 3], [0, 20, -14, 90, 60, 4]].forEach(([x, y, z, w, h, s]) => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), sheetMat(w, h, s)); m.position.set(x, y, z); m.rotation.y = (s - 2.5) * 0.15; scene.add(m); sheets.push(m);
  });
}
function buildSteam() {
  const per = PHONE ? 18 : 34, n = per * VENTS.length, R = rng(99);
  const base = new THREE.PlaneGeometry(1, 1);
  const g = new THREE.InstancedBufferGeometry(); g.index = base.index; g.attributes.position = base.attributes.position; g.attributes.uv = base.attributes.uv;
  const ip = new Float32Array(n * 3), is = new Float32Array(n * 4);
  for (let i = 0; i < n; i++) { const v = VENTS[Math.floor(i / per)]; ip.set([v[0], 0.05, v[1]], i * 3); is.set([R(), R(), R(), R()], i * 4); }
  g.setAttribute('iPos', new THREE.InstancedBufferAttribute(ip, 3)); g.setAttribute('iSeed', new THREE.InstancedBufferAttribute(is, 4));
  g.instanceCount = n;
  steam = new THREE.Mesh(g, new THREE.ShaderMaterial({
    uniforms: { ...U }, transparent: true, depthWrite: false,
    vertexShader: `uniform float uTime; attribute vec3 iPos; attribute vec4 iSeed; varying vec2 vUv; varying float vA; varying vec3 vW; varying float vS;
      void main(){
        float life = 6. + iSeed.y*5.;
        float age = fract(uTime/life + iSeed.x);
        vec3 p = iPos + vec3((iSeed.z-.5)*0.7 + sin(age*3.+iSeed.w*6.)*0.5*age + age*2.2, age*8., (iSeed.w-.5)*0.7 + age*0.8);
        float size = 1.1 + age*6.;
        vec3 right = vec3(viewMatrix[0][0], viewMatrix[1][0], viewMatrix[2][0]);
        vec3 up = vec3(viewMatrix[0][1], viewMatrix[1][1], viewMatrix[2][1]);
        vec3 w = p + (right*position.x + up*position.y)*size;
        vW = w; vUv = uv; vS = iSeed.w*10.; vA = smoothstep(0.,.1,age)*(1.-age);
        gl_Position = projectionMatrix*viewMatrix*vec4(w,1.);
      }`,
    fragmentShader: `${COMMON} varying vec2 vUv; varying float vA; varying vec3 vW; varying float vS;
      void main(){
        float r = length(vUv-.5)*2.;
        float a = pow(max(1.-r,0.),1.6) * (0.45+0.9*fbm(vUv*2.6+vS+uTime*0.05)) * vA * 0.12;
        vec3 c = uFogCol*7. + lights(vW, normalize(cameraPosition-vW))*0.7 + vec3(.8,.9,1.)*uSpotI*spotCone(vW)*0.6 + vec3(.3,.35,.45)*uFlash;
        gl_FragColor = vec4(c, a);
      }`,
  }));
  steam.frustumCulled = false; scene.add(steam);
}
function buildDrone() {
  drone = new THREE.Group();
  const dark = new THREE.MeshBasicMaterial({ color: 0x07080a });
  const body = new THREE.Mesh(new THREE.BoxGeometry(1.5, 0.32, 1.0), dark); drone.add(body);
  const pod = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.3, 0.5), dark); pod.position.y = -0.3; drone.add(pod);
  [[-1, -1], [1, -1], [-1, 1], [1, 1]].forEach(([x, z]) => {
    const arm = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.06, 0.08), dark); arm.position.set(x * 0.85, 0.05, z * 0.6); arm.rotation.y = x * z * 0.6; drone.add(arm);
    const disc = new THREE.Mesh(new THREE.CircleGeometry(0.55, 24), new THREE.MeshBasicMaterial({ color: 0x1a1d22, transparent: true, opacity: 0.35, side: THREE.DoubleSide, depthWrite: false }));
    disc.rotation.x = -Math.PI / 2; disc.position.set(x * 1.2, 0.12, z * 0.85); drone.add(disc);
  });
  drone.nav = [new THREE.Mesh(new THREE.SphereGeometry(0.09, 8, 6), new THREE.MeshBasicMaterial({ color: new THREE.Color(4, 0.25, 0.3) })), new THREE.Mesh(new THREE.SphereGeometry(0.09, 8, 6), new THREE.MeshBasicMaterial({ color: new THREE.Color(5, 5, 5.5) }))];
  drone.nav[0].position.set(-0.8, 0, 0.5); drone.nav[1].position.set(0.8, 0, -0.5); drone.nav.forEach(m => drone.add(m));
  const lamp = new THREE.Mesh(new THREE.SphereGeometry(0.16, 10, 8), new THREE.MeshBasicMaterial({ color: new THREE.Color(14, 15, 16) })); lamp.position.y = -0.46; drone.add(lamp);
  scene.add(drone);
  const cg = new THREE.CylinderGeometry(0.1, 1, 1, 40, 1, true); cg.translate(0, -0.5, 0);
  cone = new THREE.Mesh(cg, new THREE.ShaderMaterial({
    uniforms: { ...U }, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
    vertexShader: `varying float vT; varying vec3 vN; varying vec3 vV; varying vec3 vW;
      void main(){ vT = -position.y; vN = normalize(normalMatrix*normal); vec4 mv = modelViewMatrix*vec4(position,1.); vV = -mv.xyz; vW = (modelMatrix*vec4(position,1.)).xyz; gl_Position = projectionMatrix*mv; }`,
    fragmentShader: `${COMMON} varying float vT; varying vec3 vN; varying vec3 vV; varying vec3 vW;
      void main(){
        float e = abs(dot(normalize(vN), normalize(vV)));
        float motes = 0.7 + 0.6*vnoise(vec2(vT*30. - uTime*2., atan(vN.x,vN.z)*6.));
        float a = pow(e, 1.6) * pow(1.-vT, 1.3) * smoothstep(0.,.03,vT) * motes;
        gl_FragColor = vec4(vec3(.75,.85,1.)*a*0.075*uSpotI, 1.);
      }`,
  }));
  cone.frustumCulled = false; scene.add(cone);
}

// ============================================================ post
const FinalShader = {
  uniforms: { tDiffuse: { value: null }, uTime: { value: 0 }, uFade: { value: 1 }, uFlash: { value: 0 }, uRes: { value: new THREE.Vector2(1, 1) } },
  vertexShader: `varying vec2 vUv; void main(){ vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.); }`,
  fragmentShader: `uniform sampler2D tDiffuse; uniform float uTime, uFade, uFlash; uniform vec2 uRes; varying vec2 vUv;
    float h(vec2 p){ vec3 p3 = fract(vec3(p.xyx) * .1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
    void main(){
      vec2 c = vUv-.5; float r2 = dot(c,c);
      vec3 col;
      col.r = texture2D(tDiffuse, vUv - c*0.0035).r; col.g = texture2D(tDiffuse, vUv).g; col.b = texture2D(tDiffuse, vUv + c*0.0035).b;
      col *= 1. - r2*1.05;
      col += vec3(.012,.014,.02)*uFlash;
      float g = h(vUv*uRes + fract(uTime*7.)*100.) - .5;
      col += g*0.006 + g*col*0.12;
      col = max(col, 0.) * uFade;
      gl_FragColor = vec4(col, 1.);
    }`,
};
let composer, bloom, finalPass;
function buildPost() {
  composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, camera));
  bloom = new UnrealBloomPass(new THREE.Vector2(innerWidth / 2, innerHeight / 2), 0.62, 0.55, 0.62);
  composer.addPass(bloom);
  finalPass = new ShaderPass(FinalShader); composer.addPass(finalPass);
  composer.addPass(new OutputPass());
}

// ============================================================ the environment map, taken from the plaza
let cubeRT, cubeCam, cubeDummy;
function buildEnv() {
  cubeRT = new THREE.WebGLCubeRenderTarget(PHONE ? 128 : 256, { type: THREE.HalfFloatType, generateMipmaps: true, minFilter: THREE.LinearMipmapLinearFilter });
  cubeCam = new THREE.CubeCamera(1, 3000, cubeRT); cubeCam.position.set(0, 22, 4);
  cubeDummy = new THREE.WebGLCubeRenderTarget(4);
  U.uEnv.value = cubeRT.texture;
}
function renderEnv() {
  U.uEnvOn.value = 0; U.uEnv.value = cubeDummy.texture;
  const hide = [rain, steam, cone, ...sheets, ...signs.map(s => s.halo)];
  hide.forEach(o => o.visible = false);
  cubeCam.update(renderer, scene);
  hide.forEach(o => o.visible = true);
  U.uEnv.value = cubeRT.texture; U.uEnvOn.value = 1;
}

// ============================================================ live spray
const live = new Map();
const raycaster = new THREE.Raycaster();
function liveFor(obj) {
  if (live.has(obj)) return live.get(obj);
  let P, mat, map;
  if (obj === ground) {
    P = new Painter({ u0: -60, v0: -60, u1: 60, v1: 60, pxm: PHONE ? 7 : 10, drips: false });
    mat = ground.material; map = (pt) => [P.x(pt.x), P.y(-pt.z)];
  } else {
    const W = obj.userData.wall, top = Math.min(W.h, 110);
    P = new Painter({ u0: 0, v0: 0, u1: W.w, v1: top, pxm: W === walls.hoard ? 60 : (PHONE ? 10 : 18), drips: false, ledges: W.podium > 0 ? ledgesFor(W.podium, top) : [] });
    mat = W.mat; map = (pt, uv) => [P.x(uv.x * W.w), P.y(uv.y * W.h)];
  }
  const L = new LiveLayer(P);
  const t = new THREE.CanvasTexture(P.c); t.premultiplyAlpha = true; t.colorSpace = THREE.NoColorSpace;
  mat.uniforms.uLive.value = t; mat.uniforms.uHasLive.value = 1;
  mat.uniforms.uLR.value.set(P.u0, P.v0, P.u1, P.v1); mat.uniforms.uLTex.value.set(1 / P.W, 1 / P.H);
  const e = { L, P, t, map, lastUp: 0, mat };
  live.set(obj, e);
  return e;
}
const paintables = () => [...Object.values(walls).map(w => w.mesh), ground];
const blockers = () => signs.map(s => s.mesh);
function sprayAt(nx, ny, dt) {
  raycaster.setFromCamera({ x: nx, y: ny }, camera);
  const hits = raycaster.intersectObjects([...paintables(), ...blockers()], false);
  if (!hits.length) { lastLive && lastLive.L.lift(); lastLive = null; return null; }
  const h = hits[0];
  if (h.object.userData.sign) { lastLive && lastLive.L.lift(); lastLive = null; return null; }
  const e = liveFor(h.object);
  if (lastLive && lastLive !== e) lastLive.L.lift();
  lastLive = e;
  const [x, y] = e.map(h.point, h.uv || { x: 0, y: 0 });
  const rWorld = Math.min(1.3, Math.max(0.07, h.distance * 0.0125));
  e.L.sprayTo(x, y, rWorld * e.P.pxm, dt, now);
  return h;
}
let lastLive = null;

// ============================================================ state, time, input
let now = 0, last = performance.now() / 1000, introT0 = 0, introDone = !INTRO, state = 'corp';
let look = { yaw: 0, pitch: 0 }, target = { yaw: 0, pitch: 0 }, ptr = { x: 0, y: 0, has: false };
let rest = { yaw: 0, pitch: 0.27, z: 34 };
const sound = new Sound();
const flashes = [];
function planFlashes() {
  const R = rng(161);
  let t = 16;
  for (let i = 0; i < 60; i++) { flashes.push({ t, dir: V3(R() - 0.5, 0.35 + R() * 0.4, -0.4 - R() * 0.6).normalize(), near: R() < 0.35, k: 0.6 + R() * 0.6, heard: false }); t += 13 + R() * 20; }
  if (INTRO) flashes.unshift({ t: 5.75, dir: V3(0.15, 0.62, -0.77).normalize(), near: true, k: 1.15, heard: false });
}
function flashAt(t) {
  if (REDUCED) return { v: 0, dir: null };
  let v = 0, dir = null;
  for (const f of flashes) {
    const d = t - f.t; if (d < 0 || d > 2) continue;
    const p = (Math.exp(-d * 10) + 0.85 * (d > 0.17 ? Math.exp(-(d - 0.17) * 6) : 0) + 0.35 * (d > 0.42 ? Math.exp(-(d - 0.42) * 9) : 0)) * f.k;
    if (p > v) { v = p; dir = f.dir; }
    if (!f.heard && FREEZE === null) { f.heard = true; sound.thunder(f.near ? 0.5 + Math.random() * 0.5 : 1.6 + Math.random() * 1.5, f.near); }
  }
  return { v, dir };
}

const ui = document.getElementById('ui'), typeEl = document.getElementById('type'), hint = document.getElementById('hint');
const TYPE_LABEL = 'ANTIMONY //:', TYPE_REST = ' LONDON', TYPE0 = 0.6, CH = 0.08;
function renderType(t) {
  if (!INTRO || introDone) { typeEl.style.opacity = 0; return; }
  const full = TYPE_LABEL + TYPE_REST, n = Math.max(0, Math.min(full.length, Math.floor((t - TYPE0) / CH) + 1));
  const typing = t < TYPE0 + full.length * CH + 0.25;
  const k = typing ? Math.min(3, n) : 0;
  const shown = full.slice(0, n), body = shown.slice(0, n - k), hl = shown.slice(n - k);
  const lab = body.slice(0, TYPE_LABEL.length), rest = body.slice(TYPE_LABEL.length);
  const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;');
  typeEl.innerHTML = `<span class="lab">${esc(lab)}</span><span>${esc(rest)}</span>${hl ? `<mark>${esc(hl)}</mark>` : ''}`;
  typeEl.style.opacity = t < TYPE0 ? 0 : t < 3.0 ? 1 : Math.max(0, 1 - (t - 3.0) / 0.7);
}

function easeIO(x) { x = Math.min(1, Math.max(0, x)); return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; }
function easeO(x) { x = Math.min(1, Math.max(0, x)); return 1 - Math.pow(1 - x, 3); }

function skipIntro() {
  if (introDone) return;
  introDone = true; store.set(KEY, '1');
  U.uDrip.value = 1; U.uReveal.value = 1; uvTarget = 0.75; typeEl.style.opacity = 0;
  look.yaw = target.yaw = rest.yaw; look.pitch = target.pitch = rest.pitch;
  showUI();
}
function showUI() { ui.classList.add('on'); document.getElementById('snd').classList.add('on'); document.getElementById('work').classList.add('on'); }

function layout() {
  const w = innerWidth, h = innerHeight, asp = w / h;
  camera.fov = asp < 0.8 ? 64 : 56; camera.aspect = asp; camera.updateProjectionMatrix();
  const hf = 2 * Math.atan(Math.tan(camera.fov * Math.PI / 360) * asp);
  const D = Math.max(46, 25 / Math.tan(hf / 2));
  rest.z = -18 + D;
  rest.pitch = Math.atan((24 - 1.7) / D) - (asp < 0.8 ? 0.06 : 0.17);
  camera.position.set(0, 1.7, rest.z);
  renderer.setPixelRatio(baseDPR() * quality);
  renderer.setSize(w, h, false);
  composer && composer.setSize(w, h);
  composer && composer.setPixelRatio && composer.setPixelRatio(baseDPR() * quality);
  finalPass && finalPass.uniforms.uRes.value.set(w, h);
  const s = PHONE ? 0.36 : 0.5;
  reflRT && reflRT.setSize(Math.round(w * s * quality), Math.round(h * s * quality));
}

// ---- pointer
let down = null, spraying = false;
function ndc(e) { return { x: (e.clientX / innerWidth) * 2 - 1, y: -(e.clientY / innerHeight) * 2 + 1 }; }
function pickSign(e) {
  raycaster.setFromCamera(ndc(e), camera);
  const hits = raycaster.intersectObjects([...paintables(), ...blockers()], false);
  return hits.length && hits[0].object.userData.sign ? hits[0].object.userData.sign : null;
}
const isTrigger = s => s && (s.id === 'screen' || s.id === 'Rbox');
el.addEventListener('pointerdown', e => {
  if (!introDone) { skipIntro(); return; }
  if (sound.on) sound.start();
  el.setPointerCapture(e.pointerId);
  const sg = pickSign(e);
  down = { x: e.clientX, y: e.clientY, t: performance.now(), sign: sg, id: e.pointerId };
  ptr.x = e.clientX / innerWidth * 2 - 1; ptr.y = e.clientY / innerHeight * 2 - 1; ptr.has = true;
  const clicky = isTrigger(sg) || (sg && sg.product && state === 'rebel');
  if (!clicky) startSpray();
});
let sprayT0 = 0;
function startSpray() { if (spraying) return; spraying = true; sprayT0 = performance.now(); sound.rattle(); }
function stopSpray() { spraying = false; sound.spray(false); lastLive && lastLive.L.lift(); lastLive = null; }
el.addEventListener('pointermove', e => {
  ptr.x = e.clientX / innerWidth * 2 - 1; ptr.y = e.clientY / innerHeight * 2 - 1; ptr.has = true;
  if (down && !spraying && (Math.hypot(e.clientX - down.x, e.clientY - down.y) > 8)) startSpray();
  if (!down && introDone) {
    const sg = pickSign(e);
    el.style.cursor = (isTrigger(sg) && state === 'corp') || (sg && sg.product && state === 'rebel') ? 'pointer' : '';
  }
});
const endPtr = e => {
  if (!down) return;
  const moved = Math.hypot(e.clientX - down.x, e.clientY - down.y), dt = performance.now() - down.t;
  if (!spraying && moved < 8 && dt < 600) {
    const sg = down.sign;
    if (isTrigger(sg)) { state === 'corp' ? takeover(sg) : null; }
    else if (sg && sg.product && state === 'rebel') { const w = WORK[sg.product]; window.open(w.url, '_blank', 'noopener'); }
  }
  stopSpray(); down = null;
  if (e.pointerType !== 'mouse') ptr.has = false;
};
el.addEventListener('pointerup', endPtr);
el.addEventListener('pointercancel', endPtr);
el.addEventListener('pointerleave', e => { if (e.pointerType === 'mouse' && !down) ptr.has = false; });
addEventListener('keydown', e => {
  if (!introDone) { skipIntro(); return; }
  if (e.key === 'Escape') revert();
});
addEventListener('wheel', () => { if (!introDone) skipIntro(); }, { passive: true });
document.getElementById('take').addEventListener('click', () => { if (!introDone) skipIntro(); state === 'corp' ? takeover(screen) : revert(); });

// ---- sound toggle
const sndBtn = document.getElementById('snd');
function setSound(v) { sound.setOn(v); sndBtn.setAttribute('aria-pressed', v ? 'true' : 'false'); sndBtn.classList.toggle('live', v); store.set(SKEY, v ? '1' : '0'); }
sndBtn.addEventListener('click', e => { e.stopPropagation(); setSound(!sound.on); });
if (store.get(SKEY) === '1') {
  // the stored choice is honoured, but the browser still needs a gesture to start the audio
  sndBtn.setAttribute('aria-pressed', 'true'); sndBtn.classList.add('live'); sound.on = true;
  const kick = () => { setSound(true); removeEventListener('pointerdown', kick, true); removeEventListener('keydown', kick, true); };
  addEventListener('pointerdown', kick, true); addEventListener('keydown', kick, true);
}

// ============================================================ the takeover
let uvTarget = 0.75, screenCycle = { next: 9, phase: 0, t0: 0 }, envDirtyAt = -1;
function takeover(origin) {
  if (state !== 'corp') return;
  state = 'rebel';
  sound.swell(true); sound.crackle(1.2, 1.6);
  const o = origin ? origin.pos : screen.pos;
  const order = signs.filter(s => s !== screen).sort((a, b) => a.pos.distanceTo(o) - b.pos.distanceTo(o));
  swapSign(screen, screen.rebel, 0);
  order.forEach((s, i) => swapSign(s, s.rebel, 0.45 + i * 0.32 + Math.random() * 0.12));
  envDirtyAt = now + 0.45 + order.length * 0.32 + 1.5;
  uvTarget = 1.25;
  hint.textContent = PHONE ? 'Ours for now.' : 'Ours for now. Escape gives it back.';
  document.getElementById('take').textContent = 'Give the plaza back';
}
function revert() {
  if (state !== 'rebel') return;
  state = 'corp';
  sound.swell(false); sound.crackle(0.8, 1);
  const order = [...signs].sort(() => Math.random() - 0.5);
  order.forEach((s, i) => swapSign(s, s.vert ? 'v0' : s.corp, 0.1 + i * 0.16));
  envDirtyAt = now + 0.1 + order.length * 0.16 + 1.4;
  uvTarget = 0.75;
  hint.textContent = HINT;
  document.getElementById('take').textContent = 'Take the plaza';
}
const HINT = PHONE ? 'Drag to spray. Tap the screen.' : 'Hold to spray. Take the screen.';
hint.textContent = HINT;

function updateSigns(dt) {
  // the hijacked feed: every so often the corporate screen loses its grip
  let glitch = 0;
  if (state === 'corp' && !screen.pending && screen.t0 < 0) {
    const c = screenCycle;
    if (now > c.next) {
      const p = now - c.next;
      if (p < 0.55) { glitch = 0.9; screen.mat.uniforms.uProg.value = p > 0.3 ? 0.35 : 0.1; }
      else if (p < 3.2) { glitch = p < 0.9 ? 0.5 : 0.06; screen.mat.uniforms.uProg.value = 1; screen.mat.uniforms.uB.value = atlas.rect(4); }
      else if (p < 3.6) { glitch = 0.9; screen.mat.uniforms.uProg.value = 0.4; }
      else { screen.mat.uniforms.uProg.value = 0; c.next = now + 8 + Math.random() * 7; }
      if (p < 0.05 || (p > 3.2 && p < 3.25)) sound.crackle(0.5, 1);
    }
  }
  if (state === 'rebel' && Math.random() < dt * 0.15) { screen.mat.uniforms.uGlitch.value = 0.6; sound.crackle(0.25, 0.6); }
  screen.mat.uniforms.uGlitch.value = Math.max(glitch, screen.mat.uniforms.uGlitch.value * Math.exp(-dt * 6));
  for (const s of signs) {
    const u = s.mat.uniforms;
    if (s.pending && now >= s.pending.at) {
      u.uA.value = rectFor(s, s.cur); u.uB.value = rectFor(s, s.pending.key);
      s.colB = meanFor(s.pending.key); s.colFrom = s.colNow.clone();
      s.cur = s.pending.key; s.t0 = now; s.pending = null;
      if (s === screen || Math.random() < 0.5) sound.crackle(0.3, 0.5);
    }
    if (s.t0 >= 0) {
      const p = REDUCED ? 1 : (now - s.t0) / 1.3;
      u.uProg.value = Math.min(1, p);
      s.colNow.copy(s.colFrom).lerp(s.colB, easeO(p));
      if (p >= 1) { u.uA.value = u.uB.value.clone(); u.uProg.value = 0; s.t0 = -1; }
    }
    // the light each sign throws into the wet
    let k = s.colNow, flick = (s.t0 >= 0) ? (Math.random() < 0.6 ? 1 : 0.2) : 1;
    if (s === screen) k = (state === 'rebel' ? s.t0 < 0 || u.uProg.value > 0.5 : u.uProg.value > 0.5) ? SPILL.rebel : SPILL.corp;
    const g = u.uGain.value * flick;
    s.halo.material.uniforms.uCol.value.set(k.r * g, k.g * g, k.b * g);
    const sp = s === screen ? 3.2 : 1.0;
    if (s.light >= 0) U.uLCol.value[s.light].set(k.r * g * sp, k.g * g * sp, k.b * g * sp);
  }
  return glitch;
}

// ============================================================ frame
let fpsAcc = 0, fpsN = 0, lastQ = 0, running = true, frameSkip = false;
let shotFrames = 0, lastStill = 0, stillDirty = true;
function frame() {
  if (!running) return;
  // capture mode: a frozen moment renders a few times, then holds still for the camera
  if (FREEZE !== null && Q.has('shot') && ++shotFrames > (+Q.get('shot') || 2)) { document.body.dataset.shot = '1'; return; }
  requestAnimationFrame(frame);
  const tn = performance.now() / 1000;
  let dt = Math.min(0.1, tn - last);
  if (PHONE) { frameSkip = !frameSkip; if (frameSkip) return; } // phones hold thirty frames a second
  // reduced motion: a still frame, redrawn only when the visitor does something
  if (REDUCED && introDone && !spraying && !down && tn - lastStill < 1.5 && !stillDirty) return;
  lastStill = tn; stillDirty = false;
  last = tn;
  if (FREEZE !== null) { now = FREEZE; dt = 1 / 60; }
  else if (REDUCED) { now = 20; }
  else now += dt;
  tick(dt);
  // adaptive quality
  if (FREEZE === null) {
    fpsAcc += dt; fpsN++;
    if (fpsN >= 60) {
      const ms = fpsAcc / fpsN * 1000; fpsAcc = 0; fpsN = 0;
      const budget = PHONE ? 40 : 22;
      if (!Q.has('q') && ms > budget && quality > 0.55 && tn - lastQ > 2) { quality *= 0.85; lastQ = tn; layout(); }
      else if (!Q.has('q') && ms < budget * 0.6 && quality < 1 && tn - lastQ > 4) { quality = Math.min(1, quality * 1.1); lastQ = tn; layout(); }
    }
  }
}

function tick(dt) {
  const t = now;
  U.uTime.value = REDUCED ? 20 : t;
  // ---- intro
  let fade = 1;
  if (INTRO && !introDone) {
    renderType(t);
    fade = easeO((t - 1.6) / 1.9) * (t < 1.6 ? 0 : 1);
    const k = easeIO((t - 3.5) / 3.1);
    look.yaw = -0.1 * (1 - k) + rest.yaw * k;
    look.pitch = -0.62 * (1 - k) + rest.pitch * k;
    target.yaw = look.yaw; target.pitch = look.pitch;
    U.uDrip.value = Math.pow(Math.min(1, Math.max(0, (t - 4.7) / 5.5)), 0.85);
    // the rebels' ultraviolet floods stutter on after the strike
    const r = t < 5.78 ? 0 : t < 6.6 ? (Math.sin(t * 61) > 0.1 - (t - 5.78) * 1.4 ? 1 : 0.15) * Math.min(1, (t - 5.78) / 0.5) : 1;
    U.uReveal.value = r; uvTarget = 0.75 * r; U.uUV.value = uvTarget;
    if (t > 6.9) showUI();
    if (t >= INTRO_END) { introDone = true; store.set(KEY, '1'); typeEl.style.opacity = 0; U.uReveal.value = 1; uvTarget = 0.75; }
  } else {
    if (U.uDrip.value < 1) U.uDrip.value = Math.min(1, U.uDrip.value + dt / 5.5);
    // ---- look around
    const damp = spraying ? 0.3 : 1;
    if (ptr.has && !REDUCED) {
      const up = -ptr.y;
      target.yaw = rest.yaw - ptr.x * (PHONE ? 0.22 : 0.44);
      target.pitch = rest.pitch + (up > 0 ? Math.pow(up, 1.25) * (PHONE ? 0.55 : 0.62) : up * 0.3);
    } else if (!REDUCED) {
      target.yaw = rest.yaw + Math.sin(t * 0.07) * 0.03;
      target.pitch = rest.pitch + Math.sin(t * 0.053) * 0.012;
    }
    const a = 1 - Math.exp(-dt * 2.6 * damp);
    look.yaw += (target.yaw - look.yaw) * a; look.pitch += (target.pitch - look.pitch) * a;
    if (FREEZE !== null && !ptr.has) { look.yaw = target.yaw = rest.yaw; look.pitch = target.pitch = rest.pitch; }
  }
  if (Q.has('look')) { const [y, p] = Q.get('look').split(',').map(Number); look.yaw = y; look.pitch = p; }
  camera.rotation.set(look.pitch, look.yaw, 0);
  camera.updateMatrixWorld();

  // ---- lightning
  const fl = flashAt(t);
  U.uFlash.value = fl.v; if (fl.dir) U.uFlashDir.value.copy(fl.dir);
  finalPass.uniforms.uFlash.value = fl.v; finalPass.uniforms.uTime.value = t; finalPass.uniforms.uFade.value = fade;

  // ---- the drone and its light
  const da = t * 0.055 + 1.0;
  const dp = V3(Math.sin(da) * 26, 42 + Math.sin(t * 0.31) * 2.5, -2 + Math.cos(da) * 13);
  const prevD = drone.position.clone();
  drone.position.copy(dp); drone.rotation.set(Math.sin(t * 0.7) * 0.04, -da + Math.PI / 2, Math.cos(t * 0.5) * 0.05);
  drone.nav[0].visible = Math.sin(t * 6) > 0.7; drone.nav[1].visible = Math.sin(t * 4 + 1) > 0.92;
  const aim = V3(Math.sin(t * 0.19) * 17 + Math.sin(t * 0.47) * 3, 21 + Math.sin(t * 0.29) * 6, -18);
  if (INTRO && !introDone) aim.set(-6 + (t - 3) * 2.2, 24, -18);
  const dir = aim.clone().sub(dp); const len = dir.length() * 1.15; dir.normalize();
  U.uSpotPos.value.copy(dp).y -= 0.5; U.uSpotDir.value.copy(dir);
  cone.position.copy(U.uSpotPos.value);
  cone.quaternion.setFromUnitVectors(V3(0, -1, 0), dir);
  const rad = len * Math.tan(0.075); cone.scale.set(rad, len, rad);

  // ---- signs, screen, ultraviolet
  const glitch = updateSigns(dt);
  if (introDone) { U.uUV.value += (uvTarget - U.uUV.value) * (1 - Math.exp(-dt * (REDUCED ? 30 : 1.2))); if (FREEZE === null && !REDUCED) U.uUV.value *= 1 + (Math.random() < 0.02 ? -0.08 : 0); }
  if (REDUCED && signs.some(s => s.pending || s.t0 >= 0)) stillDirty = true;
  if (envDirtyAt > 0 && now > envDirtyAt) { envDirtyAt = -1; renderEnv(); }

  // ---- live paint
  if (spraying && ptr.has) {
    const h = sprayAt(ptr.x, -ptr.y, dt);
    if (performance.now() - sprayT0 > 280) sound.spray(!!h, 0);
  }
  for (const [, e] of live) {
    e.L.step(dt, now);
    if (e.L.dirty && performance.now() - e.lastUp > 40) { e.t.needsUpdate = true; e.L.dirty = false; e.lastUp = performance.now(); }
    e.mat.uniforms.uHasLive.value = (e.L.used || e.L.drips.length) ? 1 : 0;
  }

  // ---- sound follows the eye
  if (sound.ctx) {
    const fwd = V3(0, 0, -1).applyQuaternion(camera.quaternion);
    const right = V3(1, 0, 0).applyQuaternion(camera.quaternion);
    const toS = screen.pos.clone().sub(camera.position).normalize();
    const toD = drone.position.clone().sub(camera.position);
    const dd = toD.length(); toD.normalize();
    const radial = (drone.position.distanceTo(camera.position) - prevD.distanceTo(camera.position)) / Math.max(dt, 1e-3);
    sound.update({ screenFacing: Math.max(0, fwd.dot(toS)), screenPan: right.dot(toS) * 0.8, glitch: glitch > 0.3, droneDist: dd, dronePan: right.dot(toD), droneRadial: radial });
  }

  // ---- render: the reflection first, then the frame
  updateMirror();
  ground.visible = false; rain.visible = false; sheets.forEach(s => s.visible = false);
  renderer.setRenderTarget(reflRT); renderer.clear(); renderer.render(scene, mirrorCam); renderer.setRenderTarget(null);
  ground.visible = true; rain.visible = true; sheets.forEach(s => s.visible = true);
  composer.render(dt);
}

document.addEventListener('visibilitychange', () => {
  if (document.hidden) { running = false; sound.pause(true); }
  else { running = true; last = performance.now() / 1000; sound.pause(false); requestAnimationFrame(frame); }
});
addEventListener('resize', layout);

// ============================================================ go
async function init() {
  const tA = performance.now();
  await fontsReady();
  atlas = await buildAtlas();
  buildSky(); buildTowers(); buildFarCity(); buildGround(); buildHoarding(); buildSigns(); buildRain(); buildSteam(); buildDrone();
  buildPost(); buildEnv(); layout();
  const tB = performance.now();
  paintWorld(signs);
  if (Q.has('shot')) console.log('timing: build', Math.round(tB - tA), 'paint', Math.round(performance.now() - tB));
  planFlashes();
  // light positions: the screen, the lobby, the signs that throw light, a street lamp
  const lp = U.uLPos.value, lc = U.uLCol.value;
  lp[0].copy(screen.pos).addScaledVector(screen.n, 6);
  lp[1].set(0, 4, -15); lc[1].set(0.12, 0.14, 0.2);
  for (const s of signs) if (s.light > 0) lp[s.light].copy(s.pos).addScaledVector(s.n, 3);
  lp[7].set(-6, 6, 19); lc[7].set(0.1, 0.12, 0.17);
  updateSigns(0);
  // the first look, for the environment map
  look.yaw = rest.yaw; look.pitch = rest.pitch; camera.rotation.set(look.pitch, look.yaw, 0); camera.updateMatrixWorld();
  renderEnv();
  if (!INTRO) { introDone = true; U.uDrip.value = 1; showUI(); look.yaw = target.yaw = rest.yaw; look.pitch = target.pitch = rest.pitch; }
  else { look.yaw = -0.1; look.pitch = -0.62; U.uDrip.value = 0; U.uReveal.value = 0; uvTarget = 0; U.uUV.value = 0; }
  if (Q.has('takeover')) { takeover(screen); for (const s of signs) if (s.pending) s.pending.at = -10; now = FREEZE ?? 0; updateSigns(0); signs.forEach(s => { if (s.t0 >= 0) s.t0 = now - 5; }); updateSigns(0); renderEnv(); }
  if (Q.has('spray')) demoSpray();
  if (Q.has('shot')) document.body.classList.add('shot');
  document.body.classList.add('ready');
  requestAnimationFrame(frame);
  window.__reb = { takeover: () => takeover(screen), revert, demoSpray, skip: skipIntro, signs, atlas, state: () => state, live: () => live.size,
    project: id => { const s = signs.find(x => x.id === id); const v = s.pos.clone().project(camera); return [(v.x + 1) / 2 * innerWidth, (1 - v.y) / 2 * innerHeight]; } };
}

// a visitor's marks, for the record: used only by the ?spray hook
function demoSpray() {
  const pts = [];
  for (let i = 0; i <= 60; i++) { const k = i / 60; pts.push([-0.66 + k * 0.32, -0.02 + Math.sin(k * 9) * 0.06 + k * 0.1]); }
  for (let i = 0; i <= 40; i++) { const k = i / 40; pts.push([-0.34 + Math.cos(k * 6.28) * 0.05, 0.08 + Math.sin(k * 6.28) * 0.08]); }
  for (let i = 0; i <= 50; i++) { const k = i / 50; pts.push([0.42 + k * 0.22, -0.32 + Math.sin(k * 5) * 0.04]); }
  camera.rotation.set(rest.pitch, rest.yaw, 0); camera.updateMatrixWorld();
  let prev = null;
  pts.forEach(([x, y], i) => {
    if (prev && Math.hypot(x - prev[0], y - prev[1]) > 0.1) lastLive && lastLive.L.lift();
    now += 1 / 60; sprayAt(x, y, 1 / 60); prev = [x, y];
    // where the hand pauses, paint gathers and runs
    if (i % 17 === 0) for (let k = 0; k < 14; k++) { now += 1 / 30; sprayAt(x, y, 1 / 30); }
  });
  lastLive && lastLive.L.lift(); lastLive = null;
  for (let i = 0; i < 240; i++) { now += 1 / 30; for (const [, e] of live) e.L.step(1 / 30, now - 200); }
  for (const [, e] of live) { e.t.needsUpdate = true; e.mat.uniforms.uHasLive.value = 1; e.L.lastFade = 1e9; }
  now = FREEZE ?? 0;
}

init();
