"""The page system for the Antimony brand guidelines: CSS, the chapter head, sections, panels and the footer."""
import html as H
import re
import geo as g

CH = [("index", "Introduction"), ("logo", "Logo"), ("type", "Typography"), ("colour", "Colour"), ("motion", "Motion"),
      ("art", "Art direction"), ("use", "Brand in use"), ("downloads", "Downloads")]

CSS = r"""
@font-face { font-family: "Timeless Serif"; src: url(fonts/TimelessSerifVF.woff2) format("woff2"); font-weight: 200 700; font-display: swap; }
@font-face { font-family: "Timeless Serif"; src: url(fonts/TimelessSerifItalicVF.woff2) format("woff2"); font-weight: 200 700; font-style: italic; font-display: swap; }
@font-face { font-family: "Commit Mono"; src: url(fonts/CommitMono-Latin-VF.woff2) format("woff2"); font-weight: 200 700; font-display: swap; }
:root {
  --cream: #EEEAE0; --ink: #0B0C0C; --stone: #141311; --sky: #94E6FF; --pru: #1F3F7A; --cob: #2448FF; --washi: #F3ECDD;
  --fg: #0B0C0C; --rule: #0B0C0C; --hair: rgba(11, 12, 12, .2); --dim: rgba(11, 12, 12, .64);
  --serif: "Timeless Serif", "Iowan Old Style", Georgia, serif; --mono: "Commit Mono", ui-monospace, Menlo, monospace;
  --pad: 40px; --gap: 20px; color-scheme: light;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html { background: var(--cream) url(img/tex/grain-alpha.png) 0 0 / 128px 128px; color: var(--fg); -webkit-text-size-adjust: 100%; scroll-behavior: smooth; }
body { font: 500 16px/1.45 var(--serif); -webkit-font-smoothing: antialiased; overflow-x: clip; }
a { color: inherit; text-decoration-thickness: 1px; text-underline-offset: .2em; }
:focus-visible { outline: 1px solid currentColor; outline-offset: 4px; }
::selection { background: var(--sky); color: var(--ink); }
img, svg { display: block; max-width: 100%; }
.vh { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
.mono { font: 400 11px/1.5 var(--mono); letter-spacing: .1em; text-transform: uppercase; }
.wrap { padding-inline: var(--pad); max-width: 1760px; margin-inline: auto; }
.g12 { display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); column-gap: var(--gap); }

/* the dark head of every chapter */
.head { background: var(--ink); color: var(--cream); position: relative; overflow: hidden; }
.head::before { content: ""; position: absolute; inset: 0; background: url(img/tex/grain-light.png) 0 0 / 128px 128px; pointer-events: none; }
.head .wrap { min-height: 470px; display: flex; flex-direction: column; justify-content: space-between; padding-top: 34px; padding-bottom: 40px; position: relative; }
.head.cover .wrap { min-height: min(100svh, 980px); }
.bar { align-items: center; }
.bar .home { grid-column: 1 / 4; display: block; width: 132px; text-decoration: none; }
.bar .title { grid-column: 4 / 9; font-size: 14px; }
.big { font: 400 clamp(76px, 15.6vw, 244px)/.86 var(--serif); letter-spacing: -.038em; margin-left: -.04em; padding-top: .5em; }
.cover .big { font-size: clamp(76px, 15.2vw, 248px); line-height: .84; }

/* the menu */
.mb { position: fixed; z-index: 60; top: 24px; right: 24px; width: 44px; height: 44px; border-radius: 11px; border: 1px solid rgba(238,234,224,.28); background: rgba(11,12,12,.86);
  color: var(--cream); display: grid; place-items: center; cursor: pointer; -webkit-backdrop-filter: blur(6px); backdrop-filter: blur(6px); }
.mb svg { width: 16px; height: 12px; }
.menu { position: fixed; inset: 0; z-index: 59; background: var(--ink); color: var(--cream); display: none; overflow-y: auto; }
.menu.on { display: block; }
.menu .wrap { padding-top: 34px; padding-bottom: 60px; }
.menu ol { list-style: none; margin-top: 12vh; }
.menu li a { display: grid; grid-template-columns: 2.2em minmax(0, 1fr); align-items: baseline; text-decoration: none; font: 400 clamp(40px, 6.4vw, 92px)/1.08 var(--serif); letter-spacing: -.025em; padding: .06em 0; }
.menu li a span { font-size: .42em; color: rgba(238,234,224,.5); letter-spacing: 0; }
.menu li a:hover em, .menu li a[aria-current] em { color: var(--sky); }
.menu em { font-style: normal; }

/* contents of a chapter, and the statement */
.toc { padding-top: 72px; }
.toc h2 { grid-column: 1 / 4; font: 400 38px/1 var(--serif); letter-spacing: -.02em; }
.toc ol { grid-column: 4 / 10; list-style: none; }
.toc li a { font: 600 21px/1.62 var(--serif); text-decoration: none; letter-spacing: -.005em; }
.toc li a:hover { text-decoration: underline; }
.intro { padding-top: 120px; align-items: start; }
.intro .st { grid-column: 1 / 9; font: 500 clamp(28px, 2.9vw, 42px)/1.13 var(--serif); letter-spacing: -.016em; text-wrap: pretty; }
.intro .act { grid-column: 10 / 13; justify-self: end; padding-top: 10px; }
.pill { display: inline-flex; align-items: center; gap: 10px; background: var(--sky); color: var(--ink); border-radius: 999px; padding: 10px 20px 11px; font: 600 14px/1 var(--serif); text-decoration: none; white-space: nowrap; }
.pill:hover { background: #B8EEFF; }
.pill svg { width: 11px; height: 11px; }

/* sections */
.sec { padding-top: 150px; }
.sec > .g12 { border-top: 1px solid var(--rule); padding-top: 16px; row-gap: 18px; }
.sec .lab { grid-column: 1 / 4; font: 600 23px/1.16 var(--serif); letter-spacing: -.01em; }
.sec .p1 { grid-column: 4 / 7; } .sec .p2 { grid-column: 7 / 10; } .sec .p12 { grid-column: 4 / 10; }
.sec .p1, .sec .p2, .sec .p12 { font-size: 15.5px; line-height: 1.46; text-wrap: pretty; }
.sec .p1 p + p, .sec .p2 p + p, .sec .p12 p + p { margin-top: .8em; }
.sec .act { grid-column: 10 / 13; justify-self: end; }
.body { margin-top: 64px; display: grid; gap: var(--gap); }
.sub { margin-top: 80px; }
.body > .sub:first-child { margin-top: 8px; }
.sub > .g12 { border-top: 1px solid var(--hair); padding-top: 14px; }
.sub .lab { font-size: 18px; }

.r2, .r3, .r4, .r5 { display: grid; gap: var(--gap); }
.r2 { grid-template-columns: repeat(2, minmax(0, 1fr)); } .r3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.r4 { grid-template-columns: repeat(4, minmax(0, 1fr)); } .r5 { grid-template-columns: repeat(5, minmax(0, 1fr)); }
figure { min-width: 0; display: grid; gap: 12px; align-content: start; }
figcaption { font-size: 14px; line-height: 1.42; color: var(--dim); max-width: 34em; }
figcaption b { display: block; color: var(--fg); font-weight: 600; font-size: 15px; margin-bottom: 2px; }

/* panels: the specimens sit on these */
.pan { position: relative; aspect-ratio: 16 / 9; display: grid; place-items: center; overflow: hidden; min-width: 0; }
.pan.sq { aspect-ratio: 1; } .pan.tall { aspect-ratio: 4 / 5; } .pan.wide { aspect-ratio: 21 / 8; } .pan.slim { aspect-ratio: 3 / 1; }
.pan.c { background: var(--cream) url(img/tex/grain-alpha.png) 0 0 / 128px 128px; box-shadow: inset 0 0 0 1px var(--hair); }
.pan.w { background: var(--washi) url(img/tex/grain-alpha.png) 0 0 / 128px 128px; box-shadow: inset 0 0 0 1px rgba(11,12,12,.08); }
.pan.i { background: var(--ink); color: var(--cream); }
.pan.s { background: var(--stone); color: var(--cream); }
.pan.p { background: var(--pru); color: var(--cream); }
.pan.k { background: var(--sky); }
.pan.i::before, .pan.s::before, .pan.p::before { content: ""; position: absolute; inset: 0; background: url(img/tex/grain-light.png) 0 0 / 128px 128px; pointer-events: none; }
.pan > .art { position: relative; }
.pan .tag { position: absolute; left: 18px; bottom: 15px; font: 400 10.5px/1 var(--mono); letter-spacing: .12em; text-transform: uppercase; opacity: .62; }
.pan .tag.r { left: auto; right: 18px; }
.pan .tag.t { bottom: auto; top: 16px; }
.pan > img.fill { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }

/* mock-ups, drawn at their true size and scaled to fit */
.mock { position: relative; overflow: hidden; width: 100%; }
.mock::after { content: ""; position: absolute; inset: 0; box-shadow: inset 0 0 0 1px var(--hair); pointer-events: none; }
.mock iframe { position: absolute; left: 0; top: 0; border: 0; transform-origin: 0 0; pointer-events: none; background: transparent; }
.mockrow { display: flex; gap: 14px; flex-wrap: wrap; font: 400 10.5px/1.4 var(--mono); letter-spacing: .1em; text-transform: uppercase; color: var(--dim); }
.mockrow a { color: var(--fg); }

/* tables */
.tab { width: 100%; border-collapse: collapse; font-size: 15px; }
.tab th, .tab td { text-align: left; vertical-align: top; padding: 12px 14px 12px 0; border-top: 1px solid var(--hair); }
.tab thead th { font: 400 10.5px/1.4 var(--mono); letter-spacing: .1em; text-transform: uppercase; color: var(--dim); border-top: 0; padding-bottom: 8px; }
.tab td.n { font: 400 13px/1.5 var(--mono); font-variant-numeric: tabular-nums; white-space: nowrap; }
.scroll { overflow-x: auto; }
.facts { display: grid; }
.facts > div { display: grid; grid-template-columns: minmax(0, 3fr) minmax(0, 9fr); column-gap: var(--gap); border-top: 1px solid var(--hair); padding: 13px 0 14px; }
.facts b { font: 400 13px/1.5 var(--mono); letter-spacing: .02em; color: var(--pru); }
.facts span { font-size: 15.5px; }

/* the foot of every chapter */
.foot { background: var(--pru); color: var(--cream); margin-top: 170px; position: relative; overflow: hidden; }
.foot::before { content: ""; position: absolute; inset: 0; background: url(img/tex/grain-light.png) 0 0 / 128px 128px; pointer-events: none; }
.foot .wrap { position: relative; padding-top: 96px; padding-bottom: 46px; }
.foot .huge { width: 100%; height: auto; }
.foot hr { border: 0; border-top: 1px solid rgba(238,234,224,.5); margin: 74px 0 30px; }
.pn { display: grid; grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr); align-items: center; gap: 24px; }
.pn a { font: 300 clamp(30px, 4.6vw, 68px)/1 var(--serif); letter-spacing: -.03em; text-decoration: none; white-space: nowrap; }
.pn a:hover { color: var(--sky); }
.pn .nx { justify-self: end; } .pn .sym { width: clamp(44px, 4.4vw, 62px); }
.foot .fine { margin-top: 56px; display: flex; justify-content: space-between; gap: 20px; font: 400 10.5px/1.5 var(--mono); letter-spacing: .12em; text-transform: uppercase; color: rgba(238,234,224,.62); }

@media (max-width: 1100px) {
  .sec .p1 { grid-column: 4 / 8; } .sec .p2 { grid-column: 8 / 13; } .sec .p12 { grid-column: 4 / 13; }
  .toc ol { grid-column: 4 / 13; }
  .r5 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .r4 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 760px) {
  :root { --pad: 20px; --gap: 12px; }
  body { font-size: 15px; }
  .g12 { grid-template-columns: minmax(0, 1fr); }
  .g12 > * { grid-column: 1 / -1 !important; }
  .head .wrap { min-height: 340px; padding-top: 22px; padding-bottom: 22px; }
  .head.cover .wrap { min-height: 88svh; }
  .bar { display: flex; gap: 16px; }
  .bar .home { width: 104px; } .bar .title { font-size: 12.5px; }
  .mb { top: 14px; right: 14px; width: 40px; height: 40px; }
  .big { font-size: clamp(48px, 16.4vw, 120px); letter-spacing: -.035em; }
  .cover .big { font-size: clamp(60px, 20.5vw, 120px); }
  .toc { padding-top: 44px; } .toc h2 { font-size: 30px; margin-bottom: 14px; } .toc li a { font-size: 18px; }
  .intro { padding-top: 64px; } .intro .st { font-size: 25px; line-height: 1.16; } .intro .act { justify-self: start; padding-top: 24px; }
  .sec { padding-top: 96px; } .sec .lab { font-size: 21px; } .sec .act { justify-self: start; }
  .body { margin-top: 36px; }
  .r2, .r3 { grid-template-columns: minmax(0, 1fr); }
  .r4, .r5 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .r2.keep { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .pan .tag { left: 12px; bottom: 10px; font-size: 9px; } .pan .tag.r { right: 12px; } .pan .tag.t { top: 10px; }
  .facts > div { grid-template-columns: minmax(0, 1fr); row-gap: 2px; }
  .foot { margin-top: 110px; } .foot .wrap { padding-top: 56px; padding-bottom: 30px; } .foot hr { margin: 44px 0 22px; }
  .pn { grid-template-columns: minmax(0, 1fr) auto; row-gap: 26px; }
  .pn .pv { grid-column: 1 / 2; } .pn .sym { grid-column: 2 / 3; grid-row: 1; justify-self: end; } .pn .nx { grid-column: 1 / -1; justify-self: start; }
  .pn a { font-size: 34px; }
  .foot .fine { flex-direction: column; gap: 4px; }
  .tab { font-size: 14px; }
  .pan.rdp { aspect-ratio: auto; padding: 28px 0 24px; }
  .rd { grid-template-columns: repeat(3, minmax(0, 1fr)) !important; row-gap: 26px !important; width: 90% !important; }
  .rd > span[aria-hidden] { display: none; }
  .ms { grid-template-columns: repeat(2, minmax(0, 1fr)) !important; row-gap: 30px !important; }
  .cons { overflow-x: auto; justify-items: start; place-items: start; padding: 16px 0; aspect-ratio: auto !important; }
  .cons > .art { width: 720px !important; flex: none; }
  .ccombo { grid-template-columns: repeat(3, minmax(0, 1fr)) !important; }
  .ramp { grid-template-columns: repeat(3, minmax(0, 1fr)) !important; }
  .wts { grid-template-columns: repeat(3, minmax(0, 1fr)) !important; row-gap: 18px; }
  .pan.wide.gridp { aspect-ratio: 4 / 3; }
  .pan.anno { aspect-ratio: 4 / 3; }
  .pan.anno > .art { width: 96% !important; }
  .scroll { overflow: visible; min-width: 0; max-width: 100%; }
  .tab { max-width: 100%; }
  .tab, .tab tbody, .tab tr, .tab th, .tab td { display: block; }
  .tab thead { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
  .tab tr { border-top: 1px solid var(--hair); padding: 12px 0 13px; }
  .tab tbody th, .tab tbody td { position: relative; padding: 2px 0 2px calc(6.4em + 12px); border-top: 0; white-space: normal !important; }
  .tab tbody th::before, .tab tbody td::before { content: attr(data-label); position: absolute; left: 0; top: 5px; font: 400 10px/1.5 var(--mono); letter-spacing: .1em; text-transform: uppercase; color: var(--dim); }
  .tab tbody tr > :first-child { display: block; padding: 0 0 6px; font-weight: 600; }
  .tab tbody tr > :first-child::before { content: none; }
  .tab td.n { white-space: normal; overflow-wrap: anywhere; }
  .scale td div { max-width: 100% !important; }
  .pan.tl { overflow-x: auto; place-items: center start; padding-left: 16px; }
}
@media (prefers-reduced-motion: reduce) { html { scroll-behavior: auto; } }
"""

ARROW_DL = '<svg viewBox="0 0 11 11" aria-hidden="true"><path d="M5.5 0V9M1.5 5.5L5.5 9.5L9.5 5.5M0 10.5H11" fill="none" stroke="currentColor" stroke-width="1.2"/></svg>'
BURGER = '<svg viewBox="0 0 16 12" aria-hidden="true"><path d="M0 .5H16M0 6H16M0 11.5H16" stroke="currentColor" stroke-width="1.1"/></svg>'

def esc(s): return H.escape(s, quote=True)

def menu(slug):
    items = "".join(f'<li><a href="{s}.html"{" aria-current=\"page\"" if s == slug else ""}><span>{i:02d}</span><em>{t}</em></a></li>' for i, (s, t) in enumerate(CH))
    return (f'<button class="mb" type="button" aria-expanded="false" aria-controls="menu" aria-label="Contents">{BURGER}</button>'
            f'<nav class="menu" id="menu" aria-label="Chapters"><div class="wrap"><div class="g12 bar"><a class="home" href="index.html" aria-label="Antimony brand guidelines">{g.caps(g.CREAM, g.SKY, style="width:100%;height:auto")}</a><span class="title">Brand guidelines</span></div><ol>{items}</ol></div></nav>')

MENU_JS = """<script>
(function () {
  var b = document.querySelector(".mb"), m = document.getElementById("menu");
  function set(on) { m.classList.toggle("on", on); b.setAttribute("aria-expanded", on ? "true" : "false"); b.setAttribute("aria-label", on ? "Close contents" : "Contents");
    b.innerHTML = on ? '<svg viewBox="0 0 12 12" aria-hidden="true" style="width:12px;height:12px"><path d="M.5 .5L11.5 11.5M11.5 .5L.5 11.5" stroke="currentColor" stroke-width="1.1"/></svg>' : '""" + BURGER.replace("'", "\\'") + """';
    document.documentElement.style.overflow = on ? "hidden" : ""; }
  b.addEventListener("click", function () { set(!m.classList.contains("on")); });
  addEventListener("keydown", function (e) { if (e.key === "Escape" && m.classList.contains("on")) { set(false); b.focus(); } });
  m.addEventListener("click", function (e) { if (e.target.closest("a")) set(false); });
  /* mock-ups are drawn at their true size and scaled to the width they are given */
  var ms = document.querySelectorAll(".mock");
  function fit() { ms.forEach(function (d) { var f = d.querySelector("iframe"); var k = d.clientWidth / (+f.getAttribute("width")); f.style.transform = "scale(" + k + ")"; }); }
  if (ms.length) { fit(); if (window.ResizeObserver) { var ro = new ResizeObserver(fit); ms.forEach(function (d) { ro.observe(d); }); } else addEventListener("resize", fit); }
})();
</script>"""

def head_html(title, desc):
    return (f'<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
            f'<meta name="theme-color" content="#0B0C0C"><title>{esc(title)}</title><meta name="description" content="{esc(desc)}">'
            f'<link rel="icon" href="img/favicon.svg" type="image/svg+xml"><link rel="icon" href="img/favicon-32.png" sizes="32x32" type="image/png"><link rel="apple-touch-icon" href="img/apple-touch-icon.png">'
            f'<link rel="preload" href="fonts/TimelessSerifVF.woff2" as="font" type="font/woff2" crossorigin>'
            f'<style>{CSS}</style></head><body>')

def chapter_head(slug, title, cover=False):
    return (f'<header class="head{" cover" if cover else ""}"><div class="wrap"><div class="g12 bar"><a class="home" href="index.html" aria-label="Antimony brand guidelines, introduction">{g.caps(g.CREAM, g.SKY, style="width:100%;height:auto")}</a>'
            f'<span class="title">Brand guidelines</span></div><h1 class="big">{title}</h1></div></header>')

def toc(name, sections):
    lis = "".join(f'<li><a href="#{a}">{esc(b)}</a></li>' for a, b in sections)
    return f'<nav class="wrap toc" aria-label="In this chapter"><div class="g12"><h2>{esc(name)}</h2><ol>{lis}</ol></div></nav>'

def intro(statement, action=""):
    return f'<section class="wrap"><div class="g12 intro"><p class="st">{statement}</p>{f"<div class=act>{action}</div>" if action else ""}</div></section>'

def pill(href, text, download=True):
    return f'<a class="pill" href="{href}"{" download" if download else ""}>{esc(text)}{ARROW_DL if download else ""}</a>'

def section(id_, label, p1="", p2="", body="", act="", wide_text=False):
    paras = (f'<div class="p12">{p1}</div>' if wide_text else (f'<div class="p1">{p1}</div>' if p1 else "") + (f'<div class="p2">{p2}</div>' if p2 else ""))
    return (f'<section class="wrap sec" id="{id_}"><div class="g12"><h2 class="lab">{label}</h2>{paras}{f"<div class=act>{act}</div>" if act else ""}</div>'
            + (f'<div class="body">{body}</div>' if body else "") + '</section>')

def sub(label, p1="", body="", p2=""):
    return (f'<div class="sub"><div class="g12"><h3 class="lab">{label}</h3>{f"<div class=p1>{p1}</div>" if p1 else ""}{f"<div class=p2>{p2}</div>" if p2 else ""}</div>'
            + (f'<div class="body">{body}</div>' if body else "") + '</div>')

def pan(content, kind="c", shape="", tag="", tag_r="", style="", cls="", label=None):
    t = (f'<span class="tag">{tag}</span>' if tag else "") + (f'<span class="tag r">{tag_r}</span>' if tag_r else "")
    lab = f' role="img" aria-label="{esc(label)}"' if label else ""
    return f'<div class="pan {kind} {shape} {cls}"{lab}{f" style={chr(34)}{style}{chr(34)}" if style else ""}>{content}{t}</div>'

def fig(panel, title="", text=""):
    cap = f"<figcaption>{f'<b>{title}</b>' if title else ''}{text}</figcaption>" if (title or text) else ""
    return f"<figure>{panel}{cap}</figure>"

def mock(src, w, h, title, links=()):
    lk = "".join(f'<a href="{a}" download>{esc(b)}</a>' for a, b in links)
    return (f'<figure><div class="mock" style="aspect-ratio:{w}/{h}"><iframe src="{src}" width="{w}" height="{h}" title="{esc(title)}" scrolling="no" tabindex="-1" aria-hidden="true"></iframe></div>'
            + (f'<div class="mockrow"><span>{w} &times; {h}</span>{lk}</div>' if True else "") + '</figure>')

def foot(slug):
    i = [s for s, _ in CH].index(slug)
    p = CH[i - 1] if i > 0 else None; n = CH[i + 1] if i < len(CH) - 1 else None
    pv = f'<a class="pv" href="{p[0]}.html">&larr; {p[1]}</a>' if p else '<span class="pv"></span>'
    nx = f'<a class="nx" href="{n[0]}.html">{n[1]} &rarr;</a>' if n else f'<a class="nx" href="index.html">Introduction &rarr;</a>'
    sym = g.mark(**g.mark_for(g.PRU), label="", style="width:100%;height:auto")
    return (f'<footer class="foot"><div class="wrap">{g.serif(g.CREAM, g.SKY, style="width:100%;height:auto;display:block").replace("<svg ", "<svg class=\"huge\" ", 1)}'
            f'<hr><nav class="pn" aria-label="Chapters">{pv}<span class="sym">{sym}</span>{nx}</nav>'
            f'<div class="fine"><span>Antimony brand guidelines</span><span>Edition three, October 2026</span></div></div></footer>')

def label_tables(body):
    """Gives every body cell its column's heading, so a table can stack into labelled rows on a phone."""
    def one(t):
        heads = re.findall(r"<th[^>]*>(.*?)</th>", re.search(r"<thead>(.*?)</thead>", t.group(0), re.S).group(1), re.S)
        def row(r):
            i = iter(heads)
            return re.sub(r"<(td|th)(?=[\s>])", lambda c: f'<{c.group(1)} data-label="{next(i, "")}"', r.group(0))
        return re.sub(r"<tbody>.*?</tbody>", lambda b: re.sub(r"<tr>.*?</tr>", row, b.group(0), flags=re.S), t.group(0), flags=re.S)
    return re.sub(r'<table class="tab[^"]*">.*?</table>', one, body, flags=re.S)

def page(slug, title, desc, body):
    return head_html(title, desc) + menu(slug) + label_tables(body) + foot(slug) + MENU_JS + "</body></html>"
